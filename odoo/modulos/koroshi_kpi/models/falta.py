# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI KPI v1.3 - Faltas por dia: lo que piden los pedidos de tienda y no se ha cogido, una fila por
# OUT, articulo y motivo (lo mismo que sale abajo del todo en el Monitor picking, pero guardado por dia).
#
# OUT del dia = OUT de PED. TIENDAS creadas ese dia (hora de Madrid) que no son pedido pendiente de otra
# (sin backorder_id); lo que quedo en sus pedidos pendientes (backorders) cuenta en la OUT de origen.
# Motivos:
#   sin_stock  = lo pide el pedido y no esta reservado (no hay en stock): al validar va a pedido pendiente
#   no_cogido  = habia stock (reservado) pero no se ha cogido; solo en OUT parciales (algo cogido y sin
#                cerrar caja hace mas de PARADA_MIN) o validadas: no encontrado en el hueco
#   pendiente  = ya validada la OUT: lo que falto esta en su pedido pendiente (backorder) esperando stock
#   cancelado  = ya validada la OUT sin pedido pendiente (o pendiente cancelado): no se sirve
# Solo escribe en su tabla (koroshi.kpi.falta): no toca albaranes, stock ni productos.
# =============================================================================
import datetime

import pytz

from odoo import api, fields, models

from .kpi import COMPANY_ID, TZ, tipo_producto

TIPO_PEDIDO = 'PED. TIENDAS'
PARADA_MIN = 20         # igual que el Monitor: sin cerrar caja en estos minutos = parada


class KoroshiKpiFalta(models.Model):
    _name = 'koroshi.kpi.falta'
    _description = 'KOROSHI faltas por dia'
    _order = 'fecha desc, out, referencia'

    fecha = fields.Date('Día', required=True, index=True)
    picking_id = fields.Many2one('stock.picking', 'OUT', ondelete='cascade', index=True)
    out = fields.Char('Nº OUT')
    tienda = fields.Char('Tienda')
    pedido = fields.Char('Pedido')
    estado = fields.Selection([('hecha', 'Validada'), ('curso', 'Cogiéndose'), ('parcial', 'Parcial'),
                               ('pend', 'Sin empezar')], 'Estado OUT')
    product_id = fields.Many2one('product.product', 'Artículo')
    referencia = fields.Char('Referencia')
    tipo = fields.Char('Tipo', help='Letras 5 y 6 de la referencia: 2621PT40-... = PT')
    pedidas = fields.Float('Uds pedidas', digits=(16, 0), help='Lo que pide el pedido de este artículo en esta OUT')
    servidas = fields.Float('Uds cogidas', digits=(16, 0), help='Lo cogido o servido de este artículo en esta OUT')
    faltan = fields.Float('Uds que faltan', digits=(16, 0))
    motivo = fields.Selection([('sin_stock', 'Sin stock'), ('no_cogido', 'No cogido (había stock)'),
                               ('pendiente', 'En pedido pendiente'), ('cancelado', 'No servido (cancelado)')],
                              'Motivo')
    pendiente_out = fields.Char('Pedido pendiente', help='OUT pendiente (backorder) donde ha quedado lo que falta')
    recalculado = fields.Datetime('Recalculado el')

    @api.model
    def _rango_utc(self, dia):
        tz = pytz.timezone(TZ)
        ini = tz.localize(datetime.datetime.combine(dia, datetime.time.min)).astimezone(pytz.utc).replace(tzinfo=None)
        return ini, ini + datetime.timedelta(days=1)

    @api.model
    def recalcular_dia(self, dia):
        """Borra y vuelve a sacar las faltas de un dia (solo esta tabla)."""
        Pick = self.env['stock.picking'].sudo()
        Falta = self.sudo()
        ini, fin = self._rango_utc(dia)
        raices = Pick.search([('company_id', '=', COMPANY_ID), ('picking_type_code', '=', 'outgoing'),
                              ('state', '!=', 'cancel'), ('backorder_id', '=', False),
                              ('sale_id.s_order_type_id.name', '=', TIPO_PEDIDO),
                              ('create_date', '>=', ini), ('create_date', '<', fin)])
        # Cada OUT con sus pedidos pendientes (backorders, y los pendientes de estos)
        raiz_de = dict([(p.id, p.id) for p in raices])
        nivel = raices
        while nivel:
            hijos = Pick.search([('backorder_id', 'in', nivel.ids)])
            for h in hijos:
                raiz_de[h.id] = raiz_de[h.backorder_id.id]
            nivel = hijos.filtered(lambda h: h.id not in nivel.ids)
        todos = Pick.browse(list(raiz_de.keys()))

        # Estado de cada OUT (como el Monitor): validada, cogiendose, parcial (parada) o sin empezar
        ahora = fields.Datetime.now()
        leido = {}
        ultima = {}
        for ml in self.env['stock.move.line'].sudo().search([('picking_id', 'in', raices.ids), ('qty_done', '>', 0)]):
            pid = ml.picking_id.id
            leido[pid] = leido.get(pid, 0.0) + ml.qty_done
            w = ml.result_package_id and ml.result_package_id.create_date or ml.write_date
            if w and (pid not in ultima or w > ultima[pid]):
                ultima[pid] = w
        hoy = datetime.datetime.now(pytz.timezone(TZ)).date()
        estado = {}
        for p in raices:
            if p.state == 'done':
                estado[p.id] = 'hecha'
            elif leido.get(p.id):
                parada = dia < hoy or not ultima.get(p.id) or \
                    (ahora - ultima[p.id]).total_seconds() > PARADA_MIN * 60
                estado[p.id] = parada and 'parcial' or 'curso'
            else:
                estado[p.id] = 'pend'

        # Por OUT de origen y articulo: pedido, cogido y lo que falta por motivo
        datos = {}
        for m in self.env['stock.move'].sudo().search([('picking_id', 'in', todos.ids)]):
            pk = m.picking_id
            raiz = raiz_de[pk.id]
            d = datos.setdefault((raiz, m.product_id.id), {'pedidas': 0.0, 'servidas': 0.0, 'faltas': {},
                                                           'pendiente': ''})
            q = m.product_uom_qty
            hecho = m.quantity_done or 0.0
            d['pedidas'] += q
            if m.state == 'cancel':
                motivo, falta = 'cancelado', q
            elif m.state == 'done':
                d['servidas'] += hecho
                continue
            elif pk.id != raiz:
                motivo, falta = 'pendiente', max(q - hecho, 0.0)
                d['servidas'] += hecho
                d['pendiente'] = pk.name
            else:
                d['servidas'] += hecho
                disp = max(m.reserved_availability or 0.0, hecho)
                sin = max(q - disp, 0.0)
                if sin > 0.001:
                    d['faltas']['sin_stock'] = d['faltas'].get('sin_stock', 0.0) + sin
                if estado[raiz] in ('parcial', 'hecha'):
                    motivo, falta = 'no_cogido', max(q - hecho, 0.0) - sin
                else:
                    continue
            if falta > 0.001:
                d['faltas'][motivo] = d['faltas'].get(motivo, 0.0) + falta

        Falta.search([('fecha', '=', dia)]).unlink()
        vals = []
        cuando = fields.Datetime.now()
        Prod = self.env['product.product'].sudo()
        for (raiz, prod_id), d in datos.items():
            if not d['faltas']:
                continue
            p = Pick.browse(raiz)
            prod = Prod.browse(prod_id)
            for motivo, falta in d['faltas'].items():
                vals.append({
                    'fecha': dia, 'picking_id': raiz, 'out': p.name.replace('EFFEC/OUT/', ''),
                    'tienda': (p.partner_id.name or '').split(', ')[-1], 'pedido': p.origin or '',
                    'estado': estado[raiz], 'product_id': prod_id,
                    'referencia': prod.default_code or prod.name or '', 'tipo': tipo_producto(prod),
                    'pedidas': d['pedidas'], 'servidas': d['servidas'], 'faltan': falta, 'motivo': motivo,
                    'pendiente_out': motivo == 'pendiente' and d['pendiente'].replace('EFFEC/OUT/', '') or False,
                    'recalculado': cuando,
                })
        if vals:
            Falta.create(vals)
        return len(vals)

    @api.model
    def action_recalcular_hoy(self):
        """Menu 'Recalcular faltas de hoy': saca las de hoy y ayer y abre la lista."""
        hoy = datetime.datetime.now(pytz.timezone(TZ)).date()
        for d in (hoy - datetime.timedelta(days=1), hoy):
            self.recalcular_dia(d)
        return self.env.ref('koroshi_kpi.action_koroshi_kpi_falta').read()[0]
