# Opción B: pantalla de preparación propia dentro de Lecturas

**Plan final v1 · 10/11/2026**

Estudio de solo lectura: no se ha modificado ningún fichero existente y no se ha ejecutado nada contra el servidor de Odoo.

Ficheros que acompañan a este plan:

- Maqueta de las pantallas: `bin/versiones/20261110_IDEAS_preparacion_en_lecturas_v1.html`
- Diagnóstico de solo lectura: `odoo/KOROSHI_preparacion_lecturas_DIAGNOSTICO_2026-11-10.py`

Dos afirmaciones que cambian el plan, comprobadas en el código local:

- `koroshi_operarios/models/tarea.py:189-194`: `empezar()` cierra la tarea abierta como `dejada/otro` sin mirar si su OUT ya está validada. **El fallo existe.**
- `koroshi_caja_existente/models/stock_picking.py:160-174`: `_koroshi_corregir_bultos` solo escribe `number_of_packages` cuando la OUT tiene cajas de otra OUT (`if not ajenas: continue`). **En una OUT normal no escribe los bultos.** El comentario de las líneas 158-159 dice que los escribe después «la validación de la PDA», pero no aclara si lo hace el JS o el Python de Brain Station.

---

## 1. Resumen

Se crea un módulo nuevo, `koroshi_preparacion`, que el operario verá como «Lecturas v3.x».

- Hace un `include` mínimo de `_abrir` en koroshi_operarios v2.3.
- Si el modo es «propia» y la asignación es una OUT suelta, abre una acción de cliente propia en la que se leen las piezas y se meten en caja.
- Todo se escribe en datos estándar: `qty_done` y `result_package_id` (con `put_in_pack`).
- En cualquier otro caso se sigue por el camino de hoy (`_super`).

**La decisión clave:** en el primer piloto **la validación se sigue haciendo en la app clásica**. Al final de la OUT, el botón principal es «Validar en la app». Así el riesgo más grave, los bultos (`number_of_packages`) y XPO, que dependen de código de Brain Station que no tenemos, no frena el piloto. La validación propia llega después, con su propio interruptor y cuando sepamos qué hace Brain Station al validar.

## 2. Comparación de los tres planes estudiados (1-10, 10 = mejor)

| Plan | Seguridad | Valor para el operario | Esfuerzo (10 = poco) | Encaje con las reglas | Media |
|---|---|---|---|---|---|
| Mínimo viable | 6 | 6 | 8 | 8 | 7,0 |
| **Riesgo primero** | **9** | 7 | 5 | **9** | **7,5** |
| Operario primero | 5 | **9** | 4 | 6 | 6,0 |

**Mínimo viable**
- A favor: el alcance más corto y la idea de dejar que `validar_out` imponga «solo se valida con todo leído».
- En contra: su v3.0 ya valida en la pantalla propia con los bultos y XPO sin resolver, y su prueba de «OUT de prueba sin XPO» da por hecho que se puede crear sin efectos (S4T, cola), cosa no comprobada.

**Riesgo primero** (base elegida)
- A favor: es el único que (a) desacopla la validación con «Validar en la app», (b) pone el interruptor también en el servidor, (c) corrige el fallo de `empezar` antes del piloto, (d) prohíbe el «simulacro con rollback» en producción y (e) separa `validar_propia` en otro parámetro.
- En contra: el «modo sombra» completo cuesta 3-4 días por poco valor, y el entorno de pruebas con Odoo community en docker no sirve tal cual (operarios y faltantes dependen de `stock_barcode`, que es Enterprise).

**Operario primero**
- A favor: la mejor ergonomía (una cosa grande cada vez, guantes, botones de 64 px, colores y sonidos, «lo no guardado no cuenta», aceptar el EAN de otra línea pendiente avisando).
- En contra: valida en la v3.0 con los bultos sin resolver, mete embalajes sin saber si existen y propone un «Validar igual» con líneas pendientes que nunca podría funcionar (`validar_out` devuelve `pendientes`, faltante.py:425-462). Lo que falta va siempre por Faltante.

**Resultado:** base «Riesgo primero» + pantalla y principios de «Operario primero» + recorte de alcance y regla «validar_out decide» de «Mínimo».

## 3. Decisión recomendada

1. **Módulo aparte, apagado al instalar y con interruptor en el servidor.** No se toca `stock_barcode` ni la v2.3, y no hay campos nuevos en las tablas de stock.
2. **Primer valor real (v3.1): leer y encajar en la pantalla propia; validar en la app clásica.** El operario gana la parte que más tiempo lleva (leer y cerrar cajas, sin el diálogo «Nombre del Paquete»). Bultos, XPO, impresión y validación de Brain Station siguen igual.
3. **Validación propia (v3.2) solo cuando el diagnóstico y el código de Brain Station respondan S1-S3** (§13).
4. **Lotes Z- fuera hasta la v3.4**, con diseño propio.
5. **Antes de todo, koroshi_operarios v2.3.3** con la corrección de `empezar`. Sin ella, las métricas del piloto no se pueden comparar.

## 4. Supuestos sin verificar

| # | Supuesto | De dónde sale | Cómo se cierra |
|---|---|---|---|
| X1 | Brain Station escribe `number_of_packages` al validar (¿JS o Python?) | comentario de caja_existente:158 | Leer el JS del bundle `web.assets_backend` y el Python de custom_addons. Diagnóstico bloques J y F2. Si no hay acceso, pedírselo a Brain Station. |
| X2 | `put_in_pack(package_name=...)` es la firma de Brain Station y renombra «la última caja» | caja_existente (inferido) | Igual que X1. Diagnóstico F1/F2 (cajas CJ por OUT). |
| X3 | El contexto `barcode_view` cambia qué líneas toma `put_in_pack` en Odoo 13 | memoria del código community | Releer `stock_picking.py` 13.0 community antes de programar `/caja`. |
| X4 | Con nada leído, `put_in_pack` toma las líneas reservadas con qty_done=0 | community 13 | Igual que X3. Mientras tanto, `/caja` exige al menos una línea con qty_done>0 y sin caja. |
| X5 | La app clásica guarda valores ABSOLUTOS desde su memoria | Enterprise, de memoria | Leer el JS de picking_client_action. Mientras tanto: una sola salida a la app y no abrir si hay otra tarea viva en la OUT. |
| X6 | La app suma `packaging.qty` al leer un embalaje | Enterprise, de memoria | Diagnóstico I3. Si hay 0 embalajes con barcode, no se trata. |
| X7 | XPO se envía dentro de `action_done` | supuesto | Leer delivery_xpo y koroshi_xpo_bultos (`xpo_es_send_shipping`, 283-310). Diagnóstico K3. |
| X8 | `start_batch_processing` y `action_validate` son de barcode_batch_process | notas 21/10 y 09/11 | Diagnóstico J y H5. Solo hace falta para la v3.4. |
| X9 | El tipo 45 es el de OUT de tiendas | diagnósticos anteriores | Diagnóstico B. |
| X10 | Cada operario tiene su usuario de Odoo en la PDA | desconocido | Diagnóstico D2 (write_uid). Decide si se activa por grupo o por PDA. |
| X11 | Hay acciones automáticas on_write sobre stock.move.line (la 20 de cajas duplicadas) | desconocido | Diagnóstico K1. Si la hay, se dispararía en CADA lectura. |
| X12 | El eco de las dos vías (bus y campo) llega en menos de 150 ms | supuesto | Medirlo en la PDA con la pantalla nueva, nunca en la v2.3. |

## 5. Arquitectura

```
Lecturas (koroshi_operarios v2.3.3, sin tocar salvo la corrección de empezar)
  └─ include (koroshi_preparacion): willStart lee el modo; _abrir desvía si modo='propia' y tipo='out'
        └─ do_action('koroshi_preparacion.accion_pantalla', {desde_operarios, preparacion_out, preparacion_operario})
              Pantalla de preparación = Operarios.extend({...})
              (hereda _aviso, _pitido, _vibrar, _falloRpc, _esSinConexion, _sinConexion/_probarConexion,
               _confirmar, _abrirHoja/_cerrarHoja, _foco/_estadoLector)
              ├─ Faltante (koroshi_faltantes, con include: si desde_preparacion, «Volver a la OUT» = history_back)
              └─ «Abrir/Validar en la app» = /stock_barcode/scan_from_main_menu + do_action (encima de la pila)
        al terminar: history_back → Lecturas.on_attach_callback → «¡Hecho!» → siguiente en 3 s
```

- **Módulo:** `koroshi_preparacion` 13.0.1.x. Depende de koroshi_operarios, koroshi_faltantes y koroshi_caja_existente. Conserva `stock_barcode`, porque la salida a la app lo usa.
- **Pila de acciones:** Lecturas → Preparación → (Faltante | app clásica). Cualquier `history_back` vuelve a Preparación; su `on_attach_callback` recarga `/cargar` y, si la OUT está `done`, hace otro `history_back` a Lecturas. Se reutiliza intacta la vuelta que ya funciona en la v2.3.
- **Lo nuevo:** el modelo `koroshi.preparacion.lectura`, el grupo `koroshi_preparacion.grupo_pantalla_propia` y los parámetros `koroshi_preparacion.activa`, `koroshi_preparacion.validar_propia` y `koroshi_preparacion.leer_ubicacion`.
- **Ningún campo nuevo** en stock.picking, stock.move, stock.move.line, stock.picking.batch ni stock.picking.type.
- **Robustez del include:** va en try/catch en `willStart` y solo sobrescribe `_abrir`. Si el modo no se puede leer, se toma `'app'`. Lección del 03/11: un error de JS en `web.assets_backend` tumba todo el backend.

## 6. Versiones y alcance

| Versión | Módulo | Alcance | Escribe en stock |
|---|---|---|---|
| **v2.3.3** | koroshi_operarios | En `Tarea.empezar`, si la tarea abierta tiene sus pickings validados: `_cerrar('acabada', 'validada', _hora_validacion)` en vez de `dejada/otro`. Antes, contar en el servidor cuántas tareas están así (diagnóstico P). | No |
| **v3.0** base + simulación | koroshi_preparacion 1.0 | Grupo, parámetros (apagado), include de `_abrir`, pantalla completa con `/cargar` y `/leer` en **simulación** (clasifica y dice qué línea sumaría, sin escribir) y banda «SIMULACIÓN». Mide latencia, orden de líneas y choques de códigos con OUT reales sin tocarlas. La simulación es **un valor del parámetro (`activa='sombra'`)**, nunca una constante del código (lección del 27/10). | No |
| **v3.1** leer y encajar; validar en la app (**primer piloto**) | 1.1 | Suma de qty_done en el servidor con bloqueo e `id_lectura`, «Deshacer última», «Cantidad» (con tope en lo reservado), cerrar caja (`put_in_pack` con CJ), Faltante, Saltar, «Abrir en la app» y Salir. Al terminar, **«Validar en la app»**. | qty_done y cajas (lo mismo que hace la app) |
| **v3.2** validar en la pantalla propia | 1.2 | `/validar` con `koroshi.faltante.validar_out` + `_cerrar_operarios` + bultos según X1/X7. Solo con `validar_propia='1'`. Lectura de O-BTN.validate y O-BTN.pack. | Validación |
| **v3.3** comodidad y control | 1.3 | Lectura de ubicación (`no`/`aviso`/`obligatoria`), cierre de caja automático al leer una CJ nueva, «validar al completar», recuperar la sesión, embalajes si X6 lo pide, aviso de CJ de otra tienda e informe app frente a propia. | — |
| **v3.4** lotes Z- | 2.0 | Diseño propio: reparto de cada pieza a la caja de su OUT y validación OUT a OUT con `validar_out` (nunca `batch.done()`). No se empieza sin X8. | Sí |
| **v3.5** (opcional) | operarios v2.4 | Mixin `koroshi_operarios.Utilidades` para no depender de `Operarios.extend`. | No |

Fuera de la v3.x: crear líneas fuera de lo reservado o leer de más, la ronda de revisión (INT), la cola sin conexión y el modo «poner a 0».

## 7. Flujo de pantallas

Ver la maqueta `20261110_IDEAS_preparacion_en_lecturas_v1.html`.

**Disposición vertical fija** (PDA de unos 5"), con las clases `o_ko_*` de la v2.3:

```
[Cabecera: quién soy · OUT/xxxx · tienda · «uds 12/40» + barra]                 15 %
[TARJETA CENTRAL del paso]                                                      55 %
[Aviso de la última lectura (verde/rojo)]                                       10 %
[Botonera: Cantidad · Deshacer · Caja] (botones ≥ 64 px, separados ≥ 12 px)     12 %
[Pie: ☰ (Faltante, Saltar, Abrir en la app, Salir) · reloj · sonido]
```

Principios:

- El camino normal se hace solo con el lector.
- Una cosa grande cada vez; se puede usar con guantes.
- Verde/agudo = sumado; doble agudo = línea completa; triple + fondo verde = OUT completa; rojo/grave/vibración = error, y **la pantalla no avanza**.
- **Lo que no ha confirmado el servidor no cuenta.**

| Paso | Tarjeta | Entradas | Salidas |
|---|---|---|---|
| `cargando` | «Abriendo OUT/x para Nombre» (capa de la v2.3) | — | `ir_a`, o error y «Abrir en la app» |
| `ir_a` (azul) | «VE A» + ubicación ≥ 40 px · «Ref 12345 · Rojo · M» ≥ 28 px · «Coge 3» | lectura de ubicación (v3.3) o EAN directo | `leer` |
| `leer` (blanca) | Ref + talla/color + «2 de 3» con círculos | EAN → +1. EAN de otra línea pendiente → se suma a esa y avisa «Era la ref X». EAN que no está en la OUT → rojo «Este artículo no está en este pedido». Línea completa → rojo «Ya tienes las 3». | siguiente `ir_a`, o sigue en `leer` si es la misma ubicación |
| `caja` (amarilla) | «Cerrar caja CJ… con 8 uds» | leer CJ o pulsar «Caja» | `leer`/`ir_a`. Sin lecturas sin caja: «La caja está vacía» (sin llamar al servidor). Si sale un asistente: rojo «Ciérrala en la app». |
| `resumen` (verde) | «Todo leído · 40 uds · 4 cajas», chips de cajas | v3.1: **«Validar en la app»** (80 px). v3.2: «Validar» o «Cerrar caja y validar». | — |
| `resumen` incompleto | «Faltan 3 uds de 2 refs» | Solo **[Ir a Faltante]** y [Abrir en la app]. **No hay «Validar igual».** | — |
| `preguntar` (v3.2) | «¿Dejar pedido pendiente con lo que falta?» Sí / No (mismo texto que Faltantes, respetando `koroshi_faltantes.pedido_pendiente`) | toque | `validada` |
| `validada` | Fondo verde «OUT/xxxx validada» | — | `history_back` a 1,5 s → Lecturas «¡Hecho!» |

**Orden de clasificación de cada lectura** (siempre en el servidor; se confirma con el diagnóstico C2/I2):

1. matrícula CJ → caja;
2. O-BTN.* (v3.2);
3. EAN o referencia de un producto de la OUT;
4. embalaje (v3.3);
5. ubicación;
6. tarjeta de empleado → «Ya estás dentro» o «Termina esta OUT antes de cambiar»;
7. otra OUT → «Estás en OUT/x; usa Saltar»;
8. desconocido → error.

**Comportamiento transversal:**

- Sin conexión: la banda roja de la v2.3, no se lee y «Reintentar» reenvía con el mismo `id_lectura`.
- Inactividad: solo avisa, no expulsa a mitad de una OUT.
- Antirrebote: se descarta solo el **eco** del mismo código por bus y campo dentro de una ventana pequeña medida (X12), no 700 ms.
- Activación por PDA: el responsable la cambia con la pulsación larga en ☰ (localStorage).

## 8. Endpoints (`/koroshi/preparacion/*`)

Reglas comunes: `type='json'`, `auth='user'`; escriben con el usuario de la sesión, **sin sudo** (salvo en la tabla propia); responden `{ok, que, msg, ...}`; **todas las rutas que escriben comprueban `activa`** y se niegan con `'0'` o `'sombra'`.

| Ruta | Parámetros | Qué hace | Defensas |
|---|---|---|---|
| `/modo` | `{}` | `{modo: 'propia'\|'app'\|'sombra', validar_propia, motivo}` desde ir.config_parameter y has_group | — |
| `/cargar` | `{picking_id\|codigo, employee_id}` | OUT, líneas pendientes en el orden de `koroshi.faltante.lineas_pendientes`, cajas y progreso. Usa `comprobar_linea` para los motivos de rechazo. | Rechaza: company ≠ 8, tipo distinto de OUT, done/cancel, estado distinto de assigned, OUT de un lote Z-, lote/paquete de origen/propietario, y otra tarea o asignación viva en la OUT de otro operario. Siempre ofrece «Abrir en la app». |
| `/leer` | `{picking_id, codigo, id_lectura, employee_id, pda}` | Clasifica (§7). En un producto elige la move.line (mismo producto, qty_done < reservado, preferencia por la ubicación actual y luego el orden) y hace `SELECT id FROM stock_move_line WHERE id=%s FOR UPDATE NOWAIT` + `write({'qty_done': q+1})`. Búsquedas de producto y ubicación copiadas de faltantes (`_producto`, `_ubicacion`). | Idempotente por `id_lectura` (índice único). Tope en lo reservado (`de_mas`). `no_esta` sin crear líneas. Si la línea desaparece (reserva anulada por S4T o `reubicar`) → `recargar`. Si falla NOWAIT → «Otra PDA está leyendo esta OUT». Con `activa='sombra'` responde igual y guarda `simulada=True` sin escribir. |
| `/cantidad` | `{linea_id, cantidad, id_lectura}` | Fija la cantidad leída por esta PDA en la línea | 0 ≤ x ≤ reservado. Solo reduce lo leído por esta PDA (sin «poner a 0» genérico, que vigila `action_puestos_a_cero`). |
| `/deshacer` | `{picking_id, pda}` | Revierte la última lectura no deshecha de esta PDA en esta OUT | Solo si la línea aún no tiene caja |
| `/caja` | `{picking_id, codigo?}` | `picking.with_context(barcode_view=True).put_in_pack(package_name=codigo)` → caja_existente → Brain Station → community | Exige al menos una línea qty_done>0 sin `result_package_id` (X4). El código cumple el patrón CJ. Si devuelve un asistente (`res_model`), no se fuerza: error y «Ábrela en la app». El error de la acción automática 20 se muestra tal cual. |
| `/validar` (v3.2) | `{picking_id, pedido_pendiente}` | Exige todo lo leído en caja. `koroshi.faltante.validar_out` → `_respuesta_validar` → bultos según X1/X7 (`number_of_packages` = cajas propias distintas, campo existente) → `_cerrar_operarios`. | Todo o nada (savepoint de faltantes). Solo acepta stock.backorder.confirmation. Transferencia inmediata, cantidades de más y otros asistentes → error y «Abrir en la app». Nunca con todo qty_done=0. |
| `/koroshi/operarios/estado`, `/motivos`, `/saltar` | — | Los de la v2.3, sin cambios | — |

**Prohibido en el código:** `action_done` directo; `force_assign` / «Forzar disponibilidad»; escribir `stock.quant`; crear move.line; `stock.immediate.transfer` y `stock.overprocessed.transfer`; las rutas `/stock_barcode/*` salvo `scan_from_main_menu`.

**Tabla `koroshi.preparacion.lectura`:** `picking_id`, `move_line_id`, `employee_id`, `user_id`, `pda` (id de localStorage), `codigo`, `tipo` (leer/cantidad/deshacer/caja/validar), `cantidad`, `id_lectura` (único), `simulada`, `deshecha`, `resultado`, `fecha`. Sirve para la idempotencia, «Deshacer», la auditoría del piloto y el informe de comparación.

## 9. Impacto módulo a módulo

| Módulo | Qué pasa | Cambio |
|---|---|---|
| koroshi_operarios | Productividad (`uds_fin - uds_inicio`), cola, «¡Hecho!», contador y correo salen de `qty_done` y `state`; ahora se ven en tiempo real. | Solo la v2.3.3 (`empezar`). El include llega desde el módulo nuevo. |
| koroshi_faltantes | Se reutilizan `validar_out`, `lineas_pendientes`, `comprobar_linea`, `_respuesta_validar`, `_cerrar_operarios` y la pantalla. Mejora: lo ya leído **siempre** está guardado antes de `reubicar` o `sin_alternativa`. | Un include en el módulo nuevo: con `desde_preparacion`, «Volver a la OUT» hace `history_back`. |
| koroshi_caja_existente | `put_in_pack(package_name)` se llama igual que hoy y se cumple su requisito de qty_done guardado. `_koroshi_corregir_bultos` sigue, pero **solo cubre las cajas ajenas**. | Ninguno |
| koroshi_xpo_bultos | Cuenta los `result_package_id`; no depende de la interfaz. | Ninguno (comprobar X7 para la v3.2) |
| koroshi_monitor | leído = qty_done; la hora es la real; «En curso» saldrá antes; bultos = `number_of_packages`. | Ninguno. Avisar a quien lo mire durante el piloto. |
| koroshi_kpi / hoja de carga | Uds y horas por caja; la hoja usa `number_of_packages`. | Ninguno en la v3.1 (valida la app). Riesgo en la v3.2. |
| Reparto y etiquetas de zona | Las CJ reservadas se aceptan como nombre de caja. | Ninguno |
| Lotes Z- | Por `_super` (start_batch_processing) hasta la v3.4. `/cargar` rechaza las OUT de un Z-. | Ninguno |
| stock_barcode / Brain Station | No se tocan. Siguen siendo la salida de emergencia y, en la v3.1, la validación. | Ninguno |

## 10. Convivencia y vuelta atrás

Orden de decisión:

1. **`koroshi_preparacion.activa`** (data noupdate, `'0'` al instalar). El servidor lo comprueba en cada escritura.
   - `'0'`: nadie; las rutas no escriben.
   - `'sombra'`: pantalla en simulación para los del grupo.
   - `'piloto'`: los del grupo.
   - `'1'`: los del grupo y las PDA forzadas.
2. **Grupo «KOROSHI Preparación: pantalla propia»**, vacío al instalar (mismo patrón que `grupo_tarjeta_obligatoria`).
3. **localStorage `koroshi_preparacion_pda`** = `'app'` | `'propia'` | `''`. **`'app'` gana siempre.** `'propia'` solo vale si 1 y 2 lo permiten. Si D2 dice que las PDA comparten usuario, este es el control principal del piloto.
4. **`koroshi_preparacion.validar_propia`** (`'0'` por defecto). Con `'0'`, el final es «Validar en la app».

Vuelta atrás, de menos a más: (a) la PDA en `'app'`; (b) sacar al usuario del grupo; (c) `activa='0'`, efecto inmediato en el servidor; (d) dejar el módulo instalado sin usar; (e) desinstalar solo en un mantenimiento planificado, con el zip con fecha guardado en `bin/`.

Una OUT a medias se termina en la app sin perder nada (los datos son estándar), siempre que no haya otra PDA con la app abierta en esa OUT (X5).

## 11. Pruebas (sin validar OUT reales)

| Fase | Qué | Dónde |
|---|---|---|
| T0 | Revisión de código y lint de Python/JS/XML. Pruebas `TransactionCase` **solo con un entorno con addons Enterprise**. Si no lo hay, la elección de línea, la idempotencia y los topes van en funciones puras probadas sin Odoo. | Local |
| T1 | Diagnóstico de solo lectura (`odoo/KOROSHI_preparacion_lecturas_DIAGNOSTICO_2026-11-10.py`, por partes con `PARTE`), más la lectura del JS de Brain Station en el bundle y de custom_addons si hay acceso. Cierra X1-X11. | Servidor (lectura) |
| T2 | Instalar v2.3.3 y v3.0 con `activa='0'` fuera de horas, **con permiso expreso del usuario**. Comprobar que Lecturas funciona igual (OUT, Z-, Faltante, ☰) y que no hay errores de JS. | Producción, apagado |
| T3 | `activa='sombra'`, 20-30 OUT reales. El responsable lee en simulación una OUT ya cargada antes de que el operario la prepare. Se mide latencia, orden, EAN no encontrados y choques. Cero escrituras en stock. | Producción, simulación |
| T4 | Piloto v3.1: 1 operario, 1 PDA, franja tranquila, responsable delante y `activa='0'` a mano. Se lee y encaja en la pantalla propia y **se valida en la app clásica** (trabajo normal). Comprobar por OUT: qty_done = lo leído; cajas CJ correctas; `number_of_packages`; etiquetas y XPO; tarea `acabada/validada`; monitor, KPI y hoja de carga; sin movimientos «Cantidad de producto actualizada» nuevos; sin duplicados por `id_lectura`; NOWAIT con dos PDA; corte de wifi. | Producción |
| T5 | v3.2: primero en una copia o staging si existe (U3). En producción, la primera validación propia es trabajo real: OK expreso del usuario, OUT a OUT, revisando bultos y XPO. | — |

**Nunca:** un «simulacro» de `button_validate` con rollback en producción; un modo de prueba que se active editando una constante; validar OUT reales en pruebas.

## 12. Riesgos (por gravedad)

1. **Bultos o XPO al validar en la pantalla propia.** → La v3.1 valida en la app; la v3.2 solo con X1/X7 resueltos.
2. **Lo que Brain Station hace en JS y la pantalla se saltaría** (impresión, peso, comprobaciones). → Leer su JS antes de la v3.1 y de la v3.2.
3. **Transferencia inmediata o `put_in_pack` sin nada leído.** → `validar_out` los rechaza y `/caja` exige lecturas.
4. **App y pantalla propia en la misma OUT** (X5). → Una sola salida a la app, no se abre si hay otra tarea viva, NOWAIT.
5. **Error de JS en web.assets_backend** (precedente del 03/11). → Include mínimo en try/catch, instalación fuera de horas, zip para volver atrás.
6. **Acción automática on_write en stock.move.line en cada lectura** (X11): carga y duplicados de la acción 20.
7. **Latencia:** un RPC con bloqueo por EAN. Con 10.000 u/día, unas 2-3 lecturas/s en pico. Se mide en T3; si es mala, se agrupan lecturas cada 0,5 s con `id_lectura`.
8. **La reserva cambia a mitad** (S4T, `reubicar`, crones). → `recargar` y aviso; nunca se crean líneas.
9. **Lecturas dobles o perdidas** por el filtro de 700 ms. → Antirrebote medido e `id_lectura`.
10. **Choque de códigos** (EAN, CJ, ubicación, tarjeta, O-BTN). → Orden fijo en el servidor, validado en T3.
11. **Usuario compartido en la PDA.** → Control por localStorage.
12. **Embalajes o uom distinta** (X6). → Mientras no se traten: «Ábrela en la app».

## 13. Preguntas abiertas

**Servidor** (solo lectura: diagnóstico + lectura del código):

- S1. ¿Qué sobrescribe stock_barcode_optimization en Python (`put_in_pack`, `_put_in_pack`, `button_validate`, `action_done`, `_check_backorder`) y qué escribe su JS al validar (bultos, peso, impresión)? (J y bundle)
- S2. ¿`delivery_package_number` calcula los bultos? ¿delivery_xpo envía dentro de `action_done`, y con qué número? (J, K3, F2)
- S3. ¿La acción automática 20 y otras sobre stock.move.line, stock.picking o stock.quant.package son on_write? (K1)
- S4. ¿El tipo 45 es el de OUT de tiendas? ¿Tiene `show_reserved`, `no_overscan` u otros campos de terceros? (B)
- S5. ¿Las PDA usan un usuario por operario o uno compartido? ¿Qué acción de inicio tienen? (D1/D2)
- S6. ¿Qué nomenclatura de códigos se usa? ¿Hay EAN duplicados o que coincidan con CJ, ubicaciones o tarjetas? (C2, I2, I4)
- S7. ¿Hay embalajes con barcode y uom distinta de Unidades en las OUT? (I1, I3)
- S8. ¿Cuántas tareas `dejada/otro` tienen la OUT done? (P)
- S9. ¿Hay OUT con lote, paquete de origen o propietario? ¿Se valida alguna vez sin caja? (F1, F3)
- S10. ¿Qué hace barcode_batch_process (`start_batch_processing`, `action_validate`)? (H5, solo para la v3.4)

**Usuario:**

- U1. ¿Leer la ubicación es «no», «aviso» u «obligatoria»?
- U2. Cierre de caja: ¿se lee la CJ cada vez, hay una caja abierta implícita o se usa el botón?
- U3. ¿Hay una copia o staging para probar la validación? ¿Se puede crear una OUT de prueba sin efectos (S4T, XPO, impresión)?
- U4. ¿Se acepta que en la v3.x no se pueda leer de más ni añadir productos (todo va a Faltante o a la app)?
- U5. Pedido pendiente en la pantalla nueva: ¿`preguntar`, `si` o `no`?
- U6. ¿Quién hace el piloto (operario y PDA) y en qué franja?
- U7. ¿Los lotes Z- entran algún día (v3.4) o se quedan siempre en la app clásica?
- U8. ¿Están bien el nombre `koroshi_preparacion` y la serie «Lecturas v3.x»?
- U9. ¿Das permiso para instalar en producción (T2) cuando esté listo, con el interruptor a `'0'`?

## 14. Esfuerzo estimado (días de desarrollo, sin esperas)

| Bloque | Días |
|---|---|
| v2.3.3 (corrección de `empezar`) | 0,5 |
| T1: diagnóstico + lectura del JS/Python de Brain Station | 1,5-2 |
| v3.0: módulo, grupo, parámetros, include de `_abrir`, `/modo`, `/cargar`, `/leer` (con simulación), pantalla completa | 4-5 |
| v3.1: escritura con NOWAIT, `id_lectura`, cantidad, deshacer, `/caja`, include de Faltantes, «Abrir/Validar en la app», Saltar, tabla de lecturas | 3-4 |
| T0, T2, T3, T4 y ajustes | 2-3 (+3-5 de calendario de piloto) |
| Documentación (README, hoja del operario, informe y zips con fecha en `bin/versiones`, sin sobrescribir) | 1 |
| **Hasta el piloto v3.1** | **≈ 12-16 días** |
| v3.2: validación propia + bultos/XPO (según S1-S2) | 2-4 |
| v3.3: ubicación, cierre automático, validar al completar, sesión, embalajes, informe | 3-4 |
| v3.4: lotes Z- | 8-12 |
| v3.5: mixin en operarios v2.4 | 1-2 |
| **Total hasta la v3.3** | **≈ 17-24 días** |

## Ficheros locales en los que se basa (solo leídos)

- `odoo/modulos/koroshi_operarios/models/tarea.py` (178-206, 221-239)
- `odoo/modulos/koroshi_operarios/static/src/js/operarios_pantalla.js` (`_abrir` 354-389)
- `odoo/modulos/koroshi_caja_existente/models/stock_picking.py` (36-44, 157-186)
- `odoo/modulos/koroshi_faltantes/models/faltante.py` (219-233, 425-462)
- `odoo/modulos/koroshi_faltantes/controllers/main.py` (155-189, 329-338)
- `odoo/modulos/koroshi_xpo_bultos/models/delivery_carrier.py` (283-310)
- `odoo/modulos/koroshi_monitor/controllers/main.py` (113) y `koroshi_kpi/controllers/hoja_carga.py` (84-87)
