# Tablero del responsable: v8 (20/11/2026, sin código)

Sale de la v7 (`diseno-tablero-responsable_2026-11-20_v7.md`, no se toca). Recoge la respuesta de «Zonas: mejorar»
del 20/11. El orden de la «siguiente libre» lo decide solo operarios, sin depender de zonas. Zonas no hereda nada de
operarios: así un upgrade de operarios no arrastra a zonas, que parte a las 04:50.

## Siguiente libre, cuando la columna de un operario queda vacía

1. **Agrupaciones Z- con zona `T\d+`** (las «tradicionales» de zonas 1.7.0):
   - van primero las de **número de pedido más bajo** de sus OUT, con `_numero_pedido` del origin, que operarios ya
     tiene copiado;
   - si empatan, por nombre;
   - **una sola persona por T**, que la hace entera (tipo `agrupacion`).
2. **Zonas `D\d+` y `MU\d+`**: todas llevan los mismos pedidos, así que la prioridad no las distingue.
   - La persona libre va a **la zona que acabaría más tarde**: más uds pendientes por persona que ya está en ella,
     es decir, «reforzar la que va atrasada».
   - Dentro de la zona, OUT a OUT por CAJA, como en la v5.
3. **Lo que no es Z-** (`WEB_…`, etc.): como hoy.

- Las uds no cuentan para la prioridad. «La de 50 acaba antes y coge otra» sale sola de «quien acaba coge la
  siguiente».
- Juntar las pequeñas ya lo hace la T al crearse.
- **Modo del día**: el tablero no lo lee. Distingue por el nombre: la T va entera y a una persona; D y MU van OUT a
  OUT. Zonas deja de todas formas el parámetro `koroshi_zonas.modo_dia` (`AAAA-MM-DD:zonas|tradicional`), que no se usa.

## Orden de salida

- **operarios 2.23.0 primero**, con la regla T incluida: no se usa hasta que existan T y no hace daño.
- Después, zonas 1.7.0, cuando zonas haya pasado a real.
- Las dos, con el sí de Isaac.

## Sigue pendiente

- **P4 «Sin área»**: ¿la columna se queda o se quita? Lo decide Isaac.
- **Área actual de cada operario**: se le ha preguntado a «PDA: entrada única». Mientras no exista, se deduce de lo
  que hay.
