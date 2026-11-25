# Respuesta a S4T y KOROSHI: cancelaciones y aviso de «en proceso» (19/11/2026)

Borrador. No enviado: lo revisa Isaac. Hilo «RE: cada cuanto nos enviais informacion?» (19/11, 11:11).
Comprobado en Odoo (lectura) y en el código de la acción 1800 v6.3 y `koroshi_agrupaciones_web`.

---

**Para:** Andrés Moya (S4T)
**CC:** Sonia, Betty
**Asunto:** RE: cada cuánto nos enviáis información? — cancelaciones

Hola,

Sí, queremos que la cancelación de Betty nos llegue sola. Os proponemos este flujo.

**Cómo está hoy (para que veáis de dónde partimos)**
- Si una orden se cancela, hoy lo hacemos a mano en Odoo. **A S4T no se lo decimos**: las órdenes canceladas se quedan
  en PENDING en vuestro lado (hoy hay 9 así, de las 00:27 a las 09:00).
- Los pedidos web que cancelamos por falta de stock van por correo a Betty, que los cancela en el ERP. Eso no cambia.

**1. Endpoint de cancelaciones (vosotros → nosotros)**
Vosotros publicáis una lista de órdenes a cancelar. Nosotros la **leemos** (GET, como las demás) cada pocos minutos y,
por cada orden, **respondemos** con un resultado:

| Respuesta nuestra | Cuándo |
|---|---|
| `cancelada` | La orden está **sin empezar**: ninguna prenda leída ni caja ni OUT validada |
| `no_cancelable` + motivo | La orden **ya está en proceso**: leída, en caja o validada |
| `no_encontrada` | No existe esa orden en Odoo |

Es **idempotente**: si nos mandáis dos veces la misma orden, damos la misma respuesta.

**2. Qué estados admiten cancelar**
| Estado de la orden en nuestro almacén | ¿Se cancela? |
|---|---|
| Sin empezar (sin lecturas) | **Sí** |
| Con prendas leídas, sin caja | **No** |
| Con prendas en caja (CJ) | **No** |
| Validada o expedida | **No** |

Una OUT con algo leído **no se cancela nunca**; es la regla que ya aplicamos.

**3. Aviso de «empezamos a preparar» (nosotros → vosotros)**
Podemos avisar cuando se lee la **primera prenda** de una orden (pasa a «en proceso»). Para esto nos tenéis que decir
**por dónde**: un endpoint nuevo `POST` o un estado nuevo en el que ya usamos. Con ese aviso, KOROSHI ve las órdenes
en proceso y no intenta cancelarlas.

**4. Casos especiales**
- Las órdenes de **Zalando** no se cancelan nunca por este camino.
- Los pedidos **web** siguen por correo a Betty (no pasan por S4T).
- Si una orden se cancela dos veces a la vez (nosotros y vosotros), gana la primera.

**Qué haría falta en Odoo** (nosotros, no vosotros)
1. Un cron que lea vuestra lista (no hay nada hasta que publiquéis el endpoint).
2. La regla «sin empezar», en una sola función y con una prueba.
3. La cancelación con motivo y registro de quién y cuándo (también para las que se cancelan a mano).
4. El aviso de «en proceso» al leer la primera prenda.
5. Las pruebas en un entorno que no toque pedidos reales: ¿tenéis entorno de pruebas?

**Qué os pedimos**
1. La definición del endpoint (campos, paginación, cómo marcáis una orden como cancelada).
2. Por dónde quereis recibir el aviso de «en proceso».
3. Un entorno de pruebas o una orden de prueba.

Gracias,

Isaac

---

## Para Isaac (no va en el correo)

- **Estados reales de una OUT en Odoo**, para definir «sin empezar»: ninguna línea con `qty_done > 0`, ninguna
  `result_package_id`, ninguna OUT `done`. Hay que mirarlo para **todas** las OUT del pedido (un pedido de tienda
  suele tener 2 a 5).
- La acción 1800 v6.3 ya cancela **backorders vacías de días anteriores** de las tiendas (nunca Zalando). Esa
  cancelación es nuestra y no depende de S4T. La cancelación pedida por S4T sería otra regla.
- `koroshi_agrupaciones_web` (instalado el 18/11) cancela las web no reservadas con correo a Betty; se queda igual.
- Es **trabajo nuevo** (módulo o versión nueva de `koroshi_s4t_sync`) y exige a S4T que defina el endpoint. Nada de
  esto está hecho. Hasta que no contesten, Sonia/Betty tienen que seguir cancelando a mano.
- **Si Isaac prefiere,** el punto 3 («en proceso») se puede responder en otro correo aparte, más tarde.
