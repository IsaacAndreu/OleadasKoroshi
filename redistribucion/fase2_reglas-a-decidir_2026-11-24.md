# Fase 2 — Reglas que hay que decidir (24/11/2026)

**Estado: BORRADOR para decidir.** Todavía no es la propuesta de movimientos. Los números salen de
`programa/redistrib/escenario.py` aplicado a la copia de Odoo del 23/11 a las 17:07
(`copias/20261123_1707_odoo.sqlite`). Esa copia tiene el stock y las salidas desde el 24/11/2025. No se ha escrito
nada en Odoo.

## 1. Qué se ha medido

| Medida | Valor | Cómo |
|---|---|---|
| Capacidad de un hueco | ~770 L (90–95 % de los huecos llenos tienen ≤ 10 contenedores) | Litros por hueco en la copia; cuadra con 10 cajas de 84 L |
| Contenedor típico | Mediana de 3 uds y 8,7 L. Hay dos grupos: cajas de unos 90 L y cartones de proveedor de unos 600 L | Litros por contenedor |
| Niveles C3 y C4 | Casi vacíos: 809 y 793 huecos con stock, frente a unos 3.500 en C1 | Huecos con stock por nivel |
| Lineales | Hoy hay 83 lineales con mayoría de zona 0 y 52 con mayoría de Z. La 0 está sobre todo en L45–L120; la Z, cerca de expedición | Zona de la mayoría de las unidades |
| Metros por pick hoy | **101,7 m** | Cada modelo-color, a la media de sus huecos (por uds), por los albaranes de entrega de 28 días |
| Modelos-color en más de un lineal | **7.969 de 11.230 (71 %)** | |
| Pendiente de ubicar | Unas 82.000–86.000 uds (muelle, N1, perchas, contenedores colgados de la nave) | Depende de si cuenta lo que hay fuera de L01–L136 |

Los litros salen de la ficha solo en el 8 % de los productos. Para el resto se usa la media de la familia
(`TIPOS` de kpi.py). Los m³ son **orientativos**.

## 2. Escenarios calculados

Reglas comunes de todos los escenarios:
- se coloca el modelo-color entero;
- los huecos se llenan al 90 %;
- se recorren los lineales del más cercano al más lejano de expedición;
- dentro de la zona 0, primero lo que tiene más picks por litro;
- después va la Z.

| | A | B | C | D | E |
|---|---|---|---|---|---|
| Zona 0 en niveles | C1–C2 | C1–C3 | C1–C2 | C1–C2 | C1–C4 |
| Juntar cajas medio vacías de Z | Sí | Sí | **No** | Sí | Sí |
| Z en lineales aparte | Sí | Sí | Sí | **No: Z en C3–C4, encima de la 0** | Sí |
| **Metros por pick** (hoy 101,7) | **25,1** | 22,5 | 25,2 | 22,9 | **21,1** |
| Modelos-color en > 1 lineal (hoy 7.969) | 24 | 20 | 43 | 27 | 16 |
| Lineales de la zona 0 | L01–L24 | L01–L17 | L01–L24 | L01–L24 (C1–C2) | L01–L13 |
| Lineales de Z | L25–L35 | L18–L27 y L29 | **L25–L55** | L01–L24 (C3–C4) | L14–L24 |
| Lineales libres (de 136) | 101 | 108 | 81 | 112 | 112 |
| Huecos usados (de 21.489) | 3.740 | 3.740 | **7.015** | 3.740 | 3.740 |
| m³ ocupados (hoy 4.802) | 2.557 | 2.557 | **4.802** | 2.557 | 2.557 |
| Unidades a mover: rehacer toda la nave (de 361.673) | 361.667 | 361.653 | 361.660 | 361.666 | 361.668 |
| Unidades a mover: mínimo con esa frontera | 326.138 | 323.463 | 326.138 | 326.138 | 322.359 |
| Sin sitio | 0 | 0 | 0 | 0 | 0 |

En todos los escenarios, la **zona 0 son solo 589 modelos-color, pero tienen el 91 % de los picks** (45.647 de
50.285). La Z son 10.716 modelos-color con 4.638 picks. En unidades están a medias:
185.432 de la 0 y 176.241 de Z. Casi todo el ahorro de metros sale de traer la 0 cerca de expedición.

Lo que mueve cada regla está en negrita.

**Juntar sin cambiar las zonas de sitio** también se ha probado: dejar cada lineal con la zona que tiene hoy y solo
traer cada modelo-color a su lineal principal. Habría que mover 137.150 uds (62.633 de la 0 y 74.517 de Z), más lo
pendiente de ubicar. Los metros por pick pasan de 101,7 a **101,5**: no se gana nada en recorrido. Solo se gana orden.

## 3. Lo que hay que decidir

### 3.1 Dónde está expedición — **lo primero; todo lo demás depende de esto**

Los metros salen de la geometría de `kpi.py`, que pone la salida (BASE) en (26,30), cerca de L01. **No lo he podido
comprobar.**
- Si expedición está de verdad ahí, la zona 0 está hoy en la punta equivocada de la nave. Por eso el movimiento
  mínimo es tan grande: unas 326.000 uds, casi todo.
- Si está en otro sitio, hay que cambiar BASE y repetir los cálculos. Los números de la tabla pueden cambiar mucho.

**Necesito:** que confirmes en el plano dónde se deja la mercancía preparada (el punto al que va el operario al acabar
el pedido).

### 3.2 Niveles para la zona 0

| Opción | Metros por pick | A favor | En contra |
|---|---|---|---|
| C1–C2 (A) | 25,1 | Se coge a mano, sin escalera ni carretilla | Ocupa más lineales (L01–L24) |
| C1–C3 (B) | 22,5 | | C3 necesita escalera o recogepedidos |
| C1–C4 (E) | 21,1 | Lo más corto | C4 para picking diario es lento y peligroso |

**Recomendación: C1–C2.** La diferencia con C1–C4 son 4 m por pick. Subir a C3 o C4 para cada pick cuesta más que
eso. Hay que comprobarlo contigo: no sé con qué se coge hoy en C3.

### 3.3 Juntar las cajas medio vacías de Z

Sin juntarlas (C), la Z ocupa L25–L55 en vez de L25–L35, se usan 7.015 huecos en vez de 3.740 y se ocupan 4.802 m³ en vez de 2.557. El recorrido casi
no cambia (25,2 frente a 25,1), pero el espacio sí.

**Recomendación: sí, juntarlas**, cuando se mueva cada modelo-color, no como tarea aparte. Hay que decidir qué se
hace con la caja que queda vacía: archivar el contenedor en Odoo o reutilizarlo.

### 3.4 Frontera entre zonas: por lineales o Z arriba

- **Por lineales (A):** cada pasillo es de una sola zona. Es fácil de explicar y de señalizar.
- **Z arriba, en C3–C4 de los mismos lineales (D):** 2 m menos por pick. A cambio, mezcla zonas en el mismo hueco
  vertical, que es justo lo que pinta en rojo la lista 3 del mapa.

**Recomendación: por lineales.**

### 3.5 Rehacer toda la nave o por fases

El mínimo ya son unas 326.000 uds, así que «por fases» no ahorra unidades: solo las reparte en el tiempo.

**Recomendación: por fases, empezando por los modelos-color de la zona 0 con más picks.** Los 589 modelos-color de la 0 son
185.432 uds de las 361.673 (164.178 ya en huecos y el resto pendiente de ubicar) y dan casi todo el ahorro de
metros. Pero hoy L01–L24 están ocupados sobre todo por Z: antes de traer la 0 hay que vaciarlos. Cada tanda será
un intercambio: Z de un lineal cercano → lineales lejanos que deja libres la 0, y la 0 al hueco que queda.
Los 101 lineales que quedan libres en el escenario A dan margen para hacerlo sin bloquear. Cada fase deja la nave funcionando. La fase 3 tiene que calcular cuánto se gana
con cada tanda.

### 3.6 Lo pendiente de ubicar y los contenedores a cero

- **Pendiente:** unas 82.000–86.000 uds. Los escenarios lo colocan como si fuera stock normal. ¿Entra en el plan o se
  ubica antes, por su lado?
- **Contenedores a cero:** 30.181 sin archivar. No ocupan sitio en el cálculo, pero sí en Odoo y en las listas de la
  PDA. ¿Se archivan? Hacerlo es escribir en Odoo, así que lo harías tú o el responsable, no este programa.

### 3.7 Ritmo

¿Cuántas personas y horas al día se dedican a mover? Con eso, la fase 3 da los días de cada tanda. Ejemplo: 2
personas que muevan 1.500 uds/día cada una tardarían unas 15 semanas en mover 326.000 uds.

### 3.8 Capacidad de 770 L por hueco

Es lo que se ha medido en los huecos llenos, no la medida física. Si sabes las medidas de un hueco (ancho × fondo ×
alto útil), la cambio. Si la capacidad real fuera mayor, la zona 0 cabría en menos lineales.

## 4. Lo que falta para la fase 3 (propuesta de movimientos)

- Que confirmes BASE (3.1) y las reglas 3.2 a 3.8.
- Medidas físicas de un hueco y del pasillo, si las hay.
- La lista de movimientos en sí: de qué contenedor a qué hueco, por tandas. Se exportará a Excel para revisarla; no
  se escribirá nada en Odoo.

## 5. Respuestas de Isaac (24/11, por la tarde)

| Punto | Respuesta | Queda así |
|---|---|---|
| 3.1 Expedición | «Está en la parte de los muelles». Los muelles no salen en el mapa porque no tienen ubicación en el plano | **Pendiente de confirmar** si los muelles están en el lado de L01. MU-00…MU-14 existen en Odoo (980 ubicaciones, sin stock), pero sin coordenadas |
| 3.2 Niveles de la 0 | «Como me digas mejor» | **C1–C2** |
| 3.3 Juntar cajas de Z | Sí | **Sí** |
| 3.4 Frontera | Bien | **Por lineales** |
| 3.5 Por fases | Sí. Prioridad: la zona 0, «la de detrás de todo, del L47 al L138» | **Por fases, la 0 primero.** Falta decidir si la 0 se queda detrás o se trae junto al muelle (ver abajo) |
| 3.6 Pendiente | «Igual aún no ha llegado»; propone mirar la integración S4T en nath.tuctuc.com | Ver abajo: **no es mercancía por llegar** |
| 3.8 Capacidad | Vale | **770 L** |

### Lo pendiente de ubicar ya está en Odoo

Las 86.453 uds de «pendiente» son stock que ya está en NAVE2 en Odoo, pero no en un hueco de L01–L136:

| Dónde | Uds | Ejemplos |
|---|---|---|
| Contenedores colgados de la nave, sin hueco | 52.146 | KO_101025_1267, KO_101025_1268… |
| Perchas | 32.239 | PERCHAS_KO |
| Otros | 2.068 | 081121_001, 081121_002… |

Por eso no hace falta mirar la integración S4T para esto. Lo recibido en S4T que aún no está en Odoo no entra en la
copia. Las perchas probablemente no van a huecos y habría que sacarlas del cálculo.

### La 0 detrás o junto al muelle

Si el muelle está en el lado de L01, hay dos opciones:

| | Metros por pick (hoy 101,7) | Uds a mover |
|---|---|---|
| La 0 se queda detrás (L47–L138); solo se junta cada modelo-color en su lineal | 101,5 | 137.150 + pendiente |
| La 0 se trae delante, a L01–L24 en C1–C2 (escenario A) | 25,1 | ~326.000 |

Solo traerla delante ahorra recorrido. Dejarla detrás ordena el stock, pero no acorta el camino.

### Confirmado por Isaac: el muelle está antes de L01

«El muelle va antes de la L01, abajo del todo». Es el lado donde `kpi.py` pone la salida, BASE (26,30), así que
**los escenarios A–E valen tal como están**. La salida se toma en el centro de ese lado, a la altura del pasillo
central. Si sale por una punta, cambian unos metros, pero no la conclusión.

Zona de cada tramo de lineales hoy, según la mayoría de unidades de la copia del 23/11:

| Lineales | Zona hoy | Unidades en el tramo |
|---|---|---|
| L01–L42 | Z (outlet): 0–2 % de zona 0 | L01–L46: 76.851 de Z y 8.811 de la 0 |
| L43–L46 | Mezclados | (incluidos en la fila de arriba) |
| L47–L52 | Z por poco: 21–47 % de zona 0 | L47 en adelante: 155.367 de la 0 y 34.191 de Z |
| L53–L136 | 0, salvo L63 y L107 | (incluidos en la fila de arriba) |

De L01 P18 a la salida hay 5 m; de L136 P18, unos 135 m. Hoy la zona 0, que hace el 91 % de los picks, está en la
punta lejana. La Z, que hace el 9 %, está junto al muelle.

## 6. Propuesta (Isaac: «lo que creas mejor en tiempo y distribución»)

**Traer la zona 0 junto al muelle por tandas de lineales, empezando por L01, y mandar detrás solo la Z que estorba.**
Reglas del escenario A: la 0 en C1–C2, Z juntada, frontera por lineales, 770 L por hueco al 90 %. En cada tanda entran
los modelos-color de la 0 con más picks por litro.

Resultado acumulado, con la copia del 23/11. Las unidades de la 0 incluyen sus restos repartidos y lo pendiente de
ubicar. La Z que se saca es la que hoy ocupa esos lineales:

| Hasta el lineal | % de los picks ya delante | Uds de la 0 movidas | Uds de Z sacadas | Total movido | Metros por pick (hoy 101,7) |
|---|---|---|---|---|---|
| L01 | 20 % | 12.593 | 1.938 | 14.531 | 84,1 |
| L02 | 32 % | 24.094 | 3.804 | 27.898 | 74,7 |
| **L04 (tanda 1)** | **49 %** | 46.583 | 7.287 | **53.870** | **60,6** |
| L06 | 61 % | 69.185 | 10.152 | 79.337 | 51,0 |
| **L10 (tanda 2)** | **74 %** | 98.415 | 16.914 | **115.329** | **39,6** |
| L15 | 85 % | 126.042 | 27.175 | 153.217 | 31,9 |
| **L21 (tanda 3)** | **91 %** | 157.080 | 37.574 | **194.654** | **27,2** |
| L24 | 91 % | 185.432 | 41.721 | 227.153 | 27,2 |

Lo que se ve:
- **Las primeras tandas son las que más rinden.** Con 54.000 uds movidas (L01–L04), la mitad de los picks ya está
  delante y el recorrido baja un 40 %.
- **De L21 a L24 no se gana nada.** Son 28.000 uds de la 0 sin picks en 28 días. **Propuesta: no moverlas.** Se
  quedan detrás hasta que tengan salida, y se ahorran 28.000 uds de movimiento.
- **La Z solo se mueve cuando estorba**, unas 37.500 uds hasta la tanda 3. Va a los huecos que deja libres la 0
  detrás, juntando las cajas. El resto de la Z no se toca.
- Total hasta la tanda 3: **unas 195.000 uds, no las 326.000** de rehacerlo todo, con casi toda la ganancia (27,2 m
  frente a 25,1).

Cada tanda deja la nave funcionando. Primero se vacía de Z el lineal de delante y después se llena con la 0. Los días
de cada tanda dependen de la gente y de las horas dedicadas, que aún no tengo: no los calculo.

Las perchas (PERCHAS_KO) son todas de Z: 32.682 uds. Esta propuesta no mueve la Z pendiente, así que **no cambian
las cifras**. Se quedan donde están.
