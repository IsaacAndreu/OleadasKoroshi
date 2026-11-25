# Respuesta a S4T (Andrés Moya): número de expedición y número de albarán (19/11/2026)

Borrador. No enviado: lo revisa Isaac. Comprobado en Odoo (modo lectura, 19/11) y en `koroshi_s4t_envios` 1.3.

---

**Para:** Andrés Moya (S4T)
**Asunto:** RE: Expedición y albarán en los envíos

Hola Andrés,

Os contestamos mirando lo que mandamos de verdad hoy con `POST /shipments`.

**1. ¿Usáis un número de expedición que agrupe varias órdenes de servicio?**

Sí. Con **XPO y GLS el transportista nos da un solo número por expedición**, y una expedición puede llevar varias
órdenes de la misma tienda. Ese número es el que mandamos en `tracking_number`.

- De los envíos desde el 10/11, 296 números distintos, **60 agrupan 2 o 3 órdenes** de la misma tienda
  (por ejemplo, el XPO 121771200: órdenes 6665004125, 6665004144 y 6665004188, todas de K70).
- Cada orden se manda con una llamada propia: su `order_number`, el mismo `tracking_number` y **sus propios bultos**
  (en ese ejemplo, 21, 6 y 1; la expedición lleva 28).
- Una orden nunca lleva dos números de expedición distintos (no lo hemos visto en estas fechas).

No tenemos un «número de expedición» aparte del seguimiento del transportista. Si queréis uno propio para agrupar,
sería nuevo, y nos diríais cómo lo queréis.

**2. ¿El número de albarán del envío es el de la orden de servicio o una numeración interna?**

**Hoy no mandamos ningún albarán.** Lo que mandamos es:

| Campo | De dónde sale |
|---|---|
| `order_number` | El número de la orden de servicio que vosotros nos dais (el mismo del sync de pedidos, sin «S-»; por ejemplo, 6665004426) |
| `carrier` | GLS o XPO |
| `tracking_number` | El seguimiento o expedición del transportista |
| `packages` | Cajas distintas de esa orden en esa expedición |
| `weight_kg` / `volume_m3` | 15 kg y 0,09 m³ por bulto (el criterio de XPO) |
| `is_final` | `true` en el último envío de la orden |

Nuestra numeración interna de albaranes (`EFFEC/OUT/…`) **es interna y no la mandamos**. Una orden puede salir en varios
albaranes internos, y todos comparten la misma expedición.
Si queréis ver el número interno, **sí os podemos mandar un campo opcional** `delivery_note` (o como lo llaméis), pero
no sirve para identificar la orden, y no es obligatorio para nosotros: decidlo vosotros.

**3. El cierre del camión, para que lo sepáis**
XPO no pasa la orden a SHIPPED hasta que cerramos el camión del día en Odoo (un botón que manda el manifiesto a XPO).
GLS pasa a SHIPPED en cuanto tiene su etiqueta. Mientras el camión está abierto, los envíos XPO van **sin `is_final`**
y se pueden corregir mandando otra vez el mismo pedido y el mismo seguimiento (nos habéis dicho que actualizáis y no
duplicáis).

Si necesitáis algo más, decidnos qué campo queréis y lo miramos.

Gracias,

Isaac

---

## Para Isaac (no va en el correo)

- Verificado: 296 trackings, 238 con varias OUT y 60 con varias órdenes (desde el 10/11); 375 órdenes, ninguna con
  más de un tracking.
- Mandar un «número de albarán» propio no está implementado; sería un cambio en `koroshi_s4t_envios` (versión nueva).
- El 19/11 hay envíos de 18/11 y anteriores que Isaac mandó en bloque (638 envíos, 218 GLS y 420 XPO). No hace falta
  decírselo a S4T en este correo, pero conviene que Andrés lo sepa si ve picos.
