# Correo a S4T: equivalencias de talla para el maestro de etiquetas (borrador, 26/11/2026)

**Para:** Andrés Moya <a.moya@soft4tex.com>
**CC:** Evaldas Casas; Betty
**Asunto:** Maestro de artículos para etiquetar: equivalencias de talla EU/US/UK/IT
**Adjunto:** `20261126_tallas_equivalencias_para_S4T.csv`

---

Hola, Andrés:

Para no tener que pediros el maestro de artículos cada vez que reetiquetamos, a partir de ahora lo vamos a generar
nosotros a partir de vuestra API (`/products/by-season/{temporada}/csv`). Con ella sacamos el SKU, los EAN, la
referencia, el color y la talla.

Lo que no viene en la API son las equivalencias de talla que llevaba el maestro antiguo (TallaEU, TallaUS, TallaUK y
TallaIT; por ejemplo, 3XL = 58 / 3XL / 48 / 62). ¿Nos podéis pasar esas equivalencias para las temporadas I27 y V27?

Os adjuntamos una plantilla con todas las combinaciones de tipo de prenda y talla que hay en esas dos temporadas
(el tipo es la 5.ª y 6.ª letra de la referencia: JA, PS, CL…). Solo habría que rellenar las cuatro columnas de
talla. Si para vosotros es más fácil añadir esas columnas al CSV de la API, también nos sirve.

Dos dudas más:

1. ¿Las equivalencias dependen solo del tipo de prenda y la talla, o cambian según el modelo o el patrón? Si
   cambian, nos haría falta la tabla por referencia.
2. Algunos SKU traen dos EAN 8445 en la API (por ejemplo, 2621PT06-000003-S: 8445962859075 y 8445962870001; también
   2711JA01-000062 y 2711MC51/52). ¿Cuál es el que hay que imprimir en la etiqueta?

Muchas gracias.

Un saludo,
Isaac

---

## Notas internas (no van en el correo)

- La plantilla adjunta tiene 207 combinaciones tipo/talla, sacadas de `products_I27.csv` y `products_V27.csv`
  (descargados de la API en octubre). Si se descarga de nuevo V27 puede haber tipos o tallas nuevos: volver a sacar
  la plantilla antes de enviarla.
- Cuando S4T conteste, la tabla se pasa tal cual al script con `--tallas`:
  `python bin/KOROSHI_maestro_etiquetas_2026-11-26_v1.py --temporadas I27 V27 --tallas <tabla>.csv --salida <maestro>.csv`
  Si las equivalencias van por referencia, habrá que sacar una v2 del script.
- Mientras no lleguen las equivalencias, el maestro puede salir con las cuatro columnas de talla vacías.
