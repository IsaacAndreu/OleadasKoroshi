# -*- coding: utf-8 -*-
# v1.8.5 (26/11/2026): Inicio PDA > Recepciones > «Recepcionar» abre la pantalla nueva de koroshi_recepcion (Isaac 26/11,
# urgente: están recepcionando un contenedor con ella). La actividad es noupdate: el dato no se pisa al actualizar, así
# que se cambia aquí, y solo si sigue con lo de la 1.6.0 (si alguien la ha cambiado a mano, no se toca). Va como
# «koroshi_recepcion...,stock_barcode...»: si koroshi_recepcion no está, abre la app de código de barras como antes.
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

ANTES = 'stock_barcode.stock_barcode_action_main_menu'
AHORA = 'koroshi_recepcion.action_koroshi_recepcion_pantalla,' + ANTES


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {'active_test': False})
    act = env.ref('koroshi_actividades.actividad_pda_recepcionar', raise_if_not_found=False)
    if act and act._name == 'koroshi.actividad' and (act.abre or '').strip() == ANTES:
        act.write({'abre': AHORA})
        _logger.info('KOROSHI Actividades 1.8.5: «%s» abre ahora %s', act.name, AHORA)
