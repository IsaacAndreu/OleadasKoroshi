# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Operarios - una tarea = un operario cogiendo un pedido (OUT) o una agrupacion.
#
# Se abre desde la pantalla de lecturas (controllers/main.py): tarjeta + pedido.
# Se cierra:
#   - sola, cuando el pedido o la agrupacion esta validado (cron cada 5 min) -> acabada
#   - con "Dejar aqui" en la pantalla (tarjeta + boton)                        -> dejada
#   - cuando el mismo operario empieza otro pedido                            -> dejada
#   - a medianoche, si sigue abierta                                          -> sin cerrar
# Uds de la tarea = uds leidas (qty_done) del pedido al cerrar - uds leidas al empezar.
# Solo escribe en esta tabla: lee albaranes, lineas y agrupaciones sin cambiarlos.
# =============================================================================
import datetime

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError

ZONA_HORARIA = 'Europe/Madrid'
PREFIJOS_ZONA = ('Z-',)     # OUT de estas agrupaciones -> la tarea es de toda la agrupacion
VENTANA_TARJETA = 90        # segundos que vale la tarjeta leida para leer el pedido despues


class KoroshiOperarioTarea(models.Model):
    _name = 'koroshi.operario.tarea'
    _description = 'KOROSHI Tarea de operario'
    _order = 'inicio desc, id desc'

    name = fields.Char('Tarea', compute='_compute_name', store=True)
    employee_id = fields.Many2one('hr.employee', 'Operario', required=True, index=True, ondelete='restrict')
    picking_id = fields.Many2one('stock.picking', 'Pedido (OUT)', index=True, ondelete='set null')
    batch_id = fields.Many2one('stock.picking.batch', 'Agrupacion', index=True, ondelete='set null')
    tipo = fields.Selection([('out', 'Pedido (OUT)'), ('agrupacion', 'Agrupacion')], 'Tipo', required=True)
    referencia = fields.Char('Leido', help='Codigo que se leyo en la pantalla')
    zona = fields.Char('Zona', compute='_compute_zona', store=True,
                       help='Ultima parte del nombre de la agrupacion (D1, ZX2...) o R1/R2 de las rondas')
    company_id = fields.Many2one('res.company', 'Empresa', required=True,
                                 default=lambda self: self.env.company)

    inicio = fields.Datetime('Inicio', required=True, default=fields.Datetime.now, index=True)
    fin = fields.Datetime('Fin')
    dia = fields.Date('Dia', compute='_compute_dia', store=True, index=True)
    estado = fields.Selection([
        ('curso', 'En curso'),
        ('acabada', 'Acabada'),
        ('dejada', 'Dejada'),
        ('sin_cerrar', 'Sin cerrar'),
    ], 'Estado', default='curso', required=True, index=True)
    motivo_fin = fields.Selection([
        ('validada', 'Validada'),
        ('dejar', 'Dejar aqui'),
        ('otro', 'Empezo otro pedido'),
        ('medianoche', 'Medianoche'),
        ('manual', 'A mano'),
        ('saltar', 'Saltada'),
    ], 'Como se cerro')

    uds_inicio = fields.Float('Uds leidas al empezar', digits=(16, 0))
    uds_fin = fields.Float('Uds leidas al cerrar', digits=(16, 0))
    uds_total = fields.Float('Uds del pedido', digits=(16, 0), help='Uds que pide el pedido al empezar')
    uds = fields.Float('Uds', compute='_compute_resultado', store=True, digits=(16, 0), group_operator='sum')
    minutos = fields.Float('Minutos', compute='_compute_resultado', store=True, digits=(16, 1),
                           group_operator='sum')
    uds_hora = fields.Float('Uds/hora', compute='_compute_resultado', store=True, digits=(16, 1),
                            group_operator='avg')
    nota = fields.Char('Nota')

    # ------------------------------------------------------------------ computes
    @api.depends('employee_id', 'picking_id', 'batch_id', 'tipo', 'referencia')
    def _compute_name(self):
        for t in self:
            ref = t.batch_id.name if t.tipo == 'agrupacion' else t.picking_id.name
            t.name = '%s - %s' % (t.employee_id.name or '', ref or t.referencia or '')

    @api.depends('picking_id', 'batch_id', 'tipo')
    def _compute_zona(self):
        for t in self:
            lote = t.batch_id if t.tipo == 'agrupacion' else t.picking_id.batch_id
            nombre = lote.name or ''
            t.zona = nombre.rsplit('-', 1)[-1] if '-' in nombre else (nombre.rsplit('_', 1)[-1] if '_' in nombre else '')

    @api.depends('inicio')
    def _compute_dia(self):
        tz = pytz.timezone(ZONA_HORARIA)
        for t in self:
            t.dia = pytz.utc.localize(t.inicio).astimezone(tz).date() if t.inicio else False

    @api.depends('inicio', 'fin', 'uds_inicio', 'uds_fin', 'estado')
    def _compute_resultado(self):
        for t in self:
            if t.fin and t.inicio:
                t.minutos = max(0.0, (t.fin - t.inicio).total_seconds() / 60.0)
                t.uds = max(0.0, t.uds_fin - t.uds_inicio)
                t.uds_hora = t.minutos >= 1 and t.uds * 60.0 / t.minutos or 0.0
            else:
                t.minutos = 0.0
                t.uds = 0.0
                t.uds_hora = 0.0

    # ------------------------------------------------------------------ helpers
    def _pickings(self):
        self.ensure_one()
        if self.tipo == 'agrupacion':
            return self.batch_id.sudo().picking_ids
        return self.picking_id.sudo()

    @api.model
    def _uds_leidas(self, pickings):
        total = 0.0
        for ml in pickings.mapped('move_line_ids'):
            total += ml.qty_done
        return total

    @api.model
    def _uds_pedidas(self, pickings):
        total = 0.0
        for m in pickings.mapped('move_lines'):
            if m.state != 'cancel':
                total += m.product_uom_qty
        return total

    @api.model
    def _validado(self, pickings):
        # validado = todas sus OUT hechas o canceladas (y al menos una hecha)
        vivas = pickings.filtered(lambda p: p.state != 'cancel')
        return bool(vivas) and all(p.state == 'done' for p in vivas)

    @api.model
    def _hora_validacion(self, pickings):
        fechas = [p.date_done for p in pickings if p.state == 'done' and p.date_done]
        return fechas and max(fechas) or fields.Datetime.now()

    @api.model
    def _ultima_lectura(self, pickings, desde):
        fechas = [ml.write_date for ml in pickings.mapped('move_line_ids')
                  if ml.qty_done > 0 and ml.write_date and ml.write_date >= desde]
        return fechas and max(fechas) or desde

    def _cerrar(self, estado, motivo, fin=None):
        for t in self:
            if t.estado != 'curso':
                continue
            pickings = t._pickings()
            t.write({
                'estado': estado,
                'motivo_fin': motivo,
                'fin': fin or fields.Datetime.now(),
                'uds_fin': t._uds_leidas(pickings),
            })
        return True

    # ------------------------------------------------------------------ lecturas
    @api.model
    def buscar_objetivo(self, codigo):
        """Pedido u agrupacion a partir de un codigo leido. Devuelve (tipo, picking, batch) o (False, ...)."""
        codigo = (codigo or '').strip()
        Picking = self.env['stock.picking'].sudo()
        Batch = self.env['stock.picking.batch'].sudo()
        picking = Picking.search([('name', '=', codigo)], limit=1)
        if picking:
            lote = picking.batch_id
            if lote and (lote.name or '').startswith(PREFIJOS_ZONA):
                return 'agrupacion', picking, lote
            return 'out', picking, Batch
        lote = Batch.search([('name', '=', codigo)], limit=1)
        if lote:
            return 'agrupacion', Picking, lote
        return False, Picking, Batch

    @api.model
    def abierta_de(self, employee):
        return self.sudo().search([('employee_id', '=', employee.id), ('estado', '=', 'curso')],
                                  order='inicio desc', limit=1)

    @api.model
    def empezar(self, employee, codigo):
        """Empieza una tarea. Devuelve (tarea, mensaje). Lanza UserError si no se puede."""
        tipo, picking, lote = self.buscar_objetivo(codigo)
        if not tipo:
            raise UserError(_('No encuentro ningun pedido ni agrupacion con el codigo %s') % codigo)
        pickings = lote.picking_ids if tipo == 'agrupacion' else picking
        if self._validado(pickings):
            raise UserError(_('%s ya esta validado') % (lote.name if tipo == 'agrupacion' else picking.name))
        Tarea = self.sudo()
        abierta = self.abierta_de(employee)
        mensaje = ''
        if abierta:
            mismo = (abierta.tipo == tipo and abierta.picking_id == picking and abierta.batch_id == lote)
            if mismo:
                return abierta, _('Ya lo tenias empezado')
            abierta._cerrar('dejada', 'otro')
            mensaje = _('Cerrado el anterior (%s) como dejado. ') % (abierta.batch_id.name or abierta.picking_id.name)
        objetivo = lote if tipo == 'agrupacion' else picking
        tarea = Tarea.create({
            'employee_id': employee.id,
            'tipo': tipo,
            'picking_id': picking.id if picking else False,
            'batch_id': lote.id if tipo == 'agrupacion' else (picking.batch_id.id or False),
            'referencia': codigo,
            'company_id': objetivo.company_id.id or self.env.company.id,
            'uds_inicio': self._uds_leidas(pickings),
            'uds_total': self._uds_pedidas(pickings),
        })
        return tarea, mensaje

    @api.model
    def dejar(self, employee):
        abierta = self.abierta_de(employee)
        if not abierta:
            raise UserError(_('%s no tiene ningun pedido empezado') % employee.name)
        abierta._cerrar('dejada', 'dejar')
        return abierta

    def action_cerrar_a_mano(self):
        self._cerrar('dejada', 'manual')
        return True

    # ------------------------------------------------------------------ cron
    @api.model
    def cron_cerrar(self):
        """Cada 5 min: cierra las tareas cuyo pedido ya esta validado; las de dias anteriores, sin cerrar."""
        tz = pytz.timezone(ZONA_HORARIA)
        ahora_local = datetime.datetime.now(tz)
        medianoche = tz.localize(datetime.datetime(ahora_local.year, ahora_local.month, ahora_local.day))
        medianoche_utc = medianoche.astimezone(pytz.utc).replace(tzinfo=None)
        for t in self.sudo().search([('estado', '=', 'curso')]):
            pickings = t._pickings()
            if pickings and self._validado(pickings):
                fin = self._hora_validacion(pickings)
                if fin < t.inicio:
                    fin = t.inicio
                t._cerrar('acabada', 'validada', fin)
            elif t.inicio < medianoche_utc:
                t._cerrar('sin_cerrar', 'medianoche', self._ultima_lectura(pickings, t.inicio))
        # v2: las asignaciones de la cola cuyo pedido ya esta validado pasan a hechas
        self.env['koroshi.operario.asignacion'].cron_actualizar()
        return True

    # ------------------------------------------------------------------ informes
    @api.model
    def action_validadas_sin_operario(self):
        """OUT validadas hoy (salida) que no estan en ninguna tarea."""
        tz = pytz.timezone(ZONA_HORARIA)
        ahora_local = datetime.datetime.now(tz)
        medianoche = tz.localize(datetime.datetime(ahora_local.year, ahora_local.month, ahora_local.day))
        desde = medianoche.astimezone(pytz.utc).replace(tzinfo=None)
        hechas = self.env['stock.picking'].search([
            ('picking_type_code', '=', 'outgoing'),
            ('state', '=', 'done'),
            ('date_done', '>=', desde),
        ])
        tareas = self.sudo().search([('inicio', '>=', desde - datetime.timedelta(days=1))])
        cubiertas = tareas.mapped('picking_id')
        for t in tareas.filtered(lambda x: x.tipo == 'agrupacion'):
            cubiertas |= t.batch_id.picking_ids
        sin = hechas - cubiertas
        return {
            'type': 'ir.actions.act_window',
            'name': _('OUT validadas hoy sin operario (%d de %d)') % (len(sin), len(hechas)),
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', sin.ids)],
            'target': 'current',
        }
