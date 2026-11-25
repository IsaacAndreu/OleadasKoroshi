# Diseño: «Revisar caja» en la PDA (partir una CJ en dos) — 19/11/2026, v1

Solo diseño. No hay código. Espera el visto bueno de Isaac.

## Qué pide el almacén (chat del 19/11)

A veces se juntan dos cajas físicas bajo una misma CJ porque el operario olvidó leer la etiqueta nueva al empezar la
segunda caja. Quieren abrir «Revisar caja», leer la CJ, escanear las prendas de la caja que quedó sin etiqueta y
ponerle la CJ que faltaba. Lo que no se escanea se queda en la CJ original. Es como un doble check que deja poner
otra caja si hay que partir.

## Lo que hay hoy (leído en el código, 19/11)

- **Leer una prenda** solo suma `qty_done` en su `stock.move.line`; no toca la caja
  (`koroshi_preparacion/models/lectura.py:737-753`).
- **La caja** es un `stock.quant.package` con el nombre de la CJ. Se asigna al pulsar «Caja» y leer la etiqueta:
  `Lectura.caja` (`lectura.py:849-915`) llama a `put_in_pack(package_name=CJ)`, que escribe `result_package_id`
  en las líneas leídas sin caja. No hay caja «abierta» ni «cerrada»: la caja se cierra al leer su CJ.
  `koroshi_caja_existente` (`models/stock_picking.py:36-155`) reutiliza una CJ que ya existe (misma OUT, u otra OUT
  del mismo pedido y tienda).
- **Mover entre cajas ya existe**: `Lectura.mover_caja` (`lectura.py:961-1039`, v3.21/v3.28) mueve n uds de una
  línea a otra caja de la OUT, a una CJ nueva o «fuera de caja», y parte la línea como hace Odoo. Pantalla: ✎ en
  la línea (`static/src/js/preparacion.js:1386-1416`). **Solo con la OUT sin validar** (`_comprobar`,
  `lectura.py:662-671`) y eligiendo línea a línea, no escaneando.
- **Validar** exige que todo lo leído esté en caja (`lectura.py:1149-1167`) y después hace `button_validate`
  (`koroshi_faltantes/models/faltante.py:478-497`).
- **Lo contrario ya existe en expediciones**: acción 1844 «Juntar matrículas» (v5 preparada hoy,
  `bin/versiones/20261119_accion-1844_juntar-matriculas_v5-PREPARADA-sin-aplicar.py`). Cambia `result_package_id`
  de líneas **ya validadas**; Odoo mueve solo el stock de una caja a otra (probado a mano el 19/11 en S-6665004426).
  Dice: «solo sirve antes de que el pedido pase a SHIPPED en S4T».

### Cómo llega la caja a S4T y al transportista

| Quién | Qué manda | Cuándo | ¿Se puede corregir después? |
|---|---|---|---|
| S4T `PUT /orders/batch-update` (módulo de Effective, cron 186 / acción 1800) | por línea: sku, cantidad servida y `box_code` = `result_package_id` (solo B2B, tipos 38/39) | cuando **todas** las OUT del pedido están hechas → el pedido pasa a **READY** | **No**: con el pedido en READY el módulo no reenvía (el GET da 403). Habría que pedirlo a S4T |
| S4T `POST /shipments` (`koroshi_s4t_envios`, `models/envio.py:274-282`) | solo el **número** de bultos (cajas distintas), peso y volumen | cron cada 15 min con la OUT hecha y el pedido READY | Sí, hasta el cierre del camión: el registro pasa a «corregir» y se reenvía (`envio.py:232-240`, `423-438`) |
| XPO (`koroshi_xpo_bultos`, `delivery_carrier.py:95-119`) | número de bultos | al validar (lo llama el módulo XPO de Effective; no confirmado) | No hay reenvío; queda la nota «XPO: declarados N bultos» y el cierre del camión lo compara |
| Etiqueta del transportista | una por bulto | al validar / imprimir | Hay que reimprimir |

## Propuesta

### Dónde va

En **Lecturas (PDA)**, menú ☰ → **«Revisar caja»**, también desde la pantalla de inicio de Lecturas (sin OUT
abierta), porque el error se descubre con la caja en la mano, no con la OUT. Módulo: **koroshi_preparacion**. No
necesita módulo nuevo.

### Flujo en la PDA

1. **Revisar caja** → «Lee la CJ de la caja». Se lee la CJ con etiqueta (la que tiene todo).
2. Pantalla de la caja: OUT, tienda, pedido, estado (*sin validar* / *validada* / *S4T READY: no se puede tocar*) y
   el contenido: cada artículo con sus uds (`3 · Chaqueta X · M`).
3. **Escanear** las prendas de la caja **sin etiqueta**. Cada lectura:
   - verde: está en la caja → cuenta «1 de 3» en su fila;
   - rojo: no está en esta caja, o ya se han leído todas las que hay → no cuenta.
   - Deshacer la última, como en Lecturas.
4. Dos botones al acabar:
   - **«Todo bien, no partir»**: no cambia nada; solo apunta la revisión (sirve de doble check normal).
   - **«Lo leído va a otra caja»** → «Lee la CJ nueva» → se lee una etiqueta CJ **sin usar**. Las uds leídas pasan a
     la CJ nueva; el resto se queda en la CJ original. Mensaje: «CJ665…: 7 uds · CJ665… (nueva): 5 uds».
5. Opcional, recomendado: **«Comprobar la otra»**: escanear la caja original para ver que lo que queda cuadra (el
   mismo doble check sin partir).

Si el operario se equivoca de caja, la misma pantalla sirve para deshacer: revisar la CJ nueva, leer y devolverlas
a la original (se lee una CJ que ya es del mismo pedido: vale igual).

### Qué cambia en Odoo

- **Sin campos nuevos** en `stock.picking`, `stock.picking.type` ni `stock.move.line`. Se usa lo de siempre:
  `stock.quant.package` (la CJ nueva, nombre CJ + 9 cifras, la acción automática 20 sigue bloqueando duplicados)
  y `result_package_id` de las líneas.
- Por cada artículo leído: las líneas de la CJ original con ese producto pierden n uds y una copia con esas n uds
  queda con `result_package_id` = CJ nueva (lo mismo que hace hoy `mover_caja`). Si la caja lleva líneas de varias
  OUT del mismo pedido (caja existente), se toman de la OUT que más uds tenga en la caja.
- Las lecturas de esas uds (`koroshi.preparacion.lectura.en_caja`) pasan a la CJ nueva, para que la productividad
  siga cuadrando. Se apunta un registro tipo «Revisar caja» (nuevo valor en la selección `tipo` de
  `koroshi.preparacion.lectura`, tabla propia, no compartida) con quién, cuándo, qué CJ y cuántas uds.
- Tipo de caja (Consumibles): la CJ nueva coge el mismo tipo que la original (o se pregunta; ver P4).
- `number_of_packages` de la OUT: +1 (la lógica de bultos de `koroshi_caja_existente/models/stock_picking.py:160-186`
  y la `recalcular_bultos` de la 1844).
- Nota en el chatter de la OUT: «Revisar caja: 5 uds de CJ665… a CJ665… (operario)».
- Todo en un savepoint: si algo no cuadra (uds de más, CJ usada en otro pedido, pedido READY…), no cambia nada.

### Según en qué punto está la caja

| Estado | Qué se hace | Riesgo |
|---|---|---|
| **A. OUT sin validar** | Partir con la lógica de `mover_caja` (ya probada en PDA desde la 3.21). | Bajo |
| **B. OUT validada, pedido aún no READY en S4T** (otras OUT del pedido sin validar, o el cron 186 aún no ha pasado) | Partir líneas **ya hechas**: copia hecha con n uds en la CJ nueva y la original con n menos. Odoo mueve el stock en Clientes de una caja a otra. `koroshi_s4t_envios` lo recoge solo; **XPO ya tenía declarado un bulto menos y hay que imprimir la etiqueta del bulto nuevo** (ver P3). | Medio: cambiar `qty_done` de una línea hecha hace que Odoo devuelva y vuelva a sacar el stock del hueco. **No está probado** en este Odoo: probar antes, fuera de horas, en una OUT de prueba |
| **C. Pedido READY / SHIPPED en S4T, o camión cerrado** | **Bloqueado**: «El pedido ya está en S4T con sus cajas: avisa a expediciones». No se cambia nada. La corrección es a mano con S4T. | — |
| Caja PACK… (Zalando / About You) o sin CJ | No se ofrece (no lleva etiqueta CJ). | — |
| CJ con stock en el almacén (no es de una OUT) | Error, igual que `caja_existente`. | — |

**Recomendación**: hacer **primero solo A** (OUT sin validar) + el bloqueo de C y un aviso en B («la OUT ya está
validada: pásala a expediciones»). Es casi todo `mover_caja` con otra pantalla: poco riesgo para la PDA. B como
segunda versión, cuando sepamos cuándo se descubre el error (P1) y con la prueba de partir líneas hechas.

Carrera con el cron 186 en B: se comprueba `x_s4t_status` en la misma transacción y se bloquea la OUT
(`_bloquear`, como en Lecturas), pero si el sync está a medias en ese mismo segundo puede mandar las cajas viejas. En
A no pasa: el pedido no puede estar READY con una OUT sin validar.

## Preguntas para Isaac (y almacén)

- **P1.** ¿Cuándo se dan cuenta? ¿Antes de validar la OUT (aún en Lecturas, al cerrar la caja) o después, en
  expediciones/precinto con la OUT ya validada? Decide si basta con A.
- **P2.** ¿Quién lo usa? ¿El preparador en la PDA, o expediciones (PDA o PC)? Si es expediciones, ¿le vale la misma
  pantalla de Lecturas?
- **P3.** En B: ¿cómo se imprime hoy la etiqueta del transportista de un bulto de más, y hay que volver a declarar
  los bultos a XPO? (No he encontrado quién llama a `xpo_es_send_shipping`.)
- **P4.** ¿La CJ nueva lleva el mismo tipo de caja (consumible) que la original, o se pregunta?
- **P5.** ¿Quieren el doble check también sin partir, como paso normal (p. ej. obligatorio en tiendas)? Hoy queda
  como opcional.

## Antes de programar

- `koroshi_preparacion` está cogido en el TABLERO por la sesión de **Ronda de faltantes** (3.33.0, pendiente de
  probar en PDA). Hay que pedirlo a esa sesión (regla 6) y preguntar la `installed_version` real (regla 3).
- No hace falta tocar `koroshi_caja_existente`, `koroshi_operarios` ni `koroshi_s4t_envios` para A.
- Comprobación en Odoo en vivo (solo lectura) **no hecha**: el panel del navegador no tenía sesión iniciada. Lo
  dicho sobre `result_package_id` y el movimiento de stock sale del código y de la prueba de la 1844 v5 (19/11).

## Qué probar en una PDA real (cuando se programe A)

1. OUT de prueba sin validar con 2 cajas físicas bajo una CJ: Revisar caja, leer 3 prendas, CJ nueva → la OUT
   muestra 2 cajas y las uds cuadran; validar sale con 2 bultos.
2. Leer una prenda que no está en la caja → rojo, no cuenta.
3. Leer una CJ ya usada en otro pedido como «nueva» → error, no cambia nada.
4. Revisar caja de una OUT validada → aviso, no cambia nada.
5. Sin red a mitad → al volver no se mueve dos veces (`id_lectura`, como `mover_caja`).
