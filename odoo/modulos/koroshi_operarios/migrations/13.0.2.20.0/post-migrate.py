# -*- coding: utf-8 -*-
# v2.20.0: al actualizar, el usuario «Almacen 2» (almacen2@nath.es, los jefes de almacén) entra en el grupo del
# tablero (KOROSHI: Tablero del responsable). «Almacén Nath» (las PDA) no entra. Si el usuario no existe, no pasa nada.
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

USUARIO_TABLERO = 'almacen2@nath.es'


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    grupo = env.ref('koroshi_operarios.grupo_tablero', raise_if_not_found=False)
    usuario = env['res.users'].with_context(active_test=False).search([('login', '=', USUARIO_TABLERO)], limit=1)
    if grupo and usuario and usuario not in grupo.users:
        grupo.write({'users': [(4, usuario.id)]})
    _logger.info('KOROSHI Operarios 2.20.0: tablero para %s', usuario.login if usuario else 'nadie (no existe %s)'
                 % USUARIO_TABLERO)
