# koroshi_agrupaciones_web

Cortes de pedidos web (Isaac, 13/11 y 18/11/2026). Diseño: `bin/versiones/diseno-agrupaciones-web-por-corte_2026-11-18_v2.md`.

## Qué hace cada corte (06:00 y 11:00, hora del almacén)

1. **Cancela** las OUT web creadas antes del corte que no están al 100 % reservadas (sin agrupación y sin nada leído)
   y manda a Betty la lista: las cancela en el TPV de KOROSHI y rehacen el pedido con lo que sí hay. A S4T, nada.
2. **Agrupa** las 100 % reservadas en orden de llegada en `WEB_ddmmaa_NN` de hasta 100 uds (En curso; PedidosMultiples).

## Parámetros (`koroshi_agrupaciones_web.*`)

| Clave | Por defecto | Qué es |
|---|---|---|
| `activo` | 0 | 1 = el cron hace los cortes |
| `cancelar` | 0 | 1 = cancela de verdad; 0 = solo apunta cuáles cancelaría |
| `cortes` | 06:00,11:00 | horas del almacén |
| `tope_uds` | 100 | uds máximas por agrupación (una OUT no se parte) |
| `correo_canceladas` | betty@nath.es | a quién va la lista de canceladas |
| `dias_atras` | 3 | solo OUT creadas desde hace N días |
| `margen_minutos` | 120 | un corte que llega más tarde (servidor parado, recién encendido) no se hace |
| `servidor` | NATH | servidor de correo saliente |
| `ultimo_corte` | — | lo escribe el cron |

## Puesta en marcha

1. Instalar (todo apagado). 2. KOROSHI > Pedidos web > Simular corte ahora, y comparar. 3. `activo = 1` con
`cancelar = 0` un día (agrupa; las canceladas solo se apuntan). 4. `cancelar = 1`.

Tests sin Odoo: `python -m unittest discover -s tests` desde la carpeta del módulo.
