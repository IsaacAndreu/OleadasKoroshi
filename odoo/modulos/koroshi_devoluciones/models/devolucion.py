# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Devoluciones - «Ubicar devoluciones» (fase 1)                    v1.0 20/11/2026
#
# Sustituye el Excel de devoluciones (EAN + contenedor, que después se subía a Odoo). El operario elige qué
# manipulación ha hecho, lee prenda, prenda… y el contenedor (KO_/TT_) o el hueco. Cada tanda queda apuntada
# (quién, cuándo, qué opción, artículo y uds) y, con el parámetro koroshi_devoluciones.stock = 'mover' (por defecto),
# el stock pasa al contenedor:
#   1. primero lo que haya LIBRE de ese artículo en la ubicación de devoluciones (la de destino del tipo DEV de la
#      compañía 8, DEVOLUCIO_KOROSHI, o la del parámetro koroshi_devoluciones.origen_id): movimiento interno;
#   2. lo que falte entra como ajuste de inventario (desde pérdidas de inventario, como «Añadir prendas» de
#      Contenedores y como hacía la subida del Excel).
# Con koroshi_devoluciones.stock = 'apuntar' solo se apunta, sin mover nada.
# Solo escribe en sus tablas y crea stock.move hechos (sin albarán). Sin campos en tablas de Odoo.
# =============================================================================
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_round
from odoo.addons.koroshi_base import comun

_logger = logging.getLogger(__name__)

COMPANY_ID = comun.COMPANY_ID
P = 'koroshi_devoluciones.'
PARAM_STOCK = P + 'stock'          # 'mover' (por defecto) o 'apuntar'
PARAM_ORIGEN = P + 'origen_id'     # id de la ubicación de devoluciones (si no, la de destino del tipo DEV)
PREFIJOS = ('KO_', 'TT_')


def es_contenedor(nombre):
    return (nombre or '').upper()[:3] in PREFIJOS


class KoroshiDevolucionManipulacion(models.Model):
    _name = 'koroshi.devolucion.manipulacion'
    _description = 'KOROSHI: opción de manipulación de devoluciones'
    _order = 'sequence, id'

    name = fields.Char('Opción (lo que ve el operario)', required=True, translate=False)
    codigo_factura = fields.Char('Código de factura', help='M1, M2, M3… Solo sale en el informe, no en la PDA.')
    sequence = fields.Integer('Orden', default=10)
    color = fields.Char('Color del botón', default='#0b4f9c', help='Color en hexadecimal (#0b4f9c).')
    active = fields.Boolean('Activa', default=True)


class KoroshiDevolucionUbicada(models.Model):
    _name = 'koroshi.devolucion.ubicada'
    _description = 'KOROSHI: prenda de devolución ubicada (una línea por artículo y tanda)'
    _order = 'fecha desc, id desc'
    _rec_name = 'tanda'

    tanda = fields.Char('Tanda', required=True, index=True, readonly=True,
                        help='Las prendas que se guardaron juntas al leer el contenedor o la ubicación.')
    fecha = fields.Datetime('Cuándo', required=True, default=fields.Datetime.now, readonly=True, index=True)
    dia = fields.Date('Día', required=True, readonly=True, index=True,
                      help='Día en la hora del almacén (para agrupar por día, semana o mes).')
    employee_id = fields.Many2one('hr.employee', 'Operario', readonly=True, index=True, ondelete='restrict')
    user_id = fields.Many2one('res.users', 'Usuario de Odoo', readonly=True, default=lambda s: s.env.uid)
    manipulacion_id = fields.Many2one('koroshi.devolucion.manipulacion', 'Manipulación', required=True,
                                      readonly=True, index=True, ondelete='restrict')
    codigo_factura = fields.Char('Código de factura', related='manipulacion_id.codigo_factura', store=True,
                                 readonly=True)
    product_id = fields.Many2one('product.product', 'Artículo', required=True, readonly=True, index=True,
                                 ondelete='restrict')
    uds = fields.Integer('Uds', required=True, readonly=True)
    ubicacion_id = fields.Many2one('stock.location', 'Contenedor o ubicación', required=True, readonly=True,
                                   index=True, ondelete='restrict')
    ubicacion = fields.Char('Contenedor o ubicación (leído)', readonly=True)
    stock = fields.Selection([('mover', 'Movido'), ('apuntar', 'Solo apuntado')], 'Stock', readonly=True,
                             default='apuntar')
    uds_devoluciones = fields.Integer('Uds desde devoluciones', readonly=True,
                                      help='Uds que estaban libres en la ubicación de devoluciones y se han movido.')
    uds_nuevas = fields.Integer('Uds nuevas (ajuste)', readonly=True,
                                help='Uds que no estaban en Odoo y han entrado con un ajuste de inventario.')
    move_ids = fields.Many2many('stock.move', 'koroshi_devolucion_ubicada_move_rel', 'ubicada_id', 'move_id',
                                'Movimientos de stock', readonly=True)
    estado = fields.Selection([('hecha', 'Hecha'), ('anulada', 'Anulada')], 'Estado', default='hecha',
                              required=True, readonly=True, index=True)
    anulada_por = fields.Many2one('res.users', 'Anulada por', readonly=True)
    anulada_el = fields.Datetime('Anulada el', readonly=True)

    # ------------------------------------------------------------------ configuración
    @api.model
    def _modo_stock(self):
        """'apuntar' solo si el parámetro lo dice exactamente; si no, 'mover' (lo que hacía la subida del Excel)."""
        valor = (self.env['ir.config_parameter'].sudo().get_param(PARAM_STOCK) or '').strip().lower()
        return 'apuntar' if valor == 'apuntar' else 'mover'

    @api.model
    def _ubicacion_devoluciones(self):
        """Ubicación de donde se coge primero el stock: la del parámetro o la de destino del tipo DEV (compañía 8),
        la misma que usa koroshi_s4t_traspasos para las devoluciones web. Puede no haber: entonces todo es ajuste."""
        Loc = self.env['stock.location'].sudo()
        valor = (self.env['ir.config_parameter'].sudo().get_param(PARAM_ORIGEN) or '').strip()
        if valor.isdigit():
            loc = Loc.browse(int(valor)).exists()
            if loc:
                return loc
        tipo = self.env['stock.picking.type'].sudo().search([
            ('company_id', '=', COMPANY_ID), ('code', '=', 'incoming'), ('sequence_code', '=', 'DEV'),
        ], limit=1)
        return tipo.default_location_dest_id

    # ------------------------------------------------------------------ stock
    @api.model
    def _mover(self, producto, uds, origen, destino, nombre, quants=None):
        """Movimiento hecho de uds de origen a destino (sin albarán), como Contenedores y Faltantes. Si se pasan
        quants, cada línea sale de la sububicación (y paquete y propietario) de su quant."""
        company = self.env['res.company'].sudo().browse(COMPANY_ID)
        uom = producto.uom_id
        if quants:
            lineas = []
            resto = uds
            for q, n in quants:
                if resto <= 0:
                    break
                n = min(n, resto)
                lineas.append((0, 0, {
                    'product_id': producto.id, 'product_uom_id': uom.id, 'qty_done': n,
                    'location_id': q.location_id.id, 'location_dest_id': destino.id,
                    'package_id': q.package_id.id or False, 'owner_id': q.owner_id.id or False,
                    'company_id': company.id,
                }))
                resto -= n
        else:
            lineas = [(0, 0, {
                'product_id': producto.id, 'product_uom_id': uom.id, 'qty_done': uds,
                'location_id': origen.id, 'location_dest_id': destino.id, 'company_id': company.id,
            })]
        move = self.env['stock.move'].sudo().create({
            'name': nombre, 'origin': nombre, 'product_id': producto.id, 'product_uom': uom.id,
            'product_uom_qty': uds, 'location_id': origen.id, 'location_dest_id': destino.id,
            'company_id': company.id, 'move_line_ids': lineas,
        })
        move._action_done()
        if move.state != 'done':
            raise UserError(_('No se ha podido mover %s a %s.') % (producto.display_name, destino.display_name))
        return move

    @api.model
    def _libres(self, producto, ubicacion):
        """[(quant, uds libres)] de un artículo en una ubicación y sus hijas (cantidad menos reservada, > 0)."""
        quants = self.env['stock.quant'].sudo().search([
            ('product_id', '=', producto.id), ('location_id', 'child_of', ubicacion.id),
            ('company_id', '=', COMPANY_ID), ('quantity', '>', 0)])
        res = []
        for q in quants:
            libre = int(float_round(q.quantity - q.reserved_quantity, precision_digits=0, rounding_method='DOWN'))
            if libre > 0:
                res.append((q, libre))
        return res

    @api.model
    def _entrar_en(self, producto, uds, destino, nombre):
        """Pone uds del artículo en el destino. Devuelve (moves, uds desde devoluciones, uds nuevas)."""
        if producto.tracking and producto.tracking != 'none':
            raise UserError(_('%s va por lote o número de serie: no se puede ubicar aquí. Avisa a IT.')
                            % producto.display_name)
        moves = self.env['stock.move']
        origen = self._ubicacion_devoluciones()
        de_dev = 0
        if origen and origen != destino:
            libres = self._libres(producto, origen)
            de_dev = min(uds, sum(n for q, n in libres))
            if de_dev:
                moves |= self._mover(producto, de_dev, origen, destino, nombre, quants=libres)
        nuevas = uds - de_dev
        if nuevas:
            perdidas = producto.with_context(force_company=COMPANY_ID).property_stock_inventory
            if not perdidas:
                raise UserError(_('El artículo %s no tiene ubicación de pérdidas de inventario. Avisa a IT.')
                                % producto.display_name)
            moves |= self._mover(producto, nuevas, perdidas, destino, nombre)
        return moves, de_dev, nuevas

    # ------------------------------------------------------------------ guardar una tanda (desde la PDA)
    @api.model
    def guardar_tanda(self, tanda, employee, manipulacion, destino, lineas):
        """lineas = {product.product: uds}. Todo o nada (savepoint). Si la tanda ya existe (la PDA reintenta tras
        cortarse la wifi), no se repite: devuelve lo que ya había."""
        ya = self.sudo().search([('tanda', '=', tanda)])
        if ya:
            return ya, True
        modo = self._modo_stock()
        nombre = 'KOROSHI devoluciones %s: %s en %s (%s)' % (tanda, manipulacion.name, destino.name, employee.name)
        hechas = self.sudo()
        with self.env.cr.savepoint():
            for producto, uds in lineas.items():
                vals = {
                    'tanda': tanda, 'dia': comun.hoy_local(), 'employee_id': employee.id,
                    'manipulacion_id': manipulacion.id, 'product_id': producto.id, 'uds': uds,
                    'ubicacion_id': destino.id, 'ubicacion': destino.name, 'stock': modo,
                }
                if modo == 'mover':
                    moves, de_dev, nuevas = self._entrar_en(producto, uds, destino, nombre)
                    vals.update({'uds_devoluciones': de_dev, 'uds_nuevas': nuevas, 'move_ids': [(6, 0, moves.ids)]})
                hechas |= self.sudo().create(vals)
        return hechas, False

    # ------------------------------------------------------------------ anular (jefes)
    def action_anular(self):
        """Anula las tandas de las líneas marcadas (la tanda entera). Si se movió stock, lo devuelve a donde estaba
        (devoluciones o pérdidas de inventario), solo si sigue libre en el contenedor; si no, no anula nada."""
        if not self.env.user.has_group('stock.group_stock_manager'):
            raise UserError(_('Solo un responsable de inventario puede anular tandas.'))
        lineas = self.sudo().search([('tanda', 'in', self.mapped('tanda')), ('estado', '=', 'hecha')])
        with self.env.cr.savepoint():
            for l in lineas:
                for m in l.move_ids.filtered(lambda m: m.state == 'done'):
                    uds = int(m.quantity_done)
                    libres = self._libres(m.product_id, m.location_dest_id)
                    libres = [(q, n) for q, n in libres if q.location_id == m.location_dest_id]
                    if sum(n for q, n in libres) < uds:
                        raise UserError(_('No se puede anular la tanda %s: %s ya no está (libre) en %s.')
                                        % (l.tanda, m.product_id.display_name, m.location_dest_id.name))
                    self._mover(m.product_id, uds, m.location_dest_id, m.location_id,
                                'KOROSHI devoluciones %s: anulada por %s' % (l.tanda, self.env.user.name),
                                quants=libres)
            lineas.write({'estado': 'anulada', 'anulada_por': self.env.uid, 'anulada_el': fields.Datetime.now()})
        return True
