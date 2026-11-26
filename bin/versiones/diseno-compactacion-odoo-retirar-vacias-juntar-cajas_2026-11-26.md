# Compactación en Odoo: retirar cajas a 0 y juntar cajas (diseño, 26/11/2026)

**Estado: DISEÑO para Isaac. No hay código, ni versión, ni nada instalado.** Las dos tareas van en
`koroshi_contenedores` (servidor y repo en la 1.15.0, instalada el 24/11, tanda A). Regla 6: un módulo, una sesión.
Por eso las dos propuestas van juntas y saldrían en una sola versión, o en dos seguidas (la 1.16.0 y la 1.17.0).

Origen: el programa de Windows de solo lectura (`redistribucion/programa/`). Con la copia del 23/11 calculó lo
siguiente (`redistribucion/fase2b_compactacion-zona0_2026-11-26.md`, Excel `compactacion-zona0_20261126_1157.xlsx`):

- 13.188 cajas a 0 en la zona 0. Al retirarlas quedan libres 1.487 huecos.
- 2.524 cajas a mover. Liberan 1.216 huecos más.

**No hace falta ningún campo nuevo en `stock.picking`, `stock.picking.type` ni `stock.move.line` (regla 7).** Tampoco
en `stock.location`. Todo lo nuevo va en tablas propias del módulo.

---

## 0. Lo que ya existe (comprobado en el código, regla 10)

| Qué | Dónde | Qué hace hoy |
|---|---|---|
| Mover contenedor | `controllers/main.py:896` `/mover` | Cambia el `location_id` del KO_ (la ubicación hija) al hueco leído. Las prendas (quants) y las reservas de las OUT **no se tocan**: van con la caja. No crea albaranes. Deja una línea `mover` en `koroshi.contenedor.movimiento`. |
| Archivar desde el hueco | `main.py:299` `/archivar` | Archiva los marcados. Si uno tiene prendas o reservas, no archiva ninguno. Pide «¿físicamente vacíos?». |
| Archivar uno | `main.py:334` `/archivar_uno` (1.10.0) | Lo mismo desde la ficha del contenedor. |
| Antes de archivar | `main.py:454` → `koroshi.faltante.antes_de_archivar` | Los faltantes pendientes que apuntan a la caja pasan a apuntar a su hueco. Si alguno está en una ronda abierta, no se archiva. |
| Poner a cero | `main.py:461` `/cero` (1.11.0, 1.13.0) | Hace un ajuste contra pérdidas de inventario. Las líneas de OUT reservadas pasan por Faltantes: otro hueco o la OUT sale sin ellas, y el faltante se cierra como «no encontrado». Es todo o nada. No lo hace si hay algo leído. |
| Añadir prendas | `main.py:518` `/anadir` | Ajuste + desde pérdidas. Lleva un id de tanda para que un reintento no lo duplique. |
| Panel del hueco | `main.py:107` `_datos_hueco` | Las cajas del hueco con uds, reservadas y la marca `vacio`. En la PDA están los botones «Marcar vacíos» y «Archivar marcados». |
| Inventario del lineal | `main.py:127` `_datos_lineal` | Al leer «L67» salen los huecos con nº de cajas, cajas con stock y uds. El lineal se saca del nombre del hueco. |
| Lecturas ve el cambio de hueco | `koroshi_preparacion` 3.35.0 (R7, instalada el 24/11) | Si la ubicación de una línea cambia, la PDA recarga la OUT. Sin leer, se refresca cada 30 s. |
| Faltante encontrado | `koroshi_faltantes/models/faltante.py:616` `marcar_encontrado(ubicacion)` | Devuelve las uds de FALTANTE a la ubicación que se diga. |

Conclusión: **mover, archivar, poner a cero y añadir ya funcionan y están probados en el almacén**. Lo que falta es:

- la **lista de trabajo** (qué cajas y en qué orden);
- el **modo ronda** en la PDA (ir hueco a hueco sin tener que pensar);
- el **avance por lineal**.

---

## 1. Retirar cajas a 0

### 1.1 Qué es una «caja a 0» y cómo sale la lista (en vivo, en Odoo)

Una caja a 0 es un contenedor KO_/TT_ que cumple todo esto:

- está activo, es interno y es de la compañía 8;
- su padre es un hueco de un lineal entre **L44 y L136** (zona 0);
- no tiene ningún quant con `quantity != 0` ni con `reserved_quantity != 0`;
- **no tiene ninguna línea de movimiento abierta que salga de ella o vaya a ella.** Esto es nuevo: hoy `/archivar` no lo
  mira. Una caja de una recepción en curso está a 0 hasta que se valida, y archivarla rompería la recepción.

El rango de lineales va en un parámetro, `koroshi_contenedores.cajas_cero_lineales = 44-136`. Así se puede ampliar a
la zona Z (763 cajas en 86 huecos de L01–L43) sin sacar otra versión.

**Por qué por lineal y no por «zona del hueco»:** un hueco que solo tiene cajas a 0 no tiene stock con el que
clasificarlo (I27/V27). El programa usa el lineal por la misma razón.

**Cálculo:** una sola consulta SQL de solo lectura con contenedores, padre y quants agrupados. No se guarda nada, así
que la lista siempre es la de ese momento: si alguien mete prendas en una caja, deja de salir. Hay dos vistas:

- **Resumen de lineales (PDA):** lineal, huecos con cajas a 0, cajas a 0, huecos que quedan libres al retirarlas y
  cajas «tiene prendas» pendientes. Ordenado por lineal.
- **Un lineal:** hueco a hueco (P y C en orden de pasillo), con sus cajas a 0 y, aparte, las que tienen stock (para que
  el operario no las toque).

Coste: unas 20.000 cajas a 0 en la nave. Con SQL agrupado debería tardar menos de 1 s, pero **hay que medirlo**. Si
tarda más, el resumen se calcula una vez cada pocos minutos y se guarda en memoria (como la caché del monitor), nunca
en una tabla.

### 1.2 Lo que hace el operario en la PDA

En la pantalla de Contenedores, botón nuevo **«Retirar cajas a 0»**:

```
┌──────────────────────────────┐
│ Retirar cajas a 0            │
│ L44   12 huecos  31 cajas    │
│ L45    8 huecos  19 cajas  ✓5│   ✓ = huecos que quedan libres
│ L67   40 huecos 112 cajas    │
│ …                            │
│ [Lee un lineal o un hueco]   │
└──────────────────────────────┘
```

1. **Lee el hueco** (su código de barras) o toca un lineal y va al primero pendiente. Sale el hueco:

```
┌──────────────────────────────┐
│ L67 P16 C2                   │
│ A 0 en Odoo (retirar):       │
│  ☐ KO_090726_045             │
│  ☐ KO_090726_046             │
│  ☐ KO_090726_047             │
│ Con prendas (no tocar):      │
│    KO_090726_051  24 uds     │
│                              │
│ Lee cada caja a 0.           │
└──────────────────────────────┘
```

2. **Lee cada caja a 0** que tiene delante. Leerla la marca ☑ («vista»). Una caja con stock leída aquí pita en rojo:
   «tiene 24 uds: no se retira». Una caja de otro hueco: «es de L67 P18 C1». En ninguno de los dos casos se mueve nada.
3. Al tocar una caja vista salen dos botones:
   - **«Vacía»** (lo normal, y lo que vale por defecto);
   - **«Tiene prendas»** (ver 1.4).
4. Botón **«Retirar las vacías (3)»**. Confirmación «¿Están físicamente vacías y las quitas del palé?». Se archivan
   todas a la vez. El operario saca las cajas del palé, a la pila de cajas vacías.
5. Si quedan cajas a 0 sin leer, sale **«No están (2)»**: la caja está en Odoo y no en el palé. Pide otra confirmación
   y se archivan con la nota «no estaba en el hueco». Así se limpian los 1.487 huecos que a lo mejor ya están vacíos de
   verdad.
6. Si el hueco queda sin ninguna caja, sale **«✓ L67 P16 C2 queda libre»** y va al siguiente hueco del lineal.

Se usa el lector «leer al parar» y la tarjeta de `koroshi_base` (1.15.0), los mismos de ahora.

### 1.3 Lo que pasa en Odoo

Se reutiliza `/archivar` con tres cambios:

- Mira las **líneas de movimiento abiertas** (`stock.move.line` con `location_id` o `location_dest_id` = la caja y
  `state` distinto de done/cancel). Si hay alguna, no se archiva: «KO_… está en IN/… sin validar».
- Usa `pda.empleado_valido`. Hoy `/limpiar` (`main.py:182`) y `/mover` (`main.py:900`) aceptan cualquier
  `hr.employee`; el resto de rutas usa la regla de la 1.15.0.
- Línea `archivar` en `koroshi.contenedor.movimiento` con «vacía, ronda» o «no estaba en el hueco» en `destino`.

Sigue pasando `antes_de_archivar` (faltantes con vuelta a la caja). **No hay ajuste de stock**: la caja está a 0, así que
archivarla no cambia ninguna cantidad. Es el caso de la KO_090726_030, la 032, la 046 y la 047 de la foto.

### 1.4 Casos especiales

**a) Reservas.** Por definición, una caja de la lista no tiene reservas. Si tiene `reserved_quantity` sin `quantity`
(un quant descuadrado), no es «a 0»: sale en el resumen como **«Revisar»**, no en la ronda. Para esas está ya «Poner a
cero» (1.11.0), que pasa las reservas por Faltantes. No se toca nada de las OUT desde la ronda.

**b) Stock negativo (26 casos en la copia).** Una caja con −2 uds no está a 0. Normalmente quiere decir que se sacó de
ella algo que Odoo tenía en otro sitio, así que la diferencia real está en otra caja. Propuesta: **salen en «Revisar»,
en rojo, y el operario no las retira.** Un jefe las abre y decide entre:

- «Poner a cero», que con cantidad negativa ya hace un ajuste + (`main.py:506`) y después «Archivar»;
- buscar la otra caja con «¿Dónde está?» (1.6.0).

→ **Decisión 1 de Isaac.**

**c) Caja a 0 en Odoo con prendas dentro (la KO_090726_045).** Es stock que hay y Odoo no tiene: lo contrario de un
faltante. Propuesta: «Tiene prendas» abre el modo de leer prendas que ya existe («Añadir prendas»), y al «Guardar» Odoo
mira cada artículo **por este orden**:

1. ¿Hay un **faltante pendiente** de ese artículo con `ubicacion_vieja_id` = esta caja o su hueco? Entonces es esa
   prenda: `marcar_encontrado(caja)`. Pasa de FALTANTE a la caja sin ajuste contra pérdidas, y el faltante queda
   «Encontrado».
2. Si no, ¿hay un faltante pendiente de ese artículo en cualquier sitio? Se avisa («Hay un faltante de este artículo de
   L70 P02: ¿es esta?») y el operario elige entre «Sí, es esa» y «No, añadir».
3. Si no, es un **ajuste + contra pérdidas de inventario**, como «Añadir prendas», con la acción `anadir` y la nota «caja
   a 0 con prendas (ronda)».

La caja **no se retira**: tiene stock y se queda en el palé. Sale de la lista porque ya no está a 0.

Alternativa: no tocar stock en la ronda, apuntar «tiene prendas» y dejarlo en una lista para Soporte o Faltantes.

→ **Decisión 2 de Isaac.** Recomiendo la primera: lo arregla en el acto el que tiene la prenda en la mano, y el paso 1
cierra faltantes que hoy se dan por perdidos.

**d) Etiqueta de la caja retirada.** Al archivar la KO_, su etiqueta deja de servir: leerla da «No encuentro el
contenedor (o está archivado)». Si la caja física se vuelve a usar con la misma etiqueta, en recepción saldría ese
error. → **Decisión 3 de Isaac:** quitar o tachar la etiqueta al retirar la caja (propuesta), o desarchivar al leerla en
Recepción (más código, y en otro módulo).

### 1.5 Datos

- **Sin tablas nuevas.** La lista se calcula en vivo y el rastro queda en `koroshi.contenedor.movimiento`, que ya
  existe.
- Un valor nuevo en el campo `accion` (tabla propia): `revisar_prendas`, para «tiene prendas» si Isaac elige la
  alternativa de 1.4 c. Con la propuesta recomendada no hace falta, porque se usan `anadir` y el registro de Faltantes.
- Un parámetro: `koroshi_contenedores.cajas_cero_lineales`.
- Avance: el resumen de lineales es el avance. Las cajas a 0 que quedan se cuentan en vivo, y las retiradas hoy salen
  del registro (filtro «Hoy» + acción «Archivar vacío», agrupado por persona, en la vista que ya existe).

### 1.6 Riesgos para el almacén

| Riesgo | Qué se hace |
|---|---|
| Archivar una caja que una IN o una INT van a llenar | Comprobación nueva de líneas abiertas (1.3). Hoy no se mira. |
| El operario retira una caja con stock al confundirse de etiqueta | Solo se archivan las **leídas** y a 0 en Odoo. Leer una con stock pita en rojo. |
| «No están» archiva cajas que sí están detrás de otras | Hace falta otra confirmación, con la lista. Queda la nota «no estaba» y se puede desarchivar desde Odoo. |
| Lentitud en la PDA con lineales grandes | Una consulta por lineal. Medirla antes de instalar (debería ir por debajo de 1 s). |
| Instalar en horas de trabajo saca las sesiones | Instalar fuera de horas; un `-u` de contenedores arrastra el menú. |

---

## 2. Juntar cajas (compactar)

### 2.1 De dónde sale la lista: ¿calcularla en Odoo o importarla del programa?

| | Calcular en Odoo | Importar del programa (Excel) |
|---|---|---|
| Litros por ud | **No están en Odoo**: salen del MASTER v14 (Excel, packing list), en 549 de 562 modelos-color. Habría que subirlos a Odoo (¿a qué campo? `product.volume` es estándar, pero la ficha la usan otros) | Ya los tiene |
| ABC (líneas de 28 días) | Una consulta pesada sobre `stock.move.line`, en un cron nocturno | Ya lo calcula (copia en SQLite) |
| Reglas (mitad, colores, A en C1–C2, restos al fondo, 90 %) | Pasar a `logica.py` unas 400 líneas de `compactar.py`, con sus pruebas. Quedarían **dos copias** de las reglas | Una sola copia, ya probada (47 pruebas) y revisada por Isaac en el Excel |
| Frescura | En vivo | Tan vieja como la copia (hoy la del 23/11). Hay que comprobar cada paso al hacerlo |
| Riesgo en producción | Cálculo pesado en el servidor de la PDA (ya hubo sustos con transacciones largas: feed S4T del 19/11) | Ninguno: el cálculo va en el PC |
| Capacidad del hueco | 770 L sin medir, en los dos | Igual |

**Propuesta: importar**, con una comprobación en vivo de cada paso al ejecutarlo. Pasar el cálculo a Odoo más adelante,
cuando estén medidos la capacidad del hueco y las reglas, si hace falta recalcular cada día.

1. El programa saca, de una **copia del mismo día**, un fichero `plan_compactacion_AAAAMMDD.xlsx` con una fila por caja:

   `orden, lineal_origen, hueco_origen, contenedor, hueco_destino, modelo-color, uds, litros, clase, resto_talla`

   Es la hoja «Cajas a mover» que ya existe, más el orden.
2. En Odoo, *Inventario › KOROSHI › Compactación › Importar plan* (solo jefes). Al importar se comprueba cada fila:
   - la caja existe, está activa y **está en el hueco de origen**;
   - el destino existe y es un hueco.

   Lo que no cuadre se importa como «Saltado (al importar)», con el motivo. Si se importa un plan nuevo, el anterior
   queda «Sustituido» y sus pasos pendientes ya no se ofrecen.

### 2.2 Datos (tablas propias, nada en tablas compartidas)

- **`koroshi.compactacion.plan`**: nombre, fecha de la copia, fichero, quién lo importó, estado (activo o sustituido) y
  totales.
- **`koroshi.compactacion.paso`**:
  - `plan_id`, `orden`, `lineal`;
  - `contenedor_id` (`stock.location`), `origen_id`, `destino_id` y `destino_real_id`;
  - `modelo_color`, `uds`, `litros`, `clase`, `resto`;
  - `estado`: pendiente, hecho, cambiado (a otro destino), saltado, no está;
  - `motivo`, `employee_id`, `fecha` y `movimiento_id` (la línea de `koroshi.contenedor.movimiento`).
- `koroshi.contenedor.movimiento`: campo nuevo `paso_id`, en tabla propia.

### 2.3 Cómo se registra que una caja cambia de hueco

**Igual que hoy**, con `/mover`: cambia el `location_id` del KO_, y las prendas y las reservas viajan con la caja (sin
albarán ni `stock.move`). Lecturas ve el hueco nuevo (R7, instalado). Lo nuevo es esto:

- `/mover` recibe un `paso_id` opcional. Si llega, se comprueba en vivo, dentro de la misma petición:
  - la caja sigue en el hueco de origen del paso. Si no, el paso pasa a «saltado» con el motivo «ya no está en el
    hueco de origen»;
  - la caja **no tiene prendas leídas sin validar** en una OUT (`_leidas`, `main.py:399`). Si las tiene: «la está
    preparando X: déjala para luego». Que tenga reservas no lo impide (viajan con ella);
  - si el destino leído no es el del plan, se acepta como **«cambiado»** (el palé estaba lleno), pero antes se comprueba
    en vivo la regla de los colores: si el destino tiene el mismo modelo en otro color, sale un aviso en rojo y hay que
    pulsar otra vez «Confirmar».
- Una línea `mover` en el registro, con `paso_id`. El paso queda «hecho» o «cambiado».

El 90 % del destino **no** se recalcula en vivo, porque en Odoo no están los litros. El plan ya lo cuenta, y el
operario dice «No cabe» si lo ve lleno.

### 2.4 Lo que lee el operario, y en qué orden

Botón nuevo **«Compactar (plan)»** en Contenedores. Sale el resumen por lineal (2.5) y el operario toca uno o lee el
lineal. El orden lo marca el plan (beneficio: primero los huecos que se vacían con menos cajas), **agrupado por hueco de
origen**, para que vacíe un hueco entero antes de pasar al siguiente.

```
┌──────────────────────────────┐
│ L67 · paso 3 de 41           │
│ Vaciar L67 P22 C1 (2 cajas)  │
│                              │
│  KO_150726_118  12 uds       │
│   2622JA00-000003 NEGRO      │
│   → L68 P05 C2               │
│  KO_150726_119   8 uds       │
│   (mismo modelo-color, mismo │
│    destino)                  │
│                              │
│ 1) Lee las cajas             │
│ 2) Lee el hueco de destino   │
│ [No está] [No cabe] [Saltar] │
└──────────────────────────────┘
```

1. **Lee la caja** (o las dos, que van al mismo destino: la cola de mover ya admite varias). Si lee una caja que no es
   del paso: «Esa no está en el plan de este hueco».
2. **Lee el hueco de destino.** Si es el del plan, ✓ y pitido bueno. Si es otro, aviso y confirmar (2.3).
3. Cuando todas las cajas del origen están hechas: **«✓ L67 P22 C1 libre»** y pasa al siguiente hueco de origen.
4. Botones:
   - «No está»: la caja no está en el hueco. Paso «no está», sin cambiar nada en Odoo; queda para revisar.
   - «No cabe»: el destino está lleno. El operario puede leer otro hueco (paso «cambiado») o dejar el paso «saltado».
   - «Saltar»: lo deja para luego, sigue pendiente y va al final.

**Antes de compactar un lineal, retirar sus cajas a 0.** El plan da por hecho que ya no están. Si al abrir el lineal le
quedan cajas a 0, sale el aviso «L67 tiene 112 cajas a 0: retíralas primero», con un botón para ir a la ronda de la
parte 1. Avisa, no bloquea.

### 2.5 Avance por lineal

- **En la PDA**, la pantalla «Compactar (plan)» muestra, por lineal:
  - pasos hechos / total;
  - huecos libres / previstos;
  - pasos saltados, «no está» y «cambiado».

  Se calcula desde `koroshi.compactacion.paso`.
- **En Odoo (oficina):** la lista de pasos con filtros por estado, agrupada por lineal y por persona, y una tabla
  dinámica lineal × estado. Desde ahí se ven y se reabren los «no está» y los saltados.
- Nada en el monitor por ahora. Si Isaac lo quiere en la pantalla del almacén, sería otro módulo y otra sesión.

### 2.6 Riesgos para el almacén

| Riesgo | Qué se hace |
|---|---|
| Plan viejo: entre la copia y el día de mover se ha preparado, ha entrado stock y se han hecho las INT de zonas de las 04:50 | Copia del mismo día, comprobación en vivo de cada paso (2.3), y «no está»/«no cabe» con su motivo. Recomendado: el plan del día se usa ese día; si no, se recalcula |
| Mover una caja mientras un preparador va hacia ella | Las cajas con prendas leídas no se mueven. Las reservadas sí, y Lecturas recarga (R7) en 30 s o al leer. Mejor compactar cada lineal cuando no tiene oleada abierta (lo decide el jefe) |
| Mezclar colores al cambiar de destino | Aviso en vivo con el modelo-color del destino (2.3) |
| Pasar del 90 % | Solo el plan lo controla (no hay litros en Odoo). El operario lo ve y usa «No cabe» |
| Importar dos planes a la vez | Un solo plan activo; el anterior queda «Sustituido» |
| Volumen de escritura | 2.524 pasos y otras tantas líneas de registro: poca cosa |

---

## 3. Qué hay que decidir (Isaac)

1. **Stock negativo (26 cajas):** ¿solo para un jefe en «Revisar» (propuesta) o que el operario las ponga a cero?
2. **Caja a 0 con prendas (la 045):** ¿se resuelve en el acto (primero un faltante pendiente y, si no hay, un ajuste +;
   propuesta) o se apunta para Soporte o Faltantes?
3. **Etiqueta de la caja retirada:** ¿se quita o se tacha (propuesta)?
4. **Plan de compactación:** ¿importar el Excel del programa (propuesta) o calcularlo en Odoo? Si se calcula en Odoo, hay
   que decidir dónde se guardan los litros por ud del MASTER.
5. **Orden de las versiones:** ¿primero «Retirar cajas a 0» sola (1.16.0, más corta y sin tablas nuevas) y después
   «Compactar (plan)» (1.17.0)? Es la propuesta.
6. **Capacidad del hueco:** los 770 L siguen sin medir. El plan se puede importar igual, pero el 90 % depende de esa
   medida.

## 4. Qué hay que probar

**Sin Odoo (pruebas de `logica.py`):**

- qué es una «caja a 0» (quants, reservas, negativos);
- rango de lineales del parámetro;
- leer el Excel del plan (columnas, filas malas);
- orden de los pasos agrupados por origen;
- regla «mismo modelo, otro color» para el destino cambiado.

**En Odoo, en el navegador, con cajas de prueba (no en OUT reales):**

- crear dos KO_ de prueba en un hueco: una a 0 y otra con una prenda;
- una caja a 0 en una IN sin validar no se archiva;
- «No están» con confirmación;
- «Tiene prendas» con un faltante pendiente de esa caja (Encontrado) y sin él (ajuste +);
- importar un plan de tres filas, una ya movida a mano (al importar queda «Saltado»);
- mover a otro destino con el mismo modelo en otro color (aviso).

**Medir:** el tiempo de la consulta del resumen de lineales en la base de datos real (de solo lectura, con permiso).

**En una PDA real:**

- ronda en L67 P16, el hueco de la foto (030/032 y 046/047 retiradas; 045 con su prenda);
- lector «leer al parar» con varias cajas seguidas;
- un lineal de compactación entero con el preparador trabajando al lado: comprobar que Lecturas ve el hueco nuevo.

**No se puede probar sin instalar:** la pantalla de la PDA y el importador. Se instala fuera de horas, con el sí de
Isaac. El `-u` de contenedores arrastra `koroshi_menu`.

## 5. Aparte (no es de este encargo)

- `/mover` y `/limpiar` no usan `pda.empleado_valido` (la tarjeta de un operario dado de baja vale). Se arregla dentro
  de la 1.16.0, porque es el mismo módulo.
