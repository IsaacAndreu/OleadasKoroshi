# -*- coding: utf-8 -*-
from odoo import api, models

SALTAR = 'tuctuc_saltar_quant_tasks'


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def _get_quants_action(self, domain=None, extend=False):
        # odoo13/addons/stock/models/stock_quant.py:616 llama a _quant_tasks() en cada clic del boton Stock:
        # _merge_quants (:518, GROUP BY sobre los 6,5 M quants y UPDATE/DELETE) y _unlink_zero_quants (:502).
        # Medido en tuctuc el 23/11/2026 con los SELECT equivalentes: 9,4 s + 2,3 s por clic, y escribe.
        action = super(StockQuant, self.with_context(**{SALTAR: True}))._get_quants_action(
            domain=domain, extend=extend)
        # Que la marca no viaje al cliente dentro del contexto de la accion.
        if isinstance(action.get('context'), dict):
            action['context'].pop(SALTAR, None)
        return action

    @api.model
    def _quant_tasks(self):
        # El planificador (stock/models/stock_rule.py:492) y custom_addons/procurement_ext
        # (procurement_group.py:72) llaman sin la marca: siguen fusionando y borrando quants a cero.
        if self.env.context.get(SALTAR):
            return
        return super(StockQuant, self)._quant_tasks()
