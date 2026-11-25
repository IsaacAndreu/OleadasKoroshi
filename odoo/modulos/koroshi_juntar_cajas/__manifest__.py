# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Juntar cajas',
    'summary': 'PDA (área Expediciones): meter una caja pequeña (CJ) dentro de otra del mismo pedido y tienda, para '
               'que salga un bulto menos. La misma lógica que la acción 1844 «Juntar matrículas».',
    'description': """
Juntar cajas (KOROSHI, Effective Logistics).
Diseño: bin/versiones/diseno-juntar-cajas-pda_2026-11-25.md (visto bueno de Isaac el 25/11/2026, con J1-J4 como se
proponían: cualquiera con tarjeta; con etiqueta del transportista deja pero avisa; cualquier caja, avisando si la
«pequeña» es más grande; no imprime nada).

En la PDA, área Expediciones, botón «Juntar cajas»:
1. Tarjeta del operario (la misma de las otras pantallas).
2. Leer la CJ pequeña (se pueden leer varias).
3. Leer la CJ destino: enseña pedido, tienda, uds y «Bultos del pedido: N -> N-1», con los errores y avisos.
4. «Juntar»: mueve las líneas (y el stock) a la caja destino, todo o nada, y recalcula los bultos de las OUT.

Lo que mueve es lo mismo que la acción de servidor 1844 v5 (que sigue igual para el PC). Además no deja si el pedido
está SHIPPED en S4T, si alguna OUT va en un camión cerrado (koroshi.envio.cierre) o si es de Zalando. Si ya hay
etiqueta del transportista avisa en rojo y deja una nota en el pedido (koroshi_s4t_envios pone el envío en
«corregir»).

Cada junta queda en koroshi.juntar.registro (KOROSHI Operarios > Cajas juntadas) con quién, cuándo, las dos CJ, los
bultos antes y después y los ids de líneas y quants movidos, para deshacer en la oficina. No añade campos a tablas de
Odoo.

v1.0.0 (25/11/2026): primera versión. Lógica en logica.py con tests sin Odoo. Necesita koroshi_base 1.2.1 (comun.js y
pda.py) y koroshi_actividades con áreas (1.6.0 o más).
""",
    'version': '13.0.1.0.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'stock', 'hr', 'barcodes', 'sale_stock', 'koroshi_base', 'koroshi_operarios',
                'koroshi_actividades'],
    'data': [
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/juntar_views.xml',
        'views/menu.xml',
        'data/actividad.xml',
    ],
    'qweb': ['static/src/xml/juntar_cajas.xml'],
    'installable': True,
    'application': False,
}
