# Correo a KOROSHI: incidencia del pedido 57080 (24/11/2026, v2)

Borrador, **sin enviar**. Responde al correo de support@koroshi.tv «INCIDENCIA PEDIDO 57080» (18/11, 23/11 y 24/11),
dirigido a Betty con copia a Sandra (web), Cruz Jimeno y Jose Luis; Isaac en copia.
v2: sustituye a la v1 (mismo archivo, sin enviar), que decía que S4T no nos lo había mandado.

## Comprobado (solo lectura, 24/11)

**En S4T** (dashboard `/api/service/dashboard/orders-b2c`):
- `0000057080`, cliente 00005555, **PENDING**, cabecera «vista» (descargada) el **30/10 a las 18:00**.
- 1 línea: **2621JA28-000003-M** (EAN 8445962839732), 1 ud, servida 0. **La línea consta «No visto»**: nunca se
  descargó.
- `0000057079` está igual: PENDING, vista el 30/10 a las 18:00, 1 línea 2611ZA11-000003-UNI «No visto». Tampoco está en
  Odoo.
- La 57076 y la 57078 no existen en S4T.

**En Odoo**:
- No hay pedido, OUT ni registro en el feed (`s4t.order.feed`) de la 57080 ni de la 57079.
- La importación de las 18:00 del 30/10 sí creó la W-0000057084, y la de las 17:30 creó la 57081, la 57082 y la
  57083-02.
- Hay stock de la prenda: **37 uds** de 2621JA28-000003-M en huecos (L118 P10 C1 15, L118 P11 C1 14, L118 P10 C2 8).

**Conclusión**:
- La importación de las 18:00 del 30/10 marcó como vistas las cabeceras de la 57079 y la 57080, pero no descargó sus
  líneas ni las creó en Odoo. Es el mismo síntoma que los pedidos perdidos del 12/11 (58545–58555).
- El almacén no los ha visto nunca: no se han preparado ni entregado a SEUR.
- El «realizado» del 06/11 que ve KOROSHI (ticket 5555251971, operador 000001, 10:22:51) no lo ha puesto el almacén.

**Pendiente**:
- Recuperar la 57079 y la 57080 con la acción «Recuperar Pedidos Online» (1827). Esto escribe en producción: hace falta
  el sí de Isaac.
- Antes, conviene confirmar con KOROSHI que siguen vivos y no los han rehecho con otro número.
- Mirar si hay más pedidos de S4T en PENDING sin línea vista que no estén en Odoo.

---

**Para:** support@koroshi.tv
**CC:** Betty, Sandra (web@koroshi.tv), Cruz Jimeno, Jose Luis
**Asunto:** RE: INCIDENCIA PEDIDO 57080

Buenas tardes:

Disculpad el retraso en contestar.

Hemos revisado el pedido **57080** y **no ha llegado nunca al almacén**, así que no se ha preparado ni se ha entregado
a SEUR y no hay manifiesto.

Lo que ha pasado:
- El 30/10 a las 18:00 el pedido se marcó como descargado en S4T, pero **su línea no llegó a bajarse** (en S4T consta
  «No visto»). Por eso no se creó en nuestro sistema.
- El pedido sigue en S4T como **PENDING**, con 0 de 1 servida.
- Le ha pasado lo mismo al pedido **57079**, del mismo momento.
- El «realizado» del 06/11 (ticket 5555251971, operador 000001) no lo hemos puesto nosotros. ¿Nos podéis decir quién
  es el operador 000001? Nos ha aparecido también en otros pedidos anulados.

Tenemos stock de la prenda del 57080 (**2621JA28 000003 M**). Si nos confirmáis que el pedido sigue vivo y que no lo
habéis rehecho con otro número, lo recuperamos y sale hoy mismo. Lo mismo con el 57079 (**2611ZA11 000003 UNI**).

Estamos revisando si hay más pedidos en esta situación para recuperarlos.

Un saludo,

Isaac
Soporte almacén KOROSHI – Amposta
