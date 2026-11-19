# Logística KOROSHI · decisiones y dudas para el jefe (19/11/2026)

Excel: `bin/versiones/261119_MASTER_OI_26-27_KOROSHI_v8.xlsx` (datos de Odoo del 27/10/2026).

## Lo que ya está

- **Matriz artículos**: una fila por modelo con uds a preparar, % implantado, litros/ud, gramos/ud,
  densidad, uds por caja de 93 L (por volumen o por peso, la que llegue antes) y litros del lote.
- **Clasificación ABC**: rotación (A = los que suman el 80 % de las uds a preparar) × tamaño (uds que caben
  en una caja grande). Cada celda es una zona candidata del layout, con una propuesta de ubicación.
- **Recepción vs compra**: separa lo que está pendiente o en camino de lo que falta de verdad.

| m³ del lote | Pequeño | Mediano | Grande | Total |
|---|---|---|---|---|
| A (80 % de las uds) | 100 | 679 | **1.043** | 1.822 |
| B | 36 | 91 | 239 | 365 |
| C | 11 | 122 | 193 | 326 |
| Sin salidas aún | 2 | 80 | 297 | 379 |

## Decisiones que necesito

1. **A-Grande** (más de 1.000 m³, lo que más se mueve y caben menos de 15 por caja): ¿jaula o palet con
   ruedas a nivel 0, o reserva en alto y bajar por columnas?
2. **Cortes de la matriz**: A = 80 %, B = 95 %; Grande si caben menos de 15 por caja, Pequeño si más de 40.
   ¿Te valen?
3. **Peso máximo por caja: ¿17 o 18 kg?** En 148 modelos el límite de la caja lo pone el peso, no el volumen.
4. **Las propuestas de ubicación por celda** (hoja «Clasificación ABC», amarillo): ¿cuáles cambiarías?

Dato de contexto: para llegar al 80 % de las uds hacen falta 250 de 427 modelos con salidas. La rotación está
muy repartida, así que una «zona caliente» pequeña no recogería casi nada.

## Recibido vs comprado: qué hay que preguntar

Los negativos de «Recibido − comprado» son casi todos mercancía que aún no ha llegado (18 modelos de la
temporada 27 en camino y 42 recepciones a medias). Lo que sí hay que preguntar:

**Falta de verdad**
- **2621JA67** (chaqueta hombre): comprado 2.846, recibido 1.425, pendiente 1. **Faltan 1.420 sin explicar.**

**Temporada 26 sin recibir nada (pendiente en Odoo): ¿han llegado y no se han recepcionado, o vienen tarde?**
- 2622TP07 (1.066), 2621SU60 (634), 2621PL50 (590), 2622TP09 (555)

**Ni recibido ni pendiente en Odoo: ¿anulado, otro código o no existe en Odoo?**
- 2621PT15 (1.506), 2621ZC01 (1.000), 2621PT41 (985), 2711JA71 (706)
- 2622JA13 (1.239): tiene 442 en stock y 794 servidas, así que en Odoo debe de estar con otro código.

**Sobran mucho (probable error del packing list)**
- 2621JA50: PL 663, recibido 6.363. 2621CL04: PL 806, recibido 1.534. 2622BL15: PL 624, recibido 644.

**Pendiente en Odoo mayor que lo comprado (20 modelos)**: ¿pedido duplicado, segundo envío o recepciones
abiertas que sobran? Los más claros: 2711JA09 (pendiente 2.576 para 1.800 comprados),
2711JA11 (1.657 / 801) y 2711TR34 (1.330 / 665).

## Datos que faltan

| Dato | Para qué | Cómo |
|---|---|---|
| Uds por talla de cada modelo | Repartir columnas por talla | Script de solo lectura `odoo/KOROSHI_exportar_tallas_MASTER_DIAGNOSTICO_2026-11-19.py` (lo lanzo yo) |
| Fecha prevista de llegada | Separar «en camino» de «debería haber llegado» | Sale del mismo script |
| Recuento de estanterías y columnas por lineal | Saber cuánto espacio hay | Fotos (las tengo, pendientes de pasar) |
| Litros de la caja pequeña | Caja grande o pequeña por modelo | ¿Medidas? |
| Un pedido tipo | Comparar layouts por segundos por unidad | Uno real y representativo |
