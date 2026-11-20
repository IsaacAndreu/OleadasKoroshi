# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Devoluciones - rutas de la pantalla «Ubicar devoluciones» (PDA). Con sudo, como Contenedores: el usuario de
# la PDA no necesita permisos sobre stock.location ni stock.move.
#   /inicio   opciones de manipulación (botones) y modo de stock
#   /leer     un código: tarjeta, prenda (EAN o referencia), contenedor KO_/TT_ o hueco (código de barras)
#   /guardar  una tanda: prendas + contenedor/hueco (todo o nada; si se repite la misma tanda, no se duplica)
# v1.1 «Llegadas» (fase 2, etapa 1):
#   /llegada  un código de paquete (matrícula CJ, Zalando o transportista) -> «ha llegado hoy»; o la tarjeta
#   /llegadas_hoy  lo llegado hoy por canal y los últimos leídos (para la pantalla)
# v1.2 «Contenido» (fase 2, etapa 2):
#   /contenido_leer     tarjeta, paquete (código llegado en los últimos 30 días) o prenda
#   /contenido_guardar  prendas del paquete con su resultado (bien / manipulación / tara); sin repetir la tanda
# Solo ubicaciones de la compañía 8 (UBRAN tiene los mismos huecos con el mismo código de barras: Contenedores 1.8.1).
# =============================================================================
import re

from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.addons.koroshi_base import comun

from ..models.devolucion import es_contenedor
from ..models.paquete import CANALES

COMPANY_ID = comun.COMPANY_ID
DE_LA_COMPANIA = ('company_id', 'in', [COMPANY_ID, False])
MAX_UDS_ARTICULO = 500      # uds de un artículo en una tanda (más = lecturas de más)
MAX_ARTICULOS = 300         # artículos distintos en una tanda
RE_TANDA = re.compile(r'^[A-Za-z0-9_-]{6,40}$')


def _msg(e):
    return e.args[0] if e.args else str(e)


def _literal(texto):
    """El texto tal cual para un =ilike (en ILIKE «_» es «cualquier letra»; los contenedores son KO_110626_032)."""
    return (texto or '').replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


class KoroshiDevoluciones(http.Controller):

    def _comprobar_usuario(self):
        if not request.env.user.has_group('stock.group_stock_user'):
            raise UserError('No tienes permiso para ubicar devoluciones.')

    def _buscar_producto(self, codigo):
        """Prenda por EAN (con o sin 0 delante), código alternativo, referencia interna o nombre (como Contenedores)."""
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
        if not p:   # muchos artículos no tienen referencia interna: la referencia está en el nombre
            p = Product.search([('name', '=', codigo), DE_LA_COMPANIA], limit=1)
        return p

    def _destino(self, codigo):
        """Contenedor KO_/TT_ (por nombre o código de barras) o hueco (código de barras). Vacío si no es ninguno."""
        Loc = request.env['stock.location'].sudo()
        if es_contenedor(codigo):
            loc = Loc.search([('usage', '=', 'internal'), DE_LA_COMPANIA, '|',
                              ('name', '=ilike', _literal(codigo)), ('barcode', '=ilike', _literal(codigo))])
            loc = loc.filtered(lambda l: es_contenedor(l.name))
            if not loc:
                raise UserError('No encuentro el contenedor %s (o está archivado).' % codigo)
        else:
            loc = Loc.search([('barcode', '=', codigo), ('usage', '=', 'internal'), DE_LA_COMPANIA])
        if len(loc) > 1:
            raise UserError('Hay %d ubicaciones con el código %s. Avisa a IT.' % (len(loc), codigo))
        return loc

    def _datos_destino(self, loc):
        cont = es_contenedor(loc.name)
        return {'id': loc.id, 'nombre': loc.name, 'tipo': 'contenedor' if cont else 'hueco',
                'hueco': (loc.location_id.complete_name if cont else loc.complete_name) or ''}

    @http.route('/koroshi/devoluciones/inicio', type='json', auth='user')
    def inicio(self, **kw):
        try:
            self._comprobar_usuario()
            ops = request.env['koroshi.devolucion.manipulacion'].sudo().search([])
            return {'ok': True, 'modo': request.env['koroshi.devolucion.ubicada']._modo_stock(),
                    'opciones': [{'id': o.id, 'nombre': o.name, 'color': o.color or '#0b4f9c'} for o in ops]}
        except (UserError, ValidationError) as e:
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/koroshi/devoluciones/leer', type='json', auth='user')
    def leer(self, codigo='', **kw):
        try:
            self._comprobar_usuario()
            codigo = (codigo or '').strip()
            if not codigo:
                raise UserError('Código vacío.')
            if not es_contenedor(codigo):
                emp = request.env['hr.employee'].sudo().search([('barcode', '=', codigo)], limit=1)
                if emp:
                    return {'ok': True, 'tipo': 'persona', 'persona': {'id': emp.id, 'nombre': emp.name}}
            loc = self._destino(codigo)
            if loc:
                return {'ok': True, 'tipo': 'destino', 'destino': self._datos_destino(loc)}
            p = self._buscar_producto(codigo)
            if p:
                return {'ok': True, 'tipo': 'prenda', 'prenda': {'id': p.id, 'nombre': p.display_name}}
            raise UserError('Prenda no encontrada: «%s». No se ha contado.' % codigo)
        except (UserError, ValidationError) as e:
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/koroshi/devoluciones/guardar', type='json', auth='user')
    def guardar(self, tanda='', employee_id=False, manipulacion_id=False, destino_id=False, lineas=None, **kw):
        """lineas = [{'producto_id': id, 'uds': n}]. tanda = id que pone la PDA (si se reintenta, no se duplica)."""
        try:
            self._comprobar_usuario()
            if not RE_TANDA.match(tanda or ''):
                raise UserError('Tanda no válida. Vuelve a empezar.')
            emp = request.env['hr.employee'].sudo().browse(int(employee_id or 0)).exists()
            if not emp:
                raise UserError('Pasa antes tu tarjeta de operario.')
            man = request.env['koroshi.devolucion.manipulacion'].sudo().browse(int(manipulacion_id or 0)).exists()
            if not man or not man.active:
                raise UserError('Elige qué has hecho (la opción ya no existe).')
            destino = request.env['stock.location'].sudo().browse(int(destino_id or 0)).exists()
            if not destino or destino.usage != 'internal' or not destino.active or \
                    (destino.company_id and destino.company_id.id != COMPANY_ID):
                raise UserError('Ese contenedor o ubicación ya no es válido. Vuelve a leerlo.')
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
            if len(por_producto) > MAX_ARTICULOS:
                raise UserError('Más de %d artículos en una tanda: guárdalas en dos veces.' % MAX_ARTICULOS)
            for p, uds in por_producto.items():
                if uds > MAX_UDS_ARTICULO:
                    raise UserError('Más de %d uds de %s: revisa las lecturas.' % (MAX_UDS_ARTICULO, p.display_name))
            hechas, repetida = request.env['koroshi.devolucion.ubicada'].guardar_tanda(
                tanda, emp, man, destino, por_producto)
            total = sum(hechas.mapped('uds'))
            msg = 'Guardado: %d ud%s de «%s» en %s.' % (total, '' if total == 1 else 's', man.name, destino.name)
            # v1.0.1: devoluciones de tienda: todo entra como nuevo (ya no se dice en cada tanda)
            return {'ok': True, 'msg': msg, 'uds': total}
        except (UserError, ValidationError) as e:
            return {'ok': False, 'msg': _msg(e)}

    # ------------------------------------------------------------------ v1.1: Llegadas
    def _hoy(self):
        P = request.env['koroshi.devolucion.paquete'].sudo()
        hoy = comun.hoy_local()
        grupos = P.read_group([('dia', '=', hoy), ('estado', 'in', ('llegado', 'leido'))], ['canal'], ['canal'])
        por_canal = {g['canal']: g['canal_count'] for g in grupos}
        ultimos = P.search([('dia', '=', hoy), ('estado', 'in', ('llegado', 'leido'))], limit=8)
        return {'total': sum(por_canal.values()),
                'por_canal': [{'canal': c, 'nombre': n, 'n': por_canal.get(c, 0)} for c, n in CANALES
                              if por_canal.get(c)],
                'ultimos': [self._datos_paquete(p) for p in ultimos]}

    def _datos_paquete(self, p):
        loc = comun.a_local(p.llegada)
        return {'id': p.id, 'codigo': p.name, 'canal': dict(CANALES).get(p.canal, p.canal),
                'tienda': p.tienda_id.name or '', 'hora': loc.strftime('%d/%m %H:%M') if loc else '',
                'quien': p.employee_id.name or ''}

    @http.route('/koroshi/devoluciones/llegadas_hoy', type='json', auth='user')
    def llegadas_hoy(self, **kw):
        try:
            self._comprobar_usuario()
            return dict(self._hoy(), ok=True, canales=[{'id': c, 'nombre': n} for c, n in CANALES])
        except (UserError, ValidationError) as e:
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/koroshi/devoluciones/llegada', type='json', auth='user')
    def llegada(self, codigo='', canal='', employee_id=False, **kw):
        try:
            self._comprobar_usuario()
            codigo = (codigo or '').strip()
            if not codigo:
                raise UserError('Código vacío.')
            emp = request.env['hr.employee'].sudo().search([('barcode', '=', codigo)], limit=1)
            if emp:
                return {'ok': True, 'tipo': 'persona', 'persona': {'id': emp.id, 'nombre': emp.name}}
            emp = request.env['hr.employee'].sudo().browse(int(employee_id or 0)).exists()
            if not emp:
                raise UserError('Pasa antes tu tarjeta de operario.')
            p, nuevo = request.env['koroshi.devolucion.paquete'].registrar(codigo, canal, emp)
            d = self._datos_paquete(p)
            if nuevo:
                msg = 'Ha llegado: %s (%s%s).' % (d['codigo'], d['canal'], ', ' + d['tienda'] if d['tienda'] else '')
            else:
                msg = 'Ya estaba: %s llegó el %s (%s). No se apunta otra vez.' % (d['codigo'], d['hora'], d['quien'])
            return dict(self._hoy(), ok=True, tipo='paquete', nuevo=nuevo, msg=msg, paquete=d)
        except (UserError, ValidationError) as e:
            return {'ok': False, 'msg': _msg(e)}

    # ------------------------------------------------------------------ v1.2: Contenido
    def _datos_contenido(self, p):
        d = self._datos_paquete(p)
        d.update({'uds': p.uds_leidas, 'bien': p.uds_bien, 'manipular': p.uds_manipular, 'tara': p.uds_tara})
        return d

    @http.route('/koroshi/devoluciones/contenido_leer', type='json', auth='user')
    def contenido_leer(self, codigo='', **kw):
        try:
            self._comprobar_usuario()
            codigo = (codigo or '').strip()
            if not codigo:
                raise UserError('Código vacío.')
            emp = request.env['hr.employee'].sudo().search([('barcode', '=', codigo)], limit=1)
            if emp:
                return {'ok': True, 'tipo': 'persona', 'persona': {'id': emp.id, 'nombre': emp.name}}
            paq = request.env['koroshi.devolucion.paquete'].buscar_reciente(codigo)
            if paq:
                return {'ok': True, 'tipo': 'paquete', 'paquete': self._datos_contenido(paq)}
            p = self._buscar_producto(codigo)
            if p:
                return {'ok': True, 'tipo': 'prenda', 'prenda': {'id': p.id, 'nombre': p.display_name}}
            raise UserError('«%s» no es un paquete llegado (léelo antes en Llegadas) ni una prenda conocida.' % codigo)
        except (UserError, ValidationError) as e:
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/koroshi/devoluciones/contenido_guardar', type='json', auth='user')
    def contenido_guardar(self, tanda='', paquete_id=False, employee_id=False, lineas=None, **kw):
        """lineas = [{'producto_id', 'resultado' (bien/manipular/tara), 'manipulacion_id', 'uds'}]."""
        try:
            self._comprobar_usuario()
            if not RE_TANDA.match(tanda or ''):
                raise UserError('Tanda no válida. Vuelve a empezar.')
            emp = request.env['hr.employee'].sudo().browse(int(employee_id or 0)).exists()
            if not emp:
                raise UserError('Pasa antes tu tarjeta de operario.')
            paq = request.env['koroshi.devolucion.paquete'].sudo().browse(int(paquete_id or 0)).exists()
            if not paq or paq.estado == 'anulado':
                raise UserError('Ese paquete ya no es válido. Vuelve a leerlo.')
            Product = request.env['product.product'].sudo()
            Man = request.env['koroshi.devolucion.manipulacion'].sudo()
            juntas = {}
            for l in (lineas or []):
                p = Product.browse(int(l.get('producto_id') or 0)).exists()
                uds = int(l.get('uds') or 0)
                res = l.get('resultado')
                man = Man.browse(int(l.get('manipulacion_id') or 0)).exists() if res == 'manipular' else Man
                if not p or uds <= 0 or res not in ('bien', 'manipular', 'tara') or (res == 'manipular' and not man):
                    raise UserError('Lectura no válida. Vuelve a leer las prendas.')
                clave = (p, res, man)
                juntas[clave] = juntas.get(clave, 0) + uds
            if not juntas:
                raise UserError('Lee antes alguna prenda.')
            for (p, res, man), uds in juntas.items():
                if uds > MAX_UDS_ARTICULO:
                    raise UserError('Más de %d uds de %s: revisa las lecturas.' % (MAX_UDS_ARTICULO, p.display_name))
            nuevo = paq.guardar_contenido(tanda, emp, [(p, r, m, u) for (p, r, m), u in juntas.items()])
            d = self._datos_contenido(paq)
            msg = 'Guardado en %s: %d uds (bien %d, manipular %d, tara %d).' % (
                d['codigo'], d['uds'], d['bien'], d['manipular'], d['tara'])
            if not nuevo:
                msg += ' (ya estaba guardado; no se repite)'
            return {'ok': True, 'msg': msg, 'paquete': d}
        except (UserError, ValidationError) as e:
            return {'ok': False, 'msg': _msg(e)}
