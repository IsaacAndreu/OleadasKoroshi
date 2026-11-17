# -*- coding: utf-8 -*-
"""v1.29.0 (17/11/2026): cierre del camión XPO de un día.

Al acabar de cargar, alguien de expediciones pulsa «Cerrar camión y enviar manifiesto» en Consulta de envíos. Se manda
el Excel XPO de ese día por correo (para y cc en parámetros) y queda guardado aquí: qué OUT y qué seguimientos iban.
koroshi_s4t_envios (1.3 o más) mira este modelo para mandar el is_final a S4T solo cuando el camión ha salido.
Uno por día; si hay que repetirlo, se reenvía y se cuenta.
"""
from odoo import fields, models


class KoroshiEnvioCierre(models.Model):
    _name = 'koroshi.envio.cierre'
    _description = 'Cierre del camión XPO de un día (manifiesto enviado)'
    _order = 'dia desc, id desc'
    _rec_name = 'dia'

    dia = fields.Date(string='Día', required=True, index=True, readonly=True)
    transportista = fields.Selection([('xpo', 'XPO SAS')], string='Transportista', required=True, default='xpo',
                                     readonly=True)
    company_id = fields.Many2one('res.company', string='Compañía', required=True, index=True, readonly=True,
                                 default=lambda self: self.env.company)
    picking_ids = fields.Many2many('stock.picking', 'koroshi_envio_cierre_picking_rel', 'cierre_id', 'picking_id',
                                   string='OUT', readonly=True)
    seguimientos = fields.Text(string='Seguimientos XPO', readonly=True)
    tiendas = fields.Integer(string='Tiendas', readonly=True)
    pedidos = fields.Integer(string='Pedidos', readonly=True)
    bultos = fields.Integer(string='Bultos', readonly=True)
    cajas = fields.Integer(string='Cajas', readonly=True)
    diferencias = fields.Text(string='Diferencias sin resolver', readonly=True)
    para = fields.Char(string='Para', readonly=True)
    cc = fields.Char(string='CC', readonly=True)
    envios = fields.Integer(string='Veces enviado', readonly=True)
    fecha_envio = fields.Datetime(string='Último envío', readonly=True)
    usuario_id = fields.Many2one('res.users', string='Enviado por', readonly=True)
    adjunto_id = fields.Many2one('ir.attachment', string='Excel enviado', readonly=True, ondelete='set null')
    mail_id = fields.Many2one('mail.mail', string='Correo', readonly=True, ondelete='set null')

    _sql_constraints = [
        ('koroshi_envio_cierre_dia', 'unique(company_id, transportista, dia)',
         'Ese día ya tiene su cierre: hay que reenviarlo, no crear otro.'),
    ]
