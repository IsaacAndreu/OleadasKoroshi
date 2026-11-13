# -*- coding: utf-8 -*-
# v3.29.0: antes de crear la restricción única (picking_id, titular_id, ayudante_id) en koroshi.preparacion.equipo se
# quitan las filas repetidas (misma OUT, mismo titular y mismo ayudante), quedándose la más nueva de cada una, que es
# la que usaba la PDA (la búsqueda va por id desc). El 13/11/2026 solo había una: EFFEC/OUT/24410 (ids 4 y 5, creadas
# en el mismo segundo por dos PDA a la vez; la OUT ya está validada). Sin ellas, PostgreSQL no crearía la restricción
# y Odoo solo lo diría en el log.
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute("SELECT to_regclass('koroshi_preparacion_equipo')")
    if not cr.fetchone()[0]:
        return
    cr.execute("""
        DELETE FROM koroshi_preparacion_equipo e
         USING koroshi_preparacion_equipo otra
         WHERE e.picking_id = otra.picking_id
           AND e.titular_id = otra.titular_id
           AND e.ayudante_id = otra.ayudante_id
           AND e.id < otra.id
     RETURNING e.id, e.picking_id
    """)
    borradas = cr.fetchall()
    _logger.info('KOROSHI Preparación 3.29.0: %s filas repetidas de OUT a dos borradas (id, OUT): %s',
                 len(borradas), borradas)
