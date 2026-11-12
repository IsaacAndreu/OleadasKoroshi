# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Preparación en Lecturas (v3.0.0, v3.5 estado ligero) - rutas JSON de la pantalla de la PDA.
# Toda la lógica está en models/lectura.py. Las respuestas llevan siempre 'ok' y, si hay OUT, su 'estado'.
# v3.15: con lote_id (en vez de picking_id) las rutas trabajan con la agrupación Z- entera (models/agrupacion.py).
# =============================================================================
from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

from ..models.lectura import Ocupada


def _msg(e):
    return getattr(e, 'name', False) or str(e)


class KoroshiPreparacion(http.Controller):

    def _lectura(self):
        return request.env['koroshi.preparacion.lectura']

    def _agrupacion(self):
        return request.env['koroshi.preparacion.agrupacion']

    def _empleado(self, employee_id):
        return request.env['hr.employee'].sudo().browse(int(employee_id or 0)).exists()

    def _picking(self, picking_id=False, picking_name=False):
        Picking = request.env['stock.picking']
        if picking_id:
            return Picking.browse(int(picking_id)).exists()
        if picking_name:
            return Picking.search([('name', '=', picking_name)], limit=1)
        return Picking

    def _lote(self, lote_id=False):
        return request.env['stock.picking.batch'].browse(int(lote_id or 0)).exists()

    def _con_estado(self, picking, res, employee=None, ligero=False, lote=None):
        try:
            if lote:
                lote.invalidate_cache()
                res['estado'] = self._agrupacion().estado(lote, employee, ligero=ligero)   # v3.15
                return res
            picking.invalidate_cache()
            # v3.3: el ayudante ve las líneas al revés; v3.5: tras leer / deshacer, estado ligero
            res['estado'] = self._lectura().estado(picking, employee, ligero=ligero)
        except Exception:  # el estado es para pintar: nunca rompe la respuesta
            pass
        return res

    @http.route('/koroshi/preparacion/modo', type='json', auth='user')
    def modo(self, employee_id=False, picking_name=False, lote_id=False, **kw):
        """¿Se prepara esta OUT (o agrupación Z-, v3.15) en la pantalla nueva? Solo si el operario está activado."""
        emp = self._empleado(employee_id)
        Lectura = self._lectura()
        if not Lectura.empleado_activo(emp):
            return {'ok': True, 'propia': False}
        if lote_id:
            return {'ok': True, 'propia': self._agrupacion().lote_propio(self._lote(lote_id))}
        if picking_name:
            picking = self._picking(picking_name=picking_name)
            return {'ok': True, 'propia': bool(picking) and Lectura.picking_propio(picking)}
        return {'ok': True, 'propia': True}

    @http.route('/koroshi/preparacion/cargar', type='json', auth='user')
    def cargar(self, picking_id=False, picking_name=False, employee_id=False, ligero=False, lote_id=False, **kw):
        if lote_id:
            lote = self._lote(lote_id)
            if not lote:
                return {'ok': False, 'msg': 'No se encuentra la agrupación.'}
            return {'ok': True, 'estado': self._agrupacion().estado(lote, self._empleado(employee_id),
                                                                     ligero=bool(ligero))}
        picking = self._picking(picking_id, picking_name)
        if not picking:
            return {'ok': False, 'msg': 'No se encuentra la OUT %s.' % (picking_name or picking_id or '')}
        # v3.5: ligero=True para el refresco de cada 10 s al preparar a dos
        return {'ok': True, 'estado': self._lectura().estado(picking, self._empleado(employee_id), ligero=bool(ligero))}

    @http.route('/koroshi/preparacion/leer', type='json', auth='user')
    def leer(self, picking_id=False, codigo='', employee_id=False, id_lectura=False, lote_id=False, linea_id=False,
             **kw):
        lote = self._lote(lote_id) if lote_id else None
        picking = None if lote_id else self._picking(picking_id)
        emp = self._empleado(employee_id)
        try:
            if lote_id:
                res = self._agrupacion().leer(lote, emp, codigo, id_lectura, linea_id)
            else:
                res = self._lectura().leer(picking, emp, codigo, id_lectura)
        except Ocupada as e:
            # v3.6: la PDA lo vuelve a mandar en un momento (mismo id_lectura): no se pierde
            return {'ok': False, 'que': 'ocupada', 'msg': _msg(e)}
        except (UserError, ValidationError) as e:
            res = {'ok': False, 'msg': _msg(e)}
        return self._con_estado(picking, res, emp, ligero=True, lote=lote)

    @http.route('/koroshi/preparacion/deshacer', type='json', auth='user')
    def deshacer(self, picking_id=False, employee_id=False, lote_id=False, **kw):
        lote = self._lote(lote_id) if lote_id else None
        picking = None if lote_id else self._picking(picking_id)
        emp = self._empleado(employee_id)
        try:
            if lote_id:
                res = self._agrupacion().deshacer(lote, emp)
            else:
                res = self._lectura().deshacer(picking, emp)
        except Ocupada as e:
            # v3.6: la PDA lo vuelve a mandar en un momento (mismo id_lectura): no se pierde
            return {'ok': False, 'que': 'ocupada', 'msg': _msg(e)}
        except (UserError, ValidationError) as e:
            res = {'ok': False, 'msg': _msg(e)}
        return self._con_estado(picking, res, emp, ligero=True, lote=lote)

    @http.route('/koroshi/preparacion/caja', type='json', auth='user')
    def caja(self, picking_id=False, codigo='', employee_id=False, id_lectura=False, lote_id=False, out_id=False,
             **kw):
        lote = self._lote(lote_id) if lote_id else None
        picking = None if lote_id else self._picking(picking_id)
        emp = self._empleado(employee_id)
        try:
            if lote_id:
                res = self._agrupacion().caja(lote, emp, codigo, id_lectura, out_id)
            else:
                res = self._lectura().caja(picking, emp, codigo, id_lectura)
        except Ocupada as e:
            # v3.6: la PDA lo vuelve a mandar en un momento (mismo id_lectura): no se pierde
            return {'ok': False, 'que': 'ocupada', 'msg': _msg(e)}
        except (UserError, ValidationError) as e:
            res = {'ok': False, 'msg': _msg(e)}
        return self._con_estado(picking, res, emp, lote=lote)

    @http.route('/koroshi/preparacion/cantidad', type='json', auth='user')
    def cantidad(self, picking_id=False, linea_id=False, cantidad=0, employee_id=False, id_lectura=False, lote_id=False,
                 **kw):
        """v3.7: n uds de golpe en una línea ya comprobada con la pistola."""
        lote = self._lote(lote_id) if lote_id else None
        picking = None if lote_id else self._picking(picking_id)
        emp = self._empleado(employee_id)
        try:
            if lote_id:
                res = self._agrupacion().poner_cantidad(lote, emp, linea_id, cantidad, id_lectura)
            else:
                res = self._lectura().poner_cantidad(picking, emp, linea_id, cantidad, id_lectura)
        except Ocupada as e:
            return {'ok': False, 'que': 'ocupada', 'msg': _msg(e)}
        except (UserError, ValidationError) as e:
            res = {'ok': False, 'msg': _msg(e)}
        return self._con_estado(picking, res, emp, ligero=True, lote=lote)

    @http.route('/koroshi/preparacion/impresos', type='json', auth='user')
    def impresos(self, picking_id=False, lote_id=False, **kw):
        """v3.7: etiqueta de caja, etiquetas del transportista y albarán de la OUT (para volver a imprimirlos)."""
        if lote_id:
            lote = self._lote(lote_id)
            if not lote:
                return {'ok': False, 'msg': 'No se encuentra la agrupación.'}
            return {'ok': True, 'impresos': self._agrupacion().impresos(lote)}
        picking = self._picking(picking_id)
        if not picking:
            return {'ok': False, 'msg': 'No se encuentra la OUT.'}
        return {'ok': True, 'impresos': self._lectura().impresos(picking)}

    @http.route('/koroshi/preparacion/validar', type='json', auth='user')
    def validar(self, picking_id=False, employee_id=False, pedido_pendiente=False, lote_id=False, **kw):
        lote = self._lote(lote_id) if lote_id else None
        picking = None if lote_id else self._picking(picking_id)
        emp = self._empleado(employee_id)
        pp = pedido_pendiente if pedido_pendiente in ('si', 'no') else None
        try:
            if lote_id:
                res = self._agrupacion().validar(lote, emp, pp)
            else:
                res = self._lectura().validar(picking, emp, pp)
        except (UserError, ValidationError) as e:
            res = {'ok': False, 'que': 'no_validada', 'msg': _msg(e)}
        return self._con_estado(picking, res, emp, lote=lote)
