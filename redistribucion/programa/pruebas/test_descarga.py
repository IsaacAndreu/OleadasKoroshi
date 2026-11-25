# -*- coding: utf-8 -*-
"""Pruebas de la descarga a SQLite con el Odoo inventado (sin red)."""
import datetime
import sqlite3
import tempfile
import unittest
from pathlib import Path

from redistrib import productos as P
from redistrib import ubicaciones as U
from redistrib.descarga import Descarga, copias_completas
from pruebas.odoo_falso import OdooFalso

HOY = datetime.datetime(2026, 11, 23, 9, 0)


def descargar(carpeta, ahora=HOY, cliente=None, **kw):
    return Descarga(cliente or OdooFalso(), carpeta, pagina=3, avisar=lambda *_: None, ahora=ahora).ejecutar(**kw)


class Ubicaciones(unittest.TestCase):

    def test_clasificar(self):
        N = 'EFFEC/Stock/NAVE2/'
        casos = [
            (('00006 - L01 P19 C2', N + '00006 - L01 P19 C2', 'L01 P19 C2'), ('hueco', 1, 19, 2, True)),
            (('00999 - L121 P03 C7', N + '00999 - L121 P03 C7', ''), ('hueco', 121, 3, 7, True)),     # sin código
            (('KO_110626_032', N + 'x/KO_110626_032', ''), ('contenedor', None, None, None, True)),
            (('MU-05', N + 'MU-05', 'MU-05'), ('muelle', None, None, None, True)),
            (('N1-L05', N + 'N1-L05', 'N1-L05 P01 C1'), ('n1', None, None, None, True)),
            (('SORTER', 'EFFEC/SORTER', 'SORTER'), ('otra', None, None, None, False)),
            (('NAVE2', 'EFFEC/Stock/NAVE2', ''), ('otra', None, None, None, True)),
        ]
        for args, (tipo, lineal, pos, nivel, nave) in casos:
            with self.subTest(args=args):
                r = U.clasificar(*args)
                self.assertEqual((r['tipo'], r['lineal'], r['posicion'], r['nivel'], r['en_nave']),
                                 (tipo, lineal, pos, nivel, nave))
        self.assertEqual(U.texto_hueco(3, 5, 4), 'L03 P05 C4')


class Productos(unittest.TestCase):

    def test_codigo_familia_zona(self):
        self.assertEqual(P.partir_codigo('2621JA67-NEGRO-M', ''), ('2621JA67', 'NEGRO', 'M'))
        self.assertEqual(P.partir_codigo('', '[2621JA67-NEGRO-XL-2] Chaqueta'), ('2621JA67', 'NEGRO', 'XL-2'))
        self.assertEqual(P.familia('2621JA67'), 'JA')
        self.assertEqual(P.familia('RARO'), '')
        self.assertEqual(P.nombre_temporada([7, ' i27 ']), 'I27')
        self.assertEqual([P.zona(t) for t in ('I27', 'V27', 'I25', '')], ['0', '0', 'Z', P.SIN_TEMPORADA])

    def test_litros_de_kpi(self):
        tabla = P.litros_por_familia()
        self.assertEqual(tabla['JA'], 8.4)          # kpi.py TIPOS
        self.assertEqual(P.litros(0.0084, 'JA'), (8.4, False))
        self.assertEqual(P.litros(0, 'JA'), (8.4, True))
        self.assertEqual(P.litros(None, ''), (None, True))


class Descargar(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def test_primera_sin_fecha_para(self):
        with self.assertRaises(ValueError):
            descargar(self.dir)
        self.assertEqual(list(self.dir.glob('*')), [])

    def test_copia_completa(self):
        ruta, res, avisos, texto = descargar(self.dir, desde=datetime.date(2026, 11, 1))
        self.assertEqual(ruta.name, '20261123_0900_odoo.sqlite')
        self.assertTrue(ruta.with_suffix('.resumen.txt').exists())
        bd = sqlite3.connect(ruta)
        self.assertEqual(res['filas']['stock'], 13)
        self.assertEqual(res['filas']['productos'], 5)
        self.assertEqual(res['filas']['salidas'], 23)                      # días 0..22 (desde el 01/11)
        # contenedor -> su hueco; el del muelle no tiene hueco
        self.assertEqual(bd.execute('SELECT hueco_id FROM ubicaciones WHERE id = 100').fetchone()[0], 10)
        self.assertIsNone(bd.execute('SELECT hueco_id FROM ubicaciones WHERE id = 104').fetchone()[0])
        x = res['raro']
        self.assertEqual(x['nombres_en_nave_que_no_encajan']['n'], 2)       # NAVE2 y «PASILLO RARO»
        self.assertEqual(x['contenedores_sin_hueco_padre']['n'], 1)
        self.assertEqual(x['huecos_con_mas_de_4_niveles'][0][:2], ['L121 P01', 6])
        self.assertEqual(x['productos_sin_temporada']['uds'], 8)
        self.assertEqual(x['stock_negativo'], {'filas': 1, 'uds': -2})
        self.assertEqual(x['contenedores_activos_a_cero'], 1)               # KO_110626_002
        self.assertEqual(x['productos_sin_volumen_ni_familia'], 1)
        self.assertEqual(res['uds_por_zona']['0'], 10 + 4 + 6 + 3 + 2 + 1 + 9 + 7)
        self.assertIn('Comparación con el Excel', texto)
        self.assertEqual(avisos, [])
        # tipo de cada línea sacado de su albarán; la de MODALADA (id 999) no se baja
        self.assertEqual(bd.execute('SELECT COUNT(*) FROM salidas WHERE tipo_operacion_id IS NULL').fetchone()[0], 0)
        self.assertIsNone(bd.execute('SELECT id FROM salidas WHERE id = 999').fetchone())
        self.assertEqual(dict(bd.execute('SELECT tipo_operacion_id, COUNT(*) FROM salidas GROUP BY 1')), {1: 18, 2: 5})

    def test_nunca_sobrescribe(self):
        descargar(self.dir, desde=datetime.date(2026, 11, 1))
        with self.assertRaises(FileExistsError):
            descargar(self.dir, desde=datetime.date(2026, 11, 1))
        self.assertEqual(len(copias_completas(self.dir)), 1)

    def test_incremental(self):
        descargar(self.dir, desde=datetime.date(2026, 11, 1))
        falso = OdooFalso()
        nueva = falso.datos['stock.move.line'][0].copy()
        nueva.update(id=5000, date='2026-11-24 10:00:00')
        falso.datos['stock.move.line'].append(nueva)
        ruta, res, avisos, _ = descargar(self.dir, ahora=HOY + datetime.timedelta(days=1), cliente=falso)
        self.assertEqual(res['filas']['salidas'], 24)
        self.assertEqual(avisos, [])
        # solo se piden a Odoo las líneas desde la descarga anterior menos el margen
        fechas = [c[2] for m, met, a, k in falso.registro if m == 'stock.move.line' and met == 'search_read'
                  for c in a[0] if c[0] == 'date']
        self.assertTrue(fechas and all(f.startswith('2026-11-20') for f in fechas), fechas)
        self.assertEqual(len(copias_completas(self.dir)), 2)

    def test_incremental_avisa_si_no_cuadra(self):
        descargar(self.dir, desde=datetime.date(2026, 11, 1))
        falso = OdooFalso()
        vieja = falso.datos['stock.move.line'][0].copy()
        vieja.update(id=6000, date='2026-11-02 10:00:00')     # hecha «antes» de la última descarga, no la ve
        falso.datos['stock.move.line'].append(vieja)
        _, _, avisos, _ = descargar(self.dir, ahora=HOY + datetime.timedelta(days=1), cliente=falso)
        self.assertTrue(avisos and '--completa' in avisos[0])

    def test_sin_salidas_copia_las_anteriores(self):
        descargar(self.dir, desde=datetime.date(2026, 11, 1))
        falso = OdooFalso()
        _, res, _, _ = descargar(self.dir, ahora=HOY + datetime.timedelta(hours=1), cliente=falso, con_salidas=False)
        self.assertEqual(res['filas']['salidas'], 23)
        self.assertFalse([r for r in falso.registro if r[0] == 'stock.move.line'])

    def test_solo_lectura(self):
        falso = OdooFalso()
        descargar(self.dir, cliente=falso, desde=datetime.date(2026, 11, 1))
        self.assertTrue({r[1] for r in falso.registro} <= {'search_read', 'read', 'search_count', 'fields_get'})


if __name__ == '__main__':
    unittest.main()


class ReglasDel23_11(unittest.TestCase):
    """Lo que enseñó la primera descarga real (23/11/2026)."""

    def test_codigos_antiguos_y_ean(self):
        self.assertEqual(P.partir_codigo('8445514658309', '001-3-000003-36'), ('001-3', '000003', '36'))
        self.assertEqual(P.partir_codigo(None, 'KRMP03-9333-000003-36'), ('KRMP03-9333', '000003', '36'))
        self.assertEqual(P.partir_codigo(None, '2621zc01-000019-85'), ('2621ZC01', '000019', '85'))
        self.assertEqual(P.familia('2621ZC01'), 'ZC')
        self.assertEqual(P.zona('PERMANENTE'), P.ZONA_Z)          # decisión de Isaac, 23/11

    def test_solo_la_nave2_de_effec(self):
        self.assertFalse(U.clasificar('KO_1', 'TARKO/Stock/NAVE2/KO_1', '')['en_nave'])
        self.assertTrue(U.clasificar('KO_1', 'EFFEC/Stock/NAVE2/KO_1', '')['en_nave'])
        self.assertEqual(U.clasificar('PERCHAS_KO', 'EFFEC/Stock/NAVE2/PERCHAS_KO', '')['tipo'], 'perchas')

    def test_hijo_de_hueco_es_contenedor(self):
        falso = OdooFalso()
        N = 'EFFEC/Stock/NAVE2'
        falso.datos['stock.location'].append({'id': 400, 'name': 'GC_SS22_001', 'complete_name': N + '/x/GC_SS22_001',
                                              'location_id': [10, 'x'], 'barcode': False, 'active': True})
        ruta, *_ = Descarga(falso, tempfile.mkdtemp(), avisar=lambda *_: None, ahora=HOY).ejecutar(
            desde=datetime.date(2026, 11, 1))
        fila = sqlite3.connect(ruta).execute('SELECT tipo, hueco_id FROM ubicaciones WHERE id = 400').fetchone()
        self.assertEqual(fila, ('contenedor', 10))


class MapaJSON(unittest.TestCase):
    """Datos del mapa desde la copia inventada (sin Odoo)."""

    def test_generar(self):
        import json
        from redistrib import mapa_json
        d = Path(tempfile.mkdtemp())
        ruta, *_ = descargar(d, desde=datetime.date(2026, 10, 1))
        raiz = Path(__file__).resolve().parents[2]
        datos, tam = mapa_json.generar(ruta, raiz / 'prototipo-mapa_2026-11-23_v2', d)
        self.assertEqual(set(tam), {'datos.json', 'huecos.json', 'modelos.json', 'listas.json'})
        pos = {(p['l'], p['p']): p for p in datos['posiciones']}
        p = pos[('L01', 1)]
        self.assertEqual([n[0] for n in p['niv']], [1, 2, 3, 4])
        self.assertEqual(p['u'], 10 + 5 + 4)                     # KO_110626_001 (C1) + suelto en C2
        self.assertEqual(p['niv'][0][3:5], [1, 2])               # C1: 1 contenedor con stock, 2 activos
        self.assertEqual(p['zona'], 'M')                         # 14 de zona 0 y 5 de Z: la Z pasa del 10 %
        modelos = json.loads((d / 'modelos.json').read_text(encoding='utf-8'))
        self.assertEqual(modelos['2621JA67-NEGRO'][0], 2)        # L01 y L02
        listas = json.loads((d / 'listas.json').read_text(encoding='utf-8'))
        self.assertIn('KO_110626_002', [r[0] for r in listas['l2']['filas']])
        tipos5 = {r[1] for r in listas['l5']['filas']}
        self.assertTrue({'muelle', 'n1', 'otra'} <= tipos5, tipos5)
        self.assertGreater(datos['posiciones'][0]['v'] + sum(p['v'] for p in datos['posiciones']), 0)
