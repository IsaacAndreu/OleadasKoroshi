# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Preparación en Lecturas (v3.0.0) - rutas JSON de la pantalla de la PDA.
# Toda la lógica está en models/lectura.py. Las respuestas llevan siempre 'ok' y, si hay OUT, su 'estado'.
# =============================================================================
from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request


def _msg(e):
    return getattr(e, 'name', False) or str(e)


class KoroshiPreparacion(http.Controller):

    def _lectura(self):
        return request.env['koroshi.preparacion.lectura']

    def _empleado(self, employee_id):
        return request.env['hr.employee'].sudo().browse(int(employee_id or 0)).exists()

    def _picking(self, picking_id=False, picking_name=False):
        Picking = request.env['stock.picking']
        if picking_id:
            return Picking.browse(int(picking_id)).exists()
        if picking_name:
            return Picking.search([('name', '=', picking_name)], limit=1)
        return Picking

    def _con_estado(self, picking, res):
        try:
            picking.invalidate_cache()
            res['estado'] = self._lectura().estado(picking)
        except Exception:  # el estado es para pintar: nunca rompe la respuesta
            pass
        return res

    @http.route('/koroshi/preparacion/modo', type='json', auth='user')
    def modo(self, employee_id=False, picking_name=False, **kw):
        """¿Se prepara esta OUT en la pantalla nueva? Solo si el operario está activado y la OUT es suelta."""
        emp = self._empleado(employee_id)
        Lectura = self._lectura()
        if not Lectura.empleado_activo(emp):
            return {'ok': True, 'propia': False}
        if picking_name:
            picking = self._picking(picking_name=picking_name)
            return {'ok': True, 'propia': bool(picking) and Lectura.picking_propio(picking)}
        return {'ok': True, 'propia': True}

    @http.route('/koroshi/preparacion/cargar', type='json', auth='user')
    def cargar(self, picking_id=False, picking_name=False, **kw):
        picking = self._picking(picking_id, picking_name)
        if not picking:
            return {'ok': False, 'msg': 'No se encuentra la OUT %s.' % (picking_name or picking_id or '')}
        return {'ok': True, 'estado': self._lectura().estado(picking)}

    @http.route('/koroshi/preparacion/leer', type='json', auth='user')
    def leer(self, picking_id=False, codigo='', employee_id=False, id_lectura=False, **kw):
        picking = self._picking(picking_id)
        try:
            res = self._lectura().leer(picking, self._empleado(employee_id), codigo, id_lectura)
        except (UserError, ValidationError) as e:
            res = {'ok': False, 'msg': _msg(e)}
        return self._con_estado(picking, res)

    @http.route('/koroshi/preparacion/deshacer', type='json', auth='user')
    def deshacer(self, picking_id=False, employee_id=False, **kw):
        picking = self._picking(picking_id)
        try:
            res = self._lectura().deshacer(picking, self._empleado(employee_id))
        except (UserError, ValidationError) as e:
            res = {'ok': False, 'msg': _msg(e)}
        return self._con_estado(picking, res)

    @http.route('/koroshi/preparacion/caja', type='json', auth='user')
    def caja(self, picking_id=False, codigo='', employee_id=False, id_lectura=False, **kw):
        picking = self._picking(picking_id)
        try:
            res = self._lectura().caja(picking, self._empleado(employee_id), codigo, id_lectura)
        except (UserError, ValidationError) as e:
            res = {'ok': False, 'msg': _msg(e)}
        return self._con_estado(picking, res)

    @http.route('/koroshi/preparacion/validar', type='json', auth='user')
    def validar(self, picking_id=False, employee_id=False, pedido_pendiente=False, **kw):
        picking = self._picking(picking_id)
        try:
            res = self._lectura().validar(picking, self._empleado(employee_id),
                                          pedido_pendiente if pedido_pendiente in ('si', 'no') else None)
        except (UserError, ValidationError) as e:
            res = {'ok': False, 'que': 'no_validada', 'msg': _msg(e)}
        return self._con_estado(picking, res)
