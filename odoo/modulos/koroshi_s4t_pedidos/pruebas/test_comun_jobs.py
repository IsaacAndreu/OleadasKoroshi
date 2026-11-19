# -*- coding: utf-8 -*-
# Pruebas sin Odoo de models/comun_jobs.py (candado, marcas de job), con dobles de queue_job y del cursor.
#   python odoo/modulos/koroshi_s4t_pedidos/pruebas/test_comun_jobs.py
import importlib
import os
import sys
import types
import unittest

MODULO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Abortada(Exception):
    pass


def _cargar():
    """Carga comun_jobs sin Odoo: paquetes vacios para el modulo y dobles de psycopg2 y queue_job."""
    psy = types.ModuleType('psycopg2')
    psy.Error = Abortada
    sys.modules['psycopg2'] = psy

    class RetryableJobError(Exception):
        def __init__(self, msg, seconds=None, ignore_retry=False):
            super().__init__(msg)
            self.seconds = seconds
            self.ignore_retry = ignore_retry

    def job(func=None, default_channel='root', retry_pattern=None):
        def deco(f):
            f.delayable = True
            f.default_channel = default_channel
            f.retry_pattern = retry_pattern
            return f
        return deco(func) if func else deco

    def identity_exact(job_):
        return 'id'

    for nombre in ('odoo', 'odoo.addons', 'odoo.addons.queue_job'):
        sys.modules[nombre] = types.ModuleType(nombre)
    exc = types.ModuleType('odoo.addons.queue_job.exception')
    exc.RetryableJobError = RetryableJobError
    sys.modules['odoo.addons.queue_job.exception'] = exc
    jb = types.ModuleType('odoo.addons.queue_job.job')
    jb.job = job
    jb.identity_exact = identity_exact
    sys.modules['odoo.addons.queue_job.job'] = jb

    pk = types.ModuleType('ksp')
    pk.__path__ = [MODULO]
    sys.modules['ksp'] = pk
    pm = types.ModuleType('ksp.models')
    pm.__path__ = [os.path.join(MODULO, 'models')]
    sys.modules['ksp.models'] = pm
    return importlib.import_module('ksp.models.comun_jobs'), RetryableJobError


cj, RetryableJobError = _cargar()


class CursorFalso(object):
    """Simula los candados de sesion de Postgres compartidos entre conexiones."""
    tomados = set()

    def __init__(self, abortada=False):
        self.abortada = abortada
        self.rollbacks = 0
        self._res = None

    def execute(self, sql, params):
        if self.abortada:
            raise Abortada('current transaction is aborted')
        if 'pg_try_advisory_lock' in sql:
            libre = params not in CursorFalso.tomados
            if libre:
                CursorFalso.tomados.add(params)
            self._res = (libre,)
        elif 'pg_advisory_unlock' in sql:
            CursorFalso.tomados.discard(params)
            self._res = (True,)

    def fetchone(self):
        return self._res

    def rollback(self):
        self.rollbacks += 1
        self.abortada = False


class TestCandado(unittest.TestCase):

    def setUp(self):
        CursorFalso.tomados = set()

    def test_una_copia_trabaja_la_otra_espera_sin_gastar_reintentos(self):
        a, b = CursorFalso(), CursorFalso()
        with cj.candado(a, 719401, 10131, 'Feed 6665004459'):
            with self.assertRaises(RetryableJobError) as ctx:
                with cj.candado(b, 719401, 10131, 'Feed 6665004459'):
                    self.fail('la segunda copia no debe entrar')
            self.assertEqual(ctx.exception.seconds, 300)
            self.assertTrue(ctx.exception.ignore_retry)
        self.assertEqual(CursorFalso.tomados, set())          # soltado al acabar
        with cj.candado(b, 719401, 10131, 'Feed 6665004459'):   # ahora ya entra
            pass

    def test_otro_feed_no_espera(self):
        with cj.candado(CursorFalso(), 719401, 1, 'a'):
            with cj.candado(CursorFalso(), 719401, 2, 'b'):
                pass
            with cj.candado(CursorFalso(), 719402, 1, 'pedido con el mismo id'):
                pass

    def test_se_suelta_con_error_y_transaccion_abortada(self):
        cr = CursorFalso()
        with self.assertRaises(ValueError):
            with cj.candado(cr, 719402, 7, 'Pedido S-1'):
                cr.abortada = True          # p. ej. serialize dentro del job
                raise ValueError('fallo')
        self.assertEqual(cr.rollbacks, 1)
        self.assertEqual(CursorFalso.tomados, set())


class TestMarcasJob(unittest.TestCase):

    def test_copia_las_marcas_del_metodo_de_effective(self):
        effective = types.ModuleType('feed_effective')

        def action_create_sale_order(self):
            return 'effective'
        action_create_sale_order.delayable = True
        action_create_sale_order.retry_pattern = {1: 60, 5: 300}
        action_create_sale_order.default_channel = 'root.s4t_sync'

        class SOrderFeed(object):
            _name = 's4t.order.feed'
        SOrderFeed.action_create_sale_order = action_create_sale_order
        effective.SOrderFeed = SOrderFeed

        def nuestro(self):
            return 'koroshi'
        res = cj.heredar_marcas_job(nuestro, effective, 's4t.order.feed', 'action_create_sale_order')
        self.assertIs(res, nuestro)
        self.assertTrue(res.delayable)
        self.assertEqual(res.retry_pattern, {1: 60, 5: 300})
        self.assertEqual(res.default_channel, 'root.s4t_sync')

    def test_sin_original_se_marca_como_job_del_canal(self):
        def nuestro(self):
            return 'koroshi'
        res = cj.heredar_marcas_job(nuestro, None, 's4t.order.feed', 'action_create_sale_order')
        self.assertTrue(res.delayable)
        self.assertEqual(res.default_channel, 'root.s4t_sync')

    def test_opciones(self):
        op = cj.opciones_job('S4T Confirmar pedido S-1')
        self.assertEqual(op['channel'], 'root.s4t_sync')
        self.assertEqual(op['priority'], 5)
        self.assertIn('identity_key', op)


if __name__ == '__main__':
    unittest.main()
