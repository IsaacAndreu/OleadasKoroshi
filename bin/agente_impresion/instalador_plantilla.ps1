# =============================================================================
# KOROSHI - instalar el agente de impresion en un PC del almacen (v__VERSION__, __FECHA__)
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
    Write-Host 'KOROSHI - instalar el agente de impresion (v__VERSION__)' -ForegroundColor White

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
#__AGENTE__#
'@
    Bien "$agente (v__VERSION__)"

    # ---------------------------------------------------------------- 5. config.ini
    Paso '5. Configuracion'
    $cfgRuta = Join-Path $CARPETA 'config.ini'
    $antes = @{}
    if (Test-Path $cfgRuta) {
        foreach ($l in Get-Content $cfgRuta) { if ($l -match '^\s*(\w+)\s*=\s*(.*)$') { $antes[$Matches[1]] = $Matches[2].Trim() } }
    }
    $ajuste = $(if ($antes.ajuste) { $antes.ajuste } else { 'fit' })
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
