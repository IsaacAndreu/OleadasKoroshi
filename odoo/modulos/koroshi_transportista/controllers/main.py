# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Transportista v1.1.0 - rutas de la pantalla de la PDA.
# /leer: tarjeta -> la persona; CJ (o sus últimas 4-9 cifras, v1.1.0) -> el estado de la tienda con las CJ leídas (solo lee).
# /etiquetar: GLS o XPO de verdad (solo si cuadra), y el PDF a la cola del portátil. Tarjeta obligatoria. Token.
# /reimprimir: vuelve a mandar a la cola el PDF de una expedición hecha.
# Permiso, tarjeta y lector: koroshi_base.pda, como Juntar cajas.
# =============================================================================
from odoo import http
from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.koroshi_base import comun, pda

from .. import logica


class KoroshiTransportista(http.Controller):

    def _modelo(self):
        return request.env['koroshi.transportista.registro']

    def _envolver(self, funcion):
        """Errores de uso -> {'ok': False, 'msg'} (la PDA pita y lo dice), deshaciendo lo que no se haya guardado."""
        pda.comprobar_grupo(request.env, 'Hace falta el permiso de Inventario para sacar etiquetas.')
        try:
            return funcion()
        except UserError as e:
            request.env.cr.rollback()
            return {'ok': False, 'msg': e.args[0] if e.args else str(e)}

    @http.route('/koroshi/transportista/leer', type='json', auth='user')
    def leer(self, codigo='', leidas=None, partner_id=False, **kw):
        def hacer():
            texto = (codigo or '').strip()
            leidas_ = list(leidas or [])
            def caja(cj, escrita=''):
                if escrita and cj in leidas_:
                    return {'ok': False, 'msg': '%s (escrita %s) ya está leída.' % (cj, escrita)}
                if cj not in leidas_:
                    leidas_.append(cj)
                r = self._modelo().estado(leidas_, partner_id)
                r.update({'tipo': 'caja', 'cj': cj, 'escrita': escrita})
                return r
            if comun.es_matricula(texto):
                return caja(texto.upper())
            if texto:
                emp = request.env['hr.employee'].sudo().search([('barcode', '=', texto)], limit=1)
                if emp:
                    if not pda.es_empleado_valido(request.env, emp):
                        return {'ok': False, 'msg': pda.TARJETA_NO_VALE}
                    return {'ok': True, 'tipo': 'persona', 'persona': {'id': emp.id, 'nombre': emp.name}}
                if logica.son_cifras(texto):          # v1.1.0: las últimas cifras de una CJ que no se lee
                    return caja(self._modelo().cj_por_cifras(texto, partner_id), escrita=texto)
                return {'ok': False, 'msg': '%s no es una caja (CJ), ni sus últimas cifras, ni una tarjeta.' % texto}
            r = self._modelo().estado(leidas_, partner_id)
            r['tipo'] = 'estado'
            return r
        return self._envolver(hacer)

    @http.route('/koroshi/transportista/etiquetar', type='json', auth='user')
    def etiquetar(self, leidas=None, partner_id=False, transportista='', employee_id=False, token='', **kw):
        def hacer():
            emp = pda.empleado_valido(request.env, employee_id)
            return self._modelo().etiquetar(list(leidas or []), partner_id, transportista, employee=emp,
                                            token=token or '')
        return self._envolver(hacer)

    @http.route('/koroshi/transportista/reimprimir', type='json', auth='user')
    def reimprimir(self, partner_id=False, tracking='', employee_id=False, **kw):
        def hacer():
            emp = pda.empleado_valido(request.env, employee_id)
            return self._modelo().reimprimir(partner_id, tracking, employee=emp)
        return self._envolver(hacer)
