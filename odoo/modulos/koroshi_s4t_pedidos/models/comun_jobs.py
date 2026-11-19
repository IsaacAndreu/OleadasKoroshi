# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Pedidos S4T grandes - candado por feed/pedido, guardar a mitad de job y decorador de queue_job.
# =============================================================================
import contextlib
import logging
import threading

import psycopg2

from odoo.addons.queue_job.exception import RetryableJobError

from .. import logica

_logger = logging.getLogger(__name__)

# queue_job 13: segun la version, un metodo solo se puede encolar si lleva @job. En las que ya no hace falta,
# el decorador sigue existiendo (o no) y aqui da igual.
try:
    from odoo.addons.queue_job.job import job as _decorador_job
except ImportError:  # pragma: no cover
    _decorador_job = None

try:
    from odoo.addons.queue_job.job import identity_exact
except ImportError:  # pragma: no cover
    identity_exact = None


def como_job(func):
    if _decorador_job is None:
        return func
    return _decorador_job(default_channel=logica.CANAL)(func)


def heredar_marcas_job(nuestro, modulo_original, modelo, metodo):
    """Al heredar un metodo que es job, queue_job 13 mira las marcas (delayable, retry_pattern, default_channel...)
    del metodo FINAL, que es el nuestro. Se copian las del original para que se encole igual que antes, con el
    canal y los reintentos que le puso Effective. Si no se encuentra el original, se marca como job del canal S4T
    (sin esto, el with_delay de Effective fallaria y no entraria ningun pedido)."""
    original = None
    for obj in (vars(modulo_original).values() if modulo_original is not None else ()):
        if isinstance(obj, type) and metodo in vars(obj) and modelo in (
                getattr(obj, '_name', None), getattr(obj, '_inherit', None)):
            original = vars(obj)[metodo]
            break
    if original is None:
        _logger.warning('KOROSHI S4T: no encuentro %s.%s en %s; se marca como job del canal %s',
                        modelo, metodo, getattr(modulo_original, '__name__', '?'), logica.CANAL)
        return como_job(nuestro)
    nuestro.__dict__.update({k: v for k, v in vars(original).items() if k != '__wrapped__'})
    return nuestro


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
