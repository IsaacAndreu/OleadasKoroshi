# -*- coding: utf-8 -*-
# v3.36: «Caja llena» por volumen (diseño 25/11/2026). Cada respuesta a «¿Caja llena?» de la PDA queda aquí, para
# ajustar los % con datos reales (el Monitor lo enseña). Tabla propia: nada nuevo en albaranes ni movimientos.
from odoo import api, fields, models

AVISOS = [('llena', 'Llena (100 %)'), ('dos', '¿Dos cajas? (115 %)')]
RESPUESTAS = [('cerrar', 'Caja llena: cerrar'), ('cabe', 'Aún cabe más')]


class CajaLlena(models.Model):
    _name = 'koroshi.preparacion.caja_llena'
    _description = 'KOROSHI Preparación: respuestas a «¿Caja llena?» en la PDA'
    _order = 'id desc'

    employee_id = fields.Many2one('hr.employee', 'Operario', index=True, ondelete='set null')
    picking_id = fields.Many2one('stock.picking', 'OUT', index=True, ondelete='set null')
    batch_id = fields.Many2one('stock.picking.batch', 'Agrupación', ondelete='set null')
    tipo_caja_id = fields.Many2one('koroshi.consumable.item', 'Tipo de caja', ondelete='set null')
    capacidad = fields.Float('Capacidad (m3)', digits=(16, 4))
    m3 = fields.Float('m3 al preguntar', digits=(16, 4))
    pct = fields.Integer('% al preguntar')
    uds = fields.Integer('Uds sin caja al preguntar')
    aviso = fields.Selection(AVISOS, 'Aviso')
    respuesta = fields.Selection(RESPUESTAS, 'Respuesta')
    caja = fields.Char('CJ cerrada después', index=True)
    m3_cierre = fields.Float('m3 al cerrar', digits=(16, 4))
    pct_cierre = fields.Integer('% al cerrar')
    fecha_cierre = fields.Datetime('Cerrada el')

    @api.model
    def guardar(self, picking, employee, lote=None, tipo_caja=False, capacidad=0.0, m3=0.0, uds=0, aviso='',
                respuesta=''):
        """Una respuesta de la PDA. Lo que llega mal escrito se guarda vacío: nunca da error a la PDA por esto."""
        def num(v, tipo=float):
            try:
                return tipo(v or 0)
            except (TypeError, ValueError):
                return tipo(0)
        capacidad, m3 = num(capacidad), num(m3)
        tipo = self.env['koroshi.consumable.item'].sudo().browse(num(tipo_caja, int)).exists()
        return self.sudo().create({
            'employee_id': employee.id if employee else False,
            'picking_id': picking.id if picking else False,
            'batch_id': lote.id if lote else False,
            'tipo_caja_id': tipo.id if tipo else False,
            'capacidad': capacidad,
            'm3': m3,
            'pct': int(round(100 * m3 / capacidad)) if capacidad else 0,
            'uds': num(uds, int),
            'aviso': aviso if aviso in dict(AVISOS) else False,
            'respuesta': respuesta if respuesta in dict(RESPUESTAS) else False,
        })
