# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Actividades - lista de actividades que se eligen en el portátil.
# Se cambian desde Configuración (nombre, orden, color, archivar) sin tocar código.
#
# v1.6.0 (entrada única de la PDA, diseño bin/versiones/diseno-pda-entrada-unica_2026-11-20_v2.md): cada actividad
# tiene su área (Recepciones, Picking, Compactación, Devoluciones, Inversa, Expediciones o Extra). Entrar en un área
# en la pantalla «Inicio (PDA)» = empezar una de sus actividades: el tiempo va a la misma tabla de tramos que el
# portátil. «Abre» = la pantalla que se abre después (Lecturas, Contenedores...), como id externo o número de acción.
# =============================================================================
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)

# Mismos códigos que el tablero del responsable (koroshi_operarios 2.23.0, models/tablero_areas.py, AREAS)
AREAS = [
    ('recepciones', 'Recepciones'),
    ('picking', 'Picking'),
    ('compactacion', 'Compactación'),
    ('devoluciones', 'Devoluciones'),
    ('inversa', 'Inversa'),
    ('expediciones', 'Expediciones'),
    ('extra', 'Extra'),
]


def accion_de(env, texto):
    """v1.6.0: 'modulo.id_externo' o un número -> la acción (ir.actions.*), o None si no existe (módulo sin instalar,
    acción borrada o texto mal escrito). Nunca da error: el botón simplemente no abre nada.
    v1.8.5: varias separadas por coma = la primera que exista (p. ej. la pantalla de koroshi_recepcion y, si no está
    instalada, la app de código de barras)."""
    texto = (texto or '').strip()
    if not texto:
        return None
    if ',' in texto:
        for parte in texto.split(','):
            accion = accion_de(env, parte)
            if accion:
                return accion
        return None
    try:
        if texto.isdigit():
            accion = env['ir.actions.actions'].sudo().browse(int(texto)).exists()
        else:
            accion = env.ref(texto, raise_if_not_found=False)
    except Exception:   # id externo mal escrito (sin punto, etc.)
        _logger.info('KOROSHI ACTIVIDADES: la acción «%s» no existe', texto)
        return None
    if not accion or not accion._name.startswith('ir.actions.'):
        return None
    return accion


class KoroshiActividad(models.Model):
    _name = 'koroshi.actividad'
    _description = 'KOROSHI Actividad (manipulaciones)'
    _order = 'sequence, id'

    name = fields.Char('Actividad', required=True, translate=False)
    sequence = fields.Integer('Orden', default=10)
    color = fields.Char('Color', default='#0b4f9c', help='Color del botón en el portátil (#rrggbb)')
    active = fields.Boolean('Activa', default=True)
    company_id = fields.Many2one('res.company', 'Empresa', default=lambda self: self.env.company)
    nota = fields.Char('Qué incluye', help='Texto pequeño debajo del nombre en el botón (opcional)')
    # v1.1.0: inversa
    pide_matricula = fields.Boolean('Lee matrículas (inversa)',
                                    help='Mientras se está en esta actividad, cada caja que se abre se lee (CJ + 9 '
                                         'cifras): cajas por persona, tiempo de cada caja y uds del teórico.')
    # v1.6.0: entrada única de la PDA
    area = fields.Selection(AREAS, 'Área (PDA)', index=True,
                            help='Área de la pantalla «Inicio (PDA)» en la que sale esta actividad. Vacío = no sale '
                                 'en la PDA (solo en el portátil).')
    abre = fields.Char('Abre (PDA)',
                       help='Pantalla que se abre en la PDA al empezar esta actividad: id externo de la acción '
                            '(p. ej. koroshi_operarios.action_koroshi_operarios_pantalla) o su número. Vacío = se '
                            'queda en el Inicio contando el tiempo. Varias separadas por coma = la primera que '
                            'exista.')
    en_portatil = fields.Boolean('En el portátil', default=True,
                                 help='Sale como botón en el portátil de Actividades. Las de la PDA con su propia '
                                      'pantalla (Picking, Compactación...) no hace falta que salgan.')

    def accion_abre(self):
        """v1.6.0: la acción de «Abre» o None."""
        self.ensure_one()
        return accion_de(self.env, self.abre)
