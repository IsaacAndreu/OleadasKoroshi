from odoo import models, fields, api

class ProductPackaging(models.Model):
    _inherit = 'product.packaging'

    default_location_src_id = fields.Many2one('stock.location', 'Product Consume Source Location')
    default_location_dest_id = fields.Many2one('stock.location', 'Product Consume Destination Location')
    product_packaging_consume_ids = fields.One2many('product.packaging.consume', 'product_packaging_id', string='Product Packaging Consume')

class ProductPackagingConsume(models.Model):
    _name = 'product.packaging.consume'
    _description = 'Product Packaging Consume'

    product_id = fields.Many2one('product.product', 'Product', required=True,  domain="[('type', '!=', 'service'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure', related='product_id.uom_id', store=True)
    quantity = fields.Float(
        'Quantity', default=0.0, digits='Product Unit of Measure', required=True, copy=False)
    product_packaging_id = fields.Many2one('product.packaging', string='Product Packaging', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', readonly=True, required=True,
        default=lambda self: self.env.company)

class StockQuantPackage(models.Model):
    _inherit = 'stock.quant.package'

    def _compute_move_count(self):
        for record in self:
            move_ids = self.env['stock.move'].search([('consume_package_id', '=', record.id)])
            record.move_count = len(move_ids.ids)

    move_count = fields.Integer(string='Stock Moves', compute='_compute_move_count')

    def action_view_moves(self):
        action = self.env.ref('stock.stock_move_action').read()[0]
        action['domain'] = [('consume_package_id', '=', self.id)]
        return action
