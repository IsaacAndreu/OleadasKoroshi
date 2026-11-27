# -*- coding: utf-8 -*-
from odoo import fields, models


class KoroshiContenedorMovimiento(models.Model):
    _name = 'koroshi.contenedor.movimiento'
    _description = 'KOROSHI: movimiento de contenedor entre ubicaciones'
    _order = 'id desc'

    # v1.5: 'cero' y 'anadir' son ajustes de inventario (cambian el stock): una línea por artículo, con su movimiento
    # v1.7: 'cantidad' también (uds reales de un artículo del contenedor; uds = diferencia, + o -)
    # v1.13: 'faltante' = una línea reservada (o una parte) que ha pasado a Faltantes al poner a cero o al cambiar la
    # cantidad (uds = las que salen del contenedor a FALTANTE; reservadas = las que ha perdido la reserva aquí)
    # v1.16: 'con_prendas' = en la ronda de cajas a 0, la caja está a 0 en Odoo y tiene prendas (no cambia el stock;
    # queda pendiente hasta que se añaden sus prendas o se archiva). 'encontrado' = al resolverla, prendas que eran un
    # faltante pendiente de esa caja o de su hueco (de FALTANTE a la caja, sin ajuste)
    accion = fields.Selection([('mover', 'Mover'), ('archivar', 'Archivar vacío'), ('cero', 'Poner a cero'),
                               ('anadir', 'Añadir prendas'), ('cantidad', 'Cambiar cantidad'),
                               ('faltante', 'A Faltantes'), ('cambiar_articulo', 'Cambiar artículo'),
                               ('con_prendas', 'Caja a 0 con prendas (marcada)'),
                               ('encontrado', 'Encontrado (de Faltantes)')], 'Acción',
                              default='mover', required=True)
    contenedor = fields.Char('Contenedor', required=True, index=True)
    origen_id = fields.Many2one('stock.location', 'Origen (hueco)', ondelete='set null')
    destino_id = fields.Many2one('stock.location', 'Destino (hueco)', ondelete='set null')
    origen = fields.Char('Origen')
    destino = fields.Char('Destino')
    uds = fields.Float('Uds', digits=(16, 2))
    reservadas = fields.Float('Reservadas', digits=(16, 2))
    lineas = fields.Integer('Referencias')
    employee_id = fields.Many2one('hr.employee', 'Operario (tarjeta)', ondelete='set null', index=True)
    producto_id = fields.Many2one('product.product', 'Artículo', ondelete='set null', index=True)   # v1.5
    move_id = fields.Many2one('stock.move', 'Movimiento de stock', ondelete='set null')             # v1.5
    user_id = fields.Many2one('res.users', 'Usuario de Odoo', default=lambda s: s.env.uid)
    # v1.13 (R3): id de la tanda de «Añadir prendas» que pone la PDA; un reintento con la misma tanda no se repite
    tanda = fields.Char('Tanda (PDA)', index=True, readonly=True)
    faltante_id = fields.Many2one('koroshi.faltante', 'Faltante', ondelete='set null', readonly=True)   # v1.13
    # v1.14 (R23): «Es otro» (error de talla). producto_id = lo que decía Odoo (sale del contenedor, move_id);
    # producto_nuevo_id = lo que hay de verdad (entra, move_nuevo_id). Una línea por cambio
    producto_nuevo_id = fields.Many2one('product.product', 'Artículo real', ondelete='set null', index=True,
                                        readonly=True)
    move_nuevo_id = fields.Many2one('stock.move', 'Movimiento del artículo real', ondelete='set null', readonly=True)
    # v1.17: el paso de «Compactar» que hizo este movimiento (accion 'mover')
    paso_id = fields.Many2one('koroshi.compactacion.paso', 'Paso de compactación', ondelete='set null', readonly=True)

    _sql_constraints = [
        ('tanda_producto_unica', 'unique (tanda, producto_id)',
         'Esa tanda ya está guardada: no se añade dos veces.'),
    ]
