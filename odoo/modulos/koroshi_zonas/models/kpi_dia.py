# -*- coding: utf-8 -*-
# =============================================================================
# Amplia la ficha diaria de koroshi_kpi (no se duplica): % real de cajas cerradas de las zonas del dia,
# sacado de las filas medidas de koroshi.zonas.ejecucion.out. Campos calculados sin guardar: no cambian
# la tabla de koroshi_kpi.
# =============================================================================
from odoo import fields, models


class KoroshiKpiDia(models.Model):
    _inherit = 'koroshi.kpi.dia'

    zonas_cajas_reales = fields.Integer('Zonas: cajas reales', compute='_compute_zonas_cajas')
    zonas_cajas_cerradas = fields.Integer('Zonas: cajas cerradas reales', compute='_compute_zonas_cajas')
    zonas_pct_cajas_cerradas = fields.Float('Zonas: % cajas cerradas', compute='_compute_zonas_cajas',
                                            digits=(16, 1),
                                            help='Cajas propias no compartidas que llegan al mínimo de llenado, '
                                                 'sobre las cajas reales de las OUT de zonas (Z-) del día')

    def _compute_zonas_cajas(self):
        Fila = self.env['koroshi.zonas.ejecucion.out'].sudo()
        for r in self:
            reales = cerradas = 0
            if r.fecha and r.metodo in ('zonas', 'mixto'):
                for g in Fila.read_group([('fecha', '=', r.fecha), ('medida', '=', True)],
                                         ['cajas_reales', 'cajas_cerradas'], []):
                    reales = g['cajas_reales'] or 0
                    cerradas = g['cajas_cerradas'] or 0
            r.zonas_cajas_reales = reales
            r.zonas_cajas_cerradas = cerradas
            r.zonas_pct_cajas_cerradas = reales and round(100.0 * cerradas / reales, 1) or 0.0
