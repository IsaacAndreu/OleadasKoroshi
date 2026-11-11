# -*- coding: utf-8 -*-
# =============================================================================
# Criterio de aceptacion de la fase 2: con las mismas OUT de entrada, el motor da EXACTAMENTE el mismo
# reparto (zona final de cada linea reservada) y el mismo informe que la accion 1883 original.
# - Datos sinteticos con semilla (tests/sintetico.py).
# - Volcados reales anonimizados en tests/datos/*.json (los saca tests/volcar_datos.js en Odoo).
# =============================================================================
import glob
import json
import os
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
sys.path.insert(0, AQUI)

from motor import v12f  # noqa: E402
import arnes_1883  # noqa: E402
import sintetico  # noqa: E402


def desde_utc(datos, zona='Europe/Madrid'):
    import datetime
    import pytz
    ahora = datetime.datetime.strptime(datos['ahora'], '%Y-%m-%d %H:%M:%S')
    tz = pytz.timezone(zona)
    med = tz.localize(datetime.datetime(ahora.year, ahora.month, ahora.day))
    return med.astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S')


class IgualQue1883(object):

    def comparar(self, datos, contexto, modo=None):
        texto_o, R_o = arnes_1883.ejecutar_original(datos, contexto, modo)
        datos_m = datos
        if not contexto.get('prueba_ids') and not contexto.get('prueba_agrupacion'):
            # sin prueba, el lector hace el search de la accion en Odoo: aqui lo mismo sobre los datos
            datos_m = dict(datos)
            datos_m['outs'] = arnes_1883.filtrar_hoy(datos, 8, 'PED. TIENDAS', desde_utc(datos))
        elif contexto.get('prueba_agrupacion'):
            pref = contexto['prueba_agrupacion']
            datos_m = dict(datos)
            datos_m['outs'] = sorted([o for o in datos['outs'] if (o['batch_name'] or '').startswith(pref)
                                      and o['state'] != 'cancel' and o['company_id'] == 8
                                      and o['picking_type_code'] == 'outgoing'], key=lambda o: o['name'])
        elif contexto.get('prueba_ids'):
            por_id = dict((o['id'], o) for o in datos['outs'])
            datos_m = dict(datos)
            datos_m['outs'] = [por_id[i] for i in contexto['prueba_ids'] if i in por_id]
        cambios = modo and {'MODO': modo} or None
        rep = v12f.repartir(datos_m, cambios, contexto)
        if R_o is not None:
            self.assertEqual(rep.zona_fin, R_o['zona_fin'], 'zona final de cada linea distinta')
            self.assertEqual(rep.R['grupos'], R_o['grupos'])
            self.assertEqual(rep.R['pers'], R_o['pers'])
            self.assertEqual(rep.R['seg_z'], R_o['seg_z'])
        self.assertEqual(rep.lineas, texto_o)
        return rep


class TestSintetico(IgualQue1883, unittest.TestCase):

    def test_prueba_ids(self):
        for semilla in range(8):
            datos = sintetico.generar(semilla)
            ids = [o['id'] for o in datos['outs']]
            with self.subTest(semilla=semilla):
                self.comparar(datos, {'prueba_ids': ids})

    def test_prueba_ids_con_hechas(self):
        # prueba_ids con OUT ya leidas: cuenta qty_done si es mayor que la reserva
        datos = sintetico.generar(11)
        for o in datos['outs']:
            for ml in o['lineas']:
                if ml['id'] % 3 == 0:
                    ml['qty_done'] = ml['qty'] + 1
                    ml['qty'] = 0.0
        self.comparar(datos, {'prueba_ids': [o['id'] for o in datos['outs']]})

    def test_hoy_diagnostico(self):
        for semilla in range(20, 26):
            datos = sintetico.generar(semilla, n_pedidos=90)
            with self.subTest(semilla=semilla):
                self.comparar(datos, {}, modo='DIAGNOSTICO')

    def test_prueba_agrupacion(self):
        datos = sintetico.generar(31)
        for n, o in enumerate(datos['outs']):
            o['batch_name'] = n % 2 and 'Z-2210-D%d' % (n % 3 + 1) or o['batch_name']
        self.comparar(datos, {'prueba_agrupacion': 'Z-2210-'})

    def test_contexto_y_r2(self):
        datos = sintetico.generar(41, n_pedidos=120)
        datos['lotes_existentes'] = ['Z-1011-D1', 'Z-1011-R2-D1', 'Z-0911-D1']
        ctx = {'prueba_ids': [o['id'] for o in datos['outs']], 'personas': 9, 'zonas': 4,
               'hora_inicio': '07:00', 'hora_fin': '11:00', 'una_ronda': False}
        self.comparar(datos, ctx)

    def test_anonimizado_y_json(self):
        # lo que se guarda en datos_entrada pasa por JSON y por anonimizar.py: el reparto no cambia
        import anonimizar
        datos = json.loads(json.dumps(sintetico.generar(61)))
        datos = anonimizar.anonimizar(datos)
        self.comparar(datos, {'prueba_ids': [o['id'] for o in datos['outs']]})

    def test_otras_variantes(self):
        datos = sintetico.generar(51, n_pedidos=80)
        ids = [o['id'] for o in datos['outs']]
        for ctx in ({'prueba_ids': ids, 'zonas': 1}, {'prueba_ids': ids, 'zonas': 20},
                    {'prueba_ids': ids, 'personas': 3}, {'prueba_ids': ids, 'zonas_muelle': 0},
                    {'prueba_ids': ids[:5]}, {'prueba_ids': []}):
            # prueba_ids vacio = sin prueba (la accion iria a REAL): se compara en DIAGNOSTICO
            with self.subTest(ctx=sorted(ctx), n=len(ctx.get('prueba_ids') or [])):
                self.comparar(datos, ctx, modo=not ctx.get('prueba_ids') and 'DIAGNOSTICO' or None)


class TestVolcados(IgualQue1883, unittest.TestCase):

    def test_volcados_reales(self):
        ficheros = sorted(glob.glob(os.path.join(AQUI, 'datos', '*.json')))
        if not ficheros:
            self.skipTest('Aun no hay volcados reales en tests/datos/')
        for f in ficheros:
            with open(f, encoding='utf-8') as fh:
                datos = json.load(fh)
            with self.subTest(fichero=os.path.basename(f)):
                ctx = datos.get('contexto') or {'prueba_ids': [o['id'] for o in datos['outs']]}
                sin_prueba = not ctx.get('prueba_ids') and not ctx.get('prueba_agrupacion')
                self.comparar(datos, ctx, modo=sin_prueba and 'DIAGNOSTICO' or None)


if __name__ == '__main__':
    unittest.main()
