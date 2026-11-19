# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Pedidos S4T grandes - paso 1: crear y guardar el pedido (job de Effective, con candado).
#
# action_create_sale_order de Effective (api_s4t_batch_update_PROD/models/s4t_order_feed.py:56) crea el pedido,
# llama a action_confirm (:218) y deja el feed en 'done' con su sale_order_id (:222-224), todo en una transaccion.
# Aqui:
#   - un candado por feed: nunca corren dos copias del mismo feed a la vez (19/11: el cron 192 y un reencolado a mano
#     dejaron dos copias que se tumbaron entre ellas en cada reintento);
#   - si el feed ya tiene pedido (otra copia lo guardo), esta no hace nada y el job acaba bien;
#   - en pedidos b2b, el contexto koroshi_confirmar_diferido hace que sale.order.action_confirm deje los grandes
#     para otro job (models/sale_order.py);
#   - commit al acabar: el pedido queda guardado aunque luego choque la escritura de queue_job en su fila.
# =============================================================================
import logging

from odoo import models

from .. import logica
from .comun_jobs import candado, guardar

_logger = logging.getLogger(__name__)


class S4tOrderFeed(models.Model):
    _inherit = 's4t.order.feed'

    def action_create_sale_order(self):
        self.ensure_one()
        que = 'Feed %s' % (self.s4t_order_number or self.id)
        with candado(self.env.cr, logica.CLAVE_FEED, self.id, que):
            if self.state == 'done' and self.sale_order_id:
                _logger.info('KOROSHI S4T: %s ya tiene el pedido %s; esta copia del job no hace nada',
                             que, self.sale_order_id.name)
                return True
            diferir = self.s4t_mode == 'b2b'
            res = super(S4tOrderFeed, self.with_context(koroshi_confirmar_diferido=diferir)).action_create_sale_order()
            guardar(self.env)
            return res
