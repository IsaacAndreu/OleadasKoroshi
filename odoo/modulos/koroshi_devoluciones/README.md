# KOROSHI Devoluciones (v1.0, 20/11/2026)

«Ubicar devoluciones» en la PDA, sin Excel. Es la fase 1 del diseño `bin/versiones/diseno-devoluciones_2026-11-20_v2.md`.
**Sin instalar.**

## Qué hace

Hoy se apuntan en un Excel el EAN y el contenedor, y después se suben a Odoo. Con este módulo se hace en la PDA:

1. Se pasa la tarjeta. Es la misma de Lecturas, Contenedores y Faltante.
2. Se toca qué se ha hecho:
   - **Quitar precio**;
   - **Quitar precio y embolsar**;
   - **Reetiquetar y embolsar**.
3. Se lee prenda, prenda…
   - Cada lectura cuenta 1 ud.
   - «Quitar la última» deshace la última lectura.
   - «Cantidad» da N uds a la última lectura.
   - «Borrar todo» vacía la lista.
4. Se lee el contenedor `KO_`/`TT_` o el hueco (código de barras, solo de la compañía 8). Así se guarda la tanda. La
   opción se queda puesta para el siguiente cajón.

## Stock

El parámetro `koroshi_devoluciones.stock` vale `mover` al instalar. Con `mover`, cada prenda pasa al contenedor así:

1. Primero se coge lo que haya **libre** de ese artículo en la ubicación de devoluciones (movimiento interno). La
   ubicación es la del parámetro `koroshi_devoluciones.origen_id` (id de `stock.location`). Si no está, es la de destino
   del tipo de operación DEV de la compañía 8 (`DEVOLUCIO_KOROSHI`), la misma de `koroshi_s4t_traspasos`.
2. Lo que falte entra como **ajuste de inventario** desde pérdidas de inventario, como hace «Añadir prendas» en
   Contenedores.

Con `apuntar` solo se apunta, y la pantalla lo dice.

**Cuidado con las DEV de S4T.** Si una devolución web se ubica antes de validar su DEV, entra como ajuste. Si después
se valida la DEV, esas prendas se cuentan dos veces. Hay que validar la DEV **antes** de ubicar, o no validarla.

## Oficina

En Inventario > KOROSHI Operarios > Devoluciones:

- **Devoluciones ubicadas**: lista de quién, cuándo, qué opción, artículo, uds y contenedor. Desde aquí un responsable
  de inventario puede **anular una tanda**: el stock vuelve a donde estaba, solo si sigue libre en el contenedor.
- **Informe por día, semana o mes**: pivote y gráfico de uds por manipulación. Se agrupa por día, semana o mes, por
  código de factura o por operario.
- **Opciones de manipulación** (solo jefes): nombre, código de factura (M1/M2/M3, solo para el informe), color y orden.
  Se pueden añadir opciones sin programar.

## Tablas

`koroshi.devolucion.ubicada` y `koroshi.devolucion.manipulacion`. Sin campos en tablas de Odoo.

Instalar después de `koroshi_base` y `koroshi_operarios` (ya instalados).
