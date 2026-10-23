# KOROSHI Monitor zonas (Odoo 13)

Pantalla en directo de cómo van las agrupaciones de picking por zonas (Z-ddmm-D1…D5, ZX).
Es la misma página que `bin/versiones/estado-OUT-agrupaciones-Z-*.html`, pero dentro de Odoo
y con datos al momento. **Solo lee: no cambia nada.**

- Menú: **Inventario › Monitor picking** (desde v1.3, al lado de KOROSHI KPI; antes en Operaciones).
- Se refresca sola cada minuto; botón **Refrescar** para hacerlo al momento.
- Desplegable con las últimas agrupaciones (Z-2210, Z-2110…). Por defecto, la última.
- Se acuerda de qué zonas has abierto o cerrado en «OUT por zona» al refrescar.
- **v1.1:** en el desplegable salen también **«Tiendas <día>»** (hoy y 2 días antes) para cuando se coge
  **una OUT por pedido** sin zonas: % hecho, **ritmo del equipo (u/h)**, **hora prevista de fin**,
  unidades leídas por hora y cada OUT con lo que ha tardado y su ritmo. Si hoy hay agrupaciones de zona
  Z-ddmm, por defecto se abre esa; si no, «Tiendas (hoy)».
- **v1.2:** en «Tiendas», **cajas cerradas** de cada OUT, **hace cuánto** se cerró la última (si una OUT
  cogiéndose pasa de 20 min sin cerrar caja sale en naranja y en un aviso arriba), **personas cogiendo ahora**
  (OUT en curso con caja cerrada en los últimos 20 min) y u por caja. Los minutos de cada OUT se estiman con
  las horas de sus cajas (Odoo solo guarda cuándo se cierra cada caja).
- **v1.3:** bloque **«Personas y horas»** en cualquier día (también días anteriores y zonas): personas (máximo a la vez
  y media), horas-persona, horas de reloj, uds por hora-persona, uds por persona y segundos por prenda. Se estima con
  las cajas cerradas cada cuarto de hora (cuántas OUT, o zonas, cierran caja a la vez), igual que KOROSHI KPI.
- **v1.4:** OUT **«Parcial (falta stock)»** en morado: ya se ha cogido todo lo que hay y solo faltan prendas sin stock
  (al validar van a pedido pendiente). **«Sin stock»**: OUT en espera sin nada que coger. El % y la hora de fin cuentan
  solo lo que hay en stock. Al final de la pantalla, **lista de faltantes** por OUT y artículo.

## Instalar

1. Copiar la carpeta `koroshi_monitor` (o descomprimir `bin/koroshi_monitor_2026-10-22_0825_v1.zip`)
   en una carpeta de módulos del servidor que esté en el `addons_path`
   (la de los módulos propios, junto a `/opt/nath-erp/odoo13`).
2. Reiniciar Odoo (hace falta para que lea el controlador Python).
3. En Odoo, modo desarrollador: **Aplicaciones › Actualizar lista de aplicaciones**.
4. Buscar **KOROSHI Monitor zonas** (quitar el filtro «Aplicaciones») e **Instalar**.
5. Abrir **Inventario › Operaciones › Monitor zonas**.

Para actualizar una versión nueva: copiar encima, reiniciar Odoo y en el módulo pulsar **Actualizar**.

## Qué calcula

Para cada OUT de las agrupaciones `<prefijo>*` de la empresa 8 (EFFECTIVE LOGISTICS):

| Dato | De dónde sale |
|---|---|
| Uds | Suma de `product_uom_qty` de los movimientos no cancelados |
| Leído | Suma de `qty_done` de las líneas |
| Estado | Hecha = OUT validada · Cogiéndose = algo leído · Sin empezar = nada leído |
| Huecos | Ubicaciones distintas de las líneas (`27009 - L59 P14 C1`) |
| Lineales | `L` mínimo–máximo de esas ubicaciones; en ZX, `MU-xx` |
| Empieza / última | Primera y última línea leída (`write_date`), o la hora de validación si está hecha |
| Caja | Número de caja de tienda de la nota de la OUT («CAJA nn») |

Ficheros: `controllers/main.py` (datos, ruta `/koroshi_monitor/datos`), `static/src/js/monitor.js`
(pantalla), `static/src/css/monitor.css`, `views/menu.xml`, `views/assets.xml`.
- **v1.5:** los **pedidos pendientes en espera** (lo que faltaba al validar, sin stock) ya no salen: solo una nota con
  cuántos hay. En la lista, columna **«Sin stock»** (uds que no se pueden coger) en vez del número negativo al lado de
  «Leído». Fuera la tarjeta de «faltan» de arriba (el detalle sigue abajo del todo).
- **v1.6:** fuera la lista de **faltantes** de abajo y la columna «Sin stock»: las faltas, guardadas por día, están en
  **KOROSHI KPI › Faltas por día** (koroshi_kpi v1.3).
- **v1.7 (tiendas):** franja grande arriba (% hecho, hora de fin, uds por coger); filas con color según el estado;
  «Sin empezar» como fichas de tienda (K10 138 u…) con la lista plegada y «Hechas» plegadas. Botón **Modo pantalla**
  para la pantalla vertical del almacén: sin el menú de Odoo, letra grande y solo lo que se está cogiendo; se queda
  guardado en ese navegador (botón «Salir de pantalla» para volver). La K75 sale bien (su nombre lleva coma).
