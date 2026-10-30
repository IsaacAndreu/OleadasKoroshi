# Reunión KOROSHI · volúmenes, picking y datos (27/10/2026)

Resumen de la reunión (audio de unas 2 h 30 min) y de las notas de WhatsApp del 26-27/10. Si las notas y el audio no coinciden, manda lo dicho en el audio.

Datos de referencia: Excel **Volúmenes por artículo I27/V27** (109 packing lists, 591 líneas de artículo), marca KOROSHI, Odoo nath.tuctuc.com.

---

## 1. Cómo llamamos a cada forma de preparar

| Nombre | Qué es |
|---|---|
| **Picking B2B por pedido** | Antes «tradicional». Una persona prepara el pedido de la tienda de principio a fin (1 OUT por pedido). |
| **Picking B2B por zonas** | El pedido se parte en varias OUT, una por zona (de un lineal a otro). Cada persona hace solo su zona y en expedición se junta todo en un palet por tienda. |
| **Picking B2B por oleada** | Se coge por artículo para varios pedidos y luego se reparte por tienda. |
| **Picking B2C por oleada** | Lo de siempre para web. Hay que definir cuántas uds y cuántas líneas lleva cada oleada. |

**Conclusión de las pruebas:** partir por zonas da más **capacidad** (más gente trabajando a la vez, «sprint»), pero **la productividad no ha mejorado** en ningún momento. Compactar ubicaciones ganaría solo un **5-10 %** de tiempo: sigue siendo muy lento para 10.000 uds/día.

## 2. Indicadores de tiempo (notas WhatsApp)

- **Tiempo de servicio:** desde que el cliente pide hasta que sale.
- **Tiempo de productividad:** desde que arranca la OUT hasta que se acaba.
- El dato de 10,5 h de mediana (del pedido a validar la OUT, 21-23/10) cuenta desde que el pedido entra en Odoo a la 1:30. **Hay que calcularlo desde que se empieza la OUT.**
- Por fase (picking, packing/U, expedición). Picking ya medido: unos 48 s/ud (10 s andando, 38 s en la ubicación).

## 3. Códigos y familias

- Código de artículo: **26** = temporada (invierno 27) · **21** = hombre invierno, **22** = mujer invierno · **SU** = familia (sudaderas) · **01** = número de serie. Ej.: 2622SU01.
- La columna «Familia» del Excel es en realidad la **subfamilia** (35 distintas). Las familias grandes (chaquetas, pantalones…) agruparían 4-5 de estas. El proveedor lo hace al revés: la subfamilia es lo grueso y la familia el detalle. **Hay que filtrar primero por subfamilia y luego mirar lo que lleva dentro.**
- El cliente quiere que se agrupe y llegue por **modelo-color** (sin mezclar tallas de un mismo modelo-color). Trabajar siempre por modelo-color: si se agrupa solo por modelo, puede pasar que un color se venda y otro no.

## 4. Volumen: litros y m³

- **Litros (L/ud)** = volumen de **una unidad**. Es la unidad de referencia para el artículo individual.
- **m³** = cuando hay más de una unidad (cajas, partidas, totales).
- Conversión: **1 m³ = 1.000 L** → L/ud = CBM/ud × 1.000. Una caja de 60×40×40 = **96 L**.
- Las fórmulas del Excel tenían errores de escala (×1.000 / ×1.000.000): hay que **recalcular desde los datos de origen** (packing list). «Primero los cimientos sólidos.»
- Hay que añadir una **columna con los litros por unidad**.

## 5. Peso: siempre neto

- El peso del Excel es lo que pone el packing list (lo que declara el proveedor). **Se trabaja con el peso neto, no con el bruto.**
- **Pedir al proveedor que incluya una columna de peso neto** (net weight y gross weight).
- **Comprobarlo**: pesar 2 o 3 cajas al azar de las primeras que se encuentren.
- Mientras no haya neto: estimar el **cartón vacío en 1,2 kg** (ej. real: bruto 1.380 g, neto 1.260 g). **Peso neto = peso bruto − (nº cartones × 1,2)**. Peso neto por unidad = peso neto ÷ unidades.
- Mostrar con **3 decimales**.
- Notas WhatsApp: el real se puede sacar al ubicar, pesando una caja con carro y báscula. Teórico (P/L) frente a real: esa desviación es la buena y va formando la «memoria» del algoritmo.

## 6. Densidad (peso volumétrico)

- **Densidad = kg/m³** (lo mismo que gramos por litro). Ej.: una camiseta da unos 159 kg/m³. Nos acostumbramos a llamarla **densidad**, aunque el concepto de transporte sea el mínimo de kilos por m³ que te cobran.
- Sirve porque volumen y peso van relacionados: hay artículos con mucho volumen y poco peso, y al revés. No cuesta nada arrastrar el dato.
- **Aire al expedir** (la prenda se descomprime al sacarla del cartón del proveedor), para empezar:
  - densidad **menor de 120 kg/m³** → **+15 a +20 %** de volumen;
  - densidad **mayor de 200 kg/m³** → **+10 %**.
- El 17 % de aire que salía «chirría»: si el volumen sale del packing list, es lógico que haya descompresión. Hay que analizarlo.

## 7. Formato del Excel

- Cabeceras claras, que cualquiera entienda qué hay en cada columna, y en el orden en que se consultan.
- Sin anchos innecesarios.
- Orden pedido: **después de la columna C (subfamilia) → densidad (kg/m³) → volumen total (CBM)**.
- Insertar 3-4 filas arriba y poner los **totales en la fila 6**: suma hasta el **último registro** (no hasta una fila fija). Columnas de texto (género, familia, temporada) sin fórmula.
- Medias **ponderadas** (peso total ÷ unidades totales), no promedios de líneas.
- **Limpiar los datos**: hay líneas con ceros (unos 60-70 artículos, ~12 %). Sin datos limpios no se puede sacar conclusiones.

## 8. Concentración del volumen (ABC)

Ordenado por CBM total de mayor a menor:
- **244 artículos (~40 %) = 84 % del volumen** total (2.721 m³). Los otros ~370 artículos solo ocupan el 16 %.
- **67 artículos = 50 % del volumen**; 9 artículos de más de 30 m³; 18 artículos (filas 8-25) ya consumen mucho volumen cada uno.
- Esos artículos grandes tienen que ir **arriba (estantería alta)** y seguramente a **doble pasillo / doble línea**.
- Dentro de cada rango de volumen, ordenar por **unidades** (ABC por rotación).
- Con la velocidad del operario andando y el impacto del volumen unitario en viajes y cajas, el layout sale por matemáticas; luego se afina a mano.

## 9. Palets necesarios

- Palet 1,20 × 0,80 × 1,60 m de media (4 alturas de unos 40 cm) = **1,54 m³**.
- **Nº de palets = CBM total ÷ 1,54, redondeando siempre hacia arriba.** Total arriba, como suma simple.
- Debate abierto: palet entero por artículo (monorreferencia), y si en las dos caras de un lineal puede ir el mismo artículo. Depende del espacio y de separar recorridos de picking y de reposición: hay que simularlo.
- Reposición: es sencilla y rápida (cuando hay hueco abajo, se baja de arriba), la pueden hacer 2-4 personas sin pensar.

## 10. Implantación, reposición y foto actual

- **% de implantación por modelo** (cantidad y %): es un dato **histórico** que se irá acumulando para prever la temporada siguiente. Pregunta clave: de todos los m³ de la temporada, **cuántos van a implantación**.
- **Regla:** todo lo que salga en los **5 días siguientes** a que nos pasen el pedido cuenta como **implantación**; el resto, **reposición**. **Implantación + reposición = salidas totales.**
- **Eficacia del modelo:** el ranking de ventas lo estimamos por el ranking de compras; con la campaña a la mitad, ya se puede medir lo que sale de verdad.
- **Pendiente de servir** = comprado − salidas (lo que queda en almacén).
- **Foto de hoy:** unas **300.000 uds** de invierno 27 salidas desde julio (≈55-57 % de las unidades); queda aproximadamente el **50 % del volumen**.
- **Decisión a tomar:** qué esfuerzo supone, con lo que queda de campaña, **compactar y pasar unos 60 artículos a estantería alta** (o abrir pasillos con esa medida), y qué ventaja daría.

## 11. Medir

- Hay que medir **picking y expedición**.
- **Un usuario por PDA:** **24,90 €/usuario/mes**, pero con **compromiso anual** (el pago es mensual, el contrato es de un año). Andrés ya intentó licencias mensuales y le dijeron que no, porque el contrato es anual. Comprobar si se puede subir y bajar licencias cada mes; si no, plantearlo al **renovar** (los 4 meses fuertes concentran casi todo).
- **Geolocalización dentro de la nave:** con GPS, wifi y móvil no es exacto (techo, palets, columnas). Haría falta balizas Bluetooth o repetidores. **Pendiente el coste** (lo responde David). Con eso y el monitor se sabría dónde está cada persona y cuánto anda. Dato orientativo: unos 16 min/km mezclando andar y leer.
- **Tiempos no productivos:** horas totales de todas las personas ÷ lo que se mide (por documentos de facturación). Hacerlo mensual. Si no, la única solución es sobredimensionar.

## 12. Notas WhatsApp que no salen en el audio

- **Palet contenedor:** al montar el palet (retractilado) tiene que quedar trazado qué cajas leídas lleva (palet → cajas).
- **Nombre del Excel:** **MASTER OI 26/27**.
- **Otra pestaña** con: eficacia; implantación inicial / reposición / stock (los tres en % y en uds); **TEUs** (para dimensionar las recepciones recibidas y pendientes, por modelo); fecha de recepción, fecha de implantación y días entre ambas. Títulos e indicadores afinados y **color de la celda según el valor**.

---

## Pendientes

1. Pedir al proveedor la columna de **peso neto** en el packing list y comprobar pesando 2-3 cajas.
2. Recalcular **litros/ud** desde los datos de origen y limpiar las líneas a cero.
3. Montar el **MASTER OI 26/27** con las columnas y la pestaña de implantación/reposición/stock.
4. Calcular el **esfuerzo de compactar y subir ~60 artículos** a estantería alta.
5. Mirar el **contrato de Odoo** (licencias mensuales) y el **coste de geolocalización** (David).
6. Medir los tiempos de servicio y productividad **desde el inicio de la OUT**.
