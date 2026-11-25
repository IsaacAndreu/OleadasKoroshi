# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Transportista v1.2.0 - bultos de GLS en el envío agrupado = cajas distintas.
# delivery_gls_asm (custom_addons, _gls_asm_send_grouped_shipping) suma len(package_ids) OUT por OUT: una caja que
# está en dos OUT del mismo envío (Juntar cajas) se cuenta dos veces. K41 25/11: 7 cajas -> 8 etiquetas GLS.
# Con el contexto koroshi_gls_bultos=N (lo pone solo la pantalla Transportista) se manda N en <Bultos>. Sin el
# contexto (acción 1834 del portátil, cualquier otro uso) todo sigue igual. No cambia delivery_gls_asm ni añade campos.
# =============================================================================
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    def _gls_asm_send_grouped_shipping(self, gls_request, pickings):
        bultos = int(self.env.context.get('koroshi_gls_bultos') or 0)
        if bultos > 0:
            original = gls_request._send_shipping

            def enviar(vals):
                if vals.get('bultos') != bultos:
                    _logger.info('Transportista: GLS %s: bultos %s -> %s (cajas distintas)',
                                 vals.get('remite_departamento'), vals.get('bultos'), bultos)
                return original(dict(vals, bultos=bultos))
            gls_request._send_shipping = enviar
        return super(DeliveryCarrier, self)._gls_asm_send_grouped_shipping(gls_request, pickings)
