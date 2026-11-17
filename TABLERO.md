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

## Congelación (desde el 17/11/2026)

Hasta instalar lo de «Hecho y sin instalar» **no se programan funciones nuevas**: solo arreglos, correos, análisis y
diseño. Cada versión nueva deja viejo el plan de actualización (el v2 ya está instalado; el vigente es el v3). Se levanta cuando
Isaac lo diga.

## En curso

| Tema | Módulo cogido | Chat | Siguiente paso |
|---|---|---|---|
| Coordinación y traspaso de la auditoría | — | Traspaso KOROSHI: reparto por zonas | Plan de actualización v3 con las versiones de abajo |
| Excel de envíos para tiendas | **koroshi_monitor (1.33.0)** | Excel de envíos para tiendas | Pendiente de instalar (plan v3, tanda B) |
| Mejoras del Monitor de picking | — (suelta koroshi_monitor) | Millores del Monitor picking | Hecho: instaló la 1.32.0 el 17/11 a las 12:37 y dejó el servidor libre. Archivar |
| Ronda de faltantes en Lecturas | koroshi_faltantes (1.7.0) + koroshi_preparacion (3.33.0) | Faltantes (la sesión de los faltantes y la sync S4T) | Pendiente de instalar (plan v3, tanda A) |
| Resumen de productividad por correo | ? (informe / kpi) | Resumen de productividad por correo | Rellenar |
| Carga del camión por CJ | ? (monitor / s4t_envios) | Carga del camión por CJ | Rellenar; spec en `intent/carga-camion-bultos/` |
| Pedidos pendientes por reasignar | ? | Pedidos pendientes por reasignar | Rellenar |
| Alarma PDA si el operario no lee | ? (operarios / preparacion) | PDA: alarma sonora | Rellenar |
| Sync S4T (acción 1800 v6.3, koroshi_s4t_sync) | koroshi_s4t_sync | Sincronización de pedidos con transportista | Rellenar |
| Correos pendientes | — | Correus per enviar | — |

Las filas con «?» las rellena su chat la próxima vez que se abra.

## Esperando a alguien

| Qué | A quién | Desde | Dónde |
|---|---|---|---|
| Envíos y bultos (manual, v3 informal) | S4T | 16/11 | `bin/versiones/correo-s4t-envios-bultos_2026-11-17_v3-informal.md` |
| Devoluciones web | S4T | 17/11 | `bin/versiones/correo-s4t-devoluciones-web_2026-11-17.md` |
| Teórico por matrícula | S4T | 14/11 | `bin/versiones/pregunta-s4t-teorico-matriculas_2026-11-14_1457.md` |
| Devoluciones online | Sonia | 17/11 | `bin/versiones/correo-devoluciones-online-respuesta-sonia_2026-11-17_v2.md` |
| Instalar lo de abajo | Isaac | 13/11 | Plan v3: `bin/versiones/plan-actualizacion-koroshi_2026-11-17_v3.md` |
| Dónde van las fotos (fase 6) | Isaac | 16/11 | `TRASPASO_AUDITORIA.md` |
| Push forzado de la historia limpia (fase 6) | Isaac | 16/11 | `TRASPASO_AUDITORIA.md` |

## Hecho y sin instalar

«Servidor» = leído en nath.tuctuc.com el 17/11 por la tarde (installed_version = latest_version en todos). El plan v2
ya está instalado entero. **Antes de instalar, volver a leer la `installed_version`** (el servidor puede ir por delante
del repo).

| Módulo | Servidor | Último en el repo | Nota |
|---|---|---|---|
| koroshi_faltantes | 1.6.1 | **1.7.0** | Plan v3, tanda A (junto con preparacion) |
| koroshi_preparacion | 3.32.0 | **3.33.0** | La PDA. Plan v3, tanda A (junto con faltantes) |
| koroshi_monitor | 1.32.0 | **1.33.0** | Plan v3, tanda B (después de la A) |

Plan: `bin/versiones/plan-actualizacion-koroshi_2026-11-17_v3.md`.

**No instalar todavía** (decidido): koroshi_actividades (menús ocultos, icono para todos), koroshi_s4t_traspasos
(crearía DEV de todo desde el 01/07), koroshi_delegacion, koroshi_menu 2.5.0 (en el servidor está la 2.4.1).

**Al día**: base 1.0.0, operarios 2.18.1, kpi 1.9.0, warehouse_map .46, consumibles 1.4.0, xpo_bultos 1.3.0,
pda_app 1.1.0, caja_existente 1.4.0, zonas 1.4.0 (en sombra), informe 1.2.0, menu 2.4.1, s4t_envios 1.3.0,
s4t_sync 1.0.0, sesiones 1.0.0, contenedores 1.4.0, rendiment 1.1.0.
