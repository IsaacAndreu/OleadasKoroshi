# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Traspasos S4T - devoluciones e-commerce y correcciones        v1.0 12/11/2026
#
# Concepto:
#   1. DESCARGAR: GET /transfers/<endpoint>?viewed=false&skip=0&limit=100, repetido hasta que llegue vacio.
#      S4T marca cada traspaso como descargado la primera vez que lo devuelve: por eso cada pagina se
#      GUARDA y se hace commit ANTES de pedir la siguiente. Si algo se perdiera, se recupera por fecha
#      (asistente "Recuperar por fecha": transfer_date, sin viewed) y se descartan los ya guardados por transfer_id.
#   2. PROCESAR (cada traspaso por separado, un error no para el resto):
#      - devolucion -> recepcion DEV de 6665 (Clientes -> DEVOLUCIO_KOROSHI), confirmada y lista para validar.
#      - correccion -> solo se registra (tienda, articulos, +/-). No mueve stock.
#   SKU Odoo (product.style_code) = article_id-color_id-size  (p. ej. 2512PT89-000030-38).
#   Tienda = res.partner con barcode = destination_id (p. ej. 00000010 = K10).
#
# v1.1 (14/11/2026, auditoria 13/11 fase 3):
#   - Cada traspaso se guarda en su propio savepoint y PRIMERO el JSON crudo: si uno trae algo raro, se queda guardado
#     en 'error' con el JSON y el resto de la pagina sigue (antes fallaba la pagina entera, y S4T ya la habia marcado
#     como descargada: se perdia).
#   - Conciliacion diaria: una vez al dia (desde koroshi_s4t_traspasos.hora_conciliacion, 06:00) se vuelven a pedir
#     por fecha los de hoy y ayer y se guardan los que falten.
#   - Los que dan error se reintentan en cada pasada hasta MAX_INTENTOS veces.
# =============================================================================
import datetime
import hashlib
import json
import logging

import pytz

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

COMPANY_ID = 8                     # EFFECTIVE LOGISTICS, S.L.
TIMEOUT = 60
LIMITE_PAGINA = 100
MAX_PAGINAS = 50                   # proteccion: 5.000 traspasos por pasada como mucho
MAX_INTENTOS = 5                   # v1.1: veces que se reintenta procesar uno con error
TZ = 'Europe/Madrid'
P = 'koroshi_s4t_traspasos.'
ENDPOINTS = {
    'devolucion': '/transfers/return-ecommerce',
    'correccion': '/transfers/corrections',
}


class KoroshiS4tTraspaso(models.Model):
    _name = 'koroshi.s4t.traspaso'
    _description = 'Traspaso S4T (devolucion e-commerce o correccion)'
    _order = 'transfer_date desc, id desc'

    name = fields.Char(string='Traspaso', required=True, readonly=True, index=True)
    tipo = fields.Selection([('devolucion', 'Devolucion e-commerce'), ('correccion', 'Correccion')],
                            string='Tipo', required=True, readonly=True, index=True)
    transfer_type = fields.Char(string='Tipo S4T', readonly=True)
    status = fields.Char(string='Estado S4T', readonly=True)
    transfer_date = fields.Date(string='Fecha', readonly=True)
    origin_id = fields.Char(string='Origen', readonly=True)
    destination_id = fields.Char(string='Destino', readonly=True)
    warehouse_id_s4t = fields.Char(string='Almacen S4T', readonly=True)
    operator_id = fields.Char(string='Operario S4T', readonly=True)
    total_quantity = fields.Float(string='Unidades', readonly=True)
    customer_viewed_at = fields.Char(string='Descargado antes en S4T', readonly=True)
    tienda_id = fields.Many2one('res.partner', string='Tienda', readonly=True)
    line_ids = fields.One2many('koroshi.s4t.traspaso.linea', 'traspaso_id', string='Lineas', readonly=True)
    picking_id = fields.Many2one('stock.picking', string='Recepcion', readonly=True)
    state = fields.Selection([
        ('nuevo', 'Nuevo'),
        ('recepcion', 'Recepcion creada'),
        ('registrado', 'Registrado'),
        ('error', 'Error'),
    ], string='Estado', default='nuevo', readonly=True, index=True)
    error = fields.Text(string='Error', readonly=True)
    datos = fields.Text(string='JSON recibido', readonly=True)
    intentos = fields.Integer(string='Intentos', readonly=True, help='v1.1: veces que se ha intentado procesar')

    _sql_constraints = [
        ('traspaso_uniq', 'unique (name, tipo)', 'Este traspaso de S4T ya esta guardado.'),
    ]

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------
    @api.model
    def _api(self):
        config = self.env['s4t.config'].sudo().search([('state', '=', 'valid')], limit=1)
        if not config or not config.api_key or not config.host:
            raise UserError(_('No hay configuracion S4T valida (host y X-Api-Key).'))
        return config.host.rstrip('/'), {'X-Api-Key': config.api_key}

    @api.model
    def _get(self, tipo, params):
        host, cabeceras = self._api()
        resp = requests.get(host + ENDPOINTS[tipo], headers=cabeceras, params=params, timeout=TIMEOUT)
        if resp.status_code != 200:
            raise UserError(_('S4T %s: HTTP %s %s') % (ENDPOINTS[tipo], resp.status_code, (resp.text or '')[:300]))
        cuerpo = resp.json()
        if isinstance(cuerpo, list):        # v1.1: por si llega la lista sola
            return cuerpo
        return (cuerpo or {}).get('transfers') or []

    # ------------------------------------------------------------------
    # Guardar
    # ------------------------------------------------------------------
    @api.model
    def _guardar(self, tipo, transfers):
        """Crea los traspasos que no esten ya guardados. Devuelve cuantos son nuevos.
        v1.1: uno a uno, cada uno en su savepoint. Si uno falla, se guarda igual con su JSON en 'error'."""
        nuevos = 0
        for t in transfers:
            crudo = json.dumps(t, ensure_ascii=False, default=str)
            tid = (isinstance(t, dict) and str(t.get('transfer_id') or '').strip()) or \
                'SIN_ID_%s' % hashlib.md5(crudo.encode('utf-8')).hexdigest()[:12]
            if self.search_count([('name', '=', tid), ('tipo', '=', tipo)]):
                continue
            try:
                with self.env.cr.savepoint():
                    self.create(self._valores(tipo, tid, t, crudo))
            except Exception as e:
                _logger.exception('KOROSHI S4T TRASPASOS: %s %s no se ha podido guardar entero', tipo, tid)
                with self.env.cr.savepoint():
                    self.create({'name': tid, 'tipo': tipo, 'datos': crudo, 'state': 'error',
                                 'intentos': MAX_INTENTOS,
                                 'error': _('No se ha podido guardar (revisar el JSON): %s') % str(e)[:1500]})
            nuevos += 1
        return nuevos

    @api.model
    def _valores(self, tipo, tid, t, crudo):
        if not isinstance(t, dict):
            raise UserError(_('El traspaso no es un objeto JSON'))
        tienda_codigo = t.get('destination_id') if tipo == 'correccion' else t.get('origin_id')
        tienda = self.env['res.partner'].sudo().search([('barcode', '=', tienda_codigo)], limit=1) \
            if tienda_codigo else self.env['res.partner']
        lineas = []
        for l in t.get('lines') or []:
            lineas.append((0, 0, {
                'line_number': l.get('line_number'),
                'article_id': l.get('article_id'),
                'color_id': l.get('color_id'),
                'size': l.get('size'),
                'quantity': l.get('quantity') or 0.0,
                'boxes': l.get('boxes') or 0.0,
            }))
        return {
            'name': tid,
            'tipo': tipo,
            'transfer_type': t.get('transfer_type'),
            'status': t.get('status'),
            'transfer_date': t.get('transfer_date') or False,
            'origin_id': t.get('origin_id'),
            'destination_id': t.get('destination_id'),
            'warehouse_id_s4t': t.get('warehouse_id'),
            'operator_id': t.get('operator_id'),
            'total_quantity': t.get('total_quantity') or 0.0,
            'customer_viewed_at': t.get('customer_viewed_at') or False,
            'tienda_id': tienda.id or False,
            'line_ids': lineas,
            'datos': crudo,
        }

    @api.model
    def descargar_nuevos(self, tipo):
        """viewed=false y skip=0 siempre, hasta que llegue vacio. Commit despues de guardar cada pagina."""
        total = 0
        for _pagina in range(MAX_PAGINAS):
            transfers = self._get(tipo, {'viewed': 'false', 'skip': 0, 'limit': LIMITE_PAGINA})
            if not transfers:
                break
            total += self._guardar(tipo, transfers)
            self.env.cr.commit()
        return total

    @api.model
    def recuperar_por_fecha(self, tipo, fecha):
        """Vuelve a pedir los traspasos de un dia (sin viewed) y guarda solo los que falten."""
        total = 0
        skip = 0
        for _pagina in range(MAX_PAGINAS):
            transfers = self._get(tipo, {'transfer_date': fecha, 'skip': skip, 'limit': LIMITE_PAGINA})
            if not transfers:
                break
            total += self._guardar(tipo, transfers)
            skip += len(transfers)
        return total

    # ------------------------------------------------------------------
    # Procesar
    # ------------------------------------------------------------------
    @api.model
    def _tipo_dev(self):
        return self.env['stock.picking.type'].sudo().search([
            ('company_id', '=', COMPANY_ID), ('code', '=', 'incoming'), ('sequence_code', '=', 'DEV'),
            ('warehouse_id.code', '=', 'EFFEC')], limit=1)

    def _procesar_uno(self):
        self.ensure_one()
        faltan = self.line_ids.filtered(lambda l: not l.product_id)
        if faltan:
            raise UserError(_('Articulos no encontrados en Odoo: %s') % ', '.join(faltan.mapped('sku')))
        if self.tipo == 'correccion':
            self.write({'state': 'registrado', 'error': False})
            return
        tipo_dev = self._tipo_dev()
        if not tipo_dev:
            raise UserError(_('No se encuentra el tipo de operacion DEV de 6665.'))
        cantidades = {}
        for l in self.line_ids:
            if l.quantity <= 0:
                raise UserError(_('Linea con cantidad %s en una devolucion: %s') % (l.quantity, l.sku))
            cantidades[l.product_id] = cantidades.get(l.product_id, 0.0) + l.quantity
        origen = tipo_dev.default_location_src_id or self.env.ref('stock.stock_location_customers')
        destino = tipo_dev.default_location_dest_id
        Picking = self.env['stock.picking'].with_context(force_company=COMPANY_ID,
                                                         allowed_company_ids=[COMPANY_ID]).sudo()
        picking = Picking.create({
            'picking_type_id': tipo_dev.id,
            'location_id': origen.id,
            'location_dest_id': destino.id,
            'partner_id': self.tienda_id.id or False,
            'origin': 'S4T DevoEcom %s' % self.name,
            'company_id': COMPANY_ID,
            'move_lines': [(0, 0, {
                'name': producto.display_name,
                'product_id': producto.id,
                'product_uom': producto.uom_id.id,
                'product_uom_qty': cantidad,
                'location_id': origen.id,
                'location_dest_id': destino.id,
                'company_id': COMPANY_ID,
            }) for producto, cantidad in cantidades.items()],
        })
        picking.action_confirm()
        picking.action_assign()
        picking.message_post(body=_('Devolucion e-commerce %s de S4T (%s, %s uds). Recepcion creada '
                                    'automaticamente: validar al recibir las prendas.')
                             % (self.name, self.transfer_date or '', self.total_quantity))
        self.write({'state': 'recepcion', 'picking_id': picking.id, 'error': False})

    def action_procesar(self):
        hechos = 0
        for rec in self.filtered(lambda r: r.state in ('nuevo', 'error')):
            try:
                with self.env.cr.savepoint():
                    rec._procesar_uno()
                    rec.write({'intentos': rec.intentos + 1})
                hechos += 1
            except Exception as e:
                rec.write({'state': 'error', 'error': str(e)[:2000], 'intentos': rec.intentos + 1})
                _logger.warning('KOROSHI S4T TRASPASOS: %s %s -> %s', rec.tipo, rec.name, e)
        return hechos

    @api.model
    def conciliar(self, forzar=False):
        """v1.1: una vez al dia (desde koroshi_s4t_traspasos.hora_conciliacion) vuelve a pedir por fecha los de hoy y
        ayer y guarda los que falten. Devuelve cuantos ha recuperado (None si hoy ya se habia hecho)."""
        Param = self.env['ir.config_parameter'].sudo()
        ahora = datetime.datetime.now(pytz.timezone(TZ))
        hoy = ahora.date()
        if not forzar:
            if Param.get_param(P + 'ultima_conciliacion') == hoy.isoformat():
                return None
            try:
                hh, mm = [int(x) for x in (Param.get_param(P + 'hora_conciliacion') or '06:00').split(':')]
            except ValueError:
                hh, mm = 6, 0
            if (ahora.hour, ahora.minute) < (hh, mm):
                return None
        total = 0
        for tipo in ('devolucion', 'correccion'):
            for dia in (hoy - datetime.timedelta(days=1), hoy):
                try:
                    total += self.recuperar_por_fecha(tipo, dia.isoformat())
                    self.env.cr.commit()
                except Exception as e:
                    self.env.cr.rollback()
                    _logger.exception('KOROSHI S4T TRASPASOS: conciliacion %s %s: %s', tipo, dia, e)
        Param.set_param(P + 'ultima_conciliacion', hoy.isoformat())
        _logger.info('KOROSHI S4T TRASPASOS: conciliacion de hoy y ayer: %d recuperados', total)
        return total

    # ------------------------------------------------------------------
    # Cron
    # ------------------------------------------------------------------
    @api.model
    def cron_traspasos(self):
        for tipo in ('devolucion', 'correccion'):
            try:
                nuevos = self.descargar_nuevos(tipo)
                _logger.info('KOROSHI S4T TRASPASOS: %s: %d nuevos guardados', tipo, nuevos)
            except Exception as e:
                self.env.cr.rollback()
                _logger.exception('KOROSHI S4T TRASPASOS: error descargando %s: %s', tipo, e)
        self.conciliar()                    # v1.1: una vez al dia
        # v1.1: tambien los que dieron error, hasta MAX_INTENTOS veces
        pendientes = self.search(['|', ('state', '=', 'nuevo'),
                                  '&', ('state', '=', 'error'), ('intentos', '<', MAX_INTENTOS)])
        hechos = pendientes.action_procesar()
        self.env.cr.commit()
        _logger.info('KOROSHI S4T TRASPASOS: %d procesados de %d nuevos o con error', hechos, len(pendientes))
        return True


class KoroshiS4tTraspasoLinea(models.Model):
    _name = 'koroshi.s4t.traspaso.linea'
    _description = 'Linea de traspaso S4T'
    _order = 'traspaso_id, line_number, id'

    traspaso_id = fields.Many2one('koroshi.s4t.traspaso', required=True, ondelete='cascade', index=True)
    line_number = fields.Char(string='Linea')
    article_id = fields.Char(string='Articulo')
    color_id = fields.Char(string='Color')
    size = fields.Char(string='Talla')
    quantity = fields.Float(string='Unidades')
    boxes = fields.Float(string='Cajas (por linea, no sumar)')
    sku = fields.Char(string='SKU', compute='_compute_producto', store=True)
    product_id = fields.Many2one('product.product', string='Producto', compute='_compute_producto', store=True)

    @api.depends('article_id', 'color_id', 'size')
    def _compute_producto(self):
        Producto = self.env['product.product'].sudo()
        for l in self:
            l.sku = '-'.join([(l.article_id or '').strip(), (l.color_id or '').strip(), (l.size or '').strip()])
            l.product_id = Producto.search([('style_code', '=', l.sku)], limit=1) if l.article_id else False
