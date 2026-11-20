# -*- coding: utf-8 -*-
# v1.6.0 (20/11/2026): entrada única de la PDA. Las actividades de partida (data/actividades.xml) son noupdate, así que
# al actualizar no reciben su área: se la pone esta migración (solo si aún no tiene, para no pisar lo cambiado a mano).
# Reparto acordado con Isaac el 20/11 (diseno-pda-entrada-unica_2026-11-20_v2.md): manipulaciones del portátil en
# Recepciones, devoluciones en Devoluciones, inversa en Inversa (y en la PDA abre la pantalla de Actividades).
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

AREAS = {
    'koroshi_actividades.actividad_marketplace': {'area': 'recepciones'},
    'koroshi_actividades.actividad_tiendas': {'area': 'recepciones'},
    'koroshi_actividades.actividad_web': {'area': 'recepciones'},
    'koroshi_actividades.actividad_bolsas': {'area': 'recepciones'},
    'koroshi_actividades.actividad_devoluciones': {'area': 'devoluciones'},
    'koroshi_actividades.actividad_inversa': {'area': 'inversa',
                                              'abre': 'koroshi_actividades.action_koroshi_actividades_pantalla'},
}


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {'active_test': False})
    for xmlid, vals in AREAS.items():
        act = env.ref(xmlid, raise_if_not_found=False)
        if not act or act._name != 'koroshi.actividad' or act.area:
            continue
        act.write(vals)
        _logger.info('KOROSHI Actividades 1.6.0: %s -> área %s', act.name, vals['area'])
