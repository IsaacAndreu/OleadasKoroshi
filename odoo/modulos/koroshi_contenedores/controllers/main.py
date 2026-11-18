# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Contenedores - rutas de la pantalla. Con sudo: el usuario de la PDA no necesita permisos sobre
# stock.location. Cambian location_id del contenedor (KO_/TT_), lo archivan y escriben en koroshi.contenedor.movimiento.
# v1.5: /cero y /anadir hacen ajustes de inventario (stock.move hecho contra pérdidas de inventario); quién y cuándo
# queda en koroshi.contenedor.movimiento, como en Lecturas y Faltantes.
# =============================================================================
import re

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import float_is_zero

PREFIJOS = ('KO_', 'TT_')
MAX_LINEAS = 40
MAX_ANADIR = 500          # v1.5: uds de un artículo en un solo «Añadir» (más = lecturas de más)
COMPANY_ID = 8            # EFFECTIVE LOGISTICS (si el contenedor no tiene empresa)
MAX_HUECOS = 400
LINEAL_RE = re.compile(r'^L\d{1,4}$', re.I)


def _es_contenedor_nombre(nombre):
    return (nombre or '').upper()[:3] in PREFIJOS


def _msg(e):
    return e.args[0] if e.args else str(e)


def _num(x):
    return ('%g' % round(x or 0, 2)).replace('.', ',')


def _literal(texto):
    """v1.4: el texto tal cual para un =ilike: en ILIKE «_» es «cualquier letra» y «%» «cualquier cosa», y los nombres
    son KO_110626_032 (con «_»): sin escaparlos, KO_110626_032 también encontraba p. ej. KOX110626X032."""
    return (texto or '').replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


class KoroshiContenedores(http.Controller):

    def _comprobar_usuario(self):
        if not request.env.user.has_group('stock.group_stock_user'):
            raise UserError('No tienes permiso para mover contenedores.')

    def _datos_contenedor(self, loc):
        Quant = request.env['stock.quant'].sudo()
        quants = Quant.search([('location_id', '=', loc.id), ('quantity', '!=', 0)])
        lineas = [{'producto': q.product_id.display_name, 'uds': q.quantity, 'reservadas': q.reserved_quantity}
                  for q in quants[:MAX_LINEAS]]
        return {
            'id': loc.id,
            'nombre': loc.name,
            'hueco': loc.location_id.complete_name or '',
            'uds': sum(quants.mapped('quantity')),
            'reservadas': sum(quants.mapped('reserved_quantity')),
            'n_lineas': len(quants),
            'lineas': lineas,
            'mas': max(0, len(quants) - MAX_LINEAS),
        }

    def _hijos_contenedor(self, hueco):
        Loc = request.env['stock.location'].sudo()
        return Loc.search([('location_id', '=', hueco.id), ('usage', '=', 'internal')]).filtered(
            lambda l: _es_contenedor_nombre(l.name))

    def _datos_hueco(self, hueco):
        """Hueco y sus contenedores KO_/TT_ con lo que tienen (para mover y para limpiar)."""
        Quant = request.env['stock.quant'].sudo()
        hijos = self._hijos_contenedor(hueco)
        quants = Quant.search([('location_id', 'in', hijos.ids + [hueco.id]), ('quantity', '!=', 0)])
        por_loc = {}
        for q in quants:
            d = por_loc.setdefault(q.location_id.id, {'uds': 0.0, 'res': 0.0, 'n': 0})
            d['uds'] += q.quantity
            d['res'] += q.reserved_quantity
            d['n'] += 1
        conts = []
        for h in hijos:
            d = por_loc.get(h.id, {'uds': 0.0, 'res': 0.0, 'n': 0})
            conts.append({'id': h.id, 'nombre': h.name, 'uds': d['uds'], 'reservadas': d['res'], 'n_lineas': d['n'],
                          'vacio': d['n'] == 0 and not d['res']})
        directo = por_loc.get(hueco.id, {'uds': 0.0, 'n': 0})
        return {'id': hueco.id, 'nombre': hueco.complete_name, 'contenedores': conts,
                'directo_uds': directo['uds'], 'directo_n': directo['n']}

    def _datos_lineal(self, lineal):
        """Inventario de un lineal (L94...): sus huecos con contenedores, contenedores con stock y unidades.
        Solo lectura. El lineal se saca del nombre del hueco: «07828 - L94 P35 C1»."""
        Loc = request.env['stock.location'].sudo()
        Quant = request.env['stock.quant'].sudo()
        clave = ' %s ' % lineal
        huecos = Loc.search([('usage', '=', 'internal'), ('name', 'ilike', clave)], order='name', limit=MAX_HUECOS + 1)
        huecos = huecos.filtered(lambda l: not _es_contenedor_nombre(l.name) and clave in (' %s ' % l.name.upper()))
        truncado = len(huecos) > MAX_HUECOS
        huecos = huecos[:MAX_HUECOS]
        hijos = Loc.search([('location_id', 'in', huecos.ids), ('usage', '=', 'internal')]).filtered(
            lambda l: _es_contenedor_nombre(l.name))
        grupos = Quant.read_group([('location_id', 'in', hijos.ids + huecos.ids), ('quantity', '!=', 0)],
                                  ['location_id', 'quantity:sum', 'reserved_quantity:sum'], ['location_id'], lazy=False)
        por_loc = {g['location_id'][0]: g for g in grupos}
        datos = {h.id: {'id': h.id, 'nombre': h.name, 'n_cont': 0, 'n_cont_stock': 0, 'uds': 0.0, 'reservadas': 0.0,
                        'directo_uds': (por_loc.get(h.id) or {}).get('quantity', 0.0)} for h in huecos}
        for c in hijos:
            d = datos.get(c.location_id.id)
            if not d:
                continue
            d['n_cont'] += 1
            g = por_loc.get(c.id)
            if g:
                d['n_cont_stock'] += 1
                d['uds'] += g['quantity']
                d['reservadas'] += g['reserved_quantity']
        filas = [datos[h.id] for h in huecos]
        return {'codigo': lineal, 'huecos': filas, 'truncado': truncado,
                'con_stock': len([f for f in filas if f['uds'] or f['directo_uds']]),
                'uds': sum(f['uds'] + f['directo_uds'] for f in filas)}

    @http.route('/koroshi/contenedores/hueco', type='json', auth='user')
    def hueco(self, ubicacion_id=False, **kw):
        """Panel de un hueco (para abrirlo desde la lista de un lineal)."""
        try:
            self._comprobar_usuario()
            hueco = request.env['stock.location'].sudo().browse(int(ubicacion_id or 0)).exists()
            if not hueco:
                raise UserError('No encuentro la ubicación.')
            self._validar_destino(hueco)
            return {'ok': True, 'ubicacion': self._datos_hueco(hueco)}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/koroshi/contenedores/limpiar', type='json', auth='user')
    def limpiar(self, ubicacion_id=False, employee_id=False, confirmado=False, **kw):
        """Archiva los contenedores KO_/TT_ del hueco que están a cero. Los que aún tienen stock o reservas no se tocan.
        Hay que confirmar que el hueco está físicamente vacío."""
        try:
            self._comprobar_usuario()
            if not confirmado:
                raise UserError('Confirma que la ubicación está físicamente vacía.')
            emp = request.env['hr.employee'].sudo().browse(int(employee_id or 0)).exists()
            if not emp:
                raise UserError('Pasa antes tu tarjeta de operario.')
            hueco = request.env['stock.location'].sudo().browse(int(ubicacion_id or 0)).exists()
            if not hueco:
                raise UserError('Escanea la ubicación.')
            self._validar_destino(hueco)
            Quant = request.env['stock.quant'].sudo()
            Mov = request.env['koroshi.contenedor.movimiento'].sudo()
            archivados, con_stock = [], []
            for c in self._hijos_contenedor(hueco):
                quants = Quant.search([('location_id', '=', c.id), '|', ('quantity', '!=', 0),
                                       ('reserved_quantity', '!=', 0)])
                if quants:
                    con_stock.append(c.name)
                    continue
                c.write({'active': False})
                Mov.create({'accion': 'archivar', 'contenedor': c.name, 'origen_id': hueco.id,
                            'origen': hueco.complete_name, 'destino': '(archivado, vacío, confirmado)',
                            'employee_id': emp.id})
                archivados.append(c.name)
            if not archivados and not con_stock:
                raise UserError('%s no tiene contenedores KO_/TT_: ya está limpia.' % hueco.complete_name)
            msg = '%s: %d contenedor(es) vacío(s) archivado(s) en %s' % (emp.name, len(archivados),
                                                                         hueco.complete_name)
            if con_stock:
                msg += '. NO se tocan por tener stock: %s' % ', '.join(con_stock)
            return {'ok': True, 'msg': msg, 'quedan': len(con_stock)}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    # ------------------------------------------------------------------ v1.5: compactar un hueco
    def _empleado(self, employee_id):
        emp = request.env['hr.employee'].sudo().browse(int(employee_id or 0)).exists()
        if not emp:
            raise UserError('Pasa antes tu tarjeta de operario.')
        return emp

    def _contenedor(self, contenedor_id):
        c = request.env['stock.location'].sudo().browse(int(contenedor_id or 0)).exists()
        if not c or not _es_contenedor_nombre(c.name) or c.usage != 'internal' or not c.active:
            raise UserError('Ese contenedor ya no es válido (¿archivado?). Vuelve a escanear el hueco.')
        return c

    def _quants(self, contenedor):
        """Prendas del contenedor: con cantidad o con reserva."""
        return request.env['stock.quant'].sudo().search([('location_id', '=', contenedor.id), '|',
                                                         ('quantity', '!=', 0), ('reserved_quantity', '!=', 0)])

    def _pedidos_reservados(self, contenedor):
        """OUT (y su pedido) que tienen reservadas prendas de este contenedor."""
        mls = request.env['stock.move.line'].sudo().search([
            ('location_id', '=', contenedor.id), ('state', 'not in', ('done', 'cancel')), ('product_qty', '>', 0)])
        return ['%s%s' % (p.name, ' (%s)' % p.origin if p.origin else '') for p in mls.mapped('picking_id')]

    def _ajuste(self, producto, qty, contenedor, company, emp, accion, nombre):
        """Ajuste de inventario de qty uds (+ entra en el contenedor, - sale) contra la ubicación de pérdidas de
        inventario del artículo, como un ajuste de Odoo. Mismo movimiento que koroshi_faltantes._mover (probado en
        producción). Deja su línea en el registro (quién, cuándo, artículo, uds y movimiento)."""
        perdidas = producto.with_context(force_company=company.id).property_stock_inventory
        if not perdidas:
            raise UserError('El artículo %s no tiene ubicación de pérdidas de inventario. Avisa a IT.'
                            % producto.display_name)
        origen, destino = (perdidas, contenedor) if qty > 0 else (contenedor, perdidas)
        uds = abs(qty)
        uom = producto.uom_id
        move = request.env['stock.move'].sudo().create({
            'name': nombre,
            'origin': nombre,
            'product_id': producto.id,
            'product_uom': uom.id,
            'product_uom_qty': uds,
            'location_id': origen.id,
            'location_dest_id': destino.id,
            'company_id': company.id,
            'move_line_ids': [(0, 0, {
                'product_id': producto.id,
                'product_uom_id': uom.id,
                'qty_done': uds,
                'location_id': origen.id,
                'location_dest_id': destino.id,
                'company_id': company.id,
            })],
        })
        move._action_done()
        if move.state != 'done':
            raise UserError('No se ha podido ajustar %s en %s.' % (producto.display_name, contenedor.name))
        request.env['koroshi.contenedor.movimiento'].sudo().create({
            'accion': accion, 'contenedor': contenedor.name, 'origen_id': contenedor.location_id.id,
            'origen': contenedor.location_id.complete_name, 'destino': contenedor.location_id.complete_name,
            'uds': qty, 'lineas': 1, 'producto_id': producto.id, 'move_id': move.id, 'employee_id': emp.id,
        })
        return move

    @http.route('/koroshi/contenedores/detalle', type='json', auth='user')
    def detalle(self, contenedor_ids=None, **kw):
        """Datos de uno o varios contenedores (para «Mover marcados» y para abrir uno desde la lista del hueco)."""
        try:
            self._comprobar_usuario()
            conts = [self._contenedor(i) for i in (contenedor_ids or [])]
            if not conts:
                raise UserError('Marca antes algún contenedor.')
            return {'ok': True, 'contenedores': [self._datos_contenedor(c) for c in conts]}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/koroshi/contenedores/archivar', type='json', auth='user')
    def archivar(self, contenedor_ids=None, ubicacion_id=False, employee_id=False, confirmado=False, **kw):
        """Archiva los contenedores marcados. Si alguno tiene prendas o reservas no se archiva ninguno: primero hay
        que ponerlo a cero (o moverlo). Así un toque sin querer no se lleva stock."""
        try:
            self._comprobar_usuario()
            if not confirmado:
                raise UserError('Confirma que están físicamente vacíos.')
            emp = self._empleado(employee_id)
            hueco = request.env['stock.location'].sudo().browse(int(ubicacion_id or 0)).exists()
            if not hueco:
                raise UserError('Escanea la ubicación.')
            conts = [self._contenedor(i) for i in (contenedor_ids or [])]
            if not conts:
                raise UserError('Marca antes algún contenedor.')
            for c in conts:
                if c.location_id.id != hueco.id:
                    raise UserError('%s ya no está en %s. Vuelve a escanear el hueco.' % (c.name, hueco.complete_name))
            con_stock = [c.name for c in conts if self._quants(c)]
            if con_stock:
                raise UserError('No se archiva nada: %s tiene prendas en el sistema. Ponlo a cero primero '
                                '(tócalo en la lista) o desmárcalo.' % ', '.join(con_stock))
            Mov = request.env['koroshi.contenedor.movimiento'].sudo()
            for c in conts:
                c.write({'active': False})
                Mov.create({'accion': 'archivar', 'contenedor': c.name, 'origen_id': hueco.id,
                            'origen': hueco.complete_name, 'destino': '(archivado, vacío, confirmado)',
                            'employee_id': emp.id})
            return {'ok': True, 'msg': '%s: %d contenedor(es) archivado(s) en %s' % (emp.name, len(conts),
                                                                                    hueco.complete_name),
                    'ubicacion': self._datos_hueco(hueco)}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/koroshi/contenedores/producto', type='json', auth='user')
    def producto(self, codigo='', **kw):
        """Prenda leída para añadir: EAN (y UPC/EAN con 0 delante), código alternativo o referencia interna."""
        try:
            self._comprobar_usuario()
            codigo = (codigo or '').strip()
            if not codigo:
                raise UserError('Código vacío.')
            variantes = [codigo]
            if codigo.isdigit() and len(codigo) == 12:
                variantes.append('0' + codigo)
            if codigo.isdigit() and len(codigo) == 13 and codigo.startswith('0'):
                variantes.append(codigo[1:])
            Product = request.env['product.product'].sudo()
            p = Product.search([('barcode', 'in', variantes)], limit=1)
            if not p and 'product.barcode' in request.env:
                p = request.env['product.barcode'].sudo().search([('name', 'in', variantes)], limit=1).product_id
            if not p:
                p = Product.search([('default_code', '=', codigo)], limit=1)
            if not p:
                raise UserError('%s no es una prenda conocida: no se añade.' % codigo)
            return {'ok': True, 'producto': {'id': p.id, 'nombre': p.display_name}}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/koroshi/contenedores/cero', type='json', auth='user')
    def cero(self, contenedor_id=False, employee_id=False, confirmado=False, **kw):
        """Pone a cero el contenedor (está físicamente vacío y Odoo dice que tiene prendas): ajuste de inventario de
        cada artículo. No se deja si alguna prenda está reservada para una OUT."""
        try:
            self._comprobar_usuario()
            if not confirmado:
                raise UserError('Confirma que el contenedor está físicamente vacío.')
            emp = self._empleado(employee_id)
            c = self._contenedor(contenedor_id)
            quants = self._quants(c)
            if not quants:
                raise UserError('%s ya está a cero.' % c.name)
            if any(q.reserved_quantity for q in quants):
                pedidos = self._pedidos_reservados(c)
                raise UserError('No se pone a cero: %s tiene prendas reservadas para %s. Quita antes la reserva '
                                'desde el pedido.' % (c.name, ', '.join(pedidos) or 'un pedido'))
            if quants.filtered(lambda q: q.lot_id or q.package_id or q.owner_id):
                raise UserError('%s tiene prendas con lote, paquete o propietario: hazlo desde Odoo o avisa a IT.'
                                % c.name)
            por_producto = {}
            for q in quants:
                d = por_producto.setdefault(q.product_id, {'qty': 0.0, 'company': q.company_id})
                d['qty'] += q.quantity
            total, n = 0.0, 0
            with request.env.cr.savepoint():    # todo o nada
                for producto, d in por_producto.items():
                    if float_is_zero(d['qty'], precision_rounding=producto.uom_id.rounding):
                        continue
                    self._ajuste(producto, -d['qty'], c, d['company'], emp, 'cero',
                                 'KOROSHI contenedor %s: poner a cero (%s)' % (c.name, emp.name))
                    total += d['qty']
                    n += 1
            return {'ok': True, 'msg': '%s: %s a cero (%s uds de %d ref. fuera del stock)' % (
                emp.name, c.name, _num(total), n), 'contenedor': self._datos_contenedor(c)}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/koroshi/contenedores/anadir', type='json', auth='user')
    def anadir(self, contenedor_id=False, employee_id=False, lineas=None, **kw):
        """Añade al contenedor las prendas leídas (Odoo no las tenía): ajuste de inventario de cada artículo.
        lineas = [{'producto_id': id, 'uds': n}]."""
        try:
            self._comprobar_usuario()
            emp = self._empleado(employee_id)
            c = self._contenedor(contenedor_id)
            Product = request.env['product.product'].sudo()
            por_producto = {}
            for l in (lineas or []):
                p = Product.browse(int(l.get('producto_id') or 0)).exists()
                uds = int(l.get('uds') or 0)
                if not p or uds <= 0:
                    raise UserError('Lectura no válida. Vuelve a leer las prendas.')
                por_producto[p] = por_producto.get(p, 0) + uds
            if not por_producto:
                raise UserError('Lee antes alguna prenda.')
            for p, uds in por_producto.items():
                if uds > MAX_ANADIR:
                    raise UserError('Más de %d uds de %s: revisa las lecturas.' % (MAX_ANADIR, p.display_name))
            company = c.company_id or request.env['res.company'].sudo().browse(COMPANY_ID)
            with request.env.cr.savepoint():    # todo o nada
                for p, uds in por_producto.items():
                    self._ajuste(p, uds, c, company, emp, 'anadir',
                                 'KOROSHI contenedor %s: añadir prendas (%s)' % (c.name, emp.name))
            return {'ok': True, 'msg': '%s: %d uds añadidas a %s' % (emp.name, sum(por_producto.values()), c.name),
                    'contenedor': self._datos_contenedor(c)}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    def _validar_destino(self, destino):
        if destino.usage != 'internal':
            raise UserError('%s no es una ubicación interna.' % destino.complete_name)
        if _es_contenedor_nombre(destino.name):
            raise UserError('%s es otro contenedor: escanea la ubicación (hueco) de destino.' % destino.name)

    @http.route('/koroshi/contenedores/leer', type='json', auth='user')
    def leer(self, codigo='', **kw):
        """Un código leído: contenedor (KO_/TT_) o ubicación de destino (código de barras del hueco)."""
        try:
            self._comprobar_usuario()
            codigo = (codigo or '').strip()
            if not codigo:
                raise UserError('Código vacío.')
            Loc = request.env['stock.location'].sudo()
            if LINEAL_RE.match(codigo):
                return {'ok': True, 'tipo': 'lineal', 'lineal': self._datos_lineal(codigo.upper())}
            if not _es_contenedor_nombre(codigo):
                emp =request.env['hr.employee'].sudo().search([('barcode', '=', codigo)], limit=1)
                if emp:
                    return {'ok': True, 'tipo': 'persona', 'persona': {'id': emp.id, 'nombre': emp.name}}
            if _es_contenedor_nombre(codigo):
                loc = Loc.search([('usage', '=', 'internal'), '|',
                                  ('name', '=ilike', _literal(codigo)), ('barcode', '=ilike', _literal(codigo))])
                loc = loc.filtered(lambda l: _es_contenedor_nombre(l.name))
                if not loc:
                    raise UserError('No encuentro el contenedor %s (o está archivado).' % codigo)
                if len(loc) > 1:
                    raise UserError('Hay %d contenedores llamados %s. Avisa a IT.' % (len(loc), codigo))
                return {'ok': True, 'tipo': 'contenedor', 'contenedor': self._datos_contenedor(loc)}
            loc = Loc.search([('barcode', '=', codigo)])
            if not loc:
                raise UserError('No conozco la ubicación %s.' % codigo)
            if len(loc) > 1:
                raise UserError('Hay %d ubicaciones con el código %s. Avisa a IT.' % (len(loc), codigo))
            self._validar_destino(loc)
            return {'ok': True, 'tipo': 'ubicacion', 'ubicacion': self._datos_hueco(loc)}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/koroshi/contenedores/mover', type='json', auth='user')
    def mover(self, contenedor_ids=None, destino_id=False, employee_id=False, **kw):
        try:
            self._comprobar_usuario()
            emp = request.env['hr.employee'].sudo().browse(int(employee_id or 0)).exists()
            if not emp:
                raise UserError('Pasa antes tu tarjeta de operario.')
            Loc = request.env['stock.location'].sudo()
            Quant = request.env['stock.quant'].sudo()
            Mov = request.env['koroshi.contenedor.movimiento'].sudo()
            destino = Loc.browse(int(destino_id or 0)).exists()
            if not destino:
                raise UserError('Escanea la ubicación de destino.')
            self._validar_destino(destino)
            conts = Loc.browse([int(i) for i in (contenedor_ids or [])]).exists()
            if not conts:
                raise UserError('Escanea antes un contenedor.')
            movidos, iguales = [], []
            for c in conts:
                if not _es_contenedor_nombre(c.name) or c.usage != 'internal' or not c.active:
                    raise UserError('%s ya no es un contenedor válido.' % c.name)
                if destino.id == c.id or (destino.parent_path or '').startswith(c.parent_path or '#'):
                    raise UserError('No se puede mover %s dentro de sí mismo.' % c.name)
                if c.location_id.id == destino.id:
                    iguales.append(c.name)
                    continue
                quants = Quant.search([('location_id', '=', c.id), ('quantity', '!=', 0)])
                origen = c.location_id
                c.write({'location_id': destino.id})
                Mov.create({
                    'contenedor': c.name, 'origen_id': origen.id, 'destino_id': destino.id,
                    'origen': origen.complete_name, 'destino': destino.complete_name,
                    'uds': sum(quants.mapped('quantity')), 'reservadas': sum(quants.mapped('reserved_quantity')),
                    'lineas': len(quants), 'employee_id': emp.id,
                })
                movidos.append(c.name)
            if not movidos:
                raise UserError('%s ya estaba en %s.' % (', '.join(iguales), destino.complete_name))
            msg = '%s: %s → %s' % (emp.name, ', '.join(movidos), destino.complete_name)
            if iguales:
                msg += ' (%s ya estaba allí)' % ', '.join(iguales)
            return {'ok': True, 'msg': msg}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}
