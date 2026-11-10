# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Preparación en Lecturas (v3.0.0) - lógica del servidor.
#
# La app de código de barras (stock_barcode + stock_barcode_optimization de Brain Station) solo hace en el servidor:
#   1) guardar qty_done de las move.line,
#   2) put_in_pack(package_name=<CJ>) en el diálogo «Nombre del Paquete»,
#   3) button_validate.
# Esta pantalla hace exactamente lo mismo, una lectura cada vez, y apunta cada lectura en koroshi.preparacion.lectura.
# Sin campos nuevos en las tablas de stock. Nunca escribe stock.quant ni fuerza disponibilidad.
# =============================================================================
import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero

_logger = logging.getLogger(__name__)

COMPANY_ID = 8                      # EFFECTIVE LOGISTICS, S.L.
RE_CJ = re.compile(r'^CJ\d{9}$')    # matrícula de caja (igual que koroshi_caja_existente)
PREFIJOS_ZONA = ('Z-',)             # agrupaciones de zona: se preparan en la app de siempre
PARAM_ACTIVA = 'koroshi_preparacion.activa'
PARAM_EMPLEADOS = 'koroshi_preparacion.empleados'


class Lectura(models.Model):
    _name = 'koroshi.preparacion.lectura'
    _description = 'KOROSHI Preparación: lectura en la PDA'
    _order = 'id desc'

    fecha = fields.Datetime('Fecha', required=True, default=fields.Datetime.now, index=True)
    picking_id = fields.Many2one('stock.picking', 'OUT', index=True, ondelete='cascade')
    move_line_id = fields.Many2one('stock.move.line', 'Línea', ondelete='set null')
    employee_id = fields.Many2one('hr.employee', 'Operario', index=True, ondelete='set null')
    user_id = fields.Many2one('res.users', 'Usuario', default=lambda s: s.env.uid)
    tipo = fields.Selection([('leer', 'Leer'), ('deshacer', 'Deshacer'), ('caja', 'Caja'), ('validar', 'Validar')],
                            'Tipo', required=True)
    codigo = fields.Char('Código leído')
    producto = fields.Char('Producto')
    cantidad = fields.Float('Cantidad', digits=(16, 0))
    resultado = fields.Selection([('ok', 'Bien'), ('error', 'Error')], 'Resultado', required=True, default='ok')
    mensaje = fields.Char('Mensaje')
    id_lectura = fields.Char('Id de la lectura', index=True, help='La pone la PDA: si reintenta, no cuenta dos veces')
    deshecha = fields.Boolean('Deshecha')

    # ------------------------------------------------------------------ parámetros
    @api.model
    def _param(self, clave, defecto=''):
        return self.env['ir.config_parameter'].sudo().get_param(clave, defecto) or defecto

    @api.model
    def empleado_activo(self, employee):
        """La pantalla nueva se usa si el módulo está activo y el operario está en la lista (o la lista es '*')."""
        if not employee or self._param(PARAM_ACTIVA, '1') in ('0', 'False', 'false', ''):
            return False
        lista = [x.strip().upper() for x in re.split(r'[,;\s]+', self._param(PARAM_EMPLEADOS, '')) if x.strip()]
        if '*' in lista:
            return True
        return (employee.barcode or '').upper() in lista or str(employee.id) in lista

    @api.model
    def picking_propio(self, picking):
        """OUT que se puede preparar aquí: salida de la company 8, sin agrupación de zona, ni hecha ni cancelada."""
        if not picking or picking.picking_type_code != 'outgoing' or picking.company_id.id != COMPANY_ID:
            return False
        if picking.state in ('done', 'cancel', 'draft'):
            return False
        if picking.batch_id and (picking.batch_id.name or '').startswith(PREFIJOS_ZONA):
            return False
        return True

    # ------------------------------------------------------------------ estado de la OUT
    @api.model
    def _lineas(self, picking):
        return picking.move_line_ids.sorted(
            lambda l: (l.location_id.complete_name or '', l.product_id.default_code or '', l.id))

    @api.model
    def _sin_caja(self, picking):
        return picking.move_line_ids.filtered(
            lambda l: not l.result_package_id and float_compare(l.qty_done, 0, precision_digits=3) > 0)

    @api.model
    def estado(self, picking):
        lineas = []
        siguiente = False
        for ml in self._lineas(picking):
            pedidas = ml.product_uom_qty
            leidas = ml.qty_done
            completa = float_compare(leidas, pedidas, precision_digits=3) >= 0 and not float_is_zero(
                pedidas + leidas, precision_digits=3)
            lineas.append({
                'id': ml.id,
                'producto_id': ml.product_id.id,     # v3.0.1: foto /web/image/product.product/<id>/image_256
                'producto': ml.product_id.display_name or '',
                'ref': ml.product_id.default_code or '',
                'ean': ml.product_id.barcode or '',
                'ubicacion': ml.location_id.name or '',
                'ubicacion_completa': ml.location_id.complete_name or '',
                'pedidas': round(pedidas),
                'leidas': round(leidas),
                'caja': ml.result_package_id.name or '',
                'completa': completa,
            })
            if not siguiente and not completa and not ml.result_package_id:
                siguiente = ml.id
        cajas = {}
        for ml in picking.move_line_ids.filtered('result_package_id'):
            cajas.setdefault(ml.result_package_id.name, 0)
            cajas[ml.result_package_id.name] += ml.qty_done
        sin_caja = sum(self._sin_caja(picking).mapped('qty_done'))
        pedidas = sum(picking.move_line_ids.mapped('product_uom_qty'))
        leidas = sum(picking.move_line_ids.mapped('qty_done'))
        zona = ''
        if picking.batch_id and not (picking.batch_id.name or '').startswith(PREFIJOS_ZONA):
            zona = picking.batch_id.name or ''
        return {
            'out': {
                'id': picking.id,
                'name': picking.name,
                'tienda': picking.partner_id.name or '',
                'origen': picking.origin or '',
                'estado': picking.state,
                'agrupacion': zona,
                'propia': self.picking_propio(picking),
            },
            'lineas': lineas,
            'siguiente_id': siguiente,
            'sin_caja': round(sin_caja),
            'cajas': [{'nombre': k, 'uds': round(v)} for k, v in sorted(cajas.items())],
            'pedidas': round(pedidas),
            'leidas': round(leidas),
            'todo_leido': bool(lineas) and all(l['completa'] for l in lineas),
        }

    # ------------------------------------------------------------------ ayudas
    @api.model
    def _bloquear(self, picking):
        """Una sola PDA escribe a la vez en la misma OUT."""
        try:
            self.env.cr.execute('SELECT id FROM stock_picking WHERE id = %s FOR UPDATE NOWAIT', (picking.id,))
        except Exception:
            raise UserError(_('Otra PDA está guardando en %s. Vuelve a leer en un segundo.') % picking.name)

    @api.model
    def _variantes(self, codigo):
        """El código tal cual y la conversión UPC (12) <-> EAN-13 con 0 delante (nomenclatura upc_ean_conv)."""
        res = [codigo]
        if codigo.isdigit() and len(codigo) == 12:
            res.append('0' + codigo)
        if codigo.isdigit() and len(codigo) == 13 and codigo.startswith('0'):
            res.append(codigo[1:])
        return res

    @api.model
    def _producto_de(self, picking, codigo):
        """Producto de la OUT con ese código: EAN principal, códigos alternativos (product_multi_barcode) o
        referencia interna. Devuelve (producto, en_la_out)."""
        variantes = self._variantes(codigo)
        productos = picking.move_line_ids.mapped('product_id')
        for p in productos:
            if p.barcode and p.barcode in variantes:
                return p, True
        if 'product.barcode' in self.env:
            alt = self.env['product.barcode'].sudo().search(
                [('name', 'in', variantes), ('product_id', 'in', productos.ids)], limit=1)
            if alt:
                return alt.product_id, True
        for p in productos:
            if p.default_code and p.default_code == codigo:
                return p, True
        # no es de la OUT: ¿es un producto?
        otro = self.env['product.product'].sudo().search([('barcode', 'in', variantes)], limit=1)
        if not otro and 'product.barcode' in self.env:
            alt = self.env['product.barcode'].sudo().search([('name', 'in', variantes)], limit=1)
            otro = alt.product_id
        return otro, False

    @api.model
    def _apuntar(self, picking, employee, tipo, codigo, resultado='ok', mensaje='', ml=None, cantidad=0,
                 id_lectura=False, producto=''):
        return self.sudo().create({
            'picking_id': picking.id if picking else False,
            'move_line_id': ml.id if ml else False,
            'employee_id': employee.id if employee else False,
            'tipo': tipo,
            'codigo': codigo,
            'producto': producto or (ml.product_id.display_name if ml else ''),
            'cantidad': cantidad,
            'resultado': resultado,
            'mensaje': (mensaje or '')[:250],
            'id_lectura': id_lectura or False,
        })

    @api.model
    def _repetida(self, id_lectura):
        if not id_lectura:
            return False
        return self.sudo().search([('id_lectura', '=', id_lectura)], limit=1)

    @api.model
    def _comprobar(self, picking):
        if not picking:
            raise UserError(_('No se encuentra la OUT.'))
        if picking.state == 'done':
            raise UserError(_('%s ya está validada.') % picking.name)
        if picking.state == 'cancel':
            raise UserError(_('%s está cancelada.') % picking.name)
        if not self.picking_propio(picking):
            raise UserError(_('%s no se prepara aquí: ábrela en la app de código de barras.') % picking.name)

    # ------------------------------------------------------------------ leer un producto
    @api.model
    def leer(self, picking, employee, codigo, id_lectura=False):
        """Suma 1 ud a la línea del producto leído. Devuelve {'ok', 'msg', 'linea_id', 'que'}."""
        codigo = (codigo or '').strip()
        previa = self._repetida(id_lectura)
        if previa:
            return {'ok': previa.resultado == 'ok', 'msg': previa.mensaje, 'linea_id': previa.move_line_id.id,
                    'que': 'repetida'}
        self._comprobar(picking)
        if RE_CJ.match(codigo):
            return {'ok': False, 'que': 'es_caja', 'msg': _('Es una caja: pulsa «Caja» antes de leerla.')}
        tarjeta = self.env['hr.employee'].sudo().search([('barcode', '=', codigo)], limit=1)
        if tarjeta:
            return {'ok': False, 'que': 'es_tarjeta',
                    'msg': _('Es la tarjeta de %s. Para cambiar de operario vuelve a Lecturas (←).') % tarjeta.name}
        producto, en_la_out = self._producto_de(picking, codigo)
        if not producto:
            msg = _('Código %s desconocido. No cuenta.') % codigo
            self._apuntar(picking, employee, 'leer', codigo, 'error', msg, id_lectura=id_lectura)
            return {'ok': False, 'que': 'desconocido', 'msg': msg}
        if not en_la_out:
            msg = _('%s no es de este pedido. No cuenta.') % producto.display_name
            self._apuntar(picking, employee, 'leer', codigo, 'error', msg, id_lectura=id_lectura,
                          producto=producto.display_name)
            return {'ok': False, 'que': 'no_es_del_pedido', 'msg': msg}
        self._bloquear(picking)
        lineas = self._lineas(picking).filtered(
            lambda l: l.product_id == producto and not l.result_package_id
            and float_compare(l.qty_done, l.product_uom_qty, precision_digits=3) < 0)
        if not lineas:
            total = sum(picking.move_line_ids.filtered(lambda l: l.product_id == producto).mapped('product_uom_qty'))
            msg = _('Ya tienes todas las uds de %s (%s). No cuenta.') % (producto.display_name, round(total))
            self._apuntar(picking, employee, 'leer', codigo, 'error', msg, id_lectura=id_lectura,
                          producto=producto.display_name)
            return {'ok': False, 'que': 'completo', 'msg': msg}
        ml = lineas[0]
        primera = float_is_zero(sum(picking.move_line_ids.mapped('qty_done')), precision_digits=3)
        ml.write({'qty_done': ml.qty_done + 1})
        if primera and hasattr(picking, 'set_barcode_start_date'):
            # lo mismo que la app de Brain Station al primer producto (fecha de inicio de la preparación)
            try:
                with self.env.cr.savepoint():
                    picking.set_barcode_start_date()
            except Exception as e:  # solo informativo
                _logger.info('KOROSHI preparacion: set_barcode_start_date %s: %s', picking.name, e)
        hechas = sum(picking.move_line_ids.filtered(lambda l: l.product_id == producto).mapped('qty_done'))
        total = sum(picking.move_line_ids.filtered(lambda l: l.product_id == producto).mapped('product_uom_qty'))
        msg = '%s  %s de %s' % (producto.default_code or producto.display_name, round(hechas), round(total))
        self._apuntar(picking, employee, 'leer', codigo, 'ok', msg, ml=ml, cantidad=1, id_lectura=id_lectura)
        return {'ok': True, 'que': 'producto', 'msg': msg, 'linea_id': ml.id}

    # ------------------------------------------------------------------ deshacer la última
    @api.model
    def deshacer(self, picking, employee):
        self._comprobar(picking)
        self._bloquear(picking)
        dominio = [('picking_id', '=', picking.id), ('tipo', '=', 'leer'), ('resultado', '=', 'ok'),
                   ('deshecha', '=', False)]
        if employee:
            dominio.append(('employee_id', '=', employee.id))
        ultima = self.sudo().search(dominio, limit=1)
        if not ultima or not ultima.move_line_id:
            return {'ok': False, 'msg': _('No hay ninguna lectura tuya que deshacer en %s.') % picking.name}
        ml = ultima.move_line_id
        if ml.result_package_id:
            return {'ok': False, 'msg': _('%s ya está en la caja %s: no se puede deshacer.')
                    % (ml.product_id.default_code or ml.product_id.display_name, ml.result_package_id.name)}
        if float_compare(ml.qty_done, 1, precision_digits=3) < 0:
            ultima.deshecha = True
            return {'ok': False, 'msg': _('Esa línea ya no tiene uds leídas.')}
        ml.write({'qty_done': ml.qty_done - 1})
        ultima.deshecha = True
        msg = _('Deshecha: %s (−1)') % (ml.product_id.default_code or ml.product_id.display_name)
        self._apuntar(picking, employee, 'deshacer', ultima.codigo, 'ok', msg, ml=ml, cantidad=-1)
        return {'ok': True, 'msg': msg, 'linea_id': ml.id}

    # ------------------------------------------------------------------ cerrar caja
    @api.model
    def caja(self, picking, employee, codigo, id_lectura=False):
        codigo = (codigo or '').strip().upper()
        previa = self._repetida(id_lectura)
        if previa:
            return {'ok': previa.resultado == 'ok', 'msg': previa.mensaje, 'que': 'repetida'}
        self._comprobar(picking)
        if not RE_CJ.match(codigo):
            return {'ok': False, 'msg': _('%s no es una etiqueta de caja (CJ + 9 cifras). Lee la etiqueta de la caja.')
                    % codigo}
        self._bloquear(picking)
        sin_caja = self._sin_caja(picking)
        if not sin_caja:
            return {'ok': False, 'msg': _('No hay nada leído fuera de caja: lee algún artículo antes de cerrar la caja.')}
        uds = sum(sin_caja.mapped('qty_done'))
        try:
            with self.env.cr.savepoint():
                # igual que el diálogo «Nombre del Paquete» de la app (Brain Station + koroshi_caja_existente)
                res = picking.put_in_pack(package_name=codigo)
                if isinstance(res, dict) and res.get('res_model'):
                    raise UserError(_('Odoo pide otra cosa al cerrar la caja (%s). Ciérrala en la app de código de '
                                      'barras.') % (res.get('name') or res.get('res_model')))
        except (UserError, ValidationError) as e:
            msg = e.name if hasattr(e, 'name') else str(e)
            self._apuntar(picking, employee, 'caja', codigo, 'error', msg, id_lectura=id_lectura)
            return {'ok': False, 'msg': msg}
        msg = _('Caja %s cerrada con %s uds.') % (codigo, round(uds))
        self._apuntar(picking, employee, 'caja', codigo, 'ok', msg, cantidad=uds, id_lectura=id_lectura)
        return {'ok': True, 'msg': msg}

    # ------------------------------------------------------------------ validar
    @api.model
    def validar(self, picking, employee, pedido_pendiente=None):
        """Misma validación que koroshi_faltantes (button_validate, todo o nada). Devuelve
        {'ok', 'que': 'validada' | 'quedan' | 'preguntar' | 'sin_caja' | 'no_validada', 'msg'}."""
        self._comprobar(picking)
        sin_caja = sum(self._sin_caja(picking).mapped('qty_done'))
        if float_compare(sin_caja, 0, precision_digits=3) > 0:
            return {'ok': False, 'que': 'sin_caja',
                    'msg': _('Hay %s uds sin caja: pulsa «Caja» y lee la etiqueta antes de validar.') % round(sin_caja)}
        if pedido_pendiente not in ('si', 'no'):
            fijo = self._param('koroshi_faltantes.pedido_pendiente', 'no')
            pedido_pendiente = fijo if fijo in ('si', 'no') else None
        Faltante = self.env['koroshi.faltante']
        try:
            r = Faltante.validar_out(picking, pedido_pendiente)
        except (UserError, ValidationError) as e:
            msg = e.name if hasattr(e, 'name') else str(e)
            self._apuntar(picking, employee, 'validar', picking.name, 'error', msg)
            return {'ok': False, 'que': 'no_validada', 'msg': msg}
        if r['estado'] == 'pendientes':
            return {'ok': False, 'que': 'quedan', 'n': r['n'],
                    'msg': _('Quedan %s líneas por coger: léelas o pulsa «Faltante».') % r['n']}
        if r['estado'] == 'preguntar':
            return {'ok': True, 'que': 'preguntar', 'msg': _('Faltan uds. ¿Crear un pedido pendiente con lo que falta?')}
        msg = _('%s validada.') % picking.name
        self._apuntar(picking, employee, 'validar', picking.name, 'ok', msg)
        try:
            # cierra ya la tarea del operario (lo mismo que hace koroshi_faltantes al validar)
            with self.env.cr.savepoint():
                self.env['koroshi.operario.tarea'].sudo().cron_cerrar()
        except Exception:
            pass
        return {'ok': True, 'que': 'validada', 'msg': msg}
