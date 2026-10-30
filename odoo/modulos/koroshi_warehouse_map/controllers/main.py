# -*- coding: utf-8 -*-
import datetime
import json
import re

from odoo import fields, http
from odoo.http import request


COMPANY_ID = 8  # EFFECTIVE LOGISTICS, S.L.
LINE_RE = re.compile(r'\bL(\d{1,3})\b', re.IGNORECASE)
POSITION_RE = re.compile(r'\bP(\d{1,3})\b', re.IGNORECASE)
LEVEL_RE = re.compile(r'\bC([1-4])\b', re.IGNORECASE)


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
        return local.strftime('%H:%M')

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
            'firstPickAt': self._time(session.started_at),
            'lastPick': location or '—',
            'lastAt': self._time(session.last_scan_at),
            'lastScanAt': self._time(session.last_scan_at),
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
            return {'demand': 0.0, 'units': 0.0, 'line_count': 0, 'boxes': 0}
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
        for line in move_lines[:2000]:
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
                'location': location,
                'reference': reference,
                'ean': barcode,
                'qty': float(demand or 0.0),
                'done': done,
                'quantity': done,
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
        move_lines = request.env['stock.move.line'].sudo().search(
            move_line_domain,
            order='write_date desc, id desc', limit=1,
        )
        last_line = move_lines[:1]
        location = ''
        last_at = None
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
        return {
            'id': 'picking-%s' % picking.id,
            'initials': name[:2].upper(),
            'name': name,
            'pda': 'Odoo',
            'out': picking.name,
            'status': {'picking': 'En picking', 'done': 'Finalizado'}.get(state, 'Sin empezar'),
            'location': location or 'Sin escaneo',
            'start': self._time(picking.date),
            'firstPickAt': '',
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
        }

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
        stamp = fields.Datetime.now().replace('-', '').replace(':', '').replace(' ', '_')
        layout = request.env['koroshi.layout'].sudo().create({
            'name': name,
            'code': 'NAU2-%s-%s' % (request.env.user.id, stamp),
            'company_id': company.id,
            'source_version': 'NAU-2 · 2026-10-29',
            'map_json': json.dumps(data, ensure_ascii=False),
        })
        body = json.dumps({'ok': True, 'layout_id': layout.id, 'name': layout.name},
                          ensure_ascii=False)
        return request.make_response(body, headers=[
            ('Content-Type', 'application/json; charset=utf-8'),
            ('Cache-Control', 'no-store'),
        ])

    @http.route('/koroshi_warehouse_map/data', type='http', auth='user',
                methods=['GET'], csrf=False)
    def data(self, **kwargs):
        company = self._company()
        Session = request.env['koroshi.pick.session'].sudo()
        sessions = Session.search([
            ('company_id', '=', company.id),
            ('active', '=', True),
        ], limit=200)
        if sessions:
            people = [self._session_row(session, index)
                      for index, session in enumerate(sessions)]
            source = 'ODOO · sesiones PDA'
        else:
            Picking = request.env['stock.picking'].sudo()
            pickings = Picking.search([
                ('company_id', '=', company.id),
                ('picking_type_code', '=', 'outgoing'),
                ('state', 'not in', ('cancel',)),
            ], order='write_date desc, id desc', limit=40)
            people = [self._picking_row(picking, index)
                      for index, picking in enumerate(pickings)]
            source = 'ODOO · OUTs'
        payload = {
            'ok': True,
            'source': source,
            'updated_at': fields.Datetime.now(),
            'company_id': company.id,
            'people': people,
        }
        body = json.dumps(payload, default=str, ensure_ascii=False)
        return request.make_response(body, headers=[
            ('Content-Type', 'application/json; charset=utf-8'),
            ('Cache-Control', 'no-store'),
        ])
