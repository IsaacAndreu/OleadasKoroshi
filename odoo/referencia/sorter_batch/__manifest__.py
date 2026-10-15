# -*- coding: utf-8 -*-
{
    'name': 'Sorter Batch',
    'summary': "Create sorter batches from picking operations.",
    'author': "EFFECTIVE LOGISTICS SL",
    "website": "https://effectivelog.com/",
    'license': 'AGPL-3',
    'category': 'Inventory',
    'version': '13.0.0.3',
    'depends': [
        'base',
        'stock'
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sorter_batch_sequence.xml',
        'data/stock_picking_action.xml',
        'views/sorter_batch_view.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}
