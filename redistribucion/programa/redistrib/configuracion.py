# -*- coding: utf-8 -*-
"""Configuración del programa y contraseña de Odoo.

- `config.local.toml` (fuera de git): dirección, base de datos, usuario y ajustes de lectura. Hay un modelo en
  `config.ejemplo.toml`.
- La contraseña NO está en ningún fichero: se guarda en el almacén de credenciales de Windows con `keyring`
  (servicio SERVICIO_KEYRING, cuenta = el usuario de Odoo) y se lee de ahí. Nunca se imprime.
"""
import getpass
import tomllib
from pathlib import Path

SERVICIO_KEYRING = 'koroshi-redistribucion-odoo'
CARPETA = Path(__file__).resolve().parent.parent
RUTA_CONFIG = CARPETA / 'config.local.toml'
POR_DEFECTO = {'pausa': 0.5, 'pagina': 2000, 'timeout': 120}


class ErrorConfiguracion(Exception):
    pass


def leer_config(ruta=RUTA_CONFIG):
    ruta = Path(ruta)
    if not ruta.exists():
        raise ErrorConfiguracion('No existe %s. Copiar config.ejemplo.toml a config.local.toml y rellenarlo.' % ruta.name)
    with open(ruta, 'rb') as fh:
        datos = tomllib.load(fh)
    odoo = datos.get('odoo') or {}
    if any(k in odoo for k in ('clave', 'password', 'contrasena', 'contraseña')):
        raise ErrorConfiguracion('La contraseña no va en %s: se guarda con «python programa.py guardar-clave».' % ruta.name)
    falta = [k for k in ('url', 'bd', 'usuario') if not str(odoo.get(k) or '').strip()]
    if falta:
        raise ErrorConfiguracion('Falta en [odoo] de %s: %s' % (ruta.name, ', '.join(falta)))
    lectura = dict(POR_DEFECTO)
    lectura.update(datos.get('lectura') or {})
    return {'url': odoo['url'].strip().rstrip('/'), 'bd': odoo['bd'].strip(), 'usuario': odoo['usuario'].strip(),
            'pausa': float(lectura['pausa']), 'pagina': int(lectura['pagina']), 'timeout': int(lectura['timeout'])}


def _keyring():
    try:
        import keyring
    except ImportError:
        raise ErrorConfiguracion('Falta la librería keyring: «python -m pip install keyring».') from None
    return keyring


def leer_clave(usuario):
    clave = _keyring().get_password(SERVICIO_KEYRING, usuario)
    if not clave:
        raise ErrorConfiguracion('No hay contraseña guardada para «%s». Guardarla con «python programa.py guardar-clave».'
                                 % usuario)
    return clave


def guardar_clave(usuario):
    """Pide la contraseña sin que se vea en pantalla (dos veces) y la guarda en el almacén de Windows."""
    uno = getpass.getpass('Contraseña de Odoo para %s (no se ve al escribir): ' % usuario)
    dos = getpass.getpass('Repetirla: ')
    if not uno or uno != dos:
        raise ErrorConfiguracion('Vacía o no coinciden: no se ha guardado nada.')
    _keyring().set_password(SERVICIO_KEYRING, usuario, uno)
