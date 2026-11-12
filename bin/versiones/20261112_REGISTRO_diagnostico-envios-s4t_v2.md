# Registro: diagnóstico de envíos a S4T v2 (12/11/2026)

Acción de servidor **1935**, «KOROSHI - Diagnostico envios S4T (shipments) v2 12/11 peso como XPO - NO ENVIA».
Código: `bin/KOROSHI_envios_s4t_shipments_2026-11-12_v2_peso-como-XPO_DIAGNOSTICO.py`. No envía nada.
La v1 (acción 1934) sigue en Odoo; ver `20261112_REGISTRO_diagnostico-envios-s4t_v1.md`.

## Qué peso mandan hoy los transportistas (código del servidor)

- **XPO** (`delivery_xpo`, EFFEC): `Peso = 15 + por cada OUT (shipping_weight si > 0, si no sus bultos)`.
  Como no hay pesos, sale **15 kg + 1 kg por caja**. Para el volumen suma el volumen de cada producto por sus
  unidades; si el producto no tiene volumen, cuenta 0,09 m3 por unidad.
- **GLS** (`delivery_gls_asm`, OCA): manda `peso = suma de shipping_weight`, que es **0**, y el volumen vacío.
  GLS no recibe nuestro peso.
- `koroshi_xpo_bultos` solo cambia el número de bultos, no el peso.

La v2 usa la regla de XPO para los dos transportistas, por tracking y pedido: `weight_kg = 15 + 1 x cajas distintas`.
El volumen es la suma del volumen de producto por las unidades hechas (0,09 m3/ud si el producto no lo tiene).

## Resultado (200 pedidos desde el 01/11, los más recientes primero)

- **184 pedidos listos, 185 POST.** Uno de ellos tiene dos trackings.
- 0 con problemas. 7 tienen OUT pendientes y 6 tienen alguna OUT sin etiqueta.
- 387 líneas usan los 0,09 m3/ud porque el producto no tiene volumen.

Ejemplos:

```
S-6665004194: XPO 121771219 | 3 bultos | 0.178 m3 | 18.0 kg | is_final=true | EFFEC/OUT/24919
S-6665004193: XPO 121771212 | 1 bultos | 0.245 m3 | 16.0 kg | is_final=true | EFFEC/OUT/24918
S-6665004192: GLS 1378191123 | 1 bultos | 0.030 m3 | 16.0 kg | is_final=true | EFFEC/OUT/24917
S-6665004191: XPO 121771235 | 1 bultos | 0.333 m3 | 16.0 kg | is_final=true | EFFEC/OUT/24916
```

## Puntos a decidir

- **Peso poco real:** 1 caja = 16 kg. Es lo que se declara a XPO, pero no es el peso real.
- **Volumen inflado** cuando faltan volúmenes de producto. Por ejemplo, 1 caja = 0,333 m3, cuando una caja plena son 0,084.
  Se podría limitar a `cajas x 0,084` como máximo.
- **Expedición compartida:** si una expedición XPO lleva varios pedidos, con esta regla cada pedido suma 15 kg de base.
