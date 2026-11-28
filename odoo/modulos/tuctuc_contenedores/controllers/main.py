# -*- coding: utf-8 -*-
# =============================================================================
# TUCTUC Contenedores - rutas de la pantalla. Clon de koroshi_contenedores 1.17.0 para odoo.tuctuc.com (nave de
# Oriola - Amposta). Cambios (28/11/2026):
#   - Multicompañía: sin compañía fija. Las búsquedas van a las compañías de la PDA (tuctuc.almacen) que tiene el
#     usuario. La compañía sale del contenedor o del hueco leído.
#   - La nave es una, pero cada hueco existe una vez por compañía con el MISMO CÓDIGO DE BARRAS y otro número
#     delante (WH-OR/Stock/N1/23998 - L100 P17 C2 y MIECI/Stock/24003 - L100 P17 C2, código «L100 P17 C2», visto el
#     28/11): son «gemelos» (_gemelos, por el código de barras). Un hueco leído
#     enseña los contenedores de todas sus compañías; al mover, cada contenedor va al gemelo de SU compañía (nunca se
#     mueve stock entre compañías) y si no existe, error.
#   - Prefijos de contenedor del parámetro tuctuc_base.prefijos_contenedor (KO_, TT_, UB_, MI_).
#   - Sin zona 0 (en Oriola no hay outlet, Isaac 28/11): todos los lineales y todas las temporadas, salvo que los
#     parámetros tuctuc_contenedores.lineales / .temporadas digan otra cosa.
#   - Modelo-color: plantilla y atributo de color (los artículos no se llaman MODELO-COLOR-TALLA).
# Con sudo: el usuario de la PDA no necesita permisos sobre
# stock.location. Cambian location_id del contenedor (KO_/TT_), lo archivan y escriben en tuctuc.contenedor.movimiento.
# v1.5: /cero y /anadir hacen ajustes de inventario (stock.move hecho contra pérdidas de inventario); quién y cuándo
# queda en tuctuc.contenedor.movimiento, como en Lecturas y Faltantes.
# v1.6: /leer con una prenda (EAN o referencia) dice dónde hay stock de ella; /mover dice cuántos contenedores movió.
# v1.7: /cantidad pone las uds reales de un artículo del contenedor (ajuste de la diferencia, + o -, nunca por debajo
# de lo reservado). /buscar y /leer encuentran el contenedor por un trozo del nombre (etiqueta rota: «290726_44»).
# v1.8: /buscar y /leer por trozo buscan todo lo que tiene código: contenedores, huecos (código de barras o nombre),
# lineales y artículos (EAN, referencia o nombre); /donde dice dónde está un artículo por su id. Leer la referencia
# entera de un artículo (2622JA00-000003-L) ya lo encuentra: en muchos artículos la referencia solo está en el nombre.
# v1.13 (revisión general 23/11): a Faltantes solo la diferencia (R1); «Cambiar» no se hace con prendas leídas sin
# validar ni si Odoo ha cambiado mientras se contaba (R2); «Añadir» con id de tanda (R3); «Poner a cero» cierra sus
# faltantes como no encontrados y «Archivar» no deja faltantes con vuelta al contenedor (R4); cada faltante deja su
# línea en el registro; la compañía sale de tuctuc_base (O6).
# v1.14 (R23): /cambiar_articulo («Es otro»): lo que Odoo llama A en el contenedor es B (error de talla). Un ajuste de
# -N de A y otro de +N de B en un savepoint, y UNA línea en el registro con los dos movimientos.
# v1.15 (revisión general 23/11, O5 y R16): grupo, tarjeta y búsqueda de la prenda salen de tuctuc_base.pda (1.2.0).
# La tarjeta tiene que ser de un operario activo de la compañía (antes bastaba con que existiera).
# =============================================================================
import base64
import json
import logging
import re

from odoo import fields, http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import float_compare, float_is_zero
from odoo.addons.tuctuc_base import pda

from .. import logica

_logger = logging.getLogger(__name__)

MAX_LINEAS = 40
MAX_ANADIR = 500          # v1.5: uds de un artículo en un solo «Añadir» (más = lecturas de más)
ORIGEN = 'Desde Contenedores'   # v1.13: nota en el faltante y en el historial de la OUT
MAX_HUECOS = 400
MAX_DONDE = 60            # v1.6: ubicaciones como máximo al buscar dónde está un artículo
MAX_BUSCAR = 20           # v1.7: contenedores como máximo al buscar por un trozo del nombre
MIN_BUSCAR = 2            # v1.7: caracteres mínimos para buscar por un trozo
MIN_BUSCAR_OTROS = 3      # v1.8: huecos y artículos, a partir de 3 caracteres
MAX_TIPO = 8              # v1.8: resultados como máximo de cada tipo (contenedor, hueco, artículo)
# v1.8.2: también los lineales de MU (MU-01…MU-14): sus huecos se llaman «MU-01 P00 C1», sin número delante
LINEAL_RE = re.compile(r'^(L\d{1,4}|MU-? ?\d{1,2})$', re.I)

# 1.0.1 (prueba en tuctuc 28/11): en Oriola los lineales del 1 al 9 se escriben con cero («00049 - L01 P30 C1»):
# «Compactar» L1 decía «No encuentro columnas en L1». Se busca L1 y L01.
_SQL_LINEAL = 'AND (h.name ILIKE %s OR h.name ILIKE %s OR h.name ILIKE %s OR h.name ILIKE %s)'


def _patrones_lineal(n):
    """ILIKE del lineal n en el nombre del hueco, con y sin cero delante: ['% L1 %', 'L1 %', '% L01 %', 'L01 %']."""
    res = []
    for codigo in ('L%d' % n, 'L%02d' % n):
        res += ['%% %s %%' % codigo, '%s %%' % codigo]
    return res
LINEAL_DELANTE_RE = re.compile(r'^(L\d{1,4}|MU-\d{1,2})(\s|$)', re.I)   # «MU-00 P» o «L70 P3»: se ofrece el lineal
# v1.16.0: retirar cajas a 0 (parámetros del sistema; los pone IT)
PARAM_LINEALES = 'tuctuc_contenedores.lineales'     # «1-189» o vacío (todos): lineales de la ronda y de Compactar
PARAM_REVISAR = 'tuctuc_contenedores.tarjetas_revisar'         # ids de empleado: stock negativo y descuadres
PARAM_CON_PRENDAS = 'tuctuc_contenedores.tarjetas_con_prendas'  # ids de empleado: cajas a 0 con prendas
GRUPO_REVISAR = 'tuctuc_contenedores.group_revisar'            # usuarios de Odoo que revisan sin tarjeta
# v1.17.0: «Compactar» (fase 1). Parámetros del sistema; si no están, los valores de aquí
PARAM_CAJAS_COLUMNA = 'tuctuc_contenedores.cajas_columna'   # 8: cajas que caben en una columna (medio palé)
PARAM_CAJAS_VACIAR = 'tuctuc_contenedores.cajas_vaciar'     # 4: se vacían las columnas con menos cajas que esto
PARAM_DISTANCIA = 'tuctuc_contenedores.lineales_distancia'  # 2: destino en el mismo lineal o hasta ±2
PARAM_TEMPORADAS = 'tuctuc_contenedores.temporadas'   # vacío = todas (TUCTUC); «AW26-27,SS26» = solo esas


def _lineal(texto):
    """Código del lineal normalizado (L94, MU-01) o None. «mu1», «MU 01» y «MU-1» son MU-01."""
    t = (texto or '').strip().upper()
    if not LINEAL_RE.match(t):
        return None
    if t.startswith('MU'):
        return 'MU-%02d' % int(re.sub(r'\D', '', t))
    return t


def _prefijos():
    """Prefijos de contenedor (parámetro tuctuc_base.prefijos_contenedor), en mayúsculas. Todos de 3 caracteres."""
    return [p.upper() for p in pda.prefijos_contenedor(request.env)]


def _es_contenedor_nombre(nombre):
    return (nombre or '').upper()[:3] in _prefijos()


def _cias():
    """Ids de las compañías de la PDA (tuctuc.almacen) que tiene el usuario."""
    usuario = request.env.user.company_ids
    return [c.id for c in request.env['tuctuc.almacen'].companias() if c in usuario]


def _de_la_compania():
    """Dominio: de una compañía de la PDA o sin compañía (en koroshi: compañía 8)."""
    return ('company_id', 'in', _cias() + [False])


def _dominio_prefijos():
    """Dominio OR: el nombre empieza por alguno de los prefijos de contenedor."""
    partes = [('name', '=ilike', _literal(p) + '%') for p in _prefijos()]
    return ['|'] * (len(partes) - 1) + partes if partes else [('id', '=', 0)]


def _msg(e):
    return e.args[0] if e.args else str(e)


def _num(x):
    return ('%g' % round(x or 0, 2)).replace('.', ',')


def _literal(texto):
    """v1.4: el texto tal cual para un =ilike: en ILIKE «_» es «cualquier letra» y «%» «cualquier cosa», y los nombres
    son KO_110626_032 (con «_»): sin escaparlos, KO_110626_032 también encontraba p. ej. KOX110626X032."""
    return (texto or '').replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


class TuctucContenedores(http.Controller):

    def _comprobar_usuario(self):
        pda.comprobar_grupo(request.env, 'No tienes permiso para mover contenedores.')   # v1.15

    def _datos_contenedor(self, loc):
        Quant = request.env['stock.quant'].sudo()
        quants = Quant.search([('location_id', '=', loc.id), ('quantity', '!=', 0)])
        lineas = [{'producto': q.product_id.display_name, 'producto_id': q.product_id.id,   # v1.7: para «Cambiar»
                   'uds': q.quantity, 'reservadas': q.reserved_quantity}
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
            'con_prendas': loc.name in self._marcas_con_prendas(),     # v1.16.0
            'banda': self._banda(loc),                                  # v1.17.0
            'revisar': bool(quants.filtered(lambda q: q.quantity < 0 or (q.reserved_quantity > 0 and
                                                                        q.reserved_quantity > q.quantity))),
        }

    def _gemelos(self, hueco):
        """TUCTUC: el mismo hueco físico en todas las compañías de la PDA: los huecos con su mismo código de barras
        («L100 P17 C2»; el nombre lleva otro número delante en cada compañía). Sin código de barras, solo él."""
        Loc = request.env['stock.location'].sudo()
        if not hueco or _es_contenedor_nombre(hueco.name) or not hueco.barcode:
            return hueco
        return Loc.search([('barcode', '=', hueco.barcode), ('usage', '=', 'internal'), _de_la_compania()]) | hueco

    def _gemelo(self, hueco, compania, cerca=None):
        """TUCTUC: el hueco de esa compañía y, con `cerca` (donde está ahora el contenedor), de su mismo almacén: nunca
        se mueve stock entre compañías ni entre almacenes (MODA INTIMA tiene MODAI y MIECI con los mismos códigos de
        barras). Vacío si no existe."""
        almacen = cerca.get_warehouse() if cerca else None
        suyos = self._gemelos(hueco).filtered(lambda h: h.company_id == compania or not h.company_id)
        if almacen:
            suyos = suyos.filtered(lambda h: h.get_warehouse() == almacen)
        return suyos.sorted(lambda h: (h != hueco, h.id))[:1]

    def _compania_de(self, loc):
        """TUCTUC: compañía de una ubicación (la suya o la de su almacén de la PDA)."""
        return loc.company_id or request.env['tuctuc.almacen'].de_ubicacion(loc).company_id

    def _hijos_contenedor(self, hueco):
        """Contenedores del hueco y de sus gemelos (todas las compañías: es el mismo sitio físico)."""
        Loc = request.env['stock.location'].sudo()
        return Loc.search([('location_id', 'in', self._gemelos(hueco).ids), ('usage', '=', 'internal')]).filtered(
            lambda l: _es_contenedor_nombre(l.name))

    def _datos_hueco(self, hueco):
        """Hueco y sus contenedores KO_/TT_ con lo que tienen (para mover y para limpiar)."""
        Quant = request.env['stock.quant'].sudo()
        hijos = self._hijos_contenedor(hueco)
        gemelos = self._gemelos(hueco)
        quants = Quant.search([('location_id', 'in', hijos.ids + gemelos.ids), ('quantity', '!=', 0)])
        bandas = {b.contenedor_id.id: b.banda for b in request.env['tuctuc.contenedor.banda'].sudo().search(
            [('contenedor_id', 'in', hijos.ids)])}                      # v1.17.0
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
                          'vacio': d['n'] == 0 and not d['res'], 'banda': bandas.get(h.id, ''),   # v1.17: altura
                          'compania': h.company_id.name or ''})
        directo = {'uds': sum(por_loc.get(g.id, {}).get('uds', 0.0) for g in gemelos),
                   'n': sum(por_loc.get(g.id, {}).get('n', 0) for g in gemelos)}
        return {'id': hueco.id, 'nombre': hueco.complete_name, 'contenedores': conts,
                'directo_uds': directo['uds'], 'directo_n': directo['n']}

    def _datos_lineal(self, lineal):
        """Inventario de un lineal (L94...): sus huecos con contenedores, contenedores con stock y unidades.
        Solo lectura. El lineal se saca del nombre del hueco: «07828 - L94 P35 C1»."""
        Loc = request.env['stock.location'].sudo()
        Quant = request.env['stock.quant'].sudo()
        clave = ' %s ' % lineal
        # «07828 - L94 P35 C1» lleva el lineal en medio; «MU-01 P00 C1» (v1.8.2), al principio
        huecos = Loc.search([('usage', '=', 'internal'), _de_la_compania(), '|', ('name', 'ilike', clave),
                             ('name', '=ilike', _literal(lineal) + ' %')], order='name', limit=MAX_HUECOS + 1)
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
        # TUCTUC: el mismo hueco en varias compañías (gemelos) es una sola fila (el id, el del primero)
        filas, por_nombre = [], {}
        for h in huecos:
            d = datos[h.id]
            clave = h.barcode or h.id
            if clave not in por_nombre:
                por_nombre[clave] = d
                filas.append(d)
                continue
            f = por_nombre[clave]
            for k in ('n_cont', 'n_cont_stock', 'uds', 'reservadas', 'directo_uds'):
                f[k] += d[k]
        return {'codigo': lineal, 'huecos': filas, 'truncado': truncado,
                'con_stock': len([f for f in filas if f['uds'] or f['directo_uds']]),
                'uds': sum(f['uds'] + f['directo_uds'] for f in filas)}

    @http.route('/tuctuc/contenedores/hueco', type='json', auth='user')
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

    @http.route('/tuctuc/contenedores/limpiar', type='json', auth='user')
    def limpiar(self, ubicacion_id=False, employee_id=False, confirmado=False, **kw):
        """Archiva los contenedores KO_/TT_ del hueco que están a cero. Los que aún tienen stock o reservas no se tocan.
        Hay que confirmar que el hueco está físicamente vacío."""
        try:
            self._comprobar_usuario()
            if not confirmado:
                raise UserError('Confirma que la ubicación está físicamente vacía.')
            emp = self._empleado(employee_id)   # v1.16.0: tarjeta válida (activo y de la compañía), como el resto
            hueco = request.env['stock.location'].sudo().browse(int(ubicacion_id or 0)).exists()
            if not hueco:
                raise UserError('Escanea la ubicación.')
            self._validar_destino(hueco)
            Quant = request.env['stock.quant'].sudo()
            Mov = request.env['tuctuc.contenedor.movimiento'].sudo()
            archivados, con_stock = [], []
            Faltante = request.env['tuctuc.faltante'].sudo()
            marcadas = self._marcas_con_prendas()     # v1.16.0
            for c in self._hijos_contenedor(hueco):
                if c.name in marcadas or request.env['stock.move.line'].sudo().search_count([
                        ('state', 'not in', ('done', 'cancel')), '|', ('location_id', '=', c.id),
                        ('location_dest_id', '=', c.id)]):
                    con_stock.append('%s (marcada con prendas o con movimiento sin validar)' % c.name)
                    continue
                quants = Quant.search([('location_id', '=', c.id), '|', ('quantity', '!=', 0),
                                       ('reserved_quantity', '!=', 0)])
                if quants:
                    con_stock.append(c.name)
                    continue
                if Faltante.en_ronda_de(c):   # v1.13 (R4): con un faltante en una ronda abierta no se toca
                    con_stock.append('%s (faltante en ronda)' % c.name)
                    continue
                Faltante.antes_de_archivar(c)
                c.write({'active': False})
                Mov.create({'accion': 'archivar', 'contenedor': c.name, 'origen_id': hueco.id,
                            'origen': hueco.complete_name, 'destino': '(archivado, vacío, confirmado)',
                            'employee_id': emp.id})
                archivados.append(c.name)
            if not archivados and not con_stock:
                raise UserError('%s no tiene contenedores: ya está limpia.' % hueco.complete_name)
            msg = '%s: %d contenedor(es) vacío(s) archivado(s) en %s' % (emp.name, len(archivados),
                                                                         hueco.complete_name)
            if con_stock:
                msg += '. NO se tocan por tener stock (o un faltante en ronda): %s' % ', '.join(con_stock)
            return {'ok': True, 'msg': msg, 'quedan': len(con_stock)}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    # ------------------------------------------------------------------ v1.5: compactar un hueco
    def _empleado(self, employee_id):
        return pda.empleado_valido(request.env, employee_id)   # v1.15 (R16): activo y de la compañía

    def _contenedor(self, contenedor_id):
        c = request.env['stock.location'].sudo().browse(int(contenedor_id or 0)).exists()
        if not c or not _es_contenedor_nombre(c.name) or c.usage != 'internal' or not c.active:
            raise UserError('Ese contenedor ya no es válido (¿archivado?). Vuelve a escanear el hueco.')
        return c

    def _quants(self, contenedor):
        """Prendas del contenedor: con cantidad o con reserva."""
        return request.env['stock.quant'].sudo().search([('location_id', '=', contenedor.id), '|',
                                                         ('quantity', '!=', 0), ('reserved_quantity', '!=', 0)])

    def _pedidos_reservados(self, contenedor, producto=None):
        """OUT (y su pedido) que tienen reservadas prendas de este contenedor (v1.7: o solo de un artículo)."""
        dominio = [('location_id', '=', contenedor.id), ('state', 'not in', ('done', 'cancel')), ('product_qty', '>', 0)]
        if producto:
            dominio.append(('product_id', '=', producto.id))
        mls = request.env['stock.move.line'].sudo().search(dominio)
        return ['%s%s' % (p.name, ' (%s)' % p.origin if p.origin else '') for p in mls.mapped('picking_id')]

    def _ajuste(self, producto, qty, contenedor, company, emp, accion, nombre, tanda=False):
        """Ajuste de inventario de qty uds (+ entra en el contenedor, - sale) contra la ubicación de pérdidas de
        inventario del artículo, como un ajuste de Odoo. Mismo movimiento que tuctuc_faltantes._mover (probado en
        producción). Deja su línea en el registro (quién, cuándo, artículo, uds y movimiento)."""
        move = self._mover_ajuste(producto, qty, contenedor, company, nombre)
        request.env['tuctuc.contenedor.movimiento'].sudo().create({
            'accion': accion, 'contenedor': contenedor.name, 'origen_id': contenedor.location_id.id,
            'origen': contenedor.location_id.complete_name, 'destino': contenedor.location_id.complete_name,
            'uds': qty, 'lineas': 1, 'producto_id': producto.id, 'move_id': move.id, 'employee_id': emp.id,
            'tanda': tanda or False,
        })
        return move

    def _mover_ajuste(self, producto, qty, contenedor, company, nombre):
        """v1.14: el movimiento de stock de _ajuste, sin línea en el registro (/cambiar_articulo deja una sola para
        los dos movimientos)."""
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
        return move

    @http.route('/tuctuc/contenedores/detalle', type='json', auth='user')
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

    @http.route('/tuctuc/contenedores/archivar', type='json', auth='user')
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
            self._antes_de_archivar(conts, emp)   # v1.13 (R4): antes de escribir nada
            Mov = request.env['tuctuc.contenedor.movimiento'].sudo()
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

    @http.route('/tuctuc/contenedores/archivar_uno', type='json', auth='user')
    def archivar_uno(self, contenedor_id=False, employee_id=False, confirmado=False, **kw):
        """v1.10.0: archiva el contenedor abierto (botón «Archivar» de su ficha), esté en la lista de mover o en la
        del hueco. Mismas reglas que «Archivar marcados»: confirmado y sin prendas ni reservas en el sistema."""
        try:
            self._comprobar_usuario()
            if not confirmado:
                raise UserError('Confirma que está físicamente vacío.')
            emp = self._empleado(employee_id)
            c = self._contenedor(contenedor_id)
            if self._quants(c):
                raise UserError('No se archiva: %s tiene prendas en el sistema. Ponlo a cero primero.' % c.name)
            self._antes_de_archivar([c], emp)   # v1.13 (R4)
            hueco = c.location_id
            c.write({'active': False})
            request.env['tuctuc.contenedor.movimiento'].sudo().create({
                'accion': 'archivar', 'contenedor': c.name, 'origen_id': hueco.id, 'origen': hueco.complete_name,
                'destino': '(archivado, vacío, confirmado)', 'employee_id': emp.id})
            return {'ok': True, 'msg': '%s: %s archivado (estaba en %s)' % (emp.name, c.name, hueco.complete_name)}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    def _buscar_producto(self, codigo):
        """Prenda por EAN (y UPC/EAN con 0 delante), código alternativo, referencia interna o nombre. Vacío si no hay.
        v1.15 (O5): la de tuctuc_base.pda, la misma en todas las pantallas (con sudo, como antes)."""
        return pda.buscar_producto(request.env['product.product'].sudo().env, codigo)

    def _donde(self, producto):
        """v1.6: dónde hay stock de un artículo (ubicaciones internas de la compañía), por hueco y contenedor, para
        devolver al sitio una prenda fuera de lugar. Solo lectura."""
        quants = request.env['stock.quant'].sudo().search([
            ('product_id', '=', producto.id), ('location_id.usage', '=', 'internal'),
            ('company_id', 'in', _cias()), ('quantity', '>', 0)])
        filas = []
        for q in quants:
            loc = q.location_id
            hueco = loc.location_id if _es_contenedor_nombre(loc.name) else loc
            filas.append({'hueco_id': hueco.id, 'hueco': hueco.complete_name,
                          'contenedor': loc.name if hueco != loc else '',
                          'uds': q.quantity, 'reservadas': q.reserved_quantity})
        filas.sort(key=lambda f: (f['hueco'], f['contenedor']))
        return {'id': producto.id, 'nombre': producto.display_name, 'filas': filas[:MAX_DONDE],
                'mas': max(0, len(filas) - MAX_DONDE), 'uds': sum(f['uds'] for f in filas),
                'reservadas': sum(f['reservadas'] for f in filas)}

    @http.route('/tuctuc/contenedores/producto', type='json', auth='user')
    def producto(self, codigo='', modelo_de=False, **kw):
        """Prenda leída para añadir: EAN (y UPC/EAN con 0 delante), código alternativo o referencia interna.
        v1.14: con modelo_de (id del artículo que dice Odoo, para «Es otro») dice también si es el mismo modelo."""
        try:
            self._comprobar_usuario()
            codigo = (codigo or '').strip()
            if not codigo:
                raise UserError('Código vacío.')
            p = self._buscar_producto(codigo)
            if not p:
                raise UserError('%s no es una prenda conocida: no se añade.' % codigo)
            res = {'id': p.id, 'nombre': p.display_name}
            if modelo_de:   # v1.14
                a = request.env['product.product'].sudo().browse(int(modelo_de)).exists()
                res['mismo_modelo'] = bool(a) and logica.mismo_modelo(a.product_tmpl_id.id, p.product_tmpl_id.id)
            return {'ok': True, 'producto': res}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    def _leidas(self, c, producto=None):
        """v1.13: líneas abiertas (OUT sin validar) que sacan prendas de este contenedor y ya tienen algo leído."""
        dominio = [('location_id', '=', c.id), ('state', 'not in', ('done', 'cancel')), ('qty_done', '>', 0)]
        if producto:
            dominio.append(('product_id', '=', producto.id))
        return request.env['stock.move.line'].sudo().search(dominio)

    def _reservas_a_faltantes(self, c, emp, producto=None, dejar=0, que=''):
        """v1.11.0: cada línea de OUT reservada en el contenedor pasa por Faltantes como si el operario la marcara:
        reubicar en el hueco con stock libre más cercano que llegue (tuctuc.faltante.reubicar) o, si no hay,
        sin_alternativa (la OUT sale sin ella). En los dos casos la unidad va a FALTANTE y queda su registro.
        No se toca una línea que ya tiene algo leído: alguien la está preparando.
        v1.12.0: con producto, solo sus líneas, y se para cuando lo reservado que queda es <= dejar.
        v1.13.0 (R1): pasa solo lo que sobra (reservado - dejar): una línea de 5 con 4 en el contenedor sigue con 4
        reservadas aquí y solo 1 pasa a Faltantes. El hueco alternativo se busca entre todos, no solo los 5 más
        cercanos. Cada faltante deja su línea en el registro de Contenedores.
        Devuelve (resumen por línea, faltantes creados)."""
        Faltante = request.env['tuctuc.faltante'].sudo()
        Mov = request.env['tuctuc.contenedor.movimiento'].sudo()
        dominio = [('location_id', '=', c.id), ('state', 'not in', ('done', 'cancel')), ('product_qty', '>', 0)]
        if producto:
            dominio.append(('product_id', '=', producto.id))
        # las pequeñas primero (logica.repartir): una OUT pasa entera antes que partir dos
        mls = request.env['stock.move.line'].sudo().search(dominio, order='product_qty, id')
        leidas = mls.filtered(lambda l: not float_is_zero(l.qty_done, precision_rounding=l.product_uom_id.rounding))
        if leidas:
            raise UserError('No se ha cambiado nada: %s ya tiene prendas leídas en %s (alguien la está '
                            'preparando). Espera a que acabe.' % (c.name, ', '.join(leidas.mapped('picking_id.name'))))
        sobra = sum(mls.mapped('product_qty')) - (dejar if producto else 0)
        origen = '%s (%s, %s, %s)' % (ORIGEN, c.name, que or 'compactar', emp.name)
        resumen, faltantes = [], Faltante.browse()
        for ml, quitar in zip(mls, logica.repartir(mls.mapped('product_qty'), sobra)):
            if not quitar:
                continue
            picking, product = ml.picking_id, ml.product_id
            parte = float_compare(quitar, ml.product_qty, precision_rounding=product.uom_id.rounding) < 0
            raiz = Faltante._raiz_stock(picking)
            destino = Faltante.mejor_destino(product, c, raiz, quitar)
            cantidad = quitar if parte else None
            if destino:
                f = Faltante.reubicar(ml, destino, emp, cantidad=cantidad, origen=origen)
                texto = '%s %s: %s ud(s) ahora se cogen en %s' % (picking.name, product.display_name, _num(quitar),
                                                                   f.ubicacion_nueva_id.complete_name)
            else:
                f = Faltante.sin_alternativa(ml, emp, cantidad=cantidad, origen=origen)
                texto = '%s %s: %s ud(s) sin stock en otro hueco, la OUT sale sin ellas' % (
                    picking.name, product.display_name, _num(quitar))
            resumen.append(texto)
            faltantes |= f
            Mov.create({'accion': 'faltante', 'contenedor': c.name, 'origen_id': c.location_id.id,
                        'origen': c.location_id.complete_name, 'destino': 'FALTANTE (%s)' % texto,
                        'uds': -f.cantidad_faltant, 'reservadas': -quitar, 'lineas': 1, 'producto_id': product.id,
                        'move_id': f.move_faltant_id.id, 'faltante_id': f.id, 'employee_id': emp.id})
        return resumen, faltantes

    def _antes_de_archivar(self, conts, emp=None):
        """v1.13 (R4): los faltantes pendientes con vuelta a estos contenedores pasan a apuntar a su hueco; si alguno
        está en una ronda abierta, error y no se archiva ninguno.
        v1.16.0: tampoco con movimientos sin validar, ni una caja marcada «Tiene prendas» salvo los de su lista."""
        Loc = request.env['stock.location'].sudo()
        ubicaciones = Loc.browse([c.id for c in conts])
        marcadas = [c.name for c in ubicaciones if c.name in self._marcas_con_prendas()]
        if marcadas and not self._puede_con_prendas(emp):
            raise UserError('No se archiva nada: %s está marcada «Tiene prendas» y la resuelven %s.' % (
                ', '.join(marcadas), self._nombres_tarjetas(PARAM_CON_PRENDAS)))
        # v1.16.0: una caja de una IN, INT u OUT sin validar (sale de ella o va a ella) no se archiva: rompería ese
        # albarán. Antes no se miraba (una caja a 0 de una recepción en curso se podía archivar).
        abiertas = request.env['stock.move.line'].sudo().search([
            ('state', 'not in', ('done', 'cancel')), '|', ('location_id', 'in', ubicaciones.ids),
            ('location_dest_id', 'in', ubicaciones.ids)])
        if abiertas:
            raise UserError('No se archiva nada: %s tiene movimientos sin validar en %s.' % (
                ', '.join(sorted(set((abiertas.mapped('location_id') | abiertas.mapped('location_dest_id'))
                                     .filtered(lambda l: l in ubicaciones).mapped('name')))),
                ', '.join(sorted(set(abiertas.mapped('picking_id.name')))) or 'un albarán'))
        request.env['tuctuc.faltante'].sudo().antes_de_archivar(ubicaciones)

    @http.route('/tuctuc/contenedores/cero', type='json', auth='user')
    def cero(self, contenedor_id=False, employee_id=False, confirmado=False, pasar_faltantes=False, **kw):
        """Pone a cero el contenedor (está físicamente vacío y Odoo dice que tiene prendas): ajuste de inventario de
        cada artículo. v1.11.0: si hay prendas reservadas para una OUT, con pasar_faltantes se hace antes lo mismo que
        el operario al marcar un faltante (tuctuc_faltantes): la línea se reserva en otro hueco con stock libre (el
        más cercano) o, si no hay, la OUT sale sin ella; la unidad va a FALTANTE y queda en Faltantes."""
        try:
            self._comprobar_usuario()
            if not confirmado:
                raise UserError('Confirma que el contenedor está físicamente vacío.')
            emp = self._empleado(employee_id)
            c = self._contenedor(contenedor_id)
            self._exigir_revisar(c, emp)        # v1.16.0: negativos y descuadres, solo los de «Revisar»
            quants = self._quants(c)
            if not quants:
                raise UserError('%s ya está a cero.' % c.name)
            if quants.filtered(lambda q: q.lot_id or q.package_id or q.owner_id):
                raise UserError('%s tiene prendas con lote, paquete o propietario: hazlo desde Odoo o avisa a IT.'
                                % c.name)
            resumen = []
            with request.env.cr.savepoint():    # todo o nada (también lo de Faltantes)
                if any(q.reserved_quantity for q in quants):
                    if not pasar_faltantes:      # la PDA pregunta antes, con las OUT
                        return {'ok': False, 'reservado': True, 'pedidos': self._pedidos_reservados(c),
                                'msg': '%s tiene prendas reservadas para %s.' % (
                                    c.name, ', '.join(self._pedidos_reservados(c)) or 'un pedido')}
                    resumen, faltantes = self._reservas_a_faltantes(c, emp, que='poner a cero')
                    # v1.13 (R4): el contenedor está vacío (confirmado): lo que pasó a FALTANTE no va a aparecer
                    # en él. Se cierra ya como no encontrado (de FALTANTE a pérdidas), sin ronda que vuelva aquí.
                    for f in faltantes:
                        f._cerrar_no_encontrado('%s puesto a cero (vacío, confirmado por %s): no encontrado.'
                                                % (c.name, emp.name))
                    if faltantes:
                        resumen = [r + ' (no encontrado)' for r in resumen]
                    quants = self._quants(c)
                    if any(q.reserved_quantity for q in quants):
                        raise UserError('%s sigue con prendas reservadas que no son de ninguna OUT abierta. '
                                        'No se ha cambiado nada: avisa a IT.' % c.name)
                por_producto = {}
                for q in quants:
                    d = por_producto.setdefault(q.product_id, {'qty': 0.0, 'company': q.company_id})
                    d['qty'] += q.quantity
                total, n = 0.0, 0
                for producto, d in por_producto.items():
                    if float_is_zero(d['qty'], precision_rounding=producto.uom_id.rounding):
                        continue
                    self._ajuste(producto, -d['qty'], c, d['company'], emp, 'cero',
                                 'TUCTUC contenedor %s: poner a cero (%s)' % (c.name, emp.name))
                    total += d['qty']
                    n += 1
                request.env['stock.move'].flush()   # v1.13: todo escrito dentro del savepoint
            msg ='%s: %s a cero (%s uds de %d ref. fuera del stock)' % (emp.name, c.name, _num(total), n)
            if resumen:
                msg += '. A Faltantes: ' + '; '.join(resumen)
            return {'ok': True, 'msg': msg, 'contenedor': self._datos_contenedor(c)}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/tuctuc/contenedores/anadir', type='json', auth='user')
    def anadir(self, contenedor_id=False, employee_id=False, lineas=None, tanda=False, **kw):
        """Añade al contenedor las prendas leídas (Odoo no las tenía): ajuste de inventario de cada artículo.
        lineas = [{'producto_id': id, 'uds': n}].
        v1.13 (R3): tanda = id que pone la PDA a lo leído. Si se corta la wifi y se reintenta lo mismo, la tanda ya
        está guardada y no se vuelve a añadir (como Devoluciones). Dos peticiones a la vez con la misma tanda: la
        restricción única (tanda, artículo) del registro hace fallar la segunda."""
        try:
            self._comprobar_usuario()
            emp = self._empleado(employee_id)
            c = self._contenedor(contenedor_id)
            tanda = (tanda or '').strip()[:60] if isinstance(tanda, str) else ''
            # v1.16.0: caja marcada «Tiene prendas» en la ronda: solo la resuelven los de tarjetas_con_prendas, y lo
            # leído cubre antes los faltantes pendientes de la caja o de su hueco (Encontrado)
            pendiente = c.name in self._marcas_con_prendas()
            if pendiente and not self._puede_con_prendas(emp):
                raise UserError('%s está marcada «Tiene prendas»: la resuelven %s. No se añade nada.' % (
                    c.name, self._nombres_tarjetas(PARAM_CON_PRENDAS)))
            if tanda:
                # v1.16.0: la tanda de lo encontrado en Faltantes lleva «-F» detrás
                ya = request.env['tuctuc.contenedor.movimiento'].sudo().search(
                    [('tanda', 'in', [tanda, tanda + '-F'])])
                if ya:
                    return {'ok': True, 'repetida': True,
                            'msg': 'Ya estaba guardado: %s uds añadidas a %s (no se añade otra vez)'
                                   % (_num(sum(ya.mapped('uds'))), ya[0].contenedor),
                            'contenedor': self._datos_contenedor(c)}
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
            company = self._compania_de(c)
            textos, ajustadas = [], 0.0
            with request.env.cr.savepoint():    # todo o nada
                for p, uds in por_producto.items():
                    resto = uds
                    if pendiente:               # v1.16.0
                        resto, t = self._encontrar(p, uds, c, emp, tanda)
                        textos += t
                    if not float_is_zero(resto, precision_rounding=p.uom_id.rounding):
                        nombre = 'TUCTUC contenedor %s: %s (%s)' % (
                            c.name, 'caja a 0 con prendas' if pendiente else 'añadir prendas', emp.name)
                        self._ajuste(p, resto, c, company, emp, 'anadir', nombre, tanda=tanda)
                        ajustadas += resto
                request.env['stock.move'].flush()   # v1.13: la restricción de la tanda salta aquí dentro
            msg = '%s: %d uds añadidas a %s' % (emp.name, sum(por_producto.values()), c.name)
            if pendiente:
                msg += ' (%s por ajuste de inventario)' % _num(ajustadas)
            if textos:
                msg += '. ' + '. '.join(textos)
            return {'ok': True, 'msg': msg, 'contenedor': self._datos_contenedor(c)}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/tuctuc/contenedores/cantidad', type='json', auth='user')
    def cantidad(self, contenedor_id=False, employee_id=False, producto_id=False, uds=None, pasar_faltantes=False,
                 antes=None, **kw):
        """v1.7: uds reales de un artículo en el contenedor (se ha contado y no cuadra). Ajuste de inventario de la
        diferencia (+ entra, - sale), como /cero y /anadir. No se baja de lo reservado para una OUT.
        v1.13 (R2): no se cambia si hay prendas de ese artículo leídas para una OUT sin validar (están en un carro:
        lo contado no las incluye y el ajuste las quitaría otra vez al validar), ni si las uds de Odoo han cambiado
        desde que se abrió el contenedor (antes = las que enseñaba la PDA)."""
        try:
            self._comprobar_usuario()
            emp = self._empleado(employee_id)
            c = self._contenedor(contenedor_id)
            self._exigir_revisar(c, emp)        # v1.16.0
            p = request.env['product.product'].sudo().browse(int(producto_id or 0)).exists()
            if not p:
                raise UserError('Artículo no válido. Vuelve a abrir el contenedor.')
            try:
                nuevas = int(uds)
            except (TypeError, ValueError):
                raise UserError('Escribe las uds que hay (un número).')
            if nuevas < 0:
                raise UserError('Las uds no pueden ser negativas.')
            quants = self._quants(c).filtered(lambda q: q.product_id == p)
            if quants.filtered(lambda q: q.lot_id or q.package_id or q.owner_id):
                raise UserError('%s tiene prendas con lote, paquete o propietario: hazlo desde Odoo o avisa a IT.'
                                % c.name)
            actual = sum(quants.mapped('quantity'))
            reservadas = sum(quants.mapped('reserved_quantity'))
            # v1.13 (R2): lo leído sin validar ya no está en el contenedor y Odoo aún lo cuenta. Restarlo daría por
            # hecho que se contó después de leerlo; si el preparador lee mientras se cuenta, saldría stock de más.
            # Lo seguro es no cambiar nada y contar cuando se valide.
            leidas = self._leidas(c, p)
            if leidas:
                raise UserError('No se cambia nada: %s uds de %s ya están leídas para %s y sin validar (están en un '
                                'carro). Vuelve a contar cuando se valide.' % (
                                    _num(sum(leidas.mapped('qty_done'))), p.display_name,
                                    ', '.join(leidas.mapped('picking_id.name')) or 'una OUT'))
            if antes is not None:
                try:
                    antes = float(antes)
                except (TypeError, ValueError):
                    antes = None
            if antes is not None and float_compare(antes, actual, precision_rounding=p.uom_id.rounding) != 0:
                raise UserError('No se cambia nada: %s tenía %s uds de %s al abrirlo y ahora tiene %s (se ha movido '
                                'stock mientras contabas). Vuelve a abrir el contenedor y cuenta otra vez.' % (
                                    c.name, _num(antes), p.display_name, _num(actual)))
            if nuevas < reservadas and not pasar_faltantes:
                pedidos = self._pedidos_reservados(c, p)
                raise UserError('No se baja a %d: %s uds de %s están reservadas para %s.' % (
                    nuevas, _num(reservadas), p.display_name, ', '.join(pedidos) or 'un pedido'))
            company = quants[:1].company_id or self._compania_de(c)
            resumen = []
            with request.env.cr.savepoint():    # todo o nada (también lo de Faltantes)
                if nuevas < reservadas:
                    # v1.12.0: lo reservado que no está pasa por Faltantes (como «Poner a cero», v1.11.0)
                    resumen, _f = self._reservas_a_faltantes(c, emp, producto=p, dejar=nuevas, que='cambiar')
                    quants = self._quants(c).filtered(lambda q: q.product_id == p)
                    if sum(quants.mapped('reserved_quantity')) > nuevas:
                        raise UserError('%s sigue con más de %d uds reservadas que no son de ninguna OUT abierta. '
                                        'No se ha cambiado nada: avisa a IT.' % (p.display_name, nuevas))
                antes = sum(quants.mapped('quantity'))
                diferencia = nuevas - antes
                if not resumen and float_is_zero(diferencia, precision_rounding=p.uom_id.rounding):
                    raise UserError('%s ya tiene %d uds de %s: no se cambia nada.' % (c.name, nuevas, p.display_name))
                if abs(diferencia) > MAX_ANADIR:
                    raise UserError('Cambio de más de %d uds: revisa la cantidad.' % MAX_ANADIR)
                if not float_is_zero(diferencia, precision_rounding=p.uom_id.rounding):
                    self._ajuste(p, diferencia, c, company, emp, 'cantidad',
                                 'TUCTUC contenedor %s: cambiar cantidad (%s)' % (c.name, emp.name))
                request.env['stock.move'].flush()   # v1.13: todo escrito dentro del savepoint
            msg = '%s: %s en %s pasa de %s a %d uds' % (emp.name, p.display_name, c.name, _num(actual), nuevas)
            if resumen:
                msg += '. A Faltantes: ' + '; '.join(resumen)
            return {'ok': True, 'msg': msg, 'contenedor': self._datos_contenedor(c)}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    def _esperando(self, producto, limite=5):
        """v1.14: OUT abiertas de la compañía con el artículo sin reservar del todo (para avisar al entrar stock)."""
        moves = request.env['stock.move'].sudo().search([
            ('product_id', '=', producto.id), ('state', 'in', ('confirmed', 'partially_available')),
            ('picking_id.picking_type_id.code', '=', 'outgoing'), ('company_id', 'in', _cias())],
            order='id', limit=50)
        pickings = moves.mapped('picking_id')
        nombres = ['%s%s' % (p.name, ' (%s)' % p.origin if p.origin else '') for p in pickings[:limite]]
        return nombres, max(0, len(pickings) - limite)

    @http.route('/tuctuc/contenedores/cambiar_articulo', type='json', auth='user')
    def cambiar_articulo(self, contenedor_id=False, employee_id=False, producto_id=False, producto_real_id=False,
                         uds=None, antes=None, tanda=False, pasar_faltantes=False, otro_modelo=False, **kw):
        """v1.14 (R23), «Es otro»: `uds` de lo que Odoo llama A (producto_id) en el contenedor son en realidad B
        (producto_real_id), un error de talla. En un savepoint: lo reservado de A que ya no cabe pasa por Faltantes
        (como «Cambiar»: otro hueco o la OUT sale sin ello), ajuste de -uds de A y de +uds de B contra pérdidas, y una
        sola línea «Cambiar artículo» en el registro con los dos movimientos. B entra libre (no se reserva nada).
        Las mismas protecciones que «Cambiar» (R2): nada si hay prendas de A o de B leídas sin validar en el
        contenedor ni si las uds de A han cambiado desde que se abrió (antes). tanda: un reintento no se repite.
        pasar_faltantes y otro_modelo: la PDA ya lo ha avisado y el operario ha vuelto a pulsar «Guardar»."""
        try:
            self._comprobar_usuario()
            emp = self._empleado(employee_id)
            c = self._contenedor(contenedor_id)
            self._exigir_revisar(c, emp)        # v1.16.0
            Product = request.env['product.product'].sudo()
            a = Product.browse(int(producto_id or 0)).exists()
            b = Product.browse(int(producto_real_id or 0)).exists()
            if not a or not b:
                raise UserError('Artículo no válido. Vuelve a abrir el contenedor.')
            if a == b:
                raise UserError('Es el mismo artículo. Si faltan o sobran uds, usa «Cambiar».')
            Mov = request.env['tuctuc.contenedor.movimiento'].sudo()
            tanda = (tanda or '').strip()[:64] if isinstance(tanda, str) else ''
            if tanda:
                ya = Mov.search([('tanda', '=', tanda)], limit=1)
                if ya:
                    return {'ok': True, 'repetida': True,
                            'msg': 'Ya estaba guardado: %s uds de %s son %s en %s (no se hace otra vez)' % (
                                _num(ya.uds), ya.producto_id.display_name, ya.producto_nuevo_id.display_name,
                                ya.contenedor),
                            'contenedor': self._datos_contenedor(c)}
            if not logica.mismo_modelo(a.product_tmpl_id.id, b.product_tmpl_id.id) and not otro_modelo:
                raise UserError('%s no es el mismo modelo que %s: confírmalo en la PDA.' % (
                    b.display_name, a.display_name))
            if 'tracking' in a._fields and (a.tracking != 'none' or b.tracking != 'none'):
                raise UserError('Artículo con lote o número de serie: hazlo desde Odoo o avisa a IT.')
            try:
                n = int(uds)
            except (TypeError, ValueError):
                raise UserError('Escribe cuántas uds son del otro artículo (un número).')
            quants = self._quants(c).filtered(lambda q: q.product_id == a)
            if quants.filtered(lambda q: q.lot_id or q.package_id or q.owner_id):
                raise UserError('%s tiene prendas con lote, paquete o propietario: hazlo desde Odoo o avisa a IT.'
                                % c.name)
            actual = sum(quants.mapped('quantity'))
            reservadas = sum(quants.mapped('reserved_quantity'))
            error = logica.error_uds_cambio(n, actual, MAX_ANADIR)
            if error:
                raise UserError(error)
            leidas = self._leidas(c, a) | self._leidas(c, b)
            if leidas:
                raise UserError('No se cambia nada: hay prendas de %s leídas para %s y sin validar (están en un '
                                'carro). Vuelve a probar cuando se valide.' % (
                                    ', '.join(leidas.mapped('product_id.display_name')),
                                    ', '.join(leidas.mapped('picking_id.name')) or 'una OUT'))
            if antes is not None:
                try:
                    antes = float(antes)
                except (TypeError, ValueError):
                    antes = None
            if antes is not None and float_compare(antes, actual, precision_rounding=a.uom_id.rounding) != 0:
                raise UserError('No se cambia nada: %s tenía %s uds de %s al abrirlo y ahora tiene %s (se ha movido '
                                'stock mientras tanto). Vuelve a abrir el contenedor.' % (
                                    c.name, _num(antes), a.display_name, _num(actual)))
            a_faltantes = logica.reservas_a_faltantes(n, actual, reservadas)
            if a_faltantes > 0 and not pasar_faltantes:
                raise UserError('%s uds de %s están reservadas para %s y no quedarían: confírmalo en la PDA.' % (
                    _num(a_faltantes), a.display_name, ', '.join(self._pedidos_reservados(c, a)) or 'un pedido'))
            company = quants[:1].company_id or self._compania_de(c)
            nombre = 'TUCTUC contenedor %s: %s es %s (%s)' % (c.name, a.display_name, b.display_name, emp.name)
            resumen = []
            with request.env.cr.savepoint():    # todo o nada (también lo de Faltantes)
                if a_faltantes > 0:
                    resumen, _f = self._reservas_a_faltantes(c, emp, producto=a, dejar=actual - n,
                                                             que='es otro artículo')
                    quants = self._quants(c).filtered(lambda q: q.product_id == a)
                    if float_compare(sum(quants.mapped('reserved_quantity')), actual - n,
                                     precision_rounding=a.uom_id.rounding) > 0:
                        raise UserError('%s sigue con más de %s uds reservadas que no son de ninguna OUT abierta. '
                                        'No se ha cambiado nada: avisa a IT.' % (a.display_name, _num(actual - n)))
                move_a = self._mover_ajuste(a, -n, c, company, nombre)
                move_b = self._mover_ajuste(b, n, c, company, nombre)
                Mov.create({
                    'accion': 'cambiar_articulo', 'contenedor': c.name, 'origen_id': c.location_id.id,
                    'origen': c.location_id.complete_name, 'destino': c.location_id.complete_name,
                    'uds': n, 'lineas': 1, 'producto_id': a.id, 'producto_nuevo_id': b.id,
                    'move_id': move_a.id, 'move_nuevo_id': move_b.id, 'employee_id': emp.id, 'tanda': tanda or False,
                })
                request.env['stock.move'].flush()   # la restricción de la tanda salta aquí dentro
            msg = '%s: en %s, %d uds de %s son %s (%s pasa de %s a %s uds)' % (
                emp.name, c.name, n, a.display_name, b.display_name, a.display_name, _num(actual), _num(actual - n))
            if resumen:
                msg += '. A Faltantes: ' + '; '.join(resumen)
            esperando, mas = self._esperando(b)
            if esperando:
                msg += '. OUT esperando %s: %s%s (ya hay stock aquí; no se ha reservado nada)' % (
                    b.display_name, ', '.join(esperando), ' y %d más' % mas if mas else '')
            return {'ok': True, 'msg': msg, 'contenedor': self._datos_contenedor(c)}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    def _por_trozo(self, texto):
        """v1.7: contenedores KO_/TT_ activos cuyo nombre contiene el texto (etiqueta rota, escrito a mano).
        Devuelve (encontrados hasta MAX_BUSCAR, hay más)."""
        texto = (texto or '').strip()
        if len(texto) < MIN_BUSCAR:
            return request.env['stock.location'].sudo(), False
        dominio = [('usage', '=', 'internal'), _de_la_compania(), ('name', '=ilike', '%' + _literal(texto) + '%')]
        dominio += _dominio_prefijos()
        locs = request.env['stock.location'].sudo().search(dominio, order='name', limit=MAX_BUSCAR + 1)
        return locs[:MAX_BUSCAR], len(locs) > MAX_BUSCAR

    def _sugerir(self, texto):
        """v1.8: todo lo que tiene código y contiene el texto: lineal, contenedores, huecos y artículos (solo lectura).
        Devuelve (items, hay más, contenedores encontrados)."""
        texto = (texto or '').strip()
        items, mas = [], False
        Loc = request.env['stock.location'].sudo()
        m = LINEAL_DELANTE_RE.match(texto)
        lineal = _lineal(texto) or (m and _lineal(m.group(1)))   # v1.8.2: MU y «MU-00 P» también ofrecen el lineal
        if lineal:
            items.append({'tipo': 'lineal', 'id': 0, 'codigo': lineal, 'nombre': 'Lineal ' + lineal,
                          'detalle': 'Inventario del lineal'})
        conts, mas_c = self._por_trozo(texto)
        conts = conts[:MAX_TIPO]
        mas = mas or mas_c
        items += [{'tipo': 'contenedor', 'id': l.id, 'nombre': l.name, 'detalle': l.location_id.complete_name or ''}
                  for l in conts]
        if len(texto) >= MIN_BUSCAR_OTROS:
            lit = '%' + _literal(texto) + '%'
            huecos = Loc.search([('usage', '=', 'internal'), _de_la_compania(), '|', ('barcode', '=ilike', lit),
                                 ('name', '=ilike', lit)],
                                order='name', limit=MAX_TIPO * 3)
            huecos = huecos.filtered(lambda l: not _es_contenedor_nombre(l.name))
            mas = mas or len(huecos) > MAX_TIPO
            items += [{'tipo': 'hueco', 'id': l.id, 'nombre': l.barcode or l.name, 'detalle': l.complete_name}
                      for l in huecos[:MAX_TIPO]]
            pre = _literal(texto) + '%'
            # un hueco (L94 P35), un lineal o un contenedor no es un artículo: no se busca (la búsqueda de artículos
            # tarda ~1 s, la de huecos ~0,2 s)
            sin_articulos = bool(re.match(r'^(L\d|MU-)', texto, re.I)) or _es_contenedor_nombre(texto)
            Product = request.env['product.product'].sudo()
            prods = Product.browse() if sin_articulos else Product.search([
                _de_la_compania(), '|', '|',
                ('name', '=ilike', pre), ('default_code', '=ilike', pre), ('barcode', '=ilike', pre)],
                order='name', limit=MAX_TIPO + 1)
            mas = mas or len(prods) > MAX_TIPO
            prods = prods[:MAX_TIPO]
            stock = {}
            if prods:
                for g in request.env['stock.quant'].sudo().read_group(
                        [('product_id', 'in', prods.ids), ('location_id.usage', '=', 'internal'),
                         ('company_id', 'in', _cias())], ['quantity'], ['product_id']):
                    stock[g['product_id'][0]] = g['quantity']
            items += [{'tipo': 'articulo', 'id': p.id, 'nombre': p.display_name,
                       'detalle': '%s uds en almacén' % _num(stock.get(p.id, 0))} for p in prods]
        return items, mas, conts

    @http.route('/tuctuc/contenedores/buscar', type='json', auth='user')
    def buscar(self, texto='', **kw):
        """v1.7: sugerencias mientras se escribe (solo lectura). v1.8: de todo lo que tiene código."""
        try:
            self._comprobar_usuario()
            items, mas, _c = self._sugerir(texto)
            return {'ok': True, 'items': items, 'mas': mas}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/tuctuc/contenedores/donde', type='json', auth='user')
    def donde(self, producto_id=False, **kw):
        """v1.8: dónde está un artículo elegido de la lista (solo lectura)."""
        try:
            self._comprobar_usuario()
            p = request.env['product.product'].sudo().browse(int(producto_id or 0)).exists()
            if not p:
                raise UserError('Artículo no válido.')
            return {'ok': True, 'tipo': 'articulo', 'articulo': self._donde(p)}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    def _por_trozo_leer(self, codigo):
        """v1.7: /leer sin coincidencia exacta: un contenedor = se abre; varios = lista para elegir. v1.8: también
        huecos, lineales y artículos; un solo artículo se abre (dónde está). Un hueco nunca se abre solo: con
        contenedores en la lista de mover sería el destino, así que se elige tocándolo."""
        items, mas, conts = self._sugerir(codigo)
        # «290726_44» también encuentra KO_290726_440…449: si existe KO_290726_44 (nombre entero), es ese
        exacto = conts.filtered(lambda l: l.name.upper()[3:] == codigo.strip().upper())
        if len(exacto) == 1:
            return {'ok': True, 'tipo': 'contenedor', 'contenedor': self._datos_contenedor(exacto)}
        if len(items) == 1 and items[0]['tipo'] == 'contenedor':
            return {'ok': True, 'tipo': 'contenedor', 'contenedor': self._datos_contenedor(conts)}
        if len(items) == 1 and items[0]['tipo'] == 'articulo':
            p = request.env['product.product'].sudo().browse(items[0]['id'])
            return {'ok': True, 'tipo': 'articulo', 'articulo': self._donde(p)}
        if items:
            return {'ok': True, 'tipo': 'candidatos', 'texto': codigo, 'items': items, 'mas': mas}
        return None

    def _validar_destino(self, destino):
        if destino.usage != 'internal':
            raise UserError('%s no es una ubicación interna.' % destino.complete_name)
        if _es_contenedor_nombre(destino.name):
            raise UserError('%s es otro contenedor: escanea la ubicación (hueco) de destino.' % destino.name)

    @http.route('/tuctuc/contenedores/leer', type='json', auth='user')
    def leer(self, codigo='', **kw):
        """Un código leído: tarjeta, lineal, contenedor (KO_/TT_), ubicación (código de barras del hueco) o, v1.6,
        prenda (EAN o referencia: dónde hay stock)."""
        try:
            self._comprobar_usuario()
            codigo = (codigo or '').strip()
            if not codigo:
                raise UserError('Código vacío.')
            Loc = request.env['stock.location'].sudo()
            if _lineal(codigo):
                return {'ok': True, 'tipo': 'lineal', 'lineal': self._datos_lineal(_lineal(codigo))}
            if not _es_contenedor_nombre(codigo):
                emp =request.env['hr.employee'].sudo().search([('barcode', '=', codigo)], limit=1)
                if emp:
                    return {'ok': True, 'tipo': 'persona', 'persona': {'id': emp.id, 'nombre': emp.name}}
            if _es_contenedor_nombre(codigo):
                loc = Loc.search([('usage', '=', 'internal'), _de_la_compania(), '|',
                                  ('name', '=ilike', _literal(codigo)), ('barcode', '=ilike', _literal(codigo))])
                loc = loc.filtered(lambda l: _es_contenedor_nombre(l.name))
                if not loc:
                    r = self._por_trozo_leer(codigo)    # v1.7: KO_290726_44 escrito a medias
                    if r:
                        return r
                    raise UserError('No encuentro el contenedor %s (o está archivado).' % codigo)
                if len(loc) > 1:
                    raise UserError('Hay %d contenedores llamados %s. Avisa a IT.' % (len(loc), codigo))
                return {'ok': True, 'tipo': 'contenedor', 'contenedor': self._datos_contenedor(loc)}
            loc = Loc.search([('barcode', '=', codigo), _de_la_compania()])
            if not loc:
                producto = self._buscar_producto(codigo)   # v1.6: una prenda: dónde hay stock de ella
                if producto:
                    return {'ok': True, 'tipo': 'articulo', 'articulo': self._donde(producto)}
                r = self._por_trozo_leer(codigo)        # v1.7: trozo del nombre de un contenedor (290726_44)
                if r:
                    return r
                raise UserError('No encuentro nada con «%s»: ni tarjeta, contenedor, ubicación, lineal ni artículo.'
                                % codigo)
            if len(loc) > 1:
                # TUCTUC: el mismo código de barras en varias compañías = el mismo hueco (gemelos): se enseña junto,
                # con el de la primera compañía de la PDA delante
                if _es_contenedor_nombre(loc[0].name):
                    raise UserError('Hay %d ubicaciones con el código %s. Avisa a IT.' % (len(loc), codigo))
                orden = _cias()
                loc = loc.sorted(lambda l: (orden.index(l.company_id.id) if l.company_id.id in orden else 99, l.id))[:1]
            self._validar_destino(loc)
            return {'ok': True, 'tipo': 'ubicacion', 'ubicacion': self._datos_hueco(loc)}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/tuctuc/contenedores/mover', type='json', auth='user')
    def mover(self, contenedor_ids=None, destino_id=False, employee_id=False, **kw):
        try:
            self._comprobar_usuario()
            emp = self._empleado(employee_id)   # v1.16.0: tarjeta válida (activo y de la compañía), como el resto
            Loc = request.env['stock.location'].sudo()
            Quant = request.env['stock.quant'].sudo()
            Mov = request.env['tuctuc.contenedor.movimiento'].sudo()
            destino = Loc.browse(int(destino_id or 0)).exists()
            if not destino:
                raise UserError('Escanea la ubicación de destino.')
            self._validar_destino(destino)
            conts = Loc.browse([int(i) for i in (contenedor_ids or [])]).exists()
            if not conts:
                raise UserError('Escanea antes un contenedor.')
            movidos, iguales = [], []
            pares = []
            for c in conts:
                if not _es_contenedor_nombre(c.name) or c.usage != 'internal' or not c.active:
                    raise UserError('%s ya no es un contenedor válido.' % c.name)
                # TUCTUC: al hueco de la compañía del contenedor (nunca se mueve stock entre compañías)
                dest = self._gemelo(destino, self._compania_de(c), cerca=c.location_id)
                if not dest:
                    raise UserError('%s no existe en el almacén de %s (%s, %s): no se mueve nada.' % (
                        destino.barcode or destino.name, c.name, c.location_id.get_warehouse().code or '?',
                        self._compania_de(c).name or '?'))
                if dest.id == c.id or (dest.parent_path or '').startswith(c.parent_path or '#'):
                    raise UserError('No se puede mover %s dentro de sí mismo.' % c.name)
                pares.append((c, dest))
            for c, dest in pares:
                if c.location_id.id == dest.id:
                    iguales.append(c.name)
                    continue
                quants = Quant.search([('location_id', '=', c.id), ('quantity', '!=', 0)])
                origen = c.location_id
                c.write({'location_id': dest.id})
                Mov.create({
                    'contenedor': c.name, 'origen_id': origen.id, 'destino_id': dest.id,
                    'origen': origen.complete_name, 'destino': dest.complete_name,
                    'uds': sum(quants.mapped('quantity')), 'reservadas': sum(quants.mapped('reserved_quantity')),
                    'lineas': len(quants), 'employee_id': emp.id,
                })
                movidos.append(c.name)
            if not movidos:
                raise UserError('%s ya estaba en %s.' % (', '.join(iguales), destino.complete_name))
            msg = 'Se han movido %d contenedor%s. %s: %s → %s' % (
                len(movidos), '' if len(movidos) == 1 else 'es', emp.name, ', '.join(movidos), destino.complete_name)
            if iguales:
                msg += ' (%s ya estaba allí)' % ', '.join(iguales)
            return {'ok': True, 'msg': msg}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    # ================================================================== v1.16.0: retirar cajas a 0 (ronda)
    # Diseño v2 aprobado por Isaac el 26/11 (bin/versiones/diseno-compactacion-odoo-retirar-vacias-juntar-cajas_
    # 2026-11-26_v2.md, parte 1). La lista se calcula en vivo (SQL de solo lectura) y no se guarda: el rastro queda en
    # tuctuc.contenedor.movimiento. Una caja «a 0» es un KO_/TT_ activo de un hueco del rango de lineales, sin quants
    # con cantidad ni reserva y sin líneas de movimiento abiertas. Las negativas y las de reserva descuadrada son
    # «revisar» (solo las tarjetas de tarjetas_revisar o los usuarios del grupo «Contenedores: revisar»).
    def _param(self, clave):
        return request.env['ir.config_parameter'].sudo().get_param(clave) or ''

    def _nombres_tarjetas(self, clave):
        ids = logica.ids_tarjetas(self._param(clave))
        emps = request.env['hr.employee'].sudo().browse(list(ids)).exists()
        return ', '.join(emps.mapped('name')) or '(nadie: falta poner el parámetro %s)' % clave

    def _puede_revisar(self, emp):
        return request.env.user.has_group(GRUPO_REVISAR) or bool(
            emp and emp.id in logica.ids_tarjetas(self._param(PARAM_REVISAR)))

    def _puede_con_prendas(self, emp):
        return bool(emp and emp.id in logica.ids_tarjetas(self._param(PARAM_CON_PRENDAS)))

    def _exigir_revisar(self, c, emp):
        """Las cajas con stock negativo o con más reservado que cantidad solo las tocan los de «Revisar»."""
        raras = self._quants(c).filtered(lambda q: q.quantity < 0 or (q.reserved_quantity > 0 and
                                                                     q.reserved_quantity > q.quantity))
        if raras and not self._puede_revisar(emp):
            raise UserError('%s tiene stock negativo o reservas descuadradas: la revisan %s. No se cambia nada.'
                            % (c.name, self._nombres_tarjetas(PARAM_REVISAR)))

    def _marcas_con_prendas(self):
        """Nombres de las cajas marcadas «Tiene prendas» sin nada hecho después con su stock."""
        cr = request.env.cr
        cr.execute("""
            SELECT contenedor,
                   MAX(id) FILTER (WHERE accion = 'con_prendas'),
                   MAX(id) FILTER (WHERE accion NOT IN ('con_prendas', 'mover'))
              FROM tuctuc_contenedor_movimiento
             WHERE contenedor IN (SELECT contenedor FROM tuctuc_contenedor_movimiento WHERE accion = 'con_prendas')
             GROUP BY contenedor""")
        return {n for n, marca, cambio in cr.fetchall() if logica.con_prendas_pendiente(marca, cambio)}

    def _cajas(self, extra='', args=()):
        """Cajas KO_/TT_ activas de la compañía en huecos del rango de lineales, con su estado para la ronda
        (logica.clasificar). extra: condición SQL más sobre h (hueco) o c (caja), con sus args."""
        cr = request.env.cr
        cr.execute("""
            SELECT c.id, c.name, h.id, h.name, h.complete_name,
                   COUNT(q.id) FILTER (WHERE q.quantity <> 0 OR q.reserved_quantity <> 0),
                   COUNT(q.id) FILTER (WHERE q.quantity < 0),
                   COUNT(q.id) FILTER (WHERE q.reserved_quantity > 0 AND q.reserved_quantity > q.quantity),
                   COALESCE(SUM(q.quantity), 0)
              FROM stock_location c
              JOIN stock_location h ON h.id = c.location_id
              LEFT JOIN stock_quant q ON q.location_id = c.id
             WHERE c.active AND c.usage = 'internal' AND (c.company_id = ANY(%s) OR c.company_id IS NULL)
               AND upper(left(c.name, 3)) = ANY(%s) """ + extra + """
             GROUP BY c.id, h.id""", (_cias(), _prefijos()) + tuple(args))
        filas = cr.fetchall()
        # líneas abiertas (IN, INT u OUT sin hacer) que salen de una caja o van a ella: esa caja no se retira. Con
        # pocas cajas (un hueco, un lineal) solo las suyas; con toda la nave, todas las abiertas de una vez
        ids = tuple(f[0] for f in filas)
        if not ids:
            return []
        if len(ids) <= 3000:
            cr.execute("""SELECT location_id, location_dest_id FROM stock_move_line
                           WHERE state NOT IN ('done', 'cancel') AND (location_id IN %s OR location_dest_id IN %s)""",
                       (ids, ids))
        else:
            cr.execute("""SELECT location_id, location_dest_id FROM stock_move_line
                           WHERE state NOT IN ('done', 'cancel')""")
        abiertas = set()
        for a, b in cr.fetchall():
            abiertas.add(a)
            abiertas.add(b)
        marcas = self._marcas_con_prendas()
        lo, hi = logica.rango_lineales(self._param(PARAM_LINEALES))
        res = []
        for cid, cnombre, hid, hnombre, hcompleto, activos, neg, desc, uds in filas:
            lineal = logica.lineal_de(hnombre)
            if lineal is None or not lo <= lineal <= hi or _es_contenedor_nombre(hnombre):
                continue
            estado = logica.clasificar(activos, neg, desc, cid in abiertas)
            res.append({'id': cid, 'nombre': cnombre, 'hueco_id': hid, 'hueco': hcompleto or hnombre,
                        'hueco_nombre': hnombre, 'lineal': lineal, 'estado': estado, 'uds': uds,
                        'con_prendas': estado == 'cero' and cnombre in marcas})
        return res

    def _directo(self, hueco_ids):
        """Huecos con prendas sueltas (fuera de cajas): no quedan libres aunque se retiren sus cajas."""
        if not hueco_ids:
            return set()
        request.env.cr.execute("""SELECT DISTINCT location_id FROM stock_quant
                                   WHERE location_id IN %s AND quantity <> 0""", (tuple(hueco_ids),))
        return {f[0] for f in request.env.cr.fetchall()}

    @staticmethod
    def _por_hueco(cajas):
        por = {}
        for c in cajas:
            por.setdefault(c['hueco_id'], []).append(c)
        return por

    @staticmethod
    def _libre_si_retira(lista, directo):
        """El hueco queda libre al retirar sus cajas a 0: todas a 0 (sin «con prendas») y nada suelto."""
        return not directo and all(c['estado'] == 'cero' and not c['con_prendas'] for c in lista)

    def _datos_ronda_hueco(self, hueco, emp):
        gemelos = self._gemelos(hueco)      # TUCTUC: el mismo hueco en todas las compañías
        cajas = sorted(self._cajas('AND h.id IN %s', (tuple(gemelos.ids),)), key=lambda c: c['nombre'])
        directo = bool(self._directo(gemelos.ids))

        def grupo(estado):
            return [{'id': c['id'], 'nombre': c['nombre'], 'uds': c['uds'], 'con_prendas': c['con_prendas']}
                    for c in cajas if c['estado'] == estado]
        return {'id': hueco.id, 'nombre': hueco.complete_name, 'cero': grupo('cero'), 'stock': grupo('stock'),
                'revisar': grupo('revisar'), 'abierta': grupo('abierta'), 'directo': directo,
                'libre': not cajas and not directo,
                'puede_revisar': self._puede_revisar(emp), 'puede_con_prendas': self._puede_con_prendas(emp),
                'revisan': self._nombres_tarjetas(PARAM_REVISAR)}

    @http.route('/tuctuc/contenedores/ronda/resumen', type='json', auth='user')
    def ronda_resumen(self, employee_id=False, **kw):
        """Resumen por lineal: huecos con cajas a 0, cajas, huecos que quedan libres al retirarlas y pendientes."""
        try:
            self._comprobar_usuario()
            emp = self._empleado(employee_id)
            por_hueco = self._por_hueco(self._cajas())
            directo = self._directo(list(por_hueco))
            lineales = {}
            for hid, lista in por_hueco.items():
                l = lineales.setdefault(lista[0]['lineal'], {'lineal': lista[0]['lineal'], 'huecos': 0, 'cajas': 0,
                                                             'libres': 0, 'con_prendas': 0, 'revisar': 0})
                ceros = [c for c in lista if c['estado'] == 'cero' and not c['con_prendas']]
                l['cajas'] += len(ceros)
                l['con_prendas'] += len([c for c in lista if c['con_prendas']])
                l['revisar'] += len([c for c in lista if c['estado'] == 'revisar'])
                if ceros:
                    l['huecos'] += 1
                    if self._libre_si_retira(lista, hid in directo):
                        l['libres'] += 1
            filas = [l for l in sorted(lineales.values(), key=lambda x: x['lineal'])
                     if l['cajas'] or l['con_prendas'] or l['revisar']]
            lo, hi = logica.rango_lineales(self._param(PARAM_LINEALES))
            return {'ok': True, 'rango': 'L%d–L%d' % (lo, hi), 'lineales': filas,
                    'cajas': sum(l['cajas'] for l in filas), 'huecos': sum(l['huecos'] for l in filas),
                    'libres': sum(l['libres'] for l in filas),
                    'con_prendas': sum(l['con_prendas'] for l in filas),
                    'revisar': sum(l['revisar'] for l in filas),
                    'puede_revisar': self._puede_revisar(emp), 'puede_con_prendas': self._puede_con_prendas(emp)}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/tuctuc/contenedores/ronda/lineal', type='json', auth='user')
    def ronda_lineal(self, lineal=0, employee_id=False, **kw):
        """Huecos de un lineal con cajas a 0 (o pendientes), en orden de pasillo."""
        try:
            self._comprobar_usuario()
            self._empleado(employee_id)
            try:
                n = int(lineal or 0)
            except (TypeError, ValueError):
                raise UserError('Lineal no válido.')
            cajas = [c for c in self._cajas(_SQL_LINEAL, _patrones_lineal(n)) if c['lineal'] == n]
            por_hueco = self._por_hueco(cajas)
            directo = self._directo(list(por_hueco))
            huecos = []
            for hid, lista in por_hueco.items():
                ceros = [c for c in lista if c['estado'] == 'cero' and not c['con_prendas']]
                prendas = [c for c in lista if c['con_prendas']]
                revisar = [c for c in lista if c['estado'] == 'revisar']
                if not (ceros or prendas or revisar):
                    continue
                huecos.append({'id': hid, 'nombre': lista[0]['hueco_nombre'], 'cero': len(ceros),
                               'con_prendas': len(prendas), 'revisar': len(revisar),
                               'stock': len([c for c in lista if c['estado'] == 'stock']),
                               'libre': bool(ceros) and self._libre_si_retira(lista, hid in directo)})
            huecos.sort(key=lambda h: logica.orden_hueco(h['nombre']))
            return {'ok': True, 'lineal': n, 'codigo': clave, 'huecos': huecos}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/tuctuc/contenedores/ronda/hueco', type='json', auth='user')
    def ronda_hueco(self, ubicacion_id=False, employee_id=False, **kw):
        """Cajas de un hueco por estado: a 0 (retirar), con prendas (no tocar), revisar y con movimientos abiertos."""
        try:
            self._comprobar_usuario()
            emp = self._empleado(employee_id)
            hueco = request.env['stock.location'].sudo().browse(int(ubicacion_id or 0)).exists()
            if not hueco:
                raise UserError('No encuentro la ubicación.')
            self._validar_destino(hueco)
            return {'ok': True, 'hueco': self._datos_ronda_hueco(hueco, emp)}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/tuctuc/contenedores/ronda/retirar', type='json', auth='user')
    def ronda_retirar(self, ubicacion_id=False, contenedor_ids=None, employee_id=False, motivo='vacia',
                      confirmado=False, **kw):
        """Archiva cajas a 0 del hueco: «vacia» (leídas y vacías) o «no_esta» (en Odoo y no en el palé). Se mira en
        vivo que cada una sigue a 0, sin marca «con prendas» y en ese hueco; si alguna no, no se archiva ninguna."""
        try:
            self._comprobar_usuario()
            if not confirmado:
                raise UserError('Confirma antes en la PDA.')
            emp = self._empleado(employee_id)
            hueco = request.env['stock.location'].sudo().browse(int(ubicacion_id or 0)).exists()
            if not hueco:
                raise UserError('Lee el hueco.')
            ids = {int(i) for i in (contenedor_ids or [])}
            if not ids:
                raise UserError('No hay cajas que retirar.')
            vivas = {c['id']: c for c in self._cajas('AND h.id IN %s', (tuple(self._gemelos(hueco).ids),))}
            por_que = {'stock': 'tiene prendas en Odoo', 'revisar': 'stock negativo o descuadrado',
                       'abierta': 'tiene un movimiento sin validar'}
            malas = []
            for i in sorted(ids):
                c = vivas.get(i)
                if not c:
                    malas.append('una caja que ya no está en %s' % hueco.complete_name)
                elif c['estado'] != 'cero' or c['con_prendas']:
                    malas.append('%s (%s)' % (c['nombre'], por_que.get(c['estado'], 'marcada «Tiene prendas»')))
            if malas:
                raise UserError('No se retira nada: %s. Vuelve a leer el hueco.' % '; '.join(malas))
            conts = request.env['stock.location'].sudo().browse(sorted(ids))
            self._antes_de_archivar(conts, emp)
            nota = ('(archivado, no estaba en el hueco)' if motivo == 'no_esta'
                    else '(archivado, vacía, ronda cajas a 0)')
            Mov = request.env['tuctuc.contenedor.movimiento'].sudo()
            for c in conts:
                c.write({'active': False})
                Mov.create({'accion': 'archivar', 'contenedor': c.name, 'origen_id': hueco.id,
                            'origen': hueco.complete_name, 'destino': nota, 'employee_id': emp.id})
            datos = self._datos_ronda_hueco(hueco, emp)
            msg = '%s: %d caja(s) %s en %s. Arranca o tacha su etiqueta' % (
                emp.name, len(conts), 'que no estaban, quitadas de Odoo' if motivo == 'no_esta' else 'retiradas',
                hueco.complete_name)
            if datos['libre']:
                msg += '. %s queda LIBRE' % hueco.complete_name
            return {'ok': True, 'msg': msg, 'hueco': datos}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/tuctuc/contenedores/ronda/con_prendas', type='json', auth='user')
    def ronda_con_prendas(self, contenedor_id=False, employee_id=False, **kw):
        """«Tiene prendas»: la caja está a 0 en Odoo y tiene prendas. No cambia el stock: queda marcada para que la
        resuelvan los de tarjetas_con_prendas (leer sus prendas: primero Faltantes, si no, ajuste +)."""
        try:
            self._comprobar_usuario()
            emp = self._empleado(employee_id)
            c = self._contenedor(contenedor_id)
            if self._quants(c):
                raise UserError('%s ya tiene prendas en Odoo: no hace falta marcarla.' % c.name)
            if c.name in self._marcas_con_prendas():
                raise UserError('%s ya está marcada «Tiene prendas».' % c.name)
            hueco = c.location_id
            request.env['tuctuc.contenedor.movimiento'].sudo().create({
                'accion': 'con_prendas', 'contenedor': c.name, 'origen_id': hueco.id, 'origen': hueco.complete_name,
                'destino': '(a 0 en Odoo con prendas: pendiente)', 'employee_id': emp.id})
            return {'ok': True, 'msg': '%s marcada «Tiene prendas»: se queda en el palé. La resuelven %s.' % (
                c.name, self._nombres_tarjetas(PARAM_CON_PRENDAS)), 'hueco': self._datos_ronda_hueco(hueco, emp)}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/tuctuc/contenedores/ronda/lista', type='json', auth='user')
    def ronda_lista(self, tipo='revisar', employee_id=False, **kw):
        """«Revisar» (stock negativo o descuadrado) o «Cajas con prendas», por lineal y hueco. Solo los de su lista."""
        try:
            self._comprobar_usuario()
            emp = self._empleado(employee_id)
            if tipo == 'revisar':
                if not self._puede_revisar(emp):
                    raise UserError('«Revisar» solo lo hacen %s.' % self._nombres_tarjetas(PARAM_REVISAR))
                cajas = [c for c in self._cajas() if c['estado'] == 'revisar']
            else:
                tipo = 'con_prendas'
                if not self._puede_con_prendas(emp):
                    raise UserError('Las cajas con prendas las resuelven %s.'
                                    % self._nombres_tarjetas(PARAM_CON_PRENDAS))
                cajas = [c for c in self._cajas() if c['con_prendas']]
            cajas.sort(key=lambda c: (logica.orden_hueco(c['hueco_nombre']), c['nombre']))
            mas = max(0, len(cajas) - MAX_HUECOS)
            cajas = cajas[:MAX_HUECOS]
            detalle = {}
            if tipo == 'revisar' and cajas:
                for q in request.env['stock.quant'].sudo().search(
                        [('location_id', 'in', [c['id'] for c in cajas]), '|',
                         ('quantity', '!=', 0), ('reserved_quantity', '!=', 0)]):
                    detalle.setdefault(q.location_id.id, []).append('%s: %s uds%s' % (
                        q.product_id.display_name, _num(q.quantity),
                        ' (res. %s)' % _num(q.reserved_quantity) if q.reserved_quantity else ''))
            items = [{'id': c['id'], 'nombre': c['nombre'], 'hueco_id': c['hueco_id'], 'hueco': c['hueco_nombre'],
                      'detalle': '; '.join(detalle.get(c['id'], []))} for c in cajas]
            return {'ok': True, 'tipo': tipo, 'items': items, 'mas': mas}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    def _encontrar(self, producto, uds, c, emp, tanda):
        """v1.16.0: caja marcada «Tiene prendas»: las prendas leídas de un artículo cubren antes los faltantes
        pendientes de ese artículo con vuelta a la caja o a su hueco («Encontrado»: de FALTANTE a la caja, sin
        ajuste). Un faltante no se parte. Devuelve (uds que sobran = ajuste +, textos para el mensaje)."""
        Faltante = request.env['tuctuc.faltante'].sudo()
        fs = Faltante.search([('estado', '=', 'pendiente'), ('product_id', '=', producto.id),
                              ('ubicacion_vieja_id', 'in', [c.id, c.location_id.id])], order='id')
        fs = fs.filtered(lambda f: not f.en_ronda)
        usados, resto = logica.repartir_encontrados(uds, [(f.id, f.cantidad_faltant) for f in fs])
        hechos = Faltante.browse()
        for f in Faltante.browse(usados):
            try:
                with request.env.cr.savepoint():
                    f.marcar_encontrado(c)
                hechos |= f
            except UserError:
                resto += f.cantidad_faltant      # no se ha podido (FALTANTE sin las uds): va como ajuste +
        textos = []
        if hechos:
            uds_f = sum(hechos.mapped('cantidad_faltant'))
            request.env['tuctuc.contenedor.movimiento'].sudo().create({
                'accion': 'encontrado', 'contenedor': c.name, 'origen_id': c.location_id.id, 'origen': 'FALTANTE',
                'destino': '%s (%s)' % (c.location_id.complete_name, ', '.join(hechos.mapped('name'))),
                'uds': uds_f, 'lineas': len(hechos), 'producto_id': producto.id, 'faltante_id': hechos[0].id,
                'move_id': hechos[0].move_revision_id.id, 'employee_id': emp.id,
                'tanda': (tanda + '-F') if tanda else False})
            textos.append('%s uds de %s eran un faltante (%s): encontradas, sin ajuste' % (
                _num(uds_f), producto.display_name, ', '.join(hechos.mapped('name'))))
        otros = Faltante.search_count([('estado', '=', 'pendiente'), ('product_id', '=', producto.id),
                                       ('id', 'not in', hechos.ids)])
        if otros:
            textos.append('hay %d faltante(s) de %s pendiente(s) de otros huecos: no se tocan (míralo en Faltantes)'
                          % (otros, producto.display_name))
        return max(0.0, resto), textos

    # ================================================================== v1.17.0: «Compactar» (fase 1)
    # Diseño v6 (bin/versiones/diseno-compactacion-odoo-retirar-vacias-juntar-cajas_2026-11-26_v6.md). Plan por
    # lineal, calculado en vivo («Calcular L67»): vaciar las columnas de zona 0 con pocas cajas moviendo KO ENTERAS (se
    # llevan sus prendas y reservas, como /mover) a columnas del mismo lineal o de ±2, sin pasar de 8 cajas ni mezclar
    # colores de un modelo; cada KO lleva su altura (abajo / arriba) en tuctuc.contenedor.banda. No toca reservas ni
    # crea ubicaciones. Las reglas están en logica.plan_lineal (pruebas sin Odoo).
    def _param_int(self, clave, defecto):
        try:
            return int(self._param(clave) or defecto)
        except ValueError:
            return defecto

    def _reglas_compactar(self):
        return {'capacidad': self._param_int(PARAM_CAJAS_COLUMNA, 8), 'vaciar': self._param_int(PARAM_CAJAS_VACIAR, 4),
                'distancia': self._param_int(PARAM_DISTANCIA, 2)}

    def _temporadas(self):
        """Temporadas que entran en Compactar (en mayúsculas). Vacío = todas (TUCTUC: sin zona 0)."""
        return {x.strip().upper() for x in (self._param(PARAM_TEMPORADAS) or '').split(',') if x.strip()}

    def _sql_atributo(self, campo, patron):
        """Subconsulta del valor del atributo de la variante pp: el de la plantilla (campo de style_management, si
        existe la columna) o el primero cuyo nombre case con el patrón (~*). Como tuctuc_faltantes (relativo.py)."""
        cr = request.env.cr
        cr.execute("""SELECT 1 FROM information_schema.columns
                       WHERE table_name = 'product_template' AND column_name = %s""", (campo,))
        de_plantilla = bool(cr.fetchone())
        cond = '(ptav.attribute_id = pt.%s OR pa.name ~* %%s)' % campo if de_plantilla else 'pa.name ~* %s'
        orden = '(ptav.attribute_id = pt.%s) DESC NULLS LAST, ' % campo if de_plantilla else ''
        return ("""(SELECT pav.name FROM product_variant_combination pvc
                      JOIN product_template_attribute_value ptav ON ptav.id = pvc.product_template_attribute_value_id
                      JOIN product_attribute_value pav ON pav.id = ptav.product_attribute_value_id
                      JOIN product_attribute pa ON pa.id = ptav.attribute_id
                     WHERE pvc.product_product_id = pp.id AND """ + cond + """
                     ORDER BY """ + orden + """pa.id LIMIT 1)"""), patron

    def _variantes(self, product_ids):
        """TUCTUC: {product_id: (modelo, mc, talla, plantilla)}. Modelo = nombre de la plantilla; color = atributo
        «Color grouping» o con «color» en el nombre; talla = «Size grouping» o con TALLA/SIZE en el nombre."""
        ids = list(set(product_ids))
        if not ids:
            return {}
        sql_color, p_color = self._sql_atributo('model_color_attribute', 'color')
        sql_talla, p_talla = self._sql_atributo('model_size_attribute', 'talla|size')
        cr = request.env.cr
        cr.execute("""SELECT pp.id, pt.id, upper(trim(pt.name)), """ + sql_color + """, """ + sql_talla + """
                        FROM product_product pp JOIN product_template pt ON pt.id = pp.product_tmpl_id
                       WHERE pp.id = ANY(%s)""", (p_color, p_talla, ids))
        res = {}
        for pid, tid, modelo, color, talla in cr.fetchall():
            modelo = modelo or ''
            res[pid] = (modelo, logica.mc_de(modelo, (color or '').strip()), (talla or '').strip(), tid)
        return res

    # 1.0.2 (28/11, «Compactar» L75 tardaba 24 s): las salidas de 28 días de toda la nave (99.510 líneas, 16.720
    # artículos en tuctuc) se leían en cada cálculo. Ahora:
    #   - por modelo-color (para la clase ABC, cambia poco): de stock_move (date con índice) y guardado 12 h en un
    #     adjunto, compartido por todos los procesos de Odoo; el primer cálculo después de 12 h es el lento;
    #   - por (modelo-color, talla): solo de los artículos de las plantillas del plan (consulta corta, por product_id).
    HORAS_CACHE_28 = 12
    NOMBRE_CACHE_28 = 'tuctuc_contenedores_salidas_28_dias.json'

    def _salidas_28(self, product_ids=None):
        """[(product_id, albaranes de salida hechos en 28 días)] de las compañías de la PDA (de stock_move: un albarán
        cuenta una vez por artículo). Con product_ids, solo esos."""
        desde = fields.Datetime.subtract(fields.Datetime.now(), days=28)
        cr = request.env.cr
        filtro, args = '', [desde, _cias()]
        if product_ids is not None:
            if not product_ids:
                return []
            filtro, args = 'AND m.product_id = ANY(%s)', args + [list(product_ids)]
        cr.execute("""
            SELECT m.product_id, COUNT(DISTINCT m.picking_id)
              FROM stock_move m
              JOIN stock_picking_type t ON t.id = m.picking_type_id
             WHERE m.state = 'done' AND t.code = 'outgoing' AND m.date >= %s AND m.picking_id IS NOT NULL
               AND (t.company_id = ANY(%s) OR t.company_id IS NULL) """ + filtro + """
             GROUP BY m.product_id""", args)
        return cr.fetchall()

    def _lineas_28_mc(self):
        """{modelo-color: albaranes de salida de 28 días}, de un adjunto de menos de HORAS_CACHE_28 o recalculado."""
        Adj = request.env['ir.attachment'].sudo()
        adj = Adj.search([('name', '=', self.NOMBRE_CACHE_28), ('res_model', '=', 'tuctuc.compactacion.paso')],
                         limit=1)
        limite = fields.Datetime.subtract(fields.Datetime.now(), hours=self.HORAS_CACHE_28)
        if adj and adj.write_date and adj.write_date >= limite:
            try:
                return json.loads(base64.b64decode(adj.datas or b'').decode('utf-8') or '{}')
            except ValueError:
                pass
        filas = self._salidas_28()
        var = self._variantes([f[0] for f in filas])
        por_mc = {}
        for pid, n in filas:
            if pid in var:
                mc = var[pid][1]
                por_mc[mc] = por_mc.get(mc, 0) + n
        datos = base64.b64encode(json.dumps(por_mc).encode('utf-8'))
        try:
            with request.env.cr.savepoint():
                if adj:
                    adj.write({'datas': datos})
                else:
                    Adj.create({'name': self.NOMBRE_CACHE_28, 'res_model': 'tuctuc.compactacion.paso', 'res_id': 0,
                                'type': 'binary', 'datas': datos, 'mimetype': 'application/json'})
        except Exception:   # otro proceso lo está guardando a la vez: se usa lo calculado
            _logger.info('TUCTUC Contenedores: no se ha podido guardar la caché de salidas de 28 días', exc_info=True)
        return por_mc

    def _lineas_28_talla(self, plantillas):
        """{(modelo-color, talla): albaranes de salida de 28 días} de los artículos de estas plantillas."""
        if not plantillas:
            return {}
        Prod = request.env['product.product'].sudo().with_context(active_test=False)
        ids = Prod.search([('product_tmpl_id', 'in', list(plantillas))]).ids
        filas = self._salidas_28(ids)
        var = self._variantes([f[0] for f in filas])
        por_talla = {}
        for pid, n in filas:
            if pid in var:
                _modelo, mc, talla, _tid = var[pid]
                por_talla[(mc, talla)] = por_talla.get((mc, talla), 0) + n
        return por_talla

    def _stock_tallas(self, mcs, plantillas):
        """Uds de cada talla de estos modelos-color (de estas plantillas) en las compañías de la PDA, para las bandas."""
        if not mcs or not plantillas:
            return {}
        cr = request.env.cr
        cr.execute("""
            SELECT q.product_id, SUM(q.quantity)
              FROM stock_quant q
              JOIN stock_location l ON l.id = q.location_id
              JOIN product_product pp ON pp.id = q.product_id
             WHERE q.quantity > 0 AND l.usage = 'internal' AND l.company_id = ANY(%s)
               AND pp.product_tmpl_id = ANY(%s)
             GROUP BY q.product_id""", (_cias(), list(plantillas)))
        filas = cr.fetchall()
        var = self._variantes([f[0] for f in filas])
        res = {}
        for pid, uds in filas:
            _modelo, mc, talla, _tid = var.get(pid, ('', '', '', 0))
            if mc in mcs:
                res.setdefault(mc, {})[talla] = res.get(mc, {}).get(talla, 0) + uds
        return res

    def _columnas_compactar(self, lineales, bloqueadas=()):
        """Columnas físicas de estos lineales con sus cajas con stock, para logica.plan_lineal, y los datos de cada
        caja (mc, tallas, uds, compañía).
        TUCTUC: una columna física = el mismo hueco en las compañías de la PDA (gemelos, mismo código de barras): sus cajas son
        las de todas sus compañías (comparten el sitio) y en 'cias' van las compañías en que existe. La clave de la
        columna es el id más bajo de sus gemelos; 'gemelos' = {(compañía, almacén): id del hueco} y cada caja lleva
        el (compañía, almacén) de su hueco: plan_lineal solo la manda a una columna que exista en ese par. Una columna con algo fuera de
        las temporadas del parámetro o con prendas sueltas no se toca."""
        cr = request.env.cr
        lineales = sorted(set(lineales))
        conds = ' OR '.join(['h.name ILIKE %s OR h.name ILIKE %s OR h.name ILIKE %s OR h.name ILIKE %s'] * len(lineales))
        args = [_cias(), _prefijos()]
        for n in lineales:
            args += _patrones_lineal(n)
        cr.execute("""SELECT h.id, h.name, h.company_id, h.barcode FROM stock_location h
                       WHERE h.active AND h.usage = 'internal' AND (h.company_id = ANY(%s) OR h.company_id IS NULL)
                         AND upper(left(h.name, 3)) <> ALL(%s) AND (""" + conds + ")", args)
        fisicas = {}        # (nombre, padre) -> {'clave', 'nombre', 'gemelos': {cia: id}}
        huecos = {}         # id de hueco -> clave de su columna física
        Loc = request.env['stock.location'].sudo()
        dueno = {}          # id de hueco -> (compañía, almacén): una caja solo va a un hueco de su compañía y almacén
        for hid, nombre, cia, codigo in cr.fetchall():
            if logica.lineal_de(nombre) not in lineales:
                continue
            f = fisicas.setdefault(codigo or hid, {'clave': hid, 'nombre': nombre, 'gemelos': {}})
            f['clave'] = min(f['clave'], hid)
            dueno[hid] = (cia, Loc.browse(hid).get_warehouse().id)
            f['gemelos'][dueno[hid]] = hid
        for f in fisicas.values():
            for hid in f['gemelos'].values():
                huecos[hid] = f['clave']
        if not huecos:
            return [], {}
        ids = tuple(huecos)
        cr.execute("""
            SELECT l.id, l.location_id, l.name, l.company_id, q.product_id, pp.product_tmpl_id, SUM(q.quantity)
              FROM stock_quant q
              JOIN stock_location l ON l.id = q.location_id
              JOIN product_product pp ON pp.id = q.product_id
             WHERE q.quantity > 0 AND l.active AND (l.id IN %s OR l.location_id IN %s)
             GROUP BY l.id, l.location_id, l.name, l.company_id, q.product_id, pp.product_tmpl_id""", (ids, ids))
        filas = cr.fetchall()
        var = self._variantes([f[4] for f in filas])
        tmpl_ids = list({f[5] for f in filas})
        Tmpl = request.env['product.template'].sudo()
        temporada = {}
        if 'season_id' in Tmpl._fields and tmpl_ids:
            for x in Tmpl.browse(tmpl_ids).read(['season_id']):
                temporada[x['id']] = (x['season_id'][1] if x['season_id'] else '').strip().upper()
        temporadas = self._temporadas()
        # cajas con prendas leídas para una OUT sin validar: se espera
        kos = list({f[0] for f in filas if f[0] not in huecos})
        leidas = set()
        if kos:
            cr.execute("""SELECT DISTINCT location_id FROM stock_move_line
                           WHERE state NOT IN ('done', 'cancel') AND qty_done > 0 AND location_id IN %s""",
                       (tuple(kos),))
            leidas = {f[0] for f in cr.fetchall()}
        bloq = {huecos[b] for b in bloqueadas if b in huecos}
        cols = {}
        for f in fisicas.values():
            cols[f['clave']] = {'id': f['clave'], 'nombre': f['nombre'], 'lineal': logica.lineal_de(f['nombre']),
                                'z': f['clave'] in bloq, 'extra': 0, 'cajas': [],
                                'cias': set(f['gemelos']),
                                'gemelos': f['gemelos']}
        info = {}          # caja -> {'nombre', 'mc', 'tallas': {mc: {talla: uds}}, 'uds', 'hueco', 'cia', 'plantillas'}
        for lid, padre, nombre, cia, pid, tid, uds in filas:
            clave = huecos.get(lid) or huecos.get(padre)
            if not logica.en_temporadas(temporada.get(tid, ''), temporadas) and clave in cols:
                cols[clave]['z'] = True
            if lid in huecos:                       # prendas sueltas en la columna: no se toca
                cols[huecos[lid]]['z'] = True
                continue
            if not _es_contenedor_nombre(nombre) or padre not in huecos:
                continue
            modelo, mc, talla, _tid = var.get(pid, ('', '', '', tid))
            d = info.setdefault(lid, {'nombre': nombre, 'hueco': padre, 'clave': huecos[padre], 'uds': 0.0,
                                      'tallas': {}, 'modelos': {}, 'cia': dueno[padre], 'plantillas': set()})
            d['modelos'][mc] = modelo
            d['plantillas'].add(tid)
            d['uds'] += uds
            d['tallas'].setdefault(mc, {})
            d['tallas'][mc][talla] = d['tallas'][mc].get(talla, 0) + uds
        for kid, d in info.items():
            mcs = sorted(d['tallas'], key=lambda m: -sum(d['tallas'][m].values()))
            d['mc'] = mcs[0]
            cols[d['clave']]['cajas'].append({'id': kid, 'mc': d['mc'], 'modelo': d['modelos'][d['mc']],
                                              'cia': d['cia'], 'movible': len(mcs) == 1 and kid not in leidas})
        return list(cols.values()), info

    @http.route('/tuctuc/contenedores/compactar/calcular', type='json', auth='user')
    def compactar_calcular(self, lineal=0, employee_id=False, **kw):
        """Calcula el plan de un lineal. Lo pendiente de ese lineal queda «sustituido» (lo hecho no se toca)."""
        try:
            self._comprobar_usuario()
            emp = self._empleado(employee_id)
            try:
                n = int(lineal or 0)
            except (TypeError, ValueError):
                raise UserError('Lineal no válido.')
            lo, hi = logica.rango_lineales(self._param(PARAM_LINEALES))
            if not lo <= n <= hi:
                raise UserError('L%d está fuera de los lineales de Compactar (L%d–L%d).' % (n, lo, hi))
            reglas = self._reglas_compactar()
            Paso = request.env['tuctuc.compactacion.paso'].sudo()
            otros = Paso.search([('estado', '=', 'pendiente'), ('lineal', '!=', n)])
            lineales = range(n - reglas['distancia'], n + reglas['distancia'] + 1)
            # las columnas que otro lineal está vaciando no reciben; las que van a recibir cuentan ya esas cajas
            cols, info = self._columnas_compactar(lineales, bloqueadas=set(otros.mapped('origen_id').ids))
            if not cols:
                raise UserError('No encuentro columnas en L%d.' % n)
            llegan = {}
            por_hueco = {}
            for c in cols:
                for hid in c['gemelos'].values():
                    por_hueco[hid] = c['id']
            for p in otros:
                clave = por_hueco.get(p.destino_id.id)
                if clave:
                    llegan[clave] = llegan.get(clave, 0) + 1
            for c in cols:
                c['extra'] = llegan.get(c['id'], 0)
            gemelos = {c['id']: c['gemelos'] for c in cols}
            lineas_mc = self._lineas_28_mc()   # 1.0.2: guardado 12 h
            abc = logica.clases_abc({mc: lineas_mc.get(mc, 0) for mc in lineas_mc})
            pasos, resumen = logica.plan_lineal(n, cols, abc=abc, **reglas)
            plantillas = set()
            for p in pasos:
                plantillas |= info[p['caja_id']]['plantillas']
            lineas_talla = self._lineas_28_talla(plantillas)   # 1.0.2: solo las plantillas del plan
            stock = self._stock_tallas({p['mc'] for p in pasos}, plantillas)
            bandas = {}
            for mc in {p['mc'] for p in pasos}:
                tallas = stock.get(mc) or {}
                bandas[mc] = logica.tallas_por_altura(tallas, {t: lineas_talla.get((mc, t), 0) for t in tallas})
            calculo = '%s-L%d-%s' % (fields.Datetime.now().strftime('%Y%m%d%H%M%S'), n, emp.id)
            with request.env.cr.savepoint():
                Paso.search([('lineal', '=', n), ('estado', '=', 'pendiente')]).write(
                    {'estado': 'sustituido', 'motivo': 'Recalculado (%s)' % emp.name})
                for p in pasos:
                    d = info[p['caja_id']]
                    # TUCTUC: la columna física -> el hueco real (origen: donde está la caja; destino: el gemelo de
                    # la compañía de la caja, que plan_lineal ya ha comprobado que existe)
                    destino = gemelos.get(p['destino_id'], {}).get(d['cia'])
                    Paso.create({
                        'lineal': n, 'calculo': calculo, 'orden': p['orden'], 'origen_id': d['hueco'],
                        'contenedor_id': p['caja_id'], 'contenedor': d['nombre'], 'destino_id': destino,
                        'company_id': d['cia'][0] or False,
                        'mc': p['mc'], 'uds': d['uds'],
                        'banda': logica.banda_caja(d['tallas'].get(p['mc'], {}), bandas.get(p['mc'], {}))})
            ceros = len([c for c in self._cajas(_SQL_LINEAL, _patrones_lineal(n))
                         if c['lineal'] == n and c['estado'] == 'cero' and not c['con_prendas']])
            msg = 'L%d: %d columnas se vacían moviendo %d cajas' % (n, resumen['vaciadas'], resumen['cajas'])
            if resumen['sin_sitio']:
                msg += ' (%d con pocas cajas no caben en otro sitio)' % resumen['sin_sitio']
            datos = self._datos_compactar_lineal(n)
            datos['cajas_cero'] = ceros
            return {'ok': True, 'msg': msg, 'lineal': datos}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    def _banda(self, loc):
        b = request.env['tuctuc.contenedor.banda'].sudo().search([('contenedor_id', '=', loc.id)], limit=1)
        return b.banda or ''

    def _nombre_columna(self, loc):
        return (loc.name or '').split(' - ', 1)[-1] if loc else ''

    def _datos_compactar_lineal(self, n):
        Paso = request.env['tuctuc.compactacion.paso'].sudo()
        pasos = Paso.search([('lineal', '=', n), ('estado', '!=', 'sustituido')])
        grupos = {}
        for p in pasos:
            g = grupos.setdefault(p.origen_id.id, {'origen_id': p.origen_id.id,
                                                   'origen': self._nombre_columna(p.origen_id),
                                                   'orden': p.orden, 'pasos': []})
            g['orden'] = min(g['orden'], p.orden)
            g['pasos'].append({'id': p.id, 'contenedor_id': p.contenedor_id.id, 'contenedor': p.contenedor,
                               'mc': p.mc, 'uds': p.uds, 'banda': p.banda or 'arriba',
                               'destino': self._nombre_columna(p.destino_id),
                               'destino_real': self._nombre_columna(p.destino_real_id), 'estado': p.estado,
                               'orden': p.orden})
        lista = sorted(grupos.values(), key=lambda g: (all(x['estado'] != 'pendiente' for x in g['pasos']),
                                                       g['orden']))
        for g in lista:
            g['pasos'].sort(key=lambda x: x['orden'])
            g['pendientes'] = len([x for x in g['pasos'] if x['estado'] == 'pendiente'])
            g['libre'] = all(x['estado'] in ('hecho', 'cambiado') for x in g['pasos'])
        return {'lineal': n, 'codigo': 'L%d' % n, 'grupos': lista, 'total': len(pasos),
                'hechos': len(pasos.filtered(lambda p: p.estado in ('hecho', 'cambiado'))),
                'pendientes': len(pasos.filtered(lambda p: p.estado == 'pendiente')),
                'no_esta': len(pasos.filtered(lambda p: p.estado == 'no_esta')),
                'columnas': len(lista), 'libres': len([g for g in lista if g['libre']])}

    @http.route('/tuctuc/contenedores/compactar/lineal', type='json', auth='user')
    def compactar_lineal(self, lineal=0, employee_id=False, **kw):
        try:
            self._comprobar_usuario()
            self._empleado(employee_id)
            try:
                n = int(lineal or 0)
            except (TypeError, ValueError):
                raise UserError('Lineal no válido.')
            return {'ok': True, 'lineal': self._datos_compactar_lineal(n)}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/tuctuc/contenedores/compactar/resumen', type='json', auth='user')
    def compactar_resumen(self, employee_id=False, **kw):
        """Avance por lineal: pasos hechos / total y columnas libres / previstas."""
        try:
            self._comprobar_usuario()
            self._empleado(employee_id)
            cr = request.env.cr
            cr.execute("""
                SELECT lineal, COUNT(*),
                       COUNT(*) FILTER (WHERE estado IN ('hecho', 'cambiado')),
                       COUNT(*) FILTER (WHERE estado = 'pendiente'),
                       COUNT(DISTINCT origen_id),
                       COUNT(DISTINCT origen_id) FILTER (WHERE estado IN ('pendiente', 'no_esta'))
                  FROM tuctuc_compactacion_paso WHERE estado <> 'sustituido'
                 GROUP BY lineal ORDER BY lineal""")
            filas = [{'lineal': l, 'total': t, 'hechos': h, 'pendientes': p, 'columnas': c, 'libres': c - abiertas}
                     for l, t, h, p, c, abiertas in cr.fetchall()]
            lo, hi = logica.rango_lineales(self._param(PARAM_LINEALES))
            return {'ok': True, 'lineales': filas, 'rango': 'L%d–L%d' % (lo, hi),
                    'capacidad': self._reglas_compactar()['capacidad']}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    def _modelo_mc(self, contenedor):
        """(modelo, mc) de la prenda con más uds de una caja, o None si está vacía."""
        quants = request.env['stock.quant'].sudo().search([('location_id', '=', contenedor.id), ('quantity', '>', 0)])
        if not quants:
            return None
        q = max(quants, key=lambda x: x.quantity)
        modelo, mc, _t, _tid = self._variantes([q.product_id.id]).get(q.product_id.id, ('', '', '', 0))
        return modelo, mc

    def _cajas_columna(self, columna):
        """(modelo, mc) de las cajas con stock de una columna (todas sus compañías), para avisar al dejar una caja
        fuera del plan."""
        res = []
        for c in self._hijos_contenedor(columna):
            par = self._modelo_mc(c)
            if par:
                res.append(par)
        return res

    @http.route('/tuctuc/contenedores/compactar/hacer', type='json', auth='user')
    def compactar_hacer(self, paso_ids=None, destino_id=False, employee_id=False, confirmado=False, **kw):
        """Mueve las KO de estos pasos a la columna leída (como /mover: se llevan prendas y reservas) y apunta su
        altura. Si la columna no es la del plan y hay algo que avisar (otro color del mismo modelo, más de 8 cajas),
        pide confirmar. Todo o nada."""
        try:
            self._comprobar_usuario()
            emp = self._empleado(employee_id)
            Loc = request.env['stock.location'].sudo()
            destino = Loc.browse(int(destino_id or 0)).exists()
            if not destino:
                raise UserError('Lee la columna de destino.')
            self._validar_destino(destino)
            Paso = request.env['tuctuc.compactacion.paso'].sudo()
            pasos = Paso.browse([int(i) for i in (paso_ids or [])]).exists()
            if not pasos:
                raise UserError('Lee antes las cajas del paso.')
            for p in pasos:
                c = p.contenedor_id
                if p.estado != 'pendiente':
                    raise UserError('%s ya no está pendiente (%s).' % (p.contenedor, dict(
                        p._fields['estado'].selection).get(p.estado)))
                if not c.active:
                    raise UserError('%s está archivada. Márcala «No está».' % p.contenedor)
                if c.location_id != p.origen_id and c.location_id not in self._gemelos(destino):
                    raise UserError('%s ya no está en %s (está en %s). Márcala «No está» o vuelve a calcular.' % (
                        p.contenedor, self._nombre_columna(p.origen_id), c.location_id.complete_name))
                if self._leidas(c):
                    raise UserError('%s tiene prendas leídas para una OUT sin validar: se espera. Déjala para luego.'
                                    % p.contenedor)
            # TUCTUC: cada caja va al gemelo de su compañía de la columna leída (nunca entre compañías)
            destinos = {}
            for p in pasos:
                cia = self._compania_de(p.contenedor_id)
                d = self._gemelo(destino, cia, cerca=p.contenedor_id.location_id)
                if not d:
                    raise UserError('%s no existe en el almacén de %s (%s, %s): no se mueve nada.' % (
                        destino.barcode or destino.name, p.contenedor,
                        p.contenedor_id.location_id.get_warehouse().code or '?', cia.name or '?'))
                destinos[p.id] = d
            fuera = pasos.filtered(lambda p: p.destino_id != destinos[p.id])
            if fuera and not confirmado:
                ya = self._cajas_columna(destino)
                avisos = []
                grupos = {}
                for p in fuera:
                    par = self._modelo_mc(p.contenedor_id) or ('', p.mc)
                    grupos.setdefault(par, 0)
                    grupos[par] += 1
                for (modelo, mc), cuantas in grupos.items():
                    a = logica.aviso_destino(ya, mc, modelo, cuantas, self._reglas_compactar()['capacidad'])
                    if a:
                        avisos.append(a)
                return {'ok': False, 'confirmar': True,
                        'msg': '%s no es la columna del plan (%s).%s ¿La dejas aquí?' % (
                            self._nombre_columna(destino), ', '.join(sorted(set(
                                self._nombre_columna(p.destino_id) for p in fuera))),
                            (' OJO: ' + '; '.join(avisos) + '.') if avisos else '')}
            Mov = request.env['tuctuc.contenedor.movimiento'].sudo()
            Banda = request.env['tuctuc.contenedor.banda'].sudo()
            textos = []
            with request.env.cr.savepoint():
                for p in pasos:
                    c = p.contenedor_id
                    origen = c.location_id
                    destino_c = destinos[p.id]
                    if origen != destino_c:
                        quants = request.env['stock.quant'].sudo().search(
                            [('location_id', '=', c.id), ('quantity', '!=', 0)])
                        c.write({'location_id': destino_c.id})
                        mov = Mov.create({
                            'contenedor': c.name, 'origen_id': origen.id, 'destino_id': destino_c.id,
                            'origen': origen.complete_name, 'destino': destino_c.complete_name,
                            'uds': sum(quants.mapped('quantity')),
                            'reservadas': sum(quants.mapped('reserved_quantity')), 'lineas': len(quants),
                            'employee_id': emp.id, 'paso_id': p.id})
                    else:
                        mov = Mov.browse()
                    banda = p.banda or 'arriba'
                    b = Banda.search([('contenedor_id', '=', c.id)], limit=1)
                    if b:
                        b.write({'banda': banda, 'employee_id': emp.id})
                    else:
                        Banda.create({'contenedor_id': c.id, 'banda': banda, 'employee_id': emp.id})
                    p.write({'estado': 'hecho' if p.destino_id == destino_c else 'cambiado',
                             'destino_real_id': destino_c.id, 'employee_id': emp.id,
                             'fecha': fields.Datetime.now(), 'movimiento_id': mov.id or False})
                    textos.append('%s → %s · %s' % (c.name, self._nombre_columna(destino), banda.upper()))
                request.env['tuctuc.contenedor.movimiento'].flush()
            libres = []
            for origen in pasos.mapped('origen_id'):
                resto = Paso.search([('origen_id', '=', origen.id), ('estado', '=', 'pendiente')])
                if not resto:
                    libres.append(self._nombre_columna(origen))
            return {'ok': True, 'msg': '; '.join(textos), 'libres': libres,
                    'bandas': [{'contenedor': p.contenedor, 'banda': p.banda or 'arriba'} for p in pasos],
                    'lineal': self._datos_compactar_lineal(pasos[0].lineal)}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/tuctuc/contenedores/compactar/marcar', type='json', auth='user')
    def compactar_marcar(self, paso_id=False, accion='', employee_id=False, **kw):
        """«No está» (la KO no está en la columna: queda para revisar, sin cambiar nada en Odoo) o «Saltar» (al
        final del lineal)."""
        try:
            self._comprobar_usuario()
            emp = self._empleado(employee_id)
            p = request.env['tuctuc.compactacion.paso'].sudo().browse(int(paso_id or 0)).exists()
            if not p or p.estado != 'pendiente':
                raise UserError('Ese paso ya no está pendiente. Vuelve a abrir el lineal.')
            if accion == 'no_esta':
                p.write({'estado': 'no_esta', 'employee_id': emp.id, 'fecha': fields.Datetime.now(),
                         'motivo': 'No está en la columna (%s)' % emp.name})
                msg = '%s marcada «No está».' % p.contenedor
            elif accion == 'saltar':
                ultimo = max(request.env['tuctuc.compactacion.paso'].sudo().search(
                    [('lineal', '=', p.lineal), ('estado', '!=', 'sustituido')]).mapped('orden') or [0])
                p.write({'orden': ultimo + 1})
                msg = '%s, al final del lineal.' % p.contenedor
            else:
                raise UserError('Acción no válida.')
            return {'ok': True, 'msg': msg, 'lineal': self._datos_compactar_lineal(p.lineal)}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}
