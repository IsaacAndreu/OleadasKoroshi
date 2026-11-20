# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Actividades v1.6.0 - rutas de la pantalla «Inicio (PDA)» (entrada única por áreas).
# Diseño: bin/versiones/diseno-pda-entrada-unica_2026-11-20_v2.md
#
# El operario pasa la tarjeta una vez (la misma memoria de la PDA que Lecturas, Contenedores y Faltante) y elige un
# área. Entrar en un área = empezar una de sus actividades: un tramo de koroshi.actividad.registro, la misma tabla
# del portátil (un solo tramo abierto por persona: cambiar de área cierra el anterior con «Cambió de actividad»).
# Después la PDA abre la pantalla del área (Lecturas, Contenedores...) si tiene una.
# Mismas comprobaciones que el portátil (main.py): permiso de Inventario y empleado activo con tarjeta.
# Solo escriben en koroshi.actividad.registro (y «Última señal»). No tocan cron_cerrar ni el «¿Sigues?».
# =============================================================================
from odoo import fields, http
from odoo.exceptions import UserError
from odoo.http import request

from ..models.actividad import AREAS
from .main import _comprobar_grupo, _empleado_valido, _error

NOMBRE_AREA = dict(AREAS)


class KoroshiInicioPda(http.Controller):

    def _registro(self):
        return request.env['koroshi.actividad.registro'].sudo()

    def _persona(self, employee_id):
        emp = request.env['hr.employee'].sudo().browse(int(employee_id or 0)).exists()
        if not _empleado_valido(emp):
            raise UserError('Pasa otra vez tu tarjeta.')
        return emp

    def _company_dom(self):
        return ['|', ('company_id', '=', False), ('company_id', 'in', request.env.user.company_ids.ids)]

    def _areas(self):
        """Las áreas con sus actividades activas, en el orden de AREAS. Un área sin actividades no sale."""
        acts = request.env['koroshi.actividad'].sudo().search([('area', '!=', False)] + self._company_dom())
        res = []
        for codigo, nombre in AREAS:
            lista = [{'id': a.id, 'nombre': a.name, 'nota': a.nota or '', 'color': a.color or '#0b4f9c',
                      'abre': bool(a.accion_abre())} for a in acts if a.area == codigo]
            if lista:
                res.append({'codigo': codigo, 'nombre': nombre, 'color': lista[0]['color'], 'actividades': lista})
        return res

    def _gestion(self, emp):
        if not request.env['koroshi.pda.jefe'].sudo().es_jefe(emp):
            return []
        return [{'id': e.id, 'nombre': e.name, 'nota': e.nota or ''}
                for e in request.env['koroshi.pda.enlace'].sudo().search([]) if e.accion_abre()]

    def _estado(self, emp, msg=''):
        Reg = self._registro()
        persona = Reg.estado_de(emp)
        tramo = Reg.abierto_de(emp)
        persona.update({
            'area': tramo.actividad_id.area or False,
            'area_nombre': NOMBRE_AREA.get(tramo.actividad_id.area, '') if tramo else '',
            'en_pda': bool(tramo and tramo.actividad_id.area),
        })
        return {'ok': True, 'persona': persona, 'areas': self._areas(), 'gestion': self._gestion(emp),
                'ahora': fields.Datetime.to_string(fields.Datetime.now()), 'msg': msg}

    def _abre(self, accion):
        """Lo que la PDA pasa a do_action: el id externo si lo tiene, si no el número."""
        if not accion:
            return False
        xmlid = accion.get_external_id().get(accion.id)
        return xmlid or accion.id

    # ------------------------------------------------------------------ rutas
    @http.route('/koroshi/actividades/inicio/tarjeta', type='json', auth='user')
    def tarjeta(self, codigo='', **kw):
        _comprobar_grupo()
        codigo = (codigo or '').strip()
        if not codigo:
            return {'ok': False, 'msg': 'Código vacío'}
        emp = request.env['hr.employee'].sudo().search([('barcode', '=', codigo)], limit=1)
        if not _empleado_valido(emp):
            return {'ok': False, 'msg': 'No conozco la tarjeta %s. Pide a tu responsable que te dé de alta.' % codigo}
        self._registro().confirmar(emp)    # pasar la tarjeta = «Sigo» (como en el portátil)
        return self._estado(emp)

    @http.route('/koroshi/actividades/inicio/estado', type='json', auth='user')
    def estado(self, employee_id=False, **kw):
        _comprobar_grupo()
        try:
            emp = self._persona(employee_id)
        except UserError as e:
            return _error(e)
        return self._estado(emp)

    @http.route('/koroshi/actividades/inicio/entrar', type='json', auth='user')
    def entrar(self, employee_id=False, actividad_id=False, **kw):
        """Entrar en un área: empieza su actividad (o sigue en ella si ya estaba) y dice qué pantalla abrir."""
        _comprobar_grupo()
        try:
            emp = self._persona(employee_id)
            act = request.env['koroshi.actividad'].sudo().browse(int(actividad_id or 0)).exists()
            if not act or not act.area:
                raise UserError('Elige un área.')
            Reg = self._registro()
            Reg.empezar(emp, act)
            Reg.confirmar(emp)
        except UserError as e:
            return _error(e)
        res = self._estado(emp, '%s: %s' % (NOMBRE_AREA.get(act.area, ''), act.name))
        res['abre'] = self._abre(act.accion_abre())
        res['inversa'] = bool(act.pide_matricula)
        return res

    @http.route('/koroshi/actividades/inicio/pausa', type='json', auth='user')
    def pausa(self, employee_id=False, **kw):
        _comprobar_grupo()
        try:
            emp = self._persona(employee_id)
            self._registro().pausar(emp)
        except UserError as e:
            return _error(e)
        return self._estado(emp, 'En pausa. Toca un área para seguir.')

    @http.route('/koroshi/actividades/inicio/salir', type='json', auth='user')
    def salir(self, employee_id=False, **kw):
        """Salir de la PDA: el tiempo se para (como una pausa: si vuelve hoy, sigue). Nunca da error."""
        _comprobar_grupo()
        try:
            emp = self._persona(employee_id)
        except UserError:
            return {'ok': True}
        Reg = self._registro()
        if Reg.abierto_de(emp):
            Reg.pausar(emp)
        return {'ok': True}

    @http.route('/koroshi/actividades/inicio/gestion', type='json', auth='user')
    def gestion(self, employee_id=False, enlace_id=False, **kw):
        _comprobar_grupo()
        try:
            emp = self._persona(employee_id)
        except UserError as e:
            return _error(e)
        if not request.env['koroshi.pda.jefe'].sudo().es_jefe(emp):
            return {'ok': False, 'msg': 'Gestión es solo para los jefes.'}
        enlace = request.env['koroshi.pda.enlace'].sudo().browse(int(enlace_id or 0)).exists()
        abre = self._abre(enlace.accion_abre()) if enlace else False
        if not abre:
            return {'ok': False, 'msg': 'Esta pantalla no está instalada.'}
        return {'ok': True, 'abre': abre}

    @http.route('/koroshi/actividades/inicio/senal', type='json', auth='user')
    def senal(self, employee_id=False, **kw):
        """Señal de vida desde otras pantallas de la PDA (Lecturas, Contenedores...): si la tarjeta se ha usado hace
        poco, el tramo abierto cuenta como «Sigo» y el «¿Sigues?» no lo cierra. Sin tramo abierto no hace nada."""
        _comprobar_grupo()
        try:
            emp = self._persona(employee_id)
        except UserError:
            return {'ok': False}
        tramo = self._registro().confirmar(emp)
        return {'ok': True, 'abierto': bool(self._registro().abierto_de(emp)), 'sigues': bool(tramo)}
