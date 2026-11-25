# =============================================================================
# KOROSHI - instalar el agente de impresion en un PC del almacen (v1.0.2, 25/11/2026)
#
# Un solo fichero: se manda por Teams, se guarda en el PC y se ejecuta con
#   clic derecho > «Ejecutar con PowerShell».
# Hace todo lo de bin/agente_impresion/LEEME.md:
#   1. carpeta C:\KoroshiImpresion
#   2. Python 3 (si no esta; se instala solo para este usuario, sin administrador)
#   3. SumatraPDF portable (si no esta)
#   4. el agente (va dentro de este fichero)
#   5. config.ini: codigo de la impresora en Odoo, login de Odoo y la impresora de Windows (se elige de una lista)
#   6. la contrasena en el Administrador de credenciales de Windows (se pide sin ensenarla; no va en ningun fichero)
#   7. comprueba que entra en Odoo
#   8. tarea programada: arranca el agente al iniciar sesion y lo relanza si se cae
# Se puede volver a ejecutar: actualiza el agente y deja cambiar la configuracion.
# GENERADO por bin/agente_impresion/hacer_instalador.py desde instalador_plantilla.ps1: no editar a mano.
# =============================================================================
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$CARPETA = 'C:\KoroshiImpresion'
$URL_ODOO = 'https://nath.tuctuc.com'
$BD_ODOO = 'NATH_PRODUCTION'
$CREDENCIAL = 'koroshi-impresion-odoo'
$TAREA = 'KOROSHI agente de impresion'
$PYTHON_URL = 'https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe'
$SUMATRA_URL = 'https://www.sumatrapdfreader.org/dl/rel/3.5.2/SumatraPDF-3.5.2-64.zip'

function Paso($texto) { Write-Host ''; Write-Host "== $texto" -ForegroundColor Cyan }
function Bien($texto) { Write-Host "   OK  $texto" -ForegroundColor Green }
function Aviso($texto) { Write-Host "   OJO $texto" -ForegroundColor Yellow }
function Preguntar($texto, $porDefecto) {
    $r = Read-Host ("   $texto" + $(if ($porDefecto) { " [$porDefecto]" } else { '' }))
    if ([string]::IsNullOrWhiteSpace($r)) { return $porDefecto } else { return $r.Trim() }
}
function Escribir-Utf8($ruta, $texto) {
    [IO.File]::WriteAllText($ruta, $texto, (New-Object Text.UTF8Encoding($false)))   # sin BOM
}
function Buscar-Python {
    $candidatos = @()
    $candidatos += Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\pythonw.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | ForEach-Object { $_.FullName }
    $candidatos += Get-ChildItem "$env:ProgramFiles\Python3*\pythonw.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | ForEach-Object { $_.FullName }
    $candidatos += Get-ChildItem "$env:LOCALAPPDATA\Python\pythoncore-3*\pythonw.exe", "$env:LOCALAPPDATA\Python\bin\pythonw.exe" `
        -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | ForEach-Object { $_.FullName }
    # Los del PATH, menos el de WindowsApps (abre la Microsoft Store en vez de Python)
    $candidatos += @(Get-Command pythonw.exe -All -ErrorAction SilentlyContinue) |
        Where-Object { $_.Source -notlike '*WindowsApps*' } | ForEach-Object { $_.Source }
    foreach ($c in $candidatos) {
        $python = Join-Path (Split-Path $c) 'python.exe'
        if (Test-Path $python) {
            $v = & $python -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
            if ($v -and [version]$v -ge [version]'3.8') { return $c }
        }
    }
    return $null
}

try {
    Write-Host 'KOROSHI - instalar el agente de impresion (v1.0.2)' -ForegroundColor White

    # ---------------------------------------------------------------- 1. carpeta
    Paso '1. Carpeta'
    New-Item -ItemType Directory -Force -Path $CARPETA, "$CARPETA\log" | Out-Null
    Bien $CARPETA

    # ---------------------------------------------------------------- 2. Python
    Paso '2. Python'
    $pythonw = Buscar-Python
    if (-not $pythonw) {
        Write-Host '   No esta. Descargando Python 3.12 de python.org (unos 25 MB)...'
        $inst = Join-Path $env:TEMP 'python-3.12.7-amd64.exe'
        Invoke-WebRequest -Uri $PYTHON_URL -OutFile $inst -UseBasicParsing
        Write-Host '   Instalando (para este usuario; tarda 1-2 minutos)...'
        $p = Start-Process -FilePath $inst -ArgumentList '/quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_launcher=0' -Wait -PassThru
        if ($p.ExitCode -ne 0) { throw "El instalador de Python ha devuelto $($p.ExitCode)" }
        Remove-Item $inst -Force -ErrorAction SilentlyContinue
        $pythonw = Buscar-Python
        if (-not $pythonw) { throw 'Python instalado pero no lo encuentro. Instalarlo a mano desde python.org y repetir.' }
    }
    $python = Join-Path (Split-Path $pythonw) 'python.exe'
    Bien $python

    # ---------------------------------------------------------------- 3. SumatraPDF
    Paso '3. SumatraPDF (imprime los PDF sin abrir ventanas)'
    $sumatra = Join-Path $CARPETA 'SumatraPDF.exe'
    if (-not (Test-Path $sumatra)) {
        Write-Host '   Descargando SumatraPDF portable de sumatrapdfreader.org...'
        $zip = Join-Path $env:TEMP 'SumatraPDF.zip'
        $dest = Join-Path $env:TEMP 'SumatraPDF_zip'
        Invoke-WebRequest -Uri $SUMATRA_URL -OutFile $zip -UseBasicParsing
        Remove-Item $dest -Recurse -Force -ErrorAction SilentlyContinue
        Expand-Archive -Path $zip -DestinationPath $dest -Force
        $exe = Get-ChildItem $dest -Filter 'SumatraPDF*.exe' -Recurse | Select-Object -First 1
        if (-not $exe) { throw 'El ZIP de SumatraPDF no trae el .exe' }
        Copy-Item $exe.FullName $sumatra -Force
        Remove-Item $zip, $dest -Recurse -Force -ErrorAction SilentlyContinue
    }
    Bien $sumatra

    # ---------------------------------------------------------------- 4. agente
    Paso '4. Agente'
    $agente = Join-Path $CARPETA 'agente_impresion.py'
    $tareaExiste = Get-ScheduledTask -TaskName $TAREA -ErrorAction SilentlyContinue
    if ($tareaExiste) { Stop-ScheduledTask -TaskName $TAREA -ErrorAction SilentlyContinue; Start-Sleep -Seconds 2 }
    Escribir-Utf8 $agente @'
# -*- coding: utf-8 -*-
"""
KOROSHI - agente de impresión v1.0.1 (25/11/2026)
v1.0.1: ajuste «fit» por defecto (config [impresora] ajuste). La etiqueta XPO es un PDF apaisado de 148x105 mm
  y con «noscale» salía mal en la Zebra 4x6; con «fit» Sumatra la gira y la ajusta (probado por Isaac en la GK420t).
  La de GLS ya es 100x150 mm y sale igual.
v1.0.2: por defecto «fit,landscape». La GK420t tiene el papel 4x6 en apaisado (como lo imprime Chrome) y Sumatra
  no lo lee del controlador: sin «landscape» encogía la etiqueta. Probado por Isaac el 25/11: sale perfecta.

Corre en el PC que tiene la impresora (el portátil de Expediciones) y escucha la cola de Odoo (módulo
koroshi_impresion): cada pocos segundos pregunta si hay trabajos para SU impresora, baja el PDF, lo imprime con
SumatraPDF en silencio y dice a Odoo si ha ido bien.
Diseño: bin/versiones/diseno-imprimir-desde-pda_2026-11-25_v4.md. Instrucciones: bin/agente_impresion/LEEME.md.

Solo usa la librería estándar de Python (nada que instalar con pip).
- Configuración: config.ini junto a este fichero (copiar config.ejemplo.ini). NO lleva la contraseña.
- Contraseña: en el Administrador de credenciales de Windows (credencial genérica, ver LEEME.md), nunca en un fichero.
- Solo llama a tres métodos de Odoo (lista blanca): agente_siguientes, agente_pdf y agente_hecho.

Uso:
    pythonw agente_impresion.py              # el bucle (lo arranca la tarea programada al iniciar sesión)
    python agente_impresion.py --comprobar   # conectar, decir la impresora de Windows y salir (no imprime)
    python agente_impresion.py --impresoras  # lista las impresoras de Windows
    python agente_impresion.py --probar F.pdf  # imprime un PDF local (sin Odoo) para probar papel y escala
"""
import base64
import configparser
import ctypes
import ctypes.wintypes as wt
import json
import logging
import logging.handlers
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

VERSION = '1.0.2'
AQUI = os.path.dirname(os.path.abspath(__file__))
RUTA_CONFIG = os.path.join(AQUI, 'config.ini')
CREDENCIAL = 'koroshi-impresion-odoo'        # nombre de la credencial genérica de Windows
MODELO = 'koroshi.impresion.trabajo'
METODOS_PERMITIDOS = frozenset({'agente_siguientes', 'agente_pdf', 'agente_hecho'})
ESPERAS_ERROR = (5, 10, 30, 60)              # segundos entre reintentos si Odoo no contesta
AJUSTE_DEFECTO = 'fit,landscape'      # v1.0.2: como imprime Chrome en la Zebra 4x6 (papel USER, apaisado)
ERRORES_RED = (urllib.error.URLError, ConnectionError, TimeoutError, socket.timeout)

log = logging.getLogger('agente_impresion')


class ErrorConfig(Exception):
    pass


# --------------------------------------------------------------------------- configuración
def leer_config(ruta=RUTA_CONFIG):
    if not os.path.exists(ruta):
        raise ErrorConfig('Falta %s: copiar config.ejemplo.ini y rellenarlo.' % ruta)
    cp = configparser.ConfigParser()
    cp.read(ruta, encoding='utf-8')
    o = cp['odoo'] if cp.has_section('odoo') else {}
    i = cp['impresora'] if cp.has_section('impresora') else {}
    a = cp['agente'] if cp.has_section('agente') else {}
    cfg = {
        'url': (o.get('url') or '').strip().rstrip('/'),
        'bd': (o.get('bd') or '').strip(),
        'usuario': (o.get('usuario') or '').strip(),
        'codigo': (i.get('codigo') or '').strip(),
        'nombre_windows': (i.get('nombre_windows') or '').strip(),
        'sumatra': (i.get('sumatra') or '').strip(),
        'ajuste': (i.get('ajuste') or AJUSTE_DEFECTO).replace(' ', ''),
        'segundos': float(a.get('segundos') or 3),
        'carpeta_log': (a.get('carpeta_log') or os.path.join(AQUI, 'log')).strip(),
    }
    falta = [k for k in ('url', 'bd', 'usuario', 'codigo', 'sumatra') if not cfg[k]]
    if falta:
        raise ErrorConfig('Falta en config.ini: %s' % ', '.join(falta))
    if not cfg['url'].startswith('https://'):
        raise ErrorConfig('La url tiene que ser https://')
    if not os.path.exists(cfg['sumatra']):
        raise ErrorConfig('No está SumatraPDF en %s' % cfg['sumatra'])
    return cfg


def preparar_log(carpeta):
    os.makedirs(carpeta, exist_ok=True)
    h = logging.handlers.TimedRotatingFileHandler(os.path.join(carpeta, 'agente.log'), when='midnight',
                                                  backupCount=14, encoding='utf-8')
    h.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    log.addHandler(h)
    if sys.stdout is not None:          # con pythonw no hay consola
        log.addHandler(logging.StreamHandler(sys.stdout))
    log.setLevel(logging.INFO)


# --------------------------------------------------------------------------- contraseña (Windows)
class _CREDENTIAL(ctypes.Structure):
    _fields_ = [('Flags', wt.DWORD), ('Type', wt.DWORD), ('TargetName', wt.LPWSTR), ('Comment', wt.LPWSTR),
                ('LastWritten', wt.FILETIME), ('CredentialBlobSize', wt.DWORD),
                ('CredentialBlob', ctypes.POINTER(ctypes.c_char)), ('Persist', wt.DWORD),
                ('AttributeCount', wt.DWORD), ('Attributes', ctypes.c_void_p), ('TargetAlias', wt.LPWSTR),
                ('UserName', wt.LPWSTR)]


def leer_clave(nombre=CREDENCIAL):
    """La contraseña de la credencial genérica de Windows (cmdkey /generic:...). Nunca se escribe en el log."""
    advapi = ctypes.WinDLL('advapi32', use_last_error=True)
    p = ctypes.POINTER(_CREDENTIAL)()
    if not advapi.CredReadW(nombre, 1, 0, ctypes.byref(p)):     # 1 = CRED_TYPE_GENERIC
        raise ErrorConfig('No está la credencial «%s» en el Administrador de credenciales de Windows (ver LEEME.md).'
                          % nombre)
    try:
        cred = p.contents
        datos = ctypes.string_at(cred.CredentialBlob, cred.CredentialBlobSize)
        return datos.decode('utf-16-le')
    finally:
        advapi.CredFree(p)


# --------------------------------------------------------------------------- Odoo (JSON-RPC)
class Odoo:
    def __init__(self, url, bd, usuario, clave, timeout=60):
        self.url, self.bd, self.usuario, self._clave, self.timeout = url, bd, usuario, clave, timeout
        self.uid = None

    def _rpc(self, servicio, metodo, args):
        cuerpo = json.dumps({'jsonrpc': '2.0', 'method': 'call', 'id': 1,
                             'params': {'service': servicio, 'method': metodo, 'args': args}}).encode()
        pet = urllib.request.Request(self.url + '/jsonrpc', data=cuerpo, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(pet, timeout=self.timeout) as r:
            res = json.loads(r.read().decode())
        if res.get('error'):
            err = res['error']
            datos = err.get('data') or {}
            raise RuntimeError(datos.get('message') or err.get('message') or str(err))
        return res.get('result')

    def entrar(self):
        self.uid = self._rpc('common', 'login', [self.bd, self.usuario, self._clave])
        if not self.uid:
            raise ErrorConfig('Odoo no acepta el usuario %s (¿contraseña?).' % self.usuario)
        return self.uid

    def llamar(self, metodo, *args):
        if metodo not in METODOS_PERMITIDOS:        # el agente no hace nada más en Odoo
            raise PermissionError('Método no permitido: %s' % metodo)
        if not self.uid:
            self.entrar()
        return self._rpc('object', 'execute_kw', [self.bd, self.uid, self._clave, MODELO, metodo, list(args)])


# --------------------------------------------------------------------------- impresión
def impresoras_windows():
    salida = subprocess.run(['powershell', '-NoProfile', '-Command',
                             'Get-Printer | Select-Object -ExpandProperty Name'],
                            capture_output=True, text=True, timeout=60)
    return [l.strip() for l in salida.stdout.splitlines() if l.strip()]


AJUSTES_VALIDOS = ('fit', 'shrink', 'noscale', 'landscape', 'portrait')


def imprimir_pdf(sumatra, ruta_pdf, impresora='', copias=1, timeout=180, ajuste=AJUSTE_DEFECTO):
    """Imprime con SumatraPDF sin abrir ventanas. fit (por defecto): gira y ajusta la página al papel (la XPO es
    apaisada, 148x105 mm); noscale: a su tamaño, sin girar."""
    malos = [a for a in ajuste.split(',') if a not in AJUSTES_VALIDOS]
    if malos or not ajuste:
        raise ValueError('ajuste no válido: %s (vale: %s)' % (ajuste, ', '.join(AJUSTES_VALIDOS)))
    ajustes = '%s,%dx' % (ajuste, max(1, int(copias)))
    orden = [sumatra]
    orden += ['-print-to', impresora] if impresora else ['-print-to-default']
    orden += ['-print-settings', ajustes, '-silent', ruta_pdf]
    r = subprocess.run(orden, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError('SumatraPDF devolvió %s %s' % (r.returncode, (r.stderr or r.stdout or '').strip()[:500]))


def hacer_trabajo(odoo, cfg, t):
    tid = t['id']
    ruta = None
    try:
        b64 = odoo.llamar('agente_pdf', tid)
        datos = base64.b64decode(b64)
        if not datos.startswith(b'%PDF'):
            raise RuntimeError('Lo que ha llegado no es un PDF')
        fd, ruta = tempfile.mkstemp(prefix='koroshi_%d_' % tid, suffix='.pdf')
        with os.fdopen(fd, 'wb') as f:
            f.write(datos)
        imprimir_pdf(cfg['sumatra'], ruta, cfg['nombre_windows'], t.get('copias') or 1, ajuste=cfg['ajuste'])
        odoo.llamar('agente_hecho', tid, True, '')
        log.info('Impreso %s: %s', tid, t.get('descripcion'))
    except ERRORES_RED:
        raise                                        # red: el bucle reintenta; Odoo lo devuelve a la cola a los 5 min
    except Exception as e:  # noqa: BLE001 - impresora, PDF...: se devuelve a Odoo para que se vea en la cola
        log.exception('Error en el trabajo %s', tid)
        odoo.llamar('agente_hecho', tid, False, 'PC: %s' % e)
    finally:
        if ruta and os.path.exists(ruta):
            try:
                os.remove(ruta)
            except OSError as e:
                log.warning('No se ha podido borrar %s: %s', ruta, e)


def una_vuelta(odoo, cfg):
    trabajos = odoo.llamar('agente_siguientes', cfg['codigo']) or []
    for t in trabajos:
        hacer_trabajo(odoo, cfg, t)
    return len(trabajos)


def un_solo_agente():
    """Evita dos agentes a la vez en el mismo PC (mutex con nombre de Windows)."""
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    mutex = kernel.CreateMutexW(None, False, 'Global\\koroshi_agente_impresion')
    if ctypes.get_last_error() == 183:          # ERROR_ALREADY_EXISTS
        return None
    return mutex


def bucle(cfg):
    odoo = Odoo(cfg['url'], cfg['bd'], cfg['usuario'], leer_clave())
    fallos = 0
    log.info('Agente %s en marcha: impresora %s -> «%s»', VERSION, cfg['codigo'], cfg['nombre_windows'] or 'predeterminada')
    while True:
        try:
            una_vuelta(odoo, cfg)
            if fallos:
                log.info('Odoo vuelve a contestar')
            fallos = 0
            time.sleep(cfg['segundos'])
        except ErrorConfig:
            raise
        except Exception as e:  # noqa: BLE001 - red caída, Odoo reiniciando...: esperar y seguir
            espera = ESPERAS_ERROR[min(fallos, len(ESPERAS_ERROR) - 1)]
            fallos += 1
            log.warning('Sin Odoo (%s). Reintento en %d s', e, espera)
            odoo.uid = None
            time.sleep(espera)


def main(argv):
    cfg = leer_config()
    preparar_log(cfg['carpeta_log'])
    if '--impresoras' in argv:
        for n in impresoras_windows():
            print(n)
        return 0
    if '--probar' in argv:
        ruta = argv[argv.index('--probar') + 1]
        imprimir_pdf(cfg['sumatra'], ruta, cfg['nombre_windows'], ajuste=cfg['ajuste'])
        print('Mandado a «%s»' % (cfg['nombre_windows'] or 'la predeterminada'))
        return 0
    if '--comprobar' in argv:
        odoo = Odoo(cfg['url'], cfg['bd'], cfg['usuario'], leer_clave())
        print('Odoo: entra como uid %s' % odoo.entrar())
        nombres = impresoras_windows()
        if cfg['nombre_windows'] and cfg['nombre_windows'] not in nombres:
            print('OJO: «%s» no está en Windows. Hay: %s' % (cfg['nombre_windows'], ', '.join(nombres)))
        else:
            print('Impresora de Windows: %s' % (cfg['nombre_windows'] or 'la predeterminada'))
        return 0
    if un_solo_agente() is None:
        log.info('Ya hay un agente en marcha en este PC: salgo')
        return 0
    bucle(cfg)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except ErrorConfig as e:
        log.error('%s', e)
        print(e)
        sys.exit(2)
'@
    Bien "$agente (v1.0.2)"

    # ---------------------------------------------------------------- 5. config.ini
    Paso '5. Configuracion'
    $cfgRuta = Join-Path $CARPETA 'config.ini'
    $antes = @{}
    if (Test-Path $cfgRuta) {
        foreach ($l in Get-Content $cfgRuta) { if ($l -match '^\s*(\w+)\s*=\s*(.*)$') { $antes[$Matches[1]] = $Matches[2].Trim() } }
    }
    $ajuste = $(if ($antes.ajuste) { $antes.ajuste } else { 'fit,landscape' })
    $codigo = Preguntar 'Codigo de esta impresora en Odoo (Inventario > Configuracion > Impresion > Impresoras)' $(if ($antes.codigo) { $antes.codigo } else { 'EXP1' })
    $usuario = ''
    while (-not $usuario) { $usuario = Preguntar 'Login de Odoo de Almacen Nath (el correo con que entra)' $antes.usuario }

    $impresoras = @(Get-Printer | Select-Object -ExpandProperty Name)
    Write-Host '   Impresoras de este PC:'
    for ($i = 0; $i -lt $impresoras.Count; $i++) { Write-Host ("     {0}. {1}" -f ($i + 1), $impresoras[$i]) }
    # Primero el controlador ZDesigner (el que imprime bien los PDF); el «Zebra ... - EPL» solo si no hay otro
    $sugerida = @($impresoras | Where-Object { $_ -match 'ZDesigner' }) + @($impresoras | Where-Object { $_ -match 'Zebra' }) |
        Select-Object -First 1
    if ($antes.nombre_windows) { $sugerida = $antes.nombre_windows }
    $nombreWindows = $null
    while ($null -eq $nombreWindows) {
        $r = Preguntar 'Numero de la Zebra 4x6' $sugerida
        if ($r -match '^\d+$' -and [int]$r -ge 1 -and [int]$r -le $impresoras.Count) { $nombreWindows = $impresoras[[int]$r - 1] }
        elseif ($impresoras -contains $r) { $nombreWindows = $r }
        else { Aviso 'Poner el numero de la lista' }
    }
    Escribir-Utf8 $cfgRuta @"
; KOROSHI agente de impresion. Escrito por el instalador el $(Get-Date -Format 'dd/MM/yyyy HH:mm').
; La contrasena NO esta aqui: esta en el Administrador de credenciales de Windows ($CREDENCIAL).
[odoo]
url = $URL_ODOO
bd = $BD_ODOO
usuario = $usuario

[impresora]
codigo = $codigo
nombre_windows = $nombreWindows
sumatra = $sumatra
ajuste = $ajuste

[agente]
segundos = 3
carpeta_log = $CARPETA\log
"@
    Bien "Impresora $codigo -> «$nombreWindows»"

    # ---------------------------------------------------------------- 6. contrasena
    Paso '6. Contrasena de Odoo'
    $hay = (cmdkey /list:$CREDENCIAL) -match [regex]::Escape($CREDENCIAL)
    $pedir = $true
    if ($hay) { $pedir = (Preguntar 'Ya hay una guardada. ¿Cambiarla? (s/n)' 'n') -match '^[sS]' }
    if ($pedir) {
        Write-Host '   Escribe la contrasena de Almacen Nath (no se ve al escribir) y pulsa Intro:'
        cmdkey /generic:$CREDENCIAL /user:$usuario /pass
        if ($LASTEXITCODE -ne 0) { throw 'No se ha podido guardar la contrasena' }
    }
    Bien 'Guardada en el Administrador de credenciales de Windows'

    # ---------------------------------------------------------------- 7. comprobar
    Paso '7. Comprobar (entra en Odoo; no imprime nada)'
    Push-Location $CARPETA
    & $python $agente --comprobar
    $ok = $LASTEXITCODE
    Pop-Location
    if ($ok -ne 0) { throw 'La comprobacion ha fallado (mirar el mensaje de arriba). Repetir el instalador para corregir.' }

    # ---------------------------------------------------------------- 8. tarea programada
    Paso '8. Arranque automatico'
    $yo = "$env:USERDOMAIN\$env:USERNAME"
    $accion = New-ScheduledTaskAction -Execute $pythonw -Argument "`"$agente`"" -WorkingDirectory $CARPETA
    $inicio = New-ScheduledTaskTrigger -AtLogOn -User $yo
    $ajustes = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartInterval (New-TimeSpan -Minutes 1) -RestartCount 999 `
        -MultipleInstances IgnoreNew
    $principal = New-ScheduledTaskPrincipal -UserId $yo -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -TaskName $TAREA -Action $accion -Trigger $inicio -Settings $ajustes -Principal $principal -Force | Out-Null
    Start-ScheduledTask -TaskName $TAREA
    Bien "Tarea «$TAREA» para $yo, arrancada"

    Write-Host ''
    Write-Host 'LISTO.' -ForegroundColor Green
    Write-Host "  - En Odoo, Impresoras: $codigo tiene que salir Conectada en menos de un minuto."
    Write-Host "  - Para probar el papel 4x6 con una etiqueta ya hecha:"
    Write-Host "      & '$python' '$agente' --probar C:\ruta\etiqueta.pdf"
    Write-Host "  - Log: $CARPETA\log\agente.log"
}
catch {
    Write-Host ''
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'No se ha terminado. Corregir y volver a ejecutar el instalador (se puede repetir sin problema).'
}
Read-Host 'Pulsa Intro para cerrar'
