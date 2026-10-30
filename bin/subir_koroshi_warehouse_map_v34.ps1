param(
    [string]$HostName = "nath.tuctuc.com",
    [string]$UserName = "it_nath_group",
    [string]$RemoteDir = "/home/it_nath_group",
    [int]$Port = 22,
    [string]$IdentityFile = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$zip = Join-Path $root "versiones\20261029_1630_koroshi_warehouse_map_odoo13_v34.zip"
$updater = Join-Path $PSScriptRoot "actualizar_koroshi_warehouse_map_2026-10-29_v7.sh"

if (-not (Test-Path -LiteralPath $zip)) { throw "No existe el ZIP: $zip" }
if (-not (Test-Path -LiteralPath $updater)) { throw "No existe el actualizador: $updater" }
if (-not (Get-Command scp -ErrorAction SilentlyContinue)) { throw "No se encuentra scp (OpenSSH Client)." }

$remote = "$UserName@$HostName"
$common = @("-P", [string]$Port)
if ($IdentityFile) { $common = @("-i", $IdentityFile) + $common }

Write-Host "Subiendo el módulo v34..." -ForegroundColor Cyan
& scp @common $zip "$remote`:$RemoteDir/"
if ($LASTEXITCODE -ne 0) { throw "Falló la subida del ZIP." }

Write-Host "Subiendo el actualizador..." -ForegroundColor Cyan
& scp @common $updater "$remote`:$RemoteDir/"
if ($LASTEXITCODE -ne 0) { throw "Falló la subida del actualizador." }

if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) { throw "Los archivos se subieron, pero no se encuentra ssh para chmod." }
$ssh = @("-p", [string]$Port)
if ($IdentityFile) { $ssh = @("-i", $IdentityFile) + $ssh }
& ssh @ssh $remote "chmod +x '$RemoteDir/actualizar_koroshi_warehouse_map_2026-10-29_v7.sh'"
if ($LASTEXITCODE -ne 0) { throw "No se pudo marcar el actualizador como ejecutable." }

Write-Host "Subida completada. Ejecuta en el servidor:" -ForegroundColor Green
Write-Host "  bash $RemoteDir/actualizar_koroshi_warehouse_map_2026-10-29_v7.sh check $RemoteDir/20261029_1630_koroshi_warehouse_map_odoo13_v34.zip"
Write-Host "  sudo AUTO_CONFIRM=1 bash $RemoteDir/actualizar_koroshi_warehouse_map_2026-10-29_v7.sh install $RemoteDir/20261029_1630_koroshi_warehouse_map_odoo13_v34.zip"
Write-Host "La instalación ejecuta un único systemctl restart." -ForegroundColor Green
