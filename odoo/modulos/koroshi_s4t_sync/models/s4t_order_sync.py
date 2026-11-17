# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Sync S4T con OUT canceladas v1.0.0 (17/11/2026)
#
# action_sync_order de Effective comprueba sale_order.picking_ids.mapped('state'): todas en 'done' y todas iguales.
# Con una backorder cancelada no pasa nunca. Aqui, si las canceladas son lo unico que no esta hecho, se le pasa el
# pedido viendo solo las no canceladas (env.cache, sin escribir en la base de datos) y se llama al de Effective.
# =============================================================================
import logging

from odoo import models

_logger = logging.getLogger(__name__)


def solo_canceladas_bloquean(estados):
    """True si las transferencias no hechas son todas canceladas y hay alguna hecha.
    estados: lista de estados de picking_ids."""
    hechas = [e for e in estados if e == 'done']
    canceladas = [e for e in estados if e == 'cancel']
    return bool(hechas) and bool(canceladas) and len(hechas) + len(canceladas) == len(estados)


class S4tOrderSync(models.Model):
    _inherit = 's4t.order.sync'

    def action_sync_order(self, sale_order):
        todas = sale_order.picking_ids
        if not solo_canceladas_bloquean(todas.mapped('state')):
            return super().action_sync_order(sale_order)
        vivas = todas.filtered(lambda p: p.state != 'cancel')
        _logger.info('KOROSHI S4T: %s se envia sin sus %d transferencias canceladas (%s)',
                     sale_order.name, len(todas - vivas), ', '.join((todas - vivas).mapped('name')))
        campo = sale_order._fields['picking_ids']
        self.env.cache.set(sale_order, campo, tuple(vivas.ids))
        try:
            return super().action_sync_order(sale_order)
        finally:
            sale_order.invalidate_cache(['picking_ids'], sale_order.ids)
