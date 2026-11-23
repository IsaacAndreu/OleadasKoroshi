"""Saca datos.json del Excel MASTER de zonas del 06/11/2026 para el prototipo del mapa.

Solo lee el Excel (openpyxl). No se conecta a Odoo ni al servidor.

    python extraer_datos.py            (desde esta carpeta)

Qué sale y de dónde (detalle en README.md):
  - posiciones[]: una por posición física (lineal + Pnn), con la zona de HOY (hoja «Layout hoy», texto de la
    celda) y la zona del PLAN Z5+01 (hoja «Layout compactado Z5+01», que solo lleva COLOR de celda: se traduce el
    color a categoría con la leyenda de la propia hoja).
  - lineales{}: las medidas de la hoja «Por lineal» (una fila por lineal; no hay detalle por posición ni nivel).
  - geometria: copia de _x, _y, BASE y CRUCES de odoo/modulos/koroshi_kpi/models/kpi.py (copiada, no importada).
  - ejemplo{}: DATOS DE EJEMPLO (contenedores de un hueco, modelos y flechas de movimientos). No son reales.
"""
import json
import os
import re

import openpyxl

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.normpath(os.path.join(AQUI, '..', '..'))
EXCEL = os.path.join(RAIZ, 'bin', 'versiones', '20261106_1630_MASTER-zonas-0-y-Z-layout-estanterias-cajas_v1.xlsx')
SALIDA = os.path.join(AQUI, 'datos.json')

# --- Geometría copiada de koroshi_kpi/models/kpi.py (23/11/2026) -------------------------------------------
BASE = (26.0, 30.0)             # salida y vuelta (expediciones / SORTER)
CRUCES = (7.75, 30.0, 44.25)    # pasillos transversales


def _x(lineal):
    return 30 + 2 * (lineal // 2) - 0.5


def _y_kpi(pos):
    """Igual que kpi._y (aplasta todo lo que pasa de P36 en P36)."""
    if pos <= 17:
        if pos == 0:
            return 29.3
        if pos <= 3:
            return 2 + (pos - 0.5) * 1.5
        return 9 + (pos - 3.5) * (20.0 / 14)
    pos = min(pos, 36)
    if pos <= 24:
        return 31 + (pos - 17.5) * (12.0 / 7)
    return 45.5 + (pos - 24.5) * (12.5 / 12)


# Fin de la copia. Lo de abajo es del prototipo.

def _paso(pos):
    """Largo de la celda en metros = distancia entre centros del tramo de _y (la función solo da centros)."""
    if pos == 0:
        return 0.6          # SUPUESTO: P00 está en el pasillo central (29,3 m) y _y no dice cuánto mide
    if pos <= 3:
        return 1.5
    if pos <= 17:
        return 20.0 / 14
    if pos <= 24:
        return 12.0 / 7
    return 12.5 / 12


def _y(pos):
    """_y de kpi.py, pero P37-P42 (existen en el Excel) siguen con el mismo paso en vez de pisar P36."""
    if pos <= 36:
        return _y_kpi(pos)
    return _y_kpi(36) + (pos - 36) * (12.5 / 12)


PROF = 0.40     # fondo de la estantería en metros (hoja «Medidas estanterias»: 120 x 160 x 40 cm)


def _x_celda(lineal):
    """Franja x de la estantería del lineal. _x da el centro del PASILLO del par (L02-L03 comparten pasillo):
    el lineal par queda a la izquierda del pasillo y el impar a la derecha, cada uno con 40 cm de fondo y la
    espalda a 1 m del centro (módulo de 2 m = pasillo de 1,2 m + dos fondos de 40 cm). El reparto par/impar y
    el ancho del pasillo son SUPUESTOS: kpi.py solo da el centro."""
    c = _x(lineal)
    if lineal % 2 == 0:
        return (c - 1.0, c - 1.0 + PROF)
    return (c + 1.0 - PROF, c + 1.0)


# --- Colores de las hojas de layout -> categoría -----------------------------------------------------------
# Leyenda escrita en las hojas (filas de abajo). Las dos marcadas «sin leyenda» se deducen del tono.
COLOR_PLAN = {
    '002563EB': '0',             # zona 0 (posición que hoy tiene algo)
    '00BFDBFE': '0 libre',       # zona 0 / hueco vacío hoy
    '00EA580C': 'Z',             # zona Z
    '00FED7AA': 'Z libre',       # sin leyenda: naranja claro = hueco de Z vacío hoy (como el azul claro de la 0)
    '00DCFCE7': 'libre',         # libre (la leyenda pinta 16A34A; las celdas llevan el verde claro DCFCE7)
    '00CA8A04': 'muelle',        # muelle
    '00FEF3C7': 'muelle vacío',  # sin leyenda: amarillo claro en filas de muelle
}
NO_EXISTE = '00000000'           # sin relleno = la posición no existe en ese lineal
VACIA_HOY = '00E5E7EB'           # gris = posición que existe y está vacía hoy


def _num(v):
    return None if v is None or v == '' else float(v)


def leer():
    wb = openpyxl.load_workbook(EXCEL)          # con estilos: hace falta el color de celda
    wbv = openpyxl.load_workbook(EXCEL, data_only=True)

    hoy = wb['Layout hoy']
    plan = wb['Layout compactado Z5+01']
    cab = [c.value for c in hoy[1]]
    cab_plan = [c.value for c in plan[1]]
    assert cab == cab_plan, 'las dos hojas de layout no tienen las mismas columnas'

    plan_por_lineal = {}
    for fila in plan.iter_rows(min_row=2):
        nom = fila[0].value
        if nom and re.match(r'^(L\d+|MU-\d+)$', str(nom)):
            plan_por_lineal[nom] = fila

    posiciones = []
    sin_traducir = {}
    for fila in hoy.iter_rows(min_row=2):
        nom = fila[0].value
        if not nom or not re.match(r'^(L\d+|MU-\d+)$', str(nom)):
            continue
        muelle = nom.startswith('MU-')
        num = int(nom.split('-')[1]) if muelle else int(nom[1:])
        fplan = plan_por_lineal[nom]
        for i in range(2, len(cab)):
            celda = fila[i]
            color = celda.fill.fgColor.rgb
            if color == NO_EXISTE and celda.value is None:
                continue
            pos = int(cab[i][1:])
            if celda.value in ('0', 'Z', 'M'):
                zona = celda.value
            elif color == VACIA_HOY:
                zona = 'vacía'
            else:
                zona = str(celda.value)
            cp = fplan[i].fill.fgColor.rgb
            zplan = COLOR_PLAN.get(cp)
            if zplan is None:
                sin_traducir[cp] = sin_traducir.get(cp, 0) + 1
                zplan = 'sin dato'
            p = {'l': nom, 'p': pos, 'zona': zona, 'plan': zplan}
            if muelle:
                # El muelle no tiene geometría en kpi.py: se dibuja aparte, a la derecha de la nave (SUPUESTO).
                x0 = 172 + num * 1.4
                p.update(x0=round(x0, 3), x1=round(x0 + 1.0, 3), y0=round(2 + pos * 1.25, 3),
                         y1=round(2 + pos * 1.25 + 1.1, 3), muelle=True)
            else:
                x0, x1 = _x_celda(num)
                yc, paso = _y(pos), _paso(pos)
                p.update(x0=round(x0, 3), x1=round(x1, 3), y0=round(yc - paso / 2 + 0.05, 3),
                         y1=round(yc + paso / 2 - 0.05, 3))
            posiciones.append(p)
    if sin_traducir:
        print('AVISO: colores del plan sin traducir:', sin_traducir)

    # --- Por lineal ---
    pl = wbv['Por lineal']
    cab_l = [c.value for c in pl[1]]
    lineales = {}
    for fila in pl.iter_rows(min_row=2, values_only=True):
        if not fila[0]:
            continue
        d = dict(zip(cab_l, fila))
        uds, ocup = _num(d['Uds']) or 0, _num(d['Posiciones ocupadas']) or 0
        lineales[d['Lineal']] = {
            'posiciones': _num(d['Posiciones (Odoo)']),
            'ubicaciones': _num(d['Ubicaciones Odoo']),
            'ocupadas': ocup,
            'pct_ocupacion': _num(d['% ocupacion']),
            'uds': uds,
            'uds_0': _num(d['Uds zona 0']),
            'uds_z': _num(d['Uds zona Z']),
            'uds_otras': _num(d['Uds otras']),
            'pct_0': _num(d['% zona 0']),
            'pct_z': _num(d['% zona Z']),
            'zona': d['ZONA HOY'],
            'sku': _num(d['SKU']),
            'modelos_color': _num(d['Modelos-color']),
            'litros': _num(d['Litros (estimados)']),
            'uds_por_pos_ocupada': round(uds / ocup, 1) if ocup else None,
            'temporadas': d['Temporadas principales (uds)'],
            'mover_p1': _num(d['Uds a mover P1']),
            'mover_p2': _num(d['Uds a mover P2']),
        }
    return posiciones, lineales


def ejemplo(posiciones):
    """DATOS DE EJEMPLO. Inventados a propósito para enseñar cómo se vería; no salen de Odoo ni del Excel."""
    contenedores = [
        {'nombre': 'KO_EJEMPLO_001', 'modelo': 'MODELO-EJEMPLO-A', 'color': 'NEGRO', 'tallas': 'S-M-L', 'uds': 14},
        {'nombre': 'KO_EJEMPLO_002', 'modelo': 'MODELO-EJEMPLO-A', 'color': 'BLANCO', 'tallas': 'M', 'uds': 6},
        {'nombre': 'TT_EJEMPLO_003', 'modelo': 'MODELO-EJEMPLO-B', 'color': 'AZUL', 'tallas': 'XS-S', 'uds': 9},
        {'nombre': 'KO_EJEMPLO_004', 'modelo': 'MODELO-EJEMPLO-C', 'color': 'ROJO', 'tallas': 'L-XL', 'uds': 3},
    ]
    # Modelos de ejemplo repartidos por varios lineales (el problema que se quiere resolver).
    modelos = {
        'MODELO-EJEMPLO-A': [('L03', 5), ('L03', 6), ('L44', 12), ('L87', 30), ('L110', 21)],
        'MODELO-EJEMPLO-B': [('L12', 9), ('L13', 9), ('L60', 2)],
        'MODELO-EJEMPLO-C': [('L95', 15), ('L120', 33)],
    }
    # Flechas de ejemplo: de una posición con Z hoy en un lineal de zona 0/MIXTO a una posición «Z libre» del plan.
    origen = [p for p in posiciones if p['zona'] == 'Z' and not p.get('muelle') and int(p['l'][1:]) >= 61]
    destino = [p for p in posiciones if p['plan'] == 'Z libre']
    paso_o = max(1, len(origen) // 8)
    paso_d = max(1, len(destino) // 8)
    flechas = []
    for k in range(8):
        if k * paso_o < len(origen) and k * paso_d < len(destino):
            o, d = origen[k * paso_o], destino[k * paso_d]
            flechas.append({'de': [o['l'], o['p']], 'a': [d['l'], d['p']]})
    return {
        'aviso': 'DATOS DE EJEMPLO: inventados para enseñar el formato. No son de Odoo ni del Excel.',
        'contenedores_hueco': contenedores,
        'modelos': {m: [list(x) for x in v] for m, v in modelos.items()},
        'flechas': flechas,
    }


def main():
    posiciones, lineales = leer()
    datos = {
        'fuente': os.path.basename(EXCEL),
        'fecha_datos': '06/11/2026 (stock de Odoo de ese día, según la hoja Criterios)',
        'geometria': {
            'base': BASE, 'cruces': CRUCES, 'fondo_estanteria': PROF,
            'nota': 'Copia de koroshi_kpi/models/kpi.py: _x (centro del pasillo por par de lineales), _y (centro '
                    'de la posición), BASE y CRUCES. Supuestos del prototipo: lado par/impar, 40 cm de fondo, '
                    'P00 de 0,6 m, P37-P42 siguiendo el paso de P25-P36 y el muelle dibujado aparte.',
        },
        'posiciones': posiciones,
        'lineales': lineales,
        'ejemplo': ejemplo(posiciones),
    }
    with open(SALIDA, 'w', encoding='utf-8') as f:
        json.dump(datos, f, ensure_ascii=False, separators=(',', ':'))
    n_l = len({p['l'] for p in posiciones})
    print(f'{SALIDA}: {len(posiciones)} posiciones en {n_l} lineales/muelles, {len(lineales)} filas por lineal')


if __name__ == '__main__':
    main()
