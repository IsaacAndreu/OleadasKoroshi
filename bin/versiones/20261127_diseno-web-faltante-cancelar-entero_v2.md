# Pedido web con faltante en picking: cancelarlo entero y mandar lo cogido a reubicar. Diseño v2 (27/11/2026)

Sustituye a `20261127_diseno-web-faltante-cancelar-entero.md` (v1). La v1 decía que la PDA no interviene en las
web, y **eso era falso**: se cogen con una INT por agrupación que sí hace la PDA. Sin código; espera el visto bueno.

Encargo de Isaac (27/11):
- «los pedidos de web quan estan fent picking y no hi ha 100 % se deberia cancelar cuando le den a faltante ese pedido»;
- y después: «esas prendas estarían cogidas, así que habría que mandarlas a reubicar».

## Cómo se cogen hoy las web (solo lectura, datos del 27/11)

1. El corte de las 06:00 hace `WEB_271126_01` (85 OUT, todas 100 % reservadas en sus huecos).
2. La oficina hace **una INT por agrupación**, del Stock al SORTER (`EFFEC/INT/67409`, origen `WEB_271126_01`, 05:02).
3. El operario coge esa INT con la **PDA (Lecturas)**. Si no encuentra una prenda, pulsa **Faltante**
   («Tampoco está aquí»): `koroshi_faltantes.sin_alternativa` lleva la ud a FALTANTE y la INT se valida sin ella.
   Hoy Pep ha marcado 3 en la INT/67409 (05:19-05:58).
4. En el SORTER, cada OUT se prepara en el PC con PedidosMultiples.
5. Las OUT cuya prenda faltaba ya no pueden completarse. Hoy:
   - la oficina las sacó de la agrupación (08:33);
   - el corte de las 12:00 las canceló: OUT/28199 (W-0000060355), OUT/28211 (W-0000060380) y OUT/28280 (W-0000060494),
     cada una con «Falta: … 0 de 1».
6. **Las otras prendas de esos pedidos ya estaban cogidas** y están en el SORTER, sueltas, sin pedido. Eso es lo que
   hay que mandar a reubicar.
7. Las 4 de la agrupación `INCOMPLETO` (W-0000059271, 59368, 59378, W-5920002802) son el mismo caso, pero de antes:
   nadie las canceló y siguen a medias desde el 18-23/11.

Lo que falla es el retraso: el pedido sigue vivo desde el Faltante hasta que la oficina lo saca y llega el corte
siguiente, y lo ya cogido se queda en el SORTER sin que nadie sepa que hay que devolverlo.

## Propuesta

### A. Al pulsar Faltante en la INT de una agrupación web (lo principal)

Cuando `sin_alternativa` se hace sobre una línea de una INT cuyo origen es una agrupación `WEB_…`:

1. **Qué pedido se cancela**: la OUT web de esa agrupación que lleva ese artículo y ya no tiene reserva para él. Si hay
   varias, la **última en llegar** (las primeras se sirven antes, como en el corte). Solo pedidos web: origen `W-`, tipo
   PED. ONLINE, nunca Zalando, About You ni tiendas.
2. **La OUT se cancela entera** (`action_cancel`), con una nota en la OUT y su línea en la lista del corte (acción
   «cancelada por faltante»).
3. **Las otras prendas de ese pedido** que están en la misma INT:
   - si **ya se han leído** (están en la mano del operario): la INT se queda sin ellas y en Odoo pasan del hueco a
     **REUBICAR** (movimiento interno, como el de FALTANTE);
   - si **aún no se han leído**: se quitan de la INT (se baja la línea y se libera la reserva) para que no las coja.
4. **La PDA dice**: «Pedido web W-0000060355 cancelado: deja las 2 prendas ya cogidas en REUBICAR» y la lista de lo que
   queda por coger se actualiza sola.
5. **Correo** a Betty e Isaac, como las canceladas del corte, en el momento: el pedido, qué faltaba y qué prendas van a
   REUBICAR. No se manda nada a S4T.

Todo en un savepoint: si algo falla, el Faltante se hace como hoy (pieza a FALTANTE, sin cancelar el pedido) y queda
un aviso en el log y en el correo. Interruptor `koroshi_agrupaciones_web.cancelar_faltante` = 0 al instalar.

### B. En el corte: las web que ya están a medias

Para las que ya están a medias (como las 4 de `INCOMPLETO`) o las que se cuelen: en cada corte, una OUT web con algo
leído, alguna línea sin reserva y más de 4 h agrupada se cancela entera, y lo leído pasa a REUBICAR. Lleva su propio
interruptor, `cancelar_medias`, a 0 al instalar: hasta que se encienda, solo sale en el correo.

### La ubicación REUBICAR

En Odoo no hay ninguna. Las que hay:
- `EFFEC/SORTER` (65 uds ahora): es la mesa de las web. Las prendas sueltas no se distinguen de las que esperan
  su pedido, y Odoo las puede reservar para otra OUT del SORTER.
- `EFFEC/Stock/DEVOLUCIO_KOROSHI` (112 uds): son las devoluciones web de la API. `koroshi_devoluciones` las ubicará en
  la fase 2, desde su DEV. Mezclarlas lía ese recuento.
- `EFFEC/FALTANTE`: es lo que no está. Lo de aquí sí está.

Propuesta: una **ubicación nueva `EFFEC/REUBICAR`** (interna, fuera de `EFFEC/Stock`, como el SORTER: ninguna OUT
reserva de ella), con código de barras `REUBICAR` para leerla. Se reubica desde allí con la pantalla de reubicar o de
contenedores de siempre (leer REUBICAR → prenda → hueco). La crea `koroshi_agrupaciones_web` como dato; **no es un
campo nuevo** en ninguna tabla.

## Módulos (regla 6: son tres)

| Módulo | Servidor | Nueva | Qué |
|---|---|---|---|
| koroshi_agrupaciones_web | 1.1.0 | 1.2.0 | Ubicación REUBICAR, `cancelar_por_faltante(...)` (elegir OUT, cancelar, mover a REUBICAR, correo) y la parte B en el corte |
| koroshi_faltantes | 1.12.0 | 1.13.0 | `sin_alternativa` en una INT de `WEB_…`: llama a lo anterior, si está instalado y encendido, y devuelve `web_cancelada` (pedido, n prendas, ubicación) |
| koroshi_preparacion | 3.38.1 | 3.39.0 | La PDA enseña el aviso «deja las N prendas en REUBICAR» y recarga lo pendiente de la INT |

`koroshi_faltantes` no depende de `agrupaciones_web`: lo busca en el registro y, si no está, sigue como hoy. Se
instala primero agrupaciones_web, después faltantes y después preparación, cada uno con su -u y fuera de horas.

## Preguntas para Isaac

1. **¿Ubicación nueva `EFFEC/REUBICAR`?** ¿O preferís otra que ya uséis físicamente (una mesa, un carro)?
2. Si el artículo que falta lo llevan **varios pedidos** de la agrupación, ¿se cancela el **último en llegar**?
3. Las prendas **aún no leídas** de ese pedido: ¿se quitan de la INT para que no las coja (propuesto)?
4. ¿Las 4 de `INCOMPLETO` se cancelan ya a mano (lo cogido a REUBICAR) o esperan a la parte B?
5. ¿Se instala con los interruptores a 0 y se encienden al día siguiente, como el corte?

## Cómo se probaría

- Tests sin Odoo: qué OUT se elige y qué prendas van a REUBICAR o salen de la INT.
- En el servidor, con `cancelar_faltante` = 0: un botón «Simular» sobre la INT/67409 de hoy tiene que señalar
  W-0000060355, 60380 y 60494, y decir qué prendas irían a REUBICAR.
- PDA real (con el interruptor a 1, en una INT web de verdad, con Isaac delante): pulsar Faltante, ver el aviso, dejar
  las prendas en REUBICAR y comprobar en Odoo que la OUT está cancelada, que lo cogido está en REUBICAR y que la INT
  se valida sin esas prendas.
