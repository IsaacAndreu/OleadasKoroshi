@echo off
rem Copia diaria de Odoo para el programa de redistribución (26/11/2026, lo pidió Isaac: cada día a las 19:00).
rem SOLO LECTURA de Odoo (usuario Departament IT, contraseña en el almacén de credenciales de Windows).
rem La lanza la tarea de Windows «KOROSHI copia diaria redistribucion». Solo las salidas nuevas (incremental).
rem Se guardan las 7 copias más nuevas; las del 23/11 (la base completa) no se borran nunca.
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
cd /d C:\dev\OleadasKoroshi\redistribucion\programa
echo. >> copias\copia_diaria.log
echo ==== Inicio %date% %time% >> copias\copia_diaria.log
"C:\Users\tuctuc\AppData\Local\Python\pythoncore-3.14-64\python.exe" programa.py descargar >> copias\copia_diaria.log 2>&1
set CODIGO=%errorlevel%
echo ==== Fin %date% %time% (codigo %CODIGO%) >> copias\copia_diaria.log
if not "%CODIGO%"=="0" goto :eof
powershell -NoProfile -Command "Get-ChildItem 'copias' -Filter '????????_????_odoo.sqlite' | Where-Object { $_.Name -notlike '20261123_*' } | Sort-Object Name -Descending | Select-Object -Skip 7 | ForEach-Object { Write-Output ('Borrada copia vieja: ' + $_.Name); Remove-Item -LiteralPath $_.FullName; Get-ChildItem 'copias' -Filter ($_.BaseName + '.resumen*.txt') | Remove-Item }" >> copias\copia_diaria.log 2>&1
