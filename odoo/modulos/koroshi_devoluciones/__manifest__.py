# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Devoluciones (ubicar devoluciones en la PDA)',
    'summary': 'Ubicar devoluciones sin Excel: opción de manipulación, prendas y contenedor; informe por día, semana '
               'o mes',
    'description': """
Fase 1 del diseño bin/versiones/diseno-devoluciones_2026-11-20.md (reunión del 20/11 con Cruz y Betty).

- Pantalla «Ubicar devoluciones» para la PDA (app «Devoluciones» e Inventario > KOROSHI Operarios > Devoluciones).
  Misma tarjeta de operario que Lecturas, Contenedores y Faltante.
- El operario elige qué ha hecho (Quitar precio / Quitar precio y embolsar / Reetiquetar y embolsar), lee prenda,
  prenda… y el contenedor KO_/TT_ o el hueco. Se guarda la tanda: quién, cuándo, qué opción, artículo y uds.
- Devoluciones de TIENDAS (el Excel de hoy). Stock (parámetro koroshi_devoluciones.stock = 'mover', por defecto): la
  prenda entra en el contenedor como ajuste de inventario, igual que la subida del Excel. No se toca DEVOLUCIO_KOROSHI
  (e-commerce, fase 2). Con 'apuntar' solo se apunta.
- Informe por día, semana o mes y por manipulación (pivote y gráfico). El código de factura (M1/M2/M3) se pone en
  Opciones de manipulación y solo sale en el informe.
- Un jefe (responsable de inventario) puede anular una tanda: el stock vuelve a donde estaba.

Solo escribe en sus tablas (koroshi.devolucion.ubicada y koroshi.devolucion.manipulacion) y crea movimientos de
stock hechos sin albarán. Sin campos en tablas de Odoo.

v1.0.0 (20/11/2026): primera versión. Quita el Excel de ubicar devoluciones (EAN + contenedor que se subía a
  Odoo): la PDA lee la opción, las prendas y el contenedor o hueco, mueve el stock y deja el informe para facturar.
v1.0.1 (20/11/2026): la pantalla es para las devoluciones de tiendas (Isaac, con un Excel de ejemplo: EAN +
  contenedor KO_). Todo entra como ajuste en el contenedor, como el Excel; ya no se coge antes lo libre de
  DEVOLUCIO_KOROSHI, que es de e-commerce (DEV de la API, fase 2): una prenda de tienda podía gastarse una unidad
  de una devolución web. El mensaje de «Guardado» ya no dice cuántas eran nuevas (lo son todas). Sin instalar la
  1.0.0, se instala directamente la 1.0.1.
""",
    'version': '13.0.1.0.1',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'stock', 'hr', 'barcodes', 'koroshi_base', 'koroshi_operarios'],
    'data': [
        'security/ir.model.access.csv',
        'data/datos.xml',
        'views/assets.xml',
        'views/views.xml',
        'views/menu.xml',
    ],
    'qweb': ['static/src/xml/devoluciones.xml'],
    'installable': True,
    'application': False,
}
