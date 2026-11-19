# Diseño: buscador de stock (`koroshi_buscador_stock` 1.0.0), 19/11/2026

Respuestas de Isaac (19/11):
- lo usa **la oficina**, en el portátil;
- busca por EAN o referencia, por un trozo de la referencia o la descripción, por ubicación o lineal y por
  contenedor KO_/TT_;
- enseña huecos y uds, reservadas y las OUT que las reservan, entradas pendientes y libres por prenda;
- es **solo de lectura**.

## Qué es

Es una pantalla de escritorio, en **KOROSHI > Buscador de stock** (debajo de `koroshi_menu.menu_koroshi_app`,
como Pedidos web), con una sola caja de búsqueda: se escribe o se pega el código y se pulsa Intro. El texto se
reconoce en este orden:

| Lo escrito | Se entiende como | Ejemplo |
|---|---|---|
| `L` + cifras | lineal (del nombre del hueco: «07828 - L94 P35 C1») | `L94` |
| empieza por `KO_` / `TT_` | contenedor; si no hay uno con ese nombre exacto, la lista de los que lo contienen | `KO_290726_44` |
| código de barras de una ubicación | hueco | `07828` |
| EAN (también con un 0 delante o sin él), código alternativo o referencia exacta | prenda | `8435…` |
| cualquier otra cosa (3 caracteres o más) | trozo de la referencia o de la descripción: lista de modelos para elegir (50 como máximo) | `sudadera ne` |

## Qué enseña

**Una prenda**: arriba, el modelo con todas sus tallas y colores.

| Talla/color | Stock | Reservado | Libre | Entradas pendientes |
|---|---|---|---|---|

Al pulsar una talla o color salen tres bloques:
1. **Dónde está**: el hueco, el contenedor, las uds y las reservadas (como «dónde hay» de Contenedores).
2. **Quién la reserva**: cada OUT, con su origen (pedido o tienda), su estado, las uds reservadas y de qué hueco o
   contenedor salen.
3. **Entradas pendientes**: las recepciones abiertas (sin validar ni cancelar) que traen la prenda a una
   ubicación interna, con su fecha prevista y sus uds.

**Un hueco o un contenedor**: lo que tiene dentro, una fila por prenda, con las uds, las reservadas, las libres y
las OUT que la reservan desde ahí. En un hueco se ven también sus contenedores KO_/TT_.

**Un lineal**: sus huecos, con los contenedores y las uds de cada uno. Al pulsar un hueco se abre como en el punto
anterior.

Cada nombre de OUT, recepción o prenda es un enlace que abre su ficha de Odoo en una pestaña nueva.

## Cómo está hecho

- **Una ruta JSON**, `/koroshi/buscador_stock/buscar` (y `/detalle` para abrir una talla o un hueco), que solo hace
  `search`/`read_group` sobre `stock.quant`, `stock.move.line`, `stock.move`, `stock.location` y `product.product`,
  con `sudo()` y siempre filtrada por la compañía 8 y las ubicaciones internas. **No escribe nada** y no tiene
  ningún modelo ni campo nuevo, ni en tablas compartidas ni en una suya.
- **Permisos**: el menú y la ruta solo para `stock.group_stock_user`. La ruta lo comprueba también, porque la
  ruta sola se podría llamar sin pasar por el menú.
- **Una pantalla** con una acción cliente (`AbstractAction`, como las de Contenedores y Actividades), con su JS,
  XML y CSS. Va con `role="presentation"`, no con `aria-hidden`.
- **Límites** para que no se cuelgue con una búsqueda grande: 50 modelos en la lista, 200 ubicaciones y 100 OUT por
  prenda, y 400 huecos por lineal. Si hay más, lo dice («y N más»).
- **Depende de** `stock`, `koroshi_base` (`COMPANY_ID`) y `koroshi_menu` (el menú). **No depende** de
  `koroshi_contenedores` y no lo toca: lo lleva otra sesión.

## Lo que se repite con Contenedores: decisión

`_buscar_producto` (las variantes del EAN), `_literal` (escapar `_`/`%` en `ilike`) y `_es_contenedor_nombre`
ya están en `koroshi_contenedores`. Hay dos opciones:

- **A (recomendada): copiarlas en este módulo para la 1.0.0**, con un comentario que diga de dónde salen.
  Pasarlas a `koroshi_base` es otra versión, más adelante. El motivo es que actualizar `koroshi_base` con `-u`
  actualiza también todos los módulos que dependen de él, es decir, casi todos los de KOROSHI. Eso saca las
  sesiones de la PDA (como el 17/11). Si se cambia solo el `.py`, sin `-u`, hace falta reiniciar.
- B: sacarlas ahora a `koroshi_base` 1.1.0. Toca dos módulos y obliga a esa actualización grande.

## Lo que no hace la 1.0.0

- No ajusta, no mueve y no reserva nada.
- No se usa en la PDA (no hay pantalla para el lector ni usuario «Almacén Nath»).
- No exporta a Excel. Si hace falta, se añade en otra versión.

## Dudas que quedan

1. **Entradas pendientes**: ¿las entradas de mercancía pasan por recepciones de Odoo (tipo «Recepciones») o
   entran de otra forma (inversa, traspasos S4T)? Si no pasan por recepciones, esa columna saldrá siempre a 0, y
   habría que decir qué se tiene que contar como «pendiente».
2. **Libre** = stock − reservado de las ubicaciones internas. Lo que está en la zona de salida o en cajas
   cerradas, ¿se cuenta como stock o se deja fuera?

## Cómo se probará

- Con `python -m py_compile` y `bin/comprobar.py`, y revisando a mano las consultas contra el código de Contenedores.
- En el servidor, cuando Isaac lo instale (es un módulo nuevo, **se instala solo y no a la vez** que contenedores,
  traspasos o zonas): buscar un EAN conocido, un KO_, un hueco y un lineal, y comparar con lo que da Contenedores
  en la PDA y con Inventario > Informes > Existencias.
