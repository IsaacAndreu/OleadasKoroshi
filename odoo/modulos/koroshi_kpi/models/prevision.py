# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI KPI v1.8.0 (15/11/2026, auditoria 13/11 fase 7): previsión de cajas del día por volumen.
#
# Cada mañana (cron, 05:30 hora del almacén, después del reparto por zonas de las 05:00) y con el botón
# «Prever ahora» de la ficha: volumen de lo que queda por servir en las OUT abiertas (empresa 8, tipo de pedido de la
# ficha) ÷ 0,084 m³ × factor. El factor se calibra con los días anteriores de las fichas «Día completo».
# Por la noche, al recalcular, la ficha tiene las cajas reales y la desviación.
# Solo escribe en koroshi.kpi.dia (sus campos nuevos). El cálculo, en calculo_prevision.py (con tests).
# =============================================================================
import logging

from odoo import api, fields, models
from odoo.addons.koroshi_base import comun   # v1.9

from .. import calculo_prevision as cp
from .kpi import COMPANY_ID, tipo_producto

_logger = logging.getLogger(__name__)

P = 'koroshi_kpi.'
ESTADOS_ABIERTA = ('confirmed', 'waiting', 'assigned', 'partially_available')


class KoroshiKpiDiaPrevision(models.Model):
    _inherit = 'koroshi.kpi.dia'

    cajas_previstas = fields.Integer('Cajas previstas', readonly=True,
                                     help='v1.8: volumen de lo que quedaba por servir ÷ m³ por caja × factor')
    prevision_volumen = fields.Float('Volumen previsto (m³)', readonly=True, digits=(16, 3))
    prevision_uds = fields.Float('Uds previstas', readonly=True, digits=(16, 0))
    prevision_outs = fields.Integer('OUT abiertas al prever', readonly=True)
    prevision_uds_sin_volumen = fields.Float('Uds previstas con volumen por tipo', readonly=True, digits=(16, 0),
                                             help='Productos sin volumen en Odoo: litros de la tabla por tipo')
    prevision_factor = fields.Float('Factor de la previsión', readonly=True, digits=(16, 3), group_operator=False,
                                    help='Cajas reales ÷ (volumen ÷ m³ por caja), mediana de los días anteriores')
    prevision_dias = fields.Integer('Días calibrados', readonly=True, group_operator=False)
    prevision_el = fields.Datetime('Previsto el', readonly=True)
    desvio_prevision = fields.Float('Desviación de la previsión (%)', compute='_compute_desvio_prevision', store=True,
                                    group_operator=False, digits=(16, 1),
                                    help='+ = han salido más cajas de las previstas')

    @api.depends('cajas', 'cajas_previstas')
    def _compute_desvio_prevision(self):
        for r in self:
            d = cp.desvio(r.cajas, r.cajas_previstas) if r.cajas else None
            r.desvio_prevision = d or 0.0

    # ------------------------------------------------------------------ parámetros
    def _param_float(self, clave, defecto):
        try:
            return float(self.env['ir.config_parameter'].sudo().get_param(P + clave, defecto))
        except (TypeError, ValueError):
            return float(defecto)

    # ------------------------------------------------------------------ cálculo
    def _calibrar(self):
        """Factor con las fichas «Día completo» anteriores a esta (mismo tipo de pedido)."""
        self.ensure_one()
        dias = int(self._param_float('prevision_dias', 20))
        m3 = self._param_float('m3_caja', cp.M3_CAJA)
        fichas = self.search([('metodo', '=', 'mixto'), ('fecha', '<', self.fecha),
                              ('tipo_pedido', '=', self.tipo_pedido), ('cajas', '>', 0)],
                             order='fecha desc', limit=dias)
        return cp.factor_calibrado([(f.volumen_total, f.cajas) for f in fichas], m3)

    def _pendiente_abierto(self):
        """(volumen m³, uds, uds con volumen por tipo, nº OUT) de lo que queda por servir en las OUT abiertas."""
        self.ensure_one()
        # Primero las OUT y despues sus movimientos: con el filtro por picking_id.* en stock.move tardaba ~12 s
        # (medido el 15/11); asi, menos de 0,5 s.
        dom_out = [('company_id', '=', COMPANY_ID), ('picking_type_code', '=', 'outgoing'),
                   ('state', 'in', ESTADOS_ABIERTA)]
        if self.tipo_pedido:
            dom_out.append(('sale_id.s_order_type_id.name', '=', self.tipo_pedido))
        outs = self.env['stock.picking'].sudo().search(dom_out)
        pedido = {}
        # lo ya leído de esas OUT no hace falta cogerlo, pero sigue yendo en las cajas: se cuenta igual
        for g in self.env['stock.move'].sudo().read_group(
                [('picking_id', 'in', outs.ids), ('state', 'not in', ('done', 'cancel'))],
                ['product_id', 'product_uom_qty'], ['product_id'], lazy=False):
            pedido[g['product_id'][0]] = g['product_uom_qty']
        tipos = {}
        for t in self.env['koroshi.kpi.peso.tipo'].sudo().search([]):
            tipos[t.codigo] = t.litros or 3.0
        vol = uds = uds_tipo = 0.0
        for p in self.env['product.product'].sudo().with_context(active_test=False).browse(list(pedido)):
            q = pedido[p.id]
            uds += q
            if p.volume > 0:
                vol += p.volume * q
            else:
                vol += tipos.get(tipo_producto(p), 3.0) / 1000.0 * q
                uds_tipo += q
        return vol, uds, uds_tipo, len(outs)

    def action_prever(self):
        """Botón «Prever ahora» (y el cron): previsión con lo que hay abierto en este momento."""
        m3 = self._param_float('m3_caja', cp.M3_CAJA)
        for r in self:
            factor, n = r._calibrar()
            vol, uds, uds_tipo, n_outs = r._pendiente_abierto()
            r.write({
                'cajas_previstas': cp.cajas_previstas(vol, factor, m3),
                'prevision_volumen': vol, 'prevision_uds': uds, 'prevision_outs': n_outs,
                'prevision_uds_sin_volumen': uds_tipo, 'prevision_factor': factor, 'prevision_dias': n,
                'prevision_el': fields.Datetime.now(),
            })
        return True

    @api.model
    def ficha_de_hoy(self):
        hoy = comun.hoy_local()
        return self.search([('fecha', '=', hoy), ('metodo', '=', 'mixto')], limit=1) or \
            self.create({'fecha': hoy, 'metodo': 'mixto'})

    @api.model
    def cron_prever(self):
        """Cron de la mañana: previsión de hoy en la ficha «Día completo»."""
        ficha = self.ficha_de_hoy()
        ficha.action_prever()
        _logger.info('KOROSHI KPI: previsión de hoy %s: %d cajas (%.2f m³, %d OUT, factor %.3f de %d días)',
                     ficha.fecha, ficha.cajas_previstas, ficha.prevision_volumen, ficha.prevision_outs,
                     ficha.prevision_factor, ficha.prevision_dias)
        return True

    @api.model
    def action_abrir_hoy(self):
        """Menú «Previsión de cajas de hoy»: abre la ficha de hoy (si no tiene previsión, la calcula)."""
        ficha = self.ficha_de_hoy()
        if not ficha.prevision_el:
            ficha.action_prever()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Previsión de cajas de hoy',
            'res_model': 'koroshi.kpi.dia',
            'res_id': ficha.id,
            'view_mode': 'form',
            'views': [(self.env.ref('koroshi_kpi.view_koroshi_kpi_dia_form').id, 'form')],
            'target': 'current',
        }
