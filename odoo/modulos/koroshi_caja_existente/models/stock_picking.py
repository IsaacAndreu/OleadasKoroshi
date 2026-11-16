# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Caja existente - put_in_pack(package_name) con una matricula CJ que ya existe.
#
# stock_barcode_optimization (Brain Station, custom_addons) hace:
#     put_in_pack(self, package_name=None): super().put_in_pack() (caja nueva) y despues
#     renombra la ultima caja de la OUT a package_name.
# Con una matricula ya usada eso crea una caja duplicada (la accion automatica 20 lo bloquea).
#
# Aqui, ANTES de llamar a Brain Station, si package_name es una CJ que ya existe:
#   v1.0 - la caja es de ESTA OUT: las uds leidas sin caja entran en esa caja.
#   v1.3 - la caja es de OTRA OUT del MISMO pedido y la MISMA tienda (validada o no): las uds leidas van a esa
#          caja y ESTA OUT se valida como siempre. Al validar no cuenta esa caja como bulto suyo (0 bultos);
#          la caja cuenta en la OUT duena (la que la uso primero). No se cancela ninguna OUT ni se mueve nada
#          entre OUT (la v1.1/v1.2 cancelaba la OUT pequena y eso bloquea el sync S4T del pedido).
#          La OUT duena puede volver a leer su caja aunque ya tenga prendas en Clientes de la OUT pequena.
#   Otro pedido / otra tienda / caja con stock en almacen / OUT duena cancelada: error y no se cambia nada.
# En cualquier otro caso se llama al super igual que antes.
# =============================================================================
import logging

from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round
from odoo.addons.koroshi_base import comun   # v1.4: empresa y matricula CJ

_logger = logging.getLogger(__name__)

COMPANY_ID = comun.COMPANY_ID               # v1.4: de koroshi_base (EFFECTIVE LOGISTICS, S.L.)
RE_CJ = comun.RE_CJ                         # v1.4: la misma expresion (CJ + 9 cifras), de koroshi_base


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

    # ------------------------------------------------------------------ utilidades
    def _koroshi_dueno(self, paquete):
        """OUT duena de una caja: la de la primera linea (id mas bajo) que la usa como destino."""
        ml = self.env['stock.move.line'].sudo().search([('result_package_id', '=', paquete.id),
                                                        ('state', '!=', 'cancel')], order='id', limit=1)
        return ml.picking_id

    def _koroshi_mismo_pedido(self, otra):
        self.ensure_one()
        return (otra.company_id == self.company_id
                and otra.picking_type_id == self.picking_type_id
                and (otra.origin or '') == (self.origin or '') and self.origin
                and otra.partner_id == self.partner_id
                and otra.location_dest_id == self.location_dest_id)

    def _koroshi_lineas_leidas(self, nombre):
        lineas = self.move_line_ids_without_package.filtered(
            lambda ml: ml.qty_done > 0 and not ml.result_package_id and ml.state not in ('done', 'cancel'))
        if not lineas:
            raise UserError(_('No hay uds leidas sin caja en %s. Lee primero las prendas y despues la caja %s.')
                            % (self.name, nombre))
        # Reparto de lineas como stock.picking._put_in_pack de Odoo 13: lo leido queda en una linea propia,
        # lo que falta por leer se queda en otra linea sin caja
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
        return a_meter

    # ------------------------------------------------------------------ principal
    def _koroshi_anadir_a_caja(self, existentes, nombre):
        self.ensure_one()
        if len(existentes) > 1:
            raise UserError(_('La matricula %s esta repetida en %d cajas. Avisa al responsable; no se ha '
                              'cambiado nada.') % (nombre, len(existentes)))
        paquete = existentes
        if self.state in ('done', 'cancel'):
            raise UserError(_('La OUT %s ya esta validada o cancelada.') % self.name)

        usos = self.env['stock.move.line'].sudo().search([('result_package_id', '=', paquete.id),
                                                          ('state', '!=', 'cancel')])
        if not usos:
            _logger.info('KOROSHI CAJA EXISTENTE: %s rechazada en %s: sin uso', nombre, self.name)
            raise UserError(_('La caja %s ya existe y no es de ninguna OUT.\n\nNo se puede usar en %s. Lee una '
                              'matricula nueva.\nNo se ha cambiado nada.') % (nombre, self.name))
        dueno = self._koroshi_dueno(paquete)
        otras = usos.mapped('picking_id') - self
        # Todas las OUT que usan la caja tienen que ser del mismo pedido y tienda
        ajena = otras.filtered(lambda o: not self._koroshi_mismo_pedido(o))
        if ajena:
            o = dueno in ajena and dueno or ajena[0]
            _logger.info('KOROSHI CAJA EXISTENTE: %s rechazada en %s: es de %s (otro pedido/tienda)',
                         nombre, self.name, o.name)
            raise UserError(_('La caja %s es de la OUT %s (%s, pedido %s).\n\nNo es del mismo pedido y tienda que '
                              '%s (pedido %s). Lee una matricula de esta tienda.\nNo se ha cambiado nada.')
                            % (nombre, o.name, o.partner_id.name or '', o.origin or '-', self.name,
                               self.origin or '-'))
        # Stock de la caja: solo vale el que ya esta en la tienda (prendas de OUT pequenas ya validadas)
        if paquete.quant_ids.filtered(lambda q: q.location_id.usage != 'customer'):
            donde = ', '.join(paquete.quant_ids.mapped('location_id.display_name')[:2])
            raise UserError(_('La caja %s tiene stock en %s (no esta enviada a la tienda).\n\nNo se puede usar en %s. '
                              'Lee una matricula nueva.\nNo se ha cambiado nada.') % (nombre, donde, self.name))

        if dueno == self:
            # v1.0: caja de esta OUT (v1.3: aunque ya lleve prendas de una OUT pequena validada)
            return self._koroshi_meter_en_caja_propia(paquete, usos, nombre)

        # v1.3: caja de otra OUT del mismo pedido y tienda, validada o no
        if dueno.state == 'cancel':
            raise UserError(_('La OUT %s de la caja %s esta cancelada. No se ha cambiado nada.') % (dueno.name, nombre))
        return self._koroshi_meter_en_caja_ajena(paquete, dueno, nombre)

    def _koroshi_meter_en_caja_propia(self, paquete, usos, nombre):
        lineas = self._koroshi_lineas_leidas(nombre)
        destinos_caja = usos.mapped('location_dest_id')
        if destinos_caja and lineas.mapped('location_dest_id') != destinos_caja:
            raise UserError(_('Las prendas y la caja %s van a ubicaciones distintas. No se ha cambiado nada.') % nombre)
        nivel = self.env['stock.package_level'].search([('picking_id', '=', self.id),
                                                        ('package_id', '=', paquete.id)], limit=1)
        valores = {'result_package_id': paquete.id}
        if nivel:
            valores['package_level_id'] = nivel.id
        lineas.write(valores)
        uds = sum(lineas.mapped('qty_done'))
        self.message_post(body=_('Caja existente %s: anadidas %d uds leidas en la PDA (%d lineas). '
                                 'No se ha creado ninguna caja nueva.') % (nombre, uds, len(lineas)))
        _logger.info('KOROSHI CAJA EXISTENTE: %s -> %s, %d uds, %d lineas', self.name, nombre, uds, len(lineas))
        return True

    def _koroshi_meter_en_caja_ajena(self, paquete, dueno, nombre):
        """v1.3: la caja es de otra OUT (dueno) del mismo pedido y tienda, validada o no. Las uds leidas van a esa
        caja y esta OUT se valida como siempre: al validar no cuenta la caja como bulto suyo (bultos)."""
        lineas = self._koroshi_lineas_leidas(nombre)
        lineas.write({'result_package_id': paquete.id})
        uds = sum(lineas.mapped('qty_done'))
        estado = dueno.state == 'done' and 'ya validada' or 'sin validar'
        self.message_post(body=_('Caja existente %s (de %s, %s): %d uds leidas van a esa caja. Validad esta OUT '
                                 'como siempre: no cuenta como bulto suyo.') % (nombre, dueno.name, estado, uds))
        dueno.message_post(body=_('Caja %s: %d uds de %s van tambien en esta caja (PDA).') % (nombre, uds, self.name))
        _logger.info('KOROSHI CAJA EXISTENTE: %s -> caja %s de %s (%s), %d uds', self.name, nombre,
                     dueno.name, estado, uds)
        return True

    # ------------------------------------------------------------------ bultos
    # v1.2: en la v1.1 se corregia en action_done, pero la validacion de la PDA escribe number_of_packages DESPUES
    # (K8 10/11: OUT/24181 quedo con 1 bulto). Ahora se corrige en cada escritura del campo o del estado.
    def _koroshi_corregir_bultos(self):
        if 'number_of_packages' not in self._fields or self.env.context.get('koroshi_bultos'):
            return
        for p in self:
            if p.company_id.id != COMPANY_ID or p.picking_type_code != 'outgoing' or p.state != 'done':
                continue
            cajas = p.move_line_ids.mapped('result_package_id')
            ajenas = cajas.filtered(lambda k: p._koroshi_dueno(k) != p)
            if not ajenas:
                continue
            n = len(cajas - ajenas)
            if p.number_of_packages != n:
                _logger.info('KOROSHI CAJA EXISTENTE: %s bultos %s -> %d (cajas de otra OUT: %s)', p.name,
                             p.number_of_packages, n, ', '.join(ajenas.mapped('name')))
                p.with_context(koroshi_bultos=True).write({'number_of_packages': n})

    def action_done(self):
        res = super(StockPicking, self).action_done()
        self._koroshi_corregir_bultos()
        return res

    def write(self, vals):
        res = super(StockPicking, self).write(vals)
        if not self.env.context.get('koroshi_bultos') and ('number_of_packages' in vals or 'state' in vals
                                                            or 'date_done' in vals):
            self._koroshi_corregir_bultos()
        return res
