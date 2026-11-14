# -*- coding: utf-8 -*-
import datetime
import json
import logging
import re

import pytz
import werkzeug.utils

from odoo import fields, http
from odoo.http import request
from odoo.modules.module import load_information_from_description_file

_logger = logging.getLogger(__name__)


COMPANY_ID = 8  # EFFECTIVE LOGISTICS, S.L.
LINE_RE = re.compile(r'\bL(\d{1,3})\b', re.IGNORECASE)
POSITION_RE = re.compile(r'\bP(\d{1,3})\b', re.IGNORECASE)
LEVEL_RE = re.compile(r'\bC([1-4])\b', re.IGNORECASE)
PLANNER = '/koroshi_warehouse_map/static/src/html/warehouse_planner_20261029_v1.html'
DELTA_MAX_MIN = 10      # v.45: un 'since' mas viejo que esto = foto completa (para quitar lo que ya no esta)
JSON_HDR = [('Content-Type', 'application/json; charset=utf-8'), ('Cache-Control', 'no-store')]


def _json(valor, status=200):
    return request.make_response(json.dumps(valor, default=str, ensure_ascii=False), status=status,
                                 headers=JSON_HDR)


class KoroshiWarehouseMapController(http.Controller):
    """Endpoints de lectura para la vista operativa del mapa.

    Esta primera versión no modifica albaranes, movimientos ni stock. Lee las
    sesiones propias del módulo y, si todavía no hay sesiones de PDA, muestra
    una aproximación basada en las OUT activas de Odoo.
    """

    def _company(self):
        company = request.env['res.company'].sudo().browse(COMPANY_ID).exists()
        return company or request.env.user.company_id

    def _time(self, value):
        if not value:
            return ''
        local = fields.Datetime.context_timestamp(request.env.user, value)
        # Los segundos son necesarios para medir el tiempo activo entre el
        # primer artículo validado y el último escaneo sin confundirlo con la
        # hora en la que Odoo creó automáticamente la OUT.
        return local.strftime('%H:%M:%S')

    def _carrier_values(self, picking):
        """Devuelve transportista y tracking sin romper instalaciones heredadas."""
        carrier = self._field(picking, 'carrier_id')
        return {
            'carrier': self._field(carrier, 'name', '') or '',
            'tracking': self._field(picking, 'carrier_tracking_ref', '') or '',
        }

    def _location_parts(self, value):
        value = value or ''
        line = LINE_RE.search(value)
        position = POSITION_RE.search(value)
        level = LEVEL_RE.search(value)
        return (
            line.group(0).upper() if line else '',
            position.group(0).upper() if position else '',
            ('C' + level.group(1)) if level else '',
        )

    def _marker(self, key, location, index):
        line, position, level = self._location_parts(location)
        line_number = int(line[1:]) if line else 0
        position_number = int(position[1:]) if position else 0
        if line_number:
            x = 10 + ((line_number - 1) % 16) * 5.2
            y = 22 + ((line_number - 1) // 16) * 9
        else:
            x = 18 + (index * 17) % 68
            y = 25 + (index * 23) % 58
        return {
            'x': min(max(round(x, 1), 7), 93),
            'y': min(max(round(y, 1), 12), 88),
            'line': line,
            'position': position,
            'level': level,
            'position_number': position_number,
            'key': key,
        }

    def _session_row(self, session, index):
        picking = session.picking_id
        metrics = self._picking_metrics(picking)
        lines = self._picking_lines(picking)
        if not lines:
            lines = self._event_lines(session)
        location = session.last_location or session.last_line or ''
        marker = self._marker(session.id, location, index)
        state = session.state
        status = {
            'picking': 'En picking',
            'paused': 'En pausa',
            'done': 'Finalizado',
            'cancelled': 'Cancelado',
        }.get(state, 'Sin empezar')
        timeline = []
        scan_events = session.event_ids.filtered(
            lambda event: event.event_type in ('pick', 'scan') and event.occurred_at
        ).sorted(key=lambda item: item.occurred_at)
        first_scan = scan_events[:1].occurred_at if scan_events else session.started_at
        last_scan = scan_events[-1:].occurred_at if scan_events else session.last_scan_at
        for event in session.event_ids.sorted(
                key=lambda item: item.occurred_at or datetime.datetime.min)[-8:]:
            timeline.append([
                self._time(event.occurred_at),
                dict(self.env_event_types()).get(event.event_type, event.event_type),
                event.location or session.last_location or '',
            ])
        return {
            'id': 'session-%s' % session.id,
            'initials': (session.operator_name or session.user_id.name or 'PDA')[:2].upper(),
            'name': session.operator_name or session.user_id.name or 'PDA sin asignar',
            'pda': session.pda_code or 'PDA —',
            'out': session.out_reference or (picking.name if picking else session.name),
            'status': status,
            'location': location or 'Sin ubicación',
            'start': self._time(session.started_at),
            'firstPickAt': self._time(first_scan),
            'lastPick': location or '—',
            'lastAt': self._time(last_scan),
            'lastScanAt': self._time(last_scan),
            'finish': self._time(session.finished_at) or '—',
            'units': metrics['units'],
            'demand': metrics['demand'],
            'boxes': metrics['boxes'],
            'sourceLineCount': metrics['line_count'],
            'lines': lines,
            'progress': round(session.progress or 0.0),
            'picks': session.pick_count or 0,
            'x': marker['x'],
            'y': marker['y'],
            'color': self._color(state),
            'timeline': timeline,
            'source': session.source or 'pda',
            'carrier': self._carrier_values(picking)['carrier'],
            'tracking': self._carrier_values(picking)['tracking'],
            'missing': metrics['missing'],
            'incidents': [],
        }

    def env_event_types(self):
        return {
            'start': 'Inicio del OUT',
            'pick': 'Pick confirmado',
            'pause': 'Pausa detectada',
            'resume': 'Reanudación',
            'finish': 'OUT finalizado',
            'scan': 'Último escaneo',
        }

    def _color(self, state):
        return {
            'picking': '#22c55e',
            'paused': '#ffd040',
            'done': '#8ab8d8',
            'cancelled': '#f87171',
        }.get(state, '#4da8ff')

    def _picking_metrics(self, picking):
        """Resumen seguro para el mapa: demanda, hecho, líneas y cajas."""
        if not picking:
            return {
                'demand': 0.0,
                'units': 0.0,
                'line_count': 0,
                'boxes': 0,
                'missing': 0.0,
            }
        # Odoo 13 usa `move_lines` en stock.picking. Algunas instalaciones
        # tienen además `move_ids` por módulos heredados, por eso se acepta
        # cualquiera de los dos nombres y se evita que el endpoint falle con
        # AttributeError cuando el campo no existe.
        moves = self._field(picking, 'move_ids') or self._field(picking, 'move_lines')
        if moves is None:
            moves = request.env['stock.move'].sudo().browse()
        move_lines = self._field(picking, 'move_line_ids')
        if move_lines is None:
            move_lines = request.env['stock.move.line'].sudo().search([
                ('move_id', 'in', moves.ids),
            ]) if moves else request.env['stock.move.line'].sudo().browse()
        demand = sum(float(self._field(move, 'product_uom_qty', 0.0) or 0.0)
                     for move in moves)
        units = sum(float(self._field(move, 'quantity_done', 0.0) or 0.0)
                    for move in moves)
        # En Odoo 13 la cantidad hecha puede vivir solo en stock.move.line.
        if not units and move_lines:
            units = sum(float(self._field(line, 'qty_done', 0.0) or 0.0)
                        for line in move_lines)
        try:
            packages = move_lines.mapped('result_package_id').filtered(
                lambda package: package)
        except (AttributeError, KeyError):
            packages = request.env['stock.quant.package'].sudo().browse()
        return {
            'demand': demand,
            'units': units,
            'line_count': len(move_lines) or len(moves),
            'boxes': len(packages),
            'missing': max(0.0, demand - units),
        }

    @staticmethod
    def _field(record, name, default=None):
        """Lee un campo opcional sin romper el endpoint entre versiones Odoo."""
        try:
            return getattr(record, name)
        except (AttributeError, KeyError):
            return default

    def _picking_lines(self, picking):
        """Devuelve todas las ubicaciones físicas de una OUT.

        El mapa no debe recibir únicamente la última ``stock.move.line``:
        esa era la razón por la que muchas OUT aparecían con ``1 ubicación``.
        Se envía una línea ligera por cada movimiento, con su ubicación de
        origen, referencia/EAN y cantidades prevista y realizada. El orden
        sigue siendo responsabilidad del mapa (optimizado por ubicación si
        Odoo no entrega una secuencia real de escaneo).
        """
        if not picking:
            return []
        moves = self._field(picking, 'move_ids') or self._field(picking, 'move_lines')
        if moves is None:
            moves = request.env['stock.move'].sudo().browse()
        move_lines = self._field(picking, 'move_line_ids')
        if move_lines is None:
            move_lines = request.env['stock.move.line'].sudo().search([
                ('move_id', 'in', moves.ids),
            ]) if moves else request.env['stock.move.line'].sudo().browse()
        result = []
        # Una OUT excepcionalmente grande no debe bloquear la vista operativa.
        # El contador total sigue saliendo de _picking_metrics; aquí solo se
        # limita el detalle que se pinta en el mapa.
        ordered_lines = move_lines.sorted(
            key=lambda item: (self._field(item, 'write_date', '') or '', item.id)
        )
        for line in ordered_lines[:2000]:
            location_obj = self._field(line, 'location_id')
            location = (
                self._field(location_obj, 'complete_name', '') or
                self._field(location_obj, 'name', '') or ''
            )
            if not location:
                continue
            product = self._field(line, 'product_id')
            move = self._field(line, 'move_id')
            reference = (
                self._field(product, 'default_code', '') or
                self._field(product, 'display_name', '') or
                self._field(product, 'name', '') or ''
            )
            barcode = self._field(product, 'barcode', '') or ''
            done = float(self._field(line, 'qty_done', 0.0) or 0.0)
            demand = self._field(line, 'product_uom_qty', None)
            if demand is None:
                demand = self._field(line, 'product_qty', None)
            if demand is None:
                demand = self._field(move, 'product_uom_qty', 0.0)
            result.append({
                'source_id': line.id,
                'scan_time': self._time(self._field(line, 'write_date')) if done else '',
                'location': location,
                'reference': reference,
                'ean': barcode,
                'qty': float(demand or 0.0),
                'done': done,
                'quantity': done,
                'missing': max(0.0, float(demand or 0.0) - done),
            })
        return result

    def _event_lines(self, session):
        """Fallback de ubicaciones procedentes de eventos de la PDA."""
        result = []
        for event in session.event_ids.sorted(
                key=lambda item: item.occurred_at or datetime.datetime.min):
            if event.event_type not in ('pick', 'scan') or not event.location:
                continue
            product = self._field(event, 'product_id')
            result.append({
                'source_id': event.id,
                'location': event.location,
                'reference': (
                    self._field(product, 'default_code', '') or
                    self._field(product, 'display_name', '') or ''
                ),
                'ean': self._field(product, 'barcode', '') or '',
                'qty': float(event.quantity or 0.0),
                'done': float(event.quantity or 0.0),
                'quantity': float(event.quantity or 0.0),
            })
        return result

    def _picking_row(self, picking, index):
        move_line_domain = [('picking_id', '=', picking.id), ('qty_done', '>', 0)]
        move_count = request.env['stock.move.line'].sudo().search_count(move_line_domain)
        all_done_lines = request.env['stock.move.line'].sudo().search(
            move_line_domain, order='write_date asc, id asc',
        )
        first_line = all_done_lines[:1]
        last_line = all_done_lines[-1:] if all_done_lines else all_done_lines
        location = ''
        first_at = None
        last_at = None
        if first_line:
            first_at = first_line.write_date
        if last_line:
            location = last_line.location_id.complete_name or last_line.location_id.name or ''
            last_at = last_line.write_date
        metrics = self._picking_metrics(picking)
        lines = self._picking_lines(picking)
        total = metrics['demand']
        done = metrics['units']
        progress = (done / total * 100.0) if total else 0.0
        state = 'done' if picking.state == 'done' else (
            'picking' if picking.state in ('assigned', 'confirmed', 'partially_available') else 'draft'
        )
        marker = self._marker(picking.id, location, index)
        responsible = getattr(picking, 'user_id', False)
        name = responsible.name if responsible else 'OUT sin persona asignada'
        carrier = self._carrier_values(picking)
        return {
            'id': 'picking-%s' % picking.id,
            'initials': name[:2].upper(),
            'name': name,
            'pda': 'Odoo',
            'out': picking.name,
            'status': {'picking': 'En picking', 'done': 'Finalizado'}.get(state, 'Sin empezar'),
            'location': location or 'Sin escaneo',
            'start': self._time(picking.date),
            'firstPickAt': self._time(first_at),
            'lastPick': location or '—',
            'lastAt': self._time(last_at),
            'lastScanAt': self._time(last_at),
            'finish': self._time(picking.date_done) or '—',
            'units': metrics['units'],
            'demand': metrics['demand'],
            'boxes': metrics['boxes'],
            'sourceLineCount': metrics['line_count'],
            'lines': lines,
            'progress': round(progress),
            'picks': move_count,
            'x': marker['x'],
            'y': marker['y'],
            'color': self._color(state),
            'timeline': [],
            'source': 'odoo',
            'carrier': carrier['carrier'],
            'tracking': carrier['tracking'],
            'missing': metrics['missing'],
            'incidents': [],
        }

    def _zone_rows(self, company):
        """Devuelve únicamente las zonas internas creadas hoy.

        El proceso de zonas de KOROSHI crea albaranes internos con un origen
        ``KOR-ddmm-*``. Usamos ese contrato real de Odoo, en vez de inventar
        rectángulos en el navegador. Así el mapa aparece vacío al entrar y
        solo dibuja una zona cuando existe el picking interno correspondiente.
        """
        Picking = request.env['stock.picking'].sudo()
        now_local = fields.Datetime.context_timestamp(
            request.env.user, fields.Datetime.now())
        day_token = now_local.strftime('%d%m')
        pickings = Picking.search([
            ('company_id', '=', company.id),
            ('picking_type_code', '=', 'internal'),
            ('state', '!=', 'cancel'),
            ('origin', '=like', 'KOR-%s-%%' % day_token),
        ], order='create_date asc, id asc', limit=200)
        result = []
        state_labels = {
            'draft': 'Pendiente',
            'waiting': 'Esperando reserva',
            'confirmed': 'Confirmada',
            'assigned': 'Reservada',
            'partially_available': 'Parcial',
            'done': 'Finalizada',
            'cancel': 'Cancelada',
        }
        for picking in pickings:
            created = self._field(picking, 'create_date')
            if created:
                created_local = fields.Datetime.context_timestamp(
                    request.env.user, created)
                if created_local.date() != now_local.date():
                    continue
            moves = self._field(picking, 'move_ids') or self._field(
                picking, 'move_lines')
            if moves is None:
                moves = request.env['stock.move'].sudo().browse()
            move_lines = self._field(picking, 'move_line_ids')
            if move_lines is None:
                move_lines = request.env['stock.move.line'].sudo().search([
                    ('move_id', 'in', moves.ids),
                ]) if moves else request.env['stock.move.line'].sudo().browse()
            locations = set()
            line_numbers = []
            demand = 0.0
            done = 0.0
            for line in move_lines:
                location_obj = self._field(line, 'location_id')
                location = (
                    self._field(location_obj, 'complete_name', '') or
                    self._field(location_obj, 'name', '') or ''
                )
                if location:
                    locations.add(location)
                    match = LINE_RE.search(location)
                    if match:
                        line_numbers.append(int(match.group(1)))
                qty = self._field(line, 'product_uom_qty', None)
                if qty is None:
                    qty = self._field(line, 'product_qty', 0.0)
                demand += float(qty or 0.0)
                done += float(self._field(line, 'qty_done', 0.0) or 0.0)
            if not move_lines:
                for move in moves:
                    location_obj = self._field(move, 'location_id')
                    location = (
                        self._field(location_obj, 'complete_name', '') or
                        self._field(location_obj, 'name', '') or ''
                    )
                    if location:
                        locations.add(location)
                        match = LINE_RE.search(location)
                        if match:
                            line_numbers.append(int(match.group(1)))
                    demand += float(self._field(move, 'product_uom_qty', 0.0) or 0.0)
            origin = self._field(picking, 'origin', '') or picking.name
            state = self._field(picking, 'state', 'draft')
            result.append({
                'id': 'zone-%s' % picking.id,
                'picking_id': picking.id,
                'name': origin,
                'code': origin,
                'state': state,
                'status': state_labels.get(state, state),
                'units': done,
                'demand': demand,
                'line_count': len(move_lines) or len(moves),
                'location_count': len(locations),
                'line_start': min(line_numbers) if line_numbers else 0,
                'line_end': max(line_numbers) if line_numbers else 0,
                'created_at': self._time(created) if created else '',
            })
        return result

    @http.route('/koroshi_warehouse_map/layout/save', type='http', auth='user',
                methods=['POST'], csrf=False)
    def save_layout(self, **kwargs):
        """Guarda un layout en las tablas propias del módulo.

        No toca el plano base ni ninguna tabla de stock. El navegador sigue
        guardando localmente para no perder el trabajo si la red falla y, si
        la sesión de Odoo está disponible, deja una copia en koroshi.layout.
        """
        try:
            raw = request.httprequest.get_data(as_text=True) or '{}'
            values = json.loads(raw)
            if not isinstance(values, dict):
                raise ValueError('Formato de layout no válido')
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            return request.make_response(
                json.dumps({'ok': False, 'error': str(error)}),
                status=400,
                headers=[('Content-Type', 'application/json; charset=utf-8')],
            )
        data = values.get('data') or {}
        if not isinstance(data, dict):
            return request.make_response(
                json.dumps({'ok': False, 'error': 'Los datos deben ser un objeto JSON'}),
                status=400,
                headers=[('Content-Type', 'application/json; charset=utf-8')],
            )
        company = self._company()
        name = str(values.get('name') or 'Diseño NAU-2')[:120]
        # v.45 (auditoria 13/11, fase 4): fields.Datetime.now() es un datetime: el .replace('-', '') de antes
        # fallaba SIEMPRE y el plano no se guardaba nunca (0 registros en koroshi.layout el 14/11). Con microsegundos
        # para que dos publicaciones en el mismo segundo no choquen con la restriccion unica del codigo.
        stamp = fields.Datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        try:
            layout = request.env['koroshi.layout'].sudo().create({
                'name': name,
                'code': 'NAU2-%s-%s' % (request.env.user.id, stamp),
                'company_id': company.id,
                'source_version': 'NAU-2 · 2026-10-29',
                'map_json': json.dumps(data, ensure_ascii=False),
            })
        except Exception as error:
            # v.45: el error de verdad al navegador (antes solo «No se pudo publicar ahora»)
            _logger.exception('KOROSHI Mapa: no se ha podido guardar el plano «%s»', name)
            request.env.cr.rollback()
            return _json({'ok': False, 'error': 'No se ha guardado: %s' % error}, status=500)
        return _json({'ok': True, 'layout_id': layout.id, 'name': layout.name})

    @http.route('/koroshi_warehouse_map/layout/load', type='http', auth='user', methods=['GET'], csrf=False)
    def load_layout(self, layout_id=None, **kwargs):
        """v.45: sin layout_id, la lista de planos guardados (los 20 ultimos); con layout_id, ese plano (data =
        lo mismo que se publico: pallets y linealEdits). Solo lee."""
        Layout = request.env['koroshi.layout'].sudo()
        company = self._company()
        if not layout_id:
            planos = Layout.search([('company_id', '=', company.id)], order='id desc', limit=20)
            return _json({'ok': True, 'layouts': [{
                'id': l.id, 'name': l.name, 'code': l.code,
                'created_at': fields.Datetime.context_timestamp(request.env.user, l.create_date).strftime(
                    '%d/%m/%Y %H:%M') if l.create_date else '',
                'user': l.create_uid.name or ''} for l in planos]})
        try:
            plano = Layout.browse(int(layout_id)).exists()
        except (TypeError, ValueError):
            plano = Layout.browse()
        if not plano or plano.company_id != company:
            return _json({'ok': False, 'error': 'No existe el plano %s' % layout_id}, status=404)
        try:
            data = json.loads(plano.map_json or '{}')
        except ValueError as error:
            return _json({'ok': False, 'error': 'El plano %s tiene el JSON roto: %s' % (plano.name, error)}, status=500)
        return _json({'ok': True, 'id': plano.id, 'name': plano.name, 'data': data})

    @http.route('/koroshi_warehouse_map/planner', type='http', auth='user', methods=['GET'], csrf=False)
    def planner(self, mode=None, **kwargs):
        """v.45: abre el plano con ?v=<version del manifest> para que el navegador coja siempre el de la version
        instalada (antes el ?v= estaba escrito a mano en el JS y se quedaba atrasado)."""
        try:
            version = load_information_from_description_file('koroshi_warehouse_map').get('version') or ''
        except Exception:
            version = ''
        url = '%s?v=%s' % (PLANNER, version.replace('13.0.', ''))
        if mode == 'ops':
            url += '&mode=ops'
        respuesta = werkzeug.utils.redirect(url, 302)
        respuesta.headers['Cache-Control'] = 'no-store'
        return respuesta

    @http.route('/koroshi_warehouse_map/data', type='http', auth='user',
                methods=['GET'], csrf=False)
    def data(self, since=None, **kwargs):
        company = self._company()
        ahora = fields.Datetime.now()
        now_local = fields.Datetime.context_timestamp(request.env.user, ahora)
        # v.45 (auditoria 13/11, fase 4): se respeta 'since' (hora del servidor, UTC, la que devuelve server_time):
        # solo lo que ha cambiado desde entonces, con 5 s de margen. Sin since, o mas viejo que DELTA_MAX_MIN, foto
        # completa (asi lo que ya no esta desaparece del mapa).
        desde = None
        if since:
            try:
                desde = fields.Datetime.from_string(since) - datetime.timedelta(seconds=5)
            except (TypeError, ValueError):
                desde = None
            if desde and (ahora - desde).total_seconds() > DELTA_MAX_MIN * 60:
                desde = None
        Session = request.env['koroshi.pick.session'].sudo()
        dom_sesion = [('company_id', '=', company.id), ('active', '=', True)]
        sessions = Session.search(dom_sesion, limit=200)
        if sessions and desde:
            sessions = sessions.filtered(lambda x: x.write_date and x.write_date >= desde)
        if sessions or (desde and Session.search_count(dom_sesion)):
            people = [self._session_row(session, index)
                      for index, session in enumerate(sessions)]
            source = 'ODOO · sesiones PDA'
        else:
            Picking = request.env['stock.picking'].sudo()
            # v.45: el inicio del dia en hora local pasado a UTC (write_date esta en UTC; antes se comparaba la
            # medianoche local tal cual: 1-2 horas de desfase)
            tz = pytz.timezone(request.env.user.tz or 'Europe/Madrid')
            day_start = tz.localize(datetime.datetime.combine(now_local.date(), datetime.time.min)).astimezone(
                pytz.utc).replace(tzinfo=None)
            # Most OUTs se crean de noche y pasan a reserva después. Se
            # incluyen las activas y las modificadas desde el inicio del día,
            # sin llenar el mapa con históricos cancelados.
            dominio = [
                ('company_id', '=', company.id),
                ('picking_type_code', '=', 'outgoing'),
                ('state', 'not in', ('cancel',)),
                '|',
                ('state', 'in', ('assigned', 'confirmed', 'partially_available', 'done')),
                ('write_date', '>=', fields.Datetime.to_string(day_start)),
            ]
            if desde:
                # v.45: lo que ha cambiado: la OUT o alguna de sus lineas (leer no toca la OUT, solo la linea)
                dominio += ['|', ('write_date', '>=', fields.Datetime.to_string(desde)),
                            ('move_line_ids.write_date', '>=', fields.Datetime.to_string(desde))]
            pickings = Picking.search(dominio, order='write_date desc, id desc', limit=200)
            people = [self._picking_row(picking, index)
                      for index, picking in enumerate(pickings)]
            source = 'ODOO · OUTs'
        payload = {
            'ok': True,
            'source': source,
            'updated_at': ahora,
            'server_time': fields.Datetime.to_string(ahora),     # v.45: lo que hay que mandar como 'since'
            'delta': bool(desde),
            'company_id': company.id,
            'zones': self._zone_rows(company),
            'as_of_date': now_local.strftime('%Y-%m-%d'),
            'refresh_after_seconds': 60,
        }
        # v.45: la foto completa va en 'people' (el mapa la cambia entera); los cambios, en 'records' (el mapa los
        # junta con lo que ya tiene)
        payload['records' if desde else 'people'] = people
        return _json(payload)
