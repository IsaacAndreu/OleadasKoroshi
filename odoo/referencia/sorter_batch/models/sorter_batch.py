# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SorterBatch(models.Model):
    _name = 'sorter.batch'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name_seq'

    name_seq = fields.Char('Sorter Batch', readonly=True, required=True, default='SOR', copy=False)

    company_id = fields.Many2one(comodel_name='res.company', string="Company", relation='company_id',)

    picking_ids = fields.Many2many(comodel_name='stock.picking', string='Pickings in batch file',
                                   relation='sorter_batch_picking_rel', domain="[('company_id', '=', company_id)]",)

    sorter_location = fields.Selection([('outer', 'Outer'), ('inner', 'Inner')], string='Sorter location', default='inner')

    sorter_operation_type = fields.Selection([('ORDERS', 'Orders'), ('RETURNS', 'Returns'), ('RETAIL', 'Retail')],
                                             string='Operation type', default='ORDERS')

    @api.model
    def create(self, vals):
        if vals.get('name_seq', 'SOR') == 'SOR':
            vals['name_seq'] = self.env['ir.sequence'].next_by_code('sorter.batch.sequence')
        result = super(SorterBatch, self).create(vals)
        is_import = self.env.context.get('import_file', False)
        for rec in result:
            if is_import:
                rec.message_post(body="Sorter Batch record created")
        return result
