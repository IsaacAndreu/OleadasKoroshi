# Diseño v4: «Transportista» en la PDA de Expediciones + impresión en el portátil (25/11/2026)

Sustituye a la v3 ([diseno-imprimir-desde-pda_2026-11-25_v3.md](diseno-imprimir-desde-pda_2026-11-25_v3.md)): es la
v3 con las respuestas de Isaac a P1-P5 (sección 4, ya cerrada). Base: la v2 y lo leído en producción (solo lectura). Lo que no se dice aquí
sigue como en la v2 (cola `koroshi_impresion`, agente del portátil, credenciales, plan de entrega).
**Todas las preguntas contestadas. Siguiente: el sí de Isaac para empezar por `koroshi_impresion` 1.0.0.**

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

**Elegir el transportista** (decisión P1): arriba de la pantalla hay **GLS / XPO** para elegirlo **antes de escanear**,
si el operario ya lo sabe; si no lo ha elegido, se pregunta **al final**, con todas las CJ escaneadas, al pulsar
«Imprimir etiquetas». Se propone el que tuvo esa tienda la última vez (sus OUT con tracking). Si las OUT ya traen
transportista, sale ese y, si el elegido es otro, se avisa antes de cambiarlo.
Después hace lo mismo que el portátil: pone el `carrier_id` en las OUT y llama a la lógica de la **1771** (XPO) o
de la **1834 v5** (GLS), copiada al módulo, como hizo Juntar cajas con la 1844. Las acciones del portátil siguen
como están.

**Imprimir.** Coge los PDF que acaban de quedar adjuntos, **uno por checksum**, y los manda a la cola del portátil.
La PDA dice: «XPO 121771350 · 6 bultos · imprimiendo en Expediciones».

**Reimprimir**: si la tienda ya tiene tracking de hoy, «Reimprimir» manda otra vez ese PDF (sin registrar nada).

## 4. Decisiones de Isaac (25/11, tarde)

- **P1 Transportista**: se puede elegir antes de escanear o al final, con todo escaneado (sección 3).
- **P2 Si no cuadra**: **bloquear siempre**, hasta que la pantalla haya enseñado por qué no cuadra y se arregle. Sin
  «imprimir igual» para nadie en la v1.
- **P3 Días**: sí, en una misma expedición pueden ir OUT de días distintos de la misma tienda (salen marcadas con su
  día en la lista, para que se vea).
- **P4 Impresora**: Zebra **ZD420** (o parecida; Isaac no se acuerda del modelo exacto). El nombre de Windows se mira al
  instalar el agente y se pone en `config.ini`; el papel 4x6 se comprueba con una reimpresión antes de usarlo.
- **P5 Cola**: por orden de llegada; si no hay nada delante, sale al momento.

## 5. Siguiente

Orden de la v2 (sección 6): `koroshi_impresion` 1.0.0 → agente probado aquí con «Microsoft Print to PDF» → agente en
el portátil con Isaac delante (reimprimir una etiqueta ya hecha) → `koroshi_transportista` 1.0.0 → primera expedición
real con Isaac o un jefe delante. Son dos módulos nuevos (regla 6: avisado). Modelo: Fable u Opus en esfuerzo alto.
