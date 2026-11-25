# -*- coding: utf-8 -*-
"""
Genera instalar_agente_impresion.ps1 (UN fichero para mandar por Teams) metiendo agente_impresion.py dentro de
instalador_plantilla.ps1. Uso: python bin/agente_impresion/hacer_instalador.py
Se guarda en UTF-8 con BOM: PowerShell 5.1 (Windows 10) lee sin BOM como ANSI y estropearía los acentos.
"""
import datetime
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, 'instalar_agente_impresion.ps1')


def generar():
    agente = open(os.path.join(AQUI, 'agente_impresion.py'), encoding='utf-8').read()
    plantilla = open(os.path.join(AQUI, 'instalador_plantilla.ps1'), encoding='utf-8').read()
    if re.search(r"^'@", agente, re.M):
        raise SystemExit("El agente tiene una línea que empieza por '@: rompería el here-string de PowerShell")
    version = re.search(r"^VERSION = '([\d.]+)'", agente, re.M).group(1)
    texto = (plantilla.replace('#__AGENTE__#', agente.rstrip('\n'))
             .replace('__VERSION__', version)
             .replace('__FECHA__', datetime.date.today().strftime('%d/%m/%Y')))
    with open(SALIDA, 'w', encoding='utf-8-sig', newline='\r\n') as f:
        f.write(texto)
    return SALIDA, version


if __name__ == '__main__':
    ruta, version = generar()
    print('Generado %s (agente %s)' % (ruta, version))
    sys.exit(0)
