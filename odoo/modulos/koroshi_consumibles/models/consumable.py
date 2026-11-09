# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KoroshiConsumableItem(models.Model):
    _name = 'koroshi.consumable.item'
    _description = 'Artículo consumible KOROSHI'
    _order = 'active desc, name asc'

    name = fields.Char(string='Artículo', required=True)
    code = fields.Char(string='Código interno', index=True)
    category = fields.Char(string='Categoría')
    uom = fields.Selection([
        ('unidad', 'Unidades'),
        ('caja', 'Cajas'),
        ('paquete', 'Paquetes'),
        ('rollo', 'Rollos'),
        ('otro', 'Otra unidad'),
    ], string='Unidad', required=True, default='unidad')
    initial_qty = fields.Float(
        string='Total inicial', digits=(16, 2), default=0.0,
        help='Cantidad conocida al poner en marcha el control. Betty puede revisarla con un ajuste posterior.',
    )
    minimum_qty = fields.Float(
        string='Mínimo de aviso', digits=(16, 2), default=0.0,
        help='Si el stock actual baja hasta este valor, aparece como bajo mínimo.',
    )
    company_id = fields.Many2one(
        'res.company', string='Compañía', required=True,
        default=lambda self: self.env.user.company_id, index=True,
    )
    active = fields.Boolean(default=True)
    note = fields.Text(string='Notas')
    movement_ids = fields.One2many(
        'koroshi.consumable.move', 'item_id', string='Movimientos',
    )
    current_qty = fields.Float(
        string='Stock actual', compute='_compute_totals', store=True,
        digits=(16, 2),
    )
    total_consumed = fields.Float(
        string='Total consumido', compute='_compute_totals', store=True,
        digits=(16, 2),
    )
    total_entries = fields.Float(
        string='Total entradas', compute='_compute_totals', store=True,
        digits=(16, 2),
    )
    stock_status = fields.Selection([
        ('ok', 'Correcto'),
        ('low', 'Bajo mínimo'),
        ('empty', 'Agotado'),
    ], string='Estado', compute='_compute_totals', store=True)
    last_move_date = fields.Datetime(
        string='Último movimiento', compute='_compute_last_move', store=True,
    )

    _sql_constraints = [
        ('code_company_unique', 'unique(code, company_id)',
         'El código interno debe ser único dentro de la compañía.'),
    ]

    @api.depends('initial_qty', 'minimum_qty', 'movement_ids.quantity',
                 'movement_ids.movement_type')
    def _compute_totals(self):
        for item in self:
            consumed = sum(
                move.quantity for move in item.movement_ids
                if move.movement_type == 'consumption'
            )
            entries = sum(
                move.quantity for move in item.movement_ids
                if move.movement_type == 'entry'
            )
            corrections = sum(
                move.quantity for move in item.movement_ids
                if move.movement_type == 'adjustment'
            )
            current = item.initial_qty + entries - consumed + corrections
            item.total_consumed = consumed
            item.total_entries = entries
            item.current_qty = current
            if current <= 0:
                item.stock_status = 'empty'
            elif item.minimum_qty and current <= item.minimum_qty:
                item.stock_status = 'low'
            else:
                item.stock_status = 'ok'

    @api.depends('movement_ids.date')
    def _compute_last_move(self):
        for item in self:
            dates = item.movement_ids.mapped('date')
            item.last_move_date = max(dates) if dates else False

    @api.constrains('initial_qty', 'minimum_qty')
    def _check_quantities(self):
        for item in self:
            if item.initial_qty < 0:
                raise ValidationError(_('El total inicial no puede ser negativo.'))
            if item.minimum_qty < 0:
                raise ValidationError(_('El mínimo de aviso no puede ser negativo.'))

    def action_register_consumption(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Registrar consumo'),
            'res_model': 'koroshi.consumable.move',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_item_id': self.id,
                'default_movement_type': 'consumption',
            },
        }


class KoroshiConsumableMove(models.Model):
    _name = 'koroshi.consumable.move'
    _description = 'Movimiento de consumible KOROSHI'
    _order = 'date desc, id desc'

    item_id = fields.Many2one(
        'koroshi.consumable.item', string='Artículo', required=True,
        ondelete='cascade', index=True,
    )
    date = fields.Datetime(
        string='Fecha y hora', required=True, default=fields.Datetime.now,
        index=True,
    )
    movement_type = fields.Selection([
        ('consumption', 'Consumo'),
        ('entry', 'Entrada'),
        ('adjustment', 'Corrección'),
    ], string='Tipo', required=True, default='consumption', index=True)
    quantity = fields.Float(
        string='Cantidad', required=True, digits=(16, 2),
        help='Usa una cantidad positiva para consumos y entradas. En una corrección puede ser positiva o negativa.',
    )
    responsible_id = fields.Many2one(
        'res.users', string='Registrado por', required=True,
        default=lambda self: self.env.user, readonly=True,
    )
    company_id = fields.Many2one(
        related='item_id.company_id', string='Compañía', store=True, readonly=True,
    )
    note = fields.Char(string='Motivo / observaciones')
    signed_quantity = fields.Float(
        string='Impacto en stock', compute='_compute_signed_quantity',
        digits=(16, 2),
    )

    @api.depends('movement_type', 'quantity')
    def _compute_signed_quantity(self):
        for move in self:
            move.signed_quantity = (
                -move.quantity if move.movement_type == 'consumption'
                else move.quantity
            )

    @api.constrains('movement_type', 'quantity')
    def _check_quantity(self):
        for move in self:
            if move.movement_type in ('consumption', 'entry') and move.quantity <= 0:
                raise ValidationError(_('Los consumos y entradas deben tener una cantidad positiva.'))
            if move.movement_type == 'adjustment' and not move.quantity:
                raise ValidationError(_('Una corrección no puede tener cantidad cero.'))

    @api.model
    def create(self, vals):
        move_type = vals.get('movement_type', 'consumption')
        item = self.env['koroshi.consumable.item'].browse(vals.get('item_id')).exists()
        quantity = float(vals.get('quantity') or 0.0)
        if item and move_type == 'consumption' and quantity > item.current_qty + 0.0001:
            raise ValidationError(_(
                'No se pueden registrar %(qty)s %(unit)s: el stock actual de %(item)s es %(available)s.'
            ) % {
                'qty': quantity,
                'unit': dict(item._fields['uom'].selection).get(item.uom, item.uom),
                'item': item.display_name,
                'available': item.current_qty,
            })
        return super(KoroshiConsumableMove, self).create(vals)

    def write(self, vals):
        for move in self:
            move_type = vals.get('movement_type', move.movement_type)
            quantity = float(vals.get('quantity', move.quantity) or 0.0)
            item = self.env['koroshi.consumable.item'].browse(
                vals.get('item_id', move.item_id.id)).exists()
            if item and move_type == 'consumption':
                available = item.current_qty
                if item.id == move.item_id.id:
                    available -= move.signed_quantity
                if quantity > available + 0.0001:
                    raise ValidationError(_(
                        'No se pueden dejar %(qty)s unidades consumidas: el stock disponible de %(item)s es %(available)s.'
                    ) % {
                        'qty': quantity,
                        'item': item.display_name,
                        'available': available,
                    })
        return super(KoroshiConsumableMove, self).write(vals)

    def unlink(self):
        raise ValidationError(_(
            'Los movimientos no se borran para conservar la trazabilidad. Registra una corrección.'
        ))
