# Etiqueta de zona KOROSHI (OUT + matrícula) desde la interfaz de Odoo

Sustituye al «Picking Sticker» en el picking por zonas. Se hace todo desde Odoo, en **modo desarrollador**, sin tocar el módulo stock_ext (Brain Station 23). Son 3 registros nuevos y 1 acción.

## 1. Formato de papel
Ajustes › Técnico › Informes › **Formatos de papel** › Crear:
- Nombre: `KOROSHI 4x6 (101,6 x 152,4)`
- Tamaño: **Personalizado** · Alto **152** mm · Ancho **102** mm · Orientación **Vertical**
- Márgenes: superior **3**, inferior **0**, izquierdo **3**, derecho **3** · Espacio de cabecera **0** · DPI **96**

## 2. Vista QWeb (la plantilla)
Ajustes › Técnico › Interfaz de usuario › **Vistas** › Crear:
- Nombre de la vista: `koroshi_report_etiqueta_zona`
- Tipo de vista: **QWeb**
- **Clave (Key)**: `koroshi.report_etiqueta_zona` ← tiene que ser exactamente esto
- Arquitectura: pegar el contenido de `KOROSHI_report_etiqueta_zona.xml`

## 3. Informe
Ajustes › Técnico › Acciones › **Informes** › Crear:
- Nombre: `KOROSHI Etiqueta zona`
- Modelo: `stock.picking`
- Tipo: **PDF**
- Nombre de la plantilla: `koroshi.report_etiqueta_zona`
- Formato de papel: `KOROSHI 4x6 (101,6 x 152,4)`
- Nombre del archivo impreso: `'Etiquetas zona - %s' % (object.name)`
- **NO** añadirlo al menú Imprimir (21/10/2026 se quitó): desde Imprimir la etiqueta sale sin matrícula CJ. Se imprime siempre desde Acción › KOROSHI Etiquetas zona, que reserva la CJ (y reimprime con la misma si ya la tiene).

## 4. Acción de servidor
Ajustes › Técnico › Acciones › **Acciones de servidor** › Crear:
- Nombre: `KOROSHI Etiquetas zona`
- Modelo: `stock.picking` · Acción a realizar: **Ejecutar código Python**
- Código: `KOROSHI_etiquetas_zona.py`, primero con `MODO = 'DIAGNOSTICO'`
- Botón **«Crear acción contextual»**: así sale en el menú Acción de la lista de albaranes.

## 5. Uso cada día
1. Inventario › Transferencias › filtro por la agrupación (`Z-ddmm-D3`…) › seleccionar todas sus OUT.
2. Acción › **KOROSHI Etiquetas zona**.
3. Con `MODO = 'DIAGNOSTICO'` sale un aviso con cuántas etiquetas y qué matrículas usaría, sin gastar ninguna. Con `MODO = 'REAL'` reserva las CJ que falten (una por caja prevista por volumen) y abre el PDF con las etiquetas en orden de número de caja de tienda.
4. Si se vuelve a lanzar sobre las mismas OUT, **reutiliza** sus matrículas: no gasta nuevas.

## Pendiente
- **Delegación:** Odoo no tiene ese dato. La etiqueta pone de momento la **provincia** de la tienda. Cuando tengamos la lista de delegaciones, se añade un campo a la tienda (contacto) y se cambia una línea de la plantilla.
- **Impresora:** la etiqueta es de 4x6" (la de la Zebra de la U). El «Picking Sticker» actual es de 120x70 mm. Si en las zonas se imprime en la impresora de 120x70, hay que adaptar el diseño a ese tamaño.
- **Etiqueta de bulto agrupado** (varias CJ en un bulto): siguiente paso, cuando esta funcione.
- **Etiqueta XPO por caja:** no se hace al sacar las OUT. El módulo XPO crea un envío real por tienda con el número final de bultos; se sigue generando al final, por tienda.
