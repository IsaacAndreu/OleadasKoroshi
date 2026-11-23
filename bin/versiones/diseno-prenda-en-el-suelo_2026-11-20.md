# Prenda en el suelo: «¿A dónde va esto?» en la PDA — diseño v1 (20/11/2026)

**Estado: solo diseño. No hay código ni nada instalado.** Espera el visto bueno de Isaac (preguntas al final).

Lo que pidió Isaac (20/11): «al picking o bueno algun lloc si es troben una prenda enterra deberien tindre un boto que
els hi digue esta va a X mes o menys sas la ubicacio de la gent per lo lineal que estiguen o estiguen anan aixi
podrien ells agafar i ficar-ho a una caixa de estes que estigue aprop».

## 1. Qué hace, visto desde la PDA

1. El operario pulsa **«Prenda en el suelo»** (en el Inicio PDA, y más adelante también en Lecturas).
2. Lee el **EAN de la prenda**. Opcional: lee el **hueco que tiene delante** (así se sabe dónde está él; si no lo lee,
   se usa su última lectura).
3. La PDA contesta con **una sola orden en grande**, la primera que se cumpla de esta lista:

| # | Caso | Lo que dice la PDA |
|---|---|---|
| A | La prenda está apuntada como **faltante pendiente** (koroshi_faltantes, estado «Pendiente») | «ESTA ES UN FALTANTE de la OUT S-…. Pulsa *Encontrada* y llévala a **L45 P12 C3**» (o a la persona del caso B si alguien la está pidiendo ahora) |
| B | Hay una **OUT haciéndose ahora** (asignación «Haciéndose») con esa prenda **por leer** | «Dásela a **MARÍA** — está en **L42**, va hacia **L45** (hace 2 min). Pedido S-6665…, caja de su carro.» Si hay varias, la persona más cerca de ti por lineal |
| C | Hay una OUT **en cola / sin empezar** con esa prenda reservada | «Va a una OUT que aún no ha empezado nadie: **déjala en su hueco L45 P12 C3**» (allí la cogerá quien la prepare) |
| D | **No le falta a nadie** | «No la pide nadie. Vuelve a **L45 P12 C3**» (el hueco donde Odoo tiene stock de esa prenda, el lineal más cercano a ti) |
| E | No hay stock de esa prenda en ningún hueco | «Odoo no la tiene en ningún hueco: déjala en **FALTANTE / mesa de jefes**» y queda apuntada para la oficina |

Debajo de la orden, en pequeño, las otras opciones (2.ª persona, otros huecos) por si la primera no sirve, y un botón
**«Hecho»** que deja apuntado qué se hizo.

## 2. Qué datos hay hoy (comprobado en el código)

| Pregunta | De dónde sale | Dónde |
|---|---|---|
| ¿Qué OUT le falta esa prenda? | `stock.move.line` no hechas con `qty_done < product_uom_qty` y el producto | mismo criterio que `koroshi_faltantes/models/faltante.py:273` (`lineas_pendientes`) y el buscador `koroshi_buscador_stock/controllers/main.py:187` (`_reservas`) |
| ¿Quién está haciendo esa OUT ahora? | `koroshi.operario.asignacion` (estado `curso`, `employee_id`, `picking_id` / `batch_id`) | `koroshi_operarios/models/reparto.py:256` |
| ¿Dónde está cada operario? | **No hay nada que lo diga.** Se puede sacar de su última `koroshi.preparacion.lectura` con `move_line_id` → ubicación → lineal | `koroshi_preparacion/models/lectura.py:54` (modelo), `:162` (`_ubi`) |
| ¿Hacia dónde va? | La siguiente línea por leer de su OUT en el orden de la ruta | `koroshi_preparacion/models/lectura.py:287` (`_clave`), `koroshi_preparacion/models/ruta.py` |
| Su zona / tramo (si no ha leído nada aún) | Zona = nombre de la agrupación Z-ddmm-<zona>; tramo `lineal_desde/hasta` | `koroshi_operarios/models/tarea.py:136`, `reparto.py:167` |
| Lineal de una ubicación (L94, MU-01) | Hay 6 reglas distintas; la más completa (con MU) es `_lineal` de Contenedores | `koroshi_contenedores/controllers/main.py:36-46`; la de faltantes `faltante.py:60` |
| Faltantes pendientes de esa prenda | `koroshi.faltante` (`product_id`, `estado`, `ubicacion_vieja_id`) | `koroshi_faltantes/models/faltante.py:83` |
| A qué hueco vuelve si no la pide nadie | Stock libre por hueco, ordenado por lineal más cercano | `faltante.py:187-235` (`_libre_por_ubicacion`, `alternativas`) |
| Caja CJ «abierta» | **No hay caja abierta como tal**: la CJ se crea al cerrar (`put_in_pack`, `lectura.py:849-915`). Mientras tanto, lo leído está «fuera de caja» (`en_caja` vacío, `_sin_caja` `lectura.py:280`). La «caja de al lado» de verdad es **el carro del operario que hace la OUT** | `lectura.py:73`, `:280` |
| Tarjeta del operario que la encuentra | localStorage `koroshi_operarios_pda_<uid>` (`hr.employee`) | `koroshi_operarios/static/src/js/operarios_pantalla.js:203-227` |

## 3. La regla importante: la prenda se **lee** donde toca, no se mete a ciegas

Meter la prenda en una caja sin leerla descuadra la caja (S4T, faltantes y el recuento la darían como sobrante). Por
eso la PDA **nunca** dice «métela en la caja X»: dice **a quién dársela** o **a qué hueco devolverla**.

- **Caso B**: la recibe el operario de la OUT y la **lee él en Lecturas** como una más de su ruta. Odoo la saca del
  hueco reservado. Si la prenda cayó justo de ese hueco (lo normal), el stock queda bien.
- **Caso A** (faltante): la unidad está en EFFEC/FALTANTE, no en el hueco. Antes de dársela a nadie hay que pulsar
  **«Encontrada»**, que la devuelve de FALTANTE al hueco con la lógica que ya existe en koroshi_faltantes. Si no, el
  picker la leería desde un hueco donde Odoo ya no la tiene.
- **Riesgo que no se puede evitar**: si la prenda cayó de **otro** hueco distinto del reservado, Odoo descuenta del
  reservado. Es el mismo descuadre que hoy al coger del hueco de al lado; el recuento por referencia (koroshi_recuentos)
  lo detecta. Se apunta en el registro para poder revisarlo.

Opción descartada para la v1: que quien la encuentra la lea él mismo dentro de la OUT de otro («preparar a dos»,
`lectura.py:284`). Funciona, pero parte la OUT entre dos y cambia lo que ve el compañero en su PDA.

## 4. Posición de la gente (el «més o menys» de Isaac)

Para cada operario con asignación «Haciéndose»:

1. **Dónde está**: lineal de su última lectura con línea (`move_line_id`), y **hace cuántos minutos**.
2. **Hacia dónde va**: lineal de su siguiente línea por leer en el orden de la ruta.
3. Si no ha leído nada en 10 min o no tiene lecturas: su **zona/tramo** («por la zona D1, L30-L48»), marcado como
   aproximado.
4. Quien la encuentra: el hueco que lea en el paso 2, o su última lectura, o nada (entonces no se ordena por cercanía).

Distancia = diferencia de lineales (como ya hace faltantes); MU cuenta como lineal propio. Se elige la persona con
la línea pendiente cuya posición actual o siguiente parada esté más cerca de quien la encontró.

No hace falta GPS ni balizas: es lo que se sabe por las lecturas. Lo que **no** se sabe: dónde está alguien que no
está leyendo (descanso, carro, muelle).

## 5. Dónde va: módulo y pantalla

**Recomendado: un módulo nuevo pequeño, `koroshi_prenda_suelo`**, con su pantalla de PDA (acción de cliente) y una
entrada en el **Inicio PDA, área «Picking»** (también vale «Extra»).

Por qué no dentro de otro módulo:

- **koroshi_actividades** (Inicio PDA) lo lleva la sesión «PDA: entrada única». No hace falta tocar su código: el botón
  del Inicio es un registro `koroshi.actividad` con `area` y `abre` = id de la acción (`koroshi_actividades/models/
  actividad.py:64-67`). Ese registro lo crea el módulo nuevo en su XML (registro normal, **sin** `<function>` noupdate,
  que solo corre al instalar).
- **koroshi_faltantes** sería el sitio natural (ya tiene lineales, huecos y «Encontrado»), pero lo tiene cogido la
  sesión «Ronda de faltantes». El módulo nuevo **llama** a sus métodos (`alternativas`, «Encontrado») sin cambiarlos.
- **Lecturas** (koroshi_operarios / koroshi_preparacion) es donde más se usaría, pero tocar Lecturas es tocar lo que
  más se usa en el almacén. **Fase 2**: un botón «Prenda en el suelo» en Lecturas que abre la misma pantalla con la
  tarjeta ya puesta (un cambio de una línea en el JS de Lecturas, en la sesión que tenga operarios).

Depende de: `koroshi_base`, `koroshi_operarios`, `koroshi_preparacion`, `koroshi_faltantes`, `koroshi_actividades`.

**Sin campos nuevos** en `stock.picking`, `stock.picking.type` ni `stock.move.line`. Solo una tabla propia:

`koroshi.prenda.suelo` — fecha, operario que la encontró, producto, hueco leído (opcional), caso (A-E), a quién /
a qué hueco se mandó, OUT, resultado («Hecho» / «No sirve»). Con menú en la oficina: «Prendas del suelo hoy».
Sirve para ver cuántas aparecen y de qué lineales caen.

Para el lineal: usar una regla común. Propuesta: subir la de Contenedores (con MU) a `koroshi_base.comun`
(`lineal_de(texto)`), en su propia versión de koroshi_base, y que el módulo nuevo la use. Los demás módulos se pasan
uno a uno cuando toque (regla 8).

## 6. Fases

| Fase | Qué | Toca |
|---|---|---|
| 1 | Pantalla PDA + casos A-E + registro + entrada en Inicio PDA (área Picking) | `koroshi_prenda_suelo` 1.0.0 (nuevo) y `koroshi_base` 1.2.0 (`lineal_de`) |
| 2 | Botón en Lecturas | koroshi_operarios (la sesión que lo tenga) |
| 3 (idea) | Aviso en la PDA del picker: «JUAN te trae la prenda X» (aparece en su Lecturas en el siguiente refresco) | koroshi_preparacion |

## 7. Preguntas para Isaac

1. **¿Dónde el botón primero?** Inicio PDA (Picking o Extra) en la fase 1 y Lecturas en la fase 2, ¿vale?
2. **Caso B**: ¿quien la encuentra se la **lleva** al compañero, o la deja en el hueco reservado y el compañero la
   coge al pasar? (Lo segundo es más simple y no descuadra nada; lo primero es más rápido.)
3. **Caso E** (no la tiene ningún hueco): ¿a dónde se deja físicamente? ¿FALTANTE, mesa de jefes, caja de incidencias?
4. ¿Vale un **módulo nuevo** (`koroshi_prenda_suelo`) en vez de meterlo en faltantes?
5. ¿Leer el hueco de delante es **obligatorio** (mejor cercanía) u **opcional** (más rápido)?
6. ¿Agrupaciones Z- (zonas): la «OUT haciéndose» es la agrupación entera del operario? (Así lo propone el diseño.)

## 8. Qué habrá que probar en una PDA real (cuando haya código)

- Prenda con faltante pendiente → «Encontrada» la devuelve al hueco y la OUT la puede leer.
- Prenda de una OUT haciéndose → sale el nombre correcto y el lineal de la última lectura.
- Prenda que no pide nadie → hueco correcto, y nada se mueve en Odoo.
- Que la pantalla no toque la tarjeta ni la tarea de quien la usa (vuelve a Lecturas con el mismo operario).
- Solo lectura en OUT reales: la pantalla no lee, no cierra cajas ni valida nada en la OUT de otro.
