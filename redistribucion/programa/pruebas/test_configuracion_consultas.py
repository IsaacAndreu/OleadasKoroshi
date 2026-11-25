# -*- coding: utf-8 -*-
"""Pruebas de la configuración y de las consultas (sin Odoo y sin tocar el almacén de credenciales real)."""
import datetime
import tempfile
import unittest
from pathlib import Path

from redistrib import configuracion, consultas


class Configuracion(unittest.TestCase):

    def _escribir(self, texto):
        d = tempfile.mkdtemp()
        ruta = Path(d) / 'config.local.toml'
        ruta.write_text(texto, encoding='utf-8')
        return ruta

    def test_lee(self):
        cfg = configuracion.leer_config(self._escribir(
            '[odoo]\nurl = "https://x.ejemplo/"\nbd = "B"\nusuario = "u"\n[lectura]\npagina = 3000\n'))
        self.assertEqual((cfg['url'], cfg['pagina'], cfg['pausa']), ('https://x.ejemplo', 3000, 0.5))

    def test_clave_en_fichero_no(self):
        with self.assertRaises(configuracion.ErrorConfiguracion):
            configuracion.leer_config(self._escribir('[odoo]\nurl="https://x"\nbd="B"\nusuario="u"\nclave="no"\n'))

    def test_falta(self):
        with self.assertRaises(configuracion.ErrorConfiguracion):
            configuracion.leer_config(self._escribir('[odoo]\nurl="https://x"\nbd=""\nusuario="u"\n'))
        with self.assertRaises(configuracion.ErrorConfiguracion):
            configuracion.leer_config(Path(tempfile.mkdtemp()) / 'no_existe.toml')

    def test_keyring_falso(self):
        class Falso:
            guardado = {}

            def get_password(self, s, u):
                return self.guardado.get((s, u))

        original = configuracion._keyring
        configuracion._keyring = lambda: Falso()
        try:
            with self.assertRaises(configuracion.ErrorConfiguracion):
                configuracion.leer_clave('u')
            Falso.guardado[(configuracion.SERVICIO_KEYRING, 'u')] = 'k'
            self.assertEqual(configuracion.leer_clave('u'), 'k')
        finally:
            configuracion._keyring = original


class Consultas(unittest.TestCase):

    def test_conteos_siempre_compania_8_o_su_camino(self):
        for campos in ({'company_id': {}, 'picking_code': {}}, {}):
            for etiqueta, modelo, dominio, ctx in consultas.conteos(campos, hoy=datetime.date(2026, 11, 23)):
                with self.subTest(etiqueta=etiqueta):
                    texto = repr(dominio)
                    self.assertIn('8)', texto)
                    self.assertIn('company_id', texto)

    def test_lineas_sin_campos_propios_van_por_el_albaran(self):
        d = consultas.dominio_lineas_hechas({}, datetime.date(2026, 10, 26), 'outgoing')
        self.assertIn(('move_id.company_id', '=', 8), d)
        self.assertIn(('picking_id.picking_type_id.code', '=', 'outgoing'), d)
        self.assertIn(('date', '>=', '2026-10-26 00:00:00'), d)

    def test_campos_que_faltan(self):
        hay = {m: {c: {} for c in cs} for m, cs in consultas.CAMPOS_NECESARIOS.items()}
        self.assertEqual(consultas.campos_que_faltan(hay), {})
        del hay['product.template']['season_id']
        self.assertEqual(consultas.campos_que_faltan(hay), {'product.template': ['season_id']})


if __name__ == '__main__':
    unittest.main()
