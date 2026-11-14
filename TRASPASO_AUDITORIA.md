# Traspaso: corrección de la auditoría del 13/11/2026

Documento para seguir el trabajo en otra sesión. Las reglas del proyecto están en [CLAUDE.md](CLAUDE.md) y el mapa de
módulos en [README.md](README.md): leerlos antes de empezar.

## Cómo se trabaja

- Por fases. Una versión de módulo cada vez. No se instala, ni se sube, ni se reinicia nada en el servidor: se dejan
  el ZIP y el script en `bin/` y se avisa.
- Antes de cambiar nada, leer el código y confirmar que el fallo existe tal como se describe. Si no, decirlo.
- Antes de sacar una versión, mirar la `installed_version` real. Se puede leer, sin tocar nada, en nath.tuctuc.com
  (sesión ya abierta en el navegador) con `ir.module.module.search_read`.
- Cada fase acaba con: qué se ha cambiado (archivo:línea), cómo se ha probado, qué no se ha podido probar y qué hay
  que probar en una PDA real. Luego, parar y esperar el visto bueno.
- ZIP con Python (`zipfile`, carpeta del módulo en la raíz, sin `__pycache__`), nunca sobrescribir uno que exista.
  Script de instalación: copiar el último `bin/instalar_<modulo>_*.sh` y cambiar versión y textos.
- Sin node en este PC: la sintaxis JS se comprueba con
  `cscript //nologo //E:{16d51579-a30b-4c8b-a276-0ff4dc41e755}` (quitando antes las comas finales y guardando en
  UTF-16).
- Git no tiene usuario configurado: los commits van con `GIT_AUTHOR_NAME/EMAIL` y `GIT_COMMITTER_NAME/EMAIL` en el
  entorno (los mismos que los commits anteriores). Los commits están solo en local: no se ha hecho push.

## Estado (13/11/2026)

| Fase | Estado |
|---|---|
| 0. Terreno | HECHA. Fusión de feat/koroshi-zonas (`ccfe2c10`), CLAUDE.md y README (`010e04e6`). Lista de contraseñas versionadas pasada al responsable (pendiente de rotar por él). |
| 1. Robustez PDA | HECHA, SIN INSTALAR. koroshi_preparacion 3.29.0 (`7828ec25`) y koroshi_contenedores 1.4.0 (`663f268b`). ZIP y scripts en `bin/`. Pendiente: instalar, pasar `tests/test_idempotencia.py` en una base de pruebas y probar en PDA real. |
| 2. Una sola cifra de productividad | SIGUIENTE. Sin empezar. |
| 3 a 7 | Sin empezar. |

Versiones en el servidor el 13/11 (leídas en nath.tuctuc.com): preparacion 3.28.1, contenedores 1.2.0,
operarios 2.11.1, informe 1.0.1, kpi 1.5.0, monitor 1.24.0, menu 2.1.0, zonas 1.2.0, warehouse_map
0.1.20261102.39 (el repo va por delante: 20261106.44), s4t_envios 1.1.0. En el servidor hay `koroshi_sale_order` 0.3
y `koroshi_zebra` 1.0.0 que NO están en el repo. `koroshi_actividades` está en el repo pero no en el servidor.

## Fases que quedan (encargo original)

**FASE 2 — Una sola cifra de productividad (koroshi_operarios, koroshi_informe, koroshi_kpi).** Toca tres módulos:
decirlo antes de empezar.
1. Hay cinco fórmulas de u/h (tarea.py:103, operarios/models/informe.py:93, koroshi_informe/models/informe.py:242,
   kpi.py:269, operarios/controllers/main.py:249). Una sola función resumen_operario_dia() que usen todos; quitar los
   group_operator='avg' de los ratios.
2. Dos correos diarios a las 17:00 (crons 204 y 213 activos): dejar solo el de koroshi_informe. El responsable
   desactiva el cron en el servidor; aquí se quita del XML.
3. Horas-persona del KPI (kpi.py ~105 y ~330): usar el tiempo efectivo de las tareas de operario cuando la cobertura
   sea alta; si no, la estimación por cajas, indicando la fuente.
4. Falta «no cogido»: no debe desaparecer al validar la OUT; cruzarla con koroshi.faltante (motivo no_encontrado) y
   recalcular los días con OUT abiertas.
5. recalcular_todo no debe correr en cada actualización del módulo KPI: limitarlo a los últimos N días.
6. Consumibles (consumable.py:92): el total no puede sumar todo el histórico en cada caja; hacerlo incremental o con
   read_group, y no tragar el error de concurrencia (~210).
7. Reparto (reparto.py:417): filtrar zonas Z- y tramo en el dominio antes del limit=400; no llamar _lineal dos veces
   por OUT.
8. Actividades (registro.py ~208): un tramo olvidado no puede cerrarse a las 23:59; un solo tramo abierto por persona.
   HECHO en koroshi_actividades 1.1.0 (14/11, sin instalar): 0 min + nota para revisar, e índice único.
9. Hoja de carga (hoja_carga.py:30): usar el campo de koroshi_delegacion en vez del diccionario fijo.

**FASE 3 — Integraciones y permisos**
1. koroshi_s4t_envios (sigue en modo diagnóstico; arreglar antes de activar): el cron coge 500 pedidos por fecha y los
   atascados ocupan sitio (envio.py:236); una OUT pendiente bloquea el pedido entero (~108); separar errores
   reintentables (409, 5xx, red) de definitivos y avisar de estos; proteger el caso de respuesta 200 con lista
   (~206). Valorar un job de queue_job por pedido en el canal root.s4t_sync.
2. koroshi_s4t_traspasos (sin instalar): savepoint por traspaso guardando el JSON crudo, reconciliación diaria de hoy
   y ayer, y reintento de los que están en error.
3. Permisos: comprobar grupo en las rutas de koroshi_monitor, koroshi_operarios, koroshi_actividades y hoja_carga
   (hoy auth='user' + sudo() sin has_group; oriola_monitor/controllers/main.py:295 es el modelo), y en
   koroshi.ajustes.action_guardar. Validar en servidor el employee_id que manda la PDA.
4. Monitor: caché compartida con candado como la de oriola_monitor (~306), y no refrescar con la pestaña oculta. El
   filtro Z-ddmm-% no lleva año (main.py ~462).
5. Bultos: un solo helper para contar bultos y para los 15 kg / 0,09 m3 (hoy XPO y S4T cuentan distinto).

**FASE 4 — Mapa de almacén (koroshi_warehouse_map)**
- controllers/main.py:474: fields.Datetime.now() es un datetime y .replace() falla; el plano nunca se guarda (0
  registros en koroshi.layout). Arreglarlo con strftime, añadir una ruta de carga y enseñar el error real.
- El rompecaché ?v= debe salir de la versión del manifest. Respetar el parámetro since. day_start está en hora local
  comparado con write_date en UTC.

**FASE 5 — Zonas y oleadas**
- Comprobar en el motor de koroshi_zonas (motor/v12f.py, particion.py) si hereda estos fallos de la v10: orden solo
  por número de tienda en vez de por urgencia, OUT de días anteriores que dejan de ser candidatas, y capacidad sin
  revisar después de juntar trozos. Dar el resultado antes de cambiar nada.
- Preparar la lista de acciones de servidor y crons viejos que se podrían borrar al pasar koroshi_zonas de sombra a
  real. No borrar nada.

**FASE 6 — Repositorio**
- Proponer (sin ejecutar) cómo sacar de git los binarios de bin/versiones, los ZIP y los APK manteniendo la regla de
  no sobrescribir: etiqueta de git por versión y ZIP generado desde la etiqueta.
- Un único script desplegar.sh <módulo> <versión> en lugar de uno por versión.
- Módulo koroshi_base con lo repetido: COMPANY_ID, zona horaria, límites del día en Madrid, expresión de la CJ.

**FASE 7 — Ideas nuevas (solo diseño; no programar hasta que el responsable elija)**
Aviso de caja llena por volumen (0,084 m3 por caja), bandeja del encargado, panel de integraciones, ficha KPI
autoalimentada, calidad por operario por cada 1.000 uds, ronda automática de faltantes, previsión de cajas y
posiciones reales en el mapa. Para cada una: qué módulo toca, qué datos necesita y cuánto trabajo es.
