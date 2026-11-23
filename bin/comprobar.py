# -*- coding: utf-8 -*-
"""
KOROSHI - comprobar.py (17/11/2026)

Convierte en comprobaciones las trampas que ya nos han roto algo (CLAUDE.md, reglas 2, 7 y 9). Si falla, NO se
empaqueta: empaquetar.py lo llama antes de crear la etiqueta.

Uso (desde la raiz del repositorio):
    python bin/comprobar.py                     # todos los modulos de odoo/modulos
    python bin/comprobar.py koroshi_zonas ...   # solo esos

ERRORES (paran):
  E1 aria-hidden="true" en una vista o un JS: Odoo 13 tiene una regla global display:none (usar role="presentation").
  E2 'display_notification' como accion: no existe en Odoo 13.
  E3 report_name de un informe QWeb sin punto (modulo.plantilla): 'Invalid template id' en el PDF (10/11).
  E4 Campo nuevo en stock.picking, stock.picking.type o stock.move.line sin aprobar (no_overscan tumbo la PDA el
     03/11). Los aprobados estan en bin/campos_compartidos_aprobados.txt: solo se anade uno despues de preguntar.
  E5 Modulo cambiado desde su ultima etiqueta y version sin subir (nunca se sobrescribe una version).
  E6 Version nueva sin su linea de historial en el manifest: 'vX.Y.Z (dd/mm/aaaa): ...'.
  E7 Un .py que no compila.
  E8 groups="grupo" sin el modulo delante dentro de una vista (arch): «External ID must be fully qualified» y no se
     actualiza (koroshi_menu 2.6.0, 19/11). En un <menuitem> si vale sin modulo.
  E9 Campo de Odoo con una coma al final («campo = fields.X(...),»): queda como tupla y Odoo no crea el campo; solo
     lo dice en el log («Trailing comma after field definition»). koroshi_recepcion 1.0.0, teorico_ids, 23/11.
AVISOS (no paran):
  A1 <function> dentro de noupdate="1": solo corre al INSTALAR, no al actualizar.

Solo lee ficheros y git; no toca nada.
"""
import ast
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULOS = os.path.join(RAIZ, 'odoo', 'modulos')
APROBADOS = os.path.join(RAIZ, 'bin', 'campos_compartidos_aprobados.txt')
TABLAS_COMPARTIDAS = ('stock.picking', 'stock.picking.type', 'stock.move.line')
SALTAR_DIRS = ('__pycache__', '.git', 'node_modules')

RE_ARIA = re.compile(r"""aria-hidden\s*=\s*["']true|aria-hidden["']\s*,\s*["']?true""", re.I)
RE_DISPLAY_NOTIF = re.compile(r"""["']display_notification["']""")
RE_ALTER = re.compile(r'ALTER\s+TABLE\s+(stock_picking_type|stock_picking|stock_move_line)\s+ADD', re.I)
RE_COMENT_XML = re.compile(r'<!--.*?-->', re.S)
RE_COMENT_JS = re.compile(r'/\*.*?\*/|(?<![:\w])//[^\n]*', re.S)   # /* */ y // (no el // de http://)


def ficheros(modulo):
    base = os.path.join(MODULOS, modulo)
    for raiz, dirs, nombres in os.walk(base):
        dirs[:] = [d for d in dirs if d not in SALTAR_DIRS]
        for n in nombres:
            ruta = os.path.join(raiz, n)
            yield ruta, os.path.relpath(ruta, RAIZ).replace('\\', '/')


def leer(ruta):
    with open(ruta, encoding='utf-8', errors='replace') as f:
        return f.read()


def linea_de(texto, pos):
    return texto.count('\n', 0, pos) + 1


def sin_comentarios(texto, coment):
    # Mantiene los saltos de linea para que los numeros de linea sigan valiendo
    return coment.sub(lambda m: '\n' * m.group(0).count('\n'), texto)


def git(*args):
    r = subprocess.run(['git'] + list(args), cwd=RAIZ, capture_output=True)
    return r.returncode, r.stdout.decode('utf-8', 'replace').strip()


def clave_version(v):
    return tuple(int(p) if p.isdigit() else p for p in re.split(r'[.]', v))


def version_corta(v):
    return v[5:] if v.startswith('13.0.') else v


def variantes(corta):
    """Formas en que el historial nombra una version: 1.4.0, 1.4 o (warehouse_map) 20261116.46."""
    vs = {corta}
    v = corta
    while v.endswith('.0') and v.count('.') > 1:
        v = v[:-2]
        vs.add(v)
    partes = corta.split('.')
    if len(partes) > 2:
        vs.add('.'.join(partes[-2:]))
    return vs


def aprobados():
    if not os.path.exists(APROBADOS):
        return set()
    return {l.split('#')[0].strip() for l in leer(APROBADOS).splitlines() if l.split('#')[0].strip()}


def modelos_heredados(clase):
    """(_inherit, _name) de una clase Odoo, o (None, None)."""
    hereda, nombre = None, None
    for nodo in clase.body:
        if isinstance(nodo, ast.Assign) and len(nodo.targets) == 1 and isinstance(nodo.targets[0], ast.Name):
            try:
                valor = ast.literal_eval(nodo.value)
            except Exception:
                continue
            if nodo.targets[0].id == '_inherit':
                hereda = [valor] if isinstance(valor, str) else list(valor)
            elif nodo.targets[0].id == '_name':
                nombre = valor
    return hereda, nombre


def campos_compartidos(texto):
    """[(modelo, campo, linea)] de los fields.X(...) declarados en clases que heredan una tabla compartida."""
    salida = []
    for clase in [n for n in ast.walk(ast.parse(texto)) if isinstance(n, ast.ClassDef)]:
        hereda, nombre = modelos_heredados(clase)
        if not hereda:
            continue
        for modelo in hereda:
            if modelo not in TABLAS_COMPARTIDAS or (nombre and nombre != modelo):
                continue
            for nodo in clase.body:
                if (isinstance(nodo, ast.Assign) and isinstance(nodo.value, ast.Call)
                        and isinstance(nodo.value.func, ast.Attribute)
                        and isinstance(nodo.value.func.value, ast.Name) and nodo.value.func.value.id == 'fields'):
                    for t in nodo.targets:
                        if isinstance(t, ast.Name):
                            salida.append((modelo, t.id, nodo.lineno))
    return salida


def campos_con_coma(texto):
    """[(campo, linea)] de las clases con «campo = fields.X(...),» (tupla de un solo fields.X): E9."""
    salida = []
    for clase in [n for n in ast.walk(ast.parse(texto)) if isinstance(n, ast.ClassDef)]:
        for nodo in clase.body:
            if not (isinstance(nodo, ast.Assign) and isinstance(nodo.value, ast.Tuple)):
                continue
            for el in nodo.value.elts:
                if (isinstance(el, ast.Call) and isinstance(el.func, ast.Attribute)
                        and isinstance(el.func.value, ast.Name) and el.func.value.id == 'fields'):
                    for t in nodo.targets:
                        if isinstance(t, ast.Name):
                            salida.append((t.id, nodo.lineno))
                    break
    return salida


def comprobar_modulo(modulo, ok_campos=None):
    """Devuelve (errores, avisos): listas de textos 'CODIGO ruta:linea: que pasa'."""
    errores, avisos = [], []
    ok_campos = aprobados() if ok_campos is None else ok_campos
    manifest_ruta = os.path.join(MODULOS, modulo, '__manifest__.py')
    if not os.path.exists(manifest_ruta):
        return ['E0 %s: no existe odoo/modulos/%s/__manifest__.py' % (modulo, modulo)], []

    for ruta, rel in ficheros(modulo):
        ext = os.path.splitext(ruta)[1].lower()
        if ext not in ('.py', '.xml', '.js'):
            continue
        texto = leer(ruta)

        if ext in ('.xml', '.js'):
            limpio = sin_comentarios(texto, RE_COMENT_XML if ext == '.xml' else RE_COMENT_JS)
            for m in RE_ARIA.finditer(limpio):
                errores.append('E1 %s:%d: aria-hidden="true" oculta el elemento en Odoo 13; usar role="presentation"'
                               % (rel, linea_de(limpio, m.start())))

        if ext in ('.py', '.js'):
            for n, l in enumerate(texto.splitlines(), 1):
                codigo = l.split('#')[0] if ext == '.py' else l.split('//')[0]
                if RE_DISPLAY_NOTIF.search(codigo):
                    errores.append("E2 %s:%d: la accion 'display_notification' no existe en Odoo 13" % (rel, n))

        if ext == '.py':
            try:
                compile(texto, rel, 'exec')
            except SyntaxError as e:
                errores.append('E7 %s:%s: no compila: %s' % (rel, e.lineno, e.msg))
                continue
            for modelo, campo, n in campos_compartidos(texto):
                if '%s.%s' % (modelo, campo) not in ok_campos:
                    errores.append('E4 %s:%d: campo nuevo %s.%s en una tabla compartida. Prohibido sin preguntar '
                                   '(no_overscan, 03/11). Si esta aprobado, anadirlo a bin/campos_compartidos_aprobados.txt'
                                   % (rel, n, modelo, campo))
            for campo, n in campos_con_coma(texto):
                errores.append('E9 %s:%d: el campo %s acaba en coma: es una tupla y Odoo no lo crea' % (rel, n, campo))
            for m in RE_ALTER.finditer(texto):
                errores.append('E4 %s:%d: ALTER TABLE ... ADD en una tabla compartida (%s)'
                               % (rel, linea_de(texto, m.start()), m.group(1)))

        if ext == '.xml':
            try:
                arbol = ET.fromstring(texto.encode('utf-8'))
            except ET.ParseError as e:
                errores.append('E7 %s: XML mal formado: %s' % (rel, e))
                continue
            for rep in arbol.iter('report'):
                nombre = rep.get('name') or ''
                if '.' not in nombre:
                    errores.append('E3 %s: <report id="%s"> con name="%s" sin punto (modulo.plantilla)'
                                   % (rel, rep.get('id'), nombre))
            for rec in arbol.iter('record'):
                if rec.get('model') != 'ir.actions.report':
                    continue
                for f in rec.iter('field'):
                    if f.get('name') == 'report_name' and '.' not in (f.text or ''):
                        errores.append('E3 %s: report_name "%s" sin punto (modulo.plantilla)' % (rel, f.text))
            for f in arbol.iter('field'):   # E8: groups dentro del arch de una vista
                if f.get('name') != 'arch':
                    continue
                for el in f.iter():
                    for g in (el.get('groups') or '').split(','):
                        g = g.strip().lstrip('-')
                        if g and '.' not in g:
                            errores.append('E8 %s: groups="%s" en una vista sin el modulo delante (modulo.%s)'
                                           % (rel, el.get('groups'), g))
            bloques = [arbol] if arbol.get('noupdate') in ('1', 'True', 'true') else []
            bloques += [d for d in arbol.iter('data') if d.get('noupdate') in ('1', 'True', 'true')]
            for b in bloques:
                for fn in b.iter('function'):
                    avisos.append('A1 %s: <function model="%s" name="%s"> con noupdate: solo corre al INSTALAR'
                                  % (rel, fn.get('model'), fn.get('name')))

    # ---- version e historial (E5, E6)
    texto_manifest = leer(manifest_ruta)
    try:
        version = ast.literal_eval(texto_manifest)['version']
    except Exception as e:
        return errores + ['E7 odoo/modulos/%s/__manifest__.py: no se puede leer: %s' % (modulo, e)], avisos
    corta = version_corta(version)
    ruta_git = 'odoo/modulos/%s' % modulo
    _, etiquetas = git('tag', '-l', '%s/v*' % modulo)
    etiquetas = sorted(etiquetas.split(), key=lambda t: clave_version(t.split('/v', 1)[1]))
    etiqueta_actual = '%s/v%s' % (modulo, corta)
    if etiquetas:
        ultima = etiquetas[-1]
        # git diff contra la copia de trabajo (incluye lo no commiteado); los ficheros nuevos sin seguir no cuentan
        cambiado = git('diff', '--quiet', ultima, '--', ruta_git)[0] != 0
        if cambiado and etiqueta_actual in etiquetas:
            errores.append('E5 %s: ha cambiado desde %s y la version sigue en %s. Subir la version del manifest'
                           % (ruta_git, ultima if ultima == etiqueta_actual else etiqueta_actual, corta))
        elif cambiado and clave_version(corta) < clave_version(ultima.split('/v', 1)[1]):
            errores.append('E5 %s: la version %s es menor que la ultima etiqueta %s' % (ruta_git, corta, ultima))
    if etiqueta_actual not in etiquetas:
        patron = re.compile(r'v(%s) \(\d{2}/\d{2}/\d{4}' % '|'.join(re.escape(v) for v in variantes(corta)))
        if not patron.search(texto_manifest):
            errores.append("E6 %s/__manifest__.py: falta la linea de historial 'v%s (dd/mm/aaaa): que cambia y por que'"
                           % (ruta_git, corta))
    return errores, avisos


def main(argv):
    modulos = argv or sorted(d for d in os.listdir(MODULOS)
                             if os.path.isfile(os.path.join(MODULOS, d, '__manifest__.py')))
    ok_campos = aprobados()
    total_e = total_a = 0
    for m in modulos:
        errores, avisos = comprobar_modulo(m, ok_campos)
        total_e += len(errores)
        total_a += len(avisos)
        if errores or avisos:
            print('== %s' % m)
            for t in errores + avisos:
                print('  ' + t)
    print('\n%d modulos: %d errores, %d avisos' % (len(modulos), total_e, total_a))
    return 1 if total_e else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
