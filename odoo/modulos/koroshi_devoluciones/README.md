# KOROSHI Devoluciones (v1.2.0, 20/11/2026)

«Ubicar devoluciones» en la PDA, sin Excel. Es la fase 1 del diseño `bin/versiones/diseno-devoluciones_2026-11-20_v2.md`.
1.1.0 instalada el 20/11; **1.2.0 sin instalar**.

## Qué hace

Es para las **devoluciones de tiendas**: llega una caja grande y se apunta en un Excel el EAN y el contenedor
`KO_` (una fila por prenda), y después se sube a Odoo. Con este módulo se hace en la PDA:

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

El parámetro `koroshi_devoluciones.stock` vale `mover` al instalar. Con `mover`, cada prenda entra en el contenedor o
hueco leído como **ajuste de inventario** (desde pérdidas de inventario), igual que la subida del Excel y que «Añadir
prendas» en Contenedores. Con `apuntar` solo se apunta, y la pantalla lo dice.

**v1.0.1**: no se toca `DEVOLUCIO_KOROSHI`. Ahí están las devoluciones e-commerce (DEV que entran por la API de S4T),
que se ubicarán en la fase 2 desde su DEV.

## Llegadas (v1.1.0, fase 2, etapa 1)

Pestaña «Llegadas» en la misma pantalla, al lado de «Ubicar»:

1. Se toca el canal: Tiendas, Web, Zalando, Marketplace u Otro. Se queda puesto.
2. Se lee lo que trae cada paquete: la matrícula CJ de la tienda, el código de Zalando o el del transportista (GLS…).
   - Queda «ha llegado hoy, lo leyó X».
   - Una matrícula CJ pone sola el canal Tiendas y la tienda (CJ080… = K80). Las CJ665… son cajas nuestras y se
     rechazan.
   - Si el mismo código ya llegó en los últimos 30 días, lo dice («llegó el 18/11 10:12, Cruz») y no lo repite.
3. Abajo se ve cuántos han llegado hoy por canal y los últimos.

En la oficina, **Paquetes llegados**: se busca por código, día, canal o tienda («lo de GLS del día 28»). Un jefe
puede anular una llegada leída por error. Solo apunta: no crea recepciones ni mueve stock.

## Contenido (v1.2.0, fase 2, etapa 2)

Tercera pestaña, «Contenido»:

1. Se lee el código del paquete, el mismo que en Llegadas (tiene que haber llegado en los últimos 30 días).
2. Se leen sus prendas. Cada una entra como **Bien** (va a su puesto).
3. Si una no está bien, justo después de leerla se toca qué le pasa: **Quitar precio**, **Quitar precio y
   embolsar**, **Reetiquetar y embolsar** o **Tara**. Cambia la última leída, que sale resaltada.
4. **Guardar** lo apunta en el paquete, que pasa a «Contenido leído» con sus uds bien / manipular / tara. Se puede
   volver a abrir y añadir más.

En la oficina: el contenido sale en la ficha del paquete, y **Prendas leídas en paquetes** da la lista entera (por
paquete, día, canal, resultado o manipulación). Es lo que «les mandamos» si no nos pasan qué lleva.

Todavía **no se compara con lo esperado** (bien / no ha llegado): falta la fuente. En la web hay que casar el paquete
con su devolución de S4T (DevoEcom) y en tiendas S4T no da el teórico por matrícula. Solo apunta: no mueve stock.

## Oficina

En Inventario > KOROSHI Operarios > Devoluciones:

- **Devoluciones ubicadas**: lista de quién, cuándo, qué opción, artículo, uds y contenedor. Desde aquí un responsable
  de inventario puede **anular una tanda**: el stock vuelve a donde estaba, solo si sigue libre en el contenedor.
- **Informe por día, semana o mes**: pivote y gráfico de uds por manipulación. Se agrupa por día, semana o mes, por
  código de factura o por operario.
- **Opciones de manipulación** (solo jefes): nombre, código de factura (M1/M2/M3, solo para el informe), color y orden.
  Se pueden añadir opciones sin programar.

## Tablas

`koroshi.devolucion.ubicada`, `koroshi.devolucion.manipulacion` (v1.1.0) `koroshi.devolucion.paquete` y (v1.2.0) `koroshi.devolucion.paquete.linea`. Sin campos en tablas de Odoo.

Instalar después de `koroshi_base` y `koroshi_operarios` (ya instalados).
