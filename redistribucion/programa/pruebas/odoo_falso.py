# -*- coding: utf-8 -*-
"""Odoo inventado y pequeño, para probar la descarga y el resto del programa sin conectarse a nada.
DATOS INVENTADOS: no salen de Odoo. Imita los nombres reales (muestra del 23/11): «00006 - L01 P19 C2»."""
import datetime

from redistrib.odoo_lectura import MAX_FILAS, comprobar_metodo


def _m2o(i, nombre):
    return [i, nombre] if i else False


def _ubic(i, nombre, padre, ruta_padre, barcode=False, activa=True):
    return {'id': i, 'name': nombre, 'complete_name': '%s/%s' % (ruta_padre, nombre), 'location_id': _m2o(padre, ruta_padre),
            'barcode': barcode, 'active': activa}


def datos_inventados():
    N = 'EFFEC/Stock/NAVE2'
    u = [{'id': 1, 'name': 'NAVE2', 'complete_name': N, 'location_id': [2, 'EFFEC/Stock'], 'barcode': False, 'active': True},
         {'id': 2, 'name': 'Stock', 'complete_name': 'EFFEC/Stock', 'location_id': False, 'barcode': False, 'active': True}]
    i = 10
    huecos = {}
    for lineal, pos, niveles in ((1, 1, 4), (1, 2, 2), (2, 1, 4), (121, 1, 6)):
        for c in range(1, niveles + 1):
            t = 'L%02d P%02d C%d' % (lineal, pos, c)
            u.append(_ubic(i, '%05d - %s' % (i, t), 1, N, t))
            huecos[t] = i
            i += 1
    h = huecos
    u += [_ubic(100, 'KO_110626_001', h['L01 P01 C1'], N + '/00010 - L01 P01 C1'),
          _ubic(101, 'KO_110626_002', h['L01 P01 C1'], N + '/00010 - L01 P01 C1'),     # a cero, sin archivar
          _ubic(102, 'TT_120626_001', h['L02 P01 C3'], N + '/x - L02 P01 C3'),
          _ubic(103, 'KO_110626_003', h['L01 P02 C1'], N + '/x', activa=False),         # archivado
          _ubic(200, 'MU-01', 1, N),
          _ubic(104, 'KO_130626_009', 200, N + '/MU-01'),                               # contenedor en el muelle
          _ubic(201, 'N1-L05', 1, N, 'N1-L05 P01'),
          _ubic(202, 'PASILLO RARO', 1, N),
          _ubic(300, 'SORTER', 2, 'EFFEC'),
          _ubic(301, 'Stock', 2, 'CONS')]
    p = [  # id, default_code, plantilla, volumen m3
        (1, '2621JA67-NEGRO-M', 1, 0.0084), (2, '2621JA67-NEGRO-L', 1, 0.0),
        (3, '2511PT03-AZUL-40', 2, 0.0025), (4, '2611TR01-ROJO-S', 3, 0.0), (5, 'RAROSINFAMILIA', 4, 0.0)]
    productos = [{'id': a, 'default_code': b, 'name': '[%s] Prenda' % b, 'barcode': '84%011d' % a,
                  'product_tmpl_id': [c, 'Plantilla %d' % c], 'volume': v, 'weight': 0.0, 'active': True}
                 for a, b, c, v in p]
    plantillas = [{'id': 1, 'season_id': [7, 'I27']}, {'id': 2, 'season_id': [3, 'I25']},
                  {'id': 3, 'season_id': False}, {'id': 4, 'season_id': [8, 'V27']}]
    q = [  # ubicación, producto, cantidad, reservado
        (100, 1, 10, 0), (100, 3, 5, 0), (h['L01 P01 C2'], 1, 4, 1), (h['L02 P01 C3'], 2, 6, 0),
        (102, 1, 3, 0), (h['L121 P01 C6'], 4, 8, 0), (200, 3, 20, 0), (104, 1, 2, 0), (201, 2, 1, 0),
        (202, 5, 7, 0), (300, 1, 9, 0), (301, 3, 11, 0), (h['L01 P02 C1'], 3, -2, 0)]
    quants = [{'id': n + 1, 'location_id': [a, 'x'], 'product_id': [b, 'x'], 'quantity': c, 'reserved_quantity': d}
              for n, (a, b, c, d) in enumerate(q)]
    tipos = [{'id': 3, 'name': 'MODALADA: Órdenes de entrega', 'code': 'outgoing', 'warehouse_id': [2, 'MODALADA'],
              'active': True},
             {'id': 1, 'name': 'Effective: Órdenes de entrega', 'code': 'outgoing', 'warehouse_id': [1, '6665 STOCK GENERAL KOROSHI'], 'active': True},
             {'id': 2, 'name': 'Effective: Transferencias internas', 'code': 'internal', 'warehouse_id': [1, '6665 STOCK GENERAL KOROSHI'], 'active': True}]
    hoy = datetime.datetime(2026, 11, 23, 9, 0)
    lineas = []
    for n in range(60):
        lineas.append({'id': 1000 + n, 'product_id': [1 + n % 3, 'x'], 'location_id': [[h['L01 P01 C2'], 100, 102][n % 3], 'x'],
                       'location_dest_id': [9, 'Partners/Customers'], 'qty_done': 1.0,
                       'date': (hoy - datetime.timedelta(days=n)).strftime('%Y-%m-%d %H:%M:%S'),
                       'picking_id': [n + 1, 'EFFEC/OUT/%05d' % n], 'tipo': 1 if n % 5 else 2})
    lineas.append({'id': 999, 'product_id': [1, 'x'], 'location_id': [300, 'x'], 'location_dest_id': [9, 'x'],
                   'qty_done': 1.0, 'date': '2026-11-20 10:00:00', 'picking_id': [900, 'MOD/OUT/1'], 'tipo': 3})
    albaranes = [{'id': l['picking_id'][0], 'picking_type_id': [l['tipo'], 'x']} for l in lineas]
    return {'stock.location': u, 'product.product': productos, 'product.template': plantillas, 'stock.quant': quants,
            'stock.picking.type': tipos, 'stock.move.line': lineas, 'stock.picking': albaranes}


def _cumple(fila, cond):
    campo, op, valor = cond
    if campo in ('move_id.picking_type_id', 'picking_type_id', 'picking_id.picking_type_id'):
        return fila.get('tipo') == valor if op == '=' else fila.get('tipo') in valor
    if '.' in campo or campo not in fila:
        return True                         # lo que el falso no modela (compañía, usage, state…) se da por bueno
    v = fila.get(campo)
    if isinstance(v, list):
        v = v[0]
    if op == '=':
        return v == valor
    if op == '!=':
        return v != valor
    if op == '>':
        return v > valor
    if op == '>=':
        return v >= valor
    if op == 'in':
        return v in valor
    raise NotImplementedError(op)


class OdooFalso:
    """Mismo uso que ClienteLectura (leer_paginado, llamar, campos, contar) y la misma lista blanca."""
    url, bd = 'https://odoo-inventado.ejemplo', 'INVENTADA'

    def __init__(self, datos=None):
        self.datos = datos or datos_inventados()
        self.peticiones = 0
        self.registro = []

    def _filtrar(self, modelo, dominio):
        return [f for f in self.datos[modelo] if all(_cumple(f, c) for c in dominio if isinstance(c, (list, tuple)))]

    def llamar(self, modelo, metodo, args=None, kwargs=None):
        comprobar_metodo(metodo)
        self.peticiones += 1
        self.registro.append((modelo, metodo, args, kwargs))
        kwargs = kwargs or {}
        if metodo == 'read':
            ids, campos = args[0], args[1]
            assert len(ids) <= MAX_FILAS
            return [{k: f.get(k) for k in ['id'] + campos} for f in self.datos[modelo] if f['id'] in ids]
        if metodo == 'search_read':
            filas = sorted(self._filtrar(modelo, args[0]), key=lambda f: f['id'])[:kwargs['limit']]
            return [{k: f.get(k) for k in ['id'] + kwargs['fields']} for f in filas]
        if metodo == 'search_count':
            return len(self._filtrar(modelo, args[0]))
        if metodo == 'fields_get':
            return {'company_id': {}, 'picking_code': {'store': False}}
        raise NotImplementedError(metodo)

    def campos(self, modelo, atributos=None):
        return self.llamar(modelo, 'fields_get', [], {})

    def contar(self, modelo, dominio, contexto=None):
        return self.llamar(modelo, 'search_count', [dominio], {})

    def leer_paginado(self, modelo, dominio, campos, pagina=2000, desde_id=0, contexto=None):
        ultimo = desde_id
        while True:
            filas = self.llamar(modelo, 'search_read', [list(dominio) + [('id', '>', ultimo)]],
                                {'fields': list(campos), 'limit': min(pagina, MAX_FILAS)})
            if not filas:
                return
            yield filas
            ultimo = filas[-1]['id']
            if len(filas) < pagina:
                return
