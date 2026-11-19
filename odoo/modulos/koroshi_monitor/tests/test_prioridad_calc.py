# -*- coding: utf-8 -*-
# Pruebas sin Odoo:  python -I odoo/modulos/koroshi_monitor/tests/test_prioridad_calc.py
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'controllers'))
import prioridad_calc as calc  # noqa: E402


def out(num, k, lote='', caja='', est='curso', u=10.0, leido=10.0, en_caja=0.0, ident=None):
    return {'id': ident or num, 'out': str(26500 + num % 100), 'pedido': 'S-666500%04d' % num,
            'tienda': '%s - TIENDA %s' % (k, k), 'lote': lote, 'caja': caja, 'est': est,
            'u': u, 'disp': u, 'leido': leido, 'en_caja': en_caja}


class TestPrioridad(unittest.TestCase):

    def test_caso_19_11_mu2(self):
        """19/11: 5 OUT de MU2 leidas enteras sin caja, pedidos posteriores ya cerrados (hasta 4456)."""
        abiertas = [out(4417, 'K45', 'Z-1911-MU2', '03'), out(4418, 'K41', 'Z-1911-MU2', '04'),
                    out(4419, 'K46', 'Z-1911-MU2', '05'), out(4425, 'K42', 'Z-1911-MU2', '09'),
                    out(4428, 'K31', 'Z-1911-MU2', '11'), out(4457, 'K80', est='pend', leido=0.0)]
        hechos = ['S-6665004456', 'S-6665004456', 'S-6665004455', 'S-6665004449', 'S-6665004417']
        r = calc.prioridad(abiertas, hechos)
        self.assertEqual([p['k'] for p in r['siguiente']], ['K45', 'K41', 'K46'])
        self.assertEqual(r['siguiente'][0]['pedido'], 'S-6665004417')
        self.assertEqual(r['siguiente'][0]['outs'][0]['zona'], 'MU2')
        self.assertEqual(r['ultimo_cerrado'], 'S-6665004456')
        # 4417 tiene una OUT validada pero otra abierta: no esta cerrado del todo
        self.assertEqual([o['k'] for o in r['sacar_antes']], ['K45', 'K41', 'K46', 'K42', 'K31'])
        self.assertEqual(r['sacar_antes'][0]['sin_caja'], 10.0)
        self.assertEqual(r['abiertos'], 6)

    def test_sin_stock_y_sin_numero_no_cuentan(self):
        abiertas = [out(4400, 'K10', est='sinstock', leido=0.0), out(4410, 'K11'),
                    dict(out(4420, 'K12'), pedido='ZALANDO-1')]
        r = calc.prioridad(abiertas, [])
        self.assertEqual([p['k'] for p in r['siguiente']], ['K11'])
        self.assertEqual(r['sacar_antes'], [])
        self.assertEqual(r['ultimo_cerrado'], '')

    def test_pedido_partido_en_zonas_suma(self):
        abiertas = [out(4430, 'K20', 'Z-1911-D2', '07', u=5.0, leido=2.0, ident=1),
                    out(4430, 'K20', 'Z-1911-D1', '07', u=8.0, leido=8.0, en_caja=8.0, ident=2)]
        r = calc.prioridad(abiertas, ['S-6665004429'])
        p = r['siguiente'][0]
        self.assertEqual(len(p['outs']), 2)
        self.assertEqual([o['zona'] for o in p['outs']], ['D1', 'D2'])
        self.assertEqual((p['u'], p['leido'], p['en_caja']), (13.0, 10.0, 8.0))
        self.assertEqual(r['sacar_antes'], [])      # 4429 cerrado es anterior: nada que sacar antes

    def test_todo_cerrado(self):
        r = calc.prioridad([], ['S-6665004456'])
        self.assertEqual(r['siguiente'], [])
        self.assertEqual(r['sacar_antes'], [])


if __name__ == '__main__':
    unittest.main()
