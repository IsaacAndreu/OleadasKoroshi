# -*- coding: utf-8 -*-
"""Pruebas del escenario de la fase 2 (borrador) con la copia inventada (sin Odoo)."""
import collections
import datetime
import tempfile
import unittest
from pathlib import Path

from redistrib import escenario as S
from pruebas.test_descarga import descargar

V2 = Path(__file__).resolve().parents[2] / 'prototipo-mapa_2026-11-23_v2'


class Piezas(unittest.TestCase):

    def test_rango(self):
        self.assertEqual(S._rango({1, 2, 3, 7, 9, 10}), 'L01-L03, L07, L09-L10')
        self.assertEqual(S._rango(set()), '')

    def test_zona_mc(self):
        self.assertEqual(S.zona_mc({'zona': collections.Counter({'0': 5, 'Z': 5})}), '0')    # empate: 0
        self.assertEqual(S.zona_mc({'zona': collections.Counter({'0': 4, 'Z': 6})}), 'Z')

    def test_cajas_necesarias(self):
        r = S.Reglas()
        z = {'zona': collections.Counter({'Z': 1}), 'ocupa_hoy': 4 * 84.0, 'litros': 50.0}
        self.assertEqual(S.cajas_necesarias(z, r), 84.0)                    # 4 cajas medio vacías → 1
        self.assertEqual(S.cajas_necesarias(z, S.Reglas(juntar_z=False)), 4 * 84.0)
        cero = {'zona': collections.Counter({'0': 1}), 'ocupa_hoy': 10.0, 'litros': 10.0}
        self.assertEqual(S.cajas_necesarias(cero, r), 84.0)                 # mínimo una caja entera


class Simular(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        d = Path(tempfile.mkdtemp())
        ruta, *_ = descargar(d, desde=datetime.date(2026, 10, 1))
        cls.mc, cls.huecos, metros = S.cargar(ruta, V2)
        cls.metros = staticmethod(metros)      # si no, al leerla desde self sería un método

    def test_cargar(self):
        self.assertIn('2621JA67-NEGRO', self.mc)
        self.assertTrue(self.huecos)

    def test_simular_no_pasa_de_la_capacidad(self):
        r = S.Reglas()
        res, asignado = S.simular(self.mc, self.huecos, self.metros, r)
        lleno = collections.Counter()
        for hs in asignado.values():
            for h, lt in hs.items():
                lleno[h] += lt
        self.assertTrue(all(lt <= r.litros_hueco * r.llenado + 1e-6 for lt in lleno.values()))
        for c, hs in asignado.items():                         # la zona 0 solo en sus niveles
            if S.zona_mc(self.mc[c]) == '0':
                self.assertTrue(all(h[2] in r.niveles_0 for h in hs), c)
        self.assertEqual(sum(res['modelos_color'].values()), len(self.mc))
        self.assertLessEqual(res['uds_a_mover']['minimo'], res['uds_a_mover']['rehacer_todo'])
