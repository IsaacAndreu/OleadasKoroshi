from odoo import api, fields, models, tools, _

class StockMove(models.Model):
    _inherit = "stock.move"

    # 1.0.1 (24/11/2026, tuctuc): index=True. Contar los movimientos de un paquete buscaba en stock_move entero
    # (20 M filas, 6-21 s por paquete). Indice creado a mano con CONCURRENTLY y el nombre de Odoo.
    consume_package_id = fields.Many2one('stock.quant.package', 'Consume Package', index=True)

    def write(self, vals):
        res = super(StockMove, self).write(vals)
        if vals.get('state') == 'done':
            for record in self:
                move_line = self.env['stock.move.line'].search([('move_id', '=', record.id)])
                if move_line:
                    move_line.create_package_material_transfer()
        return res

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    package_material_transfer_created = fields.Boolean(string='Package Material Transfer Created')

    def create_package_material_transfer(self):
        stock_move_pool = self.env['stock.move']
        for record in self.filtered(lambda x: x.result_package_id and x.result_package_id.packaging_id and x.result_package_id.packaging_id.product_packaging_consume_ids and x.picking_code == 'outgoing'):
            package_material_transfer_created_move = self.env['stock.move.line'].search([('picking_id', '=', record.picking_id.id), ('result_package_id', '=', record.result_package_id.id), ('package_material_transfer_created', '=', True)])
            if not package_material_transfer_created_move:
                for packaging_consume in record.result_package_id.packaging_id.product_packaging_consume_ids:
                    customerloc = self.env['stock.location'].search(['|', '&', ('company_id', '=', self.env.company.id), ('company_id', '=', False), ('usage', '=', 'customer')], limit=1)
                    location_id = (record.result_package_id.packaging_id.default_location_src_id and record.result_package_id.packaging_id.default_location_src_id.id) or (record.move_id.warehouse_id.lot_stock_id.id)
                    location_dest_id = (record.result_package_id.packaging_id.default_location_dest_id and record.result_package_id.packaging_id.default_location_dest_id.id) or customerloc.id

                    move = stock_move_pool.create({'date': fields.Datetime.now(),
                        'date_expected': fields.Datetime.now(),
                        'location_id': location_id,
                        'location_dest_id': location_dest_id,
                        'name': record.move_id.origin or record.move_id.name,
                        'procure_method': 'make_to_stock',
                        'product_id': packaging_consume.product_id.id,
                        'product_uom': packaging_consume.product_uom_id.id,
                        'product_uom_qty': packaging_consume.quantity,
                        'quantity_done': packaging_consume.quantity,
                        'partner_id': False,
                        'consume_package_id': record.result_package_id.id,
                        })
                    move._action_done()
            record.package_material_transfer_created = True
