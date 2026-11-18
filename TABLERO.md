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
| Excel de envíos para tiendas | koroshi_monitor (1.33.1, instalada 17/11 15:08) | Excel de envíos para tiendas | Comprobar el Excel XPO del 17/11: K1 = 7 bultos y «SÍ» |
| Mejoras del Monitor de picking | — (suelta koroshi_monitor) | Millores del Monitor picking | Hecho: instaló la 1.32.0 el 17/11 a las 12:37 y dejó el servidor libre. Archivar |
| Ronda de faltantes en Lecturas | koroshi_faltantes (1.7.0) + koroshi_preparacion (3.33.0), instaladas 17/11 14:45 | Faltantes (la sesión de los faltantes y la sync S4T) | Probar una ronda pequeña en una PDA; la oficina decide cuándo «Pasar los puestos a 0» |
| Contenedores: compactar huecos | koroshi_contenedores (1.5.0 hecha, sin instalar; servidor en 1.4.0) | Contenedores (compactar) | Instalar con el sí de Isaac; probar en PDA: marcar, archivar, mover, a cero y añadir |
| Resumen de productividad por correo | ? (informe / kpi) | Resumen de productividad por correo | Rellenar |
| Carga del camión por CJ | ? (monitor / s4t_envios) | Carga del camión por CJ | Rellenar; spec en `intent/carga-camion-bultos/` |
| Pedidos pendientes por reasignar | ? | Pedidos pendientes por reasignar | Rellenar |
| Alarma PDA si el operario no lee | ? (operarios / preparacion) | PDA: alarma sonora | Rellenar |
| Sync S4T (acción 1800 v6.3, koroshi_s4t_sync) | koroshi_s4t_sync | Sincronización de pedidos con transportista | Rellenar |
| Envíos a S4T en REAL (koroshi_s4t_envios 1.3.0) | — (sin código) | Esta | 17/11 ~16:50: `modo=real`, cron «Envios a S4T» ACTIVO cada 15 min, `desde`=17/11 23:00 UTC (pedidos con fecha de pedido desde el 18/11 00:00). Probado con S-6665004194 (XPO, 3 bultos): S4T READY. Vigilar los primeros envíos del 18/11 (GLS pasa a SHIPPED) |
| Correos pendientes | — | Correus per enviar | — |

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

Nada. El plan v3 (`bin/versiones/plan-actualizacion-koroshi_2026-11-17_v3.md`) quedó instalado el 17/11 por la tarde:
faltantes 1.7.0 y preparacion 3.33.0 (14:45) y monitor 1.33.0 (14:47) y 1.33.1 (15:08, cifra de u/h real), hora del almacén. **Antes de instalar algo nuevo,
volver a leer la `installed_version`** (el servidor puede ir por delante del repo).

**Instalado el 17/11 a las 15:28**: koroshi_actividades 1.3.0 (nuevo) y koroshi_menu **2.4.2** (sus menús en Personas y
Configuración). La 2.4.2 sale de la 2.4.1 en la rama `koroshi_menu-2.4` (etiqueta `koroshi_menu/v2.4.2`), no de la 2.5.0
de `main`: una 2.5.x tendrá que llevar estos menús.

**No instalar todavía** (decidido): koroshi_s4t_traspasos
(crearía DEV de todo desde el 01/07), koroshi_delegacion, koroshi_menu 2.5.0 (en el servidor está la 2.4.1).

**Al día**: actividades 1.3.1 (icono propio, 18/11 08:37), menu 2.4.2, faltantes 1.7.0, preparacion 3.33.0, monitor 1.33.1, base 1.0.0, operarios 2.18.1, kpi 1.9.0, warehouse_map .46, consumibles 1.4.0, xpo_bultos 1.3.0,
pda_app 1.1.0, caja_existente 1.4.0, zonas 1.4.0 (en sombra), informe 1.2.0, s4t_envios 1.3.0,
s4t_sync 1.0.0, sesiones 1.0.0, contenedores 1.4.0, rendiment 1.1.0.
