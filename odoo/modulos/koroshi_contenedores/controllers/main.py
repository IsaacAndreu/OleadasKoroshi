# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Contenedores - rutas de la pantalla. Con sudo: el usuario de la PDA no necesita permisos sobre
# stock.location. Cambian location_id del contenedor (KO_/TT_), lo archivan y escriben en koroshi.contenedor.movimiento.
# v1.5: /cero y /anadir hacen ajustes de inventario (stock.move hecho contra pérdidas de inventario); quién y cuándo
# queda en koroshi.contenedor.movimiento, como en Lecturas y Faltantes.
# v1.6: /leer con una prenda (EAN o referencia) dice dónde hay stock de ella; /mover dice cuántos contenedores movió.
# v1.7: /cantidad pone las uds reales de un artículo del contenedor (ajuste de la diferencia, + o -, nunca por debajo
# de lo reservado). /buscar y /leer encuentran el contenedor por un trozo del nombre (etiqueta rota: «290726_44»).
# v1.8: /buscar y /leer por trozo buscan todo lo que tiene código: contenedores, huecos (código de barras o nombre),
# lineales y artículos (EAN, referencia o nombre); /donde dice dónde está un artículo por su id. Leer la referencia
# entera de un artículo (2622JA00-000003-L) ya lo encuentra: en muchos artículos la referencia solo está en el nombre.
# v1.13 (revisión general 23/11): a Faltantes solo la diferencia (R1); «Cambiar» no se hace con prendas leídas sin
# validar ni si Odoo ha cambiado mientras se contaba (R2); «Añadir» con id de tanda (R3); «Poner a cero» cierra sus
# faltantes como no encontrados y «Archivar» no deja faltantes con vuelta al contenedor (R4); cada faltante deja su
# línea en el registro; la compañía sale de koroshi_base (O6).
# v1.14 (R23): /cambiar_articulo («Es otro»): lo que Odoo llama A en el contenedor es B (error de talla). Un ajuste de
# -N de A y otro de +N de B en un savepoint, y UNA línea en el registro con los dos movimientos.
# v1.15 (revisión general 23/11, O5 y R16): grupo, tarjeta y búsqueda de la prenda salen de koroshi_base.pda (1.2.0).
# La tarjeta tiene que ser de un operario activo de la compañía (antes bastaba con que existiera).
# =============================================================================
import re

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import float_compare, float_is_zero
from odoo.addons.koroshi_base import comun, pda

from .. import logica

PREFIJOS = ('KO_', 'TT_')
MAX_LINEAS = 40
MAX_ANADIR = 500          # v1.5: uds de un artículo en un solo «Añadir» (más = lecturas de más)
COMPANY_ID = comun.COMPANY_ID   # EFFECTIVE LOGISTICS (si el contenedor no tiene empresa); v1.13: de koroshi_base
ORIGEN = 'Desde Contenedores'   # v1.13: nota en el faltante y en el historial de la OUT
MAX_HUECOS = 400
MAX_DONDE = 60            # v1.6: ubicaciones como máximo al buscar dónde está un artículo
MAX_BUSCAR = 20           # v1.7: contenedores como máximo al buscar por un trozo del nombre
MIN_BUSCAR = 2            # v1.7: caracteres mínimos para buscar por un trozo
MIN_BUSCAR_OTROS = 3      # v1.8: huecos y artículos, a partir de 3 caracteres
MAX_TIPO = 8              # v1.8: resultados como máximo de cada tipo (contenedor, hueco, artículo)
# v1.8.1: solo ubicaciones de esta compañía. UBRAN (otra compañía) tiene los mismos huecos con el mismo código de barras
# (UBRAN/STOCK/N1/07828 - L94 P35 C1): sin esto, leer «L94 P35 C1» daba «Hay 2 ubicaciones» y el lineal y la
# búsqueda mezclaban huecos de las dos.
DE_LA_COMPANIA = ('company_id', 'in', [COMPANY_ID, False])
# v1.8.2: también los lineales de MU (MU-01…MU-14): sus huecos se llaman «MU-01 P00 C1», sin número delante
LINEAL_RE = re.compile(r'^(L\d{1,4}|MU-? ?\d{1,2})$', re.I)
LINEAL_DELANTE_RE = re.compile(r'^(L\d{1,4}|MU-\d{1,2})(\s|$)', re.I)   # «MU-00 P» o «L70 P3»: se ofrece el lineal


def _lineal(texto):
    """Código del lineal normalizado (L94, MU-01) o None. «mu1», «MU 01» y «MU-1» son MU-01."""
    t = (texto or '').strip().upper()
    if not LINEAL_RE.match(t):
        return None
    if t.startswith('MU'):
        return 'MU-%02d' % int(re.sub(r'\D', '', t))
    return t


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
        # «07828 - L94 P35 C1» lleva el lineal en medio; «MU-01 P00 C1» (v1.8.2), al principio
        huecos = Loc.search([('usage', '=', 'internal'), DE_LA_COMPANIA, '|', ('name', 'ilike', clave),
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
            Faltante = request.env['koroshi.faltante'].sudo()
            for c in self._hijos_contenedor(hueco):
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
                raise UserError('%s no tiene contenedores KO_/TT_: ya está limpia.' % hueco.complete_name)
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
        inventario del artículo, como un ajuste de Odoo. Mismo movimiento que koroshi_faltantes._mover (probado en
        producción). Deja su línea en el registro (quién, cuándo, artículo, uds y movimiento)."""
        move = self._mover_ajuste(producto, qty, contenedor, company, nombre)
        request.env['koroshi.contenedor.movimiento'].sudo().create({
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
            self._antes_de_archivar(conts)   # v1.13 (R4): antes de escribir nada
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

    @http.route('/koroshi/contenedores/archivar_uno', type='json', auth='user')
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
            self._antes_de_archivar([c])   # v1.13 (R4)
            hueco = c.location_id
            c.write({'active': False})
            request.env['koroshi.contenedor.movimiento'].sudo().create({
                'accion': 'archivar', 'contenedor': c.name, 'origen_id': hueco.id, 'origen': hueco.complete_name,
                'destino': '(archivado, vacío, confirmado)', 'employee_id': emp.id})
            return {'ok': True, 'msg': '%s: %s archivado (estaba en %s)' % (emp.name, c.name, hueco.complete_name)}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    def _buscar_producto(self, codigo):
        """Prenda por EAN (y UPC/EAN con 0 delante), código alternativo, referencia interna o nombre. Vacío si no hay.
        v1.15 (O5): la de koroshi_base.pda, la misma en todas las pantallas (con sudo, como antes)."""
        return pda.buscar_producto(request.env['product.product'].sudo().env, codigo)

    def _donde(self, producto):
        """v1.6: dónde hay stock de un artículo (ubicaciones internas de la compañía), por hueco y contenedor, para
        devolver al sitio una prenda fuera de lugar. Solo lectura."""
        quants = request.env['stock.quant'].sudo().search([
            ('product_id', '=', producto.id), ('location_id.usage', '=', 'internal'),
            ('company_id', '=', COMPANY_ID), ('quantity', '>', 0)])
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

    @http.route('/koroshi/contenedores/producto', type='json', auth='user')
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
                res['mismo_modelo'] = bool(a) and logica.mismo_modelo(a.name, p.name)
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
        reubicar en el hueco con stock libre más cercano que llegue (koroshi.faltante.reubicar) o, si no hay,
        sin_alternativa (la OUT sale sin ella). En los dos casos la unidad va a FALTANTE y queda su registro.
        No se toca una línea que ya tiene algo leído: alguien la está preparando.
        v1.12.0: con producto, solo sus líneas, y se para cuando lo reservado que queda es <= dejar.
        v1.13.0 (R1): pasa solo lo que sobra (reservado - dejar): una línea de 5 con 4 en el contenedor sigue con 4
        reservadas aquí y solo 1 pasa a Faltantes. El hueco alternativo se busca entre todos, no solo los 5 más
        cercanos. Cada faltante deja su línea en el registro de Contenedores.
        Devuelve (resumen por línea, faltantes creados)."""
        Faltante = request.env['koroshi.faltante'].sudo()
        Mov = request.env['koroshi.contenedor.movimiento'].sudo()
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

    def _antes_de_archivar(self, conts):
        """v1.13 (R4): los faltantes pendientes con vuelta a estos contenedores pasan a apuntar a su hueco; si alguno
        está en una ronda abierta, error y no se archiva ninguno."""
        Loc = request.env['stock.location'].sudo()
        ubicaciones = Loc.browse([c.id for c in conts])
        request.env['koroshi.faltante'].sudo().antes_de_archivar(ubicaciones)

    @http.route('/koroshi/contenedores/cero', type='json', auth='user')
    def cero(self, contenedor_id=False, employee_id=False, confirmado=False, pasar_faltantes=False, **kw):
        """Pone a cero el contenedor (está físicamente vacío y Odoo dice que tiene prendas): ajuste de inventario de
        cada artículo. v1.11.0: si hay prendas reservadas para una OUT, con pasar_faltantes se hace antes lo mismo que
        el operario al marcar un faltante (koroshi_faltantes): la línea se reserva en otro hueco con stock libre (el
        más cercano) o, si no hay, la OUT sale sin ella; la unidad va a FALTANTE y queda en Faltantes."""
        try:
            self._comprobar_usuario()
            if not confirmado:
                raise UserError('Confirma que el contenedor está físicamente vacío.')
            emp = self._empleado(employee_id)
            c = self._contenedor(contenedor_id)
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
                                 'KOROSHI contenedor %s: poner a cero (%s)' % (c.name, emp.name))
                    total += d['qty']
                    n += 1
                request.env['stock.move'].flush()   # v1.13: todo escrito dentro del savepoint
            msg ='%s: %s a cero (%s uds de %d ref. fuera del stock)' % (emp.name, c.name, _num(total), n)
            if resumen:
                msg += '. A Faltantes: ' + '; '.join(resumen)
            return {'ok': True, 'msg': msg, 'contenedor': self._datos_contenedor(c)}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/koroshi/contenedores/anadir', type='json', auth='user')
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
            tanda = (tanda or '').strip()[:64] if isinstance(tanda, str) else ''
            if tanda:
                ya = request.env['koroshi.contenedor.movimiento'].sudo().search([('tanda', '=', tanda)])
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
            company = c.company_id or request.env['res.company'].sudo().browse(COMPANY_ID)
            with request.env.cr.savepoint():    # todo o nada
                for p, uds in por_producto.items():
                    self._ajuste(p, uds, c, company, emp, 'anadir',
                                 'KOROSHI contenedor %s: añadir prendas (%s)' % (c.name, emp.name), tanda=tanda)
                request.env['stock.move'].flush()   # v1.13: la restricción de la tanda salta aquí dentro
            return {'ok': True, 'msg': '%s: %d uds añadidas a %s' % (emp.name, sum(por_producto.values()), c.name),
                    'contenedor': self._datos_contenedor(c)}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/koroshi/contenedores/cantidad', type='json', auth='user')
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
            company = quants[:1].company_id or c.company_id or request.env['res.company'].sudo().browse(COMPANY_ID)
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
                                 'KOROSHI contenedor %s: cambiar cantidad (%s)' % (c.name, emp.name))
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
            ('picking_id.picking_type_id.code', '=', 'outgoing'), ('company_id', '=', COMPANY_ID)],
            order='id', limit=50)
        pickings = moves.mapped('picking_id')
        nombres = ['%s%s' % (p.name, ' (%s)' % p.origin if p.origin else '') for p in pickings[:limite]]
        return nombres, max(0, len(pickings) - limite)

    @http.route('/koroshi/contenedores/cambiar_articulo', type='json', auth='user')
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
            Product = request.env['product.product'].sudo()
            a = Product.browse(int(producto_id or 0)).exists()
            b = Product.browse(int(producto_real_id or 0)).exists()
            if not a or not b:
                raise UserError('Artículo no válido. Vuelve a abrir el contenedor.')
            if a == b:
                raise UserError('Es el mismo artículo. Si faltan o sobran uds, usa «Cambiar».')
            Mov = request.env['koroshi.contenedor.movimiento'].sudo()
            tanda = (tanda or '').strip()[:64] if isinstance(tanda, str) else ''
            if tanda:
                ya = Mov.search([('tanda', '=', tanda)], limit=1)
                if ya:
                    return {'ok': True, 'repetida': True,
                            'msg': 'Ya estaba guardado: %s uds de %s son %s en %s (no se hace otra vez)' % (
                                _num(ya.uds), ya.producto_id.display_name, ya.producto_nuevo_id.display_name,
                                ya.contenedor),
                            'contenedor': self._datos_contenedor(c)}
            if not logica.mismo_modelo(a.name, b.name) and not otro_modelo:
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
            company = quants[:1].company_id or c.company_id or request.env['res.company'].sudo().browse(COMPANY_ID)
            nombre = 'KOROSHI contenedor %s: %s es %s (%s)' % (c.name, a.display_name, b.display_name, emp.name)
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
        dominio = [('usage', '=', 'internal'), DE_LA_COMPANIA, ('name', '=ilike', '%' + _literal(texto) + '%'), '|',
                   ('name', '=ilike', 'KO\\_%'), ('name', '=ilike', 'TT\\_%')]
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
            huecos = Loc.search([('usage', '=', 'internal'), DE_LA_COMPANIA, '|', ('barcode', '=ilike', lit),
                                 ('name', '=ilike', lit)],
                                order='name', limit=MAX_TIPO * 3)
            huecos = huecos.filtered(lambda l: not _es_contenedor_nombre(l.name))
            mas = mas or len(huecos) > MAX_TIPO
            items += [{'tipo': 'hueco', 'id': l.id, 'nombre': l.barcode or l.name, 'detalle': l.complete_name}
                      for l in huecos[:MAX_TIPO]]
            pre = _literal(texto) + '%'
            # un hueco (L94 P35), un lineal o un contenedor no es un artículo: no se busca (la búsqueda de artículos
            # tarda ~1 s, la de huecos ~0,2 s)
            sin_articulos = bool(re.match(r'^(L\d|MU-|KO_|TT_)', texto, re.I))
            Product = request.env['product.product'].sudo()
            prods = Product.browse() if sin_articulos else Product.search([
                ('company_id', 'in', [COMPANY_ID, False]), '|', '|',
                ('name', '=ilike', pre), ('default_code', '=ilike', pre), ('barcode', '=ilike', pre)],
                order='name', limit=MAX_TIPO + 1)
            mas = mas or len(prods) > MAX_TIPO
            prods = prods[:MAX_TIPO]
            stock = {}
            if prods:
                for g in request.env['stock.quant'].sudo().read_group(
                        [('product_id', 'in', prods.ids), ('location_id.usage', '=', 'internal'),
                         ('company_id', '=', COMPANY_ID)], ['quantity'], ['product_id']):
                    stock[g['product_id'][0]] = g['quantity']
            items += [{'tipo': 'articulo', 'id': p.id, 'nombre': p.display_name,
                       'detalle': '%s uds en almacén' % _num(stock.get(p.id, 0))} for p in prods]
        return items, mas, conts

    @http.route('/koroshi/contenedores/buscar', type='json', auth='user')
    def buscar(self, texto='', **kw):
        """v1.7: sugerencias mientras se escribe (solo lectura). v1.8: de todo lo que tiene código."""
        try:
            self._comprobar_usuario()
            items, mas, _c = self._sugerir(texto)
            return {'ok': True, 'items': items, 'mas': mas}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/koroshi/contenedores/donde', type='json', auth='user')
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

    @http.route('/koroshi/contenedores/leer', type='json', auth='user')
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
                loc = Loc.search([('usage', '=', 'internal'), DE_LA_COMPANIA, '|',
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
            loc = Loc.search([('barcode', '=', codigo), DE_LA_COMPANIA])
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
            msg = 'Se han movido %d contenedor%s. %s: %s → %s' % (
                len(movidos), '' if len(movidos) == 1 else 'es', emp.name, ', '.join(movidos), destino.complete_name)
            if iguales:
                msg += ' (%s ya estaba allí)' % ', '.join(iguales)
            return {'ok': True, 'msg': msg}
        except UserError as e:
            return {'ok': False, 'msg': _msg(e)}
