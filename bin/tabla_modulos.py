# -*- coding: utf-8 -*-
"""
KOROSHI - tabla_modulos.py (23/11/2026, revision general O10)

Rehace la tabla «Mapa de modulos» del README.md a partir de los __manifest__.py de odoo/modulos (version, summary y
dependencias propias), entre las marcas <!-- tabla-modulos --> y <!-- /tabla-modulos -->. Asi la tabla no se queda
vieja: se pasa despues de sacar versiones.

Uso (desde la raiz del repositorio):
    python bin/tabla_modulos.py            # reescribe el README
    python bin/tabla_modulos.py --ver      # solo la ensena, sin tocar el README

Solo lee los manifest y escribe README.md.
"""
import ast
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULOS = os.path.join(RAIZ, 'odoo', 'modulos')
README = os.path.join(RAIZ, 'README.md')
INICIO = '<!-- tabla-modulos -->'
FIN = '<!-- /tabla-modulos -->'
PROPIOS = ('koroshi_', 'oriola_', 'tuctuc_')


def corta(v):
    return v[5:] if v.startswith('13.0.') else v


def fila(nombre):
    with open(os.path.join(MODULOS, nombre, '__manifest__.py'), encoding='utf-8') as f:
        m = ast.literal_eval(f.read())
    deps = [d.replace('koroshi_', '') for d in m.get('depends') or [] if d.startswith(PROPIOS)]
    resumen = ' '.join((m.get('summary') or m.get('name') or '').split()).replace('|', '/')
    return '| `%s` | %s | %s | %s |' % (nombre, corta(m.get('version', '?')), resumen, ', '.join(deps) or '—')


def tabla():
    nombres = sorted(d for d in os.listdir(MODULOS) if os.path.isfile(os.path.join(MODULOS, d, '__manifest__.py')))
    lineas = [INICIO,
              '| Módulo | Versión (repo) | Qué hace (summary del manifest) | Depende de (propios) |',
              '|---|---|---|---|']
    lineas += [fila(n) for n in nombres]
    lineas.append(FIN)
    return '\n'.join(lineas), len(nombres)


def main(argv):
    texto, n = tabla()
    if '--ver' in argv:
        print(texto)
        return 0
    with open(README, encoding='utf-8') as f:
        readme = f.read()
    if INICIO not in readme or FIN not in readme:
        print('README.md no tiene las marcas %s ... %s: no se toca.' % (INICIO, FIN))
        return 1
    antes, resto = readme.split(INICIO, 1)
    despues = resto.split(FIN, 1)[1]
    with open(README, 'w', encoding='utf-8', newline='\n') as f:
        f.write(antes + texto + despues)
    print('README.md: tabla de %d modulos al dia.' % n)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
