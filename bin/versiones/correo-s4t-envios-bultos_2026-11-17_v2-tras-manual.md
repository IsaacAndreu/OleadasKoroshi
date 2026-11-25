# Correo a S4T: envíos (POST /shipments), v2 después de leer su manual (17/11/2026)

Sustituye al borrador del 16/11 (`correo-s4t-envios-bultos_2026-11-16_1734.md`). Su manual «API de envíos»
(noviembre 2026) ya responde a la pregunta 1 (corregir = volver a mandar el mismo pedido y seguimiento; S4T actualiza
y no duplica) y a la 6 (no hay campo de palets). Quedan las que el manual no cubre.

---

**Asunto:** Envíos KOROSHI por la API: dos dudas antes de activarlo

Hola,

Gracias por los manuales de envíos y traspasos. Con ellos tenemos casi todo para activar `POST /shipments`. Antes de
hacerlo nos quedan dos dudas:

1. **Después de SHIPPED.** Si un pedido ya está en SHIPPED (después del envío con `is_final=true`), ¿podemos seguir
   corrigiendo un envío (mismo `order_number` y `tracking_number`) o añadir uno nuevo si aparece otra caja? ¿O la
   API lo rechaza? ¿Y el pedido vuelve a otro estado?
2. **Primera prueba.** ¿Hay un entorno de pruebas de `/shipments`? Si no lo hay, nuestra idea es empezar con un solo
   pedido real de tienda, comprobarlo con `GET /shipments` y, si todo cuadra, activar el resto. ¿Os parece bien?

Y una pregunta que no corre prisa: cuando os llega el envío, ¿Koroshi ve en S4T los bultos por pedido y tienda? ¿Y le
llegan a XPO? Hoy les mandamos cada día un Excel con bultos, palets y tiendas, y si lo ven ahí quizá ya no haga falta.

Gracias,
Isaac Andreu – Effective Logistics
