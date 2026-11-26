# -*- coding: utf-8 -*-
"""De dónde salen los datos del programa (26/11/2026).

Las matrices son los Excels de KOROSHI en bin/versiones, con nombre AAMMDD_KOROSHI_<n>_<nombre>_v<versión>.xlsx.
De cada matriz (mismo número y nombre) se usa la versión más alta: si alguien saca una nueva, el programa la coge
sin tocar nada. Los Excels solo se leen; nunca se escriben.
"""
import dataclasses
import re
from pathlib import Path

from . import configuracion

CARPETA_MATRICES = configuracion.CARPETA.parent.parent / 'bin' / 'versiones'
RE_MATRIZ = re.compile(r'^(\d{6})_KOROSHI_(\d+)_(.+?)_v(\d+)\.xlsx$', re.I)

# Para qué usa hoy el programa cada matriz (por número). Lo que no está aquí se lista, pero aún no se usa.
USO = {
    1: 'Litros por unidad de cada modelo (hoja «MASTER por modelo»): tamaño y volumen en la compactación',
}


@dataclasses.dataclass
class Matriz:
    numero: int
    nombre: str
    version: int
    fecha: str            # dd/mm/aaaa, del nombre del fichero
    ruta: Path
    anteriores: int       # versiones más antiguas que hay en la carpeta

    @property
    def uso(self):
        return USO.get(self.numero, 'Todavía no la usa ningún cálculo')


def matrices(carpeta=CARPETA_MATRICES):
    """Última versión de cada matriz KOROSHI de la carpeta, ordenadas por número."""
    grupos = {}
    for f in Path(carpeta).glob('*.xlsx'):
        m = RE_MATRIZ.match(f.name)
        if not m or f.name.startswith('~$'):
            continue
        fecha, num, nombre, ver = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
        grupos.setdefault((num, nombre.lower()), []).append((ver, fecha, nombre, f))
    res = []
    for (num, _), vs in grupos.items():
        vs.sort()
        ver, fecha, nombre, f = vs[-1]
        res.append(Matriz(num, nombre.replace('_', ' '), ver, '%s/%s/20%s' % (fecha[4:6], fecha[2:4], fecha[0:2]),
                          f, len(vs) - 1))
    return sorted(res, key=lambda m: (m.numero, m.nombre))


def matriz(numero, carpeta=CARPETA_MATRICES):
    """La última versión de la matriz con ese número, o None."""
    return next((m for m in matrices(carpeta) if m.numero == numero), None)


def hojas(ruta):
    """Nombres de las hojas de un Excel (solo lectura)."""
    import openpyxl
    wb = openpyxl.load_workbook(ruta, read_only=True)
    try:
        return [ws.title for ws in wb.worksheets]
    finally:
        wb.close()
