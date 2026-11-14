# KOROSHI · Mapa de almacén NAU-2

Módulo inicial para Odoo 13. Añade un mapa editable y una vista operativa de
OUTs/personas/PDA bajo `Inventario > KOROSHI · Almacén`.


## v20261114.45 (14/11/2026, auditoría 13/11, fase 4)

- **Publicar versión ya guarda en Odoo.** Antes fallaba siempre: el código del plano se hacía con
  `fields.Datetime.now().replace('-', '')`, pero en Odoo 13 eso es una fecha, no un texto, y daba error. El 14/11
  había **0 planos** en `koroshi.layout`. Si algo falla, el mensaje dice el error de verdad (o «sesión caducada»).
- **Cargar de Odoo** (botón al lado de Publicar, ruta `GET /koroshi_warehouse_map/layout/load`): lista las 20 últimas
  versiones publicadas y abre la elegida en el editor. «Deshacer» vuelve a lo de antes.
- Los avisos del editor (publicado, error, cargado) se ven abajo en la pantalla; antes solo iban a la consola.
- El `?v=` del plano sale de la **versión del manifest** (la acción abre `/koroshi_warehouse_map/planner`, que
  redirige al HTML con la versión): al actualizar el módulo, el navegador coge el plano nuevo.
- `/koroshi_warehouse_map/data` respeta **`since`**: el mapa manda la hora del servidor de la última carga y recibe
  solo lo que ha cambiado (la OUT o sus líneas). Sin `since` o si es de hace más de 10 min, todo.
- El inicio del día se pasa de hora local a UTC antes de compararlo con `write_date` (antes había 1-2 h de desfase).
- Incluye la versión 20261106.44 del repo, que no llegó a instalarse (en el servidor está la 20261102.39).

## Instalación

1. Copiar la carpeta `koroshi_warehouse_map` dentro de la ruta de addons de
   Odoo 13.
2. Reiniciar Odoo.
3. Activar el modo desarrollador y pulsar **Actualizar lista de aplicaciones**.
4. Buscar **KOROSHI Mapa de almacén NAU-2** e instalarlo.
5. Abrir `Inventario > KOROSHI · Almacén > Mapa NAU-2`.

## Datos operativos

El endpoint `/koroshi_warehouse_map/data` es de solo lectura. Primero intenta
leer las sesiones propias de `koroshi.pick.session`; mientras no haya una
integración de PDA, muestra una aproximación basada en las OUT de Odoo de la
compañía 8.

La integración real de PDA debe crear o actualizar únicamente:

- `koroshi.pick.session`: una sesión por persona/PDA y OUT;
- `koroshi.pick.event`: inicio, pick, pausa, escaneo y finalización.

El módulo no modifica albaranes, movimientos, productos ni reservas.

La interfaz incluida en esta actualización es la v41 e incorpora el centro de
control de NAU-2: reconciliación, incidencias, historial, alertas, mapa de
calor, escenarios, capacidad, permisos y modo PDA. El mapa queda separado en
esqueleto fijo, diseño editable y capa operativa. Cuando se abre dentro de
Odoo consulta `/koroshi_warehouse_map/data` con refresco incremental; si no hay
sesiones PDA, muestra las OUT disponibles y diferencia datos reales de Odoo,
estimaciones y simulaciones.

La v41 añade tres modos separados (Editar mapa, Operación y Análisis), un
panel contextual a la derecha, pestañas limpias para resumen/recorrido/
incidencias/calor y un editor tipo CAD con paleta y propiedades. Mantiene
intacta la geometría del plano y reorganiza únicamente la interfaz.

La v40 añade al editor ajuste magnético activable, selección múltiple,
duplicado, alineación, deshacer/rehacer, ayuda contextual y publicación de
versiones en Odoo. El perímetro, pilares y elementos estructurales quedan
bloqueados. En el mapa operativo incorpora filtros rápidos por estado,
incidencias y transportista, auditoría de recorridos (saltos diagonales,
ubicaciones sin coordenadas y tramos locales), eventos de apertura/cierre de
caja y una leyenda clara de real/estimado/simulado.

La v37 mejora el mapa editable: los lineales se pueden seleccionar, mover con
arrastre o flechas, intercambiar con otro lineal y restablecer a su posición
original. El movimiento de lineales usa pasos de 0,5 m para conservar las filas
que empiezan en coordenadas medias. Las zonas y recuadros interiores conservan
sus asas de tamaño y el perímetro de la nave y sus pilares permanecen fuera de
la edición.

La v34 corrigió la compatibilidad con Odoo 13: usa `move_lines` cuando no
existe `move_ids`, calcula las unidades desde `stock.move.line` y evita que el
endpoint de datos devuelva HTTP 500.

La v35 añade al endpoint todas las `stock.move.line` de cada OUT (ubicación,
referencia, EAN, cantidad prevista y cantidad hecha). Así el mapa muestra los
lineales reales visitados y no solo la última ubicación conocida. Si existe una
sesión de PDA sin líneas de stock, utiliza sus eventos de escaneo como detalle.

## Plano editable

El plano de referencia se entrega como asset estático en
`static/src/html/warehouse_planner_20261029_v1.html`. Las versiones se pueden
guardar localmente y publicar en Odoo mediante `/koroshi_warehouse_map/layout/save`;
el esqueleto base nunca se sobrescribe durante una edición.
Las tarjetas de **Celdas (colmenas)** del editor también son funcionales: se
pueden arrastrar al plano, mover, redimensionar con las asas y eliminar. Cada
variante conserva su rejilla de huecos (4×9, 2×9, 1×9 o 2×7) y sus ubicaciones
se reflejan en el resumen del plano.

## Zonas del día y Monitor Picking

Las zonas dinámicas no aparecen por defecto al abrir el mapa. El endpoint
`/koroshi_warehouse_map/data` devuelve además `zones`, leyendo los pickings
internos de la compañía 8 cuyo origen sigue el formato real `KOR-ddmm-*` y
que se han creado durante el día actual. Si no hay ninguno, el mapa conserva
solo las zonas estructurales del plano; si existen, pinta sus tramos de
lineales y los deja como capa informativa no editable.

Esto permite que Monitor Picking abra este mismo mapa después de crear zonas,
sin duplicar el plano ni inventar recorridos. La integración recomendada es
un botón/enlace del monitor hacia la acción del módulo (opcionalmente con
`date` o `batch_id` como filtro); ese botón pertenece al módulo de Monitor
Picking y se puede añadir en una iteración separada.
