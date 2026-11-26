# -*- coding: utf-8 -*-
"""Pruebas de la compactación de la zona 0 con datos a mano (sin Odoo ni copia)."""
import collections
import datetime
import tempfile
import unittest
from pathlib import Path

from redistrib import compactar as C


def linea(mc, talla, uds, familia='JA', zona='0', lt_ud=2.0):
    modelo = mc.split('-')[0]
    return {'mc': mc, 'modelo': modelo, 'talla': talla, 'familia': familia, 'uds': uds, 'litros': uds * lt_ud,
            'zona': zona, 'fuente': 'MASTER', 'lt_ud': lt_ud}


def datos(cajas, lineas=None):
    return {'cajas': cajas, 'lineas': collections.Counter(lineas or {}), 'uds_salida': collections.Counter(),
            'fecha': datetime.datetime(2026, 11, 23, 17, 7), 'metros': lambda l, p: l * 10 + p}


class Clasificar(unittest.TestCase):

    def test_abc_por_lineas_y_tamano(self):
        d = datos({
            1: {'hueco': (1, 1, 1), 'nombre': 'KO_1', 'lineas': [linea('M1-NEGRO', 'L', 50, lt_ud=1.0)]},
            2: {'hueco': (1, 2, 1), 'nombre': 'KO_2', 'lineas': [linea('M2-ROJO', 'M', 10, lt_ud=8.0)]},
            3: {'hueco': (1, 3, 1), 'nombre': 'KO_3', 'lineas': [linea('M3-AZUL', 'S', 5)]},
            4: {'hueco': (1, 4, 1), 'nombre': 'KO_4', 'lineas': [linea('Z1-GRIS', 'S', 5, zona='Z')]},
        }, {'M1-NEGRO': 80, 'M2-ROJO': 15, 'M3-AZUL': 0, 'Z1-GRIS': 99})
        m = C.clasificar(d)
        self.assertNotIn('Z1-GRIS', m)                          # solo la zona 0
        # 80 de 95 líneas = 84 % → A (es el primero); con M2 se llega al 100 %, que pasa del 95 % → C
        self.assertEqual((m['M1-NEGRO']['abc'], m['M2-ROJO']['abc'], m['M3-AZUL']['abc']), ('A', 'C', 'sin salidas'))
        self.assertEqual(m['M1-NEGRO']['tamano'], 'pequeño')    # 84 uds por caja
        self.assertEqual(m['M2-ROJO']['tamano'], 'grande')      # 10 uds por caja

    def test_resto_de_talla(self):
        # 50 de la L y 2 de la XS: la caja de las XS es resto; la de las L, no
        d = datos({
            1: {'hueco': (1, 1, 1), 'nombre': 'KO_1', 'lineas': [linea('M1-NEGRO', 'L', 50)]},
            2: {'hueco': (1, 2, 1), 'nombre': 'KO_2', 'lineas': [linea('M1-NEGRO', 'XS', 2)]},
        })
        m = C.clasificar(d)
        r = C.ReglasCompactar()
        self.assertTrue(C._es_resto(d['cajas'][2], m, r))
        self.assertFalse(C._es_resto(d['cajas'][1], m, r))


class TallasPorAltura(unittest.TestCase):

    def test_tallas_por_lineas_y_restos_arriba(self):
        cajas = {i: {'hueco': (50, i, 1), 'nombre': 'KO_%d' % i, 'lineas': [linea('M1-NEGRO', t, u)]}
                 for i, (t, u) in enumerate([('L', 40), ('M', 40), ('XL', 30), ('S', 20), ('XXL', 15), ('XS', 1)], 1)}
        d = datos(cajas, {'M1-NEGRO': 100})
        d['lineas_talla'] = collections.Counter({('M1-NEGRO', 'L'): 30, ('M1-NEGRO', 'M'): 25, ('M1-NEGRO', 'XL'): 20,
                                                 ('M1-NEGRO', 'S'): 15, ('M1-NEGRO', 'XXL'): 9, ('M1-NEGRO', 'XS'): 1})
        a = C.tallas_por_altura(d, C.clasificar(d))['M1-NEGRO']
        # 146 uds: L (40) → 27 %; con M (40) → 55 %, más cerca de la mitad → C1; con XL → 75 %, más lejos → C2 y
        # todo lo que sigue a C2; XS (1 ud) es resto de talla → C3
        self.assertEqual(a['abajo'], ['L', 'M'])
        self.assertEqual(a['arriba'], ['XL', 'S', 'XXL'])
        self.assertEqual(a['restos'], ['XS'])
        self.assertEqual(a['uds']['abajo'], 80)

    def test_sin_salidas_por_stock(self):
        d = datos({1: {'hueco': (50, 1, 1), 'nombre': 'KO_1', 'lineas': [linea('M2-AZUL', '32', 5), linea('M2-AZUL', '34', 50)]}})
        d['lineas_talla'] = collections.Counter()
        a = C.tallas_por_altura(d, C.clasificar(d))['M2-AZUL']
        self.assertEqual(a['abajo'], ['34'])


class KoMixta(unittest.TestCase):

    def test_sku_con_3_cajas_lleva_ko_propia(self):
        # 42 L por ud → 2 uds por caja; L con 6 uds = 3 cajas → KO propia; XS y S (1 ud) comparten KO
        cajas = {1: {'hueco': (50, 1, 1), 'nombre': 'KO_1', 'lineas': [linea('M1-NEGRO', 'L', 2, lt_ud=42)]},
                 2: {'hueco': (50, 1, 1), 'nombre': 'KO_2', 'lineas': [linea('M1-NEGRO', 'L', 2, lt_ud=42)]},
                 3: {'hueco': (50, 1, 1), 'nombre': 'KO_3', 'lineas': [linea('M1-NEGRO', 'L', 2, lt_ud=42)]},
                 4: {'hueco': (50, 1, 1), 'nombre': 'KO_4', 'lineas': [linea('M1-NEGRO', 'XS', 1, lt_ud=42)]},
                 5: {'hueco': (50, 1, 1), 'nombre': 'KO_5', 'lineas': [linea('M1-NEGRO', 'S', 1, lt_ud=42)]}}
        d = datos(cajas)
        propios, por_lineal = C.ko_mixta(d, C.clasificar(d))
        self.assertEqual(propios, {('M1-NEGRO', 'L')})
        self.assertEqual(por_lineal[50], [5, 2])          # 5 KO hoy → 2 (la de la L y la de XS + S)


class Compactar(unittest.TestCase):

    def test_vacia_el_menos_lleno_y_no_mezcla_el_mismo_articulo(self):
        d = datos({
            1: {'hueco': (5, 1, 1), 'nombre': 'KO_1', 'lineas': [linea('M1-NEGRO', 'L', 10)]},
            2: {'hueco': (5, 2, 1), 'nombre': 'KO_2', 'lineas': [linea('M1-ROJO', 'L', 10)]},     # mismo modelo
            3: {'hueco': (5, 3, 1), 'nombre': 'KO_3', 'lineas': [linea('M9-VERDE', 'L', 10, familia='PT')]},
        }, {'M1-NEGRO': 5, 'M1-ROJO': 5, 'M9-VERDE': 5})
        m = C.clasificar(d)
        pasos, res = C.compactar(d, m)
        self.assertGreaterEqual(res['huecos_liberados'], 1)
        r = C.ReglasCompactar()
        ocupado = collections.Counter()
        dentro = collections.defaultdict(set)
        movidas = {p['clave']: p['destino'] for p in pasos}
        for k, c in d['cajas'].items():
            h = movidas.get(k, c['hueco'])
            ocupado[h] += C.ocupa(c, r)
            dentro[h] |= {x['mc'] for x in c['lineas']}
        for h, mcs in dentro.items():
            self.assertFalse({'M1-NEGRO', 'M1-ROJO'} <= mcs, h)         # dos colores del mismo modelo, nunca juntos
        self.assertTrue(all(v <= r.litros_hueco * r.llenado + 1e-6 for v in ocupado.values()))

    def test_hueco_con_z_no_se_vacia(self):
        d = datos({
            1: {'hueco': (5, 1, 1), 'nombre': 'KO_1', 'lineas': [linea('M1-NEGRO', 'L', 10), linea('Z1-GRIS', 'S', 1, zona='Z')]},
            2: {'hueco': (5, 2, 1), 'nombre': 'KO_2', 'lineas': [linea('M9-VERDE', 'L', 10, familia='PT')]},
        })
        pasos, _ = C.compactar(d, C.clasificar(d))
        self.assertNotIn((5, 1, 1), {p['hueco_origen'] for p in pasos})

    def test_cajas_a_cero(self):
        # L67 P16 C1 (foto del 26/11): KO_1 con stock, KO_2 sin quants, KO_3 con quant a 0, KO_4 negativa;
        # L67 P17 C1 solo con una caja a 0; KO_9 archivada y KO_8 fuera de la nave no cuentan
        import sqlite3
        bd = sqlite3.connect(':memory:')
        bd.execute('CREATE TABLE ubicaciones (id, tipo, lineal, posicion, nivel, en_nave, hueco_id, nombre, activa)')
        bd.execute('CREATE TABLE stock (ubicacion_id, cantidad)')
        bd.executemany('INSERT INTO ubicaciones VALUES (?,?,?,?,?,?,?,?,?)', [
            (100, 'hueco', 67, 16, 1, 1, None, 'L67 P16 C1', 1), (101, 'hueco', 67, 17, 1, 1, None, 'L67 P17 C1', 1),
            (1, 'contenedor', None, None, None, 1, 100, 'KO_1', 1), (2, 'contenedor', None, None, None, 1, 100, 'KO_2', 1),
            (3, 'contenedor', None, None, None, 1, 100, 'KO_3', 1), (4, 'contenedor', None, None, None, 1, 100, 'KO_4', 1),
            (5, 'contenedor', None, None, None, 1, 101, 'KO_5', 1), (8, 'contenedor', None, None, None, 0, 100, 'KO_8', 1),
            (9, 'contenedor', None, None, None, 1, 100, 'KO_9', 0)])
        bd.executemany('INSERT INTO stock VALUES (?,?)', [(1, 10), (3, 0), (4, -1)])
        d = datos({1: {'hueco': (67, 16, 1), 'nombre': 'KO_1', 'lineas': [linea('M1-NEGRO', 'L', 10)]}})
        original = C.mapa_json.abrir_copia
        C.mapa_json.abrir_copia = lambda ruta: bd
        try:
            v = C.cajas_a_cero('copia', d)
        finally:
            C.mapa_json.abrir_copia = original
        self.assertEqual([(x['caja'], x['zona'], x['negativo']) for x in v],
                         [('KO_2', '0', False), ('KO_3', '0', False), ('KO_4', '0', True), ('KO_5', 'solo cajas a 0', False)])
        self.assertEqual(v[0]['cajas_a_cero_hueco'], 3)
        self.assertEqual(v[0]['cajas_con_stock'], 1)
        res = C.resumen_cajas_a_cero(v)
        self.assertEqual((res['cajas_a_cero_zona0'], res['huecos_solo_a_cero_desde_l44'], res['cajas_stock_negativo']),
                         (2, 1, 1))

    def test_excel_no_sobrescribe(self):
        d = datos({1: {'hueco': (5, 1, 1), 'nombre': 'KO_1', 'lineas': [linea('M1-NEGRO', 'L', 10)]},
                   2: {'hueco': (5, 2, 1), 'nombre': 'KO_2', 'lineas': [linea('M9-VERDE', 'L', 10, familia='PT')]}})
        m = C.clasificar(d)
        pasos, res = C.compactar(d, m)
        ruta = Path(tempfile.mkdtemp()) / 'c.xlsx'
        C.exportar_excel(ruta, m, pasos, res)
        self.assertTrue(ruta.exists())
        with self.assertRaises(FileExistsError):
            C.exportar_excel(ruta, m, pasos, res)
