# -*- coding: utf-8 -*-
# =============================================================================
# v1.8.0: motor/aprender.py. Zonas que aprenden: que entra (tipo de dia) y ritmo real.
# Solo texto y propuestas: el reparto tiene que ser el mismo que sin ello.
# =============================================================================
import os
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
sys.path.insert(0, AQUI)

from motor import aprender  # noqa: E402
from motor import modelo  # noqa: E402
from motor import v12f  # noqa: E402
import sintetico  # noqa: E402

# 9 zonas-dia reales (19, 24 y 25/11, D1-D3): lecturas, lineales por OUT, segundos-persona (lecturas de la PDA)
REALES = [(604, 431, 34449), (835, 549, 41818), (764, 496, 41040), (716, 473, 37894), (929, 584, 45633),
          (914, 598, 45591), (601, 425, 29395), (874, 583, 41199), (857, 554, 41742)]


def con_implantacion(datos, uds=6):
    """Mete en cada OUT valida una linea del mismo articulo nuevo (va a todas las tiendas), en L51."""
    n = 900000
    for o in datos['outs']:
        n += 1
        o['lineas'].append({
            'id': n, 'move_id': n * 10, 'qty': float(uds), 'qty_done': 0.0, 'location_id': 777,
            'location_complete_name': 'EFFEC/Stock/NAVE2/27499 - L51 P07 C2', 'location_name': '27499 - L51 P07 C2',
            'parent_id': 4000, 'parent_complete_name': 'EFFEC/Stock/NAVE2', 'product_id': 555555,
            'default_code': '2621SU60-000003-L', 'volume': 0.002})
    return datos


class TestTipoDeDia(unittest.TestCase):

    def test_reposicion(self):
        rep = v12f.repartir(sintetico.generar(21, n_pedidos=90), {'MODO': 'DIAGNOSTICO'})
        cls = aprender.clasificar(rep)
        self.assertEqual(cls['tipo'], 'reposicion')
        lineas = aprender.lineas_clasificar(cls)
        self.assertTrue(lineas[0].startswith('TIPO DE DIA: REPOSICION'))

    def test_implantacion_y_reparto_igual(self):
        datos = con_implantacion(sintetico.generar(21, n_pedidos=90), uds=40)
        rep = v12f.repartir(datos, {'MODO': 'DIAGNOSTICO'})
        cls = aprender.clasificar(rep)
        self.assertIn(cls['tipo'], ('mixto', 'implantacion'))
        self.assertGreater(cls['pct_casi'], 5)
        self.assertEqual(cls['articulos'][0][0], '2621SU60-000003')
        self.assertEqual(cls['articulos'][0][3], 51)
        texto = '\n'.join(aprender.lineas_clasificar(cls))
        self.assertIn('2621SU60-000003', texto)
        self.assertIn('L51', texto)
        for l in aprender.lineas_clasificar(cls):
            self.assertTrue(l.startswith('TIPO DE DIA:'))       # el correo las busca asi
        # clasificar no toca el reparto
        otra = v12f.repartir(datos, {'MODO': 'DIAGNOSTICO'})
        self.assertEqual(rep.zona_fin, otra.zona_fin)

    def test_codigo_sin_referencia(self):
        # 26/11: 2621SU60 y 2621PL50 sin referencia interna; el codigo es el nombre
        self.assertEqual(aprender.codigo_de_nombre('2621SU60-000003-L'), '2621SU60-000003-L')
        self.assertEqual(aprender.codigo_de_nombre('[2621SU60-000003-L] Sudadera'), '2621SU60-000003-L')
        self.assertEqual(aprender.codigo_de_nombre(''), '')
        datos = con_implantacion(sintetico.generar(21, n_pedidos=90), uds=40)
        for o in datos['outs']:
            for ml in o['lineas']:
                if ml['product_id'] == 555555:
                    ml['default_code'] = False
                    ml['nombre'] = '2621SU60-000003-L'
        cls = aprender.clasificar(v12f.repartir(datos, {'MODO': 'DIAGNOSTICO'}))
        self.assertEqual(cls['articulos'][0][0], '2621SU60-000003')

    def test_modelo_de(self):
        self.assertEqual(aprender.modelo_de('2621SU60-000003-XL'), '2621SU60-000003')
        self.assertEqual(aprender.modelo_de('SINGUION'), 'SINGUION')


class TestRitmo(unittest.TestCase):

    def test_segundos_persona(self):
        # A lee en D1 cada 60 s; una pausa de 20 min no cuenta; lo que lee fuera de zonas ('') no se devuelve
        ls = [(0, 'A', 'D1'), (60, 'A', 'D1'), (120, 'A', 'D1'), (1320, 'A', 'D1'), (1380, 'A', ''),
              (0, 'B', 'D2'), (30, 'B', 'D2')]
        self.assertEqual(aprender.segundos_persona(ls), {'D1': 120.0, 'D2': 30.0})

    def test_trabajo_zona(self):
        outs = {1: [(10, 100, 51, 2.0), (10, 100, 51, 1.0), (11, 101, 52, 1.0)],
                2: [(10, 100, 51, 1.0), (12, 102, 0, 1.0), (13, 103, 60, 0.0)]}
        t = aprender.trabajo_zona(outs)
        self.assertEqual(t['lecturas'], 4)          # (10,100) y (11,101) en la 1; (10,100) y (12,102) en la 2
        self.assertEqual(t['lineales_out'], 3)      # 51 y 52 en la 1; 51 en la 2
        self.assertEqual(t['uds'], 6.0)
        self.assertEqual(t['anchura'], 2)
        self.assertEqual((t['lineal_min'], t['lineal_max']), (51, 52))

    def test_ajustar_exacto(self):
        filas = [(l, k, 30 * l + 50 * k) for l, k in ((100, 50), (200, 40), (150, 120), (300, 90), (80, 70), (60, 10))]
        aj = aprender.ajustar(filas)
        self.assertAlmostEqual(aj['seg_lectura'], 30, places=0)
        self.assertAlmostEqual(aj['seg_lineal'], 50, places=0)
        self.assertLess(aj['error_pct'], 0.5)
        self.assertIsNone(aprender.ajustar(filas[:5]))

    def test_proponer_con_los_reales(self):
        prop = aprender.proponer(REALES, 52, 21)
        # andar pesa mas de lo que dice el modelo de ahora; leer, menos
        self.assertGreater(prop['seg_lineal_prop'], 21)
        self.assertLess(prop['seg_lectura_prop'], 52)
        self.assertLess(prop['error_prop'], prop['error_ahora'])
        # mismo trabajo total que ahora (la hora de fin no salta)
        ahora = sum(52 * l + 21 * k for l, k, s in REALES)
        nuevo = sum(prop['seg_lectura_prop'] * l + prop['seg_lineal_prop'] * k for l, k, s in REALES)
        self.assertLess(abs(nuevo - ahora) / ahora, 0.02)

    def test_ritmo_por_contexto(self):
        p = modelo.parametros({}, {'seg_lectura': 31, 'seg_lineal': 53})
        self.assertEqual((p['SEG_LECTURA'], p['SEG_LINEAL']), (31.0, 53.0))
        p = modelo.parametros({}, {})
        self.assertEqual((p['SEG_LECTURA'], p['SEG_LINEAL']), (52, 21))


if __name__ == '__main__':
    unittest.main()
