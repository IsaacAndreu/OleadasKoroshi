# Respuesta a S4T: proceso de cada estado y equivalencias (23/11/2026)

Borrador. No enviado: lo revisa Isaac. Responde al correo de Efren (23/11) sobre PENDING / en picking / READY /
DOCUMENTED / SHIPPED. Basado en `acción 1800 v6.4` y `koroshi_s4t_envios` 1.3 (lo que hace hoy el código).

---

**Para:** Efren Arnaude, Andrés Moya
**CC:** Sonia, `spain@koroshi.tv`, Cruz Jimeno, `expediciones@koroshi.tv`
**Asunto:** RE: cada cuánto nos enviáis información? — estados

Hola Efren,

Así es el proceso en nuestro lado, estado a estado, con lo que **hacemos hoy** y lo que sería **nuevo**:

| Estado S4T | Equivale en nuestro almacén | Lo enviamos hoy |
|---|---|---|
| **PENDING** (en cola) | La orden está en Odoo y no se ha leído ninguna prenda | Sí: es el estado de partida |
| **En picking** (nuevo) | Se ha leído la primera prenda de cualquiera de sus OUT | **No**, sería nuevo |
| **READY** (preparada) | Todas las OUT están hechas, las cajas pequeñas ya juntadas y no hay prendas sin caja. Enviamos unidades servidas y caja | Sí, con `PUT /orders/batch-update`, **solo al final** |
| **DOCUMENTED** (validada) | Las OUT tienen la etiqueta/expedición del transportista | **No lo enviamos nosotros**; tendría que salir de vuestra sincronización con expediciones |
| **SHIPPED** | Último envío de la orden: GLS en cuanto tiene etiqueta; XPO cuando cerramos el camión del día | Sí, con `POST /shipments` (`is_final`) |

**Dos diferencias con vuestra lista**
1. Hoy no mandamos nada de «en caja pero sin validar»: **READY lo ponemos al final**, con la orden ya validada. Si
   queréis separar «preparada» (en caja) de «validada», sería un estado más por definir, y nos diréis cómo.
2. **DOCUMENTED** no lo ponemos nosotros. Si lo queréis como «con etiqueta», podemos mandarlo, pero necesitamos el
   endpoint.

**Qué haríamos nosotros** (con vuestro endpoint): enviar «en picking» al leer la primera prenda, mantener READY
como hasta ahora y mandar el resto de estados cada vez que cambien. Las órdenes de **Zalando** van por bultos y sin
matrícula: su «en picking» se definiría aparte.

Para empezar necesitamos el endpoint (método, campos y cómo identificáis la orden) y un entorno de pruebas.

Gracias,

Isaac

---

## Para Isaac (no va en el correo)

- **Revisa la tabla:** la columna «lo enviamos hoy» sale del código. Lo de DOCUMENTED es lo que **supongo** que
  significa su «sincronizado con las expediciones»: confírmalo antes de enviar.
- La acción 1800 v6.4 ya espera a las cajas pequeñas por juntar, **salvo si todas las OUT tienen etiqueta**
  (`ETIQUETA_CIERRA`). Si READY ha de significar «todo juntado», hay que quitar esa excepción (v6.5, pendiente de tu OK).
- «En picking» sería código nuevo en `koroshi_preparacion` (hora de la primera lectura); hoy no sé si se guarda.
