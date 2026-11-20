# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Devoluciones - «Llegadas» (fase 2, etapa 1)                       v1.1 20/11/2026
#
# Llega un paquete de devolución: se lee lo que trae (matrícula CJ de la tienda, código de Zalando o código del
# transportista, p. ej. GLS) y queda «ha llegado hoy, lo leyó X». Después se puede buscar: «lo de GLS del día 28».
# Solo apunta: no crea recepciones ni mueve stock. Las etapas siguientes (qué lleva dentro, manipulación, box del
# día) se colgarán de este registro.
# =============================================================================
import datetime
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.addons.koroshi_base import comun

NUESTRO = '665'           # CJ665…: cajas de salida nuestras (almacén 6665), no son devoluciones
DIAS_REPETIDO = 30        # el mismo código leído otra vez en menos de 30 días es el mismo paquete
CANALES = [('tienda', 'Tiendas'), ('web', 'Web'), ('zalando', 'Zalando'), ('marketplace', 'Marketplace'),
           ('otro', 'Otro')]
TIPOS = [('matricula', 'Matrícula de tienda'), ('transportista', 'Código del transportista'),
         ('zalando', 'Código de Zalando'), ('otro', 'Otro')]


def normalizar(codigo):
    """Sin espacios ni saltos y en mayúsculas (los lectores a veces meten espacios)."""
    return re.sub(r'\s+', '', codigo or '').upper()


class KoroshiDevolucionPaquete(models.Model):
    _name = 'koroshi.devolucion.paquete'
    _description = 'KOROSHI: paquete de devolución llegado'
    _order = 'llegada desc, id desc'

    name = fields.Char('Código leído', required=True, index=True, readonly=True)
    canal = fields.Selection(CANALES, 'Canal', required=True, index=True)
    tipo_codigo = fields.Selection(TIPOS, 'Tipo de código', required=True)
    tienda_id = fields.Many2one('res.partner', 'Tienda', index=True,
                                help='Si es una matrícula CJ de tienda: la tienda sale de sus cifras (CJ080… = K80).')
    llegada = fields.Datetime('Llegada', required=True, default=fields.Datetime.now, readonly=True, index=True)
    dia = fields.Date('Día', required=True, readonly=True, index=True, help='Día de llegada en hora del almacén.')
    employee_id = fields.Many2one('hr.employee', 'Leído por', readonly=True, index=True, ondelete='restrict')
    user_id = fields.Many2one('res.users', 'Usuario de Odoo', readonly=True, default=lambda s: s.env.uid)
    nota = fields.Char('Nota')
    estado = fields.Selection([('llegado', 'Ha llegado'), ('anulado', 'Anulado')], 'Estado', default='llegado',
                              required=True, index=True, readonly=True)

    @api.model
    def _tienda_de_matricula(self, codigo):
        """CJ080123456 -> tienda con barcode 00000080 (K80), como koroshi_s4t_traspasos. Vacío si no está."""
        num = int(codigo[2:5])
        return self.env['res.partner'].sudo().search([('barcode', '=', '%08d' % num)], limit=1)

    @api.model
    def registrar(self, codigo, canal, employee):
        """Apunta la llegada. Devuelve (paquete, nuevo). Si el mismo código llegó hace menos de DIAS_REPETIDO días,
        no se repite: se devuelve el que ya estaba (nuevo = False)."""
        codigo = normalizar(codigo)
        if len(codigo) < 4:
            raise UserError(_('Código demasiado corto: «%s».') % codigo)
        if dict(CANALES).get(canal) is None:
            raise UserError(_('Elige antes el canal (Tiendas, Web, Zalando…).'))
        desde = fields.Datetime.now() - datetime.timedelta(days=DIAS_REPETIDO)
        ya = self.sudo().search([('name', '=', codigo), ('estado', '=', 'llegado'), ('llegada', '>=', desde)],
                                limit=1)
        if ya:
            return ya, False
        vals = {'name': codigo, 'canal': canal, 'dia': comun.hoy_local(), 'employee_id': employee.id}
        if comun.es_matricula(codigo):
            if codigo[2:5] == NUESTRO:
                raise UserError(_('%s es una caja nuestra (CJ665…), no una devolución.') % codigo)
            tienda = self._tienda_de_matricula(codigo)
            vals.update({'canal': 'tienda', 'tipo_codigo': 'matricula', 'tienda_id': tienda.id or False})
        else:
            vals['tipo_codigo'] = {'zalando': 'zalando', 'web': 'transportista',
                                   'marketplace': 'transportista'}.get(canal, 'otro')
        return self.sudo().create(vals), True

    def action_anular(self):
        """Leído por error: se anula (no se borra; queda quién)."""
        if not self.env.user.has_group('stock.group_stock_manager'):
            raise UserError(_('Solo un responsable de inventario puede anular llegadas.'))
        for p in self.sudo():
            p.write({'estado': 'anulado',
                     'nota': ((p.nota + ' · ') if p.nota else '') + _('Anulado por %s') % self.env.user.name})
        return True
