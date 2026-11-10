# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI XPO bultos - cajas distintas de toda la expedicion XPO.
#
# delivery_xpo.xpo_es_send_shipping(pickings) hace:
#     total_packages = sum(len(p.package_ids) for p in pickings)
#     ... RegistraExpedicion(..., TotalUnidadesManipulacion=str(total_packages or 1), ...)
# package_ids de una OUT = cajas destino (result_package_id) de sus lineas. Una caja compartida por dos OUT
# (KOROSHI Caja existente v1.1+) se sumaba dos veces -> XPO declaraba y etiquetaba un bulto de mas.
#
# Aqui no se copia el metodo de EFFEC: se calcula len(pickings.mapped('package_ids')) (cajas distintas) y, solo
# si es distinto de la suma, se cambia TotalUnidadesManipulacion en la llamada a RegistraExpedicion a traves de
# un envoltorio del cliente zeep. Todo lo demas (peso, volumen, referencia, etiquetas, tracking) igual.
# =============================================================================
import logging

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

COMPANY_ID = 8                              # EFFECTIVE LOGISTICS, S.L.
CTX = 'koroshi_xpo_bultos'


class _ServicioXPO(object):
    """Envoltorio de client.service: solo cambia TotalUnidadesManipulacion de RegistraExpedicion."""

    def __init__(self, servicio, bultos):
        self._servicio = servicio
        self._bultos = bultos

    def __getattr__(self, nombre):
        metodo = getattr(self._servicio, nombre)
        if nombre != 'RegistraExpedicion':
            return metodo
        bultos = self._bultos

        def registra_expedicion(*args, **kwargs):
            if 'TotalUnidadesManipulacion' in kwargs:
                _logger.info('KOROSHI XPO BULTOS: TotalUnidadesManipulacion %s -> %d',
                             kwargs['TotalUnidadesManipulacion'], bultos)
                kwargs['TotalUnidadesManipulacion'] = str(bultos)
            return metodo(*args, **kwargs)
        return registra_expedicion


class _ClienteXPO(object):
    def __init__(self, cliente, bultos):
        self._cliente = cliente
        self.service = _ServicioXPO(cliente.service, bultos)

    def __getattr__(self, nombre):
        return getattr(self._cliente, nombre)


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    def xpo_es_send_shipping(self, pickings):
        if pickings and all(p.company_id.id == COMPANY_ID for p in pickings):
            suma = sum(len(p.package_ids) for p in pickings)
            cajas = pickings.mapped('package_ids')
            distintas = len(cajas)
            if distintas != suma:
                # Mismo minimo que delivery_xpo, pero con las cajas distintas
                if distintas < 3:
                    raise UserError(_("XPO es para pedidos con 3 o más bultos - pedidos: %s, bultos totales: %s "
                                      "(cajas distintas; hay cajas en más de una OUT)")
                                    % (', '.join(pickings.mapped('name')), distintas))
                repetidas = cajas.filtered(lambda k: len(pickings.filtered(lambda p: k in p.package_ids)) > 1)
                _logger.info('KOROSHI XPO BULTOS: %s: %d cajas distintas (suma por OUT %d; en varias OUT: %s)',
                             ', '.join(pickings.mapped('name')), distintas, suma,
                             ', '.join(repetidas.mapped('name')))
                res = super(DeliveryCarrier, self.with_context(**{CTX: distintas})).xpo_es_send_shipping(pickings)
                pickings[:1].message_post(body=_('XPO: %d bultos (cajas distintas de la expedicion). Cajas en mas '
                                                 'de una OUT, contadas una vez: %s')
                                          % (distintas, ', '.join(repetidas.mapped('name'))))
                return res
        return super(DeliveryCarrier, self).xpo_es_send_shipping(pickings)

    def _xpo_es_get_client(self):
        cliente = super(DeliveryCarrier, self)._xpo_es_get_client()
        bultos = self.env.context.get(CTX)
        if bultos:
            return _ClienteXPO(cliente, bultos)
        return cliente
