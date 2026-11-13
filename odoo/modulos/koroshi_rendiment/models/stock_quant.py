# -*- coding: utf-8 -*-
from odoo import api, models

SALTAR = 'koroshi_saltar_quant_tasks'


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def _get_quants_action(self, domain=None, extend=False):
        # stock/models/stock_quant.py:616 llama a _quant_tasks() en cada clic: GROUP BY sobre
        # toda stock_quant (1,46 M filas) + borrado de quants a cero = ~3,5 s por clic.
        action = super(StockQuant, self.with_context(**{SALTAR: True}))._get_quants_action(
            domain=domain, extend=extend)
        # Que la marca no viaje al cliente dentro del contexto de la accion.
        if isinstance(action.get('context'), dict):
            action['context'].pop(SALTAR, None)
        return action

    @api.model
    def _quant_tasks(self):
        # El planificador (stock/models/stock_rule.py:492) llama sin la marca: sigue fusionando.
        if self.env.context.get(SALTAR):
            return
        return super(StockQuant, self)._quant_tasks()
