# KOROSHI agente de impresión: crea la tarea programada que lo arranca al iniciar sesión en este PC.
# Ejecutar en PowerShell como administrador, desde C:\KoroshiImpresion:  .\instalar_tarea.ps1
# Si la tarea ya existe, la sustituye. No toca nada más.
$ErrorActionPreference = 'Stop'
$carpeta = $PSScriptRoot
$script = Join-Path $carpeta 'agente_impresion.py'
$pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonw) { throw 'No encuentro pythonw.exe: instalar Python 3 marcando «Add python.exe to PATH».' }
if (-not (Test-Path $script)) { throw "No está $script" }
if (-not (Test-Path (Join-Path $carpeta 'config.ini'))) { throw 'Falta config.ini (copiar config.ejemplo.ini y rellenarlo).' }

$usuario = "$env:USERDOMAIN\$env:USERNAME"
$accion = New-ScheduledTaskAction -Execute $pythonw -Argument "`"$script`"" -WorkingDirectory $carpeta
$inicio = New-ScheduledTaskTrigger -AtLogOn -User $usuario
$ajustes = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartInterval (New-TimeSpan -Minutes 1) -RestartCount 999 `
    -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId $usuario -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName 'KOROSHI agente de impresion' -Action $accion -Trigger $inicio -Settings $ajustes `
    -Principal $principal -Force | Out-Null
Start-ScheduledTask -TaskName 'KOROSHI agente de impresion'
Write-Host "Tarea creada para $usuario y arrancada. Log: C:\KoroshiImpresion\log\agente.log"
