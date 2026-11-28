# -*- coding: utf-8 -*-
# =============================================================================
# TUCTUC Operarios v2 - cola de pedidos por operario.
#
#   tuctuc.operario.motivo      motivos de "Saltar" y adonde va la OUT (oficina / final de su cola / sigue suya)
#   tuctuc.operario.dia         modo de reparto del dia (automatico / por pasillos / solo manual)
#   tuctuc.operario.tramo       operarios de hoy (v2.1) y su tramo de lineales para el modo por pasillos
#   tuctuc.operario.asignacion  la cola: operario + OUT o agrupacion, orden y estado
#
# Clon de koroshi_operarios 2.25.0 (reparto.py) para odoo.tuctuc.com (nave de Oriola - Amposta). Cambios:
#   - Multicompañía: el reparto del día es de la nave (uno solo, con la primera compañía de la PDA) y los candidatos
#     salen de todas las compañías de la PDA que tenga el usuario (PRIME, MODA INTIMA, UNITED; tuctuc.almacen).
#   - Qué se da: las OUT directas (las que NO salen del SORTER: esas las reparte PedidosMultiples) y las INT de la
#     estantería al SORTER (oleadas WEB, WEB B&B, PED. INICIAL). Sin agrupaciones Z- (en Oriola no hay).
#   - Sin etiquetas de zona ni matrículas CJ (en Oriola la caja la crea Odoo): «Si se le acaba la cola, darle la
#     siguiente sola» viene encendido.
#   - Sin el tablero del responsable (tipos lote/nota).
#   - _dejadas_hoy, _dejada_por_otros y en_pausa: la medianoche es la del almacén, no la de UTC.
# v2.1: "Repartir ahora" llena la cola de cada operario por bloques.
# Una OUT (o agrupacion) solo puede tener UNA asignacion viva (cola / curso / oficina): indice unico parcial en
# la base de datos, asi dos PDA nunca reciben la misma aunque pidan a la vez.
# Solo escribe en sus tablas y en tuctuc.operario.tarea. No anade campos a albaranes ni agrupaciones.
# =============================================================================
import datetime
import logging
import re

import psycopg2

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.addons.tuctuc_base import comun, pda

from .tarea import PREFIJOS_ZONA

_logger = logging.getLogger(__name__)

VIVAS = ('cola', 'curso', 'oficina')
MAX_POR_OUT = 2         # v2.5: preparar a dos -> titular + un ayudante como mucho
RE_LINEAL = re.compile(r'\bL(\d+)\b')
CANDIDATOS = 400        # OUT libres mas antiguas que se miran cada vez (modo automatico / pasillos)


def _hoy():
    return comun.hoy_local()


def _medianoche_utc():
    """00:00 de hoy en la hora del almacén, en UTC sin zona (en koroshi era la medianoche de UTC: 1-2 h de desfase)."""
    return comun.inicio_dia_utc(comun.hoy_local())


def _companias_pda(env):
    """Compañías de la PDA (tuctuc.almacen) que tiene el usuario de la PDA. Si no tiene ninguna, su compañía."""
    pda = env['tuctuc.almacen'].companias()
    res = pda.filtered(lambda c: c in env.user.company_ids)
    return res or env.company


def _sorters(env):
    """Ubicaciones SORTER de los almacenes de la PDA (WH-OR/SORTER, MODAI/SORTER)."""
    return env['tuctuc.almacen'].activos().mapped('sorter_id')


class TuctucOperarioMotivo(models.Model):
    _name = 'tuctuc.operario.motivo'
    _description = 'TUCTUC Motivo para saltar un pedido'
    _order = 'sequence, id'

    name = fields.Char('Motivo', required=True, translate=False)
    sequence = fields.Integer('Orden', default=10)
    destino = fields.Selection([
        ('oficina', 'Expediciones (no se da a nadie hasta revisarla)'),
        ('final', 'Final de su cola'),
        ('suya', 'Sigue suya y la primera (fin de turno)'),
        ('libre', 'Libre para otro (a quien la deja no le vuelve a salir hoy)'),   # v2.10
        ('pausa', 'Pausa: sigue suya y la primera (comer, café)'),                  # v2.10
    ], 'Adonde va', required=True, default='oficina')
    pide_nota = fields.Boolean('Pide texto', help='Al elegirlo en la PDA se pide escribir el motivo')
    active = fields.Boolean('Activo', default=True)


class TuctucOperarioDia(models.Model):
    _name = 'tuctuc.operario.dia'
    _description = 'TUCTUC Reparto del dia'
    _order = 'fecha desc'
    _rec_name = 'fecha'

    fecha = fields.Date('Dia', required=True, default=lambda self: _hoy(), index=True)
    # TUCTUC: un solo reparto para la nave (las tres compañías); company_id = la primera compañía de la PDA
    company_id = fields.Many2one('res.company', 'Empresa', required=True,
                                 default=lambda self: _companias_pda(self.env)[:1])
    modo = fields.Selection([
        ('auto', 'A · Automatico (la OUT libre mas antigua)'),
        ('pasillos', 'B · Por pasillos (tramo de lineales de cada operario)'),
        ('manual', 'C · Solo manual (solo lo que reparte el responsable)'),
    ], 'Modo de hoy', required=True, default='auto',
        help='Siempre se da primero lo asignado a mano. Cuando se acaba, se usa este modo.')
    pasillos_a_auto = fields.Boolean('Si no hay en su tramo, dar la mas antigua', default=True)
    # v2.1: reparto por bloques al empezar el dia (asi se pueden imprimir las etiquetas de cada uno)
    bloque = fields.Integer('Pedidos por bloque', default=10,
                            help='"Repartir ahora" llena la cola de cada operario hasta este numero de pedidos.')
    aviso_quedan = fields.Integer('Avisar cuando le queden', default=3,
                                  help='En "Operarios de hoy" la linea sale en naranja cuando al operario le quedan '
                                       'estos pedidos o menos.')
    dar_sin_etiqueta = fields.Boolean(
        'Si se le acaba la cola, darle la siguiente sola', default=True,
        help='Encendido: la PDA le da sola la siguiente segun el modo. Apagado: con la cola vacia la PDA dice '
             '"No tienes mas pedidos. Pide a tu responsable" y el responsable reparte otro bloque.')
    dar_int = fields.Boolean(
        'Dar tambien las INT al SORTER (oleadas)', default=True,
        help='Encendido: ademas de las OUT directas se dan las INT de la estanteria al SORTER (WEB, WEB B&B, '
             'PED. INICIAL). Las OUT que salen del SORTER no se dan nunca: las reparte PedidosMultiples.')
    agrupaciones = fields.Boolean('Repartir agrupaciones enteras', default=False,
                                  help='Encendido: una agrupacion cuenta como un solo pedido de la cola y se abre en '
                                       '"procesar agrupacion". Apagado (lo normal en Oriola): sus OUT una a una.')
    solo_preparadas = fields.Boolean('Solo OUT preparadas', default=True,
                                     help='En automatico y por pasillos, solo se dan OUT en estado Preparado.')
    tramo_ids = fields.One2many('tuctuc.operario.tramo', 'dia_id', 'Operarios de hoy', copy=True)
    asignacion_ids = fields.One2many('tuctuc.operario.asignacion', compute='_compute_asignaciones',
                                     string='Colas')
    oficina_ids = fields.One2many('tuctuc.operario.asignacion', compute='_compute_asignaciones',
                                  string='En expediciones')

    _sql_constraints = [('fecha_empresa_unica', 'unique(fecha, company_id)', 'Ya hay un reparto para ese dia.')]

    def _compute_asignaciones(self):
        # TUCTUC: las colas de la nave (todas las compañías de la PDA)
        Asig = self.env['tuctuc.operario.asignacion']
        for d in self:
            d.asignacion_ids = Asig.search([('estado', 'in', ('cola', 'curso'))])
            d.oficina_ids = Asig.search([('estado', '=', 'oficina')])

    @api.model
    def de_hoy(self, company=None):
        """Reparto de hoy. Si no existe, se crea copiando el ultimo (modo, interruptores y tramos).
        TUCTUC: uno para la nave, con la primera compañía de la PDA."""
        company = company or _companias_pda(self.env)[:1]
        hoy = _hoy()
        dia = self.sudo().search([('fecha', '=', hoy), ('company_id', '=', company.id)], limit=1)
        if dia:
            return dia
        ultimo = self.sudo().search([('company_id', '=', company.id)], order='fecha desc', limit=1)
        try:
            with self.env.cr.savepoint():
                if ultimo:
                    return ultimo.copy({'fecha': hoy})
                return self.sudo().create({'fecha': hoy, 'company_id': company.id})
        except psycopg2.IntegrityError:
            # otra PDA lo acaba de crear a la vez
            return self.sudo().search([('fecha', '=', hoy), ('company_id', '=', company.id)], limit=1)

    def action_repartir_ahora(self):
        """Llena hasta el bloque la cola de todos los operarios de hoy."""
        self.ensure_one()
        return self.tramo_ids.action_dar_bloque()

    @api.model
    def action_abrir_hoy(self):
        dia = self.de_hoy()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reparto de hoy'),
            'res_model': self._name,
            'res_id': dia.id,
            'view_mode': 'form',
            'target': 'current',
        }


class TuctucOperarioTramo(models.Model):
    """Operario que trabaja hoy (v2.1) y, para el modo por pasillos, su tramo de lineales (0-0 = sin tramo)."""
    _name = 'tuctuc.operario.tramo'
    _description = 'TUCTUC Operario de hoy y su tramo de lineales'
    _order = 'sequence, id'

    dia_id = fields.Many2one('tuctuc.operario.dia', 'Dia', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer('Orden', default=10)
    employee_id = fields.Many2one('hr.employee', 'Operario', required=True)
    lineal_desde = fields.Integer('Desde lineal', default=0, help='Numero de lineal: L40 -> 40. 0 = sin tramo')
    lineal_hasta = fields.Integer('Hasta lineal', default=0)
    pendientes = fields.Integer('Le quedan', compute='_compute_cola',
                                help='Pedidos en su cola, contando el que esta haciendo')
    cola_baja = fields.Boolean('Cola baja', compute='_compute_cola')

    _sql_constraints = [('operario_dia_unico', 'unique(dia_id, employee_id)',
                         'Ese operario ya esta en el reparto de hoy.')]

    @api.depends('employee_id', 'dia_id.aviso_quedan')
    def _compute_cola(self):
        Asig = self.env['tuctuc.operario.asignacion'].sudo()
        for t in self:
            cola = Asig.cola_de(t.employee_id) if t.employee_id else Asig
            t.pendientes = len(cola)
            t.cola_baja = bool(t.employee_id) and t.pendientes <= t.dia_id.aviso_quedan

    def _tiene_tramo(self):
        self.ensure_one()
        return self.lineal_hasta > 0

    @api.constrains('lineal_desde', 'lineal_hasta')
    def _check_tramo(self):
        for t in self:
            if t.lineal_hasta < t.lineal_desde:
                raise UserError(_('El tramo de %s esta al reves (desde %s hasta %s).')
                                % (t.employee_id.name, t.lineal_desde, t.lineal_hasta))

    def action_dar_bloque(self):
        """Llena la cola de estos operarios hasta el bloque del dia, repartiendo por turnos (uno a cada uno)."""
        if not self:
            raise UserError(_('Pon primero los operarios de hoy.'))
        dia = self[0].dia_id
        if dia.modo == 'manual':
            raise UserError(_('En modo "C · Solo manual" no se reparte solo: asigna a mano (Accion > Asignar a '
                              'operario en la lista de albaranes) o cambia el modo.'))
        if dia.bloque <= 0:
            raise UserError(_('"Pedidos por bloque" tiene que ser mayor que 0.'))
        Asig = self.env['tuctuc.operario.asignacion'].sudo()
        falta = {t.id: max(0, dia.bloque - len(Asig.cola_de(t.employee_id))) for t in self}
        listas = {}
        usados = set()
        dados = {t.id: 0 for t in self}
        seguir = True
        while seguir:
            seguir = False
            for t in self:
                if falta[t.id] <= 0:
                    continue
                asig = Asig._dar_de_listas(dia, t.employee_id, listas, usados)
                if asig:
                    falta[t.id] -= 1
                    dados[t.id] += 1
                    seguir = True
                else:
                    falta[t.id] = 0
        resumen = ', '.join('%s %d' % (t.employee_id.name, dados[t.id]) for t in self)
        total = sum(dados.values())
        _logger.info('TUCTUC OPERARIOS repartir bloque (%s): %s', dia.modo, resumen)
        if not total:
            raise UserError(_('No se ha repartido nada: o ya tienen el bloque lleno o no quedan pedidos libres.'))
        # True: el formulario se recarga y se ve "Le quedan" de cada uno
        return True

class TuctucOperarioAsignacion(models.Model):
    _name = 'tuctuc.operario.asignacion'
    _description = 'TUCTUC Pedido asignado a un operario'
    _order = 'employee_id, estado, secuencia, id'

    name = fields.Char('Pedido', compute='_compute_name', store=True)
    employee_id = fields.Many2one('hr.employee', 'Operario', index=True, ondelete='restrict',
                                  help='Vacio = en oficina sin operario')
    tipo = fields.Selection([('out', 'Pedido (OUT)'), ('agrupacion', 'Agrupacion')], 'Tipo', required=True,
                            default='out')
    picking_id = fields.Many2one('stock.picking', 'Pedido (OUT)', index=True, ondelete='cascade')
    batch_id = fields.Many2one('stock.picking.batch', 'Agrupacion', index=True, ondelete='cascade')
    secuencia = fields.Integer('Orden', default=100)
    estado = fields.Selection([
        ('cola', 'En cola'),
        ('curso', 'Haciendose'),
        ('oficina', 'En expediciones'),
        ('hecha', 'Hecha'),
        ('quitada', 'Quitada'),
    ], 'Estado', required=True, default='cola', index=True)
    origen = fields.Selection([
        ('manual', 'Responsable'),
        ('auto', 'Automatico'),
        ('pasillos', 'Por pasillos'),
        ('leida', 'Leida en la PDA'),
    ], 'Como se asigno', required=True, default='manual')
    motivo_id = fields.Many2one('tuctuc.operario.motivo', 'Motivo del salto')
    nota = fields.Char('Nota')
    saltos = fields.Integer('Veces saltada')
    fecha_salto = fields.Datetime('Ultimo salto')
    tarea_id = fields.Many2one('tuctuc.operario.tarea', 'Tarea actual', ondelete='set null')
    # v2.5: preparar a dos desde el reparto
    ayudante_id = fields.Many2one('hr.employee', 'Ayudante', index=True, ondelete='set null',
                                  help='Operario que entra de ayudante cuando el titular empieza esta OUT')
    uds = fields.Integer('Uds', compute='_compute_a_dos', help='Uds que pide la OUT (o la agrupacion)')
    a_dos = fields.Boolean('Para hacer a dos', compute='_compute_a_dos', search='_buscar_a_dos',
                           help='OUT suelta con al menos tuctuc_operarios.uds_a_dos uds (150 por defecto)')
    tienda = fields.Char('Tienda', related='picking_id.partner_id.name')
    estado_out = fields.Selection(related='picking_id.state', string='Estado OUT')
    company_id = fields.Many2one('res.company', 'Empresa', required=True, default=lambda self: self.env.company,
                                 index=True)

    @api.model
    def _uds_a_dos(self):
        try:
            return int(self.env['ir.config_parameter'].sudo().get_param('tuctuc_operarios.uds_a_dos', '150') or 150)
        except ValueError:
            return 150

    def _compute_a_dos(self):
        minimo = self._uds_a_dos()
        Tarea = self.env['tuctuc.operario.tarea']
        for a in self:
            a.uds = int(Tarea._uds_pedidas(a._pickings()))
            a.a_dos = a.tipo == 'out' and minimo > 0 and a.uds >= minimo

    def _buscar_a_dos(self, operador, valor):
        minimo = self._uds_a_dos()
        self.env.cr.execute("""
            SELECT m.picking_id FROM stock_move m
             WHERE m.state NOT IN ('cancel', 'done') AND m.picking_id IN (
                   SELECT picking_id FROM tuctuc_operario_asignacion WHERE tipo = 'out' AND picking_id IS NOT NULL
                      AND estado IN ('cola', 'curso', 'oficina'))
             GROUP BY m.picking_id HAVING SUM(m.product_uom_qty) >= %s""", (minimo,))
        grandes = [r[0] for r in self.env.cr.fetchall()]
        positivo = (operador == '=' and valor) or (operador == '!=' and not valor)
        dom = [('tipo', '=', 'out'), ('picking_id', 'in', grandes)]
        return dom if positivo else ['!'] + ['&'] + dom

    @api.depends('tipo', 'picking_id', 'batch_id')
    def _compute_name(self):
        for a in self:
            a.name = a.batch_id.name if a.tipo == 'agrupacion' else a.picking_id.name

    def init(self):
        # una sola asignacion viva por OUT y por agrupacion (dos PDA a la vez: la segunda falla y coge otra)
        self.env.cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS tuctuc_operario_asignacion_picking_viva
                ON tuctuc_operario_asignacion (picking_id)
                WHERE picking_id IS NOT NULL AND tipo = 'out' AND estado IN ('cola', 'curso', 'oficina')""")
        self.env.cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS tuctuc_operario_asignacion_batch_viva
                ON tuctuc_operario_asignacion (batch_id)
                WHERE batch_id IS NOT NULL AND tipo = 'agrupacion' AND estado IN ('cola', 'curso', 'oficina')""")

    # ------------------------------------------------------------------ helpers
    def _pickings(self):
        self.ensure_one()
        if self.tipo == 'agrupacion':
            return self.batch_id.sudo().picking_ids
        return self.picking_id.sudo()

    def _terminada(self):
        """True si ya no hay nada que hacer: validada, cancelada o borrada."""
        self.ensure_one()
        pickings = self._pickings()
        vivas = pickings.filtered(lambda p: p.state not in ('done', 'cancel'))
        return not vivas

    @api.model
    def _viva_de(self, picking=None, lote=None):
        dom = [('estado', 'in', VIVAS)]
        if lote:
            dom += [('tipo', '=', 'agrupacion'), ('batch_id', '=', lote.id)]
        else:
            dom += [('tipo', '=', 'out'), ('picking_id', '=', picking.id)]
        return self.sudo().search(dom, limit=1)

    @api.model
    def _crear_segura(self, vals):
        """Crea la asignacion. Si otra PDA acaba de coger esa OUT (indice unico), devuelve False."""
        try:
            with self.env.cr.savepoint():
                return self.sudo().create(vals)
        except psycopg2.IntegrityError:
            return False

    @api.model
    def _ultima_secuencia(self, employee):
        ultima = self.sudo().search([('employee_id', '=', employee.id), ('estado', '=', 'cola')],
                                    order='secuencia desc', limit=1)
        return (ultima.secuencia if ultima else 0) + 10

    @api.model
    def _primera_secuencia(self, employee):
        primera = self.sudo().search([('employee_id', '=', employee.id), ('estado', 'in', ('cola', 'curso'))],
                                     order='secuencia asc', limit=1)
        return (primera.secuencia if primera else 100) - 10

    def json(self):
        self.ensure_one()
        return {
            'id': self.id,
            'ref': self.name or '',
            'tipo': self.tipo,
            'picking_name': self.picking_id.name or '',
            'batch_id': self.batch_id.id if self.tipo == 'agrupacion' else False,
            'tienda': '' if self.tipo == 'agrupacion' else (self.picking_id.partner_id.name or ''),
            'estado': self.estado,
        }

    # ------------------------------------------------------------------ candidatos (modo automatico / pasillos)
    @api.model
    def _lineal(self, picking):
        """Lineal mas bajo de las ubicaciones reservadas de la OUT (L77 P38 C2 -> 77), o None."""
        numeros = []
        for ml in picking.move_line_ids:
            m = RE_LINEAL.search(ml.location_id.complete_name or '')
            if m:
                numeros.append(int(m.group(1)))
        return min(numeros) if numeros else None

    @api.model
    def _pickings_tramo(self, tramo, companias):
        """v2.12: ids de las OUT sin validar con alguna linea en una ubicacion del tramo (L40..L60), con una consulta
        (hay mas de 100.000 ubicaciones con L: no se pueden leer todas cada vez). Mismo lineal que RE_LINEAL."""
        self.env['stock.move.line'].flush(['picking_id', 'location_id'])
        self.env.cr.execute("""
            SELECT DISTINCT ml.picking_id
              FROM stock_move_line ml
              JOIN stock_picking p ON p.id = ml.picking_id
              JOIN stock_location l ON l.id = ml.location_id
             WHERE p.company_id = ANY(%s)
               AND p.state IN ('assigned', 'confirmed')
               AND substring(l.complete_name from '\\mL([0-9]+)\\M')::int BETWEEN %s AND %s""",
                            (companias.ids, tramo.lineal_desde, tramo.lineal_hasta))
        return [r[0] for r in self.env.cr.fetchall()]

    @api.model
    def _candidatos(self, dia, employee, tramo=None):
        """OUT directas e INT al SORTER (y agrupaciones si esta encendido) libres, de la mas antigua a la mas nueva.
        TUCTUC: de todas las compañías de la PDA que tenga el usuario. Las OUT que salen del SORTER no se dan nunca
        (las reparte PedidosMultiples)."""
        Picking = self.env['stock.picking'].sudo()
        companias = _companias_pda(self.env)
        sorters = _sorters(self.env)
        cogidas = self.sudo().search([('estado', 'in', VIVAS), ('tipo', '=', 'out')]).mapped('picking_id')
        dejadas = self._dejadas_hoy(employee)   # v2.10: «Dejar este pedido»: a este operario no se le vuelve a dar
        # OUT directas: ni las de los tipos de pedido que van por oleada (WEB, WEB B&B, PED. INICIAL: parámetro
        # tuctuc_base.tipos_oleada; el 28/11 eran 1.084 de las 1.157 OUT preparadas) ni las que salen del SORTER
        # 1.0.1 (revisión 28/11, T1): las de oleada salen de una consulta (_oleada_pendientes) y van al «not in» de
        # abajo. Antes, '!' + sale_id.s_order_type_id.name: Odoo 13 cargaba los ids de todos los pedidos de esos tipos
        # (642.340 el 28/11) en cada «siguiente», y el NOT IN dejaba fuera las OUT sin pedido de venta.
        que = [('picking_type_code', '=', 'outgoing')]
        oleada = self._oleada_pendientes(companias)
        if sorters:
            que = expression.AND([que, ['!', ('location_id', 'child_of', sorters.ids)]])
            if dia.dar_int:
                que = expression.OR([que, [('picking_type_code', '=', 'internal'),
                                           ('location_dest_id', 'child_of', sorters.ids)]])
        almacenes = self.env['tuctuc.almacen'].activos().mapped('warehouse_id')
        dom = expression.AND([que, [('company_id', 'in', companias.ids),
                                    ('picking_type_id.warehouse_id', 'in', almacenes.ids),
                                    ('id', 'not in', (cogidas | dejadas.mapped('picking_id')).ids + oleada)]])
        dom += [('state', '=', 'assigned')] if dia.solo_preparadas else [('state', 'in', ('assigned', 'confirmed'))]
        # OUT sueltas: sin agrupacion de zonas (las de una Z- solo se dan con la agrupacion entera).
        # v2.12: las Z- fuera EN EL DOMINIO, antes del limite (si no, 400 OUT de zonas llenaban el limite y no quedaba
        # ninguna suelta)
        for pref in PREFIJOS_ZONA:
            dom += ['|', ('batch_id', '=', False), '!', ('batch_id.name', '=like', pref + '%')]
        if tramo:
            # v2.12: solo las que tienen alguna linea en el tramo (en el dominio, antes del limite); despues, el lineal
            # mas bajo (el de siempre) calculado una sola vez por OUT
            dom.append(('id', 'in', self._pickings_tramo(tramo, companias)))
        sueltas = Picking.search(dom, order='scheduled_date asc, id asc', limit=CANDIDATOS)
        if tramo:
            con_lineal = [(p, self._lineal(p)) for p in sueltas]
            sueltas = [p for p, lin in con_lineal
                       if lin is not None and tramo.lineal_desde <= lin <= tramo.lineal_hasta]
        lista = [(p.scheduled_date or p.create_date, 'out', p) for p in sueltas]
        if dia.agrupaciones and not tramo:
            Batch = self.env['stock.picking.batch'].sudo()
            cogidos = self.sudo().search([('estado', 'in', VIVAS), ('tipo', '=', 'agrupacion')]).mapped('batch_id')
            cogidos |= dejadas.filtered(lambda a: a.tipo == 'agrupacion').mapped('batch_id')   # v2.10
            lotes = Batch.search([('state', 'in', ('draft', 'in_progress')),
                                  ('company_id', 'in', companias.ids), ('id', 'not in', cogidos.ids)],
                                 order='create_date asc, id asc', limit=50)
            for b in lotes:
                vivas = b.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
                if vivas & cogidas:   # v2.9: alguien hace una OUT de esta zona suelta: la zona no se da entera
                    continue
                if vivas and (not dia.solo_preparadas or any(p.state == 'assigned' for p in vivas)):
                    lista.append((b.create_date, 'agrupacion', b))
        lista.sort(key=lambda x: (x[0] or datetime.datetime.max, x[2].id))
        return lista

    @api.model
    def _oleada_pendientes(self, companias):
        """1.0.1 (T1): ids de las OUT sin hacer de los tipos de pedido que van por oleada (parámetro
        tuctuc_base.tipos_oleada: WEB, WEB B&B, PED. INICIAL), con una consulta sobre las OUT abiertas (el 28/11, unas
        1.100). Vacío si no hay tipos o la base de datos no tiene sale.order.s_order_type_id (sales_ext)."""
        tipos = pda.tipos_oleada(self.env)
        campo = self.env['sale.order']._fields.get('s_order_type_id')
        if not tipos or not campo or not campo.store or not companias:
            return []
        tabla = self.env[campo.comodel_name]._table
        self.env['stock.picking'].flush(['sale_id', 'state', 'company_id', 'picking_type_id'])
        self.env.cr.execute("""
            SELECT p.id
              FROM stock_picking p
              JOIN stock_picking_type pt ON pt.id = p.picking_type_id AND pt.code = 'outgoing'
              JOIN sale_order so ON so.id = p.sale_id
              JOIN {tabla} t ON t.id = so.s_order_type_id
             WHERE p.state NOT IN ('done', 'cancel', 'draft')
               AND p.company_id = ANY(%s)
               AND t.name = ANY(%s)""".format(tabla=tabla), (companias.ids, tipos))
        return [r[0] for r in self.env.cr.fetchall()]

    @api.model
    def _dejadas_hoy(self, employee):
        """v2.10: lo que este operario ha dejado hoy con «Dejar este pedido» (motivo con destino libre)."""
        if not employee:
            return self.browse()
        desde = _medianoche_utc()
        return self.sudo().search([('employee_id', '=', employee.id), ('estado', '=', 'quitada'),
                                   ('motivo_id.destino', '=', 'libre'), ('fecha_salto', '>=', desde)])

    @api.model
    def _dejada_por_otros(self, asig, employee):
        """v2.11: otros operarios que hoy ya han dejado este pedido (u agrupación) con «Dejar este pedido»."""
        desde = _medianoche_utc()
        dom = [('estado', '=', 'quitada'), ('motivo_id.destino', '=', 'libre'), ('fecha_salto', '>=', desde),
               ('employee_id', '!=', employee.id), ('id', '!=', asig.id)]
        if asig.tipo == 'agrupacion':
            dom += [('tipo', '=', 'agrupacion'), ('batch_id', '=', asig.batch_id.id)]
        else:
            dom += [('tipo', '=', 'out'), ('picking_id', '=', asig.picking_id.id)]
        return self.sudo().search(dom).mapped('employee_id')

    @api.model
    def soltar(self, employee):
        """v2.25 (26/11, una operaria se quedó atada a un pedido de About You: la pausa la devolvía siempre a él).
        Desde la pausa de Lecturas, la persona deja el pedido que hace o el que tiene en pausa: queda libre para otro,
        como «Dejar este pedido» de la PDA (si otro ya lo dejó hoy, a expediciones). Lo leído no se toca. El
        responsable lo ve en el Tablero («Pedidos dejados hoy»)."""
        Asig = self.sudo()
        actual = Asig.search([('employee_id', '=', employee.id), ('estado', '=', 'curso')],
                             order='write_date desc', limit=1)
        if not actual:
            actual = Asig.search([('employee_id', '=', employee.id), ('estado', '=', 'cola'),
                                  ('motivo_id.destino', '=', 'pausa')], order='fecha_salto desc', limit=1)
        if not actual:
            raise UserError(_('No tienes ningún pedido empezado ni en pausa'))
        motivo = self.env['tuctuc.operario.motivo'].sudo().search([('destino', '=', 'libre')], limit=1)
        if not motivo:
            raise UserError(_('Falta el motivo «Dejar este pedido» en Odoo: avisa al responsable'))
        return self.saltar(employee, motivo, _('Dejado desde Lecturas'), actual=actual)

    @api.model
    def en_pausa(self):
        """v2.11: quién está ahora en pausa (comer, café): su OUT sigue en cola con el motivo «pausa» de hoy y no ha
        empezado nada desde entonces. [(asignación, hora de la pausa)]"""
        desde = _medianoche_utc()
        asigs = self.sudo().search([('estado', '=', 'cola'), ('motivo_id.destino', '=', 'pausa'),
                                    ('fecha_salto', '>=', desde)], order='fecha_salto asc')
        Tarea = self.env['tuctuc.operario.tarea'].sudo()
        res = []
        for a in asigs:
            if Tarea.search_count([('employee_id', '=', a.employee_id.id), '|', ('estado', '=', 'curso'),
                                   ('inicio', '>', a.fecha_salto)]):
                continue   # ya ha vuelto (o ha empezado otra cosa)
            res.append(a)
        return res

    @api.model
    def _intentos(self, dia, employee):
        """Por donde buscar segun el modo: [('pasillos', tramo), ('auto', None)]."""
        if dia.modo == 'manual':
            return []
        if dia.modo == 'pasillos':
            tramo = dia.tramo_ids.filtered(lambda t: t.employee_id == employee and t._tiene_tramo())[:1]
            intentos = [('pasillos', tramo)] if tramo else []
            if not tramo or dia.pasillos_a_auto:
                intentos.append(('auto', None))
            return intentos
        return [('auto', None)]

    @api.model
    def _crear_para(self, employee, dia, origen, tipo, obj):
        vals = {'employee_id': employee.id, 'tipo': tipo, 'origen': origen, 'estado': 'cola',
                'secuencia': self._ultima_secuencia(employee),
                'company_id': obj.company_id.id or dia.company_id.id}
        if tipo == 'agrupacion':
            vals['batch_id'] = obj.id
        else:
            vals.update({'picking_id': obj.id, 'batch_id': obj.batch_id.id or False})
        return self._crear_segura(vals)

    @api.model
    def _dar_nueva(self, employee, dia):
        """La PDA pide y la cola esta vacia: le da la siguiente libre segun el modo, solo si el responsable lo ha
        dejado encendido (v2.1: si no, espera a que le repartan otro bloque con etiquetas)."""
        if not dia.dar_sin_etiqueta:
            return False
        for origen, tramo in self._intentos(dia, employee):
            for _fecha, tipo, obj in self._candidatos(dia, employee, tramo):
                asig = self._crear_para(employee, dia, origen, tipo, obj)
                if asig:
                    return asig
        return False

    @api.model
    def _dar_de_listas(self, dia, employee, listas, usados):
        """Como _dar_nueva, pero para repartir bloques: los candidatos se buscan una sola vez por tramo y se van
        gastando (listas y usados se comparten entre todos los operarios del reparto)."""
        for origen, tramo in self._intentos(dia, employee):
            clave = tramo.id if tramo else 'auto'
            if clave not in listas:
                listas[clave] = self._candidatos(dia, employee, tramo)
            lista = listas[clave]
            while lista:
                _fecha, tipo, obj = lista.pop(0)
                if (tipo, obj.id) in usados:
                    continue
                usados.add((tipo, obj.id))
                asig = self._crear_para(employee, dia, origen, tipo, obj)
                if asig:
                    return asig
        return False

    # ------------------------------------------------------------------ PDA
    @api.model
    def cola_de(self, employee):
        return self.sudo().search([('employee_id', '=', employee.id), ('estado', 'in', ('cola', 'curso'))],
                                  order='secuencia asc, id asc')

    @api.model
    def siguiente(self, employee):
        """Lo que tiene que hacer ahora el operario. Devuelve (asignacion, nueva).
        nueva=False si sigue con la que ya estaba haciendo (no hace falta abrirla sola al volver)."""
        dia = self.env['tuctuc.operario.dia'].de_hoy()
        actual = self.sudo().search([('employee_id', '=', employee.id), ('estado', '=', 'curso')],
                                    order='write_date desc', limit=1)
        if actual:
            if actual._terminada():
                actual._cerrar_hecha()
            else:
                actual._asegurar_tarea(employee)
                return actual, False
        # v2.5: el responsable le ha puesto de ayudante en una OUT que su titular ya esta haciendo
        Tarea = self.env['tuctuc.operario.tarea'].sudo()
        for ayuda in self.sudo().search([('ayudante_id', '=', employee.id), ('estado', '=', 'curso'),
                                         ('tipo', '=', 'out')], order='write_date asc'):
            if ayuda._terminada():
                continue
            if Tarea.search_count([('employee_id', '=', employee.id), ('picking_id', '=', ayuda.picking_id.id),
                                   ('estado', '=', 'dejada'), ('motivo_fin', '!=', 'inactividad')]):
                continue   # ya ayudo y lo dejo: no se le vuelve a meter
            mia = Tarea.search([('employee_id', '=', employee.id), ('picking_id', '=', ayuda.picking_id.id),
                                ('estado', '=', 'curso')], limit=1)
            if not mia:
                try:
                    self.ayudante_de(employee, 'out', ayuda.picking_id)   # comprueba el maximo de dos
                except UserError:
                    continue
                self.unirse(employee, ayuda)
            return ayuda, not mia
        for asig in self.cola_de(employee):
            if asig._terminada():
                asig._cerrar_hecha()
                continue
            asig._empezar(employee)
            return asig, True
        asig = self._dar_nueva(employee, dia)
        if asig:
            asig._empezar(employee)
            return asig, True
        return self.browse(), True

    def _empezar(self, employee):
        """Pasa a 'haciendose' y empieza la tarea (productividad)."""
        self.ensure_one()
        Tarea = self.env['tuctuc.operario.tarea'].sudo()
        otras = self.sudo().search([('employee_id', '=', employee.id), ('estado', '=', 'curso'),
                                    ('id', '!=', self.id)])
        if otras:
            # no deberia pasar: la que estaba haciendo vuelve la primera de su cola
            otras.write({'estado': 'cola', 'secuencia': self._primera_secuencia(employee)})
        codigo = self.batch_id.name if self.tipo == 'agrupacion' else self.picking_id.name
        tarea, _msg = Tarea.empezar(employee, codigo)
        self.write({'estado': 'curso', 'tarea_id': tarea.id})
        return tarea

    def _asegurar_tarea(self, employee):
        """Si la tarea se cerro (medianoche, fin de turno), empieza otra para no contar la noche."""
        self.ensure_one()
        if self.tarea_id and self.tarea_id.estado == 'curso':
            return self.tarea_id
        return self._empezar(employee)

    def _cerrar_hecha(self):
        for a in self:
            a.write({'estado': 'hecha'})
        return True

    @api.model
    def saltar(self, employee, motivo, nota='', actual=None):
        """La OUT que esta haciendo se salta. Devuelve (asignacion saltada, destino). v2.25: con actual, esa (la de
        la pausa, desde soltar)."""
        if not actual:
            actual = self.sudo().search([('employee_id', '=', employee.id), ('estado', '=', 'curso')],
                                        order='write_date desc', limit=1)
        if not actual:
            raise UserError(_('No tienes ningun pedido empezado'))
        if motivo.pide_nota and not (nota or '').strip():
            raise UserError(_('Escribe el motivo'))
        tarea = actual.tarea_id
        if tarea and tarea.estado == 'curso':
            tarea._cerrar('dejada', 'saltar')
            tarea.write({'nota': ('%s %s' % (motivo.name, nota or '')).strip()})
        vals = {'motivo_id': motivo.id, 'nota': (nota or '').strip(), 'saltos': actual.saltos + 1,
                'fecha_salto': fields.Datetime.now(), 'tarea_id': False}
        if motivo.destino == 'oficina':
            vals['estado'] = 'oficina'
        elif motivo.destino == 'libre':
            vals['estado'] = 'quitada'   # v2.10: libre para otro; _candidatos no se la vuelve a dar a este
            otros = self._dejada_por_otros(actual, employee)
            if otros:
                # v2.11: ya la dejó otro hoy: algo le pasa al pedido -> a expediciones, que lo revisen
                nombres = ', '.join(otros.mapped('name') + [employee.name])
                vals.update({'estado': 'oficina',
                             'nota': ('Dejado por %s. %s' % (nombres, vals.get('nota') or '')).strip()})
        elif motivo.destino == 'final':
            vals.update({'estado': 'cola', 'secuencia': self._ultima_secuencia(employee)})
        else:
            vals.update({'estado': 'cola', 'secuencia': self._primera_secuencia(employee)})
        actual.write(vals)
        return actual, ('oficina' if vals.get('estado') == 'oficina' else motivo.destino)

    @api.model
    def leida_a_mano(self, employee, tipo, picking, lote):
        """El operario lee una OUT a mano: si esta libre (o ya es suya) pasa a ser la que hace."""
        objetivo_lote = lote if tipo == 'agrupacion' else None
        viva = self._viva_de(picking=picking if tipo == 'out' else None, lote=objetivo_lote)
        zona = picking.batch_id if tipo == 'out' and picking else None
        if zona and (zona.name or '').startswith(PREFIJOS_ZONA):
            # v2.9: OUT de una zona leída sola: no si otro está haciendo ahora la zona entera
            ahora = self._tareas_de_otros(employee, 'agrupacion', picking, zona).filtered(
                lambda t: t._trabajando_ahora())
            if ahora:
                raise UserError(_('%s es de la zona %s y la esta haciendo %s')
                                % (picking.name, zona.name, ', '.join(ahora.mapped('employee_id.name'))))
        if viva and viva.estado == 'oficina':
            # v2.16: antes «Que la libere el responsable». Ahora quien la lee se la queda y sigue donde estaba;
            # en la nota queda quien la ha recogido (se ve en Reparto, pestaña «En expediciones» / tareas).
            nota = ('%s Recogido por %s.' % (viva.nota or '', employee.name)).strip()
            viva.write({'employee_id': employee.id, 'estado': 'cola', 'tarea_id': False, 'nota': nota,
                        'secuencia': self._primera_secuencia(employee)})
        if viva and viva.employee_id and viva.employee_id != employee:
            # v2.8: si otro la esta haciendo AHORA (ha leido hace poco), sigue siendo suya. Si nadie la esta haciendo
            # (la dejo, se paro o aun no la habia empezado), se la queda quien la lee, sin preguntar nada.
            otras = self._tareas_de_otros(employee, tipo, picking, lote)
            ahora = otras.filtered(lambda t: t._trabajando_ahora())
            if ahora:
                raise UserError(_('%s la esta haciendo %s') % (viva.name, ', '.join(ahora.mapped('employee_id.name'))))
            otras._relevar()
            viva.write({'employee_id': employee.id, 'estado': 'cola', 'tarea_id': False,
                        'secuencia': self._primera_secuencia(employee)})
        actual = self.sudo().search([('employee_id', '=', employee.id), ('estado', '=', 'curso')])
        if actual and actual != viva:
            # la que estaba haciendo vuelve la primera de su cola
            actual.write({'estado': 'cola', 'secuencia': self._primera_secuencia(employee), 'tarea_id': False})
        if not viva:
            vals = {'employee_id': employee.id, 'tipo': tipo, 'origen': 'leida', 'estado': 'cola',
                    'secuencia': self._primera_secuencia(employee), 'company_id': (lote or picking).company_id.id}
            if tipo == 'agrupacion':
                vals['batch_id'] = lote.id
            else:
                vals.update({'picking_id': picking.id, 'batch_id': picking.batch_id.id or False})
            viva = self._crear_segura(vals)
            if not viva:
                raise UserError(_('Otra PDA acaba de coger este pedido. Lee otro.'))
        return viva

    @api.model
    def ayudante_de(self, employee, tipo, picking):
        """v2.4: asignacion de una OUT suelta que ya esta haciendo OTRO operario (en curso). Si la hay, quien la lee
        entra de ayudante (preparar a dos) en vez de dar el error «esta asignada a X»."""
        if tipo != 'out' or not picking:
            return self.browse()
        viva = self._viva_de(picking=picking)
        if viva and viva.estado == 'curso' and viva.employee_id and viva.employee_id != employee:
            # v2.8: solo es «ayudar» si alguien la esta haciendo ahora (ha leido hace menos de
            # tuctuc_operarios.minutos_sin_leer). Si no, nada: leida_a_mano se la da a quien la lee.
            otras = self._tareas_de_otros(employee, tipo, picking, self.env['stock.picking.batch'])
            ahora = otras.filtered(lambda t: t._trabajando_ahora())
            if not ahora:
                return self.browse()
            # las tareas paradas de otros (se fueron sin dejarla) se cierran: no cuentan para el «como mucho dos»
            (otras - ahora)._relevar()
            # v2.5: como mucho dos por OUT (titular + un ayudante)
            otros = ahora.mapped('employee_id')
            if len(otros) >= MAX_POR_OUT:
                raise UserError(_('Ya hay %s operarios con %s (%s). Lee otro pedido.')
                                % (len(otros), picking.name, ', '.join(otros.mapped('name'))))
            return viva
        return self.browse()

    @api.model
    def _tareas_de_otros(self, employee, tipo, picking, lote):
        """v2.8: tareas en curso de OTROS operarios con este pedido (OUT suelta) o esta agrupacion."""
        Tarea = self.env['tuctuc.operario.tarea'].sudo()
        if tipo == 'agrupacion':
            dom = [('tipo', '=', 'agrupacion'), ('batch_id', '=', lote.id)]
        else:
            dom = [('tipo', '=', 'out'), ('picking_id', '=', picking.id)]
        return Tarea.search(dom + [('estado', '=', 'curso'), ('employee_id', '!=', employee.id)])

    @api.model
    def quien_la_hace(self, employee, picking):
        """v2.8: operarios que estan haciendo ahora esta OUT suelta (para el «¿Ayudar a X?»)."""
        otras = self._tareas_de_otros(employee, 'out', picking, self.env['stock.picking.batch'])
        return otras.filtered(lambda t: t._trabajando_ahora()).mapped('employee_id')

    @api.model
    def unirse(self, employee, viva):
        """v2.4: el operario entra de ayudante en la OUT de otro. La asignacion sigue siendo del titular; el ayudante
        solo tiene su tarea. Lo que estaba haciendo vuelve el primero de su cola (igual que al leer una OUT a mano)."""
        actual = self.sudo().search([('employee_id', '=', employee.id), ('estado', '=', 'curso')])
        if actual:
            actual.write({'estado': 'cola', 'secuencia': self._primera_secuencia(employee), 'tarea_id': False})
        tarea, _msg = self.env['tuctuc.operario.tarea'].sudo().empezar(employee, viva.picking_id.name)
        return tarea

    # ------------------------------------------------------------------ responsable
    def action_liberar(self):
        """Oficina -> libre (se podra dar otra vez en automatico)."""
        self.filtered(lambda a: a.estado == 'oficina').write({'estado': 'quitada'})
        return True

    def action_quitar(self):
        """Quita de la cola. Si se estaba haciendo, la tarea se cierra como dejada."""
        for a in self.filtered(lambda x: x.estado in ('cola', 'curso')):
            if a.tarea_id and a.tarea_id.estado == 'curso':
                a.tarea_id._cerrar('dejada', 'manual')
            a.write({'estado': 'quitada', 'tarea_id': False})
        return True

    def action_subir(self):
        """La pone la primera de la cola de su operario."""
        for a in self.filtered(lambda x: x.estado == 'cola' and x.employee_id):
            a.secuencia = self._primera_secuencia(a.employee_id)
        return True

    @api.model
    def cron_actualizar(self):
        """Cada 5 min: marca como hechas las asignaciones cuyo pedido ya esta validado o cancelado."""
        for a in self.sudo().search([('estado', 'in', ('cola', 'curso', 'oficina'))]):
            if a._terminada():
                a._cerrar_hecha()
        return True
