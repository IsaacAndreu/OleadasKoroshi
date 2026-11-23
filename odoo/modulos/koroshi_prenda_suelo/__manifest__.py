# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Prenda en el suelo',
    'summary': 'PDA: se lee una prenda encontrada en el suelo y dice a dónde va: faltante, compañero que la está '
               'preparando (dónde está y hacia dónde va), su hueco o la mesa de los jefes.',
    'description': """
Prenda en el suelo (KOROSHI, Effective Logistics).
Diseño: bin/versiones/diseno-prenda-en-el-suelo_2026-11-20.md (visto bueno de Isaac el 23/11/2026).

Lo pidió Isaac el 20/11: un botón para cuando se encuentra una prenda en el suelo que diga a dónde va, sabiendo más
o menos dónde está la gente por el lineal en que están o al que van, para que la cojan y la metan en su caja.

En la PDA (app «Prenda en el suelo»): se lee la prenda (y, si se quiere, el hueco que se tiene delante). La PDA da
una sola orden, la primera que se cumple:

A. Es un faltante pendiente (koroshi_faltantes): «Encontrada» la devuelve de FALTANTE a su hueco (lo mismo que el
asistente de la oficina; solo faltantes de 1 ud y fuera de una ronda abierta). Después dice a quién o a dónde.

B. La pide una OUT que alguien está haciendo ahora en Lecturas: a quién dársela, en qué hueco estaba su última
lectura, hacia qué hueco va y a cuántos metros (la ruta de koroshi_preparacion). La lee él en Lecturas.

C. La pide una OUT que no está haciendo nadie: a su hueco reservado.

D. No la pide nadie: al hueco donde Odoo tiene stock de esa prenda, el más cercano.

E. Odoo no la tiene en ningún hueco: al sitio del parámetro koroshi_prenda_suelo.sitio_sin_hueco (la mesa de los
jefes).

Nunca dice «métela en la caja X»: meterla sin leerla descuadra la caja.

Cada búsqueda queda apuntada (koroshi.prenda.suelo) con quién la encontró, dónde, qué dijo la PDA y si sirvió. En la
oficina: KOROSHI Operarios > Prendas del suelo.

Solo lee, menos su tabla y el «Encontrada» del caso A. No añade campos a tablas de Odoo.

v1.0.0 (23/11/2026): primera versión (fase 1 del diseño). Entra por su propio icono, no por el Inicio PDA: una
actividad del Inicio abre un tramo de tiempo y cortaría el de Picking. El botón en Lecturas es la fase 2. La regla del
lineal no pasa a koroshi_base todavía (actualizar koroshi_base arrastra a todos los módulos que dependen de él): se usa
la de koroshi_faltantes (nombre_corto) y la ruta de koroshi_preparacion (metros).
""",
    'version': '13.0.1.0.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'stock', 'hr', 'barcodes', 'koroshi_base', 'koroshi_operarios', 'koroshi_preparacion',
                'koroshi_faltantes'],
    'data': [
        'security/ir.model.access.csv',
        'data/parametros.xml',
        'views/assets.xml',
        'views/prenda_views.xml',
        'views/menu.xml',
    ],
    'qweb': ['static/src/xml/prenda_suelo.xml'],
    'installable': True,
    'application': False,
}
