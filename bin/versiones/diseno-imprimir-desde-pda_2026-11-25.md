# Diseño v1: imprimir desde la PDA en la impresora de un PC del almacén (25/11/2026)

Lo pide Isaac el 25/11 (desde la sesión de Juntar cajas). Idea ya acordada el 11/11 y aplazada («ja ho farem»).
**Solo diseño: no hay código. Espera el visto bueno de Isaac y las respuestas de la sección 8.**

## 1. El problema

Las impresoras de etiquetas van por USB a PC del almacén (sin red propia). La PDA habla con Odoo, no con el PC, así
que no puede imprimir. Hace falta que Odoo guarde «hay que imprimir esto en tal impresora» y que un programa en ese PC
lo recoja y lo mande a su impresora local.

```
PDA ──botón «Imprimir»──> Odoo: trabajo en cola (pendiente)
                               ^             │
                               │ cada 3 s    │ PDF
                     agente en el PC ────────┘──> impresora USB (Zebra 4x6 / láser)
                               └── marca impreso / error
```

## 2. Cómo se imprime hoy (para no duplicar)

Todo es **PDF de un informe QWeb** abierto en el navegador de un PC y mandado a mano a la impresora:

| Qué | Informe (`report_name`) | Dónde se lanza |
|---|---|---|
| Etiqueta de zona / matrícula CJ de la OUT | `koroshi.report_etiqueta_zona` (registros `zebra.label`, nota «ETQ ZONA <OUT>») | `koroshi_zonas/models/etiquetas.py:108`, Lecturas `koroshi_preparacion/models/lectura.py:845`, agrupación `agrupacion.py:446` |
| Albarán | `stock.report_deliveryslip` | `lectura.py:859`, `agrupacion.py:450` |
| Listas de picking (Web, Zalando, About You, INT) | `stock.report_picking`, `stock_picking_batch.report_picking_batch` | Monitor, sección «Imprimir» `koroshi_monitor/models/imprimir.py:85` |
| Huecos y contenedores | `koroshi_ubicaciones.etiqueta_ubicacion` (papel 4x6, 102x152 mm) | `koroshi_ubicaciones/models/crear.py:157` |
| Cajas de recepción | `koroshi_recepcion.etiqueta_tanda` (mismo papel 4x6) | `koroshi_recepcion/models/recepcion.py:626` |

No existe ningún módulo `koroshi_zebra` ni nada que mande ZPL. **Conclusión:** la cola no inventa etiquetas nuevas:
guarda «informe X de los registros Y» y el agente baja ese mismo PDF que hoy se abre a mano. Así cualquier informe que
ya existe se puede mandar a la cola sin tocar su diseño.

## 3. Módulo nuevo `koroshi_impresion` (pequeño, depende de `koroshi_base`)

No añade campos a `stock.picking`, `stock.picking.type` ni `stock.move.line` (regla 7). Dos modelos propios:

**`koroshi.impresora`** (la lista de impresoras; se da de alta a mano, una vez):
- `name` («Zebra Expediciones»), `codigo` (corto, el que usa el agente: `EXP1`), `puesto` (texto: «PC de
  Expediciones»), `tipo` (`zebra_4x6` / `laser_a4`), `activa`.
- `ultimo_contacto` (fecha-hora): lo escribe el agente en cada vuelta. Si hace más de 1 min, la PDA avisa «la
  impresora EXP1 no está conectada» en vez de dejar el trabajo esperando sin decir nada.

**`koroshi.impresion.trabajo`** (la cola):
- `impresora_id`, `informe` (`report_name`, p. ej. `koroshi.report_etiqueta_zona`), `modelo` + `ids_registros`
  (texto «12,13,14»), `copias`, `descripcion` («Etiquetas CJ de OUT/12345»).
- `formato`: `pdf` (lo de hoy). Se deja hueco para `zpl` (texto ZPL que se manda en crudo) por si un día se quiere,
  pero **la v1 solo hace PDF**.
- `estado`: `pendiente` → `imprimiendo` → `impreso` / `error`; `error_texto`, `intentos`.
- `usuario_id` (quién lo pidió, el operario de la PDA), `create_date`, `fecha_impreso`.
- `company_id` = compañía 8 (de `comun`).

**Métodos** (lo único que llaman la PDA y el agente):
- `encolar(impresora_codigo, informe, modelo, ids, copias=1, descripcion='')` → crea el trabajo; comprueba que el
  informe existe y que la impresora está activa; devuelve `{id, aviso}` (aviso si la impresora lleva rato sin contacto).
- `siguientes(impresora_codigo)` (agente) → marca `ultimo_contacto`, coge hasta 5 trabajos `pendiente` de esa
  impresora, los pasa a `imprimiendo` con bloqueo (`FOR UPDATE SKIP LOCKED`, por si hay dos agentes con el mismo
  código) y devuelve `[{id, informe, ids, copias}]`.
- `pdf(trabajo_id)` (agente) → genera el PDF con `render_qweb_pdf` en el servidor y lo devuelve en base64. Así el
  agente no necesita sesión web ni el truco de `allowed_company_ids` de la URL.
- `hecho(trabajo_id, ok, texto='')` (agente) → `impreso` o `error` (con texto). Un trabajo en `imprimiendo` más de
  5 min vuelve a `pendiente` (el PC se apagó a mitad); a los 3 intentos queda en `error`.
- Cron de limpieza: borra los `impreso` de más de 30 días.

**Pantallas en Odoo:** menú «Impresión» (en KOROSHI / Configuración) con impresoras y cola (lista con filtro de
errores y botón «Reintentar»). Nada más.

## 4. Botón en la PDA

Un widget JS común en el módulo (`koroshi_impresion/static/src/js/imprimir.js`): un botón «Imprimir» que abre un
selector de impresora (recuerda la última en el `localStorage` de la PDA) y llama a `encolar`. Cada pantalla que lo
quiera solo le pasa `informe`, `modelo` e `ids`. Respuesta en pantalla: «Enviado a Zebra Expediciones» o el aviso.

Primera pantalla: la que diga Isaac (pregunta P3). Las que hoy ya abren un PDF y son candidatas:
- **Lecturas / Preparación**: el «Imprimir» de hoy (`lectura.py:842`) que abre el PDF en la PDA y no sirve de nada
  allí. Cambiarlo a la cola es el caso más claro.
- **Juntar cajas** (Expediciones): reimprimir la etiqueta CJ de la caja que queda.
- Monitor (sección «Imprimir»): ya imprime bien desde un PC; no hace falta la cola salvo que se quiera mandar a otra
  impresora.

Cada pantalla que lo use es **un cambio en su módulo, con su versión**, después de instalar `koroshi_impresion`.
Si `koroshi_impresion` no está instalado, el botón no sale (comprobación como la de `zebra.label` en `etiquetas.py:36`).

## 5. Agente en el PC (Windows)

Un script Python de un fichero, `agente_impresion.py`, en `bin/agente_impresion/` del repo (sin credenciales). En el PC
se empaqueta con PyInstaller en un `.exe` para no instalar Python (el `.exe` no va en git, como los ZIP).

- **Bucle:** cada 3 s llama a `siguientes` por **JSON-RPC** (`/jsonrpc`, `execute_kw`). Si hay trabajo: `pdf`,
  guarda el PDF en una carpeta temporal, imprime, llama a `hecho`, borra el PDF. Coste: 1 llamada ligera cada 3 s por
  PC, despreciable para el servidor. El long-polling del bus de Odoo es más inmediato pero más frágil (sesión web,
  canales, reconexiones); 3 s de espera en el almacén no se notan. Se puede pasar al bus más adelante sin cambiar el
  modelo.
- **Imprimir PDF:** con **SumatraPDF** portable (`SumatraPDF.exe -print-to "<impresora>" -print-settings
  "noscale,<copias>x" -silent fichero.pdf`). Es lo más fiable en silencio en Windows, sin abrir ventanas; Adobe deja
  ventanas abiertas. Para la Zebra 4x6, el papel del controlador de Windows tiene que estar a 4x6 (102x152 mm), como
  hoy. Si un día se usa ZPL: envío RAW con `win32print` al nombre de la impresora (sin Sumatra).
- **Red:** si Odoo no responde, espera 5 s, 10 s, 30 s... hasta 60 s y sigue probando; nunca se cierra. Si la
  impresora da error (sin papel, apagada), marca el trabajo en `error` con el texto de Windows.
- **Log local:** `C:\KoroshiImpresion\log\agente_AAAAMMDD.log`, se guardan 14 días.
- **Arranque:** tarea programada de Windows «al iniciar sesión» del usuario del PC (no servicio: un servicio corre en
  la sesión 0 y a menudo no ve las impresoras USB del usuario ni su configuración de papel). Se reinicia sola si se
  cae (opción «si la tarea falla, reiniciar cada 1 min»).
- **Config local** `C:\KoroshiImpresion\config.ini` (fuera del repo): URL, base de datos, usuario, código de la
  impresora en Odoo (`EXP1`) y nombre de la impresora en Windows (`ZDesigner GK420d`). Un PC con dos impresoras = dos
  secciones, un bucle.

## 6. Credenciales

- Nunca en el código ni en el repo. La contraseña (o mejor una **clave de API** del usuario, si esta versión de
  Odoo 13 EE la tiene en Preferencias → Seguridad de la cuenta) se guarda en el **Administrador de credenciales de
  Windows** (`keyring`), como el programa de redistribución. `config.ini` solo lleva el usuario.
- No se crean usuarios nuevos en Odoo (se pagan). **Con qué usuario se conecta: pregunta P5.** El agente solo puede
  llamar a los cuatro métodos de la sección 3 (lista blanca en el propio agente) y los métodos comprueban en el
  servidor que solo tocan la cola; aunque el usuario pueda escribir, el agente no escribe nada más.

## 7. Plan de entrega

1. `koroshi_impresion` 1.0.0: modelos, métodos, menú, widget JS. Tests sin Odoo de la lógica de la cola. Instalar
   (módulo nuevo: no actualiza otros). Dar de alta una impresora de prueba.
2. Agente: probarlo primero en este PC contra producción con una impresora de prueba (o «Microsoft Print to PDF»),
   mandando a la cola un informe de solo lectura (una etiqueta de ubicación ya existente). No toca stock.
3. Instalar el agente en el primer PC (con Isaac delante: SumatraPDF, `.exe`, tarea programada, credencial).
4. Primera pantalla de la PDA con el botón (versión de su módulo).
5. Las demás pantallas, una a una.

Riesgos: (a) la Zebra imprime a otra escala si su papel en Windows no está a 4x6: se prueba con una etiqueta antes de
dejarlo; (b) si el PC está apagado los trabajos esperan (la PDA lo avisa por `ultimo_contacto`); (c) un PDF grande
(lista de picking de 30 páginas) tarda unos segundos en generarse en el servidor: igual que hoy al abrirlo.

## 8. Preguntas para Isaac

- **P1. Qué etiquetas primero.** ¿Matrícula CJ / etiqueta de zona de la OUT, albarán, etiquetas de transportista
  GLS/XPO (¿de dónde salen hoy: PDF adjunto en la OUT, web de GLS?), etiquetas de contenedor/lineal, listas de
  picking...? Propuesta: CJ / etiqueta de zona (ya es un informe de Odoo).
- **P2. Qué PC e impresoras.** ¿Cuántos PC con impresora y dónde (Expediciones, Recepciones, picking...)? ¿Modelo
  de cada una (Zebra cuál, láser cuál) y si en Windows ya tienen el papel 4x6 puesto?
- **P3. Qué pantalla de la PDA lleva el botón primero.** Propuesta: Lecturas / Preparación (cambiar su «Imprimir»
  actual) o Juntar cajas.
- **P4. Cómo se elige la impresora.** (a) El operario la elige en la PDA y la PDA la recuerda (propuesta); (b) fija
  por pantalla (Expediciones → Zebra de Expediciones); (c) fija por operario.
- **P5. Con qué usuario de Odoo se conecta el agente.** ¿Departament IT, como el programa de redistribución? ¿O el
  usuario que ya está abierto en ese PC?
- **P6. Windows de los PC**: ¿Windows 10/11, se puede instalar SumatraPDF portable y crear una tarea programada (hace
  falta administrador)? ¿El PC queda siempre encendido con la sesión abierta?
- **P7. Formato.** ¿Vale seguir con PDF (lo de hoy) o alguna Zebra va mejor con ZPL? Propuesta: PDF en la v1.
