# KOROSHI Preparación en Lecturas (v3.1.0, 10/11/2026)

Pantalla de preparación propia dentro de **Lecturas (PDA)**. El operario lee su tarjeta, se abre su OUT y la prepara
entera sin salir a la app de código de barras: leer productos, cerrar cajas con la etiqueta CJ y validar.

## v3.1.0 (tras la prueba en Odoo del 10/11)

- Productos sin foto: no se pinta el icono gris de Odoo; el texto ocupa todo el ancho (`tiene_foto` con `bin_size`).
- Nombre del producto una vez y en grande (`[X] X` -> `X`) y **talla** en un recuadro negro (atributo Talla o lo
  último de MODELO-COLOR-TALLA). La referencia interna solo si es distinta del nombre y del EAN.
- Avisos cortos: «2511TR12-000002-XL · 1 de 1».
- «Todo en caja» solo cuando hay algo leído. Barra de progreso gruesa con «N de M uds» dentro.
- El nombre del operario no se parte en la cabecera.

## Cuándo se usa

- Solo si el **operario** está activado: parámetro `koroshi_preparacion.empleados` con los códigos de tarjeta
  (ID de credencial) separados por comas. Al instalar: `OP9990001,OP9980001` (Isaac e Isaac2). `*` = todos.
  Se activa por empleado, no por usuario, porque todas las PDA entran con el mismo usuario de Odoo.
- Solo **OUT sueltas** de la company 8. Las OUT de una agrupación de zona **Z-** siguen en la app de siempre.
- `koroshi_preparacion.activa` = `0` apaga todo y Lecturas vuelve a abrir la app de código de barras (vuelta atrás
  sin desinstalar).
- Sin tarjeta, o con un operario que no está en la lista: todo igual que antes.

## Cómo se usa en la PDA

1. Lecturas abre la OUT en la pantalla nueva. Arriba: OUT, tienda, operario y progreso («3 de 4 uds», «Sin caja: N
   uds»). En grande: **Ve a** ubicación, referencia, producto y cuántas lleva.
2. **Leer el EAN** (o la referencia) suma 1 ud a su línea. Si no es de la OUT, si es desconocido o si esa línea ya
   está completa: aviso rojo, pitido grave y **no cuenta**.
3. **Caja**: se pulsa el botón, sale «Escanea la caja», se lee la etiqueta **CJ** (CJ + 9 cifras) y la caja se cierra
   con todo lo leído que no tenía caja. Se puede seguir con la siguiente caja. Una CJ leída sin pulsar Caja avisa.
4. **Validar** (verde) cuando todo está leído y en caja. Si falta algo: «Quedan N líneas…» → **Faltante**.
   Al validar vuelve a Lecturas, que enseña «¡Hecho!» y abre la siguiente.
5. **Deshacer** quita la última lectura del operario (si aún no está en una caja).
6. **←** vuelve a Lecturas sin validar (Continuar / Faltante / Saltar, como al volver de la app).
7. **Faltante** abre la pantalla de koroshi_faltantes con la OUT y el operario. «Volver a la OUT» regresa a esta
   pantalla; si se valida allí, se vuelve a Lecturas con «¡Hecho!».

No hace falta tocar el campo para leer: el lector llega por el bus de Odoo, como en la app (v3.0.2: el punto dice
siempre «Lector preparado»; gris solo sin conexión). Sin conexión: banda roja; la lectura que estaba en camino se guarda al volver la red con el mismo id (no cuenta dos
veces) y las demás no se aceptan hasta que vuelva.

## Qué escribe

Lo mismo que la app de código de barras (comprobado en su código el 10/11/2026: guarda `qty_done`, llama
`put_in_pack(package_name=CJ)` y `button_validate`):

- `stock.move.line.qty_done` (+1 / −1 por lectura).
- `put_in_pack(package_name=<CJ>)` → Brain Station + **koroshi_caja_existente** (caja de otra OUT del mismo pedido,
  etc.) funcionan igual.
- Validación de **koroshi_faltantes** (`validar_out`: `button_validate`, todo o nada; pedido pendiente según
  `koroshi_faltantes.pedido_pendiente`). Bultos, XPO, S4T y etiquetas se hacen en el servidor como siempre.
- Su propia tabla **koroshi.preparacion.lectura** (menú *KOROSHI Operarios > Lecturas de preparación*, grupo
  productividad): quién, qué OUT, código, resultado, errores.

Sin campos nuevos en albaranes, movimientos, agrupaciones ni tipos de operación. No toca stock_barcode, no escribe
stock.quant y nunca fuerza disponibilidad.

## Rutas (JSON, `auth='user'`)

| Ruta | Qué hace |
|---|---|
| `/koroshi/preparacion/modo` | ¿El operario y la OUT van a la pantalla nueva? |
| `/koroshi/preparacion/cargar` | Estado de la OUT (líneas, siguiente, sin caja, cajas, progreso) |
| `/koroshi/preparacion/leer` | +1 ud del producto leído (con `id_lectura` para no contar dos veces) |
| `/koroshi/preparacion/deshacer` | −1 de la última lectura del operario |
| `/koroshi/preparacion/caja` | Cierra la caja con la CJ leída (`put_in_pack`) |
| `/koroshi/preparacion/validar` | Valida la OUT (validación de koroshi_faltantes) |

## Depende de

`koroshi_operarios` **v2.3.0** (pantalla nueva de Lecturas) y `koroshi_faltantes` v1.3.1. Se engancha con `.include`
en `koroshi_operarios.Pantalla._abrir` y en `koroshi_faltantes.Pantalla._onVolver`; no modifica sus ficheros.

## Ficheros

- `models/lectura.py`: tabla de lecturas y toda la lógica (leer, deshacer, caja, validar, estado).
- `controllers/main.py`: rutas.
- `static/src/js/preparacion.js`: pantalla + includes en Lecturas y Faltante.
- `static/src/xml/preparacion.xml`, `static/src/css/preparacion.css`.
- `data/parametros.xml` (noupdate), `views/lectura_views.xml`, `views/assets.xml`, `security/ir.model.access.csv`.

## Pendiente (siguientes versiones)

- Lotes Z- recorriendo OUT a OUT (v3.4a del plan).
- Cerrar caja leyendo directamente la CJ sin pulsar el botón (si se quiere).
- Cantidad de golpe para líneas de muchas uds (hoy el 96 % son de 1 ud).
