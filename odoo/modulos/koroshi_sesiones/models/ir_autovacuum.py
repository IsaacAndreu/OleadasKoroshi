# -*- coding: utf-8 -*-
# v1.0.0 (17/11/2026): el auto-vacuum diario de Odoo borra las sesiones SIN usuario de mas de 7 dias (ver sesiones.py).
import logging

from odoo import api, models

from .. import sesiones

_logger = logging.getLogger(__name__)


class IrAutovacuum(models.AbstractModel):
    _inherit = 'ir.autovacuum'

    @api.model
    def power_on(self, *args, **kwargs):
        res = super(IrAutovacuum, self).power_on(*args, **kwargs)
        try:
            from odoo import http
            borradas, con_usuario, revisadas = sesiones.limpiar_sesiones(http.root.session_store)
            _logger.info('KOROSHI Sesiones: %d sesiones sin usuario borradas; %d con usuario de mas de %d dias se '
                         'quedan (%d revisadas)', borradas, con_usuario, sesiones.DIAS_SIN_USUARIO, revisadas)
        except Exception:
            _logger.exception('KOROSHI Sesiones: no se han podido limpiar las sesiones sin usuario')
        return res
