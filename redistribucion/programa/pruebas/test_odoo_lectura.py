# -*- coding: utf-8 -*-
"""Pruebas de la solo lectura. No se conectan a nada: el proxy de XML-RPC es falso y apunta lo que le llega.

Uso (desde redistribucion/programa):  python -m unittest discover -s pruebas -v
"""
import re
import unittest
import xmlrpc.client
from pathlib import Path

from redistrib import odoo_lectura
from redistrib.odoo_lectura import ClienteLectura, ErrorOdoo, LecturaProhibida

CLAVE = 'clave-secreta-de-prueba-123'


class ProxyFalso:
    """Hace de /common y /object. Apunta cada llamada en `registro` (compartido)."""

    def __init__(self, punto, registro, fallo=None):
        self.punto, self.registro, self.fallo = punto, registro, fallo

    def __getattr__(self, metodo):
        def llamada(*args):
            self.registro.append((self.punto, metodo, args))
            if self.fallo:
                raise self.fallo
            if metodo == 'version':
                return {'server_version': '13.0+e'}
            if metodo == 'authenticate':
                return 7
            m = args[4]
            if m == 'search_count':
                return 42
            if m == 'search_read':
                pagina, dominio = args[6]['limit'], args[5][0]
                desde = [c for c in dominio if c[0] == 'id'][0][2]
                return [{'id': i} for i in range(desde + 1, min(desde + pagina, 5) + 1)]
            return []
        return llamada


def cliente(registro, fallo=None, **kw):
    reloj = iter(range(0, 100000)).__next__
    return ClienteLectura('https://odoo.ejemplo', 'BD', 'usuario', CLAVE,
                          fabrica_proxy=lambda url: ProxyFalso(url.rsplit('/', 1)[1], registro, fallo),
                          reloj=lambda: float(reloj()), dormir=lambda s: None, **kw)


class ListaBlanca(unittest.TestCase):

    def test_prohibidos_no_envian_nada(self):
        prohibidos = ['write', 'create', 'unlink', 'action_done', 'action_assign', 'button_validate', 'copy',
                      'metodo_inventado', 'Write', 'search ', 'search_read;write', 'name_create', 'toggle_active',
                      'sudo', 'execute_kw', '', None, 3]
        for metodo in prohibidos:
            registro = []
            c = cliente(registro)
            with self.subTest(metodo=metodo):
                with self.assertRaises(LecturaProhibida):
                    c.llamar('stock.location', metodo, [[1]], {'context': {}})
                self.assertEqual(registro, [], 'se envió algo con %r' % (metodo,))
                self.assertEqual(c.peticiones, 0)

    def test_permitidos_pasan(self):
        registro = []
        c = cliente(registro)
        self.assertEqual(c.contar('stock.quant', []), 42)
        c.campos('stock.quant')
        c.agrupar('stock.quant', [], ['quantity'], ['location_id'])
        c.llamar('stock.quant', 'search', [[]], {'limit': 10})
        c.llamar('stock.quant', 'read', [[1, 2], ['quantity']])
        metodos = [r[2][4] for r in registro if r[1] == 'execute_kw']
        self.assertEqual(metodos, ['search_count', 'fields_get', 'read_group', 'search', 'read'])
        self.assertEqual(set(odoo_lectura.METODOS_PERMITIDOS),
                         {'search', 'search_read', 'read', 'search_count', 'read_group', 'fields_get'})

    def test_no_hay_atajos_de_escritura(self):
        c = cliente([])
        for nombre in ('write', 'create', 'unlink', 'execute_kw', 'execute'):
            self.assertFalse(hasattr(c, nombre), nombre)
        publicos = [n for n in dir(c) if not n.startswith('_')]
        for n in publicos:
            self.assertNotIsInstance(getattr(c, n), (xmlrpc.client.ServerProxy, ProxyFalso), n)

    def test_modelo_raro_no_pasa(self):
        registro = []
        with self.assertRaises(LecturaProhibida):
            cliente(registro).llamar('stock.quant; drop', 'search_count', [[]])
        self.assertEqual(registro, [])


class SinCargarElServidor(unittest.TestCase):

    def test_limites(self):
        registro = []
        c = cliente(registro)
        for args, kwargs in (([[]], {'fields': ['id']}),                      # search_read sin limit
                             ([[]], {'fields': ['id'], 'limit': 50000})):      # demasiadas filas
            with self.assertRaises(LecturaProhibida):
                c.llamar('stock.quant', 'search_read', args, kwargs)
        with self.assertRaises(LecturaProhibida):
            c.llamar('stock.quant', 'search_read', [[]], {'limit': 10})       # sin campos
        with self.assertRaises(LecturaProhibida):
            c.llamar('stock.quant', 'read', [list(range(6000)), ['id']])
        self.assertEqual(registro, [])

    def test_compania_8_siempre(self):
        registro = []
        cliente(registro).contar('stock.quant', [], {'allowed_company_ids': [1, 8], 'active_test': False})
        kwargs = registro[-1][2][6]
        self.assertEqual(kwargs['context']['allowed_company_ids'], [8])
        self.assertEqual(kwargs['context']['force_company'], 8)
        self.assertFalse(kwargs['context']['active_test'])

    def test_pausa_entre_peticiones(self):
        esperas = []
        momentos = iter([0.0, 0.0, 0.1, 0.1, 0.2, 0.2, 0.3, 0.3])
        c = ClienteLectura('https://odoo.ejemplo', 'BD', 'u', CLAVE, pausa=0.5,
                           fabrica_proxy=lambda url: ProxyFalso(url.rsplit('/', 1)[1], []),
                           reloj=lambda: next(momentos), dormir=esperas.append)
        c.version()
        c.version()
        self.assertEqual(len(esperas), 1)
        self.assertAlmostEqual(esperas[0], 0.5 - 0.1)

    def test_pausa_minima(self):
        self.assertEqual(cliente([], pausa=0).pausa, odoo_lectura.PAUSA_MINIMA)

    def test_paginado_por_id(self):
        registro = []
        paginas = list(cliente(registro).leer_paginado('stock.quant', [], ['id'], pagina=2))
        self.assertEqual([[f['id'] for f in p] for p in paginas], [[1, 2], [3, 4], [5]])
        limites = [r[2][6]['limit'] for r in registro if r[1] == 'execute_kw']
        self.assertTrue(all(lim == 2 for lim in limites))

    def test_paginado_nunca_pasa_de_5000(self):
        registro = []
        list(cliente(registro).leer_paginado('stock.quant', [], ['id'], pagina=999999))
        self.assertEqual(registro[-1][2][6]['limit'], odoo_lectura.MAX_FILAS)


class LaClaveNoSale(unittest.TestCase):

    def test_repr(self):
        c = cliente([])
        self.assertNotIn(CLAVE, repr(c))
        self.assertNotIn(CLAVE, str(c))
        self.assertNotIn(CLAVE, str(vars(c).get('usuario')))

    def test_errores_limpios(self):
        fallos = [xmlrpc.client.Fault(1, 'AccessDenied con %s dentro' % CLAVE),
                  xmlrpc.client.ProtocolError('https://odoo.ejemplo/%s' % CLAVE, 500, 'x', {}),
                  ConnectionRefusedError('rechazada %s' % CLAVE)]
        for fallo in fallos:
            with self.subTest(fallo=type(fallo).__name__):
                with self.assertRaises(ErrorOdoo) as ctx:
                    cliente([], fallo=fallo).contar('stock.quant', [])
                self.assertNotIn(CLAVE, str(ctx.exception))
                self.assertIsNone(ctx.exception.__cause__)
                self.assertTrue(ctx.exception.__suppress_context__)

    def test_url_con_clave_o_sin_https(self):
        for url in ('https://u:%s@odoo.ejemplo' % CLAVE, 'http://odoo.ejemplo', 'ftp://odoo.ejemplo'):
            with self.assertRaises(ValueError):
                ClienteLectura(url, 'BD', 'u', CLAVE)
        ClienteLectura('http://127.0.0.1:8069', 'BD', 'u', CLAVE)     # local, para pruebas


class SoloUnFicheroHablaConOdoo(unittest.TestCase):

    def test_nadie_mas_importa_xmlrpc(self):
        raiz = Path(__file__).resolve().parent.parent
        permitidos = {raiz / 'redistrib' / 'odoo_lectura.py', Path(__file__).resolve()}
        patron = re.compile(r'^\s*(import\s+xmlrpc|from\s+xmlrpc)|__import__\(\s*[\'"]xmlrpc|import_module\(\s*[\'"]xmlrpc',
                            re.M)
        culpables = [str(f.relative_to(raiz)) for f in raiz.rglob('*.py')
                     if f.resolve() not in permitidos and patron.search(f.read_text(encoding='utf-8'))]
        self.assertEqual(culpables, [])


if __name__ == '__main__':
    unittest.main()
