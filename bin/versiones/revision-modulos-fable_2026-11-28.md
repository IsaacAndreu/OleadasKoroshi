# Revisión de todos los módulos (28/11/2026)

Revisión de **solo lectura** de `odoo/modulos` (rama `feat/tuctuc-pda`, HEAD `e71282a`) y de las herramientas de
`bin/`. Seis lecturas en paralelo, una por grupo de módulos, y después comprobación a mano de los hallazgos marcados
con ✔. **Nada se ha ejecutado en Odoo ni medido en el servidor**: todo sale de leer el código. Antes de arreglar
cualquier punto hay que abrir el código y confirmarlo (CLAUDE.md, regla 10).

No repite lo de `revision-general-fable_2026-11-23.md` (R, O, C) ni lo de
`revision-fable-compactacion-zonas-faltantes_2026-11-27_v1.md` (§), salvo lo que sigue abierto, que se cita.

Códigos: **Z** zonas, agrupaciones, retener y S4T · **E** expediciones, recepción, impresión, devoluciones,
actividades · **P** preparación y operarios · **F** contenedores, faltantes, recuentos, prenda en el suelo ·
**M** monitor, KPI, informe, menú, mapa · **H** base, módulos pequeños y herramientas · **T** módulos `tuctuc_*`.
Rutas desde `odoo/modulos/` salvo las de `bin/`. Gravedad / confianza entre corchetes.

## 1. Lo 12 más importante

| # | Código | Qué | Estado en el servidor |
|---|---|---|---|
| 1 | Z1 ✔ | Retener tiendas **cancela** pedidos grandes que aún no se han reservado | instalado, `cancelar_pocas` = 1 |
| 2 | Z2 ✔ | Envíos S4T: un 502/503 gasta los 5 intentos y saca el pedido del cron para siempre | en real cada 15 min |
| 3 | E1 ✔ | Métodos públicos con `sudo()` sin permiso: cualquier sesión crea expediciones, mueve cajas o crea stock por RPC | instalado |
| 4 | E2 | XPO: un reintento tras un fallo a medias crea una segunda expedición | instalado |
| 5 | E3 | Devoluciones: una tanda reintentada entra dos veces en stock | instalado |
| 6 | F1 | Contenedores 1.17: los cuatro puntos del §3.2 siguen igual | **sin instalar** |
| 7 | P1 | Validar una agrupación Z- va en una sola transacción: si falla una OUT se deshacen todas, pero sus envíos ya salieron | instalado |
| 8 | M1 ✔ | La caché del Monitor casi nunca acierta (una por worker, 20 s, y la pantalla pide cada 60 s) | instalado |
| 9 | H1 ✔ | Validar: `koroshi_caja_existente` busca la OUT dueña de cada caja una a una, hasta tres veces | instalado |
| 10 | P4 ✔ | `_bloquear` usa `FOR UPDATE`: choca con cualquier alta que apunte a la OUT («ocupada» sin motivo) | instalado |
| 11 | H7 | `comprobar.py` compila con Python 3.14 y el servidor corre 3.5/3.6 | herramienta |
| 12 | T1 | `tuctuc_operarios`: cada «siguiente pedido» carga casi toda `sale_order` como `NOT IN` | sin instalar |

**Medida inmediata sin código para el 1** (la decide Isaac): poner `koroshi_retener_tiendas.cancelar_pocas` = 0
hasta que salga el arreglo. Sigue avisando por correo y deja de cancelar.

## 2. Zonas, agrupaciones web, retener tiendas y S4T (Z)

**Z1 ✔ [ALTO / camino confirmado, hora probable] Retener cancela pedidos grandes sin reservar.**
`koroshi_retener_tiendas/models/retenido.py:106-123, 246-282`; `koroshi_s4t_pedidos/models/sale_order.py:60-62, 76-94`.
Un pedido b2b de 60 líneas o más se confirma con `koroshi_sin_reservar` y la reserva va en un job aparte
(`with_delay`, canal `root.s4t_sync`, capacidad 1). `retenido.py:121-122` calcula `reservadas` sumando
`reserved_availability`: si a las 04:40 o 05:45 el job sigue en cola o ha fallado, da 0, el pedido sale como «pocas
uds» y `_cancelar_outs` hace `action_cancel()`. Con el canal parado una noche se cancelan todos los grandes.
Arreglo: no cancelar (solo avisar) si el pedido tiene movimientos en estado por reservar sin intento de reserva
(job «S4T Reservar OUT» sin acabar) o si entró hace menos de N minutos. Prueba: `_pocas` con un pedido sin reservar.

**Z2 ✔ [ALTO / confirmado] Envíos S4T: 5xx, 429 y 409 cuentan como intento.**
`koroshi_s4t_envios/models/envio.py:285, 309-315, 318-329, 417-423`. R11 solo cubrió `RequestException`. Un 503
va a la rama `else`, suma intento y, como es «respuesta», pone `red_seguidos` a 0. Con S4T en 503 durante 75 min
cada envío llega a 5 intentos, manda correo y queda «atascado» hasta «Enviar ahora» pedido a pedido.
Arreglo: tratar 5xx y 429 como la red (no cuentan y cortan la pasada); el contador, solo para 4xx reintentables.

**Z3 [MEDIO-ALTO / confirmado en código] El reparto de zonas tardío parte OUT ya repartidas a un operario.**
`koroshi_zonas/models/lector.py:65-74`; `motor/v12f.py:100-113`; `models/ejecucion.py:749-779`. «En la cola de un
operario» solo se mira para OUT de días anteriores y `cron_partir` no tiene tope de hora. Tras un reinicio a las
04:50 el cron corre atrasado. Arreglo: mirar `en_cola` para todas y no partir pasada una hora límite configurable.

**Z4 [MEDIO / confirmado] Un fallo transitorio a las 04:50 deja el día sin reparto.**
`koroshi_zonas/models/ejecucion.py:632-651, 764-779, 795-825`. Queda en «error», un correo, y el vigilante de las
05:15 solo avisa. Arreglo: que el vigilante relance `lanzar('REAL')` una vez (las OUT ya partidas se saltan). Con Z3.

**Z5 [MEDIO / confirmado] Agrupaciones web: lo que «espera» por `max_pedidos` desaparece a los 3 días.**
`koroshi_agrupaciones_web/models/corte.py:115-116, 123-124, 206-212, 239-241`. Con un corte al día y más de 180
completas varios días, una OUT del día D ya no es candidata el D+4 (`dias_atras` = 3): ni se agrupa, ni se cancela,
ni sale en correo. Arreglo: no aplicar `dias_atras` a las completas sin agrupar y avisar de las que esperan.

**Z6 [MEDIO / confirmado, probabilidad baja] Traspasos S4T: una página descargada y no guardada se pierde.**
`koroshi_s4t_traspasos/models/traspaso.py:113-121, 143-148, 187-196, 316-323`. S4T marca vistos los 100 al
devolverlos; si después hay timeout, JSON roto o falla el `create` de la línea 145 (sin `try`), la conciliación solo
repasa hoy y ayer. `ultima_conciliacion` se apunta aunque fallen los GET. Arreglo: conciliar N días por parámetro (7)
y apuntar solo si no falló ningún GET.

**Z7 [MEDIO / confirmado] Retener: el modo «real» no retiene nada.** `retenido.py:83-95`; `regla.py:214-215`;
`koroshi_zonas/models/lector.py:57-63`. Nadie llama a `pickings_retenidos()`. Arreglo: no admitir «real» hasta que
exista el enganche en zonas, o que el correo lo diga.

**Z8 [MEDIO-BAJO / confirmado] Envíos: aviso de caída mal calculado y contadores a 0 en real.**
`envio.py:403, 416-427, 440-444, 454-465`. Hacen falta 3 fallos seguidos: con 1-2 pendientes nunca avisa, y puede
decir «S4T vuelve» con S4T caído. `enviados`/`errores` solo se suman en diagnóstico.

**Z9 [MEDIO-BAJO / confirmado] Zonas: dos correos de alarma falsos cada día sin reparto.**
`ejecucion.py:775-778, 816-824`. Tratar «vacío» y «pocas_uds» como resultado correcto.

**Z10 [MEDIO-BAJO / confirmado] Retener apunta la revisión antes de hacerla** (patrón R10) y se salta en silencio
si llega más de 60 min tarde. `retenido.py:323-327`; `regla.py:77-78`.

**Z11 [MEDIO-BAJO / patrón confirmado, coste sin medir] Lentitud.** (a) `sale_id.s_order_type_id.name` en
`koroshi_zonas/models/lector.py:57-63` y `koroshi_s4t_pedidos/models/prioridad.py:189-194`. (b)
`envio.py:376-386, 394-397, 409-414`: `terminados` y `atascados` leen todo el histórico cada 15 min y `desde` es fijo.

**Z12 [BAJO / confirmado] `_rellenar_campos` corre en cada `-u`** (`koroshi_zonas/data/rellenar.xml:5`,
`ejecucion.py:156-177`). Guardarla con un parámetro «ya hecho».

**Z13 [MEDIO / confirmado] Siguen abiertos §2.2 y §2.4, y lo mismo en otro módulo.** Crons sin `noupdate`:
`koroshi_zonas/data/cron.xml:2, 42, 84` y `koroshi_s4t_pedidos/data/cron.xml:2, 6-16`. `rendimiento` = 0 sin validar
(`config.py:103-117`, división en `motor/v12f.py:77-78`); `iter_equilibrio` = 0 rompe (`config.py:69`,
`motor/evaluar.py:303-322`).

**Z14 [BAJO / confirmado; salta el 22/10/2027] El prefijo `Z-ddmm-` no lleva año.** `lector.py:125`;
`v12f.py:314-326`; `ejecucion.py:228-229, 242-243`; `correo.py:64-65`. Filtrar por `create_date` del día.

**Z15 [MEDIO / confirmado] Sin pruebas lo que escribe stock o habla con S4T.** `s4t_envios`, `s4t_traspasos` y
`s4t_sync` no tienen carpeta de pruebas. Empezar por `requests` simulado (5xx, lista, timeout) y `_pocas` sin reservar.

Menores: nada limpia `datos_entrada`, las simulaciones diarias ni los `mail.mail` con `auto_delete=False`; todos los
avisos van a un buzón; `correo.send()` dentro de la transacción (patrón R18).

## 3. Expediciones, recepción, impresión, devoluciones y actividades (E)

**E1 ✔ [ALTO / confirmado] Métodos públicos con `sudo()` que se saltan permiso y tarjeta.**
`koroshi_impresion/models/impresion.py:93-132, 170-186`; `koroshi_transportista/models/transportista.py:415`;
`koroshi_juntar_cajas/models/juntar.py:274, 463`; `koroshi_devoluciones/models/devolucion.py:182`. El grupo y la
tarjeta solo se miran en el controlador; por `/web/dataset/call_kw` cualquier sesión los llama. `agente_pdf` con
`sudo` devuelve cualquier adjunto o informe QWeb. Arreglo: `pda.comprobar_grupo(self.env)` dentro de cada método (o
nombre con `_`); en impresión, lista blanca de informes y grupo propio para `agente_*`.

**E2 [ALTO / probable; `delivery_xpo` no está en el repo] XPO sin «ya existe».**
`transportista.py:490-514`. Si XPO registra y falla después, se deshace todo en Odoo y el reintento crea otra
expedición. Arreglo: «intento XPO en curso» por OUT con commit propio antes de llamar; si existe sin tracking, parar.

**E3 [ALTO / carrera confirmada, frecuencia baja] Devoluciones: tanda duplicada.**
`koroshi_devoluciones/models/devolucion.py:185-202`; `static/src/js/devoluciones.js:389-392`. «¿Ya existe la tanda?»
es un `search` sin candado ni único. Arreglo: `pg_advisory_xact_lock(hashtext(tanda))` o tabla con `unique(tanda)`.
`paquete.py:112` igual (solo duplica apuntes).

**E4 [MEDIO / probable] GLS recibe menos bultos que las cajas escaneadas.** `koroshi_transportista/logica.py:225-240`;
`transportista.py:522-533`. Una OUT con cajas y `number_of_packages` = 0 va a «juntadas». Arreglo: decidir por cajas
propias y bloquear si `rep['cajas'] != n_esperadas`.

**E5 [MEDIO / mecanismo confirmado] La etiqueta se hace y no se imprime si la petición tarda.**
`transportista.py:438, 471`. `inicio = now() - 2 s` se calcula tarde y el `create_date` del adjunto es el inicio de
la transacción. Arreglo: tomar `inicio` al principio o quedarse con adjuntos de id mayor que el máximo previo.
De paso: con token repetido la PDA pinta «undefined» (`:425`, `transportista.js:346-352, 589-590`).

**E6 [MEDIO / confirmado] «Recuperar etiqueta GLS» pone el tracking viejo a OUT nuevas.**
`transportista.py:595-622, 634-635`. Si `bultos_gls != rep['cajas']`, no escribir y mandar a la oficina.

**E7 [MEDIO / confirmado] El agente reimprime si falla el «hecho».** `bin/agente_impresion/agente_impresion.py:193-200`;
`impresion.py:141-148`. Sacar el «hecho» del `try` y reintentar solo eso.

**E8 [MEDIO / confirmado] La cola de impresión no caduca.** `impresion.py:93-132, 203-209`. Con el portátil apagado
sale todo junto al día siguiente; cada «Reimprimir» encola otro. Caducar pendientes de más de N horas y no duplicar.

**E9 [MEDIO / confirmado; R16 sin aplicar] Recepción: tarjeta sin validar y responsable que elige el cliente.**
`koroshi_recepcion/controllers/main.py:46-56`; `models/recepcion.py:923`. Usar `pda.empleado_valido`,
`pda.buscar_producto` (copia propia en `:58-74`) y comprobar el responsable dentro de `validar`.

**E10 [MEDIO / probable] Recepción: caja guardada durante la validación queda fuera de stock.**
`recepcion.py:585-605, 682, 717, 780` frente a `:923-1003`. `FOR UPDATE` de la recepción en `guardar_*`.

**E11 [MEDIO / confirmado] «Asignar al palé» se lleva las cajas de otra PDA.** `recepcion.py:607-622`;
`static/src/js/recepcion.js:694, 791-808`. Filtrar por operario.

**E12 ✔ [MEDIO / patrón confirmado] Transportista: consultas pesadas por caja leída.** `transportista.py:73-77`
(dominio con punto sobre `stock.move.line`; el propio fichero lo evita en `:288`), `:320-372` (`estado()` entero en
cada lectura), `:240-244`, `:174-181`. Alimenta a E5.

**E13 [MEDIO / probable] Recepción: cada caja recalcula toda la ficha.** `controllers/main.py:81-107`;
`recepcion.py:805-833`. Devolver solo contadores y guardar `clave_fisica`.

**E14 [MEDIO / probable] Etiquetas KO: el PDF de 500 etiquetas se genera cuando lo pide el agente (60 s).**
`impresion.py:181-186`; `agente_impresion.py:126`; `recepcion.py:45, 1336`. Generarlo al encolar.

**E15 [BAJO / probable] Recepción enseña la sesión caducada como «Sin conexión».** `recepcion.js:284-288, 185-187`.

**E16 [BAJO / confirmado] «+ KO» y «+1 caja» se duplican al reintentar.** `recepcion.js:656-661, 899-901`;
`controllers/main.py:392-417`.

**E17 [BAJO / confirmado] Juntar cajas.** `juntar.py:159-160, 208-226`: con OUT sin `origin`, `_recalcular_bultos(False)`
reescribe los bultos de todas las OUT sin origen. `:113`: `sorted()` con `False` y texto da 500. `:475-477`: crea
paquete con cualquier CJ sin mirar `zebra.label`; dos PDA crean dos paquetes iguales.

**E18 [BAJO / confirmado] Actividades y deuda común.** `koroshi_actividades/models/registro.py:347-361` (`cron_cerrar`
sin savepoint por tramo); `static/src/js/actividades.js:26, 386` (panel abierto 20 s); sin tests en devoluciones y
actividades; copias para `koroshi_base` (`_empleado_valido`, tarjeta y ráfaga de `recepcion.js:146-225`, `KO_/TT_`,
`CJ665`, `EFFEC/Stock/NAVE2`).

## 4. Preparación y operarios (P)

**P1 [ALTO / probable] Validar una agrupación Z- en una transacción.** `koroshi_preparacion/models/agrupacion.py:397-418`.
Solo captura `UserError`/`ValidationError` (`:405`). Otra excepción en la OUT 8, un reintento por serialización o el
tiempo máximo deshacen las 7 ya validadas con sus envíos a XPO/S4T ya hechos. La PDA abandona a los 90 s
(`preparacion.js:75, 1704-1710`). Arreglo: capturar `Exception` por OUT con log y `commit` tras cada OUT validada.

**P2 [ALTO lentitud / mecanismo confirmado] El tablero carga todas las OUT de salida de la historia.**
`koroshi_operarios/models/tablero.py:204-207` (`_lotes_vivos`), dos veces por minuto y tablero
(`tablero_areas.py:136-137, 202`) y desde la PDA con la cola vacía (`tablero.py:303`). Arreglo: una consulta SQL.

**P3 [MEDIO / confirmado] A dos, con pausa o «dejar»: la caja del que se queda se lleva lo del que se va.**
`koroshi_preparacion/models/lectura.py:445-454, 492-496`; `koroshi_operarios/models/reparto.py:732-735, 695-707`.

**P4 ✔ [MEDIO / confirmado] `_bloquear` con `FOR UPDATE NOWAIT`.** `lectura.py:706`. Es incompatible con el
`FOR KEY SHARE` de cada `INSERT` con clave ajena a `stock_picking`. Arreglo: `FOR NO KEY UPDATE NOWAIT`.

**P5 [MEDIO / confirmado; resto de R8] Zalando/About You: la caja automática queda cerrada si la validación falla.**
`lectura.py:1322-1330, 1362-1365, 1414-1416`.

**P6 [MEDIO / confirmado] §3.1 sigue abierto.** `lectura.py:567-568`; `agrupacion.py:124`; `preparacion.js:337-339`.

**P7 [MEDIO / probable] `_cjs_de_outs` busca `zebra.label` por `note` en cada lectura.** `agrupacion.py:136, 305-313, 112`.

**P8 [BAJO-MEDIO / confirmado] O9 sigue abierto.** `koroshi_operarios/controllers/main.py:63-67, 298-308, 329-343`;
`operarios_pantalla.js:130, 1176-1186`.

**P9 [BAJO / confirmado] `invalidate_cache()` entero en cada lectura.** `koroshi_preparacion/controllers/main.py:73, 76`.

**P10 [BAJO / confirmado] R6 a medias.** `lectura.py:1427`; `koroshi_operarios/models/tarea.py:509-546`
(`_reabrir_inactivas()` global dentro de Validar).

**P11 [BAJO / confirmado] `/koroshi/preparacion/rechazadas` escribe sin permiso ni tarjeta.**
`koroshi_preparacion/controllers/main.py:224-246, 42`.

**P12 [BAJO / confirmado] «Sacar de la caja» a dos.** `lectura.py:1177-1180`.

**P13 [BAJO / probable] Un `/cargar` viejo pisa una lectura ya guardada.** `preparacion.js:223-231, 324-331, 1840-1850`.

**P14 [BAJO / confirmado] «Hoy» con la medianoche UTC.** `koroshi_operarios/models/reparto.py:470, 477, 509`.
(En `tuctuc_operarios/models/reparto.py:49-51` ya está bien: traerlo.)

**P15 [BAJO / confirmado] Pruebas y copias.** `koroshi_operarios` sin `tests/`. Copias: `_empleado_valido` y
`_comprobar_grupo` (`controllers/main.py:40-50`), `RE_CAJA_NOTA` (`tablero.py:38`, `agrupacion.py:25`),
`PREFIJOS_ZONA` (`tarea.py:33`, `lectura.py:38`). `controllers/main.py:102-103`: `except` con `pass`.

## 5. Contenedores, faltantes, recuentos y prenda en el suelo (F)

**F1 [ALTO / confirmado; antes de instalar la 1.17] §3.2 sigue abierto.** `koroshi_contenedores/controllers/main.py:1416`
y `logica.py:240` (cajas a 0 no cuentan); `logica.py:245` (columna que recibe sale como origen); `main.py:1613,
903-907` (destino sin validar); `main.py:1498-1507` («Calcular» sin bloqueo).

**F2 [MEDIO / confirmado; R17 abierto] `/mover` acepta FALTANTE como destino.** `main.py:962-965, 903-907`;
`koroshi_faltantes/data/ubicacion.xml:5-11`.

**F3 [MEDIO / confirmado] `/faltantes/reubicar` se repite si se pierde la respuesta.**
`koroshi_faltantes/static/src/js/faltantes_pantalla.js:218-221`; `controllers/main.py:276-302`;
`models/faltante.py:346-354, 414-427`. Mismo texto falso en `koroshi_recuentos/static/src/js/referencia.js:250`
(`controllers/main.py:445`).

**F4 [MEDIO / confirmado, frecuencia baja] «Poner a cero» no mira lo leído sin validar.** `main.py:496-546`
(nunca llama a `_leidas`; `:443-446, 438, 517`).

**F5 [MEDIO / confirmado] Prenda en el suelo devuelve stock a un sitio archivado o inexistente.**
`koroshi_prenda_suelo/models/prenda.py:162-166, 169-182, 317`; `koroshi_faltantes/models/faltante.py:842, 855`.

**F6 [MEDIO / confirmado] Un recuento acaba «Coincide» sin contar y nunca caduca.**
`koroshi_recuentos/controllers/main.py:606-617, 281-284, 382-384`.

**F7 [MEDIO / probable] «Retirar cajas a 0» lee toda la nave.** `main.py:1039-1083` (llamado en `:1124, 1272, 1278`).

**F8 [MEDIO / mecanismo confirmado] Dominios que materializan ids** (precisión del §3.3):
`koroshi_faltantes/models/faltante.py:226, 943`; `koroshi_prenda_suelo/models/prenda.py:133`;
`koroshi_recuentos/controllers/main.py:164`; `koroshi_contenedores/controllers/main.py:698`. Los de
`stock.quant.location_id` no son problema (es `auto_join`).

**F9 [MEDIO-BAJO / probable] Búsquedas en `stock_move_line` por ubicación sin índice.** `main.py:209-211, 421,
486-488, 1062-1064, 1431-1433`; `koroshi_recuentos/controllers/main.py:542-544, 556-557`.

**F10 [MEDIO-BAJO / confirmado] El % de faltante recorre todo `stock_move` cada hora y cambia los ids.**
`koroshi_faltantes/models/relativo.py:38-55, 161, 205-207, 226-236`; `data/cron_relativo.xml:2, 9-10`;
`data/cron.xml:2` (crons sin `noupdate`).

**F11 [BAJO / probable] Dos PDA sobre la misma caja sin bloqueo.** `main.py:496, 617, 112, 1046`.

**F12-F14 [BAJO / confirmado].** `prenda.py:225-229` (ruta por cada OUT); `koroshi_recuentos/controllers/main.py:290-292`
(caja abierta del recuento, no del operario); `main.py:1027-1037, 110, 480, 1499` (`_marcas_con_prendas`).

**F15 [BAJO / confirmado] Pruebas y duplicados.** `koroshi_faltantes` sin `tests`. Modelo/color/talla en cuatro
versiones que no coinciden (`koroshi_contenedores/logica.py:31-40, 159-169`, `koroshi_recuentos/logica.py:20-34`,
`koroshi_faltantes/models/relativo.py:183-185`): para «001-3-000003-36» recuentos da el modelo `001`.

## 6. Monitor, KPI, informe, menú, consumibles y mapa (M)

**M1 ✔ [ALTO / confirmado] La caché del Monitor casi nunca acierta.** `koroshi_monitor/cache.py:24-26`;
`controllers/main.py:43, 46, 558`; `static/src/js/monitor.js:9`. Diccionario por proceso (16 workers), 20 s de
vigencia y refresco cada 60 s. Arreglo: resultado en tabla propia con `pg_try_advisory_xact_lock` y vigencia ≥ 60 s.

**M2 [ALTO / confirmado] `/datos` recorre las tareas del día tres veces.** `main.py:411-477, 495, 704`;
`koroshi_operarios/models/tarea.py:233-246, 316-334`; `controllers/produccion.py:94-117`; `main.py:568` →
`models/imprimir.py:163-166`.

**M3 [ALTO / patrón confirmado] Bandeja del encargado.** `koroshi_menu/models/bandeja.py:311-314, 383-392`.

**M4 [MEDIO / confirmado] Rutas del mapa sin grupo y con `sudo()`; `layout/save` con `csrf=False`.**
`koroshi_warehouse_map/controllers/main.py:460-461, 508, 548-549, 329-335, 121-122`.

**M5 [MEDIO / confirmado] La tele se queda en el día viejo y no se entera de los fallos.** `monitor.js:403-409`;
`main.py:759-768`; `produccion.js:93`.

**M6 [MEDIO / confirmado] El buscador de Tiendas pide `/datos` en cada tecla y pierde el foco.**
`monitor.js:180, 231-256, 696, 889`.

**M7 [MEDIO / probable] «Cajas preparadas» cuenta dos veces una CJ compartida.** `controllers/envios.py:142, 313,
377, 675, 694` (el Monitor sí lo resuelve en `main.py:218-226`).

**M8 [MEDIO / confirmado] Hoja de carga XPO y cierre XPO cuentan distinto; `?ids=` sin compañía.**
`koroshi_kpi/controllers/hoja_carga.py:61, 64-69, 101`; `envios.py:306-312, 524-546`.

**M9 [MEDIO / confirmado] El mapa enseña las 200 últimas OUT tocadas.**
`koroshi_warehouse_map/controllers/main.py:583-597, 305-309, 169-280`.

**M10 [MEDIO-BAJO / confirmado] «Operarios» en zonas mezcla rondas y años.** `main.py:823` frente a `:803-811`.

**M11 [MEDIO-BAJO / confirmado] `try/except Exception` sin savepoint.** `main.py:481-488, 494-498, 567-571,
575-587, 703-712`; `produccion.py:171-176`.

**M12 [BAJO-MEDIO / patrón confirmado] `sale_id.s_order_type_id.name` en una docena de consultas.**
`main.py:740, 843, 852`; `envios.py:181, 483, 1039`; `kpi.py:336`; `falta.py:69, 191`; `prevision.py:279`;
`bandeja.py:244`. Una función en `koroshi_base`.

**M13 [BAJO / confirmado] Vistas con `WITH`.** `koroshi_kpi/models/semana.py:64-66`; `falta_repetida.py:158-193`.

**M14 [BAJO / confirmado] KPI recalcula en cada `-u` y crons sin `noupdate`.** `koroshi_kpi/data/recalcular.xml:5`;
`models/kpi.py:364, 443, 468-471`; `data/cron.xml:4-12, 18-26`.

**M15 [BAJO / confirmado].** `koroshi_informe/models/informe.py:239-288` copia de `produccion.py:86-137`;
`informe.py:749-752` («OUT por hacer» cuenta todo); `koroshi_informe/controllers/main.py:15-30` (un GET de vista
previa escribe); `bandeja.py:114-118, 356` y `views/bandeja.xml:78` (sin grupo).

## 7. Base, módulos pequeños y herramientas (H)

**H1 ✔ [ALTO / probable; enlaza con el «Validar tarda 7 s» medido el 12/11] `koroshi_caja_existente`.**
`models/stock_picking.py:47-51, 160-174, 176-186`. `_koroshi_corregir_bultos` corre en `action_done` y en cada
`write` con `state`, `date_done` o `number_of_packages`; por cada caja hace un `search` en `stock.move.line` por
`result_package_id` (sin índice en Odoo 13) con `order='id', limit=1`. `:40` usa `=ilike`. Confirmar con
`\d stock_move_line` y `EXPLAIN ANALYZE`. Arreglo: una consulta agrupada y solo en la última escritura.

**H2 [MEDIO / confirmado] Cinco `<function>` sin `noupdate` en cada `-u koroshi_base`.** `koroshi_kpi/data/recalcular.xml:5`;
`koroshi_zonas/data/rellenar.xml:5`; `koroshi_faltantes/data/ubicacion_v131.xml:5`;
`koroshi_operarios/data/motivos_v221.xml:6`; `koroshi_menu/views/apps.xml:5`.

**H3 [MEDIO / confirmado] `koroshi_delegacion` sigue instalable.** `models/stock_picking.py:39, 66-72`;
`__init__.py:6-8`. Poner `'installable': False`.

**H4 [BAJO / probable] `buscar_producto` sin compañía.** `koroshi_base/pda.py:64, 68`.

**H5 [BAJO / confirmado] Compañía 8 a mano.** `koroshi_monitor/static/src/js/envios.js:250, 539`; `monitor.js:31`;
`koroshi_faltantes/data/ubicacion.xml:10-11`.

**H6 [MEDIO / probable] Búsquedas en bucle.** `koroshi_juntar_cajas/models/juntar.py:287-302`;
`koroshi_operarios/models/tarea.py:520-544`; `koroshi_buscador_stock/controllers/main.py:189-193`.

**H7 [ALTO / confirmado] `comprobar.py` compila con el Python del PC.** `bin/comprobar.py:293`;
`bin/empaquetar.py:120-122`. El servidor corre 3.5.2 según `estudio-migracion-servidores_2026-11-26.md:452, 517`
(`koroshi_zonas/motor/__init__.py:5` dice 3.6: confirmar). Hoy no hay ningún caso. Arreglo: E11 que rechace por AST
f-strings, `:=` y anotaciones de variable.

**H8 [ALTO / confirmado] `desplegar.sh` reinicia con el código nuevo y deja el `-u` a mano.** `bin/desplegar.sh:256-291,
112-120`. Con un campo guardado nuevo, «column does not exist» hasta actualizar. Solo compara con el manifest del
disco, no con `installed_version` (caso recepción 1.7.x).

**H9 [MEDIO / confirmado] Nada comprueba la versión mínima de `koroshi_base`.** `desplegar.sh:126-145`;
`empaquetar.py:77-88`.

**H10 [MEDIO / confirmado] El aviso de horario y de arrastre no paran nada.** `desplegar.sh:147-200, 222-227`.

**H11 [MEDIO / confirmado] No hay marca «en curso» y la etiqueta se crea antes de validar el ZIP.**
`empaquetar.py:97-104` frente a `:112-122`. Contenedores 1.17.0 está commiteado «en curso» con versión e historial:
`empaquetar.py` crearía una etiqueta que no se puede mover.

**H12 [MEDIO-BAJO / confirmado] Reglas sin comprobar.** E10 no mira `tuctuc_*` ni XML (`comprobar.py:187, 265, 60`);
no avisa de `<function>` ni crons sin `noupdate` (`:341-346`); no ve índices ni `init()` sobre tablas compartidas;
no comprueba ficheros de `data`/`qweb` ni la sintaxis JS (R19; `node` ya está en este PC); `desplegar.sh:139, 34-36`
apunta a nath por defecto también para `tuctuc_*`; `comprobar.py:80` revienta con rutas de más de 260 caracteres;
`restaurar()` (`desplegar.sh:245-254`) hace `rm -rf` + `cp`; la tabla del README está vieja.

## 8. Módulos `tuctuc_*` (T)

Son clones bien adaptados: sin restos de compañía 8, sin choques de rutas ni xmlids, y sin arreglos perdidos.

**T1 [ALTO / confirmado] «Siguiente pedido» carga casi toda `sale_order`.** `tuctuc_operarios/models/reparto.py:426-428`
(llamado en `:557, 570`). Además una OUT sin pedido de venta no se ofrece nunca.

**T2 [MEDIO / confirmado] Alternativas de Faltante: dos listas de más de 100.000 ubicaciones** (§3.3 copiado).
`tuctuc_faltantes/models/faltante.py:264-266`; `controllers/main.py:68`; `tuctuc_preparacion/static/src/js/preparacion.js:69, 1896`.

**T3 [MEDIO / confirmado] Crons activos al instalar, sin `noupdate` ni hora.** `tuctuc_faltantes/data/cron_relativo.xml:5-14,
17-26`; `data/cron.xml:6-15`; `tuctuc_operarios/data/cron.xml:7-16`; `models/relativo.py:42-59, 193-235`.

**T4 [MEDIO / confirmado] `tuctuc_preparacion` a medio adaptar y sin commitear.** Textos «CJ» (`preparacion.js:827,
835, 1307`; `preparacion.xml:162`); patrón de caja fijo en JS (`preparacion.js:65`, `tuctuc_base/static/src/js/comun.js:11`);
`data/parametros.xml:7-15, 39-42` (`activa` = 1, `empleados` = *, `validar_parcial` = 1).

**T5 [BAJO / probable] El «reparto de hoy» depende del usuario.** `tuctuc_operarios/models/reparto.py:54-58, 126, 139`.

**T6 [BAJO] `buscar_producto` sin compañía** (`tuctuc_base/pda.py:116, 120`) y O9 copiado
(`tuctuc_operarios/controllers/main.py:65`).

## 9. Qué no se ha podido comprobar (consultas de solo lectura que faltan)

1. `installed_version` de todos los módulos (regla 3).
2. Índices reales de nath: `\d stock_move_line`, `\d stock_quant_package`, `\d zebra_label` (H1, F9, P7, E12).
3. Versión de Python del servicio `nath-erp` (H7).
4. A qué hora entran los pedidos de tienda y cuánto tarda el job «S4T Reservar OUT» (probabilidad de Z1); si desde
   el 24/11 ha habido OUT canceladas por Retener con pedidos de 60 líneas o más.
5. Log de «KOROSHI Preparación validar» (`_log_validar`) para repartir los 7 s de Validar entre H1, transportista y S4T.
6. `delivery_xpo`, `delivery_gls_asm`, `zebra.label` y `api_s4t_batch_update_PROD` no están en el repo.
7. Tiempos de F7-F10 y M3: `EXPLAIN` o el ranking del log (`odoo/modulos/koroshi_rendiment/README.md`, «Cómo se buscó»).

## 10. Miré y está bien (no volver a revisar)

Idempotencia por `id_lectura` y cola de la PDA sin red; R5, R7, R8, R16 (salvo P11), R18 y R22 corregidos; ajustes de
stock de contenedores (nunca quitan más de lo libre); envíos S4T con commit por pedido y `unique(sale_id, tracking)`;
traspasos con savepoint y único; agrupaciones web (R10 corregido, candado, cambio de hora); partir zonas todo o nada;
prioridad (R15); transportista ante doble toque y dos PDA; juntar cajas todo o nada; recepción no toca stock hasta
validar; agente con credenciales en Windows y `SKIP LOCKED`; actividades (un tramo por persona, cambio de hora);
`koroshi_base`, `koroshi_pda_app`, `koroshi_sesiones`, `koroshi_xpo_bultos`, `koroshi_rendiment`,
`koroshi_buscador_stock`; `empaquetar.py` (ZIP siempre desde la etiqueta); sin credenciales en `odoo/modulos`; sin
`aria-hidden` ni `display_notification`.
