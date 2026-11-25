# Diseño: koroshi_contenedores 1.5.0 (compactar un hueco)

18/11/2026. Solo diseño: **congelación desde el 17/11**, no se programa hasta que se levante.
Origen: dos grabaciones del almacén («Nueva grabación 24_0655» y «Carrer Danuvi 4_2104»).
Base: koroshi_contenedores **1.4.0 instalada**.

## Lo que piden (resumen de las grabaciones)

Compactar se hace por hueco (lineal, palet, columna):

1. Se escanea el hueco y salen todos sus contenedores con sus uds. Como mucho tendría que haber unos 9; en Odoo
   salen más porque hay muchos a cero.
2. Hay tres casos:
   - **Caso 1, todo vacío:** se archiva todo y los contenedores desaparecen.
   - **Caso 2, mixto (vacíos y llenos), y cuadra:** se marcan los vacíos y se archivan. Los que tienen material se
     marcan y se pasan a otro hueco, o la persona coge las prendas y las ubica.
   - **Caso 3, no cuadra con lo que hay físicamente:**
     - Odoo dice que tiene prendas y está vacío: primero se **pone a cero** y luego se archiva.
     - Odoo dice que está vacío y hay prendas: se toca el contenedor y se **escanean las prendas para añadirlas**.
3. **Regla clave**: no se puede archivar un contenedor con material. Primero hay que ponerlo a cero, para evitar
   el «lo he tocado sin querer».
4. Se mantiene mover contenedores sueltos o varios a la vez escaneándolos: hay quien los pasa por familia y no
   todos juntos.

## Qué hay ya en la 1.4.0

| Pieza | Estado |
|---|---|
| Escanear hueco → lista de contenedores con uds, reservadas y «vacío» | Hecho (`_datos_hueco`) |
| Mover uno o varios contenedores escaneándolos + destino | Hecho (`/mover`) |
| Archivar vacíos con «¿está físicamente vacía?» | Hecho, pero **todos los vacíos del hueco a la vez**, sin elegir (`/limpiar`) |
| Inventario por lineal (L94) | Hecho |
| Elegir contenedores en la lista | No |
| Poner a cero / añadir prendas | No |

## Diseño

Se hace en dos partes, para no mezclar riesgos:

- **1.5.0, casos 1 y 2: solo pantalla.** No toca el stock: cambia el hueco padre y archiva, como ahora.
- **1.6.0, caso 3: ajuste de stock.** Toca `stock.quant`, el stock real. Va aparte y con más pruebas.

### 1.5.0: elegir y actuar (casos 1 y 2)

**Pantalla del hueco** (después de escanear el hueco):

```
L94-P2-C1                                   [Marcar vacíos] [Desmarcar]
 [ ] KO_240826_1327     12 uds (3 reservadas)   2 ref.
 [x] KO_240901_0815      0 uds  VACÍO
 [x] TT_241002_1104      0 uds  VACÍO
 [ ] KO_241010_0930      4 uds                  1 ref.
 Prendas sueltas en el hueco: 0
 ------------------------------------------------------------
 [Archivar marcados (2)]        [Mover marcados (0) → escanear destino]
```

- Cada fila tiene una casilla. **«Marcar vacíos»** marca de una vez todos los que están a cero, que es el caso 1
  en un toque.
- **Archivar marcados**:
  - pregunta «¿Están físicamente vacíos? (2)»;
  - en el servidor vuelve a comprobar cada uno: si alguno tiene uds o reservas, **no lo archiva** y lo dice
    («KO_… tiene 4 uds: ponlo a cero primero»);
  - los demás se archivan igual que ahora.
- **Mover marcados**:
  - solo se activa si los marcados tienen material;
  - el siguiente escaneo de ubicación es el destino;
  - usa la misma lógica que `/mover`: cambia el padre y conserva las prendas y las reservas.
- La lista se refresca después de cada acción. Si el hueco queda sin contenedores: «Hueco limpio».
- Mover escaneando contenedores sueltos sigue igual. Si la pantalla está en un hueco y se escanea un contenedor, va
  a la cola de mover, como ahora.
- El botón actual «Archivar los vacíos» desaparece, porque «Marcar vacíos» + «Archivar marcados» hace lo mismo.

**Servidor**:

- `/koroshi/contenedores/archivar`:
  - recibe `contenedor_ids`, `hueco_id`, `employee_id` y `confirmado`;
  - comprueba que cada contenedor sea hijo de ese hueco, con nombre KO_ o TT_ y activo;
  - aplica la misma regla de cero que `/limpiar` (sin quants con cantidad ni reserva);
  - deja una línea `accion='archivar'` por contenedor.
- `/koroshi/contenedores/mover` sirve tal cual, porque ya acepta varios `contenedor_ids`.
- `/limpiar` se queda un tiempo por compatibilidad (pantallas con el JS antiguo en caché) y se quita en la
  siguiente versión.

**Tablas**: ninguna nueva y ningún campo nuevo. Solo JS, XML, CSS y una ruta.

**Riesgo**: bajo. Mismas operaciones que la 1.4.0; solo cambia que se eligen.

### 1.6.0: poner a cero y añadir prendas (caso 3)

En la pantalla del hueco, al tocar el **nombre** de un contenedor (no la casilla) se abre su detalle: prendas, uds y
reservadas, como al escanearlo ahora. Ahí aparecen dos botones:

**A) Poner a cero** (Odoo tiene prendas, el contenedor está vacío):

- Pregunta: «KO_… : Odoo dice 4 uds de 1 ref. ¿Está físicamente vacío? Las 4 uds saldrán del stock».
- **Si alguna uds está reservada para un pedido, NO se deja** y dice cuál («2 uds reservadas para
  S-6665004xxx / OUT xxxx»). Antes hay que quitar la reserva desde el pedido. Así no se rompe una preparación en
  curso.
- Ajuste de inventario de Odoo 13 sobre los quants del contenedor:
  - `inventory_quantity = 0` con `inventory_mode`;
  - genera un movimiento a la ubicación de pérdida de inventario y queda trazado en Inventario > Movimientos;
  - hay que comprobarlo en una copia antes, viendo qué movimiento crea exactamente en la 13 EE.
- Después el contenedor queda a cero y ya se puede marcar y archivar.

**B) Añadir prendas** (Odoo dice vacío o le faltan prendas):

- Modo «Añadir a KO_…»: cada EAN escaneado suma 1 ud de ese producto en ese contenedor.
  - EAN desconocido: pita y no suma.
  - Botón «Quitar la última» para deshacer un escaneo.
- Las prendas se acumulan en la pantalla. Con **«Guardar (n uds)»** se hace un único ajuste de inventario (+n) por
  producto.
- No pregunta de dónde venían. Como se dijo en la grabación: «estás poniendo la prenda dentro del contenedor y
  estás poniendo el material que es».

**Registro**: `koroshi.contenedor.movimiento` tiene que guardar estas acciones:

- añadir `('cero', 'Poner a cero')` y `('anadir', 'Añadir prendas')` al campo `accion`;
- en `uds` va lo que sale (negativo) o entra (positivo).

Es su propia tabla, no una compartida, así que la regla 7 no aplica. Aun así es un cambio de modelo: necesita
actualizar el módulo, no solo los ficheros estáticos.

**Riesgo**: alto.

- Toca el **stock real** del cliente.
- Lo que se pone a cero desaparece de los disponibles de S4T y del cliente.
- Lo que se añade aparece como disponible y se puede reservar para un pedido.

## Preguntas abiertas (para Isaac, antes de la 1.6.0)

1. **¿Quién puede poner a cero o añadir?**
   - ¿Cualquier operario con tarjeta, o solo los jefes?
   - Propuesta: los botones solo salen si la tarjeta es de un jefe (grupo nuevo «KOROSHI Contenedores: ajustar
     stock» o el de productividad).
2. **Límite**: ¿un ajuste grande (por ejemplo, más de 20 uds) pide una segunda tarjeta o se avisa a alguien?
3. **S4T / cliente**: ¿estos ajustes se tienen que comunicar?
   - ¿S4T saca el stock de Odoo o lleva el suyo?
   - Si lleva el suyo, cada ajuste lo descuadra.
4. **Reservadas**: ¿bloquear como propone el diseño, o dejar poner a cero y que el pedido se quede sin
   disponibilidad, con aviso?
5. **Informe**: ¿hace falta una lista diaria de ajustes (quién, contenedor, producto, ±uds) para los jefes?

## Pruebas previstas

**1.5.0**:

- En un hueco de prueba con contenedores vacíos y llenos: marcar vacíos, archivar y comprobar que los llenos siguen.
- Marcar un lleno + Archivar: tiene que negarse.
- Marcar dos llenos + Mover a otro hueco: comprobar que las reservas de un OUT siguen en su sitio (leer el OUT, sin
  validar).
- En la PDA real: tamaño de las casillas y que leer un contenedor mientras se ve el hueco no pierda la lectura.

**1.6.0**:

- Primero en una copia de la base de datos, no en producción: ajuste a cero, ajuste +n, el movimiento que crea, y
  que con reservas se niegue.
- En producción, solo con un contenedor real ya revisado a mano por un jefe.

## Despliegue

Cada versión por separado, con su etiqueta y ZIP (`empaquetar.py`) e instalada con `desplegar.sh`, una a la vez:

- **1.5.0**: actualizar el módulo. No hay campos nuevos.
- **1.6.0**: actualizar el módulo, porque cambia la selección de `accion`.

Fuera de horas de trabajo (actualizar saca las sesiones unos minutos).
