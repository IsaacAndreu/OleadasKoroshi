# -*- coding: utf-8 -*-
# v2.4.1: al actualizar (el servidor viene de la 2.1.0), el usuario «Almacen 2» entra en el grupo del icono de la
# bandeja. Al instalar de cero lo hace post_init_hook (__init__.py).
import logging

from odoo import SUPERUSER_ID, api
from odoo.addons.koroshi_menu import dar_bandeja_en_apps

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    usuario = dar_bandeja_en_apps(api.Environment(cr, SUPERUSER_ID, {}))
    _logger.info('KOROSHI Menú 2.4.1: icono de la bandeja en Aplicaciones para %s',
                 usuario and usuario.login or 'nadie (no existe almacen2@nath.es)')
