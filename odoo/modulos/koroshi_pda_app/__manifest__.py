# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Lecturas PDA como app',
    'summary': 'Instala Lecturas (PDA) como una app: icono en la PDA y pantalla sin barra del navegador',
    'description': """
KOROSHI Lecturas PDA como app.

Con este módulo, Chrome deja instalar Odoo como una app («Lecturas KOROSHI»): en la PDA, menú ⋮ → «Instalar
aplicación» (o «Añadir a pantalla de inicio»). Sale un icono en la pantalla de inicio que abre directamente Lecturas
(PDA), sin barra de direcciones ni pestañas.

- /koroshi_pda/inicio: con sesión abre Lecturas; sin sesión, el login de Odoo y, al entrar, Lecturas.
- /koroshi_pda/manifest.webmanifest: nombre, icono, colores y pantalla de la app.
- /koroshi_pda/sw.js: service worker mínimo (sin caché; solo para que Chrome deje instalarla). Se registra solo en
  Android.

Solo para los usuarios del parámetro koroshi_pda_app.usuarios (ids separados por comas, * = todos). Al instalar: 2
(Departament IT), para probar antes de ponerlo en el usuario de las PDA. Al resto no les cambia nada.
No escribe nada en la base de datos (solo crea el parámetro al instalar). Para que, además, al entrar en Odoo salga
Lecturas: en el usuario, Preferencias → Acción inicial = «Operarios» (Lecturas PDA).

v1.0.0 (11/11/2026): primera versión.
v1.1.0 (16/11/2026): auditoría 13/11, fase 6 (pasar a koroshi_base). La empresa sale de koroshi_base.comun. Misma
app y mismas rutas; sin campos ni vistas nuevas. Depende de koroshi_base.
""",
    'version': '13.0.1.1.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'koroshi_base', 'koroshi_operarios'],
    'data': [
        'data/parametros.xml',
        'views/layout.xml',
    ],
    'installable': True,
    'application': False,
}
