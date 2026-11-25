# Pedidos apuntados por Isaac (24/11/2026, pedidos de tienda triplicados)

Lista que ha dictado Isaac mientras revisaba el dashboard de S4T. Isaac dice que **estos deberían cancelarse**.
Estado en Odoo a las ~09:30 del 24/11 (solo lectura; no se ha cancelado nada de esta lista).

**Hecho 24/11 (~09:45):** por orden de Isaac se han cancelado en Odoo las 45 OUT abiertas de estos 16 pedidos
(recomprobadas una a una: 0 uds leídas; nota en el chatter de cada OUT). Quedan las 5 OUT ya validadas. Las S- siguen
confirmadas en Odoo y los pedidos siguen válidos en S4T.

**Regla de KOROSHI (Isaac, 24/11):** se cancelan en Odoo los 18 pedidos de esta lista y de cada tienda se prepara el
otro pedido que tengamos. Los que salen CANCELLED en la API pero ya están hechos y no están en la lista, nos los
quedamos.

**Recreadas 24/11 (~10:00)**, por orden de Isaac, las OUT del «otro pedido» que cancelé esta mañana sin nada leído
(copia de la OUT cancelada, mismo pedido y misma oleada; nota en el chatter):

| Tienda | Pedido | Cancelada | Nueva | Oleada | Uds pedidas / reservadas |
|---|---|---|---|---|---|
| K72 | 4627 | 27249 | 27565 | D1 | 46 / 37 |
| K72 | 4627 | 27426 | 27564 | D3 | 14 / 14 |
| K77 | 4628 | 27427 | 27566 | D1 | 19 / 19 |
| K77 | 4628 | 27250 | 27567 | D3 | 35 / 21 |
| K78 | 4629 | 27429 | 27569 | D1 | 21 / 21 |
| K78 | 4629 | 27251 | 27570 | D3 | 31 / 28 |
| K78 | 4629 | 27431 | 27568 | MU2 | 3 / 3 |
| K59 | 4630 | 27432 | 27572 | D1 | 15 / 15 |
| K59 | 4630 | 27433 | 27571 | D3 | 8 / 8 |
| K31 | 4635 | 27438 | 27573 | D1 | 10 / 10 |
| K31 | 4635 | 27257 | 27574 | D3 | 22 / 16 |
| K46 | 4683 | 27312 | 27575 | D1 | 26 / 21 |
| K82 | 4653 | 27275 | 27563 | JUNTAR | 2 / 2 |
| K82 | 4702 | 27331 | 27576 | JUNTAR | 13 / 13 |

## Pedidos válidos en S4T (tanda 01:58) que Isaac quiere cancelar: 16 pedidos

OUT abiertas: 45 OUT, 2.148 uds sin leer. Ya validado de estos pedidos: 5 OUT, 54 uds (no se pueden cancelar).

| Pedido | Tienda | OUT abiertas (uds pedidas, 0 leídas) | Ya validado | Cancelado de la misma tienda ya preparado |
|---|---|---|---|---|
| 6665004712 | K48 | 27481 D1 (74), 27482 D2 (67), 27371 D3 (224), 27483 MU2 (2) = 367 | — | 4614 entero (185) |
| 6665004713 | K65 | 27484 D1 (55), 27485 D2 (50), 27372 D3 (128) = 233 | 27486 MU2 (2) | 4615 entero (136) |
| 6665004714 | K33 | 27373 D1 (150), 27487 D2 (41), 27488 D3 (56) = 247 | 27489 MU2 (2) | 4616 entero (158) |
| 6665004717 | K24 | 27376 D1 (66), 27494 D2 (48), 27495 D3 (38) = 152 | — | 4619 entero (104) |
| 6665004718 | K41 | 27496 D1 (59), 27377 D2 (89), 27497 D3 (38) = 186 | — | 4620 entero (120) |
| 6665004719 | K45 | 27498 D1 (31), 27499 D2 (32), 27378 D3 (52) = 115 | — | 4621 entero (52) |
| 6665004720 | K22 | 27500 D1 (30), 27501 D2 (28), 27379 D3 (69) = 127 | 27502 MU2 (5) | 4622 entero (87) |
| 6665004721 | K83 | 27380 D1 (70), 27503 D2 (58), 27504 D3 (38) = 166 | — | 4623 entero (111) |
| 6665004725 | K72 | 27383 D1 (67), 27512 D2 (23), 27513 D3 (28) = 118 | — | 4627 D2 (24) |
| 6665004726 | K77 | 27514 D1 (36), 27515 D2 (14), 27384 D3 (53) = 103 | — | 4628 D2 (13) |
| 6665004727 | K78 | 27516 D1 (29), 27517 D2 (23), 27385 D3 (40), 27518 MU2 (4) = 96 | — | 4629 D2 (9) |
| 6665004728 | K59 | 27519 D1 (18), 27520 D2 (23), 27386 D3 (39) = 80 | — | 4630 D2 (20) |
| 6665004732 | K46 | 27527 D1 (14), 27346 D2 (27) = 41 | — | 4634 D2 (9, a medias) |
| 6665004733 | K31 | 27528 D1 (26), 27529 D2 (30), 27389 D3 (45) = 101 | — | 4635 D2 (13, a medias) |
| 6665004737 | K73 | 27535 MU2 (1) = 1 | 27350 D2 (36), 27534 D3 (9) | 4639 D2 (20) |
| 6665004751 | K82 | 27363 JUNTAR (15) = 15 | — | ninguno |

Ojo: los pedidos válidos piden **más** que los cancelados (p. ej. K48: 367 uds pendientes + 0 hechas frente a 185 del
cancelado 4614). No son copias exactas; cancelar el válido deja a la tienda solo con lo del cancelado.

## Pedidos cancelados en S4T que también ha pasado Isaac (ya cancelados en S4T; en Odoo queda lo validado)

| Pedido | Tienda | Odoo |
|---|---|---|
| 6665004618 | K10 | 3 OUT validadas: 27405 D1 (37), 27287 D2 (52 de 80), 27406 D3 (45) |
| 6665004632 | K42 | 27436 MU2 validada (1); el resto cancelado |
| 6665004667 | K10 | 27448 y 27342 canceladas, nada leído |
| 6665004694 | K69 | 27475 MU2 validada (1); el resto cancelado |
