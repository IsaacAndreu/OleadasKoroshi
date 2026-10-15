# -*- coding: utf-8 -*-

from odoo import api, fields, exceptions, models, _
from odoo.exceptions import Warning, UserError, ValidationError
import base64


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def create_batch_files(self, records):
        if len(records) > 99:
            raise UserError("No se puede crear archivos para más de 99 operaciones.")

        if len(set(records.mapped('picking_type_id'))) > 1:
            raise UserError("No se puede seleccionar más de 1 tipo de operación diferente.")

        if len(set(records.mapped('state'))) == 1 and records.mapped('state')[0] != 'assigned':
            raise UserError("Solo se puede generar archivos de operaciones 'En Curso'.")

        if len(set(records.mapped('state'))) > 1:
            raise UserError("Las operaciones seleccionadas tienen ESTADOS diferentes.")

        if len(set(records.mapped('company_id'))) > 1:
            raise UserError("Las operaciones seleccionadas pertenecen a COMPAÑIAS diferentes.")

        operations_company_id = records.mapped('company_id')[0].id

        sorter_location = self.env['stock.location'].search(
            [
                ('barcode','=', 'SORTER'),
                ('company_id', '=', operations_company_id)
            ]
        )

        stock_location = None
        picking_type = None

        if operations_company_id == 1:
            stock_location = self.env['stock.location'].search(
                [
                    ('barcode', '=', 'WH-OR-STOCK'),
                    ('company_id', '=', operations_company_id)
                ]
            )

            picking_type = self.env['stock.picking.type'].search(
                [
                    ('barcode', '=', 'WH-INTERNAL'),
                    ('company_id', '=', operations_company_id)
                ]
            )
        elif operations_company_id == 6:
            stock_location = self.env['stock.location'].search(
                [
                    ('barcode', '=', 'MODAI-STOCK'),
                    ('company_id', '=', operations_company_id)
                ]
            )

            picking_type = self.env['stock.picking.type'].search(
                [
                    ('barcode', '=', 'ORYI-INTERNAL'),
                    ('company_id', '=', operations_company_id)
                ]
            )
        elif operations_company_id == 8:
            stock_location = self.env['stock.location'].search(
                [
                    ('barcode', '=', 'EFFEC-STOCK'),
                    ('company_id', '=', operations_company_id)
                ]
            )

            picking_type = self.env['stock.picking.type'].search(
                [
                    ('barcode', '=', 'EFFEC-INTERNAL'),
                    ('company_id', '=', operations_company_id)
                ]
            )

        if not sorter_location or not stock_location or not picking_type:
            raise Warning(
                "No se ha encontrado 'sorter_location' / 'stock_location' / 'picking_type' para la compañia %s" % (
                    operations_company_id))

        selected_picking_stock_move_lines = []

        for line in records.move_line_ids_without_package:
            pick_line_values = {
                'name': line.product_id.name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_uom_qty,
                'product_uom': line.product_id.uom_id.id,
                'state': 'draft',
                'company_id': operations_company_id,
            }
            selected_picking_stock_move_lines.append((0, 0, pick_line_values))

        internal_stock_transfer = {
            'location_id': stock_location.id,
            'location_dest_id': sorter_location.id,
            'move_type': 'direct',
            'picking_type_id': picking_type.id,
            'company_id': operations_company_id,
            'move_lines': selected_picking_stock_move_lines,
        }

        operation_type = ''
        outer_sorter = '1'
        inner_sorter = '2'

        # 49
        outer_layout = [
            '0003', '0005', '0007', '0009', '0011', '0013', '0015', '0017',
            '0019', '0021', '0023', '0025', '0027', '0029', '0031', '0033',
            '0035', '0037', '0039', '0041', '0043', '0045', '0047', '0049',
            '0051', '0053', '0055', '0057', '0059', '0061', '0063', '0065',
            '0085', '0086', '0087', '0088', '0089', '0090', '0091', '0092',
            '0093', '0094', '0095', '0096', '0097', '0098', '0099', '0100',
            '0101'
        ]

        # 50 (0084 is part of Inner Sorter? in 2015 files it is)
        inner_layout = [
            '0004', '0006', '0008', '0010', '0012', '0014', '0016', '0018',
            '0020', '0022', '0024', '0026', '0028', '0030', '0032', '0034',
            '0036', '0038', '0040', '0042', '0044', '0046', '0048', '0050',
            '0052', '0054', '0056', '0058', '0060', '0062', '0064', '0066',
            '0067', '0068', '0069', '0070', '0071', '0072', '0073', '0074',
            '0075', '0076', '0077', '0078', '0079', '0080', '0081', '0082',
            '0083', '0084'
        ]

        if records.mapped('picking_type_id.code')[0] == 'incoming':
            operation_type = 'RETURNS'
        else:
            operation_type = 'ORDERS'

        inner_picking_ids = []
        outer_picking_ids = []
        for index, picking in enumerate(records):
            # if index > 48 it's for 'outer' sorter
            if index > 49:
                outer_picking_ids.append(picking.id)
            else:
                inner_picking_ids.append(picking.id)

        def get_product_data_from_id(product_id):
            product_product = self.env['product.product'].search([('id', '=', product_id)])
            return (product_product.style_code, product_product.size_attribute_id.name, product_product.barcode,
                    product_product.product_collection_id.name)

        if len(inner_picking_ids) > 0:
            inner_pickings = self.env['stock.picking'].search([('id', 'in', inner_picking_ids)])

            id_batch = self.env['sorter.batch'].create({
                'company_id': operations_company_id,
                'picking_ids': inner_pickings.ids,
                'sorter_operation_type': operation_type,
                'sorter_location': 'inner'
            })

            batch_digits = id_batch.name_seq.replace("SOR", "")

            picking_identifiers = {}
            inner_layout_text = ''

            order_name = "{}0000{}".format(operation_type, batch_digits)
            order_id = "OT0{}".format(batch_digits)

            for index, picking in enumerate(inner_pickings):
                order_batch_id = "OL{}{}".format(batch_digits, inner_layout[index][1:])

                picking_name = picking.name.replace('/', '-')

                if picking.name not in picking_identifiers:
                    picking_identifiers.update({picking.name: "{}".format(order_batch_id)})

                inner_layout_text += "{};{};{};{};{}\n".format(
                    order_name,
                    order_id,
                    inner_sorter,
                    inner_layout[index],
                    picking_name
                    # order_batch_id
                )

            picking_lines_grouped = []

            picking_lines_grouped += inner_pickings.move_line_ids_without_package.read_group(
                [('id', 'in', inner_pickings.move_line_ids_without_package.ids)],
                ['reference', 'product_id', 'product_uom_qty'],
                ['reference', 'product_id'],
                lazy=False
            )

            # inner_batch_file_content = []
            inner_batch_text = ''
            for line in picking_lines_grouped:
                if line['reference'] in picking_identifiers:
                    order_batch_id_value = picking_identifiers.get(line['reference'])
                    data = get_product_data_from_id(line['product_id'][0])

                    picking_name = line['reference'].replace('/', '-')

                    inner_batch_text += "{};{};{};{};1;Y;{};{};{};1;0;0;1;{};{};{};{};{};{};{}\n".format(
                        order_id,
                        operation_type,
                        order_name,
                        inner_sorter,
                        data[2],
                        int(line['product_uom_qty']),
                        picking_name,
                        # order_batch_id_value,
                        data[2],
                        order_id,
                        f'{data[0]} - {data[1]} ({data[3]})',
                        data[0],
                        data[1],
                        data[1],
                        picking_name
                        # order_batch_id_value
                    )

            # Crear el adjunto LAYOUT
            attachment = self.env['ir.attachment'].create({
                'name': f'LAY_{order_name}.DAT',
                'type': 'binary',
                'datas': base64.b64encode(inner_layout_text.encode('utf-8')).decode('utf-8'),
                'res_model': id_batch._name,
                'res_id': id_batch.id,
                'mimetype': 'text/plain'
            })

            # Crear el adjunto BATCH
            attachment2 = self.env['ir.attachment'].create({
                'name': f'BAT_000000000000{order_id}001.DAT',
                'type': 'binary',
                'datas': base64.b64encode(inner_batch_text.encode('utf-8')).decode('utf-8'),
                'res_model': id_batch._name,
                'res_id': id_batch.id,
                'mimetype': 'text/plain'
            })

            # Añadir un mensaje con el adjunto
            id_batch.message_post(
                body="Adjuntados archivos de Layout y batch.",
                attachment_ids=[attachment.id, attachment2.id]
            )

        if len(outer_picking_ids) > 0:
            outer_pickings = self.env['stock.picking'].search([('id', 'in', outer_picking_ids)])

            id_batch = self.env['sorter.batch'].create({
                'company_id': operations_company_id,
                'picking_ids': outer_pickings.ids,
                'sorter_operation_type': operation_type,
                'sorter_location': 'outer'
            })

            batch_digits = id_batch.name_seq.replace("SOR", "")

            picking_identifiers = {}
            # outer_layout_file_content = []
            outer_layout_text = ''

            order_name = "{}0000{}".format(operation_type, batch_digits)
            order_id = "OT0{}".format(batch_digits)

            for index, picking in enumerate(outer_pickings):
                order_batch_id = "OL{}{}".format(batch_digits, outer_layout[index][1:])

                picking_name = picking.name.replace('/', '-')

                if picking.name not in picking_identifiers:
                    picking_identifiers.update({picking.name: "{}".format(order_batch_id)})

                outer_layout_text += "{};{};{};{};{}\n".format(
                    order_name,
                    order_id,
                    outer_sorter,
                    outer_layout[index],
                    picking_name
                    # order_batch_id
                )

            picking_lines_grouped = []

            picking_lines_grouped += outer_pickings.move_line_ids_without_package.read_group(
                [('id', 'in', outer_pickings.move_line_ids_without_package.ids)],
                ['reference', 'product_id', 'product_uom_qty'],
                ['reference', 'product_id'],
                lazy=False
            )

            # outer_batch_file_content = []
            outer_batch_text = ''
            for line in picking_lines_grouped:
                if line['reference'] in picking_identifiers:
                    order_batch_id_value = picking_identifiers.get(line['reference'])
                    data = get_product_data_from_id(line['product_id'][0])

                    picking_name = line['reference'].replace('/', '-')

                    outer_batch_text += "{};{};{};{};1;Y;{};{};{};1;0;0;1;{};{};{};{};{};{};{}\n".format(
                        order_id,
                        operation_type,
                        order_name,
                        outer_sorter,
                        data[2],
                        int(line['product_uom_qty']),
                        picking_name,
                        # order_batch_id_value,
                        data[2],
                        order_id,
                        f'{data[0]} - {data[1]} ({data[3]})',
                        data[0],
                        data[1],
                        data[1],
                        picking_name
                        # order_batch_id_value
                    )

            # Crear el adjunto LAYOUT
            attachment3 = self.env['ir.attachment'].create({
                'name': f'LAY_{order_name}.DAT',
                'type': 'binary',
                'datas': base64.b64encode(outer_layout_text.encode('utf-8')).decode('utf-8'),
                'res_model': id_batch._name,
                'res_id': id_batch.id,
                'mimetype': 'text/plain'
            })

            # Crear el adjunto BATCH
            attachment4 = self.env['ir.attachment'].create({
                'name': f'BAT_000000000000{order_id}001.DAT',
                'type': 'binary',
                'datas': base64.b64encode(outer_batch_text.encode('utf-8')).decode('utf-8'),
                'res_model': id_batch._name,
                'res_id': id_batch.id,
                'mimetype': 'text/plain'
            })

            # Añadir un mensaje con el adjunto
            id_batch.message_post(
                body="Adjuntados archivos de Layout y batch.",
                attachment_ids=[attachment3.id, attachment4.id]
            )

        transfer = self.env['stock.picking'].sudo().create(internal_stock_transfer)
        if transfer:
            records.do_unreserve()
            records.write({'location_id': sorter_location.id})
            transfer.action_confirm()
            transfer.action_assign()
        else:
            raise ValidationError(_("No se ha podido generar la transferencia INT."))


    def create_transfer_for_batch(self, records):
        # if len(records) > 400:
        #     raise UserError("No se puede crear archivos para más de 400 operaciones.")

        if len(set(records.mapped('picking_type_id'))) > 1:
            raise UserError("No se puede seleccionar más de 1 tipo de operación diferente.")

        if len(set(records.mapped('state'))) == 1 and records.mapped('state')[0] != 'assigned':
            raise UserError("Solo se puede generar archivos de operaciones 'En Curso'.")

        if len(set(records.mapped('state'))) > 1:
            raise UserError("Las operaciones seleccionadas tienen ESTADOS diferentes.")

        if len(set(records.mapped('company_id'))) > 1:
            raise UserError("Las operaciones seleccionadas pertenecen a COMPAÑIAS diferentes.")

        operations_company_id = records.mapped('company_id')[0].id

        sorter_location = self.env['stock.location'].search(
            [
                ('barcode','=', 'SORTER'),
                ('company_id', '=', operations_company_id)
            ]
        )
        stock_location = None
        picking_type = None

        if operations_company_id == 1:
            stock_location = self.env['stock.location'].search(
                [
                    ('barcode', '=', 'WH-OR-STOCK'),
                    ('company_id', '=', operations_company_id)
                ]
            )

            picking_type = self.env['stock.picking.type'].search(
                [
                    ('barcode', '=', 'WH-INTERNAL'),
                    ('company_id', '=', operations_company_id)
                ]
            )
        elif operations_company_id == 6:
            stock_location = self.env['stock.location'].search(
                [
                    ('barcode', '=', 'MODAI-STOCK'),
                    ('company_id', '=', operations_company_id)
                ]
            )

            picking_type = self.env['stock.picking.type'].search(
                [
                    ('barcode', '=', 'ORYI-INTERNAL'),
                    ('company_id', '=', operations_company_id)
                ]
            )
        elif operations_company_id == 8:
            stock_location = self.env['stock.location'].search(
                [
                    ('barcode', '=', 'EFFEC-STOCK'),
                    ('company_id', '=', operations_company_id)
                ]
            )

            picking_type = self.env['stock.picking.type'].search(
                [
                    ('barcode', '=', 'EFFEC-INTERNAL'),
                    ('company_id', '=', operations_company_id)
                ]
            )

        if not sorter_location or not stock_location or not picking_type:
            raise Warning(
                "No se ha encontrado 'sorter_location' / 'stock_location' / 'picking_type' para la compañia %s" % (
                    operations_company_id))

        selected_picking_stock_move_lines = []

        for line in records.move_line_ids_without_package:
            pick_line_values = {
                'name': line.product_id.name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_uom_qty,
                'product_uom': line.product_id.uom_id.id,
                'state': 'draft',
                'company_id': operations_company_id,
            }
            selected_picking_stock_move_lines.append((0, 0, pick_line_values))

        internal_stock_transfer = {
            'location_id': stock_location.id,
            'location_dest_id': sorter_location.id,
            'move_type': 'direct',
            'picking_type_id': picking_type.id,
            'company_id': operations_company_id,
            # 'origin': records[0].carrier_id.name if records[0].carrier_id and 'DP-' in records[0].origin else "",
            'origin': records[0].batch_id.name if records[0].batch_id else "",
            'move_lines': selected_picking_stock_move_lines,
        }

        transfer = self.env['stock.picking'].sudo().create(internal_stock_transfer)
        if transfer:
            records.do_unreserve()
            records.write({'location_id': sorter_location.id})
            transfer.action_confirm()
            transfer.action_assign()
        else:
            raise Warning(_("No se ha podido generar la transferencia INT."))
