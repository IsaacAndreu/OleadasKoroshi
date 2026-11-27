# -*- coding: utf-8 -*-
{
    'name': 'TUCTUC Lecturas PDA como app',
    'summary': 'Instala Lecturas (PDA) de la nave de Oriola como una app: icono en la PDA y pantalla sin barra',
    'description': """
TUCTUC Lecturas PDA como app (odoo.tuctuc.com). Clon de koroshi_pda_app 1.2.0 (decisión de Isaac del 27/11/2026).

Con este módulo, Chrome deja instalar Odoo como una app («Lecturas Oriola»): en la PDA, menú ⋮ → «Instalar
aplicación». Sale un icono en la pantalla de inicio que abre directamente Lecturas (PDA), sin barra de direcciones.

- /tuctuc_pda/inicio: con sesión abre Lecturas con las compañías de la PDA que tenga el usuario (PRIME, MODA INTIMA,
  UNITED; de tuctuc.almacen); sin sesión, el login de Odoo y, al entrar, Lecturas.
- /tuctuc_pda/manifest.webmanifest y /tuctuc_pda/sw.js (service worker vacío, solo en Android).

Solo para los usuarios del parámetro tuctuc_pda_app.usuarios (ids separados por comas, * = todos). Al instalar está
vacío: se pone a mano el usuario de prueba. No escribe nada en la base de datos (solo crea el parámetro al instalar).

v1.0.0 (27/11/2026): primera versión, clon de koroshi_pda_app 1.2.0 sin compañía fija ni Inicio por áreas.
""",
    'version': '13.0.1.0.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'tuctuc_base', 'tuctuc_operarios'],
    'data': [
        'data/parametros.xml',
        'views/layout.xml',
    ],
    'installable': True,
    'application': False,
}
