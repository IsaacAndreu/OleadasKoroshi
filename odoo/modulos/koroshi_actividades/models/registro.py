# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Actividades - un registro = un tramo continuo de una persona en una actividad.
#
# Empezar           -> tramo nuevo «en curso» (si tenía otro abierto, se cierra: «cambió de actividad»)
# Pausar            -> se cierra el tramo (motivo «pausa»); la persona queda «en pausa»
# Seguir            -> tramo nuevo con la misma actividad
# Fin               -> se cierra el tramo (motivo «fin»); la persona queda «terminado»
# Cron cada 5 min   -> a la hora_pausa (13:00) los tramos abiertos se cierran a las 13:00 exactas («pausa 13:00»)
#                      a la hora_cierre (17:00) se cierran a las 17:00 exactas («cierre 17:00»)
#                      los de días anteriores se cierran a la hora_cierre de su día (o a medianoche)
# Como se cierra a la hora exacta, da igual que el cron pase unos minutos tarde.
# Solo escribe en esta tabla.
# =============================================================================
import datetime

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError

ZONA_HORARIA = 'Europe/Madrid'

MOTIVOS = [
    ('cambio', 'Cambió de actividad'),
    ('pausa', 'Pausa'),
    ('pausa_auto', 'Pausa automática (comida)'),
    ('fin', 'Fin'),
    ('fin_auto', 'Cierre automático (fin de jornada)'),
    ('manual', 'A mano'),
]
MOTIVOS_PAUSA = ('pausa', 'pausa_auto')
MOTIVOS_FIN = ('fin', 'fin_auto', 'manual')


def _tz():
    return pytz.timezone(ZONA_HORARIA)


def a_local(dt):
    """datetime naive UTC (Odoo) -> datetime con zona de Madrid."""
    return pytz.utc.localize(dt).astimezone(_tz()) if dt else False


def a_utc(dt_local):
    """datetime con zona -> naive UTC (Odoo)."""
    return dt_local.astimezone(pytz.utc).replace(tzinfo=None)


def hora_del_dia(dia, texto):
    """'13:00' + date -> datetime con zona de Madrid. '' o mal escrito -> None."""
    try:
        h, m = [int(x) for x in (texto or '').strip().split(':')]
        return _tz().localize(datetime.datetime.combine(dia, datetime.time(h, m)))
    except (ValueError, TypeError):
        return None


class KoroshiActividadRegistro(models.Model):
    _name = 'koroshi.actividad.registro'
    _description = 'KOROSHI Actividad: tramo de tiempo de una persona'
    _order = 'inicio desc, id desc'

    name = fields.Char('Tramo', compute='_compute_name', store=True)
    employee_id = fields.Many2one('hr.employee', 'Persona', required=True, index=True, ondelete='restrict')
    actividad_id = fields.Many2one('koroshi.actividad', 'Actividad', required=True, index=True, ondelete='restrict')
    company_id = fields.Many2one('res.company', 'Empresa', required=True, default=lambda self: self.env.company)
    inicio = fields.Datetime('Inicio', required=True, default=fields.Datetime.now, index=True)
    fin = fields.Datetime('Fin')
    dia = fields.Date('Día', compute='_compute_dia', store=True, index=True)
    estado = fields.Selection([('curso', 'En curso'), ('cerrado', 'Cerrado')], 'Estado', default='curso',
                              required=True, index=True)
    motivo_fin = fields.Selection(MOTIVOS, 'Cómo se cerró')
    minutos = fields.Float('Minutos', compute='_compute_tiempo', store=True, digits=(16, 1), group_operator='sum')
    horas = fields.Float('Horas', compute='_compute_tiempo', store=True, digits=(16, 2), group_operator='sum')
    nota = fields.Char('Nota')

    # ------------------------------------------------------------------ computes
    @api.depends('employee_id', 'actividad_id')
    def _compute_name(self):
        for r in self:
            r.name = '%s - %s' % (r.employee_id.name or '', r.actividad_id.name or '')

    @api.depends('inicio')
    def _compute_dia(self):
        for r in self:
            r.dia = a_local(r.inicio).date() if r.inicio else False

    @api.depends('inicio', 'fin')
    def _compute_tiempo(self):
        for r in self:
            if r.inicio and r.fin:
                r.minutos = max(0.0, (r.fin - r.inicio).total_seconds() / 60.0)
            else:
                r.minutos = 0.0
            r.horas = r.minutos / 60.0

    # ------------------------------------------------------------------ helpers
    @api.model
    def _param(self, clave, defecto):
        return self.env['ir.config_parameter'].sudo().get_param('koroshi_actividades.' + clave, defecto)

    @api.model
    def _hoy(self):
        return datetime.datetime.now(_tz()).date()

    @api.model
    def abierto_de(self, employee):
        return self.search([('employee_id', '=', employee.id), ('estado', '=', 'curso')], order='inicio desc', limit=1)

    def init(self):
        # v1.1.0 (auditoría 13/11, fase 2.8): un solo tramo abierto por persona, también con dos toques a la vez
        self.env.cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS koroshi_actividad_registro_uno_abierto
            ON koroshi_actividad_registro (employee_id) WHERE estado = 'curso'
        """)

    def _cerrar(self, motivo, fin=None):
        Caja = self.env['koroshi.inversa.caja']
        for r in self:
            fin_r = max(fin or fields.Datetime.now(), r.inicio)
            r.write({'estado': 'cerrado', 'motivo_fin': motivo, 'fin': fin_r})
            Caja.cerrar_por_tramo(r, motivo, fin_r)    # v1.1.0: la caja de inversa abierta se cierra a la vez

    @api.model
    def estado_de(self, employee):
        """Lo que la pantalla necesita saber de una persona hoy."""
        hoy = self._hoy()
        tramos = self.search([('employee_id', '=', employee.id), ('dia', '=', hoy)], order='inicio asc, id asc')
        ahora = fields.Datetime.now()
        minutos = sum(t.minutos if t.fin else (ahora - t.inicio).total_seconds() / 60.0 for t in tramos)
        ultimo = tramos[-1:] if tramos else self.browse()
        if not ultimo:
            situacion = 'sin_empezar'
        elif ultimo.estado == 'curso':
            situacion = 'trabajando'
        elif ultimo.motivo_fin in MOTIVOS_PAUSA:
            situacion = 'pausa'
        else:
            situacion = 'terminado'
        # v1.1.0: inversa (cajas de hoy; la caja abierta solo si está trabajando en una actividad que lee matrículas)
        pide = bool(situacion == 'trabajando' and ultimo.actividad_id.pide_matricula)
        Caja = self.env['koroshi.inversa.caja']
        inversa = Caja.resumen(employee) if (pide or Caja.search_count(
            [('employee_id', '=', employee.id), ('dia', '=', hoy)])) else False
        return {
            'pide_matricula': pide,
            'inversa': inversa,
            'employee_id': employee.id,
            'nombre': employee.name,
            'situacion': situacion,
            'actividad_id': ultimo.actividad_id.id or False,
            'actividad': ultimo.actividad_id.name or '',
            'color': ultimo.actividad_id.color or '',
            'desde': fields.Datetime.to_string(ultimo.inicio) if situacion == 'trabajando' else
            (fields.Datetime.to_string(ultimo.fin) if ultimo.fin else False),
            'pausa_auto': ultimo.motivo_fin == 'pausa_auto',
            'fin_auto': ultimo.motivo_fin == 'fin_auto',
            'entrada': fields.Datetime.to_string(tramos[0].inicio) if tramos else False,
            'minutos_hoy': round(minutos, 1),
        }

    # ------------------------------------------------------------------ acciones de la pantalla
    @api.model
    def empezar(self, employee, actividad):
        if not actividad.active:
            raise UserError(_('La actividad %s está archivada.') % actividad.name)
        abierto = self.abierto_de(employee)
        if abierto and abierto.actividad_id == actividad:
            return abierto    # ya está en esa actividad: no se parte el tramo
        abierto._cerrar('cambio')
        self.flush()    # el cierre va a la base antes de crear el nuevo (índice: un solo tramo abierto por persona)
        return self.create({'employee_id': employee.id, 'actividad_id': actividad.id,
                            'company_id': actividad.company_id.id or self.env.company.id})

    @api.model
    def pausar(self, employee):
        abierto = self.abierto_de(employee)
        if not abierto:
            raise UserError(_('%s no tiene nada empezado.') % employee.name)
        abierto._cerrar('pausa')
        return abierto

    @api.model
    def seguir(self, employee):
        """Vuelve a la última actividad de hoy (tras una pausa)."""
        if self.abierto_de(employee):
            raise UserError(_('%s ya está trabajando.') % employee.name)
        ultimo = self.search([('employee_id', '=', employee.id), ('dia', '=', self._hoy())],
                             order='inicio desc, id desc', limit=1)
        if not ultimo:
            raise UserError(_('Elige una actividad para empezar.'))
        return self.empezar(employee, ultimo.actividad_id)

    @api.model
    def acabar(self, employee):
        abierto = self.abierto_de(employee)
        if abierto:
            abierto._cerrar('fin')
            return abierto
        # en pausa: el fin se apunta en el último tramo para que la jornada salga «terminada»
        ultimo = self.search([('employee_id', '=', employee.id), ('dia', '=', self._hoy())],
                             order='inicio desc, id desc', limit=1)
        if not ultimo:
            raise UserError(_('%s no ha empezado hoy.') % employee.name)
        if ultimo.motivo_fin in MOTIVOS_PAUSA:
            ultimo.motivo_fin = 'fin'
        return ultimo

    # ------------------------------------------------------------------ cron
    @api.model
    def cron_cerrar(self):
        """Pausa de la comida y cierre de la jornada a su hora exacta. También cierra lo que quedó de otros días."""
        hora_pausa = self._param('hora_pausa', '13:00')
        hora_cierre = self._param('hora_cierre', '17:00')
        ahora = datetime.datetime.now(_tz())
        for r in self.search([('estado', '=', 'curso')]):
            inicio = a_local(r.inicio)
            dia = inicio.date()
            pausa = hora_del_dia(dia, hora_pausa)
            cierre = hora_del_dia(dia, hora_cierre)
            if pausa and inicio < pausa <= ahora:
                r._cerrar('pausa_auto', a_utc(pausa))
            elif cierre and inicio < cierre <= ahora:
                r._cerrar('fin_auto', a_utc(cierre))
            elif dia < ahora.date():
                # v1.1.0 (auditoría 13/11, fase 2.8): empezó después del cierre (o sin hora de cierre) y nadie lo
                # paró. Antes se cerraba a las 23:59 y sumaba horas que no se trabajaron: ahora cuenta 0 minutos y
                # queda marcado para corregirlo a mano en «Tramos de tiempo».
                r._cerrar('fin_auto', r.inicio)
                r.nota = _('Olvidado abierto: revisar la hora de fin a mano.')
        return True

    def action_cerrar_a_mano(self):
        self.filtered(lambda r: r.estado == 'curso')._cerrar('manual')
        return True
