# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Contenedores v1.17.0 - «Compactar» (fase 1): plan por lineal y bandas de altura. Tablas propias; no añade
# campos a tablas de Odoo ni crea ubicaciones (diseño v6, aprobado por Isaac el 26/11).
# =============================================================================
from odoo import fields, models

BANDAS = [('abajo', 'Abajo (alturas 1-2)'), ('arriba', 'Arriba (alturas 3-4)')]


class KoroshiCompactacionPaso(models.Model):
    """Un paso del plan: llevar una KO entera de una columna (hueco) a otra. El plan se calcula por lineal en la PDA
    («Calcular L67»); calcular otra vez deja «sustituido» lo pendiente de ese lineal. Se hace con /mover de siempre:
    la KO se lleva sus prendas y sus reservas."""
    _name = 'koroshi.compactacion.paso'
    _description = 'KOROSHI: paso de compactación (mover una KO entera)'
    _order = 'lineal, orden, id'

    lineal = fields.Integer('Lineal', required=True, index=True)
    calculo = fields.Char('Cálculo', index=True, readonly=True, help='Id del cálculo que creó el paso')
    orden = fields.Integer('Orden', required=True)
    origen_id = fields.Many2one('stock.location', 'Columna de origen', required=True, ondelete='cascade')
    contenedor_id = fields.Many2one('stock.location', 'KO', required=True, ondelete='cascade', index=True)
    contenedor = fields.Char('KO (nombre)')
    destino_id = fields.Many2one('stock.location', 'Columna de destino (plan)', ondelete='set null')
    destino_real_id = fields.Many2one('stock.location', 'Columna de destino (real)', ondelete='set null')
    mc = fields.Char('Modelo-color')
    uds = fields.Float('Uds', digits=(16, 2))
    banda = fields.Selection(BANDAS, 'Altura')
    estado = fields.Selection([('pendiente', 'Pendiente'), ('hecho', 'Hecho'), ('cambiado', 'Hecho en otra columna'),
                               ('no_esta', 'No está'), ('sustituido', 'Sustituido (recalculado)')], 'Estado',
                              default='pendiente', required=True, index=True)
    motivo = fields.Char('Motivo')
    employee_id = fields.Many2one('hr.employee', 'Operario', ondelete='set null')
    fecha = fields.Datetime('Hecho el')
    movimiento_id = fields.Many2one('koroshi.contenedor.movimiento', 'Registro', ondelete='set null')


class KoroshiContenedorBanda(models.Model):
    """Altura de una KO dentro de su columna (abajo o arriba). En Odoo no existen las alturas (C1–C4 son columnas):
    se apunta aquí al compactar (opción A del diseño v6). Una fila por KO."""
    _name = 'koroshi.contenedor.banda'
    _description = 'KOROSHI: altura (banda) de una KO en su columna'
    _rec_name = 'contenedor_id'

    contenedor_id = fields.Many2one('stock.location', 'KO', required=True, ondelete='cascade', index=True)
    banda = fields.Selection(BANDAS, 'Altura', required=True)
    employee_id = fields.Many2one('hr.employee', 'Operario', ondelete='set null')

    _sql_constraints = [('contenedor_unico', 'unique (contenedor_id)', 'Una KO solo tiene una altura.')]
