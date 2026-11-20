# Tablero del responsable: ajuste tras la grabación del 20/11 (diseño v6, 20/11/2026, sin código)

Sale de la v5 (`diseno-tablero-responsable_2026-11-19_v5.md`, no se toca) y de lo instalado:
- koroshi_operarios 2.20.0: tablero kanban;
- 2.21.0/2.21.1: pantalla con cinco formatos A-E y grupo por usuario;
- hoy la 2.22.1 (tarjeta compartida, de otra sesión).

Recoge los puntos 5 y 6 de `plan-grabaciones-29-30_2026-11-20.md`.

## Lo que dijo Isaac

1. **Le gusta arrastrar a la persona a su tarea**, como en el formato D: columnas por zona, se arrastra a la persona.
2. **Le preocupa que con mucha gente o muchos pedidos el tablero sea una locura.**
3. **En picking no quiere OUT sueltas.** Con 200 (o 2.000) pedidos al día no sirven. El trabajo se da por **zona o
   agrupación**.
4. **Al acabar, cada operario coge la siguiente zona o agrupación libre** por **unidades** (la de 50 acaba antes que
   la de 120) y por **prioridad de tienda** (el número S4T más bajo primero).
5. **Recepción, compactación y devoluciones no se asignan.** El operario entra en su área y ya está. Solo se asigna el
   picking.
6. **Entrada única por áreas en la PDA** (otro chat): una entrada con una pestaña por área; al entrar en un área
   empieza a contar su tiempo. Las áreas son:
   - Recepciones;
   - Picking;
   - Compactación;
   - Devoluciones;
   - Inversa;
   - Expediciones;
   - Extra.

   El tablero tiene que reflejar esas áreas.
7. **Botón para elegir cada día «tradicional o zonas», con una estimación.** Es cosa del chat de zonas. El tablero
   solo lo enseña.

## Cómo queda (propuesta)

**Un solo formato: D, por áreas.** Fuera A, B, C y E, y fuera el kanban clásico cuando este se vea bien. El tablero
se convierte en un **mapa de dónde está cada persona**: columnas = áreas, y dentro de Picking, una fila por zona o
agrupación.

```
| Picking                                   | Recepciones | Compactación | Devoluciones | Inversa | Expediciones | Sin área |
|  Z-2011-D1  ███████░░ 18/25 · 7 libres    |  AG  CR     |  DZ          |  EA          |         |  JA          |  IS      |
|    DC  SH                                 |             |              |              |         |              |          |
|  Z-2011-D2  ███░░░░░░  8/20 · 12 libres   |             |              |              |         |              |          |
|    (vacía: arrastra aquí)                 |             |              |              |         |              |          |
|  WEB_201126_01  ██████░ 30/45             |             |              |              |         |              |          |
|    DW                                     |             |              |              |         |              |          |
```

- **Solo se arrastra en Picking.** Arrastrar a una persona a una zona hace lo mismo que hoy:
  - esa zona va la primera de su cola;
  - la PDA le da sus OUT una a una, en el orden de CAJA de koroshi_zonas.
- **Las otras áreas solo se miran.** La persona sale en el área en la que ha entrado en la PDA (entrada única).
  - Si se la arrastra fuera de su área, no pasa nada; como mucho, un aviso.
  - Hasta que exista la entrada única, se sigue usando lo que hay:
    - picking = tarea en curso en Lecturas;
    - compactación = koroshi_contenedores;
    - devoluciones e inversa = actividad abierta en el portátil;
    - el resto, «Sin área».
- **Fuera de «Por repartir»**:
  - las OUT sueltas;
  - las tarjetas de actividad: las actividades ya no se asignan.
  - **Solo queda la nota**, por si el jefe quiere mandar algo concreto («ayuda a descargar el camión»).
- **Para que no sea una locura con mucha gente o pedidos**:
  - una fila por zona o agrupación, no por OUT ni por persona;
  - las personas como iniciales pequeñas;
  - las zonas acabadas se pliegan solas.
  - Con 2.000 pedidos y 30 zonas siguen siendo 30 filas.
  - Las agrupaciones de otros días o de prueba, plegadas en «Otras».
- **Columna vacía (operario que acaba su zona)**: pasa solo a la **siguiente zona o agrupación libre** (ya no a la
  siguiente OUT suelta). El orden lo decide **koroshi_zonas** (punto siguiente). El tablero lo enseña: cada zona
  libre con un número «1.ª, 2.ª…» de cuál toca después.

## Quién hace qué (para no pisarse)

- **«Siguiente zona libre» (unidades + prioridad S4T)**:
  - **lo calcula koroshi_zonas**, que ya sabe las uds y los números de pedido de cada zona (`motor/evaluar.py`,
    `numero_pedido`);
  - operarios no puede importar zonas, porque zonas depende de operarios;
  - propuesta: operarios deja un método vacío en `koroshi.operario.asignacion`, `_orden_lotes_libres(lotes)`, que
    hoy ordena por nombre;
  - koroshi_zonas lo sobrescribe con su orden;
  - **a confirmar con «Zonas: revisar»**: qué pesa más (uds o prioridad) y cómo se combinan.
- **Botón tradicional / zonas del día**: lo hace zonas. Con «tradicional», el tablero enseña en Picking una sola
  fila, «Pedidos (tradicional)», y la columna vacía da la siguiente OUT como hoy.
- **Áreas**: las define el chat de la **entrada única**. El tablero lee «en qué área está cada operario ahora».
  Propuesta: un campo `area` (selección) en la tarea en curso o en el registro de tiempos de la entrada única, en
  tabla propia, **nunca en stock.***. Hasta entonces, la deducción de arriba.

## Preguntas para Isaac

- **P1.** ¿Quitamos ya los formatos A, B, C y E y nos quedamos con D por áreas? ¿El kanban clásico se quita también?
- **P2.** Columna vacía: ¿siempre la siguiente zona libre o, en modo tradicional, la siguiente OUT?
- **P3.** ¿La nota se queda (mandar algo concreto a alguien) o también sobra?
- **P4.** «Sin área»: ¿se enseña quién ha pasado la tarjeta hoy y no está en ningún área? Sirve para ver a quien está
  parado.

## Versión

- **koroshi_operarios 2.23.0** (mirar antes la installed_version: hoy 2.22.1, de otra sesión).
- Solo tablas propias.
- Lo de zonas va en su versión de koroshi_zonas y se instala **después** de operarios (uno a uno).
