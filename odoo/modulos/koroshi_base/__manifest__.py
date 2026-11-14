# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Base',
    'summary': 'Constantes y utilidades comunes de los modulos KOROSHI (compania, hora del almacen, matricula CJ)',
    'description': """
Lo que se repetia en los modulos KOROSHI (auditoria 13/11, fase 6), en un solo sitio:
- comun.py (Python puro, con tests sin Odoo en tests/):
  COMPANY_ID (8), TZ (Europe/Madrid), RE_CJ y es_matricula(codigo), ahora_local(), hoy_local(),
  inicio_dia_utc(dia), rango_dia_utc(dia), rango_dias_utc(desde, hasta), a_local(dt), dia_local(dt).
  rango_dia_utc tiene en cuenta el cambio de hora (dias de 23 y 25 horas).
- static/src/js/comun.js: odoo.define('koroshi_base.comun') con esMatricula(codigo) para las pantallas.
Sin modelos, sin datos y sin tablas: instalarlo no cambia nada. Los modulos pasan a usarlo uno a uno, cada uno con
su version (el primero, koroshi_zonas 1.4.0).

v1.0.0 (14/11/2026): primera version (auditoria 13/11, fase 6).
""",
    'version': '13.0.1.0.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['base', 'web'],
    'data': [
        'views/assets.xml',
    ],
    'installable': True,
    'application': False,
}
