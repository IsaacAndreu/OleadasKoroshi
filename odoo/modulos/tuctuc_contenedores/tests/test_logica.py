# -*- coding: utf-8 -*-
# Pruebas sin Odoo: python odoo/modulos/tuctuc_contenedores/tests/test_logica.py
import os
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
import logica  # noqa: E402


class TestRepartir(unittest.TestCase):

    def test_solo_la_diferencia(self):
        # R1: línea de 5 reservada y hay 4: pasa 1, no 5
        self.assertEqual(logica.repartir([5], 1), [1])

    def test_ko_241026_115(self):
        # 2 uds reservadas que no están (de 2621PT01-000014-34): «Cambiar» a 0 de ese artículo
        self.assertEqual(logica.repartir([2], 2), [2])

    def test_pequenas_primero(self):
        # la línea de 1 pasa entera; la de 5 no se toca
        self.assertEqual(logica.repartir([1, 5], 1), [1, 0])

    def test_reparto_en_dos(self):
        self.assertEqual(logica.repartir([1, 3], 2), [1, 1])

    def test_nada_que_quitar(self):
        self.assertEqual(logica.repartir([2, 3], 0), [0, 0])

    def test_poner_a_cero_todas_enteras(self):
        self.assertEqual(logica.repartir([2, 3], 5), [2, 3])
        self.assertEqual(logica.repartir([2, 3], 99), [2, 3])

    def test_nunca_mas_de_lo_que_sobra(self):
        r = logica.repartir([0.5, 1.5, 4], 1.7)
        self.assertAlmostEqual(sum(r), 1.7)
        self.assertTrue(all(q <= c for q, c in zip(r, [0.5, 1.5, 4])))

    def test_sin_lineas(self):
        self.assertEqual(logica.repartir([], 3), [])

    def test_linea_a_cero(self):
        self.assertEqual(logica.repartir([0, 2], 1), [0, 1])


class TestCambiarArticulo(unittest.TestCase):
    # v1.14.0 (R23): «Es otro»

    def test_mismo_modelo(self):
        # TUCTUC: el mismo modelo es la misma plantilla (ids)
        self.assertTrue(logica.mismo_modelo(41, 41))
        self.assertFalse(logica.mismo_modelo(41, 42))
        self.assertFalse(logica.mismo_modelo(False, False))

    def test_error_uds(self):
        self.assertEqual(logica.error_uds_cambio(3, 5, 500), '')
        self.assertEqual(logica.error_uds_cambio(5, 5, 500), '')
        self.assertIn('1 o más', logica.error_uds_cambio(0, 5, 500))
        self.assertIn('1 o más', logica.error_uds_cambio(None, 5, 500))
        self.assertIn('Solo hay 5', logica.error_uds_cambio(6, 5, 500))
        self.assertIn('Más de 500', logica.error_uds_cambio(501, 600, 500))

    def test_reservas_libres_no_tocan(self):
        # 5 uds, 2 reservadas: cambiar 3 deja 2 de A, que cubren las 2 reservadas
        self.assertEqual(logica.reservas_a_faltantes(3, 5, 2), 0)

    def test_reservas_que_no_caben(self):
        # 5 uds, 4 reservadas: cambiar 3 deja 2 de A: 2 reservadas pasan a Faltantes
        self.assertEqual(logica.reservas_a_faltantes(3, 5, 4), 2)
        # todas son B: todo lo reservado pasa
        self.assertEqual(logica.reservas_a_faltantes(5, 5, 4), 4)

    def test_sin_reservas(self):
        self.assertEqual(logica.reservas_a_faltantes(5, 5, 0), 0)


class TestRondaCajasCero(unittest.TestCase):
    """v1.16.0: retirar cajas a 0."""

    def test_rango(self):
        self.assertEqual(logica.rango_lineales('44-136'), (44, 136))
        self.assertEqual(logica.rango_lineales('L1 - L43'), (1, 43))
        self.assertEqual(logica.rango_lineales('136-44'), (44, 136))
        self.assertEqual(logica.rango_lineales(''), (1, 9999))       # TUCTUC: sin zona 0, todos
        self.assertEqual(logica.rango_lineales('todo'), (1, 9999))

    def test_lineal_de(self):
        self.assertEqual(logica.lineal_de('07828 - L67 P16 C1'), 67)
        self.assertEqual(logica.lineal_de('L200 P00 C1'), 200)
        self.assertIsNone(logica.lineal_de('MU-01 P00 C1'))
        self.assertIsNone(logica.lineal_de('KO_090726_030'))
        self.assertIsNone(logica.lineal_de(''))

    def test_orden_hueco(self):
        huecos = ['07828 - L67 P10 C1', '07828 - L67 P2 C2', '07828 - L67 P2 C1', '07828 - L66 P40 C1']
        self.assertEqual(sorted(huecos, key=logica.orden_hueco),
                         ['07828 - L66 P40 C1', '07828 - L67 P2 C1', '07828 - L67 P2 C2', '07828 - L67 P10 C1'])

    def test_clasificar(self):
        self.assertEqual(logica.clasificar(0, 0, 0, False), 'cero')
        self.assertEqual(logica.clasificar(0, 0, 0, True), 'abierta')
        self.assertEqual(logica.clasificar(2, 0, 0, False), 'stock')
        self.assertEqual(logica.clasificar(1, 1, 0, False), 'revisar')     # stock negativo
        self.assertEqual(logica.clasificar(1, 0, 1, True), 'revisar')      # reservado sin cantidad

    def test_ids_tarjetas(self):
        self.assertEqual(logica.ids_tarjetas('12, 34; 56'), {12, 34, 56})
        self.assertEqual(logica.ids_tarjetas(''), set())
        self.assertEqual(logica.ids_tarjetas(None), set())

    def test_con_prendas_pendiente(self):
        self.assertFalse(logica.con_prendas_pendiente(None, None))
        self.assertTrue(logica.con_prendas_pendiente(10, None))
        self.assertTrue(logica.con_prendas_pendiente(10, 5))        # marcada después del último cambio
        self.assertFalse(logica.con_prendas_pendiente(10, 12))      # ya se resolvió

    def test_repartir_encontrados(self):
        # KO_090726_045: 1 prenda y un faltante de 1 de esa caja: encontrado, sin ajuste
        self.assertEqual(logica.repartir_encontrados(1, [(7, 1)]), ([7], 0.0))
        # 3 prendas, faltantes de 1 y 1: los dos encontrados y 1 ud de ajuste +
        self.assertEqual(logica.repartir_encontrados(3, [(7, 1), (8, 1)]), ([7, 8], 1.0))
        # un faltante de 2 con 1 prenda: no se parte; ajuste + de 1
        self.assertEqual(logica.repartir_encontrados(1, [(7, 2)]), ([], 1.0))
        # el de 2 no cabe, el de 1 sí
        self.assertEqual(logica.repartir_encontrados(1, [(7, 2), (8, 1)]), ([8], 0.0))
        self.assertEqual(logica.repartir_encontrados(2, []), ([], 2.0))


def _col(cid, lineal, cajas, z=False, nombre=None, extra=0, cia=None, cias=None):
    """Columna de prueba: cajas = lista de modelo-color («A1-NEGRO»: modelo A1). TUCTUC: cia de sus cajas y cias en
    que existe la columna (None = todas)."""
    return {'id': cid, 'nombre': nombre or '07828 - L%d P%02d C1' % (lineal, cid), 'lineal': lineal, 'z': z,
            'extra': extra, 'cias': cias,
            'cajas': [{'id': cid * 100 + i, 'mc': mc, 'modelo': mc.split('-')[0], 'movible': True, 'cia': cia}
                      for i, mc in enumerate(cajas)]}


class TestCompactarFase1(unittest.TestCase):
    """v1.17.0: plan de la fase 1 (cajas enteras, 8 por columna)."""

    def test_mc_y_temporadas(self):
        self.assertEqual(logica.mc_de('5 POCKET SHORT', 'Taupe_42'), '5 POCKET SHORT · Taupe_42')
        self.assertEqual(logica.mc_de('ZEBRA BRIEF', ''), 'ZEBRA BRIEF')
        self.assertTrue(logica.en_temporadas('AW26-27', set()))          # vacío = todas
        self.assertTrue(logica.en_temporadas('aw26-27 ', {'AW26-27'}))
        self.assertFalse(logica.en_temporadas('SS26', {'AW26-27'}))

    def test_varias_companias(self):
        # la misma columna física existe en WH-OR (1) y MODAI (23); la 3 solo en WH-OR: una caja de MODAI no va allí
        cols = [_col(1, 67, ['A1-NEGRO'], cia=23), _col(3, 67, ['A1-NEGRO'] * 4, cias={1}),
                _col(2, 67, ['A1-NEGRO'] * 2, cias={1, 23})]
        pasos, r = logica.plan_lineal(67, cols)
        self.assertEqual(r['vaciadas'], 1)
        self.assertEqual({p['destino_id'] for p in pasos}, {2})

    def test_tallas_por_altura(self):
        # M y L se piden más: abajo hasta la mitad de las uds; XS es resto (2 uds frente a 50)
        b = logica.tallas_por_altura({'XS': 2, 'S': 20, 'M': 50, 'L': 40, 'XL': 10},
                                     {'M': 30, 'L': 25, 'S': 10, 'XL': 2, 'XS': 1})
        self.assertEqual(b['M'], 'abajo')
        self.assertEqual(b['XS'], 'restos')
        self.assertEqual(b['L'], 'arriba')        # M (50 de 122) ya está cerca de la mitad; con L se pasaría más
        self.assertEqual(b['XL'], 'arriba')
        # sin líneas: por stock
        self.assertEqual(logica.tallas_por_altura({'S': 5, 'M': 10}, {}), {'M': 'abajo', 'S': 'arriba'})
        self.assertEqual(logica.tallas_por_altura({}, {}), {})

    def test_banda_caja(self):
        bandas = {'M': 'abajo', 'L': 'arriba', 'XS': 'restos'}
        self.assertEqual(logica.banda_caja({'M': 10, 'L': 2}, bandas), 'abajo')
        self.assertEqual(logica.banda_caja({'L': 10}, bandas), 'arriba')
        self.assertEqual(logica.banda_caja({'XS': 3}, bandas), 'arriba')
        self.assertEqual(logica.banda_caja({}, bandas), 'arriba')

    def test_abc(self):
        self.assertEqual(logica.clases_abc({'a': 80, 'b': 15, 'c': 5}), {'a': 'A', 'b': 'otra', 'c': 'otra'})
        self.assertEqual(logica.clases_abc({'a': 0}), {'a': 'otra'})

    def test_vacia_la_poco_llena(self):
        cols = [_col(1, 67, ['A1-NEGRO', 'A1-NEGRO']), _col(2, 67, ['A1-NEGRO'] * 5)]
        pasos, r = logica.plan_lineal(67, cols)
        self.assertEqual(r['vaciadas'], 1)
        self.assertEqual({p['destino_id'] for p in pasos}, {2})
        self.assertEqual(len(pasos), 2)

    def test_no_pasa_de_8(self):
        cols = [_col(1, 67, ['A1-NEGRO'] * 3), _col(2, 67, ['A1-NEGRO'] * 6)]
        pasos, r = logica.plan_lineal(67, cols)
        self.assertEqual(r['vaciadas'], 0)       # 6 + 3 = 9 > 8
        self.assertEqual(pasos, [])
        pasos, r = logica.plan_lineal(67, cols, capacidad=9)
        self.assertEqual(r['vaciadas'], 1)

    def test_no_mezcla_colores_del_mismo_modelo(self):
        cols = [_col(1, 67, ['A1-NEGRO']), _col(2, 67, ['A1-ROJO'] * 4), _col(3, 67, ['B2-AZUL'] * 4)]
        pasos, _r = logica.plan_lineal(67, cols)
        self.assertEqual(pasos[0]['destino_id'], 3)

    def test_prefiere_donde_ya_esta(self):
        cols = [_col(1, 67, ['A1-NEGRO']), _col(2, 67, ['B2-AZUL'] * 6), _col(3, 67, ['A1-NEGRO'] * 4)]
        pasos, _r = logica.plan_lineal(67, cols)
        self.assertEqual(pasos[0]['destino_id'], 3)

    def test_mismo_modelo_color_junto(self):
        # dos cajas del mismo modelo-color van al mismo destino; si no caben juntas, la columna no se vacía
        cols = [_col(1, 67, ['A1-NEGRO', 'A1-NEGRO']), _col(2, 67, ['B2-AZUL'] * 7), _col(3, 67, ['C3-VERDE'] * 6)]
        pasos, r = logica.plan_lineal(67, cols)
        self.assertEqual({p['destino_id'] for p in pasos}, {3})
        cols = [_col(1, 67, ['A1-NEGRO', 'A1-NEGRO']), _col(2, 67, ['B2-AZUL'] * 7)]
        pasos, r = logica.plan_lineal(67, cols)
        self.assertEqual(r['vaciadas'], 0)

    def test_todo_o_nada(self):
        # el NEGRO cabe pero el ROJO (otro modelo) no: la columna no se vacía y no hay pasos
        cols = [_col(1, 67, ['A1-NEGRO', 'B2-ROJO', 'B2-ROJO']), _col(2, 67, ['A1-NEGRO'] * 6)]
        pasos, r = logica.plan_lineal(67, cols)
        self.assertEqual((pasos, r['vaciadas']), ([], 0))

    def test_distancia_y_zona_z(self):
        cols = [_col(1, 67, ['A1-NEGRO']), _col(2, 70, ['A1-NEGRO'] * 4), _col(3, 68, ['A1-NEGRO'] * 4, z=True)]
        pasos, r = logica.plan_lineal(67, cols)
        self.assertEqual(r['vaciadas'], 0)          # L70 queda a 3 lineales y la de L68 tiene Z
        cols.append(_col(4, 69, ['A1-NEGRO'] * 4))
        pasos, r = logica.plan_lineal(67, cols)
        self.assertEqual(pasos[0]['destino_id'], 4)

    def test_no_a_columnas_vacias_ni_se_vacia_la_que_recibe(self):
        cols = [_col(1, 67, ['A1-NEGRO']), _col(2, 67, []), _col(3, 67, ['A1-NEGRO'] * 2)]
        pasos, r = logica.plan_lineal(67, cols)
        # la 1 (1 caja) va a la 3; la 3 ya recibe y no se vacía
        self.assertEqual(r['vaciadas'], 1)
        self.assertEqual([p['destino_id'] for p in pasos], [3])

    def test_clase_a_mas_cerca_del_muelle(self):
        cols = [_col(1, 67, ['A1-NEGRO']), _col(2, 66, ['B2-AZUL'] * 4), _col(3, 68, ['C3-VERDE'] * 4)]
        pasos, _r = logica.plan_lineal(67, cols, abc={'A1-NEGRO': 'A'})
        self.assertEqual(pasos[0]['destino_id'], 2)
        pasos, _r = logica.plan_lineal(67, cols, abc={'A1-NEGRO': 'otra'})
        self.assertEqual(pasos[0]['destino_id'], 3)

    def test_no_movible_y_extra(self):
        cols = [_col(1, 67, ['A1-NEGRO']), _col(2, 67, ['A1-NEGRO'] * 4)]
        cols[0]['cajas'][0]['movible'] = False
        pasos, r = logica.plan_lineal(67, cols)
        self.assertEqual((pasos, r['sin_sitio']), ([], 1))
        cols = [_col(1, 67, ['A1-NEGRO']), _col(2, 67, ['A1-NEGRO'] * 4, extra=4)]
        pasos, r = logica.plan_lineal(67, cols)
        self.assertEqual(r['vaciadas'], 0)          # 4 + 4 que ya llegan = 8: no cabe otra

    def test_aviso_destino(self):
        self.assertEqual(logica.aviso_destino([('A1', 'A1-NEGRO')] * 3, 'A1-NEGRO', 'A1', 1), '')
        self.assertIn('otro color', logica.aviso_destino([('A1', 'A1-ROJO')], 'A1-NEGRO', 'A1', 1))
        self.assertIn('pasaría de 8', logica.aviso_destino([('B', 'B-X')] * 8, 'A1-NEGRO', 'A1', 1))

if __name__ == '__main__':
    unittest.main()
