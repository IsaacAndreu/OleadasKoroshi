# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Envios a S4T - POST /shipments                           v1.0 12/11/2026
#
# Un registro koroshi.s4t.envio = un POST /shipments = un tracking de un pedido.
#   order_number  = sale.order.s4t_order_number (el mismo del batch-update)
#   carrier       = XPO o GLS segun el transportista de las OUT
#   packages      = cajas destino distintas (result_package_id) de esas OUT
#   weight_kg     = 15 kg x cajas   (v1.1: criterio con el que factura XPO, igual que koroshi_xpo_bultos v1.1)
#   volume_m3     = 0,09 m3 x cajas (v1.1: idem; antes volumen de producto, con 0,09 m3/UNIDAD sin dato)
#   is_final      = true solo en el ultimo tracking del pedido (S4T pasa la orden a SHIPPED)
#
# Seguridad: modo 'diagnostico' (parametro koroshi_s4t_envios.modo) -> nunca llama a S4T.
# Reenviar el mismo order_number + tracking_number en S4T actualiza, no duplica.
# =============================================================================
import json
import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

PARAM_MODO = 'koroshi_s4t_envios.modo'
PARAM_DESDE = 'koroshi_s4t_envios.desde'
PESO_BULTO = 15.0       # kg por caja (criterio XPO)
VOLUMEN_BULTO = 0.09    # m3 por caja (criterio XPO)
TIMEOUT = 30
MAX_INTENTOS = 5
MAX_PEDIDOS_CRON = 500


class KoroshiS4tEnvio(models.Model):
    _name = 'koroshi.s4t.envio'
    _description = 'Envio a S4T (POST /shipments)'
    _order = 'id desc'

    name = fields.Char(string='Envio', required=True, readonly=True)
    sale_id = fields.Many2one('sale.order', string='Pedido', required=True, readonly=True,
                              index=True, ondelete='cascade')
    order_number = fields.Char(string='Order number S4T', readonly=True)
    carrier = fields.Selection([('XPO', 'XPO'), ('GLS', 'GLS')], string='Transportista', readonly=True)
    tracking_number = fields.Char(string='Tracking', required=True, readonly=True, index=True)
    packages = fields.Integer(string='Bultos', readonly=True)
    weight_kg = fields.Float(string='Peso (kg)', digits=(12, 2), readonly=True)
    volume_m3 = fields.Float(string='Volumen (m3)', digits=(12, 3), readonly=True)
    is_final = fields.Boolean(string='Ultimo envio (is_final)', readonly=True)
    picking_ids = fields.Many2many('stock.picking', 'koroshi_s4t_envio_picking_rel', 'envio_id', 'picking_id',
                                   string='OUT', readonly=True)
    state = fields.Selection([
        ('diagnostico', 'Diagnostico (no enviado)'),
        ('pendiente', 'Pendiente de enviar'),
        ('enviado', 'Enviado'),
        ('error', 'Error'),
        ('omitido', 'Omitido'),
    ], string='Estado', default='diagnostico', readonly=True, index=True)
    intentos = fields.Integer(string='Intentos', readonly=True)
    fecha_envio = fields.Datetime(string='Fecha envio', readonly=True)
    order_status = fields.Char(string='Estado orden en S4T', readonly=True)
    respuesta = fields.Text(string='Respuesta S4T', readonly=True)
    error = fields.Text(string='Error', readonly=True)

    _sql_constraints = [
        ('pedido_tracking_uniq', 'unique (sale_id, tracking_number)',
         'Ya hay un envio con ese tracking para este pedido.'),
    ]

    # ------------------------------------------------------------------
    # Configuracion
    # ------------------------------------------------------------------
    @api.model
    def _modo(self):
        return (self.env['ir.config_parameter'].sudo().get_param(PARAM_MODO) or 'diagnostico').strip().lower()

    @api.model
    def _desde(self):
        return self.env['ir.config_parameter'].sudo().get_param(PARAM_DESDE) or '2026-11-01 00:00:00'

    @api.model
    def _api(self):
        config = self.env['s4t.config'].sudo().search([('state', '=', 'valid')], limit=1)
        if not config or not config.api_key or not config.host:
            raise UserError(_('No hay configuracion S4T valida (host y X-Api-Key).'))
        cabeceras = {'X-Api-Key': config.api_key, 'Content-Type': 'application/json'}
        return config.host.rstrip('/'), cabeceras

    # ------------------------------------------------------------------
    # Calculo de los envios de un pedido
    # ------------------------------------------------------------------
    @api.model
    def _transportista(self, carrier):
        texto = ('%s %s' % (carrier.delivery_type or '', carrier.name or '')).upper()
        if 'XPO' in texto:
            return 'XPO'
        if 'GLS' in texto:
            return 'GLS'
        return ''

    @api.model
    def _calcular(self, order):
        """Devuelve (lista de valores por tracking, motivo si no se puede enviar)."""
        picks = order.picking_ids.filtered(
            lambda p: p.picking_type_id.code == 'outgoing' and p.state != 'cancel')
        if not picks:
            return [], 'sin OUT'
        if any(p.state != 'done' for p in picks):
            return [], 'OUT pendientes'
        if picks.filtered(lambda p: not p.carrier_tracking_ref):
            return [], 'alguna OUT sin etiqueta'
        if order.x_s4t_status != 'READY':
            return [], 'en S4T no esta READY (%s)' % (order.x_s4t_status or 'vacio')
        if not order.s4t_order_number:
            return [], 'sin s4t_order_number'

        grupos = {}
        for p in picks:
            ref = p.carrier_tracking_ref.strip()
            grupos.setdefault(ref, self.env['stock.picking'])
            grupos[ref] |= p
        refs = sorted(grupos, key=lambda r: max(str(x.date_done or x.write_date) for x in grupos[r]))

        valores = []
        for i, ref in enumerate(refs):
            outs = grupos[ref]
            carriers = set(self._transportista(p.carrier_id) for p in outs)
            carrier = carriers.pop() if len(carriers) == 1 else ''
            if not carrier:
                return [], '%s: transportista no es GLS/XPO' % ref
            if len(ref) > 50:
                return [], '%s: tracking de mas de 50 caracteres' % ref
            lineas = outs.mapped('move_line_ids').filtered(lambda ml: ml.qty_done > 0)
            bultos = len(lineas.mapped('result_package_id'))
            if bultos <= 0:
                return [], '%s: 0 cajas' % ref
            valores.append({
                'name': '%s / %s %s' % (order.name, carrier, ref),
                'sale_id': order.id,
                'order_number': order.s4t_order_number,
                'carrier': carrier,
                'tracking_number': ref,
                'packages': bultos,
                'weight_kg': round(PESO_BULTO * bultos, 2),
                'volume_m3': round(VOLUMEN_BULTO * bultos, 3),
                'is_final': i == len(refs) - 1,
                'picking_ids': [(6, 0, outs.ids)],
            })
        return valores, ''

    @api.model
    def _sincronizar_pedido(self, order, modo):
        """Crea o actualiza los registros del pedido. No llama a S4T."""
        valores, motivo = self._calcular(order)
        if motivo:
            return self.browse(), motivo
        existentes = self.search([('sale_id', '=', order.id)])
        nuevos = self.browse()
        refs = []
        for vals in valores:
            refs.append(vals['tracking_number'])
            rec = existentes.filtered(lambda r: r.tracking_number == vals['tracking_number'])
            if rec and rec.state == 'enviado':
                nuevos |= rec
                continue
            vals = dict(vals)
            if not rec or rec.state in ('diagnostico', 'omitido'):
                vals['state'] = 'pendiente' if modo == 'real' else 'diagnostico'
            if rec:
                rec.write(vals)
            else:
                rec = self.create(vals)
            nuevos |= rec
        # Trackings que ya no estan en el pedido (etiqueta cambiada): no se envian.
        (existentes - nuevos).filtered(lambda r: r.state != 'enviado').write({'state': 'omitido'})
        return nuevos, ''

    # ------------------------------------------------------------------
    # Llamadas a S4T
    # ------------------------------------------------------------------
    def _post(self):
        self.ensure_one()
        if self._modo() != 'real':
            raise UserError(_('Modo diagnostico: no se envia nada a S4T (parametro %s).') % PARAM_MODO)
        host, cabeceras = self._api()
        payload = {
            'order_number': self.order_number,
            'carrier': self.carrier,
            'tracking_number': self.tracking_number,
            'packages': self.packages,
            'weight_kg': self.weight_kg,
            'volume_m3': self.volume_m3,
            'is_final': self.is_final,
        }
        vals = {'intentos': self.intentos + 1}
        try:
            resp = requests.post(host + '/shipments', headers=cabeceras, data=json.dumps(payload), timeout=TIMEOUT)
            try:
                cuerpo = resp.json()
            except ValueError:
                cuerpo = {'detail': (resp.text or '')[:500]}
            if resp.status_code in (200, 201):
                vals.update({
                    'state': 'enviado',
                    'fecha_envio': fields.Datetime.now(),
                    'order_status': cuerpo.get('order_status') or '',
                    'respuesta': json.dumps(cuerpo, ensure_ascii=False)[:4000],
                    'error': False,
                })
                _logger.info('KOROSHI S4T ENVIOS: %s -> %s', self.name, vals['order_status'])
            else:
                detalle = cuerpo.get('detail') if isinstance(cuerpo, dict) else cuerpo
                vals.update({
                    'state': 'error',
                    'error': 'HTTP %s: %s' % (resp.status_code, json.dumps(detalle, ensure_ascii=False)[:1000]),
                })
                _logger.warning('KOROSHI S4T ENVIOS: %s -> HTTP %s', self.name, resp.status_code)
        except requests.exceptions.RequestException as e:
            vals.update({'state': 'error', 'error': 'Red: %s' % str(e)[:1000]})
            _logger.warning('KOROSHI S4T ENVIOS: %s -> error de red', self.name)
        self.write(vals)
        return self.state == 'enviado'

    def _enviar_en_orden(self):
        """Envia los registros de UN pedido: primero los no finales; el final solo si los otros estan enviados."""
        pendientes = self.filtered(lambda r: r.state in ('pendiente', 'error') and r.intentos < MAX_INTENTOS)
        for rec in pendientes.filtered(lambda r: not r.is_final):
            rec._post()
        if all(r.state == 'enviado' for r in self.filtered(lambda r: not r.is_final)):
            for rec in pendientes.filtered(lambda r: r.is_final):
                rec._post()

    # ------------------------------------------------------------------
    # Cron
    # ------------------------------------------------------------------
    @api.model
    def cron_enviar(self):
        modo = self._modo()
        terminados = self.search([('state', '=', 'enviado'), ('is_final', '=', True)]).mapped('sale_id').ids
        pedidos = self.env['sale.order'].search([
            ('name', 'like', 'S-6665%'),
            ('state', 'in', ['sale', 'done']),
            ('x_s4t_status', '=', 'READY'),
            ('date_order', '>=', self._desde()),
            ('id', 'not in', terminados),
        ], order='date_order asc', limit=MAX_PEDIDOS_CRON)
        listos = esperando = enviados = errores = 0
        for order in pedidos:
            try:
                recs, motivo = self._sincronizar_pedido(order, modo)
                if motivo:
                    esperando += 1
                    self.env.cr.commit()
                    continue
                listos += 1
                if modo == 'real':
                    recs._enviar_en_orden()
                    enviados += len(recs.filtered(lambda r: r.state == 'enviado'))
                    errores += len(recs.filtered(lambda r: r.state == 'error'))
                self.env.cr.commit()
            except Exception as e:
                self.env.cr.rollback()
                errores += 1
                _logger.exception('KOROSHI S4T ENVIOS: error en %s: %s', order.name, e)
        _logger.info('KOROSHI S4T ENVIOS (modo %s): %d pedidos mirados, %d listos, %d esperando, '
                     '%d envios OK, %d con error', modo, len(pedidos), listos, esperando, enviados, errores)
        return True

    # ------------------------------------------------------------------
    # Botones
    # ------------------------------------------------------------------
    def action_enviar_ahora(self):
        """Envia el pedido entero (todos sus trackings, el final el ultimo)."""
        if self._modo() != 'real':
            raise UserError(_('Modo diagnostico: no se envia nada a S4T (parametro %s).') % PARAM_MODO)
        for order in self.mapped('sale_id'):
            todos = self.search([('sale_id', '=', order.id), ('state', '!=', 'omitido')])
            todos.filtered(lambda r: r.state in ('diagnostico', 'error')).write({'state': 'pendiente', 'intentos': 0})
            todos._enviar_en_orden()
        return True

    def action_consultar_s4t(self):
        """GET /shipments?order_number=... Solo lectura: no cambia nada en S4T."""
        host, cabeceras = self._api()
        for rec in self:
            try:
                resp = requests.get(host + '/shipments', headers=cabeceras,
                                    params={'order_number': rec.order_number}, timeout=TIMEOUT)
                texto = 'HTTP %s: %s' % (resp.status_code, (resp.text or '')[:4000])
            except requests.exceptions.RequestException as e:
                texto = 'Red: %s' % str(e)[:1000]
            rec.write({'respuesta': 'CONSULTA %s\n%s' % (fields.Datetime.now(), texto)})
        return True

    def action_recalcular(self):
        modo = self._modo()
        for order in self.mapped('sale_id'):
            self._sincronizar_pedido(order, modo)
        return True
