# Diseño: «Caja llena» por volumen en Lecturas (PDA) — 25/11/2026, v1

Solo diseño. No hay código. Isaac aprobó la idea el 25/11 y pidió los dos botones «Caja llena: cerrar» / «Aún cabe
más». Módulo: `koroshi_preparacion` (Lecturas): lo programa la sesión que lo tenga cogido en el TABLERO (regla 6).

## Por qué

- El 25/11, en la K1 MAQUINISTA (S-6665004772, D2), la preparadora llenó dos cajas físicas. En Odoo, las 23 uds
  quedaron en una sola CJ (CJ665013811). La segunda caja llevaba pegada la CJ665013810, que nunca se leyó. Se arregló
  con «Revisar caja» (`koroshi_juntar_cajas` 1.1.0).
- Por uds no se ve: 23 uds parecían pocas, pero 6 eran chaquetas.
- **Por volumen sí:** la 811 de antes sumaba **0,149 m3**. Después de partirla: 811 = 0,076 m3 (6 chaquetas) y
  810 = 0,073 m3 (17 uds).

## Datos (Odoo, cajas CJ desde el 24/11, 25/11 por la mañana)

- `product.product.volume` está en **1.643 de 1.753** artículos de esas cajas (94 %).
- Volumen de una caja = suma de volumen × `qty_done` de sus líneas.

| Tipo de caja | Cajas (todo con volumen) | p50 | p75 | p90 | p98 | Máx |
|---|---|---|---|---|---|---|
| CAJA 600X400X400 (0,096 m3) | 321 | 0,080 | 0,088 | 0,097 | 0,107 | 0,131 |
| CAJA KOROSHI MEDIANA | 66 | 0,036 | 0,053 | 0,066 | 0,088 | 0,099 |

- 35 cajas pasan de 0,096 m3: o la ropa se aprieta más de lo que dice Odoo, o son dos cajas en una CJ.

## Propuesta

### En la pantalla de Lecturas

Una barra «Caja 78 %» con el volumen de **mis uds leídas sin caja** en esa OUT. Es lo que ya cuenta Lecturas como
`mias_sin_caja` en `_reparto_sin_caja` (`lectura.py:376`): lo que irá en la próxima CJ que lea esa persona.

- Capacidad: la del tipo de caja que esa persona usó en su última caja; si no hay, la 600X400X400. Valores en un
  parámetro por tipo de caja (empezar con 0,090 m3 para la 600X400 y 0,060 para la mediana, y ajustar con los
  datos).
- Artículo sin volumen: cuenta con la media de los que tienen (o la de su familia, si se puede sacar del nombre).
- Hasta el 90 %: barra verde, sin avisos.
- Del 90 % al 100 %: barra naranja, «Casi llena».
- **Al llegar al 100 %**: pitido y dos botones (lo que pidió Isaac):
  - **«Caja llena: cerrar»** → abre lo de siempre: leer la CJ de la caja.
  - **«Aún cabe más»** → sigue leyendo. No vuelve a preguntar hasta el 115 %.
- **Por encima del 115 %**: aviso fuerte, rojo, con los mismos dos botones: «Esto no cabe en una caja: ¿son dos?
  Lee la CJ de la primera». La K1 habría llegado al 165 %.
- No bloquea nunca: solo avisa. Lecturas es la pantalla de todo el día.

### Datos para ajustarlo

- Cada respuesta se guarda en una tabla propia (p. ej. `koroshi.preparacion.caja_llena`: persona, OUT, tipo de caja,
  % y m3 en ese momento, respuesta, y la CJ que se leyó después). Nada de campos nuevos en tablas compartidas.
- Con eso, el Monitor (sesión de mejoras del Monitor, ya avisada) enseña cada semana cuánto cabe de verdad en cada
  tipo de caja: el volumen con el que se cierra y cuántas veces dicen «Aún cabe más» y hasta dónde llegan. Los
  porcentajes se ajustan con esos datos.

### Lo que no hace

- No cambia cómo se cierra la caja (leer la CJ con el botón Caja) ni el tipo de caja.
- No mira las cajas ya cerradas: eso lo hace el Monitor («¿dos cajas en una CJ?» por encima de ~0,11 m3).

## Preguntas

- **V1.** ¿La capacidad se toma del último tipo de caja de esa persona (propuesta) o se elige el tipo al empezar
  cada caja?
- **V2.** ¿Los porcentajes 90 / 100 / 115 valen para empezar?
- **V3.** ¿«Aún cabe más» lo puede pulsar cualquiera o pide algo (p. ej. que lo apunte el jefe)? Propuesta:
  cualquiera, queda guardado.

## Qué probar en una PDA real

1. Leer prendas hasta pasar el 90 %, el 100 % y el 115 % en una OUT de prueba (solo leer y deshacer).
2. Con dos personas en la misma OUT: cada uno ve solo su barra.
3. «Aún cabe más» y después leer la CJ: queda guardado con el volumen final.
4. Que la barra no frene la lectura (medir el tiempo de `leer` antes y después).
