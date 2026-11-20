# -*- coding: utf-8 -*-
# v1.8.3 (20/11/2026): el área Devoluciones de la PDA abre «Ubicar devoluciones» (actividad nueva de data/areas_pda.xml,
# se crea sola al actualizar). «Manipulación devoluciones» (del portátil, noupdate) pasa a Recepciones, como las otras
# manipulaciones (Isaac 20/11). Solo si sigue en Devoluciones: si alguien la ha cambiado a mano, no se pisa.
# El área de los tramos es un campo relacionado guardado: los tramos de esa actividad pasan a contar en Recepciones.
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {'active_test': False})
    act = env.ref('koroshi_actividades.actividad_devoluciones', raise_if_not_found=False)
    if act and act._name == 'koroshi.actividad' and act.area == 'devoluciones':
        act.write({'area': 'recepciones'})
        _logger.info('KOROSHI Actividades 1.8.3: %s -> área recepciones', act.name)
