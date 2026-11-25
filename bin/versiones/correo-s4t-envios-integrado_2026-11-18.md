# Correo a S4T: envíos ya integrados y en marcha (18/11/2026)

Va después de `correo-s4t-envios-bultos_2026-11-17_v3-informal.md` (sigue como estaba). Es un aviso: no pide nada nuevo, solo recuerda la duda que sigue abierta.

---

**Asunto:** Envíos KOROSHI: ya integrado y funcionando desde hoy

Hola,

Os confirmamos que la integración de envíos (POST /shipments) ya está hecha y en marcha. Desde hoy, 18/11, nuestro sistema os manda solo, cada 15 minutos, el transportista, el tracking, los bultos, el peso y el volumen de los pedidos que salen.

Lo probamos ayer con un pedido real (S-6665004194, XPO 121771219, 3 bultos) y lo recibisteis bien: la orden siguió en READY, que es lo que esperábamos.

Cómo lo mandamos, por si os sirve para ver los datos:
- **XPO:** va sin is_final hasta que sale el camión; entonces pasa a SHIPPED.
- **GLS:** va con is_final=true, así que la orden pasa a SHIPPED al recibirlo.
- Peso y volumen los declaramos como factura XPO: 15 kg y 0,09 m3 por bulto.
- Solo mandamos los pedidos de hoy en adelante; los anteriores no, porque esa información ya la tenéis.

Si veis algo raro en los datos de hoy (bultos, pesos o algún pedido que no os llegue), avisadnos y lo miramos.

Seguimos esperando la respuesta a la duda del otro día: si un pedido ya está en SHIPPED y falta o sobra una caja, ¿podemos corregir el envío o añadir otro?

Gracias!

Isaac
