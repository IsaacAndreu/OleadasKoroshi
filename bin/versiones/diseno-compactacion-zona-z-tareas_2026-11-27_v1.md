# Diseño: compactación de la zona Z (outlet, L01–L43) con tareas de Odoo — v1 (27/11/2026)

Módulo: `koroshi_contenedores` (el mismo de «Retirar cajas a 0» 1.16 y «Compactar» 1.17). **Solo diseño: sin código
hasta el sí de Isaac.** Es aparte de la fase 1 de la zona 0 (palés L44–L136).

Lo que pide Isaac (27/11): «¿cómo lo plasmamos en el módulo de compactación para que la persona que se ocupe vaya
haciéndolo sola, sin tener que ir preguntando qué hacer en cada paso?». En el audio con Cruz (27/11) operaciones lo
contó así: Odoo dice «vas a empezar con este SKU, búscalo aquí, aquí y aquí; te las traes todas, lees las vacías, las
otras las unificas» y, al acabar, «ahora este otro artículo». Mínimos pasos y que sea el sistema quien diga qué hacer.

## 0. De dónde sale

- Cálculo del plan de la Z: `redistribucion/programa/redistrib/zona_z.py` (commits aeea683 y abcc279; README,
  apartado «Zona Z»). Solo lee la copia diaria de Odoo de las 19:00.
- Estanterías: `redistribucion/estanterias-zona-z_hojas-20261102_transcripcion-20261127.csv` (tipo por posición, 207
  dudas). Medidas de hueco: hoja «Medidas estanterias» de
  `bin/versiones/20261106_1630_MASTER-zonas-0-y-Z-layout-estanterias-cajas_v1.xlsx` (faltan F, G, B25 y E2).
- Mecanismos ya hechos y probados que se reutilizan: mover una KO = cambiar su `location_id` (las prendas y las
  reservas van con ella, Lecturas lo ve: «Mover» y la 1.17); marca «Tiene prendas» y su lista (1.16); lista
  «Revisar» y tarjetas de `tarjetas_revisar` (1.16); plano con metros de `koroshi_kpi` (`metros_ruta`).

Cifras de la copia del 26/11 (cálculo del programa, por KO entera):

| Paso | Qué | KO |
|---|---|---|
| 1 | Huecos libres hoy (KO a 0 en estanterías Z) | 7.018 libres |
| 2 | Hacer sitio en L01–L15: sacar lo lento y lo muerto | 8.347 |
| 3 | Traer lo vivo (V25, I26, V24, I25, V26, V23, V22, I24: 80 % de las líneas, 41 % del stock) | 11.671 |
| 4 | El resto (lento/muerto entre sí; puede esperar) | 8.919 |
| 5 | Liberar sitios de palé (dos caras de una posición, espalda con espalda) | 183 sitios, 4.253 huecos |

## 1. Lo que cambia respecto a la zona 0

En la zona 0 una KO es una caja dentro de una columna y lo que se hace es vaciar columnas. **En la Z cada KO es un
hueco de la estantería**: A36 tiene 36 KO por posición, D10 20, C 16 y F 24. Una KO a 0 es un **hueco libre** (no se
retira) y lo que se mueve es el contenido de un hueco a otro.

Hay dos maneras de mover el contenido de un hueco, y el diseño usa las dos:

| | **Cambio de hueco** (recomendada) | **Pasar prendas** |
|---|---|---|
| Qué hace Odoo | La KO con prendas pasa a la posición de destino y la KO a 0 de destino pasa a la posición de origen: dos cambios de `location_id`, como «Mover» | Movimiento de stock interno de prenda a prenda de la KO de origen a la de destino |
| Reservas de OUT | Van con la KO: no se tocan | Solo se puede pasar lo **libre**; lo reservado se queda (o hay que esperar a que salga) |
| Lecturas / preparación | Ve la KO en su sitio nuevo al momento | Ve las prendas en la KO nueva |
| En el almacén | Se lleva el contenido entero (o la caja/bandeja si sale de la estantería) **y la etiqueta KO viaja con él** | Se leen las prendas una a una (o «todo el hueco» si no hay reservas) |
| Cuándo | Siempre que el hueco entero va al mismo sitio (el caso normal: un hueco = un modelo-color, talla) | Juntar dos huecos medio vacíos del mismo modelo-color-talla en uno |

**Pregunta clave (P1):** ¿la etiqueta KO está en la caja/bandeja (viaja con el contenido) o pegada a la estantería?
Si está en la caja, el cambio de hueco es trivial. Si está pegada a la estantería, el cambio de hueco obliga a
despegar y volver a pegar dos etiquetas (o a imprimir dos), y entonces conviene «pasar prendas».

## 2. La tarea que da Odoo (una cada vez)

**Unidad de trabajo = un modelo-color** (con su talla completa), dentro de un paso y un lineal de destino. Es lo
que contó Cruz: «empieza con este artículo, está aquí, aquí y aquí».

Pantalla de la PDA, botón nuevo **«Zona Z»** (al lado de «Compactar»):

1. **Pasar tarjeta** (como siempre). Odoo da **la siguiente tarea** (o el operario lee un lineal, «L83», y Odoo le da
   la siguiente tarea de ese lineal). La tarea queda **cogida** a su nombre (30 min sin actividad: se suelta), para
   que dos operarios no hagan la misma.
2. Odoo enseña:
   - **Qué:** `2621JA00-000003` (familia, temporada, «vivo»), N huecos, uds.
   - **Dónde está hoy:** la lista de huecos de origen, ordenada por recorrido (metros de `koroshi_kpi`), con la talla
     y las uds de cada uno: `L14 P07 C2 · KO_150926_934 · 3XL · 12 uds`…
   - **Adónde va:** el lineal de destino y **los huecos libres concretos** que Odoo le reserva, uno al lado del otro
     (misma posición y, si no caben, la siguiente), para que la talla completa quede junta:
     `L03 P12: KO_…_101, KO_…_102, KO_…_103`.
3. El operario va al primer origen y **lee la KO de origen** (☑ como en la 1.17). Puede coger varias.
4. Va al destino y **lee la KO libre de destino** (o la posición: Odoo coge la primera libre de las reservadas).
   Odoo comprueba:
   - que el destino es uno de los reservados para la tarea → hecho;
   - que es otro hueco libre **del mismo lineal de destino** → avisa y pide «Sí, aquí» (como la 1.17);
   - que es de otro lineal o que tiene prendas → no, y dice por qué.
5. Al acabar todos los orígenes: «✓ 2621JA00-000003 hecho (5 huecos, 3 libres en L14)» y **la siguiente tarea**,
   sin pulsar nada más.
6. Botones por hueco de origen: **«No está»**, **«Hay menos/más»** (pasa a prendas) y **«Saltar»**. En el destino:
   **«Lleno»**. Ver §5.

**Juntar huecos** (pasar prendas): si al final de la tarea quedan dos huecos del mismo modelo-color-talla medio
vacíos que caben en uno, Odoo lo propone como último paso de la tarea: «Junta L03 P12 C1 (4 uds) en L03 P12 C2
(6 uds)» → se leen las prendas (solo las libres) y la KO que queda a 0 es un hueco libre más. Es opcional en la
primera versión (ver P4).

## 3. El orden de las tareas

Odoo elige la siguiente tarea así (de mayor a menor prioridad):

1. **Paso**: 2 → 3 → 4 → 5. El paso 3 en un lineal solo se da cuando ese lineal tiene sitio: Odoo cuenta los huecos
   libres del lineal (en vivo) y, si no llegan para la tarea, da antes las tareas del paso 2 que lo vacían.
2. **Lineal de destino**: del más cercano al muelle al más lejano (L01 → L15 para lo vivo).
3. **Bloque**: temporada (en el orden V25, I26, V24…) → familia que más vende.
4. **Modelo-color** que más vende dentro del bloque.
5. **Si el operario eligió lineal** («compactaciones del 83»), solo las tareas con origen o destino en ese lineal,
   en el mismo orden.

**Sitios de palé (paso 5).** El plan trae la lista de las 183 posiciones (las dos caras, L01+L02, L03+L04…) que se
desmontan, agrupadas en bloques al fondo. **Desde el primer día ninguna tarea pone nada en ellas** (no son destino),
aunque se vacíen al final. Cuando las dos caras de una posición quedan sin stock y sin movimientos abiertos, Odoo:

- la pone en la lista «Posiciones para desmontar» de la pantalla del responsable, con fecha;
- avisa al responsable (aviso en la pantalla del responsable y, si se quiere, actividad de Odoo a su usuario; ver
  P6);
- el responsable pulsa «Desmontada» cuando el equipo la quita. Las KO a 0 de esas posiciones se archivan entonces
  (con la comprobación de archivar de la 1.16: sin movimientos abiertos).

## 4. De dónde saca Odoo el plan (A, B o mixto)

| | A) Lo calcula Odoo | B) Importar el fichero del programa | **C) Mixto (recomendado)** |
|---|---|---|---|
| Qué hace Odoo | Todo: ventas de un año, rotación, grupos, bloques, capacidad por tipo, lineales | Lee la lista de movimientos del programa | Importa **la estrategia** (qué bloque va a qué lineales, grupo de cada temporada, posiciones de palé, tipos de estantería). **Las tareas las calcula en vivo** |
| Datos de hoy | Sí | No: copia de las 19:00 del día anterior | Sí, en lo que cambia cada minuto (stock, huecos libres, reservas) |
| Riesgo de que Odoo y el programa digan cosas distintas | Alto: `zona_z.py` son 374 líneas que aún cambian (decisiones del 27/11), con geometría y percentiles | Ninguno | Bajo: la parte difícil la hace un solo código (el programa) |
| Trabajo | Mucho | Poco, pero la PDA manda a huecos que ya no están como en la copia | Medio |

**Recomiendo C**, por esto:

- La estrategia (qué temporada es viva, qué lineales le tocan a cada bloque, qué posiciones se desmontan) cambia
  poco: se rehace cuando Isaac lo decide (una vez a la semana o al entrar una temporada). La calcula el programa,
  que ya está hecho y comprobado, y se sube a Odoo como un fichero (botón «Importar plan Z» en el escritorio, solo
  para el grupo «Contenedores: revisar»).
- Lo que cambia cada minuto (dónde está cada prenda, qué huecos están libres, qué está reservado, qué ha hecho ya
  otro operario) lo mira Odoo en vivo al dar cada tarea. Así la PDA nunca manda a un hueco que ya se ha vaciado o
  llenado desde la copia de las 19:00.
- Si un día la estrategia se quiere calcular en Odoo (A), se cambia solo la importación: las tablas y la PDA son las
  mismas.

**Qué se importa** (tablas propias de `koroshi_contenedores`; nada en `stock.location` ni en tablas compartidas):

| Tabla | Qué guarda |
|---|---|
| `koroshi.z.plan` | Un plan importado: fecha, copia de la que sale, quién, activo (solo uno activo) |
| `koroshi.z.estanteria` | Lineal, posición, lado, tipo (A36, D10…), capacidad usada, duda de la hoja |
| `koroshi.z.bloque` | Temporada (+ familia en lo vivo), grupo (vivo/lento/muerto), orden y lineales que le tocan |
| `koroshi.z.palet` | Posición de palé (las dos caras): orden, estado (por vaciar / vacía / desmontada), fechas |

**Qué calcula Odoo en vivo** (tablas propias):

| Tabla | Qué guarda |
|---|---|
| `koroshi.z.tarea` | Paso, modelo-color, bloque, lineal de destino, estado (pendiente / cogida / hecha / incidencia / saltada), operario, cogida a las, hecha a las |
| `koroshi.z.tarea.linea` | Hueco (KO) de origen, KO de destino reservada y real, uds, modo (cambio de hueco / prendas), estado, motivo |

Las tareas se generan por lineal cuando hace falta (al pedir la siguiente), no todas de golpe: con ~29.000
movimientos, generarlas todas el primer día dejaría la mayoría viejas antes de hacerlas.

**Prueba de equivalencia:** con un ejemplo pequeño de la Z sacado del programa (un lineal, sus huecos, su bloque y
los huecos libres), las tareas que da Odoo deben mover lo mismo que el programa. Se pide a la sesión del mapa cuando
se programe.

## 5. Qué hace la PDA si algo no cuadra

| Caso | Qué hace |
|---|---|
| El hueco de origen no tiene nada | «No está» → la línea queda «incidencia» y la KO pasa a la lista «Revisar» de la 1.16 (Isaac, Betty, José Luis). No se toca el stock. La tarea sigue con los demás huecos |
| Tiene menos o más de lo que dice Odoo | «Hay menos/más» → se mueve igual con cambio de hueco (el registro va con la KO) y se apunta la diferencia para «Revisar». Odoo no ajusta solo |
| Tiene otro artículo | Igual que «No está», con motivo «otro artículo» |
| La KO de origen tiene prendas leídas para una OUT sin validar | Odoo no la da en la tarea (como la 1.17) y la deja para después |
| El destino reservado está lleno de verdad (Odoo dice 0) | «Lleno» → la KO se marca «Tiene prendas» (acción de la 1.16; la resuelven José Luis, Betty, Jordi y Darwin) y Odoo da el siguiente hueco libre de la tarea |
| No quedan huecos libres en el lineal de destino | Odoo no da la tarea; da antes las del paso 2 de ese lineal. Si tampoco hay, la tarea va al siguiente lineal del bloque (como el programa) |
| El operario deja el contenido en otro hueco libre del mismo lineal | Aviso y «Sí, aquí» |
| En otro lineal o en un hueco con prendas | No se deja |
| El operario se va sin acabar | A los 30 min la tarea se suelta; lo hecho se queda hecho |

## 6. Pantalla del responsable

En el escritorio (Inventario > KOROSHI Operarios > Contenedores > «Zona Z») y en la PDA (resumen):

- **Avance por paso**: tareas y huecos hechos / total del paso 2, 3, 4 y 5.
- **Avance por lineal**: huecos libres hoy, lo que falta por salir, lo que falta por entrar, % hecho.
- **Quién hace qué**: tareas cogidas ahora, por operario.
- **Incidencias**: lista de «No está», «Lleno», diferencias, con botón para abrir la KO.
- **Posiciones para desmontar**: las de palé que ya están vacías, desde cuándo, y «Desmontada».
- **Importar plan Z** (solo el grupo «Contenedores: revisar»).

## 7. Lo que no entra en la primera versión

- Imprimir etiquetas KO desde la PDA (hay ~3 impresoras en los pasillos y quizá 15 más por revisar): aplazado como
  en «Imprimir desde la PDA». Con 7.018 huecos libres que ya tienen KO no hace falta etiqueta nueva.
- La nave 1: primero la nave 2.
- Ordenar lo lento y lo muerto por familia (solo se separan).

## 8. Preguntas para Isaac (con la opción recomendada)

| | Pregunta | Recomendado |
|---|---|---|
| **P1** | ¿La etiqueta KO está en la caja/bandeja o pegada a la estantería? | Si va en la caja: **cambio de hueco** (sin tocar reservas). Si está pegada: pasar prendas, solo lo libre |
| **P2** | ¿De dónde saca Odoo el plan? | **C) mixto**: la estrategia del programa (botón «Importar plan Z»), las tareas en vivo en Odoo |
| **P3** | ¿La tarea la elige Odoo o el operario elige el lineal? | **Las dos**: «Siguiente tarea» por defecto y, si lee un lineal, solo las de ese lineal |
| **P4** | ¿Juntar dos huecos medio vacíos del mismo artículo-talla, ya en la primera versión? | **No**: primero el cambio de hueco. Juntar huecos, en la siguiente versión |
| **P5** | ¿Quién es el responsable que ve el avance y recibe el aviso de posición para desmontar? | Isaac y almacen2 (el grupo «Contenedores: revisar») |
| **P6** | ¿El aviso de «posición vacía para desmontar» va solo a la pantalla o también como actividad de Odoo? | **Solo pantalla** (lista con fecha). Nada de correos |
| **P7** | ¿Se empieza por un lineal de prueba? | **Sí: un lineal cercano (L03)**, con 1 operario, antes de abrirlo a todos |
| **P8** | ¿Versión? | Va después de la 1.17 (zona 0). Si se hace a la vez que la fase 2 de la zona 0, decir cuál va antes: es el mismo módulo |

## 9. Siguientes pasos

1. Isaac contesta P1–P8.
2. La sesión del mapa saca del programa el fichero del plan (estrategia) con el formato de §4 y un ejemplo pequeño de
   la Z para la prueba de equivalencia.
3. Diseño v2 con las respuestas. Después, el código (en una sesión, módulo `koroshi_contenedores`).
