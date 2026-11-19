# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Operarios v2.20.0 - Tablero del responsable (Almacén 2).
# Diseño: bin/versiones/diseno-tablero-responsable_2026-11-19_v5.md
#
# El tablero es una vista kanban de la cola de siempre (koroshi.operario.asignacion), una columna por operario.
# No es una cola nueva. Lo nuevo:
#   - estado 'pieza': lo que hay «Por repartir» (columna sin operario). Se recalcula al abrir el tablero y con
#     «Actualizar»: una pieza por agrupación viva con OUT libres (zonas Z-, WEB_...), las OUT sueltas libres más
#     antiguas y una «Nota» en blanco.
#   - tipo 'lote': tarjeta «zona o agrupación OUT a OUT». Al pedir la siguiente, la PDA le da la siguiente OUT
#     libre de esa agrupación (por el número de CAJA de la nota, el orden que pone koroshi_zonas). Varias personas
#     pueden tener la misma: cada OUT es de una sola (índice único de siempre).
#   - tipo 'nota': texto del responsable. La PDA lo enseña con «Hecho, siguiente».
# Las tarjetas 'lote' y 'nota' nunca están 'curso' (siguen 'cola' hasta acabar): las búsquedas de «lo que está
# haciendo» (estado 'curso') siguen viendo solo OUT y agrupaciones, como antes.
# Arrastrar en el tablero (contexto koroshi_tablero): pieza -> operario = se le da; cola -> otro operario = se
# cambia; cola -> «Por repartir» = Quitar. Lo que se está haciendo no se arrastra.
# Solo tablas propias: ningún campo en stock.*.
# =============================================================================
import logging
import re

import psycopg2

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import html2plaintext
from odoo.addons.koroshi_base import comun

from .reparto import VIVAS

_logger = logging.getLogger(__name__)

# Copia de koroshi_preparacion/models/agrupacion.py (RE_CAJA_NOTA) y de koroshi_zonas/motor/evaluar.py
# (numero_pedido): operarios no puede importarlos (los dos dependen de operarios). Si se pasan a koroshi_base.comun,
# quitar esta copia.
RE_CAJA_NOTA = re.compile(r'\|\s*CAJA\s+(\d+)\b')     # 'Z-1911-D2 | CAJA 05 | K34 ...' ('CAJAS 3' no)
RE_ZONA = re.compile(r'^Z-\d{4}-(?:R\d+-)?(?:D|MU)\d+$')   # zonas de koroshi_zonas (no 'Z-2210-SALIO 22-10')
SIN_NUMERO = 10 ** 12
PIEZAS_LOTES = 80        # agrupaciones vivas que se miran para «Por repartir»
PIEZAS_OUT = 40          # OUT sueltas libres en «Por repartir» (las más antiguas)
GRUPO_TABLERO = 'koroshi_operarios.grupo_tablero'


def _numero_pedido(origin):
    """'S-6665004409' -> 6665004409 (como koroshi_zonas.motor.evaluar.numero_pedido). Sin número: al final."""
    num = ''
    for ch in origin or '':
        if ch.isdigit():
            num += ch
        elif num:
            break
    return int(num) if num else SIN_NUMERO


def _clave_orden(picking):
    """Orden de las OUT dentro de una zona: el número de CAJA de la nota COMO NÚMERO (con más de 99 OUT, '100' va
    después de '11'); sin CAJA, el número de pedido y después el nombre de la OUT."""
    nota = picking.note or ''
    if '<' in nota:
        nota = html2plaintext(nota)
    m = RE_CAJA_NOTA.search(nota)
    return (int(m.group(1)) if m else SIN_NUMERO, _numero_pedido(picking.origin), picking.name or '')


class KoroshiOperarioAsignacionTablero(models.Model):
    _inherit = 'koroshi.operario.asignacion'

    employee_id = fields.Many2one(group_expand='_expandir_operarios')
    tipo = fields.Selection(selection_add=[('lote', 'Zona o agrupación (OUT a OUT)'),
                                           ('nota', 'Nota del responsable')])
    estado = fields.Selection(selection_add=[('pieza', 'Por repartir')])
    origen = fields.Selection(selection_add=[('tablero', 'Tablero')])
    texto = fields.Char('Texto de la nota', help='Lo que lee el operario en la PDA (tarjetas de nota del tablero)')
    tarjeta_id = fields.Many2one('koroshi.operario.asignacion', 'Tarjeta del tablero', index=True,
                                 ondelete='set null',
                                 help='Tarjeta de zona o agrupación de la que salió esta OUT')
    # el kanban de Odoo 13 reordena con un campo que se llame «sequence»: es el mismo orden de la cola
    sequence = fields.Integer('Orden (tablero)', related='secuencia', readonly=False)
    prog_pct = fields.Integer('Progreso (%)', compute='_compute_tablero')
    prog_texto = fields.Char('Progreso', compute='_compute_tablero')
    tambien = fields.Char('También en ella', compute='_compute_tablero',
                          help='Otros operarios con esta zona o agrupación en su columna')

    # ------------------------------------------------------------------ lo de siempre, con los tipos nuevos
    @api.depends('tipo', 'picking_id', 'batch_id', 'texto')
    def _compute_name(self):
        for a in self:
            if a.tipo == 'nota':
                a.name = a.texto or _('Nota')
            elif a.tipo in ('agrupacion', 'lote'):
                a.name = a.batch_id.name
            else:
                a.name = a.picking_id.name

    def _pickings(self):
        self.ensure_one()
        if self.tipo == 'lote':
            return self.batch_id.sudo().picking_ids
        if self.tipo == 'nota':
            return self.env['stock.picking']
        return super()._pickings()

    def _terminada(self):
        """Una nota no se acaba sola (sin pedidos, la de siempre la daría por hecha): solo con «Hecho» en la PDA."""
        self.ensure_one()
        if self.tipo == 'nota':
            return False
        return super()._terminada()

    def json(self):
        res = super().json()
        res['texto'] = (self.texto or '') if self.tipo == 'nota' else ''
        return res

    def _imprimir_etiquetas(self, dia=None):
        """Las tarjetas de zona y de nota no llevan etiqueta (la zona tiene las suyas, ya impresas)."""
        return super(KoroshiOperarioAsignacionTablero,
                     self.filtered(lambda a: a.tipo in ('out', 'agrupacion')))._imprimir_etiquetas(dia)

    # ------------------------------------------------------------------ PDA: siguiente OUT de una zona
    @api.model
    def _libres_de_lote(self, lote, employee=None):
        """OUT de la agrupación que se pueden dar: de salida, preparadas, sin asignación viva y que este operario no
        haya dejado hoy. En el orden de koroshi_zonas. Vacío si alguien hace la agrupación entera (lo de siempre)."""
        Pick = self.env['stock.picking']
        if not lote:
            return Pick
        if self.sudo().search_count([('estado', 'in', VIVAS), ('tipo', '=', 'agrupacion'), ('batch_id', '=', lote.id)]):
            return Pick
        pickings = lote.sudo().picking_ids
        cogidas = self.sudo().search([('estado', 'in', VIVAS), ('tipo', '=', 'out'),
                                      ('picking_id', 'in', pickings.ids)]).mapped('picking_id')
        if employee:
            cogidas |= self._dejadas_hoy(employee).mapped('picking_id')
        libres = pickings.filtered(lambda p: p.state == 'assigned' and p.picking_type_code == 'outgoing'
                                   and p not in cogidas)
        return libres.sorted(key=_clave_orden)

    def _dar_de_lote(self, employee):
        """Tarjeta de zona: crea la asignación de la siguiente OUT libre para este operario (o vacío)."""
        self.ensure_one()
        for p in self._libres_de_lote(self.batch_id, employee):
            asig = self._crear_segura({
                'employee_id': employee.id, 'tipo': 'out', 'origen': 'tablero', 'estado': 'cola',
                'secuencia': self._primera_secuencia(employee), 'picking_id': p.id, 'batch_id': self.batch_id.id,
                'tarjeta_id': self.id, 'company_id': p.company_id.id or self.company_id.id,
            })
            if asig:
                return asig
        return self.browse()

    def _siguiente_de_tarjeta(self, employee):
        """Lo que da una tarjeta del tablero en siguiente(): (asignación a devolver, seguir con la siguiente).
        Nunca rompe la PDA: si algo falla, se salta la tarjeta (sigue en la cola) y se apunta en el log."""
        self.ensure_one()
        if self.tipo == 'nota':
            return self, False
        try:
            self.flush()   # lo pendiente de antes se guarda fuera del savepoint (si este se deshace, no se pierde)
            with self.env.cr.savepoint():
                out = self._dar_de_lote(employee)
        except Exception:
            _logger.exception('KOROSHI OPERARIOS tablero: no se ha podido dar una OUT de %s a %s',
                              self.name, employee.name)
            return self.browse(), True
        if out:
            return out, False
        # la zona ya no tiene OUT libres: la tarjeta se acaba (las OUT que hacen otros siguen siendo suyas)
        self.write({'estado': 'hecha', 'nota': _('Sin OUT libres')})
        return self.browse(), True

    def nota_hecha(self, employee):
        """La PDA pulsa «Hecho, siguiente» en una nota suya. Si mientras tanto el responsable se la ha quitado o
        pasado a otro, no da error: la PDA pasa a lo siguiente (si no, se quedaría con una nota que ya no es suya)."""
        for a in self.filtered(lambda x: x.tipo == 'nota' and x.employee_id == employee and x.estado == 'cola'):
            a.write({'estado': 'hecha'})
        return True

    # ------------------------------------------------------------------ tablero: columnas y piezas
    @api.model
    def _expandir_operarios(self, employees, domain, order):
        """En el tablero salen todos los operarios aunque no tengan nada: los de «Operarios de hoy» si los hay; si
        no, todos los activos con tarjeta. Fuera del tablero, lo de siempre."""
        if not self.env.context.get('koroshi_tablero'):
            return employees
        Emp = self.env['hr.employee'].sudo()
        dia = self.env['koroshi.operario.dia'].sudo().search(
            [('fecha', '=', comun.hoy_local()), ('company_id', '=', self.env.company.id)], limit=1)
        extra = dia.tramo_ids.mapped('employee_id') if dia and dia.tramo_ids else Emp.search(
            [('barcode', '!=', False), '|', ('company_id', '=', False), ('company_id', '=', self.env.company.id)])
        todos = (Emp.browse(employees.ids) | extra).sorted(lambda e: (e.name or '').lower())
        return self.env['hr.employee'].browse(todos.ids)

    @api.model
    def tablero_refrescar(self):
        """Recalcula «Por repartir». Lo llaman el menú del tablero y el botón «Actualizar» (también cada minuto)."""
        company = self.env.company
        Asig = self.sudo()
        cogidas = Asig.search([('estado', 'in', VIVAS), ('tipo', '=', 'out')]).mapped('picking_id')
        enteras = Asig.search([('estado', 'in', VIVAS), ('tipo', '=', 'agrupacion')]).mapped('batch_id')
        quiero = {('nota', 0): {'tipo': 'nota', 'secuencia': 1}}
        lotes = self.env['stock.picking.batch'].sudo().search(
            [('state', 'in', ('draft', 'in_progress')), ('company_id', '=', company.id), ('id', 'not in', enteras.ids)],
            order='id desc', limit=PIEZAS_LOTES)
        # primero las zonas (por nombre: Z-1911-D1, D2...), después las demás agrupaciones
        lotes = lotes.sorted(lambda b: (not RE_ZONA.match(b.name or ''), b.name or ''))
        sec = 10
        for b in lotes:
            if any(p.state == 'assigned' and p.picking_type_code == 'outgoing' and p not in cogidas
                   for p in b.picking_ids):
                quiero[('lote', b.id)] = {'tipo': 'lote', 'batch_id': b.id, 'secuencia': sec}
                sec += 1
        outs = self.env['stock.picking'].sudo().search(
            [('picking_type_code', '=', 'outgoing'), ('company_id', '=', company.id), ('state', '=', 'assigned'),
             ('batch_id', '=', False), ('id', 'not in', cogidas.ids)],
            order='scheduled_date asc, id asc', limit=PIEZAS_OUT)
        sec = 1000
        for p in outs:
            quiero[('out', p.id)] = {'tipo': 'out', 'picking_id': p.id, 'secuencia': sec}
            sec += 1
        tengo = set()
        for pz in Asig.search([('estado', '=', 'pieza'), ('company_id', '=', company.id)]):
            clave = (pz.tipo, pz.batch_id.id if pz.tipo == 'lote' else (pz.picking_id.id if pz.tipo == 'out' else 0))
            if clave in quiero and clave not in tengo:
                tengo.add(clave)
                if pz.secuencia != quiero[clave]['secuencia']:
                    pz.write({'secuencia': quiero[clave]['secuencia']})
            else:
                pz.unlink()
        for clave, vals in quiero.items():
            if clave not in tengo:
                Asig.create(dict(vals, estado='pieza', employee_id=False, origen='tablero', company_id=company.id))
        return True

    @api.model
    def action_abrir_tablero(self):
        self.tablero_refrescar()
        desde = comun.inicio_dia_utc(comun.hoy_local())
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tablero'),
            'res_model': self._name,
            'view_mode': 'kanban,form',
            'views': [(self.env.ref('koroshi_operarios.view_koroshi_tablero_kanban').id, 'kanban'),
                      (self.env.ref('koroshi_operarios.view_koroshi_tablero_form').id, 'form')],
            'domain': [('company_id', '=', self.env.company.id), '|',
                       ('estado', 'in', ('pieza', 'cola', 'curso')),
                       '&', '&', ('estado', '=', 'hecha'), ('tipo', 'in', ('lote', 'nota')),
                       ('write_date', '>=', fields.Datetime.to_string(desde))],
            'context': {'koroshi_tablero': True, 'group_by': ['employee_id']},
            'target': 'main',
        }

    @api.depends('tipo', 'estado', 'picking_id', 'batch_id')
    def _compute_tablero(self):
        Tarea = self.env['koroshi.operario.tarea'].sudo()
        # quién tiene cada zona en su columna (una búsqueda para todo el tablero)
        lotes = self.filtered(lambda a: a.tipo == 'lote').mapped('batch_id')
        con_lote = {}
        if lotes:
            for t in self.sudo().search([('tipo', '=', 'lote'), ('estado', '=', 'cola'), ('employee_id', '!=', False),
                                         ('batch_id', 'in', lotes.ids)]):
                con_lote.setdefault(t.batch_id.id, []).append((t.employee_id.id, t.employee_id.name or ''))
        for a in self:
            a.prog_pct, a.prog_texto, a.tambien = 0, '', ''
            if a.tipo == 'nota' or not (a.picking_id or a.batch_id):
                continue
            try:
                if a.tipo == 'lote':
                    outs = a.batch_id.sudo().picking_ids.filtered(lambda p: p.state != 'cancel')
                    hechas = len(outs.filtered(lambda p: p.state == 'done'))
                    libres = len(self._libres_de_lote(a.batch_id)) if a.estado in ('pieza', 'cola') else 0
                    a.prog_pct = int(round(100.0 * hechas / len(outs))) if outs else 0
                    a.prog_texto = _('%s de %s OUT validadas · %s libres') % (hechas, len(outs), libres)
                    a.tambien = ', '.join(sorted(n for i, n in con_lote.get(a.batch_id.id, [])
                                                 if i != a.employee_id.id))
                else:
                    pickings = a._pickings()
                    total = Tarea._uds_pedidas(pickings)
                    leidas = Tarea._uds_leidas(pickings)
                    if total:
                        a.prog_pct = int(round(100.0 * min(leidas, total) / total))
                        a.prog_texto = _('%s de %s uds') % (int(round(leidas)), int(round(total)))
            except Exception:   # el progreso es solo informativo: nunca rompe el tablero
                _logger.exception('KOROSHI OPERARIOS tablero: progreso de %s', a.id)

    # ------------------------------------------------------------------ tablero: arrastrar
    def write(self, vals):
        if self.env.context.get('koroshi_tablero') and 'employee_id' in vals:
            return self._mover_en_tablero(vals)
        return super().write(vals)

    def _mover_en_tablero(self, vals):
        if not self.env.user.has_group(GRUPO_TABLERO):
            raise UserError(_('Solo el responsable (grupo «KOROSHI: Tablero del responsable») reparte el trabajo.'))
        nuevo = vals.get('employee_id') or False
        resto = {k: v for k, v in vals.items() if k != 'employee_id'}
        for a in self:
            if (a.employee_id.id or False) == nuevo:
                if resto:
                    super(KoroshiOperarioAsignacionTablero, a).write(resto)
                continue
            if a.estado == 'pieza':
                if nuevo:
                    a._dar_pieza(nuevo, resto)
                continue
            if a.estado == 'curso':
                raise UserError(_('%s la está haciendo %s. Para quitársela, ábrela y pulsa «Quitar».')
                                % (a.name, a.employee_id.name))
            if a.estado != 'cola':
                raise UserError(_('%s ya no está en la cola: no se puede mover.') % a.name)
            if not nuevo:
                a.sudo().action_quitar()   # vuelve a «Por repartir»: sale de la cola (sudo: cierra su tarea)
                continue
            emp = self.env['hr.employee'].browse(nuevo)
            super(KoroshiOperarioAsignacionTablero, a).write(
                dict(resto, employee_id=nuevo, secuencia=a._ultima_secuencia(emp)))
        return True

    def action_quitar_tablero(self):
        """Botón «Quitar» de la tarjeta del tablero. Si se está haciendo, la tarea se cierra como dejada (como
        «Quitar» en Colas). Con sudo porque el responsable no tiene por qué ver las tareas (productividad)."""
        if not self.env.user.has_group(GRUPO_TABLERO):
            raise UserError(_('Solo el responsable (grupo «KOROSHI: Tablero del responsable») reparte el trabajo.'))
        self.sudo().action_quitar()
        return {'type': 'ir.actions.act_window_close'}

    def action_subir_tablero(self):
        if not self.env.user.has_group(GRUPO_TABLERO):
            raise UserError(_('Solo el responsable (grupo «KOROSHI: Tablero del responsable») reparte el trabajo.'))
        self.sudo().action_subir()
        return {'type': 'ir.actions.act_window_close'}

    def _dar_pieza(self, emp_id, resto):
        """Pieza de «Por repartir» -> cola del operario. Una OUT suelta sale de «Por repartir»; una zona,
        agrupación o nota se queda también allí (se puede dar a varios)."""
        self.ensure_one()
        emp = self.env['hr.employee'].browse(emp_id)
        vals = dict(resto, employee_id=emp_id, estado='cola', origen='tablero',
                    secuencia=self._ultima_secuencia(emp))
        if self.tipo == 'out':
            if self._viva_de(picking=self.picking_id):
                raise UserError(_('%s ya lo tiene otro operario. Pulsa «Actualizar».') % self.name)
            # Odoo 13 deja el UPDATE para el final: flush dentro del savepoint para que el índice único salte aquí
            self.flush()
            try:
                with self.env.cr.savepoint():
                    super(KoroshiOperarioAsignacionTablero, self).write(vals)
                    self.flush()
            except psycopg2.IntegrityError:
                self.invalidate_cache()
                raise UserError(_('%s ya lo tiene otro operario. Pulsa «Actualizar».') % self.name)
            return
        self.sudo().create({'tipo': self.tipo, 'batch_id': self.batch_id.id or False, 'estado': 'pieza',
                            'employee_id': False, 'origen': 'tablero', 'company_id': self.company_id.id,
                            'secuencia': self.secuencia})
        super(KoroshiOperarioAsignacionTablero, self).write(vals)
