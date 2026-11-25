# Diseño: «Juntar cajas» en la PDA (área Expediciones) — 25/11/2026, v1

Solo diseño: no hay código. Espera el visto bueno de Isaac.

## Qué piden

El almacén quiere poder **juntar cajas (matrículas CJ)** desde la PDA: meter una caja pequeña dentro de otra del
mismo pedido y la misma tienda, para que salga un bulto menos. Hoy solo se puede desde el PC, en la ficha del pedido
(pestaña «Juntar cajas», acción de servidor 1844 v5).

También desatasca el sync a S4T. El cron 186 (acción 1800 v6.6) no pasa a READY un pedido de tienda que tiene una caja
pequeña sin juntar, mientras no tenga etiqueta. Ejemplo: el 24/11 la K40 S-6665004742 esperaba por la CJ665013630
(1 ud) y hubo que mandarla a mano con la acción 1960.

## Lo que ya existe (leído el 25/11)

- **Acción 1844 v5**, «Juntar matrículas», en producción desde el 19/11
  (`bin/versiones/20261119_accion-1844_juntar-matriculas_v5-APLICADA-produccion.py`). Se probó en S-6665004426. Hace
  todo el trabajo:
  - comprueba que las dos CJ existen, que la pequeña no está vacía, que son del mismo pedido y la misma tienda, y
    que son de la compañía 8;
  - si son de OUT distintas, la OUT de la caja pequeña tiene que estar validada;
  - mueve las líneas a la CJ destino. Si son de la misma OUT, mueve también los quants; si son de OUT distintas, Odoo
    mueve el stock al escribir la línea validada;
  - comprueba que los bultos del pedido bajan exactamente en el número de cajas juntadas. Si no, lo deshace todo;
  - recalcula `number_of_packages` de las OUT del pedido. Cada caja cuenta en la OUT que lleva más uds;
  - deja una nota en el pedido y en las OUT.
- **PDA por áreas** (`koroshi_actividades`): cada botón es un `koroshi.actividad` con `area` y `abre` (la pantalla que
  se abre). El área Expediciones ya tiene «Cargar camión», «Montar cajas» y «Meter en caja lo de expediciones».
- **`koroshi_base.pda`**: permiso (`comprobar_grupo`), tarjeta de operario (`empleado_valido`) y lector, los mismos
  que en Lecturas, Contenedores, Devoluciones y Recuentos.
- **`koroshi_s4t_envios` 1.4**: si los bultos de un envío ya mandado cambian antes del cierre del camión, el envío
  pasa a «corregir» y se reenvía con «Reenviar». Si el camión ya está cerrado, solo deja una nota.

## Propuesta

### Dónde

Un **módulo nuevo y pequeño, `koroshi_juntar_cajas`**, con una pantalla para la PDA y un botón nuevo en el área
**Expediciones**: «Juntar cajas». La actividad se crea con el módulo y abre su pantalla.

- No va en Lecturas (`koroshi_preparacion`): es la pantalla de todo el día, y allí ya existe «mover caja» con la OUT
  sin validar. Juntar se hace sobre todo en el muelle, con las OUT ya validadas.
- No añade campos a `stock.picking`, `stock.picking.type` ni `stock.move.line` (regla 7). Solo su tabla de registro
  (`koroshi.juntar.registro`) y la actividad.
- Depende de `koroshi_base`, `koroshi_actividades` y `sale_stock`. Es un módulo nuevo: se instala sin actualizar
  ningún otro.

### La lógica

La de la acción 1844 v5 pasa al módulo **tal cual** (`logica.py` + modelo), con tests sin Odoo como en
`koroshi_recuentos`. La acción 1844 sigue igual para el PC. Cuando el módulo esté probado, el botón del pedido puede
llamar al módulo, para que haya una sola lógica.

### La pantalla (PDA)

1. **Tarjeta** del operario: la misma que en el resto de pantallas, guardada 60 min.
2. **Leer la CJ pequeña.** La pantalla enseña la tienda, el pedido, las uds, la zona y si la OUT está validada. Se
   pueden leer varias seguidas.
3. **Leer la CJ destino.** La pantalla enseña:
   > K40 – PALENCIA · S-6665004742
   > CJ665013630 (1 ud, MU2) → CJ665013613 (25 uds, D1)
   > Bultos del pedido: 2 → 1
4. **«Juntar».** El botón queda bloqueado hasta la respuesta y lleva un token, contra el doble toque. Al acabar sale
   «Hecho: 2 → 1 bultos. Quita la etiqueta de la CJ665013630», o el motivo por el que no se ha hecho; en ese caso no
   se ha cambiado nada.
5. **«Otra»** vuelve al paso 2 con la tarjeta puesta.

Sin «Juntar», leer solo la CJ destino enseña las cajas pequeñas del pedido: es la propuesta que hoy da la acción 1844
sin parejas.

### Comprobaciones que se añaden a las de la 1844

| Caso | Qué hace |
|---|---|
| Pedido **SHIPPED** en S4T, o alguna de sus OUT en un **cierre de camión ya enviado** | **No deja**: la mercancía ya ha salido |
| Pedido con **etiqueta del transportista** hecha y camión sin cerrar | Deja, pero **avisa en rojo**: «Hay que rehacer la etiqueta de XPO/GLS: el transportista tiene N bultos y ahora son N-1». Nota en el pedido. `koroshi_s4t_envios` pone el envío en «corregir» |
| Pedido de **Zalando** | **No deja** (Zalando no se toca) |
| Caja pequeña de una **OUT sin validar** de otra OUT | Como la 1844: «Valida antes la OUT» |
| Las dos CJ iguales, de pedidos o tiendas distintas, o vacías | Como la 1844: no deja, con el motivo |

### Registro

Cada vez que se junta, una línea en `koroshi.juntar.registro`: quién (tarjeta), cuándo, la CJ pequeña, la CJ destino,
el pedido, las uds, los bultos antes y después, y los ids de líneas y quants movidos, para deshacer.

- La oficina lo ve en KOROSHI > Expediciones > Cajas juntadas.
- No hay botón de deshacer en la PDA: se deshace en la oficina con los ids guardados.

## Lo que no hace (v1)

- **Partir una caja** (`diseno-revisar-box-partir_2026-11-19.md`, preguntas P1-P5): queda para más adelante, en la
  misma pantalla.
- Rehacer la etiqueta del transportista: solo avisa.
- Reenviar a S4T: lo hace `koroshi_s4t_envios` (corregir + Reenviar), como ahora.

## Preguntas para Isaac (y almacén)

- **J1.** ¿Quién lo usa: cualquiera con tarjeta, o solo los de expediciones y los jefes? Propuesta: cualquiera con
  tarjeta; queda registrado quién.
- **J2.** Si el pedido ya tiene etiqueta del transportista: ¿avisar y dejar (propuesta), o no dejar y que lo haga la
  oficina?
- **J3.** ¿La caja pequeña es solo la de **3 uds o menos** (como la 1844 y el sync), o cualquier caja?
  Propuesta: cualquiera, avisando si la «pequeña» es más grande que la destino.
- **J4.** ¿Se imprime algo al juntar (por ejemplo, la etiqueta de la CJ destino otra vez)? Propuesta: no.

## Antes de programar

1. Visto bueno de Isaac a este diseño y a J1-J4.
2. Tests de la lógica sin Odoo (los casos de la tabla y los de la 1844).
3. Probar en producción solo leyendo: la propuesta de cajas pequeñas de un pedido real.
4. Primera junta real con una caja de prueba, fuera de horas y con el sí de Isaac.
5. Probar en una PDA: tarjeta, leer CJ con el lector, el doble toque y el aviso de la etiqueta.
