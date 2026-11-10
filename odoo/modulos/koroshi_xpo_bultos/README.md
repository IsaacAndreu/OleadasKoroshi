# KOROSHI XPO bultos (v1.0, 10/11/2026)

Una caja que está en más de una OUT de la misma expedición XPO cuenta **una sola vez** en los bultos que se
mandan a XPO, y por lo tanto en las etiquetas.

## Qué pasaba

- `delivery_xpo` (EFFEC, `/opt/nath-erp/nath/custom_addons`) registra **una sola expedición** para todas las OUT
  del envío (mismo destinatario) y manda `TotalUnidadesManipulacion = suma de len(package_ids)` de cada OUT.
- `package_ids` de una OUT son las cajas destino de sus líneas. Con *KOROSHI Caja existente* una OUT pequeña mete
  sus prendas en la caja de la OUT grande: esa caja está en las dos OUT y se sumaba dos veces.
- K8 10/11/2026 (expedición 121771146): 16 cajas, la CJ665009950 en OUT/24116 y OUT/24181 → XPO 17 etiquetas.
  El `number_of_packages` de las OUT (16) no se usa para esto.

## Qué hace

- Antes de llamar a `delivery_xpo` cuenta las **cajas distintas** de todas las OUT de la expedición.
- Si es igual a la suma de siempre: no hace nada (llama a `delivery_xpo` tal cual).
- Si es distinto: cambia solo `TotalUnidadesManipulacion` en la llamada a XPO, mira el mínimo de 3 bultos con las
  cajas distintas y deja una nota en la primera OUT («XPO: 16 bultos ... contadas una vez: CJ...»).
- Peso, volumen, referencia, etiqueta, tracking y cancelación: igual que `delivery_xpo`.
- Solo OUT de EFFEC (empresa 8). No toca `delivery_xpo` (si EFFEC lo actualiza, sigue funcionando mientras
  mantenga `_xpo_es_get_client` y la llamada `RegistraExpedicion(..., TotalUnidadesManipulacion=...)`).
- No añade campos. Log: `KOROSHI XPO BULTOS`.

## Prueba (fuera de horas)

Ojo: generar la etiqueta registra la expedición en XPO de verdad. Hacerlo con un envío real que tenga una caja
compartida, o avisar a XPO y cancelar la expedición después (botón de cancelar envío en la OUT).

1. Envío con una OUT pequeña metida en la caja de la OUT grande (Caja existente v1.3), p. ej. 3 cajas en total.
2. Generar la etiqueta XPO como siempre.
3. El PDF tiene tantas páginas como cajas distintas (3, no 4). Nota «XPO: 3 bultos...» en la primera OUT.
4. Envío normal sin cajas compartidas: igual que antes y sin nota.

Si algo falla: desinstalar el módulo en Aplicaciones. No deja datos propios.
