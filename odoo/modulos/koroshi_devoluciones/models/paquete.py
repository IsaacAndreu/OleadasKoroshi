# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Devoluciones - «Llegadas» (fase 2, etapa 1)                       v1.1 20/11/2026
#
# Llega un paquete de devolución: se lee lo que trae (matrícula CJ de la tienda, código de Zalando o código del
# transportista, p. ej. GLS) y queda «ha llegado hoy, lo leyó X». Después se puede buscar: «lo de GLS del día 28».
# Solo apunta: no crea recepciones ni mueve stock. Las etapas siguientes (qué lleva dentro, manipulación, box del
# día) se colgarán de este registro.
#
# v1.2 (20/11/2026) «Contenido» (fase 2, etapa 2): se abre el paquete y se leen sus prendas. Cada prenda se marca al
# leerla: Bien (va a su puesto), una de las manipulaciones (Quitar precio…) o Tara. Queda en
# koroshi.devolucion.paquete.linea (quién, cuándo, artículo, uds, resultado). Todavía no se compara con lo esperado:
# no tenemos de dónde sacarlo (web: falta casar el paquete con la DevoEcom de S4T; tiendas: S4T no da el teórico por
# matrícula). Lo leído es lo que «les mandamos» si no nos lo pasan. Solo apunta: no mueve stock.
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
    estado = fields.Selection([('llegado', 'Ha llegado'), ('leido', 'Contenido leído'), ('anulado', 'Anulado')],
                              'Estado', default='llegado', required=True, index=True, readonly=True)
    # v1.2: contenido
    linea_ids = fields.One2many('koroshi.devolucion.paquete.linea', 'paquete_id', 'Contenido', readonly=True)
    uds_leidas = fields.Integer('Uds leídas', compute='_compute_uds', store=True)
    uds_bien = fields.Integer('Bien', compute='_compute_uds', store=True)
    uds_manipular = fields.Integer('Manipular', compute='_compute_uds', store=True)
    uds_tara = fields.Integer('Tara', compute='_compute_uds', store=True)

    @api.depends('linea_ids.uds', 'linea_ids.resultado')
    def _compute_uds(self):
        for p in self:
            por = {'bien': 0, 'manipular': 0, 'tara': 0}
            for l in p.linea_ids:
                por[l.resultado] = por.get(l.resultado, 0) + l.uds
            p.uds_bien, p.uds_manipular, p.uds_tara = por['bien'], por['manipular'], por['tara']
            p.uds_leidas = sum(por.values())

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
        ya = self.sudo().search([('name', '=', codigo), ('estado', 'in', ('llegado', 'leido')),
                                 ('llegada', '>=', desde)], limit=1)
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

    @api.model
    def buscar_reciente(self, codigo):
        """v1.2: el paquete con ese código llegado en los últimos DIAS_REPETIDO días (vacío si no hay)."""
        desde = fields.Datetime.now() - datetime.timedelta(days=DIAS_REPETIDO)
        return self.sudo().search([('name', '=', normalizar(codigo)), ('estado', 'in', ('llegado', 'leido')),
                                   ('llegada', '>=', desde)], limit=1)

    def guardar_contenido(self, tanda, employee, lineas):
        """v1.2: lineas = [(producto, resultado, manipulacion o vacío, uds)]. Si la tanda ya está guardada (la PDA
        reintenta tras cortarse la wifi), no se repite."""
        self.ensure_one()
        Linea = self.env['koroshi.devolucion.paquete.linea'].sudo()
        if Linea.search_count([('tanda', '=', tanda)]):
            return False
        with self.env.cr.savepoint():
            for producto, resultado, manipulacion, uds in lineas:
                Linea.create({'paquete_id': self.id, 'tanda': tanda, 'product_id': producto.id, 'uds': uds,
                              'resultado': resultado, 'manipulacion_id': manipulacion.id or False,
                              'employee_id': employee.id, 'dia': comun.hoy_local()})
            if self.estado == 'llegado':
                self.sudo().write({'estado': 'leido'})
        return True

    def action_anular(self):
        """Leído por error: se anula (no se borra; queda quién)."""
        if not self.env.user.has_group('stock.group_stock_manager'):
            raise UserError(_('Solo un responsable de inventario puede anular llegadas.'))
        for p in self.sudo():
            p.write({'estado': 'anulado',
                     'nota': ((p.nota + ' · ') if p.nota else '') + _('Anulado por %s') % self.env.user.name})
        return True


class KoroshiDevolucionPaqueteLinea(models.Model):
    """v1.2: lo que se ha leído dentro de un paquete. Una línea por artículo, resultado y manipulación de cada
    guardado."""
    _name = 'koroshi.devolucion.paquete.linea'
    _description = 'KOROSHI: prenda leída dentro de un paquete de devolución'
    _order = 'id desc'

    paquete_id = fields.Many2one('koroshi.devolucion.paquete', 'Paquete', required=True, index=True,
                                 ondelete='cascade', readonly=True)
    canal = fields.Selection(related='paquete_id.canal', store=True, readonly=True)
    tanda = fields.Char('Tanda', index=True, readonly=True)
    product_id = fields.Many2one('product.product', 'Artículo', required=True, index=True, ondelete='restrict',
                                 readonly=True)
    uds = fields.Integer('Uds', required=True, readonly=True)
    resultado = fields.Selection([('bien', 'Bien (a su puesto)'), ('manipular', 'Manipular'), ('tara', 'Tara')],
                                 'Resultado', required=True, index=True, readonly=True)
    manipulacion_id = fields.Many2one('koroshi.devolucion.manipulacion', 'Manipulación', ondelete='restrict',
                                      readonly=True)
    employee_id = fields.Many2one('hr.employee', 'Leído por', index=True, ondelete='restrict', readonly=True)
    fecha = fields.Datetime('Cuándo', default=fields.Datetime.now, readonly=True)
    dia = fields.Date('Día', readonly=True, index=True)
