# -*- coding: utf-8 -*-
# v2.5.1: los jefes de almacén entran en «S4T API / User» (ven matrículas de caja y packing feed de S4T). Va después de
# la migración 13.0.2.5.0 (que mete a los jefes), así que desde la 2.4.2 corren las dos, en orden.
import logging

from odoo import SUPERUSER_ID, api
from odoo.addons.koroshi_menu import dar_s4t

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    nuevos = dar_s4t(api.Environment(cr, SUPERUSER_ID, {}))
    _logger.info('KOROSHI Menú 2.5.1: S4T API / User para jefes: %s', ', '.join(nuevos.mapped('login')) or 'ninguno nuevo')
