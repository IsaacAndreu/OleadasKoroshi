# Informe: validar una OUT al acabar, sin ir a la última página (09/11/2026)

Lo que piden en el almacén: al acabar un pedido hay que ir hasta el final de la OUT para encontrar **Validar**. Quieren
un botón que lleve a validar, o que se valide sola si no queda nada pendiente, y si hay faltas, que pregunte lo del
**parcial** (pedido pendiente).

Investigado leyendo el código JS que sirve el servidor (`web.assets_backend`, 09/11/2026) y los datos de Odoo (solo
lectura). **No se ha cambiado nada y no se ha validado ninguna OUT.**

## 1. Cómo funciona ahora la app de código de barras (Odoo 13)

- **Una página por ubicación.** La OUT se parte en páginas, una por cada ubicación de origen
  (`stock_barcode.ClientAction._makePages`). Las páginas se ordenan por el nombre completo de la ubicación
  (`_.sortBy(pages, 'location_name')`) y dentro de cada página van las líneas en su orden.
- **El botón Validar solo sale en la última página** (`stock_barcode.LinesWidget`: si no es la última página, se
  esconde `o_validate_page` y se enseña «Siguiente»). Por eso, con una OUT de 20 ubicaciones, hay que pasar hasta la
  última para validar.
- **Qué hace Validar** (`stock_barcode.picking_client_action._validate`): guarda lo leído (`_save`) y llama a
  `button_validate` del albarán en el servidor. Si Odoo devuelve un asistente, lo abre:
  - si queda algo sin leer → asistente de **pedido pendiente** («Crear pedido pendiente» / «Sin pedido pendiente»);
  - si no se ha leído nada → asistente de **transferencia inmediata**.
  Al acabar sale «The transfer has been validated» y vuelve a la pantalla de antes.
- **Códigos de barras de órdenes.** La app de código de barras ya trae órdenes que se ejecutan al leer un código, sin
  importar la página en la que esté (`_onBarcodeScannedHandler`: `this.commands[barcode]`):

  | Código de barras | Qué hace |
  |---|---|
  | `O-BTN.validate` | **Validar** (lo mismo que el botón de la última página, con sus asistentes) |
  | `O-BTN.pack` | Poner en paquete |
  | `O-BTN.cancel` | Cancelar |
  | `O-BTN.print-slip` / `O-BTN.print-op` | Imprimir albarán / operaciones |

  Ningún módulo de terceros (`stock_barcode_optimization`, `barcode_archive_location`) quita estas órdenes en las OUT
  sueltas.
- **Agrupaciones (`barcode_batch_process`, «procesar agrupación»).** Tiene su propia pantalla. Su lector
  (`_onBarcodeScannedHandler`) **no mira las órdenes**, así que leer `O-BTN.validate` no hace nada allí. Valida la
  agrupación con `action_validate` (datos de la operación), no OUT a OUT.

## 2. Cómo validan ahora (datos, OUT de tiendas, tipo 45)

| Desde | OUT validadas | Con pedido pendiente | Con alguna línea cancelada (sin pedido pendiente) |
|---|---|---|---|
| 26/10 | 1.009 | 25 | – |
| 02/11 | 411 | 24 | 45 |

- Pedidos pendientes creados desde el 26/10: 29 (26 siguen en espera, 2 hechos, 1 cancelado).
- Conclusión: **se hacen las dos cosas**; no hay una regla única. Por eso la validación desde Faltantes v1.3
  **pregunta lo mismo que Odoo** («¿Crear pedido pendiente?») en vez de decidirlo sola. Se puede fijar la respuesta
  con el parámetro del sistema `koroshi_faltantes.pedido_pendiente` (`preguntar` / `si` / `no`; de inicio
  `preguntar`).
- Faltantes «No está en ningún sitio»: la línea se queda **sin reserva** y la unidad va a FALTANT. Al validar, esa
  cantidad cuenta como «sin leer»: Odoo hace la pregunta del pedido pendiente.

## 3. Opciones

### A. Código `O-BTN.validate` impreso (sin programar nada) — recomendada para empezar

- Imprimir una etiqueta con el código de barras **`O-BTN.validate`** (Code 128) y pegarla en cada PDA, o en la
  mesa o al final del pasillo. Al acabar la OUT, leerla = Validar, desde cualquier página.
- Si queda algo sin leer, sale el mismo asistente de siempre (parcial).
- Riesgos: si se lee sin querer a mitad de OUT, sale la pregunta del parcial (se puede **descartar** y no pasa nada).
  **No funciona dentro de «procesar agrupación»** (Z-).
- No toca nada: ni módulos ni Odoo.

### B. Validar desde Lecturas (PDA) y desde Faltante — hecha en Faltantes v1.3 / Operarios v2.2

- Al acabar los faltantes, si ya no queda nada por coger, **se valida sola** (`button_validate` en el servidor). Si
  Odoo pide pedido pendiente, la PDA pregunta **«Sí, pedido pendiente» / «No, sin pedido pendiente»** (o usa el
  parámetro). Botón **«Validar OUT»** para hacerlo a mano.
- Si queda algo por coger: «Quedan N líneas por coger» y **Volver a la OUT**.
- Si Odoo devuelve otro asistente que no conocemos, **no se fuerza**: «Valídala en la app de código de barras».
- Interruptor `koroshi_faltantes.validar_sola` (`1` / `0`; de inicio `1`).
- Agrupaciones Z-: validar una OUT suelta dentro de la agrupación es posible en Odoo, pero la pantalla de «procesar
  agrupación» de otra PDA tendría datos viejos y la agrupación se valida entera con `action_validate`. **No se valida
  sola**: solo **Volver a la agrupación**.
- Dos PDA a la vez: `button_validate` falla si la OUT ya está validada; se enseña el motivo en rojo.
- Riesgo a probar: si algún módulo de terceros cambia `button_validate` en el servidor (no se puede ver desde el
  navegador). Probar con una OUT de prueba antes de usarlo.

### C. Botón «Validar» siempre visible dentro de la app de código de barras

- Haría falta un módulo que cambie `stock_barcode.LinesWidget` para que `o_validate_page` no se esconda en las
  páginas intermedias (o un botón flotante que llame a `_validate`). Son unas pocas líneas de JS.
- **Toca la app de código de barras**, que hasta ahora no se tocaba, y hay módulos de Brain Station encima
  (`stock_barcode_optimization`, `barcode_archive_location`). Riesgo de romper la PDA en plena temporada.
- Propuesta: dejarla para cuando baje la temporada, junto con el «Faltante» dentro de la propia OUT.

## 4. Recomendación

1. Ya: **opción A** (imprimir `O-BTN.validate`). Probarla con una OUT de prueba.
2. Con la v1.3 instalada: **opción B** para las OUT con faltantes.
3. Después de la temporada: valorar la **opción C**.
