# -*- coding: utf-8 -*-
# =============================================================================
# Una fila por OUT de una ejecucion: zona, cajas previstas, cajas reales y si salio en caja cerrada.
# Lo que haga falta guardar por OUT va aqui (con many2one a la OUT), nunca en stock.picking.
# =============================================================================
from odoo import api, fields, models

CAUSAS = [
    ('ok', 'Coincide'),
    ('caja_compartida', 'Caja compartida (caja existente)'),
    ('cogido', 'Se cogió otra cosa (faltas)'),
    ('litros', 'Modelo de litros'),
    ('sin_prevision', 'Sin previsión'),
    ('sin_medir', 'Sin medir (OUT sin validar)'),
]


class KoroshiZonasEjecucionOut(models.Model):
    _name = 'koroshi.zonas.ejecucion.out'
    _description = 'KOROSHI Zonas - OUT de una ejecución'
    _order = 'fecha desc, zona, picking_id'
    _rec_name = 'picking_id'

    ejecucion_id = fields.Many2one('koroshi.zonas.ejecucion', 'Ejecución', required=True, ondelete='cascade',
                                   index=True)
    fecha = fields.Date('Día', related='ejecucion_id.fecha', store=True, index=True)
    company_id = fields.Many2one('res.company', related='ejecucion_id.company_id', store=True)
    picking_id = fields.Many2one('stock.picking', 'OUT', required=True, ondelete='cascade', index=True)
    lote_id = fields.Many2one('stock.picking.batch', 'Agrupación', ondelete='set null')
    zona = fields.Char('Zona', index=True, help='D1, D2... de lineal; MU1, MU2 de muelle')
    pedido = fields.Char('Pedido')
    tienda = fields.Char('Tienda')
    medida = fields.Boolean('Medida', help='La OUT ya está validada y se han contado sus cajas reales')

    # Previsto (fase 1: el CAJAS n de la nota; desde la fase 3, lo que guarda el propio reparto)
    cajas_previstas = fields.Integer('Cajas previstas')
    prevision_conocida = fields.Boolean('Previsión conocida',
                                        help='Falso si la nota ya no llevaba "CAJAS n" (la pisa otro proceso)')
    # Lo cogido de verdad
    uds = fields.Float('Uds cogidas')
    litros = fields.Float('Litros (estimados)', digits=(16, 1))
    cajas_estimadas = fields.Integer('Cajas estimadas con lo cogido',
                                     help='Las cajas que daría el modelo de litros con lo que se cogió de verdad')
    cerrada_estimada = fields.Boolean('Cerrada según el modelo')
    # Cajas reales (matrículas)
    cajas_reales = fields.Integer('Cajas reales', help='Matrículas de las que esta OUT es dueña')
    cajas_cerradas = fields.Integer('Cajas cerradas reales',
                                    help='Cajas propias no compartidas que llegan al mínimo de llenado')
    cajas_compartidas = fields.Integer('Cajas compartidas', help='Cajas propias en las que otra OUT ha metido uds')
    cajas_ajenas = fields.Integer('Cajas ajenas', help='Cajas de otra OUT en las que esta OUT ha metido uds')
    uds_en_ajenas = fields.Float('Uds en cajas ajenas')
    uds_sin_caja = fields.Float('Uds sin caja')
    cerrada = fields.Boolean('OUT en caja cerrada',
                             help='Todas sus cajas propias cerradas, nada en cajas ajenas y nada sin caja')
    diferencia = fields.Integer('Reales - previstas', compute='_compute_diferencia', store=True)
    causa = fields.Selection(CAUSAS, 'Causa de la diferencia', compute='_compute_diferencia', store=True)

    _sql_constraints = [('ejecucion_picking_uniq', 'unique(ejecucion_id, picking_id)',
                         'La OUT ya está en esta ejecución.')]

    @api.depends('medida', 'prevision_conocida', 'cajas_previstas', 'cajas_estimadas', 'cajas_reales',
                 'cajas_compartidas', 'cajas_ajenas')
    def _compute_diferencia(self):
        for r in self:
            r.diferencia = r.prevision_conocida and r.medida and (r.cajas_reales - r.cajas_previstas) or 0
            if not r.medida:
                r.causa = 'sin_medir'
            elif not r.prevision_conocida:
                r.causa = 'sin_prevision'
            elif r.cajas_reales == r.cajas_previstas:
                r.causa = 'ok'
            elif r.cajas_compartidas or r.cajas_ajenas:
                r.causa = 'caja_compartida'
            elif r.cajas_estimadas != r.cajas_previstas:
                r.causa = 'cogido'
            else:
                r.causa = 'litros'
