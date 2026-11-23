# Revisión general del almacén KOROSHI (23/11/2026)

Revisión de solo lectura: no se ha cambiado código, ni empaquetado, ni tocado el servidor ni la base de datos.
Hecha por Fable con cuatro subagentes que leyeron los módulos y `bin/versiones/`.

**Cómo leer las fuentes**: `archivo:línea` con rutas desde la raíz del repo (`om/` = `odoo/modulos/`,
`bv/` = `bin/versiones/`). Marca **[C]** = lo he abierto y comprobado yo; sin marca = lo leyó un subagente en el
código y no lo he vuelto a abrir; **«sin confirmar»** = no se puede saber sin datos del servidor o sin probarlo.
Nada de lo que hay aquí se ha reproducido en Odoo: todo sale de leer.

## 1. Resumen para Isaac (10 líneas)

1. **Todo el trabajo desde el 13/11 está solo en este PC**: 343 commits y todas las etiquetas sin subir; el remoto
   sigue en el commit del 13/11 y tiene 0 etiquetas [C]. Si se rompe el disco, se pierde el mes.
2. **«Cambiar» de Contenedores 1.12.0 (instalada hoy) quita a la OUT la línea entera**, no solo lo que falta, y no
   descuenta lo ya leído sin validar: puede descuadrar stock. Sin probar en PDA [C].
3. **Validar tarda 30-50 s y no hay ni un cronómetro en el código** para saber dónde. Lo propio que sobra es poco;
   el sospechoso es el envío a XPO/S4T dentro de la validación (sin confirmar). Primero medir.
4. **Lecturas no se refresca**: confirmado. El estado ligero no trae la ubicación y, yendo solo, la pantalla no
   refresca nunca por su cuenta [C]. Arreglo pequeño, solo en koroshi_preparacion.
5. **Ningún cron avisa cuando falla**. El reparto de zonas de las 04:50, los cortes web, los envíos y traspasos a
   S4T y la ronda de faltantes pueden fallar y solo queda en el log.
6. **Hay unas 12 pruebas en PDA real apuntadas en el TABLERO y sin hacer** (la más vieja, la ronda de faltantes,
   del 17/11). Se instala más deprisa de lo que se prueba.
7. **El TABLERO se contradice** en tres módulos (informe 1.3.0, recuentos 1.1.0, actividades 1.8.3: «sin instalar»
   en una fila, «instalada» en otra) y su cabecera es del 17/11. README y TRASPASO están viejos.
8. **Nadie ha escrito a KOROSHI por la serie web 0000059xxx** (parada desde el 20/11 16:00) y hay unos 12 correos
   redactados que no consta que se hayan enviado. Tres preguntas a S4T llevan 6-9 días sin respuesta.
9. **Lo que pidió el almacén en la grabación** (recepciones primero, moda íntima y la inversa, errores de talla,
   trazabilidad por operario) solo tiene código en nada: recepciones es diseño v6, lo demás ni diseño.
10. **Orden que propongo**: copia del repo → arreglar «Cambiar» → medir Validar y arreglar Lecturas → vigilante de
    crons → una hora de pruebas en PDA → recepciones.

## 2. Nos lo estamos dejando

| # | Qué | Fuente | Desde | Quién hace qué | Riesgo si no se hace |
|---|---|---|---|---|---|
| D1 | Push: 343 commits y ~170 etiquetas solo en local. Copia de seguridad única, del 16/11 (`C:\dev\OleadasKoroshi_copia-git-antes-de-limpiar_2026-11-16.git`), en el mismo disco | `git rev-list --count origin/main..main` = 343; `git ls-remote --tags origin` = 0 [C]; `TABLERO.md:68` | 16/11 | Isaac: decidir el push forzado (pregunta P1) | Perder todo el código y los diseños del mes |
| D2 | Pruebas en PDA real sin hacer: ronda de faltantes (17/11), contenedores 1.9.3-1.12.0, tablero del responsable, tarjeta compartida, devoluciones (3 pestañas), Inicio PDA con lector, recuentos 1.1.0, menús con Almacén Nath (2.5.1, 1.37.0), cerrar un camión de prueba, imprimir de verdad desde el Monitor | `TABLERO.md:26-29,46,48-50,53,82-83,87,103` [C] | 17/11-23/11 | Almacén + Isaac: una hora con una PDA y la lista del apartado 6 | Fallos que se descubren en plena preparación |
| D3 | TABLERO se contradice: informe 1.3.0 «SIN INSTALAR» (fila 30) e instalada 20/11 14:10 (línea 96); recuentos 1.1.0 «SIN INSTALAR» (53) e instalada 14:34 (99); actividades 1.8.3 «sin instalar» (50) e instalada 16:48 (102). Cabecera «Última revisión: 17/11». «Al día» (107-109) con versiones de hace una semana | `TABLERO.md:6,30,50,53,96,99,102,107` [C] | 20/11 | Una sesión: leer `installed_version` y `latest_version` de todos y rehacer el tablero | Instalar dos veces, o creer instalado algo que no lo está |
| D4 | Filas del tablero sin rellenar: «Carga del camión por CJ», «Pedidos pendientes por reasignar», «Alarma PDA», «Sync S4T», «Correos pendientes» | `TABLERO.md:31,32,34,35,37` [C] | 17/11 | Isaac: cerrar las que ya no viven | Módulos «cogidos» por chats muertos (regla 6) |
| D5 | koroshi_preparacion sigue «cogido» por la sesión de la ronda de faltantes | `TABLERO.md:28,47` [C] | 17/11 | Isaac: soltarlo (P5) | Bloquea el arreglo de Lecturas, Validar y «revisar caja» |
| D6 | Hecho sin instalar que sigue teniendo sentido: s4t_pedidos 1.1.0 (prioridad, entra en SIMULAR), prenda_suelo 1.0.0, ubicaciones 1.0.0, cron 192 v7 (sin pegar) | `TABLERO.md:42,43,51,52` [C]; ZIP en `bin/` [C] | 19-23/11 | Isaac: el sí, uno a uno | Ver D7 antes de la prioridad en real |
| D7 | Decisiones de la reserva por prioridad sin respuesta (hora del cron, gente a esa hora, OUT de días anteriores, semana en simular). El diseño aún dice «PROPUESTA, sin código» y el código existe | `bv/diseno-reserva-tiendas-por-prioridad_2026-11-23.md:3,56-61`; `om/koroshi_s4t_pedidos/models/prioridad.py` | 23/11 | Isaac | Pasar a real sin haber decidido |
| D8 | Hecho sin instalar que se ha quedado viejo: todo lo que `TRASPASO_AUDITORIA.md` da como «SIN INSTALAR» (fases 1-6) ya entró con el plan v3 y versiones posteriores; koroshi_delegacion decidido que no | `TRASPASO_AUDITORIA.md:28-34`; `TABLERO.md:72-74,105` [C] | 17/11 | Una sesión: nota de cierre en TRASPASO | Confusión; ningún riesgo de almacén |
| D9 | Auditoría, lo que nunca se hizo: pasar `tests/test_idempotencia.py` en una base de pruebas (no consta que exista una); rotar las credenciales versionadas; decidir dónde van las fotos | `TRASPASO_AUDITORIA.md:27,28,33`; `TABLERO.md:67`; `App.config` y `bin/Release/PedidosMultiples.exe.Config` siguen en git [C] | 13-16/11 | Isaac (rotar, fotos); base de pruebas: P6 | Claves válidas en un repo de GitHub (si es público o no: sin confirmar) |
| D10 | Serie web 0000059xxx parada desde el 20/11 16:00: no hay correo ni nota a KOROSHI | solo `bv/prompt-fable-revision-general_2026-11-23.md:54-55` | 20/11 | Isaac → KOROSHI (P4) | Pedidos web que no llegan y nadie lo sabe |
| D11 | Preguntas a S4T sin respuesta registrada: teórico por matrícula (14/11, bloquea la inversa), envíos y bultos (16/11), devoluciones web (17/11) | `TABLERO.md:63-65` [C] | 14-17/11 | Isaac: reclamar | La inversa no puede empezar |
| D12 | Correos redactados que no consta que se enviaran: a S4T cancelaciones bidireccionales (20/11), expedición y albarán (19/11), correcciones de traspasos (20/11), estados para Efren (23/11); a KOROSHI pedidos web v2 (190 pedidos), prendas sin caja v2, recepciones abiertas de más (59 modelos); a Sonia devoluciones online v2 (aún con corchetes), 2621XC04, K33, 2622PT92 | `bv/correo-*.md` (cabecera «Borrador. No enviado»); `TABLERO.md:37` vacía | 15-23/11 | Isaac: enviar o tachar | Temas que KOROSHI y S4T creen cerrados |
| D13 | Diseños que esperan respuesta: zonas modo del día (preguntas 1-3 y cajas por carro), revisar caja (P1-P5), la inversa (4 decisiones), aviso de inicio de preparación a S4T, contenedores (preguntas 1, 2, 3, 5 y «qué verificar al compactar»), recuentos (pregunta 8), buscador (2 dudas) | `bv/diseno-zonas-modo-del-dia_2026-11-20.md:168-176`; `bv/diseno-revisar-box-partir_2026-11-19.md:103-113`; `bv/diseno-lectura-matriculas-inversa_2026-11-12_1705.md:56-61`; `TABLERO.md:29,47,53` | 12-20/11 | Isaac / almacén | Trabajo de diseño que caduca |
| D14 | Recepciones: diseño v6 existe y el tablero cita la v5; no hay módulo; falta saber quién crea el contenedor | `bv/diseno-recepciones-packing-list_2026-11-23_v6.md` [C]; `TABLERO.md:44` [C] | 23/11 | Almacén (respuesta), Isaac (orden de programar) | Es lo que el almacén dice que más le hace sufrir |
| D15 | Fases a medias: recuentos fase 3 (aplicar la diferencia) y 4; devoluciones fase 2 (comparar con lo esperado); prenda en el suelo fases 2-3; Inicio PDA sin poner de inicio a Almacén Nath; cron de cierre con nombre y parámetros viejos | `TABLERO.md:33,49-51,53`; `om/koroshi_actividades/data/parametros.xml:6-8,16-18` | 20/11 | Sesiones, cuando toque | Pantallas instaladas que nadie usa |
| D16 | Sin commitear: `redistribucion/programa/`, cambios en `TABLERO.md`, `.gitignore`, `.claude/launch.json` y 26 líneas añadidas **dentro** de `bv/diseno-zonas-modo-del-dia_2026-11-20.md` (se ha editado una versión en vez de sacar otra) | `git status`, `git diff --stat` [C] | 20-23/11 | Las sesiones dueñas | Se pierde o se lo lleva el commit de otra sesión |
| D17 | Código en producción fuera de módulos: unas 10 acciones y crons vivos pegados a mano (1800, 1960, 1827, 1844, 1883, 1880-1882, cron 192, acción automática 20, 1837) más 8 acciones y 3 crons viejos por borrar. De la 1960 y la 1827 el repo no tiene la versión actual | `bv/2026111*_accion-*.py`; `bv/fase5-zonas-analisis_2026-11-14.md:61-92` | — | Una sesión: copiar la 1960 y la 1827 actuales (solo lectura); Isaac: borrar lo viejo | Si alguien las toca, no hay forma de volver atrás |
| D18 | Ideas de la fase 7 nunca programadas: 4 (caja llena), 7 (calidad por operario), 8, 9 (hueco vacío), 10 (leer CJ en el muelle), 11 («Luego»), 12 | `bv/fase7-ideas-diseno_2026-11-16_ideas-oca-wms.md:16-32` | 15-16/11 | Isaac: tachar o reordenar | Ninguno inmediato |
| D19 | De la grabación del 23/11, sin recoger en ningún diseño: trazabilidad de movimientos por día y operario, errores de talla, moda íntima, cálculo de palés que ocupará lo que llega, foto del contenedor al descargar, etiquetas de palé imprimibles, imprimir por estaciones | `C:\Users\tuctuc\Videos\Nueva grabación 32_1975.txt:38-47,92-100` | 23/11 | Isaac: priorizar | Peticiones dichas en voz alta que se olvidan |

## 3. Deberíamos hacer (riesgos y controles que faltan)

| # | Riesgo | Fuente | Propuesta | Esf. |
|---|---|---|---|---|
| R1 | **«Cambiar» por debajo de lo reservado se lleva la línea entera** (`necesario = ml.product_qty`) y solo reubica si un único hueco de los 5 más cercanos tiene toda la cantidad. Línea de 5 con 4 reales: la OUT pierde las 5, van 5 a FALTANTE y luego se crean 4 por ajuste | `om/koroshi_contenedores/controllers/main.py:395,403-419` [C]; `om/koroshi_faltantes/models/faltante.py:46,232` | Bajar la línea a lo que hay y pasar a Faltantes solo la diferencia. Toca contenedores y faltantes (regla 6: decirlo) | M |
| R2 | **«Cambiar» no descuenta lo leído sin validar**: 10 en Odoo, 4 ya leídas en el carro, 6 en la caja; se pone 6, se ajusta −4 y al validar salen otras 4. Recuentos sí lo resta | `om/koroshi_contenedores/controllers/main.py:526-531` [C]; `om/koroshi_recuentos/controllers/main.py:565-569` | Restar lo leído pendiente o avisar y parar | S |
| R3 | «Añadir prendas» se duplica si se corta la wifi y el operario reintenta: la ruta no tiene clave de reintento (Devoluciones sí) | `om/koroshi_contenedores/static/src/js/contenedores.js:292,727-747`; `controllers/main.py:473-502`; `om/koroshi_devoluciones/models/devolucion.py:185-187` | Id de tanda desde la PDA | S |
| R4 | «Poner a cero» deja la unidad en FALTANTE con vuelta a un contenedor que se puede archivar; «Archivar» solo mira quants. La ronda manda después al operario allí | `om/koroshi_faltantes/models/faltante.py:381,440,661`; `om/koroshi_contenedores/controllers/main.py:182-183,297,323` | En «cero», cerrar el faltante como no encontrado en la misma transacción | S-M |
| R5 | **Error de base de datos tragado al pintar el estado**: `_con_estado` captura todo. Si el volcado de `qty_done` falla por concurrencia justo ahí, la PDA recibe «ok» y no se ha guardado nada (deducido leyendo, no reproducido) | `om/koroshi_preparacion/controllers/main.py:48-60` [C]; `models/lectura.py:741` | `flush()` antes, fuera del `try` | S |
| R6 | Validar: 30-50 s sin ningún log de tiempos. Dentro de la transacción corre `cron_cerrar()` de **todas** las tareas del almacén y la OUT queda bloqueada todo ese rato. Candidatos de fuera del repo: envío a XPO (SOAP) y acciones automáticas 17 y 18 de S4T (sin confirmar) | `om/koroshi_preparacion/models/lectura.py:1136,1216-1221` [C]; `om/koroshi_operarios/models/tarea.py:458,520-531`; `om/koroshi_xpo_bultos/models/delivery_carrier.py:95-118`; `bv/20261110_PLAN_preparacion_en_lecturas_v2.md:85,234,254` | Cronómetro por tramo en el log; cerrar solo la tarea propia. Con los tiempos, decidir si XPO/S4T van a cola | S (medir) + M-L |
| R7 | Lecturas enseña el hueco viejo: estado ligero sin ubicación y refresco solo «a dos» | `om/koroshi_preparacion/models/lectura.py:443` [C]; `static/src/js/preparacion.js:211-216` [C], `:323-329` | Sexto dato con la ubicación; si cambia, recarga entera; refresco cada ~30 s también yendo solo | S |
| R8 | Doble caja (3 → 4): no hay camino en el código que cree dos cajas con una acción (el servidor mira `id_lectura`). Pero el botón Caja no se desactiva mientras la petición vuela, y con Zalando/About You Validar cierra una caja sola que se queda aunque la validación falle. Causa real: **sin confirmar** | `om/koroshi_preparacion/static/src/js/preparacion.js:1279,2526`; `models/lectura.py:851-862,1153,1184-1187` | Consulta C2; desactivar Caja con aviso «Cerrando…» | S |
| R9 | **Ningún cron avisa si falla**. Zonas 04:50: lo que falla antes de crear la ejecución no deja ni ejecución ni mensaje en el canal | `om/koroshi_zonas/models/ejecucion.py:478-512` [C], `:575-588`; `data/cron.xml:33,62-71` | Vigilante a las 05:15: «¿hay reparto real de hoy?» con correo; rellenar destinatarios | S |
| R10 | Cortes web: `ultimo_corte` se apunta antes de hacerlo; si falla o llega más de 120 min tarde, solo log y no se repite. Un `action_cancel` que falle tumba el corte entero | `om/koroshi_agrupaciones_web/models/corte.py:275-285` [C], `:168-169` | Apuntar después; savepoint por OUT; correo si falla o se salta | S |
| R11 | Envíos S4T: los errores de red cuentan como intento; con 5 (75 min de caída) el pedido sale del cron para siempre. El aviso depende de un parámetro que el módulo no crea | `om/koroshi_s4t_envios/models/envio.py:283,315-316,333-335,348,363-364` | No contar la red como intento; cortar la pasada tras 3 fallos seguidos; correo resumen. Consulta C4 | M |
| R12 | Traspasos S4T: la corrección en error no se arregla ni creando el artículo (el producto calculado no se recalcula); tras 5 intentos, silencio | `om/koroshi_s4t_traspasos/models/traspaso.py:222-224,282,332-333,355-360` | Recalcular al procesar; correo diario con los errores | S |
| R13 | Ronda de faltantes: un faltante malo para todo el cron (sin savepoint por registro), cada 15 min | `om/koroshi_faltantes/models/faltante.py:556,585-587,702-759` | Savepoint y log por faltante | S |
| R14 | Unidades en FALTANTE que nadie recupera: solo un contador en la bandeja, sin umbral ni antigüedad | `om/koroshi_menu/models/bandeja.py:429-438` | Rojo si llevan más de N días; consulta C5 | S |
| R15 | Prioridad 1.1.0 al pasar a real: comprueba «no empezada» una vez y luego desreserva con commit por artículo; el botón manual se puede pulsar en horario; si dura más de 20 min pisa el reparto de zonas | `om/koroshi_s4t_pedidos/models/prioridad.py:67-69,92,119-139,166-179,200-201`; `om/koroshi_zonas/models/escritor.py:74-99` | Volver a comprobar dentro de cada artículo; bloquear el botón en horario; zonas espera el candado. **Antes** de poner `prioridad_modo` = real | M |
| R16 | La PDA manda el `employee_id` y casi nadie lo valida: preparación acepta cualquiera y sus rutas no comprueban grupo; contenedores, faltantes, recuentos y devoluciones solo miran que exista | `om/koroshi_preparacion/controllers/main.py:34-35,79-282`; `om/koroshi_contenedores/controllers/main.py:203-207`; `om/koroshi_faltantes/controllers/main.py:113` | `_empleado_valido` y `_comprobar_grupo` en koroshi_base, módulo a módulo | S-M |
| R17 | Mover contenedor: el destino no se limita (ni compañía, ni que no sea FALTANTE) y leer el hueco mueve al instante | `om/koroshi_contenedores/controllers/main.py:209-213,655-659`; `contenedores.js:384-387` | Limitar a ubicaciones de la compañía 8 y excluir FALTANTE | S |
| R18 | Correos que fallan en silencio: el informe se marca enviado antes de enviar | `om/koroshi_informe/models/informe.py:1101,1119,1139-1144` | Mirar el estado del correo; consulta C6 | S |
| R19 | `bin/comprobar.py` no cubre trampas ya conocidas: JS que no compila (no hay node), `except Exception` sin log, rutas `auth='user'` sin grupo, constantes copiadas (regla 8), dominio «todos» sobre one2many. `oriola_monitor` da E6 y no tiene etiqueta | `bin/comprobar.py:12-24` [C]; salida de `python bin/comprobar.py` [C]; memoria `odoo13-dominio-o2m-no-dice-todos` | Añadir E9 (constantes de koroshi_base copiadas) y A2 (ruta sin grupo); el resto, avisos | S |
| R20 | `bin/desplegar.sh` no avisa de: módulos dependientes que se actualizarán en la misma pasada, módulo nuevo con un dependiente en la tanda, ni hora de trabajo (cada actualización saca las sesiones de las PDA) | `bin/desplegar.sh:121-140,228-233` [C]; memorias `odoo-upgrade-arrastra-dependientes`, `odoo-actualizar-modulo-saca-sesiones`, `odoo-modulo-nuevo-instalar-antes-que-dependiente` | En `check`: listar dependientes instalados y avisar entre las 06:00 y las 17:00 | S |
| R21 | El 23/11 se instalaron 9 versiones entre las 08:39 y las 10:46, en horas de trabajo (contenedores 1.9.2, 1.9.3, 1.11.0, 1.12.0; monitor 1.39-1.42) | `TABLERO.md:27,29` [C] | Regla: en horario solo lo urgente; el resto, a las 14:00 o a las 17:00 | — |
| R22 | Monitor: caché con un solo candado global durante todo el cálculo; `_prioridad` relee todas las OUT de tienda de 30 días en cada cálculo; la cabecera de Producción recalcula Tiendas sin caché | `om/koroshi_monitor/controllers/main.py:41-43,548-571,610-616`; `controllers/produccion.py:169` | Candado por clave; caché propia de 2-5 min para la prioridad | M |
| R23 | Errores de talla: no existe forma de pasar unidades de un artículo a otro; hoy son dos ajustes sueltos | sin resultados en `om/` | «Cambiar artículo» en Contenedores: una transacción y una línea de registro | M |

## 4. Optimizar o simplificar

| # | Qué | Fuente | Ahorro esperado |
|---|---|---|---|
| O1 | Validar: quitar `cron_cerrar()` global de la transacción (lo propio); si la medida señala a XPO/S4T, a cola | R6 | Sin medir no se puede prometer cifra. Unas 15 validaciones lentas por mañana × 30-50 s = 8-12 min de operario parado solo en esas |
| O2 | Tipo de caja: se borra a propósito en cada caja aunque el último ya se guarda | `om/koroshi_preparacion/static/src/js/preparacion.js:819-823,1077,1096` | Un toque menos por caja |
| O3 | Tras validar: 0,9 s + 3 s de «¡Hecho!» | `preparacion.js:54,1566`; `om/koroshi_operarios/static/src/js/operarios_pantalla.js:42,552` | Hasta ~3 s por OUT |
| O4 | Tarjeta de operario copiada en 6 JS y lector «leer al parar 150 ms» solo en Contenedores; Devoluciones, Referencia, Prenda suelo y Faltante leen solo con Intro (el fallo de la 1.9.3 puede seguir allí: probar en PDA) | `contenedores.js:40,141-157,833-849`; `faltantes_pantalla.js:121-155,187`; `devoluciones.js:106-122,237`; `referencia.js:84-98,154`; `prenda_suelo.js:69-83,134`; `om/koroshi_base/static/src/js/comun.js:1-17` | Un solo lector y una sola tarjeta en koroshi_base: un fallo se arregla una vez, no seis |
| O5 | Búsqueda de producto por EAN copiada en 4 módulos; la de Faltante es más pobre | `om/koroshi_contenedores/controllers/main.py:334-349`; `om/koroshi_devoluciones/controllers/main.py:50-62`; `om/koroshi_recuentos/controllers/main.py:55-64`; `om/koroshi_prenda_suelo/models/prenda.py:88-96`; `om/koroshi_faltantes/controllers/main.py:129-132` | «No encuentra el artículo» distinto según la pantalla: evitado |
| O6 | Constantes fuera de koroshi_base: `COMPANY_ID = 8` en contenedores; `'Europe/Madrid'` en kpi; `'PED. TIENDAS'` en 5 sitios; regex de lineal en 4; `RE_CJ` propio en preparación; `PREFIJOS_ZONA` en 2 | `om/koroshi_contenedores/controllers/main.py:24` [C]; `om/koroshi_kpi/models/semana.py:55-56` [C]; `om/koroshi_monitor/controllers/main.py:44`; `om/koroshi_faltantes/models/faltante.py:60-61`; `preparacion.js:59`; `om/koroshi_preparacion/models/lectura.py:37` | Regla 8 cumplida; se hace al tocar cada módulo, sin versión propia |
| O7 | Unidades con cuatro criterios (demanda, reservado, leído, tareas) entre Monitor zonas, Tiendas, informe y operarios: de ahí el 7.056 frente a 6.980. Causa más probable: ~76 u pedidas sin reserva (sin confirmar; consulta C1) | `om/koroshi_monitor/controllers/main.py:184-190,689-690`; `om/koroshi_zonas/models/lector.py:92` | Una sola función «unidades de una OUT» en koroshi_base y una etiqueta en pantalla («pedidas» / «reservadas») |
| O8 | u/h: cuatro fórmulas (dos en el monitor, una copiada, una en el informe) | `om/koroshi_monitor/controllers/produccion_calc.py:58-60`; `controllers/main.py:496,742`; `om/koroshi_informe/models/informe.py:432` | Era el punto 1 de la fase 2 de la auditoría: sigue abierto en parte |
| O9 | `/operarios/estado` cada 60 s por PDA: SQL a `ir_module_module` y hasta 200 tareas | `om/koroshi_operarios/controllers/main.py:63-67,284`; `operarios_pantalla.js:130` | Carga constante de servidor; guardar la versión en memoria |
| O10 | Documentación: README con versiones del 16/11 y sin 6 módulos (recuentos, prenda_suelo, ubicaciones, agrupaciones_web, s4t_sync, tuctuc_rendimiento); 91 `bin/instalar_*` viejos; 244 ZIP (966 MB en `bin/`) | `README.md:24-65` [C]; `ls bin` [C] | Generar la tabla del README desde los manifest; archivar los `instalar_*` |
| O11 | TABLERO: filas de 1.500 caracteres con el historial de cada instalación | `TABLERO.md:29,46` [C] | Una línea por tema (como dice su cabecera); el historial ya está en el manifest y en git |

## 5. Plan priorizado (las 10 primeras)

Ninguna añade campos a `stock.picking`, `stock.picking.type` ni `stock.move.line` (regla 7). Las que **escriben** en
líneas de OUT ya existentes lo dicen.

| # | Qué | Esf. | Módulo | Tablas compartidas |
|---|---|---|---|---|
| 1 | Copia del repo fuera de este PC (push o copia a otro disco hoy mismo) | S | — | No |
| 2 | Contenedores «Cambiar»: solo la diferencia a Faltantes y descontar lo leído (R1, R2); de paso R3 y R4. Hasta entonces, decidir si se deja como está (P2) | M | koroshi_contenedores + koroshi_faltantes | Escribe en `stock.move.line` existentes; sin campos nuevos |
| 3 | Validar: cronómetro en el log y cerrar solo la tarea propia (R6). Una semana de datos y decidir | S | koroshi_preparacion | No |
| 4 | Lecturas: ubicación en el estado ligero, refresco yendo solo, `flush()` fuera del `try`, botón Caja (R5, R7, R8). Misma versión que el 3 | S | koroshi_preparacion | No |
| 5 | Vigilante de crons con correo: zonas 05:15, cortes web, envíos y traspasos S4T, ronda de faltantes (R9-R13) | M | koroshi_menu (bandeja) o cada módulo | No |
| 6 | Una hora de pruebas en PDA con el almacén (lista del apartado 6) y rehacer el TABLERO con las versiones leídas del servidor (D2, D3) | S | — | No |
| 7 | Escribir a KOROSHI por la serie 59xxx y enviar o tachar los correos redactados (D10-D12) | S | — | No |
| 8 | Recepciones 1.0.0 (diseño v6) e instalar antes koroshi_ubicaciones 1.0.0 | L | koroshi_recepcion (nuevo), koroshi_ubicaciones | Por confirmar al programar: el diseño usa tablas propias |
| 9 | «Cambiar artículo» para los errores de talla (R23) | M | koroshi_contenedores | No |
| 10 | Prioridad de tiendas: instalar 1.1.0 en SIMULAR y endurecerla antes de real (R15) | M | koroshi_s4t_pedidos (+ koroshi_zonas para el candado) | Desreserva `stock.move.line`; sin campos nuevos |

Después: lector y tarjeta comunes en koroshi_base (O4), empleado validado (R16), comprobar.py y desplegar.sh (R19,
R20), Monitor (R22, O7), la inversa (cuando S4T conteste) y moda íntima (falta saber qué es: P7).

**Modelo** (tabla de CLAUDE.md): 2, 3, 4, 9 y 10 tocan stock o validación → Opus en high. 5 y 8 → Fable u Opus en
high. 6 y 7 → Sonnet.

## 6. Pruebas en PDA y consultas de solo lectura

**En PDA (reversibles: leer y deshacer, sin cerrar cajas ni validar)**

1. Contenedores «Cambiar» 5 → 4 con una línea de 5 reservada: ¿la OUT pierde las 5?
2. «Cambiar» con unidades ya leídas y sin validar en otra PDA.
3. «Poner a cero» con una OUT de agrupación Z- abierta en Lecturas en otra PDA: qué ve el preparador.
4. Cortar la wifi al «Guardar» de «Añadir» y reintentar: ¿se duplica?
5. Cero → Archivar → crear ronda: adónde manda.
6. Lector con el campo marcado en Devoluciones, Referencia y Faltante (el fallo de contenedores 1.9.3).
7. Ronda de faltantes pequeña (pendiente desde el 17/11).
8. Tarjeta en Lecturas → abrir Contenedores sin pasarla, y al revés.
9. Inicio PDA: pasar la tarjeta con el lector sin tocar el campo.

**Consultas que propongo (solo lectura; Isaac decide)**

- C1 (Monitor 7.056/6.980): en los lotes `Z-2311-%` de la compañía 8, suma de `stock_move.product_uom_qty` de los
  movimientos no cancelados menos la suma por movimiento de `greatest(reservado, qty_done)` de sus líneas. Si da
  unas 76, es demanda sin reserva.
- C2 (doble caja): apuntes `tipo = 'caja'` de la OUT del operario de las 3/4 cajas, con su `id_lectura` y hora.
- C3 (versiones): `installed_version` y `latest_version` de todos los `koroshi_%` en `ir.module.module`.
- C4 (S4T): pedidos con 5 intentos de envío sin éxito; valor de `koroshi_s4t_envios.avisar`.
- C5 (FALTANTE): `koroshi.faltante` pendientes por antigüedad y stock actual en la ubicación FALTANTE.
- C6 (correos): `mail.mail` en estado de excepción de los últimos 7 días.
- C7 (crons): `ir.cron` de los módulos KOROSHI con `active`, `nextcall` y última ejecución; ¿está activo el 210?
- C8 (Validar): las líneas del log del servidor de `/koroshi/preparacion/validar` del 23/11 con su duración y el
  transportista de cada OUT (¿las lentas son las de XPO?).

## 7. Preguntas para Isaac (solo las que bloquean)

- **P1. Copia del repo.** a) Push forzado de la historia limpia a GitHub ahora (recomendado si el repo es privado);
  b) repositorio privado nuevo y dejar el viejo; c) de momento, copia del `.git` a otro disco o a Drive cada día.
- **P2. «Cambiar» por debajo de lo reservado (1.12.0), mientras no esté arreglado.** a) Avisar al almacén de que no
  lo use con reservas hasta la versión nueva (recomendado: no hace falta instalar nada); b) sacar ya una 1.12.1 que
  vuelva al bloqueo de la 1.10; c) dejarlo como está.
- **P3. Recepciones.** ¿Quién crea el contenedor al llegar: el muelle o la oficina? Sin eso no se programa la 1.0.0.
- **P4. Serie web 0000059xxx.** a) Lo preguntas tú a KOROSHI; b) una sesión redacta el correo con los datos (última
  entrada, series que sí entran).
- **P5. koroshi_preparacion.** ¿Se suelta de la sesión de la ronda de faltantes para que una sola sesión haga los
  puntos 3 y 4 del plan?
- **P6. Base de pruebas.** ¿Hay una copia de Odoo donde pasar `tests/test_idempotencia.py` y probar «Cambiar»? Si
  no la hay, todo lo de stock se sigue probando en real con la PDA.
- **P7. Moda íntima.** En la grabación se dice «primero moda íntima y la inversa» y no aparece en ningún documento:
  ¿qué hay que hacer exactamente?
- **P8. Prioridad de tiendas.** Las cuatro decisiones del diseño (hora, gente a esa hora, OUT de días anteriores,
  una semana en simular) antes de instalar la 1.1.0.

## 8. Qué no he podido comprobar

- Nada se ha ejecutado en Odoo: los descuadres de R1, R2 y R5 salen de leer el código, no de reproducirlos.
- La causa de los 30-50 s de Validar y la de la doble caja: sin datos del servidor no se puede saber.
- Si el repo de GitHub es público o privado, y si las credenciales versionadas siguen siendo válidas.
- Qué versiones hay de verdad en el servidor hoy (no se ha leído `installed_version`).
- La mayoría de las líneas citadas de los módulos las leyeron los subagentes; yo he abierto y comprobado las
  marcadas con [C].
