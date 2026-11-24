# -*- coding: utf-8 -*-
{
    'name': 'Multi Search with comma separated',
    # Copia propia de tuctuc (odoo.tuctuc.com, nath/custom_addons). Historial:
    # v11.0.1 (24/11/2026): saber si el modulo esta instalado mirando el registro cargado en vez de lanzar
    #   una consulta a ir_module_module en cada busqueda de cualquier modelo (models/multi_search.py). Mismo resultado.
    'version': '11.0.1',
    'category' : 'General',
     'summary' : """ Records bulk search on any page/model.
    """,
    'description': """
                Search for records in bulks on any page/model easily.
    """,
    'author' : 'Murugan Chinnasamy',
    'website': 'www.cmstech.com',
    'license': "OPL-1",
    'complexity': 'easy',
    'depends': ['base'],
    'data': [
             ], 
'images': ['static/description/icon.png'],    
'installable': True,
    'application': True,

    
}


