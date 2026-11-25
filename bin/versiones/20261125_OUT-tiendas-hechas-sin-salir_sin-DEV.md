# OUT de tiendas validadas el 24/11 que no han salido (sin etiqueta) y sin DEV (25/11/2026, ~10:00)

Odoo, solo lectura. OUT de PED. TIENDAS en estado hecho, validadas el 24/11, sin nº de transportista. Ninguna tiene
devolución (no hay movimientos de devolución ni otro movimiento de sus cajas después de validarlas): **todas sus cajas
están en Partner Locations/Customers**, así que para Odoo esa mercancía ya ha salido aunque físicamente esté en el
almacén. No se ha hecho ninguna de las DEV del documento del 24/11 (`20261124_DEV-7-OUT-validadas-pedidos-cancelados.md`).

## A. Pedido cancelado en S4T (estado ERROR en Odoo): DEV

| OUT | Pedido | Tienda | Zona | Uds | Cajas |
|---|---|---|---|---|---|
| 27253 | 4631 | K62 XANADU | JUNTAR | 11 | |
| 27502 | 4720 | K22 VITORIA | MU2 | 5 | CJ665013644, CJ665013635 |
| 27489 | 4714 | K33 PUERTO VENECIA | MU2 | 2 | CJ665013643 |
| 27486 | 4713 | K65 BARICENTRO | MU2 | 2 | CJ665013642 |
| 27473 | 4693 | K40 PALENCIA | MU2 | 1 | |
| 27436 | 4632 | K42 SPLAU | MU2 | 1 | CJ665013634 |
| 27475 | 4694 | K69 TARRAGONA | MU2 | 1 | CJ665013640 |
| 27457 | 4674 | K9 BALLONTI | MU2 | 1 | |

Total: 8 OUT, 24 uds. (27502 / 4720 sale PENDING en Odoo, no ERROR; estaba en la lista de Isaac para cancelar.)

## B. Pedido READY en S4T, preparado y sin salir: enviar o DEV según KOROSHI

| OUT | Pedido | Tienda | Zona | Uds | Qué dice KOROSHI |
|---|---|---|---|---|---|
| 27354, 27545 | 4742 | K40 PALENCIA | D1, MU2 | 26 | «tiene que expedirse hoy» (correo 24-25/11) |
| 27369, 27555 | 4757 | K44 GIRONA | D2, D3 | 25 | nada; revisar por qué no se etiquetó |
| 27350, 27534 | 4737 | K73 LLEIDA | D2, D3 | 45 | ya salió la 4639 de K73 (GLS); pendiente de decidir |
| 27256 | 4634 | K46 IRÚN | D2 | 16 | ya salió la 4683 (GLS); preguntado en el correo del 25/11 |
| 27420, 27422 | 4625 | K9 BALLONTI | D2, MU2 | 20 | ya salió la 4723 (XPO); preguntado en el correo del 25/11 |

Total: 9 OUT, 132 uds.

## C. Aparte

- 27576 (4702, K82, 13 uds, CJ665013649): tiene el nº XPO 121771371 pero no se declaró a XPO ni entró en el cierre
  del 24/11. KOROSHI quiere la 4751 de K82, así que esta va a DEV si la caja está en el almacén.
