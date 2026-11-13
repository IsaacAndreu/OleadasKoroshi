# KOROSHI Menú (`koroshi_menu`)

Desde la **v2.0.0** todo lo KOROSHI está en una **aplicación propia** (icono KOROSHI), fuera de Inventario y
agrupado por temas. Antes cada tema estaba repartido entre la barra de Inventario, Informes y Configuración.

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
