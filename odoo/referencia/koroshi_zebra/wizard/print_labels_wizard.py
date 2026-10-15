# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class ZebraLabelPrintWizard(models.TransientModel):
    _name = 'zebra.label.print.wizard'
    _description = 'Generar e imprimir etiquetas Zebra'

    quantity = fields.Integer(string='Cantidad de etiquetas', default=1, required=True)
    note = fields.Char(string='Nota / Lote')
    next_code_preview = fields.Char(
        string='Próximo código',
        compute='_compute_next_code_preview',
    )

    @api.depends('quantity')
    def _compute_next_code_preview(self):
        seq = self.env['ir.sequence'].search([('code', '=', 'zebra.label.code')], limit=1)
        for wiz in self:
            wiz.next_code_preview = seq.get_next_char(seq.number_next_actual) if seq else ''

    def action_generate_and_print(self):
        self.ensure_one()
        if self.quantity <= 0:
            raise UserError('La cantidad debe ser mayor a 0.')

        Label = self.env['zebra.label']
        labels = Label.create_next_labels(quantity=self.quantity, note=self.note)
        return labels.action_print()
