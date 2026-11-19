# -*- coding: utf-8 -*-
# =============================================================================
# v1.5.0: motor/tiempos.py. Aviso de hora de fin (A) y previsto contra real con las lecturas de la PDA (B).
# El aviso es solo texto: el reparto tiene que ser el mismo que sin el.
# =============================================================================
import os
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
sys.path.insert(0, AQUI)

from motor import modelo  # noqa: E402
from motor import tiempos  # noqa: E402
from motor import v12f  # noqa: E402
import sintetico  # noqa: E402


def reparto_falso(seg_z, pers, ini_min=360):
    rep = modelo.Reparto()
    rep.estado = 'listo'
    rep.orden_zonas = list(seg_z.keys())
    rep.seg_z = dict(seg_z)
    rep.pers = dict(pers)
    rep.ini_min = ini_min
    rep.fin = max(seg_z.values())
    return rep


class TestAviso(unittest.TestCase):

    def test_personas_necesarias(self):
        # D1: 4 personas x 300 min = 1200 min de trabajo; en 360 min hacen falta 4 (3,33 -> 4)
        rep = reparto_falso({'D1': 300 * 60.0, 'D2': 400 * 60.0, 'MU2': 30 * 60.0}, {'D1': 4, 'D2': 3, 'MU2': 1})
        total, por_zona = tiempos.personas_necesarias(rep, 12 * 60)
        self.assertEqual(por_zona, {'D1': 4, 'D2': 4, 'MU2': 1})
        self.assertEqual(total, 9)

    def test_lineas_aviso_a_tiempo_y_tarde(self):
        rep = reparto_falso({'D1': 200 * 60.0}, {'D1': 4})
        a_tiempo = tiempos.lineas_aviso(rep, 12 * 60, 4)
        self.assertEqual(len(a_tiempo), 1)
        self.assertIn('9:20', a_tiempo[0])
        self.assertIn('antes de las 12:00', a_tiempo[0])
        rep = reparto_falso({'D1': 480 * 60.0}, {'D1': 4})
        tarde = tiempos.lineas_aviso(rep, 12 * 60, 4)
        self.assertEqual(len(tarde), 2)
        self.assertIn('14:00, 120 min DESPUES', tarde[0])
        self.assertIn('harian falta 6 personas (D1 6), 2 mas', tarde[1])
        for l in tarde:
            self.assertTrue(l.startswith('HORA DE FIN:'))      # el correo las busca asi

    def test_sin_reparto_sin_aviso(self):
        rep = reparto_falso({'D1': 100.0}, {'D1': 1})
        rep.estado = 'pocas_uds'
        self.assertEqual(tiempos.lineas_aviso(rep, 720, 12), [])
        rep.estado = 'listo'
        rep.pers = {}
        self.assertEqual(tiempos.personas_necesarias(rep, 720), (None, {}))

    def test_con_el_motor_de_verdad(self):
        for semilla in (20, 21):
            datos = sintetico.generar(semilla, n_pedidos=90)
            rep = v12f.repartir(datos, {'MODO': 'DIAGNOSTICO'})
            with self.subTest(semilla=semilla):
                self.assertEqual(rep.estado, 'listo')
                total, por_zona = tiempos.personas_necesarias(rep, 720)
                self.assertEqual(set(por_zona), set(rep.orden_zonas))
                # Con las personas que dice, cada zona cabe en el tiempo disponible
                for zn in rep.orden_zonas:
                    trabajo = rep.seg_z[zn] * rep.pers[zn]
                    self.assertLessEqual(trabajo / por_zona[zn], (720 - rep.ini_min) * 60.0 + 1e-6)
                prev = tiempos.prevision(rep)
                self.assertEqual(set(prev['zonas']), set(rep.orden_zonas))
                self.assertAlmostEqual(prev['fin'], rep.ini_min + rep.fin / 60.0, places=0)


class TestReal(unittest.TestCase):

    def test_resumen_lecturas(self):
        lect = [(360 + i, 1.0, 'A' if i % 2 else 'B') for i in range(100)]
        lect.append((600, 0.0, 'C'))            # cantidad 0: no cuenta
        r = tiempos.resumen_lecturas(lect)
        self.assertEqual(r['uds'], 100)
        self.assertEqual(r['inicio'], 360)
        self.assertEqual(r['cola'], 360 + 94)    # la lectura 95 de 100
        self.assertEqual(r['fin'], 459)
        self.assertEqual(r['personas'], 2)
        self.assertIsNone(tiempos.resumen_lecturas([]))

    def test_comparar(self):
        previsto = {'inicio': 360, 'fin': 600, 'zonas': {'D1': {'min': 240, 'pers': 4}, 'MU2': {'min': 60, 'pers': 1}}}
        real = {'D1': {'uds': 500, 'inicio': 480, 'cola': 700, 'fin': 750, 'personas': 4},
                'MU2': None}
        lineas, res = tiempos.comparar(previsto, real, 5)
        self.assertEqual(res['inicio'], 480)
        self.assertEqual(res['fin'], 750)
        self.assertEqual(res['desvio'], 30)       # 270 min reales contra 240 previstos
        texto = '\n'.join(lineas)
        self.assertIn('MU2', texto)
        self.assertIn('+30 min', texto)
        lineas, res = tiempos.comparar(None, real, 5)
        self.assertIsNone(res['desvio'])
        self.assertIn('Sin prevision guardada', '\n'.join(lineas))
        lineas, res = tiempos.comparar(previsto, {}, 0)
        self.assertEqual(res, {})


if __name__ == '__main__':
    unittest.main()
