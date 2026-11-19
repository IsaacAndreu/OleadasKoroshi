# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Operarios v2.21.0 - Tablero del responsable: pantalla con cinco formatos (A-E) para elegir.
# Maqueta: bin/versiones/tablero-responsable-formatos_2026-11-19.html
#
# Es la misma cola y las mismas reglas del tablero 2.20.0 (models/tablero.py): aquí solo se leen los datos en una
# llamada (tablero_datos) y se mueve una tarjeta (tablero_mover, que pasa por el write() del tablero con su
# comprobación de grupo). La pantalla (static/src/js/tablero_formatos.js) pinta los datos de cinco maneras; el jefe
# elige una y en la versión siguiente se quitan las otras. Solo lee y escribe la tabla propia de asignaciones.
# =============================================================================
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.addons.koroshi_base import comun

from .tablero import GRUPO_TABLERO, RE_ZONA

_logger = logging.getLogger(__name__)


def _iniciales(nombre):
    partes = [p for p in (nombre or '').split() if p]
    if not partes:
        return '?'
    if len(partes) == 1:
        return partes[0][:2].upper()
    return (partes[0][0] + partes[1][0]).upper()


class KoroshiOperarioAsignacionFormatos(models.Model):
    _inherit = 'koroshi.operario.asignacion'

    def _comprobar_tablero(self):
        if not self.env.user.has_group(GRUPO_TABLERO):
            raise UserError(_('Solo el responsable (grupo «KOROSHI: Tablero del responsable») ve el tablero.'))

    def _tarjeta_json(self):
        a = self
        return {
            'id': a.id, 'tipo': a.tipo, 'estado': a.estado, 'nombre': (a.name or '').replace('EFFEC/', ''),
            'sub': (a.tienda or '') if a.tipo == 'out' else '', 'pct': a.prog_pct or 0, 'prog': a.prog_texto or '',
            'tambien': a.tambien or '', 'batch_id': a.batch_id.id or False,
            'zona': (a.batch_id.name or '') if a.tipo in ('lote', 'agrupacion') or a.tarjeta_id else '',
            'texto': (a.texto or '') if a.tipo == 'nota' else '',
        }

    @api.model
    def tablero_datos(self, refrescar=False):
        """Todo lo que pinta la pantalla de formatos, en una llamada. No escribe nada salvo con refrescar
        (recalcula «Por repartir», como el botón «Actualizar» del tablero)."""
        self._comprobar_tablero()
        if refrescar:
            self.tablero_refrescar()
        company = self.env.company
        Asig = self.sudo().with_context(koroshi_tablero=True)
        desde = comun.inicio_dia_utc(comun.hoy_local())
        cartas = Asig.search([('company_id', '=', company.id), '|', ('estado', 'in', ('pieza', 'cola', 'curso')),
                              '&', '&', ('estado', '=', 'hecha'), ('tipo', 'in', ('lote', 'nota')),
                              ('write_date', '>=', fields.Datetime.to_string(desde))],
                             order='secuencia asc, id asc')
        operarios = Asig._expandir_operarios(self.env['hr.employee'], [], None)
        operarios |= cartas.mapped('employee_id')
        operarios = operarios.sorted(lambda e: (e.name or '').lower())

        # uds de hoy y quién está parado ahora (la misma cifra que Productividad y el Monitor)
        uds, parado_min, en_curso = {}, {}, {}
        try:
            Tarea = self.env['koroshi.operario.tarea'].sudo()
            ops, _huecos, _parados = Tarea.resumen_operario_dia(comun.hoy_local())
            for emp_id, o in ops.items():
                uds[emp_id] = int(round(o['uds']))
            umbral = Tarea._minutos_sin_leer_max()
            for t in Tarea.search([('estado', '=', 'curso'), ('employee_id', 'in', operarios.ids)]):
                en_curso[t.employee_id.id] = True
                minutos = t._minutos_sin_leer()
                if minutos >= umbral:
                    parado_min[t.employee_id.id] = int(minutos)
        except Exception:   # solo informativo: nunca rompe el tablero
            _logger.exception('KOROSHI OPERARIOS tablero formatos: uds y parados')

        por_emp = {}
        piezas = {'zonas': [], 'actividades': [], 'notas': [], 'outs': []}
        for c in cartas:
            j = c._tarjeta_json()
            if c.estado == 'pieza':
                if c.tipo in ('lote', 'agrupacion'):
                    piezas['zonas'].append(j)
                elif c.tipo == 'actividad':
                    piezas['actividades'].append(j)
                elif c.tipo == 'nota':
                    piezas['notas'].append(j)
                else:
                    piezas['outs'].append(j)
            elif c.employee_id:
                por_emp.setdefault(c.employee_id.id, []).append((c, j))

        res_ops = []
        for e in operarios:
            lista = por_emp.get(e.id, [])
            vivas = [j for c, j in lista if c.estado in ('cola', 'curso')]
            ahora = next((j for c, j in lista if c.estado == 'curso'), None)
            if not ahora and vivas and vivas[0]['tipo'] == 'actividad':
                ahora = vivas[0]
            if e.id in parado_min:
                estado, texto = 'parado', _('parado %s min') % parado_min[e.id]
            elif e.id in en_curso:
                estado, texto = 'leyendo', _('leyendo')
            elif ahora and ahora['tipo'] == 'actividad':
                estado, texto = 'actividad', _('en el portátil')
            else:
                estado, texto = 'libre', _('sin tarea') if not vivas else _('esperando')
            res_ops.append({
                'id': e.id, 'nombre': e.name or '', 'ini': _iniciales(e.name), 'uds': uds.get(e.id, 0),
                'estado': estado, 'estado_texto': texto,
                'ahora': ahora,
                'cola': [j for j in vivas if not ahora or j['id'] != ahora['id']],
                'hechas': [j for c, j in lista if c.estado == 'hecha'],
            })

        # resumen por zona/agrupación: las que están por repartir o en la columna de alguien
        zonas = {}
        for c in cartas.filtered(lambda x: x.tipo in ('lote', 'agrupacion') and x.batch_id
                                 and x.estado in ('pieza', 'cola', 'curso')):
            z = zonas.setdefault(c.batch_id.id, {
                'batch_id': c.batch_id.id, 'nombre': c.batch_id.name or '', 'pct': c.prog_pct or 0,
                'prog': c.prog_texto or '', 'pieza_id': False, 'gente': [],
                'es_zona': bool(RE_ZONA.match(c.batch_id.name or '')),
            })
            if c.estado == 'pieza':
                z['pieza_id'] = c.id
                z['pct'], z['prog'] = c.prog_pct or 0, c.prog_texto or z['prog']
            elif c.employee_id and c.employee_id.id not in [g['id'] for g in z['gente']]:
                z['gente'].append({'id': c.employee_id.id, 'ini': _iniciales(c.employee_id.name),
                                   'nombre': c.employee_id.name or ''})
        # quien hace ahora una OUT de una zona también está en ella
        for c in cartas.filtered(lambda x: x.tipo == 'out' and x.estado == 'curso' and x.batch_id):
            z = zonas.get(c.batch_id.id)
            if z and c.employee_id.id not in [g['id'] for g in z['gente']]:
                z['gente'].append({'id': c.employee_id.id, 'ini': _iniciales(c.employee_id.name),
                                   'nombre': c.employee_id.name or ''})
        lista_zonas = sorted(zonas.values(), key=lambda z: (not z['es_zona'], z['nombre']))

        return {
            'operarios': res_ops, 'piezas': piezas, 'zonas': lista_zonas,
            'hora': comun.ahora_local().strftime('%H:%M'),
            'form_id': self.env.ref('koroshi_operarios.view_koroshi_tablero_form').id,
        }

    @api.model
    def tablero_mover(self, asignacion_id, employee_id, primero=False):
        """Mueve una tarjeta como el kanban: pieza -> operario = se le da; cola -> otro operario = se cambia;
        a «Por repartir» (employee_id False) = Quitar. Con primero, queda la primera de su cola (reforzar ya).
        Devuelve la tarjeta que queda en la columna del operario (para abrir la nota y escribirla)."""
        self._comprobar_tablero()
        carta = self.browse(int(asignacion_id)).exists()
        if not carta:
            raise UserError(_('Esa tarjeta ya no existe. Pulsa «Actualizar».'))
        carta.with_context(koroshi_tablero=True).write({'employee_id': employee_id or False})
        if employee_id and primero and carta.estado == 'cola':
            carta.sudo().action_subir()
        return {'id': carta.id, 'tipo': carta.tipo, 'estado': carta.estado}

    @api.model
    def tablero_clasico(self):
        """El tablero kanban de la 2.20.0 (botón «Clásico» de la pantalla de formatos)."""
        self._comprobar_tablero()
        return self.action_abrir_tablero()
