# Prompt para /goal: Faltantes v1.3 + Operarios v2.2 + investigar la validación (09/11/2026)

Trabajas en `C:\dev\OleadasKoroshi` (Windows). Odoo 13 Enterprise en https://nath.tuctuc.com, empresa 8 (EFFEC).
En el panel del navegador hay una sesión abierta como **Departament IT (uid 2)**. Para leer Odoo usa JSON-RPC desde esa
pestaña (`/web/dataset/call_kw`, contexto `allowed_company_ids: [8]`).

Instalado el 09/11: `koroshi_operarios` **v2.1** (13.0.2.1.0) y `koroshi_faltantes` **v1.2** (13.0.1.2.0). Código en
`odoo/modulos/koroshi_operarios` y `odoo/modulos/koroshi_faltantes`. Lee los dos README y
`bin/versiones/20261109_DISENO_koroshi_operarios_v2.md` antes de empezar.

## Normas (obligatorias)

- **Todo lo que crees en castellano:** código, textos de pantalla, README, planes de prueba y scripts.
- **No escribir en Odoo** (ni instalar, actualizar, validar, reservar o cambiar registros) sin un OK explícito del
  usuario en el chat. Leer sí se puede.
- **Nunca** pulsar «Forzar disponibilidad», validar OUT reales ni escribir `stock.quant` a mano.
- **No modificar la app `stock_barcode`** ni añadir campos a `stock.picking`, `stock.move`, `stock.move.line`,
  `stock.picking.batch` ni `stock.picking.type`.
- No borrar datos. No enseñar contraseñas.
- Versiones nuevas con fecha en el nombre y **sin sobrescribir** las anteriores (`bin/`, `bin/versiones/`).
- No hacer commit. No instalar: se deja todo listo y el usuario lo sube fuera de horas.
- **Mañana el almacén tiene que trabajar igual que hoy.** Nada de esto puede cambiar lo que ven las PDA del usuario
  «Almacén Nath» hasta que el usuario lo pida.

## Parte A · Faltantes v1.3: los faltantes se marcan al final de la OUT, sin leer el EAN

Cómo trabajan: hacen toda la OUT en la app de código de barras y, **al final**, lo que no han encontrado se marca como
faltante. El problema de ahora es que la pantalla pide el EAN, y si la pieza no está no hay EAN que leer; por eso
tampoco llega a salir el botón «No está en ningún sitio».

Nuevo flujo (desde el botón **Faltante** de Lecturas (PDA), con la OUT ya puesta, o leyendo la OUT en Faltante (PDA)):

1. **Lista de lo que falta por coger** de la OUT (o de su agrupación `Z-`): las líneas con menos uds leídas que
   reservadas y no hechas ni canceladas. Por línea: **referencia corta** en grande (p. ej. `2621JA…`, el
   `default_code`), color y talla, ubicación (`L77 P38 C2`) y uds pendientes. Ordenadas en el orden del recorrido de
   la app de código de barras (comprobar cuál es en su código).
2. El operario **marca una o varias** líneas (las que no ha encontrado) y pulsa **Continuar**. Se van resolviendo de
   una en una.
3. Para cada línea, en vez de la lista de 5 ubicaciones, **una sola recomendación**: la ubicación con stock libre más
   cercana (la primera que ya da `alternativas()`), con sus uds libres.
   - Si la encuentra allí: **lee la ubicación** → `reubicar` (como ahora).
   - Si tampoco está: botón **«Tampoco está aquí»** → se pregunta una vez más («¿No está en ninguna ubicación?»,
     dos pulsaciones) → `sin_alternativa` (como ahora: la unidad va a FALTANT y la línea queda sin reserva).
   - Si no hay ninguna ubicación con stock libre: directamente **«No está en ninguna ubicación»**.
   - Opcional, no por defecto: un enlace pequeño «Ver más ubicaciones» con la lista de antes.
4. Al acabar todas las marcadas: resumen («3 faltantes: 1 reubicado, 2 a FALTANT») y **validar la OUT**:
   - Si ya no queda **nada pendiente** (todo leído, o sin reserva por «No está en ninguna ubicación»), la OUT se
     **valida sola** desde el servidor, con la validación normal de Odoo (no escribir movimientos a mano) y con la
     **misma decisión de pedido pendiente (backorder) que toman ahora** en el almacén: sácala de la Parte C (hazla
     antes). Si los datos no lo dejan claro, pregunta al usuario antes de programarlo.
   - Además, un botón grande **«Validar OUT»** para validarla a mano (por si la validación sola falla o la
     desactivan). Interruptor en los parámetros del sistema para encender o apagar la validación sola.
   - Si aún quedan líneas pendientes que no se han marcado: no valida; avisa «Quedan N líneas por coger» con
     **Volver a la OUT**.
   - OUT de una agrupación `Z-`: investiga cómo se valida una OUT suelta dentro de la agrupación sin romper el
     «procesar agrupación» y sin validar las demás OUT. Si no es seguro, solo **Volver a la agrupación**.
   - Si la validación da error (stock, otra PDA, etc.), mensaje en rojo con el motivo y **Volver a la OUT**; no
     reintentar solo.
   - Al validar, cerrar la tarea del operario y su asignación (como ya hace el cron de Operarios).
5. Leer el EAN sigue funcionando en la lista (salta a esa línea), y la tarjeta del operario se puede leer en cualquier
   momento.
6. **Líneas con una parte leída** (p. ej. reservadas 2, leídas 1): hoy `comprobar_linea` las rechaza. Investiga si se
   puede tratar solo la parte no leída de forma segura, igual que hace Odoo al partir líneas. Si es seguro, hazlo; si
   no, que salga en la lista con un aviso claro de qué hacer.

Entregables: `koroshi_faltantes` **13.0.1.3.0**, ZIP `bin/20261109_koroshi_faltantes_v1.3.zip`, README y descripción
del manifiesto con la v1.3, CSS para la PDA (botones grandes, se usa con el dedo).

## Parte B · Operarios v2.2: Lecturas (PDA) al entrar y tarjeta obligatoria, solo para probar con Departament IT

1. Grupo nuevo **«KOROSHI Operarios: tarjeta obligatoria»** (al instalar no tiene a nadie). Para los usuarios de ese
   grupo, en Lecturas (PDA):
   - sin tarjeta **no se abre ninguna OUT**: «Lee primero tu tarjeta»;
   - comprobarlo también en el servidor (rutas `/koroshi/operarios/leer` y las que abren pedidos), no solo en el JS.
   - Los demás usuarios siguen exactamente igual que en la v2.1 (sin tarjeta la OUT se abre y no cuenta).
2. **Elegir una OUT la abre directamente.** En el almacén al elegir o leer una OUT les salen las 3 opciones
   (Continuar / Saltar / Faltante) en vez de entrar en la OUT. Revisa todos los casos de
   `operarios_pantalla.js` (`start` con operario guardado, leer tarjeta, leer OUT, volver de la app con
   `on_attach_callback`, recargar la página) y haz que **siempre que el operario elige, lee o le toca una OUT, se
   abra directamente** en la app de código de barras. Las 3 opciones solo deben salir cuando vuelve con la
   **flecha atrás sin haber validado** (es cuando las necesita, para el faltante). Para todos los usuarios, no solo
   el grupo nuevo.
3. El botón **Menú** de Lecturas lleva al menú de código de barras (inventarios, etc.). Documenta que desde allí se
   puede abrir una OUT sin tarjeta y que eso no se puede impedir sin tocar `stock_barcode`.
4. Para la prueba, **solo con el OK del usuario en el chat**: poner a **Departament IT (uid 2)** en el grupo y su
   **Acción inicial = «Operarios»** (acción de cliente 1891). Deja escrito en el plan de prueba cómo quitarlo
   (vaciar Acción inicial y sacar del grupo). **No tocar «Almacén Nath».**

Entregables: `koroshi_operarios` **13.0.2.2.0**, ZIP `bin/20261109_koroshi_operarios_v2.2.zip`, README y manifiesto.

## Parte C · Investigar la validación al final de la OUT (hacerla primero; no cambiar nada en la app de código de barras)

Lo que piden en el almacén: al acabar un pedido hay que ir al principio o al final de la OUT para encontrar
**Validar**. Quieren un botón que lleve a validar, o que se valide sola si no queda nada pendiente, y si hay faltas
que pregunte lo del **parcial** (pedido pendiente / backorder).

1. Lee el código de la app de código de barras de Odoo 13 **tal como está en el servidor** (bundle
   `web.assets_backend` desde el navegador: `stock_barcode` `ClientAction`, `picking_client_action`, el botón y la
   acción de validar, el asistente de backorder) y de los módulos de terceros que lo cambian (p. ej.
   `stock_barcode_optimization` de Brain Station). Explica dónde está el botón, qué hace y qué pasa con faltas.
2. Mira en los datos cómo validan ahora (solo leer): en las OUT de tiendas de las 2 últimas semanas, cuántas se
   validaron con backorder y cuántas sin, y cómo quedan las líneas de «No está en ningún sitio» de Faltantes.
3. Propón opciones **sin tocar `stock_barcode`** (por ejemplo, al volver a Lecturas con la flecha: si todo está leído,
   botón grande **«Validar OUT»** que llama a la validación de Odoo desde el servidor; si hay faltas, «Faltante» o
   «Validar parcial» con la misma pregunta de backorder que hace Odoo) y, aparte, qué haría falta para ponerlo dentro
   de la app de código de barras. Para cada opción: riesgos, qué pasa con agrupaciones `Z-` y con dos PDA a la vez.
4. **No validar ninguna OUT real para probar.** Si para probar hace falta una OUT de prueba, explica cuál y pide OK.
5. La validación sola al acabar los faltantes se programa en la Parte A con lo que salga de aquí. El botón dentro
   de la app de código de barras queda solo como propuesta.
6. Escribe el informe en `bin/versiones/20261109_INFORME_validar_OUT_codigo_barras.md`.

## Al acabar

- Comprobaciones estáticas de los dos módulos: `py_compile`, parsear todos los XML, `node --check` de los JS, y el
  comprobador de referencias (si no está, haz uno: campos de las vistas, métodos de los botones, xml ids,
  `ir.model.access.csv`).
- Script de instalación nuevo: `bin/actualizar_koroshi_operarios_v2.2_faltantes_v1.3_2026-11-09.sh` (copiar del de la
  v2.1 + v1.2: `check` e `install`, un solo reinicio, pasos de Aplicaciones al final). `bash -n`.
- Plan de prueba: `bin/versiones/20261109_PRUEBA_faltantes_v1.3_operarios_v2.2.md`: con OUT de prueba y operarios
  Isaac (OP9990001) / Isaac2 (OP9980001), sin validar OUT reales, y cómo dejarlo todo como estaba.
- Resumen final en catalán para el usuario: qué está hecho, qué no se ha probado en Odoo, qué necesita su OK
  (instalar fuera de horas, poner a Departament IT en el grupo y la acción inicial) y lo que dice el informe de la
  Parte C.
