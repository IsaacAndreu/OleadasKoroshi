# -*- coding: utf-8 -*-
# v2.6.0: «Departament IT» entra en «KOROSHI: IT», el grupo que ve la pestaña IT de la bandeja del encargado.
import logging

from odoo import SUPERUSER_ID, api
from odoo.addons.koroshi_menu import dar_it

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    usuario = dar_it(api.Environment(cr, SUPERUSER_ID, {}))
    _logger.info('KOROSHI Menú 2.6.0: grupo IT para %s', usuario.login or 'nadie (no existe el usuario)')
