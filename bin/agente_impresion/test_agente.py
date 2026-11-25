# -*- coding: utf-8 -*-
# Pruebas del agente sin Odoo ni impresora: python bin/agente_impresion/test_agente.py
# Un Odoo falso (http local) con los tres métodos y un SumatraPDF falso (.bat que sale con 0 o 1).
import base64
import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import agente_impresion as ag  # noqa: E402

PDF = b'%PDF-1.4 prueba'


class OdooFalso(BaseHTTPRequestHandler):
    trabajos = []
    hechos = []
    llamadas = []

    def log_message(self, *a):
        pass

    def do_POST(self):
        p = json.loads(self.rfile.read(int(self.headers['Content-Length'])))['params']
        if p['service'] == 'common':
            res = 7 if p['args'][2] == 'buena' else False
        else:
            metodo, args = p['args'][4], p['args'][5]
            OdooFalso.llamadas.append(metodo)
            if metodo == 'agente_siguientes':
                res, OdooFalso.trabajos = OdooFalso.trabajos, []
            elif metodo == 'agente_pdf':
                res = base64.b64encode(b'no es pdf' if args[0] == 99 else PDF).decode()
            else:
                OdooFalso.hechos.append(tuple(args))
                res = True
        cuerpo = json.dumps({'jsonrpc': '2.0', 'id': 1, 'result': res}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(cuerpo)


class TestAgente(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(('127.0.0.1', 0), OdooFalso)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = 'http://127.0.0.1:%d' % cls.srv.server_port
        cls.tmp = tempfile.mkdtemp()
        cls.bien = os.path.join(cls.tmp, 'sumatra_bien.bat')
        cls.mal = os.path.join(cls.tmp, 'sumatra_mal.bat')
        open(cls.bien, 'w').write('@echo %* > "%~dp0ultima.txt"\r\n@exit /b 0\r\n')
        open(cls.mal, 'w').write('@echo sin papel 1>&2\r\n@exit /b 1\r\n')

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        OdooFalso.trabajos, OdooFalso.hechos, OdooFalso.llamadas = [], [], []

    def cfg(self, sumatra):
        return {'codigo': 'EXP1', 'nombre_windows': 'ZDesigner ZD420', 'sumatra': sumatra, 'ajuste': 'fit,landscape'}

    def test_imprime_y_marca(self):
        odoo = ag.Odoo(self.url, 'bd', 'u', 'buena')
        OdooFalso.trabajos = [{'id': 1, 'descripcion': 'XPO 1', 'copias': 2}]
        self.assertEqual(ag.una_vuelta(odoo, self.cfg(self.bien)), 1)
        self.assertEqual(OdooFalso.hechos, [(1, True, '')])
        orden = open(os.path.join(self.tmp, 'ultima.txt')).read()
        self.assertIn('-print-to "ZDesigner ZD420"', orden)
        self.assertIn('fit,landscape,2x', orden)          # v1.0.1: la XPO es apaisada

    def test_error_de_impresora_va_a_odoo(self):
        odoo = ag.Odoo(self.url, 'bd', 'u', 'buena')
        OdooFalso.trabajos = [{'id': 2, 'descripcion': 'GLS', 'copias': 1}]
        ag.una_vuelta(odoo, self.cfg(self.mal))
        self.assertEqual(OdooFalso.hechos[0][:2], (2, False))
        self.assertIn('SumatraPDF', OdooFalso.hechos[0][2])

    def test_no_es_pdf(self):
        odoo = ag.Odoo(self.url, 'bd', 'u', 'buena')
        OdooFalso.trabajos = [{'id': 99, 'descripcion': 'x', 'copias': 1}]
        ag.una_vuelta(odoo, self.cfg(self.bien))
        self.assertEqual(OdooFalso.hechos[0][:2], (99, False))

    def test_cola_vacia(self):
        odoo = ag.Odoo(self.url, 'bd', 'u', 'buena')
        self.assertEqual(ag.una_vuelta(odoo, self.cfg(self.bien)), 0)
        self.assertEqual(OdooFalso.llamadas, ['agente_siguientes'])

    def test_clave_mala(self):
        with self.assertRaises(ag.ErrorConfig):
            ag.Odoo(self.url, 'bd', 'u', 'mala').entrar()

    def test_lista_blanca(self):
        odoo = ag.Odoo(self.url, 'bd', 'u', 'buena')
        with self.assertRaises(PermissionError):
            odoo.llamar('unlink', 1)

    def test_sin_red_sube_al_bucle(self):
        odoo = ag.Odoo('http://127.0.0.1:1', 'bd', 'u', 'buena', timeout=2)
        with self.assertRaises(ag.ERRORES_RED):
            ag.una_vuelta(odoo, self.cfg(self.bien))

    def test_credencial_windows(self):
        nombre = 'koroshi-impresion-PRUEBA-test'
        subprocess.run(['cmdkey', '/generic:' + nombre, '/user:prueba', '/pass:valor-de-prueba-ñ'],
                       capture_output=True, check=True)
        try:
            self.assertEqual(ag.leer_clave(nombre), 'valor-de-prueba-ñ')
        finally:
            subprocess.run(['cmdkey', '/delete:' + nombre], capture_output=True)
        with self.assertRaises(ag.ErrorConfig):
            ag.leer_clave(nombre)

    def test_ajuste_no_valido(self):
        with self.assertRaises(ValueError):
            ag.imprimir_pdf(self.bien, 'x.pdf', ajuste='girar')

    def test_config(self):
        ruta = os.path.join(self.tmp, 'config.ini')
        texto = open(os.path.join(AQUI, 'config.ejemplo.ini'), encoding='utf-8').read()
        open(ruta, 'w', encoding='utf-8').write(texto.replace('PONER_AQUI_EL_LOGIN', 'almacen@x')
                                                .replace(r'C:\KoroshiImpresion\SumatraPDF.exe', self.bien))
        cfg = ag.leer_config(ruta)
        self.assertEqual((cfg['codigo'], cfg['bd'], cfg['segundos'], cfg['ajuste']), ('EXP1', 'NATH_PRODUCTION', 3.0, 'fit,landscape'))
        with self.assertRaises(ag.ErrorConfig):
            ag.leer_config(os.path.join(self.tmp, 'no_existe.ini'))


if __name__ == '__main__':
    unittest.main()
