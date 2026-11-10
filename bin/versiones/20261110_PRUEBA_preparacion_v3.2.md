# Prueba: Preparación en Lecturas v3.2 (Faltante sin lista), 10/11/2026

Qué cambia: el botón **Faltante** de la pantalla de preparación ya no abre la lista «¿Qué falta?». Trabaja con la
línea que se ve en grande y dice dónde probar. Solo cambia la PDA (JS, plantilla y CSS). El servidor de
koroshi_faltantes es el mismo (v1.3.1).

## Instalar

1. Subir `20261110_koroshi_preparacion_v3.2.zip` y `instalar_koroshi_preparacion_v3.2_2026-11-10.sh` a
   `/home/it_nath_group` (el ZIP de Operarios v2.3.1 ya está allí; si no, subirlo también).
2. `bash instalar_koroshi_preparacion_v3.2_2026-11-10.sh check` y después
   `sudo AUTO_CONFIRM=1 bash instalar_koroshi_preparacion_v3.2_2026-11-10.sh install`.
3. Aplicaciones → «KOROSHI Preparación en Lecturas» → Actualizar (debe quedar 13.0.3.2.0).
4. **En cada PDA: cerrar Odoo y volver a abrirlo** (o recargar). Si no, el navegador sigue con la versión anterior.

## Probar (con una OUT pequeña suelta, con Isaac o Isaac2)

| # | Qué hacer | Qué debe pasar |
|---|---|---|
| 1 | Abrir la OUT desde Lecturas y pulsar **Faltante** | Sale una hoja abajo: foto, nombre y talla, «No está en X · 1 ud» en rojo y «Prueba en» con hasta 3 ubicaciones; la primera en verde, «La más cercana» |
| 2 | **Cancelar** (o tocar fuera, o ←) | Se cierra la hoja y no cambia nada |
| 3 | Con ◀ ▶ ir a otra línea y pulsar **Faltante** | La hoja es de esa línea, no de la que toca |
| 4 | En la hoja leer una CJ o la tarjeta | Aviso rojo; no hace nada |
| 5 | Leer una ubicación que no existe | «… no es una ubicación» |
| 6 | Ir a la ubicación verde, coger la pieza y **leer la ubicación** | Se cierra la hoja; «Cambiada a Y. Ahora lee el producto.» y la línea se ve con la ubicación nueva |
| 7 | Leer el EAN de la pieza | Cuenta como siempre |
| 8 | En otra línea: Faltante → **Tampoco está aquí** una vez | El botón cambia a «Pulsa otra vez: va a faltantes»; si no se pulsa en 4 s, vuelve a estar como antes |
| 9 | Pulsarlo dos veces | «Va a faltantes: la OUT sale sin esa pieza.»; la línea desaparece y la barra baja |
| 10 | Pieza sin stock en otro sitio | «No queda en ninguna otra ubicación.» y el botón dice «Mandar a faltantes» |
| 11 | **Marcar varias a la vez** | Abre la pantalla de Faltante de siempre; «Volver a la OUT» regresa a la preparación |
| 12 | Con todo leído | El botón Faltante está apagado |

Ojo: los puntos 6 y 9 **sí cambian la OUT** (reserva y FALTANTE, igual que la pantalla de Faltante de siempre).
Hacerlos solo con una pieza que de verdad falte, o en una OUT de prueba.

## Volver atrás

- Rápido: parámetro `koroshi_preparacion.activa` = `0`. Lecturas abre la app de siempre.
- A la v3.1: reinstalar `20261110_koroshi_preparacion_v3.1.zip` con su .sh y actualizar el módulo.
