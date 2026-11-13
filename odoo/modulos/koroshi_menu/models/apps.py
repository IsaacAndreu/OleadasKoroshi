# -*- coding: utf-8 -*-
# =============================================================================
# v2.1: pantalla de aplicaciones más limpia. Archiva (active = False) los iconos de aplicaciones que no se usan en
# NATH: no los ve nadie, tampoco los administradores. NO desinstala nada: los módulos, sus datos y sus crons siguen
# igual; solo desaparece el icono (y con él sus menús). Al desinstalar koroshi_menu vuelven (ver __init__.py).
#
# Lista acordada con Isaac el 13/11/2026: sin registros en los últimos 90 días, o integraciones que no se usan.
# Se quedan: Sorter Batches, Integración S4T, Koroshi Zebra y Job Queue (la usa S4T).
#
# Se ejecuta en cada instalación y actualización de koroshi_menu (views/apps.xml, <function> sin noupdate).
# Si una aplicación no está instalada, se salta sin error.
# =============================================================================
from odoo import api, models

# Menús raíz por id externo
APPS_OCULTAS = [
    'calendar.mail_menu_calendar',                                    # Calendario
    'crm.crm_menu_root',                                              # CRM
    'website.menu_website_configuration',                             # Sitio web
    'whatsapp_integration_gtica.gtica_whatsapp_template_menu_root',   # Whatsapp Templates
    'iot.iot_menu_root',                                              # IoT
    'odoo_multi_channel_sale.parent_menu_multi_channel',              # Multi-Channel
    'eci_mirakl.parent_eci_mirakl',                                   # MiraKL
    'bs_app_management.mobile_app_menu',                              # Mobile App
    'bs_ECI_Sales.eci_sales_root',                                    # ECI Sales
    'odoo_pink_connect.parent_pink_connect',                          # PinkConnect
    'integration.menu_sale_integration',                              # e-Commerce Integration
    'barcode_excel_module.menu_barcode_excel_root',                   # Barcode Excel
    'point_of_sale.menu_point_root',                                  # Punto de venta
    'helpdesk.menu_helpdesk_root',                                    # Ayuda
    'planning.planning_menu_root',                                    # Planificación
    'utm.menu_link_tracker_root',                                     # Rastr. enlaces
    'mrp.menu_mrp_root',                                              # Fabricación
    'account_consolidation.menu_consolidation',                       # Consolidación
    'project.menu_main_pm',                                           # Proyecto
    'mass_mailing.mass_mailing_menu_root',                            # Marketing por email
    'hr_attendance.menu_hr_attendance_root',                          # Asistencias
    'maintenance.menu_maintenance_title',                             # Mantenimiento
    'base.menu_board_root',                                           # Tableros
]

# Menús raíz creados a mano en el servidor (sin id externo): id de base de datos y nombre (en inglés) que debe tener.
# Solo se tocan si el id y el nombre coinciden, para no archivar otra cosa por error.
APPS_OCULTAS_SIN_XMLID = [
    (857, 'SQL Views(1)'),        # SQL Views (creado por Victor Pedraza, 17/08/2023)
    (1178, 'Warehouse Planner'),  # Warehouse Planner (enlace a un artifact, creado por Departament IT, 22/04/2026)
]


def menus_apps_ocultas(env):
    """Menús raíz de APPS_OCULTAS y APPS_OCULTAS_SIN_XMLID que existen en esta base de datos (activos o no)."""
    Menu = env['ir.ui.menu'].with_context(active_test=False, lang='en_US')
    menus = Menu.browse()
    for xmlid in APPS_OCULTAS:
        menu = env.ref(xmlid, raise_if_not_found=False)
        if menu and menu._name == 'ir.ui.menu' and not menu.parent_id:
            menus |= menu
    for menu_id, nombre in APPS_OCULTAS_SIN_XMLID:
        menu = Menu.browse(menu_id).exists()
        if menu and not menu.parent_id and menu.name == nombre:
            menus |= menu
    return menus


class KoroshiMenuApps(models.AbstractModel):
    _name = 'koroshi.menu.apps'
    _description = 'KOROSHI: aplicaciones ocultas en la pantalla de inicio'

    @api.model
    def ocultar_apps(self):
        menus = menus_apps_ocultas(self.env).sudo().filtered('active')
        if menus:
            menus.write({'active': False})
        return True
