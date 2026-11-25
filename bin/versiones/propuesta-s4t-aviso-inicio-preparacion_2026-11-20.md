# Propuesta: avisar a S4T/KOROSHI cuando EMPEZAMOS a preparar un pedido (20/11/2026)

Borrador interno para Isaac. No enviado. Pedido por KOROSHI en la grabación del 20/11 (punto 7 de
`plan-grabaciones-29-30_2026-11-20.md`).

## Qué permite hoy la API de S4T (punto 1)

- Los estados que vemos en los pedidos son **PENDING → READY → SHIPPED**, y **CANCELLED**. En
  `20261112_S4T_API_endpoints_resumen.md` no hay ningún estado tipo «en preparación» ni endpoint para ponerlo.
- `PUT /orders/batch-update` solo sirve para informar **unidades servidas y caja**, y al hacerlo la orden pasa a READY.
  Es decir, solo avisa del **final**, no del inicio.
- `POST /shipments` informa del envío (transportista, tracking, bultos). Tampoco es un aviso de inicio.
- No he podido volver a leer el `openapi.json` (pide autenticación y no uso credenciales); la conclusión sale del
  resumen del 12/11 y de lo que ya usamos. **Sin confirmar** si el esquema tiene algún campo libre tipo `notes`.

**Conclusión:** hoy no hay forma soportada de decir «empezamos». Haría falta que S4T lo defina.

## Propuesta

1. **Preguntar a Andrés (S4T)**: ¿puede añadir un estado `IN_PROGRESS` (o un endpoint `POST /orders/{id}/started`)?
   Se junta con el correo de cancelaciones bidireccionales del 20/11
   (`correo-s4t-cancelaciones-bidireccional_2026-11-20.md`), que ya propone `en_picking` al leer la primera prenda.
   El mismo aviso sirve para las dos cosas: KOROSHI ve el inicio y S4T no intenta cancelar lo que ya empezó.
2. **Qué es «empezar»** (a decidir): primera prenda leída en Lecturas de cualquiera de las OUT del pedido. Hay que
   confirmar con quien lleva `koroshi_preparacion` dónde se detecta y guardar la hora (hoy no sé si queda guardada).
3. **Odoo**: enviar el aviso una sola vez, al primer evento de lectura del pedido; si falla, reintento sin parar la
   PDA (no puede retrasar la lectura). Versión nueva de `koroshi_preparacion` o de `koroshi_s4t_envios`.
4. **Mientras tanto**, sin tocar S4T: KOROSHI puede recibir la hora de inicio/fin por un informe periódico
   (Excel o correo) sacado de Odoo con los tiempos por pedido. Es lectura, sin riesgo.

## Punto 2: pestaña para KOROSHI (monitor de picking)

Isaac dice que es tema de Andrés, así que **primero preguntarle a él** si la pestaña ha de ir dentro de S4T. Si
prefiere que la monte Odoo, hay que decidir:
- quién la ve (usuario de solo lectura, sin acceso a PDA ni a stock);
- qué se muestra: pedido, tienda, hora de inicio, hora de fin, bultos, cajas, prendas;
- que no se vean datos de operarios (ya hay un monitor interno, `koroshi_monitor`).

Es trabajo nuevo; no lo he empezado.

## Pregunta corta para Andrés (si Isaac da el sí)

> ¿Podéis añadir un estado «en preparación» (o un endpoint) para que os avisemos al leer la primera prenda de una
> orden, de modo que KOROSHI lo vea en vuestro panel? Y la pestaña de seguimiento de picking para KOROSHI, ¿preferís
> montarla vosotros o que la ofrezcamos nosotros?

## Para Isaac

- Nada enviado ni tocado en producción.
- Decisiones tuyas: si se pregunta a Andrés junto con las cancelaciones o en correo aparte; si interesa el informe
  periódico como solución provisional.
