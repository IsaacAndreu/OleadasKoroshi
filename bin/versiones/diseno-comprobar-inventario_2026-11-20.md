# Diseño: comprobar el inventario por referencia en la PDA (e inventario dinámico)

20/11/2026 · v1 · **solo diseño, sin código** · espera el visto bueno de Isaac

## 1. Punto de partida

**El problema (20/11).** Almacén Nath ha hecho ajustes a mano en Odoo («Cantidad de producto actualizada»): 630 uds desde
agosto y 212 en noviembre, sobre todo en cajas KO. Odoo baja, pero S4T sigue contando esas unidades, y KOROSHI pide
prendas que no tenemos. Según `bin/versiones/stock-tiendas-sin-servir-y-ajustes_2026-11-20.xlsx`, esta semana hay
2.615 uds sin servir en 469 referencias. De ellas, 296 están a 0 o en negativo en Odoo, y 249 tienen stock quitado a
mano. Un ejemplo: la 2622JA00-000003-L tiene 55 uds pedidas, 11 quitadas el 20/10 en L128 P15 C2/KO_240926_025 y
stock 0.

**Lo que pide Isaac.**
1. Cuando KOROSHI diga «la prenda X no está», alguien va con la PDA y revisa todas las ubicaciones y contenedores de
   esa referencia (todas las tallas y colores). Luego apunta lo que hay de verdad.
2. Si coincide, queda constancia de que se ha comprobado. Si no coincide, queda la diferencia con quién y cuándo, y
   se corrige bien, no con un «Cambiar cantidad» suelto.
3. Que estas comprobaciones vayan cubriendo el almacén poco a poco, sin cerrar para inventariar: el **inventario
   dinámico**.

**Lo que ya existe (revisado en el código).**
- **koroshi_contenedores 1.9.1.**
  - El buscador por referencia da las variantes con su stock, pero hay que abrirlas una a una
    (`controllers/main.py:554`). `_donde` (`main.py:330`) da hueco y contenedor de un solo artículo.
  - «Poner a cero», «Añadir prendas» y «Cambiar cantidad» son ajustes contra pérdidas de inventario
    (`_ajuste`, `main.py:228`) y se apuntan en `koroshi.contenedor.movimiento` con quién y cuándo. Funcionan, pero
    cada uno es un ajuste suelto: nadie revisa la referencia entera ni lo compara con nada.
- **koroshi_faltantes 1.8.1.** Faltante de picking → FALTANTE → ronda INT → encontrado o pérdidas. Está pensado para
  la reserva de una OUT, no para contar.
- **Tarjeta de operario compartida** (operarios 2.22.1): Contenedores, Lecturas y Faltante ya saben quién es.
- **Propuesta de la sesión «Pedidos web: respuesta a KOROSHI 20/11».**
  - Fase 1: pantalla «Referencia» de solo lectura (graella color × talla y cajas en orden de recorrido).
  - Fase 2: recuento en un módulo nuevo, `koroshi_recuentos`, con «Aplicar ajuste» solo para jefes.
  - Este diseño la recoge y la amplía con la corrección, el aviso a S4T y KOROSHI, y el inventario dinámico.

## 2. Qué módulo: uno nuevo, `koroshi_recuentos`

| Opción | A favor | En contra |
|---|---|---|
| Extender koroshi_contenedores | Ya tiene el buscador, la pantalla y `_ajuste` | La PDA lo usa todo el día para compactar; lo tiene otra sesión; mezclaría mover con contar |
| Extender koroshi_faltantes | Ya tiene rondas y estados | Va atado a la reserva de las OUT y a Lecturas (preparación); otro concepto |
| **Nuevo `koroshi_recuentos`** | No toca nada de lo que usa la PDA hoy; sus propias tablas; se instala y se apaga solo | Hay que repetir la búsqueda de artículo y el movimiento de ajuste |

**Propuesta:** módulo nuevo, también para la fase 1 (la pantalla «Referencia»). Así no hay que coger Contenedores.
- **Depende de:** `koroshi_base` (compañía, hora del almacén, rangos de días), `koroshi_operarios` (tarjeta) y `stock`.
- **Tablas:** solo las suyas. **Ningún campo nuevo** en `stock.picking`, `stock.picking.type` ni `stock.move.line`
  (regla 7).
- **Movimiento de ajuste:** el mismo que `koroshi_contenedores._ajuste` y `koroshi_faltantes._mover`, ya probado en
  producción: un `stock.move` hecho contra la ubicación de pérdidas de inventario del artículo. Lo único que cambia es
  el nombre: `REC/000123 2621XC04`. Cuando haya un tercer uso, se sube a `koroshi_base` (regla 8), en su propia versión.
- **En la PDA:** un botón «Recuentos» en el área «Extra» de la entrada única (o en «Gestión», si solo cuentan jefes).
  El tiempo cuenta en Actividades como «Recuento».

## 3. Cómo se registra cada comprobación

### 3.1 Modelos (propios)

**`koroshi.recuento`**: una comprobación de una referencia (el modelo, p. ej. `2621XC04`, con todas sus variantes).

| Campo | Para qué |
|---|---|
| `name` | REC/000123 |
| `referencia` | Modelo (`2621XC04`); las variantes salen del nombre, porque 9.116 artículos no tienen referencia interna |
| `motivo` | Reclamación KOROSHI / Ajuste a mano / Faltante / Stock negativo / Rotación / A mano |
| `nota` | P. ej. «KOROSHI: la tienda SL no recibe la talla L» |
| `estado` | Pendiente → Contando → Contado → **Coincide** o **Con diferencias** → Revisado → Aplicado |
| `empleado_id`, `inicio`, `fin` | Quién cuenta (tarjeta) y cuándo |
| `revisado_por`, `fecha_aplicado` | Quién da por buena la diferencia (jefe) y cuándo |

**`koroshi.recuento.linea`**: una por ubicación (hueco o contenedor) × variante.

| Campo | Para qué |
|---|---|
| `ubicacion_id` (contenedor o hueco), `hueco` | Dónde |
| `producto_id` | Variante (color / talla) |
| `odoo` | Lo que dice Odoo **en el momento de cerrar esa caja**, no al empezar (ver 3.3) |
| `en_curso` | Uds ya leídas en OUT sin validar desde esa ubicación (físicamente ya no están) |
| `contado` | Lo que hay de verdad |
| `diferencia` | `contado − (odoo − en_curso)` |
| `estado_ubicacion` | Contada / Vacía / La ubicación no existe / Encontrada fuera de lista |
| `empleado_id`, `fecha` | Quién y cuándo, por caja |
| `move_id` | El ajuste, cuando se aplica |

**`koroshi.recuento.comprobado`** (o una vista agregada sobre las líneas): **la última comprobación** de cada
(ubicación, variante), con su fecha y su resultado. Es la «constancia» que pide Isaac y la base del inventario dinámico
(punto 5).

### 3.2 En la PDA (fase 2)

1. Se lee o se escribe la referencia (`2621XC04`), o se toca una de la lista «Para contar hoy». Hay que tener puesta
   la tarjeta de operario.
2. Sale la **lista de sitios en orden de recorrido** (L73 → L76…, P y C):
   - todas las ubicaciones donde Odoo tiene stock de alguna variante;
   - **más las ubicaciones donde se quitó stock a mano en los últimos 90 días**, aunque Odoo diga 0. Es justo donde
     puede estar lo que falta (en el Excel, «Ubicación del ajuste»);
   - más FALTANTE y DEVOLUCIO_KOROSHI, si tienen algo de esa referencia.
3. En cada sitio se lee el hueco o el contenedor y después **cada prenda** (EAN). «Cantidad» sirve para paquetes
   cerrados. La pantalla:
   - va contando por color y talla;
   - pita si una prenda no es de la referencia (no se cuenta, pero se puede apuntar como «fuera de sitio»);
   - con «Caja hecha», pasa a la siguiente; con «Vacía», a 0; con «No existe», marca el sitio.
4. **«Encontrada en otro sitio»:** si al pasar se ve la referencia en un hueco que no está en la lista, se lee ese
   hueco y se cuenta igual. Queda como línea nueva con Odoo = 0.
5. «Terminar». Si todo coincide, el estado pasa a **Coincide** sin que nadie haga nada más. Si no, a **Con
   diferencias**, y avisa al jefe en la bandeja del encargado (koroshi_menu, más adelante).

**Conteo ciego (recomendado):** el operario no ve la cifra de Odoo mientras cuenta, solo lo que lleva leído. Si la ve,
tiende a «encontrar» lo que espera. Al terminar sí ve el resultado.

**La fase 2 no toca el stock.** Solo apunta.

### 3.3 Contar mientras se trabaja (sin cerrar el almacén)

El picking no se para, así que la foto de Odoo no puede ser la del principio:
- `odoo` se lee **al pulsar «Caja hecha»**, solo de esa caja (un momento, no una hora);
- `en_curso` descuenta las prendas leídas en OUT todavía sin validar desde esa caja: Odoo aún las tiene, pero ya
  están en el carro;
- si mientras se cuenta una caja se valida una OUT que sale de ella, la línea queda **«Recontar»** y la pantalla pide
  leer la caja otra vez. No se adivina.
- La lista del día evita los huecos de las zonas que se están preparando en ese momento (koroshi_zonas), o los deja
  para el final.

## 4. Cómo se corrige la diferencia y cómo se avisa

### 4.1 Revisar (oficina o jefe, fase 3)

Una pantalla por recuento con la graella color × talla:
- Odoo, contado y diferencia;
- **diferencia neta por variante**: la suma de todas las ubicaciones;
- debajo, el detalle por caja.

Antes de aplicar se separan dos casos:

| Caso | Ejemplo | Qué se hace |
|---|---|---|
| **Está, pero en otra caja** | −2 en KO_A y +2 en KO_B, misma variante; neto 0 | **Traslado interno** de A a B (como mover prendas). No cambia el total: S4T y KOROSHI no se enteran, porque no hace falta |
| **Falta o sobra de verdad** | Neto −11 (2622JA00-000003-L) | **Ajuste** contra pérdidas de inventario, `REC/000123 2621XC04`, una línea por caja |

**Reconteo de confirmación (opcional, recomendado si la diferencia neta es de más de 3 uds o de más del 20 %):**
- el jefe pulsa «Recontar» y la referencia vuelve a la lista de hoy, pero solo con las cajas que no cuadran, para
  **otra persona**;
- si el segundo conteo da lo mismo que el primero, se aplica;
- si da otra cosa, lo mira el jefe.

**Reservas de OUT.** Si en una caja se cuentan menos prendas de las que hay reservadas para una OUT:
- esa línea **no se aplica sola**;
- la pantalla dice qué OUT es y se resuelve con Faltante (cambiar la reserva a otra caja);
- igual que hoy en «Cambiar cantidad», que no deja bajar de lo reservado (`main.py:433`).

**Aplicar:** solo jefes (grupo de koroshi_menu). Crea los traslados y ajustes, guarda el `move_id` en cada línea y deja
el recuento en «Aplicado», con quién y cuándo. Es todo o nada (savepoint), como en Faltantes.

### 4.2 Avisar a S4T y a KOROSHI

S4T no se entera de los ajustes de Odoo: por eso pide prendas que no hay. Hasta donde sabemos, el módulo S4T de
Effective solo hace batch-update de pedidos y no tiene un endpoint de stock (memoria del 12/11).

**Propuesta sin API (fase 3):**
- **Acta de recuento** en Excel:
  - una fila por variante con diferencia neta: EAN, referencia, Odoo antes, contado, diferencia, fecha, quién;
  - y otra hoja con las referencias que **coinciden**, para decir «comprobado: no hay».
- Se manda un correo **diario a las 16:00** (después del camión) a una lista en un parámetro
  (`koroshi_recuentos.destinatarios`). Si un día no hay recuentos, no sale.
- KOROSHI (o S4T) ajusta su teórico con el acta y deja de pedir lo que no hay.
- Si S4T tiene o tendrá un endpoint de ajuste de stock, el acta pasa a mandarse sola, como `koroshi_s4t_envios`.
  **Pregunta para S4T.**

**Lo que no se arregla con el recuento:** el agujero lo hacen los ajustes a mano sin rastro. Mientras Almacén Nath
pueda tocar «Cantidad de producto actualizada» en Odoo, seguirán saliendo. Proponemos (fuera de este módulo, cada uno
en su versión):
- **Quitar a Almacén Nath el permiso** de ajustar cantidades a mano en Inventario. Es configuración de grupos, no
  código; lo decide Isaac.
- **En Contenedores**, cada «Cambiar cantidad» o «Poner a cero» que baje stock **crea un recuento pendiente** de esa
  referencia (motivo «Ajuste a mano»): el ajuste sigue, pero alguien lo comprueba. Sería una versión de
  koroshi_contenedores, que hoy tiene otra sesión.

## 5. Inventario dinámico: qué toca contar cada día

### 5.1 La lista «Para contar hoy»

Un cron a las 05:30 (hora del almacén) prepara la lista del día con un **tope** (parámetro: p. ej. 20 referencias, o
unos 60 min de una persona). Se cuenta en las horas flojas: después de las tiendas (13:00) y del camión (15:00). La
lista se ve en la PDA y en la oficina, y el jefe puede subir o quitar referencias.

**Prioridad (de más a menos):**

| # | Motivo | De dónde sale | Por qué |
|---|---|---|---|
| 1 | **Reclamación de KOROSHI** | Se apunta a mano o se pega una lista (Excel) | Hay una tienda esperando: hoy mismo |
| 2 | **Pedida y sin stock en Odoo** | Pedidos de tiendas sin servir ni reservar, con stock ≤ 0 (lo del Excel del 20/11, automático) | Es lo que KOROSHI va a reclamar mañana |
| 3 | **Stock negativo, o reservado > stock** | `stock.quant` | Odoo está mal seguro |
| 4 | **Ajuste a mano sin recuento posterior** | «Cantidad de producto actualizada», «Cambiar cantidad», «Poner a cero», «Puestos a 0» | Es el agujero del 20/11: 249 referencias |
| 5 | **Faltante «No encontrado»** | koroshi.faltante | Pasó a pérdidas: ¿está en otro sitio? |
| 6 | **Rotación A/B/C** | Uds servidas en los últimos 90 días: A = el 20 % de referencias que más salen (cada 30 días), B (cada 60), C (cada 120) | Lo que más sale es lo que más falla y más duele |
| 7 | **La más antigua sin comprobar** | `koroshi.recuento.comprobado` | Para cubrir todo el almacén |

Una referencia comprobada hace menos de 7 días no vuelve a la lista por los motivos 4 a 7.

### 5.2 Cuánto se tarda en cubrir el almacén

Hay que medirlo con los primeros recuentos de verdad. Para hacerse una idea: si una referencia con 2-4 cajas son unos
5 minutos, 20 referencias al día son unos 100 minutos de una persona. Con unas 5.000 referencias con stock, el motivo 7
tardaría meses. Por eso la rotación (motivo 6) es la que tiene que llevar el peso: las A se cubren cada mes, y las C
casi no salen, así que su error importa menos.

**Más adelante (otra fase, otro módulo):**
- **«Contar al vaciar»:** cuando una OUT deja un hueco o una caja a 0 según Odoo, Lecturas pregunta al que prepara
  «¿queda algo?». Es un recuento gratis, porque ya está delante. Toca koroshi_preparacion.

### 5.3 Cómo se ve si va bien

Un informe semanal (por correo, con koroshi_informe o en su propio cron):
- referencias y cajas comprobadas;
- **% que coincide** (la exactitud del inventario);
- uds ajustadas (+ y −) y traslados;
- **cobertura**: el % de uds del almacén comprobadas en los últimos 90 días, en total y en las A;
- reclamaciones de KOROSHI: cuántas había stock de verdad y cuántas no.

## 6. Fases (cada una, su versión y el sí de Isaac)

| Fase | Qué | Toca el stock |
|---|---|---|
| **1** | `koroshi_recuentos` 1.0.0: pantalla «Referencia» en la PDA (solo lectura). Graella color × talla con lo que dice Odoo y las cajas en orden de recorrido, incluidos los sitios con ajustes a mano recientes. Tocar una caja da su contenido | No |
| **2** | Recuento por referencia (punto 3): se registra, a ciegas; pantalla de oficina con la comparación; las que coinciden quedan comprobadas | No |
| **3** | Revisar y aplicar (punto 4.1), reconteo de confirmación y acta para KOROSHI y S4T (4.2) | **Sí** (solo jefes) |
| **4** | Lista «Para contar hoy» con prioridades, cobertura e informe semanal (punto 5) | No |
| Aparte | Contenedores: «Cambiar cantidad» crea un recuento pendiente · permisos de Almacén Nath · «Contar al vaciar» en Lecturas | — |

**Cómo se probará:**
- fases 1 y 2: en producción, con una referencia de la lista del 20/11, porque solo leen y apuntan;
- fase 3: primero con una referencia de prueba, con una diferencia preparada, y el ajuste deshecho a mano después;
- en una PDA real: la lectura caja a caja, el pitido de una prenda de otra referencia y «Recontar» si se valida una
  OUT de esa caja mientras se cuenta.

## 7. Preguntas para Isaac

1. **¿Módulo nuevo `koroshi_recuentos` para todo, también la fase 1?** (Recomendado: así no se coge Contenedores.)
2. **¿Conteo ciego?** El operario no ve lo que dice Odoo hasta terminar. (Recomendado: sí.)
3. **¿Quién aplica las diferencias?** Solo jefes desde la oficina, después de revisar (recomendado). Otra opción: que
   las de 1 ud se apliquen solas.
4. **¿S4T acepta ajustes de stock** (una API, o que KOROSHI los meta con el acta) o solo por correo? ¿A quién va el acta?
5. **¿Cuánto tiempo al día** se puede dedicar a contar, y quién? (Para el tope de la lista.)
6. **¿Quitamos a Almacén Nath el ajuste de cantidades a mano** en Odoo?
