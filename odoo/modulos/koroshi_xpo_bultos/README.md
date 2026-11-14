# KOROSHI XPO bultos (v1.2, 14/11/2026)

En cada expedición XPO de EFFEC (empresa 8) se mandan a XPO:

| Dato XPO | Valor |
|---|---|
| `TotalUnidadesManipulacion` (bultos) | cajas **distintas** de todas las OUT de la expedición |
| `Peso`, `PesoNeto`, `PesoBruto` | **15 kg × bultos** |
| `VolumenNeto`, `VolumenOperacional` | **0,09 m3 × bultos** |


## v1.2 (14/11/2026, auditoría 13/11, fase 3)

- `bultos_de(pickings)` y `valores_xpo(bultos)` son **la** cuenta de bultos, peso y volumen de KOROSHI: cajas
  distintas de las líneas con algo leído; 15 kg y 0,09 m³ por bulto. La usan la expedición XPO y koroshi_s4t_envios
  (antes contaban las cajas cada uno a su manera).

## v1.1 (12/11/2026): peso y volumen por bulto

- XPO factura con **15 kg y 0,09 m3 por bulto**. Su tabla del 30/10 lo muestra: 5 bultos = 75 kg y 0,45 m3;
  4 bultos = 60 kg y 0,36 m3; 6 bultos = 90 kg y 0,54 m3.
  Avisaron de que «seguimos recibiendo mal los m3 y kgs integrados» y de que eso afecta a la facturación.
- `delivery_xpo` (EFFEC) mandaba:
  - peso = 15 + 1 kg por caja, porque en Odoo no hay ningún peso;
  - volumen = volumen de los productos × unidades, con **0,09 m3 por UNIDAD** si el producto no tiene volumen.

  Ejemplo: K80 30/10, expedición 121771010, 5 bultos → XPO recibió **5,63 m3 y 20 kg** en vez de 0,45 m3 y 75 kg.
- Ahora se cambian esos valores en la llamada `RegistraExpedicion`. Se deja una nota en la primera OUT:
  «XPO: declarados N bultos, X kg y Y m3».
- Las expediciones que ya están registradas no cambian. Las tiene que corregir XPO o hay que volver a generarlas.

## v1.0 (10/11/2026): cajas distintas

Una caja que está en más de una OUT de la misma expedición cuenta **una sola vez**.
- `package_ids` de una OUT son sus cajas destino. Con *KOROSHI Caja existente*, una OUT pequeña mete sus prendas en la
  caja de la OUT grande, y esa caja se sumaba dos veces.
  Caso K8 10/11/2026 (121771146): 16 cajas y XPO sacó 17 etiquetas.
- Con cajas compartidas, el mínimo de 3 bultos se mira con las cajas distintas, y se deja una nota en la primera OUT.

## Cómo funciona

No toca `delivery_xpo`. Envuelve el cliente zeep (`_xpo_es_get_client`) y cambia solo los argumentos de
`RegistraExpedicion`. La referencia, la etiqueta, el tracking y la cancelación funcionan igual.
Sigue funcionando mientras EFFEC mantenga esa llamada. No añade campos. Log: `KOROSHI XPO BULTOS`.

## Prueba

Ojo: generar la etiqueta registra la expedición en XPO de verdad.
1. Generar la etiqueta XPO de un envío real como siempre.
2. Comprobar la nota en la OUT: «XPO: declarados 5 bultos, 75.00 kg y 0.45 m3».
3. En la pantalla de XPO (como la de su captura): `INV Vol` 0,45 y `GRS Kgs` 75.

Si algo falla: volver a la v1.0 (copia en `copias_modulos`) o desinstalar el módulo. No deja datos propios.
