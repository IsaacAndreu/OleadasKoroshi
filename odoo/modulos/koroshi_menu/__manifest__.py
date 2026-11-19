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

koroshi_actividades (registro de tiempo de manipulaciones) está en «depends» desde la v2.4.2 (y la 2.5.1): sus
informes van en Personas y su configuración en Configuración.

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
v2.4.0 (16/11/2026): auditoria 13/11, fase 7, ideas 2 y 3. «Bandeja del encargado» en Hoy: una pantalla con lo
pendiente (Lecturas sin guardar en horario, faltantes, lecturas rechazadas de cola, pedidos sin OUT, reparto de zonas
con aviso, jobs fallidos, envios S4T rechazados, traspasos S4T con error, tramos de actividad por revisar) y una
pestana de Integraciones (crons KOROSHI y S4T con retraso, cola root.s4t_sync, OUT de XPO sin etiqueta, ultima
pasada del sync S4T). Semaforo y «Abrir» en cada linea. Solo lee; tablas transitorias propias; cada fuente solo si
su modulo esta instalado. «Lecturas de la PDA» en rojo con 30 min de horario sin ninguna lectura y operarios en
Lecturas (parametro koroshi_menu.minutos_sin_lecturas): el 13-16/11 la PDA no guardaba y no lo vio nadie.
Depende de koroshi_base.
v2.4.1 (16/11/2026): la bandeja tambien como icono «Bandeja» en la pantalla de aplicaciones, solo para el grupo
«KOROSHI: Bandeja del encargado en Aplicaciones». Al actualizar (o instalar) entra el usuario «Almacen 2»
(almacen2@nath.es). Para darselo a otro: Ajustes > Usuarios. El menu de Hoy sigue igual.
v2.5.0 (16/11/2026): grupo «KOROSHI: Jefes de almacen». Solo ellos ven en la app KOROSHI: Bandeja, Prevision de
cajas, Reparto de hoy, Colas, Mapa NAU-2, la revision de Faltantes (revision, rondas, crear ronda, puestos a 0,
faltas por dia, recalcular, repetidas), Personas, KPI, Historial de consumibles, Movimientos de contenedores, las
tres de Zonas y Configuracion. El picking entra con «Almacen Nath» (almacen@nath.es), que no esta en el grupo: le
quedan Monitor, Hoja de carga XPO, Consulta de envios, Faltante (PDA) y Registrar consumo (y Lecturas, codigo de
barras, Actividades y Contenedores, de sus modulos). Al actualizar o instalar entran todos los usuarios internos de
la empresa 8 con Inventario menos Almacen Nath. Los menus llevan «-grupo» para quitar el de antes (Odoo solo anade
grupos al actualizar). Solo menus: los permisos de los datos no cambian.
v2.5.1 (19/11/2026): la 2.5.0 mas los menus de koroshi_actividades de la 2.4.2 (instalada desde el 17/11; la 2.5.0
salio antes y no los llevaba): Personas 18, 20, 25, 28 y 30 y Configuracion 35, mismos grupos que en la 2.4.2, y
koroshi_actividades en depends. Ademas los jefes de almacen entran en «S4T API / User» (modulo S4T de Effective):
Almacen 2 no veia Registro de Matriculas de Caja ni el packing feed de S4T porque no tenia ese grupo; Almacen Nath (PDA)
ya lo tenia y lo sigue teniendo. Solo anade usuarios a ese grupo (migracion 13.0.2.5.1 y post_init_hook); si el modulo
S4T no esta, no hace nada. No toca «S4T API / Admin» (configuracion con la clave de la API).
v2.5.2 (19/11/2026): «Consulta de envios» (KOROSHI > Hoy) solo para jefes de almacen: Isaac no quiere que los
operarios (Almacen Nath) vean los envios ni la produccion. Va con koroshi_monitor 1.37.0, que a quien no es jefe le
ensena el monitor con el codigo del operario en vez del nombre y sin Produccion por hora ni Consulta de envios. Las
entradas del monitor en Inventario (Consulta de envios, Produccion por hora) cuelgan de KOROSHI · Operaciones, que
este modulo archiva: no se ven. Almacen Nath sigue viendo Monitor picking, Hoja de carga XPO, Faltante (PDA) y
Registrar consumo. Solo menus.
v2.6.0 (19/11/2026): bandeja del encargado para el jefe de almacen (Isaac: lo que habia era importante para IT, no
para el jefe). Tres pestanas. Hoy: tiendas por preparar (rojo si quedan con reserva pasada la hora
koroshi_menu.hora_tiendas, 13:00), camion XPO de hoy (cerrado y correo a XPO enviado; rojo sin cerrar pasada
koroshi_menu.hora_camion, 15:00), leido sin caja en OUT sin validar (las MU2 del 18/11; rojo con mas de 60 min), OUT
de tienda validadas hoy con prendas sin caja (el Excel de Miguel del 19/11), operarios parados y tareas o actividades
abiertas de otro dia. Pendiente: faltantes, stock 0 con pedidos esperando, web (OUT sin agrupar con reserva completa
o incompleta y canceladas de hoy con el correo a Betty), envios a S4T rechazados/error/por corregir, traspasos S4T con
error y pendientes de entrar, OUT de XPO sin etiqueta y tramos de actividad por revisar. IT (grupo nuevo «KOROSHI:
IT», solo Departament IT; no vale el de administracion porque Almacen Nath tambien lo es): Lecturas de la PDA
paradas, lecturas rechazadas de cola, pedidos sin OUT, reparto de zonas con aviso, jobs fallidos, sync y cola S4T y
crons. Solo lee; tablas transitorias propias. Migracion 13.0.2.6.0 (Departament IT al grupo IT).
v2.6.1 (19/11/2026): la 2.6.0 no se pudo actualizar en el servidor («External ID 'grupo_it' must be fully
qualified»): en los groups de una vista el grupo va con el modulo delante (koroshi_menu.grupo_it). Odoo deshizo la
actualizacion y siguio en la 2.5.2. Solo cambia eso.
""",
    'version': '13.0.2.6.1',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': [
        'stock',
        'koroshi_base',
        'koroshi_kpi',
        'koroshi_operarios',
        'koroshi_preparacion',
        'koroshi_zonas',
        'koroshi_warehouse_map',
        'koroshi_monitor',
        'koroshi_consumibles',
        'koroshi_faltantes',
        'koroshi_contenedores',
        'koroshi_actividades',   # v2.4.2 / v2.5.1
    ],
    'data': [
        'views/bandeja.xml',
        'views/menu.xml',
        'views/ajustes.xml',
        'views/apps.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'application': False,
}
