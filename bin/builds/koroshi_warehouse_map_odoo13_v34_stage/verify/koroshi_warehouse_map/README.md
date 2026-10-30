# KOROSHI · Mapa de almacén NAU-2

Módulo inicial para Odoo 13. Añade un mapa editable y una vista operativa de
OUTs/personas/PDA bajo `Inventario > KOROSHI · Almacén`.

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

La interfaz incluida en esta actualización es la v34 e incorpora el centro de
control de NAU-2: reconciliación, incidencias, historial, alertas, mapa de
calor, escenarios, capacidad, permisos y modo PDA. Cuando se abre dentro de
Odoo consulta `/koroshi_warehouse_map/data` con refresco incremental; si no hay
sesiones PDA, muestra las OUT disponibles y marca los datos estimados.

La v34 corrige la compatibilidad con Odoo 13: usa `move_lines` cuando no
existe `move_ids`, calcula las unidades desde `stock.move.line` y evita que el
endpoint de datos devuelva HTTP 500.

## Plano editable

El plano de referencia se entrega como asset estático en
`static/src/html/warehouse_planner_20261029_v1.html`. La edición visual sigue
siendo local en esta primera versión; los modelos `koroshi.layout` y
`koroshi.layout.element` dejan preparada la persistencia controlada para la
siguiente iteración.
