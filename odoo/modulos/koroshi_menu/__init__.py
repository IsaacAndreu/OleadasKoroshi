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


GRUPO_S4T = 'api_s4t_batch_update_PROD.group_s4t_integration_user'   # v2.5.1: «S4T API / User» (módulo de Effective)


def dar_s4t(env):
    """v2.5.1: los jefes de almacén entran en «S4T API / User» para ver lo de la integración S4T (matrículas de caja,
    packing feed). «Almacén Nath» ya lo tiene. Solo añade; si el módulo S4T no está, no hace nada."""
    s4t = env.ref(GRUPO_S4T, raise_if_not_found=False)
    jefes = env.ref('koroshi_menu.grupo_jefes', raise_if_not_found=False)
    if not s4t or not jefes:
        return env['res.users']
    nuevos = jefes.users - s4t.users
    if nuevos:
        s4t.write({'users': [(4, u.id) for u in nuevos]})
    return nuevos


USUARIO_IT = 'departamentit@nath.es'   # v2.6: ve la pestaña IT de la bandeja


def dar_it(env):
    """v2.6: mete a «Departament IT» en «KOROSHI: IT» (la pestaña IT de la bandeja). Solo añade."""
    grupo = env.ref('koroshi_menu.grupo_it', raise_if_not_found=False)
    usuario = env['res.users'].with_context(active_test=False).search([('login', '=', USUARIO_IT)], limit=1)
    if grupo and usuario and usuario not in grupo.users:
        grupo.write({'users': [(4, usuario.id)]})
    return usuario


USUARIO_PICKING = 'almacen@nath.es'   # v2.5: «Almacén Nath», el usuario de las PDA y el picking: NO es jefe


def dar_jefes(env):
    """v2.5: mete en «KOROSHI: Jefes de almacén» a todos los usuarios internos activos de la empresa 8 con Inventario,
    menos el de picking. Solo añade (no quita a nadie). Devuelve los que ha añadido."""
    grupo = env.ref('koroshi_menu.grupo_jefes', raise_if_not_found=False)
    inventario = env.ref('stock.group_stock_user', raise_if_not_found=False)
    if not grupo or not inventario:
        return env['res.users']
    usuarios = env['res.users'].search([('share', '=', False), ('company_ids', 'in', [8]),
                                        ('groups_id', 'in', [inventario.id]), ('login', '!=', USUARIO_PICKING)])
    nuevos = usuarios - grupo.users
    if nuevos:
        grupo.write({'users': [(4, u.id) for u in nuevos]})
    return nuevos


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    dar_bandeja_en_apps(env)
    dar_jefes(env)
    dar_s4t(env)   # v2.5.1
    dar_it(env)    # v2.6.0


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for xmlid in MENUS_ANTES:
        menu = env.ref(xmlid, raise_if_not_found=False)
        if menu:
            menu.write({'active': True})
    # v2.1: vuelven los iconos de aplicaciones que se ocultaron (models/apps.py)
    menus_apps_ocultas(env).write({'active': True})
