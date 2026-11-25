# Diseño v2: «Transportista» en la PDA de Expediciones + impresión en el portátil (25/11/2026)

Sustituye a la v1 ([diseno-imprimir-desde-pda_2026-11-25.md](diseno-imprimir-desde-pda_2026-11-25.md)) con las
respuestas de Isaac del 25/11. **Solo diseño, sin código: espera el visto bueno y las preguntas de la sección 8.**

## 1. Lo que ha dicho Isaac (25/11)

- Primero, **Expediciones**: una pantalla nueva en la PDA, área Expediciones, que se llama **«Transportista»**.
- El operario **escanea todas las matrículas CJ que tiene físicamente** delante. Con ellas se hace «lo del
  transportista» (GLS o XPO) y, al pulsar **«Imprimir etiquetas»**, el portátil de Expediciones las imprime.
- Solo etiquetas **GLS / XPO**, en **PDF, como hoy**. Impresora **4x6**.
- **Un solo portátil** en Expediciones: no hay que elegir impresora.
- Usuario de Odoo del script: **Almacén Nath**.
- **Windows 10**, se puede instalar lo que haga falta.
- Más adelante habrá otros puestos (otros «scripts» = el mismo agente con otra configuración).

## 2. Cómo se hace hoy (lo que se reaprovecha)

- **GLS**: en el portátil se seleccionan las OUT en la lista de albaranes y se lanza la acción de servidor **1834
  «Enviar al Expedidor (múltiple)»** (v5 en producción desde el 24/11,
  `bin/versiones/20261124_accion-1834_enviar-expedidor_v5-cajas-compartidas-APLICADA-produccion.py`): una expedición por
  cliente (tienda), las OUT juntadas o sin caja propia no se mandan y reciben el mismo tracking, las cajas compartidas
  cuentan una vez, error -70 = ya estaba en GLS (se recupera del manifiesto). La etiqueta llega en PDF y queda
  adjunta en la OUT.
- **XPO**: `delivery_xpo` (de Effective, no está en este repo) + `koroshi_xpo_bultos` (nuestro): una expedición
  `RegistraExpedicion` con bultos = cajas **distintas** (`bultos_de()`), 15 kg y 0,09 m3 por bulto; cada OUT recibe su
  adjunto PDF `LabelXPO_...`. Después, el cierre del camión XPO (Monitor, «Consulta de envíos») y `koroshi_s4t_envios`.
- **Juntar cajas** (`koroshi_juntar_cajas`, instalado hoy) ya sabe pasar de una CJ a su OUT, pedido y tienda, y ya
  comprueba SHIPPED, camión cerrado y Zalando. Se reaprovecha esa lectura.
- Hoy en Expediciones **cuentan las cajas a mano** y comparan con Odoo en el portátil (spec del 16/11,
  `intent/carga-camion-bultos/`): escanearlas en la PDA es justo lo que esa spec echaba en falta.

## 3. La pantalla «Transportista» (PDA, área Expediciones)

```
1. Escanear CJ ──> sale la tienda (K68), el transportista (GLS/XPO) y la lista: CJ leídas / CJ que espera Odoo
2. Seguir escaneando hasta tener todas las cajas de la tienda
3. «Imprimir etiquetas» ──> registra la expedición en GLS o XPO ──> trabajo en la cola ──> sale en el portátil
```

**Escaneo.** Cada CJ leída se busca como en Juntar cajas (paquete → líneas → OUT → cliente). La primera CJ fija la
tienda y el transportista; una CJ de otra tienda o de otro transportista se rechaza con pitido y mensaje.

**Qué espera Odoo de esa tienda** (lo que se compara con lo escaneado): las OUT **validadas, sin tracking**, de ese
cliente y ese transportista, del día (o anteriores sin etiqueta, marcadas), con sus cajas distintas.

**Pantalla:**
- «Leídas 5 de 6»; lista de CJ: ✓ leída, ✗ falta (está en Odoo y no se ha escaneado), ⚠ sobra (escaneada y no está
  en ninguna OUT pendiente: ya etiquetada, sin validar, de otro día...).
- Avisos de la spec del 16/11: OUT de la tienda sin validar todavía (se quedaría fuera), OUT con 0 bultos (juntada:
  va con el mismo tracking), caja compartida entre dos OUT, camión XPO del día ya cerrado.
- **«Imprimir etiquetas»** solo se enciende cuando **leídas = las que espera Odoo** (pregunta P2).

**Al pulsar «Imprimir etiquetas»** (en el servidor, todo en una llamada):
1. Vuelve a comprobar todo (alguien pudo etiquetar desde el portátil mientras tanto). Si alguna OUT ya tiene
   tracking, para: no se registra dos veces.
2. **GLS**: la misma lógica que la acción 1834 v5, pasada a código del módulo (como hizo Juntar cajas con la 1844);
   la 1834 sigue en el portátil para quien la use. **XPO**: lo mismo que hace hoy el portátil para XPO (pregunta P1).
3. Coge los PDF de etiqueta que acaban de quedar adjuntos en las OUT (una vez por expedición, no uno por OUT si son el
   mismo) y crea los trabajos en la cola del portátil.
4. Responde a la PDA: «GLS 12345678: 6 bultos. Imprimiendo en Expediciones» o el error de GLS/XPO tal cual.
5. Deja constancia (registro propio, como `koroshi.juntar.registro`): quién, cuándo, tienda, CJ leídas, OUT, tracking.

**Reimprimir**: si la tienda ya tiene tracking de hoy, la pantalla lo dice y ofrece **«Reimprimir»**, que solo vuelve
a mandar a la cola los PDF ya adjuntos (no registra nada en GLS/XPO).

**Fuera**: Zalando (memoria «Zalando: no tocar») y lo que no sea GLS/XPO.

## 4. Cola de impresión (`koroshi_impresion`, módulo nuevo pequeño)

Como en la v1, simplificado (un puesto, solo PDF):
- `koroshi.impresora`: `name`, `codigo` (`EXP1`), `puesto` («Portátil Expediciones»), `activa`, `ultimo_contacto`.
  Hoy solo una. Si un día hay más puestos, se añaden aquí y el agente del otro PC lleva otro `codigo`.
- `koroshi.impresion.trabajo`: impresora, **adjunto PDF** (`ir.attachment` de la etiqueta) o informe + ids (para
  otros usos futuros), copias, descripción («GLS K68 S-6665004781, 6 bultos»), estado
  `pendiente → imprimiendo → impreso / error`, error, intentos, quién y cuándo.
- Métodos: `encolar(...)` (lo usa la pantalla Transportista), y para el agente `siguientes(codigo)`, `pdf(id)`,
  `hecho(id, ok, texto)`. Un trabajo «imprimiendo» más de 5 min vuelve a pendiente; a los 3 intentos, error.
- **Orden**: por orden de llegada; si la cola está vacía sale al momento (así entiendo «si no hay nada en cola»; si
  querías decir otra cosa, pregunta P5).
- Si el portátil lleva más de 1 min sin preguntar, la PDA avisa: «El portátil de Expediciones no está conectado: las
  etiquetas saldrán cuando se encienda». La expedición ya está hecha; no se pierde nada.
- Menú en Odoo con la cola (filtro de errores, botón «Reintentar»).

No toca `stock.picking`, `stock.picking.type` ni `stock.move.line` (regla 7): todo en tablas propias.

## 5. Agente en el portátil (Windows 10)

- `bin/agente_impresion/agente_impresion.py` en el repo, sin claves; en el portátil un `.exe` (PyInstaller), fuera
  de git.
- Cada 3 s pregunta a Odoo por JSON-RPC los trabajos de `EXP1`; baja el PDF, lo imprime con **SumatraPDF**
  (`-print-to "<impresora>" -print-settings "noscale" -silent`), marca impreso o error.
- Si se cae la red, reintenta (5 s… hasta 60 s) sin cerrarse. Log en `C:\KoroshiImpresion\log\`, 14 días.
- Arranca con una **tarea programada al iniciar sesión** del usuario del portátil (no servicio: los servicios suelen
  no ver la impresora USB ni su papel 4x6) y se relanza si se cae.
- `C:\KoroshiImpresion\config.ini`: URL, base de datos, usuario **Almacén Nath**, código `EXP1` y nombre de la
  impresora en Windows. La contraseña (o clave de API, si la cuenta la tiene) va en el **Administrador de
  credenciales de Windows**, nunca en el fichero ni en el repo. Almacén Nath es administrador: el agente solo llama a
  los tres métodos de la cola (lista blanca en el propio agente).

## 6. Módulos y orden (cambio en dos módulos: lo aviso antes de empezar, regla 6)

1. **`koroshi_impresion` 1.0.0** (nuevo): cola + menú. Instalar (módulo nuevo, no actualiza otros).
2. **Agente**: probarlo en este PC contra producción con «Microsoft Print to PDF», imprimiendo un PDF ya existente
   (solo lectura). Después instalarlo en el portátil con Isaac delante y sacar una etiqueta ya hecha (reimprimir).
3. **`koroshi_transportista` 1.0.0** (nuevo, depende de `koroshi_impresion`, `koroshi_xpo_bultos`, `delivery_gls_asm`,
   `delivery_xpo`): pantalla Transportista + botón en el área Expediciones (como Juntar cajas, id 18). Tests sin Odoo
   de la comparación leídas/esperadas y de la lógica 1834. Probado con simulacro de pantalla.
4. **Primera prueba real**: registrar en GLS/XPO **no es reversible**, así que la primera es una tienda de verdad a la
   hora de etiquetar, con Isaac o un jefe delante, comparando con lo que habría salido desde el portátil. Antes, solo
   lectura: escanear las CJ de una tienda ya etiquetada y ver que la pantalla dice «ya tiene tracking» y reimprime.

Modelo: por CLAUDE.md esto es diseño y dos módulos con stock y transportistas: Fable u Opus en esfuerzo alto.

## 7. Riesgos

- **Doble registro en GLS/XPO** (PDA y portátil a la vez): la comprobación de tracking justo antes y un bloqueo por
  tienda en el servidor; GLS -70 se trata como en la 1834.
- **El PDF de XPO**: si cada OUT de la expedición lleva su `LabelXPO_` con las mismas etiquetas, se imprimiría
  repetido: hay que confirmarlo leyendo `delivery_xpo` (P1).
- **Escala de la Zebra**: el papel 4x6 del controlador de Windows del portátil; se prueba con una reimpresión antes.
- Lo que se haga desde la PDA tiene que cuadrar con el cierre del camión XPO y `koroshi_s4t_envios` (usan el tracking
  y los bultos de las OUT, que se escriben igual que hoy).

## 8. Preguntas para Isaac

- **P1. XPO hoy**: ¿con qué botón o acción sacáis la etiqueta XPO en el portátil (selección de varias OUT en la lista
  + «Enviar al expedidor», otra acción de servidor…)? Para copiarla bien necesito leer `delivery_xpo` del servidor
  (solo leer, con tu sí) o que me digas el número de acción.
- **P2. Si no cuadran las cajas** (falta una CJ por escanear, o sobra una): ¿bloquear «Imprimir etiquetas» hasta que
  cuadre (propuesta), o dejar imprimir con un aviso y la confirmación del operario?
- **P3. Qué es «una expedición»**: ¿todas las OUT pendientes de la tienda (como la 1834, una por cliente; propuesta) o
  solo las del pedido de las CJ escaneadas?
- **P4. OUT de días anteriores** sin etiqueta de la misma tienda: ¿entran en la misma expedición (propuesta: sí, marcadas
  en la pantalla) o se dejan fuera?
- **P5. «Si no hay nada en cola»**: ¿lo entiendo bien (imprime por orden y, si no hay nada delante, al momento)?
- **P6. El portátil**: ¿modelo de la Zebra y nombre con que sale en Windows? ¿Está siempre encendido con la sesión
  abierta mientras se trabaja?
