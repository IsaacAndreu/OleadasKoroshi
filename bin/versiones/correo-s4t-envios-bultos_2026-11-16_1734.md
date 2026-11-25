# Correo a S4T: envíos (POST /shipments) y bultos por pedido

**Asunto:** Envíos KOROSHI por la API: corregir bultos, entorno de pruebas y qué ve Koroshi

Hola,

En Effective (NAU-2) tenemos preparada la integración de envíos con vuestra API B2B (`POST /shipments`). Por cada
pedido S-6665 en READY, con todas sus OUT preparadas y etiquetadas, os enviaríamos un envío por cada número de
seguimiento (XPO o GLS) con el transportista, el seguimiento, los bultos, el peso y el volumen. El último va con
`is_final=true` y el pedido pasa a SHIPPED. Todavía no lo hemos activado: de momento solo calculamos los envíos, sin
llamaros.

Antes de activarlo queremos asegurarnos de que el número de bultos que os mandamos es el mismo que se carga en el
camión, porque hoy, a veces, no cuadra a la primera. Para eso necesitamos saber:

1. **Corregir un envío ya mandado.** Si mandamos un envío con un número de bultos equivocado, ¿se puede corregir?
   ¿Volviendo a hacer `POST /shipments` con el mismo seguimiento, con otro endpoint o de otra forma?
2. **Deshacer SHIPPED.** Si un pedido ya está en SHIPPED (después del envío con `is_final=true`) y falta o sobra una
   caja, ¿se puede deshacer o añadir otro envío a ese pedido?
3. **Entorno de pruebas.** ¿Hay un entorno de pruebas de `/shipments`, o un pedido de prueba, para probar sin tocar
   pedidos reales? (Os lo preguntamos también en el correo del 12/11.)
4. **Qué ve Koroshi.** Cuando os llega el envío, ¿Koroshi ve en S4T los bultos por pedido y tienda al momento? Hoy
   les mandamos cada día un Excel con bultos, palets y tiendas. Si lo ven en S4T, quizá no haga falta.
5. **XPO.** ¿Estos datos le llegan a XPO desde S4T, o XPO solo tiene lo que registramos nosotros directamente con
   ellos al sacar la etiqueta?
6. **Palets.** ¿`/shipments` admite el número de palets, además de los bultos? ¿Os serviría?

Las preguntas 1 y 2 son las que más nos importan: de ellas depende si podemos activar los envíos ya o si antes
tenemos que tener la comprobación de bultos funcionando.

Gracias,
Isaac Andreu – Effective Logistics
