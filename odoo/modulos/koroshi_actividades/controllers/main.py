# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Actividades - rutas de la pantalla del portátil.
# Todas con sudo: el usuario del portátil no necesita permisos sobre las tablas.
# Solo escriben en koroshi.actividad.registro.
# =============================================================================
from odoo import fields, http
from odoo.exceptions import UserError
from odoo.http import request


def _error(e):
    return {'ok': False, 'msg': e.args[0] if e.args else str(e)}


class KoroshiActividades(http.Controller):

    def _registro(self):
        return request.env['koroshi.actividad.registro'].sudo()

    def _persona(self, employee_id):
        emp = request.env['hr.employee'].sudo().browse(int(employee_id or 0)).exists()
        if not emp:
            raise UserError('Pasa otra vez tu tarjeta.')
        return emp

    def _actividades(self):
        acts = request.env['koroshi.actividad'].sudo().search([])
        return [{'id': a.id, 'nombre': a.name, 'color': a.color or '#0b4f9c', 'nota': a.nota or ''} for a in acts]

    def _respuesta(self, emp, msg=''):
        return {'ok': True, 'persona': self._registro().estado_de(emp), 'msg': msg}

    @http.route('/koroshi/actividades/estado', type='json', auth='user')
    def estado(self, **kw):
        """Actividades para los botones y quién está trabajando o en pausa hoy."""
        Reg = self._registro()
        hoy = Reg._hoy()
        emps = Reg.search([('dia', '=', hoy)]).mapped('employee_id')
        personas = [Reg.estado_de(e) for e in emps]
        personas.sort(key=lambda p: (p['actividad'] or '', p['nombre'] or ''))
        sin_tarjeta = Reg._param('sin_tarjeta', '0') == '1'
        return {'ok': True, 'actividades': self._actividades(), 'personas': personas,
                'ahora': fields.Datetime.to_string(fields.Datetime.now()), 'sin_tarjeta': sin_tarjeta,
                'hora_pausa': Reg._param('hora_pausa', '13:00'), 'hora_cierre': Reg._param('hora_cierre', '17:00')}

    @http.route('/koroshi/actividades/tarjeta', type='json', auth='user')
    def tarjeta(self, codigo='', **kw):
        codigo = (codigo or '').strip()
        if not codigo:
            return {'ok': False, 'msg': 'Código vacío'}
        emp = request.env['hr.employee'].sudo().search([('barcode', '=', codigo)], limit=1)
        if not emp:
            return {'ok': False, 'msg': 'No conozco la tarjeta %s. Pide a tu responsable que te dé de alta.' % codigo}
        return self._respuesta(emp)

    @http.route('/koroshi/actividades/persona', type='json', auth='user')
    def persona(self, employee_id=False, **kw):
        """Solo con el parámetro sin_tarjeta = '1': abrir a una persona tocando su nombre en la lista."""
        Reg = self._registro()
        if Reg._param('sin_tarjeta', '0') != '1':
            return {'ok': False, 'msg': 'Pasa tu tarjeta.'}
        try:
            return self._respuesta(self._persona(employee_id))
        except UserError as e:
            return _error(e)

    @http.route('/koroshi/actividades/empezar', type='json', auth='user')
    def empezar(self, employee_id=False, actividad_id=False, **kw):
        try:
            emp = self._persona(employee_id)
            act = request.env['koroshi.actividad'].sudo().browse(int(actividad_id or 0)).exists()
            if not act:
                raise UserError('Elige una actividad.')
            self._registro().empezar(emp, act)
        except UserError as e:
            return _error(e)
        return self._respuesta(emp, '%s: empiezas %s' % (emp.name, act.name))

    @http.route('/koroshi/actividades/pausar', type='json', auth='user')
    def pausar(self, employee_id=False, **kw):
        try:
            emp = self._persona(employee_id)
            self._registro().pausar(emp)
        except UserError as e:
            return _error(e)
        return self._respuesta(emp, '%s: en pausa' % emp.name)

    @http.route('/koroshi/actividades/seguir', type='json', auth='user')
    def seguir(self, employee_id=False, **kw):
        try:
            emp = self._persona(employee_id)
            reg = self._registro().seguir(emp)
        except UserError as e:
            return _error(e)
        return self._respuesta(emp, '%s: sigues con %s' % (emp.name, reg.actividad_id.name))

    # ------------------------------------------------------------------ v1.1.0: inversa
    @http.route('/koroshi/actividades/fijo', type='json', auth='user')
    def fijo(self, employee_id=False, **kw):
        """Al recargar la pantalla de una estación de inversa: vuelve a abrir a la persona que estaba leyendo
        matrículas, solo si sigue trabajando en una actividad que lee matrículas."""
        try:
            emp = self._persona(employee_id)
        except UserError as e:
            return _error(e)
        tramo = self._registro().abierto_de(emp)
        if not tramo or not tramo.actividad_id.pide_matricula:
            return {'ok': False, 'msg': '', 'suelto': True}
        return self._respuesta(emp)

    @http.route('/koroshi/actividades/matricula', type='json', auth='user')
    def matricula(self, employee_id=False, codigo='', forzar=False, **kw):
        Caja = request.env['koroshi.inversa.caja'].sudo()
        try:
            emp = self._persona(employee_id)
            caja, aviso = Caja.leer(emp, codigo, forzar=bool(forzar))
        except UserError as e:
            return _error(e)
        if not caja:
            # ya leída antes: la pantalla pregunta si se cuenta otra vez
            return {'ok': False, 'repetida': aviso, 'codigo': aviso['matricula'],
                    'msg': '%s ya la leyó %s.' % (aviso['matricula'], aviso['quien'])}
        res = self._respuesta(emp, aviso or '%s · %s uds' % (caja.name, caja.uds))
        res['aviso_tipo'] = 'warn' if aviso else 'ok'
        return res

    @http.route('/koroshi/actividades/anular', type='json', auth='user')
    def anular(self, employee_id=False, **kw):
        Caja = request.env['koroshi.inversa.caja'].sudo()
        try:
            emp = self._persona(employee_id)
            caja = Caja.anular_ultima(emp)
        except UserError as e:
            return _error(e)
        return self._respuesta(emp, '%s anulada: no cuenta.' % caja.name)

    @http.route('/koroshi/actividades/fin', type='json', auth='user')
    def fin(self, employee_id=False, **kw):
        try:
            emp = self._persona(employee_id)
            self._registro().acabar(emp)
        except UserError as e:
            return _error(e)
        return self._respuesta(emp, '%s: fin de la jornada. ¡Hasta mañana!' % emp.name)
