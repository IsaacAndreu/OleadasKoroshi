# -*- coding: utf-8 -*-
# =============================================================================
# v1.6.0 (19/11/2026): orden por numero de pedido (S-6665...), lo que pide KOROSHI, en vez de por tienda (K##).
#   - Las CAJA (plan) se numeran por numero de pedido; con ORDEN_PEDIDO = False, por tienda como la 1883.
#   - Si no cabe todo, dentro de cada grupo de urgencia entran antes los pedidos mas antiguos.
#   - COMO_1883 sigue ordenando por tienda (comparacion con el cron 202).
# =============================================================================
import os
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
sys.path.insert(0, AQUI)

from motor import modelo  # noqa: E402
from motor import v12f  # noqa: E402
from motor.evaluar import numero_k, numero_pedido, SIN_PEDIDO  # noqa: E402
import sintetico  # noqa: E402


def out_de(datos, pid):
    return next(o for o in datos['outs'] if o['id'] == pid)


def cajas(rep, datos, clave):
    """Lista de claves de las OUT en el orden de sus CAJA."""
    return [clave(out_de(datos, pid)) for pid, _por_z, _pr, _sr, _caja in sorted(rep.plan, key=lambda x: x[4])]


class TestNumeroPedido(unittest.TestCase):

    def test_numero_pedido(self):
        self.assertEqual(numero_pedido('S-6665004409'), 6665004409)
        self.assertEqual(numero_pedido('S-6665004409 (2)'), 6665004409)
        self.assertEqual(numero_pedido(''), SIN_PEDIDO)
        self.assertEqual(numero_pedido(None), SIN_PEDIDO)
        self.assertLess(numero_pedido('S-6665004409'), numero_pedido('S-6665004410'))


class TestOrdenPedido(unittest.TestCase):

    def test_cajas_por_pedido(self):
        for semilla in (20, 21, 22):
            datos = sintetico.generar(semilla, n_pedidos=90)
            rep = v12f.repartir(datos, {'MODO': 'DIAGNOSTICO'})
            with self.subTest(semilla=semilla):
                ps = cajas(rep, datos, lambda o: numero_pedido(o['origin']))
                self.assertEqual(ps, sorted(ps))
                self.assertEqual([x[4] for x in rep.plan], list(range(1, len(rep.plan) + 1)))

    def test_sin_orden_pedido_por_tienda(self):
        datos = sintetico.generar(21, n_pedidos=90)
        rep = v12f.repartir(datos, {'MODO': 'DIAGNOSTICO', 'ORDEN_PEDIDO': False})
        ks = cajas(rep, datos, lambda o: numero_k(o['partner_name']))
        self.assertEqual(ks, sorted(ks))

    def test_como_1883_por_tienda(self):
        datos = sintetico.generar(21, n_pedidos=90)
        a = v12f.repartir(datos, dict(modelo.COMO_1883, MODO='DIAGNOSTICO'))
        b = v12f.repartir(datos, {'MODO': 'DIAGNOSTICO', 'ORDEN_PEDIDO': False, 'DIAS_ATRAS': 0,
                                  'ORDEN_URGENCIA': False, 'AVISO_HORA_FIN': False})
        self.assertEqual(a.plan, b.plan)
        self.assertEqual(a.zona_fin, b.zona_fin)

    def test_mismas_lineas_y_uds(self):
        # cambiar el orden no deja fuera ninguna linea ni OUT con todo en una ronda
        datos = sintetico.generar(22, n_pedidos=90)
        a = v12f.repartir(datos, {'MODO': 'DIAGNOSTICO', 'ORDEN_PEDIDO': False})
        b = v12f.repartir(datos, {'MODO': 'DIAGNOSTICO'})
        self.assertEqual(set(a.zona_fin), set(b.zona_fin))
        self.assertEqual(set(x[0] for x in a.plan), set(x[0] for x in b.plan))

    def test_si_no_cabe_entran_los_pedidos_antiguos(self):
        datos = sintetico.generar(41, n_pedidos=120)
        ctx = {'hora_inicio': '06:00', 'hora_fin': '07:00', 'una_ronda': False}
        rep = v12f.repartir(datos, {'MODO': 'DIAGNOSTICO', 'TIENDAS_48H': []}, ctx)
        self.assertTrue(rep.no_entran, 'la prueba necesita que no quepa todo')
        dentro = max(numero_pedido(out_de(datos, pid)['origin']) for pid in rep.R['pids'])
        fuera = min(numero_pedido(out_de(datos, pid)['origin']) for pid in rep.no_entran)
        self.assertLessEqual(dentro, fuera)

    def test_config(self):
        self.assertTrue(modelo.config_por_defecto()['orden_pedido'])
        self.assertFalse(modelo.cambios_desde_config({'orden_pedido': False})['ORDEN_PEDIDO'])


if __name__ == '__main__':
    unittest.main()
