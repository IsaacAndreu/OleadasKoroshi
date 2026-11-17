# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Sesiones sin caducar (v1.0.0, 17/11/2026)
#
# Odoo 13 (odoo/http.py:1157, session_gc) borra, en 1 de cada 1.000 peticiones, los ficheros de sesion de mas de
# 7 dias sin usarse. Lo llama Root.setup_session (http.py:1318) por su nombre global: cambiando odoo.http.session_gc
# deja de borrar. La limpieza de las sesiones sin usuario la hace limpiar_sesiones() desde el auto-vacuum diario.
# Python puro (sin modelos): se prueba sin Odoo (tests/test_sesiones.py).
# =============================================================================
import logging
import os
import time

_logger = logging.getLogger(__name__)

DIAS_SIN_USUARIO = 7     # las sesiones SIN usuario (login, web publica) se borran a los 7 dias, como hacia Odoo


def session_gc_sin_borrar(session_store):
    """Sustituye a odoo.http.session_gc: no borra nada en las peticiones."""
    return None


def _sid(nombre, plantilla):
    """'werkzeug_abc.sess' con plantilla 'werkzeug_%s.sess' -> 'abc'. Otro nombre -> None."""
    if '%s' not in plantilla:
        return None
    pre, post = plantilla.split('%s', 1)
    if nombre.startswith(pre) and nombre.endswith(post) and len(nombre) > len(pre) + len(post):
        return nombre[len(pre):len(nombre) - len(post)]
    return None


def limpiar_sesiones(session_store, ahora=None, dias=DIAS_SIN_USUARIO):
    """Borra los ficheros de sesion SIN usuario (uid) de mas de `dias` dias sin usarse. Los de usuario, nunca.
    Devuelve (borradas, con_usuario_viejas, revisadas)."""
    ahora = ahora or time.time()
    limite = ahora - dias * 24 * 3600
    plantilla = getattr(session_store, 'filename_template', 'werkzeug_%s.sess')
    borradas = con_usuario = revisadas = 0
    for nombre in os.listdir(session_store.path):
        ruta = os.path.join(session_store.path, nombre)
        try:
            if os.path.getmtime(ruta) >= limite:
                continue
        except OSError:
            continue
        sid = _sid(nombre, plantilla)
        if not sid:
            continue
        revisadas += 1
        try:
            sesion = session_store.get(sid)
            uid = sesion.get('uid')
        except Exception:
            uid = None      # fichero roto: no tiene usuario que se pueda recuperar
        if uid:
            con_usuario += 1
            continue
        try:
            os.unlink(ruta)
            borradas += 1
        except OSError:
            pass
    return borradas, con_usuario, revisadas


def activar():
    """Cambia odoo.http.session_gc (una vez por proceso)."""
    try:
        from odoo import http
    except ImportError:     # tests sin Odoo
        return False
    if http.session_gc is not session_gc_sin_borrar:
        http.session_gc = session_gc_sin_borrar
        _logger.info('KOROSHI Sesiones: session_gc desactivado, las sesiones con usuario no se borran')
    return True


activar()
