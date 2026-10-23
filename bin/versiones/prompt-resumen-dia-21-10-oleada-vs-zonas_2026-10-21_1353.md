# Contexto para otra IA: picking KOROSHI, oleada vs zonas (21/10/2026)

Actúa como consultor de operaciones de almacén y de Odoo 13. Te paso todo lo que hemos medido hoy en una prueba real. Quiero que me ayudes a decidir el método, dimensionar personal para 10.000–15.000 unidades/día y planificar cómo imprimir las etiquetas de caja. Responde en castellano, con números y supuestos claros.

## Empresa y sistemas
- Almacén logístico (Effective Logistics) que prepara los pedidos de reposición de ~50 tiendas de moda KOROSHI (pedidos "PED. TIENDAS", 1 pedido = 1 tienda = 1 albarán de salida OUT).
- Odoo 13 Enterprise (licencia por usuario interno; hoy hay 6 usuarios internos y todas las PDA comparten el usuario "Almacén Nath").
- PDA con la app de códigos de barras de Odoo + módulos de Brain Station 23 (barcode_batch_process, stock_barcode_optimization…). Hoy los operarios imprimen una etiqueta por OUT y la escanean con la PDA para abrirla; van OUT a OUT.
- Matrículas de caja "CJ…" (modelo zebra.label, secuencia "Etiquetas Zebra", ej. CJ665004045). En la PDA se escanea la CJ al cerrar la caja (crea el paquete).
- Transportista XPO (módulo propio delivery_xpo + merge_delivery_shipment): la etiqueta XPO se genera al final, por tienda, juntando todas sus OUT en un solo envío con el nº de bultos.
- Programa propio "Pedidos Múltiples" (C#, puesto "la U"): lee prenda a prenda, la asigna a la bahía de su tienda (10 bahías), cierra caja (llama a una acción de Odoo que crea la CJ) e imprime la etiqueta de caja en una Zebra 4x6".
- Nave: lineales L1–L136, posiciones P00–P38; NAVE2 aparte. Cajas de envío 60x40x40 (~75 litros útiles). Baúles de picking 80x50x33 (~100 l útiles).

## Método 1: oleada + U (como se hizo esta mañana)
1. De noche, una acción de Odoo elige 10 tiendas (~2.000 u), crea la oleada (agrupación B-KOR-2110-01) y 5 INT por zonas (D1–D5, cortadas para que todas tarden lo mismo) + 1 INT de NAVE2. Los INT llevan la mercancía a la ubicación SORTER.
2. 5 operarios cogen su zona en baúles y los llevan a la U.
3. Se validan los INT, "Comprobar disponibilidad" en las 10 OUT y se carga la oleada en el programa.
4. En la U, 1 puesto lee prenda a prenda → bahía → cierra caja (CJ) → etiqueta.
5. Después: precintar, etiqueta XPO, montar y flejar palets. Solo hay 4 cajas montadas por bahía: hay que ir montando más.

Datos reales de hoy:
- 10 tiendas, 1.620 u pedidas, 1.503 con stock reservado, 1.482 cogidas (21 no aparecieron en el hueco; luego 16 se encontraron).
- Picking: 6:10 → ~8:25 (D5 7:39, D4 7:48, D2 ~7:50, D3 ~7:55, D1 ~8:20). ≈ 8,2 horas-persona → **≈ 180 u/h por persona**.
- Zonas con implantación (11 artículos con todas las tallas a las 10 tiendas, 831 u): D2 (tops TR, 12 u por hueco) iba a ~270 u/h; D4 (chaquetas) a ~142 u/h.
- 105 baúles llenos (~14 u por baúl). Previsión ~125–130 cajas de envío.
- Lectura en la U: empezó a las 9:14; a las 12:58 llevaba 1.035 de 1.482 u → **≈ 277 u/h por puesto**. Fin previsto ~14:30–15:00 (≈ 8 h 30 desde el inicio).
- Incidencias: (a) no se puede cargar la oleada en la U mientras los INT están abiertos (~1 h de U parada); (b) error al validar INT "El registro no existe (stock.move)": causa = líneas "fantasma" que deja la PDA al escanear un artículo equivocado (17 hoy); se arregló borrándolas con una acción; la versión nueva de la acción de zonas crea un movimiento por artículo para evitarlo; (c) stock mal ubicado en 14 huecos; (d) alguien pulsó "Force Availability" en la agrupación y marcó todo como hecho sin reservar; se deshizo con una acción.

## Método 2: zonas sin U (prueba de esta mañana)
1. Una acción de Odoo parte cada pedido de tienda en una OUT por zona (mismo pedido de origen S-…), y crea una agrupación por zona (Z-2110-D1…D5 + ZX = NAVE2). Cada OUT lleva en la nota la zona y el "número de caja de tienda" (01–25, igual en todas las zonas).
2. Cada operario coge su zona OUT a OUT con la PDA, mete en caja, escanea la CJ y valida. Las cajas salen cerradas en el lineal.
3. Al final: transpaleta a expediciones, juntar las cajas de cada tienda (vienen de varias zonas), fleje. XPO por tienda.

Datos reales de hoy:
- 25 tiendas (las más grandes no empezadas), 1.696 u, partidas en **118 OUT** (25 originales + 93 nuevas; 4,7 OUT por pedido; 27 OUT con ≤3 u).
- Unidades por zona: D1 170, D2 200, D3 558, D4 446 (chaquetas implantación), D5 299 (chaquetas), ZX 23.
- Etiquetas de OUT impresas entre 8:48 y ~9:05 (≈15 min de preparación).
- Picking: 9:35 → 12:59: **1.666 u en 3 h 24 → ≈ 491 u/h de equipo**; con 5 personas **≈ 98 u/h por persona**, ya con caja cerrada y matrícula. (No está confirmado cuántas personas había.)
- Ritmos por tramo: 9:53–10:17 ~220 u/h; 10:43–11:31 ~530 u/h; 11:31–12:00 ~570 u/h; 12:00–12:25 ~480 u/h.
- Cajas: ~220 si cada OUT va en su caja; ~155 si en el muelle se juntan las partes pequeñas de cada tienda.
- Problemas: van OUT a OUT (repiten pasillo una vez por tienda); muchas OUT pequeñas; en la lista de Odoo las columnas "Demanded/Reserved Quantity" salen infladas en las OUT partidas (campo guardado copiado del original), las unidades reales son correctas.

## Comparación de hoy (de principio a fin)
- Zonas: 1.696 u, 3 h 24, cajas cerradas al acabar el picking.
- Oleada: 1.482 u, ~8 h 30 (picking 2 h 15 + espera ~1 h + U ~5–6 h), más cajas/precinto/palets después.
- Por hora-persona salen parecido (~100–110 u por hora-persona) si en la oleada se cuenta picking + U; si se cuentan cajas y palets de la oleada (~4,3 h-persona por 1.000 u, estimado), las zonas ganan ~20 %.
- Individual (14 pedidos sueltos): 1.176 u, 8:00 → 11:38 (~325 u/h de equipo).
- Hoy entraron 50 pedidos de tienda con 4.664 u (más 31 online con 64 u). 0 recepciones.

## Proyecciones que hice (revísalas)
Supuestos: picking oleada 180 u/h/persona; U 277 u/h/puesto; zonas 98 u/h/persona hoy y 150 con mejoras (varias OUT por pasada, sin imprimir, menos OUT pequeñas).
- 10.000 u desde las 3:00: oleada 8 pickers + 5 U + ~5 de cajas/palets (~18 personas) ≈ 11:45; con 1 U es imposible (36 h). Zonas 8 personas a 150 u/h ≈ 11:20 (+1–2 de expedición).
- 15.000 u desde las 3:00 con 8 zonas: oleada 8 pickers + 6 U + 6–7 cajas/palets (~20 personas) ≈ 14:00; zonas 8 personas a 150 u/h ≈ 15:30 (~10 personas); para antes de las 14:00 en zonas ≈ 10 pickers + 2 expedición.
- Con la misma plantilla (~20 personas), zonas acabaría 2 h 30–5 h antes que oleada.
- 10.000 u son ~130–150 tiendas: en zonas hay que trabajar por rondas de ~25 tiendas y evitar OUT a OUT.

## Lo que queremos preparar (para mañana: 8 personas, 8 zonas, método zonas)
1. Partir los pedidos en 8 zonas (la acción ya admite N_ZONAS = 8).
2. Que al sacar las OUT de cada zona se imprima, por cada caja prevista, una etiqueta 4x6" con: zona, nº de caja de tienda, DELEGACIÓN (en grande), tienda, PEDIDO S-… (en grande), "caja i de n", código de barras de la OUT (para abrirla en la PDA) y código de barras de la matrícula CJ (para cerrar la caja). Nº de cajas previstas por volumen (litros/75).
3. Otra etiqueta de "bulto agrupado" cuando varias cajas pequeñas de la misma tienda se meten en un solo bulto: una CJ de bulto + la lista de las CJ que contiene.
4. Ideal: que salga también la etiqueta del transportista XPO por caja. Problema: el módulo XPO crea un envío real por tienda con el nº final de bultos; generarlo al principio con bultos estimados es arriesgado.
5. Más adelante: un usuario por PDA (costaría licencias Enterprise) o una tarjeta fija por zona para abrir la agrupación sin imprimir nada.

Ya tenemos (borradores, en modo diagnóstico): una acción de servidor que, por agrupación de zona, calcula las cajas por volumen, reserva las matrículas CJ en zebra.label y devuelve la lista de etiquetas "OUT|CJ|zona|caja|tienda|pedido|i|n" para que las imprima el programa de la U; y el diseño de las dos etiquetas.

## Preguntas para ti
1. ¿Qué método recomiendas para 10.000–15.000 u/día y con cuántas personas? ¿Qué datos nos faltan para decidir?
2. ¿Cómo organizarías las rondas de zonas (cuántas tiendas por ronda, cómo agrupar por delegación/ruta de transporte)?
3. ¿Dónde implementarías la impresión OUT/matrícula: en el programa de la U (menú "imprimir etiquetas de zona" que llama a la acción de Odoo), en un informe QWeb de Odoo sobre la agrupación, o en la app de la PDA? Pros y contras.
4. ¿Cómo resolverías la etiqueta XPO por caja (o por tienda) sin crear envíos con bultos equivocados?
5. ¿Qué mediríais en las próximas pruebas para tener ritmos fiables (personas por zona, inicio/fin, cajas, incidencias)?
