# -*- coding: utf-8 -*-
# v2.21.1: el tablero va por usuario, no por ser administrador. Dentro: Almacen 2 (jefes de almacén), Departament IT e
# Ismael (los administradores que lo pidieron). Fuera: «Almacén Nath» (las PDA), que entró en la 2.21.0 por ser
# administrador. Si un usuario no existe, no pasa nada.
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

DENTRO = ('almacen2@nath.es', 'departamentit@nath.es', 'ismael@nath.es')
FUERA = ('almacen@nath.es',)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    grupo = env.ref('koroshi_operarios.grupo_tablero', raise_if_not_found=False)
    if not grupo:
        return
    Users = env['res.users'].with_context(active_test=False)
    dentro = Users.search([('login', 'in', DENTRO)])
    fuera = Users.search([('login', 'in', FUERA)])
    ops = [(4, u.id) for u in dentro] + [(3, u.id) for u in fuera if u in grupo.users]
    if ops:
        grupo.write({'users': ops})
    _logger.info('KOROSHI Operarios 2.21.1: tablero para %s; fuera %s',
                 ', '.join(dentro.mapped('login')), ', '.join(fuera.mapped('login')) or 'nadie')
