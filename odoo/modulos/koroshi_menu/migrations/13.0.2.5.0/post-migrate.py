# -*- coding: utf-8 -*-
# v2.5.0: al actualizar, los usuarios internos de la empresa 8 con Inventario (menos «Almacén Nath», el del picking)
# entran en «KOROSHI: Jefes de almacén». Al instalar de cero lo hace post_init_hook (__init__.py).
import logging

from odoo import SUPERUSER_ID, api
from odoo.addons.koroshi_menu import dar_jefes

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    nuevos = dar_jefes(api.Environment(cr, SUPERUSER_ID, {}))
    _logger.info('KOROSHI Menú 2.5.0: jefes de almacén: %s', ', '.join(nuevos.mapped('login')) or 'ninguno nuevo')
