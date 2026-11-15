# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Menú',
    'summary': 'Aplicación KOROSHI propia (Hoy, Faltantes, Personas, Almacén, KPI, Configuración) e icono de Monitor picking',
    'description': """
KOROSHI Menú
============

Desde la v2.0.0 todo lo KOROSHI está en una aplicación propia, fuera de Inventario, agrupado por temas:

* **Hoy**: Monitor picking, Previsión de cajas, Reparto de hoy, Colas, Mapa NAU-2, Hoja de carga XPO de hoy, Consulta de envíos.
* **Faltantes**: Faltante (PDA), Revisión de faltantes, Rondas de faltantes (INT), Crear ronda de revisión, Puestos
  a 0 hoy, Faltas por día, Faltas repetidas (revisar), Recalcular faltas de hoy.
* **Personas**: Productividad, Tareas, OUT validadas hoy sin operario, Lecturas de preparación e «Informe de
  productividad (correo)» (de koroshi_informe).
* **Almacén**: Movimientos de contenedores, Registrar consumo, Historial de consumibles, Ejecuciones de zonas, Cajas
  cerradas por día y zona, Diagnóstico de zonas de hoy.
* **KPI**: KPI por día, Comparativa de semanas, Pesos y litros por tipo.
* **Configuración**: Ajustes KOROSHI, Operarios, Crear operarios, Motivos para saltar, Consumibles, Zonas,
  Configuración de planos, Sesiones operativas.

En la pantalla de aplicaciones: Lecturas (PDA), Actividades, Contenedores (iconos de sus módulos), Monitor picking y
KOROSHI (iconos de este módulo). En Inventario no queda nada KOROSHI salvo lo de S4T (Operaciones).

Además archiva los iconos de aplicaciones que no se usan en NATH (no los ve nadie, ni los administradores): Calendario,
CRM, Sitio web, Whatsapp Templates, IoT, Multi-Channel, MiraKL, Mobile App, ECI Sales, PinkConnect, e-Commerce
Integration, Barcode Excel, Punto de venta, Ayuda, Planificación, Rastr. enlaces, Fabricación, Consolidación, Proyecto,
Marketing por email, Asistencias, Mantenimiento, Tableros, SQL Views y Warehouse Planner. No desinstala nada: los
módulos, sus datos y sus crons siguen igual. La lista está en models/apps.py; se aplica en cada actualización.

Cómo funciona: este módulo crea sus propios menús apuntando a las MISMAS acciones (con los mismos grupos) y archiva
(active = False) los 5 menús KOROSHI antiguos de Inventario y la «Hoja de carga XPO» de Informes. No cambia ningún
otro módulo: al actualizarlos, sus menús siguen archivados (el menuitem no toca «active»). Lo mismo vale para los
iconos de aplicaciones archivados.

ATENCIÓN: si un módulo KOROSHI añade un menú nuevo, sale dentro de su menú viejo (archivado) y NO se ve: hay que
añadirlo aquí. Al desinstalar este módulo vuelven los menús de antes y los iconos de aplicaciones archivados.

Pendiente: koroshi_actividades (Jornada por persona, Horas por actividad, Tramos de tiempo y Actividades) no está en
«depends» porque aún no está instalado en el servidor. Cuando se instale, añadirlo y meter sus entradas en Personas
(huecos 20, 25 y 30) y Configuración (hueco 35).

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
v2.0.0 (13/11/2026): aplicación KOROSHI propia con secciones por tema (antes cada tema estaba repartido entre la barra,
Informes y Configuración de Inventario) e icono de Monitor picking en la pantalla de aplicaciones. Movimientos de
contenedores, que no se veía (colgaba de KOROSHI Operarios, archivado), pasa a Almacén. Los tres menús KOROSHI de
Inventario desaparecen (se conservan sus ids como secciones Hoy, Personas y Configuración). Nueva dependencia:
koroshi_contenedores. No llegó a instalarse.
v2.1.0 (13/11/2026): archiva 25 iconos de aplicaciones que no se usan (models/apps.py, views/apps.xml). Incluye la
v2.0.0.
v2.2.0 (14/11/2026): auditoria 13/11, fase 3. «Guardar» de Ajustes KOROSHI solo para el responsable de Inventario
(stock.group_stock_manager, el mismo grupo que ve el menu): el modelo es transitorio y escribe parametros con
sudo(), asi que cualquier usuario podia cambiarlos por RPC.
v2.3.0 (15/11/2026): auditoria 13/11, fase 7. «Prevision de cajas» en Hoy (la ficha de hoy de koroshi_kpi 1.8:
cajas previstas por volumen, reales y desviacion). Necesita koroshi_kpi 1.8.0.
""",
    'version': '13.0.2.3.0',
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
        'koroshi_contenedores',
    ],
    'data': [
        'views/menu.xml',
        'views/ajustes.xml',
        'views/apps.xml',
    ],
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'application': False,
}
