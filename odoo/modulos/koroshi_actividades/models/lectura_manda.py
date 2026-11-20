# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Actividades v1.8.0 - «la lectura manda» (entrada única de la PDA, fase 4; Isaac 20/11: sí).
# Diseño: bin/versiones/diseno-pda-entrada-unica_2026-11-20_v2.md
#
# El área en que se ha entrado en el Inicio puede quedarse vieja: alguien entra en Picking y se pone a compactar sin
# tocar nada. Cada 5 min, un cron mira las lecturas y corrige el tramo:
#   - leer en Lecturas / Preparación (tarea de picking en curso)  -> Picking
#   - mover un contenedor (koroshi_contenedores)                   -> Compactación
# Si la persona está en otra área, su tramo se cierra («Cambió de actividad») a la hora de la primera lectura nueva y
# se abre el del área de la lectura desde esa hora. Si estaba en pausa (o había acabado) y vuelve a leer, se le abre el
# tramo desde esa lectura.
# Solo a quien ya usa las áreas hoy (tiene algún tramo de hoy con área): a los demás no se les crea nada.
# Y en Picking y Compactación, sin lecturas en koroshi_actividades.minutos_sin_lecturas (15; 0 = nunca) el tramo se
# cierra a la hora de la última lectura (motivo «Sin lecturas»), como la tarea de picking por inactividad (operarios
# 2.19). Si vuelve a leer, el mismo cron lo abre otra vez desde esa lectura.
#
# Va por cron y no dentro de la lectura a propósito: si algo falla aquí, la PDA no se entera (la lectura no espera a
# este código ni puede romperse por él). Cada persona en su savepoint. Solo escribe en koroshi.actividad.registro.
# =============================================================================
import datetime
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

AREAS_CON_LECTURAS = ('picking', 'compactacion')
MINUTOS_SIN_LECTURAS = 15
VENTANA_CONTENEDORES = 15     # minutos hacia atrás en que se miran los movimientos de contenedor


class KoroshiActividadRegistroLectura(models.Model):
    _inherit = 'koroshi.actividad.registro'

    # ------------------------------------------------------------------ señales de lectura
    @api.model
    def _senales_lectura(self, ahora):
        """{employee_id: {'picking': (primera, ultima), 'compactacion': (primera, ultima)}} de las lecturas recientes.
        Picking: tareas en curso (inicio y última actividad). Compactación: movimientos de contenedor de los últimos
        VENTANA_CONTENEDORES min."""
        res = {}

        def poner(emp_id, area, primera, ultima):
            if not emp_id or not ultima:
                return
            d = res.setdefault(emp_id, {})
            p, u = d.get(area, (None, None))
            d[area] = (min(x for x in (p, primera or ultima) if x), max(x for x in (u, ultima) if x))

        Tarea = self.env['koroshi.operario.tarea'].sudo()
        for t in Tarea.search([('estado', '=', 'curso')]):
            poner(t.employee_id.id, 'picking', t.inicio, t._ultima_actividad() or t.inicio)
        if 'koroshi.contenedor.movimiento' in self.env:
            desde = ahora - datetime.timedelta(minutes=VENTANA_CONTENEDORES)
            for m in self.env['koroshi.contenedor.movimiento'].sudo().search(
                    [('employee_id', '!=', False), ('create_date', '>=', fields.Datetime.to_string(desde))]):
                poner(m.employee_id.id, 'compactacion', m.create_date, m.create_date)
        return res

    @api.model
    def _ultima_lectura_area(self, employee, area, desde):
        """Última lectura de la persona en un área con lecturas desde una hora (para el cierre «Sin lecturas»)."""
        fechas = []
        if area == 'picking':
            Tarea = self.env['koroshi.operario.tarea'].sudo()
            for t in Tarea.search([('employee_id', '=', employee.id), '|', ('estado', '=', 'curso'),
                                   ('fin', '>=', fields.Datetime.to_string(desde))]):
                fechas.append(t._ultima_actividad() if t.estado == 'curso' else (t.fin or t.inicio))
        elif area == 'compactacion' and 'koroshi.contenedor.movimiento' in self.env:
            m = self.env['koroshi.contenedor.movimiento'].sudo().search(
                [('employee_id', '=', employee.id), ('create_date', '>=', fields.Datetime.to_string(desde))],
                order='create_date desc', limit=1)
            if m:
                fechas.append(m.create_date)
        fechas = [f for f in fechas if f]
        return max(fechas) if fechas else None

    @api.model
    def _actividad_de_area(self, area, company):
        """La actividad con que se entra en un área por lectura: la primera activa de esa área que abre pantalla (en
        la 1.6.0, «Picking» y «Compactación»); si no hay, la primera del área."""
        Act = self.env['koroshi.actividad'].sudo()
        dom = [('area', '=', area), '|', ('company_id', '=', False), ('company_id', '=', company.id)]
        acts = Act.search(dom)
        return acts.filtered(lambda a: a.abre)[:1] or acts[:1]

    # ------------------------------------------------------------------ cron
    @api.model
    def cron_areas_por_lectura(self):
        ahora = fields.Datetime.now()
        hoy = self._hoy()
        senales = self._senales_lectura(ahora)
        hechos = set()
        for emp_id, areas in senales.items():
            emp = self.env['hr.employee'].sudo().browse(emp_id).exists()
            if not emp:
                continue
            try:
                with self.env.cr.savepoint():
                    self._seguir_lectura(emp, areas, hoy)
                    self.flush()
                hechos.add(emp_id)
            except Exception:
                _logger.exception('KOROSHI ACTIVIDADES: no se ha podido poner el área por lectura de %s', emp.name)
        try:
            with self.env.cr.savepoint():
                self._cerrar_sin_lecturas(ahora)
                self.flush()
        except Exception:
            _logger.exception('KOROSHI ACTIVIDADES: cierre de áreas sin lecturas')
        return True

    def _seguir_lectura(self, emp, areas, hoy):
        """Pone a la persona en el área de su lectura más reciente, si usa las áreas hoy."""
        area, (primera, ultima) = max(areas.items(), key=lambda x: x[1][1])
        tramos_hoy = self.search([('employee_id', '=', emp.id), ('dia', '=', hoy), ('area', '!=', False)],
                                 order='inicio desc, id desc')
        if not tramos_hoy:
            return    # no usa las áreas hoy: no se le crea nada
        abierto = self.abierto_de(emp)
        if abierto and abierto.area == area:
            if not abierto.confirmado or ultima > abierto.confirmado:
                abierto.write({'confirmado': ultima})    # leer es dar señal («¿Sigues?»)
            return
        referencia = abierto.inicio if abierto else (tramos_hoy[0].fin or tramos_hoy[0].inicio)
        if abierto and abierto.confirmado and abierto.confirmado > referencia:
            referencia = abierto.confirmado
        if ultima <= referencia:
            return    # la lectura es anterior a entrar en el área actual (o a la pausa): manda el área elegida
        act = self._actividad_de_area(area, emp.company_id or self.env.company)
        if not act:
            return
        # desde la primera lectura nueva; si la tarea ya venía de antes de entrar en el área actual, no se sabe cuándo
        # volvió a leer: desde la última lectura (como mucho se pierden unos minutos de picking, nunca se inventan)
        desde = primera if primera > referencia else ultima
        if abierto:
            abierto._cerrar('cambio', desde)
            self.flush()
        nuevo = self.create({'employee_id': emp.id, 'actividad_id': act.id, 'inicio': desde, 'confirmado': ultima,
                             'company_id': act.company_id.id or emp.company_id.id or self.env.company.id,
                             'nota': 'Por lectura'})
        _logger.info('KOROSHI ACTIVIDADES: %s pasa a %s por lectura (desde %s)', emp.name, act.name, desde)
        return nuevo

    def _cerrar_sin_lecturas(self, ahora):
        minutos = self._minutos_param('minutos_sin_lecturas', MINUTOS_SIN_LECTURAS)
        if minutos <= 0:
            return
        limite = ahora - datetime.timedelta(minutes=minutos)
        for r in self.search([('estado', '=', 'curso'), ('area', 'in', AREAS_CON_LECTURAS),
                              ('inicio', '<', fields.Datetime.to_string(limite))]):
            ultima = self._ultima_lectura_area(r.employee_id, r.area, r.inicio)
            if ultima and ultima >= limite:
                continue
            # sin ninguna lectura desde que entró: se cierra a la hora de entrar (0 min), como la tarea sin lecturas
            r._cerrar('sin_lecturas', max(ultima or r.inicio, r.inicio))
            _logger.info('KOROSHI ACTIVIDADES: %s sin lecturas en %s desde %s: tramo cerrado',
                         r.employee_id.name, r.area, ultima or r.inicio)
