# Koroshi Zebra

Módulo Odoo compatible con **Odoo 13** (sintaxis de vistas `attrs`) para
generar e imprimir etiquetas secuenciales tipo
`CJ665000001`, con barcode Code128, tamaño de etiqueta 150 x 110 mm.

## Instalación

1. Copia la carpeta `koroshi_zebra` dentro de tu carpeta de addons.
2. Reinicia el servidor Odoo y actualiza la lista de apps
   (Ajustes > Activar modo desarrollador > Apps > Actualizar lista de apps).
3. Busca "Koroshi Zebra" e instala el módulo.

## Uso

1. Ve al menú **Koroshi Zebra > Imprimir Etiquetas**.
2. Indica la **cantidad** de etiquetas a generar (ej: 50) y opcionalmente
   una nota/lote.
3. Pulsa **Generar e Imprimir**: se crearán N registros correlativos
   empezando por el próximo número de la secuencia (por defecto
   `CJ665000001`, luego `CJ665000002`, `CJ665000003`...) y se abrirá
   el PDF con una etiqueta por página, lista para imprimir.
4. También puedes reimprimir etiquetas ya creadas desde
   **Koroshi Zebra > Historial de Etiquetas**.

## Ajustar el punto de partida / formato de la secuencia

Ve a Ajustes > Técnico > Secuencias y Códigos > Secuencias, busca
"Secuencia Etiquetas Zebra (CJ)" (código `zebra.label.code`) y edita:

- **Prefijo**: `CJ`
- **Próximo número**: `665000001` (o el que corresponda)
- **Relleno con ceros**: `9`

## Impresión en impresora Zebra

El reporte se genera como PDF con el tamaño de página exacto de la
etiqueta (150 x 110 mm, orientación horizontal, márgenes de 2 mm),
usando el generador de barcode Code128 nativo de Odoo
(`/report/barcode/?type=Code128&value=...`), sin dependencias externas.

Para imprimir en la Zebra tienes dos caminos habituales:

1. **Como impresora normal (recomendado, más simple):** instala el
   driver de Windows/Mac de la Zebra (modo "página completa" / "label"
   con el tamaño de página 150x110mm configurado en el driver), y
   simplemente imprime el PDF que genera Odoo como imprimirías
   cualquier documento. Como la página del PDF ya mide exactamente
   150x110mm, no hace falta "encajar a la página": actívalo al 100%
   / "tamaño real", sin escalar.
2. **Impresión directa por red/ZPL:** si prefieres mandar ZPL crudo al
   puerto 9100 de la impresora en vez de un PDF, dímelo y te agrego un
   botón adicional que genere el ZPL (con el `^BC` para Code128) y lo
   envíe directo a la IP de la impresora vía socket, sin pasar por el
   diálogo de impresión de Windows.

## Ajustar tamaños de texto / barcode

Todo el diseño está en
`report/label_report_templates.xml` (bloque `<style>`), en unidades
`pt` para los textos y `mm` para la caja del barcode — puedes tocar
`font-size` y `max-height` ahí para afinar el parecido con tu etiqueta
original.
