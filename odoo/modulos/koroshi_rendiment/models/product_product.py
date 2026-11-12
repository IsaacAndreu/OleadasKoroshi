# -*- coding: utf-8 -*-
from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _get_barcode_domain(self, sub_domain, domain):
        # product_multi_barcode/models/product_product.py:47-64 cambia cualquier
        # ('barcode', op, valor) por ('barcode_ids', 'in', <ids de product.barcode>).
        # Con ('barcode', '!=', False) carga los 463.120 codigos y hace un IN enorme:
        # 4,5 s para buscar 6 productos (la PDA lo hace en cada albaran, desde
        # stock_barcode_optimization.get_all_products_by_barcode).
        # product.product.barcode esta guardado y se calcula de barcode_ids: comprobado en
        # produccion (12/11/2026) que "barcode no vacio" == "tiene algun product.barcode"
        # en todos los productos (0 diferencias). Para ese caso se usa la columna directamente.
        # '= False' no se toca: el modulo OCA devuelve 0 productos y cambiarlo cambiaria
        # resultados en otros sitios.
        if sub_domain[1] == '!=' and sub_domain[2] in (False, None):
            return domain
        return super(ProductProduct, self)._get_barcode_domain(sub_domain, domain)
