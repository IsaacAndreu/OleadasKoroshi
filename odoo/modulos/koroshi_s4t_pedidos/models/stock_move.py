# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Pedidos S4T grandes - confirmar sin reservar.
#
# Solo con el contexto koroshi_sin_reservar=True, que pone el job «S4T Confirmar pedido» (models/sale_order.py) y
# nadie mas: la PDA, las oleadas, «Comprobar disponibilidad» y los crons reservan como siempre.
# No anade campos.
# =============================================================================
from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_assign(self):
        if self.env.context.get('koroshi_sin_reservar'):
            return
        return super()._action_assign()
