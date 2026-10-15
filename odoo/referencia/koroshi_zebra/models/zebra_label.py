# -*- coding: utf-8 -*-
import io
import re

from odoo import api, fields, models

SEQUENCE_CODE = 'zebra.label.code'

# Medidas físicas de la etiqueta
PAGE_W_MM = 110.0
PAGE_H_MM = 150.0


class ZebraLabel(models.Model):
    _name = 'zebra.label'
    _description = 'Etiqueta Zebra (secuencial CJ...)'
    _order = 'id desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Código',
        required=True,
        copy=False,
        readonly=True,
        index=True,
    )
    sequence_number = fields.Integer(
        string='Número secuencial',
        readonly=True,
        help='Sólo la parte numérica del código, útil para ordenar/buscar.',
    )
    state = fields.Selection(
        [('draft', 'Pendiente'), ('printed', 'Impresa')],
        string='Estado',
        default='draft',
        readonly=True,
    )
    print_date = fields.Datetime(string='Fecha de impresión', readonly=True)
    note = fields.Char(string='Nota / Lote')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Ya existe una etiqueta con ese código.'),
    ]

    # ------------------------------------------------------------------
    # Secuencia / creación
    # ------------------------------------------------------------------
    @api.model
    def _get_next_code(self):
        return self.env['ir.sequence'].next_by_code(SEQUENCE_CODE)

    @api.model
    def _numeric_part(self, code):
        match = re.search(r'(\d+)$', code or '')
        return int(match.group(1)) if match else 0

    @api.model
    def create_next_labels(self, quantity=1, note=False):
        labels = self.browse()
        for _i in range(quantity):
            code = self._get_next_code()
            labels += self.create({
                'name': code,
                'sequence_number': self._numeric_part(code),
                'note': note,
            })
        return labels

    # ------------------------------------------------------------------
    # Generación del PDF (ReportLab, tamaño exacto, sin wkhtmltopdf)
    # ------------------------------------------------------------------
    def build_pdf(self):
        """Devuelve los bytes de un PDF con una etiqueta por página,
        a exactamente 110 x 150 mm, independiente de wkhtmltopdf."""
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.graphics.barcode import createBarcodeDrawing
        from reportlab.graphics import renderPDF

        buf = io.BytesIO()
        page_w = PAGE_W_MM * mm
        page_h = PAGE_H_MM * mm
        c = canvas.Canvas(buf, pagesize=(page_w, page_h))

        left = 4 * mm
        content_w = page_w - 2 * left
        center_x = page_w / 2.0

        def fit_font(text, font, max_size, max_width, min_size=8):
            size = max_size
            while size > min_size and c.stringWidth(text, font, size) > max_width:
                size -= 1
            return size

        for rec in self:
            code = rec.name or ''

            # --- Recuadro "VALIDAR ETIQUETA" ---
            box_h = 16 * mm
            box_bottom = 129 * mm
            c.setLineWidth(1.4)
            c.rect(left, box_bottom, content_w, box_h, stroke=1, fill=0)
            tsize = fit_font('VALIDAR ETIQUETA', 'Helvetica-Bold', 22, content_w - 4 * mm)
            c.setFont('Helvetica-Bold', tsize)
            c.drawCentredString(center_x, box_bottom + box_h / 2.0 - tsize * 0.35,
                                'VALIDAR ETIQUETA')

            # --- Regla negra gruesa ---
            c.setFillColorRGB(0, 0, 0)
            c.rect(left, 126 * mm, content_w, 2 * mm, stroke=0, fill=1)

            # --- Código grande ---
            csize = fit_font(code, 'Helvetica-Bold', 34, content_w)
            c.setFont('Helvetica-Bold', csize)
            c.drawCentredString(center_x, 116 * mm, code)

            # --- Código de barras Code128 (vector) ---
            bar_bottom = 44 * mm
            bar_h = 68 * mm
            drawing = createBarcodeDrawing(
                'Code128', value=code, width=content_w, height=bar_h,
                humanReadable=False, quiet=False,
            )
            renderPDF.draw(drawing, c, left, bar_bottom)

            # --- Código repetido debajo del barcode ---
            c.setFont('Helvetica-Bold', 11)
            c.drawCentredString(center_x, 37 * mm, code)

            # --- "(NO TAPAR!!!)" ---
            fsize = fit_font('(NO TAPAR!!!)', 'Helvetica-Bold', 22, content_w)
            c.setFont('Helvetica-Bold', fsize)
            c.drawCentredString(center_x, 13 * mm, '(NO TAPAR!!!)')

            c.showPage()

        c.save()
        return buf.getvalue()

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------
    def action_print(self):
        """Marca como impresas y abre el PDF (tamaño exacto) en una pestaña."""
        self.write({
            'state': 'printed',
            'print_date': fields.Datetime.now(),
        })
        ids_str = ','.join(str(i) for i in self.ids)
        return {
            'type': 'ir.actions.act_url',
            'url': '/koroshi_zebra/print?ids=%s' % ids_str,
            'target': 'new',
        }

    def action_reset_draft(self):
        self.write({'state': 'draft', 'print_date': False})
