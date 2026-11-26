# koroshi_zonas: zonas que se adaptan a lo que entra y aprenden (26/11/2026)

Sesión «Zonas: mejorar». **Solo diseño, sin código.** El módulo lo lleva ahora «Correcciones revisión general».

Isaac (26/11): «quiero que este módulo de zonas vaya aprendiendo y haciendo las zonas en base a lo que entra».

## Lo que pasó el 26/11 (diagnóstico, solo lectura)

- 6.192 uds (el doble que el 24 y 25). Prenda nueva a casi todas las tiendas: 2621SU60 y 2621PL50, todas las tallas,
  ~600 uds, en L51-L52 (contenedores KO_171126). Lineales L50-L59: 1.690 uds en D2 (otros días < 30).
- 10 % de las uds en SKUs que van a ≥ 80 % de las tiendas (19-25/11: 0 %): **día de implantación**.
- El reparto equilibra trabajo, no metros: D1 L1-L51 (2 pers.), D2 casi solo L42-L79 (4), **D3 L70-L136 (5)**.
  Otros días D3 era L100-L136.
- Nada cambió en el módulo (1.7.0 = solo avisos; motor igual desde 1.6.0), ni en los parámetros (24, 25 y 26 iguales).
  El orden por pedido no mueve fronteras (la partición suma el trabajo por pasillo).
- Con 4 o 5 zonas de lineal (probar, sin rastro) la última zona sigue siendo L70-L136 y se gana ~12 min: no es la
  solución.
- Lecturas a las 08:17: D1 32 s/ud, D2 35 s/ud, **D3 41 s/ud** (28 % hecho contra 42 % de D1 y D2). Las zonas anchas
  son más lentas de lo que el modelo dice (un solo valor de 21 s por lineal).

## Propuesta: tres piezas

### 1. Ver qué entra (cada mañana, antes de partir)
- Clasificar el día con los datos que ya lee el motor: % de uds en SKUs que van a ≥ 50 % y ≥ 80 % de las tiendas
  (memoria «implantación vs reposición»: días de implantación = ≥ 50 % de las uds en SKUs compartidos).
- Sale en el informe: «Día de REPOSICIÓN (0 % compartido)» o «Día con IMPLANTACIÓN (10 %: 2621SU60, 2621PL50 → 49
  tiendas, L51-L52)».

### 2. Zona por artículo para lo compartido
- Los SKUs que van a ≥ N % de las tiendas (ajuste, propuesta 80 %) y suman ≥ M uds (propuesta 200) salen de las zonas
  de lineal a una zona **ART** (`Z-ddmm-ART`): una persona (o dos) coge la prenda del hueco y la reparte en las cajas de
  las tiendas (como el muelle, pero por artículo). Lista en el informe: prenda, hueco, uds, tiendas.
- El resto se parte por zonas como hoy, ya sin el bloque denso: zonas más iguales y más cortas.
- Riesgo medio: cambia la forma de trabajar ese día (reparto a cajas por artículo). Se prueba primero en diagnóstico.

### 3. Aprender de lo que pasa (cada noche)
- Ya se guarda cada noche, por zona, el previsto contra real con las lecturas de la PDA (1.5.0).
- Añadir: segundos por ud reales de cada zona según su **anchura** (lineales) y su **densidad** (uds por lineal).
  Con 2-3 semanas sale una fórmula propia del almacén (p. ej. «21 s por lineal» pasa a depender de la anchura).
- Con esos valores el motor reparte mejor las fronteras: una zona ancha y poco densa ya no se lleva 5 personas y
  2.300 uds porque el modelo la crea más barata de lo que es.
- **No se cambia solo**: la pantalla enseña «previsto contra real» y la propuesta de ritmo; un jefe pulsa «Usar el
  ritmo real» (como en el diseño del modo del día, `diseno-zonas-modo-del-dia_2026-11-20.md`).

## Orden propuesto
1. Pieza 1 (solo informe): riesgo nulo.
2. Pieza 3 (medir y proponer, sin aplicar): riesgo nulo, empieza a juntar datos ya.
3. Pieza 2 (zona ART): cuando haya otro día de implantación con el diagnóstico enseñando cómo quedaría.
