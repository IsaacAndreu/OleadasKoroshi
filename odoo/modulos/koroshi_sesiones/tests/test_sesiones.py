# -*- coding: utf-8 -*-
# Pruebas sin Odoo:  python -I odoo/modulos/koroshi_sesiones/tests/test_sesiones.py
import os
import pickle
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import sesiones  # noqa: E402


class Almacen(object):
    """Como el FilesystemSessionStore de werkzeug: path, filename_template y get(sid) (dict)."""
    filename_template = 'werkzeug_%s.sess'

    def __init__(self, path):
        self.path = path

    def guardar(self, sid, datos, edad_dias):
        ruta = os.path.join(self.path, self.filename_template % sid)
        with open(ruta, 'wb') as f:
            pickle.dump(datos, f)
        t = time.time() - edad_dias * 86400
        os.utime(ruta, (t, t))
        return ruta

    def get(self, sid):
        with open(os.path.join(self.path, self.filename_template % sid), 'rb') as f:
            return pickle.load(f)


class TestSesiones(unittest.TestCase):

    def test_limpiar(self):
        d = tempfile.mkdtemp()
        a = Almacen(d)
        vieja_usuario = a.guardar('a1', {'uid': 2, 'login': 'almacen'}, 400)
        vieja_sin = a.guardar('a2', {'uid': None}, 8)
        nueva_sin = a.guardar('a3', {}, 1)
        rota = os.path.join(d, 'werkzeug_a4.sess')
        with open(rota, 'wb') as f:
            f.write(b'basura')
        os.utime(rota, (time.time() - 9 * 86400,) * 2)
        otro = os.path.join(d, 'otro.txt')
        open(otro, 'w').close()
        os.utime(otro, (time.time() - 30 * 86400,) * 2)
        borradas, con_usuario, revisadas = sesiones.limpiar_sesiones(a)
        self.assertEqual((borradas, con_usuario, revisadas), (2, 1, 3))
        self.assertTrue(os.path.exists(vieja_usuario))     # con usuario: nunca
        self.assertFalse(os.path.exists(vieja_sin))        # sin usuario y vieja: fuera
        self.assertTrue(os.path.exists(nueva_sin))         # sin usuario pero reciente: se queda
        self.assertFalse(os.path.exists(rota))             # rota y vieja: fuera
        self.assertTrue(os.path.exists(otro))              # no es una sesion: no se toca

    def test_sid(self):
        self.assertEqual(sesiones._sid('werkzeug_abc.sess', 'werkzeug_%s.sess'), 'abc')
        self.assertIsNone(sesiones._sid('werkzeug_.sess', 'werkzeug_%s.sess'))
        self.assertIsNone(sesiones._sid('x.sess', 'werkzeug_%s.sess'))

    def test_gc_no_borra(self):
        self.assertIsNone(sesiones.session_gc_sin_borrar(None))


if __name__ == '__main__':
    unittest.main()
