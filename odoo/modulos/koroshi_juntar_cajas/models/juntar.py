# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Juntar cajas v1.0.0 - meter una caja pequeña (CJ) dentro de otra del mismo pedido y tienda, desde la PDA.
# Diseño: bin/versiones/diseno-juntar-cajas-pda_2026-11-25.md (visto bueno de Isaac el 25/11/2026).
#
# Lo que mueve es lo mismo que la acción de servidor 1844 v5 («Juntar matrículas», en producción desde el 19/11):
#   - Caja pequeña y destino de la MISMA OUT: las líneas y el stock (quants) pasan a la caja destino.
#   - De OUT distintas (la pequeña ya validada): las líneas pasan a la caja destino; al escribir una línea validada
#     Odoo saca el stock de la caja pequeña y lo mete en la grande. Los package_level que se quedan vacíos se borran.
#   - Los bultos del pedido tienen que bajar exactamente en el número de cajas juntadas; si no, se deshace todo.
#   - number_of_packages de las OUT del pedido = cajas reales (cada caja cuenta en la OUT que lleva más uds).
# Además (diseño 25/11): no se junta si el pedido está SHIPPED en S4T, si alguna OUT va en un camión cerrado o si es
# de Zalando; si ya tiene etiqueta del transportista se avisa (hay que rehacerla) y queda una nota en el pedido.
# Cada junta queda en koroshi.juntar.registro (quién, qué, bultos y los ids movidos, para deshacer en la oficina).
# =============================================================================
import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.koroshi_base.comun import COMPANY_ID

from .. import logica

_logger = logging.getLogger(__name__)


class KoroshiJuntarRegistro(models.Model):
    _name = 'koroshi.juntar.registro'
    _description = 'KOROSHI Cajas juntadas (PDA)'
    _order = 'id desc'
    _rec_name = 'cj_pequena'

    fecha = fields.Datetime('Cuándo', default=fields.Datetime.now, readonly=True, index=True)
    employee_id = fields.Many2one('hr.employee', 'Operario', readonly=True)
    user_id = fields.Many2one('res.users', 'Usuario de Odoo', default=lambda self: self.env.uid, readonly=True)
    cj_pequena = fields.Char('Caja pequeña', readonly=True, index=True)
    cj_destino = fields.Char('Caja destino', readonly=True, index=True)
    pedido = fields.Char('Pedido', readonly=True, index=True)
    tienda = fields.Char('Tienda', readonly=True)
    uds = fields.Integer('Uds movidas', readonly=True)
    bultos_antes = fields.Integer('Bultos antes', readonly=True)
    bultos_despues = fields.Integer('Bultos después', readonly=True)
    aviso = fields.Char('Aviso', readonly=True)
    lineas_ids = fields.Char('Líneas movidas (ids)', readonly=True)
    quants_ids = fields.Char('Stock movido (ids de quants)', readonly=True)
    misma_out = fields.Boolean('Misma OUT', readonly=True)
    token = fields.Char('Token', readonly=True, index=True, copy=False,
                        help='Lo pone la PDA: si la misma junta llega dos veces (doble toque), no se repite.')

    # ------------------------------------------------------------------ lectura
    def _lineas(self, paquete):
        return self.env['stock.move.line'].sudo().search(
            [('result_package_id', 'in', paquete.ids), ('state', '!=', 'cancel'), ('qty_done', '>', 0)])

    def _outs_pedido(self, origen):
        return self.env['stock.picking'].sudo().search(
            [('origin', '=', origen), ('picking_type_code', '=', 'outgoing'), ('company_id', '=', COMPANY_ID),
             ('state', '!=', 'cancel')])

    def _bultos_pedido(self, origen):
        lin = self.env['stock.move.line'].sudo().search(
            [('picking_id', 'in', self._outs_pedido(origen).ids), ('result_package_id', '!=', False),
             ('state', '!=', 'cancel'), ('qty_done', '>', 0)])
        return len(lin.mapped('result_package_id'))

    @api.model
    def _tienda(self, partner):
        nombre = partner and partner.name or ''
        return nombre.split(', ')[-1]

    @api.model
    def _pedido_venta(self, origen):
        return self.env['sale.order'].sudo().search([('name', '=', origen)], limit=1)

    def _estado_pedido(self, origen):
        """Lo que no depende de la caja: SHIPPED, camión cerrado, Zalando, etiqueta."""
        so = self._pedido_venta(origen)
        outs = self._outs_pedido(origen)
        shipped = bool(so) and 'x_s4t_status' in so._fields and so.x_s4t_status == 'SHIPPED'
        en_cierre = False
        if 'koroshi.envio.cierre' in self.env and outs:
            en_cierre = bool(self.env['koroshi.envio.cierre'].sudo().search_count([('picking_ids', 'in', outs.ids)]))
        destino = so.partner_shipping_id if so else outs[:1].partner_id
        zalando = 'ZALANDO' in (destino.display_name or '').upper()
        con_etiqueta = outs.filtered(lambda p: p.carrier_tracking_ref)
        transportista = logica.transportista(' '.join(con_etiqueta.mapped('carrier_id.name')))
        return {'so': so, 'outs': outs, 'shipped': shipped, 'en_cierre': en_cierre, 'zalando': zalando,
                'etiqueta': bool(con_etiqueta), 'transportista': transportista}

    @api.model
    def info_caja(self, cj):
        """Lo que se enseña al leer una CJ: pedido, tienda, uds, OUT, zonas y las cajas del pedido. Solo lee."""
        cj = (cj or '').strip().upper()
        paquetes = self.env['stock.quant.package'].sudo().search([('name', '=', cj)])
        if len(paquetes) != 1:
            raise UserError(_('%s no es una caja cerrada.') % cj)
        lin = self._lineas(paquetes)
        if not lin:
            raise UserError(_('%s está vacía (¿ya juntada?).') % cj)
        outs = lin.mapped('picking_id')
        if outs.mapped('company_id').ids != [COMPANY_ID]:
            raise UserError(_('%s no es de esta empresa.') % cj)
        origenes = sorted(set(outs.mapped('origin')))
        origen = origenes[0] if len(origenes) == 1 else ''
        cajas = []
        if origen:
            todas = self.env['stock.move.line'].sudo().search(
                [('picking_id', 'in', self._outs_pedido(origen).ids), ('result_package_id', '!=', False),
                 ('state', '!=', 'cancel'), ('qty_done', '>', 0)])
            por_caja = {}
            for ml in todas:
                c = por_caja.setdefault(ml.result_package_id.name, {'uds': 0, 'zonas': set()})
                c['uds'] += ml.qty_done
                if ml.picking_id.batch_id:
                    c['zonas'].add(ml.picking_id.batch_id.name)
            for nombre in sorted(por_caja, key=lambda n: -por_caja[n]['uds']):
                uds = int(por_caja[nombre]['uds'])
                cajas.append({'cj': nombre, 'uds': uds, 'zonas': ', '.join(sorted(por_caja[nombre]['zonas'])),
                              'pequena': uds <= logica.MAX_UDS_PEQUENA})
        return {
            'cj': cj,
            'uds': int(sum(lin.mapped('qty_done'))),
            'pedido': origen or ', '.join(origenes),
            'tienda': self._tienda(outs[:1].partner_id),
            'outs': ['%s%s' % (p.name, '' if p.state == 'done' else ' (sin validar)') for p in outs],
            'zonas': ', '.join(sorted(set(outs.mapped('batch_id.name')))) or '-',
            'validada': all(l.state == 'done' for l in lin),
            'cajas_pedido': cajas,
        }

    # ------------------------------------------------------------------ comprobar
    def _comprobar(self, pequenas, destino):
        """(trabajo, errores, avisos, origen). trabajo = [(paquete pequeño, paquete destino, líneas)]. No cambia nada."""
        Paquete = self.env['stock.quant.package'].sudo()
        destino = (destino or '').strip().upper()
        pequenas = [c.strip().upper() for c in pequenas if (c or '').strip()]
        if not pequenas:
            raise UserError(_('Lee antes la caja pequeña.'))
        if not destino:
            raise UserError(_('Lee la caja destino (donde se mete la pequeña).'))
        pd = Paquete.search([('name', '=', destino)])
        ld = self._lineas(pd) if len(pd) == 1 else self.env['stock.move.line']
        trabajo, errores, avisos = [], [], []
        usadas = set()
        origen = ''
        for cj in pequenas:
            po = Paquete.search([('name', '=', cj)])
            lo = self._lineas(po) if len(po) == 1 else self.env['stock.move.line']
            ped_o = sorted(set(lo.mapped('picking_id.origin')))
            estado = self._estado_pedido(ped_o[0]) if len(ped_o) == 1 else {}
            otra_out = bool(set(lo.mapped('picking_id').ids) - set(ld.mapped('picking_id').ids))
            d = {
                'cj_o': cj, 'cj_d': destino,
                'n_paquetes_o': len(po), 'n_paquetes_d': len(pd),
                'uds_o': int(sum(lo.mapped('qty_done'))), 'uds_d': int(sum(ld.mapped('qty_done'))),
                'pedidos_o': ped_o, 'pedidos_d': sorted(set(ld.mapped('picking_id.origin'))),
                'tiendas_o': lo.mapped('picking_id.partner_id').ids, 'tiendas_d': ld.mapped('picking_id.partner_id').ids,
                'companias_o': lo.mapped('picking_id.company_id').ids, 'compania': COMPANY_ID,
                'otra_out': otra_out, 'o_sin_validar': bool(lo.filtered(lambda ml: ml.state != 'done')),
                'shipped': estado.get('shipped'), 'en_cierre': estado.get('en_cierre'),
                'zalando': estado.get('zalando'),
                'usada': 'origen' if cj in usadas else ('destino_vaciada' if destino in pequenas else None),
                'etiqueta': estado.get('etiqueta'), 'transportista': estado.get('transportista'),
            }
            usadas.add(cj)
            error = logica.error_pareja(d)
            if error:
                errores.append(error)
                continue
            for a in logica.avisos(d):
                if a not in avisos:
                    avisos.append(a)
            origen = ped_o[0]
            trabajo.append((po, pd, lo))
        return trabajo, errores, avisos, origen

    @api.model
    def previa(self, pequenas, destino):
        """Lo que pasará al pulsar «Juntar», sin cambiar nada: errores, avisos y bultos antes -> después."""
        trabajo, errores, avisos, origen = self._comprobar(pequenas, destino)
        res = {'ok': not errores, 'errores': errores, 'avisos': avisos, 'pedido': origen}
        if trabajo:
            antes = self._bultos_pedido(origen)
            info = self.info_caja(destino)
            res.update({
                'tienda': info['tienda'],
                'bultos_antes': antes,
                'bultos_despues': antes - len(trabajo),
                'pequenas': [{'cj': t[0].name, 'uds': int(sum(t[2].mapped('qty_done'))),
                              'zonas': ', '.join(sorted(set(t[2].mapped('picking_id.batch_id.name')))) or '-'}
                             for t in trabajo],
                'destino': {'cj': info['cj'], 'uds': info['uds'], 'zonas': info['zonas']},
            })
        return res

    # ------------------------------------------------------------------ juntar
    def _recalcular_bultos(self, origen):
        outs = self._outs_pedido(origen)
        lin = self.env['stock.move.line'].sudo().search(
            [('picking_id', 'in', outs.ids), ('result_package_id', '!=', False), ('state', '!=', 'cancel'),
             ('qty_done', '>', 0)])
        reparto = {}
        for ml in lin:
            caja = reparto.setdefault(ml.result_package_id.id, {})
            caja[ml.picking_id.id] = caja.get(ml.picking_id.id, 0) + ml.qty_done
        cambios = logica.bultos_por_out(reparto, set(lin.mapped('picking_id').ids),
                                        set(outs.filtered(lambda p: p.state == 'done').ids),
                                        {p.id: p.number_of_packages for p in outs})
        Out = self.env['stock.picking'].sudo()
        hechos = []
        for out_id, antes, despues in cambios:
            p = Out.browse(out_id)
            p.write({'number_of_packages': despues})
            hechos.append('%s: %d -> %d' % (p.name, antes, despues))
        return hechos

    @api.model
    def juntar(self, pequenas, destino, employee=None, token=''):
        """Junta de verdad. Todo o nada: si algo no cuadra, UserError y la ruta deshace (rollback)."""
        if token:
            hecho = self.sudo().search([('token', '=', token)], limit=1)
            if hecho:
                return {'ok': True, 'repetida': True, 'pedido': hecho.pedido, 'bultos_antes': hecho.bultos_antes,
                        'bultos_despues': hecho.bultos_despues, 'pequenas': [hecho.cj_pequena]}
        trabajo, errores, avisos, origen = self._comprobar(pequenas, destino)
        if errores:
            raise UserError('\n'.join(errores) + _('\nNo se ha cambiado nada.'))
        Quant = self.env['stock.quant'].sudo()
        antes = self._bultos_pedido(origen)
        registros = []
        for po, pd, lo in trabajo:
            quants = Quant.search([('package_id', '=', po.id)])
            uds = int(sum(lo.mapped('qty_done')))
            outs_destino = self._lineas(pd).mapped('picking_id')
            misma_out = not (set(lo.mapped('picking_id').ids) - set(outs_destino.ids))
            lineas_ids, quants_ids = list(lo.ids), list(quants.ids)
            if misma_out:
                lo.write({'result_package_id': pd.id})
                if quants:
                    quants.write({'package_id': pd.id})
            else:
                niveles = lo.mapped('package_level_id')
                lo.write({'result_package_id': pd.id, 'package_level_id': False})
                for nv in niveles:
                    if not nv.move_line_ids:
                        nv.unlink()
                for p in lo.mapped('picking_id'):
                    p.message_post(body=_('Juntar cajas (PDA): las %d uds de esta OUT van dentro de la caja %s, que '
                                          'es la que lleva la matrícula. El bulto se cuenta en la OUT que lleva más '
                                          'uds de esa caja.') % (uds, pd.name))
            if self._lineas(po) or Quant.search_count([('package_id', '=', po.id), ('quantity', '!=', 0)]):
                raise UserError(_('%s sigue teniendo líneas o stock. No se ha cambiado nada.') % po.name)
            registros.append({'cj_pequena': po.name, 'cj_destino': pd.name, 'uds': uds, 'misma_out': misma_out,
                              'lineas_ids': json.dumps(lineas_ids), 'quants_ids': json.dumps(quants_ids)})
        despues = self._bultos_pedido(origen)
        if not logica.cuadra(antes, despues, len(trabajo)):
            raise UserError(_('No cuadra: los bultos del pedido pasan de %d a %d y tenían que ser %d. '
                              'No se ha cambiado nada.') % (antes, despues, antes - len(trabajo)))
        cambios_bultos = self._recalcular_bultos(origen)
        estado = self._estado_pedido(origen)
        tienda = self._tienda(estado['outs'][:1].partner_id)
        aviso = ' '.join(avisos)
        for i, vals in enumerate(registros):
            vals.update({'pedido': origen, 'tienda': tienda, 'bultos_antes': antes, 'bultos_despues': despues,
                         'aviso': aviso, 'employee_id': employee.id if employee else False,
                         'token': token if i == 0 else False})
            self.sudo().create(vals)
        quien = employee.name if employee else self.env.user.name
        texto = _('Juntar cajas (PDA, %s): %s. Bultos del pedido: %d -> %d.') % (
            quien, '; '.join('%s (%d uds) metida en %s' % (r['cj_pequena'], r['uds'], r['cj_destino'])
                             for r in registros), antes, despues)
        if estado['etiqueta']:
            texto += _(' OJO: el pedido ya tenía etiqueta de %s: hay que rehacerla con %d bultos.') % (
                estado['transportista'] or 'transportista', despues)
        if estado['so']:
            estado['so'].message_post(body=texto)
        _logger.info('KOROSHI JUNTAR CAJAS: %s | %s', texto, ', '.join(cambios_bultos))
        return {'ok': True, 'pedido': origen, 'tienda': tienda, 'bultos_antes': antes, 'bultos_despues': despues,
                'pequenas': [r['cj_pequena'] for r in registros], 'destino': registros[0]['cj_destino'],
                'avisos': avisos, 'etiqueta': estado['etiqueta']}
