# -*- coding: utf-8 -*-
# =============================================================================
# TUCTUC Preparación en Lecturas - rutas JSON de la pantalla de la PDA. Clon de koroshi_preparacion 3.38.1 para
# odoo.tuctuc.com (nave de Oriola - Amposta). Toda la lógica está en models/lectura.py. Las respuestas llevan siempre
# 'ok' y, si hay OUT, su 'estado'.
#
# Diferencias con KOROSHI:
#   - Multicompañía: cada ruta trabaja con la compañía de la OUT como compañía activa (tuctuc_base.pda.con_compania),
#     para que put_in_pack, los paquetes y la validación salgan con la compañía de la OUT (PRIME, MODA INTIMA o
#     UNITED) aunque en la PDA esté marcada otra.
#   - Sin agrupaciones Z- (en Oriola no hay): con lote_id, la agrupación no se prepara aquí (la PDA abre la app de
#     código de barras, como hace koroshi con las agrupaciones que no son Z-).
#   - Sin «Caja llena» (sin tipos de caja con capacidad): /caja_llena contesta ok sin guardar nada.
#
# v3.29 (de KOROSHI): todo lo que la PDA manda con id_lectura y Odoo no acepta queda apuntado. Mover, deshacer y
# validar llevan id_lectura: si la PDA reintenta, no se hace dos veces.
# v3.35 (de KOROSHI): las rutas que escriben piden permiso de Inventario y una tarjeta válida (tuctuc_base.pda).
# =============================================================================
import logging
import time

from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

from odoo.addons.tuctuc_base import pda

from ..models.lectura import Ocupada

_logger = logging.getLogger(__name__)

SIN_AGRUPACION = 'Las agrupaciones se preparan OUT a OUT: lee la OUT.'
SIN_PERMISO = 'Hace falta el permiso de Inventario para preparar.'


def _msg(e):
    return getattr(e, 'name', False) or str(e)


class TuctucPreparacion(http.Controller):

    def _lectura(self, diferida=False, picking=None):
        """El modelo de lecturas; con picking, con la compañía de la OUT como compañía activa (UserError si el usuario
        de la PDA no tiene esa compañía)."""
        L = request.env['tuctuc.preparacion.lectura']
        if picking:
            L = pda.con_compania(L, picking.sudo().company_id)
        return L.with_context(kp_diferida=True) if diferida else L   # v3.29

    def _empleado(self, employee_id):
        return request.env['hr.employee'].sudo().browse(int(employee_id or 0)).exists()

    def _comprobar_grupo(self):
        """True si el usuario de la PDA no tiene permiso de Inventario (también en las rutas que solo leen)."""
        return not request.env.user.has_group(pda.GRUPO_ALMACEN)

    def _no_vale(self, employee_id):
        """v3.35 (R16): texto del rechazo si el usuario de la PDA no tiene permiso de Inventario o si la tarjeta que
        manda no vale (de baja, sin tarjeta o de otra empresa). '' = todo bien. Sin tarjeta, como antes (se acepta)."""
        if self._comprobar_grupo():
            return SIN_PERMISO
        if employee_id and not pda.es_empleado_valido(request.env, self._empleado(employee_id)):
            _logger.warning('TUCTUC Preparación: tarjeta no válida (employee_id %s): no se guarda', employee_id)
            return pda.TARJETA_NO_VALE
        return ''

    def _picking(self, picking_id=False, picking_name=False):
        Picking = request.env['stock.picking']
        if picking_id:
            return Picking.browse(int(picking_id)).exists()
        if picking_name:
            return Picking.search([('name', '=', picking_name)], limit=1)
        return Picking

    def _con_estado(self, picking, res, employee=None, ligero=False):
        # v3.34 (R5): lo leído se escribe aquí, fuera del try (si falla, el error sale y la PDA reintenta)
        request.env['stock.move.line'].flush()
        if not picking:
            return res
        try:
            picking.invalidate_cache()
            Lectura = self._lectura(picking=picking)
            res['estado'] = Lectura.estado(picking.with_env(Lectura.env), employee, ligero=ligero)
        except Exception:  # el estado es para pintar: nunca rompe la respuesta (v3.29: pero queda en el log)
            _logger.exception('TUCTUC Preparación: no se ha podido calcular el estado de %s', picking.display_name)
        return res

    def _cerrada(self, picking, res):
        """v3.29: la OUT ya está hecha o cancelada: la PDA no se queda esperando con lo de la cola."""
        if res.get('ok') or res.get('que') in ('repetida', 'ocupada', 'validada'):
            return res
        if picking and picking.state in ('done', 'cancel'):
            res['que'] = 'out_cerrada'
        return res

    def _rechazo(self, Lectura, picking, emp, tipo, codigo, id_lectura, res):
        """v3.29: lo que no se ha aceptado, apuntado siempre (si la lógica no lo ha apuntado ya)."""
        if not res.get('ok') and id_lectura and res.get('que') not in ('ocupada', 'repetida'):
            Lectura.apuntar_rechazo(picking, emp, tipo, codigo, res.get('msg') or '', id_lectura)
        return res

    def _hacer(self, picking, diferida, funcion):
        """Llama a funcion(Lectura, picking) con la compañía de la OUT. Devuelve (Lectura, res)."""
        Lectura = self._lectura(diferida)
        try:
            Lectura = self._lectura(diferida, picking)
            return Lectura, funcion(Lectura, picking.with_env(Lectura.env) if picking else picking)
        except Ocupada as e:
            # v3.6: la PDA lo vuelve a mandar en un momento (mismo id_lectura): no se pierde
            return Lectura, {'ok': False, 'que': 'ocupada', 'msg': _msg(e)}
        except (UserError, ValidationError) as e:
            return Lectura, {'ok': False, 'msg': _msg(e)}

    @http.route('/tuctuc/preparacion/modo', type='json', auth='user')
    def modo(self, employee_id=False, picking_name=False, lote_id=False, **kw):
        """¿Se prepara esta OUT en la pantalla nueva? Solo si el operario está activado. Las agrupaciones, no."""
        if self._comprobar_grupo():
            return {'ok': True, 'propia': False}
        emp = self._empleado(employee_id)
        Lectura = self._lectura()
        if not Lectura.empleado_activo(emp) or lote_id:
            return {'ok': True, 'propia': False}
        if picking_name:
            picking = self._picking(picking_name=picking_name)
            return {'ok': True, 'propia': bool(picking) and Lectura.picking_propio(picking)}
        return {'ok': True, 'propia': True}

    @http.route('/tuctuc/preparacion/cargar', type='json', auth='user')
    def cargar(self, picking_id=False, picking_name=False, employee_id=False, ligero=False, lote_id=False, **kw):
        if self._comprobar_grupo():
            return {'ok': False, 'msg': SIN_PERMISO}
        if lote_id:
            return {'ok': False, 'msg': SIN_AGRUPACION}
        picking = self._picking(picking_id, picking_name)
        if not picking:
            return {'ok': False, 'msg': 'No se encuentra la OUT %s.' % (picking_name or picking_id or '')}
        try:
            Lectura = self._lectura(picking=picking)
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}
        # v3.5: ligero=True para el refresco al preparar a dos
        return {'ok': True, 'estado': Lectura.estado(picking.with_env(Lectura.env), self._empleado(employee_id),
                                                     ligero=bool(ligero))}

    @http.route('/tuctuc/preparacion/leer', type='json', auth='user')
    def leer(self, picking_id=False, codigo='', employee_id=False, id_lectura=False, lote_id=False, linea_id=False,
             diferida=False, **kw):
        if lote_id:
            return {'ok': False, 'msg': SIN_AGRUPACION}
        picking = self._picking(picking_id)
        emp = self._empleado(employee_id)
        no_vale = self._no_vale(employee_id)   # v3.35 (R16)
        if no_vale:
            return {'ok': False, 'msg': no_vale}
        Lectura, res = self._hacer(picking, diferida, lambda L, p: L.leer(p, emp, codigo, id_lectura))
        if res.get('que') == 'ocupada':
            return res
        self._rechazo(Lectura, picking, emp, 'leer', codigo, id_lectura, self._cerrada(picking, res))
        return self._con_estado(picking, res, emp, ligero=True)

    @http.route('/tuctuc/preparacion/deshacer', type='json', auth='user')
    def deshacer(self, picking_id=False, employee_id=False, lote_id=False, id_lectura=False, **kw):
        if lote_id:
            return {'ok': False, 'msg': SIN_AGRUPACION}
        picking = self._picking(picking_id)
        emp = self._empleado(employee_id)
        no_vale = self._no_vale(employee_id)   # v3.35 (R16)
        if no_vale:
            return {'ok': False, 'msg': no_vale}
        _L, res = self._hacer(picking, False, lambda L, p: L.deshacer(p, emp, id_lectura))
        if res.get('que') == 'ocupada':
            return res
        self._cerrada(picking, res)
        return self._con_estado(picking, res, emp, ligero=True)

    @http.route('/tuctuc/preparacion/caja', type='json', auth='user')
    def caja(self, picking_id=False, codigo='', employee_id=False, id_lectura=False, lote_id=False, out_id=False,
             tipo_caja=False, diferida=False, **kw):
        if lote_id:
            return {'ok': False, 'msg': SIN_AGRUPACION}
        picking = self._picking(picking_id)
        emp = self._empleado(employee_id)
        no_vale = self._no_vale(employee_id)   # v3.35 (R16)
        if no_vale:
            return {'ok': False, 'msg': no_vale}
        Lectura, res = self._hacer(picking, diferida, lambda L, p: L.caja(p, emp, codigo, id_lectura, tipo_caja))
        if res.get('que') == 'ocupada':
            return res
        self._rechazo(Lectura, picking, emp, 'caja', codigo, id_lectura, self._cerrada(picking, res))
        return self._con_estado(picking, res, emp)

    @http.route('/tuctuc/preparacion/cantidad', type='json', auth='user')
    def cantidad(self, picking_id=False, linea_id=False, cantidad=0, employee_id=False, id_lectura=False, lote_id=False,
                 diferida=False, **kw):
        """v3.7: n uds de golpe en una línea ya comprobada con la pistola."""
        if lote_id:
            return {'ok': False, 'msg': SIN_AGRUPACION}
        picking = self._picking(picking_id)
        emp = self._empleado(employee_id)
        no_vale = self._no_vale(employee_id)   # v3.35 (R16)
        if no_vale:
            return {'ok': False, 'msg': no_vale}
        Lectura, res = self._hacer(picking, diferida,
                                   lambda L, p: L.poner_cantidad(p, emp, linea_id, cantidad, id_lectura))
        if res.get('que') == 'ocupada':
            return res
        self._rechazo(Lectura, picking, emp, 'leer', 'A MANO +%s' % (cantidad or 0), id_lectura,
                      self._cerrada(picking, res))
        return self._con_estado(picking, res, emp, ligero=True)

    @http.route('/tuctuc/preparacion/rechazadas', type='json', auth='user')
    def rechazadas(self, picking_id=False, lote_id=False, lecturas=None, motivo='', **kw):
        """v3.29: lo de la cola de la PDA que no se ha aplicado y que Odoo no ha podido apuntar él mismo: se apunta como
        rechazado de cola para que el encargado lo vea. lecturas = [{tipo, codigo, id, employee_id, n}]."""
        if self._comprobar_grupo():
            return {'ok': False, 'msg': SIN_PERMISO}
        picking = self._picking(picking_id) if picking_id else None
        texto = ('Error de Odoo: %s' % motivo)[:200] if motivo else \
            'Caducada: más de 24 h en la memoria de la PDA. No se ha aplicado.'
        Lectura = self._lectura(True)
        n = 0
        for i in (lecturas or [])[:500]:
            if not isinstance(i, dict):
                continue
            tipo = i.get('tipo') if i.get('tipo') in ('leer', 'caja') else 'leer'
            codigo = i.get('codigo') or ('A MANO +%s' % (i.get('n') or 1) if i.get('tipo') == 'cantidad' else '')
            if Lectura.apuntar_rechazo(picking, self._empleado(i.get('employee_id')), tipo, codigo, texto,
                                       i.get('id') or False, cantidad=i.get('n') or 0):
                n += 1
        return {'ok': True, 'apuntadas': n}

    @http.route('/tuctuc/preparacion/color', type='json', auth='user')
    def color(self, employee_id=False, color=False, **kw):
        """v3.21: el color de la franja de la ubicación de cada operario (leer o, con color, guardar)."""
        emp = self._empleado(employee_id)
        no_vale = self._no_vale(employee_id)   # v3.35 (R16)
        if no_vale:
            return {'ok': False, 'msg': no_vale}
        Pref = request.env['tuctuc.preparacion.preferencia'].sudo()
        if color:
            return {'ok': True, 'color': Pref.poner_color(emp, color)}
        return {'ok': True, 'color': Pref.color_de(emp)}

    @http.route('/tuctuc/preparacion/caja_llena', type='json', auth='user')
    def caja_llena(self, **kw):
        """Sin «Caja llena» en Oriola (desactivada en el estado: la PDA no pregunta). Si llega, no se guarda nada."""
        if self._comprobar_grupo():
            return {'ok': False, 'msg': SIN_PERMISO}
        return {'ok': True}

    @http.route('/tuctuc/preparacion/mover_caja', type='json', auth='user')
    def mover_caja(self, picking_id=False, linea_id=False, cantidad=1, destino='', employee_id=False, id_lectura=False,
                   **kw):
        """v3.21: pasar uds de una caja cerrada a otra caja de la OUT (o a una nueva). v3.29: con id_lectura."""
        picking = self._picking(picking_id)
        emp = self._empleado(employee_id)
        no_vale = self._no_vale(employee_id)   # v3.35 (R16)
        if no_vale:
            return {'ok': False, 'msg': no_vale}
        _L, res = self._hacer(picking, False,
                              lambda L, p: L.mover_caja(p, emp, linea_id, cantidad, destino, id_lectura))
        if res.get('que') == 'ocupada':
            return res
        self._cerrada(picking, res)
        return self._con_estado(picking, res, emp)

    @http.route('/tuctuc/preparacion/impresos', type='json', auth='user')
    def impresos(self, picking_id=False, lote_id=False, **kw):
        """v3.7: etiquetas del transportista y albarán de la OUT (para volver a imprimirlos)."""
        if self._comprobar_grupo():
            return {'ok': False, 'msg': SIN_PERMISO}
        if lote_id:
            return {'ok': False, 'msg': SIN_AGRUPACION}
        picking = self._picking(picking_id)
        if not picking:
            return {'ok': False, 'msg': 'No se encuentra la OUT.'}
        return {'ok': True, 'impresos': self._lectura().impresos(picking)}

    @http.route('/tuctuc/preparacion/ronda_marcar', type='json', auth='user')
    def ronda_marcar(self, picking_id=False, linea_id=False, resultado='', employee_id=False, id_lectura=False, **kw):
        """v3.33: ronda de faltantes: «No está» / «La ubicación no existe» en una línea."""
        picking = self._picking(picking_id)
        emp = self._empleado(employee_id)
        no_vale = self._no_vale(employee_id)   # v3.35 (R16)
        if no_vale:
            return {'ok': False, 'msg': no_vale}
        _L, res = self._hacer(picking, False,
                              lambda L, p: L.ronda_marcar(p, emp, linea_id, resultado, id_lectura))
        if res.get('que') == 'ocupada':
            return res
        return self._con_estado(picking, res, emp)

    @http.route('/tuctuc/preparacion/validar', type='json', auth='user')
    def validar(self, picking_id=False, employee_id=False, pedido_pendiente=False, lote_id=False, tipo_caja=False,
                incompleto=False, id_lectura=False, **kw):
        if lote_id:
            return {'ok': False, 'que': 'no_validada', 'msg': SIN_AGRUPACION}
        picking = self._picking(picking_id)
        emp = self._empleado(employee_id)
        no_vale = self._no_vale(employee_id)   # v3.35 (R16)
        if no_vale:
            return {'ok': False, 'msg': no_vale}
        pp = pedido_pendiente if pedido_pendiente in ('si', 'no') else None
        t0 = time.monotonic()
        _L, res = self._hacer(picking, False, lambda L, p: L.validar(p, emp, pp, tipo_caja, bool(incompleto),
                                                                     id_lectura))
        if res.get('que') == 'ocupada':
            # v3.29: otra petición está validando (la misma PDA que reintenta u otra): se vuelve a probar
            return res
        if not res.get('ok') and not res.get('que'):
            res['que'] = 'no_validada'
        t1 = time.monotonic()
        tiempos = res.pop('_tiempos', None) or {}
        res = self._con_estado(picking, res, emp)
        self._log_validar(picking, pp, res, tiempos, t0, t1)
        return res

    def _log_validar(self, picking, pp, res, tiempos, t0, t1):
        """v3.34 (R6): una línea por validación con los ms de cada tramo. Nunca rompe la respuesta."""
        try:
            t2 = time.monotonic()
            transportistas = ', '.join(sorted(set(picking.mapped('carrier_id.name')))) or 'sin transportista'
            pendiente = 'no'
            if picking.mapped('backorder_ids'):
                pendiente = 'crea pedido pendiente'
            elif pp == 'no' and any(m.state == 'cancel' for m in picking.mapped('move_lines')):
                pendiente = 'cancela lo que falta'
            _logger.info(
                'TUCTUC Preparación validar %s [%s]: %s en %d ms (comprobaciones %s, validar %s, tarea %s, estado %d ms); '
                'asistente de pedido pendiente: %s%s',
                picking.display_name if picking else '-', transportistas, res.get('que') or '-',
                int((t2 - t0) * 1000), tiempos.get('comprobaciones', '-'), tiempos.get('validar', '-'),
                tiempos.get('tarea', '-'), int((t2 - t1) * 1000), pendiente,
                ' (con caja automática)' if tiempos.get('caja_auto') else '')
        except Exception:
            _logger.exception('TUCTUC Preparación: no se ha podido apuntar el tiempo de validar')
