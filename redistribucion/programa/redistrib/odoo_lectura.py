# -*- coding: utf-8 -*-
"""Único fichero del programa que habla con Odoo (XML-RPC). SOLO LECTURA.

El usuario que se usa (Departament IT) puede escribir en Odoo, así que la solo lectura la garantiza este
fichero y nada más:

- Lista blanca de métodos: solo pasan los de METODOS_PERMITIDOS. Cualquier otro (write, create, unlink,
  action_…, uno inventado…) lanza LecturaProhibida ANTES de abrir conexión o enviar nada.
- No hay ninguna forma pública de llegar al proxy de XML-RPC: solo `llamar()` y sus atajos de lectura.
- La contraseña no se imprime nunca: no sale en repr(), y los errores de red o de Odoo se limpian antes de
  subir (se sustituye por «***» y se corta la cadena de la excepción original con `from None`).
- Sin cargar el servidor: una petición cada vez, con una pausa mínima entre peticiones, páginas de 5.000
  filas como mucho y siempre con la compañía 8 en el contexto.

Ningún otro fichero del programa puede importar xmlrpc (lo comprueba pruebas/test_odoo_lectura.py).
"""
import logging
import time
import xmlrpc.client
from urllib.parse import urlsplit

_log = logging.getLogger(__name__)

COMPANIA = 8                     # Effective Logistics (igual que koroshi_base.comun.COMPANY_ID)
METODOS_PERMITIDOS = frozenset({'search', 'search_read', 'read', 'search_count', 'read_group', 'fields_get'})
METODOS_COMUNES = frozenset({'version', 'authenticate'})    # del punto /xmlrpc/2/common
MAX_FILAS = 5000                 # tope de filas por petición (search, search_read, read)
PAUSA_MINIMA = 0.3               # segundos entre dos peticiones, aunque la configuración diga menos
HOSTS_LOCALES = ('localhost', '127.0.0.1', '::1')


class LecturaProhibida(Exception):
    """Se ha pedido algo que no es de solo lectura. No se ha enviado nada a Odoo."""


class ErrorOdoo(Exception):
    """Fallo de red o de Odoo, con la contraseña ya quitada del mensaje."""


def comprobar_metodo(metodo):
    """Lanza LecturaProhibida si `metodo` no está en la lista blanca. Comparación exacta (ni mayúsculas ni
    espacios: «Write», «write » o «search_read;write» no pasan)."""
    if not isinstance(metodo, str) or metodo not in METODOS_PERMITIDOS:
        raise LecturaProhibida('Método no permitido (solo lectura): %r. Permitidos: %s'
                               % (metodo, ', '.join(sorted(METODOS_PERMITIDOS))))


def _transporte(https, timeout):
    base = xmlrpc.client.SafeTransport if https else xmlrpc.client.Transport

    class _ConTiempo(base):
        def make_connection(self, host):
            con = super().make_connection(host)
            con.timeout = timeout
            return con
    return _ConTiempo()


def _fabrica_real(timeout):
    def fabrica(url_punto):
        return xmlrpc.client.ServerProxy(url_punto, transport=_transporte(url_punto.startswith('https'), timeout),
                                         allow_none=True)
    return fabrica


class ClienteLectura:
    """Cliente XML-RPC de solo lectura para Odoo 13.

    `fabrica_proxy(url_punto)` devuelve el proxy de cada punto (/common y /object); en las pruebas se pasa uno
    falso que apunta lo que le llega. `reloj` y `dormir` también se pueden cambiar en las pruebas."""

    def __init__(self, url, bd, usuario, clave, pausa=0.5, timeout=120, fabrica_proxy=None,
                 reloj=time.monotonic, dormir=time.sleep):
        partes = urlsplit(url or '')
        if partes.username or partes.password:
            raise ValueError('La dirección de Odoo no puede llevar usuario ni clave dentro')
        if partes.scheme != 'https' and not (partes.scheme == 'http' and partes.hostname in HOSTS_LOCALES):
            raise ValueError('La dirección de Odoo tiene que ser https:// (http solo para pruebas en este PC)')
        if not bd or not usuario:
            raise ValueError('Faltan la base de datos o el usuario en la configuración')
        if not clave:
            raise ValueError('Falta la contraseña (se lee del almacén de credenciales de Windows)')
        self.url = '%s://%s' % (partes.scheme, partes.netloc)
        self.bd = bd
        self.usuario = usuario
        self.__clave = clave
        self.pausa = max(float(pausa), PAUSA_MINIMA)
        self.__fabrica = fabrica_proxy or _fabrica_real(timeout)
        self.__proxies = {}
        self.__uid = None
        self.__ultima = None
        self._reloj, self._dormir = reloj, dormir
        self.peticiones = 0

    def __repr__(self):
        return '<ClienteLectura %s bd=%s usuario=%s clave=***>' % (self.url, self.bd, self.usuario)

    __str__ = __repr__

    # ------------------------------------------------------------------ internas
    def _limpiar(self, texto):
        texto = str(texto)
        return texto.replace(self.__clave, '***') if self.__clave else texto

    def _proxy(self, punto):
        if punto not in self.__proxies:
            self.__proxies[punto] = self.__fabrica('%s/xmlrpc/2/%s' % (self.url, punto))
        return self.__proxies[punto]

    def _esperar_turno(self):
        """Una petición cada vez y con pausa: no se lanza la siguiente hasta que pasa `pausa` desde la anterior."""
        if self.__ultima is not None:
            falta = self.pausa - (self._reloj() - self.__ultima)
            if falta > 0:
                self._dormir(falta)

    def _enviar(self, punto, metodo, *args):
        self._esperar_turno()
        inicio = self._reloj()
        try:
            return getattr(self._proxy(punto), metodo)(*args)
        except xmlrpc.client.Fault as e:
            raise ErrorOdoo('Odoo respondió con un error: %s' % self._limpiar(e.faultString)[:2000]) from None
        except xmlrpc.client.ProtocolError as e:
            raise ErrorOdoo('Error HTTP %s en %s' % (e.errcode, self._limpiar(e.url))) from None
        except (OSError, xmlrpc.client.Error) as e:
            raise ErrorOdoo('No se pudo hablar con Odoo: %s' % self._limpiar(e)) from None
        finally:
            self.__ultima = self._reloj()
            self.peticiones += 1
            _log.debug('%s.%s %.2f s', punto, metodo, self.__ultima - inicio)

    # ------------------------------------------------------------------ /common
    def version(self):
        """Versión del servidor. No necesita usuario."""
        return self._enviar('common', 'version')

    def autenticar(self):
        if self.__uid is None:
            uid = self._enviar('common', 'authenticate', self.bd, self.usuario, self.__clave, {})
            if not uid:
                raise ErrorOdoo('Usuario o contraseña incorrectos para %s en %s' % (self.usuario, self.bd))
            self.__uid = uid
        return self.__uid

    # ------------------------------------------------------------------ /object
    def llamar(self, modelo, metodo, args=None, kwargs=None):
        """Única puerta a execute_kw. Primero se comprueba todo; si algo no cuadra no se envía nada."""
        comprobar_metodo(metodo)
        if not isinstance(modelo, str) or not modelo.replace('.', '').replace('_', '').isalnum():
            raise LecturaProhibida('Nombre de modelo no válido: %r' % (modelo,))
        args = list(args or [])
        kwargs = dict(kwargs or {})
        contexto = dict(kwargs.get('context') or {})
        contexto['allowed_company_ids'] = [COMPANIA]          # siempre la compañía 8, la pida quien la pida
        contexto['force_company'] = COMPANIA
        kwargs['context'] = contexto
        if metodo in ('search', 'search_read'):
            limite = kwargs.get('limit')
            if not limite or limite > MAX_FILAS:
                raise LecturaProhibida('%s sin límite o con más de %d filas: usar leer_paginado()' % (metodo, MAX_FILAS))
        if metodo == 'read' and (not args or len(args[0]) > MAX_FILAS):
            raise LecturaProhibida('read de más de %d ids: partirlo' % MAX_FILAS)
        if metodo in ('search_read', 'read') and not (kwargs.get('fields') or (metodo == 'read' and len(args) > 1)):
            raise LecturaProhibida('%s sin lista de campos: pedir solo los necesarios' % metodo)
        uid = self.autenticar()
        return self._enviar('object', 'execute_kw', self.bd, uid, self.__clave, modelo, metodo, args, kwargs)

    # ------------------------------------------------------------------ atajos (todos pasan por llamar)
    def contar(self, modelo, dominio, contexto=None):
        return self.llamar(modelo, 'search_count', [dominio], {'context': contexto or {}})

    def campos(self, modelo, atributos=('string', 'type', 'relation', 'store')):
        return self.llamar(modelo, 'fields_get', [], {'attributes': list(atributos)})

    def agrupar(self, modelo, dominio, campos, agrupar_por, contexto=None):
        return self.llamar(modelo, 'read_group', [dominio, campos, agrupar_por],
                           {'lazy': False, 'context': contexto or {}})

    def leer_paginado(self, modelo, dominio, campos, pagina=2000, desde_id=0, contexto=None):
        """Recorre el modelo por id creciente, de `pagina` en `pagina` filas (máx. 5.000), una petición cada vez.
        Devuelve un generador de listas de filas. Al ir por id (y no por offset) sirve para descargas
        incrementales: `desde_id` = el último id que ya se tiene."""
        pagina = min(int(pagina), MAX_FILAS)
        ultimo = int(desde_id or 0)
        while True:
            filas = self.llamar(modelo, 'search_read', [list(dominio) + [('id', '>', ultimo)]],
                                {'fields': list(campos), 'limit': pagina, 'order': 'id asc',
                                 'context': contexto or {}})
            if not filas:
                return
            yield filas
            ultimo = filas[-1]['id']
            if len(filas) < pagina:
                return
