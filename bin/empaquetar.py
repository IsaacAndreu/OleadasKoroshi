# -*- coding: utf-8 -*-
"""
KOROSHI - empaquetar.py (auditoria 13/11, fase 6, 14/11/2026)

Etiqueta la version de un modulo y genera su ZIP DESDE LA ETIQUETA (git archive, todo en LF).
Sustituye a los ZIP hechos a mano con zipfile y a guardar los ZIP en git.

Uso (desde la raiz del repositorio):
    python bin/empaquetar.py koroshi_zonas              # version del manifest de HEAD
    python bin/empaquetar.py koroshi_zonas --commit X   # etiquetar una version ya commiteada en el commit X

Reglas (nunca se sobrescribe una version):
  - El modulo tiene que estar commiteado (sin cambios en la copia de trabajo).
  - Etiqueta anotada <modulo>/v<version> (p. ej. koroshi_zonas/v1.3.0). Si ya existe con OTRO contenido, para:
    hay que sacar una version nueva. Nunca se mueve ni se borra una etiqueta.
  - ZIP bin/AAAAMMDD_<modulo>_v<version>.zip. Si ya hay uno de esa version con otro contenido, para.
  - El ZIP se comprueba: solo la carpeta del modulo, manifest con la version, .py que compilan.
La etiqueta necesita usuario de git: si no hay, se pone con GIT_COMMITTER_NAME / GIT_COMMITTER_EMAIL en el entorno.
Despues se instala con bin/desplegar.sh <check|install> <modulo> <version>. Este script no sube nada.
"""
import ast
import datetime
import io
import os
import subprocess
import sys
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULOS = 'odoo/modulos'


def git(*args, **kw):
    # core.autocrlf=false solo para 'archive' (todo en LF); 'status' con la configuracion del repositorio
    pre = ['git', '-c', 'core.autocrlf=false'] if args and args[0] == 'archive' else ['git']
    r = subprocess.run(pre + list(args), cwd=RAIZ, capture_output=True, **kw)
    if r.returncode != 0 and not kw.get('input'):
        raise RuntimeError('git %s: %s' % (' '.join(args), r.stderr.decode('utf-8', 'replace').strip()))
    return r.stdout


def existe_ref(ref):
    return subprocess.run(['git', 'rev-parse', '-q', '--verify', ref], cwd=RAIZ,
                          capture_output=True).returncode == 0


def arbol(rev, modulo):
    return git('rev-parse', '%s:%s/%s' % (rev, MODULOS, modulo)).decode().strip()


def version_corta(v):
    return v[5:] if v.startswith('13.0.') else v


def contenido_zip(ruta):
    z = zipfile.ZipFile(ruta)
    return dict((n, z.read(n).replace(b'\r\n', b'\n')) for n in z.namelist() if not n.endswith('/'))


def parar(msg):
    sys.stderr.write('PARO: %s\n' % msg)
    sys.exit(1)


def main(argv):
    if not argv or argv[0].startswith('-'):
        parar('uso: python bin/empaquetar.py <modulo> [--commit <rev>]')
    modulo = argv[0]
    commit = 'HEAD'
    if '--commit' in argv:
        commit = argv[argv.index('--commit') + 1]
    commit = git('rev-parse', '--verify', commit + '^{commit}').decode().strip()
    if not existe_ref('%s:%s/%s/__manifest__.py' % (commit, MODULOS, modulo)):
        parar('%s no tiene %s/%s/__manifest__.py' % (commit[:8], MODULOS, modulo))
    if commit == git('rev-parse', 'HEAD').decode().strip():
        sucio = git('status', '--porcelain', '--', '%s/%s' % (MODULOS, modulo)).decode().strip()
        if sucio:
            parar('%s tiene cambios sin commitear:\n%s' % (modulo, sucio))
    manifest = git('show', '%s:%s/%s/__manifest__.py' % (commit, MODULOS, modulo)).decode('utf-8')
    version = ast.literal_eval(manifest)['version']
    corta = version_corta(version)
    etiqueta = '%s/v%s' % (modulo, corta)

    # ---- etiqueta
    if existe_ref('refs/tags/' + etiqueta):
        if arbol(etiqueta, modulo) != arbol(commit, modulo):
            parar('la etiqueta %s ya existe con OTRO contenido de %s. Nunca se sobrescribe una version: subir la '
                  'version del manifest.' % (etiqueta, modulo))
        print('Etiqueta %s: ya existe con el mismo contenido' % etiqueta)
    else:
        git('tag', '-a', etiqueta, commit, '-m', '%s %s' % (modulo, version))
        print('Etiqueta %s creada en %s' % (etiqueta, commit[:8]))

    # ---- ZIP
    binp = os.path.join(RAIZ, 'bin')
    sufijo = '_%s_v%s.zip' % (modulo, corta)
    previos = [f for f in os.listdir(binp) if f.endswith(sufijo) and f[:8].isdigit() and len(f) == 8 + len(sufijo)]
    tmp = os.path.join(binp, '.empaquetar_%s.zip' % os.getpid())
    try:
        git('archive', '--format=zip', '-o', tmp, '%s:%s' % (etiqueta, MODULOS), modulo)
        nuevo = contenido_zip(tmp)
        # comprobaciones
        fuera = [n for n in nuevo if not n.startswith(modulo + '/')]
        if fuera:
            parar('el ZIP trae cosas fuera de %s/: %s' % (modulo, fuera[:3]))
        if ast.literal_eval(nuevo[modulo + '/__manifest__.py'].decode('utf-8'))['version'] != version:
            parar('el manifest del ZIP no tiene la version %s' % version)
        for n, datos in nuevo.items():
            if n.endswith('.py'):
                compile(datos, n, 'exec')
        if previos:
            for f in previos:
                if contenido_zip(os.path.join(binp, f)) != nuevo:
                    parar('ya hay bin/%s con OTRO contenido de %s %s. Nunca se sobrescribe una version.'
                          % (f, modulo, corta))
            print('ZIP: ya esta (bin/%s), mismo contenido' % previos[0])
            return 0
        destino = os.path.join(binp, datetime.date.today().strftime('%Y%m%d') + sufijo)
        os.replace(tmp, destino)
        print('ZIP: bin/%s (%d ficheros, version %s)' % (os.path.basename(destino), len(nuevo), version))
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    print('Para instalar: bash desplegar.sh check %s %s' % (modulo, corta))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except RuntimeError as e:
        parar(str(e))
