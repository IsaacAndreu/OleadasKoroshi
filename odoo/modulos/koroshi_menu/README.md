# KOROSHI Menú (`koroshi_menu`)

Desde la **v2.0.0** todo lo KOROSHI está en una **aplicación propia** (icono KOROSHI), fuera de Inventario y
agrupado por temas. Antes cada tema estaba repartido entre la barra de Inventario, Informes y Configuración.



## v2.5.0: jefes de almacén (16/11/2026)

Grupo **«KOROSHI: Jefes de almacén»**. El picking entra con **Almacén Nath** (almacen@nath.es), que no está en él.

| | Lo ven |
|---|---|
| **Todos (también el picking)** | Monitor picking, Hoja de carga XPO de hoy, Consulta de envíos, Faltante (PDA), Registrar consumo. Fuera de esta app: Lecturas, código de barras, Actividades, Contenedores y los botones de las OUT («Enviar al Expedidor», «Hoja de carga XPO»). |
| **Solo jefes** | Bandeja, Previsión de cajas, Reparto de hoy, Colas, Mapa NAU-2; Revisión, Rondas, Crear ronda, Puestos a 0, Faltas por día, Recalcular y Faltas repetidas; Personas entera; KPI entera; Historial de consumibles, Movimientos de contenedores y las tres de Zonas; Configuración entera. |

- Al actualizar (o instalar) entran **todos los usuarios internos de la empresa 8 con Inventario menos Almacén Nath**
  (el 16/11: Administración, Almacen 2, BackOffice, Departament IT y Jose Ismael Fonollosa). Solo añade.
- Un usuario nuevo: Ajustes › Usuarios › el usuario › «KOROSHI: Jefes de almacén».
- Solo cambia qué menús se ven: los permisos de los datos son los de siempre.
- «Crear ronda» y «Puestos a 0» eran del responsable de Inventario: ahora, de los jefes.

## v2.4.1: icono «Bandeja» en Aplicaciones, solo para Almacen 2 (16/11/2026)

- La bandeja también sale como icono propio en la pantalla de aplicaciones, solo para el grupo «KOROSHI: Bandeja del
  encargado en Aplicaciones». Al actualizar (o instalar) entra el usuario **Almacen 2** (almacen2@nath.es).
- Para dárselo a otro: Ajustes › Usuarios › el usuario › ese grupo. «Hoy › Bandeja del encargado» sigue para todo
  Inventario.

## v2.4.0: Bandeja del encargado (16/11/2026, auditoría 13/11, fase 7, ideas 2 y 3)

**Hoy › Bandeja del encargado**: una pantalla con todo lo que hay que mirar. Cada línea con semáforo (rojo, ámbar,
verde, gris = sin datos), cuántas, detalle y «Abrir» (la lista donde se resuelve). «Actualizar» lo vuelve a calcular.

| Pestaña | Línea | Rojo / ámbar cuando |
|---|---|---|
| Pendiente | Lecturas de la PDA | rojo: 30 min **de horario** (los tramos de la alarma de la PDA) sin ninguna lectura guardada, con operarios hoy en Lecturas. El 13-16/11 la PDA no guardaba y no lo vio nadie. Minutos: parámetro `koroshi_menu.minutos_sin_lecturas` |
| Pendiente | Faltantes pendientes | ámbar si hay alguno (y el más antiguo) |
| Pendiente | Lecturas rechazadas de cola de la PDA | rojo si hay alguna (preparación 3.29+) |
| Pendiente | Pedidos sin OUT (¿OUT borrada?) | rojo: pedidos confirmados de los últimos 7 días sin ninguna entrega |
| Pendiente | Reparto de zonas de hoy con aviso | ámbar: error, fallos, «AVISO:» o «NO SE HA PARTIDO» |
| Pendiente | Jobs fallidos (queue_job) | rojo si hay alguno |
| Pendiente | Envíos rechazados por S4T, traspasos S4T con error, tramos de actividad por revisar | solo si su módulo está instalado |
| Integraciones | Sync de pedidos S4T: última pasada | el resumen del cron 186; ámbar si hace más de 1 h |
| Integraciones | Cola S4T (root.s4t_sync) | rojo con fallidos; ámbar si un job espera más de 30 min |
| Integraciones | OUT de XPO validadas hoy sin etiqueta | rojo si hay alguna |
| Integraciones | Cron: … (los KOROSHI y S4T activos) | ámbar con 15 min de retraso, rojo con 60 |

Solo lee (con sudo). Tablas transitorias propias (`koroshi.bandeja`, `koroshi.bandeja.linea`): no toca stock ni
tablas compartidas. Si una fuente falla, sale en gris con el error y el resto sigue. Las líneas de crons y del sync
no tienen «Abrir» (son pantallas de Ajustes › Técnico).

## v2.3.0 (15/11/2026, auditoría 13/11, fase 7)

- **Hoy › Previsión de cajas**: abre la ficha de hoy de koroshi_kpi 1.8 (cajas previstas por volumen, reales y
  desviación). Si aún no tiene previsión, la calcula al abrir.

## v2.2.0: solo el responsable guarda los Ajustes (14/11/2026, auditoría 13/11, fase 3)

- **Ajustes KOROSHI › Guardar** solo funciona para el responsable de Inventario (`stock.group_stock_manager`, el mismo
  grupo que ve el menú). Antes cualquier usuario podía cambiar los parámetros llamando al botón por RPC (el modelo es
  transitorio y guarda con `sudo()`). A los demás les sale «Solo el responsable de Inventario puede cambiar los Ajustes
  KOROSHI» y no se guarda nada (tampoco la parte de koroshi_informe).

## Pantalla de aplicaciones

Lecturas (PDA) · Actividades · Contenedores (iconos de sus módulos) · **Monitor picking** · **KOROSHI** (iconos de
este módulo, en `static/description/`).

**Aplicaciones ocultas (v2.1):** se archivan los iconos de 25 aplicaciones que no se usan (sin registros en 90 días o
integraciones en desuso), para todos, también administradores: Calendario, CRM, Sitio web, Whatsapp Templates, IoT,
Multi-Channel, MiraKL, Mobile App, ECI Sales, PinkConnect, e-Commerce Integration, Barcode Excel, Punto de venta,
Ayuda, Planificación, Rastr. enlaces, Fabricación, Consolidación, Proyecto, Marketing por email, Asistencias,
Mantenimiento, Tableros, SQL Views y Warehouse Planner. No se desinstala nada (datos y crons siguen igual). Lista en
`models/apps.py`; se aplica en cada actualización y se deshace al desinstalar. Se quedan Sorter Batches, Integración
S4T, Koroshi Zebra y Job Queue. Para volver a mostrar una: quitarla de la lista y, en Ajustes › Técnico › Menús
(filtro Archivados), activar su menú raíz.

## Dónde está cada cosa (KOROSHI › …)

- **Hoy:** Monitor picking · Reparto de hoy · Colas · Mapa NAU-2 · Hoja de carga XPO de hoy · Consulta de envíos
- **Faltantes:** Faltante (PDA) · Revisión de faltantes · Rondas de faltantes (INT) · Crear ronda de revisión ·
  Puestos a 0 hoy · Faltas por día · Faltas repetidas (revisar) · Recalcular faltas de hoy
- **Personas:** Productividad · Tareas · OUT validadas hoy sin operario · Lecturas de preparación · Informe de
  productividad (correo) (submenú de koroshi_informe)
- **Almacén:** Movimientos de contenedores · Registrar consumo · Historial de consumibles · Ejecuciones de zonas ·
  Cajas cerradas por día y zona · Diagnóstico de zonas de hoy
- **KPI:** KPI por día · Comparativa de semanas · Pesos y litros por tipo
- **Configuración:** Ajustes KOROSHI · Operarios · Crear operarios · Motivos para saltar · Consumibles: artículos ·
  Consumibles: totales iniciales · Zonas: configuración · Zonas: simular hoy (se deshace) · Zonas: medir desde el
  22/10 · Configuración de planos · Sesiones operativas

En Inventario no queda nada KOROSHI salvo lo de S4T (Inventario › Operaciones), que sigue en sus módulos.

**Pendiente:** koroshi_actividades (Jornada por persona, Horas por actividad, Tramos de tiempo, Actividades) no está
instalado en el servidor (13/11/2026) y no está en `depends`. Al instalarlo: añadirlo a `depends` y meter sus
entradas en Personas (huecos 20, 25, 30) y Configuración (hueco 35).

## Cómo funciona

- Crea sus propios menús con las **mismas acciones y los mismos grupos** que los de antes.
- Conserva los ids de la v1.x: `menu_koroshi` es ahora la sección Hoy, `menu_koroshi_informes` la sección Personas
  (koroshi_informe engancha ahí su submenú, sequence 45) y `menu_koroshi_config` la sección Configuración.
- Archiva (`active = False`) los 5 menús KOROSHI de antes y «Hoja de carga XPO de hoy» de Informes. Al actualizar
  esos módulos siguen archivados (el `menuitem` no toca `active`; comprobado en el servidor el 13/11/2026).
- Ojo con los permisos: en la v1.x lo que estaba en Informes y Configuración de Inventario solo lo veían los
  administradores de Inventario (esos menús de Odoo son de administradores). En la app KOROSHI las secciones son
  para usuarios de Inventario. El 13/11/2026 los 6 usuarios con Inventario son administradores: nadie ve nada nuevo.
- Si un módulo KOROSHI añade un menú nuevo, sale dentro de su menú viejo (archivado, no se ve): **hay que añadirlo
  aquí**.
- **Desinstalar** este módulo deja todo como antes (`uninstall_hook` vuelve a activar los menús).

## Versiones

- **v1.0.0 (12/11/2026):** primera versión.
- **v1.1.0 (12/11/2026):** **Ajustes KOROSHI**: los parámetros KOROSHI (orden de Preparación, agrupaciones, minutos sin
  leer, salida por inactividad, OUT a dos, informe diario, faltantes, faltas repetidas, usuarios de la PDA) en una
  pantalla, con nombre y explicación. Solo escribe los que cambian; siguen en Parámetros del sistema como siempre.
  Menús nuevos de koroshi_kpi 1.5 en Informes › KOROSHI: **Comparativa de semanas** y **Faltas repetidas (revisar)**.
  Necesita koroshi_kpi 1.5.0 y koroshi_operarios 2.8.0 instalados antes.
- **v2.0.0 (13/11/2026):** aplicación **KOROSHI** propia con secciones por tema (Hoy, Faltantes, Personas, Almacén,
  KPI, Configuración) e icono **Monitor picking**. «Movimientos de contenedores», que no se veía, pasa a Almacén. Los
  tres menús KOROSHI de Inventario desaparecen. Nueva dependencia: koroshi_contenedores (instalado, 1.1.0).
- **v2.1.0 (13/11/2026):** archiva 25 iconos de aplicaciones que no se usan (lista en `models/apps.py`). Incluye la
  v2.0.0, que no llegó a instalarse.
