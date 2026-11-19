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
    @api.model
    def tablero_refrescar(self):
        """Lo de koroshi_operarios (zonas, agrupaciones, OUT, nota) y una pieza por actividad activa."""
        res = super(KoroshiOperarioAsignacionActividad,
                    self.with_context(koroshi_conservar_actividades=True)).tablero_refrescar()
        company = self.env.company
        Asig = self.sudo()
        actividades = self.env['koroshi.actividad'].sudo().search(
            ['|', ('company_id', '=', False), ('company_id', '=', company.id)])
        tengo = set()
        for pz in Asig.search([('estado', '=', 'pieza'), ('tipo', '=', 'actividad'), ('company_id', '=', company.id)]):
            if pz.actividad_id in actividades and pz.actividad_id.id not in tengo:
                tengo.add(pz.actividad_id.id)
            else:
                pz.unlink()   # actividad archivada, repetida o pieza recién dada (sin actividad_id)
        for i, act in enumerate(actividades):
            if act.id not in tengo:
                Asig.create({'tipo': 'actividad', 'actividad_id': act.id, 'estado': 'pieza', 'employee_id': False,
                             'origen': 'tablero', 'company_id': company.id, 'secuencia': 2 + i})
        return res

    def unlink(self):
        if self.env.context.get('koroshi_conservar_actividades'):
            # koroshi_operarios borra las piezas que no conoce: las de actividad las lleva este módulo
            self = self.filtered(lambda a: not (a.tipo == 'actividad' and a.estado == 'pieza'))
        return super(KoroshiOperarioAsignacionActividad, self).unlink()

    def _dar_pieza(self, emp_id, resto):
        """Al dar una actividad, la pieza que vuelve a «Por repartir» lleva también su actividad."""
        actividad = self.actividad_id
        res = super()._dar_pieza(emp_id, resto)
        if self.tipo == 'actividad' and actividad:
            nueva = self.sudo().search([('estado', '=', 'pieza'), ('tipo', '=', 'actividad'),
                                        ('actividad_id', '=', False), ('company_id', '=', self.company_id.id)],
                                       order='id desc', limit=1)
            nueva.write({'actividad_id': actividad.id})
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
