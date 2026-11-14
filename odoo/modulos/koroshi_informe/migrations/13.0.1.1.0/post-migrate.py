# -*- coding: utf-8 -*-
# v1.1.0 (con koroshi_operarios 2.12.0): las tareas que ya hay se recalculan con la cifra nueva (parado, efectivo y u/h
# sobre el efectivo). Va aqui y no en koroshi_operarios porque el parado sale de las lecturas de koroshi_preparacion, que
# al actualizar se carga DESPUES de koroshi_operarios (alli aun no estaria y todo saldria con parado 0). Este modulo
# depende de los dos. Solo escribe en koroshi_operario_tarea. El 14/11/2026 eran 51 tareas: es un momento.
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    if 'koroshi.operario.tarea' not in env or 'parado' not in env['koroshi.operario.tarea']._fields:
        return
    Tarea = env['koroshi.operario.tarea']
    tareas = Tarea.with_context(active_test=False).search([])
    for nombre in ('minutos', 'uds', 'parado', 'efectivo', 'uds_hora'):
        env.add_to_compute(Tarea._fields[nombre], tareas)
    tareas.recompute()
    tareas.flush()
    _logger.info('KOROSHI Informe 1.1.0: %s tareas de operarios recalculadas (parado, efectivo, u/h)', len(tareas))
