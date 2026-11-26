# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Operarios v2.23.0 - Tablero del responsable por áreas (formato D). Sustituye a los cinco formatos de la
# 2.21 (tablero_formatos.py). Diseño: bin/versiones/diseno-tablero-responsable_2026-11-20_v8.md (Isaac, 20/11).
#
# Columnas = áreas (Picking, Recepciones, Compactación, Devoluciones, Inversa, Expediciones, Extra) y «Sin área»
# (quien ha trabajado hoy y ahora no está en ninguna). En Picking, una fila por zona o agrupación con trabajo, en el
# orden en que se dan (tablero.py, _lotes_por_prioridad). Solo se arrastra a Picking: persona -> zona = esa zona la
# primera de su cola (tablero_mover, por el write() del tablero con su comprobación de grupo). Las demás áreas solo se
# miran: no se asignan.
#
# En qué área está cada uno: _tablero_areas(). Por defecto se deduce de lo que hay (tarea de picking en curso,
# Contenedores en los últimos 15 min, tramo abierto del portátil de Actividades). La entrada única de la PDA
# (koroshi_actividades, otra sesión) lo sobrescribirá con el área de su tramo abierto. Solo lee, salvo
# tablero_mover (tabla propia de asignaciones). Nada en stock.*.
# =============================================================================
import datetime
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.addons.koroshi_base import comun

from .reparto import VIVAS
from .tablero import GRUPO_TABLERO

_logger = logging.getLogger(__name__)

# Orden de las columnas (la entrada única usa los mismos códigos: diseno-pda-entrada-unica_2026-11-20.md, 3.2)
AREAS = [
    ('picking', 'Picking'),
    ('recepciones', 'Recepciones'),
    ('compactacion', 'Compactación'),
    ('devoluciones', 'Devoluciones'),
    ('inversa', 'Inversa'),
    ('expediciones', 'Expediciones'),
    ('extra', 'Extra'),
]
MINUTOS_CONTENEDORES = 15   # un movimiento de Contenedores más reciente = está compactando


def _iniciales(nombre):
    partes = [p for p in (nombre or '').split() if p]
    if not partes:
        return '?'
    if len(partes) == 1:
        return partes[0][:2].upper()
    return (partes[0][0] + partes[1][0]).upper()


def area_de_actividad(nombre):
    """Área de una actividad del portátil por su nombre, hasta que koroshi.actividad tenga su campo «Área»."""
    n = (nombre or '').lower()
    if 'devoluci' in n:
        return 'devoluciones'
    if 'inversa' in n:
        return 'inversa'
    if 'recep' in n or 'descarg' in n:
        return 'recepciones'
    if 'expedic' in n or 'cargar' in n or 'camión' in n or 'camion' in n:
        return 'expediciones'
    if 'compact' in n or 'contenedor' in n:
        return 'compactacion'
    if 'picking' in n:
        return 'picking'
    return 'extra'


class KoroshiOperarioAsignacionAreas(models.Model):
    _inherit = 'koroshi.operario.asignacion'

    def _comprobar_tablero(self):
        if not self.env.user.has_group(GRUPO_TABLERO):
            raise UserError(_('Solo el responsable (grupo «KOROSHI: Tablero del responsable») ve el tablero.'))

    # ------------------------------------------------------------------ dónde está cada uno
    @api.model
    def _tablero_areas(self, empleados):
        """{employee_id: {'area', 'desde' (datetime UTC), 'detalle'}} de los que ahora están en un área. Quien no sale
        está «Sin área». Gana la señal más reciente. La entrada única (koroshi_actividades) lo sobrescribirá."""
        res = {}

        def poner(emp_id, area, desde, detalle):
            if not desde:
                return
            if emp_id not in res or desde > res[emp_id]['desde']:
                res[emp_id] = {'area': area, 'desde': desde, 'detalle': detalle or ''}

        if not empleados:
            return res
        ahora = fields.Datetime.now()
        Tarea = self.env['koroshi.operario.tarea'].sudo()
        for t in Tarea.search([('estado', '=', 'curso'), ('employee_id', 'in', empleados.ids)]):
            ref = (t.batch_id.name if t.tipo == 'agrupacion' else t.picking_id.name) or t.referencia or ''
            poner(t.employee_id.id, 'picking', t._ultima_actividad() or t.inicio, ref.replace('EFFEC/', ''))
        if 'koroshi.contenedor.movimiento' in self.env:
            desde = ahora - datetime.timedelta(minutes=MINUTOS_CONTENEDORES)
            for m in self.env['koroshi.contenedor.movimiento'].sudo().search(
                    [('employee_id', 'in', empleados.ids), ('create_date', '>=', fields.Datetime.to_string(desde))],
                    order='id desc'):
                poner(m.employee_id.id, 'compactacion', m.create_date, m.contenedor)
        if 'koroshi.actividad.registro' in self.env:
            for r in self.env['koroshi.actividad.registro'].sudo().search(
                    [('employee_id', 'in', empleados.ids), ('estado', '=', 'curso')]):
                senal = max([d for d in (r.inicio, getattr(r, 'confirmado', False)) if d])
                poner(r.employee_id.id, area_de_actividad(r.actividad_id.name), senal, r.actividad_id.name)
        return res

    @api.model
    def _tablero_de_hoy(self, company):
        """Quién ha trabajado hoy (o tiene algo en su cola): los que salen en el tablero."""
        Emp = self.env['hr.employee'].sudo()
        hoy = comun.hoy_local()
        desde, hasta = comun.rango_dia_utc(hoy)
        ids = set(self.env['koroshi.operario.tarea'].sudo().search([('dia', '=', hoy)]).mapped('employee_id').ids)
        ids |= set(self.sudo().search([('estado', 'in', VIVAS), ('employee_id', '!=', False),
                                       ('company_id', '=', company.id)]).mapped('employee_id').ids)
        dia = self.env['koroshi.operario.dia'].sudo().search([('fecha', '=', hoy), ('company_id', '=', company.id)],
                                                             limit=1)
        ids |= set(dia.tramo_ids.mapped('employee_id').ids)
        if 'koroshi.actividad.registro' in self.env:
            ids |= set(self.env['koroshi.actividad.registro'].sudo().search(
                [('dia', '=', hoy)]).mapped('employee_id').ids)
        if 'koroshi.contenedor.movimiento' in self.env:
            ids |= set(self.env['koroshi.contenedor.movimiento'].sudo().search(
                [('employee_id', '!=', False), ('create_date', '>=', fields.Datetime.to_string(desde)),
                 ('create_date', '<', fields.Datetime.to_string(hasta))]).mapped('employee_id').ids)
        return Emp.browse(list(ids)).exists()

    # ------------------------------------------------------------------ datos de la pantalla
    @api.model
    def tablero_datos(self, refrescar=False):
        """Todo lo que pinta el tablero por áreas, en una llamada. Solo escribe con refrescar (recalcula «Por
        repartir», como el botón «Actualizar»)."""
        self._comprobar_tablero()
        if refrescar:
            self.tablero_refrescar()
        company = self.env.company
        Asig = self.sudo()
        Tarea = self.env['koroshi.operario.tarea'].sudo()
        hoy = comun.hoy_local()
        empleados = self._tablero_de_hoy(company)

        uds, parado_min = {}, {}
        try:
            ops, _huecos, _parados = Tarea.resumen_operario_dia(hoy)
            for emp_id, o in ops.items():
                uds[emp_id] = int(round(o['uds']))
            umbral = Tarea._minutos_sin_leer_max()
            for t in Tarea.search([('estado', '=', 'curso'), ('employee_id', 'in', empleados.ids)]):
                minutos = t._minutos_sin_leer()
                if minutos >= umbral:
                    parado_min[t.employee_id.id] = int(minutos)
        except Exception:   # solo informativo: nunca rompe el tablero
            _logger.exception('KOROSHI OPERARIOS tablero áreas: uds y parados')
        try:
            areas = self._tablero_areas(empleados)
        except Exception:
            _logger.exception('KOROSHI OPERARIOS tablero áreas: áreas')
            areas = {}

        # zona o agrupación de cada uno en picking: lo que hace ahora y, si no, lo primero de su cola
        vivas = Asig.search([('estado', 'in', VIVAS), ('employee_id', 'in', empleados.ids)],
                            order='secuencia asc, id asc')
        lote_de, cola_de = {}, {}
        for a in vivas.sorted(lambda x: (x.estado != 'curso', x.secuencia, x.id)):
            emp = a.employee_id.id
            if a.tipo in ('lote', 'agrupacion', 'out') and a.batch_id and emp not in lote_de:
                lote_de[emp] = a.batch_id.id
            if a.estado == 'cola' and a.tipo in ('lote', 'agrupacion', 'out'):
                cola_de.setdefault(emp, []).append((a.batch_id.name if a.tipo in ('lote', 'agrupacion')
                                                    else a.picking_id.name or '').replace('EFFEC/', ''))

        personas = []
        for e in empleados.sorted(lambda x: (x.name or '').lower()):
            ar = areas.get(e.id)
            area = ar['area'] if ar else ''
            estado = 'parado' if e.id in parado_min else ('trabaja' if ar else 'libre')
            if e.id in parado_min:
                detalle = _('parado %s min') % parado_min[e.id]
            elif ar:
                detalle = ar['detalle']
            elif cola_de.get(e.id):
                detalle = _('le toca %s') % cola_de[e.id][0]
            else:
                detalle = ''
            personas.append({
                'id': e.id, 'nombre': e.name or '', 'ini': _iniciales(e.name), 'uds': uds.get(e.id, 0),
                'area': area, 'estado': estado, 'detalle': detalle or '',
                'desde': comun.a_local(ar['desde']).strftime('%H:%M') if ar else '',
                'lote': lote_de.get(e.id) if area == 'picking' or not area else False,
                'cola': cola_de.get(e.id, []),
            })

        # filas de Picking: lo libre por prioridad y lo que alguien está haciendo
        piezas = {}
        for pz in Asig.search([('estado', '=', 'pieza'), ('tipo', 'in', ('lote', 'agrupacion')),
                               ('company_id', '=', company.id)]):
            piezas[pz.batch_id.id] = pz.id
        filas, vistas = [], set()
        orden = 0
        for r in self._lotes_por_prioridad(company=company):
            b = r['batch']
            vistas.add(b.id)
            con_gente = any(p['lote'] == b.id and p['area'] == 'picking' for p in personas)
            if not con_gente:
                orden += 1
            filas.append(self._fila_lote(b, r['entera'], piezas.get(b.id, False), r['pendientes'],
                                         0 if con_gente else orden))
        for b in self.env['stock.picking.batch'].sudo().browse(
                [i for i in set(p['lote'] for p in personas if p['lote'] and p['area'] == 'picking') if i not in vistas]).exists():
            filas.append(self._fila_lote(b, False, False, None, 0))

        # v2.25: aviso al responsable de los pedidos que alguien ha dejado hoy («Dejar este pedido» o desde Lecturas)
        dejados = []
        try:
            desde, hasta = comun.rango_dia_utc(hoy)
            estados = dict(self._fields['estado'].selection)
            for a in Asig.search([('motivo_id.destino', '=', 'libre'), ('company_id', '=', company.id),
                                  ('fecha_salto', '>=', fields.Datetime.to_string(desde)),
                                  ('fecha_salto', '<', fields.Datetime.to_string(hasta))],
                                 order='fecha_salto desc', limit=20):
                dejados.append({
                    'hora': comun.a_local(a.fecha_salto).strftime('%H:%M'), 'quien': a.employee_id.name or '',
                    'pedido': (a.name or '').replace('EFFEC/', ''), 'tienda': a.tienda or '',
                    'prog': a.prog_texto or '', 'estado': estados.get(a.estado, ''),
                })
        except Exception:   # solo informativo: nunca rompe el tablero
            _logger.exception('KOROSHI OPERARIOS tablero áreas: dejados')

        return {
            'areas': [{'codigo': c, 'nombre': n} for c, n in AREAS],
            'personas': personas,
            'filas': filas,
            'dejados': dejados,
            'hora': comun.ahora_local().strftime('%H:%M'),
        }

    @api.model
    def _fila_lote(self, b, entera, pieza_id, pendientes, orden):
        outs = b.sudo().picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing' and p.state != 'cancel')
        hechas = len(outs.filtered(lambda p: p.state == 'done'))
        total = len(outs)
        texto = _('%s de %s OUT') % (hechas, total)
        if pendientes:
            texto += _(' · %s uds por hacer') % pendientes
        return {
            'batch_id': b.id, 'nombre': b.name or '', 'entera': entera, 'pieza_id': pieza_id, 'orden': orden,
            'pct': int(round(100.0 * hechas / total)) if total else 0, 'texto': texto,
        }

    @api.model
    def tablero_mover(self, asignacion_id, employee_id, primero=False):
        """Persona -> zona: pieza -> operario = se le da (con primero, la primera de su cola, para reforzar ya).
        Devuelve la tarjeta que queda en la cola del operario."""
        self._comprobar_tablero()
        carta = self.browse(int(asignacion_id)).exists()
        if not carta:
            raise UserError(_('Esa zona ya no está por repartir. Pulsa «Actualizar».'))
        carta.with_context(koroshi_tablero=True).write({'employee_id': employee_id or False})
        if employee_id and primero and carta.estado == 'cola':
            carta.sudo().action_subir()
        return {'id': carta.id, 'tipo': carta.tipo, 'estado': carta.estado}
