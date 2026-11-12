# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Menú de Inventario',
    'summary': 'Ordena los menús KOROSHI de Inventario: uno solo arriba con lo de cada día; informes y ajustes en su sitio',
    'description': """
KOROSHI Menú de Inventario
==========================

Antes había 5 menús KOROSHI en la barra de Inventario (KPI, Operarios, Zonas, Operaciones, Faltantes), con 35
opciones. Ahora:

* **KOROSHI** (barra de arriba): solo lo que se abre cada día (Monitor, Consulta de envíos, Reparto de hoy, Colas,
  Mapa NAU-2, Hoja de carga XPO, Faltante (PDA), Revisión de faltantes, Registrar consumo).
* **Informes › KOROSHI**: KPI, faltas, productividad, tareas, zonas, rondas de faltantes, historial de consumibles.
* **Configuración › KOROSHI**: operarios, motivos, consumibles, zonas, planos, sesiones, rondas y puestos a 0.

Lecturas (PDA) ya tiene su icono en la pantalla de inicio (koroshi_operarios v2.7).

Cómo funciona: este módulo crea sus propios menús apuntando a las MISMAS acciones (con los mismos grupos) y archiva
(active = False) los 5 menús KOROSHI de antes y la «Hoja de carga XPO» de Informes. No cambia ningún otro módulo:
al actualizarlos, sus menús siguen archivados (el menuitem no toca «active»). Si un módulo KOROSHI añade un menú
nuevo, sale dentro del menú viejo (archivado): hay que añadirlo aquí. Al desinstalar este módulo vuelven los menús de
antes.

v1.0.0 (12/11/2026): primera versión.
""",
    'version': '13.0.1.0.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': [
        'stock',
        'koroshi_kpi',
        'koroshi_operarios',
        'koroshi_preparacion',
        'koroshi_zonas',
        'koroshi_warehouse_map',
        'koroshi_monitor',
        'koroshi_consumibles',
        'koroshi_faltantes',
    ],
    'data': [
        'views/menu.xml',
    ],
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'application': False,
}
