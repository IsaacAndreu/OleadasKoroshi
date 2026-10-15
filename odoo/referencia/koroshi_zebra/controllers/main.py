# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request, content_disposition


class KoroshiZebraController(http.Controller):

    @http.route('/koroshi_zebra/print', type='http', auth='user')
    def print_labels(self, ids=None, **kwargs):
        if not ids:
            return request.not_found()
        try:
            label_ids = [int(i) for i in ids.split(',') if i.strip()]
        except ValueError:
            return request.not_found()

        labels = request.env['zebra.label'].browse(label_ids).exists()
        if not labels:
            return request.not_found()

        pdf_content = labels.build_pdf()
        filename = 'etiquetas.pdf'
        if len(labels) == 1:
            filename = 'etiqueta_%s.pdf' % (labels.name or labels.id)

        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf_content)),
            # 'inline' = abre en el visor del navegador para imprimir; el
            # usuario también puede descargarlo desde ahí.
            ('Content-Disposition', content_disposition(filename).replace('attachment', 'inline', 1)),
        ]
        return request.make_response(pdf_content, headers=headers)
