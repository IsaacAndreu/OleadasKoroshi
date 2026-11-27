# Revisión crítica: compactación, zonas y faltantes (27/11/2026, v1)

Revisor: Fable 5.2, sesión de solo lectura. No se ha tocado código, git, Odoo ni el servidor. No se ha consultado
Odoo: las cifras nuevas salen de la copia `redistribucion/programa/copias/20261126_1454_odoo.sqlite` (26/11 14:54),
abierta en solo lectura.

Cómo leer las pruebas:

- **[copia 26/11]**: cifra calculada por mí sobre esa copia.
- **[código]**: leído por mí en el fichero y línea que se cita.
- **[subagente]**: lo leyó un subagente de esta sesión (mismo modelo) con `archivo:línea`; lo marcado además con
  «comprobado» lo he vuelto a leer yo.
- **HIPÓTESIS**: no comprobado; se dice qué dato lo confirmaría.
- **Estimación mía**: aritmética sobre un supuesto que se indica; no es una medida.

---

## Resumen: lo 10 más importante

1. **El escenario «traer la zona 0 a L01–L24» pone palés donde hay estanterías.** `escenario.py` trata los 136
   lineales como huecos de palé de 770 L; las hojas del 02/11 dicen que L01–L43 son estanterías (A36, D10, B24…: ni
   una posición de palé). Además trató C1–C2 como alturas, y son columnas. Los 25,1 m por pick y la decisión 3.2
   («la 0 en C1–C2») no valen tal como están. → §1.1
2. **El plan de la zona Z (27/11) contradice la decisión del 24/11.** Lleva el outlet vivo a L01–L15, justo donde
   el 24/11 se decidió traer la zona 0. Son 28.937 movimientos de KO para un outlet que vendió 59.376 uds en un
   año y hace el 7 % de las líneas. → §1.2
3. **La temporada que viene (V27) sale clasificada como «sin salidas» y va al fondo.** 45 de sus 47 modelos-color
   no tienen líneas en 28 días porque aún no se venden. Hay 39.890 uds de V27 y 27.888 están en contenedores sin
   hueco. Mientras, I27 sale a 20.000–26.000 uds por semana: la zona 0 se vacía sola. Lo que decide cómo queda la
   nave en junio es **dónde se ubica V27**, no mover I27. → §1.3
4. **Más de la mitad de las cajas de L44+ están a 0 en Odoo (19.863 de 38.278) y la 1.17 no las cuenta.** De las
   2.080 columnas candidatas a vaciar, 1.129 tienen 4 o más cajas físicas si las de a 0 siguen allí; 870 columnas
   de destino estarían ya llenas. La fase 0 tiene que ir antes y bloquear, no avisar. → §1.4
5. **Lecturas no se entera cuando se mueve una KO.** El refresco (R7) compara el id de la ubicación de la línea, que
   es la KO, y ese id no cambia al moverla de hueco. Todos los diseños dan por hecho que «Lecturas lo ve». → §3.1
6. **La zona de cada línea se fija a las 04:50 y nadie la vuelve a mirar.** Mover una KO reservada a otro lineal
   deja la OUT con una línea fuera de su zona. Además, los crons de `koroshi_zonas` no llevan `noupdate`: una
   actualización de madrugada puede saltarse el reparto. → §2.1 y §2.2
7. **No está claro qué es físicamente una posición.** La v6 dice 8 cajas por columna y 16 por palé; la memoria,
   «8 cajas por palé». Y 2.066 de 2.445 posiciones de L44+ solo usan 1 o 2 de sus 4 columnas: o la mitad de los
   sitios de palé ya está libre, o C3–C4 no existen. Liberar columnas no es liberar suelo. → §1.5
8. **La alarma del % de faltante es ruido en un 86 %.** No tiene mínimo de unidades recibidas (132 SKU en alarma;
   19 con 50 o más recibidas), cuenta el pack de calcetines que a KOROSHI se le excluyó y cuenta como faltante lo
   que está en FALTANTE sin revisar. Dentro se dice 0,035 % y a KOROSHI 0,28 %. → §4.1 y §4.2
9. **La ronda INT/67387 abierta bloquea otras vías y nada impide que S4T pida cada día lo que no hay.** Las
   regularizaciones a S4T están propuestas, sin fila en el tablero y sin código. → §4.3 y §4.4
10. **Los documentos van por detrás de la realidad.** La v6 dice «no hay código de la 1.17.0» y el árbol de
    trabajo ya la tiene sin commitear; el tablero cita la v4; las cifras de la fase 1 (1.711 columnas, 2.779 KO,
    6.167 KO) no están en ningún documento del repo; I27 y V27 están escritas a mano en tres sitios. → §5

---

## 1. Redistribución y compactación

### 1.1 El escenario de la fase 2 no cuadra con la nave (error)

- **Qué:** `escenario.py` coloca la zona 0 en L01–L24 «niveles 1–2», con 770 L por hueco en toda la nave.
- **Prueba:**
  - `redistribucion/programa/redistrib/escenario.py:27-29` (`niveles_0 = (1, 2)`, `litros_hueco = 770.0`) y `:36`
    (`lineales = (1, 136)`): la misma capacidad para todos los lineales.
  - `redistribucion/estanterias-zona-z_hojas-20261102_transcripcion-20261127.csv`: 1.612 filas de L01–L43; tipos
    A36 432, D10 420, B24 165, C 143, B25 124, X 118, E 96, F 52, E2 38, G 18. **Ninguna «PAL».**
  - `memory/nau2-c1-c4-son-columnas.md`: C1–C4 son columnas, no alturas (Isaac, 26/11). La regla se quitó de
    `compactar.py:351`, pero no de `escenario.py` ni de `fase2_reglas-a-decidir_2026-11-24.md` §3.2 y §6.
  - `TABLERO.md:60` sigue diciendo «Isaac decidió el 24/11: … 0 en C1–C2».
- **Impacto:** los escenarios A–E (25,1 m por pick, L01–L24, 101 lineales libres, tandas de 54.000 / 115.000 /
  195.000 uds) describen una nave que no existe. Las chaquetas («A grande», 73 % del volumen de la 0 según
  `fase2b` línea 31) no caben en una librería A36. La «fase 3» del diseño v6 se apoya en esto.
- **Propuesta:** rehacer el escenario con dos tipos de sitio (estantería por tipo, palé por columnas de 8 cajas) y
  sin alturas. Mientras, no usar los 25,1 m ni las tandas. La pregunta real es otra: ¿se desmontan estanterías
  cerca del muelle para poner palés de la 0, o la 0 se acerca dentro de L44+ (lo más pedido en L44–L60)?

### 1.2 El plan de la zona Z va contra la decisión del 24/11 (contradicción)

- **Qué:** `zona_z.py` trae el outlet «vivo» a los lineales más cercanos al muelle.
- **Prueba:**
  - Ejecutado sobre la copia del 26/11: `lineales_vivo` = L01–L13 y L15; pasos 2 / 3 / 4 = 8.347 / 11.671 / 8.919
    KO (28.937 movimientos). Coincide con `diseno-compactacion-zona-z-tareas_2026-11-27_v1.md` §0.
  - `fase2_reglas…` §6: «Traer la zona 0 junto al muelle por tandas de lineales, empezando por L01».
  - Venta del outlet en un año: 59.376 uds en 11.776 pedidos. **[copia 26/11]** Líneas de 28 días: I27 92,8 %,
    todo lo demás 7 %.
  - 32.618 de esas 59.376 uds (55 %) salieron en 299 pedidos de más de 50 uds: ventas por lotes, que no se
    preparan prenda a prenda.
  - 6.519 de 10.627 modelos-color del outlet no han vendido nada en un año (40.971 uds).
- **Impacto:** casi 29.000 movimientos (un movimiento por cada 2 prendas que el outlet vende al año) que se
  tendrían que deshacer si después se trae la 0 delante. Es el mayor trabajo de nave de todo lo planeado y el de
  menos retorno en recorrido.
- **Propuesta:** no programar las tareas de la Z hasta decidir qué va junto al muelle (decisión D1). Si el motivo
  de la Z es liberar suelo (paso 5: 183 sitios de palé), hacer solo eso: vaciar esas posiciones, sin reordenar por
  temporada y familia.

### 1.3 El ABC por líneas de 28 días castiga a la temporada que entra (error de supuesto)

- **Qué:** lo que no tiene líneas en 28 días es «sin salidas» y va «al destino más lejano».
- **Prueba:**
  - `compactar.py:211-212` (`abc = 'sin salidas'`) y `:342` (`al_fondo = resto or clase in ('C', 'sin salidas')`).
    La 1.17 lo copia: `diseno…_v6.md` §2.2 («los de poca salida… al más lejano») y `main.py:1355-1364`.
  - **[copia 26/11]** V27: 47 modelos-color con stock, 39.890 uds; 45 sin ninguna línea en 28 días (38.818 uds).
    I27: 552 modelos-color, 144.933 uds; 3 sin líneas (9 uds).
  - En `fase2b` el grupo «Sin salidas, mediano: 10 modelos-color, 8.814 uds» son los V27 del 23/11.
  - **[copia 26/11]** V27 por dónde está: 12.002 uds en huecos de L44+ y **27.888 en contenedores sin hueco**
    (colgados de NAVE2). En tres días V27 subió de 29.544 a 39.891 uds e I27 bajó de 156.263 a 145.527 (resúmenes
    de las copias del 23/11 y del 26/11).
  - **[copia 26/11]** Salidas de I27 por semana, últimas ocho: 12.753, 17.426, 19.257, 13.636, 17.627, 25.837,
    20.298, 22.023 uds.
- **Impacto:**
  - El plan aleja del muelle justo lo que se va a vender en primavera.
  - Con 145.000 uds de I27 y 20.000–26.000 de salida semanal, buena parte de las columnas de I27 se vaciará sola
    en semanas (aritmética simple; el ritmo no será constante). Mover hoy cajas de I27 gana poco tiempo.
  - Las 27.888 uds de V27 sin hueco no entran en ningún cálculo de compactación ni de metros, y son las que hay
    que ubicar bien. La meta escrita es «verano ubicado por modelo-color antes de junio de 2027».
- **Propuesta:**
  1. Regla nueva: la temporada más nueva con stock no es nunca «sin salidas»; se trata como A.
  2. Orden del trabajo: retirar cajas a 0 → decidir en qué lineales entra V27 → compactar **solo esos lineales**
     → ubicar V27 por modelo-color a la primera. La fase 3 de recepción («ordenar», pendiente en `TABLERO.md:45`)
     es donde se decide.

### 1.4 Las cajas a 0 ocupan sitio y el plan no las cuenta (error)

- **Qué:** el plan de la 1.17 y el del programa solo cuentan cajas con stock.
- **Prueba:**
  - `koroshi_contenedores/controllers/main.py:1416` (`WHERE q.quantity > 0`) y `logica.py:240` (ocupación =
    cajas con stock + pendientes de llegar). **[código]**
  - `compactar.py:144-145`: «La compactación no las cuenta, así que supone que ya se han retirado».
  - v6 §2: antes de calcular, «Avisa, no bloquea».
  - **[copia 26/11]** Contenedores activos en huecos de L44+: 38.278; a 0 o menos: 19.863 (24 negativos).
  - **[copia 26/11]** Columnas solo de zona 0 en L44+: 3.184. Con menos de 4 cajas con stock: 2.080 (3.642 KO).
    De esas, **1.129 llegan a 4 o más contando las de a 0**. Columnas con 8 o más cajas en total: 870.
- **Impacto:** si las cajas a 0 siguen físicamente en el palé, el operario llega a un destino «con sitio» que
  está lleno («No cabe» una y otra vez), o deja «LIBRE» una columna que aún tiene cajas vacías.
- **Propuesta:** no calcular un lineal mientras él o sus vecinos (±2) tengan cajas a 0 sin retirar; o contar todas
  las KO activas como ocupación. Es un cambio de dos líneas de criterio, antes de instalar la 1.17.

### 1.5 Columna, palé y posición: tres definiciones (contradicción y dato que falta)

- **Qué:** no hay una definición única de cuántas cajas lleva un palé ni de cuántos palés tiene una posición.
- **Prueba:**
  - v6 §1: «Una columna es medio palé: **8 cajas, 4 de alto × 2 de fondo**. Un palé son 2 columnas» (16 por palé).
  - `memory/nau2-orientacion-palet-pendiente.md`: «8 cajas por palé (Isaac, 26/11)».
  - Capacidad en tres versiones: «cuadra con 10 cajas de 84 L» (`fase2_reglas…` §1 y `escenario.py:7`), «9 cajas
    de 84 L son 756 L» (`compactar.py:558`) y 8 cajas (v6). El programa sigue con 770 L (`compactar.py:50`).
  - **[copia 26/11]** Cajas con stock por columna (solo zona 0): 1 → 1.028; 2 → 542; 3 → 510; 4 → 484; 5 → 145;
    6 → 186; 7 → 116; 8 → 155; 9 → 12; 10 → 6. Solo 18 columnas pasan de 8: **el tope de 8 cuadra con los datos**;
    el de 10 no.
  - **[copia 26/11]** Posiciones de L44+ según cuántas columnas tienen stock: 1 → 798; 2 → 1.268; 3 → 38; 4 → 341.
    Huecos con stock por columna: C1 2.144, C2 1.913, C3 379, C4 376.
  - `compactar.py:511-512`: «C3–C4 casi no se usan y no sé si existen físicamente».
- **Impacto:**
  - Si una posición son dos palés (C1–C2 y C3–C4), en 2.066 de 2.445 posiciones el segundo sitio ya está vacío
    según Odoo: habría suelo libre sin mover nada. Si C3–C4 no existen, los «huecos de Odoo» sobran.
  - El plan de la 1.17 mide «columnas libres» (v6 §3). Isaac pide suelo (30–40 %). En `fase2b` ya se veía la
    diferencia: 36,5 % de huecos, pero 25 % de posiciones enteras. El orden «primero la columna que se vacía
    moviendo menos cajas» no busca vaciar el palé entero.
- **Propuesta:** aclararlo con una visita de diez minutos (D2). Después, cambiar el objetivo del plan a «palés
  enteros vacíos»: preferir como origen la columna cuya pareja ya está vacía o también se vacía.

### 1.6 Capacidad de las estanterías de la Z: se usa la cifra optimista (error de supuesto)

- **Qué:** la capacidad por tipo es la mayor entre la nominal y el percentil 90 de lo que hay hoy.
- **Prueba:** `zona_z.py:216` (`max(real or 0, nom or 0)`). Resultado sobre la copia del 26/11:

  | Tipo | Nominal | P90 hoy | Se usa | Media real de KO por posición |
  |---|---|---|---|---|
  | D10 | 10 | 20 | 20 | 17,1 (6.687 KO en 391 posiciones) |
  | C | 8 | 16 | 16 | 12,4 (1.553 en 125) |
  | E | 8 | 18 | 18 | 6,6 (508 en 77) |

  Capacidad total 33.028 KO para 36.569 KO: ya no caben 3.541.
- **Impacto:** el tipo E se cuenta a 18 cuando hoy tiene 6,6 de media. Con la nominal en C, D10 y E la capacidad
  baja unas 5.600 KO y no cabrían unas 9.000 (cálculo mío aproximado, no ejecutado en el programa).
- **Contradicción añadida:** el diseño de la Z dice «cada KO es un hueco de la estantería» y «KO a 0 = hueco
  libre» (7.018). El README del programa dice que D10, C y E tienen «~2 KO por hueco». En esos tres tipos (655
  de 1.606 posiciones) una KO a 0 no es un hueco libre.
- **Otros datos de las hojas:** 207 dudas en 1.606 posiciones; 12 posiciones marcadas «X» (sin estantería) tienen
  170 KO en Odoo; los pares de lineales (L01/L02, L03/L04…) salen casi siempre idénticos. **HIPÓTESIS:** la hoja
  dibuja el par y se ha copiado a las dos caras; lo confirma mirar una hoja.
- **Propuesta:** capacidad = nominal salvo donde se confirme en la nave; contar huecos libres por celda, no por KO.

### 1.7 Otras diferencias entre el programa, la v6 y los criterios de Isaac

| Qué | Prueba | Propuesta |
|---|---|---|
| El programa vacía huecos por litros (< 385 L, hasta 4 cajas); la v6, «menos de 4 cajas» | `compactar.py:327`, v6 §2.1 | Rehacer los números con la regla de la v6 y guardarlos en un documento |
| Las cifras de la fase 1 (1.711 columnas y 2.779 KO con tope 8; 1.650 y 2.631 con tope 7; 6.167 KO «opción A») no están en ningún fichero del repo | `grep` en todo el repo: solo salen en el prompt de esta revisión | Escribirlas con su copia y sus reglas. No he podido comprobarlas |
| KO con dos modelos-color: la v6 dice «unas 40»; en la copia del 26/11 hay 6 de 9.662 | **[copia 26/11]** | Corregir la cifra; el caso es marginal |
| «19.190 de 39.246 contenedores de L44+ a 0»: con la copia del 26/11 salen 19.863 de 38.278 | **[copia 26/11]** | Citar siempre la copia y el criterio |
| Criterio de Isaac «talla completa para el multimarca»: no hay ninguna regla que lo aplique en la zona 0 | `compactar.py`, `logica.py` | Decidir si es de la fase 2 o se cae |
| «Abajo / arriba» es por caja, sin límite: una columna puede recibir 8 «ABAJO» cuando abajo caben 4 | `main.py:1507` **[subagente]** | Limitar a 4 por columna o quitar la banda de la fase 1 |
| Decisión 13: en la v5 la opción A era otra cosa (una KO por modelo-color y banda) que en la v6 (banda por caja). El «de acuerdo, procede» era a las fases | v5 y v6 §6 **[subagente]** | Volver a preguntarla con el texto de la v6 |
| Decisión 4 («el plan se calcula en Odoo, no se importa») frente a la Z, que recomienda importar | v2 y diseño Z §4 **[subagente]** | Decidir una sola vez para las dos zonas |
| El README del mapa v4 es el texto del v3 (título y carpeta del v3) | `prototipo-mapa_2026-11-26_v4/README.md:1` | Menor; el v4 está parado |

### 1.8 Quién lo hace y cuánto tarda (nadie lo ha calculado)

Ningún documento da horas. **Estimación mía**, con un supuesto sin medir de 1 a 2 minutos por caja (ir, leer,
mover, leer el destino):

| Trabajo | Cajas | Horas |
|---|---|---|
| Retirar cajas a 0 de L44+ | 19.863 | 330–660 (mucho menos si la mayoría ya no está y se confirma por hueco) |
| Fase 1 de la zona 0 | 2.779 (cifra del prompt) | 45–90 |
| Zona Z, pasos 2 a 4 | 28.937 | 480–960 |

El dato que falta es el tiempo real por caja y qué parte de las cajas a 0 sigue en la nave. Sale del piloto de
L67 P16, que lleva pendiente desde el 26/11 (`TABLERO.md:29`).

---

## 2. Zonas de preparación

Leído por subagente en `odoo/modulos/koroshi_zonas` (1.10.0); lo marcado «comprobado» lo he releído yo.

### 2.1 La zona se decide a las 04:50 y no se vuelve a mirar (riesgo, cruza con la compactación)

- **Prueba:** `motor/v12f.py:141-150` (comprobado): `lineal_de(ml['location_complete_name'])` y
  `pasillo = lineal // 2`. Solo se comprueba al partir (`models/escritor.py:150`).
- **Impacto:** mover una KO reservada (con «Mover», con la 1.17 a ±2 lineales o con el cambio de hueco de la Z)
  puede dejar una línea de una OUT de D1 en lineales de otra zona. Además, el ritmo aprendido de noche
  (`models/ejecucion.py:416`) se calcula con la ubicación ya movida.
- **Atenuante [copia 26/11]:** a las 14:54 solo había 24 uds reservadas en la zona 0 de L44+ y 572 en la Z. Por
  la tarde casi no hay reservas que mover.
- **Propuesta:** compactar después de acabar el picking del día (el 26/11 la previsión daba fin a las 12:44) y, en
  `compactar_hacer`, no mover una KO con reserva de una agrupación Z- de hoy. Lo segundo toca dos módulos.

### 2.2 Los crons no llevan `noupdate` (riesgo)

- **Prueba:** `data/cron.xml:2` (`<odoo>` sin `noupdate`), `:42` (`nextcall` = mañana 03:50 UTC), `:84`
  (`active = False` en el cron del correo). Comprobado.
- **Impacto:**
  - Actualizar `koroshi_zonas`, o un módulo que lo arrastre (`koroshi_base`, `koroshi_kpi`), entre la 01:00 y las
    04:50 mueve el reparto al día siguiente. Solo lo ve el vigilante.
  - Cada actualización apaga el cron del correo aunque se haya encendido a mano.
  - 03:50 UTC es fijo: con el horario de verano el reparto pasa a las 05:50 y el vigilante de las 05:15 dará
    falsa alarma a diario.
- **Propuesta:** `noupdate="1"` y hora calculada en local. Hasta entonces, no actualizar nada que arrastre zonas
  de madrugada.

### 2.3 Se instaló «elegir zonas» sin la parte de la que depende (contradicción con el diseño)

- **Prueba:** `diseno-zonas-criterio-tiempo-cajas-picos_2026-11-26.md` §3.B: «Con 52/21 ninguna pasa los 30 min de
  pico sin la parte A. Por eso A va antes que B». El manifest deja A «para después». El respaldo, `motor/elegir.py:89-93`
  (comprobado), elige la opción de menos pico sin mirar la hora de fin.
- **Impacto:** el único día comprobado es el 26/11 con 23/73. Un día en que todas las opciones pasen de 30 min, el
  criterio pasa a ser «menos pico» aunque acabe más tarde.
- **Propuesta:** en el respaldo, ordenar por hora de fin y después por pico; o esperar a la parte A.

### 2.4 El ritmo 23/73 y el «pico» se apoyan en muy poco (error de supuesto)

| Qué | Prueba **[subagente]** | Propuesta |
|---|---|---|
| 23 = segundos por lectura; 73 = segundos por lineal visitado. El nivel absoluto no se aprende: se escala para igualar el trabajo total del ritmo anterior (52/21, del 22/10) | `motor/aprender.py:227-248`, `models/config.py:136` | Comparar la hora de fin real del 26 y del 27/11 con las dos previsiones antes de fiarse |
| El ajuste vale con 6 filas (dos días de 3 zonas) y dos variables muy correlacionadas. Historial: 24/41, 31/53, 16,8/52,1 | `motor/aprender.py:20`, manifest | Mínimo en días, no en filas, y enseñar cuánto cambia al quitar un día |
| Solo entran días «medidos»; una OUT sin validar deja el día fuera. Se aprende de los días buenos | `models/config.py:125`, `models/ejecucion.py:335` | Guardar también los parciales con su motivo |
| El «pico» es la diferencia entre duraciones previstas, con la plantilla entera, sin descansos, todos a la vez, nadie en Zalando o web. Umbral fijo de 30 min, dure el día 4 u 8 horas | `motor/elegir.py:13` (comprobado: constante, no parámetro), `motor/v12f.py:75` | Personas reales del día y umbral relativo; el diseño decía «en la configuración» |
| `rendimiento = 0` en la configuración da división por cero a las 04:50 | `motor/v12f.py:77-78` (comprobado), `config.py:103-117` no lo valida | Validar que sea mayor que 0 |
| El tiempo previsto no tiene coste por caja: más cajas por unidad (chaquetas, final de temporada) no alarga la previsión | `motor/evaluar.py:105` | Añadir el término o avisar los días de mucho volumen |
| El 27/11, primer día de la 1.10.0 con 23/73, es Black Friday | Fecha | No sacar conclusiones de ese día solo |
| La cifra que justificó el cambio («3 zonas, 12:44, pico 16 min») sale de un script que no está en el repo | Diseño §2 | Guardar el script y el JSON en `bin/versiones/` |

### 2.5 Lo que queda fuera de las zonas

- Lo no reservado no cuenta tiempo ni zona, y los pedidos de menos de 15 uds se saltan (`motor/v12f.py:135` y
  `:192`). Los restos de «Validar incompleto» van sueltos y a los 7 días salen del informe (`models/lector.py:62`).
  **[subagente]**
- **[copia 26/11]** Hay 27.888 uds de V27, 1.626 de I27 y 30.500 de Z en contenedores sin hueco. En `v12f.py:150-153`
  lo que no tiene lineal va por el nombre del hueco. **HIPÓTESIS:** cuando V27 empiece a pedirse, esas líneas no
  caerán en ninguna zona de lineal; lo confirma mirar a qué zona fue una línea reservada en una KO sin hueco.
- El «modo del día» (`diseno-zonas-modo-del-dia_2026-11-20.md`) sigue entero sin hacer y tiene tres números de
  versión distintos (1.7.0, 1.10.0 y 1.11.0 según el documento). **[subagente]**

---

## 3. Riesgos para la PDA y cruces entre módulos

### 3.1 Lecturas no detecta el cambio de hueco de una KO (error)

- **Prueba [código]:** `koroshi_preparacion/models/lectura.py:274` (`_ubi` devuelve `ml.location_id`, que es la
  KO), `:566-568` (el estado ligero manda `self._ubi(ml).id`) y `static/src/js/preparacion.js:337-339` (solo
  recarga si ese id cambia). Al mover una KO cambia el padre de la KO, no su id. No lo he ejecutado.
- **Impacto:** el preparador sigue viendo el hueco viejo hasta que reabre la OUT, y va a un sitio vacío. Afecta a
  «Mover» (ya instalado), a la 1.17 y al «cambio de hueco» de la Z. La v6 (principio 2) y el diseño de la Z (§0)
  dicen lo contrario.
- **Propuesta:** en `koroshi_preparacion` (otro módulo, otra sesión), mandar también el id del hueco padre. Se
  confirma en diez minutos en el navegador: mover una KO de prueba con una línea reservada abierta en Lecturas.

### 3.2 La 1.17 en el árbol de trabajo: cosas que arreglar antes de instalar

Todo **[subagente]**, salvo la primera fila.

| Qué | Prueba | Impacto |
|---|---|---|
| No cuenta las cajas a 0 | `main.py:1416`, `logica.py:240` **[código]** | Ver §1.4 |
| Una columna que espera cajas de otro lineal puede salir como origen a vaciar | `logica.py:245` | Se vacía lo que se acaba de llenar |
| El destino no se valida como dice la v6: con «Sí, aquí» una KO puede acabar en la Z o en cualquier ubicación interna; los vecinos de L44 incluyen L42–L43 | `main.py:1613`, `:903-907`, `:1478` | Mezcla de zonas |
| Las KO con dos modelos-color no salen como «revisar»; salen como «no caben» | `main.py:1459`, `:1513` | Texto engañoso |
| «Calcular» lee las salidas de 28 días de toda la compañía, no las del lineal | `main.py:1355-1364` **[código]** | **HIPÓTESIS** de lentitud; se mide antes de instalar |
| Dos «Calcular» a la vez dejan dos planes; recalcular sustituye pasos que otro tiene cogidos | Sin bloqueo | Dos operarios al mismo sitio |
| Sin referencia (`default_code`) no hay stock por talla y todo sale «ARRIBA» | `main.py:1386`, `logica.py:210-213` | **HIPÓTESIS:** depende de cuántos I27/V27 no tienen referencia |
| Falta la prueba de equivalencia con el programa que pide la v6 §7 | `tests/test_logica.py` | No se sabe si Odoo y el programa dan lo mismo |
| El `employee_id` lo manda el cliente: las listas de tarjetas se saltan enviando otro id | Rutas de «revisar» | Permiso solo aparente |

Comprobado y correcto: la 1.17 no añade campos a `stock.picking`, `stock.picking.type`, `stock.move.line` ni
`stock.location`; los parámetros son registros, no `<function>`; no hay `aria-hidden` ni `display_notification`.

### 3.3 Dominios con punto en lo ya instalado (riesgo de lentitud en la PDA)

- **Prueba [subagente]:** `koroshi_contenedores/controllers/main.py:385` y `:856` (`location_id.usage`, en «dónde»
  y en el buscador, a cada tecla) y `:698` (`picking_id.picking_type_id.code`). `koroshi_faltantes/models/faltante.py:226-228`,
  llamado en bucle por línea desde contenedores (`main.py:455-457`).
- **Impacto:** en Odoo 13 eso busca todas las ubicaciones internas (cada KO es una: unas 79.000) y hace `IN`. Es
  el patrón de `memory/odoo13-dominio-campo-punto-lista-ids.md`.
- **Propuesta:** filtrar por la rama NAVE2 (`child_of`) o por SQL. **HIPÓTESIS** hasta medirlo en el log.

### 3.4 Temporadas escritas a mano en tres sitios (riesgo en el cambio de temporada)

- **Prueba:** `redistribucion/programa/redistrib/productos.py:17`, `koroshi_contenedores/controllers/main.py:1348`
  (parámetro, por defecto «I27,V27») y `bin/KOROSHI_crear_INT_zonas_PLANIFICADA.py:56`. **[código]**
- **Impacto:**
  - Cuando entre la temporada siguiente, sus cajas serán «zona Z» para la 1.17: sus columnas no se vacían ni
    reciben, sin aviso. En el programa, `zona_z.py:177-181` la marcaría como la más nueva y la trataría como outlet
    «vivo».
  - Cuando I27 deje de ser temporada actual, unas 100.000 uds de L44+ pasan de golpe a ser Z.
- **Propuesta:** un solo sitio (parámetro en `koroshi_base`, regla 8) y un aviso cuando haya stock de una
  temporada que no está en ninguna lista. Decidir cuándo I27 pasa a outlet y qué se hace con sus restos (D7).

### 3.5 Recepción, devoluciones y la ronda de faltantes mientras se compacta

- **Recepción:** `koroshi_recepcion` 1.8.0 crea una KO por caja. Cada contenedor marítimo añade cientos de KO
  (RC/0002: 1.046 cajas, `TABLERO.md:45`). Si entran en los lineales que se están compactando, el plan se queda
  viejo cada día. Ver la propuesta de §1.3.
- **Devoluciones:** «Ubicar» entra prendas por EAN y KO. **HIPÓTESIS:** puede ubicar en una KO de una columna en
  vaciado o en un hueco «reservado» de una tarea de la Z, porque esas reservas solo existen en tablas propias. Se
  confirma leyendo qué valida `koroshi_devoluciones` del destino.
- **Zona Z, «cambio de hueco»:** la KO libre de destino necesita las mismas comprobaciones que la ronda de la
  1.16 (líneas abiertas, negativos, marca «Tiene prendas», faltantes en ronda), no solo «Odoo dice 0». **[subagente]**
- **Choque entre fases:** si alguien amplía `cajas_cero_lineales` a L01–L43, la ronda «Retirar cajas a 0»
  archivaría los huecos libres de la Z. **[subagente]**
- **Final de temporada:** las chaquetas llenan la caja con unas 10 uds (`memory/pendiente-procedimientos-final-temporada.md`).
  Los topes por cajas (8 por columna) no cambian, pero las previsiones de zonas y «Caja llena» sí. Sin
  procedimiento escrito todavía.

---

## 4. Faltantes

Leído por subagente; comprobado por mí lo que se indica.

### 4.1 La alarma del 7 % / 10 % no distingue señal de ruido (error)

- **Prueba:**
  - `koroshi_faltantes/models/relativo.py:133-143` (comprobado): la única condición es `faltante < 1`. Sin mínimo
    de unidades recibidas.
  - `bin/versiones/20261127_faltante-relativo_datos_v1.txt`: 132 SKU al 7 % o más; solo 19 con 50 o más
    recibidas; 102 con 20 o menos; 73 con una sola unidad de faltante.
  - `relativo.py:29` (comprobado): el patrón de prenda admite `2611UN10-`. El pack de calcetines está excluido en
    `odoo/KOROSHI_faltante_relativo_listado_2026-11-26.py:10` y en lo enviado a KOROSHI, pero no en el módulo.
  - `relativo.py:180` (comprobado): `neto = bajas − altas + en_FALTANTE`. Lo que está en FALTANTE sin revisar
    cuenta como faltante: 45 SKU pasan del 7 % solo por eso.
- **Impacto:** el correo de las 17:00 dirá «unos 132 SKU en alarma» cuando a KOROSHI se le contaron 9 críticos.
  Con el pack, el global del módulo sería del orden del 0,6 %, no el 0,29 % del HTML (cálculo del subagente:
  (1.815 + 2.024) ÷ (630.387 + 4.048)). El % sube solo mientras no se hagan rondas.
- **Propuesta:** parámetro de mínimo recibido (50), lista de exclusión por parámetro y dos columnas: «confirmado»
  (bajas − altas) y «en revisión» (en FALTANTE).

### 4.2 Cifras que no coinciden entre documentos (contradicción)

| Qué | Prueba |
|---|---|
| Global: 0,035 % (pérdida neta, documento interno), 0,28 % (correo a KOROSHI), 0,29 % (HTML del 27/11), 0,32 % (respuesta del 23/11) | `20261126_investigacion-faltantes_v1.md:17-19` (comprobado), `20261126_correo-koroshi-faltante-relativo_v1.md:22` |
| El mismo 189 con signo contrario: pérdida neta de 189 en la temporada 26 y +189 en la tabla mensual desde agosto | md líneas 19 y 170 (comprobado). Coincidencia o error: hay que recalcular, y las cifras van tecleadas en el script |
| «73 % = bajas de 1 a 3 uds a mano»: el 73,4 % es todo el grupo B; las de 1 a 3 uds son el 50 % (1.923 de 3.814 líneas) | md §2; mal citado en `20261126_inventario-dinamico-diseno_v1.md:5` y en la memoria `faltante-relativo-umbrales-avisos` |
| Los «datos conocidos del 24/11» (223 SKU a 0 y 497 uds; 459 faltantes desde el 01/11; 126 líneas) no están en ningún fichero | El md da 240 SKU y −504 uds, y 563 registros desde el 09/11 (el módulo nació el 09/11) |
| `TABLERO.md:65` dice a la vez «1.12.0 INSTALADA», «servidor 1.10.0» e «Instalar la 1.12.0» | Fila de faltantes |

**Propuesta:** un solo global con nombre fijo para fuera (bajas brutas ÷ recibido, sin pack) y otro para dentro
(pérdida neta), y usar las cifras del 26/11.

### 4.3 La ronda INT/67387 abierta bloquea (riesgo)

- **Prueba:** `models/faltante.py:590-592` (comprobado): con un faltante «en ronda» no se puede marcar Encontrado
  ni No encontrado fuera de esa INT. `:846-854` y `koroshi_contenedores/controllers/main.py:219`: no se archiva
  una caja con un faltante en ronda abierta. En `20261124_ronda-faltantes-prioritarios_koroshi_v1.xlsx`, 20 de los
  90 faltantes están en la INT/67387. **[subagente]**
- **Impacto:** esos 20 resultados de la ronda en papel no se pueden apuntar, y «Retirar cajas a 0» falla en esas
  cajas. No bloquea OUT.
- **Propuesta:** cancelar la INT (los faltantes vuelven a pendiente) o hacerla antes que la de papel.
- **Riesgo añadido [subagente]:** `crear_ronda` (`faltante.py:666-726`) no mira si hoy ya hay stock del SKU en la
  ubicación vieja. Leer una prenda ya dada de alta por otra vía sería «Encontrado» y un +1 de más. **HIPÓTESIS:**
  falta leer el lado de Lecturas.

### 4.4 Nada corta la repetición diaria (se ha pasado por alto)

- **Prueba:** el md §4 dice que no hay regularizaciones a S4T desde el 14/08; no hay código de regularización ni
  de snapshot en `odoo/modulos`; las acciones 4 y 5 del md no tienen fila en el tablero. La memoria dice «el
  snapshot a S4T lo mandamos nosotros». **[subagente]**
- **Impacto:** las mismas prendas se piden, se cancelan y se cuentan cada día (las faltas se cuentan 2,8 veces,
  md resumen punto 2).
- **Propuesta:** abrir la fila en el tablero y aclarar quién manda el snapshot. Es lo que más líneas canceladas
  quita por menos trabajo.

### 4.5 Lo que no se ha cruzado

- **Cajas a 0 con prendas:** la marca «Tiene prendas» de la 1.16 no se cruza con los faltantes. Parte de lo
  «perdido» puede estar en esas cajas (en noviembre, altas de contenedor 1.234 frente a 341 bajas, md §5). El
  piloto de retirar cajas a 0 es también la ronda de faltantes más barata. **[subagente]**
- **[copia]** El stock en EFFEC/FALTANTE pasó de 429 uds (23/11) a 679 (26/11): +250 en tres días. Coincide con
  «Poner a cero» y «Cambiar» pasando por Faltantes; sin rondas, solo crece.
- **Stock negativo:** 98 filas, −185 uds, igual el 23/11 y el 26/11. La fórmula no las mira: son prendas servidas
  que cuentan como faltante. **[subagente]**
- **Causas sin separar en la alarma:** cruce de talla (2621XC04: faltan 22 y sobran 20, y aun así alarma),
  recepción mal contada, devolución mal ubicada, sorter.
- **Correo de las 17:00:** un solo destinatario (Isaac), cuando el nivel 1 es José Luis; con la tabla vacía manda
  «Ninguno»; el recálculo borra e inserta todo cada hora (`relativo.py:205-207`). **[subagente]**

---

## 5. Contradicciones de estado (documentos frente a la realidad)

| Qué dice | Qué hay | Prueba |
|---|---|---|
| El prompt de esta revisión: «koroshi_zonas 1.10.0 sin instalar» | El tablero: «1.10.0 INSTALADA 26/11 ~16:15». La fila mezcla frases de varios días y cuesta leerla | `TABLERO.md:42` |
| v6: «No hay código de la 1.17.0» | El árbol de trabajo tiene `13.0.1.17.0` sin commitear (13 ficheros, `models/compactar.py` nuevo) | `git status`; `__manifest__.py:153` **[subagente]** |
| Tablero: «siguiente: 1.17.0 Reagrupar KO con KO mixta, en diseño», diseño v4 | La v6 pasó la KO mixta a la fase 2 | `TABLERO.md:29` |
| `logica.py:149`: «Diseño v6 aprobado» | La v6 se titula «DISEÑO v6 para Isaac», con las decisiones 15 y 16 abiertas | **[subagente]** |
| v6: decisión 14 «Decidido» | La v5 decía que Isaac no había confirmado el fondo; la v6 no dice cuándo lo confirmó | v5 y v6 §6 **[subagente]** |
| Tablero: «espera… la capacidad real de un palé (770 L)» | La v6: «la fase 1 no necesita litros» | `TABLERO.md:60` |
| Código de la 1.16: «Arranca o tacha su etiqueta KO_» | La decisión 3 (qué se hace con la etiqueta) sigue pendiente | `main.py:1233` **[subagente]** |

---

## 6. Mejoras, ordenadas por impacto frente a esfuerzo

| # | Mejora | Qué gana | Esfuerzo |
|---|---|---|---|
| 1 | Diez minutos en la nave para aclarar columna, palé, posición y C3–C4 (D2) | Desbloquea el objetivo de la 1.17 y la fase 3; puede descubrir suelo ya libre | Muy bajo |
| 2 | Piloto de «Retirar cajas a 0» en L67 P16 midiendo segundos por caja y cuántas siguen allí | Da las horas reales de todo el plan; encuentra prendas «perdidas» | Bajo; ya instalado |
| 3 | No mover la Z hasta decidir D1 | Evita hasta 29.000 movimientos que quizá se deshagan | Ninguno |
| 4 | Tratar V27 como clase A y decidir sus lineales antes de compactar | La temporada nueva queda bien a la primera | Bajo en código; una decisión |
| 5 | Mínimo de recibido, exclusión del pack y dos columnas en el % de faltante | Alarmas de 132 a unas 19; mismas cifras dentro y fuera | Bajo (un módulo) |
| 6 | Cancelar o hacer la INT/67387 | Desbloquea 20 faltantes y el archivado de esas cajas | Muy bajo |
| 7 | Contar las cajas a 0 en la 1.17 y validar el destino | Evita «No cabe» en cadena y KO en zona equivocada | Bajo, antes de instalar |
| 8 | Lecturas: recargar cuando cambia el hueco padre | El preparador no va a un hueco vacío | Bajo, pero en `koroshi_preparacion` (PDA: fuera de horas) |
| 9 | `noupdate` en los crons de zonas y validar `rendimiento > 0` | Evita un día sin reparto | Muy bajo |
| 10 | Regularización o snapshot a S4T | Quita las faltas repetidas cada día | Medio; depende de S4T |
| 11 | Temporadas en un solo parámetro con aviso | Evita el fallo silencioso al cambiar de temporada | Bajo, toca tres sitios |
| 12 | Rehacer el escenario de la fase 3 con estanterías reales | Cifras de metros que se puedan creer | Medio |

---

## 7. Orden recomendado y decisiones de Isaac

**Orden:**

1. Mejoras 1, 2 y 6: no necesitan código.
2. D1 y D5 (abajo): deciden si la Z se toca y dónde entra V27.
3. Faltantes (mejora 5) y zonas (mejora 9): cambios pequeños, cada uno en su módulo.
4. 1.17 con la mejora 7, instalada después de que el lineal de prueba esté sin cajas a 0. Compactar por la tarde
   hasta tener la mejora 8.
5. Ubicar V27 en los lineales compactados.
6. Fase 3 rehecha. La zona Z, la última.

**Decisiones, de la que más bloquea a la que menos:**

| # | Decisión | Qué bloquea | Recomendación |
|---|---|---|---|
| D1 | ¿Qué va junto al muelle: la zona 0 o el outlet vivo? ¿Se desmontan estanterías de L01–L43? | Todo el plan de la Z y la fase 3 | No mover la Z ahora. Si las estanterías se quedan, acercar la 0 dentro de L44+ y dejar el outlet donde está |
| D2 | ¿Cuántas cajas lleva un palé (8 o 16) y cuántos palés tiene una posición? ¿Existen C3–C4? | Objetivo de la 1.17, tope 7 u 8, fase 3 | Medirlo en la nave. Con los datos, 8 por columna es coherente |
| D5 | ¿En qué lineales entra V27 y con qué regla? | Qué lineales compactar primero | Los más cercanos al muelle de L44+, por modelo-color, una vez compactados |
| D3 | P1 de la Z: ¿la etiqueta KO va en la caja o en la estantería? | Todo el mecanismo de la Z | Solo hace falta si D1 mantiene el plan de la Z |
| D4 | Decisión 15: tope 7 u 8 | Parámetro de la 1.17 | 8, contando las cajas a 0 |
| D6 | % de faltante: mínimo recibido, pack, quién recibe el correo | Mejora 5 | 50 uds; pack fuera; añadir a José Luis |
| D7 | ¿Cuándo pasa I27 a outlet y qué se hace con sus restos? | Parámetro de temporadas, fase 2 | Fijar la fecha ahora |
| D8 | Decisión 13 (altura): ¿vale la banda por caja de la v6? | Parte de la 1.17 | Quitarla de la fase 1 o limitarla a 4 «abajo» |

---

## 8. Datos que faltan y cómo conseguirlos con poco trabajo

| Dato | Cómo | Trabajo en la nave |
|---|---|---|
| Qué es una posición y si C3–C4 existen | Mirar 10 posiciones de L44+ (5 con solo C1–C2 en Odoo y 5 con las cuatro) y una foto de cada | 10 min |
| Cuántas cajas a 0 siguen en la nave y cuánto se tarda | Piloto de la ronda 1.16 en L67 y dos lineales más, con hora de inicio y fin | 1–2 h |
| Si Lecturas ve el cambio de hueco | Navegador, una KO de prueba con una línea reservada | 10 min, sin nave |
| Dudas de las hojas de la Z (207) y si cada hoja dibuja el par de lineales | Solo si D1 mantiene la Z: repasar las posiciones «X» que tienen KO en Odoo (12) y el tipo E | 30 min |
| Capacidad real de D10, C y E | Contar celdas y KO en 5 posiciones de cada tipo | 20 min |
| Hora de fin real frente a prevista con 23/73 | Ya está en Odoo (informe de zonas del 26 y del 27/11): solo leer | Ninguno |
| A qué zona va una línea reservada en una KO sin hueco | Leer una OUT real con una línea de V27 | Ninguno |
| Coste de «Calcular» y de los dominios con punto | Log de tiempos o EXPLAIN en producción, con permiso | Ninguno |
| Productos I27/V27 sin referencia | Un `search_count` de solo lectura | Ninguno |
| El 189 y los tres globales | Recalcular con el script del 26/11 sobre los mismos movimientos | Ninguno |

---

## 9. Lo que no he podido comprobar

- Las cifras de la fase 1 con 8 cajas por columna (1.711 / 2.779 / 1.650 / 2.631 / 6.167): no tienen documento.
- Nada se ha ejecutado en Odoo ni en una PDA. Lo de Lecturas (§3.1) y los hallazgos de la 1.17 son lectura de
  código; la 1.17 puede cambiar, porque otra sesión la está escribiendo.
- Las horas de §1.8 son una estimación con un supuesto sin medir.
- Lo marcado **[subagente]** sin «comprobado» no lo he releído yo.
- No he abierto las fotos ni las ocho hojas originales del 02/11; solo su transcripción.
