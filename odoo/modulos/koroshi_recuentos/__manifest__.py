# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Recuentos (comprobar el inventario por referencia)',
    'summary': 'PDA: una referencia con todas sus tallas y colores, dónde está y cuánto dice Odoo. Después, '
               'recuentos leídos que corrigen el stock (inventario dinámico).',
    'description': """
Comprobar el inventario por referencia en la PDA (KOROSHI, Effective Logistics).
Diseño: bin/versiones/diseno-comprobar-inventario_2026-11-20_v3.md (aprobado por Isaac el 20/11/2026).

Fase 1 (esta versión), SOLO LECTURA: pantalla «Referencia» (app «Referencia» e Inventario > KOROSHI Operarios >
Recuentos > Referencia).
- Se lee una prenda (EAN) o se escribe la referencia (2621XC04) o una variante (2621XC04-000014-42). Un trozo
  (2621XC) da la lista de referencias que empiezan así.
- Arriba, tabla color x talla con lo que dice Odoo de cada variante (reservado entre paréntesis, negativo en rojo).
- Debajo, todos los sitios (hueco y contenedor KO_/TT_) en orden de recorrido (L por número, P y C; luego MU; luego
  el resto, como FALTANTE), con lo que dice Odoo de cada variante. Marcas: «negativo», «varios colores».
- En naranja, los sitios donde se quitó stock de la referencia a pérdidas de inventario en los últimos 90 días
  («Cantidad de producto actualizada», Contenedores, Faltante no encontrado...), con cuántas, cuándo, qué y quién.
  Si Odoo ya no tiene nada allí, sale igual con «Odoo 0: mirar»: es donde puede estar lo que falta.
- Tocar un sitio enseña todo lo que Odoo dice que hay en él (en negrita, lo de la referencia).
- Solo ubicaciones internas de la compañía 8. No crea, no escribe y no mueve nada; no pide tarjeta.
Fases siguientes (sin hacer): recuento leído a ciegas con segunda lectura, que se aplica solo y deja registro de cada
lectura; acta en Excel; lista «Para contar hoy».

Sin tablas propias en esta versión. No añade campos a tablas de Odoo.

v1.0.0 (20/11/2026): primera versión, fase 1: pantalla «Referencia» de solo lectura (lo pide Isaac el 20/11: cuando
  KOROSHI dice «la prenda X no está», ver de una vez todas sus tallas, colores y sitios, y dónde se quitó a mano).
""",
    'version': '13.0.1.0.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'stock', 'barcodes', 'koroshi_base', 'koroshi_operarios'],
    'data': [
        'views/assets.xml',
        'views/views.xml',
        'views/menu.xml',
    ],
    'qweb': ['static/src/xml/referencia.xml'],
    'installable': True,
    'application': False,
}
