# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api

from . import models
from .models.apps import menus_apps_ocultas

# Menús de antes que este módulo archiva (views/menu.xml). Al desinstalar, vuelven.
MENUS_ANTES = [
    'koroshi_kpi.menu_koroshi_kpi_root',
    'koroshi_operarios.menu_koroshi_operarios_root',
    'koroshi_zonas.menu_koroshi_zonas_root',
    'koroshi_warehouse_map.menu_koroshi_warehouse_root',
    'koroshi_faltantes.menu_koroshi_faltantes_root',
    'koroshi_kpi.menu_koroshi_hoja_carga',
]


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for xmlid in MENUS_ANTES:
        menu = env.ref(xmlid, raise_if_not_found=False)
        if menu:
            menu.write({'active': True})
    # v2.1: vuelven los iconos de aplicaciones que se ocultaron (models/apps.py)
    menus_apps_ocultas(env).write({'active': True})
