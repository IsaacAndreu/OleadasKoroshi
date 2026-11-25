# Diseño v3: «Transportista» en la PDA de Expediciones + impresión en el portátil (25/11/2026)

Sustituye a la v2 ([diseno-imprimir-desde-pda_2026-11-25_v2.md](diseno-imprimir-desde-pda_2026-11-25_v2.md)). Cambia
con lo leído en producción (solo lectura) y las respuestas de Isaac del 25/11 por la tarde. Lo que no se dice aquí
sigue como en la v2 (cola `koroshi_impresion`, agente del portátil, credenciales, plan de entrega).
**Solo diseño, sin código: espera el visto bueno.**

## 1. Lo nuevo de Isaac

- **Hoy**: en el portátil «se eligen las OUT, se les pone el transportista y se imprime con una acción».
- **Para qué sirve además** la pantalla: comprobar que hay **exactamente los bultos que dice Odoo**. Si se escanean
  más matrículas que bultos tiene Odoo, **salta un error** y la pantalla enseña qué pasa.

## 2. Lo leído en producción (25/11, solo lectura)

Copia de las acciones: `bin/versiones/20261125_acciones-expedidor-1771-1262-1878-1879_COPIA-produccion.py`.

| Acción | Qué hace |
|---|---|
| **1771** «Enviar al Expedidor (múltiple)» | **XPO**. Para si alguna OUT ya tiene tracking o si el transportista no es XPO (id 173). Llama a `carrier.xpo_es_send_shipping(OUT)` (`delivery_xpo` + `koroshi_xpo_bultos`: bultos = cajas distintas). |
| **1834** «Enviar al Expedidor (múltiple)» | **GLS** (v5 del 24/11): una expedición por cliente, juntadas sin mandar y con el mismo tracking, cajas compartidas una vez, -70 recuperado del manifiesto. |
| 1878 y 1879 (mismo nombre) | Herramientas de GLS: diagnóstico y recuperar etiqueta. No envían nada. |
| 1262 «Print Shipping Label» | `records.shipping_label_pdf()`: abre el PDF de la etiqueta para imprimir. |

Así que hoy son tres pasos en el portátil: seleccionar las OUT de la tienda → poner el transportista (GLS o XPO) →
la acción de ese transportista, que registra la expedición y deja el PDF.

**Etiquetas del 24/11** (181 adjuntos, todos `Almacén Nath` salvo uno):
- **Una expedición = las OUT de una tienda**: el pedido S-… **y su SUMINISTROS** del día (p. ej. XPO 121771350 =
  S-6665004628 + «SUMINISTROS KOROSHI 24/11 K77»; GLS 1384086009 = S-6665004731 + SUMINISTROS K68). Esto contesta la P3
  de la v2: van juntas todas las OUT pendientes de la tienda.
- **El mismo PDF se adjunta a cada OUT** de la expedición (mismo checksum): `LabelXPO_<n>.pdf` o
  `gls_label_<codbar>.pdf`. **Se imprime una sola vez por expedición**, no una por OUT (si no, saldrían 4 copias).
- El PDF de GLS trae una página por bulto (de 170 KB a 1,2 MB); el de XPO, 55–70 KB.

## 3. La pantalla «Transportista» (cambios sobre la v2)

**Cuadrar los bultos (lo que pide Isaac).** Odoo espera, para la tienda de la primera CJ escaneada, las cajas
distintas de sus OUT validadas sin tracking (la misma cuenta que mandan XPO, `bultos_de()`, y GLS, 1834 v5).
- **Una CJ de más**: **error al momento**, con pitido, y la pantalla dice **por qué** esa caja no cuenta:
  - es de otra tienda (cuál);
  - es de una OUT **sin validar** (cuál, y quién la tiene);
  - ya tiene etiqueta (tracking y día);
  - está **dentro de otra** (juntada con «Juntar cajas»: en cuál);
  - no está en ninguna OUT (CJ vacía o leída de más).
- **Una CJ de menos**: la lista enseña cuáles faltan, con su OUT. El botón no se enciende.
- **«Imprimir etiquetas»** solo cuando escaneadas = esperadas. Esto contesta la P2 de la v2: **bloquea**.
- Arriba siempre: «Tienda K68 · Leídas 5 de 6 bultos».

**Elegir el transportista.** Al pulsar, la PDA pregunta **GLS / XPO** (dos botones grandes) y propone el que tuvo esa
tienda la última vez (se mira en sus OUT con tracking). Si las OUT ya traen transportista, sale ese y no se pregunta.
Después hace lo mismo que el portátil: pone el `carrier_id` en las OUT y llama a la lógica de la **1771** (XPO) o
de la **1834 v5** (GLS), copiada al módulo, como hizo Juntar cajas con la 1844. Las acciones del portátil siguen
como están.

**Imprimir.** Coge los PDF que acaban de quedar adjuntos, **uno por checksum**, y los manda a la cola del portátil.
La PDA dice: «XPO 121771350 · 6 bultos · imprimiendo en Expediciones».

**Reimprimir**: si la tienda ya tiene tracking de hoy, «Reimprimir» manda otra vez ese PDF (sin registrar nada).

## 4. Preguntas que quedan

- **P1. Quién decide GLS o XPO** para cada tienda: ¿lo sabe el operario (dos botones, proponiendo el de la última vez,
  que es la propuesta) o hay una regla fija por tienda que se pueda poner en Odoo?
- **P2. Una CJ de menos**: ¿siempre bloquea, o un jefe puede decir «imprimir igual» (por ejemplo, una caja que ya
  está en el palé y no se puede escanear)? Propuesta: bloquea siempre en la v1.
- **P3. OUT de días anteriores** sin etiqueta de la misma tienda: ¿entran en la expedición (propuesta: sí, marcadas)?
- **P4. El portátil**: modelo de la Zebra y nombre en Windows; ¿encendido con la sesión abierta mientras se trabaja?
- **P5. «Si no hay nada en cola»**: ¿imprime por orden y, si no hay nada delante, al momento?
