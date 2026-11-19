# Tablero KOROSHI

**Una página con el estado de verdad.** Cada chat lo lee al empezar y actualiza su línea al acabar (y en el mismo
commit). El detalle de cada tema va en su chat, en `TRASPASO_AUDITORIA.md` o en `bin/versiones/`; aquí solo una línea.

Última revisión: 17/11/2026 tarde (plan v3; koroshi_monitor lo tiene el chat del Excel de envíos).

## Cómo se usa

1. **Antes de tocar un módulo**, mirar «En curso»: si otro chat lo tiene cogido, no se toca (CLAUDE.md, regla 6).
   Si está libre, apuntarse: una línea con el módulo, el chat y el siguiente paso.
2. **Al sacar una versión**, pasarla a «Hecho y sin instalar» (o actualizar su fila).
3. **Al acabar el tema**, borrar la línea de «En curso» y archivar el chat.
4. **Ideas nuevas**: al chat coordinador («Traspaso KOROSHI: reparto por zonas»), que abre el chat que toque.

## Congelación (17/11/2026): levantada el 18/11/2026

Isaac la levantó el 18/11 para koroshi_contenedores 1.5.0 (compactar huecos), que es urgente. Se vuelve a programar con
las reglas de siempre: una versión, una instalación a la vez.

## En curso

| Tema | Módulo cogido | Chat | Siguiente paso |
|---|---|---|---|
| Coordinación y traspaso de la auditoría | — | Traspaso KOROSHI: reparto por zonas | Plan v3 instalado entero el 17/11 por la tarde |
| Cierre del camión XPO: formato de Erika | koroshi_monitor (1.34.0 instalada 18/11 15:53 hora local) | Resumen reunión 18/11 (lo coge del chat «Excel de envíos para tiendas», con el sí de Isaac) | Destinatarios ya cambiados a la lista XPO (18/11 ~16:00). Falta cerrar un camión de prueba |
| Mejoras del Monitor de picking | — (suelta koroshi_monitor) | Millores del Monitor picking | Hecho: instaló la 1.32.0 el 17/11 a las 12:37 y dejó el servidor libre. Archivar |
| Ronda de faltantes en Lecturas | koroshi_faltantes (1.7.0) + koroshi_preparacion (3.33.0), instaladas 17/11 14:45 | Faltantes (la sesión de los faltantes y la sync S4T) | Probar una ronda pequeña en una PDA; la oficina decide cuándo «Pasar los puestos a 0» |
| Contenedores: compactar huecos | koroshi_contenedores (**1.7.0 instalada 19/11 ~09:50 hora local**: «Cambiar» uds de un artículo del contenedor, buscar por trozo del nombre / sugerencias, «Abrir» desde la lista de mover) | Contenedores (compactar) | Ctrl+F5 en las PDA y probar en PDA real «Cambiar» cantidad y buscar por trozo; pendiente: qué quieren «verificar» al compactar |
| Resumen de productividad por correo | ? (informe / kpi) | Resumen de productividad por correo | Rellenar |
| Carga del camión por CJ | ? (monitor / s4t_envios) | Carga del camión por CJ | Rellenar; spec en `intent/carga-camion-bultos/` |
| Pedidos pendientes por reasignar | ? | Pedidos pendientes por reasignar | Rellenar |
| Cierre por inactividad (15 min) y u/h sin sesiones olvidadas | koroshi_operarios (2.19.0) + koroshi_monitor (1.35.0), instaladas 18/11 16:11-16:17 hora local | Cierre por inactividad | Comprobar que el cron cierra solo la próxima tarea olvidada (las dos pasadas de justo después de instalar no cerraron; Diana y Sheyla se cerraron llamando a `cron_cerrar(inactividad=True)` por RPC). Probar en PDA: volver a leer tras el cierre abre otra tarea |
| Alarma PDA si el operario no lee | ? (operarios / preparacion) | PDA: alarma sonora | Rellenar |
| Sync S4T (acción 1800 v6.3, koroshi_s4t_sync) | koroshi_s4t_sync | Sincronización de pedidos con transportista | Rellenar |
| Envíos a S4T en REAL (koroshi_s4t_envios 1.3.0) | — (sin código) | Esta | 17/11 ~16:50: `modo=real`, cron «Envios a S4T» ACTIVO cada 15 min, `desde`=17/11 23:00 UTC (pedidos con fecha de pedido desde el 18/11 00:00). Probado con S-6665004194 (XPO, 3 bultos): S4T READY. Vigilar los primeros envíos del 18/11 (GLS pasa a SHIPPED) |
| Correos pendientes | — | Correus per enviar | — |
| Poner en marcha los traspasos S4T (devoluciones web) | koroshi_s4t_traspasos (1.3.0 instalada 19/11 09:44 hora local, `modo`=guardar, cron 218 archivado) | Traspasos S4T (19/11) | Primera descarga hecha: 4 devoluciones (8 uds; la del 18/11 y 3 de sep/oct) y 18 correcciones, todo en «Nuevo», sin DEV. Falta: decidir las 3 viejas («Sin DEV» o DEV), `modo`=real y activar el cron. Los 2 palets entran cuando S4T migre la página antigua |
| Agrupaciones web por corte (06:00 y 11:00) y cancelación de las no reservadas | koroshi_agrupaciones_web (1.0.0 instalada 18/11 16:25; `activo`=1 desde 18/11, `cancelar`=1 desde 19/11 08:30) | Agrupaciones web por corte | 19/11 06:00: primera WEB_191126_01 automática (45 OUT, 82 uds). Comprobar la primera cancelación de las 11:00 y el correo a isaac.andreu@nath.es y betty@nath.es |

| Zonas: mejorar (acabar a la hora y pasar a real) | koroshi_zonas (1.5.0 HECHA, SIN INSTALAR; en el servidor la 1.4.0 en sombra) | Zonas: mejorar | 1.5.0: la sombra pasa a ser un SIMULAR (ensayo de partir), aviso de hora de fin y personas que faltan, y previsto contra real con las lecturas de la PDA. Instalar con el sí de Isaac (no a la vez que otra actualización); después, rellenar los destinatarios del correo y activar el cron 210 si se quiere el aviso por correo. Diagnóstico: `bin/versiones/zonas-diagnostico-y-mejoras_2026-11-19.md` |

Las filas con «?» las rellena su chat la próxima vez que se abra.

## Esperando a alguien

| Qué | A quién | Desde | Dónde |
|---|---|---|---|
| Envíos y bultos (manual, v3 informal) | S4T | 16/11 | `bin/versiones/correo-s4t-envios-bultos_2026-11-17_v3-informal.md` |
| Devoluciones web | S4T | 17/11 | `bin/versiones/correo-s4t-devoluciones-web_2026-11-17.md` |
| Teórico por matrícula | S4T | 14/11 | `bin/versiones/pregunta-s4t-teorico-matriculas_2026-11-14_1457.md` |
| Devoluciones online | Sonia | 17/11 | `bin/versiones/correo-devoluciones-online-respuesta-sonia_2026-11-17_v2.md` |
| Dónde van las fotos (fase 6) | Isaac | 16/11 | `TRASPASO_AUDITORIA.md` |
| Push forzado de la historia limpia (fase 6) | Isaac | 16/11 | `TRASPASO_AUDITORIA.md` |

## Hecho y sin instalar

El plan v3 (`bin/versiones/plan-actualizacion-koroshi_2026-11-17_v3.md`) quedó instalado el 17/11 por la tarde:
faltantes 1.7.0 y preparacion 3.33.0 (14:45) y monitor 1.33.0 (14:47) y 1.33.1 (15:08, cifra de u/h real), hora del almacén. **Antes de instalar algo nuevo,
volver a leer la `installed_version`** (el servidor puede ir por delante del repo).

**Instalado el 17/11 a las 15:28**: koroshi_actividades 1.3.0 (nuevo) y koroshi_menu **2.4.2** (sus menús en Personas y
Configuración). La 2.4.2 sale de la 2.4.1 en la rama `koroshi_menu-2.4` (etiqueta `koroshi_menu/v2.4.2`), no de la 2.5.0
de `main`: una 2.5.x tendrá que llevar estos menús.

**No instalar todavía** (decidido): koroshi_delegacion, koroshi_menu 2.5.0 (en el servidor está la 2.4.1).

**Al día**: s4t_traspasos 1.3.0 (19/11 09:44, modo guardar), agrupaciones_web 1.0.0 (18/11 16:25; encendido, cancela desde el 19/11), contenedores 1.7.0 (cambiar cantidad y buscar por trozo, 19/11 ~09:50), actividades 1.3.1 (icono propio, 18/11 08:37), menu 2.4.2, faltantes 1.7.0, preparacion 3.33.0, monitor 1.35.0 (sin huecos de 15 min en Producción por hora, 18/11 16:17), base 1.0.0, operarios 2.19.0 (cierre por inactividad, 18/11 16:11), kpi 1.9.0, warehouse_map .46, consumibles 1.4.0, xpo_bultos 1.3.0,
pda_app 1.1.0, caja_existente 1.4.0, zonas 1.4.0 (en sombra), informe 1.2.0, s4t_envios 1.3.0,
s4t_sync 1.0.0, sesiones 1.0.0, rendiment 1.1.0.
