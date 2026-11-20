# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Recuentos v1.1.0 (fase 2): el recuento leído de una referencia. Solo apunta: NO toca el stock.
# Diseño: bin/versiones/diseno-comprobar-inventario_2026-11-20_v3.md, puntos 3 y 4.
# - koroshi.recuento: una comprobación de una referencia (todas sus tallas y colores).
# - koroshi.recuento.caja: cada sitio (hueco o contenedor) a contar, en orden de recorrido, con su vuelta (1.ª, 2.ª
#   o 3.ª lectura) y su estado.
# - koroshi.recuento.linea: por caja, vuelta y variante: lo que decía Odoo al cerrar esa vuelta y lo leído.
# - koroshi.recuento.lectura: CADA lectura de la PDA, tal cual. Nunca se borra ni se edita: «Quitar la última» la
#   marca como anulada, con su hora («que quede siempre registro de todo», Isaac 20/11).
# Todo se escribe desde las rutas de la PDA (con sudo); en Odoo, todos los usuarios solo pueden leer.
# Tablas propias: no añade campos a tablas de Odoo.
# =============================================================================
from odoo import api, fields, models

ESTADOS_RECUENTO = [
    ('contando', 'Contando'),
    ('coincide', 'Coincide'),
    ('diferencias', 'Con diferencias confirmadas'),
    ('para_jefe', 'Para el jefe'),
]
ESTADOS_CAJA = [
    ('pendiente', 'Sin contar'),
    ('contando', 'Contando'),
    ('cuadra', 'Cuadra'),
    ('confirmada', 'Diferencia confirmada'),
    ('para_jefe', 'Para el jefe'),
    ('no_existe', 'El sitio no existe'),
]
CERRADAS = ('cuadra', 'confirmada', 'para_jefe', 'no_existe')


class KoroshiRecuento(models.Model):
    _name = 'koroshi.recuento'
    _description = 'KOROSHI: recuento de una referencia'
    _order = 'id desc'

    name = fields.Char('Recuento', required=True, readonly=True, default='/', index=True)
    referencia = fields.Char('Referencia', required=True, index=True, readonly=True)
    motivo = fields.Selection([('koroshi', 'Reclamación de KOROSHI'), ('ajuste', 'Ajuste a mano'),
                               ('faltante', 'Faltante'), ('negativo', 'Stock negativo'), ('rotacion', 'Rotación'),
                               ('mano', 'A mano (PDA)')], 'Motivo', default='mano', required=True, readonly=True)
    nota = fields.Char('Nota', readonly=True)
    estado = fields.Selection(ESTADOS_RECUENTO, 'Estado', default='contando', required=True, index=True,
                              readonly=True)
    employee_id = fields.Many2one('hr.employee', 'Empezado por (tarjeta)', ondelete='set null', readonly=True)
    user_id = fields.Many2one('res.users', 'Usuario de Odoo', default=lambda s: s.env.uid, readonly=True)
    inicio = fields.Datetime('Inicio', default=fields.Datetime.now, readonly=True)
    fin = fields.Datetime('Fin', readonly=True)
    company_id = fields.Many2one('res.company', 'Compañía', readonly=True)
    producto_ids = fields.Many2many('product.product', 'koroshi_recuento_producto_rel', 'recuento_id', 'producto_id',
                                    'Variantes', readonly=True,
                                    help='Las variantes de la referencia al empezar (para no buscarlas en cada lectura).')
    caja_ids = fields.One2many('koroshi.recuento.caja', 'recuento_id', 'Cajas', readonly=True)
    linea_ids = fields.One2many('koroshi.recuento.linea', 'recuento_id', 'Líneas', readonly=True)
    lectura_ids = fields.One2many('koroshi.recuento.lectura', 'recuento_id', 'Lecturas', readonly=True)
    n_cajas = fields.Integer('Cajas', compute='_compute_resumen', store=True)
    n_contadas = fields.Integer('Contadas', compute='_compute_resumen', store=True)
    n_diferencias = fields.Integer('Con diferencia', compute='_compute_resumen', store=True)
    uds_diferencia = fields.Float('Diferencia (uds)', compute='_compute_resumen', store=True, digits=(16, 2),
                                  help='Suma de lo leído menos lo que decía Odoo en las cajas con diferencia '
                                       'confirmada (+ sobra, - falta).')

    @api.depends('caja_ids.estado', 'caja_ids.diferencia')
    def _compute_resumen(self):
        for r in self:
            r.n_cajas = len(r.caja_ids)
            r.n_contadas = len(r.caja_ids.filtered(lambda c: c.estado in CERRADAS))
            dif = r.caja_ids.filtered(lambda c: c.estado == 'confirmada')
            r.n_diferencias = len(dif)
            r.uds_diferencia = sum(dif.mapped('diferencia'))

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].sudo().next_by_code('koroshi.recuento') or '/'
        return super().create(vals)


class KoroshiRecuentoCaja(models.Model):
    _name = 'koroshi.recuento.caja'
    _description = 'KOROSHI: sitio (hueco o contenedor) de un recuento'
    _order = 'recuento_id desc, orden, id'

    recuento_id = fields.Many2one('koroshi.recuento', 'Recuento', required=True, ondelete='cascade', index=True)
    orden = fields.Integer('Orden (recorrido)')
    ubicacion_id = fields.Many2one('stock.location', 'Sitio', ondelete='set null', index=True)
    hueco = fields.Char('Hueco')
    contenedor = fields.Char('Contenedor')
    estado = fields.Selection(ESTADOS_CAJA, 'Estado', default='pendiente', required=True)
    vuelta = fields.Integer('Lectura (vuelta)', default=0,
                            help='1.ª, 2.ª o 3.ª lectura de la caja. Si no cuadra, se lee otra vez.')
    vuelta_inicio = fields.Datetime('Inicio de la vuelta')
    fuera_de_lista = fields.Boolean('Encontrada fuera de lista',
                                    help='Odoo no tenía la referencia aquí: el operario leyó este sitio al pasar.')
    con_ajuste = fields.Boolean('Con ajuste a mano reciente')
    movimientos = fields.Integer('Vueltas repetidas por movimientos',
                                 help='Veces que hubo que volver a leer porque se movió stock de la caja mientras '
                                      'se contaba.')
    employee_id = fields.Many2one('hr.employee', 'Contada por', ondelete='set null')
    fecha = fields.Datetime('Cerrada')
    odoo = fields.Float('Odoo', digits=(16, 2), help='Lo que decía Odoo al cerrar la última vuelta (menos lo leído '
                                                     'en OUT sin validar).')
    contado = fields.Float('Leído', digits=(16, 2))
    diferencia = fields.Float('Diferencia', digits=(16, 2), help='Leído - Odoo (+ sobra, - falta).')
    linea_ids = fields.One2many('koroshi.recuento.linea', 'caja_id', 'Líneas')
    lectura_ids = fields.One2many('koroshi.recuento.lectura', 'caja_id', 'Lecturas')


class KoroshiRecuentoLinea(models.Model):
    _name = 'koroshi.recuento.linea'
    _description = 'KOROSHI: variante de una caja en una vuelta del recuento'
    _order = 'caja_id, vuelta, producto_id'

    caja_id = fields.Many2one('koroshi.recuento.caja', 'Caja', required=True, ondelete='cascade', index=True)
    recuento_id = fields.Many2one('koroshi.recuento', 'Recuento', related='caja_id.recuento_id', store=True,
                                  index=True)
    vuelta = fields.Integer('Vuelta')
    producto_id = fields.Many2one('product.product', 'Artículo', ondelete='set null', index=True)
    odoo = fields.Float('Odoo', digits=(16, 2))
    en_curso = fields.Float('En OUT sin validar', digits=(16, 2),
                            help='Prendas ya leídas en una OUT sin validar desde esta caja: Odoo aún las tiene, '
                                 'pero ya no están.')
    esperado = fields.Float('Debería haber', digits=(16, 2))
    contado = fields.Float('Leído', digits=(16, 2))
    diferencia = fields.Float('Diferencia', digits=(16, 2))
    final = fields.Boolean('Vuelta que vale', help='La vuelta con la que se cerró la caja.')


class KoroshiRecuentoLectura(models.Model):
    _name = 'koroshi.recuento.lectura'
    _description = 'KOROSHI: una lectura de la PDA en un recuento'
    _order = 'id desc'

    recuento_id = fields.Many2one('koroshi.recuento', 'Recuento', required=True, ondelete='cascade', index=True)
    caja_id = fields.Many2one('koroshi.recuento.caja', 'Caja', ondelete='cascade', index=True)
    vuelta = fields.Integer('Vuelta')
    codigo = fields.Char('Leído', required=True)
    producto_id = fields.Many2one('product.product', 'Artículo', ondelete='set null')
    resultado = fields.Selection([('contada', 'Contada'), ('otra', 'De otra referencia'),
                                  ('desconocida', 'No reconocida'), ('anulada', 'Anulada («Quitar la última»)'),
                                  ('descartada', 'Descartada (se movió stock de la caja mientras se contaba)')],
                                 'Resultado', required=True)
    employee_id = fields.Many2one('hr.employee', 'Operario (tarjeta)', ondelete='set null')
    fecha = fields.Datetime('Cuándo', default=fields.Datetime.now)
    anulada_fecha = fields.Datetime('Anulada o descartada')
