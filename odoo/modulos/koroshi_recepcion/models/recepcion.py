# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Recepción por contenedor (1.0.0, 23/11/2026).
#
# Un contenedor marítimo que llega (koroshi.recepcion) trae una o varias IN de KOROSHI (las crea OdooBot por API, una
# por pedido, del tipo «6665 STOCK GENERAL KOROSHI: Recepciones»). Odoo no tiene su matrícula: la escribe quien
# recibe. Se lee a ciegas, caja a caja: artículo + cantidad + contenedor de control (un KO_ por caja) + palé y cara
# (PAL-03 A). Al validar se compara con lo que traen las IN, se ponen las líneas hechas (destino = el KO_ de cada caja)
# y se valida la IN, dejando pendiente lo que no ha llegado (como hoy la PDA).
#
# Solo tablas propias. No añade campos a stock.picking, stock.picking.type ni stock.move.line: crea registros
# (ubicaciones KO_ y PAL-, líneas hechas de las IN) y valida la IN con lo de Odoo.
# Diseño: bin/versiones/diseno-recepciones-packing-list_2026-11-23_v6.md
#
# 1.1.0 (26/11/2026, urgente, Isaac): la recepción ya NO usa el contenedor de control KO_. Las cajas llegan solo con
# la etiqueta del proveedor (REFERENCE, ORDER NUMBER = origin de la IN, talla y uds a mano, nº de caja a rotulador).
# Cada lectura = nº de caja (el escrito a mano) + nº de pedido de la etiqueta (opcional; aviso si no es de ninguna IN
# del contenedor) + artículo + cantidad, en el palé y cara activos. Al validar, el destino de las líneas hechas es el
# palé (PAL-NN A/B). El KO_ se pondrá después, al ordenar y ubicar (fase 2). Las lecturas de la 1.0.x con KO_ siguen
# validándose a su KO_.
#
# 1.2.0 (26/11/2026, opción A de Isaac: «es quedarà en pendiente fins que es fiquen a llegir les prendes»): al llegar,
# por cada caja solo se apunta nº de caja + modelo (REFERENCE de la etiqueta) + uds totales de la caja + palé/cara
# (+ pedido, opcional). NO toca stock ni las IN: no crea líneas hechas ni valida; la IN queda pendiente y la recepción
# se «Cierra» (libera sus IN). La comparación es por modelo: cajas y uds llegadas contra las uds de las IN de ese
# modelo (suma de sus SKU). Las prendas se leen después, al ubicar.
# =============================================================================
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_is_zero

from odoo.addons.koroshi_base import comun
from odoo.addons.koroshi_recepcion import logica as L
from odoo.addons.koroshi_ubicaciones import nombres as N

_logger = logging.getLogger(__name__)

PARAM_TIPO = 'koroshi_recepcion.tipo_in_id'     # si está, el id del tipo de operación de las IN (si no, se busca)
DESTINO_IN = 'EFFEC/RECEP_KO'                    # destino de las IN de KOROSHI (así se reconoce su tipo)
NAVE = 'EFFEC/Stock/NAVE2'                       # donde nacen los KO_ (como en koroshi_ubicaciones)
NOMBRE_PADRE_PALETS = 'RECEPCION'                # EFFEC/Stock/NAVE2/RECEPCION: dentro, los PAL-NN A/B
ESTADOS = [('pendiente', 'Pendiente de recepcionar'), ('leyendo', 'Leyendo'), ('validada', 'Validada'),
           ('cerrada', 'Cerrada (cajas apuntadas; la IN sigue pendiente)'), ('cancelada', 'Cancelada')]


def es_contenedor(loc):
    return (loc.name or '')[:3].upper() in N.PREFIJOS_CONTENEDOR


class KoroshiRecepcion(models.Model):
    _name = 'koroshi.recepcion'
    _description = 'KOROSHI: contenedor que se recibe'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char('Recepción', required=True, readonly=True, copy=False, default='Nueva')
    matricula = fields.Char('Matrícula del contenedor', required=True, tracking=True,
                            help='La de la puerta o el lateral del contenedor (p. ej. MSKU1234567).')
    referencia = fields.Char('Referencia del proveedor o BL', tracking=True)
    muelle = fields.Char('Muelle', tracking=True)
    fecha_llegada = fields.Datetime('Llegada', default=fields.Datetime.now, tracking=True)
    state = fields.Selection(ESTADOS, 'Estado', default='pendiente', required=True, tracking=True)
    picking_ids = fields.Many2many('stock.picking', 'koroshi_recepcion_picking_rel', 'recepcion_id', 'picking_id',
                                   string='IN que trae',
                                   help='Las IN de KOROSHI de este contenedor. Al validar a medias se añaden solas '
                                        'las IN pendientes que deja Odoo (backorder).')
    cajas = fields.Integer('Cajas (según quien recepciona)', tracking=True,
                           help='Las que dice quien recepciona (o el albarán). Opcional: sirve para ver los huecos de '
                                'numeración hasta ese número.')
    palets = fields.Integer('Palés', tracking=True)
    contenedor_ids = fields.Many2many('stock.location', 'koroshi_recepcion_contenedor_rel', 'recepcion_id',
                                      'location_id', string='Contenedores de control (KO_)')
    lectura_ids = fields.One2many('koroshi.recepcion.lectura', 'recepcion_id', 'Lecturas')
    comparacion_ids = fields.One2many('koroshi.recepcion.comparacion', 'recepcion_id', 'Comparación')
    tanda_ids = fields.One2many('koroshi.recepcion.tanda', 'recepcion_id', 'Etiquetas')
    teorico_ids = fields.One2many('koroshi.recepcion.teorico', 'recepcion_id', 'Teórico guardado',
                                  help='Foto de lo que traían las IN, tomada antes de la primera validación: después '
                                       'Odoo cambia las cantidades de las IN validadas (lo que sobra se suma).')
    company_id = fields.Many2one('res.company', default=lambda s: comun.COMPANY_ID, readonly=True)
    notas = fields.Text('Notas')
    # resúmenes
    uds_leidas = fields.Integer('Uds leídas', compute='_compute_resumen')
    cajas_leidas = fields.Integer('Cajas leídas', compute='_compute_resumen')
    uds_validadas = fields.Integer('Uds pasadas a stock', compute='_compute_resumen')
    uds_teoricas = fields.Integer('Uds de las IN', compute='_compute_resumen')
    cajas_packing = fields.Integer('Cajas según el packing de S4T', compute='_compute_packing',
                                   help='Suma de las cajas (s4t_packages) del packing list de S4T de los pedidos de '
                                        'sus IN. Si se escribe «Cajas» a mano, manda lo escrito.')
    cajas_total_txt = fields.Integer('Cajas a recibir', compute='_compute_packing')
    packing_avisos = fields.Char('Avisos del packing', compute='_compute_packing')
    resumen_cajas_txt = fields.Text('Cajas leídas', compute='_compute_resumen_cajas',
                                    help='Cajas leídas, huecos en la numeración y cajas con un pedido que no es de las '
                                         'IN de este contenedor.')

    @api.depends('lectura_ids.cantidad', 'lectura_ids.estado', 'lectura_ids.validada', 'picking_ids')
    def _compute_resumen(self):
        for r in self:
            ok = r.lectura_ids.filtered(lambda l: l.estado == 'ok')
            r.uds_leidas = sum(ok.mapped('cantidad'))
            r.cajas_leidas = len({l.caja_txt for l in ok})
            r.uds_validadas = sum(ok.filtered('validada').mapped('cantidad'))
            r.uds_teoricas = int(sum(r._teorico().values()))

    def _compute_resumen_cajas(self):
        for r in self:
            r.resumen_cajas_txt = r.texto_cajas(r.resumen_cajas())

    def _origenes(self):
        return [o for o in self._todas_las_in().mapped('origin') if o]

    def packing(self):
        """1.4.0: total de cajas y uds del packing list de S4T (s4t.packing.feed, módulo de Effective: solo se LEE)
        de los pedidos de las IN (feed.name = origin de la IN). Ver logica.total_packing."""
        self.ensure_one()
        origenes = self._origenes()
        feeds = []
        if origenes and 's4t.packing.feed' in self.env:
            Feed = self.env['s4t.packing.feed'].sudo()
            campos = Feed._fields
            for f in Feed.search([('name', 'in', origenes)], order='id desc'):
                if 'company_id' in campos and f.company_id and f.company_id.id != comun.COMPANY_ID:
                    continue
                feeds.append((f.name, f.s4t_packages if 's4t_packages' in campos else 0,
                              f.s4t_pack_qty if 's4t_pack_qty' in campos else 0,
                              f.duplicated if 'duplicated' in campos else False))
            feeds.sort(key=lambda x: x[3])      # del mismo pedido, primero el que no está marcado duplicado
        return L.total_packing(origenes, feeds)

    def cajas_total(self, pack=None):
        """Las cajas que hay que recibir: las escritas a mano si las hay; si no, las del packing de S4T."""
        self.ensure_one()
        return self.cajas or (pack or self.packing())['cajas']

    def _compute_packing(self):
        for r in self:
            pack = r.packing()
            r.cajas_packing = pack['cajas']
            r.cajas_total_txt = r.cajas_total(pack)
            avisos = []
            if pack['duplicados']:
                avisos.append('packing marcado duplicado o repetido en S4T: %s (contado una vez)'
                              % ', '.join(pack['duplicados']))
            if pack['sin_packing']:
                avisos.append('sin packing en S4T: %s' % ', '.join(pack['sin_packing']))
            r.packing_avisos = '; '.join(avisos)

    def resumen_cajas(self):
        """Por caja: las leídas, los huecos de numeración y las de un pedido ajeno (ver logica.resumen_cajas)."""
        self.ensure_one()
        ok = self.lectura_ids.filtered(lambda l: l.estado == 'ok')
        origenes = self._origenes()       # ahora (si se enlaza la IN después, el aviso desaparece)
        return L.resumen_cajas([(l.caja_txt, l.pedido or '', L.pedido_ajeno(l.pedido, origenes)) for l in ok],
                               self.cajas_total())      # 1.4.0: las escritas o, si no, las del packing

    @api.model
    def texto_cajas(self, res):
        lineas = ['Cajas leídas: %d%s' % (len(res['leidas']),
                                          (': ' + ', '.join(res['leidas'])) if res['leidas'] else '')]
        if res['n_huecos']:
            lineas.append('Huecos en la numeración (%d): %s%s' % (
                res['n_huecos'], ', '.join(map(str, res['huecos'])), '…' if res['huecos_mas'] else ''))
        else:
            lineas.append('Sin huecos en la numeración.')
        if res['ajenas']:
            lineas.append('Cajas con un pedido que no es de este contenedor: %s' % ', '.join(
                'caja %s (pedido %s)' % (c, p) for c, p in res['ajenas']))
        return '\n'.join(lineas)

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nueva') == 'Nueva':
            vals['name'] = self.env['ir.sequence'].next_by_code('koroshi.recepcion') or 'Nueva'
        if vals.get('matricula'):
            vals['matricula'] = vals['matricula'].strip().upper()
        r = super().create(vals)
        r._comprobar_ins()
        return r

    def write(self, vals):
        if vals.get('matricula'):
            vals['matricula'] = vals['matricula'].strip().upper()
        cambia_in = 'picking_ids' in vals and not self.env.context.get('koroshi_backorders')
        antes = {r.id: r.picking_ids for r in self} if cambia_in else {}
        res = super().write(vals)
        if cambia_in:
            self._comprobar_ins()
            for r in self:
                if not r.teorico_ids:
                    continue
                # ya hay foto del teórico (algo validado): se pueden añadir IN, no quitarlas
                if antes[r.id] - r.picking_ids:
                    raise UserError('%s ya tiene lecturas pasadas a stock: sus IN no se quitan (solo se pueden añadir).'
                                    % r.name)
                nuevas = r.picking_ids - antes[r.id]
                Teorico = self.env['koroshi.recepcion.teorico'].sudo()
                for m in nuevas.mapped('move_lines').filtered(lambda x: x.state != 'cancel'):
                    Teorico.create({'recepcion_id': r.id, 'producto_id': m.product_id.id, 'uds': m.product_qty})
        return res

    def _comprobar_ins(self):
        """Solo IN de KOROSHI, y ninguna en otra recepción abierta (contaría dos veces)."""
        tipo = self.tipo_in()
        for r in self:
            malas = r.picking_ids.filtered(lambda p: p.picking_type_id != tipo)
            if malas:
                raise UserError('%s no son IN de KOROSHI (%s).' % (', '.join(malas.mapped('name')), tipo.display_name))
            otra = self.search([('id', '!=', r.id), ('state', 'in', ('pendiente', 'leyendo')),
                                ('picking_ids', 'in', r.picking_ids.ids)], limit=1)
            if otra:
                repetidas = r.picking_ids & otra.picking_ids
                raise UserError('%s ya está en otra recepción abierta: %s (%s).' % (
                    ', '.join(repetidas.mapped('name')), otra.name, otra.matricula))

    # ------------------------------------------------------------------ IN
    @api.model
    def tipo_in(self):
        """El tipo de operación de las IN de KOROSHI (el 44 en producción, 23/11): parámetro o, si no, el de entrada
        de la compañía que llega a EFFEC/RECEP_KO."""
        Tipo = self.env['stock.picking.type'].sudo()
        pid = self.env['ir.config_parameter'].sudo().get_param(PARAM_TIPO)
        if pid and pid.isdigit():
            t = Tipo.browse(int(pid)).exists()
            if t:
                return t
        return Tipo.search([('company_id', '=', comun.COMPANY_ID), ('code', '=', 'incoming'),
                            ('default_location_dest_id.complete_name', '=', DESTINO_IN)], limit=1)

    @api.model
    def ins_abiertas(self):
        """IN de KOROSHI sin validar ni cancelar, por fecha prevista."""
        tipo = self.tipo_in()
        if not tipo:
            raise UserError('No encuentro el tipo de operación de las IN de KOROSHI (destino %s).' % DESTINO_IN)
        return self.env['stock.picking'].sudo().search([
            ('picking_type_id', '=', tipo.id), ('state', 'not in', ('done', 'cancel'))],
            order='scheduled_date, id')

    def _todas_las_in(self):
        """Las IN enlazadas y las pendientes (backorder) que han salido de ellas, de cualquier nivel."""
        self.ensure_one()
        Picking = self.env['stock.picking'].sudo()
        todas = self.picking_ids.sudo()
        nuevas = todas
        while nuevas:
            nuevas = Picking.search([('backorder_id', 'in', nuevas.ids), ('id', 'not in', todas.ids)])
            todas |= nuevas
        return todas

    def _in_abiertas(self):
        return self._todas_las_in().filtered(lambda p: p.state not in ('done', 'cancel'))

    def _teorico(self):
        """{producto: uds} de lo que traen las IN. Desde la primera validación, la foto guardada (teorico_ids): al
        validar, Odoo cambia las IN (lo que sobra se suma a la demanda) y la sobra dejaría de verse."""
        if self.teorico_ids:
            res = {}
            for t in self.teorico_ids:
                res[t.producto_id] = res.get(t.producto_id, 0) + t.uds
            return res
        return self._teorico_de_las_in()

    def _teorico_de_las_in(self):
        """{producto: uds} de las IN ahora (todas: validadas y pendientes, sin las canceladas), en la unidad del
        producto (product_qty)."""
        res = {}
        if not self.picking_ids:
            return res
        for m in self._todas_las_in().mapped('move_lines'):
            if m.state != 'cancel':
                res[m.product_id] = res.get(m.product_id, 0) + m.product_qty
        return res

    def _foto_teorico(self):
        if not self.teorico_ids:
            self.env['koroshi.recepcion.teorico'].sudo().create([
                {'recepcion_id': self.id, 'producto_id': p.id, 'uds': q}
                for p, q in self._teorico_de_las_in().items()])

    def _leido(self):
        res = {}
        for l in self.lectura_ids.filtered(lambda x: x.estado == 'ok'):
            res[l.producto_id] = res.get(l.producto_id, 0) + l.cantidad
        return res

    # ------------------------------------------------------------------ ubicaciones (KO_ y palés)
    def _nave(self):
        nave = self.env['stock.location'].sudo().search([('complete_name', '=', NAVE),
                                                         ('company_id', '=', comun.COMPANY_ID)], limit=1)
        if not nave:
            raise UserError('No encuentro la ubicación %s.' % NAVE)
        return nave

    @api.model
    def padre_palets(self, crear=False):
        Loc = self.env['stock.location'].sudo()
        nave = self._nave()
        padre = Loc.with_context(active_test=False).search([('location_id', '=', nave.id),
                                                            ('name', '=', NOMBRE_PADRE_PALETS)], limit=1)
        if padre and not padre.active and crear:
            padre.active = True
        if not padre and crear:
            padre = Loc.create({'name': NOMBRE_PADRE_PALETS, 'location_id': nave.id, 'usage': 'internal',
                                'company_id': comun.COMPANY_ID})
        return padre

    @api.model
    def palets_existentes(self):
        padre = self.padre_palets()
        if not padre:
            return self.env['stock.location']
        locs = self.env['stock.location'].sudo().search([('location_id', '=', padre.id)])
        return locs.filtered(lambda l: L.palet_de(l.name)).sorted(lambda l: L.numero_palet(l.name))

    def _asegurar_palets(self, cuantos):
        """Crea los PAL-NN A/B que falten hasta «cuantos» palés. Devuelve los creados (para imprimir sus etiquetas)."""
        padre = self.padre_palets(crear=True)
        Loc = self.env['stock.location'].sudo()
        ya = {l.name: l for l in Loc.with_context(active_test=False).search([('location_id', '=', padre.id)])}
        creados = Loc.browse()
        for nombre in L.nombres_palets(cuantos):
            loc = ya.get(nombre)
            if loc and not loc.active:
                loc.active = True
            if not loc:
                creados |= Loc.create({'name': nombre, 'barcode': nombre, 'location_id': padre.id,
                                       'usage': 'internal', 'company_id': comun.COMPANY_ID})
        return creados

    def _crear_contenedores(self, cantidad):
        """Crea «cantidad» KO_ del día (como koroshi_ubicaciones: sigue el último número, también archivados)."""
        if not (1 <= cantidad <= L.MAX_CAJAS):
            raise UserError('Se pueden crear de 1 a %d contenedores de una vez.' % L.MAX_CAJAS)
        Loc = self.env['stock.location'].sudo()
        pref = N.prefijo_dia('KO_', comun.hoy_local())
        existentes = Loc.with_context(active_test=False).search(
            [('name', '=like', N.escapar_like(pref) + '%')]).mapped('name')
        nave = self._nave()
        locs = Loc.browse()
        for n in N.nombres_contenedores(pref, N.siguiente_numero(existentes, pref), cantidad):
            locs |= Loc.create({'name': n, 'barcode': n, 'location_id': nave.id, 'usage': 'internal',
                                'company_id': comun.COMPANY_ID})
        return locs

    def recepcionar(self, cajas, palets, muelle=None, employee=None):
        """Botón «Recepcionar» (o «+ palés» después): crea los palés que faltan hasta «palets» y una tanda de etiquetas
        con los nuevos. «cajas» es opcional (las que dice quien recepciona): desde la 1.1.0 NO se crean KO_ (las cajas
        llevan su nº escrito a mano). Devuelve la tanda (o vacío si no hay nada nuevo)."""
        self.ensure_one()
        if self.state in ('validada', 'cancelada'):
            raise UserError('La recepción %s está %s.' % (self.name, dict(ESTADOS)[self.state].lower()))
        cajas, palets = int(cajas or 0), int(palets or 0)
        if not (0 <= cajas <= L.MAX_CAJAS):
            raise UserError('El nº de cajas va de 0 a %d.' % L.MAX_CAJAS)
        if not (1 <= palets <= L.MAX_PALETS):
            raise UserError('Escribe cuántos palés vas a usar (de 1 a %d).' % L.MAX_PALETS)
        nuevos_ko = self.env['stock.location']      # 1.1.0: ya no se crean KO_ al recepcionar
        nuevos_pal = self._asegurar_palets(max(palets, self.palets or 0))
        vals = {'cajas': cajas or self.cajas, 'palets': max(palets, self.palets or 0), 'state': 'leyendo'}
        if muelle:
            vals['muelle'] = muelle.strip()
        if nuevos_ko:
            vals['contenedor_ids'] = [(4, l.id) for l in nuevos_ko]
        self.sudo().write(vals)
        if not (nuevos_ko or nuevos_pal):
            return self.env['koroshi.recepcion.tanda']
        que = []
        if nuevos_ko:
            que.append('%d cajas %s a %s' % (len(nuevos_ko), nuevos_ko[0].name, nuevos_ko[-1].name))
        if nuevos_pal:
            que.append('%d caras de palé' % len(nuevos_pal))
        tanda = self.env['koroshi.recepcion.tanda'].sudo().create({
            'recepcion_id': self.id, 'name': ', '.join(que), 'employee_id': employee and employee.id or False,
            'ubicacion_ids': [(6, 0, (nuevos_ko | nuevos_pal).ids)]})
        self.message_post(body='Recepcionar: %s (%s).' % (', '.join(que), employee and employee.name or
                                                            self.env.user.name))
        return tanda

    def contenedor_para_leer(self, loc, escribir=True):
        """Comprueba que un KO_ leído se puede usar en esta recepción y, con escribir, lo añade si es nuevo (al
        guardar la lectura; al solo leer la etiqueta no se escribe nada)."""
        self.ensure_one()
        if self.state != 'leyendo':
            raise UserError('La recepción %s no está abierta para leer: pulsa «Recepcionar».' % self.name)
        if not es_contenedor(loc) or loc.usage != 'internal':
            raise UserError('%s no es un contenedor KO_.' % loc.display_name)
        if loc in self.contenedor_ids:
            return loc
        otra = self.search([('id', '!=', self.id), ('contenedor_ids', 'in', loc.id),
                            ('state', 'in', ('pendiente', 'leyendo'))], limit=1)
        if otra:
            raise UserError('%s es de otra recepción (%s, %s).' % (loc.name, otra.name, otra.matricula))
        if self.env['stock.quant'].sudo().search_count([('location_id', '=', loc.id), ('quantity', '!=', 0)]):
            raise UserError('%s ya tiene prendas en Odoo: no es una caja nueva. Usa una etiqueta de esta recepción.'
                            % loc.name)
        if escribir:
            self.sudo().write({'contenedor_ids': [(4, loc.id)]})
        return loc

    def palet_valido(self, loc):
        """Un palé leído o tocado: PAL-NN A/B dentro de EFFEC/Stock/NAVE2/RECEPCION."""
        padre = self.padre_palets()
        if not loc or not padre or loc.location_id != padre or not L.palet_de(loc.name):
            raise UserError('%s no es un palé de recepción (PAL-01 A…).' % (loc and loc.display_name or '?'))
        return loc

    def modelos_de_las_in(self):
        return {L.modelo_de(p.default_code or p.name) for p in self._teorico()}

    def guardar_caja(self, caja, pedido, palet, modelo, cantidad, employee=None, token=None):
        """1.2.0 (opción A): una caja que llega: su nº escrito a mano, el modelo de la etiqueta, las uds totales de la
        caja y el palé (y el pedido de la etiqueta, opcional). No toca stock. Mismo token = la misma lectura."""
        self.ensure_one()
        Lectura = self.env['koroshi.recepcion.lectura'].sudo()
        if token:
            ya = Lectura.search([('token', '=', token)], limit=1)
            if ya:
                return ya
        if self.state != 'leyendo':
            raise UserError('La recepción %s no está abierta para leer (%s).' % (
                self.name, dict(ESTADOS)[self.state].lower()))
        cantidad = L.cantidad_valida(cantidad)
        caja = L.normalizar_caja(caja)
        modelo = L.normalizar_modelo(modelo)
        pedido = ' '.join((pedido or '').split())[:40]
        self.palet_valido(palet)
        if modelo not in self.modelos_de_las_in():
            Product = self.env['product.product'].sudo().with_context(active_test=False)
            if not Product.search_count(['|', ('default_code', '=', modelo),
                                         ('default_code', '=like', N.escapar_like(modelo) + '-%')]):
                raise UserError('No conozco el modelo %s: no hay ninguna prenda con esa referencia. Revisa el '
                                'REFERENCE de la etiqueta o lee el código de barras de una prenda.' % modelo)
        return Lectura.create({
            'recepcion_id': self.id, 'caja': caja, 'pedido': pedido or False, 'modelo_leido': modelo,
            'pedido_ajeno': L.pedido_ajeno(pedido, self._origenes()), 'palet_id': palet.id,
            'cantidad': cantidad, 'employee_id': employee and employee.id or False, 'token': token or False})

    def guardar_lectura(self, caja, pedido, palet, producto, cantidad, employee=None, token=None):
        """Guarda lo leído de una caja del proveedor (1.1.0): su nº escrito a mano, el pedido de la etiqueta (opcional),
        el artículo y la cantidad, en el palé activo. Una caja con varios artículos = varias lecturas con el mismo nº.
        Si la misma lectura llega dos veces (mismo token: doble toque o reintento), devuelve la primera sin repetirla."""
        self.ensure_one()
        Lectura = self.env['koroshi.recepcion.lectura'].sudo()
        if token:
            ya = Lectura.search([('token', '=', token)], limit=1)
            if ya:
                return ya
        if self.state != 'leyendo':
            raise UserError('La recepción %s no está abierta para leer (%s).' % (
                self.name, dict(ESTADOS)[self.state].lower()))
        cantidad = L.cantidad_valida(cantidad)
        caja = L.normalizar_caja(caja)
        pedido = ' '.join((pedido or '').split())[:40]
        self.palet_valido(palet)
        if not producto:
            raise UserError('Falta el artículo.')
        return Lectura.create({
            'recepcion_id': self.id, 'caja': caja, 'pedido': pedido or False,
            'pedido_ajeno': L.pedido_ajeno(pedido, self._origenes()), 'palet_id': palet.id,
            'producto_id': producto.id, 'cantidad': cantidad, 'employee_id': employee and employee.id or False,
            'token': token or False})

    def avisos_lectura(self, lectura):
        """Lo que se enseña en pantalla al guardar (no para nada): pedido ajeno, caja ya leída en otro palé."""
        avisos = []
        if lectura.pedido_ajeno:
            avisos.append('el pedido %s no es de ninguna IN de este contenedor (%s)' % (
                lectura.pedido, ', '.join(self._origenes()) or 'sin IN'))
        otros = self.lectura_ids.filtered(lambda l: l.estado == 'ok' and l.id != lectura.id
                                          and l.caja_txt == lectura.caja_txt and l.palet_id != lectura.palet_id)
        if otros:
            avisos.append('la caja %s ya está leída en %s' % (
                lectura.caja_txt, ', '.join(sorted(set(otros.mapped('palet_id.name'))))))
        if lectura.modelo_leido:
            if lectura.modelo_leido not in self.modelos_de_las_in():
                avisos.append('el modelo %s no viene en las IN de este contenedor' % lectura.modelo_leido)
            igual = self.lectura_ids.filtered(lambda l: l.estado == 'ok' and l.id != lectura.id
                                              and l.caja_txt == lectura.caja_txt and l.modelo == lectura.modelo)
            if igual:
                avisos.append('la caja %s ya tenía %d uds de %s: ¿la has apuntado dos veces? (si sí, anula una)' % (
                    lectura.caja_txt, sum(igual.mapped('cantidad')), lectura.modelo))
        return avisos

    def siguiente_contenedor(self):
        """El primer KO_ de la recepción sin ninguna lectura (para «Siguiente caja» sin leer la etiqueta)."""
        self.ensure_one()
        usados = set(self.lectura_ids.filtered(lambda l: l.estado == 'ok').mapped('contenedor_id').ids)
        for loc in self.contenedor_ids.sorted('name'):
            if loc.id not in usados:
                return loc
        return self.env['stock.location']

    # ------------------------------------------------------------------ comparar
    def comparar(self):
        """Rehace las filas de comparación y las devuelve. 1.2.0: por MODELO (2711JA22): uds de las IN de ese modelo
        (suma de sus SKU) contra las uds llegadas en sus cajas, con cuántas cajas y dónde (palé / caja)."""
        self.ensure_one()
        Comp = self.env['koroshi.recepcion.comparacion'].sudo()
        Comp.search([('recepcion_id', '=', self.id)]).unlink()
        teorico = {}
        for prod, uds in self._teorico().items():
            m = L.modelo_de(prod.default_code or prod.name)
            teorico[m] = teorico.get(m, 0) + uds
        leido, donde, cajas = {}, {}, {}
        for l in self.lectura_ids.filtered(lambda x: x.estado == 'ok'):
            m = l.modelo or '?'
            leido[m] = leido.get(m, 0) + l.cantidad
            cajas.setdefault(m, set()).add(l.caja_txt)
            d = donde.setdefault(m, {})
            clave = '%s / caja %s' % (l.palet_id.name or '¿palé?', l.caja_txt)
            d[clave] = d.get(clave, 0) + l.cantidad
        filas = []
        for m, (t, le, dif, estado) in L.comparar(teorico, leido).items():
            filas.append({
                'recepcion_id': self.id, 'modelo': m, 'cajas': len(cajas.get(m, ())), 'teorico': t, 'leido': le,
                'diferencia': dif, 'estado': estado,
                'donde': ', '.join('%s: %g' % (k, v) for k, v in sorted(
                    donde.get(m, {}).items(), key=lambda kv: (L.clave_caja(kv[0].split('caja ')[-1]), kv[0]))),
            })
        filas.sort(key=lambda f: f['modelo'])
        return Comp.create(filas) if filas else Comp

    def cerrar(self, employee=None):
        """1.2.0 (opción A): termina de apuntar cajas. No toca stock ni las IN (quedan pendientes, libres para leer
        las prendas después)."""
        self.ensure_one()
        if self.state not in ('pendiente', 'leyendo'):
            raise UserError('Solo se cierra una recepción abierta (esta está %s).' % dict(ESTADOS)[self.state].lower())
        self._bloquear()
        # 1.2.1: las prendas leídas con la 1.1.0 (artículo y cantidad) tampoco pasan a stock al cerrar (opción A):
        # quedan apuntadas y la IN pendiente. Antes no se podía cerrar con ellas y, sin responsables, no había salida.
        self.comparar()
        self.sudo().state = 'cerrada'
        self.message_post(body='Cerrada por %s: %d cajas, %d uds apuntadas. Las IN siguen pendientes (%s).' % (
            employee and employee.name or self.env.user.name, self.cajas_leidas, self.uds_leidas,
            ', '.join(self._in_abiertas().mapped('name')) or '-'))

    def action_cerrar(self):
        self.cerrar()

    # ------------------------------------------------------------------ validar
    def _bloquear(self):
        try:
            self.env.cr.execute('SELECT id FROM koroshi_recepcion WHERE id = %s FOR UPDATE NOWAIT', (self.id,))
        except Exception:
            raise UserError('Otra persona está validando esta recepción ahora mismo. Espera un momento.')

    def validar(self, parcial=False, employee=None):
        """Pasa a stock lo leído y no validado: líneas hechas en las IN (destino = el KO_ de cada caja) y valida las IN
        donde se han puesto líneas; lo que no ha llegado queda en una IN pendiente (backorder), como hoy.
        parcial=True: «Validar lo leído hasta ahora» (la lectura sigue). Sin parcial, no se cierra mientras quede algo
        leído que no puede pasar a stock (no viene en ninguna IN abierta): hay que anularlo o enlazar su IN.
        Todo o nada: si algo falla, quien llama deshace la transacción. Devuelve un resumen."""
        self.ensure_one()
        if self.state != 'leyendo':
            raise UserError('Solo se valida una recepción que se está leyendo (esta está %s).'
                            % dict(ESTADOS)[self.state].lower())
        self._bloquear()
        if self.lectura_ids.filtered(lambda l: l.estado == 'ok' and not l.producto_id):
            raise UserError('Esta recepción tiene cajas apuntadas por modelo (sin prendas): no pasa nada a stock. La IN '
                            'queda pendiente hasta leer las prendas: usa «Cerrar».')
        self._foto_teorico()      # antes de tocar las IN: después Odoo cambia sus cantidades
        lecturas = self.lectura_ids.filtered(lambda l: l.estado == 'ok' and not l.validada).sorted('id')
        abiertas = self._in_abiertas().sorted(lambda p: (p.scheduled_date or fields.Datetime.now(), p.id))
        otra_unidad = abiertas.mapped('move_lines').filtered(
            lambda m: m.state not in ('done', 'cancel') and m.product_uom != m.product_id.uom_id)
        if otra_unidad:
            raise UserError('Hay líneas de IN en otra unidad de medida (%s): esta pantalla cuenta prendas. Valida esas '
                            'IN en Odoo.' % ', '.join(otra_unidad[:5].mapped('product_id.display_name')))
        pendientes = []
        for p in abiertas:
            for m in p.move_lines.filtered(lambda x: x.state not in ('done', 'cancel')).sorted('id'):
                pendientes.append((m, m.product_id, m.product_uom_qty - m.quantity_done))
        # destino: el palé (1.1.0); las lecturas de la 1.0.x con KO_, su KO_
        leidos = [(l, l.producto_id, l.contenedor_id or l.palet_id, l.cantidad) for l in lecturas]
        lineas, sin_in = L.repartir(pendientes, leidos)
        teoricos = set(self._teorico())
        sin_in_txt = ['%s %g uds en la caja %s%s' % (
            l.producto_id.display_name, l.cantidad, l.caja_txt,
            ' (sus IN ya están validadas)' if l.producto_id in teoricos else ' (no viene en ninguna IN)')
            for l in sin_in]
        if sin_in and not parcial:
            raise UserError('No se cierra el contenedor: hay %d lecturas que no pueden pasar a stock: %s. Anúlalas si '
                            'son un error o enlaza su IN; para pasar el resto, «Validar lo leído hasta ahora».'
                            % (len(sin_in), '; '.join(sin_in_txt[:10])))
        tracking = self.env['product.product'].browse({mov.product_id.id for mov, _d, _u, _l in lineas}).filtered(
            lambda p: p.tracking != 'none')
        if tracking:
            raise UserError('Hay artículos con lote o número de serie (%s): esta pantalla no los valida. Valida la IN '
                            'en Odoo.' % ', '.join(tracking[:5].mapped('display_name')))
        MoveLine = self.env['stock.move.line'].sudo()
        hechas = self.env['koroshi.recepcion.lectura']
        tocadas = self.env['stock.picking']
        for mov, destino, uds, lects in lineas:
            if mov.picking_id.state == 'draft':
                mov.picking_id.action_confirm()
            MoveLine.create({
                'move_id': mov.id, 'picking_id': mov.picking_id.id, 'product_id': mov.product_id.id,
                'product_uom_id': mov.product_uom.id, 'location_id': mov.location_id.id,
                'location_dest_id': destino.id, 'qty_done': uds, 'company_id': mov.company_id.id,
            })
            tocadas |= mov.picking_id
            for l in lects:
                hechas |= l
        validadas = []
        for p in abiertas:       # en el orden de las IN, solo las que tienen líneas de esta pasada
            if p in tocadas:
                self._validar_in(p)
                validadas.append(p.name)
        hechas.sudo().write({'validada': True, 'validada_en': fields.Datetime.now()})
        # las IN pendientes nuevas (backorder) quedan enlazadas para la próxima vez (o para reabrir)
        nuevas = self._todas_las_in() - self.picking_ids
        vals = {}
        if nuevas:
            vals['picking_ids'] = [(4, p.id) for p in nuevas]
        if not parcial:
            vals['state'] = 'validada'
        if vals:
            self.sudo().with_context(koroshi_backorders=True).write(vals)
        uds = sum(hechas.mapped('cantidad'))
        quien = employee and employee.name or self.env.user.name
        self.message_post(body='%s por %s: %g uds a stock. IN validadas: %s. IN pendientes: %s.%s' % (
            'Validado lo leído hasta ahora' if parcial else 'Validado', quien, uds, ', '.join(validadas) or '-',
            ', '.join(self._in_abiertas().mapped('name')) or '-',
            (' No pasan a stock: %s.' % '; '.join(sin_in_txt)) if sin_in_txt else ''))
        self.comparar()
        return {'uds': uds, 'pickings': validadas, 'pendientes': self._in_abiertas().mapped('name'),
                'sin_in': sin_in_txt}

    def reabrir(self, employee=None):
        """Vuelve a «Leyendo» un contenedor validado que dejó IN pendientes (llegan las cajas que faltaban)."""
        self.ensure_one()
        if self.state not in ('validada', 'cerrada'):
            raise UserError('Solo se reabre una recepción validada o cerrada.')
        if self.state == 'cerrada':
            self._comprobar_ins()        # sus IN pueden estar ya en otra recepción abierta
        if not self._in_abiertas():
            raise UserError('%s no tiene IN pendientes: no hay nada que recibir.' % self.name)
        self.sudo().state = 'leyendo'
        self.message_post(body='Reabierta por %s: IN pendientes %s.' % (
            employee and employee.name or self.env.user.name, ', '.join(self._in_abiertas().mapped('name'))))

    def action_reabrir(self):
        self._comprobar_responsable_usuario()
        self.reabrir()

    def _validar_in(self, picking):
        """La validación normal de Odoo (button_validate), como koroshi_faltantes con las OUT. Si Odoo pregunta por
        lo pendiente, se deja pendiente (backorder), como hoy. Lo que sobra de un artículo es real: se acepta
        (skip_overprocessed_check). Cualquier otro asistente: no se fuerza nada y no se valida nada."""
        p = picking.with_context(allowed_company_ids=[comun.COMPANY_ID], force_company=comun.COMPANY_ID,
                                 skip_overprocessed_check=True)
        res = p.button_validate()
        if isinstance(res, dict) and res.get('res_model'):
            modelo = res['res_model']
            if modelo != 'stock.backorder.confirmation':
                raise UserError('Odoo pide otra cosa al validar %s (%s). Valídala en Odoo.'
                                % (picking.name, res.get('name') or modelo))
            self.env[modelo].sudo().with_context(**(res.get('context') or {})).create(
                {'pick_ids': [(4, picking.id)]}).process()
        if picking.state != 'done':
            raise UserError('Odoo no ha validado %s (estado %s).' % (picking.name, picking.state))

    def action_validar(self):
        self._comprobar_responsable_usuario()
        r = self.validar(parcial=False)
        return self._aviso_validado(r)

    def action_validar_parcial(self):
        self._comprobar_responsable_usuario()
        r = self.validar(parcial=True)
        return self._aviso_validado(r)

    def _comprobar_responsable_usuario(self):
        if not self.env.user.has_group('stock.group_stock_manager'):
            raise UserError('Solo el responsable de recepciones valida (Inventario / Administrador).')

    def _aviso_validado(self, r):
        # display_notification no existe en Odoo 13 (CLAUDE.md, regla 9): se vuelve a abrir la ficha; el resumen
        # queda en el historial.
        return {'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id, 'view_mode': 'form',
                'target': 'current'}

    def action_comparar(self):
        self.ensure_one()
        self.comparar()
        return {'type': 'ir.actions.act_window', 'name': 'Comparación %s' % self.name,
                'res_model': 'koroshi.recepcion.comparacion', 'view_mode': 'tree',
                'domain': [('recepcion_id', '=', self.id)], 'context': {'search_default_diferencias': 1},
                'target': 'current'}

    def action_exportar(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_url', 'url': '/koroshi/recepcion/exportar?recepcion_id=%d' % self.id,
                'target': 'new'}

    def action_cancelar(self):
        for r in self:
            if r.lectura_ids.filtered('validada'):
                raise UserError('%s ya tiene lecturas pasadas a stock: no se puede cancelar.' % r.name)
            r.state = 'cancelada'

    def action_pantalla(self):
        self.ensure_one()
        return {'type': 'ir.actions.client', 'tag': 'koroshi_recepcion_pantalla', 'params': {'recepcion_id': self.id}}


class KoroshiRecepcionLectura(models.Model):
    """Una línea leída: lo que hay en una caja (un artículo; una caja con varias tallas son varias lecturas)."""
    _name = 'koroshi.recepcion.lectura'
    _description = 'KOROSHI: lectura de una caja en la recepción'
    _order = 'id desc'

    recepcion_id = fields.Many2one('koroshi.recepcion', required=True, ondelete='cascade', index=True)
    contenedor_id = fields.Many2one('stock.location', 'KO_ (hasta la 1.0.1)', index=True,
                                    help='Solo en lecturas de la 1.0.x: desde la 1.1.0 la caja es su nº escrito a mano.')
    caja = fields.Char('Nº de caja', index=True, help='El nº escrito a mano en la caja del proveedor (1.1.0).')
    caja_txt = fields.Char('Caja', compute='_compute_caja_txt', store=True, index=True,
                           help='El nº de caja o, en las lecturas de la 1.0.x, el KO_.')
    pedido = fields.Char('Pedido (etiqueta)', help='ORDER NUMBER de la etiqueta de la caja, si se ha escrito.')
    pedido_ajeno = fields.Boolean('Pedido que no es de este contenedor', readonly=True,
                                  help='Se escribió un pedido y no es el origen de ninguna IN del contenedor.')
    palet_id = fields.Many2one('stock.location', 'Palé', required=True)
    producto_id = fields.Many2one('product.product', 'Artículo', index=True,
                                  help='Vacío en las cajas apuntadas por modelo (1.2.0).')
    modelo_leido = fields.Char('Modelo (etiqueta)', help='1.2.0: el REFERENCE de la etiqueta de la caja (2711JA22).')
    cantidad = fields.Integer('Uds', required=True)
    employee_id = fields.Many2one('hr.employee', 'Operario')
    user_id = fields.Many2one('res.users', 'Usuario', default=lambda s: s.env.user)
    fecha = fields.Datetime('Cuándo', default=fields.Datetime.now)
    estado = fields.Selection([('ok', 'Leída'), ('anulada', 'Anulada')], default='ok', required=True)
    validada = fields.Boolean('Pasada a stock', readonly=True)
    validada_en = fields.Datetime('Pasada a stock el', readonly=True)
    token = fields.Char('Token', readonly=True, copy=False,
                        help='Lo pone la pantalla: si la misma lectura llega dos veces (doble toque), no se repite.')
    # para filtrar y exportar
    modelo = fields.Char(compute='_compute_partes', store=True)
    talla = fields.Char(compute='_compute_partes', store=True)
    matricula = fields.Char(related='recepcion_id.matricula', store=True, string='Matrícula')

    _sql_constraints = [('token_unico', 'unique(token)', 'Esta lectura ya está guardada.')]

    @api.depends('caja', 'contenedor_id')
    def _compute_caja_txt(self):
        for l in self:
            l.caja_txt = l.caja or l.contenedor_id.name or ''

    @api.depends('producto_id', 'modelo_leido')
    def _compute_partes(self):
        # 1.2.0: modelo = solo el modelo (2711JA22), sin color: así se compara con las cajas apuntadas por modelo
        for l in self:
            if l.producto_id:
                l.modelo = L.modelo_de(l.producto_id.default_code or l.producto_id.name)
                l.talla = L.partes_referencia(l.producto_id.default_code or l.producto_id.name)[2]
            else:
                l.modelo = l.modelo_leido or ''
                l.talla = ''

    def anular(self):
        for l in self:
            l.recepcion_id._bloquear()     # no a la vez que una validación
            l.invalidate_cache(['validada'])
            if l.validada:
                raise UserError('Esta lectura ya está pasada a stock: no se puede anular aquí.')
            l.estado = 'anulada'


class KoroshiRecepcionComparacion(models.Model):
    """Fila de la comparación de una recepción (se rehace cada vez que se compara): para mirar y exportar."""
    _name = 'koroshi.recepcion.comparacion'
    _description = 'KOROSHI: comparación de una recepción con sus IN'
    _order = 'modelo, color, talla, id'

    recepcion_id = fields.Many2one('koroshi.recepcion', required=True, ondelete='cascade', index=True)
    producto_id = fields.Many2one('product.product', 'Artículo')
    modelo = fields.Char('Modelo')
    color = fields.Char('Color')
    talla = fields.Char('Talla')
    ean = fields.Char('EAN')
    cajas = fields.Integer('Cajas')
    teorico = fields.Float('Teórico (IN)', digits=(16, 0))
    leido = fields.Float('Leído', digits=(16, 0))
    diferencia = fields.Float('Diferencia', digits=(16, 0))
    estado = fields.Selection([('ok', 'Correcto'), ('falta', 'Falta'), ('sobra', 'Sobra'),
                               ('no_venia', 'No venía en las IN')], 'Estado')
    donde = fields.Char('Dónde (palé / caja: uds)')


class KoroshiRecepcionTeorico(models.Model):
    """Foto de lo que traían las IN de una recepción, tomada antes de la primera validación."""
    _name = 'koroshi.recepcion.teorico'
    _description = 'KOROSHI: teórico guardado de una recepción'

    recepcion_id = fields.Many2one('koroshi.recepcion', required=True, ondelete='cascade', index=True)
    producto_id = fields.Many2one('product.product', 'Artículo', required=True)
    uds = fields.Float('Uds', digits=(16, 0))


class KoroshiRecepcionTanda(models.Model):
    """Etiquetas creadas de una vez (Recepcionar, + cajas, + palés), para imprimirlas en la Zebra 4x6."""
    _name = 'koroshi.recepcion.tanda'
    _description = 'KOROSHI: etiquetas de una recepción'
    _order = 'id desc'

    recepcion_id = fields.Many2one('koroshi.recepcion', required=True, ondelete='cascade')
    name = fields.Char('Qué', required=True)
    fecha = fields.Datetime('Cuándo', default=fields.Datetime.now)
    employee_id = fields.Many2one('hr.employee', 'Quién')
    ubicacion_ids = fields.Many2many('stock.location', 'koroshi_recepcion_tanda_loc_rel', 'tanda_id', 'location_id',
                                     string='Ubicaciones')

    def action_imprimir(self):
        self.ensure_one()
        return self.env.ref('koroshi_recepcion.action_etiqueta_tanda').report_action(self)


class KoroshiRecepcionResponsable(models.Model):
    """Quién puede validar desde la pantalla (con su tarjeta). En la PDA todos entran con el mismo usuario de Odoo,
    así que el permiso va por la tarjeta del operario."""
    _name = 'koroshi.recepcion.responsable'
    _description = 'KOROSHI: responsable de recepciones'

    employee_id = fields.Many2one('hr.employee', 'Persona', required=True)

    _sql_constraints = [('empleado_unico', 'unique(employee_id)', 'Esta persona ya es responsable.')]

    @api.model
    def es_responsable(self, employee):
        return bool(employee) and bool(self.sudo().search_count([('employee_id', '=', employee.id)]))


class InformeEtiquetaTanda(models.AbstractModel):
    _name = 'report.koroshi_recepcion.etiqueta_tanda'
    _description = 'KOROSHI: etiquetas 4x6 de una recepción (cajas KO_ y palés)'

    @api.model
    def _get_report_values(self, docids, data=None):
        tandas = self.env['koroshi.recepcion.tanda'].sudo().browse(docids)
        etiquetas = []
        for t in tandas:
            r = t.recepcion_id
            for loc in t.ubicacion_ids.with_context(active_test=False).sorted('name'):
                etiquetas.append(self._etiqueta(loc, r))
        return {'doc_ids': docids, 'doc_model': 'koroshi.recepcion.tanda', 'docs': tandas, 'etiquetas': etiquetas}

    @api.model
    def _etiqueta(self, loc, r):
        from werkzeug.urls import url_quote
        codigo = loc.barcode or loc.name
        palet = L.palet_de(loc.name)
        llegada = comun.a_local(r.fecha_llegada)
        if palet:
            num, cara = L.numero_palet(palet)
            et = {'tipo': 'palet', 'arriba': 'PALÉ', 'grande': '%d %s' % (num, cara), 'pie': 'Recepción'}
        else:
            et = {'tipo': 'caja', 'arriba': 'CAJA', 'grande': loc.name,
                  'pie': '%s · %s · %s' % ('Muelle %s' % r.muelle if r.muelle else 'Muelle ?',
                                           llegada and llegada.strftime('%d/%m/%Y') or '', r.matricula or '')}
        et['codigo'] = codigo
        et['url'] = '/report/barcode/?type=Code128&value=%s&width=900&height=300&humanreadable=0' % url_quote(codigo)
        return et
