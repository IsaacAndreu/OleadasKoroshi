# Resumen del trabajo 06/11 – 11/11/2026 (KOROSHI en Odoo 13)

Documento para pasar el contexto a otra sesión de Claude. Odoo: `nath.tuctuc.com`, compañía 8 (EFFEC), almacén
6665 STOCK GENERAL KOROSHI. Repo: `IsaacAndreu/OleadasKoroshi`. Copias con fecha en `bin/versiones/`.

## Reglas de trabajo (siguen vigentes)

- Escribir en Odoo **solo con aprobación explícita** del usuario. No borrar datos. Nunca pulsar «Forzar disponibilidad».
- No mostrar contraseñas ni repetir datos personales de clientes.
- **Nunca sobrescribir versiones**: cada fichero nuevo con fecha (y hora) en `bin/versiones/`.
- Commit/push solo cuando el usuario lo pide. Instalar módulos fuera del horario de trabajo.
- Cambiar `MODO` (DIAGNOSTICO/REAL) en las acciones con mucho cuidado.
- Pruebas en OUT reales: reversibles (leer y deshacer; sin cajas ni validar).
- Todo lo que se crea (módulos, textos, docs, scripts) en **castellano**; con el usuario se puede hablar en catalán.
- Llamadas RPC desde el navegador: `fetch('/web/dataset/call_kw')` con `context:{allowed_company_ids:[8]}`;
  si la sesión caduca, pedir al usuario que entre de nuevo.

## 1. Zonas (partir OUT por zonas)

- **Prueba Z-0611 (06/11):** 5 OUT en 3 zonas. Bultos correctos; no se juntaron matrículas.
  - Los «-29 bultos» de la OUT 23442: el contador `number_of_packages` (módulo `delivery_package_number`) suma/resta 1
    al poner/quitar caja y puede quedar negativo mientras se cancelan matrículas; se corrige al validar.
  - Cajas por **volumen**: una caja llena ≈ **0,084 m³** de `product.volume` (caja de 80 L, ~10 uds).
  - La caja de 4 uds fue un «pico» que no se podía llenar con lo que quedaba.
- **Resumen de todas las pruebas** (21/10, 22/10, 27/10 R1 y R2, 06/11): `bin/versiones/20261106_1630_resum-proves-zones_v1.html`.
- **Producción:** cron **202** lanza la acción **1883** «KOROSHI Partir OUT zonas v12 REAL» (v12f, MODO REAL) cada día a
  las 04:00 UTC. v12 «caja cerrada»: corta cada OUT para que la última caja llegue al 80 % de 80 L (casi 90 % de cajas
  cerradas). La acción **1881** es el diagnóstico con la misma lógica (publica en un canal). Comprobado activo el 11/11.
- Copias anteriores: `bin/versiones/20261110_accion_188x_v12d_ANTES-de-v12f.py`.

## 2. Sincronización con S4T (Koroshi)

- **S-6665003781 no se enviaba:** nombre de caja doblado (`CJxxxxCJxxxx`) → S4T rechaza con «KO: None». Se corrigió el
  nombre y se sincronizó (`sale.order.action_s4t_manual_sync`; campos `x_s4t_status` READY/ERROR/PENDING y `x_s4t_last_log`).
- **Acción automática 20** (acción de servidor 1873, modelo `stock.quant.package`, campo `name`), renombrada
  «KOROSHI - Bloquear matriculas CJ duplicadas o mal leidas». v2: si el nombre contiene CJ y no es exactamente `CJ` + 9
  dígitos, bloquea con aviso «Matricula mal leida»; además bloquea duplicados.
  Copias: `bin/versiones/20261106_1120_accion-auto-20_bloquear-matriculas-CJ_v1-COPIA-produccion.py` y `..._v2-formato.py`.
- **Acción 1800 v2 (11/11)**, lanzada por el cron **186** cada 15 min (reactivado el 11/11, estuvo pausado desde el 06/11
  por las pruebas de zonas): solo envía pedidos con **todas** las OUT hechas **y** con transportista (`carrier_id`) y
  etiqueta (`carrier_tracking_ref`). Los demás se cuentan como «sin transportista o sin etiqueta» en el Registro.
  `SOLO_CON_TRANSPORTISTA = False` vuelve a la v1; `DIAGNOSTICO = True` no envía nada.
  Copias: `bin/versiones/20261111_accion-1800_sync-pedidos-s4t_v1-COPIA-produccion.py` y `..._v2-solo-con-transportista.py`.
  Se enviaron a mano S-6665004035 (K10) y S-6665004042 (K9), con matrículas juntadas (correcto según el usuario).
  S-6665003356 y 3359 (21/10) nunca tendrán etiqueta: salen siempre como saltados.

## 3. Faltantes

Idea del usuario: el operario debe poder cerrar el pedido aunque falte una prenda; después, con calma, alguien
comprueba si la falta es real. Primero buscar el artículo en una ubicación cercana; si no está, moverlo a una
ubicación «FALTAS-REVISAR» en vez de ajustar inventario. Se desarrolla en el módulo `koroshi_faltantes`
(propuesta: `bin/versiones/20261109_1130_PROPUESTA_koroshi_faltantes_v1.md`) y en «Preparación en Lecturas»
(`koroshi_preparacion`, planes v3.x del 10/11).

## 4. Monitor (`koroshi_monitor`) v1.19.2

- v1.19: menú «Consulta de envíos» (Tiendas: XPO SAS/GLS; Web: GLS/SEUR), compara bultos declarados con cajas CJ
  reales, Excel por fechas. Solo lectura. Ficheros nuevos: `controllers/envios.py`, `static/src/js/envios.js`,
  `static/src/css/envios.css`.
- v1.19.1: en zonas, cada OUT abierta cuenta como una persona en «Personas y horas».
- v1.19.2: botón «Consulta envíos / Excel» en la cabecera del Monitor picking.
- Zips: `bin/versiones/20261111_koroshi_monitor_v1.19.1.zip` y `..._v1.19.2.zip`; scripts de actualización
  `bin/actualizar_koroshi_monitor_v1.19.x_autonomo.sh`.
- 11/11: el usuario lo desinstaló porque «Inventario daba error» y se **reinstaló** (`button_immediate_install`).
  Funciona; ids de acción nuevos 1914 y 1915 (nada usaba los antiguos 1846 y 1913).

## 5. PENDIENTE: error de Inventario en móvil/PDA

`TypeError: this.$el.swipe is not a function at Class._enableSwipe (web.assets_backend.js)` al abrir Inventario
(acción 216, kanban de `stock.picking.type`) en pantalla móvil, a veces al iniciar sesión.

- Es código estándar de Odoo (`web.KanbanRendererMobile._enableSwipe`, usa `jquery.touchSwipe`). Ninguno de
  nuestros módulos toca swipe, jQuery ni `loadJS`.
- `KanbanView.init` (y `BaseSettingView`) añaden `/web/static/lib/jquery.touchSwipe/jquery.touchSwipe.js` a `jsLibs`
  en móvil; `getController` espera `ajax.loadLibs`. Un solo jQuery 3.3.1.
- Reproducido varias veces en 375 px antes; en las últimas pruebas (recarga directa a Inventario y Operarios →
  Inventario) **cargó bien** y el swipe se aplicó. En una carga anterior touchSwipe se pidió **dos veces**.
- Hipótesis (sin confirmar): carrera en la primera carga — `ajax.loadJS` da por cargada la librería si ya existe la
  etiqueta `<script>` aunque aún no haya terminado, y el kanban llama a `.swipe` antes de tiempo.
- No se ha cambiado nada en Odoo. Propuesta pendiente de aprobación: pequeño guard en un módulo nuestro
  (`KanbanRenderer.include({_enableSwipe: ...})` que, si `$.fn.swipe` no existe, carga la librería y reintenta o
  se salta el swipe), instalado fuera de horario. Pedir al usuario si en la PDA el error desaparece al recargar.
- La sesión de inicio de la PDA lleva a la pantalla «Operarios» (acción 1891, «Lee tu tarjeta»).

## 6. Otros

- **Matriz Excel de compactación** (transcripts «Carrer Po 44/45» + MASTER OI 26/27 v3): se hizo el resumen de lo que
  debe tener; se ofreció crear el Excel base (Parámetros, Tipos de hueco, Artículo/talla, Modelo, Simulación de pedido
  tipo). **Esperando respuesta.**
- Prefijo 2621 = temporada I27.
- Job de Zalando S-6665003972 (deadlock en la cola): se preguntó si posponerlo a las 19:00; sin respuesta.
- PDA módulo nuevo vs app Código de barras: aún sin datos para comparar velocidad.
