# Tablero del responsable: v7 (20/11/2026, sin código)

Sale de la v6 (`diseno-tablero-responsable_2026-11-20_v6.md`, no se toca). Recoge dos cosas:
- las respuestas de Isaac del 20/11;
- el diseño de zonas, `diseno-zonas-modo-del-dia_2026-11-20.md`, de la sesión «Zonas: mejorar».

## Respuestas de Isaac (20/11)

- **P1: solo el formato D.** Fuera A, B, C, E y el kanban clásico.
- **P3: sin nota.** «Por repartir» se queda sin nada suelto: en Picking solo hay zonas y agrupaciones.
- **P2: el modo tradicional sobra en el tablero.** La columna vacía da siempre la siguiente zona o agrupación libre,
  nunca una OUT suelta.
- **P4 «Sin área»**: lo preguntó (¿qué sería?). Se le explica abajo y queda pendiente.

## Lo que trae zonas (si Isaac lo aprueba allí)

- **Agrupaciones nuevas `Z-ddmm-T01`, `T02`…** para los pedidos sueltos y pequeños:
  - con OUT enteras;
  - por número de pedido;
  - juntando pequeños hasta un mínimo de uds.
  - El filtro de zonas del tablero (`RE_ZONA`) pasa a aceptar `T\d+` además de `D\d+` y `MU\d+`.
- **En una T trabaja una sola persona** (va con su carro y la prepara entera).
  - Al arrastrar una T a alguien, se le da **la agrupación entera** (tipo `agrupacion`, la de siempre). La pieza sale
    de «Por repartir», como una OUT suelta hoy.
  - En D y MU sigue igual: OUT a OUT y varias personas a la vez.
- **Prioridad** de una zona o agrupación = **el número de pedido más bajo que lleva**. El tablero lo calcula solo, con
  `_numero_pedido` del origin, que ya tiene. **No hace falta enganche con zonas**: se cae el `_orden_lotes_libres`
  de la v6.
- **La de 50 acaba antes y coge otra** sale sola de «quien acaba coge la siguiente». No hay regla por uds.

## Cómo queda

- Pantalla única D por áreas. En **Picking**, una fila por zona o agrupación libre o empezada, en orden de prioridad,
  con «1.ª, 2.ª…» en las que nadie ha empezado.
- **Arrastrar a una persona a una zona**: esa zona va la primera de su cola, como en la 2.21.
- **Columna vacía**: la PDA le da la siguiente libre por prioridad:
  - en D y MU, la siguiente OUT de la primera zona que tenga OUT libres;
  - en una T, la T entera, si nadie la tiene.
- **Las demás áreas solo se miran.** Salen de la entrada única de la PDA, sesión «pda-entrada-unica», cuando exista.
  Hasta entonces se deducen de lo que hay.

## P4 explicada: «Sin área»

Es la columna de quien **ha pasado la tarjeta hoy pero ahora no está en ninguna área**. Por ejemplo:
- ha acabado una zona y no ha cogido otra;
- ha salido de Contenedores;
- está en el descanso.

Sirve para ver de un vistazo quién está parado, y desde ahí se le arrastra a una zona de picking.

Opciones para Isaac:
- **(a)** la columna se queda;
- **(b)** se quita, y quien no está en ningún área no sale.

## Versión

- **koroshi_operarios 2.23.0**: mirar la installed_version antes; hoy es la 2.22.1.
- Las T de zonas pueden llegar después. El tablero ya las acepta, y mientras no existan no cambia nada.
