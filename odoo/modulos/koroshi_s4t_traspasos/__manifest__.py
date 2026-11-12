# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Traspasos S4T (devoluciones y correcciones)',
    'summary': 'Descarga de S4T las devoluciones e-commerce y las correcciones de traspasos y las guarda en Odoo',
    'description': """
Lee de la API B2B de S4T (solo GET):
- /transfers/return-ecommerce: devoluciones de la tienda online a 6665 (DevoEcom).
- /transfers/corrections: correcciones de los traspasos de reposicion diaria de 6665 a las tiendas (+/-).

Cada traspaso se GUARDA primero en Odoo (con su JSON tal cual) y despues se procesa. Asi no se pierde nada aunque
S4T lo marque como descargado la primera vez que lo devuelve.
- Devolucion: crea una recepcion DEV de 6665 (Clientes -> DEVOLUCIO_KOROSHI) lista para validar (no la valida).
- Correccion: solo se registra (tienda, articulos, +/-). No mueve stock hasta saber con S4T que significa.

SE INSTALA CON EL CRON ARCHIVADO. Primera descarga: "Ejecutar manualmente" el cron y revisar.
Usa host y X-Api-Key de s4t.config (api_s4t_batch_update_PROD). No anade campos a tablas existentes.
v1.0 (12/11/2026).
""",
    'version': '13.0.1.0.0',
    'author': 'NATH',
    'category': 'Inventory',
    'license': 'LGPL-3',
    'depends': ['api_s4t_batch_update_PROD', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/datos.xml',
        'views/traspaso_views.xml',
        'wizard/recuperar_views.xml',
    ],
    'installable': True,
    'application': False,
}
