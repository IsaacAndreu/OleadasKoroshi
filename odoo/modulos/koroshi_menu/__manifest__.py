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
v1.1.0 (12/11/2026): «Ajustes KOROSHI» (Configuración › KOROSHI, responsables de Inventario): los parámetros KOROSHI
en una sola pantalla con nombre y explicación (orden de Preparación, agrupaciones, minutos sin leer, informe diario,
faltantes, faltas repetidas, usuarios de la PDA). Menús nuevos de koroshi_kpi 1.5: Comparativa de semanas y Faltas
repetidas (Informes › KOROSHI).
v1.2.0 (12/11/2026): en Ajustes KOROSHI, «Alarma en la PDA: minutos sin leer» (koroshi_preparacion.minutos_alarma,
necesita koroshi_preparacion v3.22): con la OUT abierta tantos minutos sin leer, la PDA pita sin parar y parpadea en
rojo. 0 = sin alarma.
v1.3.0 (12/11/2026): «Alarma en la PDA: horario» (koroshi_preparacion.horario_alarma): tramos HH:MM-HH:MM separados por
comas en que puede sonar la alarma; por defecto 06:00-10:00,10:15-13:00,14:00-17:00 (sin la pausa de 10:00-10:15 ni la
comida de 13 a 14). Se comprueba el formato al guardar. Incluye la v1.2.0 (no llegó a instalarse).
""",
    'version': '13.0.1.3.0',
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
        'views/ajustes.xml',
    ],
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'application': False,
}
