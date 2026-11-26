# Compactación en Odoo: retirar cajas a 0 y juntar cajas (diseño v2, 26/11/2026)

**Estado: DISEÑO v2 para Isaac. No hay código, ni versión, ni nada instalado.** La v1 (el mismo nombre, sin `_v2`) se
conserva tal cual.

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

## 2. Juntar cajas, con el cálculo en Odoo (versión 1.17.0)

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
  - destino cambiado con otro color y por encima del 90 %.
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
