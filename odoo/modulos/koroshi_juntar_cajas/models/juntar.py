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
# v1.1.0 (25/11): «Revisar caja» (contenido_caja, prenda_en_caja, previa_partir, partir, revisada_bien) y
#   _mover_lineas: las líneas validadas cambian de caja sin tocar el stock de los huecos ni las reservas.
# =============================================================================
import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.koroshi_base import comun, pda
from odoo.addons.koroshi_base.comun import COMPANY_ID

from .. import logica

_logger = logging.getLogger(__name__)


class KoroshiJuntarRegistro(models.Model):
    _name = 'koroshi.juntar.registro'
    _description = 'KOROSHI Cajas juntadas (PDA)'
    _order = 'id desc'
    _rec_name = 'cj_pequena'

    tipo = fields.Selection([('juntar', 'Juntar cajas'), ('partir', 'Revisar caja: pasada a otra CJ'),
                             ('revisar', 'Revisar caja: todo bien')], 'Qué', default='juntar', readonly=True,
                            index=True)   # v1.1.0
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
        estado_s4t = so.x_s4t_status if so and 'x_s4t_status' in so._fields else ''
        shipped = estado_s4t == 'SHIPPED'
        ready = estado_s4t == 'READY'       # v1.1.0: S4T ya tiene las cajas de antes (aviso)
        en_cierre = False
        if 'koroshi.envio.cierre' in self.env and outs:
            en_cierre = bool(self.env['koroshi.envio.cierre'].sudo().search_count([('picking_ids', 'in', outs.ids)]))
        destino = so.partner_shipping_id if so else outs[:1].partner_id
        zalando = 'ZALANDO' in (destino.display_name or '').upper()
        con_etiqueta = outs.filtered(lambda p: p.carrier_tracking_ref)
        transportista = logica.transportista(' '.join(con_etiqueta.mapped('carrier_id.name')))
        return {'so': so, 'outs': outs, 'shipped': shipped, 'ready': ready, 'en_cierre': en_cierre, 'zalando': zalando,
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
                'ready': estado.get('ready'),
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

    # ------------------------------------------------------------------ v1.1.0: mover sin tocar los huecos
    def _uds_en_paquete(self, paquete):
        """Uds de stock (quants) dentro de un paquete."""
        if not paquete:
            return 0.0
        return sum(self.env['stock.quant'].sudo().search([('package_id', '=', paquete.id)]).mapped('quantity'))

    def _mover_lineas(self, lineas, destino):
        """v1.1.0 (pedido de Isaac el 25/11: «moverlas entre caja y caja sin tocar el stock»). Pasa líneas ENTERAS a
        otra caja sin tocar el stock de los huecos ni las reservas:
        - Líneas sin validar: write normal de result_package_id (lo mismo que hace Lecturas al cerrar una caja).
        - Líneas validadas: Odoo 13, al escribir result_package_id en una línea hecha, la deshace (devuelve las uds al
          hueco), la vuelve a hacer (las saca otra vez) y llama a _free_reservation: si ese hueco estuviera
          sobrerreservado, quitaría la reserva a otras OUT. Aquí se cambia solo la caja de la línea en la base de
          datos y el stock se mueve en Clientes de un paquete al otro (stock.quant._update_available_quantity). Los
          package_level que quedan vacíos se borran, como en la acción 1844 v5.
        Devuelve las uds de líneas validadas que pasan (para comprobar los quants)."""
        Quant = self.env['stock.quant'].sudo()
        hechas = lineas.filtered(lambda ml: ml.state == 'done')
        pendientes = lineas - hechas
        niveles = lineas.mapped('package_level_id')
        if pendientes:
            pendientes.write({'result_package_id': destino.id, 'package_level_id': False})
        uds_hechas = 0.0
        for ml in hechas:
            q = ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id, rounding_method='HALF-UP')
            uds_hechas += q
            if ml.product_id.type != 'product':
                continue
            Quant._update_available_quantity(ml.product_id, ml.location_dest_id, -q, lot_id=ml.lot_id,
                                             package_id=ml.result_package_id, owner_id=ml.owner_id)
            Quant._update_available_quantity(ml.product_id, ml.location_dest_id, q, lot_id=ml.lot_id,
                                             package_id=destino, owner_id=ml.owner_id)
        if hechas:
            self.env.cr.execute(
                "UPDATE stock_move_line SET result_package_id = %s, package_level_id = NULL, write_uid = %s, "
                "write_date = (now() at time zone 'UTC') WHERE id IN %s",
                (destino.id, self.env.uid, tuple(hechas.ids)))
            hechas.invalidate_cache(['result_package_id', 'package_level_id'])
        niveles.invalidate_cache(['move_line_ids'])
        for nv in niveles.exists():
            if not nv.move_line_ids:
                nv.unlink()
        return uds_hechas

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
            stock_d = self._uds_en_paquete(pd)
            hechas = self._mover_lineas(lo, pd)     # v1.1.0: sin tocar los huecos
            if abs(self._uds_en_paquete(pd) - stock_d - hechas) > 0.001:
                raise UserError(_('El stock de %s no cuadra después de mover. No se ha cambiado nada.') % pd.name)
            if not misma_out:
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
        texto += self._texto_avisos(estado, despues)
        if estado['so']:
            estado['so'].message_post(body=texto)
        _logger.info('KOROSHI JUNTAR CAJAS: %s | %s', texto, ', '.join(cambios_bultos))
        return {'ok': True, 'pedido': origen, 'tienda': tienda, 'bultos_antes': antes, 'bultos_despues': despues,
                'pequenas': [r['cj_pequena'] for r in registros], 'destino': registros[0]['cj_destino'],
                'avisos': avisos, 'etiqueta': estado['etiqueta']}

    def _texto_avisos(self, estado, bultos):
        """v1.1.0: lo que se añade a la nota del pedido si ya tenía etiqueta o ya estaba READY en S4T."""
        texto = ''
        if estado['etiqueta']:
            texto += _(' OJO: el pedido ya tenía etiqueta de %s: hay que rehacerla con %d bultos.') % (
                estado['transportista'] or 'transportista', bultos)
        if estado.get('ready'):
            texto += _(' OJO: el pedido ya estaba READY en S4T con las cajas de antes: hay que volver a mandarlo '
                       '(acción 1960).')
        return texto

    # ================================================================== v1.1.0: «Revisar caja»
    def _caja_y_lineas(self, cj):
        cj = (cj or '').strip().upper()
        paquetes = self.env['stock.quant.package'].sudo().search([('name', '=', cj)])
        if len(paquetes) != 1:
            raise UserError(_('%s no es una caja cerrada.') % cj)
        lin = self._lineas(paquetes)
        if not lin:
            raise UserError(_('%s está vacía.') % cj)
        if lin.mapped('picking_id.company_id').ids != [COMPANY_ID]:
            raise UserError(_('%s no es de esta empresa.') % cj)
        return paquetes, lin

    @api.model
    def contenido_caja(self, cj):
        """Lo que hay dentro de una CJ según Odoo, por artículo. Solo lee."""
        paquete, lin = self._caja_y_lineas(cj)
        outs = lin.mapped('picking_id')
        origenes = sorted(set(outs.mapped('origin')))
        por_producto = {}
        for ml in lin:
            p = por_producto.setdefault(ml.product_id.id, {
                'product_id': ml.product_id.id, 'nombre': ml.product_id.display_name,
                'ean': ml.product_id.barcode or '', 'uds': 0, 'lineas': 0, 'max_linea': 0})
            p['uds'] += int(ml.qty_done)
            p['lineas'] += 1
            p['max_linea'] = max(p['max_linea'], int(ml.qty_done))
        estado = self._estado_pedido(origenes[0]) if len(origenes) == 1 else {}
        return {
            'cj': paquete.name,
            'uds': int(sum(lin.mapped('qty_done'))),
            'pedido': ', '.join(origenes),
            'tienda': self._tienda(outs[:1].partner_id),
            'outs': ['%s%s' % (p.name, '' if p.state == 'done' else ' (sin validar)') for p in outs],
            'zonas': ', '.join(sorted(set(outs.mapped('batch_id.name')))) or '-',
            'productos': sorted(por_producto.values(), key=lambda x: x['nombre']),
            'bloqueo': ('Zalando' if estado.get('zalando') else 'SHIPPED' if estado.get('shipped') else
                        'camión cerrado' if estado.get('en_cierre') else ''),
        }

    @api.model
    def prenda_en_caja(self, cj, codigo):
        """La prenda leída, si está dentro de esa CJ. No cambia nada."""
        paquete, lin = self._caja_y_lineas(cj)
        producto = pda.buscar_producto(self.env, codigo, archivados=True)
        if not producto:
            raise UserError(_('No encuentro ninguna prenda con el código %s.') % codigo)
        if producto.id not in lin.mapped('product_id').ids:
            raise UserError(_('%s NO está en %s según Odoo. Apártala: no cuenta.') % (producto.display_name,
                                                                                      paquete.name))
        return {'ok': True, 'product_id': producto.id, 'nombre': producto.display_name}

    def _comprobar_partir(self, cj, nueva, leidas):
        """(paquete origen, paquete nuevo o vacío, líneas a mover, errores, avisos, origen, estado, nueva_vacia).
        leidas: [{'product_id', 'uds'}]. No cambia nada."""
        Paquete = self.env['stock.quant.package'].sudo()
        cj = (cj or '').strip().upper()
        nueva = (nueva or '').strip().upper()
        if not comun.es_matricula(nueva):
            raise UserError(_('%s no es una matrícula CJ.') % nueva)
        po = Paquete.search([('name', '=', cj)])
        lo = self._lineas(po) if len(po) == 1 else self.env['stock.move.line']
        pn = Paquete.search([('name', '=', nueva)])
        ln = self._lineas(pn) if len(pn) == 1 else self.env['stock.move.line']
        por_producto = {}
        for x in leidas or []:
            try:
                pid, n = int(x.get('product_id')), int(x.get('uds') or 0)
            except (TypeError, ValueError, AttributeError):
                raise UserError(_('Lectura mal formada. Vuelve a empezar la caja.'))
            if n > 0:
                por_producto[pid] = por_producto.get(pid, 0) + n
        ped_o = sorted(set(lo.mapped('picking_id.origin')))
        estado = self._estado_pedido(ped_o[0]) if len(ped_o) == 1 else {}
        d = {
            'cj_o': cj, 'cj_n': nueva, 'n_paquetes_o': len(po), 'n_paquetes_n': len(pn),
            'uds_o': int(sum(lo.mapped('qty_done'))), 'leidas': sum(por_producto.values()),
            'pedidos_o': ped_o, 'pedidos_n': sorted(set(ln.mapped('picking_id.origin'))),
            'tiendas_o': lo.mapped('picking_id.partner_id').ids, 'tiendas_n': ln.mapped('picking_id.partner_id').ids,
            'stock_n_suelto': bool(len(pn) == 1 and not ln and self._uds_en_paquete(pn)),
            'shipped': estado.get('shipped'), 'en_cierre': estado.get('en_cierre'), 'zalando': estado.get('zalando'),
            'etiqueta': estado.get('etiqueta'), 'transportista': estado.get('transportista'),
            'ready': estado.get('ready'),
        }
        errores = []
        error = logica.error_partir(d)
        if error:
            errores.append(error)
        mover = self.env['stock.move.line']
        if not errores:
            Producto = self.env['product.product'].sudo()
            for pid, n in sorted(por_producto.items()):
                del_producto = lo.filtered(lambda ml: ml.product_id.id == pid)
                nombre = Producto.browse(pid).display_name
                hay = int(sum(del_producto.mapped('qty_done')))
                if n > hay:
                    errores.append(_('De %s has leído %d y en %s solo hay %d.') % (nombre, n, cj, hay))
                    continue
                ids = logica.elegir_lineas([(ml.id, ml.qty_done) for ml in del_producto], n)
                if ids is None:
                    errores.append(_('%s: en %s van %d uds juntas en una misma línea y has leído %d. Así no se puede '
                                     'pasar sin tocar el stock: avisa a la oficina.') % (nombre, cj, hay, n))
                    continue
                mover |= del_producto.filtered(lambda ml: ml.id in ids)
        avisos = logica.avisos(d, partir=True) if not errores else []
        return po, pn, mover, errores, avisos, (ped_o[0] if len(ped_o) == 1 else ''), estado, not ln

    @api.model
    def previa_partir(self, cj, nueva, leidas):
        """Lo que pasará al pulsar «Pasar», sin cambiar nada."""
        po, pn, mover, errores, avisos, origen, estado, nueva_vacia = self._comprobar_partir(cj, nueva, leidas)
        res = {'ok': not errores, 'errores': errores, 'avisos': avisos, 'pedido': origen,
               'nueva': (nueva or '').strip().upper(), 'nueva_existe': bool(pn)}
        if not errores:
            antes = self._bultos_pedido(origen)
            pasan = int(sum(mover.mapped('qty_done')))
            res.update({'bultos_antes': antes, 'bultos_despues': antes + (1 if nueva_vacia else 0),
                        'pasan': pasan, 'quedan': int(sum(self._lineas(po).mapped('qty_done'))) - pasan})
        return res

    @api.model
    def partir(self, cj, nueva, leidas, employee=None, token=''):
        """Pasa las prendas leídas (líneas enteras) de la CJ origen a la CJ nueva. Todo o nada."""
        if token:
            hecho = self.sudo().search([('token', '=', token)], limit=1)
            if hecho:
                return {'ok': True, 'repetida': True, 'pedido': hecho.pedido, 'bultos_antes': hecho.bultos_antes,
                        'bultos_despues': hecho.bultos_despues, 'cj': hecho.cj_pequena, 'nueva': hecho.cj_destino,
                        'pasan': hecho.uds}
        po, pn, mover, errores, avisos, origen, estado, nueva_vacia = self._comprobar_partir(cj, nueva, leidas)
        if errores:
            raise UserError('\n'.join(errores) + _('\nNo se ha cambiado nada.'))
        nombre_nueva = (nueva or '').strip().upper()
        if not pn:
            pn = self.env['stock.quant.package'].sudo().create(
                {'name': nombre_nueva, 'packaging_id': po.packaging_id.id or False})
        antes = self._bultos_pedido(origen)
        uds_o = int(sum(self._lineas(po).mapped('qty_done')))
        pasan = int(sum(mover.mapped('qty_done')))
        stock_o, stock_n = self._uds_en_paquete(po), self._uds_en_paquete(pn)
        lineas_ids = list(mover.ids)
        outs = mover.mapped('picking_id')
        hechas = self._mover_lineas(mover, pn)
        if abs(self._uds_en_paquete(po) - (stock_o - hechas)) > 0.001 or \
                abs(self._uds_en_paquete(pn) - (stock_n + hechas)) > 0.001:
            raise UserError(_('El stock de las cajas no cuadra después de mover. No se ha cambiado nada.'))
        if int(sum(self._lineas(po).mapped('qty_done'))) != uds_o - pasan:
            raise UserError(_('Las uds de %s no cuadran después de mover. No se ha cambiado nada.') % po.name)
        despues = self._bultos_pedido(origen)
        esperado = antes + (1 if nueva_vacia else 0)
        if despues != esperado:
            raise UserError(_('No cuadra: los bultos del pedido pasan de %d a %d y tenían que ser %d. '
                              'No se ha cambiado nada.') % (antes, despues, esperado))
        cambios_bultos = self._recalcular_bultos(origen)
        tienda = self._tienda(estado['outs'][:1].partner_id)
        quien = employee.name if employee else self.env.user.name
        texto = _('Revisar caja (PDA, %s): %d uds de %s pasan a %s. Bultos del pedido: %d -> %d.') % (
            quien, pasan, po.name, pn.name, antes, despues)
        texto += self._texto_avisos(estado, despues)
        for p in outs:
            p.message_post(body=texto)
        if estado['so']:
            estado['so'].message_post(body=texto)
        self.sudo().create({
            'tipo': 'partir', 'cj_pequena': po.name, 'cj_destino': pn.name, 'pedido': origen, 'tienda': tienda,
            'uds': pasan, 'bultos_antes': antes, 'bultos_despues': despues, 'aviso': ' '.join(avisos),
            'employee_id': employee.id if employee else False, 'lineas_ids': json.dumps(lineas_ids),
            'quants_ids': '', 'misma_out': len(outs) == 1, 'token': token or False})
        _logger.info('KOROSHI REVISAR CAJA: %s | %s', texto, ', '.join(cambios_bultos))
        return {'ok': True, 'pedido': origen, 'tienda': tienda, 'cj': po.name, 'nueva': pn.name, 'pasan': pasan,
                'quedan': uds_o - pasan, 'bultos_antes': antes, 'bultos_despues': despues, 'avisos': avisos,
                'etiqueta': estado['etiqueta']}

    @api.model
    def revisada_bien(self, cj, leidas_uds, employee=None):
        """«Todo bien»: solo apunta la revisión (doble check). No cambia nada de la caja."""
        paquete, lin = self._caja_y_lineas(cj)
        outs = lin.mapped('picking_id')
        uds = int(sum(lin.mapped('qty_done')))
        try:
            leidas_uds = int(leidas_uds or 0)
        except (TypeError, ValueError):
            leidas_uds = 0
        self.sudo().create({
            'tipo': 'revisar', 'cj_pequena': paquete.name, 'pedido': ', '.join(sorted(set(outs.mapped('origin')))),
            'tienda': self._tienda(outs[:1].partner_id), 'uds': leidas_uds,
            'aviso': '' if leidas_uds == uds else _('Leídas %d de %d uds') % (leidas_uds, uds),
            'employee_id': employee.id if employee else False})
        return {'ok': True, 'cj': paquete.name, 'leidas': leidas_uds, 'uds': uds}
