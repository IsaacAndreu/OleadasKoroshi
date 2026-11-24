# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Retener pedidos de tienda: revisa los pedidos S- de tienda de la noche y retiene los duplicados por tienda
# y los cancelados en S4T. Solo escribe en su tabla, en sus parametros y en mail.mail. No cancela nada.
# Diseno: bin/versiones/diseno-retener-pedidos-tienda_2026-11-24.md
# =============================================================================
import datetime
import logging

import pytz
import requests

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.addons.koroshi_base import comun

from .. import regla

_logger = logging.getLogger(__name__)

P = 'koroshi_retener_tiendas.'
PARAM_MODO = P + 'modo'                    # aviso (no aparta nada) o real (los enganches apartan los retenidos)
PARAM_HORAS = P + 'horas'                  # horas locales a las que el cron revisa y avisa: '04:40,05:45'
PARAM_ULTIMA = P + 'ultima'                # clave de la ultima revision del cron (la escribe el cron)
PARAM_HORA_NOCHE = P + 'hora_noche'        # desde que hora del dia anterior cuenta la noche: '14:00'
PARAM_TIPO = P + 'tipo_pedido'             # tipo de pedido de las tiendas: 'PED. TIENDAS'
PARAM_AVISAR = P + 'avisar'                # correos separados por comas
PARAM_S4T = P + 's4t'                      # 1 = preguntar el estado a S4T; 0 = solo duplicados (P0 del diseno)
PARAM_S4T_PAGINAS = P + 's4t_paginas'      # maximo de paginas de 500 pedidos que se leen de la API

MARGEN_MIN = 60
TIMEOUT = 30
TAMANO_PAGINA = 500
VIEWED = 'true'     # NUNCA 'false': marcaria como vistos los pedidos nuevos y Odoo ya no los crearia


class KoroshiPedidoRetenido(models.Model):
    _name = 'koroshi.pedido.retenido'
    _description = 'KOROSHI pedido de tienda retenido (duplicado o cancelado en S4T)'
    _order = 'noche desc, tienda, creado, id'
    _rec_name = 'pedido'

    noche = fields.Date('Noche', required=True, index=True, help='Día de la mañana en que se prepararía')
    sale_id = fields.Many2one('sale.order', 'Pedido de venta', required=True, index=True, ondelete='cascade')
    pedido = fields.Char('Pedido', required=True)
    tienda = fields.Char('Tienda', index=True)
    creado = fields.Datetime('Entró en Odoo')
    uds = fields.Float('Uds pedidas', digits=(16, 0))
    n_out = fields.Integer('OUT abiertas')
    estado_s4t = fields.Char('Estado en S4T', help='Vacío: S4T no se ha preguntado o no conoce el pedido')
    motivo = fields.Selection([(regla.DUPLICADO, 'Varios pedidos de la tienda'),
                               (regla.CANCELADO, 'Cancelado en S4T'),
                               (regla.DUPLICADO_CANCELADO, 'Varios pedidos y cancelado en S4T'),
                               (regla.UNICO_VIVO, 'Único vivo en S4T (pasa)')], 'Motivo', required=True)
    retener = fields.Boolean('Retenido', help='No entra en zonas ni en el reparto de operarios (en modo real)')
    decision = fields.Selection([('pendiente', 'Sin decidir'), ('preparar', 'Preparar'),
                                 ('cancelado', 'Cancelado en Odoo a mano')], 'Decisión', default='pendiente',
                                required=True)
    decidido_por = fields.Many2one('res.users', 'Decidido por', readonly=True)
    decidido_el = fields.Datetime('Decidido el', readonly=True)
    company_id = fields.Many2one('res.company', 'Compañía', default=lambda s: comun.COMPANY_ID)

    _sql_constraints = [('noche_pedido_unico', 'unique(noche, sale_id)', 'Un pedido solo una vez por noche.')]

    # ------------------------------------------------------------------ parametros
    @api.model
    def _param(self, clave, defecto=''):
        return (self.env['ir.config_parameter'].sudo().get_param(clave) or defecto).strip()

    @api.model
    def _modo(self):
        return self._param(PARAM_MODO, 'aviso').lower()

    # ------------------------------------------------------------------ lo que leen los enganches
    @api.model
    def pickings_retenidos(self):
        """Ids de las OUT abiertas de los pedidos retenidos sin decidir. Lo llaman zonas y operarios para dejarlas
        fuera. En modo aviso devuelve [] (no se aparta nada). Nunca falla: si algo va mal, [] y al log."""
        try:
            if self._modo() != 'real':
                return []
            filas = self.sudo().search([('retener', '=', True), ('decision', '=', 'pendiente')])
            outs = filas.mapped('sale_id.picking_ids').filtered(
                lambda p: p.picking_type_code == 'outgoing' and p.state not in ('done', 'cancel'))
            return outs.ids
        except Exception:
            _logger.exception('KOROSHI Retener: no se han podido leer los retenidos; no se aparta nada')
            return []

    # ------------------------------------------------------------------ pedidos de la noche
    @api.model
    def _pedidos_noche(self, ahora):
        hora_noche = regla.hora(self._param(PARAM_HORA_NOCHE, '14:00'), (14, 0))
        # la hora local sin zona y despues localize: el dia del cambio de hora el desfase es el de esa hora
        desde_local = comun.zona().localize(regla.inicio_noche(ahora.replace(tzinfo=None), hora_noche))
        desde = desde_local.astimezone(pytz.utc).replace(tzinfo=None)
        tipo = self._param(PARAM_TIPO, 'PED. TIENDAS')
        Venta = self.env['sale.order'].sudo().with_context(allowed_company_ids=[comun.COMPANY_ID])
        ventas = Venta.search([('company_id', '=', comun.COMPANY_ID), ('name', '=like', 'S-%'),
                               ('s_order_type_id.name', '=', tipo), ('state', '!=', 'cancel'),
                               ('create_date', '>=', desde.strftime('%Y-%m-%d %H:%M:%S'))], order='create_date, id')
        pedidos = []
        for v in ventas:
            outs = v.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing' and
                                          p.state not in ('done', 'cancel'))
            pedidos.append({
                'id': v.id,
                'name': v.name,
                'tienda': regla.tienda_de(v.partner_shipping_id.name or v.partner_id.name),
                'creado': v.create_date,
                'uds': sum(v.order_line.mapped('product_uom_qty')),
                'n_out': len(outs),
            })
        return pedidos

    # ------------------------------------------------------------------ S4T
    @api.model
    def _estados_s4t(self, numeros):
        """Estado de los pedidos en S4T. Solo GET y siempre viewed=true (viewed=false marcaria como vistos los
        pedidos nuevos y no se volverian a crear en Odoo). Devuelve (ok, {numero: ESTADO}, nota para el aviso)."""
        if self._param(PARAM_S4T, '0') != '1':
            return False, {}, 'no se pregunta (parámetro %s = 0): solo se miran los duplicados' % PARAM_S4T
        if not numeros:
            return True, {}, 'no hay pedidos que preguntar'
        if 's4t.config' not in self.env:
            return False, {}, 'sin módulo S4T (s4t.config): solo se miran los duplicados'
        config = self.env['s4t.config'].sudo().search([('state', '=', 'valid')], limit=1)
        if not config or not config.api_key or not config.host:
            return False, {}, 'sin configuración S4T válida: solo se miran los duplicados'
        base = config.host.rstrip('/')
        if '/api/service' not in base:
            base += '/api/service'
        try:
            paginas = max(int(self._param(PARAM_S4T_PAGINAS, '40')), 1)
        except ValueError:
            paginas = 40
        pendientes = set(numeros)
        estados = {}
        campos = {}
        leidos = 0
        try:
            for pagina in range(paginas):
                params = {'viewed': VIEWED, 'skip': pagina * TAMANO_PAGINA, 'limit': TAMANO_PAGINA}
                r = requests.get('%s/orders/b2b' % base, headers={'X-Api-Key': config.api_key}, params=params,
                                 timeout=TIMEOUT)
                if r.status_code != 200:
                    return False, {}, 'S4T contesta HTTP %s: solo se miran los duplicados' % r.status_code
                datos = r.json()
                items = datos
                if isinstance(datos, dict):
                    items = next((v for v in datos.values() if isinstance(v, list)), [])
                if not items:
                    break
                leidos += len(items)
                est, cam = regla.estados_de_items(items, pendientes)
                estados.update(est)
                for k, v in cam.items():
                    campos.setdefault(k, v)
                pendientes -= set(est)
                if not pendientes or len(items) < TAMANO_PAGINA:
                    break
        except Exception as e:
            _logger.warning('KOROSHI Retener: S4T no contesta: %s', e)
            return False, {}, 'S4T sin respuesta (%s): solo se miran los duplicados' % str(e)[:120]
        nota = 'leídos %s pedidos; %s de %s encontrados (campos: %s)' % (
            leidos, len(estados), len(numeros), ', '.join('%s=%s' % kv for kv in sorted(campos.items())) or '-')
        _logger.info('KOROSHI Retener: S4T %s', nota)
        return True, estados, nota

    # ------------------------------------------------------------------ revisar
    @api.model
    def revisar(self, avisar=False):
        """Revisa los pedidos de tienda de esta noche y apunta los retenidos. Las decisiones ya tomadas no se tocan.
        Devuelve (filas de esta noche, texto del aviso, noche)."""
        ahora = comun.ahora_local()
        hora_noche = regla.hora(self._param(PARAM_HORA_NOCHE, '14:00'), (14, 0))
        noche = regla.inicio_noche(ahora.replace(tzinfo=None), hora_noche).date() + datetime.timedelta(days=1)
        pedidos = self._pedidos_noche(ahora)
        ok, estados, nota = self._estados_s4t([regla.numero_s4t(p['name']) for p in pedidos if p['tienda']])
        resultado = regla.decidir(pedidos, estados, ok)
        Fila = self.sudo()
        existentes = dict((f.sale_id.id, f) for f in Fila.search([('noche', '=', noche)]))
        for p in pedidos:
            if p['id'] not in resultado:
                continue
            retener, motivo, est = resultado[p['id']]
            vals = {'tienda': p['tienda'], 'pedido': p['name'], 'creado': p['creado'], 'uds': p['uds'],
                    'n_out': p['n_out'], 'motivo': motivo, 'retener': retener}
            if est or ok:
                vals['estado_s4t'] = est
            fila = existentes.get(p['id'])
            if fila:
                if fila.decision == 'pendiente':
                    fila.write(vals)
                else:
                    fila.write({'n_out': p['n_out'], 'estado_s4t': vals.get('estado_s4t', fila.estado_s4t)})
            else:
                Fila.create(dict(vals, noche=noche, sale_id=p['id']))
        filas = Fila.search([('noche', '=', noche)])
        texto = regla.texto_aviso([{
            'tienda': f.tienda, 'pedido': f.pedido, 'hora': f.creado and comun.a_local(f.creado).strftime('%H:%M') or '',
            'uds': f.uds, 'estado_s4t': f.estado_s4t or '', 'motivo': f.motivo, 'retener': f.retener,
            'decision': f.decision} for f in filas], nota, self._modo())
        pendientes = filas.filtered(lambda f: f.retener and f.decision == 'pendiente')
        _logger.info('KOROSHI Retener: noche %s, %s pedidos, %s retenidos sin decidir. %s',
                     noche, len(pedidos), len(pendientes), nota)
        if avisar and pendientes:
            self._avisar('%s pedidos de tienda retenidos (%s tiendas)' % (
                len(pendientes), len(set(pendientes.mapped('tienda')))), texto)
        return filas, texto, noche

    @api.model
    def _avisar(self, asunto, texto):
        """Correo a los de koroshi_retener_tiendas.avisar. Nunca rompe el cron."""
        destinatarios = self._param(PARAM_AVISAR)
        if not destinatarios:
            _logger.warning('KOROSHI Retener: sin destinatarios en %s; el aviso solo queda en el log', PARAM_AVISAR)
            return False
        try:
            cuerpo = (texto or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            correo = self.env['mail.mail'].sudo().create({
                'subject': 'KOROSHI: %s' % asunto,
                'email_to': destinatarios,
                'body_html': '<pre style="font-size:12px">%s</pre>' % cuerpo,
                'auto_delete': False,
            })
            correo.send()
            return True
        except Exception:
            _logger.exception('KOROSHI Retener: no se ha podido enviar el aviso «%s»', asunto)
            return False

    @api.model
    def cron_revisar(self):
        """Cada 15 min: a las horas de koroshi_retener_tiendas.horas (04:40 y 05:45 de inicio), revisa la noche y,
        si hay retenidos sin decidir, avisa. Nunca rompe."""
        Param = self.env['ir.config_parameter'].sudo()
        ahora = comun.ahora_local()
        clave = regla.hora_pendiente(ahora, regla.horas(self._param(PARAM_HORAS, '04:40,05:45')),
                                     Param.get_param(PARAM_ULTIMA) or '', MARGEN_MIN)
        if not clave:
            return False
        Param.set_param(PARAM_ULTIMA, clave)
        try:
            with self.env.cr.savepoint():
                self.revisar(avisar=True)
        except Exception as e:
            _logger.exception('KOROSHI Retener: la revisión de las %s ha fallado', clave)
            self.env.cache.invalidate()
            self._avisar('ERROR al revisar los pedidos de tienda (%s)' % clave,
                         'La revisión de duplicados y cancelados en S4T ha fallado: %s\n'
                         'Los pedidos de esta noche NO se han revisado.' % e)
        return True

    # ------------------------------------------------------------------ pantalla
    @api.model
    def accion_revisar_ahora(self):
        """Menú «Revisar ahora»: revisa sin mandar correo, guarda y abre la lista de esta noche. (No se enseña el
        texto con un UserError: desharía lo guardado; display_notification no existe en Odoo 13.)"""
        _filas, _texto, noche = self.revisar(avisar=False)
        accion = self.env.ref('koroshi_retener_tiendas.action_koroshi_pedido_retenido').read()[0]
        accion['domain'] = [('noche', '=', fields.Date.to_string(noche))]
        accion['name'] = 'Pedidos de tienda: noche %s' % noche.strftime('%d/%m')
        return accion

    def _decidir(self, decision):
        if not self.env.user.has_group('stock.group_stock_manager'):
            raise UserError('Solo un responsable de almacén puede decidir sobre un pedido retenido.')
        self.sudo().write({'decision': decision, 'decidido_por': self.env.uid,
                           'decidido_el': fields.Datetime.now()})
        for f in self:
            if f.sale_id:
                f.sale_id.sudo().message_post(body='KOROSHI Retener (%s, noche %s): %s por %s.' % (
                    dict(self._fields['motivo'].selection).get(f.motivo), f.noche,
                    dict(self._fields['decision'].selection).get(decision), self.env.user.name))
        return True

    def accion_preparar(self):
        return self._decidir('preparar')

    def accion_cancelado(self):
        return self._decidir('cancelado')

    def accion_pendiente(self):
        return self._decidir('pendiente')
