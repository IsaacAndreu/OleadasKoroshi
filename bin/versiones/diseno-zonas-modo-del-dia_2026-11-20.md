# Picking por zonas o agrupaciones: modo del día, estimación y orden (20/11/2026)

Sesión «Zonas: mejorar» (koroshi_zonas). Encargo: punto 5 de `plan-grabaciones-29-30_2026-11-20.md` (grabación del
almacén, 20/11). **Solo diseño: no se ha tocado código ni datos.** Va con el diseño del tablero
(`diseno-tablero-responsable_2026-11-19_v5.md`, sesión «Tablero del responsable»), que ya resuelve la mitad.

Lo que pide Isaac:

1. Dar trabajo por **zona o agrupación**, nunca pedido a pedido (con 200 o 2.000 pedidos no se pueden poner uno a uno).
2. Un **botón para elegir cada día «tradicional» o «zonas»**, con una estimación del tiempo de cada uno a partir de
   la producción, que se vaya afinando.
3. Cuando un operario acaba, **coge la siguiente libre** según las unidades (la de 50 acaba antes y coge otra; si la
   3 tiene 20, que coja la 3 y la 4) y según la **prioridad de las tiendas**: número S4T más bajo primero.

## 0. Cómo está hoy (20/11)

- koroshi_zonas 1.6.0 instalada en sombra (19/11 12:10). **Ensayo de hoy: BIEN, sin fallos**, y la comparación con el
  cron 202 IGUAL (1.233 líneas, 0 distintas). Era la condición para pasar a real.
- Hoy solo había 2 OUT para zonas (2.283 uds) y **37 pedidos de menos de 15 uds** que zonas salta (`MIN_UDS_PEDIDO`):
  esos van hoy en tradicional, una OUT cada uno. Es justo el caso «si la 3 tiene 20, que coja la 3 y la 4».
- El tablero (v5) ya hace:
  - **tarjeta por zona o agrupación**, no por pedido (punto 1);
  - dentro de la tarjeta, **la siguiente OUT libre por el número de CAJA** de la nota (el orden que pone zonas);
  - columna vacía = la siguiente OUT libre de cualquier sitio, como el automático de hoy.
- Las CAJA van por número de pedido S-6665 en cuanto el módulo parta en real (1.6.0). El monitor 1.36.0 ya enseña
  «Siguiente tienda» y «Sacar estas antes».

**Lo que falta, y es de zonas:** el modo del día con su estimación (punto 2) y las agrupaciones del día tradicional,
hechas por número de pedido y juntando los pedidos pequeños (punto 3). Lo de «coge la siguiente» es del tablero.

## 1. Modo del día (punto 2)

En **Inventario > KOROSHI Zonas > Hoy** (pantalla nueva, solo jefes):

| Opción | Qué hace a las 04:50 |
|---|---|
| **Zonas** | Parte por zonas (lo de ahora en real). |
| **Tradicional** | No parte: junta las OUT enteras en agrupaciones por número de pedido (apartado 2). |
| **La más rápida** (por defecto) | Calcula las dos y hace la que acaba antes. Si salen parecidas (< 15 min), zonas, que cierra más cajas. |
| **Esperar** | No hace nada: calcula las dos, las publica y espera a que un jefe pulse el botón. |

- La elección se guarda en la configuración y **vale hasta que se cambie** (no hay que tocarla cada día).
- La pantalla «Hoy» enseña las dos estimaciones con las OUT que hay en ese momento (botón «Calcular», no escribe nada)
  y, si aún no se ha hecho nada hoy, dos botones: **«Partir por zonas ahora»** y **«Agrupar en tradicional ahora»**.
- Las dos estimaciones salen también en el canal a las 04:50, con la elegida:
  «Hoy 2.283 uds · Zonas: acaba 7:47 · Tradicional: acaba 8:30 · Se hace: ZONAS».
- Una vez partido, no se puede cambiar de modo ese día (deshacer un reparto es tocar OUT ya impresas).

### Estimación

Las dos con el mismo modelo de tiempo que ya acierta (19/11: previsto 9:49, real 9:31): 52 s por lectura y 21 s por
lineal nuevo, con las personas de la configuración.

- **Zonas**: la de ahora (la zona más larga con las personas repartidas por trabajo).
- **Tradicional**: cada agrupación es una vuelta entera al almacén (lecturas + todos los lineales que toca). Se simula
  el día: cada persona coge la siguiente agrupación libre al acabar la suya (lo del punto 3) y la hora de fin es la de
  la última. Así «la de 50 acaba antes y coge otra» ya está en la cuenta.

### Afinar con el tiempo

Ya se guarda cada noche el previsto contra real con las lecturas de la PDA (1.5.0). Se añade el **modo** de cada día y,
por modo, el **ritmo real** de los últimos 10 días (uds por persona y hora). La pantalla «Hoy» enseña «ritmo previsto
x1,00 · real últimos 10 días x0,92 (zonas) / x1,05 (tradicional)» y un botón **«Usar el ritmo real»**. No se cambia
solo: lo decide un jefe (un día raro no debe mover la estimación).

## 2. Agrupaciones del día tradicional (punto 3)

En tradicional las OUT **no se parten**: se juntan enteras en agrupaciones, en orden de número de pedido S-6665, hasta
llegar a un mínimo de unidades.

- Recorrer los pedidos de menor a mayor número. Se van metiendo en la agrupación abierta hasta que tiene **al menos
  N uds** (ajuste nuevo, propuesta: 60 uds) o **M OUT** (posiciones del carro, propuesta: 8). Entonces se abre otra.
  - Un pedido de 120 uds va solo en su agrupación.
  - Los de 20 se juntan: la 3 y la 4 (y la 5, si hace falta para llegar al mínimo).
  - Nunca se parte un pedido entre dos agrupaciones.
- **También los días de zonas**: los pedidos de menos de 15 uds que zonas salta (hoy, 37) se juntan igual en
  agrupaciones tradicionales, en vez de ir sueltos.
- Nombre: **`Z-ddmm-T01`, `Z-ddmm-T02`…** (T de tradicional). Con prefijo Z-:
  - la PDA ya prepara las Z- con su carro y las CAJA (`koroshi_preparacion`, `PREFIJOS_ZONA = ('Z-',)`);
  - faltantes y operarios ya las tratan como zona;
  - el monitor las enseña con la zona «T01»;
  - la medición de cajas de zonas las cuenta igual.
  - El tablero tiene que aceptar `T\d+` además de `D\d+` y `MU\d+` en su filtro.
- Nota de cada OUT, igual que en zonas: `Z-2011-T03 | CAJA 02 | K34 ... | PEDIDO S-... | CAJAS n`. La CAJA es la
  posición en el carro, por número de pedido.
- Lo que escribe: crear agrupaciones (`stock.picking.batch`), meter las OUT y la nota. **No parte movimientos ni crea
  OUT**: menos riesgo que zonas. Mismas reglas que zonas: solo PED. TIENDAS de la compañía 8, Preparadas, sin nada
  leído, sin agrupación; Zalando y web nunca.

### Quién coge la siguiente (tablero)

- La **prioridad de una agrupación o zona** es el número de pedido más bajo que lleva. Las agrupaciones T salen ya
  numeradas en ese orden (T01 = los pedidos más antiguos).
- Cuando un operario acaba y su columna está vacía, coge **la siguiente agrupación libre por ese orden** (en tradicional,
  una persona por agrupación: va con su carro). En zonas, la siguiente OUT libre de su zona por CAJA, como en el v5.
- Las unidades no hacen falta como regla aparte: al ser «quien acaba coge la siguiente», la de 50 acaba antes y coge
  otra sola. Lo de juntar las pequeñas ya lo hace la agrupación T.

## 3. Qué módulo lleva cada cosa

| Qué | Módulo | Sesión |
|---|---|---|
| Modo del día, pantalla «Hoy», estimaciones, ritmo real | koroshi_zonas 1.7.0 | Zonas: mejorar |
| Agrupaciones T (tradicional y pedidos pequeños de días de zonas) | koroshi_zonas 1.7.0 | Zonas: mejorar |
| Filtro `T\d+`, siguiente agrupación libre por número de pedido, una persona por T | koroshi_operarios (tablero) | Tablero del responsable |
| Monitor y PDA | sin cambios (ya leen Z- y CAJA) | — |

Campos nuevos solo en tablas propias (`koroshi.zonas.config`, `koroshi.zonas.ejecucion`). Ninguno en `stock.picking`,
`stock.picking.type` ni `stock.move.line`.

## 4. Orden y riesgos

1. **Primero pasar zonas a real** (desactivar el cron 202 y `modo_cron = real`), con el sí de Isaac. El ensayo de hoy
   ha salido bien. Todo lo de este documento necesita el módulo partiendo.
2. Luego la 1.7.0 con el modo del día en **Zonas** (como ahora) y las T solo para los pedidos pequeños. Riesgo bajo:
   solo agrupa OUT enteras que hoy van sueltas.
3. Cuando se vea bien una semana, probar un día en **Tradicional** o **La más rápida**.

Riesgos:
- **La estimación de tradicional no está calibrada**: no hay días medidos con agrupaciones T. Los primeros días, el
  ritmo de tradicional es una suposición (el mismo de zonas). Por eso empiezo por zonas y el ritmo real se enseña,
  no se aplica solo.
- **Nombre `Z-ddmm-T01`**: hay que comprobar que nada de lo que lee Z- (correo y etiquetas de zonas, monitor, faltantes,
  tablero) dé por hecho que la zona es D o MU. Lo reviso antes de escribir código.
- **Una persona por T**: si dos cogen la misma agrupación entera se pisan el carro. El tablero debe darla a una sola.

## 4b. Lo hablado con el Tablero (20/11, su v6)

- El Tablero propuso que zonas sobrescriba un método de operarios (`_orden_lotes_libres`). Contestado que **no**:
  obligaría a koroshi_zonas a depender de koroshi_operarios, y cada actualización de operarios arrastraría a zonas
  (lo que pasó el 20/11 con contenedores y faltantes). El orden lo decide operarios solo, por el nombre:
  - **T\d+**: por el número de pedido más bajo de sus OUT (los dígitos del origin); una persona por T, entera.
  - **D\d+ / MU\d+**: llevan los mismos pedidos; la persona libre va a la zona que acabaría más tarde (más uds
    pendientes por persona). Dentro, OUT a OUT por CAJA.
  - Prioridad primero; a igual prioridad, el nombre. Las uds no son criterio para las T.
- Si el tablero necesita el modo del día: parámetro `koroshi_zonas.modo_dia` = `AAAA-MM-DD:zonas|tradicional`, que
  escribe zonas al partir o agrupar.
- El Tablero lo acepta (su v7): T\d+ en el filtro, una T entera a una persona, prioridad calculada por él desde el
  origin; sin enganche. Isaac: en el tablero no hay modo tradicional con OUT sueltas (columna vacía = siguiente zona o
  agrupación libre). Única condición: la CAJA de la nota de las T en el orden de preparación (lo es: posición del
  carro por número de pedido, y la PDA ordena el carro por CAJA).
- Orden de versiones: operarios 2.23.0 primero (ya con la regla T, que no hace nada hasta que existan), zonas 1.7.0
  después de pasar a real. Las dos con el sí de Isaac.

## 5. Preguntas para Isaac

1. ¿El mínimo de una agrupación tradicional: 60 uds u 8 OUT (lo que llegue antes), u otros números?
2. ¿«La más rápida» por defecto, o prefieres que espere a que un jefe pulse el botón?
3. ¿Juntamos ya en T los pedidos pequeños de los días de zonas (hoy 37 pedidos de menos de 15 uds)?
4. ¿Pasamos zonas a real esta tarde (desactivar el cron 202 y poner el módulo en real)?
