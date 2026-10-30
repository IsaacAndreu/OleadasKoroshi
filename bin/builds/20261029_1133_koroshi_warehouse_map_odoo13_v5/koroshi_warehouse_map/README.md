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

## Interfaz de trabajo

La barra superior separa claramente los dos usos:

- **Mapa editable**: conserva el plano y vuelve a mostrar el botón
  **Herramientas** para activar la barra técnica, deshacer, reglas, lineales,
  leyenda, cotas, guardado y exportación.
- **Mapa operativo**: muestra un panel lateral sencillo con selector de OUT,
  filtros de pendientes/terminadas, estadísticas de unidades, paradas,
  distancia y tiempo estimado, además de ver recorrido y simulación.

El plano de referencia no se redibuja ni se modifica al cambiar entre modos.

## Plano editable

El plano de referencia se entrega como asset estático en
`static/src/html/warehouse_planner_20261029_v1.html`. La edición visual sigue
siendo local en esta primera versión; los modelos `koroshi.layout` y
`koroshi.layout.element` dejan preparada la persistencia controlada para la
siguiente iteración.
