# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Preparación en Lecturas (v3.0.0, v3.5 estado ligero) - rutas JSON de la pantalla de la PDA.
# Toda la lógica está en models/lectura.py. Las respuestas llevan siempre 'ok' y, si hay OUT, su 'estado'.
# v3.15: con lote_id (en vez de picking_id) las rutas trabajan con la agrupación Z- entera (models/agrupacion.py).
# v3.29: todo lo que la PDA manda con id_lectura y Odoo no acepta queda apuntado (con diferida=True si venía de la
# cola de la PDA). Mover, deshacer y validar llevan también id_lectura: si la PDA reintenta, no se hace dos veces.
# v3.34: lo pendiente se escribe en la base de datos ANTES de calcular el estado y fuera de su try (R5); /validar deja
# una línea en el log con los ms de cada tramo y el transportista (R6).
# =============================================================================
import logging
import time

from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

from ..models.lectura import Ocupada

_logger = logging.getLogger(__name__)


def _msg(e):
    return getattr(e, 'name', False) or str(e)


class KoroshiPreparacion(http.Controller):

    def _lectura(self, diferida=False):
        L = request.env['koroshi.preparacion.lectura']
        return L.with_context(kp_diferida=True) if diferida else L   # v3.29

    def _agrupacion(self, diferida=False):
        A = request.env['koroshi.preparacion.agrupacion'].con_memo()   # v3.29: las OUT vivas, una vez por petición
        return A.with_context(kp_diferida=True) if diferida else A

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

    def _con_estado(self, picking, res, employee=None, ligero=False, lote=None, agrupacion=None):
        # v3.34 (R5): lo leído se escribe aquí, fuera del try. Antes se escribía al calcular el estado, dentro del try:
        # si la escritura fallaba (dos PDA a la vez en la misma línea), el error se tragaba, la PDA recibía «ok» y no
        # se guardaba nada. Ahora el error sale: Odoo repite la petición o la PDA la reintenta con el mismo id.
        request.env['stock.move.line'].flush()
        try:
            if lote:
                lote.invalidate_cache()
                res['estado'] = (agrupacion or self._agrupacion()).estado(lote, employee, ligero=ligero)   # v3.15
                return res
            picking.invalidate_cache()
            # v3.3: el ayudante ve las líneas al revés; v3.5: tras leer / deshacer, estado ligero
            res['estado'] = self._lectura().estado(picking, employee, ligero=ligero)
        except Exception:  # el estado es para pintar: nunca rompe la respuesta (v3.29: pero queda en el log)
            _logger.exception('KOROSHI Preparación: no se ha podido calcular el estado de %s',
                              (lote or picking).display_name if (lote or picking) else '-')
        return res

    def _cerrada(self, picking, lote, res):
        """v3.29: la OUT (o la agrupación) ya está hecha o cancelada: la PDA no se queda esperando con lo de la cola."""
        if res.get('ok') or res.get('que') in ('repetida', 'ocupada', 'validada'):
            return res
        if lote is not None:
            if lote and not lote.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel')):
                res['que'] = 'out_cerrada'
        elif picking and picking.state in ('done', 'cancel'):
            res['que'] = 'out_cerrada'
        return res

    def _rechazo(self, Lectura, picking, emp, tipo, codigo, id_lectura, res):
        """v3.29: lo que no se ha aceptado, apuntado siempre (si la lógica no lo ha apuntado ya)."""
        if not res.get('ok') and id_lectura and res.get('que') not in ('ocupada', 'repetida'):
            Lectura.apuntar_rechazo(picking, emp, tipo, codigo, res.get('msg') or '', id_lectura)
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
             diferida=False, **kw):
        lote = self._lote(lote_id) if lote_id else None
        picking = None if lote_id else self._picking(picking_id)
        emp = self._empleado(employee_id)
        Lectura = self._lectura(diferida)
        Agrupacion = self._agrupacion(diferida)
        try:
            if lote_id:
                res = Agrupacion.leer(lote, emp, codigo, id_lectura, linea_id)
            else:
                res = Lectura.leer(picking, emp, codigo, id_lectura)
        except Ocupada as e:
            # v3.6: la PDA lo vuelve a mandar en un momento (mismo id_lectura): no se pierde
            return {'ok': False, 'que': 'ocupada', 'msg': _msg(e)}
        except (UserError, ValidationError) as e:
            res = {'ok': False, 'msg': _msg(e)}
        self._rechazo(Lectura, picking, emp, 'leer', codigo, id_lectura, self._cerrada(picking, lote, res))
        return self._con_estado(picking, res, emp, ligero=True, lote=lote, agrupacion=Agrupacion)

    @http.route('/koroshi/preparacion/deshacer', type='json', auth='user')
    def deshacer(self, picking_id=False, employee_id=False, lote_id=False, id_lectura=False, **kw):
        lote = self._lote(lote_id) if lote_id else None
        picking = None if lote_id else self._picking(picking_id)
        emp = self._empleado(employee_id)
        Agrupacion = self._agrupacion()
        try:
            if lote_id:
                res = Agrupacion.deshacer(lote, emp, id_lectura)
            else:
                res = self._lectura().deshacer(picking, emp, id_lectura)   # v3.29: con id_lectura
        except Ocupada as e:
            # v3.6: la PDA lo vuelve a mandar en un momento (mismo id_lectura): no se pierde
            return {'ok': False, 'que': 'ocupada', 'msg': _msg(e)}
        except (UserError, ValidationError) as e:
            res = {'ok': False, 'msg': _msg(e)}
        self._cerrada(picking, lote, res)
        return self._con_estado(picking, res, emp, ligero=True, lote=lote, agrupacion=Agrupacion)

    @http.route('/koroshi/preparacion/caja', type='json', auth='user')
    def caja(self, picking_id=False, codigo='', employee_id=False, id_lectura=False, lote_id=False, out_id=False,
             tipo_caja=False, diferida=False, **kw):
        lote = self._lote(lote_id) if lote_id else None
        picking = None if lote_id else self._picking(picking_id)
        emp = self._empleado(employee_id)
        Lectura = self._lectura(diferida)
        Agrupacion = self._agrupacion(diferida)
        try:
            if lote_id:
                res = Agrupacion.caja(lote, emp, codigo, id_lectura, out_id, tipo_caja)
            else:
                res = Lectura.caja(picking, emp, codigo, id_lectura, tipo_caja)   # v3.24
        except Ocupada as e:
            # v3.6: la PDA lo vuelve a mandar en un momento (mismo id_lectura): no se pierde
            return {'ok': False, 'que': 'ocupada', 'msg': _msg(e)}
        except (UserError, ValidationError) as e:
            res = {'ok': False, 'msg': _msg(e)}
        self._rechazo(Lectura, picking, emp, 'caja', codigo, id_lectura, self._cerrada(picking, lote, res))
        return self._con_estado(picking, res, emp, lote=lote, agrupacion=Agrupacion)

    @http.route('/koroshi/preparacion/cantidad', type='json', auth='user')
    def cantidad(self, picking_id=False, linea_id=False, cantidad=0, employee_id=False, id_lectura=False, lote_id=False,
                 diferida=False, **kw):
        """v3.7: n uds de golpe en una línea ya comprobada con la pistola."""
        lote = self._lote(lote_id) if lote_id else None
        picking = None if lote_id else self._picking(picking_id)
        emp = self._empleado(employee_id)
        Lectura = self._lectura(diferida)
        Agrupacion = self._agrupacion(diferida)
        try:
            if lote_id:
                res = Agrupacion.poner_cantidad(lote, emp, linea_id, cantidad, id_lectura)
            else:
                res = Lectura.poner_cantidad(picking, emp, linea_id, cantidad, id_lectura)
        except Ocupada as e:
            return {'ok': False, 'que': 'ocupada', 'msg': _msg(e)}
        except (UserError, ValidationError) as e:
            res = {'ok': False, 'msg': _msg(e)}
        self._rechazo(Lectura, picking, emp, 'leer', 'A MANO +%s' % (cantidad or 0), id_lectura,
                      self._cerrada(picking, lote, res))
        return self._con_estado(picking, res, emp, ligero=True, lote=lote, agrupacion=Agrupacion)

    @http.route('/koroshi/preparacion/rechazadas', type='json', auth='user')
    def rechazadas(self, picking_id=False, lote_id=False, lecturas=None, motivo='', **kw):
        """v3.29: lo de la cola de la PDA que no se ha aplicado y que Odoo no ha podido apuntar él mismo: lo que llevaba
        más de 24 h en la memoria (motivo vacío; antes se tiraba sin decir nada) o lo que dio un error de Odoo. Se
        apunta como rechazado de cola para que el encargado lo vea. lecturas = [{tipo, codigo, id, employee_id, n}].
        Si ya estaba apuntado (mismo id) no se repite."""
        picking = self._picking(picking_id) if picking_id else None
        if not picking and lote_id:
            lote = self._lote(lote_id)
            picking = lote.picking_ids[:1] if lote else None
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

    @http.route('/koroshi/preparacion/color', type='json', auth='user')
    def color(self, employee_id=False, color=False, **kw):
        """v3.21: el color de la franja de la ubicación de cada operario (leer o, con color, guardar)."""
        emp = self._empleado(employee_id)
        Pref = request.env['koroshi.preparacion.preferencia'].sudo()
        if color:
            return {'ok': True, 'color': Pref.poner_color(emp, color)}
        return {'ok': True, 'color': Pref.color_de(emp)}

    @http.route('/koroshi/preparacion/mover_caja', type='json', auth='user')
    def mover_caja(self, picking_id=False, linea_id=False, cantidad=1, destino='', employee_id=False, id_lectura=False,
                   **kw):
        """v3.21: pasar uds de una caja cerrada a otra caja de la OUT (o a una nueva). v3.29: con id_lectura."""
        picking = self._picking(picking_id)
        emp = self._empleado(employee_id)
        try:
            res = self._lectura().mover_caja(picking, emp, linea_id, cantidad, destino, id_lectura)
        except Ocupada as e:
            return {'ok': False, 'que': 'ocupada', 'msg': _msg(e)}
        except (UserError, ValidationError) as e:
            res = {'ok': False, 'msg': _msg(e)}
        self._cerrada(picking, None, res)
        return self._con_estado(picking, res, emp)

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

    @http.route('/koroshi/preparacion/ronda_marcar', type='json', auth='user')
    def ronda_marcar(self, picking_id=False, linea_id=False, resultado='', employee_id=False, id_lectura=False, **kw):
        """v3.33: ronda de faltantes: «No está» / «La ubicación no existe» en una línea."""
        picking = self._picking(picking_id)
        emp = self._empleado(employee_id)
        try:
            res = self._lectura().ronda_marcar(picking, emp, linea_id, resultado, id_lectura)
        except Ocupada as e:
            return {'ok': False, 'que': 'ocupada', 'msg': _msg(e)}
        except (UserError, ValidationError) as e:
            res = {'ok': False, 'msg': _msg(e)}
        return self._con_estado(picking, res, emp)

    @http.route('/koroshi/preparacion/validar', type='json', auth='user')
    def validar(self, picking_id=False, employee_id=False, pedido_pendiente=False, lote_id=False, tipo_caja=False,
                incompleto=False, id_lectura=False, **kw):
        lote = self._lote(lote_id) if lote_id else None
        picking = None if lote_id else self._picking(picking_id)
        emp = self._empleado(employee_id)
        pp = pedido_pendiente if pedido_pendiente in ('si', 'no') else None
        Agrupacion = self._agrupacion()
        t0 = time.monotonic()
        try:
            if lote_id:
                res = Agrupacion.validar(lote, emp, pp)
            else:
                res = self._lectura().validar(picking, emp, pp, tipo_caja, bool(incompleto), id_lectura)   # v3.29
        except Ocupada as e:
            # v3.29: otra petición está validando (la misma PDA que reintenta u otra): se vuelve a probar
            return {'ok': False, 'que': 'ocupada', 'msg': _msg(e)}
        except (UserError, ValidationError) as e:
            res = {'ok': False, 'que': 'no_validada', 'msg': _msg(e)}
        t1 = time.monotonic()
        tiempos = res.pop('_tiempos', None) or {}
        res = self._con_estado(picking, res, emp, lote=lote, agrupacion=Agrupacion)
        self._log_validar(picking, lote, pp, res, tiempos, t0, t1)
        return res

    def _log_validar(self, picking, lote, pp, res, tiempos, t0, t1):
        """v3.34 (R6): una línea por validación con los ms de cada tramo, para saber dónde se van los 30-50 s. Sin
        optimizar nada: con una semana de log se decide (p. ej. si XPO/S4T van a una cola). Nunca rompe la respuesta."""
        try:
            t2 = time.monotonic()
            pickings = lote.picking_ids if lote else picking
            transportistas = ', '.join(sorted(set(pickings.mapped('carrier_id.name')))) or 'sin transportista'
            pendiente = 'no'
            if pickings.mapped('backorder_ids'):
                pendiente = 'crea pedido pendiente'
            elif pp == 'no' and any(m.state == 'cancel' for m in pickings.mapped('move_lines')):
                pendiente = 'cancela lo que falta'
            _logger.info(
                'KOROSHI Preparación validar %s [%s]: %s en %d ms (comprobaciones %s, validar %s, tarea %s, estado %d ms); '
                'asistente de pedido pendiente: %s%s',
                (lote or picking).display_name if (lote or picking) else '-', transportistas, res.get('que') or '-',
                int((t2 - t0) * 1000), tiempos.get('comprobaciones', '-'), tiempos.get('validar', '-'),
                tiempos.get('tarea', '-'), int((t2 - t1) * 1000), pendiente,
                ' (con caja sola Zalando/About You)' if tiempos.get('caja_auto') else '')
        except Exception:
            _logger.exception('KOROSHI Preparación: no se ha podido apuntar el tiempo de validar')
