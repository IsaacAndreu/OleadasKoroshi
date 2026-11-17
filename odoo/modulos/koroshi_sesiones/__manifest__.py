# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Sesiones sin caducar',
    'summary': 'Las sesiones con usuario no se borran nunca (Odoo 13 las borraba a los 7 dias sin usarse)',
    'description': """
Odoo 13 borra en cada peticion (1 de cada 1.000) los ficheros de sesion que llevan mas de 7 dias sin usarse
(odoo/http.py, session_gc): una PDA o un PC que no se usa en una semana tiene que volver a entrar.
Lo pidio Isaac el 17/11/2026: que no se salga nunca de la sesion.

Con este modulo:
- session_gc de las peticiones deja de borrar sesiones (no hace nada).
- La limpieza pasa al auto-vacuum diario de Odoo (ir.autovacuum, cron «Base: Auto-vacuum internal data»): borra solo
  las sesiones SIN usuario (paginas de login o web publica, la mayoria) de mas de 7 dias. Las sesiones con usuario
  (uid) no se borran nunca.
- La cookie de sesion ya dura 90 dias y Odoo la renueva en cada respuesta: mientras se use, no caduca.

No evita: cerrar sesion a mano, cambiar la contrasena del usuario, archivar el usuario, borrar las cookies del
navegador ni el «Failed to load registry» cuando se actualizan modulos a la vez (17/11 09:22 UTC): en ese caso Odoo
cierra la sesion de quien hace una peticion. Para eso: una sola actualizacion a la vez.

Sin modelos nuevos, sin campos y sin vistas. Al desinstalarlo, el cambio de session_gc sigue hasta reiniciar Odoo.

v1.0.0 (17/11/2026): primera version.
""",
    'version': '13.0.1.0.0',
    'author': 'NATH',
    'category': 'Hidden',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [],
    'installable': True,
    'application': False,
}
