{
    'name': "Package Consume",
    'version': '1.0.1',
    # Historial (tuctuc):
    # v1.0.1 (24/11/2026): index=True en stock.move.consume_package_id (busqueda por paquete sin recorrer stock_move).
    'category': 'Operations/Inventory',
    'sequence': 20,
    'summary': """create material moves for product packaging.""",
    'description': """create material moves for product packaging.""",
    'license': 'OPL-1',
    'author': "Dream Mountain Services",
    'website': "https://DreamMtn.Services",
    'support': 'support@DreamMtn.Services',
    'depends': ['stock', 'delivery'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_packaging_views.xml',
        'views/stock_quant_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
