# Compactación en Odoo: retirar cajas a 0 y reagrupar KO (diseño v4, 26/11/2026)

**Estado: DISEÑO v4 para Isaac.** La v1, la v2 y la v3 se conservan tal cual.

**Cambios de la v4 (respuestas de Isaac del 26/11):**

- **Nombre:** la parte 2 pasa a llamarse **«Reagrupar KO»**. «Juntar cajas» ya es otra cosa en Expediciones
  (`koroshi_juntar_cajas`).
- **9. KO vacía con una prenda reservada:** ya está hecho desde la 1.11.0, con «Poner a cero» (2.6).
- **10.** Una etiqueta en cada caja.
- **11.** La recepción sigue con una KO por caja.
- **12.** 8 cajas por ubicación.


- **Parte 1 (1.16.0, retirar cajas a 0):** escrita a partir de la v2, sin empaquetar ni instalar. No cambia.
- **Parte 2 (1.17.0, reagrupar KO):** sin código. **Lo nuevo de la v3 es el apartado 2.6:** la KO mixta y las tallas
  por altura que decidió Isaac el 26/11 (idea de Andrés), con los datos de la sesión del mapa (`redistrib/compactar.py`:
  `ko_mixta` y `tallas_por_altura`). También cambian el 2.4, el 3 y el 4.

**Cambios respecto a la v1, con las respuestas de Isaac del 26/11:**

| Decisión de Isaac | Dónde está en el diseño |
|---|---|
| Las 26 cajas con stock negativo las revisa Isaac a mano desde Contenedores. Solo pueden él y `almacen2`; con tarjeta, Betty, José Luis e Isaac | 1.4 b |
| Las cajas a 0 con prendas las resuelven José Luis, Betty, Jordi y Darwin | 1.4 c |
| El plan de compactación se calcula en Odoo, no se importa del programa | 2.1 y 2.2, rehechos |
| Primero la 1.16.0 (retirar cajas a 0) y después la 1.17.0 (compactar) | 3 |
| La etiqueta es la del KO_ pegada en la caja física | 1.4 d |
| Cómo medir la capacidad de un hueco | 5 |

Las dos tareas van en `koroshi_contenedores` (servidor y repo en la 1.15.0). Regla 6: un módulo, una sesión.

**No hace falta ningún campo nuevo en `stock.picking`, `stock.picking.type` ni `stock.move.line` (regla 7).** Tampoco
en `stock.location`, `product.product` ni `hr.employee`. Todo lo nuevo va en tablas y parámetros propios del módulo.

---

## 0. Lo que ya existe (comprobado en el código, regla 10)

| Qué | Dónde | Qué hace hoy |
|---|---|---|
| Mover contenedor | `controllers/main.py:896` `/mover` | Cambia el `location_id` del KO_ al hueco leído. Las prendas y las reservas de las OUT van con la caja. No crea albaranes. Deja una línea `mover` en `koroshi.contenedor.movimiento` |
| Archivar desde el hueco | `main.py:299` `/archivar` | Archiva las cajas marcadas. Si una tiene prendas o reservas, no archiva ninguna. Pide «¿físicamente vacíos?» |
| Archivar una | `main.py:334` `/archivar_uno` (1.10.0) | Lo mismo, desde la ficha del contenedor |
| Antes de archivar | `main.py:454` → `koroshi.faltante.antes_de_archivar` | Los faltantes con vuelta a la caja pasan a apuntar a su hueco. Con una ronda abierta, no archiva |
| Poner a cero | `main.py:461` `/cero` | Ajuste contra pérdidas. Las reservas pasan por Faltantes. Todo o nada. Con cantidad negativa, el ajuste es + (`main.py:506`) |
| Añadir prendas | `main.py:518` `/anadir` | Ajuste + desde pérdidas, con id de tanda |
| Panel del hueco y del lineal | `main.py:107`, `main.py:127` | Cajas del hueco con uds y reservadas; huecos del lineal |
| Lecturas ve el cambio de hueco | `koroshi_preparacion` 3.35.0 (R7, instalada el 24/11) | Recarga la OUT si cambia la ubicación de una línea |
| Faltante encontrado | `koroshi_faltantes/models/faltante.py:616` `marcar_encontrado(ubicacion)` | De FALTANTE a la ubicación que se diga |
| Temporada | `product.template.season_id` (I27, V27…) | El programa la lee de ahí (`redistribucion/programa/redistrib/descarga.py:151`) |

---

## 1. Retirar cajas a 0 (versión 1.16.0)

### 1.1 Qué es una «caja a 0» y cómo sale la lista (en vivo)

Una caja a 0 es un KO_/TT_ que cumple todo esto:

- está activo y es de la compañía 8;
- su hueco está entre **L44 y L136**. El rango va en el parámetro `koroshi_contenedores.cajas_cero_lineales = 44-136`;
- no tiene ningún quant con cantidad ni con reserva;
- **no tiene ninguna línea de movimiento abierta** que salga de la caja o vaya a ella. Esta comprobación es nueva: así
  no se archiva una caja de una IN o una INT sin validar.

La lista se calcula con una consulta SQL de solo lectura cada vez que se abre. No se guarda en ninguna tabla.

Las cajas que no son «a 0» pero tampoco están bien van a una lista aparte, **«Revisar»**:

- las que tienen stock negativo;
- las que tienen reservas sin cantidad.

### 1.2 Lo que hace el operario en la PDA (cualquier operario)

Botón **«Retirar cajas a 0»**. Sale el resumen por lineal: huecos con cajas a 0, número de cajas, huecos que quedan
libres y cajas «con prendas» pendientes.

1. Lee el hueco. Salen las cajas a 0 y, aparte, las cajas con stock («no tocar»).
2. Lee cada caja a 0 que tiene delante. Si lee una con stock, pita en rojo y no pasa nada.
3. Tres botones:
   - «Retirar las vacías (N)»: hay que confirmar. Se archivan.
   - «No están (N)»: otra confirmación. Se archivan con la nota «no estaba en el hueco».
   - «Tiene prendas», en una caja leída: ver 1.4 c.
4. Si el hueco queda sin cajas, sale «✓ L67 P16 C2 queda libre» y se pasa al siguiente hueco.

### 1.3 Lo que pasa en Odoo

Es el mismo `/archivar` de ahora con tres cambios:

- la comprobación de líneas abiertas de 1.1;
- la tarjeta se valida con `pda.empleado_valido`;
- en el registro se apunta «vacía, ronda» o «no estaba en el hueco».

No hay ajuste de stock: la caja ya está a 0.

### 1.4 Casos especiales

**a) Reservas.** Las cajas de la ronda no tienen reservas. Las descuadradas van a «Revisar» (b).

**b) Stock negativo y reservas descuadradas: solo Isaac** (decisión de Isaac).

- **Quién puede:**
  - **con tarjeta:** Betty, José Luis e Isaac. Parámetro `koroshi_contenedores.tarjetas_revisar`, con los ids de
    empleado; lo pone IT al instalar;
  - **desde Odoo, sin la PDA:** los usuarios de Isaac y `almacen2`, con un grupo nuevo «KOROSHI Contenedores: revisar».
- **Qué ven:** en el resumen de «Retirar cajas a 0», un botón **«Revisar (26)»**, y solo ellos. Lista por lineal y
  hueco con cada caja, el artículo y las uds (en rojo, −2). Se va al hueco con la lista.
- **Qué hacen, caja a caja** (se abre su ficha de siempre):
  - **«Está vacía»**: «Poner a cero», que con negativo hace el ajuste +, y después «Archivar». Las dos cosas en un solo
    paso, con una confirmación.
  - **«Hay N prendas»**: «Cambiar» a las uds contadas (ajuste de la diferencia).
  - **«¿Dónde está?»**: la búsqueda de siempre, para encontrar la caja donde Odoo tiene ese stock de más.
- **Para los demás:** la caja de «Revisar» sale en gris en la ronda, «la revisa Isaac». Si alguien que no está en la
  lista abre la ficha, «Poner a cero» y «Cambiar» le dicen «Solo Betty, José Luis o Isaac».
- **Registro:** cada cosa queda en `koroshi.contenedor.movimiento`, con la nota «revisión de negativos».

**c) Caja a 0 con prendas (como la KO_090726_045): la resuelven José Luis, Betty, Jordi y Darwin** (decisión de Isaac).

- **En la ronda:** el operario que la encuentra pulsa «Tiene prendas». **No cambia el stock.** La caja se queda en el
  palé y pasa a la lista **«Cajas con prendas»**. Se apunta en el registro con la acción nueva `con_prendas` (tabla
  propia).
- **Quién la resuelve:** solo con la tarjeta de José Luis, Betty, Jordi o Darwin (parámetro
  `koroshi_contenedores.tarjetas_con_prendas`). Abren la lista en la PDA, van al hueco, leen la caja y leen sus
  prendas. Al «Guardar», Odoo mira cada artículo por este orden:
  1. Un faltante pendiente de ese artículo con vuelta a esta caja o a su hueco: **«Encontrado»** (de FALTANTE a la
     caja, sin ajuste).
  2. Un faltante pendiente de ese artículo en otro sitio: lo pregunta («¿es el de L70 P02?») y el operario elige entre
     «Sí, es ese» y «No».
  3. Si no hay ninguno: **ajuste +** contra pérdidas, como «Añadir prendas».
- **Después:** la caja sale de la lista. Ya tiene stock, así que no se retira.

**d) La etiqueta KO_ de la caja retirada.** Sí: es la etiqueta pegada en la caja de cartón. Al archivar el contenedor
en Odoo, esa etiqueta deja de valer: si alguien la lee (en Contenedores, Recepción o Lecturas), Odoo dice «no encuentro
el contenedor (o está archivado)». Si la caja vacía se vuelve a usar con la etiqueta vieja, ese error saldría más
adelante.

**Propuesta: al retirar la caja, arrancar o tachar la etiqueta KO_.** No cambia nada en Odoo: es una instrucción para el
operario, y la PDA se lo recuerda en el mensaje de «Retirada». → **Decisión 3 (pendiente).**

### 1.5 Datos (1.16.0)

- **Sin tablas nuevas.**
- **Acciones nuevas** en el campo `accion` de `koroshi.contenedor.movimiento` (tabla propia): `con_prendas`, y la nota
  de la revisión de negativos.
- **Parámetros:** `cajas_cero_lineales`, `tarjetas_revisar` y `tarjetas_con_prendas`.
- **Grupo nuevo:** «KOROSHI Contenedores: revisar», para los usuarios de Isaac y `almacen2`.

### 1.6 Riesgos

| Riesgo | Qué se hace |
|---|---|
| Archivar una caja de una IN o INT sin validar | Comprobación de líneas abiertas |
| Retirar una caja con stock al confundirse de etiqueta | Solo se archivan las leídas que están a 0 en Odoo |
| «No están» archiva cajas que estaban detrás | Otra confirmación, la nota y se puede desarchivar desde Odoo |
| Lentitud en lineales grandes | Medir la consulta antes de instalar |
| Instalar en horas de trabajo | Fuera de horas: un `-u` de contenedores arrastra el menú |

---

## 2. Reagrupar KO, con el cálculo en Odoo (versión 1.17.0)

### 2.1 Qué necesita Odoo para calcular el plan

El cálculo del programa (`redistribucion/programa/redistrib/compactar.py`) usa cinco datos. Así quedaría en Odoo:

| Dato | En el programa | En Odoo (propuesta) |
|---|---|---|
| Qué es zona 0 | Temporada I27 / V27 | `product.template.season_id`. Parámetro `koroshi_contenedores.temporadas_zona0 = I27,V27` |
| Litros por ud | MASTER v14 (Excel); si el modelo no está, la ficha o 2,5 L | **Tabla propia `koroshi.contenedor.litros`**: modelo, litros/ud, fuente y fecha. Se carga desde la oficina con «Importar MASTER» (lee la hoja «MASTER por modelo»). Si el modelo no está: `product.volume` × 1000 si lo tiene; si no, 2,5 L, y el paso sale marcado «sin dato» |
| ABC (líneas de salida de 28 días) | Copia SQLite | **Cron nocturno propio**, a las 02:00 hora local: líneas de OUT hechas en 28 días, por modelo-color, en la tabla propia `koroshi.contenedor.abc`. Lejos del cron 222 (03:30 UTC) y de las zonas (04:50) |
| Cajas, huecos y uds | Copia SQLite | **En vivo**: quants de las cajas de los lineales que se calculan |
| Capacidad de un hueco, caja, llenado | 770 L / 84 L / 90 % | Parámetros `litros_hueco` (770 hasta medirlo), `litros_caja` (84) y `llenado` (0,9) |

¿Por qué una tabla propia para los litros y no `product.volume`? Porque la ficha del artículo la usan otros (S4T, XPO
bultos). Una tabla propia no cambia nada fuera del módulo.

### 2.2 Cómo se calcula: por lineal, cuando se pide

- **Las reglas** pasan de `compactar.py` a `logica.py` del módulo, como funciones sin Odoo:
  - vaciar los huecos llenos a menos de la mitad;
  - no mezclar dos colores del mismo modelo;
  - el mismo modelo-color va junto;
  - lo de clase A va a C1–C2;
  - los restos de talla (≤ 2 uds o ≤ 5 % de la talla más fuerte) van al fondo;
  - nada pasa del 90 %;
  - primero lo que libera más huecos con menos cajas;
  - no se vacían los huecos con algo de Z.

  Las pruebas de `redistribucion/programa/pruebas/test_compactar.py` se copian a `tests/test_logica.py`. **Prueba de
  equivalencia:** el mismo ejemplo tiene que dar el mismo plan en el programa y en Odoo.
- **Cuándo se calcula:** el jefe o el operario pulsa **«Calcular L67»** en la PDA o en la oficina. Odoo lee en vivo:
  - el lineal y sus destinos posibles (L65 a L69);
  - el ABC y los litros guardados;

  y escribe los pasos en `koroshi.compactacion.paso`. Son unos 5 lineales cada vez: tendría que tardar pocos segundos
  (**medirlo**).
- **Por qué por lineal y no la nave entera:** el plan está al día en el momento de empezar, y no hay un cálculo de
  20.000 cajas en el servidor de la PDA. Lo que se pierde: el orden «por beneficio» es dentro del lineal, no de toda la
  nave. Para elegir qué lineal empezar, el resumen enseña cuántos huecos libera cada uno (calculado la noche anterior
  con el ABC; ver 2.5).
- **Dos lineales vecinos:** al calcular L68, los destinos que ya usan los pasos pendientes de L67 cuentan como
  ocupados. Así dos planes no llenan el mismo palé dos veces.
- **Recalcular:** «Calcular» otra vez sustituye los pasos pendientes de ese lineal. Los hechos se quedan.

### 2.3 Datos (1.17.0, todo en tablas propias)

- **`koroshi.contenedor.litros`**: modelo, litros/ud, fuente (MASTER o ficha) y fecha de carga.
- **`koroshi.contenedor.abc`**: modelo-color, líneas en 28 días, clase y fecha.
- **`koroshi.compactacion.paso`**:
  - lineal, orden y hueco de origen;
  - contenedor, destino y destino real;
  - modelo-color, uds, litros, clase y resto;
  - estado: pendiente, hecho, cambiado, saltado o no está;
  - motivo, operario, fecha y la línea del registro.
- **`koroshi.contenedor.movimiento`**: campo nuevo `paso_id`.
- **Cron nuevo** del ABC (02:00).

### 2.4 Mover, lo que lee el operario y el avance

(v3: esto vale para el paso «Mover KO». «Pasar prendas», de la KO mixta, está en el 2.6.)

Igual que en la v1, salvo que la lista sale de «Calcular» en lugar de importarse:

- **Mover:**
  - con `/mover` de siempre, que recibe `paso_id`;
  - se comprueba en vivo que la caja sigue en el origen y que no tiene prendas leídas sin validar;
  - si el operario la lleva a otro destino, se avisa cuando allí hay el mismo modelo en otro color. Con los litros ya en
    Odoo, también se avisa **si pasa del 90 %**.
- **El operario:** lee el lineal y vacía hueco de origen tras hueco de origen. Primero lee las cajas y después el hueco
  de destino. Tiene «No está», «No cabe» y «Saltar».
- **Antes:** si el lineal tiene cajas a 0, sale el aviso «retíralas primero», con un botón a la ronda de la 1.16.0.
- **Avance por lineal:**
  - en la PDA: pasos hechos / total, huecos libres / previstos y saltados;
  - en la oficina: lista y tabla dinámica de lineal × estado.

### 2.5 Riesgos

| Riesgo | Qué se hace |
|---|---|
| Dos copias de las reglas (programa y Odoo) | **Odoo pasa a ser el que manda.** El programa se queda para el mapa y para comparar, con la prueba de equivalencia |
| Litros del MASTER desactualizados en Odoo | La fecha de carga se ve en el resumen. «Importar MASTER» cada vez que haya MASTER nuevo |
| El cálculo tarda con la PDA esperando | Por lineal, solo cuando se pide. Medirlo; si pasa de ~5 s, se hace en la cola (`queue_job`) y la PDA espera el aviso |
| El cron del ABC carga el servidor | De noche, de solo lectura con `read_group`. Medirlo con una llamada a mano antes de activarlo |
| Mover mientras se prepara | Las cajas con prendas leídas no se mueven. Las reservadas sí: Lecturas recarga (R7) |
| La capacidad del hueco no está medida | Parámetro de 770 L. Se cambia sin versión en cuanto se mida (5) |

---

### 2.6 KO mixta y tallas por altura (decisión de Isaac del 26/11)

**El criterio, tal como lo pasa la sesión del mapa:**

- **KO mixta, en cada hueco:**
  - un SKU (modelo-color + talla) con stock en la zona 0 para **3 cajas o más** (uds ≥ 3 × uds por caja de 84 L,
    del MASTER) lleva **su propia KO**;
  - las tallas con menos stock de ese modelo-color van juntas en **una sola KO por modelo-color**.

  El corte de 3 va en un parámetro, `koroshi_contenedores.cajas_ko_propia = 3`.
- **Tallas por altura:**
  - **C1 (el suelo):** las tallas más pedidas (por sus líneas de 28 días) hasta la mitad de las unidades del
    modelo-color;
  - **C2:** el resto;
  - **C3:** los restos de talla (≤ 2 uds o ≤ 5 % de la talla más fuerte).
- **Datos de la copia del 23/11** (zona 0, desde L44):

  | | KO con stock |
  |---|---|
  | Hoy | 10.256 |
  | KO mixta | **6.381** |
  | Una por modelo-color | 4.620 |
  | Una por SKU | 6.764 |

  1.057 SKU llevan KO propia: son el 77 % de las uds y el 60 % de las líneas.

**Qué cambia respecto a la v2:** «Reagrupar KO» deja de ser solo mover cajas enteras. Hay **tres tipos de paso**:

| Paso | Qué es | En Odoo | ¿Existe ya? |
|---|---|---|---|
| **Mover KO** | Una KO entera a otro hueco o a otra altura (C1 → C2) | Cambia el `location_id` de la KO; prendas y reservas van con ella | **Sí** (`/mover`, probado) |
| **Pasar prendas** | Unas tallas de la KO A a la KO B (separar un SKU con KO propia, juntar tallas pequeñas en la mixta, subir los restos a C3) | Movimiento interno **hecho** de A a B, por artículo y uds (`stock.move`, de una ubicación interna a otra, sin albarán) | **No.** Es nuevo y es lo delicado (ver más abajo) |
| **Archivar KO vacía** | La KO que se queda sin nada después de pasar sus prendas | La ronda de la 1.16.0 | Sí (1.16.0) |

**Cómo sale el plan de un hueco** («Calcular L67», como en el 2.2, una función más en `logica.py` con pruebas
contra el programa):

1. Para cada modelo-color del hueco, qué SKU llevan KO propia (stock de la zona 0 ≥ 3 cajas) y qué tallas van a la
   mixta.
2. A qué altura va cada talla (C1, C2 o C3).
3. **KO de destino:**
   - **se reutiliza siempre que se pueda**: la KO que ya tiene más uds de ese SKU (KO propia) o de esas tallas (mixta)
     se queda con su etiqueta;
   - solo se crea una KO nueva cuando no hay ninguna que sirva.
4. **Pasos:** primero «Mover KO» (lo que ya está bien y solo cambia de altura), después «Pasar prendas» y al final
   «Archivar KO vacía».

**Lo que lee el operario en «Pasar prendas»:**

1. Lee la **KO de origen** y después la **KO de destino**. La PDA dice qué pasar: «Pasa la talla 36 y la 38 de
   KO_…_118 a KO_…_120».
2. Hay dos formas de hacerlo:
   - **«Pasar todo»**, si todo lo de la KO va a la misma: un toque y se confirman las uds que dice Odoo;
   - **leer cada prenda** (como en «Añadir prendas»: cada lectura es 1 ud, con «Cantidad» para poner N). Odoo solo
     acepta tallas que sean de ese paso.
3. **«Guardar»:** un movimiento interno por artículo, todo o nada, y su línea en el registro, con la acción nueva
   `pasar` y el paso.

**El punto delicado: las reservas.** Hoy, mover una KO entera no toca las reservas, porque viajan con la ubicación.
Pasar prendas de A a B sí las toca: si las uds de A están reservadas para una OUT, al moverlas la OUT pierde la reserva.
Hay dos opciones:

- **A (recomendada para empezar):** solo se pasa lo **libre**. Lo reservado se queda en A hasta que se prepare la OUT,
  y A sigue en el plan como «pendiente: N uds reservadas». Una pasada más tarde, o al día siguiente, acaba el paso. Es
  seguro: no toca ninguna OUT.
- **B:** pasar también lo reservado y **cambiar en el acto la reserva de la OUT de A a B** (la línea de la OUT pasa a
  coger en B). Es más rápido, pero toca las reservas de las OUT abiertas desde Contenedores. Si falla, la OUT se queda
  sin reserva o reservada donde no está, y eso para la PDA en el almacén. Haría falta probarlo a fondo y pasaría a
  ser la parte más arriesgada de la versión.

→ **Decisión 9 (v4).** Isaac pregunta por un caso concreto: la KO está vacía de verdad, pero Odoo dice que tiene una
prenda reservada. **Ya está resuelto desde la 1.11.0 y no cambia:**

1. Se abre la KO y se pulsa **«Poner a cero»**.
2. La línea reservada de la OUT pasa por Faltantes:
   - la OUT se reserva en el hueco más cercano que tenga stock libre o, si no hay ninguno, sale sin esa prenda;
   - la unidad va a FALTANTE y se cierra en el acto como «no encontrado», porque la caja está vacía y no tiene sentido
     volver a buscarla allí;
   - queda la nota en la OUT y la línea en el registro.
3. Después, **«Archivar»**.

Si hay prendas pero menos de las que dice Odoo, se usa **«Cambiar»**: solo la diferencia pasa a Faltantes. La única
excepción es una caja con stock negativo o con más reservado que cantidad: esa la revisan Isaac, Betty o José Luis
(1.16.0).

Para las KO que sí tienen las prendas reservadas, se sigue proponiendo la **opción A**: se pasa solo lo libre.

**Qué más cambia:**

- **Una KO puede ser varias cajas físicas.** Una KO propia de un SKU con stock para 5 cajas son 5 cajas con la misma
  etiqueta KO. Hay que decidir si la etiqueta va en cada caja (se imprimen N copias) o en el frente del palé.
  → **Decisión 10.** Además:
  - la ocupación del hueco se sigue contando por cajas físicas (84 L cada una), no por KO;
  - «Cambiar» la cantidad de una KO así es contar todas sus cajas.
- **Crear KO nuevas e imprimir su etiqueta** lo hace hoy `koroshi_ubicaciones` (la Zebra). Si la compactación tiene que
  crear KO, o lo hace llamando a ese módulo (cambio en dos módulos: hay que decirlo antes y hacerlo en dos sesiones,
  regla 6), o la PDA dice «Coge una etiqueta KO nueva de las impresas» y la lee. **Propuesta:** reutilizar siempre que
  se pueda y, para las pocas que falten, tirar de un taco de KO ya impresas. Así 1.17.0 no toca `koroshi_ubicaciones`.
- **Recepción:** `koroshi_recepcion` 1.8.0 (diseño v7, otra sesión) crea **una KO por caja**. Con la KO mixta, ¿la
  recepción sigue igual y la compactación agrupa después, o la recepción debe dejar ya la KO mixta? Es otro módulo y
  otra sesión. → **Decisión 11.**
- **Retirar cajas a 0 (1.16.0)** sirve igual. Una KO de varias cajas está a 0 cuando lo están todas. Después de «Pasar
  prendas», las KO vacías van a esa ronda.
- **Tamaño:** de 10.256 a 6.381 KO quiere decir unos **3.900 «Pasar prendas»**, más los «Mover KO» de las alturas.
  Esto ya no son las 2.524 cajas a mover de la v2: es bastante más trabajo de almacén. **Propuesta:** hacerlo por
  lineal y **empezar por los modelos-color de clase A**, que es donde se nota en la preparación.

**Datos nuevos (todo en tablas propias):**

- `koroshi.compactacion.paso` gana:
  - `tipo` (mover, pasar, archivar);
  - `ko_destino_id`, `producto_id`, `uds`, `uds_hechas`, `uds_reservadas_pendientes` y `altura`.
- Parámetro `cajas_ko_propia`.
- Acción nueva `pasar` en el registro.

**Nada en `stock.picking`, `stock.picking.type` ni `stock.move.line`** (regla 7). Con la opción B se escribiría la
ubicación de líneas de OUT que ya existen. No es un campo nuevo, pero es tocar reservas: por eso es una decisión aparte.

## 3. Decisiones

| # | Decisión | Estado |
|---|---|---|
| 1 | Stock negativo | **Decidido:** lo revisa Isaac. Con tarjeta, Betty, José Luis e Isaac; desde Odoo, Isaac y `almacen2` |
| 2 | Caja a 0 con prendas | **Decidido:** la marca cualquiera en la ronda; la resuelven José Luis, Betty, Jordi o Darwin |
| 3 | Etiqueta KO_ de la caja retirada | **Pendiente:** ¿arrancarla o tacharla? |
| 4 | Plan de compactación | **Decidido:** se calcula en Odoo, por lineal y cuando se pide |
| 5 | Orden | **Decidido:** primero la 1.16.0 (retirar cajas a 0), después la 1.17.0 (compactar) |
| 6 | Capacidad del hueco | **Pendiente:** medirla (5) |
| 7 | `almacen2` | **Por confirmar:** ¿es un usuario de Odoo (el de una PDA o un PC)? |
| 8 | Jordi y Darwin | **Por confirmar:** que tienen tarjeta de operario en Odoo |
| — | KO mixta y tallas por altura | **Decidido (Isaac, 26/11):** KO propia con 3 cajas o más; el resto, una KO por modelo-color; C1 / C2 / C3 por tallas (2.6) |
| 9 | Pasar prendas con reservas | **Propuesta A**, solo lo libre. Una KO vacía con algo reservado: «Poner a cero» (ya existe, 1.11.0) |
| 10 | Etiqueta de una KO de varias cajas | **Decidido:** una etiqueta en cada caja (N copias de la misma KO) |
| 11 | KO en la recepción | **Decidido:** la recepción sigue con una KO por caja; se reagrupa al compactar |
| 12 | Capacidad | **Decidido:** 8 cajas por ubicación (medio palé). Parámetro `cajas_hueco = 8`; el plan cuenta cajas, no litros. **Por confirmar:** ¿el tope es 7 cajas (90 %) u 8? |

## 4. Qué hay que probar

- **Sin Odoo (`logica.py`):**
  - qué es una caja a 0, las negativas y las reservas descuadradas;
  - el rango de lineales;
  - las listas de tarjetas;
  - las reglas de compactación con la prueba de equivalencia con el programa;
  - los destinos ya usados por otro lineal.
- **En el navegador, con cajas de prueba:**
  - una caja a 0 en una IN sin validar no se archiva;
  - «No están»;
  - «Tiene prendas» y su resolución, con faltante y sin él;
  - una tarjeta que no está en la lista no puede revisar ni resolver;
  - «Calcular» un lineal pequeño y comparar con el programa;
  - destino cambiado con otro color y por encima del 90 %;
  - (v3) «Pasar prendas» con una KO de prueba con tallas libres y reservadas: solo pasa lo libre (opción A) y la OUT
    sigue reservada en A;
  - (v3) plan de KO mixta de un hueco calculado en Odoo igual que `ko_mixta` y `tallas_por_altura` del programa
    (prueba de equivalencia).
- **Medir (solo lectura, con permiso):**
  - la consulta del resumen de cajas a 0;
  - el cron del ABC;
  - «Calcular» en un lineal grande.
- **En una PDA real:**
  - la ronda en L67 P16, el hueco de la foto;
  - la revisión de una caja negativa con la tarjeta de Isaac;
  - un lineal de compactación entero con preparación al lado.

## 5. Cómo medir la capacidad de un hueco

Hay dos formas. Con la primera basta; la segunda la confirma.

**A. Contando cajas (recomendado: es lo que importa).** Se eligen 3 o 4 huecos que estén **llenos de verdad** con cajas
de 84 L, mejor de formatos distintos (C1 y C2; 1-0-60, 1C40 y 2C40 si son distintos de tamaño). En cada uno:

1. Cuántas cajas hay de frente (a lo ancho).
2. Cuántas hay hacia el fondo.
3. Cuántas hay de alto, hasta donde se puede apilar sin tocar la viga de arriba y sacando bien la de arriba.
4. Capacidad = frente × fondo × alto cajas. Por ejemplo, 3 × 3 × 1 = 9 cajas = 756 L.

Apuntar el lineal y el hueco (p. ej. L67 P16 C1) y hacer una foto de frente. Si hay huecos de alturas distintas, uno de
cada.

**B. Con el metro (para comprobar).** En cada hueco, el espacio útil en cm:

- **ancho:** entre los dos montantes;
- **fondo:** del borde de la viga a la pared o al palé de detrás;
- **alto:** del palé a la viga de arriba, menos unos 10 cm para meter la mano.

Litros = ancho × fondo × alto ÷ 1000. Y la caja de 84 L por fuera: largo × ancho × alto. Con las dos medidas se calcula
cuántas caben y se compara con A.

Con el resultado se cambia el parámetro `koroshi_contenedores.litros_hueco`, sin sacar versión. Si C1 y C2 (o los
formatos) dan cosas distintas, habría un valor por formato. Eso sería otro cambio pequeño en el diseño.

## 6. Aparte

- `/mover` y `/limpiar` no usan `pda.empleado_valido`. Se arregla en la 1.16.0.
