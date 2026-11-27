# Inventario dinámico en Lecturas: diseño v1 (26/11/2026)

Encargo de Isaac (26/11): cuando un operario coge prendas de una ubicación donde, según Odoo, quedan menos de 3 uds, la
PDA pregunta cuántas quedan (botones 3, 2, 1, 0). Si no coincide, no se ajusta nada: se apunta (operario, ubicación,
SKU, Odoo, operario) y se revisa en la ronda de faltantes. Origen: `20261126_investigacion-faltantes_v1.md` (73 % de las
cancelaciones de tienda = SKU con las últimas 1–3 uds dadas de baja a mano, sin nombre).

**Nada hecho aún.** Espera el sí de Isaac y los dos módulos libres.

## Toca dos módulos

| Módulo | Quién lo tiene (TABLERO 26/11) | Qué cambia |
|---|---|---|
| `koroshi_faltantes` 1.12.0 → **1.13.0** | «Investigación faltantes» (1.12.0 sin instalar, commit a1d8d97; lo suelta para esto en cuanto Isaac dé el sí) | tipo «recuento», 4 campos propios, 2 botones de revisión, filtro |
| `koroshi_preparacion` 3.37.0 → **3.38.0** | «Caja llena / soltar pedido» (3.37.0 sin instalar) | pregunta en la PDA, ruta nueva, parámetro |

Orden de instalación: faltantes 1.13.0 **antes** que preparación 3.38.0 (preparación ya depende de faltantes). Si
preparación llega antes, no rompe: solo apunta el recuento en su registro de lecturas y no crea el faltante.

Ningún campo nuevo en `stock.picking`, `stock.picking.type` ni `stock.move.line` (regla 7). Todo va en
`koroshi.faltante` y `koroshi.preparacion.lectura`, que son tablas propias.

## 1. Cuándo sale la pregunta

**Qué es «lo que dice Odoo»**: lo que debería quedar físicamente en el hueco cuando el operario se va.

    queda_odoo = cantidad del quant (SKU, ubicación)
               − uds ya leídas (qty_done) en cualquier OUT/INT abierta de ese SKU y ubicación   ← ya no están en el hueco
               − uds que le faltan por leer a esta pantalla de ese SKU y ubicación               ← (0 al acabar la línea)

Lo reservado para otras OUT **sigue en el hueco** (aún no lo ha cogido nadie), así que entra en `queda_odoo`. Se calcula
aparte (`reservado_otras` = pedidas − leídas de las otras líneas abiertas) para la revisión: si el operario dice menos
que eso, otra OUT va a fallar en ese hueco → sale la primera en la lista.

**Sale cuando** se completa la última línea de la pantalla de ese SKU en esa ubicación (en una agrupación, la última de
las tiendas) y `0 < queda_odoo < umbral`.

**No sale**:
- si Odoo ya dice 0 (pedido de Isaac: no frenar);
- en la ronda de faltantes (INT «RONDA FALTANTES») ni si la ubicación es FALTANTE, pérdidas o no interna;
- si esa ubicación y SKU ya se han contado hoy (cualquier operario): una vez por hueco y día. Evita que diez OUT
  seguidas del mismo hueco pregunten diez veces;
- con el umbral a 0 (apagado).

**Parámetro**: `koroshi_preparacion.recuento_umbral` = 3 (se crea al actualizar; 0 = apagado). Los botones van de
`umbral` a 0; el de arriba dice «3 o más».

**Cómo lo sabe la PDA sin esperar**: la carga entera de Lecturas trae en cada línea `queda_odoo` (sin lo de esta
pantalla) y `recontado_hoy`. Son dos consultas agrupadas más (quants y move lines abiertas de los SKU de la pantalla),
solo en la carga entera, no en la ligera de cada lectura. La PDA decide sola al leer, como ya hace con «Caja llena».
El servidor vuelve a calcular `queda_odoo` al recibir la respuesta, y es el dato que se guarda.

## 2. Que no frene el picking

- Una franja con 4 botones grandes, como la de «Caja llena» (`static/src/xml/preparacion.xml:50-53`), no una hoja que
  tape la pantalla. Texto: «L12-03-B · 2611XC04 M — ¿Cuántas quedan en el hueco?». Un toque y se va.
- **Si lee otra prenda sin contestar, la pregunta se va y no se apunta nada.** Nunca bloquea la lectura.
- La respuesta se manda sin esperar (como `/koroshi/preparacion/caja_llena`): si no hay red, se pierde sin avisar.
- Sonido corto distinto (el de aviso suave), no el de error.

## 3. Dónde se guarda

- **Todas las respuestas** (cuadren o no) → `koroshi.preparacion.lectura`, tipo nuevo `recuento`, con ubicación, SKU,
  Odoo y operario. Es el «inventario de todo»: se ve qué huecos se han contado y cuándo, sin llenar Faltantes.
- **Solo las diferencias** → `koroshi.faltante` con `tipo = 'recuento'`:
  - `employee_id` = operario de la tarjeta; `user_id` el de la PDA; `product_id`; `ubicacion_vieja_id` = el hueco;
  - campos nuevos en `koroshi.faltante`: `recuento_odoo`, `recuento_operario`, `recuento_reservado` (lo de otras OUT),
    `recuento_out` (texto con la OUT; **no** `picking_id`);
  - `cantidad` = diferencia (Odoo − operario; negativa si sobra), `cantidad_faltant` = 0 (no se ha movido nada).

Por qué `picking_id` vacío y `cantidad_faltant` = 0 (comprobado en el código):
- `koroshi_kpi/models/falta.py:137-140` suma la `cantidad` de los faltantes con `picking_id` como «no cogido»: un
  recuento con OUT inflaría el KPI.
- `crear_ronda` (`faltante.py:672-674`) y Prenda en el suelo (`koroshi_prenda_suelo/models/prenda.py:163-166`) solo
  cogen `cantidad_faltant > 0`: no meten un recuento en una INT ni lo ofrecen para devolver.
- «No encontrado» (`faltante.py:601-614`) no mueve nada con `cantidad_faltant` = 0.
- El % de faltante (`models/relativo.py`) no lee `koroshi.faltante`: no cambia.

## 4. Cómo entra en la ronda

En «Revisión de faltantes» (José Luis) sale con el filtro nuevo **«Recuentos»** y en la bandeja de pendientes (la
bandeja ya cuenta todos los pendientes; en rojo a los 3 días). Columnas: hueco, SKU, Odoo, operario, reservado otras
OUT, quién y cuándo. Orden: primero los que dejan sin servir otra OUT (operario < reservado).

José Luis va al hueco, cuenta y elige (botones solo para responsables, como Encontrado/No encontrado):

| Botón | Cuándo | Qué hace |
|---|---|---|
| **Odoo tiene razón** | hay lo que dice Odoo | estado `encontrado`, nada se mueve |
| **Pasar a FALTANTE** (pide cuántas faltan, por defecto Odoo − operario) | falta stock | mueve esas uds del hueco a FALTANTE con su nombre (como `_sin_alternativa`); queda `pendiente` con `cantidad_faltant` > 0 y desde ahí es un faltante normal: entra en la siguiente ronda y, si no aparece, «No encontrado» lo lleva a pérdidas |
| **No encontrado** (ya existe) | | igual que hoy |

Si **sobra** (operario > Odoo) no hay botón de alta: se cierra con nota y el ajuste lo hace el responsable a mano. Es
la señal de las bajas a 0 falsas de la investigación (98 quants negativos).

## 5. Lo que no hace

- No ajusta stock en la PDA nunca.
- No pregunta en huecos con 3 o más ni con 0.
- No cuenta las uds en otras ubicaciones del mismo SKU.

## 6. Qué habrá que probar en una PDA real (prueba reversible: leer y deshacer, sin cerrar cajas ni validar)

1. OUT con una línea de un hueco que quede en 1–2: al leer la última ud sale la franja; tocar «1» → franja fuera,
   lectura sigue. Deshacer la lectura.
2. Mismo caso, leer otra prenda sin contestar → la franja se va, nada apuntado.
3. Hueco que se queda en 0 o en ≥ 3 → no sale.
4. Agrupación con el mismo SKU para 2 tiendas en el hueco → sale una vez, al acabar la segunda.
5. Segunda OUT del mismo hueco el mismo día → no vuelve a salir.
6. Respuesta distinta de Odoo → aparece en «Revisión de faltantes › Recuentos» con el nombre del operario; ni la OUT ni
   el KPI cambian.
7. Tiempo de la carga entera de Lecturas antes y después (log), por las dos consultas nuevas.

## Preguntas para Isaac

1. ¿Umbral 3 y «una vez por hueco y día»? (alternativa: preguntar siempre, más datos y más toques).
2. ¿Guardar también los que cuadran solo en el registro de lecturas (propuesto) o como faltante cerrado?
3. Si sobra, ¿basta con nota o quieres botón de alta?
4. ¿Me pasas `koroshi_faltantes` y `koroshi_preparacion` (los tienen «Investigación faltantes» y «Caja llena / soltar
   pedido»)?
