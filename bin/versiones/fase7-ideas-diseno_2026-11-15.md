# Fase 7 de la auditoría 13/11: ideas nuevas (solo diseño)

15/11/2026. **Solo diseño: no se ha programado nada.** Para cada idea: qué es, qué módulo toca, qué datos necesita
(con lo que hay hoy en el servidor, leído en modo lectura) y cuánto trabajo es. Se programa cuando el responsable
elija.

Trabajo: **P** = pequeño (1 sesión), **M** = mediano (2-3 sesiones), **G** = grande (4 o más). Riesgo PDA = si toca
algo que los operarios usan todo el día.

## Resumen

| # | Idea | Módulo | Datos hoy | Trabajo | Riesgo PDA | Propuesta |
|---|---|---|---|---|---|---|
| 1 | Previsión de cajas | kpi (+ menu «Hoy») | **Sí**: calibrado con 20 días | P | No | **Primero** |
| 2 | Bandeja del encargado | menu | Sí | M | No | **Segundo** |
| 3 | Panel de integraciones | menu o monitor | Sí | P-M | No | Con la 2 (misma pantalla) |
| 4 | Aviso de caja llena por volumen | preparacion | Sí (88 % de las uds con volumen) | M | **Alto** | Tercero, con piloto |
| 5 | Ronda automática de faltantes | faltantes | Pocos (9 faltantes en total) | P | Bajo | Cuando haya volumen |
| 6 | Ficha KPI autoalimentada | kpi | **Falta**: actividades sin instalar | P (cuando haya datos) | No | Después de instalar actividades |
| 7 | Calidad por operario cada 1.000 uds | informe + kpi | **Falta**: <5 % de las uds tienen operario | M | No | Esperar |
| 8 | Posiciones reales en el mapa | warehouse_map | **Falta**: 0 planos guardados | G | No | Esperar al plano |

## 1. Previsión de cajas

- **Qué**: antes de empezar el día, cuántas cajas van a salir (para preparar cartón, personas y transportista). Por
  día, por zona y por tienda. Después, comparada con las reales.
- **Datos (comprobado)**: `koroshi.kpi.dia` ya guarda cada día el volumen (`volumen_total`) y las cajas reales. Del
  20/10 al 13/11, en los días normales, **cajas reales ÷ (volumen ÷ 0,084 m³) = 0,97-1,17, mediana ≈ 1,07**.
  Ejemplos: 09/11 → 1,00; 10/11 → 1,05; 11/11 → 1,04; 13/11 → 1,08. Solo falla con días muy pequeños (12/11,
  883 uds → 1,67), porque pesa más la última caja de cada OUT.
- **Hallazgo**: la previsión que ya hace koroshi_zonas (cajas de 80 L, «CAJAS n» de la nota) **se pasa**: 13/11, 266
  previstas y 199 reales (+34 %); 11/11, 528 y 452 (+17 %); 10/11, 530 y 494 (+7 %). Con el volumen ÷ 0,084 × 1,07
  se habría acertado más. Encaja con la nota de la configuración de zonas: la caja grande real es de ~93 L, no de
  80 L. Revisar `litros_caja` de zonas con estos datos es una decisión aparte.
- **Cómo**:
  - Previsión = Σ por OUT de max(1, volumen ÷ 0,084) × factor. El factor se calibra solo con los últimos 20 días de
    `kpi.dia`.
  - Las uds sin volumen en Odoo (11,5 % esta semana: 3.205 de 27.798) usan los litros por tipo de
    `koroshi.kpi.peso.tipo`, como ya hace el KPI.
  - Se enseña en el menú «Hoy» y en el correo diario; la ficha KPI guarda previsto frente a real.
- **Módulo**: koroshi_kpi (cálculo y campo `cajas_previstas` en `koroshi.kpi.dia`, tabla propia) y koroshi_menu (la
  cifra en «Hoy»). Ningún campo en tablas de stock.
- **Trabajo**: P.

## 2. Bandeja del encargado

- **Qué**: una sola pantalla con **todo lo que necesita una persona**, en vez de buscarlo en cinco sitios. Cada
  línea con qué es, desde cuándo y un botón para ir a ello.
- **Datos (ya existen)**:

  | Qué | Dónde | Hoy |
  |---|---|---|
  | Faltantes pendientes | `koroshi.faltante` estado pendiente | 7 |
  | Lecturas rechazadas de cola | `koroshi.preparacion.lectura` (campo `diferida`, preparacion 3.29+) | el campo aún no está en la base de datos: falta instalar |
  | Tramos de actividad cerrados a 0 min «para revisar» | koroshi_actividades 1.1.0 | sin instalar |
  | Pedidos rechazados por S4T | koroshi_s4t_envios 1.2.0 | sin instalar |
  | Traspasos S4T con error | koroshi_s4t_traspasos | sin instalar |
  | Pedidos sin OUT (posible OUT borrada) | `sale.order` S-6665 sin OUT | 3 esta semana |
  | Reparto de zonas con aviso («NO SE HA PARTIDO», hora de fin, OUT de días anteriores) | `koroshi.zonas.ejecucion` | — |
  | Jobs fallidos | `queue.job` failed | 1 desde el 01/11 |
- **Cómo**:
  - Pantalla nueva en la app KOROSHI.
  - Lee cada fuente solo si su módulo está instalado (`'modelo' in env`), así no crea dependencias nuevas.
  - Sin tablas: se calcula al abrir.
  - Opcional: un número en el menú con cuántas hay.
- **Módulo**: koroshi_menu (ya depende de casi todos).
- **Trabajo**: M.

## 3. Panel de integraciones

- **Qué**: el estado de lo que habla con fuera, en una pantalla:
  - S4T: último envío bien, pendientes y rechazados; resumen de la última pasada del cron 186; traspasos.
  - XPO: OUT sin etiqueta.
  - queue_job: canal `root.s4t_sync`.
  - Crons KOROSHI: activo, última ejecución y si va con retraso.
- **Datos**: todo existe.
  - El cron 186 deja su resumen en `ir.logging` («SYNC S4T: 43 candidatos…»), leído el 15/11.
  - `ir.cron` tiene `lastcall` y `nextcall`.
  - `queue.job` tiene el estado.
- **Cómo**: una pestaña más de la bandeja (idea 2). Semáforo verde, ámbar o rojo, por ejemplo: rojo si el cron 186
  lleva más de 1 hora sin pasar o si hay jobs fallidos.
- **Módulo**: koroshi_menu (con la 2) o koroshi_monitor (que ya tiene la consulta de envíos).
- **Trabajo**: P si va con la 2, M si va sola.

## 4. Aviso de caja llena por volumen

- **Qué**: en la PDA, mientras se llena una caja, aviso cuando el volumen de lo leído llega a lo que cabe en una caja
  (~0,084 m³; la caja física 60×40×33 es 0,079 m³). Por ejemplo, la barra de la caja se pone ámbar al 85 % y roja
  al 100 %: «Caja llena: ciérrala con la CJ».
- **Datos (comprobado)**:
  - Esta semana, el **88 % de las uds** de las OUT tienen volumen en Odoo (24.593 de 27.798).
  - Por artículo, el 34 % de los SKU no tienen volumen (1.274 de 3.784): para esas uds se usan los litros por tipo
    de `koroshi.kpi.peso.tipo`.
  - Mediana medida de las cajas llenas: 10 uds y 0,084 m³.
- **Cómo**:
  - El servidor ya sabe qué hay leído en la caja abierta. El estado de la pantalla lleva el volumen de esa caja
    (calculado, sin campo nuevo) y el JS pinta el aviso.
  - Umbrales como parámetros.
  - **No bloquea**: solo avisa.
- **Módulo**: koroshi_preparacion (pantalla de la PDA). preparacion no depende de koroshi_kpi: los litros por tipo
  van a koroshi_base (`comun.litros_ud`) o se leen del parámetro.
- **Trabajo**: M.
- **Riesgo**: **alto**, porque es la pantalla de la PDA de todo el día. Piloto con una persona, fuera de horas punta.

## 5. Ronda automática de faltantes

- **Qué**: hoy la ronda de revisión de faltantes se crea a mano («Crear ronda de revisión», koroshi_faltantes 1.1).
  Automática: a una hora fija (p. ej. 12:00 y 17:00), si hay faltantes pendientes, se crea la INT de la ronda y se
  pone en la cola del encargado (o de quien se elija).
- **Datos**: **9 faltantes en total desde el 09/11** (7 pendientes, 2 encontrados). **Nunca se ha creado una ronda.**
  Las faltas «no cogido» del KPI son muchas más (190 desde el 01/11), pero no pasan por el botón de faltante.
- **Cómo**:
  - Cron que llama a `crear_ronda()`, que ya existe, solo si hay N pendientes o alguno de más de X horas.
  - Parámetros: horas, mínimo y a quién se asigna.
  - La asignación a cola usa `koroshi.operario.asignacion`, que ya existe; faltantes ya depende de operarios.
- **Módulo**: koroshi_faltantes.
- **Trabajo**: P.
- **Valor hoy**: bajo, por los pocos faltantes. Sube si se usa el botón de faltante en vez de dejar la línea sin
  coger.

## 6. Ficha KPI autoalimentada

- **Qué**: que la ficha diaria del KPI se rellene sola: personas y horas de picking, packing y expedición.
- **Datos (comprobado)**:
  - **Los 6 campos a mano están a 0 en todas las fichas del 09/11 al 14/11**: nadie los rellena.
  - El picking ya sale de las tareas de operario cuando la cobertura llega al 80 % (fase 2, sin instalar).
  - Esta semana solo hay 51 tareas, así que la cobertura no llegaría.
  - Packing y expedición saldrían de `koroshi.actividad.registro` (actividades «Tiendas», «Web», «Manipulación
    marketplace»…), pero **koroshi_actividades no está instalado**.
- **Cómo**:
  - Mapa actividad → columna del KPI (p. ej. Tiendas/Web → packing). Hoy no hay ninguna actividad de expedición en
    `koroshi_actividades/data/actividades.xml`: habría que añadirla.
  - Horas = Σ minutos del día y personas = personas distintas.
  - Campo «fuente» como el de picking: a mano, actividades o estimado.
  - Lo que se escriba a mano manda.
- **Módulo**: koroshi_kpi (dependencia blanda de actividades, como hoja_carga con delegacion).
- **Trabajo**: P, pero **antes hay que instalar koroshi_actividades y usarlo** en el portátil.

## 7. Calidad por operario cada 1.000 uds

- **Qué**: errores por cada 1.000 uds cogidas, por operario y semana. Errores = faltas «no cogido» (había stock) +
  faltantes no encontrados + cajas devueltas por error, si algún día llega ese dato de S4T.
- **Datos (comprobado)**: **falta saber quién ha cogido cada ud**.
  - Esta semana, `koroshi.preparacion.lectura` tiene **687 lecturas con operario** (506 de una sola persona) frente a
    ~27.800 uds servidas. Las tareas de operario son 51.
  - El resto se coge con la app estándar, que solo sabe el usuario de la PDA (6 usuarios), no la persona.
  - `koroshi.kpi.falta` no tiene operario.
- **Cómo**, cuando haya datos: operario de la línea = el de la lectura o la tarea; las faltas se cruzan por línea;
  informe semanal en koroshi_informe.
- **Requisito**: que la preparación con tarjeta (preparacion/operarios) sea la forma normal de coger. Con menos del
  ~80 % de las uds con operario, el número engaña.
- **Módulo**: koroshi_informe y koroshi_kpi.
- **Trabajo**: M. **Esperar.**

## 8. Posiciones reales en el mapa

- **Qué**: en el mapa de NAU-2, ver dónde está cada cosa de verdad: ubicaciones con stock, lo que falta por coger de
  hoy por zona y, si se quiere, dónde está cada operario (la ubicación de su última lectura).
- **Datos (comprobado)**:
  - **0 planos guardados** (`koroshi.layout`): guardar fallaba hasta la versión .45 de la fase 4, sin instalar.
  - 0 sesiones y eventos de picking.
  - Las 110.436 ubicaciones internas de la empresa 8 (50.642 con stock) tienen `posx/posy = 0`.
  - El mapa tendría que unir cada estantería del plano con su lineal (`L12`…) y sus huecos, por el nombre.
- **Cómo**:
  1. Instalar la .45.
  2. Dibujar y guardar el plano.
  3. Cada elemento del plano lleva su rango de lineales.
  4. El servidor agrupa por lineal (como hace ya zonas con `lineal_de`) y el mapa pinta.
  - Sin escribir en `stock.location`.
- **Módulo**: koroshi_warehouse_map.
- **Trabajo**: G.
- **Requisito**: el plano guardado.

## Orden propuesto

1. **Previsión de cajas** (1): datos listos, poco trabajo, sin riesgo, y ayuda a decidir el `litros_caja` de zonas.
2. **Bandeja del encargado + panel de integraciones** (2 y 3), en una versión de koroshi_menu.
3. **Aviso de caja llena** (4), con piloto en una PDA.
4. Las demás cuando estén sus requisitos: actividades instalado (6), preparación con tarjeta generalizada (7), plano
   guardado (8) y faltantes con volumen (5).

Cada una, un módulo y una versión, con `empaquetar.py` y `desplegar.sh`.
