# Preparación en Lecturas v3.3: rendimiento (plan, 10/11/2026)

Ideas para la v3.3, todavía **sin hacer**. Sale de medir la v3.2.0 en Odoo real (nath.tuctuc.com), solo lectura.

## Estado al escribir esto

- En Odoo real: koroshi_preparacion **13.0.3.2.0** instalada y actualizada. koroshi_operarios 13.0.2.3.1.
- En git, sin instalar todavía: **v3.2.1** (solo CSS: en la hoja de Faltante, las uds van debajo de la ubicación).
  Entregables: `bin/20261110_koroshi_preparacion_v3.2.1.zip` y `bin/instalar_koroshi_preparacion_v3.2.1_2026-11-10.sh`.
- Activado solo para Isaac e Isaac2: `koroshi_preparacion.empleados` = `OP9990001,OP9980001`, `activa` = `1`.
- Tras actualizar, en cada PDA hay que cerrar Odoo y volver a abrirlo (si no, el navegador sigue con el JS viejo).

## Medidas (v3.2.0, Odoo real)

| Qué | Tiempo | Datos |
|---|---|---|
| `/koroshi/preparacion/modo` | 0,09 s | — |
| `/cargar` OUT de 2-7 líneas | 0,18 s | 1-3 KB |
| `/cargar` OUT de 73 líneas | 0,29 s | 24 KB |
| `/cargar` OUT de 141 líneas | 0,35 s | **46 KB** |
| `/koroshi/faltantes/buscar` (alternativas) | **0,7 s** | — |
| Foto `image_256` | 0,16 s | 15 KB |

Recordatorio: p90 de 84 líneas por OUT, el 96 % de las líneas es de 1 ud.

## Dónde puede ir lento

1. **Cada lectura devuelve el `estado` entero.** En una OUT de 141 líneas, cada EAN = 46 KB y el servidor recalcula
   todas las líneas (`tiene_foto` con `bin_size`, talla por atributos, orden por `complete_name`). Con lecturas
   rápidas la cola se acumula (1-2 s) y el pitido llega tarde. No se pierde ninguna, pero se nota.
2. **El cliente repinta la lista entera** (`_pintarLineas`) en cada lectura, aunque esté cerrada. Con más de 100
   líneas en una PDA lenta, se nota.
3. **La foto se descarga al cambiar de línea**: un momento en blanco.
4. **Validar** (Brain Station, XPO, S4T y bultos) tarda segundos. No es código nuestro; ya hay capa «Validando…».
5. **Odoo ocupado por crons** («server is busy»): todo más lento. El reintento con `id_lectura` ya lo cubre.
6. **Dos PDA en la misma OUT**: `FOR UPDATE NOWAIT` da error a una en lugar de esperar. Raro y querido.

La tabla `koroshi.preparacion.lectura` crece (~10.000 lecturas al día), pero `id_lectura`, `picking_id`,
`employee_id` y `fecha` ya tienen índice.

## v3.3: qué hacer, por orden

1. **Lectura ligera** (la mejora grande para OUT grandes).
   - `leer`, `deshacer` y `caja` devuelven solo las líneas cambiadas (id, leidas, completa, caja) y los totales
     (pedidas, leidas, sin_caja, cajas, siguiente_id, todo_leido). Menos de 1 KB.
   - Lo fijo (nombre, talla, foto, ubicación, EAN, ref) solo en `/cargar`.
   - El cliente parchea su `estado`. Si algo no cuadra (una línea desconocida, p. ej. tras `put_in_pack`, que
     parte líneas), hace `/cargar` entero.
   - `caja` puede devolver el estado entero: pasa pocas veces y parte líneas.
2. **Pintar la lista solo si está abierta**, y solo la `<li>` que cambia.
3. **Precargar la foto de la línea siguiente** (`new Image().src = …`) mientras se lee la actual.
4. **Faltante**: lanzar `/koroshi/faltantes/buscar` en cuanto se pulsa (ya sale «Buscando…»). Opcional: cachear
   las alternativas por producto durante la sesión de la pantalla.
5. Opcional: `tiene_foto` y talla con caché por producto en el servidor (`ormcache` o un dict por petición), si
   `/cargar` sigue lento en OUT de más de 150 líneas.

Nada de esto cambia lo que se escribe en Odoo (qty_done, put_in_pack, validación). Es solo cómo viajan y se
pintan los datos.

## Cómo probarlo

- Medir de nuevo `/cargar` y `leer` en EFFEC/OUT/24409 (141 líneas) y en una de 2-7 líneas. Objetivo: `leer`
  igual de rápido en OUT grandes que en pequeñas.
- Pruebas en OUT reales siempre reversibles: leer y Deshacer; ni cajas ni validar.
- Maqueta: `build_mock_prep.py` (scratchpad de la sesión), servida con la configuración «operarios-mock-v23»
  (puerto 8770). Si no está, generarla otra vez a partir del módulo.

## Otros pendientes

- Lotes Z- recorriendo OUT a OUT (plan v2, v3.4a).
- Arreglo del bloque H del diagnóstico (plan v2 §15).
- Acciones de servidor 1908 y 1912 (diagnóstico): se pueden borrar si el usuario quiere.
- Credencial de operario (sesión de Almacén2): arreglada en Odoo; falta probarla desde la PDA.
