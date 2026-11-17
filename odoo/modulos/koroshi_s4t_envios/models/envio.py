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
#
# v1.2 (14/11/2026, auditoria 13/11 fase 3):
#   - Una OUT pendiente ya no para el pedido entero: los trackings de las OUT hechas se mandan (sin is_final); el
#     final solo cuando ya no queda ninguna OUT por hacer. Si el ultimo ya se mando sin is_final, se reenvia con
#     is_final (S4T actualiza, no duplica).
#   - Errores: 408, 409, 429, 5xx y red se reintentan (hasta MAX_INTENTOS); los demas 4xx son definitivos
#     ('rechazado'): no se reintentan y se avisa (nota en el pedido y correo a koroshi_s4t_envios.avisar). Al agotar
#     los intentos tambien se avisa.
#   - Respuesta 200 con una lista en vez de un objeto: ya no rompe.
#   - Cron: los pedidos rechazados o con los intentos agotados ya no ocupan sitio, y se recorren por turnos
#     (koroshi_s4t_envios.cursor) para que los que esperan no tapen siempre a los mismos.
#   - Bultos, peso y volumen: los de koroshi_xpo_bultos (bultos_de, valores_xpo), la misma cuenta que XPO.
#   - Valorado queue_job (un job por pedido en root.s4t_sync): no hace falta con el cursor y los commits por pedido;
#     ademas ese canal ya dio problemas (pedidos atascados por canal sin configurar).
#
# v1.3 (17/11/2026, spec intent/carga-camion-bultos/spec_2026-11-17.md):
#   - Camion XPO: si koroshi_monitor 1.29 esta instalado (modelo koroshi.envio.cierre), un tracking XPO esta
#     'cerrado' cuando alguna de sus OUT va en un cierre (manifiesto enviado). El is_final (y SHIPPED) solo va cuando
#     todas las OUT del pedido estan hechas Y todos sus trackings XPO estan cerrados. GLS, como en la v1.2. Sin el
#     modelo de cierre, todo como en la v1.2.
#   - Correccion: si los bultos de un envio ya mandado cambian antes del cierre, pasa a 'corregir' (con los bultos
#     de S4T y los nuevos) y se corrige con el boton «Reenviar» (nunca solo). Despues del cierre, o con el final ya
#     mandado, solo se avisa con una nota en el pedido (una vez por cada cifra nueva).
# =============================================================================
import json
import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.koroshi_xpo_bultos.models.delivery_carrier import bultos_de, valores_xpo

_logger = logging.getLogger(__name__)

PARAM_MODO = 'koroshi_s4t_envios.modo'
PARAM_DESDE = 'koroshi_s4t_envios.desde'
PARAM_CURSOR = 'koroshi_s4t_envios.cursor'      # v1.2: ultimo pedido mirado por el cron
PARAM_AVISAR = 'koroshi_s4t_envios.avisar'      # v1.2: correos para los rechazos (separados por coma)
REINTENTABLES = (408, 409, 429)                 # v1.2: y cualquier 5xx
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
        ('error', 'Error (se reintenta)'),
        ('rechazado', 'Rechazado por S4T (no se reintenta)'),
        ('corregir', 'Bultos cambiados (pulsar Reenviar)'),     # v1.3
        ('omitido', 'Omitido'),
    ], string='Estado', default='diagnostico', readonly=True, index=True)
    # v1.3: correccion de bultos y cierre del camion XPO
    packages_nuevo = fields.Integer(string='Bultos nuevos (sin reenviar)', readonly=True)
    packages_aviso = fields.Integer(string='Bultos ya avisados', readonly=True)
    cerrado = fields.Boolean(string='Camion cerrado', readonly=True,
                             help='Alguna OUT de este tracking va en un manifiesto XPO enviado (koroshi_monitor).')
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
        todas = order.picking_ids.filtered(
            lambda p: p.picking_type_id.code == 'outgoing' and p.state != 'cancel')
        if not todas:
            return [], 'sin OUT'
        # v1.2: se mandan las OUT hechas; las que faltan no paran el pedido, solo el is_final
        picks = todas.filtered(lambda p: p.state == 'done')
        quedan = todas - picks
        if not picks:
            return [], 'OUT pendientes'
        if picks.filtered(lambda p: not p.carrier_tracking_ref):
            return [], 'alguna OUT hecha sin etiqueta'
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
        en_cierre = self._en_cierre(picks)          # v1.3: None = sin koroshi_monitor 1.29 (como la v1.2)

        valores = []
        for i, ref in enumerate(refs):
            outs = grupos[ref]
            carriers = set(self._transportista(p.carrier_id) for p in outs)
            carrier = carriers.pop() if len(carriers) == 1 else ''
            if not carrier:
                return [], '%s: transportista no es GLS/XPO' % ref
            if len(ref) > 50:
                return [], '%s: tracking de mas de 50 caracteres' % ref
            bultos = len(bultos_de(outs))            # v1.2: la misma cuenta que la expedicion XPO
            if bultos <= 0:
                return [], '%s: 0 cajas' % ref
            peso, volumen = valores_xpo(bultos)
            # v1.3: XPO cerrado = alguna de sus OUT va en un manifiesto enviado; GLS y sin cierres, siempre «cerrado»
            cerrado = carrier != 'XPO' or en_cierre is None or bool(set(outs.ids) & en_cierre)
            valores.append({
                'name': '%s / %s %s' % (order.name, carrier, ref),
                'sale_id': order.id,
                'order_number': order.s4t_order_number,
                'carrier': carrier,
                'tracking_number': ref,
                'packages': bultos,
                'weight_kg': peso,
                'volume_m3': volumen,
                'is_final': not quedan and i == len(refs) - 1,
                'cerrado': cerrado,
                'picking_ids': [(6, 0, outs.ids)],
            })
        # v1.3: el final solo cuando todos los trackings del pedido han salido en su camion
        if valores and not all(v['cerrado'] for v in valores):
            valores[-1]['is_final'] = False
        return valores, ''

    @api.model
    def _en_cierre(self, picks):
        """v1.3: ids de esas OUT que van en algun cierre de camion XPO (koroshi_monitor 1.29). None si no esta."""
        if 'koroshi.envio.cierre' not in self.env:
            return None
        cierres = self.env['koroshi.envio.cierre'].sudo().search([('picking_ids', 'in', picks.ids)])
        return set(cierres.mapped('picking_ids').ids) & set(picks.ids)

    def _avisar_bultos(self, nuevos):
        """v1.3: los bultos han cambiado cuando ya no se puede corregir: nota en el pedido, una vez por cifra."""
        self.ensure_one()
        if self.packages_aviso == nuevos:
            return
        motivo = self.cerrado and _('el camion ya ha salido') or _('el pedido ya esta en SHIPPED')
        texto = _('Envio a S4T %s: S4T tiene %d bultos y ahora salen %d, pero %s: no se corrige en S4T.') % (
            self.name, self.packages, nuevos, motivo)
        try:
            with self.env.cr.savepoint():
                self.sale_id.message_post(body=texto, subtype='mail.mt_note')
        except Exception:
            _logger.exception('KOROSHI S4T ENVIOS: no se ha podido avisar de los bultos de %s', self.name)
        self.write({'packages_aviso': nuevos})

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
            if rec and rec.state == 'rechazado':
                nuevos |= rec               # v1.2: definitivo; solo se reintenta con «Enviar ahora»
                continue
            if rec and rec.state in ('enviado', 'corregir'):
                # v1.3: S4T ya tiene este tracking con rec.packages bultos
                cambiado = vals['packages'] != rec.packages
                rec.write({'cerrado': vals['cerrado']})
                if cambiado and not vals['cerrado'] and not rec.is_final:
                    # Antes de que salga el camion: se marca y se corrige con «Reenviar» (nunca solo)
                    rec.write({'state': 'corregir', 'packages_nuevo': vals['packages']})
                    nuevos |= rec
                    continue
                if rec.state == 'corregir':
                    # Ha vuelto a la cifra de S4T, o el camion ya ha salido: ya no se corrige
                    rec.write({'state': 'enviado', 'packages_nuevo': 0})
                if cambiado:
                    rec._avisar_bultos(vals['packages'])
                if not (vals['is_final'] and not rec.is_final):
                    nuevos |= rec
                    continue
                # Ahora es el ultimo: se reenvia con is_final y con los bultos que S4T ya tiene
                vals = dict(vals, packages=rec.packages, weight_kg=rec.weight_kg, volume_m3=rec.volume_m3)
            vals = dict(vals)
            if not rec or rec.state in ('diagnostico', 'omitido', 'enviado'):
                # v1.2: 'enviado' aqui = se mando sin is_final y ahora es el ultimo: se reenvia con is_final
                vals['state'] = 'pendiente' if modo == 'real' else 'diagnostico'
                if rec and rec.state == 'enviado':
                    vals['intentos'] = 0
            if rec:
                rec.write(vals)
            else:
                rec = self.create(vals)
            nuevos |= rec
        # Trackings que ya no estan en el pedido (etiqueta cambiada): no se envian.
        (existentes - nuevos).filtered(lambda r: r.state not in ('enviado', 'corregir')).write({'state': 'omitido'})
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
            if isinstance(cuerpo, list):
                # v1.2: a veces llega una lista: se usa el primer objeto (y se guarda todo en la respuesta)
                completo = cuerpo
                cuerpo = dict(next((x for x in cuerpo if isinstance(x, dict)), {}))
                cuerpo.setdefault('_lista', completo)
            elif not isinstance(cuerpo, dict):
                cuerpo = {'detail': cuerpo}
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
                detalle = cuerpo.get('detail', cuerpo)
                reintentable = resp.status_code in REINTENTABLES or resp.status_code >= 500
                vals.update({
                    'state': reintentable and 'error' or 'rechazado',
                    'error': 'HTTP %s: %s' % (resp.status_code, json.dumps(detalle, ensure_ascii=False)[:1000]),
                })
                _logger.warning('KOROSHI S4T ENVIOS: %s -> HTTP %s (%s)', self.name, resp.status_code,
                                reintentable and 'se reintenta' or 'rechazado')
        except requests.exceptions.RequestException as e:
            vals.update({'state': 'error', 'error': 'Red: %s' % str(e)[:1000]})
            _logger.warning('KOROSHI S4T ENVIOS: %s -> error de red', self.name)
        self.write(vals)
        if self.state == 'rechazado' or (self.state == 'error' and self.intentos >= MAX_INTENTOS):
            self._avisar()
        return self.state == 'enviado'

    def _avisar(self):
        """v1.2: error definitivo (rechazado o intentos agotados): nota interna en el pedido y correo a los de
        koroshi_s4t_envios.avisar. Nunca para el cron."""
        self.ensure_one()
        motivo = self.state == 'rechazado' and _('S4T lo ha rechazado') or \
            _('%d intentos sin conseguirlo') % self.intentos
        texto = _('Envio a S4T %s (tracking %s): %s. %s') % (self.name, self.tracking_number, motivo, self.error or '')
        try:
            with self.env.cr.savepoint():
                self.sale_id.message_post(body=texto, subtype='mail.mt_note')
                correos = [c.strip() for c in (self.env['ir.config_parameter'].sudo().get_param(PARAM_AVISAR) or '')
                           .replace(';', ',').split(',') if c.strip()]
                if correos:
                    self.env['mail.mail'].sudo().create({
                        'subject': _('S4T: envio de %s sin enviar') % (self.sale_id.name or ''),
                        'body_html': '<p>%s</p><p>Inventario &gt; S4T &gt; Envios: revisarlo y «Enviar ahora».</p>'
                                     % texto,
                        'email_to': ', '.join(correos),
                        'auto_delete': True,
                    })
        except Exception:
            _logger.exception('KOROSHI S4T ENVIOS: no se ha podido avisar de %s', self.name)

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
        # v1.2: los atascados (rechazados o con los intentos agotados) no ocupan sitio: se arreglan a mano
        atascados = self.search(['|', ('state', '=', 'rechazado'),
                                 '&', ('state', '=', 'error'), ('intentos', '>=', MAX_INTENTOS)]).mapped('sale_id').ids
        dominio = [
            ('name', 'like', 'S-6665%'),
            ('state', 'in', ['sale', 'done']),
            ('x_s4t_status', '=', 'READY'),
            ('date_order', '>=', self._desde()),
            ('id', 'not in', terminados + atascados),
        ]
        # v1.2: por turnos: desde el ultimo mirado; al llegar al final se vuelve a empezar
        Param = self.env['ir.config_parameter'].sudo()
        try:
            cursor = int(Param.get_param(PARAM_CURSOR) or 0)
        except ValueError:
            cursor = 0
        Pedido = self.env['sale.order']
        pedidos = Pedido.search(dominio + [('id', '>', cursor)], order='id asc', limit=MAX_PEDIDOS_CRON)
        if len(pedidos) < MAX_PEDIDOS_CRON:
            pedidos |= Pedido.search(dominio + [('id', '<=', cursor), ('id', 'not in', pedidos.ids)],
                                     order='id asc', limit=MAX_PEDIDOS_CRON - len(pedidos))
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
        if pedidos:
            ultimo = pedidos[-1].id if len(pedidos) >= MAX_PEDIDOS_CRON else 0
            Param.set_param(PARAM_CURSOR, str(ultimo))
            self.env.cr.commit()
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
            todos.filtered(lambda r: r.state in ('diagnostico', 'error', 'rechazado')).write(
                {'state': 'pendiente', 'intentos': 0})
            todos._enviar_en_orden()
        return True

    def action_reenviar(self):
        """v1.3: manda a S4T los bultos nuevos de los envios en 'corregir' (mismo tracking: S4T actualiza, no duplica).
        Solo antes de que salga el camion; con el is_final que ya tenia."""
        if self._modo() != 'real':
            raise UserError(_('Modo diagnostico: no se envia nada a S4T (parametro %s).') % PARAM_MODO)
        for rec in self:
            if rec.state != 'corregir' or not rec.packages_nuevo:
                raise UserError(_('%s no tiene bultos pendientes de reenviar.') % rec.name)
            if rec.cerrado or rec.is_final:
                raise UserError(_('%s: el camion ya ha salido o el pedido ya esta en SHIPPED; no se corrige.')
                                % rec.name)
            peso, volumen = valores_xpo(rec.packages_nuevo)
            rec.write({'packages': rec.packages_nuevo, 'weight_kg': peso, 'volume_m3': volumen,
                       'packages_nuevo': 0, 'state': 'pendiente', 'intentos': 0})
            rec._post()
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
