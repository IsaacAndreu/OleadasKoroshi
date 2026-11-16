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


USUARIO_BANDEJA = 'almacen2@nath.es'   # v2.4.1: «Almacen 2» ve el icono de la bandeja en Aplicaciones


def dar_bandeja_en_apps(env):
    """v2.4.1: mete al usuario «Almacen 2» en el grupo del icono de la bandeja (si existe y no está ya)."""
    grupo = env.ref('koroshi_menu.grupo_bandeja_app', raise_if_not_found=False)
    usuario = env['res.users'].with_context(active_test=False).search([('login', '=', USUARIO_BANDEJA)], limit=1)
    if grupo and usuario and usuario not in grupo.users:
        grupo.write({'users': [(4, usuario.id)]})
    return usuario


def post_init_hook(cr, registry):
    dar_bandeja_en_apps(api.Environment(cr, SUPERUSER_ID, {}))


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for xmlid in MENUS_ANTES:
        menu = env.ref(xmlid, raise_if_not_found=False)
        if menu:
            menu.write({'active': True})
    # v2.1: vuelven los iconos de aplicaciones que se ocultaron (models/apps.py)
    menus_apps_ocultas(env).write({'active': True})
