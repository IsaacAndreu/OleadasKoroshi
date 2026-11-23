# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Prenda en el suelo v1.0.0 - rutas de la pantalla de la PDA.
# /leer: lo que se lee en la pantalla. Una tarjeta de operario -> la persona; un hueco -> «estoy aquí»; una prenda
#   -> a dónde va (koroshi.prenda.suelo.buscar). /contestar: «Hecho» / «No sirve». /encontrada: caso A.
# Mismas comprobaciones que Lecturas: permiso de Inventario y empleado activo con tarjeta de la empresa.
# =============================================================================
from odoo import http
from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.koroshi_operarios.controllers.main import _comprobar_grupo, _empleado_valido


class KoroshiPrendaSuelo(http.Controller):

    def _modelo(self):
        return request.env['koroshi.prenda.suelo']

    def _empleado(self, employee_id):
        emp = request.env['hr.employee'].sudo().browse(int(employee_id or 0)).exists()
        return emp if _empleado_valido(emp) else request.env['hr.employee']

    def _envolver(self, funcion):
        """Errores de uso -> {'ok': False, 'msg'} (la PDA pita y lo dice), deshaciendo lo que se hubiera escrito."""
        _comprobar_grupo()
        try:
            return funcion()
        except UserError as e:
            request.env.cr.rollback()
            return {'ok': False, 'msg': e.args[0] if e.args else str(e)}

    @http.route('/koroshi/prenda_suelo/leer', type='json', auth='user')
    def leer(self, codigo='', employee_id=False, ubicacion_id=False, sin_faltantes=False, **kw):
        def hacer():
            texto = (codigo or '').strip()
            if not texto:
                return {'ok': False, 'msg': 'Código vacío.'}
            emp = request.env['hr.employee'].sudo().search([('barcode', '=', texto)], limit=1)
            if emp:
                if not _empleado_valido(emp):
                    return {'ok': False, 'msg': 'Esa tarjeta no vale (empleado de baja o de otra empresa).'}
                return {'ok': True, 'tipo': 'persona', 'persona': {'id': emp.id, 'nombre': emp.name}}
            Modelo = self._modelo()
            loc = Modelo.ubicacion_por_codigo(texto)
            if loc:
                return {'ok': True, 'tipo': 'ubicacion',
                        'ubicacion': {'id': loc.id, 'nombre': Modelo._ubi_corta(loc)}}
            product = Modelo.producto_por_codigo(texto)
            if not product:
                return {'ok': False, 'msg': 'No conozco el código %s: ni prenda, ni hueco, ni tarjeta.' % texto}
            ubicacion = request.env['stock.location'].sudo().browse(int(ubicacion_id or 0)).exists()
            return Modelo.buscar(product, self._empleado(employee_id), ubicacion,
                                 sin_faltantes=bool(sin_faltantes), codigo=texto)
        return self._envolver(hacer)

    @http.route('/koroshi/prenda_suelo/contestar', type='json', auth='user')
    def contestar(self, registro_id=False, resultado='', employee_id=False, **kw):
        def hacer():
            reg = self._modelo().sudo().browse(int(registro_id or 0)).exists()
            if not reg:
                return {'ok': False, 'msg': 'No encuentro esta búsqueda. Vuelve a leer la prenda.'}
            reg.contestar(resultado, self._empleado(employee_id))
            return {'ok': True}
        return self._envolver(hacer)

    @http.route('/koroshi/prenda_suelo/encontrada', type='json', auth='user')
    def encontrada(self, registro_id=False, employee_id=False, **kw):
        def hacer():
            reg = self._modelo().sudo().browse(int(registro_id or 0)).exists()
            if not reg:
                return {'ok': False, 'msg': 'No encuentro esta búsqueda. Vuelve a leer la prenda.'}
            hueco = reg.encontrada(self._empleado(employee_id))
            return {'ok': True, 'hueco': hueco}
        return self._envolver(hacer)
