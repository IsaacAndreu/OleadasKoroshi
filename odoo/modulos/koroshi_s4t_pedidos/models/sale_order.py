# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Pedidos S4T grandes - paso 2 (confirmar sin reservar) y paso 3 (reservar por bloques).
#
# Solo cuando action_confirm llega desde el feed b2b (contexto koroshi_confirmar_diferido) y el pedido tiene
# koroshi_s4t_pedidos.umbral_lineas lineas o mas (60 por defecto; 0 = apagado). Cualquier otro action_confirm
# (tiendas pequenas, web, el boton Confirmar) va como siempre.
#
# Paso 2: action_confirm con koroshi_sin_reservar (models/stock_move.py: _action_assign no hace nada) y encola el
#         paso 3 en la misma transaccion. Si falla, el pedido sigue en presupuesto: nunca queda medio confirmado.
# Paso 3: reserva los movimientos de sus OUT en bloques de koroshi_s4t_pedidos.bloque_reserva (50), con commit por
#         bloque. Si un bloque choca con una PDA, se deshace solo ese bloque y se repite (3 veces). Una OUT a medio
#         reservar es lo mismo que una OUT con falta de stock: se puede seguir con «Comprobar disponibilidad».
# =============================================================================
import logging
import time

import psycopg2

from odoo import models
from odoo.service.model import PG_CONCURRENCY_ERRORS_TO_RETRY

from odoo.addons.queue_job.exception import RetryableJobError

from .. import logica
from .comun_jobs import candado, como_job, entero_param, guardar, opciones_job

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        if not self.env.context.get('koroshi_confirmar_diferido'):
            return super().action_confirm()
        umbral = entero_param(self.env, logica.PARAM_UMBRAL, logica.UMBRAL_POR_DEFECTO, 0)
        grandes = self.filtered(lambda o: logica.es_grande(len(o.order_line), umbral))
        for pedido in grandes:
            pedido.with_context(koroshi_confirmar_diferido=False).with_delay(
                **opciones_job(logica.DESC_CONFIRMAR % pedido.name)).koroshi_confirmar_s4t()
            _logger.info('KOROSHI S4T: %s tiene %d lineas: se guarda ahora y se confirma en otro job',
                         pedido.name, len(pedido.order_line))
        resto = self - grandes
        if resto:
            return super(SaleOrder, resto.with_context(koroshi_confirmar_diferido=False)).action_confirm()
        return True

    # ---------------------------------------------------------------- paso 2

    @como_job
    def koroshi_confirmar_s4t(self):
        self.ensure_one()
        pedido = self.with_context(koroshi_confirmar_diferido=False, koroshi_sin_reservar=False)
        with candado(self.env.cr, logica.CLAVE_PEDIDO, self.id, 'Pedido %s' % self.name):
            if pedido.state not in logica.ESTADOS_PEDIDO_SIN_CONFIRMAR:
                _logger.info('KOROSHI S4T: %s ya esta en estado %s; no se confirma otra vez',
                             pedido.name, pedido.state)
                return 'Ya estaba en estado %s' % pedido.state
            inicio = time.time()
            pedido.with_context(koroshi_sin_reservar=True).action_confirm()
            moves = pedido._koroshi_moves_por_reservar()
            pedido.with_delay(**opciones_job(logica.DESC_RESERVAR % pedido.name)).koroshi_reservar_s4t()
            guardar(self.env)
            msg = '%s confirmado sin reservar en %.0f s: %d OUT, %d movimientos por reservar' % (
                pedido.name, time.time() - inicio, len(pedido.picking_ids), len(moves))
            _logger.info('KOROSHI S4T: %s', msg)
            return msg

    # ---------------------------------------------------------------- paso 3

    def _koroshi_moves_por_reservar(self):
        pickings = self.picking_ids.filtered(lambda p: p.state not in ('draft', 'cancel', 'done'))
        return pickings.mapped('move_lines').filtered(
            lambda m: m.state in logica.ESTADOS_POR_RESERVAR).sorted('id')

    @como_job
    def koroshi_reservar_s4t(self):
        self.ensure_one()
        nombre = self.name
        pedido = self.with_context(koroshi_confirmar_diferido=False, koroshi_sin_reservar=False)
        with candado(self.env.cr, logica.CLAVE_PEDIDO, self.id, 'Pedido %s' % nombre):
            if pedido.state != 'sale':
                return '%s esta en estado %s: no se reserva' % (nombre, pedido.state)
            ids = pedido._koroshi_moves_por_reservar().ids
            if not ids:
                return '%s: nada por reservar' % nombre
            tam = entero_param(self.env, logica.PARAM_BLOQUE, logica.BLOQUE_POR_DEFECTO, 1)
            inicio = time.time()
            choques = 0
            Move = self.env['stock.move'].with_context(koroshi_sin_reservar=False)
            for trozo in logica.bloques(ids, tam):
                for intento in range(logica.INTENTOS_BLOQUE):
                    try:
                        Move.browse(trozo).filtered(lambda m: m.state in logica.ESTADOS_POR_RESERVAR)._action_assign()
                        guardar(self.env)
                        break
                    except psycopg2.OperationalError as e:
                        if e.pgcode not in PG_CONCURRENCY_ERRORS_TO_RETRY:
                            raise
                        choques += 1
                        self.env.cr.rollback()
                        self.env.clear()
                        if intento == logica.INTENTOS_BLOQUE - 1:
                            raise RetryableJobError(
                                '%s: un bloque de la reserva choca con otra operacion %d veces seguidas; '
                                'lo ya reservado queda guardado y se sigue en %d s'
                                % (nombre, logica.INTENTOS_BLOQUE, logica.ESPERA_RESERVA),
                                seconds=logica.ESPERA_RESERVA)
                        time.sleep(1 + 2 * intento)
            quedan = len(pedido._koroshi_moves_por_reservar())
            msg = '%s reservado en %.0f s: %d movimientos en bloques de %d, %d choques repetidos, %d sin stock ' \
                  'completo' % (nombre, time.time() - inicio, len(ids), tam, choques, quedan)
            _logger.info('KOROSHI S4T: %s', msg)
            return msg
