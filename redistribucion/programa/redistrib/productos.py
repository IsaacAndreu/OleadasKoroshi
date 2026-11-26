# -*- coding: utf-8 -*-
"""Modelo, color, talla, familia, temporada, zona y litros de un producto. Funciones puras.

- Código «MODELO-COLOR-TALLA» (como odoo/KOROSHI_exportar_tallas_MASTER_SHELL_2026-11-20.py l. 97–106):
  de default_code y, si no hay, de la primera palabra del nombre sin corchetes.
- Familia: letras 5 y 6 del modelo (RE_TIPO de koroshi_kpi/models/kpi.py): 2621JA67 -> JA.
- Temporada: nombre de product.template.season_id (modelo style.season). Zona 0 = TEMPORADAS_ACTUALES.
- Litros: volume (m³) de la ficha × 1000; si es 0 o no hay, litros medios de la familia de la tabla TIPOS
  de kpi.py (se lee del fichero, no se copia) y se marca como estimado.
"""
import ast
import re
from pathlib import Path

from . import configuracion

TEMPORADAS_ACTUALES = ('I27', 'V27')      # bin/KOROSHI_crear_INT_zonas_PLANIFICADA.py l. 56
# PERMANENTE (54.449 uds el 23/11: perchas, bolsas, suministros y básicos) va en zona Z: lo decidió Isaac el
# 23/11/2026. Ojo: el Excel del 06/11 la contaba en zona 0, así que las zonas de hoy no se comparan tal cual.
TEMPORADAS_PERMANENTES = ('PERMANENTE',)
ZONA_0, ZONA_Z, SIN_TEMPORADA = '0', 'Z', 'sin temporada'
RE_FAMILIA = re.compile(r'^\d{4}([A-Z]{2})')
RUTA_KPI = configuracion.CARPETA.parents[1] / 'odoo' / 'modulos' / 'koroshi_kpi' / 'models' / 'kpi.py'

_litros_familia = None


def litros_por_familia(ruta=RUTA_KPI):
    """{familia: litros} de la tabla TIPOS de kpi.py, leída con ast (kpi.py importa odoo y no se puede importar)."""
    global _litros_familia
    if _litros_familia is None or ruta != RUTA_KPI:
        arbol = ast.parse(Path(ruta).read_text(encoding='utf-8'))
        for nodo in arbol.body:
            if isinstance(nodo, ast.Assign) and any(getattr(t, 'id', '') == 'TIPOS' for t in nodo.targets):
                tabla = {k: v[2] for k, v in ast.literal_eval(nodo.value).items()}
                if ruta != RUTA_KPI:
                    return tabla
                _litros_familia = tabla
                break
        else:
            raise ValueError('No se encuentra TIPOS en %s' % ruta)
    return _litros_familia


RE_COLOR_ANTIGUO = re.compile(r'^\d{6}$')


def partir_codigo(default_code, nombre):
    """(modelo, color, talla), en mayúsculas.

    - Normal: «2621JA67-NEGRO-M» -> ('2621JA67', 'NEGRO', 'M'); la talla se queda con el resto («XL-2»).
    - Si la referencia es un EAN (solo cifras) o no hay, se usa la primera palabra del nombre (descarga del 23/11:
      15.725 productos antiguos con referencia = EAN y nombre «001-3-000003-36»).
    - Formato antiguo, con color de 6 cifras en penúltimo lugar: «001-3-000003-36» -> ('001-3', '000003', '36'),
      «KRMP03-9333-000003-36» -> ('KRMP03-9333', '000003', '36').
    """
    codigo = (default_code or '').strip()
    if not codigo or codigo.isdigit():
        codigo = (nombre or '').split(' ')[0].strip('[]') if nombre else codigo
    t = codigo.upper().split('-')
    if len(t) >= 4 and RE_COLOR_ANTIGUO.match(t[-2]):
        return '-'.join(t[:-2]), t[-2], t[-1]
    return t[0], (t[1] if len(t) > 1 else ''), '-'.join(t[2:])


def familia(modelo):
    m = RE_FAMILIA.match(modelo or '')
    return m.group(1) if m else ''


def nombre_temporada(season_id):
    """season_id de XML-RPC: [id, 'I27'] o False."""
    if not season_id:
        return ''
    return str(season_id[1] if isinstance(season_id, (list, tuple)) else season_id).strip().upper()


def zona(temporada):
    if not temporada:
        return SIN_TEMPORADA
    return ZONA_0 if temporada in TEMPORADAS_ACTUALES else ZONA_Z


def litros(volumen_m3, fam, tabla=None):
    """(litros por prenda, estimado). Ficha si > 0; si no, media de la familia; si tampoco, (None, True)."""
    if volumen_m3 and volumen_m3 > 0:
        return round(volumen_m3 * 1000.0, 3), False
    tabla = litros_por_familia() if tabla is None else tabla
    return tabla.get(fam), True
