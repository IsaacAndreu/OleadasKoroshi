# Tablero KOROSHI

**Una página con el estado de verdad.** Cada chat lo lee al empezar y actualiza su línea al acabar (y en el mismo
commit). El detalle de cada tema va en su chat, en `TRASPASO_AUDITORIA.md` o en `bin/versiones/`; aquí solo una línea.

Última revisión: 17/11/2026 (creado).

## Cómo se usa

1. **Antes de tocar un módulo**, mirar «En curso»: si otro chat lo tiene cogido, no se toca (CLAUDE.md, regla 6).
   Si está libre, apuntarse: una línea con el módulo, el chat y el siguiente paso.
2. **Al sacar una versión**, pasarla a «Hecho y sin instalar» (o actualizar su fila).
3. **Al acabar el tema**, borrar la línea de «En curso» y archivar el chat.
4. **Ideas nuevas**: al chat coordinador («Traspaso KOROSHI: reparto por zonas»), que abre el chat que toque.

## Congelación (desde el 17/11/2026)

Hasta instalar lo de «Hecho y sin instalar» **no se programan funciones nuevas**: solo arreglos, correos, análisis y
diseño. Cada versión nueva deja viejo el plan de actualización (el v2 de esta mañana ya lo está). Se levanta cuando
Isaac lo diga.

## En curso

| Tema | Módulo cogido | Chat | Siguiente paso |
|---|---|---|---|
| Coordinación y traspaso de la auditoría | — | Traspaso KOROSHI: reparto por zonas | Plan de actualización v3 con las versiones de abajo |
| Excel de envíos para tiendas | koroshi_monitor (1.33.0) | Excel de envíos para tiendas | Pendiente de instalar |
| Mejoras del Monitor de picking | koroshi_monitor ⚠ | Millores del Monitor picking | ⚠ mismo módulo que el Excel de envíos: confirmar cuál lo tiene |
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
| Instalar lo de abajo | Isaac | 13/11 | Plan v2 (ya viejo): `bin/versiones/plan-actualizacion-koroshi_2026-11-17_v2.md` |
| Dónde van las fotos (fase 6) | Isaac | 16/11 | `TRASPASO_AUDITORIA.md` |
| Push forzado de la historia limpia (fase 6) | Isaac | 16/11 | `TRASPASO_AUDITORIA.md` |

## Hecho y sin instalar

«Servidor» = leído en nath.tuctuc.com el 17/11 por la mañana. **Antes de instalar, volver a leer la
`installed_version`** (el servidor puede ir por delante del repo).

| Módulo | Servidor | Plan v2 | Último en el repo | Nota |
|---|---|---|---|---|
| koroshi_base | — | 1.0.0 | 1.0.0 | Primero y solo (tanda 1) |
| koroshi_operarios | 2.11.1 | 2.14.0 | **2.18.1** | +4 versiones desde el plan |
| koroshi_monitor | 1.24.0 | 1.29.0 | **1.33.0** | +4 versiones desde el plan |
| koroshi_preparacion | 3.29.0 | 3.31.0 | **3.33.0** | La PDA. +2 desde el plan |
| koroshi_faltantes | 1.4.1 | 1.5.0 | **1.7.0** | +3 desde el plan |
| koroshi_kpi | 1.5.0 | 1.9.0 | 1.9.0 | |
| koroshi_warehouse_map | 0.1.20261102.39 | .46 | .46 | |
| koroshi_consumibles | 1.3.0 | 1.4.0 | 1.4.0 | |
| koroshi_xpo_bultos | 1.1.0 | 1.3.0 | 1.3.0 | |
| koroshi_pda_app | 1.0.0 | 1.1.0 | 1.1.0 | |
| koroshi_caja_existente | 1.3.0 | 1.4.0 | 1.4.0 | |
| koroshi_zonas | 1.2.0 | 1.4.0 | 1.4.0 | Sigue en sombra |
| koroshi_informe | 1.0.1 | 1.2.0 | 1.2.0 | |
| koroshi_menu | 2.1.0 | 2.4.1 | 2.5.0 | **Instalar la 2.4.1, NO la 2.5.0** |
| koroshi_s4t_envios | 1.1.0 | 1.3.0 | 1.3.0 | Sigue en diagnóstico |
| koroshi_s4t_sync | — | — | **1.0.0** | Nuevo (17/11), no está en el plan |
| koroshi_sesiones | — | — | **1.0.0** | Nuevo (17/11), no está en el plan |

**No instalar todavía** (decidido): koroshi_actividades (menús ocultos, icono para todos), koroshi_s4t_traspasos
(crearía DEV de todo desde el 01/07), koroshi_delegacion, koroshi_menu 2.5.0.

**Al día**: koroshi_contenedores 1.4.0, koroshi_rendiment 1.1.0.
