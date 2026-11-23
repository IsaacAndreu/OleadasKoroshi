# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Monitor v1.31.0 (17/11/2026): pantalla «Producción por hora» (solo lee, no cambia nada).
#
# /koroshi_monitor/produccion (json): por operario, sus pedidos y sus uds y u/h de cada hora del dia elegido, y el
# total del equipo hora a hora. Las cuentas estan en produccion_calc.py.
# /koroshi_monitor/produccion.xlsx (http): lo mismo en Excel para un dia o un rango (hojas Por hora, Resumen, Pedidos).
# Datos: tareas de koroshi_operarios (>= 2.12, tarea._medir: la misma cifra que la tabla Operarios, Productividad,
# el correo y el KPI) y lecturas de koroshi_preparacion (hora y cantidad de cada lectura en la PDA).
# =============================================================================
import datetime
import io
import threading
import time

import pytz
import xlsxwriter

from odoo import fields, http
from odoo.http import content_disposition, request
from odoo.addons.koroshi_base import comun

import logging

from . import produccion_calc as calc
from ..cache import CachePorClave
from .main import _comprobar_jefe, codigo_op, etiqueta_op   # v1.37.0: solo jefes

_logger = logging.getLogger(__name__)
COMPANY_ID = comun.COMPANY_ID
N_DIAS = 14             # dias en el desplegable
MAX_DIAS_EXCEL = 31
CACHE_SEG = 30
_cache = CachePorClave(CACHE_SEG)   # v1.44.0 (R22): candado por clave (antes uno solo para todos los dias y tipos)
# v1.44.0 (R22): la cabecera (las cuentas de Tiendas del dia) es la misma para todos los tipos: una vez por dia y no
# una por tipo
_cache_cabecera = CachePorClave(CACHE_SEG)


TIPOS = ('tiendas', 'web', 'marketplace', 'otros')     # v1.32.0: selector de la pantalla
NOMBRE_TIPO = {'PED. TIENDAS': 'tiendas', 'PED. MARKETPLACE': 'marketplace', 'PED. WEB': 'web'}
PARAM_RITMO = 'koroshi_monitor.ritmo_estandar'          # v1.32.0: u/h real por debajo de la cual sale en rojo


def tipo_de(picking):
    """v1.32.0: tiendas / web / marketplace / otros segun el tipo del pedido de venta (y W-... = web, como Consulta
    de envios). Las INT y lo que no tiene pedido de venta: otros."""
    if not picking:
        return 'otros'
    try:
        nombre = picking.sale_id and picking.sale_id.s_order_type_id and picking.sale_id.s_order_type_id.name or ''
    except AttributeError:      # sin el campo s_order_type_id
        nombre = ''
    if nombre in NOMBRE_TIPO:
        return NOMBRE_TIPO[nombre]
    if (picking.origin or '').startswith('W-'):
        return 'web'
    return 'otros'


def ritmo_estandar(env):
    try:
        return max(1, int(float(env['ir.config_parameter'].sudo().get_param(PARAM_RITMO, calc.RITMO_ESTANDAR))))
    except (TypeError, ValueError):
        return calc.RITMO_ESTANDAR


class KoroshiProduccion(http.Controller):

    def _env(self):
        return request.env(context=dict(request.env.context, allowed_company_ids=[COMPANY_ID]))

    def _tz(self):
        # como el Monitor (v1.28): la hora del usuario; sin zona, la del almacen
        return pytz.timezone(request.env.user.tz or comun.TZ)

    def _hoy(self):
        return datetime.datetime.now(pytz.utc).astimezone(self._tz()).date()

    def _fecha(self, texto, defecto):
        try:
            return datetime.datetime.strptime(texto or '', '%Y-%m-%d').date()
        except ValueError:
            return defecto

    def _tareas(self, env, dia):
        """Tareas del dia medidas y con sus lecturas, para produccion_calc. None si falta koroshi_operarios 2.12."""
        if 'koroshi.operario.tarea' not in env.registry:
            return None
        Tarea = env['koroshi.operario.tarea'].sudo()
        if not hasattr(Tarea, '_medir') or not hasattr(Tarea, '_marcas_preparacion'):
            return None
        ahora = fields.Datetime.now()
        tareas = Tarea.search([('dia', '=', dia)], order='inicio asc')
        if not tareas:
            return []
        marcas = tareas._marcas_preparacion(ahora)
        umbral = Tarea._minutos_sin_leer_max()
        pickings = dict((t.id, t._pickings().ids) for t in tareas)
        # uds de cada lectura de la PDA (solo «leer» bien hechas y no deshechas: deshacer marca la lectura deshecha)
        lecturas = {}
        if 'koroshi.preparacion.lectura' in env.registry:
            todos = set()
            for ids in pickings.values():
                todos.update(ids)
            desde = min(t.inicio for t in tareas)
            hasta = max((t.fin or ahora) for t in tareas)
            for l in env['koroshi.preparacion.lectura'].sudo().search_read([
                    ('tipo', '=', 'leer'), ('resultado', '=', 'ok'), ('deshecha', '=', False),
                    ('employee_id', 'in', tareas.mapped('employee_id').ids), ('picking_id', 'in', list(todos)),
                    ('fecha', '>=', desde), ('fecha', '<=', hasta)], ['employee_id', 'picking_id', 'fecha', 'cantidad']):
                if l['employee_id'] and l['picking_id']:
                    lecturas.setdefault((l['employee_id'][0], l['picking_id'][0]), []).append(
                        (l['fecha'], l['cantidad'] or 0.0))
        datos = []
        for t in tareas:
            med = t._medir(ahora, marcas.get(t.id), umbral)
            fin = med['fin'] or t.inicio
            huecos = list(med['huecos'] or [])
            if med.get('parado_ahora'):        # abierta y ahora sin leer: ese rato tampoco cuenta
                huecos.append((med['parado_ahora'][0], ahora, med['parado_ahora'][1]))
            suyas = []
            for pid in pickings[t.id]:
                for fecha, cant in lecturas.get((t.employee_id.id, pid), []):
                    if t.inicio <= fecha <= fin:
                        suyas.append((fecha, cant))
            ref = (t.batch_id.name if t.tipo == 'agrupacion' else t.picking_id.name) or t.referencia or ''
            pick0 = t.picking_id if t.tipo != 'agrupacion' else t.batch_id.picking_ids[:1]
            datos.append({
                'tipo': tipo_de(pick0), 'pickings': pickings[t.id],
                'op': etiqueta_op(t.employee_id), 'codigo': codigo_op(t.employee_id),
                'ref': ref.replace('EFFEC/', ''), 'out_id': t.picking_id.id if t.tipo != 'agrupacion' else False,
                'estado': dict(t._fields['estado'].selection).get(t.estado, t.estado),
                'inicio': t.inicio, 'fin': fin, 'uds': med['uds'], 'minutos': med['minutos'],
                'efectivo': med['efectivo'], 'huecos': huecos, 'lecturas': suyas,
            })
        return datos

    def _turnos(self, env, datos):
        """v1.38.0: {op: turno} por la hora de su primera tarea del día (koroshi_base 1.1 comun.turno_de). Con
        koroshi_base 1.0 no hay turnos: la presencia queda como en la 1.37."""
        if not hasattr(comun, 'turno_de'):
            return {}
        texto = comun.texto_turnos(env)
        entrada = {}
        for t in datos:
            if t['op'] not in entrada or t['inicio'] < entrada[t['op']]:
                entrada[t['op']] = t['inicio']
        return dict((op, comun.turno_de(ini, texto)) for op, ini in entrada.items())

    def _calcular(self, dia, tipo=None):
        env = self._env()
        datos = self._tareas(env, dia)
        if datos is None:
            return {'sin_modulo': True}
        filtrar = (lambda t: t['tipo'] == tipo) if tipo in TIPOS else None
        minutos_hueco = calc.MINUTOS_HUECO
        if hasattr(env['koroshi.operario.tarea'], '_minutos_sin_leer_max'):
            minutos_hueco = env['koroshi.operario.tarea'].sudo()._minutos_sin_leer_max()
        res = calc.produccion(datos, self._tz(), filtrar=filtrar, ritmo=ritmo_estandar(env), minutos_hueco=minutos_hueco,
                              turnos=self._turnos(env, datos))
        res['sin_modulo'] = False
        res['tipo'] = tipo if tipo in TIPOS else 'todo'
        return res

    def _cabecera(self, dia):
        """v1.32.0: franja del dia de los pedidos de tienda: total, hecho, pendiente, ritmo del equipo, horas que
        quedan y hora de fin. Las mismas cuentas que la vista Tiendas del Monitor; hoy suma tambien las OUT de tienda
        abiertas de dias anteriores (lo pendiente a primera hora)."""
        from .main import KoroshiMonitor
        try:
            r = KoroshiMonitor()._calcular_datos('TIENDAS:%s' % dia.isoformat(), forzar=True,
                                                abiertas_antes=(dia == self._hoy()))
        except Exception:
            _logger.exception('KOROSHI Produccion: no se ha podido calcular la cabecera del dia')
            return {}
        total = sum([(d['leido'] if d['est'] == 'hecha' else d['disp']) for d in r.get('D') or []])
        hecho = sum([d['leido'] for d in r.get('D') or []])
        eq = r.get('equipo') or {}
        pendiente = max(total - hecho, 0.0)
        return {
            'total': int(round(total)), 'hecho': int(round(hecho)), 'pendiente': int(round(pendiente)),
            'pct': int(round(100.0 * hecho / total)) if total else 0, 'uh_equipo': eq.get('uh') or 0,
            'horas_quedan': round(pendiente / eq['uh'], 1) if eq.get('uh') else None,
            'fin_previsto': eq.get('fin_previsto') or '', 'inicio': eq.get('inicio') or '',
            'out': len(r.get('D') or []), 'anteriores': r.get('abiertas_antes', 0),
        }

    @http.route('/koroshi_monitor/produccion', type='json', auth='user')
    def produccion(self, dia=None, tipo=None, **kw):
        _comprobar_jefe()   # v1.37.0: solo jefes
        hoy = self._hoy()
        d = self._fecha(dia, hoy)
        tipo = tipo if tipo in TIPOS else None
        clave = (request.env.cr.dbname, request.env.user.tz or '', d.isoformat(), tipo or '')

        def calcular():
            r = self._calcular(d, tipo)
            if not r.get('sin_modulo'):
                r['cabecera'] = _cache_cabecera.obtener(clave[:3], lambda: self._cabecera(d))
            return r
        res = dict(_cache.obtener(clave, calcular))   # v1.44.0: candado por clave
        res.update({'dia': d.isoformat(), 'hoy': hoy.isoformat(), 'es_hoy': d == hoy,
                    'dias': [(hoy - datetime.timedelta(days=i)).isoformat() for i in range(N_DIAS)],
                    'hora': datetime.datetime.now(pytz.utc).astimezone(self._tz()).strftime('%H:%M')})
        return res

    @http.route('/koroshi_monitor/produccion.xlsx', type='http', auth='user')
    def produccion_excel(self, desde=None, hasta=None, **kw):
        _comprobar_jefe()   # v1.37.0: solo jefes
        hoy = self._hoy()
        d1 = self._fecha(desde, hoy)
        d2 = self._fecha(hasta, d1)
        if d2 < d1:
            d1, d2 = d2, d1
        if (d2 - d1).days >= MAX_DIAS_EXCEL:
            d1 = d2 - datetime.timedelta(days=MAX_DIAS_EXCEL - 1)
        salida = io.BytesIO()
        libro = xlsxwriter.Workbook(salida, {'in_memory': True})
        neg = libro.add_format({'bold': True, 'bg_color': '#DCE6F1', 'border': 1})
        h_hora = libro.add_worksheet('Por hora')
        h_res = libro.add_worksheet('Resumen')
        h_ped = libro.add_worksheet('Pedidos')
        # v1.32.0: u/h real (hora entera, presencia) y u/h picking (minutos efectivos), minutos perdidos y tipo
        cab_hora = ['Día', 'Operario', 'Código', 'Hora', 'Uds', 'Min presencia', 'Min efectivos', 'Min perdidos',
                    'u/h real', 'u/h picking']
        cab_res = ['Día', 'Operario', 'Código', 'Pedidos', 'Uds', 'Min presencia', 'Min efectivos', 'Min perdidos',
                   'Horas presencia', 'u/h real', 'u/h picking', 'Estimado (sin lecturas PDA)']
        cab_ped = ['Día', 'Operario', 'Código', 'Pedido', 'Tipo', 'Estado', 'Inicio', 'Fin', 'Uds', 'Min (inicio a fin)',
                   'Min efectivos', 'u/h picking', 'Estimado (sin lecturas PDA)']
        for hoja, cab in ((h_hora, cab_hora), (h_res, cab_res), (h_ped, cab_ped)):
            for c, txt in enumerate(cab):
                hoja.write(0, c, txt, neg)
            hoja.freeze_panes(1, 0)
            hoja.set_column(0, 0, 11)
            hoja.set_column(1, 1, 30)
            hoja.set_column(2, len(cab) - 1, 13)

        def vacio(x):
            return x if x is not None else ''

        fh = fr = fp = 1
        d = d1
        while d <= d2:
            r = self._calcular(d)
            dia_txt = d.strftime('%d/%m/%Y')
            for o in r.get('operarios') or []:
                for h in r['horas']:
                    c = o['celdas'].get(str(h))
                    if not c:
                        continue
                    h_hora.write_row(fh, 0, [dia_txt, o['op'], o['codigo'], '%02d:00-%02d:00' % (h, (h + 1) % 24),
                                             c['uds'], c['pres'], c['min'], c['perdido'], vacio(c['uh_real']),
                                             vacio(c['uh'])])
                    fh += 1
                h_res.write_row(fr, 0, [dia_txt, o['op'], o['codigo'], o['n_pedidos'], o['uds'], o['presencia'],
                                        o['efectivo'], o['perdido'], o['horas_pres'], o['uh_real'], o['uh'],
                                        'Sí' if o['estimado'] else ''])
                fr += 1
                for p in o['pedidos']:
                    h_ped.write_row(fp, 0, [dia_txt, o['op'], o['codigo'], p['ref'], p['tipo'], p['estado'], p['ini'],
                                            p['fin'], p['uds'], p['min_total'], p['min'], p['uh'],
                                            'Sí' if p['estimado'] else ''])
                    fp += 1
            eq = r.get('equipo')
            if eq:
                for h in r['horas']:
                    c = eq['celdas'].get(str(h))
                    if c:
                        h_hora.write_row(fh, 0, [dia_txt, 'EQUIPO (u/h por persona)', '',
                                                 '%02d:00-%02d:00' % (h, (h + 1) % 24), c['uds'], c['pres'], c['min'],
                                                 c['perdido'], vacio(c['uh_real']), vacio(c['uh'])])
                        fh += 1
                h_res.write_row(fr, 0, [dia_txt, 'EQUIPO', '', '', eq['uds'], eq['presencia'], eq['efectivo'],
                                        eq['perdido'], eq['horas_pres'], eq['uh_real'], eq['uh'], ''])
                fr += 1
            d += datetime.timedelta(days=1)
        libro.close()
        nombre = 'produccion_operarios_%s.xlsx' % (d1.isoformat() if d1 == d2 else '%s_%s' % (d1.isoformat(),
                                                                                                d2.isoformat()))
        return request.make_response(salida.getvalue(), headers=[
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', content_disposition(nombre)),
        ])
