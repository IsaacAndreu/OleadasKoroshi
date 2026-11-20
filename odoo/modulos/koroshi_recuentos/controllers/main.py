# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Recuentos - rutas de la pantalla «Referencia» (fase 1, SOLO LECTURA).
# Diseño: bin/versiones/diseno-comprobar-inventario_2026-11-20_v3.md
# /referencia: un modelo (2621XC04), una variante o un EAN -> todas sus variantes (color x talla) con lo que dice
#   Odoo, y los sitios (hueco o contenedor) en orden de recorrido. También salen los sitios donde se quitó stock de la
#   referencia en los últimos DIAS_AJUSTES días (ajuste a pérdidas de inventario), aunque Odoo diga 0: es donde puede
#   estar lo que falta.
# /caja: lo que dice Odoo que hay en un sitio (todas las referencias).
# Con sudo y solo lectura: no crea, no escribe y no mueve nada. Solo ubicaciones internas de la compañía 8.
# =============================================================================
import datetime

from odoo import fields, http
from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.koroshi_base import comun

from .. import logica

PREFIJOS_CONTENEDOR = ('KO_', 'TT_')
DIAS_AJUSTES = 90          # ajustes a pérdidas de inventario que se enseñan (días hacia atrás)
MAX_VARIANTES = 300
MAX_SITIOS = 200
MAX_MODELOS = 20           # modelos sugeridos si lo escrito es un trozo
MAX_CAJA = 80              # líneas como máximo al abrir un sitio
MIN_TROZO = 4


def _literal(texto):
    """El texto tal cual para un =like / =ilike («_» y «%» son comodines en SQL)."""
    return (texto or '').replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def _es_contenedor(nombre):
    return (nombre or '').upper()[:3] in PREFIJOS_CONTENEDOR


def _fecha(dt):
    loc = comun.a_local(dt)
    return loc.strftime('%d/%m/%Y %H:%M') if loc else ''


class KoroshiRecuentos(http.Controller):

    def _comprobar_usuario(self):
        if not request.env.user.has_group('stock.group_stock_user'):
            raise UserError('No tienes permiso para ver el inventario.')

    # ------------------------------------------------------------------ artículos
    def _por_codigo(self, codigo):
        """Variante por EAN (y UPC con 0 delante), código alternativo o referencia interna; vacío si no hay."""
        posibles = [codigo]
        if codigo.isdigit() and len(codigo) == 12:
            posibles.append('0' + codigo)
        if codigo.isdigit() and len(codigo) == 13 and codigo.startswith('0'):
            posibles.append(codigo[1:])
        Product = request.env['product.product'].sudo().with_context(active_test=False)
        p = Product.search([('barcode', 'in', posibles)], limit=1)
        if not p and 'product.barcode' in request.env:
            p = request.env['product.barcode'].sudo().search([('name', 'in', posibles)], limit=1).product_id
        if not p:
            p = Product.search([('default_code', '=', codigo)], limit=1)
        return p

    def _variantes(self, modelo):
        """Todas las variantes del modelo (también las archivadas: pueden tener stock). La referencia está en el
        nombre (9.116 artículos no tienen referencia interna) o en la referencia interna."""
        if not modelo:
            return request.env['product.product']
        patron = _literal(modelo) + '-%'
        Product = request.env['product.product'].sudo().with_context(active_test=False)
        return Product.search(['&', ('company_id', 'in', [comun.COMPANY_ID, False]),
                               '|', '|', ('name', '=like', patron), ('default_code', '=like', patron),
                               ('name', '=', modelo)], limit=MAX_VARIANTES)

    def _modelos_que_empiezan(self, texto):
        """Modelos distintos cuyo nombre empieza por el trozo escrito (para elegir)."""
        Product = request.env['product.product'].sudo()
        prods = Product.search([('company_id', 'in', [comun.COMPANY_ID, False]),
                                ('name', '=ilike', _literal(texto) + '%')], limit=400)
        vistos = []
        for p in prods:
            m = logica.modelo_de(p.name)
            if m and m not in vistos:
                vistos.append(m)
        return sorted(vistos)[:MAX_MODELOS]

    def _nombre_variante(self, p):
        return p.default_code or p.name or ''

    # ------------------------------------------------------------------ sitios
    def _sitio_de(self, loc):
        """(hueco, contenedor) de una ubicación: el contenedor KO_/TT_ cuelga del hueco."""
        if _es_contenedor(loc.name):
            return loc.location_id, loc
        return loc, None

    def _sitio_vacio(self, loc):
        hueco, cont = self._sitio_de(loc)
        return {
            'id': loc.id,
            'hueco': logica.hueco_corto(hueco.name),
            'hueco_largo': hueco.complete_name or '',
            'contenedor': cont.name if cont else '',
            'filas': {},            # producto_id -> {'uds', 'reservadas'}
            'ajuste': None,
            '_orden': logica.clave_recorrido(hueco.name),
        }

    # ------------------------------------------------------------------ rutas
    @http.route('/koroshi/recuentos/referencia', type='json', auth='user')
    def referencia(self, texto='', **kw):
        self._comprobar_usuario()
        texto = (texto or '').strip()
        if not texto:
            return {'error': 'Escribe o lee una referencia (2621XC04) o una prenda.'}
        prenda = self._por_codigo(texto)
        modelo = logica.modelo_de(self._nombre_variante(prenda) if prenda else texto)
        variantes = self._variantes(modelo)
        if not variantes and prenda:
            variantes = prenda          # artículo sin «-»: se enseña él solo
        if not variantes:
            if len(texto) < MIN_TROZO:
                return {'error': 'No hay ninguna referencia %s. Escribe al menos %d caracteres.' % (texto, MIN_TROZO)}
            modelos = self._modelos_que_empiezan(texto)
            if len(modelos) == 1:
                return self.referencia(texto=modelos[0])
            if not modelos:
                return {'error': 'No hay ninguna referencia que empiece por %s.' % texto}
            return {'tipo': 'modelos', 'texto': texto, 'modelos': modelos}
        return self._datos_referencia(modelo, variantes, prenda)

    def _datos_referencia(self, modelo, variantes, prenda):
        ids = variantes.ids
        Quant = request.env['stock.quant'].sudo()
        quants = Quant.search([('product_id', 'in', ids), ('location_id.usage', '=', 'internal'),
                               ('company_id', '=', comun.COMPANY_ID),
                               '|', ('quantity', '!=', 0), ('reserved_quantity', '!=', 0)])
        sitios = {}
        for q in quants:
            s = sitios.get(q.location_id.id)
            if s is None:
                s = sitios[q.location_id.id] = self._sitio_vacio(q.location_id)
            f = s['filas'].setdefault(q.product_id.id, {'uds': 0.0, 'reservadas': 0.0})
            f['uds'] += q.quantity
            f['reservadas'] += q.reserved_quantity

        # Stock quitado a mano (ajuste a pérdidas de inventario) en los últimos DIAS_AJUSTES días, por sitio
        desde = fields.Datetime.now() - datetime.timedelta(days=DIAS_AJUSTES)
        moves = request.env['stock.move'].sudo().search([
            ('product_id', 'in', ids), ('state', '=', 'done'), ('date', '>=', desde),
            ('location_id.usage', '=', 'internal'), ('location_dest_id.usage', '=', 'inventory'),
            ('company_id', '=', comun.COMPANY_ID)], order='date desc', limit=500)
        ajustes_uds = 0.0
        for mv in moves:
            loc = mv.location_id
            s = sitios.get(loc.id)
            if s is None:
                if len(sitios) >= MAX_SITIOS:
                    continue
                s = sitios[loc.id] = self._sitio_vacio(loc)
            a = s['ajuste']
            if a is None:            # el primero es el más reciente (order date desc)
                a = s['ajuste'] = {'uds': 0.0, 'veces': 0, 'fecha': _fecha(mv.date), 'que': mv.name or '',
                                   'quien': mv.create_uid.name or ''}
            a['uds'] += mv.product_qty
            a['veces'] += 1
            ajustes_uds += mv.product_qty

        # Variantes: color x talla
        info = {}
        for p in variantes:
            _m, color, talla = logica.partes(self._nombre_variante(p))
            info[p.id] = {'color': color or '—', 'talla': talla or '—'}
        colores = sorted({v['color'] for v in info.values()})
        tallas = sorted({v['talla'] for v in info.values()}, key=logica.clave_talla)
        celdas = {c: {t: {'uds': 0.0, 'reservadas': 0.0, 'existe': False} for t in tallas} for c in colores}
        for pid, v in info.items():
            celdas[v['color']][v['talla']]['existe'] = True
        for s in sitios.values():
            for pid, f in s['filas'].items():
                v = info.get(pid)
                if v:
                    c = celdas[v['color']][v['talla']]
                    c['uds'] += f['uds']
                    c['reservadas'] += f['reservadas']

        lista = []
        for s in sorted(sitios.values(), key=lambda x: (x['_orden'], x['contenedor'])):
            filas = []
            for pid, f in s['filas'].items():
                v = info.get(pid, {'color': '?', 'talla': '?'})
                filas.append({'color': v['color'], 'talla': v['talla'], 'uds': f['uds'],
                              'reservadas': f['reservadas']})
            filas.sort(key=lambda r: (r['color'], logica.clave_talla(r['talla'])))
            uds = sum(r['uds'] for r in filas)
            lista.append({
                'id': s['id'], 'hueco': s['hueco'], 'hueco_largo': s['hueco_largo'], 'contenedor': s['contenedor'],
                'filas': filas, 'uds': uds, 'reservadas': sum(r['reservadas'] for r in filas),
                'negativo': any(r['uds'] < 0 for r in filas),
                'varios_colores': len({r['color'] for r in filas if r['uds'] > 0}) > 1,
                'ajuste': s['ajuste'],
                # Odoo ya no tiene nada de la referencia aquí, pero se quitó a mano: hay que mirar
                'solo_ajuste': s['ajuste'] is not None and not any(r['uds'] or r['reservadas'] for r in filas),
            })
        lista = lista[:MAX_SITIOS]

        return {
            'tipo': 'referencia',
            'modelo': modelo,
            'leida': self._nombre_variante(prenda) if prenda else '',
            'n_variantes': len(variantes),
            'colores': colores,
            'tallas': tallas,
            'celdas': celdas,
            'total': sum(c['uds'] for fila in celdas.values() for c in fila.values()),
            'reservadas': sum(c['reservadas'] for fila in celdas.values() for c in fila.values()),
            'sitios': lista,
            'dias_ajustes': DIAS_AJUSTES,
            'ajustes_uds': ajustes_uds,
            'hora': comun.ahora_local().strftime('%d/%m/%Y %H:%M'),
        }

    @http.route('/koroshi/recuentos/caja', type='json', auth='user')
    def caja(self, ubicacion_id=False, modelo='', **kw):
        self._comprobar_usuario()
        loc = request.env['stock.location'].sudo().browse(int(ubicacion_id or 0)).exists()
        if not loc or loc.usage != 'internal' or loc.company_id.id not in (comun.COMPANY_ID, False):
            return {'error': 'Ese sitio no existe o no es del almacén.'}
        hueco, cont = self._sitio_de(loc)
        quants = request.env['stock.quant'].sudo().search(
            [('location_id', '=', loc.id), '|', ('quantity', '!=', 0), ('reserved_quantity', '!=', 0)])
        modelo = (modelo or '').upper()
        filas = []
        for q in quants:
            nombre = self._nombre_variante(q.product_id)
            filas.append({'nombre': nombre, 'uds': q.quantity, 'reservadas': q.reserved_quantity,
                          'de_la_referencia': bool(modelo) and logica.modelo_de(nombre) == modelo})
        filas.sort(key=lambda r: (not r['de_la_referencia'], r['nombre']))
        return {
            'id': loc.id,
            'hueco': logica.hueco_corto(hueco.name),
            'hueco_largo': hueco.complete_name or '',
            'contenedor': cont.name if cont else '',
            'filas': filas[:MAX_CAJA],
            'mas': max(0, len(filas) - MAX_CAJA),
            'uds': sum(r['uds'] for r in filas),
            'referencias': len(filas),
        }
