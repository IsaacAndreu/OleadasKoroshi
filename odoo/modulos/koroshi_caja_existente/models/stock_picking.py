# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Caja existente - put_in_pack(package_name) con una matricula CJ que ya existe.
#
# stock_barcode_optimization (Brain Station, custom_addons) hace:
#     put_in_pack(self, package_name=None): super().put_in_pack() (caja nueva) y despues
#     renombra la ultima caja de la OUT a package_name.
# Con una matricula ya usada eso crea una caja duplicada (la accion automatica 20 lo bloquea).
#
# Aqui, ANTES de llamar a Brain Station: si package_name es una CJ que ya existe y es de esta OUT,
# se meten las uds leidas sin caja en ESA caja (mismo reparto de lineas que stock._put_in_pack de Odoo 13)
# y no se llama al super. En cualquier otro caso se llama al super igual que antes.
# =============================================================================
import logging
import re

from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round

_logger = logging.getLogger(__name__)

COMPANY_ID = 8                              # EFFECTIVE LOGISTICS, S.L.
RE_CJ = re.compile(r'^CJ\d{9}$')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def put_in_pack(self, package_name=None):
        nombre = (package_name or '').strip().upper()
        if (nombre and len(self) == 1 and RE_CJ.match(nombre)
                and self.company_id.id == COMPANY_ID and self.picking_type_code == 'outgoing'):
            existentes = self.env['stock.quant.package'].sudo().search([('name', '=ilike', nombre)])
            existentes = existentes.filtered(lambda p: (p.name or '').strip().upper() == nombre)
            if existentes:
                return self._koroshi_anadir_a_caja(existentes, nombre)
        return super(StockPicking, self).put_in_pack(package_name=package_name)

    def _koroshi_anadir_a_caja(self, existentes, nombre):
        self.ensure_one()
        if len(existentes) > 1:
            raise UserError(_('La matricula %s esta repetida en %d cajas. Avisa al responsable; no se ha '
                              'cambiado nada.') % (nombre, len(existentes)))
        paquete = existentes
        if self.state in ('done', 'cancel'):
            raise UserError(_('La OUT %s ya esta validada o cancelada.') % self.name)

        # De quien es la caja: lineas (no canceladas) que la usan como destino y stock dentro
        usos = self.env['stock.move.line'].sudo().search([('result_package_id', '=', paquete.id),
                                                          ('state', '!=', 'cancel')])
        otras = usos.mapped('picking_id') - self
        if otras or paquete.quant_ids or not usos:
            if otras:
                o = otras[0]
                donde = _('es de la OUT %s (%s)') % (o.name, o.partner_id.name or '')
            elif paquete.quant_ids:
                donde = _('ya tiene stock en %s') % ', '.join(paquete.quant_ids.mapped('location_id.display_name')[:2])
            else:
                donde = _('ya existe y no es de esta OUT')
            _logger.info('KOROSHI CAJA EXISTENTE: %s rechazada en %s: %s', nombre, self.name, donde)
            raise UserError(_('La caja %s %s.\n\nNo se puede usar en %s. Lee una matricula nueva.\n'
                              'No se ha cambiado nada.') % (nombre, donde, self.name))

        # Lo mismo que mira stock_barcode_optimization: uds leidas sin caja
        lineas = self.move_line_ids_without_package.filtered(
            lambda ml: ml.qty_done > 0 and not ml.result_package_id and ml.state not in ('done', 'cancel'))
        if not lineas:
            raise UserError(_('No hay uds leidas sin caja en %s. Lee primero las prendas y despues la caja %s.')
                            % (self.name, nombre))
        destinos_caja = usos.mapped('location_dest_id')
        if destinos_caja and lineas.mapped('location_dest_id') != destinos_caja:
            raise UserError(_('Las prendas y la caja %s van a ubicaciones distintas. No se ha cambiado nada.') % nombre)

        # Reparto de lineas como stock.picking._put_in_pack de Odoo 13: lo leido entra en la caja,
        # lo que falta por leer se queda en una linea sin caja
        a_meter = self.env['stock.move.line']
        for ml in lineas:
            if float_compare(ml.qty_done, ml.product_uom_qty, precision_rounding=ml.product_uom_id.rounding) >= 0:
                a_meter |= ml
            else:
                falta = float_round(ml.product_uom_qty - ml.qty_done,
                                    precision_rounding=ml.product_uom_id.rounding, rounding_method='UP')
                hecho = ml.qty_done
                nueva = ml.copy(default={'product_uom_qty': 0, 'qty_done': hecho})
                ml.write({'product_uom_qty': falta, 'qty_done': 0.0})
                nueva.write({'product_uom_qty': hecho})
                a_meter |= nueva

        nivel = self.env['stock.package_level'].search([('picking_id', '=', self.id),
                                                        ('package_id', '=', paquete.id)], limit=1)
        valores = {'result_package_id': paquete.id}
        if nivel:
            valores['package_level_id'] = nivel.id
        a_meter.write(valores)

        uds = sum(a_meter.mapped('qty_done'))
        self.message_post(body=_('Caja existente %s: anadidas %d uds leidas en la PDA (%d lineas). '
                                 'No se ha creado ninguna caja nueva.') % (nombre, uds, len(a_meter)))
        _logger.info('KOROSHI CAJA EXISTENTE: %s -> %s, %d uds, %d lineas', self.name, nombre, uds, len(a_meter))
        return True
