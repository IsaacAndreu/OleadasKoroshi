# -*- coding: utf-8 -*-
# =============================================================================
# TUCTUC Operarios - datos de la pantalla de la PDA (accion de cliente tuctuc_operarios_pantalla,
# static/src/js/operarios_pantalla.js). Clon de koroshi_operarios 2.25.0 para odoo.tuctuc.com (nave de Oriola).
# Usuario con sesion: el de las PDA de Oriola, con las compañías de la PDA (PRIME, MODA INTIMA, UNITED).
#
# JSON /tuctuc/operarios/leer       {codigo, employee_id}        -> tarjeta, o pedido leido a mano
# JSON /tuctuc/operarios/operario   {employee_id}                -> el operario guardado en la PDA sigue valiendo
# JSON /tuctuc/operarios/siguiente  {employee_id}                -> v2: lo que le toca (lo abre la pantalla)
# JSON /tuctuc/operarios/saltar     {employee_id, motivo_id, nota} -> v2: saltar la que esta haciendo
# JSON /tuctuc/operarios/motivos    {}                           -> v2: motivos para saltar
# JSON /tuctuc/operarios/dejar      {employee_id}                -> "Dejar aqui" (v1, se mantiene)
# JSON /tuctuc/operarios/estado     {employee_id}                -> tareas abiertas (+ v2.3: n_operarios, contador
#                                                                    del dia del operario, minutos_inactividad;
#                                                                    v2.15: version_pantallas)
#
# v2.3: las respuestas llevan claves nuevas (solo lectura, el contrato de antes no cambia): en la asignacion y en
# cada pedido de la cola zona, lineas, uds, hechas; en la tarea minutos desde que empezo, hechas y uds.
#
# La tarjeta se busca en todas las empresas: es la misma tarjeta OP0001... que en NATH (decisión de Isaac 27/11:
# los operarios se crean aquí con el mismo código). Solo escribe en las tablas del modulo (con sudo, porque el
# usuario de la PDA no tiene permisos sobre ellas). Sin el tablero del responsable (no se clona): sin nota_hecha.
# =============================================================================

import hashlib
import logging

from odoo import fields, http
from odoo.exceptions import UserError
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.addons.tuctuc_base import comun, pda

_logger = logging.getLogger(__name__)



# v2.13 (auditoria 13/11, fase 3): las rutas hacen sudo(), asi que antes cualquier usuario con sesion podia usarlas.
# Ahora hace falta el permiso de Inventario (stock.group_stock_user; el 14/11 lo tienen los 6 usuarios de la empresa 8,
# PDA incluidas). Mismo criterio que oriola_monitor.
GRUPO_RUTAS = 'stock.group_stock_user'


def _comprobar_grupo():
    if not request.env.user.has_group(GRUPO_RUTAS):
        raise AccessError('Hace falta el permiso de Inventario para usar esta pantalla.')


def _empleado_valido(emp):
    """El employee_id lo manda la PDA y no se puede dar por bueno: empleado activo, con tarjeta (ID de credencial)
    y sin empresa o de una empresa del usuario de la PDA (tuctuc_base.pda.es_empleado_valido)."""
    return pda.es_empleado_valido(request.env, emp)


def _hora(dt):
    if not dt:
        return ''
    return comun.a_local(dt).strftime('%H:%M')


def _version_pantallas():
    """v2.15: huella de lo que hay instalado en la BD (latest_version de los modulos tuctuc_*) mas el parametro
    tuctuc_operarios.recargar_pda. Cambia al actualizar un modulo (cuando la BD ya esta al dia, no al reiniciar) o al
    cambiar el parametro: la PDA lo ve en /estado y se recarga sola en un momento seguro (operarios_pantalla.js)."""
    request.env.cr.execute("""SELECT name, COALESCE(latest_version, '') FROM ir_module_module
                              WHERE state = 'installed' AND name LIKE %s ORDER BY name""", ('tuctuc%',))
    texto = ';'.join('%s=%s' % fila for fila in request.env.cr.fetchall())
    forzar = request.env['ir.config_parameter'].sudo().get_param('tuctuc_operarios.recargar_pda', '') or ''
    return hashlib.md5((texto + '|' + forzar).encode('utf-8')).hexdigest()[:12]


def _error(e):
    return {'ok': False, 'msg': e.name if hasattr(e, 'name') else str(e)}


def _zona(lote):
    nombre = lote.name or ''
    if '-' in nombre:
        return nombre.rsplit('-', 1)[-1]
    return nombre.rsplit('_', 1)[-1] if '_' in nombre else ''


def _detalle(pickings, lote):
    """v2.3 (solo lectura): zona, n de lineas, uds pedidas y uds ya leidas de una OUT, INT o agrupacion."""
    Tarea = request.env['tuctuc.operario.tarea'].sudo()
    pickings = pickings.sudo()
    moves = pickings.mapped('move_lines').filtered(lambda m: m.state != 'cancel')
    return {
        'zona': _zona(lote),
        'lineas': len(moves),
        'uds': round(Tarea._uds_pedidas(pickings)),
        'hechas': round(Tarea._uds_leidas(pickings)),
    }


def _asig_json(a):
    """asignacion.json() + v2.3 zona / lineas / uds / hechas."""
    if not a:
        return False
    res = a.json()
    try:
        lote = a.batch_id if a.tipo == 'agrupacion' else a.picking_id.batch_id
        res.update(_detalle(a._pickings(), lote))
    except Exception:  # el detalle es solo informativo: nunca rompe la pantalla
        _logger.warning('TUCTUC Operarios: sin detalle de %s', a.name, exc_info=True)
    return res


def _tarea_json(t):
    if not t:
        return False
    ref = t.batch_id.name if t.tipo == 'agrupacion' else t.picking_id.name
    tienda = '' if t.tipo == 'agrupacion' else (t.picking_id.partner_id.name or '')
    return {
        'id': t.id,
        'operario': t.employee_id.name,
        'ref': ref or t.referencia or '',
        'tipo': t.tipo,
        'picking_name': t.picking_id.name or '',
        'batch_id': t.batch_id.id or False,
        'tienda': tienda,
        'inicio': _hora(t.inicio),
        'estado': t.estado,
        'uds_total': t.uds_total,
        # v2.3
        'minutos': int(max((fields.Datetime.now() - t.inicio).total_seconds() // 60, 0)) if t.inicio else 0,
        'zona': t.zona or '',
    }


class TuctucOperarios(http.Controller):

    def _empleado(self, employee_id):
        emp = request.env['hr.employee'].sudo().browse(int(employee_id or 0)).exists()
        if not _empleado_valido(emp):           # v2.13
            raise UserError('Lee primero tu tarjeta')
        return emp

    def _cola_json(self, emp):
        Asig = request.env['tuctuc.operario.asignacion'].sudo()
        return [_asig_json(a) for a in Asig.cola_de(emp)[:10]]

    def _siguiente(self, emp):
        Asig = request.env['tuctuc.operario.asignacion'].sudo()
        asig, nueva = Asig.siguiente(emp)
        tarea = asig.tarea_id if asig else False
        ayudante = bool(asig) and asig.employee_id != emp
        if ayudante:
            # v2.5: de ayudante (puesto desde el reparto): su tarea, no la del titular
            tarea = request.env['tuctuc.operario.tarea'].sudo().abierta_de(emp)
        res = {'ok': True, 'que': 'siguiente', 'nueva': nueva, 'asignacion': _asig_json(asig) if asig else False,
               'tarea': _tarea_json(tarea) if tarea else False, 'cola': self._cola_json(emp),
               'operario': emp.name, 'employee_id': emp.id}
        if ayudante and nueva:
            res['msg_ayudante'] = 'Te unes a %s con %s. Tú haces la segunda mitad.' % (
                asig.employee_id.name, asig.picking_id.name)
        if not asig:
            res['msg'] = 'No tienes más pedidos. Pide a tu responsable.'
        return res

    @http.route('/tuctuc/operarios/leer', type='json', auth='user')
    def leer(self, codigo='', employee_id=False, ayudar=False, **kw):
        _comprobar_grupo()   # v2.13
        codigo = (codigo or '').strip()
        if not codigo:
            return {'ok': False, 'msg': 'Codigo vacio'}
        Emp = request.env['hr.employee'].sudo().with_context(active_test=True)
        emp = Emp.search([('barcode', '=', codigo)], limit=1)
        Tarea = request.env['tuctuc.operario.tarea'].sudo()
        if emp:
            return {'ok': True, 'que': 'tarjeta', 'employee_id': emp.id, 'operario': emp.name,
                    'abierta': _tarea_json(Tarea.abierta_de(emp))}
        if not employee_id and request.env.user.has_group('tuctuc_operarios.grupo_tarjeta_obligatoria'):
            # v2.2: para este grupo, sin tarjeta no se abre nada (el JS tampoco lo abre por su cuenta)
            return {'ok': False, 'obligatoria': True,
                    'msg': 'Lee primero tu tarjeta. Sin tarjeta no se puede abrir ningún pedido.'}
        Asig = request.env['tuctuc.operario.asignacion'].sudo()
        try:
            emp = self._empleado(employee_id)
            tipo, picking, lote = Tarea.buscar_objetivo(codigo)
            if not tipo:
                raise UserError('No encuentro ningun pedido ni agrupacion con el codigo %s' % codigo)
            ayuda = Asig.ayudante_de(emp, tipo, picking)
            if ayuda and not ayudar:
                # v2.5: antes de entrar se pregunta (por si la ha leido sin querer)
                # v2.8: solo se llega aqui si alguien la esta haciendo ahora; se nombra a quien de verdad lee
                nombres = ', '.join(Asig.quien_la_hace(emp, picking).mapped('name')) or ayuda.employee_id.name
                return {'ok': True, 'que': 'ayudar', 'codigo': codigo, 'titular': nombres,
                        'msg': '%s está haciendo %s.' % (nombres, picking.name)}
            if ayuda:
                # v2.4: la OUT ya la esta haciendo otro -> entra de ayudante (preparar a dos)
                tarea = Asig.unirse(emp, ayuda)
                return {'ok': True, 'que': 'empezada', 'ayudante': True, 'tarea': _tarea_json(tarea),
                        'asignacion': _asig_json(ayuda), 'cola': self._cola_json(emp),
                        'msg': 'Te unes a %s con %s. Tú haces la segunda mitad.' % (ayuda.employee_id.name, picking.name)}
            asig = Asig.leida_a_mano(emp, tipo, picking, lote)
            if asig._terminada():
                asig._cerrar_hecha()
                raise UserError('%s ya esta validado' % asig.name)
            tarea = asig._empezar(emp)
        except UserError as e:
            return _error(e)
        return {'ok': True, 'que': 'empezada', 'msg': '', 'tarea': _tarea_json(tarea),
                'asignacion': _asig_json(asig), 'cola': self._cola_json(emp)}

    @http.route('/tuctuc/operarios/operario', type='json', auth='user')
    def operario(self, employee_id=False, **kw):
        _comprobar_grupo()   # v2.13
        try:
            emp = self._empleado(employee_id)
        except UserError as e:
            return _error(e)
        return {'ok': True, 'employee_id': emp.id, 'operario': emp.name}

    @http.route('/tuctuc/operarios/siguiente', type='json', auth='user')
    def siguiente(self, employee_id=False, **kw):
        _comprobar_grupo()   # v2.13
        try:
            emp = self._empleado(employee_id)
            return self._siguiente(emp)
        except UserError as e:
            return _error(e)

    @http.route('/tuctuc/operarios/motivos', type='json', auth='user')
    def motivos(self, **kw):
        _comprobar_grupo()   # v2.13
        Motivo = request.env['tuctuc.operario.motivo'].sudo()
        sin_caja = request.env.ref('tuctuc_operarios.motivo_sin_caja', raise_if_not_found=False)   # v2.17
        return {'ok': True, 'motivos': [{'id': m.id, 'nombre': m.name, 'destino': m.destino,
                                         'pide_nota': m.pide_nota, 'sin_caja': m == sin_caja}
                                        for m in Motivo.search([])]}

    @http.route('/tuctuc/operarios/saltar', type='json', auth='user')
    def saltar(self, employee_id=False, motivo_id=False, nota='', **kw):
        _comprobar_grupo()   # v2.13
        Asig = request.env['tuctuc.operario.asignacion'].sudo()
        Motivo = request.env['tuctuc.operario.motivo'].sudo()
        try:
            emp = self._empleado(employee_id)
            motivo = Motivo.browse(int(motivo_id or 0)).exists()
            if not motivo:
                raise UserError('Elige un motivo')
            asig, destino = Asig.saltar(emp, motivo, nota)
        except UserError as e:
            return _error(e)
        texto = {'oficina': '%s queda en expediciones' % asig.name,
                 'final': '%s va al final de tu cola' % asig.name,
                 'suya': '%s sigue siendo tuya: la primera al volver' % asig.name,
                 'libre': '%s la hará otro: no te vuelve a salir' % asig.name,          # v2.10
                 'pausa': '%s sigue siendo tuya: la primera al volver' % asig.name}[destino]
        if destino in ('suya', 'pausa'):
            # fin de turno: no se abre nada mas
            return {'ok': True, 'que': 'saltada', 'destino': destino, 'msg': texto, 'cola': self._cola_json(emp)}
        res = self._siguiente(emp)
        res.update({'que': 'saltada', 'destino': destino, 'msg_salto': texto})
        return res

    @http.route('/tuctuc/operarios/soltar', type='json', auth='user')
    def soltar(self, employee_id=False, **kw):
        """v2.25: dejar el pedido (el que hace o el de la pausa) para que lo haga otro. Lo usa la pausa de Lecturas."""
        _comprobar_grupo()
        Asig = request.env['tuctuc.operario.asignacion'].sudo()
        try:
            emp = self._empleado(employee_id)
            asig, destino = Asig.soltar(emp)
        except UserError as e:
            return _error(e)
        texto = ('%s queda en expediciones: ya lo había dejado otro hoy' % asig.name if destino == 'oficina'
                 else '%s la hará otro: no te vuelve a salir hoy' % asig.name)
        return {'ok': True, 'que': 'soltada', 'destino': destino, 'msg': texto}

    @http.route('/tuctuc/operarios/dejar', type='json', auth='user')
    def dejar(self, employee_id=False, **kw):
        _comprobar_grupo()   # v2.13
        Tarea = request.env['tuctuc.operario.tarea'].sudo()
        try:
            emp = self._empleado(employee_id)
            tarea = Tarea.dejar(emp)
        except UserError as e:
            return _error(e)
        return {'ok': True, 'que': 'dejada', 'tarea': _tarea_json(tarea), 'uds': tarea.uds,
                'minutos': round(tarea.minutos)}

    @http.route('/tuctuc/operarios/estado', type='json', auth='user')
    def estado(self, employee_id=False, **kw):
        _comprobar_grupo()   # v2.13
        Tarea = request.env['tuctuc.operario.tarea'].sudo()
        abiertas = Tarea.search([('estado', '=', 'curso')], order='inicio asc', limit=200)
        res = {'ok': True, 'ahora': _hora(fields.Datetime.now()),
               'abiertas': [_tarea_json(t) for t in abiertas],
               # v2.3
               'n_operarios': len(abiertas.mapped('employee_id')),
               'minutos_inactividad': self._minutos_inactividad(),
               'version_pantallas': _version_pantallas()}   # v2.15
        emp = request.env['hr.employee'].sudo().browse(int(employee_id or 0)).exists()
        if emp:
            res['dia'] = self._contador_dia(emp)
        return res

    @http.route('/tuctuc/operarios/minutos_tarjeta', type='json', auth='user')
    def minutos_tarjeta(self, **kw):
        """v2.22.1: minutos sin actividad que dura la tarjeta compartida en Contenedores y Faltante
        (parametro tuctuc_operarios.minutos_tarjeta, 60 si no esta o no es un numero; minimo 1)."""
        _comprobar_grupo()
        valor = request.env['ir.config_parameter'].sudo().get_param('tuctuc_operarios.minutos_tarjeta', '60')
        try:
            minutos = int(float(valor or 60))
        except ValueError:
            minutos = 60
        return {'ok': True, 'minutos': max(minutos, 1)}

    def _minutos_inactividad(self):
        valor = request.env['ir.config_parameter'].sudo().get_param('tuctuc_operarios.minutos_inactividad', '0')
        try:
            return max(int(float(valor or 0)), 0)
        except ValueError:
            return 0

    def _contador_dia(self, emp):
        """v2.3: pedidos y uds de hoy del operario: uds de las tareas cerradas + lo leido desde que empezo en la
        abierta; pedidos = tareas acabadas (validadas). v2.12: las uds de la abierta con _uds_hasta_ahora(), lo mismo
        que resumen_operario_dia() (asi cuenta bien la OUT a dos de tuctuc_preparacion)."""
        Tarea = request.env['tuctuc.operario.tarea'].sudo()
        hoy = comun.hoy_local()
        pedidos, uds = 0, 0.0
        for t in Tarea.search([('dia', '=', hoy), ('employee_id', '=', emp.id)]):
            if t.estado == 'curso':
                uds += t._uds_hasta_ahora()
            else:
                uds += t.uds or 0.0
                if t.estado == 'acabada':
                    pedidos += 1
        return {'pedidos': pedidos, 'uds': int(round(uds))}
