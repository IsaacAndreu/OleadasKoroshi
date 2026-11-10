# Opción B: pantalla de preparación propia dentro de Lecturas

**Plan v2 · 10/11/2026** (sustituye a la v1 del mismo día, que se conserva sin tocar)

Estudio de solo lectura: no se ha modificado ningún fichero existente y no se ha ejecutado nada contra el servidor de Odoo para escribir este plan. Se basa en el resultado real del diagnóstico de solo lectura lanzado hoy (company 8, 10/11/2026 13:13 UTC), en tres partes.

Ficheros que acompañan a este plan:

- Plan anterior: `bin/versiones/20261110_PLAN_preparacion_en_lecturas_v1.md`
- Maqueta de las pantallas: `bin/versiones/20261110_IDEAS_preparacion_en_lecturas_v1.html`
- Diagnóstico de solo lectura: `odoo/KOROSHI_preparacion_lecturas_DIAGNOSTICO_2026-11-10.py`
- Salida del diagnóstico: `parte1.txt` (A, J, K), `parte2.txt` (B, C, D, P, I, L), `parte3.txt` (E, F, G, H). En este plan se citan como «P1:línea», «P2:línea», «P3:línea».

---

## 0. Qué ha cambiado respecto a la v1 y por qué

| # | Cambio | Por qué (evidencia) |
|---|---|---|
| 1 | **Requisito previo nuevo: poner en producción koroshi_operarios v2.3** (con la corrección de `empezar`, como v2.3.3). | En el servidor está instalada la **2.2.2**, no la 2.3 (P1:15). La v1 daba por hecho que el include iba sobre la v2.3. |
| 2 | **La corrección de `empezar` deja de ser bloqueante.** Se mantiene, pero ya no es «antes de todo». | 0 tareas `dejada/otro` en 14 días, 0 con la OUT validada (P2:368-369). Solo hay 4 tareas en total (P2:357): Lecturas casi no se usa todavía. |
| 3 | **La activación ya no es por grupo de usuario, sino por empleado + PDA.** El grupo pasa a ser solo el de quien configura. | Todas las move.line de las OUT del tipo 45 de 14 días las escribe **un único usuario compartido** (id 394, 42.567 líneas, P2:331-332). Los 7 empleados tienen tarjeta y **ninguno tiene usuario** (P2:365). Un grupo activaría la pantalla en todas las PDA a la vez. |
| 4 | **Sin embalajes ni unidades de medida distintas: se quitan de la v3.3.** | 0 embalajes con barcode, uom siempre Unidades, tracking `none` (P2:375, P2:383). |
| 5 | **Sin lotes, propietarios ni paquetes de origen: los rechazos de `/cargar` por esos motivos quedan como defensa, no como caso.** | lot_id 0, lot_name 0, package_id 0, owner_id 0 (P3:37-44); 0 quants con paquete en las ubicaciones de origen (P3:54). |
| 6 | **La búsqueda de producto debe contemplar los códigos alternativos (`product.barcode`) y la conversión UPC/EAN.** | `product_multi_barcode` instalado con 463.120 registros en `product.barcode` (P2:384, P1:4). Nomenclatura con `upc_ean_conv=always` (P2:297). |
| 7 | **Riesgo «acción automática en cada lectura» rebajado.** | Sobre stock.move.line solo está la 19, **inactiva** y limitada a INT (P1:212-214). La 20 es sobre `stock.quant.package.name` (se dispara al crear caja, no al leer) (P1:215-216). 16, 17 y 18 son sobre stock.picking (16 solo DEV/INT; 17 y 18 al cambiar `state`, es decir, al validar) (P1:209-223). |
| 8 | **Bultos (`number_of_packages`): nadie los escribe de forma sistemática hoy.** La v3.2 sigue bloqueada, pero la pregunta cambia: ya no es «qué escribe Brain Station», sino «qué camino de validación deja los bultos vacíos». | De 576 OUT, 237 tienen bultos = cajas distintas, **339 vacío/0** y **0 distintos** (P3:51). Cuando se escribe, siempre es correcto. |
| 9 | **Lotes Z-: sube la prioridad.** Se parte la v3.4 en v3.4a (Z- recorriendo OUT a OUT, barata) y v3.4b (reparto multipedido, cara). La v3.4a pasa **delante** de la v3.3. | 29 de las 41 OUT asignadas ahora están dentro de un lote Z- (P3:29). 12 lotes Z- en 14 días, 6 creados hoy (P3:101-103). Con la v1, la pantalla solo serviría para ~3 de cada 10 OUT asignadas. |
| 10 | **Lectura de ubicación: por defecto «no».** | Ubicaciones de origen distintas por OUT: p50 1, **p90 57**, máx 212 (P3:21). Casi una ubicación por línea: leer la ubicación duplicaría las lecturas. |
| 11 | **Diseño para OUT de una línea y una unidad.** | 96,2 % de las líneas son de 1 ud; uds/línea p90 1, máx 5 (P3:22-23). «Cantidad» pasa a ser un caso raro. |
| 12 | **La OUT es bimodal (pedidos pequeños y pedidos de tienda).** El piloto debe medirse con OUT de tienda. | Líneas por OUT p50 **2**, p90 **84**, máx 365 (P3:18). Solo 758 de las 1.836 OUT validadas del tipo 45 tienen origen de tienda S-66 (P2:284). |
| 13 | **Se confirma que la app clásica guarda de golpe al final.** Ventaja real nueva de la pantalla propia: lo leído no se pierde si la PDA se cae. | Tiempo entre la primera y la última escritura de las move.line de una OUT: p50 0, p90 0 min (P3:32); última escritura a `date_done`: p50 7 s, p90 25 s (P3:74). |
| 14 | **Supuesto nuevo X13: asistente de transportista en `put_in_pack`.** | `delivery_barcode` y `delivery_xpo` instalados (P1:9, P1:30). En Odoo 13, el módulo `delivery` puede devolver el asistente `choose.delivery.package` al meter en caja si la OUT tiene transportista. Si pasa siempre, `/caja` no puede ir por el servidor tal cual. |
| 15 | **Supuesto nuevo X14: el lote Z- guarda su propio estado de lectura.** | `barcode_batch_process` añade `batch.operation.line` con `done_qty` y `cached_json_str`, y en el lote `is_processing`, `last_scanned_picking` y `last_sticker_data` (P1:75-96). Escribir qty_done en una OUT de un Z- por fuera de su app puede dejar ese estado desfasado. |
| 16 | **Tres módulos de terceros tocan el JS de la app de picking**, no uno. | `stock_barcode_optimization` (abstract y picking_client_action), `barcode_archive_location` (picking_client_action, demand_location) y `barcode_batch_process` (P1:48-50, P1:59-62, P1:163-168). |
| 17 | **El bloque H del diagnóstico falló** (`auto_join`) y H5 no salió. S10 sigue abierta. Corrección en §15. | P3:116. |
| 18 | **Esfuerzo:** hasta el piloto v3.1 **≈ 12-16 días** (igual, con otra composición); total hasta v3.3 con v3.4a **≈ 20-27 días**. | §14. |

---

## 1. Resumen

Se crea un módulo nuevo, `koroshi_preparacion`, que el operario verá como «Lecturas v3.x».

- Hace un `include` mínimo de `_abrir` en koroshi_operarios **v2.3.3 (que primero hay que poner en producción: hoy está la 2.2.2)**.
- Si el modo es «propia» para **ese empleado y esa PDA** y la asignación es una OUT suelta (no de un lote Z-), abre una acción de cliente propia en la que se leen las piezas y se meten en caja.
- Todo se escribe en datos estándar: `qty_done` y `result_package_id` (con `put_in_pack`).
- En cualquier otro caso se sigue por el camino de hoy (`_super`).

**La decisión clave se mantiene:** en el primer piloto **la validación se sigue haciendo en la app clásica**. El diagnóstico lo refuerza: hoy 339 de 576 OUT quedan con `number_of_packages` vacío y no sabemos qué camino lo deja así (P3:51).

**Lo nuevo más importante:** el 71 % de las OUT asignadas ahora mismo va en lotes Z- (P3:29). La v3.1 es el piloto seguro, pero el valor real llega con la v3.4a (Z- recorriendo OUT a OUT), que se adelanta.

## 2. Comparación de los tres planes estudiados (1-10, 10 = mejor)

Sin cambios respecto a la v1: se sigue con la base «Riesgo primero» + pantalla y principios de «Operario primero» + recorte de alcance y regla «validar_out decide» de «Mínimo».

| Plan | Seguridad | Valor para el operario | Esfuerzo (10 = poco) | Encaje con las reglas | Media |
|---|---|---|---|---|---|
| Mínimo viable | 6 | 6 | 8 | 8 | 7,0 |
| **Riesgo primero** | **9** | 7 | 5 | **9** | **7,5** |
| Operario primero | 5 | **9** | 4 | 6 | 6,0 |

Matiz nuevo: el «Validar igual» de «Operario primero» queda aún más descartado (G1: con `pedido_pendiente='no'`, 63 OUT se validaron con moves cancelados y sin pedido pendiente, P3:61; P2:312), y su gestión de embalajes ya no hace falta (X6 cerrado).

## 3. Decisión recomendada

1. **Poner en producción koroshi_operarios v2.3.3** (v2.3 + corrección de `empezar`) antes de instalar nada nuevo. Es el requisito real; la corrección en sí ya no es urgente.
2. **Módulo aparte, apagado al instalar y con interruptor en el servidor.** No se toca `stock_barcode` ni la v2.3, y no hay campos nuevos en las tablas de stock.
3. **Activación por empleado y por PDA**, no por grupo de usuario (usuario compartido).
4. **Primer valor real (v3.1): leer y encajar en la pantalla propia; validar en la app clásica**, solo en OUT sueltas.
5. **v3.4a (lotes Z- OUT a OUT) justo después del piloto v3.1**, antes de la v3.2 si X1/X7 siguen abiertos, y siempre antes de la v3.3.
6. **Validación propia (v3.2) solo cuando se sepa qué deja los bultos vacíos (X1) y si XPO va dentro de `action_done` (X7).**

## 4. Supuestos: estado tras el diagnóstico

| # | Supuesto | Estado | Evidencia | Qué queda / cómo se cierra |
|---|---|---|---|---|
| X1 | Brain Station escribe `number_of_packages` al validar | **Refutado como regla general; origen sigue abierto** | 576 OUT: 237 = cajas distintas, 339 vacío/0, 0 distintos (P3:51). `delivery_package_number` instalado 13.0.1.1.0 con «última» 13.0.1.0.0 (P1:8). | Cruzar las 339 vacías con: dentro de lote Z- / suelta, origen S-66 o no, con o sin `result_package_id`, usuario y `date_done` (diagnóstico v2, §15). Leer el Python de `delivery_package_number` 1.1.0. |
| X2 | `put_in_pack(package_name=...)` es la firma de Brain Station y renombra «la última caja» | **Abierto (indicios a favor)** | 40.916 move.line con caja: 38.389 CJ y 2.527 PACK (P3:41-43); `package_level_id` en 40.894 (P3:40), coherente con el `_put_in_pack` estándar de Odoo 13. Brain Station solo registra 2 campos y 3 vistas en Python (P1:47-54). | Leer el Python de `stock_barcode_optimization`. Averiguar de dónde salen las 2.527 cajas PACK (¿lotes Z-? ¿caja sin nombre?). |
| X3 | El contexto `barcode_view` cambia qué líneas toma `put_in_pack` | **Abierto** (no se cierra con diagnóstico) | — | Leer `stock/models/stock_picking.py` 13.0 community. |
| X4 | Con nada leído, `put_in_pack` toma las líneas reservadas con qty_done=0 | **Abierto** | — | Igual que X3. Se mantiene la defensa: `/caja` exige al menos una línea con qty_done>0 y sin caja. |
| X5 | La app clásica guarda valores ABSOLUTOS desde su memoria | **Confirmado en parte**: guarda de golpe al final | Primera a última escritura por OUT: p50 0, p90 0 min (P3:32); última escritura a `date_done`: p50 7 s (P3:74). | Que sean absolutos sigue sin leer en el JS. La defensa de la v1 se mantiene (una sola salida a la app; no abrir si hay otra tarea viva). |
| X6 | La app suma `packaging.qty` al leer un embalaje | **Cerrado: no aplica** | 0 embalajes con barcode; uom siempre Unidades (P2:375, P2:383). | Se quitan los embalajes del alcance. Si un día aparecen: «Ábrela en la app». |
| X7 | XPO se envía dentro de `action_done` | **Abierto** | No hay canal de cola de XPO; solo `root`, `root.invoice_validate_sii` y `root.s4t_sync` (P1:242-245). Si XPO se envía, no va por cola. | Leer `delivery_xpo` y `koroshi_xpo_bultos` (`xpo_es_send_shipping`). Contar OUT del tipo 45 por `carrier_id` y `delivery_type` (§15). |
| X8 | `start_batch_processing` y `action_validate` son de `barcode_batch_process` | **Confirmado en parte** | `start_batch_processing` está en la vista kanban de lotes del módulo (P1:67-68). `action_validate` no aparece. H5 no llegó a ejecutarse (P3:116). | Volver a lanzar H corregido (§15) y leer el Python/JS del módulo. Necesario para la v3.4a. |
| X9 | El tipo 45 es el de OUT de tiendas | **Confirmado con matiz** | Tipo 45 «Órdenes de entrega», prefijo EFFEC/OUT/, `show_reserved=True` (P2:8-10). Pero solo 758 de 1.836 validadas tienen origen S-66 (P2:283-284): también lleva otros pedidos (origen W-…). | Decidir si la pantalla vale para todo el tipo 45 o solo para origen S-66 (U10). |
| X10 | Cada operario tiene su usuario de Odoo en la PDA | **Refutado** | Un único usuario escribe todas las move.line (P2:331-332); 7 empleados, 0 con usuario (P2:365). | Activación por empleado + PDA. El operario solo se identifica por `employee_id`: la tabla propia de lecturas es la única auditoría por persona. |
| X11 | Hay acciones automáticas on_write sobre stock.move.line | **Refutado para las OUT** | La 19 (stock.move.line) está **inactiva** y su dominio es solo INT (P1:212-214). La 20 es sobre `stock.quant.package` por `name` (P1:215-216). | Vigilar: si alguien reactiva la 19, no afecta a OUT. La 20 se dispara en cada `/caja` (como hoy con la app). 17 y 18 se disparan al validar, sea cual sea la pantalla. |
| X12 | El eco de las dos vías (bus y campo) llega en menos de 150 ms | **Abierto** (no se puede medir desde el servidor) | P1:250. | Medir en la PDA en T3 (simulación). |
| **X13** (nuevo) | `put_in_pack` en una OUT con transportista devuelve el asistente `choose.delivery.package` (módulos `delivery`/`delivery_barcode`) | **Abierto** | `delivery_barcode` y `delivery_xpo` instalados (P1:9, P1:30). | Leer `delivery/models/stock_picking.py` 13.0 (`_pre_put_in_pack_hook`) y contar OUT del tipo 45 por transportista (§15). Si devuelve el asistente siempre, `/caja` debe pasar el contexto que use la app o la v3.1 cierra las cajas en la app. |
| **X14** (nuevo) | El lote Z- guarda su propio estado de lectura (`batch.operation.line.done_qty`, `cached_json_str`, `is_processing`) que se desfasa si se escribe qty_done por fuera | **Abierto** | Campos de `barcode_batch_process` (P1:75-96). 6 de 12 lotes tienen OUT en estados distintos (P3:114): ya se validan OUT sueltas dentro de un lote. | Leer el Python de `barcode_batch_process` antes de la v3.4a. Hasta entonces, `/cargar` rechaza las OUT de un Z-. |

## 5. Preguntas del servidor (S1-S10): estado

| # | Pregunta | Estado | Evidencia y consecuencia |
|---|---|---|---|
| S1 | Qué sobrescribe `stock_barcode_optimization` en Python y qué hace su JS al validar | **Abierto (acotado)** | En datos solo añade `stock.location.sequence`, `res.users.can_see_barcode_thumbnail`, 3 vistas y 2 JS: `abstract_client_action.js` y `picking_client_action.js` (P1:47-54). Además, `barcode_archive_location` también tiene su `picking_client_action.js` (P1:163-168). Sus métodos Python no se ven desde el servidor (P1:248). → Leer los 3 JS del bundle y, si se puede, el Python. |
| S2 | ¿`delivery_package_number` calcula los bultos? ¿XPO va dentro de `action_done`? | **Abierto (con dato nuevo)** | 339 de 576 OUT sin bultos (P3:51): no hay cálculo automático que cubra todo. Sin cola de XPO (P1:242-245). → Diagnóstico v2 (§15) y lectura de código. |
| S3 | Acciones automáticas on_write sobre stock.move.line, stock.picking o stock.quant.package | **Respondida** | 19 inactiva (move.line, INT); 20 activa (package, `name`); 16 activa (picking, DEV/INT); 17 y 18 activas (picking, `state`) (P1:209-223). Ninguna se dispara al leer en una OUT. |
| S4 | ¿Tipo 45 = OUT de tiendas? ¿`show_reserved`, `no_overscan`, otros campos? | **Respondida** | Sí (con otros pedidos además de tiendas); `show_reserved=True`; `stock_barcode_no_overscan` **desinstalado** (P1:37); campos de terceros: `count_picking_2binvoiced` y `reserve_rule_ids` = 1 regla de reserva (P2:4, P2:10). |
| S5 | ¿Usuario por operario o compartido? ¿Acción de inicio? | **Respondida** | Compartido (P2:331-332). El usuario de la PDA no tiene acción de inicio; el de IT tiene «Operarios» (P2:322-324). |
| S6 | Nomenclatura y choques de códigos | **Respondida (con un cabo suelto)** | Nomenclatura por defecto, `upc_ean_conv=always`, reglas: ubicación `414`, paquete `PACK`, lote `10`, producto `.*` (P2:297-306). Barcodes principales: 0 repetidos, 0 con nombre de caja, **1 igual a una ubicación**, 0 con tarjeta; **236 referencias son el barcode de algún producto** (P2:378-380). Las ubicaciones (`KO_…`, `SORTER`) y las CJ no siguen las reglas `414`/`PACK` (P2:388-389). Cabo suelto: no se revisaron choques en los 463.120 `product.barcode` alternativos. |
| S7 | Embalajes con barcode y uom distinta | **Respondida: no hay** | P2:375, P2:383. |
| S8 | Tareas `dejada/otro` con la OUT done | **Respondida: 0** | P2:368-371. Solo 4 tareas en total (P2:357). |
| S9 | OUT con lote, paquete de origen o propietario; validación sin caja | **Respondida** | 0 lotes, 0 paquetes de origen, 0 propietarios (P3:37-44). 1.651 de 42.567 move.line (3,9 %) se validaron **sin caja** (P3:45). |
| S10 | Qué hace `barcode_batch_process` (`start_batch_processing`, `action_validate`) | **Abierto** | H5 no se ejecutó por el error `auto_join` (P3:116). Solo se sabe que `start_batch_processing` es un botón de su kanban (P1:68). |

## 6. Datos del diagnóstico que fijan el diseño

| Dato | Valor | Consecuencia |
|---|---|---|
| Volumen diario (tipo 45) | 1.445-7.260 uds/día laborable; 324 OUT el 09/11 (P3:4-15) | Con el escenario de 10.000 u/día y 96 % de líneas de 1 ud: ≈ 10.000 lecturas/día. Con varias PDA, 2-3 lecturas/s en pico (sin cambios respecto a la v1). |
| Líneas por OUT | p50 2, p90 84, máx 365 (P3:18) | Bimodal. La lista de la pantalla debe aguantar 400 líneas sin paginar en el servidor (cargar una vez, refrescar por línea). |
| Uds por línea | 96,2 % de 1 ud; máx 5 (P3:22-23) | Un EAN = una línea completa casi siempre. «Cantidad» es secundario. El doble pitido «línea completa» será el normal: usar el **simple** para «sumado y completa» cuando la línea es de 1 ud, y reservar el doble para líneas de >1 ud. |
| Ubicaciones por OUT | p50 1, p90 57, máx 212 (P3:21) | `leer_ubicacion='no'` por defecto. La tarjeta `ir_a` es la pantalla principal (una ubicación por pieza). |
| Cajas por OUT | p50 3, p90 10, máx 20; uds por caja p50 9, p90 25, máx 54 (P3:48-49) | Coincide con «caja plena ≈ 10 uds». Aviso suave a partir de 25 uds en una caja abierta (v3.3). |
| OUT asignadas ahora | 41; 29 en lote Z- (P3:26-29) | Cobertura de la v3.1: ~30 %. Justifica adelantar la v3.4a. |
| Lotes Z- | p50 20 OUT, 284 move.line, 58 ubicaciones; 51 % de productos van a más de una OUT (P3:107-113) | El reparto multipedido (v3.4b) es caro. Recorrer OUT a OUT (v3.4a) pierde la ventaja del recorrido único, pero es barato. |
| Sobrelectura y productos añadidos | 0 y 0 (P3:64-65) | Se confirma U4: en la v3.x no se lee de más ni se añaden productos. |
| Faltantes | 1 en 14 días (P3:69) | El circuito de Faltante casi no se usa: el include de faltantes se deja simple. |
| Pedido pendiente | parámetro `pedido_pendiente='no'`; 63 OUT done con moves cancelados sin pendiente (P2:312, P3:61) | U5 casi respondida: la pantalla respeta el parámetro; por defecto «no». |
| OUT sin responsable (`user_id`) | 576 de 576 (P3:75) | El monitor no puede saber quién prepara por `user_id`: lo sabrá por la tarea de Lecturas y la tabla propia. |
| Usuarios de la OUT | 0 de 576 con más de un usuario (P3:73) | No hay base para medir conflictos entre PDA; el bloqueo NOWAIT se prueba a propósito en T4. |

## 7. Arquitectura

```
Lecturas (koroshi_operarios v2.3.3: hoy en el servidor está la 2.2.2)
  └─ include (koroshi_preparacion): willStart lee el modo; _abrir desvía si modo='propia' y tipo='out' y la OUT no es de un Z-
        └─ do_action('koroshi_preparacion.accion_pantalla', {desde_operarios, preparacion_out, preparacion_operario})
              Pantalla de preparación = Operarios.extend({...})
              (hereda _aviso, _pitido, _vibrar, _falloRpc, _esSinConexion, _sinConexion/_probarConexion,
               _confirmar, _abrirHoja/_cerrarHoja, _foco/_estadoLector)
              ├─ Faltante (koroshi_faltantes, con include: si desde_preparacion, «Volver a la OUT» = history_back)
              └─ «Abrir/Validar en la app» = /stock_barcode/scan_from_main_menu + do_action (encima de la pila)
        al terminar: history_back → Lecturas.on_attach_callback → «¡Hecho!» → siguiente en 3 s
```

- **Módulo:** `koroshi_preparacion` 13.0.1.x. Depende de koroshi_operarios (≥ 2.3.3), koroshi_faltantes y koroshi_caja_existente. Conserva `stock_barcode`, porque la salida a la app lo usa.
- **Pila de acciones:** igual que en la v1.
- **Lo nuevo:** el modelo `koroshi.preparacion.lectura`, el modelo `koroshi.preparacion.piloto` (empleados habilitados, ver §10), el grupo `koroshi_preparacion.grupo_responsable` (solo para configurar) y los parámetros `koroshi_preparacion.activa`, `koroshi_preparacion.validar_propia` y `koroshi_preparacion.leer_ubicacion` (por defecto `'no'`).
- **Ningún campo nuevo** en stock.picking, stock.move, stock.move.line, stock.picking.batch, stock.picking.type ni hr.employee.
- **Robustez del include:** try/catch en `willStart`, solo sobrescribe `_abrir`. Si el modo no se puede leer, `'app'`. Ojo: en `web.assets_backend` ya hay JS de 3 módulos de terceros sobre la app de picking (P1:48-50, P1:59-62, P1:163-168); el include no toca ninguno de ellos.

## 8. Versiones y alcance

| Versión | Módulo | Alcance | Escribe en stock |
|---|---|---|---|
| **v2.3.3** | koroshi_operarios | Lo de la v2.3 (aún no instalada) + en `Tarea.empezar`, si la tarea abierta tiene sus pickings validados: `_cerrar('acabada', 'validada', _hora_validacion)` en vez de `dejada/otro`. | No |
| **v3.0** base + simulación | koroshi_preparacion 1.0 | Parámetros (apagado), tabla de empleados del piloto, include de `_abrir`, pantalla completa con `/cargar` y `/leer` en **simulación** (`activa='sombra'`, nunca una constante del código). Búsqueda de producto: **primero entre los productos de la OUT** (barcode principal, códigos alternativos de `product.barcode` y UPC↔EAN con 0 inicial), luego referencia. Mide latencia, orden y choques. | No |
| **v3.1** leer y encajar; validar en la app (**primer piloto**) | 1.1 | Suma de qty_done en el servidor con bloqueo e `id_lectura`, «Deshacer última», «Cantidad» (secundario), cerrar caja (`put_in_pack` con CJ, según X13), Faltante, Saltar, «Abrir en la app» y Salir. Al terminar, **«Validar en la app»**. Solo OUT sueltas. | qty_done y cajas |
| **v3.4a** lotes Z- OUT a OUT (**adelantada**) | 1.2 | Desde un lote Z- asignado, la pantalla recorre sus OUT una a una con el mismo flujo de la v3.1 y se valida cada OUT en la app (o con `validar_out` cuando exista la v3.2). Sin reparto multipedido. No se empieza sin X8, X14 y S10. | qty_done y cajas |
| **v3.2** validar en la pantalla propia | 1.3 | `/validar` con `koroshi.faltante.validar_out` + `_cerrar_operarios` + bultos según X1/X7. Solo con `validar_propia='1'`. Lectura de O-BTN.validate y O-BTN.pack. | Validación |
| **v3.3** comodidad y control | 1.4 | Lectura de ubicación (`no`/`aviso`/`obligatoria`, por defecto `no`), cierre de caja automático al leer una CJ nueva, aviso de caja llena (>25 uds), «validar al completar», recuperar la sesión, aviso de CJ de otra tienda e informe app frente a propia. **Sin embalajes.** | — |
| **v3.4b** lotes Z- multipedido | 2.0 | Reparto de cada pieza a la caja de su OUT en un solo recorrido y validación OUT a OUT con `validar_out` (nunca `batch.done()`). Solo si la v3.4a demuestra que hace falta. | Sí |
| **v3.5** (opcional) | operarios v2.4 | Mixin `koroshi_operarios.Utilidades`. | No |

Fuera de la v3.x: crear líneas fuera de lo reservado o leer de más (G2/G3 = 0), la ronda de revisión (INT), la cola sin conexión, el modo «poner a 0» y los embalajes.

## 9. Flujo de pantallas

Ver la maqueta `20261110_IDEAS_preparacion_en_lecturas_v1.html`. Cambios respecto a la v1 marcados con **(v2)**.

**Disposición vertical fija** (PDA de unos 5"), con las clases `o_ko_*` de la v2.3:

```
[Cabecera: quién soy · OUT/xxxx · tienda · «uds 12/40» + barra]                 15 %
[TARJETA CENTRAL del paso]                                                      55 %
[Aviso de la última lectura (verde/rojo)]                                       10 %
[Botonera: Caja · Deshacer · Cantidad] (botones ≥ 64 px, separados ≥ 12 px)     12 %
[Pie: ☰ (Faltante, Saltar, Abrir en la app, Salir) · reloj · sonido]
```

**(v2)** «Caja» pasa a ser el primer botón: con 1 ud por línea, cerrar caja es mucho más frecuente que cambiar la cantidad.

Principios: el camino normal solo con el lector; una cosa grande cada vez; se puede usar con guantes; verde/agudo = sumado; doble agudo = línea de varias uds completa **(v2)**; triple + fondo verde = OUT completa; rojo/grave/vibración = error y la pantalla no avanza; **lo que no ha confirmado el servidor no cuenta**.

| Paso | Tarjeta | Entradas | Salidas |
|---|---|---|---|
| `cargando` | «Abriendo OUT/x para Nombre» | — | `ir_a`, o error y «Abrir en la app» |
| `ir_a` (azul) | «VE A» + ubicación ≥ 40 px · «Ref 12345 · Rojo · M» ≥ 28 px · «Coge 1» | EAN directo (por defecto); lectura de ubicación solo si `leer_ubicacion` ≠ `no` | `leer`; **(v2)** con 1 ud, la lectura correcta salta directamente al siguiente `ir_a` |
| `leer` (blanca) | Solo en líneas de >1 ud: Ref + talla/color + «2 de 3» | EAN → +1. EAN de otra línea pendiente → se suma a esa y avisa «Era la ref X». EAN que no está en la OUT → rojo. Línea completa → rojo «Ya tienes las 3». | siguiente `ir_a` |
| `caja` (amarilla) | «Cerrar caja CJ… con 8 uds» | leer CJ o pulsar «Caja» | `ir_a`. Sin lecturas sin caja: «La caja está vacía». Si sale un asistente (X13): rojo «Ciérrala en la app». |
| `resumen` (verde) | «Todo leído · 40 uds · 4 cajas», chips de cajas | v3.1: **«Validar en la app»** (80 px). v3.2: «Validar» o «Cerrar caja y validar». | — |
| `resumen` incompleto | «Faltan 3 uds de 2 refs» | Solo [Ir a Faltante] y [Abrir en la app]. No hay «Validar igual». | — |
| `preguntar` (v3.2) | Solo si `koroshi_faltantes.pedido_pendiente='preguntar'` (hoy vale `no`, P2:312) | toque | `validada` |
| `validada` | Fondo verde «OUT/xxxx validada» | — | `history_back` a 1,5 s |

**Orden de clasificación de cada lectura** (en el servidor; confirmado con C2/I2):

1. matrícula CJ (patrón `CJ` + dígitos; 0 choques con EAN, P2:379) → caja;
2. O-BTN.* (v3.2);
3. **(v2)** EAN de un producto **de la OUT** (principal, alternativos de `product.barcode`, UPC↔EAN). Va antes que la ubicación porque hay 1 EAN que coincide con un barcode de ubicación (P2:379);
4. referencia (`default_code`) de un producto de la OUT. **(v2)** Nunca antes que el EAN: 236 referencias son el barcode de algún producto (P2:380);
5. ubicación;
6. tarjeta de empleado → «Ya estás dentro» o «Termina esta OUT antes de cambiar»;
7. otra OUT → «Estás en OUT/x; usa Saltar»;
8. EAN de un producto que no está en la OUT → «Este artículo no está en este pedido»;
9. desconocido → error.

**Comportamiento transversal:** sin conexión, banda roja de la v2.3 y «Reintentar» con el mismo `id_lectura`; inactividad solo avisa; antirrebote del eco medido (X12); activación por PDA con pulsación larga en ☰ (localStorage).

## 10. Convivencia, activación y vuelta atrás

**(v2) Orden de decisión**, adaptado al usuario compartido:

1. **`koroshi_preparacion.activa`** (data noupdate, `'0'` al instalar). El servidor lo comprueba en cada escritura.
   - `'0'`: nadie; las rutas no escriben.
   - `'sombra'`: pantalla en simulación para los empleados del piloto.
   - `'piloto'`: los empleados del piloto, en las PDA marcadas.
   - `'1'`: todos los empleados en las PDA marcadas.
2. **Empleados del piloto** (`koroshi.preparacion.piloto`: `employee_id`, `activo`, `nota`), vacío al instalar. El empleado se conoce por la tarjeta en Lecturas. Sustituye al grupo de la v1, que no sirve porque todas las PDA entran con el mismo usuario.
3. **localStorage `koroshi_preparacion_pda`** = `'app'` | `'propia'` | `''`. **`'app'` gana siempre.** Pasa a ser un control principal, no secundario.
4. **`koroshi_preparacion.validar_propia`** (`'0'` por defecto).
5. **Grupo `koroshi_preparacion.grupo_responsable`**: solo para ver el menú de configuración, la tabla de lecturas y el informe.

Vuelta atrás, de menos a más: (a) la PDA en `'app'`; (b) quitar al empleado del piloto; (c) `activa='0'`, efecto inmediato; (d) dejar el módulo instalado sin usar; (e) desinstalar solo en un mantenimiento planificado, con el zip con fecha guardado en `bin/`.

Una OUT a medias se termina en la app sin perder nada, siempre que no haya otra PDA con la app abierta en esa OUT (X5: la app guarda de golpe al final, P3:32 y P3:74).

## 11. Endpoints (`/koroshi/preparacion/*`)

Reglas comunes: `type='json'`, `auth='user'`; escriben con el usuario de la sesión, sin sudo (salvo en las tablas propias); responden `{ok, que, msg, ...}`; todas las rutas que escriben comprueban `activa` y el empleado del piloto, y se niegan con `'0'` o `'sombra'`. **(v2)** Como `write_uid` siempre será el usuario compartido, todas reciben `employee_id` y `pda` y lo guardan en `koroshi.preparacion.lectura`.

| Ruta | Parámetros | Qué hace | Defensas |
|---|---|---|---|
| `/modo` | `{employee_id, pda}` | `{modo, validar_propia, leer_ubicacion, motivo}` | — |
| `/cargar` | `{picking_id\|codigo, employee_id}` | OUT, líneas pendientes en el orden de `koroshi.faltante.lineas_pendientes`, cajas y progreso. | Rechaza: company ≠ 8, tipo ≠ 45 (o según U10), done/cancel, estado ≠ assigned, **OUT de un lote Z- (hasta v3.4a; X14)**, lote/paquete de origen/propietario (hoy 0, se deja como defensa), otra tarea o asignación viva en la OUT de otro empleado. Siempre ofrece «Abrir en la app». |
| `/leer` | `{picking_id, codigo, id_lectura, employee_id, pda}` | Clasifica (§9). En un producto elige la move.line (mismo producto, qty_done < reservado, preferencia por la ubicación actual y luego el orden) y hace `SELECT ... FOR UPDATE NOWAIT` + `write({'qty_done': q+1})`. **(v2)** La búsqueda de producto no se copia tal cual de faltantes (`_producto` solo mira `barcode` y `default_code`): se limita a los productos de la OUT y se comprueba en T1 que la búsqueda por `barcode` encuentra los alternativos de `product_multi_barcode`. | Idempotente por `id_lectura`. Tope en lo reservado. Sin crear líneas. `recargar` si la línea desaparece. NOWAIT. Con `'sombra'`, `simulada=True` sin escribir. |
| `/cantidad` | `{linea_id, cantidad, id_lectura}` | Fija la cantidad leída por esta PDA en la línea | 0 ≤ x ≤ reservado (máx. 5 hoy, P3:22). |
| `/deshacer` | `{picking_id, pda}` | Revierte la última lectura no deshecha de esta PDA en esta OUT | Solo si la línea aún no tiene caja |
| `/caja` | `{picking_id, codigo?}` | `put_in_pack(package_name=codigo)` → caja_existente → Brain Station → community. Dispara la acción automática 20 (matrículas CJ duplicadas, P1:215). | Exige al menos una línea qty_done>0 sin caja (X4). Patrón CJ. **(v2)** Si devuelve un asistente (`choose.delivery.package` u otro, X13): error y «Ciérrala en la app». El error de la acción 20 se muestra tal cual. |
| `/validar` (v3.2) | `{picking_id, pedido_pendiente}` | Exige todo lo leído en caja. `validar_out` → `_respuesta_validar` → bultos según X1/X7 → `_cerrar_operarios`. Las acciones 17 y 18 (S4T, al cambiar `state`) se disparan igual que hoy. | Todo o nada. Solo `stock.backorder.confirmation`. Otros asistentes → «Abrir en la app». Nunca con todo qty_done=0. |
| `/koroshi/operarios/estado`, `/motivos`, `/saltar` | — | Los de la v2.3, sin cambios | — |

**Prohibido en el código:** `action_done` directo; `force_assign`; escribir `stock.quant`; crear move.line; `stock.immediate.transfer` y `stock.overprocessed.transfer`; las rutas `/stock_barcode/*` salvo `scan_from_main_menu`; **(v2)** escribir en `batch.operation.line` o en los campos de `barcode_batch_process` del lote.

**Tabla `koroshi.preparacion.lectura`:** `picking_id`, `move_line_id`, `batch_id` (v3.4a), `employee_id`, `user_id`, `pda`, `codigo`, `tipo` (leer/cantidad/deshacer/caja/validar), `cantidad`, `id_lectura` (único), `simulada`, `deshecha`, `resultado`, `ms_servidor` **(v2: latencia medida en el servidor)**, `fecha`.

## 12. Impacto módulo a módulo

| Módulo | Qué pasa | Cambio |
|---|---|---|
| koroshi_operarios | **Instalado 2.2.2** (P1:15). Productividad y «¡Hecho!» salen de `qty_done` y `state`; ahora se verán en tiempo real (hoy la app escribe todo al final). | Poner en producción la v2.3.3. El include llega desde el módulo nuevo. |
| koroshi_faltantes | Instalado 1.3.1 (P1:12). Se reutilizan `validar_out`, `lineas_pendientes`, `comprobar_linea`, `_respuesta_validar`, `_cerrar_operarios`. Uso real muy bajo (1 faltante en 14 días). | Un include en el módulo nuevo para «Volver a la OUT». |
| koroshi_caja_existente | Instalado 1.3.0 (P1:11). `_koroshi_corregir_bultos` solo cubre cajas ajenas (1 caja en 2 OUT en 3 días, P3:50). | Ninguno |
| koroshi_xpo_bultos | Cuenta los `result_package_id`. | Ninguno (X7 para la v3.2) |
| koroshi_monitor | leído = qty_done, ahora en tiempo real; bultos = `number_of_packages` (hoy vacío en el 59 %, P3:51). | Ninguno. Avisar a quien lo mire durante el piloto de que el leído se moverá durante la preparación. |
| koroshi_kpi / hoja de carga | La hoja usa `number_of_packages`. | Ninguno en la v3.1. **(v2)** Revisar cómo trata hoy las 339 OUT con bultos vacíos: es un problema que ya existe, no lo crea la pantalla. |
| Reparto y etiquetas de zona (cron 202) | Crea los lotes Z- cada día a las 04:00 UTC (P1:232). | Ninguno. El piloto, fuera de esa franja. |
| Lotes Z- / barcode_batch_process | Por `_super` hasta la v3.4a. `/cargar` rechaza las OUT de un Z-. | Ninguno |
| stock_barcode / Brain Station / barcode_archive_location / delivery_barcode | No se tocan. Siguen siendo la salida de emergencia y, en la v3.1, la validación. | Ninguno |
| S4T (acciones 17 y 18, crones 173 y 182) | Controlan matrículas y nombres de caja al cambiar `state` (P1:217-223); Get Orders cada 15 min (P1:235) puede cambiar la reserva a mitad. | Ninguno. `recargar` si cambia la reserva. |

## 13. Pruebas (sin validar OUT reales)

| Fase | Qué | Dónde |
|---|---|---|
| T0 | Revisión de código y lint. `TransactionCase` solo con un entorno con addons Enterprise; si no, funciones puras (elección de línea, clasificación, idempotencia, topes). | Local |
| T1 | **Hecho en parte** (diagnóstico de hoy). Falta: diagnóstico v2 con el bloque H corregido y las consultas nuevas (§15); lectura del JS de los 3 módulos de terceros (bundle); Python de `stock_barcode_optimization`, `barcode_batch_process`, `delivery_package_number` 1.1.0, `delivery` 13.0 (`_pre_put_in_pack_hook`) y `delivery_xpo`. Cierra X1, X2, X7, X8, X13, X14, S1, S2, S10. | Servidor (lectura) |
| T2 | Instalar v2.3.3 (primero) y luego v3.0 con `activa='0'` fuera de horas y fuera de la franja del cron 202, **con permiso expreso del usuario**. Comprobar que Lecturas funciona igual (OUT, Z-, Faltante, ☰) y que no hay errores de JS. | Producción, apagado |
| T3 | `activa='sombra'`, 20-30 OUT reales **de tienda (origen S-66) y sueltas**, con al menos 5 de más de 80 líneas. Se mide latencia (`ms_servidor` + PDA), orden, EAN no encontrados (alternativos, UPC), choques y eco (X12). Cero escrituras en stock. | Producción, simulación |
| T4 | Piloto v3.1: 1 empleado, 1 PDA, franja tranquila, responsable delante y `activa='0'` a mano. Se valida en la app clásica. Comprobar por OUT: qty_done = lo leído; cajas CJ; `number_of_packages` (comparar con el 59 % vacío de hoy); etiquetas y XPO; tarea `acabada/validada`; monitor, KPI y hoja de carga; sin duplicados por `id_lectura`; NOWAIT con dos PDA; corte de wifi; **cerrar caja en una OUT con transportista (X13)**. | Producción |
| T4a | Piloto v3.4a con un lote Z- pequeño (≤ 10 OUT): comprobar que el lote sigue abriéndose y validándose bien en su app después (X14). | Producción |
| T5 | v3.2: primero en una copia o staging si existe (U3). En producción, OK expreso del usuario, OUT a OUT. | — |

**Nunca:** un «simulacro» de `button_validate` con rollback en producción; un modo de prueba que se active editando una constante; validar OUT reales en pruebas.

## 14. Riesgos (por gravedad)

1. **Bultos o XPO al validar en la pantalla propia.** Hoy ya faltan bultos en 339 de 576 OUT. → La v3.1 valida en la app; la v3.2 solo con X1/X7 resueltos.
2. **(v2) Escribir en OUT de lotes Z- por fuera de su app** (X14). → Rechazo en `/cargar` hasta la v3.4a; la v3.4a no empieza sin leer `barcode_batch_process`.
3. **Lo que hace el JS de terceros y la pantalla se saltaría** (3 módulos: impresión, peso, comprobaciones, ubicaciones archivadas). → Leer los 3 JS antes de la v3.1.
4. **(v2) Asistente de transportista al cerrar caja** (X13). → `/caja` no fuerza asistentes; si pasa siempre, la v3.1 cierra las cajas en la app y se replantea.
5. **Transferencia inmediata o `put_in_pack` sin nada leído.** → `validar_out` los rechaza y `/caja` exige lecturas.
6. **App y pantalla propia en la misma OUT** (X5: la app guarda al final con lo que tenía en memoria). → Una sola salida a la app, no se abre si hay otra tarea viva, NOWAIT.
7. **Error de JS en web.assets_backend** (precedente del 03/11). → Include mínimo en try/catch, instalación fuera de horas, zip para volver atrás.
8. **(v2) Usuario compartido**: cualquier error de activación afecta a todas las PDA. → Activación por empleado + localStorage, con `'app'` ganando siempre.
9. **Latencia:** un RPC con bloqueo por EAN; ≈ 10.000/día en el escenario objetivo. Se mide en T3.
10. **La reserva cambia a mitad** (S4T Get Orders cada 15 min, `reubicar`, cron 202, regla de reserva del tipo 45). → `recargar` y aviso; nunca se crean líneas.
11. **Lecturas dobles o perdidas.** → Antirrebote medido e `id_lectura`.
12. **(v2) Códigos alternativos no encontrados o UPC de 12 dígitos.** → Búsqueda en los productos de la OUT con alternativos y conversión; medido en T3.
13. ~~Acción automática on_write en stock.move.line~~ **(v2) Rebajado**: la 19 está inactiva y es de INT; solo la 20 al crear caja.
14. ~~Embalajes o uom distinta~~ **(v2) Cerrado**: no hay.
15. **(v2) Baja adopción de Lecturas** (4 tareas en total). → El piloto de la v3.1 necesita que el operario ya trabaje con Lecturas v2.3; si no, primero se adopta Lecturas.

## 15. Corrección del bloque H del diagnóstico y consultas nuevas

**Qué falló.** H1 y H2-H4 salieron bien; el error salta justo después de «ejemplos» (P3:115-116), en:

```python
if 'mail.tracking.value' in env and campo_existe('mail.tracking.value', 'field'):
    n_track = env['mail.tracking.value'].search_count([('field.model', '=', 'stock.picking'), ('field.name', '=', 'batch_id'), ...])
```

En Odoo 13, `mail.tracking.value.field` **es un Char** (el nombre técnico del campo), no un many2one a `ir.model.fields` (eso llega en versiones posteriores con `field_id`). `campo_existe` devuelve True porque el campo existe, pero el dominio `('field.model', ...)` intenta recorrer un campo no relacional; el analizador de dominios pide `field.auto_join` a un campo Char, que no tiene ese atributo, y Odoo lanza `AttributeError('auto_join')`, cuyo texto es justamente «auto_join». Como todo el bloque H está en un único `try`, **H5 no llegó a ejecutarse** (S10 y X8 siguen abiertos).

**Corrección propuesta** (en un fichero nuevo con fecha, sin tocar el actual):

1. Mirar el tipo antes de filtrar y usar el modelo del mensaje:

```python
tipo_f = env['ir.model.fields'].search([('model', '=', 'mail.tracking.value'), ('name', '=', 'field')], limit=1).ttype
if tipo_f == 'char':
    dom_t = [('field', '=', 'batch_id'), ('mail_message_id.model', '=', 'stock.picking'), ('create_date', '>=', desde_txt)]
else:
    dom_t = [('field.model', '=', 'stock.picking'), ('field.name', '=', 'batch_id'), ('create_date', '>=', desde_txt)]
n_track = env['mail.tracking.value'].search_count(dom_t)
```

   (Si `batch_id` no tiene `tracking`, saldrá 0: es normal y no es un error.)
2. Partir H en tres `try` independientes (H1, H2-H4 + seguimiento, H5), para que un fallo no se lleve por delante H5.
3. En H5, además de lo que ya busca: listar los métodos públicos visibles por botones en las vistas de `stock.picking.batch` (`button name=` en `arch_db`) y las acciones de servidor del módulo `barcode_batch_process` por `ir.model.data`.

**Consultas nuevas para el diagnóstico v2** (todas de solo lectura):

- **X1/S2:** de las 576 OUT de 3 días, cruzar `number_of_packages` vacío/0 con: `batch_id` Z- o no; origen S-66 o no; nº de cajas; `carrier_id`; hora de `date_done`.
- **X2:** las 2.527 move.line con caja `PACK%`: ¿en OUT de lotes Z-, de qué origen, de qué días?
- **X7/X13:** OUT del tipo 45 de 14 días por `carrier_id` y `carrier_id.delivery_type`; y si el tipo de paquete del transportista está definido.
- **Cobertura:** de las 1.836 OUT validadas en 14 días, cuántas estaban en un lote Z- (y cuántas uds).
- **S6:** EAN de `product.barcode` (alternativos) de los productos de las OUT que se repiten entre productos o coinciden con CJ, ubicaciones o tarjetas; nº de barcodes de 12 dígitos (UPC).
- **F3:** las 1.651 move.line sin caja: ¿de qué OUT (origen, lote)?
- Repetir **L** completo (la parte 2 salió cortada: «66 líneas más», P2:402).

## 16. Preguntas abiertas

**Servidor** (solo lectura): S1, S2 y S10 siguen abiertas (§5), más X1, X2, X3, X4, X5 (parte de valores absolutos), X7, X8, X12, X13 y X14 (§4). S3-S9 quedan respondidas.

**Usuario:**

- U1. ¿Leer la ubicación es «no», «aviso» u «obligatoria»? **Recomendación v2: «no»** (p90 de 57 ubicaciones por OUT).
- U2. Cierre de caja: ¿se lee la CJ cada vez, hay una caja abierta implícita o se usa el botón?
- U3. ¿Hay una copia o staging para probar la validación? ¿Se puede crear una OUT de prueba sin efectos (S4T, XPO, impresión)?
- U4. ~~¿Se acepta que no se pueda leer de más ni añadir productos?~~ **(v2) Respaldado por los datos** (0 casos en 3 días, P3:64-65). Solo falta el visto bueno.
- U5. Pedido pendiente: hoy el parámetro es `no` (P2:312). ¿Se mantiene en la pantalla nueva?
- U6. ¿Quién hace el piloto (empleado y PDA) y en qué franja? ¿Esa persona ya usa Lecturas?
- U7. **(v2) Reformulada:** ¿los lotes Z- se preparan recorriendo OUT a OUT (v3.4a, barato) o hace falta el reparto multipedido en un solo recorrido (v3.4b)?
- U8. ¿Están bien el nombre `koroshi_preparacion` y la serie «Lecturas v3.x»?
- U9. ¿Das permiso para instalar en producción (T2) cuando esté listo: primero operarios v2.3.3 y luego v3.0 con el interruptor a `'0'`?
- **U10 (nueva).** ¿La pantalla vale para todo el tipo 45 o solo para los pedidos de tienda (origen S-66)? Los otros son pedidos pequeños (p50 de 2 líneas).
- **U11 (nueva).** ¿Por qué no se usa todavía Lecturas en el día a día (4 tareas en total)? ¿Hay algo que frene la v2.3 antes de pensar en la v3?

## 17. Esfuerzo estimado (días de desarrollo, sin esperas)

| Bloque | v1 | **v2** | Motivo del cambio |
|---|---|---|---|
| v2.3.3 (corrección de `empezar`) + puesta en producción de la v2.3 | 0,5 | **1** | La v2.3 no está instalada. |
| T1: resto del diagnóstico + lectura del JS/Python de terceros | 1,5-2 | **1-1,5** | Buena parte ya está hecha hoy; quedan H corregido, consultas nuevas y la lectura de código (3 JS en vez de 1). |
| v3.0: módulo, parámetros, tabla de empleados del piloto, include, `/modo`, `/cargar`, `/leer` (simulación), pantalla | 4-5 | **4-5** | Sin grupo, pero con tabla de piloto y búsqueda con alternativos/UPC. Se compensa. |
| v3.1: escritura, `id_lectura`, cantidad, deshacer, `/caja` (con X13), Faltante, «Abrir/Validar en la app», Saltar, tabla de lecturas | 3-4 | **3-4** | — |
| T0, T2, T3, T4 y ajustes | 2-3 (+3-5 de calendario) | **2-3** (+3-5 de calendario) | — |
| Documentación | 1 | **1** | — |
| **Hasta el piloto v3.1** | **≈ 12-16** | **≈ 12-16** | Igual en total, distinto reparto. |
| v3.4a: lotes Z- OUT a OUT (+ T4a) | — | **3-4** | Nuevo, adelantado. |
| v3.2: validación propia + bultos/XPO | 2-4 | **2-4** | X1 sigue abierto, aunque el problema ya está acotado. |
| v3.3: ubicación, cierre automático, aviso de caja llena, validar al completar, sesión, informe | 3-4 | **2,5-3,5** | Sin embalajes. |
| v3.4b: lotes Z- multipedido | 8-12 (v3.4) | **8-12** | Solo si la v3.4a no basta. |
| v3.5: mixin en operarios v2.4 | 1-2 | **1-2** | — |
| **Total hasta la v3.3** | **≈ 17-24** (sin Z-) | **≈ 20-27** (con v3.4a) | Incluye la cobertura de lotes Z- básica. |

## Ficheros en los que se basa (solo leídos)

- `bin/versiones/20261110_PLAN_preparacion_en_lecturas_v1.md`
- `odoo/KOROSHI_preparacion_lecturas_DIAGNOSTICO_2026-11-10.py` (bloque H, líneas 826-900; seguimiento en 884-887)
- Salida del diagnóstico de hoy, partes 1, 2 y 3
- `odoo/modulos/koroshi_faltantes/controllers/main.py` (`_producto`, 129-132; `_ubicacion`, 134-138)
- Los ficheros locales que ya citaba la v1 (tarea.py, operarios_pantalla.js, caja_existente, faltante.py, delivery_carrier.py, monitor, hoja_carga.py)
