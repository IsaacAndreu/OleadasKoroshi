# -*- coding: utf-8 -*-
# =============================================================================
# TUCTUC Operarios - una tarea = un operario cogiendo un pedido (OUT), una INT al SORTER o una agrupacion.
# Clon de koroshi_operarios 2.25.0 (tarea.py) para odoo.tuctuc.com. Cambios: sin agrupaciones de zona Z- (en Oriola
# no hay), la referencia sin el almacén delante (WH-OR/, MODAI/, UBRAN/) y las lecturas de tuctuc_preparacion.
#
# Se abre desde la pantalla de lecturas (controllers/main.py): tarjeta + pedido.
# Se cierra:
#   - sola, cuando el pedido o la agrupacion esta validado (cron cada 5 min) -> acabada
#   - con "Dejar aqui" en la pantalla (tarjeta + boton)                        -> dejada
#   - cuando el mismo operario empieza otro pedido                            -> dejada
#   - a medianoche, si sigue abierta                                          -> sin cerrar
#   - v2.19: tras tuctuc_operarios.minutos_cierre_inactividad min (15) sin hacer nada -> dejada (inactividad), a la
#     hora de su ultima actividad. No toca el pedido (ni lineas, ni cajas, ni validar): sigue siendo suyo. Si despues
#     vuelve a leer en Preparacion, el cron abre otra tarea desde esa lectura.
# Uds de la tarea = uds leidas (qty_done) del pedido al cerrar - uds leidas al empezar.
# v2.12 (auditoria 13/11, fase 2): UNA sola cifra de productividad para todo (tarea, Productividad, correo de
# koroshi_informe, KPI y PDA):
#   minutos   = de que lee la OUT a que se cierra la tarea (si sigue abierta, hasta ahora)
#   parado    = huecos de tuctuc_operarios.minutos_sin_leer min (15) o mas sin leer en Preparacion entre la
#               primera lectura y el cierre; si sigue abierta, tambien lo que lleva ahora sin hacer nada
#   efectivo  = minutos - parado
#   u/h       = uds * 60 / efectivo                        -> uds_hora_de()
# La calculan huecos_de() y _medir(); resumen_operario_dia() la suma por operario y dia.
# Solo escribe en esta tabla: lee albaranes, lineas y agrupaciones sin cambiarlos.
# =============================================================================
import datetime
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.addons.tuctuc_base import comun   # v2.14: hora del almacen

ZONA_HORARIA = comun.TZ
# Agrupaciones de zona (en NATH, Z-: sus OUT solo se dan con la agrupación entera). En Oriola no hay: los lotes
# B-ECI_, B-VP_, WEB_... se dan OUT a OUT. Vacío = ninguna.
PREFIJOS_ZONA = ()
VENTANA_TARJETA = 90        # segundos que vale la tarjeta leida para leer el pedido despues
# v2.8: una tarea en curso sin leer nada en estos minutos ya no cuenta como «la esta haciendo ahora» (parametro
# tuctuc_operarios.minutos_sin_leer). Quien lee esa OUT se la queda sin preguntar; el monitor la marca en rojo.
MINUTOS_SIN_LEER = 15
# v2.19: una tarea en curso sin hacer nada en estos minutos se cierra sola (parametro
# tuctuc_operarios.minutos_cierre_inactividad; 0 = nunca). Peticion de Isaac 18/11: sesiones olvidadas abiertas.
MINUTOS_CIERRE_INACTIVIDAD = 15
RE_OP = re.compile(r'^([A-Za-z]+)0*(\d+)$')


def codigo_corto(barcode):
    """OP0007 -> OP7 (estaba en informe.py; v2.12 aqui para resumen_operario_dia)."""
    m = RE_OP.match((barcode or '').strip())
    return m and '%s%s' % (m.group(1).upper(), m.group(2)) or (barcode or '?')


def uds_hora_de(uds, efectivo):
    """v2.12: LA formula de u/h (uds por hora de tiempo efectivo). Menos de 1 minuto efectivo = 0."""
    return efectivo >= 1 and (uds or 0.0) * 60.0 / efectivo or 0.0


def huecos_de(marcas, inicio, fin, umbral, cerrada):
    """v2.12: huecos sin leer de una tarea [(desde, hasta, minutos)]. marcas = horas de sus lecturas en Preparacion.
    Cuenta de inicio a la primera lectura y entre lecturas; si esta cerrada, tambien de la ultima lectura al cierre.
    Sin lecturas (la hizo con la app de codigo de barras) no hay detalle: ningun hueco."""
    if not marcas or not inicio:
        return []
    marcas = [inicio] + sorted(marcas)
    res = []
    for a, b in zip(marcas, marcas[1:]):
        m = (b - a).total_seconds() / 60.0
        if m >= umbral:
            res.append((a, b, m))
    if cerrada and fin and fin > marcas[-1]:
        m = (fin - marcas[-1]).total_seconds() / 60.0
        if m >= umbral:
            res.append((marcas[-1], fin, m))
    return res


class TuctucOperarioTarea(models.Model):
    _name = 'tuctuc.operario.tarea'
    _description = 'TUCTUC Tarea de operario'
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
        ('relevo', 'La siguio otro operario'),
        ('inactividad', 'Sin actividad'),       # v2.19
    ], 'Como se cerro')

    uds_inicio = fields.Float('Uds leidas al empezar', digits=(16, 0))
    uds_fin = fields.Float('Uds leidas al cerrar', digits=(16, 0))
    uds_total = fields.Float('Uds del pedido', digits=(16, 0), help='Uds que pide el pedido al empezar')
    uds = fields.Float('Uds', compute='_compute_resultado', store=True, digits=(16, 0), group_operator='sum')
    minutos = fields.Float('Minutos', compute='_compute_resultado', store=True, digits=(16, 1),
                           group_operator='sum')
    # v2.12: tiempo parado y efectivo (tabla propia). u/h sobre el efectivo y sin media al agrupar (una media de
    # ratios no es la u/h del grupo: la del grupo es la suma de uds entre la suma de efectivo)
    parado = fields.Float('Min parado', compute='_compute_resultado', store=True, digits=(16, 1), group_operator='sum',
                          help='Huecos de tuctuc_operarios.minutos_sin_leer minutos o mas sin leer en Preparacion')
    efectivo = fields.Float('Min efectivos', compute='_compute_resultado', store=True, digits=(16, 1),
                            group_operator='sum', help='Minutos - parado')
    uds_hora = fields.Float('Uds/hora', compute='_compute_resultado', store=True, digits=(16, 1),
                            group_operator=False, help='Uds * 60 / minutos efectivos')
    nota = fields.Char('Nota')
    # v2.5: preparar a dos (lo rellena tuctuc_preparacion al cerrar la tarea)
    a_dos = fields.Boolean('A dos', index=True, help='La OUT la ha preparado con otro operario a la vez')
    companero_id = fields.Many2one('hr.employee', 'Compañero', ondelete='set null')

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
        for t in self:
            t.dia = comun.dia_local(t.inicio) or False

    @api.depends('inicio', 'fin', 'uds_inicio', 'uds_fin', 'estado')
    def _compute_resultado(self):
        cerradas = self.filtered(lambda x: x.fin and x.inicio and isinstance(x.id, int))
        marcas = cerradas._marcas_preparacion()
        umbral = self._minutos_sin_leer_max()
        for t in self:
            if t.fin and t.inicio:
                minutos = max(0.0, (t.fin - t.inicio).total_seconds() / 60.0)
                parado = sum(h[2] for h in huecos_de(marcas.get(t.id), t.inicio, t.fin, umbral, True))
                t.minutos = minutos
                t.uds = max(0.0, t.uds_fin - t.uds_inicio)
                t.parado = min(parado, minutos)
                t.efectivo = max(minutos - t.parado, 0.0)
                t.uds_hora = uds_hora_de(t.uds, t.efectivo)
            else:
                t.minutos = 0.0
                t.uds = 0.0
                t.parado = 0.0
                t.efectivo = 0.0
                t.uds_hora = 0.0

    # ------------------------------------------------------------------ v2.12: una sola cifra de productividad
    def _marcas_preparacion(self, ahora=None):
        """{tarea.id: [horas de las lecturas de su operario en sus OUT entre inicio y fin (o ahora)]}, con una sola
        busqueda para todas. Sin tuctuc_preparacion, todo vacio."""
        res = dict((t.id, []) for t in self)
        if not self or 'tuctuc.preparacion.lectura' not in self.env:
            return res
        ahora = ahora or fields.Datetime.now()
        por_clave = {}
        for t in self:
            for pid in t._pickings().ids:
                por_clave.setdefault((t.employee_id.id, pid), []).append(t)
        if not por_clave:
            return res
        desde = min(t.inicio for t in self)
        hasta = max((t.fin or ahora) for t in self)
        for l in self.env['tuctuc.preparacion.lectura'].sudo().search([
                ('employee_id', 'in', list(set(k[0] for k in por_clave))),
                ('picking_id', 'in', list(set(k[1] for k in por_clave))),
                ('fecha', '>=', desde), ('fecha', '<=', hasta)]):
            for t in por_clave.get((l.employee_id.id, l.picking_id.id), []):
                if t.inicio <= l.fecha <= (t.fin or ahora):
                    res[t.id].append(l.fecha)
        return res

    def _medir(self, ahora, marcas, umbral):
        """Uds, minutos, parado y efectivo de una tarea (cerrada o abierta hasta ahora), con huecos_de(). Igual que
        los campos guardados de las cerradas; en las abiertas suma ademas lo que lleva ahora sin hacer nada."""
        self.ensure_one()
        en_curso = self.estado == 'curso'
        fin_t = ahora if en_curso else (self.fin or self.inicio)
        huecos = huecos_de(marcas, self.inicio, fin_t, umbral, not en_curso)
        parado = sum(h[2] for h in huecos)
        parado_ahora = None
        if en_curso:
            # lo que lleva sin leer ahora (Preparacion o una linea del pedido con la app de codigo de barras)
            ultima = self._ultima_actividad() or self.inicio
            m = max((ahora - ultima).total_seconds() / 60.0, 0.0)
            if m >= umbral:
                parado += m
                parado_ahora = (ultima, m)
            uds = self._uds_hasta_ahora()
            minutos = max((ahora - self.inicio).total_seconds() / 60.0, 0.0)
        else:
            uds = self.uds or 0.0
            minutos = self.minutos or 0.0
        parado = min(parado, minutos)
        efectivo = max(minutos - parado, 0.0)
        return {'uds': uds, 'minutos': minutos, 'parado': parado, 'efectivo': efectivo, 'fin': fin_t,
                'huecos': huecos, 'parado_ahora': parado_ahora, 'uds_hora': uds_hora_de(uds, efectivo),
                'sin_detalle': not marcas and not en_curso and minutos >= 1}

    @api.model
    def resumen_operario_dia(self, dia, ahora=None):
        """v2.12: resumen por operario de las tareas de ese dia (lo abierto, hasta ahora). LA cifra que usan
        Productividad, el correo y la ficha de koroshi_informe, el KPI y la PDA. No escribe nada.
        Devuelve (ops, huecos, parados_ahora):
          ops = {employee_id: {employee_id, codigo, nombre, tareas, acabadas, dejadas, sin_cerrar, curso, uds,
                               minutos, parado, efectivo, uds_hora, sin_detalle, inicio, fin}}
          huecos = [{codigo, nombre, desde, hasta, min, ref}]       (los parados de 15 min o mas)
          parados_ahora = [{codigo, nombre, ref, desde, min, uds_total, leidas}]"""
        Tarea = self.sudo()
        ahora = ahora or fields.Datetime.now()
        umbral = Tarea._minutos_sin_leer_max()
        tareas = Tarea.search([('dia', '=', dia)], order='inicio asc')
        marcas = tareas._marcas_preparacion(ahora)
        ops = {}
        huecos = []
        parados_ahora = []
        for t in tareas:
            e = t.employee_id
            cod = codigo_corto(e.barcode)
            o = ops.setdefault(e.id, {
                'employee_id': e.id, 'codigo': cod, 'nombre': e.name or '', 'tareas': 0, 'acabadas': 0,
                'dejadas': 0, 'sin_cerrar': 0, 'curso': 0, 'uds': 0.0, 'minutos': 0.0, 'parado': 0.0,
                'sin_detalle': 0, 'inicio': None, 'fin': None,
            })
            med = t._medir(ahora, marcas.get(t.id), umbral)
            ref = ((t.batch_id.name if t.tipo == 'agrupacion' else t.picking_id.name) or t.referencia or '')
            ref = re.sub(r'^[^/]+/', '', ref)   # sin el almacén delante: WH-OR/OUT/123 -> OUT/123
            for a, b, m in med['huecos']:
                huecos.append({'codigo': cod, 'nombre': e.name, 'desde': a, 'hasta': b, 'min': m, 'ref': ref})
            if med['parado_ahora']:
                pickings = t._pickings()
                parados_ahora.append({
                    'codigo': cod, 'nombre': e.name, 'ref': ref, 'desde': med['parado_ahora'][0],
                    'min': med['parado_ahora'][1], 'uds_total': t.uds_total or 0.0,
                    'leidas': Tarea._uds_leidas(pickings)})
            if med['sin_detalle']:
                o['sin_detalle'] += 1
            if t.estado == 'curso':
                o['curso'] += 1
            elif t.estado == 'acabada':
                o['acabadas'] += 1
            elif t.estado == 'dejada':
                o['dejadas'] += 1
            else:
                o['sin_cerrar'] += 1
            o['tareas'] += 1
            o['uds'] += med['uds']
            o['minutos'] += med['minutos']
            o['parado'] += med['parado']
            if not o['inicio'] or t.inicio < o['inicio']:
                o['inicio'] = t.inicio
            if not o['fin'] or med['fin'] > o['fin']:
                o['fin'] = med['fin']
        for o in ops.values():
            o['efectivo'] = max(o['minutos'] - o['parado'], 0.0)
            o['uds_hora'] = uds_hora_de(o['uds'], o['efectivo'])
        return ops, huecos, parados_ahora

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

    def _uds_hasta_ahora(self):
        """v2.5: uds de una tarea en curso hasta ahora (el monitor). tuctuc_preparacion la cambia al preparar a dos."""
        self.ensure_one()
        return max(self._uds_leidas(self._pickings()) - (self.uds_inicio or 0.0), 0.0)

    # ------------------------------------------------------------------ v2.8: ¿la esta haciendo ahora?
    @api.model
    def _minutos_sin_leer_max(self):
        valor = self.env['ir.config_parameter'].sudo().get_param('tuctuc_operarios.minutos_sin_leer', '')
        try:
            return int(valor) if valor else MINUTOS_SIN_LEER
        except ValueError:
            return MINUTOS_SIN_LEER

    def _ultima_actividad(self):
        """Ultima vez que alguien hizo algo en el pedido desde que empezo esta tarea: la ultima lectura de este operario
        en Preparacion (leer, deshacer, caja, validar) o la ultima linea leida del pedido (app de codigo de barras:
        el 12/11 Andy dejo Preparacion a las 8:40 y siguio la INT 67365 con codigo de barras hasta las 9:53). Lo mas
        reciente de las dos. Si aun no ha leido nada, la hora en que empezo la tarea."""
        self.ensure_one()
        ultima = self.inicio
        pickings = self._pickings()
        fechas = [self._ultima_lectura(pickings, self.inicio)]
        if 'tuctuc.preparacion.lectura' in self.env:
            lectura = self.env['tuctuc.preparacion.lectura'].sudo().search(
                [('picking_id', 'in', pickings.ids), ('employee_id', '=', self.employee_id.id),
                 ('fecha', '>=', self.inicio)], order='fecha desc', limit=1)
            if lectura:
                fechas.append(lectura.fecha)
        for fecha in fechas:
            if fecha and (not ultima or fecha > ultima):
                ultima = fecha
        return ultima

    def _minutos_sin_leer(self, ahora=None):
        self.ensure_one()
        ultima = self._ultima_actividad()
        if not ultima:
            return 0.0
        return max(((ahora or fields.Datetime.now()) - ultima).total_seconds() / 60.0, 0.0)

    def _trabajando_ahora(self):
        """En curso y con algo leido (o empezada) hace menos de tuctuc_operarios.minutos_sin_leer minutos."""
        self.ensure_one()
        return self.estado == 'curso' and self._minutos_sin_leer() < self._minutos_sin_leer_max()

    def _relevar(self):
        """La sigue otro operario: se cierra como dejada a la hora de su ultima lectura (no cuenta el tiempo parado)."""
        for t in self.filtered(lambda x: x.estado == 'curso'):
            fin = t._ultima_actividad() or fields.Datetime.now()
            t._cerrar('dejada', 'relevo', fin)
        return True

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
            # v2.9: una OUT leída es solo esa OUT, aunque sea de una zona (Z-). La zona entera, leyendo la Z-.
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
    def cron_cerrar(self, inactividad=False):
        """Cada 5 min: cierra las tareas cuyo pedido ya esta validado; las de dias anteriores, sin cerrar.
        v2.19: antes, reabre las cerradas por inactividad en las que el operario ha vuelto a leer (tambien cuando lo
        llama tuctuc_preparacion al validar, para no perder esas uds). Despues, solo desde el cron
        (inactividad=True), cierra las que llevan tuctuc_operarios.minutos_cierre_inactividad min sin hacer nada."""
        self._reabrir_inactivas()
        medianoche_utc = comun.inicio_dia_utc(comun.hoy_local())
        for t in self.sudo().search([('estado', '=', 'curso')]):
            pickings = t._pickings()
            if pickings and self._validado(pickings):
                fin = self._hora_validacion(pickings)
                if fin < t.inicio:
                    fin = t.inicio
                t._cerrar('acabada', 'validada', fin)
            elif t.inicio < medianoche_utc:
                t._cerrar('sin_cerrar', 'medianoche', self._ultima_lectura(pickings, t.inicio))
        if inactividad:
            self._cerrar_inactivas()
        # v2: las asignaciones de la cola cuyo pedido ya esta validado pasan a hechas
        self.env['tuctuc.operario.asignacion'].cron_actualizar()
        return True

    # ------------------------------------------------------------------ v2.19: cierre por inactividad
    @api.model
    def _minutos_cierre_inactividad(self):
        valor = self.env['ir.config_parameter'].sudo().get_param('tuctuc_operarios.minutos_cierre_inactividad', '')
        try:
            return int(valor) if valor not in (False, None, '') else MINUTOS_CIERRE_INACTIVIDAD
        except ValueError:
            return MINUTOS_CIERRE_INACTIVIDAD

    @api.model
    def _cerrar_inactivas(self, ahora=None):
        """Cierra como dejada (inactividad) cada tarea en curso sin actividad en N minutos, con fin = su ultima
        actividad: ese rato no cuenta ni como trabajado ni como presencia. Solo escribe en esta tabla. No se cierra si
        otro operario tiene la misma OUT en curso (preparar a dos: Preparacion parte la ruta por el orden de inicio y
        al volver le cambiaria la mitad). Devuelve las tareas cerradas."""
        minutos = self._minutos_cierre_inactividad()
        cerradas = self.browse()
        if minutos <= 0:
            return cerradas
        ahora = ahora or fields.Datetime.now()
        abiertas = self.sudo().search([('estado', '=', 'curso')])
        pickings = dict((t.id, t._pickings()) for t in abiertas)
        for t in abiertas:
            ultima = t._ultima_actividad() or t.inicio
            if (ahora - ultima).total_seconds() / 60.0 < minutos:
                continue
            a_dos = any(o.id != t.id and o.employee_id != t.employee_id and (pickings[o.id] & pickings[t.id])
                        for o in abiertas)
            if a_dos:
                continue
            t._cerrar('dejada', 'inactividad', max(ultima, t.inicio))
            t.write({'nota': ((t.nota or '') + ' Cerrada sola: %d min sin actividad.' % minutos).strip()})
            cerradas |= t
        return cerradas

    @api.model
    def _reabrir_inactivas(self):
        """Tareas cerradas por inactividad (ultimas 24 h) en las que el operario ha vuelto a leer en Preparacion y no
        ha empezado nada despues: otra tarea desde esa primera lectura, con uds_inicio = uds_fin de la cerrada (asi
        cuenta lo que lea a partir de ahi). Si su asignacion apuntaba a la cerrada, pasa a la nueva."""
        nuevas = self.browse()
        if 'tuctuc.preparacion.lectura' not in self.env:
            return nuevas
        Tarea = self.sudo()
        Lectura = self.env['tuctuc.preparacion.lectura'].sudo()
        Asig = self.env['tuctuc.operario.asignacion'].sudo()
        desde = fields.Datetime.now() - datetime.timedelta(hours=24)
        for t in Tarea.search([('estado', '=', 'dejada'), ('motivo_fin', '=', 'inactividad'), ('fin', '>=', desde)],
                              order='fin asc'):
            emp = t.employee_id
            if Tarea.search_count([('employee_id', '=', emp.id), ('id', '!=', t.id), ('inicio', '>=', t.fin)]):
                continue   # ya ha empezado otra cosa (o ya se reabrio)
            if Tarea.abierta_de(emp):
                continue
            pickings = t._pickings()
            primera = Lectura.search([('picking_id', 'in', pickings.ids), ('employee_id', '=', emp.id),
                                      ('fecha', '>', t.fin)], order='fecha asc', limit=1)
            if not primera:
                continue
            nueva = Tarea.create({
                'employee_id': emp.id,
                'tipo': t.tipo,
                'picking_id': t.picking_id.id,
                'batch_id': t.batch_id.id,
                'referencia': t.referencia,
                'company_id': t.company_id.id,
                'inicio': primera.fecha,
                'uds_inicio': t.uds_fin,
                'uds_total': t.uds_total,
                'nota': 'Sigue tras cerrarse por inactividad.',
            })
            Asig.search([('tarea_id', '=', t.id), ('estado', '=', 'curso')]).write({'tarea_id': nueva.id})
            nuevas |= nueva
        return nuevas

    # ------------------------------------------------------------------ informes
    @api.model
    def action_validadas_sin_operario(self):
        """OUT validadas hoy (salida) que no estan en ninguna tarea."""
        desde = comun.inicio_dia_utc(comun.hoy_local())
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
