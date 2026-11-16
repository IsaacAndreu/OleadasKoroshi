# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI XPO bultos - cajas distintas, peso y volumen por bulto en la expedicion XPO.
#
# delivery_xpo.xpo_es_send_shipping(pickings) hace:
#     total_packages = sum(len(p.package_ids) for p in pickings)
#     weight = 15 + por OUT (shipping_weight o sus bultos)        -> 15 + 1 kg/caja (no hay pesos en Odoo)
#     volume = suma volumen producto x uds (0,09 m3/ud sin dato) -> p. ej. 5 cajas = 5,63 m3
#     ... RegistraExpedicion(expedicion={..'Peso'..}, TotalUnidadesManipulacion=..., PesoNeto, PesoBruto,
#                            VolumenNeto, VolumenOperacional)
#
# v1.0 (10/11/2026): una caja compartida por dos OUT contaba dos veces -> se mandan las cajas DISTINTAS.
# v1.1 (12/11/2026): XPO factura con 15 kg y 0,09 m3 POR BULTO (su tabla del 30/10: 5 bultos = 75 kg y
#   0,45 m3) y se quejaba de que recibia mal los m3 y kg (K80: 5 bultos, 5,63 m3, 20 kg). Ahora, en TODAS las
#   expediciones de EFFEC, se mandan: bultos = cajas distintas, peso = 15 x bultos, volumen = 0,09 x bultos.
#
# v1.2 (14/11/2026, auditoria 13/11 fase 3): bultos_de() y valores_xpo() son LA cuenta de bultos, peso y volumen de
#   KOROSHI: la usan esta expedicion XPO y koroshi_s4t_envios (antes cada uno contaba las cajas a su manera).
#
# No se copia el metodo de EFFEC: se cambian esos valores en la llamada a RegistraExpedicion a traves de un
# envoltorio del cliente zeep. Referencia, etiquetas, tracking y cancelacion: igual que delivery_xpo.
# =============================================================================
import logging

from odoo import _, models
from odoo.exceptions import UserError
from odoo.addons.koroshi_base import comun   # v1.3: la empresa

_logger = logging.getLogger(__name__)

COMPANY_ID = comun.COMPANY_ID               # v1.3: de koroshi_base (EFFECTIVE LOGISTICS, S.L.)
CTX = 'koroshi_xpo_bultos'
PESO_BULTO = 15.0                           # kg por bulto (criterio de XPO)
VOLUMEN_BULTO = 0.09                        # m3 por bulto (criterio de XPO)


def valores_xpo(bultos):
    """Peso (kg) y volumen (m3) que se declaran a XPO (y a S4T) para N bultos."""
    return round(PESO_BULTO * bultos, 2), round(VOLUMEN_BULTO * bultos, 2)


def bultos_de(pickings):
    """v1.2: las cajas DISTINTAS (stock.quant.package) de unas OUT: las cajas destino de sus lineas con algo leido.
    Una caja compartida por dos OUT cuenta una vez. Si ninguna linea tiene nada leido (aun sin validar), las cajas
    destino de todas sus lineas (lo mismo que package_ids de Odoo)."""
    lineas = pickings.mapped('move_line_ids')
    cajas = lineas.filtered(lambda ml: ml.qty_done > 0).mapped('result_package_id')
    return cajas or lineas.mapped('result_package_id')


class _ServicioXPO(object):
    """Envoltorio de client.service: cambia bultos, peso y volumen de RegistraExpedicion."""

    def __init__(self, servicio, bultos):
        self._servicio = servicio
        self._bultos = bultos

    def __getattr__(self, nombre):
        metodo = getattr(self._servicio, nombre)
        if nombre != 'RegistraExpedicion':
            return metodo
        bultos = self._bultos
        peso, volumen = valores_xpo(bultos)

        def registra_expedicion(*args, **kwargs):
            antes = (kwargs.get('TotalUnidadesManipulacion'), kwargs.get('PesoBruto'), kwargs.get('VolumenNeto'))
            kwargs['TotalUnidadesManipulacion'] = str(bultos)
            kwargs['PesoNeto'] = peso
            kwargs['PesoBruto'] = peso
            kwargs['VolumenNeto'] = volumen
            kwargs['VolumenOperacional'] = volumen
            expedicion = kwargs.get('expedicion')
            if isinstance(expedicion, dict) and 'Peso' in expedicion:
                expedicion = dict(expedicion)
                expedicion['Peso'] = peso
                kwargs['expedicion'] = expedicion
            _logger.info('KOROSHI XPO BULTOS: bultos/peso/volumen %s/%s/%s -> %d/%.2f/%.2f',
                         antes[0], antes[1], antes[2], bultos, peso, volumen)
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
            cajas = bultos_de(pickings)          # v1.2: la misma cuenta que koroshi_s4t_envios
            distintas = len(cajas)
            if distintas and distintas != suma:
                # Mismo minimo que delivery_xpo, pero con las cajas distintas
                if distintas < 3:
                    raise UserError(_("XPO es para pedidos con 3 o más bultos - pedidos: %s, bultos totales: %s "
                                      "(cajas distintas; hay cajas en más de una OUT)")
                                    % (', '.join(pickings.mapped('name')), distintas))
                repetidas = cajas.filtered(lambda k: len(pickings.filtered(lambda p: k in bultos_de(p))) > 1)
                _logger.info('KOROSHI XPO BULTOS: %s: %d cajas distintas (suma por OUT %d; en varias OUT: %s)',
                             ', '.join(pickings.mapped('name')), distintas, suma,
                             ', '.join(repetidas.mapped('name')))
                pickings[:1].message_post(body=_('XPO: %d bultos (cajas distintas de la expedicion). Cajas en mas '
                                                 'de una OUT, contadas una vez: %s')
                                          % (distintas, ', '.join(repetidas.mapped('name'))))
            bultos = distintas or suma or 1
            res = super(DeliveryCarrier, self.with_context(**{CTX: bultos})).xpo_es_send_shipping(pickings)
            peso, volumen = valores_xpo(bultos)
            pickings[:1].message_post(body=_('XPO: declarados %d bultos, %.2f kg y %.2f m3 (15 kg y 0,09 m3 por '
                                             'bulto).') % (bultos, peso, volumen))
            return res
        return super(DeliveryCarrier, self).xpo_es_send_shipping(pickings)

    def _xpo_es_get_client(self):
        cliente = super(DeliveryCarrier, self)._xpo_es_get_client()
        bultos = self.env.context.get(CTX)
        if bultos:
            return _ClienteXPO(cliente, bultos)
        return cliente
