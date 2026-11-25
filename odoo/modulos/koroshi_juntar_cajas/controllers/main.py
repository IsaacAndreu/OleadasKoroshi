# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Juntar cajas v1.0.0 - rutas de la pantalla de la PDA.
# /leer: una tarjeta de operario -> la persona; una CJ -> su pedido, tienda, uds y las cajas del pedido (solo lee).
# /previa: lo que pasará al juntar (errores, avisos, bultos antes -> después), sin cambiar nada.
# /juntar: junta de verdad (todo o nada). La tarjeta es obligatoria. Token contra el doble toque.
# Permiso, tarjeta y lector: koroshi_base.pda, como Lecturas, Contenedores, Devoluciones y Recuentos.
# =============================================================================
from odoo import http
from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.koroshi_base import comun, pda


class KoroshiJuntarCajas(http.Controller):

    def _modelo(self):
        return request.env['koroshi.juntar.registro']

    def _envolver(self, funcion):
        """Errores de uso -> {'ok': False, 'msg'} (la PDA pita y lo dice), deshaciendo lo que se hubiera escrito."""
        pda.comprobar_grupo(request.env, 'Hace falta el permiso de Inventario para juntar cajas.')
        try:
            return funcion()
        except UserError as e:
            request.env.cr.rollback()
            return {'ok': False, 'msg': e.args[0] if e.args else str(e)}

    @http.route('/koroshi/juntar_cajas/leer', type='json', auth='user')
    def leer(self, codigo='', **kw):
        def hacer():
            texto = (codigo or '').strip()
            if not texto:
                return {'ok': False, 'msg': 'Código vacío.'}
            if comun.es_matricula(texto):
                return dict(self._modelo().info_caja(texto.upper()), ok=True, tipo='caja')
            emp = request.env['hr.employee'].sudo().search([('barcode', '=', texto)], limit=1)
            if emp:
                if not pda.es_empleado_valido(request.env, emp):
                    return {'ok': False, 'msg': pda.TARJETA_NO_VALE}
                return {'ok': True, 'tipo': 'persona', 'persona': {'id': emp.id, 'nombre': emp.name}}
            return {'ok': False, 'msg': '%s no es una caja (CJ) ni una tarjeta.' % texto}
        return self._envolver(hacer)

    @http.route('/koroshi/juntar_cajas/previa', type='json', auth='user')
    def previa(self, pequenas=None, destino='', **kw):
        def hacer():
            return self._modelo().previa(list(pequenas or []), destino)
        return self._envolver(hacer)

    @http.route('/koroshi/juntar_cajas/juntar', type='json', auth='user')
    def juntar(self, pequenas=None, destino='', employee_id=False, token='', **kw):
        def hacer():
            emp = pda.empleado_valido(request.env, employee_id)
            return self._modelo().juntar(list(pequenas or []), destino, employee=emp, token=token or '')
        return self._envolver(hacer)

    # ------------------------------------------------------------------ v1.1.0: «Revisar caja»
    def _persona(self, texto):
        emp = request.env['hr.employee'].sudo().search([('barcode', '=', texto)], limit=1)
        if not emp:
            return None
        if not pda.es_empleado_valido(request.env, emp):
            return {'ok': False, 'msg': pda.TARJETA_NO_VALE}
        return {'ok': True, 'tipo': 'persona', 'persona': {'id': emp.id, 'nombre': emp.name}}

    @http.route('/koroshi/revisar_caja/caja', type='json', auth='user')
    def revisar_caja(self, codigo='', **kw):
        """Una CJ -> lo que hay dentro (solo lee). Una tarjeta -> la persona."""
        def hacer():
            texto = (codigo or '').strip()
            if not texto:
                return {'ok': False, 'msg': 'Código vacío.'}
            if comun.es_matricula(texto):
                return dict(self._modelo().contenido_caja(texto.upper()), ok=True, tipo='caja')
            return self._persona(texto) or {'ok': False, 'msg': '%s no es una caja (CJ) ni una tarjeta.' % texto}
        return self._envolver(hacer)

    @http.route('/koroshi/revisar_caja/prenda', type='json', auth='user')
    def revisar_prenda(self, cj='', codigo='', **kw):
        """Una prenda leída: si está en la CJ (solo lee). Una tarjeta -> la persona."""
        def hacer():
            texto = (codigo or '').strip()
            if not texto:
                return {'ok': False, 'msg': 'Código vacío.'}
            return self._persona(texto) or dict(self._modelo().prenda_en_caja(cj, texto), tipo='prenda')
        return self._envolver(hacer)

    @http.route('/koroshi/revisar_caja/previa', type='json', auth='user')
    def revisar_previa(self, cj='', nueva='', leidas=None, **kw):
        def hacer():
            return self._modelo().previa_partir(cj, nueva, list(leidas or []))
        return self._envolver(hacer)

    @http.route('/koroshi/revisar_caja/partir', type='json', auth='user')
    def revisar_partir(self, cj='', nueva='', leidas=None, employee_id=False, token='', **kw):
        def hacer():
            emp = pda.empleado_valido(request.env, employee_id)
            return self._modelo().partir(cj, nueva, list(leidas or []), employee=emp, token=token or '')
        return self._envolver(hacer)

    @http.route('/koroshi/revisar_caja/bien', type='json', auth='user')
    def revisar_bien(self, cj='', leidas_uds=0, employee_id=False, **kw):
        def hacer():
            emp = pda.empleado_valido(request.env, employee_id)
            return self._modelo().revisada_bien(cj, leidas_uds, employee=emp)
        return self._envolver(hacer)
