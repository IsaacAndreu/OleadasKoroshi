# KOROSHI Faltantes (v1.6.0, 17/11/2026)

Qué hacer en la PDA cuando una pieza de una OUT no está donde dice Odoo. Hasta ahora se ponía a 0 la ubicación desde la PDA:
el stock se iba a pérdidas sin saber quién, de qué OUT ni por qué. Del 27/10 al 09/11 se hizo 111 veces (159 uds), y el 44 % de
esos artículos tenía stock libre en otra ubicación.

Con este módulo:
- la línea de la OUT pasa a otra ubicación con stock libre;
- la pieza que no está va a **EFFEC/FALTANTE**;
- queda un registro que se revisa cada día.

## v1.6.0: solo lineales y muelle (17/11/2026)

- «Prueba en» solo propone ubicaciones de **NAVE2**: huecos de los lineales (L.. P.. C..) y cajas KO del muelle
  (KO_ sueltas en NAVE2, aún sin hueco). Antes mandaba a coger de **DEVOLUCIO_KOROSHI** (foto de la PDA, 17/11) y
  podía proponer CAJAS, PRUEBA o la raíz de Stock.
- Si se lee una ubicación de fuera, avisa «solo de los lineales y del muelle» y no cambia nada.
- Constante `ZONA_PICKING` en `models/faltante.py`. Sin campos ni vistas nuevas.

## v1.5.0: pasa a koroshi_base (16/11/2026, auditoría 13/11, fase 6)

- La hora del almacén sale de `koroshi_base.comun` (instalar koroshi_base antes).
- «Puestos a 0 hoy» ya empieza a las 00:00 justas también el día del cambio de hora (antes, una hora corrido).
- La pantalla Faltante de la PDA no cambia. Sin campos ni vistas nuevas.

## v1.4.1: corrección (11/11/2026)

- «Prueba en» salía gris oscuro sobre negro (la regla antigua `.o_kf_reco span`): ahora en blanco y la letra se ajusta.
- Debajo de la ubicación sale el nombre del artículo una vez (antes el EAN en algunas líneas, o el código repetido).

## v1.4.0: mismo aspecto que Preparación (11/11/2026)

- Lo grande y en negro es la **ubicación** (hueco y KO en la misma línea y del mismo tamaño, la letra baja sola si no
  cabe); la referencia del artículo va debajo, más pequeña.
- «Prueba en»: etiqueta negra con franja de código de barras. Dónde no está: tachada en rojo.
- Botones planos; en la PDA sin la barra de menús de Odoo (`body.o_kf_en_faltante`).

## En la PDA (v1.3): al final de la OUT, sin leer el EAN

En el almacén los faltantes se marcan **al final**: se hace toda la OUT en la app de código de barras y lo que no se ha
encontrado se marca después. Si la pieza no está, no hay EAN que leer, así que la v1.3 enseña la lista.

1. Acabada la OUT, **flecha atrás** y en Lecturas (PDA) **Faltante**. La OUT (o la agrupación `Z-`) ya viene puesta.
2. Sale **¿Qué falta?**: lo que queda por coger de la OUT, en el orden de la app de código de barras. Por línea:
   **referencia** en grande, color / talla, ubicación y uds (y las leídas, si hay una parte leída).
   - Se **marcan** una o varias y **Continuar**. Si solo queda una, ya viene marcada.
   - También se puede **leer la ubicación** donde se está (elige la línea de allí) o el EAN.
3. Para cada línea marcada sale **una ubicación recomendada** («Prueba en L44 P17 C3 · 3 ud libres»), la de stock libre
   más cercana. *Ver más ubicaciones* enseña las demás (hasta 5).
   - **Está allí:** leer la ubicación de donde se coge → la línea pasa allí (igual que antes). Hay que ir a cogerla y
     leerla en la OUT.
   - **Tampoco está aquí** y otra vez para confirmar → **No está en ninguna ubicación**: la pieza va a FALTANTE y la OUT
     sale sin ella.
   - *Esta no: dejarla y seguir* deja esa línea sin tocar.
4. Al acabar, resumen («3 faltantes: 1 reubicado, 2 a FALTANTE») y:
   - si **no queda nada por coger**, la OUT **se valida sola** con la validación normal de Odoo, **sin pedido
     pendiente** (v1.3.1: lo que falta ya está en FALTANTE, no se pregunta). Validada, vuelve sola a Lecturas, que
     abre la siguiente. Con el parámetro `pedido_pendiente` = `preguntar`, la PDA pregunta Sí / No como en la v1.3;
   - botón **Validar OUT** para hacerlo a mano (si la validación sola está apagada o ha fallado);
   - si **queda algo por coger** (p. ej. lo reubicado), «Quedan N líneas por coger» y **Volver a la OUT**;
   - **agrupaciones `Z-`:** no se validan solas (la agrupación se valida entera en «procesar agrupación»): **Volver a la
     agrupación**.
   - Si Odoo pide otra cosa al validar (transferencia inmediata, otro asistente) o da error, no se fuerza: sale el
     motivo en rojo y se valida en la app de código de barras.

Parámetros del sistema (*Ajustes > Técnico > Parámetros del sistema*):

| Clave | Valores | Inicio |
|---|---|---|
| `koroshi_faltantes.validar_sola` | `1` se valida sola / `0` solo con el botón | `1` |
| `koroshi_faltantes.pedido_pendiente` | `no` / `si` / `preguntar` | `no` (v1.3.1) |

Validar sin ir a la última página de la OUT, sin faltantes: leer el código de barras de órdenes **`O-BTN.validate`** de la
app de código de barras (ver `bin/versiones/20261109_INFORME_validar_OUT_codigo_barras.md`).

## Qué pasa en Odoo cuando se elige otra ubicación, y cómo queda trazado (v1.3.1)

Ejemplo: la OUT dice 2 uds de KS-24117 en `L07 P03 C2`, no están, y se encuentran en `L07 P05 C1`.

1. En *Faltante* el operario va a `L07 P05 C1` y **lee esa ubicación** (no basta con tocar el botón).
2. Odoo, de golpe (si algo falla no se hace nada):
   - la **línea de la OUT cambia de ubicación**: se quita la reserva de `L07 P03 C2` y se reserva en `L07 P05 C1`
     (el cambio estándar de Odoo, solo con stock libre: no quita nada a otra OUT);
   - las 2 uds que no estaban **pasan de `L07 P03 C2` a FALTANTE** con un movimiento interno hecho
     (`KOROSHI Faltante OUT/…`). Así Odoo deja de creer que están en `L07 P03 C2`;
   - queda el **registro de faltante** (operario, OUT, artículo, uds, ubicación vieja, ubicación nueva, hora);
   - **v1.3.1:** queda una **nota en el historial de la OUT**: «Faltante: KS-24117 2 uds no estaban en L07 P03 C2; se
     cogen en L07 P05 C1. 2 uds de la ubicación vieja a FALTANTE. Operario: …».
3. **Volver a la OUT:** la app de código de barras la vuelve a cargar y esa línea ya sale en la página **«Desde
   L07 P05 C1»**: el operario lee la ubicación nueva y el artículo, como cualquier otra línea. La ubicación vieja ya no
   sale en la OUT.
4. Al validar, la salida de stock es **desde `L07 P05 C1`**, que es de donde ha salido de verdad.

Dónde mirarlo después:

| Qué | Dónde |
|---|---|
| De dónde salió de verdad cada pieza | La OUT > *Operaciones detalladas* (ubicación origen = la nueva) |
| Que se cambió, quién y cuándo | Historial (chatter) de la OUT (v1.3.1) y *KOROSHI Faltantes > Faltantes* |
| Las uds que no estaban | *Inventario > Informes > Movimientos de stock*: descripción `KOROSHI Faltante OUT/…`, origen la OUT, de la vieja a FALTANTE |
| Qué pasó con ellas | Faltante en *Encontrado* (vuelven a una ubicación) o *No encontrado* (a pérdidas de inventario) |

## En la PDA (v1.0 - v1.2)

1. Haciendo una OUT en la app de código de barras falta una pieza. Se sale con la **flecha atrás** y en la pantalla de
   **Operarios** se pulsa **Faltante**. También se abre desde *Inventario > KOROSHI Faltantes > Faltante (PDA)*.
2. Leer **la OUT** y después **el EAN** de la pieza que no está.
   - **v1.2:** si se entra con el botón *Faltante* de Operarios v2 mientras se hace una OUT, la OUT ya viene puesta:
     solo hay que leer el EAN.
   - Si el artículo tiene varias líneas en la OUT, se elige la línea con un botón.
   - La OUT también se puede leer solo con el número (`23649`).
3. Sale:
   - **Reservada en:** `L46 P15 C3 · KO_140726_005 · 1 ud`;
   - **Con stock libre:** hasta 5 ubicaciones, ordenadas por el lineal más cercano al de la reservada. Para cada una se
     ve cuántas uds libres tiene (cantidad − reservado).
4. Ir a una de ellas, coger la pieza y **leer la ubicación** (la caja `KO_…` o el hueco `L44 P17 C3`). En ese momento,
   todo de golpe:
   1. la línea de la OUT pasa a esa ubicación con la reserva buena. Si se lee el hueco, se usa la caja KO de dentro con
      más stock libre;
   2. la unidad que faltaba va de la ubicación vieja a **FALTANTE**;
   3. queda el registro (quién, OUT, artículo, de dónde, a dónde, hora).

   Si algo falla, no se cambia nada y sale el motivo en rojo.
5. Si no está en ningún sitio: **No está en ningún sitio** (dos pulsaciones). Se quita la reserva de esa línea, la unidad
   va a FALTANTE y la OUT se valida sin esa pieza, como hasta ahora.
6. **Volver a la OUT:** la abre otra vez en la app de código de barras, ya con la ubicación nueva. Si es de una
   agrupación `Z-`, abre la agrupación.
   - Si se entró desde Operarios, al validar se vuelve a Operarios.
7. **Otro faltante en esta OUT** vuelve al paso del EAN.

La tarjeta del operario se puede leer en cualquier momento. Si no se lee, se pone el operario de la tarea abierta de esa
OUT o agrupación (koroshi_operarios).

## Ronda de revisión: ir a ver si los faltantes son reales (v1.1)

FALTANTE no es un sitio de la nave: es una ubicación de Odoo donde quedan las uds que no se han encontrado. Para buscarlas
se hace una **ronda** con una INT normal, en la app de código de barras.

1. **Crear la ronda:** *Inventario > KOROSHI Faltantes > Crear ronda de revisión* (responsable de almacén).
   - Crea **una INT** (`EFFEC/INT/…`, origen `RONDA FALTANTES dd/mm hh:mm`) con todos los faltantes pendientes que
     tienen uds en FALTANTE y no están ya en otra ronda.
   - Hay una línea por faltante, de **FALTANTE a la ubicación donde tenía que estar**, ordenadas por lineal.
   - Para hacer la ronda solo con algunos: en *Revisión de faltantes*, seleccionarlos y después *Acción > Crear ronda con
     los seleccionados*.
2. **En la PDA:** abrir la INT como cualquier otra y, ubicación por ubicación:
   - **Está donde decía:** leer el artículo y la ubicación.
   - **Está en otra caja** (la de al lado, otra talla...): leer el artículo y **la ubicación donde está**.
   - **No está:** no leer nada de esa línea.
3. **Validar la INT.** Odoo pregunta qué hacer con lo no leído:
   - **Crear pedido pendiente:** lo no leído sigue en una INT nueva para mirarlo otro día.
   - **Sin pedido pendiente:** lo no leído se da por perdido.
4. **Cada 15 minutos** (cron *KOROSHI Faltantes: actualizar rondas*) se actualizan los faltantes solos:

   | En la INT | Faltante |
   |---|---|
   | línea leída | **Encontrado**, con la ubicación donde se leyó (el stock ya ha vuelto con la INT) |
   | validada *Sin pedido pendiente* y la línea no leída | **No encontrado**: movimiento de FALTANTE a pérdidas de inventario |
   | *Crear pedido pendiente* | sigue **Pendiente**, ahora en la INT nueva (*Rondas* +1) |
   | INT **cancelada entera** | vuelve a **Pendiente** sin ronda (cancelar no es «no encontrado») |
   | línea de 2+ uds leída a medias | lo leído pasa a Encontrado y el resto queda como otro faltante |

Las rondas se ven en *Rondas de faltantes (INT)*. Mientras un faltante está en una ronda abierta no se puede marcar a mano:
se revisa en la INT.

## Revisión a mano (oficina)

*Inventario > KOROSHI Faltantes > Revisión de faltantes*: por defecto salen los pendientes. Hay filtros por día, operario,
estado, tipo y ronda, y se puede exportar a Excel (seleccionar > Exportar). Para casos sueltos fuera de ronda:

- **Encontrado:** se elige la ubicación y las uds vuelven de FALTANTE a ella.
- **No encontrado:** las uds van de FALTANTE a pérdidas de inventario. Es lo que antes se hacía poniendo a 0 en la PDA, pero
  ahora queda registrado.

*Puestos a 0 hoy* son los movimientos «Cantidad de producto actualizada» de hoy hacia pérdidas, agrupados por usuario.
Sirve para ver si se sigue poniendo a 0 desde la PDA en vez de usar esta pantalla.

## Qué cuenta y límites (v1)

- **Uds de la línea:** las uds de la línea de la OUT que no estaban.
- **Uds a FALTANTE:** las que se han movido de verdad. Nunca más de las que Odoo tiene libres en la ubicación vieja, porque
  si no Odoo quitaría reservas a otras OUT. Si ya no quedaba nada (alguien la puso a 0), se mueve 0 y se apunta en la nota.
- v1.0 - v1.2: solo líneas sin nada leído. **v1.3:** también líneas con una parte leída: lo leído se queda en la línea y
  solo se toca lo que falta (ver abajo). Líneas con lote, paquete o propietario: no (se hacen en la oficina).
  El 91 % de las líneas son de 1 ud.
- La ubicación nueva tiene que tener **libre al menos lo de la línea entera**. Si no, no se cambia nada y sale cuánto hay.
  Si Odoo reserva menos de lo esperado (otra PDA ha reservado a la vez), se deshace todo y sale el aviso.
- No se sabe si otra PDA tiene abierta la misma OUT. Por eso hay que salir de la OUT antes de usar la pantalla. Con las
  zonas, cada OUT la hace una persona.

## Cómo cambia la reserva (técnico)

- **Reubicar:** `write({'location_id': nueva})` sobre la `stock.move.line` reservada. Es el write estándar de Odoo 13, el
  mismo que usa la app de código de barras al cambiar de ubicación: quita la reserva de la vieja y reserva en la nueva
  con `strict=True`, solo de stock libre.
- **v1.3, línea con una parte leída:** `write({'product_uom_qty': leido})` en la línea (write estándar: devuelve al
  quant solo lo que falta) y, para reubicar, `move._update_reserved_quantity(falta, libre, nueva, strict=True)`, el método
  estándar con el que Odoo reserva. Para «No está», solo el write.
- **Validar (v1.3):** `button_validate()` del albarán, igual que la app de código de barras. Si devuelve el asistente de
  pedido pendiente, se crea con su contexto y `process()` (sí) o `process_cancel_backorder()` (no). Cualquier otro
  asistente no se toca. Todo en un savepoint.
- **No está en ningún sitio:** `unlink()` de esa `stock.move.line`. Es el estándar de Odoo: devuelve la reserva al quant y
  recalcula el estado del movimiento, como «Anular reserva» pero solo de esa línea.
- **A FALTANTE y en la revisión:** `stock.move` interno con su línea ya hecha (`qty_done`) y `_action_done()`, como hace
  Odoo al ajustar cantidades.
- Todo va dentro de un *savepoint*. Si algo falla, se vuelve atrás y se limpia la caché del ORM.
- **Ronda:** `stock.picking` del tipo de transferencias internas del almacén (`int_type_id`), de FALTANTE a EFFEC/Stock,
  con un `stock.move` por faltante. Se confirma con `_action_confirm(merge=False)`, para que cada faltante tenga su línea
  aunque se repitan artículo y ubicación, y después `action_assign()`. La INT solo reserva en FALTANTE, que está fuera de
  Stock: no quita nada a ninguna OUT. El enlace faltante ↔ movimiento está en la tabla propia (`ronda_move_id`).
- Los automatismos de Odoo sobre albaranes no afectan a la ronda (comprobado el 09/11):
  - «Bloq» solo actúa con el usuario 68, que está desactivado;
  - los controles S4T solo actúan con OUT validadas.

## Seguridad

- **No añade campos** a `stock.picking`, `stock.move`, `stock.move.line`, `stock.picking.batch` ni `stock.picking.type`.
  Ojo: el 03/11 un campo en `stock.picking.type` tumbó la PDA.
- No toca la app de código de barras, no usa «Forzar disponibilidad» y no escribe `stock.quant` a mano.
- **EFFEC/FALTANTE** es interna, dentro de la vista `EFFEC` pero **fuera de `EFFEC/Stock`**, así que ninguna OUT reserva
  allí. La pantalla se niega a funcionar si alguien la mueve dentro de Stock.
- Permisos:
  - la pantalla usa los permisos normales del usuario de almacén: puede crear faltantes, pero no borrarlos;
  - Encontrado / No encontrado solo los puede usar el responsable de almacén.
- Depende de `koroshi_operarios`, que hay que instalar antes.

## Ficheros

```
models/faltante.py              koroshi.faltante: alternativas, reubicar, sin_alternativa, revision, ronda, informe
data/cron.xml                   cron cada 15 min: actualizar faltantes desde las INT de ronda
wizard/encontrado.py            asistente Encontrado (elegir ubicacion)
controllers/main.py             /koroshi/faltantes/buscar, /reubicar, /sin_alternativa, /pendientes, /validar (json)
data/parametros.xml             v1.3: koroshi_faltantes.validar_sola y .pedido_pendiente (noupdate)
data/ubicacion.xml              EFFEC/FALTANTE (noupdate)
data/ubicacion_v131.xml         v1.3.1: renombra FALTANT -> FALTANTE (nombre y codigo de barras)
views/assets.xml                css y js en web.assets_backend
static/src/js/faltantes_pantalla.js  accion de cliente koroshi_faltantes_pantalla + boton en Operarios
static/src/xml/faltantes.xml    plantilla de la pantalla + t-extend de la pantalla de Operarios
static/src/css/faltantes.css    estilos (dentro de .o_koroshi_faltantes)
views/faltante_views.xml        lista, ficha, pivot, filtros, acciones
views/wizard_views.xml          formulario del asistente
views/menu.xml                  Inventario > KOROSHI Faltantes
security/ir.model.access.csv    permisos
```
