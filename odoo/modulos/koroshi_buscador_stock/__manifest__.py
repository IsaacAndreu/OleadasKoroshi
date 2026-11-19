# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Buscador de stock',
    'summary': 'Pantalla de la oficina para buscar stock por EAN, referencia, trozo, hueco, lineal o contenedor. '
               'Solo lectura.',
    'description': """
Buscador de stock para la oficina (KOROSHI > Almacén > Buscador de stock). SOLO LECTURA: no cambia nada.

Una sola caja de búsqueda. Lo escrito se entiende, por este orden, como:
- lineal (L94): sus huecos con contenedores y unidades;
- contenedor KO_/TT_ (nombre entero o un trozo): lo que tiene dentro;
- código de barras de un hueco: sus contenedores y sus prendas;
- EAN (con o sin 0 delante), código alternativo o referencia exacta: el modelo con todas sus tallas y colores;
- cualquier otra cosa (3 caracteres o más; varias palabras = todas): lista de modelos y contenedores que lo contienen.

De cada talla o color: stock, reservado, libre y entradas pendientes (recepciones abiertas hacia una ubicación
interna); dónde está (hueco y contenedor), qué albaranes la reservan y desde dónde, y qué recepciones la traen.
De cada hueco o contenedor: sus prendas con uds, reservadas y libres, y los albaranes que reservan desde ahí.

Solo stock de ubicaciones internas de la compañía 8. Lee con sudo, pero el menú y las rutas son solo para usuarios
de inventario. Sin modelos ni campos nuevos. No depende de koroshi_contenedores: las búsquedas de EAN y de contenedor
están copiadas de su 1.7.0 (se pasarán a koroshi_base en otra versión). Diseño:
bin/versiones/diseno-buscador-stock_2026-11-19.md

v1.0.0 (19/11/2026): primera versión (pedido de Isaac del 19/11: buscador de stock aparte para la oficina).
""",
    'version': '13.0.1.0.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'stock', 'product', 'koroshi_base', 'koroshi_menu'],
    'data': [
        'views/assets.xml',
        'views/menu.xml',
    ],
    'qweb': ['static/src/xml/buscador_stock.xml'],
    'installable': True,
    'application': False,
}
