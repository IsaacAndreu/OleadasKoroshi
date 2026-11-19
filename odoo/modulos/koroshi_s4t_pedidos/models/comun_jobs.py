# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Pedidos S4T grandes - candado por feed/pedido, guardar a mitad de job y opciones de queue_job.
# =============================================================================
import contextlib
import logging
import threading

import psycopg2

from odoo.addons.queue_job.exception import RetryableJobError

from .. import logica

_logger = logging.getLogger(__name__)

# queue_job del servidor: 13.0.3.10.1 (visto el 19/11). En esta version cualquier metodo se puede encolar con
# with_delay sin el decorador @job (obsoleto); Effective tampoco lo usa. No se usa aqui.
try:
    from odoo.addons.queue_job.job import identity_exact
except ImportError:  # pragma: no cover
    identity_exact = None


def opciones_job(descripcion):
    """Argumentos de with_delay para los jobs de este modulo: canal S4T, prioridad de reintento de Effective (5) y,
    si queue_job lo permite, sin duplicados mientras haya uno igual pendiente o en curso."""
    opciones = {'channel': logica.CANAL, 'priority': 5, 'description': descripcion}
    if identity_exact is not None:
        opciones['identity_key'] = identity_exact
    return opciones


def _soltar(cr, clave, ident):
    try:
        cr.execute('SELECT pg_advisory_unlock(%s, %s)', (clave, ident))
    except psycopg2.Error:
        # La transaccion ha quedado abortada por el error que nos trae aqui: se deshace (queue_job la iba a
        # deshacer igual) y se suelta. El candado es de la sesion: no se va con el rollback.
        cr.rollback()
        cr.execute('SELECT pg_advisory_unlock(%s, %s)', (clave, ident))


@contextlib.contextmanager
def candado(cr, clave, ident, que):
    """Un solo job a la vez por feed o por pedido.

    Si otra copia del mismo job esta trabajando (porque alguien lo reencolo mientras seguia vivo), esta no hace nada
    y queue_job la vuelve a mirar en 5 min, sin gastar reintentos. El candado es de la sesion de Postgres: aguanta
    los commit de mitad de job y Postgres lo suelta solo si el worker muere o se corta la conexion."""
    cr.execute('SELECT pg_try_advisory_lock(%s, %s)', (clave, ident))
    if not cr.fetchone()[0]:
        _logger.warning('KOROSHI S4T: %s ya lo esta procesando otra copia del job; esta espera %d s',
                        que, logica.ESPERA_COPIA)
        raise RetryableJobError('%s: otra copia del job esta trabajando; se vuelve a mirar en %d s'
                                % (que, logica.ESPERA_COPIA),
                                seconds=logica.ESPERA_COPIA, ignore_retry=True)
    try:
        yield
    finally:
        _soltar(cr, clave, ident)


def guardar(env):
    """Commit a mitad de job: lo hecho queda guardado aunque luego choque la escritura de queue_job en su propia
    fila. En los tests de Odoo no se hace commit."""
    if getattr(threading.current_thread(), 'testing', False):
        return
    env['base'].flush()
    env.cr.commit()


def entero_param(env, clave, defecto, minimo):
    return logica.leer_entero(env['ir.config_parameter'].sudo().get_param(clave), defecto, minimo)
