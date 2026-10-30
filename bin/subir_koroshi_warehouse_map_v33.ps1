param(
    [string]$HostName = "nath.tuctuc.com",
    [string]$UserName = "it_nath_group",
    [string]$RemoteDir = "/home/it_nath_group",
    [int]$Port = 22,
    [string]$IdentityFile = ""
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$zip = Join-Path $root "versiones\20261029_1535_koroshi_warehouse_map_odoo13_v33.zip"
$updater = Join-Path $PSScriptRoot "actualizar_koroshi_warehouse_map_2026-10-29_v7.sh"

if (-not (Test-Path -LiteralPath $zip)) {
    throw "No existe el paquete: $zip"
}
if (-not (Test-Path -LiteralPath $updater)) {
    throw "No existe el actualizador: $updater"
}
if (-not (Get-Command scp -ErrorAction SilentlyContinue)) {
    throw "No se encuentra scp. Instala/activa OpenSSH Client en Windows."
}

$remote = "$UserName@$HostName"
$scpArgs = @("-P", [string]$Port, $zip, "$remote`:$RemoteDir/")
if ($IdentityFile) {
    $scpArgs = @("-i", $IdentityFile) + $scpArgs
}

Write-Host "Subiendo paquete del módulo..." -ForegroundColor Cyan
& scp @scpArgs
if ($LASTEXITCODE -ne 0) { throw "scp del ZIP ha fallado (código $LASTEXITCODE)." }

$scpArgs = @("-P", [string]$Port, $updater, "$remote`:$RemoteDir/")
if ($IdentityFile) {
    $scpArgs = @("-i", $IdentityFile) + $scpArgs
}

Write-Host "Subiendo actualizador..." -ForegroundColor Cyan
& scp @scpArgs
if ($LASTEXITCODE -ne 0) { throw "scp del actualizador ha fallado (código $LASTEXITCODE)." }

if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
    throw "El ZIP y el script se han subido, pero no se encuentra ssh para aplicar chmod."
}

$sshArgs = @("-p", [string]$Port, $remote, "chmod +x '$RemoteDir/actualizar_koroshi_warehouse_map_2026-10-29_v7.sh'")
if ($IdentityFile) {
    $sshArgs = @("-i", $IdentityFile) + $sshArgs
}

Write-Host "Marcando el actualizador como ejecutable..." -ForegroundColor Cyan
& ssh @sshArgs
if ($LASTEXITCODE -ne 0) { throw "La subida terminó, pero no se pudo ejecutar chmod (código $LASTEXITCODE)." }

Write-Host "Subida completada." -ForegroundColor Green
Write-Host "En el servidor ejecuta primero:" -ForegroundColor Yellow
Write-Host "  bash $RemoteDir/actualizar_koroshi_warehouse_map_2026-10-29_v7.sh check $RemoteDir/20261029_1535_koroshi_warehouse_map_odoo13_v33.zip"
Write-Host "Y, si el check termina correctamente, instala con:" -ForegroundColor Yellow
Write-Host "  sudo AUTO_CONFIRM=1 bash $RemoteDir/actualizar_koroshi_warehouse_map_2026-10-29_v7.sh install $RemoteDir/20261029_1535_koroshi_warehouse_map_odoo13_v33.zip"
Write-Host "El modo install reinicia Odoo una sola vez; no hace stop/start separado." -ForegroundColor Green
