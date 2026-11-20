# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Actividades v1.5.0 - tarjetas de actividad en el tablero del responsable (koroshi_operarios 2.20.0).
# Diseño: bin/versiones/diseno-tablero-responsable_2026-11-19_v5.md
#
# El responsable (Almacén 2) arrastra «Manipulación devoluciones» (o cualquier actividad activa) a la columna de
# un operario. Cuando le toca, su PDA no abre nada: «Ve al portátil de Actividades». La tarjeta se acaba cuando la
# persona pulsa «Fin» en el portátil (registro.acabar). Cambiar a otra actividad o la pausa no la acaban.
# Como las notas, la tarjeta nunca está 'curso' (sigue 'cola' hasta el Fin): no cuenta como pedido ni abre tarea de
# productividad. Solo la tabla propia de asignaciones (koroshi_operarios); nada en stock.*.
# v1.6.0: ya no se crean piezas de actividad (tablero por áreas); _tablero_areas() da el área del tramo abierto.
# =============================================================================
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class KoroshiOperarioAsignacionActividad(models.Model):
    _inherit = 'koroshi.operario.asignacion'

    tipo = fields.Selection(selection_add=[('actividad', 'Actividad (portátil)')])
    actividad_id = fields.Many2one('koroshi.actividad', 'Actividad', index=True, ondelete='cascade')

    @api.depends('tipo', 'picking_id', 'batch_id', 'texto', 'actividad_id')
    def _compute_name(self):
        super()._compute_name()
        for a in self.filtered(lambda x: x.tipo == 'actividad'):
            a.name = a.actividad_id.name or _('Actividad')

    def _pickings(self):
        self.ensure_one()
        if self.tipo == 'actividad':
            return self.env['stock.picking']
        return super()._pickings()

    def _terminada(self):
        """Una actividad solo se acaba con «Fin» en el portátil (sin pedidos, la de siempre la daría por hecha)."""
        self.ensure_one()
        if self.tipo == 'actividad':
            return False
        return super()._terminada()

    def _empezar(self, employee):
        """siguiente() llama a _empezar con lo primero de la cola: una actividad no abre tarea de productividad ni
        pasa a 'curso' (el tiempo lo cuenta el portátil). La PDA la enseña y espera al Fin."""
        if self.tipo == 'actividad':
            return self.env['koroshi.operario.tarea']
        return super()._empezar(employee)

    def json(self):
        res = super().json()
        if self.tipo == 'actividad':
            res['tienda'] = _('Ve al portátil de Actividades')
        return res

    # ------------------------------------------------------------------ piezas del tablero
    # v1.6.0: fuera las piezas de actividad en «Por repartir» (tablero por áreas, koroshi_operarios 2.23.0, diseño
    # diseno-pda-entrada-unica_2026-11-20_v2.md: las actividades ya no se asignan; cada uno entra en su área en la PDA).
    # Sin tablero_refrescar propio, el de koroshi_operarios borra las piezas de actividad que queden. Las tarjetas que
    # ya estaban dadas (en cola) siguen funcionando hasta su Fin (_pickings, _terminada, _empezar, json).

    # ------------------------------------------------------------------ v1.6.0: en qué área está cada uno
    @api.model
    def _tablero_areas(self, empleados):
        """Tablero por áreas (koroshi_operarios 2.23.0): el área del tramo abierto de cada persona (la que eligió en
        el Inicio de la PDA o en el portátil) en vez de adivinarla por el nombre de la actividad. Lo demás (tarea de
        picking en curso, Contenedores en 15 min) sigue como lo calcula koroshi_operarios; gana la señal más
        reciente, como allí. Con koroshi_operarios anterior a la 2.23.0 este método no lo llama nadie."""
        padre = getattr(super(KoroshiOperarioAsignacionActividad, self), '_tablero_areas', None)
        res = padre(empleados) if padre else {}
        if not empleados:
            return res
        Reg = self.env['koroshi.actividad.registro'].sudo()
        for r in Reg.search([('employee_id', 'in', empleados.ids), ('estado', '=', 'curso')]):
            if not r.actividad_id.area:
                continue
            senal = max([d for d in (r.inicio, r.confirmado) if d])
            emp_id = r.employee_id.id
            actual = res.get(emp_id)
            # el tramo manda sobre lo que koroshi_operarios dedujo del mismo tramo (por el nombre); otra señal más
            # reciente (leer una OUT, mover un contenedor) gana
            if actual and actual.get('desde') and actual['desde'] > senal and actual.get('detalle') != r.actividad_id.name:
                continue
            res[emp_id] = {'area': r.actividad_id.area, 'desde': senal, 'detalle': r.actividad_id.name or ''}
        return res

    # ------------------------------------------------------------------ el Fin del portátil
    @api.model
    def actividad_acabada(self, employee, actividad):
        """«Fin» en el portátil: la tarjeta de actividad de esta persona (la de esa actividad o, si no hay, la primera)
        pasa a hecha. La PDA lo ve en la siguiente consulta y pasa a lo siguiente."""
        cartas = self.sudo().search([('employee_id', '=', employee.id), ('tipo', '=', 'actividad'),
                                     ('estado', '=', 'cola')], order='secuencia asc, id asc')
        carta = cartas.filtered(lambda a: a.actividad_id == actividad)[:1] or cartas[:1]
        if carta:
            carta.write({'estado': 'hecha'})
        return carta
