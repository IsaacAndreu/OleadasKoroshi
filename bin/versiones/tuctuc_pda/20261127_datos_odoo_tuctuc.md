# Datos de odoo.tuctuc.com (leídos por RPC, 27/11/2026)

- Odoo 13.0+e, base de datos TUCTUC_PRODUCTION. Hay 445 módulos instalados y ningún koroshi_*.
- Instalados: stock_barcode, stock_barcode_optimization, barcodes, hr, hr_attendance, stock_picking_batch, delivery, sale_stock, queue_job, sales_ext (s_order_type_id), style_management (season_id), delivery_package_number (number_of_packages).
- NO existen: zebra.label, product.barcode, product_multi_barcode, warehouse EFFEC.

## Almacenes (todos con delivery_steps = ship_only)

| id | código | compañía | stock | OUT | INT | IN | DEV |
|---|---|---|---|---|---|---|---|
| 1 | WH-OR | PRIME COLLECTIONS (1) | WH-OR/Stock | 2 | 5 | 1 | 151 |
| 109 | MODAI | MODA INTIMA 1964 (23) | MODAI/Stock | 839 | 842 | 838 | 847 |
| 99 | UBRAN | UNITED BRANDS 2015 (21) | UBRAN/STOCK (en mayúsculas) | 747 | 750 | 746 | 2037 |

- SORTER: WH-OR/SORTER, WH-OR/Stock/N1/SORTER y MODAI/SORTER (todos internal).
- Faltas: existe WH-OR/Stock/N1/FALTAS_001.
- Ubicaciones: `.../N1/06298 - L75 P38 C2/KO_300726_755`, `UBRAN/STOCK/N1/20640 - L147 P05 C4/UB_240725_612`, `.../TT_240726_013`. Hay 152.101 internas en WH-OR.

## Cómo se trabaja hoy (OUT del 26/11)

- Las OUT salen de WH-OR/SORTER hacia el cliente, en paquetes BOX0699806 (result_package_id). 5.317 de 5.572 líneas tienen paquete; 3.951 van en lote.
- Las INT van de la estantería a WH-OR/SORTER.
- Líneas de OUT por usuario: Almacen Automatizado [081] 3.923, LLUIS 504, Almacen Prime Collections 486, Mercy 392, Administracion 252, Jordi 15.
- Lotes: B-ECI_271126_06, B-VP_271126_03, WEB_271126_02, B-MIECI_271126.

## Personas

- Usuarios del almacén con compañías [1, 21, 23] (algunos además 3, 4, 5, 7), tz Europe/Madrid.
- hr.employee con barcode: PRIME 58, MODA INTIMA 3.

## Productos

- EAN 8447333…, 8435689… Códigos KG14A401W1 y 9873-07-36.
