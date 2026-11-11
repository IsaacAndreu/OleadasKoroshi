# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Preparación en Lecturas (v3.4.0) - productividad al preparar a dos.
#
# koroshi_operarios cuenta las uds de una tarea como «uds leídas de la OUT al cerrar - al empezar». Con dos operarios
# en la misma OUT cada uno se contaría también lo del otro. Si en el tiempo de la tarea otro operario ha leído en esta
# pantalla la misma OUT, la tarea cuenta solo las lecturas propias (koroshi.preparacion.lectura, sin las deshechas).
# v3.4: marca la tarea «a dos» con el compañero (informes) y da las uds en curso al monitor de la misma forma.
# Solo escribe en koroshi.operario.tarea (uds_inicio / uds_fin / nota / a_dos / companero_id).
# =============================================================================
from odoo import fields, models


class KoroshiOperarioTarea(models.Model):
    _inherit = 'koroshi.operario.tarea'

    def _lecturas_a_dos(self, hasta):
        """(otros, propias): lecturas de otros operarios y las propias en esta OUT durante la tarea."""
        self.ensure_one()
        Lectura = self.env['koroshi.preparacion.lectura'].sudo()
        base = [('picking_id', '=', self.picking_id.id), ('tipo', '=', 'leer'), ('resultado', '=', 'ok'),
                ('fecha', '>=', self.inicio), ('fecha', '<=', hasta)]
        otros = Lectura.search(base + [('employee_id', '!=', False), ('employee_id', '!=', self.employee_id.id)])
        propias = Lectura.search(base + [('employee_id', '=', self.employee_id.id), ('deshecha', '=', False)])
        return otros, propias

    def _uds_hasta_ahora(self):
        if self.tipo == 'out' and self.picking_id and self.estado == 'curso':
            otros, propias = self._lecturas_a_dos(fields.Datetime.now())
            if otros:
                return sum(propias.mapped('cantidad'))
        return super(KoroshiOperarioTarea, self)._uds_hasta_ahora()

    def _cerrar(self, estado, motivo, fin=None):
        abiertas = self.filtered(lambda t: t.estado == 'curso' and t.tipo == 'out' and t.picking_id)
        res = super(KoroshiOperarioTarea, self)._cerrar(estado, motivo, fin)
        for t in abiertas:
            otros, propias = t._lecturas_a_dos(t.fin or fields.Datetime.now())
            if not otros:
                continue
            t.write({
                'uds_inicio': 0.0,
                'uds_fin': sum(propias.mapped('cantidad')),
                'a_dos': True,
                'companero_id': otros[:1].employee_id.id,
                'nota': ((t.nota or '') + ' Preparada a dos: cuenta solo sus lecturas.').strip(),
            })
        return res
