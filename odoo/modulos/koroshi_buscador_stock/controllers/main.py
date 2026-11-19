# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Buscador de stock - rutas de la pantalla de la oficina. SOLO LECTURA: search/read_group sobre stock.quant,
# stock.move.line, stock.move, stock.location y product.product, siempre en ubicaciones internas de la compañía 8.
# No escribe nada ni tiene modelos propios. Con sudo (como Contenedores), pero solo para usuarios de inventario.
# Diseño: bin/versiones/diseno-buscador-stock_2026-11-19.md
# =============================================================================
import re

from odoo import http
from odoo.addons.koroshi_base import comun
from odoo.exceptions import UserError
from odoo.http import request

COMPANY_ID = comun.COMPANY_ID
PREFIJOS = ('KO_', 'TT_')
LINEAL_RE = re.compile(r'^L\d{1,4}$', re.I)
MIN_TROZO = 3             # caracteres mínimos para buscar por un trozo de referencia o descripción
MIN_TROZO_CONT = 2        # como Contenedores 1.7 (MIN_BUSCAR)
MAX_MODELOS = 100         # modelos en la lista de un trozo (v1.2: 100; antes 50)
MAX_PRODUCTOS_TROZO = 3000  # variantes leídas para sacar esos modelos (v1.2: 3000; antes 600)
MAX_CONTENEDORES = 20     # contenedores en la lista de un trozo
MAX_UBICACIONES = 200     # ubicaciones con stock de una prenda
MAX_OUT = 100             # OUT que reservan una prenda (o desde un hueco)
MAX_ENTRADAS = 100        # recepciones abiertas de una prenda
MAX_HUECOS = 400          # huecos de un lineal
MAX_FILAS_HUECO = 300     # prendas dentro de un hueco o contenedor
ESTADOS_ABIERTOS = ('waiting', 'confirmed', 'partially_available', 'assigned')


# --- Copiadas de koroshi_contenedores 1.7.0 (controllers/main.py), opción A del diseño: se pasarán a koroshi_base en
# --- otra versión (actualizar koroshi_base con -u actualiza todos sus dependientes y saca las sesiones de la PDA).
def _es_contenedor_nombre(nombre):
    return (nombre or '').upper()[:3] in PREFIJOS


def _literal(texto):
    """El texto tal cual para un =ilike: en ILIKE «_» es «cualquier letra» y «%» «cualquier cosa» (KO_110626_032)."""
    return (texto or '').replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def _variantes_ean(codigo):
    """EAN tal cual, UPC de 12 cifras con 0 delante y EAN de 13 con 0 delante sin él."""
    variantes = [codigo]
    if codigo.isdigit() and len(codigo) == 12:
        variantes.append('0' + codigo)
    if codigo.isdigit() and len(codigo) == 13 and codigo.startswith('0'):
        variantes.append(codigo[1:])
    return variantes
# --- fin de lo copiado


def _msg(e):
    return e.args[0] if e.args else str(e)


def _redondear(x):
    return round(x or 0.0, 3)


class KoroshiBuscadorStock(http.Controller):

    # ------------------------------------------------------------------ comunes
    def _comprobar_usuario(self):
        if not request.env.user.has_group('stock.group_stock_user'):
            raise UserError('Solo para usuarios de inventario.')

    def _env(self, modelo):
        return request.env[modelo].sudo()

    def _dominio_quant(self):
        return [('location_id.usage', '=', 'internal'), ('company_id', '=', COMPANY_ID)]

    def _hueco_y_contenedor(self, loc):
        """(hueco, nombre del contenedor o '') de una ubicación interna."""
        if _es_contenedor_nombre(loc.name):
            return loc.location_id, loc.name
        return loc, ''

    def _nombre_variante(self, p):
        valores = p.product_template_attribute_value_ids.mapped('name')
        return ' / '.join(valores) or p.default_code or p.display_name

    def _buscar_producto(self, codigo):
        """Prenda por EAN (con o sin 0 delante), código alternativo (product.barcode) o referencia interna exacta."""
        variantes = _variantes_ean(codigo)
        Product = self._env('product.product')
        p = Product.search([('barcode', 'in', variantes)], limit=1)
        if not p and 'product.barcode' in request.env:
            p = self._env('product.barcode').search([('name', 'in', variantes)], limit=1).product_id
        if not p:
            p = Product.search([('default_code', '=', codigo)], limit=1)
        return p

    def _contenedores_por_trozo(self, texto):
        texto = (texto or '').strip()
        Loc = self._env('stock.location')
        if len(texto) < MIN_TROZO_CONT:
            return Loc, False
        dominio = [('usage', '=', 'internal'), ('name', '=ilike', '%' + _literal(texto) + '%'), '|',
                   ('name', '=ilike', 'KO\\_%'), ('name', '=ilike', 'TT\\_%')]
        locs = Loc.search(dominio, order='name', limit=MAX_CONTENEDORES + 1)
        return locs[:MAX_CONTENEDORES], len(locs) > MAX_CONTENEDORES

    def _lista_contenedores(self, locs):
        return [{'id': l.id, 'nombre': l.name, 'hueco': l.location_id.complete_name or ''} for l in locs]

    def _modelos_por_trozo(self, texto):
        """Modelos (product.template) cuya referencia, descripción o EAN contiene todas las palabras escritas.
        v1.2: en KOROSHI cada talla es un modelo aparte («2621JA54-000006-L»): primero los que tienen stock (de más a
        menos) y los que están a 0 no se enseñan, salvo que ninguno tenga stock. Devuelve (filas, hay más, a 0
        ocultos, ninguno con stock)."""
        palabras = [w for w in texto.split() if w]
        dominio = [('type', '=', 'product')]
        for w in palabras:
            lit = '%' + _literal(w) + '%'
            dominio += ['|', '|', ('default_code', '=ilike', lit), ('name', '=ilike', lit), ('barcode', '=ilike', lit)]
        productos = self._env('product.product').search(dominio, limit=MAX_PRODUCTOS_TROZO)
        cortado = len(productos) >= MAX_PRODUCTOS_TROZO
        plantillas = productos.mapped('product_tmpl_id')
        if not plantillas:
            return [], False, 0, False
        todos = plantillas.mapped('product_variant_ids')
        stock = {}
        for g in self._env('stock.quant').read_group(
                self._dominio_quant() + [('product_id', 'in', todos.ids)],
                ['product_id', 'quantity:sum', 'reserved_quantity:sum'], ['product_id'], lazy=False):
            stock[g['product_id'][0]] = g
        filas = []
        for t in plantillas:
            uds = sum((stock.get(p.id) or {}).get('quantity', 0.0) for p in t.product_variant_ids)
            res = sum((stock.get(p.id) or {}).get('reserved_quantity', 0.0) for p in t.product_variant_ids)
            filas.append({'id': t.id, 'nombre': t.display_name, 'referencia': t.default_code or '',
                          'variantes': len(t.product_variant_ids), 'uds': _redondear(uds),
                          'reservadas': _redondear(res), 'libres': _redondear(uds - res)})
        con = [f for f in filas if f['uds'] > 0]
        if con:
            con.sort(key=lambda f: (-f['uds'], f['nombre']))
            ocultos, ninguno = len(filas) - len(con), False
            filas = con
        else:
            filas.sort(key=lambda f: f['nombre'])
            ocultos, ninguno = 0, True
        return filas[:MAX_MODELOS], cortado or len(filas) > MAX_MODELOS, ocultos, ninguno

    # ------------------------------------------------------------------ datos
    def _datos_modelo(self, plantilla, producto_id=False):
        """Tallas y colores del modelo: stock, reservado, libre y entradas pendientes de cada uno."""
        variantes = plantilla.product_variant_ids
        stock = {g['product_id'][0]: g for g in self._env('stock.quant').read_group(
            self._dominio_quant() + [('product_id', 'in', variantes.ids)],
            ['product_id', 'quantity:sum', 'reserved_quantity:sum'], ['product_id'], lazy=False)}
        entradas = {g['product_id'][0]: g for g in self._env('stock.move').read_group(
            self._dominio_entradas() + [('product_id', 'in', variantes.ids)],
            ['product_id', 'product_qty:sum'], ['product_id'], lazy=False)}
        filas = []
        for p in variantes:
            s = stock.get(p.id) or {}
            uds = s.get('quantity', 0.0)
            res = s.get('reserved_quantity', 0.0)
            filas.append({'id': p.id, 'variante': self._nombre_variante(p), 'referencia': p.default_code or '',
                          'ean': p.barcode or '', 'uds': _redondear(uds), 'reservadas': _redondear(res),
                          'libres': _redondear(uds - res),
                          'entradas': _redondear((entradas.get(p.id) or {}).get('product_qty', 0.0))})
        total = {k: _redondear(sum(f[k] for f in filas)) for k in ('uds', 'reservadas', 'libres', 'entradas')}
        # v1.1: dónde está el modelo entero (todas las tallas), sin tener que pulsar cada talla (pedido de Isaac 19/11)
        quants = self._env('stock.quant').search(
            self._dominio_quant() + [('product_id', 'in', variantes.ids), ('quantity', '!=', 0)],
            limit=MAX_UBICACIONES + 1)
        donde = []
        for q in quants[:MAX_UBICACIONES]:
            hueco, cont = self._hueco_y_contenedor(q.location_id)
            donde.append({'hueco_id': hueco.id, 'hueco': hueco.complete_name, 'contenedor': cont,
                          'ubicacion_id': q.location_id.id, 'producto_id': q.product_id.id,
                          'variante': self._nombre_variante(q.product_id), 'uds': _redondear(q.quantity),
                          'reservadas': _redondear(q.reserved_quantity),
                          'libres': _redondear(q.quantity - q.reserved_quantity)})
        donde.sort(key=lambda f: (f['hueco'], f['contenedor'], f['variante']))
        return {'id': plantilla.id, 'nombre': plantilla.display_name, 'referencia': plantilla.default_code or '',
                'filas': filas, 'total': total, 'producto_id': producto_id or False,
                'donde': donde, 'donde_mas': len(quants) > MAX_UBICACIONES}

    def _dominio_entradas(self):
        return [('picking_type_id.code', '=', 'incoming'), ('state', 'in', ESTADOS_ABIERTOS),
                ('location_dest_id.usage', '=', 'internal'), ('company_id', '=', COMPANY_ID)]

    def _reservas(self, dominio_extra):
        """OUT (y otros albaranes) con reserva: una fila por albarán con sus uds reservadas y de dónde salen."""
        lineas = self._env('stock.move.line').search(
            [('state', 'not in', ('done', 'cancel')), ('product_qty', '>', 0), ('picking_id', '!=', False),
             ('location_id.usage', '=', 'internal'), ('picking_id.company_id', '=', COMPANY_ID)] + dominio_extra,
            order='picking_id', limit=MAX_OUT * 20)
        por_albaran = {}
        for ml in lineas:
            pk = ml.picking_id
            d = por_albaran.get(pk.id)
            if not d:
                if len(por_albaran) >= MAX_OUT:
                    continue
                d = por_albaran[pk.id] = {'id': pk.id, 'nombre': pk.name, 'origen': pk.origin or '',
                                          'tipo': pk.picking_type_id.name or '', 'estado': pk.state,
                                          'estado_txt': dict(pk._fields['state'].selection).get(pk.state, pk.state),
                                          'uds': 0.0, 'desde': set(), 'prendas': set()}
            d['uds'] += ml.product_qty
            hueco, cont = self._hueco_y_contenedor(ml.location_id)
            d['desde'].add(cont or hueco.complete_name)
            d['prendas'].add(ml.product_id.default_code or ml.product_id.display_name)
        filas = []
        for d in por_albaran.values():
            d['uds'] = _redondear(d['uds'])
            d['desde'] = ', '.join(sorted(d['desde']))
            d['prendas'] = ', '.join(sorted(d['prendas']))
            filas.append(d)
        filas.sort(key=lambda f: f['nombre'])
        return {'filas': filas, 'mas': len(lineas) >= MAX_OUT * 20 or len(por_albaran) >= MAX_OUT,
                'uds': _redondear(sum(f['uds'] for f in filas))}

    def _datos_prenda(self, producto):
        """Una talla/color: dónde está (hueco y contenedor), quién la reserva y qué recepciones la traen."""
        quants = self._env('stock.quant').search(
            self._dominio_quant() + [('product_id', '=', producto.id), ('quantity', '!=', 0)])
        donde = []
        for q in quants:
            hueco, cont = self._hueco_y_contenedor(q.location_id)
            donde.append({'hueco_id': hueco.id, 'hueco': hueco.complete_name, 'contenedor': cont,
                          'ubicacion_id': q.location_id.id, 'uds': _redondear(q.quantity),
                          'reservadas': _redondear(q.reserved_quantity),
                          'libres': _redondear(q.quantity - q.reserved_quantity)})
        donde.sort(key=lambda f: (f['hueco'], f['contenedor']))
        moves = self._env('stock.move').search(self._dominio_entradas() + [('product_id', '=', producto.id)],
                                               order='date_expected, id', limit=MAX_ENTRADAS + 1)
        entradas = [{'id': m.picking_id.id, 'nombre': m.picking_id.name or m.reference or '',
                     'origen': m.picking_id.origin or m.origin or '',
                     'fecha': comun.a_local(m.picking_id.scheduled_date or m.date_expected).strftime('%d/%m/%Y %H:%M')
                     if (m.picking_id.scheduled_date or m.date_expected) else '',
                     'estado_txt': dict(m._fields['state'].selection).get(m.state, m.state),
                     'uds': _redondear(m.product_qty)} for m in moves[:MAX_ENTRADAS]]
        return {'id': producto.id, 'nombre': producto.display_name, 'variante': self._nombre_variante(producto),
                'plantilla_id': producto.product_tmpl_id.id, 'ean': producto.barcode or '',
                'donde': donde[:MAX_UBICACIONES], 'donde_mas': max(0, len(donde) - MAX_UBICACIONES),
                'uds': _redondear(sum(f['uds'] for f in donde)),
                'reservadas': _redondear(sum(f['reservadas'] for f in donde)),
                'reservas': self._reservas([('product_id', '=', producto.id)]),
                'entradas': entradas, 'entradas_mas': len(moves) > MAX_ENTRADAS,
                'entradas_uds': _redondear(sum(e['uds'] for e in entradas))}

    def _datos_ubicacion(self, loc):
        """Un hueco (con sus contenedores) o un contenedor: lo que tiene dentro, prenda por prenda."""
        Loc = self._env('stock.location')
        es_cont = _es_contenedor_nombre(loc.name)
        locs = loc
        contenedores = []
        if not es_cont:
            hijos = Loc.search([('location_id', '=', loc.id), ('usage', '=', 'internal')]).filtered(
                lambda l: _es_contenedor_nombre(l.name))
            locs |= hijos
            por_hijo = {g['location_id'][0]: g for g in self._env('stock.quant').read_group(
                [('location_id', 'in', hijos.ids), ('quantity', '!=', 0)],
                ['location_id', 'quantity:sum', 'reserved_quantity:sum'], ['location_id'], lazy=False)}
            for h in hijos.sorted('name'):
                g = por_hijo.get(h.id) or {}
                contenedores.append({'id': h.id, 'nombre': h.name, 'uds': _redondear(g.get('quantity', 0.0)),
                                     'reservadas': _redondear(g.get('reserved_quantity', 0.0))})
        quants = self._env('stock.quant').search([('location_id', 'in', locs.ids), ('quantity', '!=', 0)],
                                                 limit=MAX_FILAS_HUECO * 3)
        filas = []
        for q in quants:
            p = q.product_id
            filas.append({'producto_id': p.id, 'plantilla_id': p.product_tmpl_id.id, 'nombre': p.display_name,
                          'referencia': p.default_code or '', 'ean': p.barcode or '',
                          'contenedor': q.location_id.name if q.location_id != loc else '',
                          'uds': _redondear(q.quantity), 'reservadas': _redondear(q.reserved_quantity),
                          'libres': _redondear(q.quantity - q.reserved_quantity)})
        filas.sort(key=lambda f: (f['contenedor'], f['referencia'], f['nombre']))
        hueco = loc.location_id if es_cont else loc
        return {'id': loc.id, 'nombre': loc.name, 'completo': loc.complete_name, 'es_contenedor': es_cont,
                'activo': loc.active, 'hueco_id': hueco.id, 'hueco': hueco.complete_name or '',
                'contenedores': contenedores, 'filas': filas[:MAX_FILAS_HUECO],
                'mas': max(0, len(filas) - MAX_FILAS_HUECO),
                'uds': _redondear(sum(f['uds'] for f in filas)),
                'reservadas': _redondear(sum(f['reservadas'] for f in filas)),
                'reservas': self._reservas([('location_id', 'in', locs.ids)])}

    def _datos_lineal(self, lineal):
        """Huecos de un lineal (L94), sacado del nombre del hueco «07828 - L94 P35 C1», como Contenedores 1.3."""
        Loc = self._env('stock.location')
        Quant = self._env('stock.quant')
        clave = ' %s ' % lineal
        huecos = Loc.search([('usage', '=', 'internal'), ('name', 'ilike', clave)], order='name',
                            limit=MAX_HUECOS + 1)
        huecos = huecos.filtered(lambda l: not _es_contenedor_nombre(l.name) and clave in (' %s ' % l.name.upper()))
        truncado = len(huecos) > MAX_HUECOS
        huecos = huecos[:MAX_HUECOS]
        hijos = Loc.search([('location_id', 'in', huecos.ids), ('usage', '=', 'internal')]).filtered(
            lambda l: _es_contenedor_nombre(l.name))
        por_loc = {g['location_id'][0]: g for g in Quant.read_group(
            [('location_id', 'in', hijos.ids + huecos.ids), ('quantity', '!=', 0)],
            ['location_id', 'quantity:sum', 'reserved_quantity:sum'], ['location_id'], lazy=False)}
        datos = {}
        for h in huecos:
            g = por_loc.get(h.id) or {}
            datos[h.id] = {'id': h.id, 'nombre': h.name, 'n_cont': 0, 'n_cont_stock': 0,
                           'uds': g.get('quantity', 0.0), 'reservadas': g.get('reserved_quantity', 0.0)}
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
        filas = []
        for h in huecos:
            d = datos[h.id]
            d['uds'] = _redondear(d['uds'])
            d['reservadas'] = _redondear(d['reservadas'])
            filas.append(d)
        return {'codigo': lineal, 'huecos': filas, 'truncado': truncado,
                'con_stock': len([f for f in filas if f['uds']]),
                'uds': _redondear(sum(f['uds'] for f in filas))}

    # ------------------------------------------------------------------ rutas
    @http.route('/koroshi/buscador_stock/buscar', type='json', auth='user')
    def buscar(self, texto='', **kw):
        """Lo escrito en la caja: lineal, contenedor, hueco, prenda o trozo de referencia/descripción."""
        try:
            self._comprobar_usuario()
            texto = (texto or '').strip()
            if not texto:
                raise UserError('Escribe un EAN, una referencia, un trozo de la descripción, un hueco, un lineal '
                                'o un contenedor.')
            Loc = self._env('stock.location')
            if LINEAL_RE.match(texto):
                return {'ok': True, 'tipo': 'lineal', 'lineal': self._datos_lineal(texto.upper())}
            if _es_contenedor_nombre(texto):
                loc = Loc.search([('usage', '=', 'internal'), '|', ('name', '=ilike', _literal(texto)),
                                  ('barcode', '=ilike', _literal(texto))]).filtered(
                    lambda l: _es_contenedor_nombre(l.name))
                if len(loc) == 1:
                    return {'ok': True, 'tipo': 'ubicacion', 'ubicacion': self._datos_ubicacion(loc)}
                locs, mas = self._contenedores_por_trozo(texto)
                if locs:
                    return {'ok': True, 'tipo': 'lista', 'texto': texto, 'modelos': [], 'modelos_mas': False,
                            'ocultos_cero': 0, 'ninguno_con_stock': False, 'contenedores': self._lista_contenedores(locs), 'contenedores_mas': mas}
                raise UserError('No encuentro el contenedor %s (o está archivado).' % texto)
            loc = Loc.search([('barcode', '=', texto), ('usage', '=', 'internal')])
            if len(loc) == 1:
                return {'ok': True, 'tipo': 'ubicacion', 'ubicacion': self._datos_ubicacion(loc)}
            if len(loc) > 1:
                raise UserError('Hay %d ubicaciones con el código %s. Avisa a IT.' % (len(loc), texto))
            producto = self._buscar_producto(texto)
            if producto:
                return {'ok': True, 'tipo': 'modelo',
                        'modelo': self._datos_modelo(producto.product_tmpl_id, producto.id),
                        'prenda': self._datos_prenda(producto)}
            if len(texto) < MIN_TROZO:
                raise UserError('Escribe al menos %d caracteres para buscar por un trozo.' % MIN_TROZO)
            modelos, modelos_mas, ocultos, ninguno = self._modelos_por_trozo(texto)
            locs, cont_mas = self._contenedores_por_trozo(texto)
            if not modelos and not locs:
                raise UserError('No encuentro nada con «%s»: ni prenda, ni hueco, ni contenedor.' % texto)
            if len(modelos) == 1 and not locs:      # v1.1: uno solo (v1.2: uno solo con stock): se abre directamente
                t = self._env('product.template').browse(modelos[0]['id'])
                return {'ok': True, 'tipo': 'modelo', 'modelo': self._datos_modelo(t), 'prenda': False}
            return {'ok': True, 'tipo': 'lista', 'texto': texto, 'modelos': modelos, 'modelos_mas': modelos_mas,
                    'ocultos_cero': ocultos, 'ninguno_con_stock': ninguno,
                    'contenedores': self._lista_contenedores(locs), 'contenedores_mas': cont_mas}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/koroshi/buscador_stock/modelo', type='json', auth='user')
    def modelo(self, plantilla_id=False, producto_id=False, **kw):
        try:
            self._comprobar_usuario()
            t = self._env('product.template').browse(int(plantilla_id or 0)).exists()
            if not t:
                raise UserError('Ese modelo ya no existe.')
            r = {'ok': True, 'tipo': 'modelo', 'modelo': self._datos_modelo(t, producto_id), 'prenda': False}
            p = self._env('product.product').browse(int(producto_id or 0)).exists()
            if p and p.product_tmpl_id == t:
                r['prenda'] = self._datos_prenda(p)
            return r
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/koroshi/buscador_stock/ubicacion', type='json', auth='user')
    def ubicacion(self, ubicacion_id=False, **kw):
        try:
            self._comprobar_usuario()
            loc = self._env('stock.location').with_context(active_test=False).browse(int(ubicacion_id or 0)).exists()
            if not loc or loc.usage != 'internal':
                raise UserError('Esa ubicación ya no existe o no es interna.')
            return {'ok': True, 'tipo': 'ubicacion', 'ubicacion': self._datos_ubicacion(loc)}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}
