# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Informe: correo de productividad del almacen (diario, semanal y mensual).
#
# Diario (a la hora de koroshi_informe.hora_diario, 17:00): cifras del dia (ficha KPI del dia completo, recalculada
# antes de mandar), operarios de hoy (tareas con tarjeta), mejores de los ultimos 5 dias y records, tiempos
# parados, faltas del dia y esta semana contra la pasada.
# Semanal (lunes a la hora de koroshi_informe.hora_resumen): la semana anterior contra la de antes.
# Mensual (dia 1 a la misma hora): el mes anterior contra el de antes.
#
# Fuentes (solo lectura): koroshi.operario.tarea (koroshi_operarios), koroshi.preparacion.lectura (paradas),
# koroshi.kpi.dia / koroshi.kpi.falta / koroshi.kpi.falta.repetida (koroshi_kpi) y stock.picking.
# Escribe: su tabla koroshi.informe.operario.dia (un resumen por operario y dia, para records y comparar), sus
# parametros koroshi_informe.*, el mail.mail y, antes del diario, la ficha KPI y las faltas de ese dia
# (koroshi_kpi: action_recalcular, lo mismo que su boton Recalcular).
#
# Parado = huecos de koroshi_operarios.minutos_sin_leer minutos (15) o mas sin ninguna lectura de Preparacion con el
# pedido abierto, y lo que lleva sin leer un pedido aun abierto. Las tareas hechas con la app de codigo de barras
# (sin Preparacion) no tienen el detalle: su parado es 0 y se avisa.
# u/h = uds x 60 / (minutos con el pedido abierto - parado).
# =============================================================================
import datetime
import html
import logging
import re

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.koroshi_operarios.models.informe import codigo_corto, hm
from odoo.addons.koroshi_operarios.models.tarea import ZONA_HORARIA

_logger = logging.getLogger(__name__)

COMPANY_ID = 8          # EFFECTIVE LOGISTICS, S.L.
P = 'koroshi_informe.'
DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
DIAS_CORTO = ['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom']
MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre',
         'noviembre', 'diciembre']
MOTIVOS = [('pendiente', 'En pedido pendiente'), ('no_cogido', 'No cogido (había stock)'),
           ('sin_stock', 'Sin stock'), ('cancelado', 'No servido (cancelado)')]
MEDALLAS = ['🥇', '🥈', '🥉']

# estilos (los correos no leen <style>: todo en linea)
S_TH = 'style="text-align:left;padding:5px;background:#f2f2f2;border-bottom:2px solid #999"'
S_THR = 'style="text-align:right;padding:5px;background:#f2f2f2;border-bottom:2px solid #999"'
S_TD = 'style="padding:5px;border-bottom:1px solid #ddd"'
S_TDR = 'style="padding:5px;border-bottom:1px solid #ddd;text-align:right"'
S_TDG = 'style="padding:5px;border-bottom:1px solid #ddd;text-align:right;color:#888"'
S_H3 = 'style="margin:20px 0 6px;border-bottom:2px solid #111;padding-bottom:3px;font-size:15px"'
S_NOTA = 'style="color:#888;font-size:11px;margin:4px 0"'
ROJO = '#b00020'
VERDE = '#1b7f3b'


def num(x):
    return '{:,.0f}'.format(x or 0).replace(',', '.')


def esc(s):
    return html.escape('' if s is None else str(s))


def var(actual, antes):
    """Variacion en % o None."""
    if not antes:
        return None
    return (actual - antes) * 100.0 / antes


def flecha(v, texto=''):
    if v is None:
        return '<span style="color:#888">%s</span>' % esc(texto or '–')
    color = v >= 0 and VERDE or ROJO
    return '<span style="color:%s">%s %s %%%s</span>' % (
        color, v >= 0 and '▲' or '▼', num(abs(v)), texto and ' ' + esc(texto) or '')


def nombre_bonito(nombre):
    return ' '.join(p.capitalize() for p in (nombre or '').split())


class KoroshiInformeOperarioDia(models.Model):
    _name = 'koroshi.informe.operario.dia'
    _description = 'KOROSHI Informe: resumen por operario y día'
    _order = 'fecha desc, uds_hora desc'

    fecha = fields.Date('Día', required=True, index=True)
    employee_id = fields.Many2one('hr.employee', 'Operario', required=True, index=True, ondelete='cascade')
    codigo = fields.Char('Código')
    nombre = fields.Char('Nombre')
    tareas = fields.Integer('Pedidos empezados')
    acabadas = fields.Integer('Pedidos acabados')
    uds = fields.Float('Uds', digits=(16, 0))
    minutos = fields.Float('Minutos con pedido abierto', digits=(16, 1))
    parado = fields.Float('Minutos parado', digits=(16, 1))
    efectivo = fields.Float('Minutos trabajando', digits=(16, 1))
    uds_hora = fields.Float('u/h', digits=(16, 0), group_operator='avg')
    sin_detalle = fields.Integer('Tareas sin detalle de paradas',
                                 help='Hechas sin Preparación en Lecturas: no se sabe si hubo paradas')
    inicio = fields.Datetime('Empieza')
    fin = fields.Datetime('Acaba')

    _sql_constraints = [('fecha_operario_unico', 'unique(fecha, employee_id)', 'Un resumen por operario y día')]


class KoroshiInforme(models.AbstractModel):
    _name = 'koroshi.informe'
    _description = 'KOROSHI Informe de productividad por correo'

    # ================================================================== utilidades
    @api.model
    def _param(self, clave, defecto=''):
        valor = self.env['ir.config_parameter'].sudo().get_param(P + clave, defecto)
        return valor if valor not in (False, None) else defecto

    @api.model
    def _param_int(self, clave, defecto):
        try:
            return int(self._param(clave, str(defecto)))
        except ValueError:
            return defecto

    @api.model
    def _set(self, clave, valor):
        self.env['ir.config_parameter'].sudo().set_param(P + clave, valor)

    @api.model
    def _ahora_local(self):
        return datetime.datetime.now(pytz.timezone(ZONA_HORARIA))

    @api.model
    def _hoy(self):
        return self._ahora_local().date()

    @api.model
    def _limites(self, desde, hasta=None):
        """UTC sin zona [desde 00:00, hasta+1 00:00) en hora de Madrid."""
        tz = pytz.timezone(ZONA_HORARIA)
        hasta = hasta or desde
        ini = tz.localize(datetime.datetime.combine(desde, datetime.time.min)).astimezone(pytz.utc)
        fin = tz.localize(datetime.datetime.combine(hasta + datetime.timedelta(days=1), datetime.time.min))
        return ini.replace(tzinfo=None), fin.astimezone(pytz.utc).replace(tzinfo=None)

    @api.model
    def _hora(self, dt):
        if not dt:
            return ''
        return pytz.utc.localize(dt).astimezone(pytz.timezone(ZONA_HORARIA)).strftime('%H:%M')

    @api.model
    def _excluidos(self):
        """Codigos de tarjeta que no salen (pruebas): koroshi_informe.excluir, separados por coma."""
        return set(codigo_corto(x.strip()) for x in (self._param('excluir') or '').split(',') if x.strip())

    @api.model
    def _minutos_ranking(self):
        return max(self._param_int('minutos_ranking', 60), 0)

    # ================================================================== operarios de un dia
    @api.model
    def _operarios_dia(self, dia):
        """Resumen por operario de las tareas de ese dia. Devuelve (filas, huecos, parados_ahora).
        filas: {employee_id: {...}}. No escribe nada."""
        Tarea = self.env['koroshi.operario.tarea'].sudo()
        ahora = fields.Datetime.now()
        umbral = Tarea._minutos_sin_leer_max()
        tareas = Tarea.search([('dia', '=', dia)], order='inicio asc')
        lect = {}
        if tareas and 'koroshi.preparacion.lectura' in self.env:
            ini, fin = self._limites(dia)
            for l in self.env['koroshi.preparacion.lectura'].sudo().search([
                    ('employee_id', 'in', tareas.mapped('employee_id').ids), ('picking_id', '!=', False),
                    ('fecha', '>=', ini), ('fecha', '<', fin + datetime.timedelta(hours=6))]):
                lect.setdefault((l.employee_id.id, l.picking_id.id), []).append(l.fecha)
        ops = {}
        huecos = []
        parados_ahora = []
        for t in tareas:
            e = t.employee_id
            cod = codigo_corto(e.barcode)
            o = ops.setdefault(e.id, {
                'employee_id': e.id, 'codigo': cod, 'nombre': e.name or '', 'tareas': 0, 'acabadas': 0,
                'uds': 0.0, 'minutos': 0.0, 'parado': 0.0, 'sin_detalle': 0, 'inicio': None, 'fin': None,
                'curso': 0,
            })
            en_curso = t.estado == 'curso'
            fin_t = ahora if en_curso else (t.fin or t.inicio)
            pickings = t._pickings()
            ref = (t.batch_id.name if t.tipo == 'agrupacion' else t.picking_id.name) or t.referencia or ''
            ref = ref.replace('EFFEC/', '')
            marcas = []
            for pid in pickings.ids:
                marcas += [f for f in lect.get((e.id, pid), []) if t.inicio <= f <= fin_t]
            parado = 0.0
            if marcas:
                marcas = [t.inicio] + sorted(marcas)
                for a, b in zip(marcas, marcas[1:]):
                    m = (b - a).total_seconds() / 60.0
                    if m >= umbral:
                        parado += m
                        huecos.append({'codigo': cod, 'nombre': e.name, 'desde': a, 'hasta': b, 'min': m, 'ref': ref})
                ultima = marcas[-1]
                if not en_curso and t.fin and t.fin > ultima:
                    m = (t.fin - ultima).total_seconds() / 60.0
                    if m >= umbral:
                        parado += m
                        huecos.append({'codigo': cod, 'nombre': e.name, 'desde': ultima, 'hasta': t.fin, 'min': m,
                                       'ref': ref})
            elif not en_curso and (t.minutos or 0) >= 1:
                o['sin_detalle'] += 1
            if en_curso:
                # lo que lleva sin leer ahora (Preparacion o una linea del pedido con la app de codigo de barras)
                ultima = t._ultima_actividad() or t.inicio
                m = max((ahora - ultima).total_seconds() / 60.0, 0.0)
                if m >= umbral:
                    parado += m
                    parados_ahora.append({
                        'codigo': cod, 'nombre': e.name, 'ref': ref, 'desde': ultima, 'min': m,
                        'uds_total': t.uds_total or 0.0, 'leidas': Tarea._uds_leidas(pickings)})
                o['curso'] += 1
                uds = t._uds_hasta_ahora()
                minutos = max((ahora - t.inicio).total_seconds() / 60.0, 0.0)
            else:
                uds = t.uds or 0.0
                minutos = t.minutos or 0.0
                if t.estado == 'acabada':
                    o['acabadas'] += 1
            o['tareas'] += 1
            o['uds'] += uds
            o['minutos'] += minutos
            o['parado'] += min(parado, minutos)
            if not o['inicio'] or t.inicio < o['inicio']:
                o['inicio'] = t.inicio
            if not o['fin'] or fin_t > o['fin']:
                o['fin'] = fin_t
        for o in ops.values():
            o['efectivo'] = max(o['minutos'] - o['parado'], 0.0)
            o['uds_hora'] = o['efectivo'] >= 1 and o['uds'] * 60.0 / o['efectivo'] or 0.0
        return ops, huecos, parados_ahora

    @api.model
    def _guardar_dia(self, dia, filas):
        Tabla = self.env['koroshi.informe.operario.dia'].sudo()
        Tabla.search([('fecha', '=', dia)]).unlink()
        for o in filas.values():
            Tabla.create({
                'fecha': dia, 'employee_id': o['employee_id'], 'codigo': o['codigo'], 'nombre': o['nombre'],
                'tareas': o['tareas'], 'acabadas': o['acabadas'], 'uds': o['uds'], 'minutos': o['minutos'],
                'parado': o['parado'], 'efectivo': o['efectivo'], 'uds_hora': o['uds_hora'],
                'sin_detalle': o['sin_detalle'], 'inicio': o['inicio'], 'fin': o['fin'],
            })

    @api.model
    def cerrar_dias(self):
        """Guarda el resumen por operario de los dias ya acabados que faltan (hasta ayer). La primera vez, desde la
        primera tarea. Solo escribe en koroshi.informe.operario.dia y el parametro cerrado_hasta."""
        ayer = self._hoy() - datetime.timedelta(days=1)
        hecho = self._param('cerrado_hasta')
        dominio = [('dia', '<=', ayer)]
        if hecho:
            dominio.append(('dia', '>', hecho))
        Tarea = self.env['koroshi.operario.tarea'].sudo()
        dias = sorted(set(Tarea.search(dominio).mapped('dia')))
        for d in dias:
            self._guardar_dia(d, self._operarios_dia(d)[0])
        if hecho != ayer.isoformat():
            self._set('cerrado_hasta', ayer.isoformat())
        return len(dias)

    @api.model
    def _historial(self, hasta, vivo=None, dia_vivo=None):
        """Filas por operario y dia hasta 'hasta' (incluido): las guardadas y, para dia_vivo, las de 'vivo'."""
        excl = self._excluidos()
        filas = []
        for r in self.env['koroshi.informe.operario.dia'].sudo().search([('fecha', '<=', hasta)]):
            if r.fecha == dia_vivo:
                continue
            filas.append({'fecha': r.fecha, 'employee_id': r.employee_id.id, 'codigo': r.codigo, 'nombre': r.nombre,
                          'tareas': r.tareas, 'acabadas': r.acabadas, 'uds': r.uds, 'minutos': r.minutos,
                          'parado': r.parado, 'efectivo': r.efectivo, 'sin_detalle': r.sin_detalle})
        for o in (vivo or {}).values():
            f = dict(o)
            f['fecha'] = dia_vivo
            filas.append(f)
        return [f for f in filas if f['codigo'] not in excl]

    @api.model
    def _sumar(self, filas):
        """Junta filas por operario: {employee_id: totales con u/h y dias}."""
        res = {}
        for f in filas:
            o = res.setdefault(f['employee_id'], {
                'employee_id': f['employee_id'], 'codigo': f['codigo'], 'nombre': f['nombre'], 'tareas': 0,
                'acabadas': 0, 'uds': 0.0, 'minutos': 0.0, 'parado': 0.0, 'efectivo': 0.0, 'sin_detalle': 0,
                'dias': set()})
            for k in ('tareas', 'acabadas', 'uds', 'minutos', 'parado', 'efectivo', 'sin_detalle'):
                o[k] += f.get(k) or 0
            o['dias'].add(f['fecha'])
        for o in res.values():
            o['uds_hora'] = o['efectivo'] >= 1 and o['uds'] * 60.0 / o['efectivo'] or 0.0
            o['n_dias'] = len(o['dias'])
        return res

    @api.model
    def _records(self, hist):
        """Mejor dia de cada operario (con minutos_ranking o mas trabajando): {employee_id: (u/h, fecha, n dias)}."""
        minr = self._minutos_ranking()
        res = {}
        for f in hist:
            if f['efectivo'] < max(minr, 1):
                continue
            uh = f['uds'] * 60.0 / f['efectivo']
            r = res.get(f['employee_id'])
            n = (r and r[2] or 0) + 1
            if not r or uh > r[0]:
                res[f['employee_id']] = (uh, f['fecha'], n)
            else:
                res[f['employee_id']] = (r[0], r[1], n)
        return res

    @api.model
    def _mejores(self, hist, hasta, n_dias=5):
        """Los ultimos n dias con actividad hasta 'hasta': u/h de cada operario en esos dias, de mas a menos."""
        fechas = sorted(set(f['fecha'] for f in hist if f['fecha'] <= hasta), reverse=True)[:n_dias]
        suma = self._sumar([f for f in hist if f['fecha'] in fechas])
        minr = max(self._minutos_ranking(), 1)
        lista = [o for o in suma.values() if o['efectivo'] >= minr]
        lista.sort(key=lambda o: -o['uds_hora'])
        return lista, fechas

    # ================================================================== datos del almacen
    @api.model
    def _fichas(self, desde, hasta):
        """Fichas KPI del dia completo: {fecha: ficha}."""
        fichas = self.env['koroshi.kpi.dia'].sudo().search([('metodo', '=', 'mixto'), ('fecha', '>=', desde),
                                                            ('fecha', '<=', hasta)])
        return dict((f.fecha, f) for f in fichas)

    @api.model
    def _faltas(self, desde, hasta):
        """Faltas (uds) por dia, por motivo y por articulo."""
        por_dia, por_motivo, por_ref = {}, {}, {}
        for f in self.env['koroshi.kpi.falta'].sudo().search([('fecha', '>=', desde), ('fecha', '<=', hasta),
                                                              ('faltan', '>', 0)]):
            por_dia[f.fecha] = por_dia.get(f.fecha, 0.0) + f.faltan
            por_motivo[f.motivo] = por_motivo.get(f.motivo, 0.0) + f.faltan
            por_ref[f.referencia or '?'] = por_ref.get(f.referencia or '?', 0.0) + f.faltan
        return por_dia, por_motivo, por_ref

    @api.model
    def _uh_ficha(self, fichas):
        """(uds, horas-persona picking, u/h, alguna estimada) de unas fichas."""
        uds = sum(f.uds for f in fichas)
        uds_h = sum(f.uds for f in fichas if f.hp_picking > 0)
        hp = sum(f.hp_picking for f in fichas if f.hp_picking > 0)
        estimada = any((not (f.pick_personas * f.pick_horas)) and f.pick_hp_auto > 0 for f in fichas)
        return uds, hp, hp and uds_h / hp or 0.0, estimada

    @api.model
    def _cobertura(self, desde, hasta):
        """(OUT validadas, de ellas con operario) entre esos dias."""
        ini, fin = self._limites(desde, hasta)
        hechas = self.env['stock.picking'].sudo().search([
            ('company_id', '=', COMPANY_ID), ('picking_type_code', '=', 'outgoing'), ('state', '=', 'done'),
            ('date_done', '>=', ini), ('date_done', '<', fin)])
        tareas = self.env['koroshi.operario.tarea'].sudo().search([
            ('inicio', '>=', ini - datetime.timedelta(days=1)), ('inicio', '<', fin)])
        cubiertas = tareas.mapped('picking_id')
        for t in tareas.filtered(lambda x: x.tipo == 'agrupacion'):
            cubiertas |= t.batch_id.picking_ids
        return len(hechas), len(hechas & cubiertas)

    @api.model
    def _recalcular_kpi(self, dia):
        """Ficha KPI del dia completo y faltas de ese dia al momento (lo mismo que el boton Recalcular de la ficha).
        Si falla, se sigue con lo que haya."""
        try:
            with self.env.cr.savepoint():
                self.env['koroshi.kpi.dia'].sudo().crear_fichas(dia).filtered(
                    lambda f: f.metodo == 'mixto').action_recalcular()
        except Exception:
            _logger.exception('KOROSHI Informe: no se ha podido recalcular la ficha KPI del %s', dia)

    # ================================================================== trozos de html
    @api.model
    def _tarjeta(self, valor, texto, sub=''):
        return ('<td style="border:1px solid #ddd;padding:10px;text-align:center;width:25%%">'
                '<div style="font-size:22px;font-weight:bold">%s</div><div style="color:#666">%s</div>'
                '<div style="font-size:12px">%s</div></td>') % (valor, texto, sub)

    @api.model
    def _cabecera(self, titulo, subtitulo):
        return ('<div style="max-width:720px;font-family:Arial,sans-serif;font-size:13px;color:#222">'
                '<div style="background:#111;color:#fff;padding:12px 16px">'
                '<div style="font-size:18px;font-weight:bold">%s</div><div style="color:#bbb">%s</div></div>') % (
                    esc(titulo), esc(subtitulo))

    @api.model
    def _pie(self):
        return ('<p style="color:#888;font-size:11px;margin-top:18px;border-top:1px solid #ddd;padding-top:8px">'
                'Correo automático de Odoo (KOROSHI Informe). Detalle en Inventario › Informes › KOROSHI. '
                'Destinatarios y horas en Configuración › KOROSHI › Ajustes KOROSHI.</p></div>')

    @api.model
    def _tabla_operarios(self, filas, previo=None, con_horas=True, con_dias=False):
        """Tabla de operarios. previo: {employee_id: u/h de antes} para la ultima columna."""
        h = ['<table style="border-collapse:collapse;width:100%"><tr>', '<th %s>Operario</th>' % S_TH]
        if con_horas:
            h.append('<th %s>De – a</th>' % S_TH)
        if con_dias:
            h.append('<th %s>Días</th>' % S_THR)
        h.append(''.join('<th %s>%s</th>' % (S_THR, c) for c in ['Pedidos', 'Uds', 'Tiempo', 'u/h', 'Parado']))
        if previo is not None:
            h.append('<th %s>%s</th>' % (S_THR, con_dias and 'vs antes' or 'vs sus 5 días'))
        h.append('</tr>')
        tot = {'uds': 0.0, 'min': 0.0, 'par': 0.0, 'ef': 0.0, 'ped': 0}
        for o in filas:
            ped = '%d' % o['acabadas']
            if o.get('curso'):
                ped += ' <span style="color:#888">(%d abierta%s)</span>' % (o['curso'], o['curso'] > 1 and 's' or '')
            par = o['parado'] >= 1 and '<span style="color:%s">%s</span>' % (ROJO, hm(o['parado'])) or '–'
            if o.get('sin_detalle') and o['parado'] < 1:
                par = '<span style="color:#888" title="sin Preparación">?</span>'
            h.append('<tr><td %s><b>%s</b> %s</td>' % (S_TD, esc(o['codigo']), esc(nombre_bonito(o['nombre']))))
            if con_horas:
                h.append('<td %s>%s – %s</td>' % (S_TD, self._hora(o['inicio']), self._hora(o['fin'])))
            if con_dias:
                h.append('<td %s>%d</td>' % (S_TDR, o['n_dias']))
            h.append('<td %s>%s</td><td %s>%s</td><td %s>%s</td><td %s><b>%s</b></td><td %s>%s</td>' % (
                S_TDR, ped, S_TDR, num(o['uds']), S_TDR, hm(o['minutos']), S_TDR,
                o['uds_hora'] and num(o['uds_hora']) or '–', S_TDR, par))
            if previo is not None:
                antes = previo.get(o['employee_id'])
                h.append('<td %s>%s</td>' % (S_TDR, antes and flecha(var(o['uds_hora'], antes)) or
                                             '<span style="color:#888">primer día</span>'))
            h.append('</tr>')
            tot['uds'] += o['uds']
            tot['min'] += o['minutos']
            tot['par'] += o['parado']
            tot['ef'] += o['efectivo']
            tot['ped'] += o['acabadas']
        cols = 1 + (con_horas and 1 or 0) + (con_dias and 1 or 0)
        h.append('<tr style="font-weight:bold"><td style="padding:5px" colspan="%d">Total con tarjeta</td>' % cols)
        h.append(''.join('<td style="padding:5px;text-align:right">%s</td>' % v for v in [
            tot['ped'], num(tot['uds']), hm(tot['min']), tot['ef'] >= 1 and num(tot['uds'] * 60.0 / tot['ef']) or '–',
            tot['par'] >= 1 and hm(tot['par']) or '–']))
        if previo is not None:
            h.append('<td></td>')
        h.append('</tr></table>')
        h.append('<p %s>Solo cuenta lo leído con tarjeta (Lecturas / Preparación). u/h = uds × 60 / tiempo con el pedido '
                 'abierto sin el tiempo parado. «?» = hecho sin Preparación: no se sabe si paró.</p>' % S_NOTA)
        return ''.join(h)

    @api.model
    def _seccion_mejores(self, lista, records, fechas, titulo, fechas_nota=None):
        """fechas: dias en los que un record cuenta como nuevo (🏆). fechas_nota: dias que se dicen abajo."""
        minr = self._minutos_ranking()
        h = ['<h3 %s>%s</h3>' % (S_H3, esc(titulo))]
        if not lista:
            h.append('<p>Nadie con %d min o más trabajando con tarjeta.</p>' % minr)
            return ''.join(h)
        h.append('<table style="border-collapse:collapse;width:100%"><tr>')
        h.append('<th %s>#</th><th %s>Operario</th><th %s>u/h</th><th %s>Uds</th><th %s>Su récord</th>'
                 '<th %s>Día del récord</th></tr>' % (S_TH, S_TH, S_THR, S_THR, S_THR, S_TH))
        for i, o in enumerate(lista[:5]):
            rec = records.get(o['employee_id'])
            nuevo = rec and rec[1] in fechas and rec[2] > 1
            h.append('<tr><td %s>%s</td><td %s>%s %s</td><td %s><b>%s</b></td><td %s>%s</td><td %s>%s%s</td>'
                     '<td %s>%s</td></tr>' % (
                         S_TD, i < 3 and MEDALLAS[i] or i + 1, S_TD, esc(o['codigo']),
                         esc(nombre_bonito(o['nombre'])), S_TDR, num(o['uds_hora']), S_TDR, num(o['uds']),
                         S_TDR, rec and num(rec[0]) or '–', nuevo and ' 🏆' or '', S_TD,
                         rec and rec[1].strftime('%d/%m') or ''))
        h.append('</table>')
        if records:
            emp, (uh, fecha, n) = max(records.items(), key=lambda x: x[1][0])
            quien = [o for o in lista if o['employee_id'] == emp]
            cod = quien and quien[0]['codigo'] or self.env['hr.employee'].sudo().browse(emp).barcode
            h.append('<p style="margin:4px 0">Récord del almacén (un operario en un día): <b>%s u/h</b>, %s, %s.</p>' % (
                num(uh), esc(codigo_corto(cod)), fecha.strftime('%d/%m/%Y')))
        h.append('<p %s>Días con tarjeta: %s. Entran quienes llevan %d min o más trabajando. 🏆 = bate su récord.</p>' % (
            S_NOTA, ', '.join(f.strftime('%d/%m') for f in sorted(fechas_nota or fechas)), minr))
        return ''.join(h)

    @api.model
    def _seccion_faltas(self, por_motivo, por_ref, titulo, n_refs=5):
        h = ['<h3 %s>%s</h3>' % (S_H3, esc(titulo))]
        total = sum(por_motivo.values())
        if not total:
            h.append('<p>Sin faltas.</p>')
        else:
            h.append('<table style="border-collapse:collapse">')
            for clave, texto in MOTIVOS:
                if por_motivo.get(clave):
                    h.append('<tr><td style="padding:3px 12px 3px 0">%s</td><td style="text-align:right"><b>%s</b> uds'
                             '</td></tr>' % (texto, num(por_motivo[clave])))
            h.append('<tr><td style="padding:3px 12px 3px 0"><b>Total</b></td><td style="text-align:right"><b>%s</b> '
                     'uds</td></tr></table>' % num(total))
            top = sorted(por_ref.items(), key=lambda x: -x[1])[:n_refs]
            h.append('<p style="margin:6px 0">Más falta: %s.</p>' % ', '.join(
                '%s (%s)' % (esc(r), num(q)) for r, q in top))
        rep = self.env['koroshi.kpi.falta.repetida'].sudo().search([('sigue', '=', True)], limit=10)
        if rep:
            h.append('<p style="margin:6px 0">Faltas repetidas (siguen): %s.</p>' % ', '.join(
                '<b>%s</b> %d días%s' % (esc(r.referencia), r.dias, r.ubicacion_id and ' (%s)' % esc(
                    r.ubicacion_id.name) or '') for r in rep))
        else:
            h.append('<p style="margin:6px 0">Faltas repetidas: <b>ninguna</b>.</p>')
        return ''.join(h)

    # ================================================================== diario
    @api.model
    def datos_diario(self, dia, recalcular=True):
        if recalcular:
            self.env['koroshi.operario.tarea'].sudo().cron_cerrar()
            self._recalcular_kpi(dia)
        self.cerrar_dias()
        vivo, huecos, parados = self._operarios_dia(dia)
        excl = self._excluidos()
        vivo = dict((k, v) for k, v in vivo.items() if v['codigo'] not in excl)
        huecos = [x for x in huecos if x['codigo'] not in excl]
        parados = [x for x in parados if x['codigo'] not in excl]
        hist = self._historial(dia, vivo, dia)
        lunes = dia - datetime.timedelta(days=dia.weekday())
        fichas = self._fichas(lunes - datetime.timedelta(days=7), dia)
        faltas_dia, _m, _r = self._faltas(lunes - datetime.timedelta(days=7), dia)
        _d, por_motivo, por_ref = self._faltas(dia, dia)
        return {'dia': dia, 'vivo': vivo, 'huecos': huecos, 'parados': parados, 'hist': hist, 'lunes': lunes,
                'fichas': fichas, 'faltas_dia': faltas_dia, 'por_motivo': por_motivo, 'por_ref': por_ref,
                'cobertura': self._cobertura(dia, dia)}

    @api.model
    def html_diario(self, d):
        dia = d['dia']
        hoy = dia == self._hoy()
        ficha = d['fichas'].get(dia)
        antes = d['fichas'].get(dia - datetime.timedelta(days=7))
        uds = ficha and ficha.uds or 0.0
        uds_antes = antes and antes.uds or 0.0
        faltas = d['faltas_dia'].get(dia, 0.0)
        faltas_antes = d['faltas_dia'].get(dia - datetime.timedelta(days=7), 0.0)
        n_ops = self.env['hr.employee'].sudo().search_count([('category_ids.name', '=', 'Operario KOROSHI')])
        hechas, con_op = d['cobertura']
        dcorto = DIAS_CORTO[dia.weekday()]
        h = [self._cabecera('KOROSHI · %s %s' % (DIAS[dia.weekday()].lower(), dia.strftime('%d/%m/%Y')),
                            'Resumen del almacén%s · NAU-2' % (hoy and ' a las %s' % self._ahora_local().strftime(
                                '%H:%M') or ''))]
        sub_ped = '%s OUT' % num(ficha and ficha.outs or 0)
        if hoy:
            pend = self.env['stock.picking'].sudo().search_count([
                ('company_id', '=', COMPANY_ID), ('picking_type_code', '=', 'outgoing'),
                ('state', 'in', ('confirmed', 'waiting', 'assigned'))])
            sub_ped += ' · %s OUT por hacer' % num(pend)
        h.append('<table role="presentation" style="border-collapse:collapse;width:100%;margin:14px 0"><tr>')
        h.append(self._tarjeta(num(uds), 'uds hechas', flecha(var(uds, uds_antes), '(%s pasado %s)' % (
            dcorto, num(uds_antes)))))
        h.append(self._tarjeta(num(ficha and ficha.pedidos or 0), 'pedidos de tienda', '<span style="color:#666">%s'
                               '</span>' % sub_ped))
        h.append(self._tarjeta(num(faltas), 'uds de falta', '<span style="color:#666">%s pasado: %s</span>' % (
            dcorto, num(faltas_antes))))
        h.append(self._tarjeta('%d / %d' % (len(d['vivo']), n_ops), 'operarios con tarjeta',
                               '<span style="color:%s">%d de %d OUT con operario</span>' % (
                                   con_op * 2 < hechas and ROJO or '#666', con_op, hechas)))
        h.append('</tr></table>')

        # operarios de hoy
        h.append('<h3 %s>Operarios %s</h3>' % (S_H3, hoy and 'de hoy' or 'del día'))
        filas = sorted(d['vivo'].values(), key=lambda o: -o['uds_hora'])
        if filas:
            previo = {}
            for emp in d['vivo']:
                antes_f = [f for f in d['hist'] if f['employee_id'] == emp and f['fecha'] < dia]
                fechas = sorted(set(f['fecha'] for f in antes_f), reverse=True)[:5]
                s = self._sumar([f for f in antes_f if f['fecha'] in fechas]).get(emp)
                if s and s['uds_hora']:
                    previo[emp] = s['uds_hora']
            h.append(self._tabla_operarios(filas, previo))
        else:
            h.append('<p><b>Nadie ha leído su tarjeta.</b></p>')

        # mejores y records
        lista, fechas = self._mejores(d['hist'], dia)
        h.append(self._seccion_mejores(lista, self._records(d['hist']), [dia],
                                       'Mejores de los últimos 5 días y récords', fechas))

        # tiempos parados
        umbral = self.env['koroshi.operario.tarea'].sudo()._minutos_sin_leer_max()
        h.append('<h3 %s>Tiempos parados</h3>' % S_H3)
        items = []
        for p in d['parados']:
            items.append('<li><b>Ahora mismo:</b> %s (%s uds, %s leídas) abierta por %s y <b style="color:%s">sin leer '
                         'nada desde las %s</b> (%s).</li>' % (
                             esc(p['ref']), num(p['uds_total']), num(p['leidas']), esc(p['codigo']), ROJO,
                             self._hora(p['desde']), hm(p['min'])))
        for x in sorted(d['huecos'], key=lambda x: -x['min'])[:10]:
            items.append('<li>%s: %s – %s (%s) sin leer con %s abierta.</li>' % (
                esc(x['codigo']), self._hora(x['desde']), self._hora(x['hasta']), hm(x['min']), esc(x['ref'])))
        tot_par = sum(o['parado'] for o in filas)
        tot_min = sum(o['minutos'] for o in filas)
        if items:
            h.append('<ul style="margin:4px 0 0 18px;padding:0">%s</ul>' % ''.join(items))
        h.append('<p style="margin:4px 0">Total parado del día: <b>%s</b> de %s con pedido abierto (%s %%).</p>' % (
            hm(tot_par), hm(tot_min), num(tot_min and tot_par * 100.0 / tot_min or 0)))
        h.append('<p %s>Parado = %d min o más sin leer nada con un pedido abierto (el «minutos sin leer = parado» de '
                 'Ajustes KOROSHI y del monitor).</p>' % (S_NOTA, umbral))

        # faltas
        h.append(self._seccion_faltas(d['por_motivo'], d['por_ref'], 'Faltas del día'))

        # semana
        h.append(self._seccion_semana(d))
        h.append(self._pie())
        asunto = 'KOROSHI %s %s · %s uds · %s pedidos' % (dcorto, dia.strftime('%d/%m'), num(uds),
                                                          num(ficha and ficha.pedidos or 0))
        v = var(uds, uds_antes)
        if v is not None:
            asunto += ' · %s%s %% vs %s pasado' % (v >= 0 and '+' or '−', num(abs(v)), dcorto)
        return asunto, ''.join(h)

    @api.model
    def _seccion_semana(self, d):
        dia, lunes = d['dia'], d['lunes']
        h = ['<h3 %s>Esta semana contra la pasada</h3>' % S_H3,
             '<table style="border-collapse:collapse;width:100%"><tr>',
             '<th %s>Día</th>' % S_TH,
             ''.join('<th %s>%s</th>' % (S_THR, c) for c in ['Uds', 'Sem. pasada', 'u/h-persona', 'Sem. pasada',
                                                              'Faltas', 'Sem. pasada']), '</tr>']
        esta, pasada = [], []
        f_esta = f_pasada = 0.0
        marca = False
        x = lunes
        while x <= dia:
            a = d['fichas'].get(x)
            b = d['fichas'].get(x - datetime.timedelta(days=7))
            if a or b or x.weekday() < 5:
                ua = self._uh_ficha(a and [a] or [])
                ub = self._uh_ficha(b and [b] or [])
                fa = d['faltas_dia'].get(x, 0.0)
                fb = d['faltas_dia'].get(x - datetime.timedelta(days=7), 0.0)
                marca = marca or ua[3] or ub[3]
                h.append('<tr><td %s>%s%s</td><td %s>%s</td><td %s>%s</td><td %s>%s</td><td %s>%s</td><td %s>%s</td>'
                         '<td %s>%s</td></tr>' % (
                             S_TD, DIAS[x.weekday()], x == self._hoy() and ' (hoy)' or '',
                             S_TDR, a and num(a.uds) or '–', S_TDG, b and num(b.uds) or '–',
                             S_TDR, ua[2] and num(ua[2]) + (ua[3] and ' ⚠' or '') or '–',
                             S_TDG, ub[2] and num(ub[2]) + (ub[3] and ' ⚠' or '') or '–',
                             S_TDR, num(fa), S_TDG, num(fb)))
                if a:
                    esta.append(a)
                if b:
                    pasada.append(b)
                f_esta += fa
                f_pasada += fb
            x += datetime.timedelta(days=1)
        ue, up = self._uh_ficha(esta), self._uh_ficha(pasada)
        h.append('<tr style="font-weight:bold"><td style="padding:5px">Lunes a %s</td>' % (
            dia == self._hoy() and 'hoy' or DIAS[dia.weekday()].lower()))
        h.append(''.join('<td style="padding:5px;text-align:right%s">%s</td>' % (g and ';color:#888' or '', v) for v, g in [
            (num(ue[0]), False), (num(up[0]), True), (ue[2] and num(ue[2]) or '–', False),
            (up[2] and num(up[2]) or '–', True), (num(f_esta), False), (num(f_pasada), True)]))
        h.append('</tr></table>')
        h.append('<p %s>Uds y u/h-persona de la ficha KPI del día completo (pedidos de tienda; uds = las de las cajas '
                 'cerradas ese día). %s</p>' % (S_NOTA, marca and '⚠ horas de picking estimadas por las cajas (no '
                                                 'apuntadas a mano en la ficha): con zonas salen pocas horas y la u/h se '
                                                 'dispara.' or ''))
        h.append('<p style="margin:4px 0">Uds lunes a hoy: %s.</p>' % flecha(var(ue[0], up[0]), 'vs semana pasada'))
        return ''.join(h)

    # ================================================================== semanal y mensual
    @api.model
    def datos_periodo(self, desde, hasta, ant_desde, ant_hasta):
        self.cerrar_dias()
        hist = self._historial(hasta)
        en = [f for f in hist if desde <= f['fecha'] <= hasta]
        ant = [f for f in hist if ant_desde <= f['fecha'] <= ant_hasta]
        fichas = self._fichas(ant_desde, hasta)
        faltas_dia, _m, _r = self._faltas(ant_desde, ant_hasta)
        f_dia, por_motivo, por_ref = self._faltas(desde, hasta)
        faltas_dia.update(f_dia)
        return {'desde': desde, 'hasta': hasta, 'ant_desde': ant_desde, 'ant_hasta': ant_hasta, 'hist': hist,
                'en': en, 'ant': ant, 'fichas': fichas, 'faltas_dia': faltas_dia, 'por_motivo': por_motivo,
                'por_ref': por_ref, 'cobertura': self._cobertura(desde, hasta)}

    @api.model
    def html_periodo(self, d, tipo):
        desde, hasta = d['desde'], d['hasta']
        semanal = tipo == 'semanal'
        fe = [f for k, f in d['fichas'].items() if desde <= k <= hasta]
        fa = [f for k, f in d['fichas'].items() if d['ant_desde'] <= k <= d['ant_hasta']]
        ue, ua = self._uh_ficha(fe), self._uh_ficha(fa)
        ped_e, ped_a = sum(f.pedidos for f in fe), sum(f.pedidos for f in fa)
        fal_e = sum(v for k, v in d['faltas_dia'].items() if desde <= k <= hasta)
        fal_a = sum(v for k, v in d['faltas_dia'].items() if d['ant_desde'] <= k <= d['ant_hasta'])
        hechas, con_op = d['cobertura']
        if semanal:
            titulo = 'KOROSHI · semana del %s al %s' % (desde.strftime('%d/%m'), hasta.strftime('%d/%m/%Y'))
            antes_txt = 'semana anterior'
        else:
            titulo = 'KOROSHI · %s %d' % (MESES[desde.month - 1], desde.year)
            antes_txt = MESES[d['ant_desde'].month - 1]
        h = [self._cabecera(titulo, 'Resumen %s · contra %s' % (semanal and 'semanal' or 'mensual', antes_txt))]
        h.append('<table role="presentation" style="border-collapse:collapse;width:100%;margin:14px 0"><tr>')
        h.append(self._tarjeta(num(ue[0]), 'uds hechas', flecha(var(ue[0], ua[0]), '(%s)' % num(ua[0]))))
        h.append(self._tarjeta(num(ped_e), 'pedidos de tienda', flecha(var(ped_e, ped_a), '(%s)' % num(ped_a))))
        h.append(self._tarjeta(ue[2] and num(ue[2]) + (ue[3] and ' ⚠' or '') or '–', 'u/h-persona',
                               flecha(var(ue[2], ua[2]), '(%s)' % (ua[2] and num(ua[2]) or '–'))))
        h.append(self._tarjeta(num(fal_e), 'uds de falta', '<span style="color:#666">antes: %s</span>' % num(fal_a)))
        h.append('</tr></table>')
        h.append('<p style="margin:0 0 8px;color:#666">OUT validadas: %s, con operario: %s (%s %%).</p>' % (
            num(hechas), num(con_op), num(hechas and con_op * 100.0 / hechas or 0)))

        # por dia (semanal) o por semana (mensual)
        tramos = []
        if semanal:
            x = desde
            while x <= hasta:
                tramos.append(('%s %s' % (DIAS[x.weekday()], x.strftime('%d/%m')), x, x, x - datetime.timedelta(days=7)))
                x += datetime.timedelta(days=1)
        else:
            x = desde
            while x <= hasta:
                fin = min(x + datetime.timedelta(days=6 - x.weekday()), hasta)
                tramos.append(('Semana del %s al %s' % (x.strftime('%d/%m'), fin.strftime('%d/%m')), x, fin, None))
                x = fin + datetime.timedelta(days=1)
        h.append('<h3 %s>%s</h3>' % (S_H3, semanal and 'Día a día' or 'Semana a semana'))
        h.append('<table style="border-collapse:collapse;width:100%"><tr>')
        cols = ['Uds', 'Pedidos', 'u/h-persona', 'Faltas'] + (semanal and ['Uds sem. anterior'] or [])
        h.append('<th %s>%s</th>%s</tr>' % (S_TH, semanal and 'Día' or 'Semana',
                                            ''.join('<th %s>%s</th>' % (S_THR, c) for c in cols)))
        for texto, a, b, prev in tramos:
            ff = [f for k, f in d['fichas'].items() if a <= k <= b]
            u = self._uh_ficha(ff)
            if not ff and semanal and a.weekday() >= 5:
                continue
            fal = sum(v for k, v in d['faltas_dia'].items() if a <= k <= b)
            h.append('<tr><td %s>%s</td><td %s>%s</td><td %s>%s</td><td %s>%s</td><td %s>%s</td>' % (
                S_TD, texto, S_TDR, ff and num(u[0]) or '–', S_TDR, ff and num(sum(f.pedidos for f in ff)) or '–',
                S_TDR, u[2] and num(u[2]) + (u[3] and ' ⚠' or '') or '–', S_TDR, num(fal)))
            if semanal:
                fp = d['fichas'].get(prev)
                h.append('<td %s>%s</td>' % (S_TDG, fp and num(fp.uds) or '–'))
            h.append('</tr>')
        h.append('</table>')
        if ue[3] or ua[3]:
            h.append('<p %s>⚠ horas de picking estimadas por las cajas (no apuntadas a mano): la u/h no es fiable.</p>'
                     % S_NOTA)

        # operarios
        h.append('<h3 %s>Operarios %s</h3>' % (S_H3, semanal and 'de la semana' or 'del mes'))
        suma = self._sumar(d['en'])
        if suma:
            previo = dict((k, v['uds_hora']) for k, v in self._sumar(d['ant']).items() if v['uds_hora'])
            filas = sorted(suma.values(), key=lambda o: -o['uds_hora'])
            h.append(self._tabla_operarios(filas, previo, con_horas=False, con_dias=True).replace(
                'primer día', 'nuevo'))
        else:
            h.append('<p><b>Nadie ha leído su tarjeta.</b></p>')

        # mejores del periodo y records batidos
        minr = max(self._minutos_ranking(), 1)
        lista = sorted([o for o in suma.values() if o['efectivo'] >= minr], key=lambda o: -o['uds_hora'])
        fechas = sorted(set(f['fecha'] for f in d['en']))
        h.append(self._seccion_mejores(lista, self._records(d['hist']), fechas,
                                       semanal and 'Mejores de la semana y récords' or 'Mejores del mes y récords'))

        # paradas del periodo
        par = sum(o['parado'] for o in suma.values())
        mins = sum(o['minutos'] for o in suma.values())
        par_a = sum(f['parado'] for f in d['ant'])
        h.append('<h3 %s>Tiempos parados</h3>' % S_H3)
        h.append('<p style="margin:4px 0">Parado: <b>%s</b> de %s con pedido abierto (%s %%). %s: %s.</p>' % (
            hm(par), hm(mins), num(mins and par * 100.0 / mins or 0), antes_txt.capitalize(), hm(par_a)))

        h.append(self._seccion_faltas(d['por_motivo'], d['por_ref'],
                                      semanal and 'Faltas de la semana' or 'Faltas del mes', n_refs=10))
        h.append(self._pie())
        if semanal:
            asunto = 'KOROSHI semana %s–%s · %s uds' % (desde.strftime('%d/%m'), hasta.strftime('%d/%m'), num(ue[0]))
        else:
            asunto = 'KOROSHI %s %d · %s uds' % (MESES[desde.month - 1], desde.year, num(ue[0]))
        v = var(ue[0], ua[0])
        if v is not None:
            asunto += ' · %s%s %% vs %s' % (v >= 0 and '+' or '−', num(abs(v)), antes_txt)
        return asunto, ''.join(h)

    @api.model
    def _semana_anterior(self, hoy):
        lunes = hoy - datetime.timedelta(days=hoy.weekday()) - datetime.timedelta(days=7)
        return (lunes, lunes + datetime.timedelta(days=6),
                lunes - datetime.timedelta(days=7), lunes - datetime.timedelta(days=1))

    @api.model
    def _mes_anterior(self, hoy):
        fin = hoy.replace(day=1) - datetime.timedelta(days=1)
        ini = fin.replace(day=1)
        fin_a = ini - datetime.timedelta(days=1)
        return ini, fin, fin_a.replace(day=1), fin_a

    @api.model
    def componer(self, tipo='diario', dia=None, recalcular=True):
        """(asunto, html) del informe. dia: el dia del diario, o un dia de la semana/mes SIGUIENTE al resumido."""
        dia = dia or self._hoy()
        if tipo == 'diario':
            return self.html_diario(self.datos_diario(dia, recalcular))
        if tipo == 'semanal':
            return self.html_periodo(self.datos_periodo(*self._semana_anterior(dia)), 'semanal')
        if tipo == 'mensual':
            return self.html_periodo(self.datos_periodo(*self._mes_anterior(dia)), 'mensual')
        raise UserError(_('Tipo de informe desconocido: %s') % tipo)

    # ================================================================== envio
    @api.model
    def _destinatarios(self):
        return ','.join(x.strip() for x in re.split(r'[,;\s]+', self._param('destinatarios') or '') if x.strip())

    @api.model
    def enviar(self, tipo='diario', dia=None, destinatarios=None):
        destinatarios = destinatarios or self._destinatarios()
        if not destinatarios:
            raise UserError(_('Faltan los correos: Ajustes KOROSHI › Informe de productividad (parámetro %s'
                              'destinatarios).') % P)
        asunto, cuerpo = self.componer(tipo, dia)
        servidor = self.env['ir.mail_server'].sudo().search([('name', '=', self._param('servidor', 'NATH'))], limit=1)
        empresa = self.env['res.company'].sudo().browse(COMPANY_ID)
        remitente = (servidor.smtp_user if servidor and '@' in (servidor.smtp_user or '') else '') \
            or empresa.email or self.env.user.email or ''
        mail = self.env['mail.mail'].sudo().create({
            'subject': asunto, 'email_from': remitente, 'email_to': destinatarios, 'body_html': cuerpo,
            'mail_server_id': servidor.id or False, 'auto_delete': False,
        })
        mail.send()
        return mail

    @api.model
    def _accion_enviado(self, mail):
        if self.env.user.has_group('base.group_system'):
            return {'type': 'ir.actions.act_window', 'name': _('Informe enviado'), 'res_model': 'mail.mail',
                    'res_id': mail.id, 'view_mode': 'form', 'target': 'new'}
        return {'type': 'ir.actions.act_window_close'}

    @api.model
    def action_enviar_diario(self):
        return self._accion_enviado(self.enviar('diario'))

    @api.model
    def action_enviar_semanal(self):
        return self._accion_enviado(self.enviar('semanal'))

    @api.model
    def action_enviar_mensual(self):
        return self._accion_enviado(self.enviar('mensual'))

    @api.model
    def _hora_param(self, clave, defecto):
        try:
            hh, mm = [int(x) for x in (self._param(clave, defecto) or defecto).split(':')]
            return hh, mm
        except ValueError:
            return [int(x) for x in defecto.split(':')]

    @api.model
    def _toca(self, clave_ultimo, periodo, hora_ok):
        """Marca y devuelve True si hay que mandar el informe de 'periodo'. La primera vez solo marca (al instalar no
        se manda el de la semana o el mes anterior)."""
        ultimo = self._param(clave_ultimo)
        if ultimo == periodo or not hora_ok:
            return False
        self._set(clave_ultimo, periodo)       # se marca antes: si el correo falla no se reintenta cada 15 min
        return bool(ultimo)

    @api.model
    def cron_informe(self):
        """Cada 15 min: cierra los dias acabados y manda lo que toque (diario, semanal el lunes, mensual el dia 1)."""
        try:
            with self.env.cr.savepoint():
                self.cerrar_dias()
        except Exception:
            _logger.exception('KOROSHI Informe: no se han podido cerrar los dias')
        ahora = self._ahora_local()
        hoy = ahora.date()
        hay_correos = bool(self._destinatarios())
        # diario
        if self._param('diario', '1') in ('1', 'True', 'true'):
            hh, mm = self._hora_param('hora_diario', '17:00')
            if self._param('ultimo_diario') != hoy.isoformat() and (ahora.hour, ahora.minute) >= (hh, mm):
                self._set('ultimo_diario', hoy.isoformat())
                hay = self.env['koroshi.operario.tarea'].sudo().search_count([('dia', '=', hoy)]) or \
                    self._cobertura(hoy, hoy)[0]
                if hay and hay_correos:
                    self._enviar_seguro('diario', hoy)
        hh, mm = self._hora_param('hora_resumen', '08:00')
        hora_ok = (ahora.hour, ahora.minute) >= (hh, mm)
        # semanal: la semana anterior, desde el lunes a esa hora
        if self._param('semanal', '1') in ('1', 'True', 'true'):
            lunes = self._semana_anterior(hoy)[0]
            if self._toca('ultimo_semanal', lunes.isoformat(), hora_ok or hoy.weekday() > 0) and hay_correos:
                self._enviar_seguro('semanal', hoy)
        # mensual: el mes anterior, desde el dia 1 a esa hora
        if self._param('mensual', '1') in ('1', 'True', 'true'):
            mes = self._mes_anterior(hoy)[0]
            if self._toca('ultimo_mensual', mes.isoformat()[:7], hora_ok or hoy.day > 1) and hay_correos:
                self._enviar_seguro('mensual', hoy)
        return True

    @api.model
    def _enviar_seguro(self, tipo, dia):
        try:
            with self.env.cr.savepoint():
                self.enviar(tipo, dia)
        except Exception:
            _logger.exception('KOROSHI Informe: no se ha podido mandar el informe %s', tipo)
