# Respuesta a S4T: cancelaciones bidireccionales y estado «en picking» (20/11/2026)

Borrador. No enviado: lo revisa Isaac. Parte de `correo-s4t-cancelaciones-propuesta-flujo_2026-11-19.md` (no se toca).
Comprobado en Odoo, en lectura, el 20/11.

---

**Para:** Andrés Moya y quien escribió el correo (S4T)
**CC:** Sonia, Betty
**Asunto:** RE: Cancelaciones bidireccionales

Hola,

Estamos de acuerdo: hace falta una conexión en los dos sentidos, con la regla de que **una orden que ya está en picking
no se cancela sola**. Os proponemos esto.

**Lo que ha pasado hoy, que es justo el caso que queremos evitar**
Esta mañana se anularon en S4T los pedidos de tienda del 6665004464 al 6665004510 (47 órdenes). Nos hemos enterado
por otro lado, no por la API. En Odoo, esas 47 órdenes seguían vivas y una de ellas, la **K80 (6665004510)**, se
preparó y se **validó a las 06:31** (1 bulto) cuando en vuestro sistema ya estaba CANCELLED. Hoy no hay nada que nos
avise de una cancelación vuestra, y nosotros tampoco os avisamos de las nuestras: las canceladas en Odoo se quedan
en PENDING en S4T.

**1. Estado de la orden en picking (nosotros → vosotros)**
Aceptamos enviaros el estado, y lo haríamos así:

| Estado que os mandamos | Cuándo |
|---|---|
| `en_cola` | La orden está en Odoo, sin ninguna prenda leída |
| `en_picking` | Se ha leído la primera prenda (empieza la preparación) |
| `preparada` | Está leída y en caja, sin validar |
| `validada` | La OUT está hecha |

Os lo enviaríamos al cambiar de estado. **Necesitamos que nos digáis el endpoint** (método, campos, cómo identificáis la
orden). Para las órdenes de **Zalando**, que van por bultos y sin matrícula, el estado «en picking» se tendría que
definir aparte.

**2. Endpoint para cancelar (en los dos sentidos)**
- **Vosotros → nosotros:** una solicitud de cancelación de una orden. Nosotros respondemos en el acto con:
  - `cancelada`: la orden no está en picking (`en_cola`);
  - `no_cancelable` + estado: ya está en picking o más allá (`en_picking`, `preparada` o `validada`);
  - `no_encontrada`.
- **Nosotros → vosotros** (desde Koroshi central o desde el almacén, sin correo): la misma solicitud a vuestro
  endpoint, y vosotros respondéis igual: `cancelada` o `no_cancelable` + el motivo.

Para que no haya dos respuestas distintas a la vez: **vale la primera que llegue**, y la otra parte recibe `no_cancelable`
con el motivo «ya cancelada» o «ya en picking».

**3. Qué hacemos cuando se pide cancelar algo que ya está en picking**
No se cancela de forma automática: devolvemos `no_cancelable` y la decide una persona (Erika o Betty), que os contesta.
Si se decide cancelar igualmente, se hace a mano y se os avisa por el endpoint.

**4. Lo que haríamos nosotros en Odoo**
1. Leer vuestras solicitudes cada pocos minutos y contestar con el resultado.
2. Una regla única de «¿se puede cancelar?»: sin ninguna prenda leída, sin caja y sin OUT validada, en todas las OUT
   de la orden.
3. Enviar el estado cada vez que cambia.
4. Dejar constancia de quién cancela y cuándo, también cuando se cancela a mano.
5. Un aviso en pantalla si se intenta preparar o validar una orden que vosotros habéis marcado como cancelada.

**Lo que os pedimos**
1. La definición de los dos endpoints (el de estado y el de cancelación).
2. Un entorno de pruebas, o una orden de prueba, para no tocar pedidos reales.
3. Confirmar los estados y que la regla «en picking no se cancela solo» es la que queréis.

Mientras no esté listo, ¿podéis avisarnos por correo o por la vía de siempre al anular un lote de pedidos, como el de hoy?

Gracias,

Isaac

---

## Para Isaac (no va en el correo)

- **Hechos comprobados (20/11, lectura):** las 47 órdenes S-6665004464 a 4510 están en «Pedido de venta» y en PENDING
  de nuestro lado (`x_s4t_status`); **solo la 4510 tiene OUT**, EFFEC/OUT/26752, validada el 20/11 a las 05:31 UTC
  (06:31 hora del almacén), con 1 bulto. En Odoo no hay nada que lea el estado CANCELLED de S4T.
- **No lo he hecho:** no hay nada hoy que impida preparar o validar una orden cancelada en S4T. El «aviso en pantalla»
  del punto 4.5 sería código nuevo.
- Los estados de Odoo que usa la propuesta (sin leer / leída / en caja / validada) salen del flujo de Lecturas
  (`koroshi_preparacion`); hay que confirmar con la persona que lleva ese módulo cómo se detecta cada uno.
- La K80 (4510) ya se ha validado: lo que se hace con ella (devolver el género, avisar a S4T) lo decide Isaac.
- Pendiente de decidir: ¿quién cancela en Odoo cuando S4T pide cancelar y la orden está en picking? He puesto a
  Erika o Betty; que Isaac lo confirme.
