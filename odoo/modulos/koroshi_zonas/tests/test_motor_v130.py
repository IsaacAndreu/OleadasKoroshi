# -*- coding: utf-8 -*-
# =============================================================================
# v1.3.0 (auditoria 13/11, fase 5): lo nuevo que la 1883 no hacia.
#   - OUT de dias anteriores ('de_antes', las marca el lector) y orden por urgencia cuando no cabe todo.
#   - Aviso en el informe si con "Todo en una ronda" se acaba despues de la hora de fin.
#   - Con UNA_RONDA y sin OUT de dias anteriores, el reparto es el mismo que con COMO_1883.
# =============================================================================
import os
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
sys.path.insert(0, AQUI)

from motor import modelo  # noqa: E402
from motor import v12f  # noqa: E402
from motor.evaluar import numero_k, numero_pedido  # noqa: E402
import sintetico  # noqa: E402


def validas(datos):
    """Las OUT que el motor no salta (para no depender de las 'raras' del generador)."""
    rep = v12f.repartir(datos, dict(modelo.COMO_1883, MODO='DIAGNOSTICO'), {'una_ronda': True})
    return set(rep.R['pids'])


class TestV130(unittest.TestCase):

    def test_una_ronda_sin_antes_mismo_reparto(self):
        for semilla in (20, 21, 22):
            datos = sintetico.generar(semilla, n_pedidos=90)
            with self.subTest(semilla=semilla):
                a = v12f.repartir(datos, dict(modelo.COMO_1883, MODO='DIAGNOSTICO'))
                b = v12f.repartir(datos, {'MODO': 'DIAGNOSTICO', 'ORDEN_PEDIDO': False})   # v1.6.0: aparte
                self.assertEqual(a.zona_fin, b.zona_fin)
                self.assertEqual(a.plan, b.plan)

    def test_aviso_hora_fin(self):
        datos = sintetico.generar(21, n_pedidos=90)
        ctx = {'hora_inicio': '06:00', 'hora_fin': '06:30', 'una_ronda': True}
        nuevo = v12f.repartir(datos, {'MODO': 'DIAGNOSTICO', 'ORDEN_PEDIDO': False}, ctx)   # v1.6.0: aparte
        self.assertGreater(nuevo.pasa_hora_fin, 0)
        avisos = [l for l in nuevo.lineas if l.startswith('AVISO:')]
        self.assertEqual(len(avisos), 1)
        self.assertIn('6:30', avisos[0])
        viejo = v12f.repartir(datos, dict(modelo.COMO_1883, MODO='DIAGNOSTICO'), ctx)
        self.assertEqual(viejo.pasa_hora_fin, 0)
        self.assertFalse([l for l in viejo.lineas if l.startswith('AVISO:')])
        # el aviso no cambia el reparto
        self.assertEqual(nuevo.zona_fin, viejo.zona_fin)

    def test_sin_aviso_si_acaba_a_tiempo(self):
        datos = sintetico.generar(21, n_pedidos=90)
        rep = v12f.repartir(datos, {'MODO': 'DIAGNOSTICO'}, {'hora_fin': '23:59', 'una_ronda': True})
        self.assertEqual(rep.pasa_hora_fin, 0)
        self.assertFalse([l for l in rep.lineas if l.startswith('AVISO:')])

    def test_urgentes_entran_primero(self):
        datos = sintetico.generar(41, n_pedidos=120)
        ok = validas(datos)
        outs = [o for o in datos['outs'] if o['id'] in ok]
        # la tienda de numero mas alto: con la 1883 es la primera que se queda fuera
        alta = max(outs, key=lambda o: (numero_k(o['partner_name']), o['name']))
        for o in datos['outs']:
            if o['partner_name'] == alta['partner_name']:
                o['de_antes'] = True
                o['create_date'] = '2026-11-09 10:00:00'
        ctx = {'hora_inicio': '06:00', 'hora_fin': '07:00', 'una_ronda': False}
        viejo = v12f.repartir(datos, dict(modelo.COMO_1883, MODO='DIAGNOSTICO'), ctx)
        nuevo = v12f.repartir(datos, {'MODO': 'DIAGNOSTICO'}, ctx)
        self.assertTrue(viejo.no_entran, 'la prueba necesita que no quepa todo')
        self.assertIn(alta['id'], viejo.no_entran)
        self.assertNotIn(alta['id'], nuevo.no_entran)
        self.assertIn(alta['id'], nuevo.R['pids'])
        self.assertTrue([l for l in nuevo.lineas if l.startswith('OUT de dias anteriores')])
        # v1.6.0: las que entran se numeran por numero de pedido
        ks = [numero_pedido(datos_out['origin']) for datos_out in
              [next(o for o in datos['outs'] if o['id'] == pid) for pid in nuevo.R['pids']]]
        self.assertEqual(ks, sorted(ks))

    def test_tiendas_48h_antes_que_el_resto(self):
        datos = sintetico.generar(41, n_pedidos=120)
        ok = validas(datos)
        outs = [o for o in datos['outs'] if o['id'] in ok]
        alta = max(outs, key=lambda o: (numero_k(o['partner_name']), o['name']))
        ctx = {'hora_inicio': '06:00', 'hora_fin': '07:00', 'una_ronda': False}
        k_alta = numero_k(alta['partner_name'])
        nuevo = v12f.repartir(datos, {'MODO': 'DIAGNOSTICO', 'TIENDAS_48H': [k_alta]}, ctx)
        viejo = v12f.repartir(datos, dict(modelo.COMO_1883, MODO='DIAGNOSTICO', TIENDAS_48H=[k_alta]), ctx)
        self.assertIn(alta['id'], viejo.no_entran)
        self.assertIn(alta['id'], nuevo.R['pids'])

    def test_saltadas_del_lector(self):
        datos = sintetico.generar(21, n_pedidos=30)
        datos['saltadas_lector'] = ['OUT/99999 (K1): de un dia anterior y en la cola de OP1']
        rep = v12f.repartir(datos, {'MODO': 'DIAGNOSTICO'})
        self.assertIn('   OUT/99999 (K1): de un dia anterior y en la cola de OP1', rep.lineas)

    def test_config_nueva(self):
        cfg = modelo.config_por_defecto()
        self.assertEqual(cfg['dias_atras'], 7)
        self.assertTrue(cfg['orden_urgencia'])
        cambios = modelo.cambios_desde_config({'dias_atras': 0, 'orden_urgencia': False})
        self.assertEqual(cambios['DIAS_ATRAS'], 0)
        self.assertFalse(cambios['ORDEN_URGENCIA'])


if __name__ == '__main__':
    unittest.main()
