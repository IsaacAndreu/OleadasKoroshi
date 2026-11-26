@echo off
rem Abre el programa de redistribución: el compilado si existe; si no, con Python.
if exist "%~dp0programa\dist\Redistribucion\Redistribucion.exe" (
  start "" "%~dp0programa\dist\Redistribucion\Redistribucion.exe"
) else (
  start "" pythonw "%~dp0programa\ventana.py"
)
