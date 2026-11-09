# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Faltantes - datos de la pantalla "Faltante" de la PDA (accion de cliente
# koroshi_faltantes_pantalla, static/src/js/faltantes_pantalla.js). Usuario con sesion (p. ej. "Almacen Nath").
#
# JSON /koroshi/faltantes/buscar           {codigo, out_id, move_line_id}   -> tarjeta, OUT, lineas o linea
# JSON /koroshi/faltantes/reubicar         {move_line_id, codigo, employee_id} -> cambia la reserva + FALTANT
# JSON /koroshi/faltantes/sin_alternativa  {move_line_id, employee_id}      -> quita la reserva + FALTANT
# JSON /koroshi/faltantes/pendientes       {out_id | lote_id}               -> v1.3: lo que queda por coger
# JSON /koroshi/faltantes/validar          {out_id, pedido_pendiente}       -> v1.3: valida la OUT (button_validate)
#
# v1.3: al leer la OUT sale la lista de lo que queda por coger (sin leer el EAN). Leer una ubicacion elige la
# linea pendiente de esa ubicacion. Despues de cada faltante, si no queda nada por coger, se valida.
#
# Lee y escribe con el usuario de la sesion (derechos normales de almacen). La tarjeta del operario se busca
# con sudo en todas las empresas, como en koroshi_operarios.
# =============================================================================
from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

from ..models.faltante import PREFIJOS_ZONA, nombre_corto


def _msg(e):
    return e.name if hasattr(e, 'name') else str(e)


def _out_json(picking):
    batch = picking.batch_id
    zona = bool(batch and (batch.name or '').startswith(PREFIJOS_ZONA))
    return {
        'id': picking.id,
        'name': picking.name,
        'tienda': picking.partner_id.name or '',
        'batch_id': batch.id if zona else False,
        'batch_name': batch.name if zona else '',
    }


def _linea_json(ml, Faltante, con_alternativas=False):
    res = {
        'id': ml.id,
        'producto': ml.product_id.display_name,
        'ean': ml.product_id.barcode or '',
        'cantidad': ml.product_uom_qty,
        'leidas': ml.qty_done,
        'pendiente': Faltante.pendiente_de(ml),
        'ref': ml.product_id.default_code or '',
        'variante': _variante(ml.product_id),
        'ubicacion': nombre_corto(ml.location_id),
        'ubicacion_completa': ml.location_id.complete_name,
        'motivo': Faltante.comprobar_linea(ml),
    }
    if con_alternativas and not res['motivo']:
        raiz = Faltante._raiz_stock(ml.picking_id)
        alt = Faltante.alternativas(ml.product_id, ml.location_id, raiz)
        res['alternativas'] = alt['lista']
        res['alternativas_total'] = alt['total']
    return res


def _variante(product):
    """'Azul / M' con los valores de atributos (color, talla) del articulo."""
    return ' / '.join(product.product_template_attribute_value_ids.mapped('name'))


def _pendiente_json(ml, Faltante):
    """v1.3: una linea de la lista "Que falta" (lo que queda por coger de la OUT)."""
    return {
        'id': ml.id,
        'ref': ml.product_id.default_code or ml.product_id.barcode or '',
        'producto': ml.product_id.name or '',
        'variante': _variante(ml.product_id),
        'ean': ml.product_id.barcode or '',
        'ubicacion': nombre_corto(ml.location_id),
        'pendiente': Faltante.pendiente_de(ml),
        'leidas': ml.qty_done,
        'out': ml.picking_id.name,
        'tienda': ml.picking_id.partner_id.name or '',
        'motivo': Faltante.comprobar_linea(ml),
    }


def _pendientes(pickings, Faltante):
    return [_pendiente_json(ml, Faltante) for ml in Faltante.lineas_pendientes(pickings)]


def _lote_json(lote):
    """v1.3: una agrupacion de zonas leida en la pantalla (va en el sitio de la OUT)."""
    return {
        'id': False,
        'lote_id': lote.id,
        'name': lote.name,
        'tienda': '',
        'batch_id': lote.id,
        'batch_name': lote.name,
    }


def _empleado_json(emp):
    return {'id': emp.id, 'nombre': emp.name} if emp else False


class KoroshiFaltantes(http.Controller):

    # ------------------------------------------------------------------ ayudas
    def _tarjeta(self, codigo):
        return request.env['hr.employee'].sudo().search([('barcode', '=', codigo)], limit=1)

    def _operario(self, employee_id, picking=None):
        """El de la tarjeta leida o, si no hay, el de la tarea abierta de esa OUT o agrupacion."""
        emp = request.env['hr.employee'].sudo().browse(int(employee_id or 0)).exists()
        if emp or not picking:
            return emp
        Tarea = request.env['koroshi.operario.tarea'].sudo()
        dom = [('estado', '=', 'curso'), '|', ('picking_id', '=', picking.id)]
        dom += [('batch_id', '=', picking.batch_id.id)] if picking.batch_id else [('id', '=', 0)]
        return Tarea.search(dom, order='inicio desc', limit=1).employee_id

    def _picking(self, codigo):
        Picking = request.env['stock.picking']
        pk = Picking.search([('name', '=', codigo)], limit=1)
        if not pk and codigo.isdigit() and len(codigo) <= 6:     # solo el numero: 23649 -> EFFEC/OUT/23649
            pks = Picking.search([('name', '=like', '%/' + codigo)], limit=2)
            pk = pks if len(pks) == 1 else Picking
        return pk

    def _producto(self, codigo):
        Product = request.env['product.product']
        return (Product.search([('barcode', '=', codigo)], limit=1) or
                Product.search([('default_code', '=', codigo)], limit=1))

    def _ubicacion(self, codigo, company):
        Loc = request.env['stock.location']
        dom = [('company_id', 'in', [company.id, False])]
        return (Loc.search([('barcode', '=', codigo)] + dom, limit=1) or
                Loc.search([('name', '=', codigo), ('usage', '=', 'internal')] + dom, limit=1))

    def _linea(self, move_line_id):
        return request.env['stock.move.line'].browse(int(move_line_id or 0)).exists()

    def _lote(self, codigo):
        """v1.3: agrupacion de zonas (Z-...) por su nombre."""
        if not codigo.startswith(PREFIJOS_ZONA):
            return request.env['stock.picking.batch']
        return request.env['stock.picking.batch'].search([('name', '=', codigo)], limit=1)

    def _parametro(self, clave, defecto):
        return request.env['ir.config_parameter'].sudo().get_param(clave, defecto)

    def _validar_sola(self):
        return self._parametro('koroshi_faltantes.validar_sola', '1') not in ('0', 'False', 'false', '')

    def _respuesta_validar(self, picking, Faltante, pedido_pendiente=None):
        """Valida la OUT (v1.3). pedido_pendiente: None -> usa el parametro (preguntar / si / no)."""
        if pedido_pendiente is None:
            fijo = self._parametro('koroshi_faltantes.pedido_pendiente', 'preguntar')
            pedido_pendiente = fijo if fijo in ('si', 'no') else None
        try:
            r = Faltante.validar_out(picking, pedido_pendiente)
        except (UserError, ValidationError) as e:
            return {'ok': False, 'que': 'no_validada', 'msg': _msg(e), 'out': _out_json(picking)}
        if r['estado'] == 'pendientes':
            return {'ok': True, 'que': 'quedan', 'n': r['n'], 'out': _out_json(picking),
                    'msg': 'Quedan %d lineas por coger: vuelve a la OUT.' % r['n']}
        if r['estado'] == 'preguntar':
            return {'ok': True, 'que': 'preguntar', 'out': _out_json(picking)}
        self._cerrar_operarios()
        return {'ok': True, 'que': 'validada', 'out': _out_json(picking),
                'msg': 'OUT %s validada.' % picking.name}

    def _cerrar_operarios(self):
        """Tras validar: cierra ya la tarea y la asignacion del operario (lo mismo que el cron de Operarios)."""
        try:
            with request.env.cr.savepoint():
                request.env['koroshi.operario.tarea'].sudo().cron_cerrar()
        except Exception:      # no puede deshacer la validacion: lo hara el cron en 5 minutos
            pass

    def _tras_faltante(self, picking, Faltante, res):
        """v1.3: despues de reubicar o mandar a FALTANT, lo que queda por coger de la OUT y, si no queda
        nada y esta encendido, la validacion."""
        pendientes = _pendientes(picking, Faltante)
        res['pendientes'] = pendientes
        zona = bool(picking.batch_id and (picking.batch_id.name or '').startswith(PREFIJOS_ZONA))
        res['se_puede_validar'] = not pendientes and not zona
        res['validar_sola'] = self._validar_sola() and res['se_puede_validar']
        return res

    # ------------------------------------------------------------------ rutas
    @http.route('/koroshi/faltantes/buscar', type='json', auth='user')
    def buscar(self, codigo='', out_id=False, move_line_id=False, employee_id=False, **kw):
        Faltante = request.env['koroshi.faltante']
        codigo = (codigo or '').strip()
        try:
            # una linea concreta (cuando la OUT tiene varias del mismo articulo)
            if move_line_id and not codigo:
                ml = self._linea(move_line_id)
                if not ml:
                    return {'ok': False, 'msg': 'La linea ya no existe. Vuelve a leer la OUT.'}
                return {'ok': True, 'que': 'linea', 'out': _out_json(ml.picking_id),
                        'linea': _linea_json(ml, Faltante, con_alternativas=True)}
            if not codigo:
                return {'ok': False, 'msg': 'Codigo vacio'}

            emp = self._tarjeta(codigo)
            if emp:
                return {'ok': True, 'que': 'tarjeta', 'operario': _empleado_json(emp)}

            picking = self._picking(codigo)
            if picking:
                if picking.state in ('done', 'cancel'):
                    return {'ok': False, 'msg': 'La OUT %s ya esta %s.' % (
                        picking.name, 'validada' if picking.state == 'done' else 'cancelada')}
                # v1.3: con la OUT sale directamente la lista de lo que queda por coger
                return {'ok': True, 'que': 'out', 'out': _out_json(picking),
                        'operario': _empleado_json(self._operario(employee_id, picking)),
                        'pendientes': _pendientes(picking, Faltante)}

            lote = self._lote(codigo)
            if lote:
                # v1.3: agrupacion de zonas leida: lo que queda por coger de todas sus OUT
                pickings = lote.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
                if not pickings:
                    return {'ok': False, 'msg': 'La agrupacion %s no tiene OUT por hacer.' % lote.name}
                return {'ok': True, 'que': 'out', 'out': _lote_json(lote),
                        'operario': _empleado_json(self._operario(employee_id, pickings[0])),
                        'pendientes': _pendientes(pickings, Faltante)}

            picking = request.env['stock.picking'].browse(int(out_id or 0)).exists()
            lote = request.env['stock.picking.batch'].browse(int(kw.get('lote_id') or 0)).exists()
            if not picking and not lote:
                return {'ok': False, 'msg': 'No encuentro la OUT %s. Lee primero la OUT.' % codigo}
            pickings = lote.picking_ids if lote else picking

            # v1.3: la ubicacion donde esta el operario -> las lineas pendientes de esa ubicacion
            ubicacion = self._ubicacion(codigo, pickings[0].company_id)
            if ubicacion:
                lineas = Faltante.lineas_pendientes(pickings).filtered(
                    lambda l: l.location_id == ubicacion or l.location_id.parent_path.startswith(
                        ubicacion.parent_path or '-'))
                if not lineas:
                    return {'ok': False, 'msg': 'En %s no queda nada por coger de esta OUT.'
                                                % nombre_corto(ubicacion)}
                if len(lineas) == 1:
                    return {'ok': True, 'que': 'linea', 'out': _out_json(lineas.picking_id),
                            'linea': _linea_json(lineas, Faltante, con_alternativas=True)}
                return {'ok': True, 'que': 'filtro', 'ids': lineas.ids,
                        'msg': 'En %s quedan %d lineas: elige la que no esta.' % (nombre_corto(ubicacion),
                                                                                    len(lineas))}

            product = self._producto(codigo)
            if not product:
                return {'ok': False, 'msg': 'No encuentro el articulo ni la ubicacion %s.' % codigo}
            lineas = pickings.mapped('move_line_ids').filtered(
                lambda l: l.product_id == product and l.state not in ('done', 'cancel'))
            if not lineas:
                return {'ok': False, 'msg': 'El articulo %s no esta en %s.' % (
                    product.display_name, lote.name if lote else picking.name)}
            libres = lineas.filtered(lambda l: not Faltante.comprobar_linea(l))
            if len(libres) == 1:
                return {'ok': True, 'que': 'linea', 'out': _out_json(libres.picking_id),
                        'linea': _linea_json(libres, Faltante, con_alternativas=True)}
            if not libres:
                return {'ok': False, 'msg': Faltante.comprobar_linea(lineas[0])}
            # v1.3: varias lineas del mismo articulo: se filtran en la lista de pendientes
            return {'ok': True, 'que': 'filtro', 'ids': libres.ids,
                    'msg': 'Este articulo tiene %d lineas por coger: elige la que no esta.' % len(libres)}
        except (UserError, ValidationError) as e:
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/koroshi/faltantes/reubicar', type='json', auth='user')
    def reubicar(self, move_line_id=False, codigo='', employee_id=False, **kw):
        Faltante = request.env['koroshi.faltante']
        codigo = (codigo or '').strip()
        if not codigo:
            return {'ok': False, 'msg': 'Codigo vacio'}
        emp = self._tarjeta(codigo)
        if emp:
            return {'ok': True, 'que': 'tarjeta', 'operario': _empleado_json(emp)}
        ml = self._linea(move_line_id)
        if not ml:
            return {'ok': False, 'msg': 'La linea ya no existe. Vuelve a leer la OUT.'}
        ubicacion = self._ubicacion(codigo, ml.picking_id.company_id)
        if not ubicacion:
            return {'ok': False, 'msg': '%s no es una ubicacion. Lee la ubicacion de donde coges la pieza.'
                                        % codigo}
        picking = ml.picking_id
        try:
            f = Faltante.reubicar(ml, ubicacion, self._operario(employee_id, picking))
        except (UserError, ValidationError) as e:
            return {'ok': False, 'msg': _msg(e)}
        texto = 'Hecho: la linea pasa a %s. Ve a cogerla alli.' % nombre_corto(f.ubicacion_nueva_id)
        texto += ' %s ud a FALTANT.' % f.cantidad_faltant if f.cantidad_faltant else ''
        # v1.3: la pieza esta en la ubicacion nueva pero aun no se ha leido: la linea sigue pendiente
        return self._tras_faltante(picking, Faltante, {
            'ok': True, 'que': 'hecho', 'tipo': 'reubicado', 'msg': texto, 'nota': f.nota or '',
            'out': _out_json(picking), 'faltante_id': f.id, 'ubicacion_nueva': nombre_corto(f.ubicacion_nueva_id)})

    @http.route('/koroshi/faltantes/sin_alternativa', type='json', auth='user')
    def sin_alternativa(self, move_line_id=False, employee_id=False, **kw):
        Faltante = request.env['koroshi.faltante']
        ml = self._linea(move_line_id)
        if not ml:
            return {'ok': False, 'msg': 'La linea ya no existe. Vuelve a leer la OUT.'}
        picking = ml.picking_id
        try:
            f = Faltante.sin_alternativa(ml, self._operario(employee_id, picking))
        except (UserError, ValidationError) as e:
            return {'ok': False, 'msg': _msg(e)}
        texto = 'Hecho: la pieza va a faltantes; la OUT se valida sin ella.'
        texto += ' %s ud a FALTANT.' % f.cantidad_faltant if f.cantidad_faltant else ''
        return self._tras_faltante(picking, Faltante, {
            'ok': True, 'que': 'hecho', 'tipo': 'sin_alternativa', 'msg': texto, 'nota': f.nota or '',
            'out': _out_json(picking), 'faltante_id': f.id})

    @http.route('/koroshi/faltantes/pendientes', type='json', auth='user')
    def pendientes(self, out_id=False, lote_id=False, **kw):
        """v1.3: lo que queda por coger de la OUT (o de la agrupacion), para refrescar la lista."""
        Faltante = request.env['koroshi.faltante']
        lote = request.env['stock.picking.batch'].browse(int(lote_id or 0)).exists()
        picking = request.env['stock.picking'].browse(int(out_id or 0)).exists()
        if not lote and not picking:
            return {'ok': False, 'msg': 'Lee primero la OUT.'}
        pickings = lote.picking_ids if lote else picking
        return {'ok': True, 'que': 'lista', 'pendientes': _pendientes(pickings, Faltante)}

    @http.route('/koroshi/faltantes/validar', type='json', auth='user')
    def validar(self, out_id=False, pedido_pendiente=False, **kw):
        """v1.3: valida la OUT con la validacion normal de Odoo. pedido_pendiente: 'si' / 'no' (respuesta
        del operario) o vacio (usa el parametro koroshi_faltantes.pedido_pendiente; 'preguntar' de inicio)."""
        Faltante = request.env['koroshi.faltante']
        picking = request.env['stock.picking'].browse(int(out_id or 0)).exists()
        if not picking:
            return {'ok': False, 'msg': 'Lee primero la OUT.'}
        return self._respuesta_validar(picking, Faltante,
                                       pedido_pendiente if pedido_pendiente in ('si', 'no') else None)
