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
# v1.7.0 (20/11, Isaac: cierre por turno, no a las 17:00 para todos). hora_pausa y hora_cierre ya no se usan. El turno
#   sale de la hora de entrada (primer tramo o primera tarea de Lecturas del día; koroshi_base comun.turno_de):
#   6-14 o 8-13 y 14-17. Al final de cada tramo del turno (13:00 comida, 14:00 / 17:00 fin) se pregunta «¿Sigues?» a
#   quien no ha dado señal desde esa hora; sin respuesta en minutos_respuesta, se cierra A ESA HORA (comida = pausa
#   automática, fin = cierre automático). Si contesta después del fin, se le pregunta cada minutos_sigues. Sin turno
#   (entra después de las 11): el «¿Sigues?» de la 1.4. Tope para todo: hora_tope (22:00).
# v1.4.0 «¿Sigues?» (Isaac 19/11: se van a las 14:00 sin «Fin» y el tramo seguía abierto hasta las 17:00). Estas
#   actividades no leen nada, así que no se sabe si alguien sigue: se le pregunta. Desde sigues_desde (13:00), a quien
#   lleva minutos_sigues (30) sin dar señal (pasar la tarjeta, empezar, seguir o leer una matrícula) su fila del portátil
#   pide «¿Sigues? Pasa tu tarjeta». Si en minutos_respuesta (15) nadie la pasa, el cron cierra el tramo («No contestó
#   ¿Sigues?», queda en pausa): a las 13:00 si no dio señal desde entonces, si no a la hora en que se le preguntó.
# Solo escribe en esta tabla.
# =============================================================================
import datetime
import logging

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.addons.koroshi_base import comun   # v1.3: hora del almacen

_logger = logging.getLogger(__name__)

MOTIVOS = [
    ('cambio', 'Cambió de actividad'),
    ('pausa', 'Pausa'),
    ('pausa_auto', 'Pausa automática (comida)'),
    ('fin', 'Fin'),
    ('fin_auto', 'Cierre automático (fin de jornada)'),
    ('manual', 'A mano'),
    ('sin_respuesta', 'No contestó «¿Sigues?»'),      # v1.4.0
    ('sin_lecturas', 'Sin lecturas (Picking, Compactación)'),   # v1.8.0: lectura_manda.py
]
MOTIVOS_PAUSA = ('pausa', 'pausa_auto', 'sin_respuesta', 'sin_lecturas')
# v1.4.0: «¿Sigues?» (parámetros koroshi_actividades.sigues_desde / minutos_sigues / minutos_respuesta)
SIGUES_DESDE = '13:00'
MINUTOS_SIGUES = 30
MINUTOS_RESPUESTA = 15
HORA_TOPE = '22:00'     # v1.7.0: lo que nadie cierre, a esta hora
MOTIVOS_FIN = ('fin', 'fin_auto', 'manual')


def _tz():
    return comun.zona()


def a_local(dt):
    """datetime naive UTC (Odoo) -> datetime con zona de Madrid."""
    return comun.a_local(dt) or False


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
    # v1.4.0: última vez que se sabe que la persona estaba (tarjeta, matrícula). Vacío = el inicio del tramo.
    confirmado = fields.Datetime('Última señal', help='Última vez que pasó la tarjeta o leyó una matrícula con este '
                                                     'tramo abierto. Lo usa el «¿Sigues?».')
    # v1.6.0: área de la PDA (la de su actividad), para «Horas por área» y el tablero del responsable
    area = fields.Selection(related='actividad_id.area', string='Área', store=True, index=True, readonly=True)

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
        return comun.hoy_local()

    @api.model
    def abierto_de(self, employee):
        return self.search([('employee_id', '=', employee.id), ('estado', '=', 'curso')], order='inicio desc', limit=1)

    @api.model
    def _minutos_param(self, clave, defecto):
        try:
            return int(self._param(clave, str(defecto)) or 0)
        except ValueError:
            return defecto

    def _entrada(self):
        """v1.7.0: primera señal del día de la persona: su primer tramo de Actividades o su primera tarea de Lecturas."""
        self.ensure_one()
        desde, hasta = comun.rango_dia_utc(a_local(self.inicio).date())
        dom = [('employee_id', '=', self.employee_id.id), ('inicio', '>=', desde), ('inicio', '<', hasta)]
        primero = self.search(dom, order='inicio asc', limit=1).inicio or self.inicio
        if 'koroshi.operario.tarea' in self.env:
            t = self.env['koroshi.operario.tarea'].sudo().search(dom, order='inicio asc', limit=1).inicio
            if t and t < primero:
                primero = t
        return primero

    def _turno(self):
        """v1.7.0: turno de la persona ese día (comun.turno_de) o None (sin turno, o koroshi_base 1.0)."""
        self.ensure_one()
        if not hasattr(comun, 'turno_de'):
            return None
        return comun.turno_de(self._entrada(), comun.texto_turnos(self.env))

    def _sigues_turno(self, turno, ahora, cada, espera):
        """v1.7.0: «¿Sigues?» con turno. Al final de cada tramo del turno, a quien no dio señal desde entonces;
        después del fin del turno, cada `cada` min desde la última señal."""
        senal = max(self.confirmado or self.inicio, self.inicio)
        for _ini, corte in turno['tramos']:
            if self.inicio < corte <= ahora and senal < corte:
                final = corte == turno['fin']
                return {'pregunta': corte, 'cierre': corte, 'motivo': 'fin_auto' if final else 'pausa_auto',
                        'cerrar': ahora >= corte + datetime.timedelta(minutes=espera)}
        if cada > 0 and senal >= turno['fin']:
            pregunta = senal + datetime.timedelta(minutes=cada)
            if ahora >= pregunta:
                return {'pregunta': pregunta, 'cierre': pregunta, 'motivo': 'sin_respuesta',
                        'cerrar': ahora >= pregunta + datetime.timedelta(minutes=espera)}
        return None

    def _sigues(self, ahora=None):
        """v1.4.0: «¿Sigues?» de un tramo en curso. None si no toca preguntar todavía; si toca,
        {'pregunta': cuándo se le preguntó, 'cierre': a qué hora se cerraría, 'cerrar': ya pasó el tiempo de respuesta}
        (fechas naive UTC, como en Odoo)."""
        self.ensure_one()
        cada = self._minutos_param('minutos_sigues', MINUTOS_SIGUES)
        if self.estado != 'curso' or not self.inicio:
            return None
        turno = self._turno()     # v1.7.0
        if turno:
            return self._sigues_turno(turno, ahora or fields.Datetime.now(), cada,
                                      max(self._minutos_param('minutos_respuesta', MINUTOS_RESPUESTA), 0))
        if cada <= 0:
            return None
        desde_l = hora_del_dia(a_local(self.inicio).date(), self._param('sigues_desde', SIGUES_DESDE))
        if not desde_l:
            return None
        espera = max(self._minutos_param('minutos_respuesta', MINUTOS_RESPUESTA), 0)
        ahora = ahora or fields.Datetime.now()
        desde = a_utc(desde_l)
        senal = max(self.confirmado or self.inicio, self.inicio)
        pregunta = max(senal, desde) + datetime.timedelta(minutes=cada)
        if ahora < pregunta:
            return None
        return {'pregunta': pregunta, 'cierre': desde if senal <= desde else pregunta, 'motivo': 'sin_respuesta',
                'cerrar': ahora >= pregunta + datetime.timedelta(minutes=espera)}

    @api.model
    def confirmar(self, employee):
        """v1.4.0: la persona está (pasó la tarjeta o leyó una matrícula). Devuelve el tramo abierto si tenía
        pendiente el «¿Sigues?» (para darle las gracias), si no un registro vacío."""
        abierto = self.abierto_de(employee)
        if not abierto:
            return self.browse()
        pendiente = bool(abierto._sigues())
        abierto.write({'confirmado': fields.Datetime.now()})
        return abierto if pendiente else self.browse()

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
        sigues = ultimo._sigues(ahora) if situacion == 'trabajando' else None     # v1.4.0
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
            'sigues': bool(sigues),                                       # v1.4.0: hay que pasar la tarjeta
            'sigues_desde': fields.Datetime.to_string(sigues['pregunta']) if sigues else False,
            'sin_respuesta': ultimo.motivo_fin == 'sin_respuesta',
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
        registro = self._acabar(employee)
        self._tablero_fin(employee, registro.actividad_id)   # v1.5.0
        return registro

    def _tablero_fin(self, employee, actividad):
        """v1.5.0: «Fin» acaba la tarjeta de actividad del tablero (koroshi_operarios 2.20). Nunca impide el Fin: si
        falla, se apunta en el log y la tarjeta la quita el responsable."""
        Asig = self.env['koroshi.operario.asignacion'].sudo()
        if not hasattr(Asig, 'actividad_acabada'):
            return
        try:
            self.flush()
            with self.env.cr.savepoint():
                Asig.actividad_acabada(employee, actividad)
                Asig.flush()
        except Exception:
            _logger.exception('KOROSHI ACTIVIDADES: no se ha podido acabar la tarjeta del tablero de %s', employee.name)

    def _acabar(self, employee):
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
        """Pausa de la comida y cierre de la jornada a su hora exacta. También cierra lo que quedó de otros días.
        v1.4.0: y los tramos con el «¿Sigues?» sin contestar (ver _sigues).
        v1.7.0: la pausa y el cierre los pone el turno de cada uno (_sigues_turno); hora_tope cierra lo que quede."""
        # v1.7.0: sin hora_pausa ni hora_cierre: el turno de cada uno («¿Sigues?» al final de cada tramo) y un tope
        hora_tope = self._param('hora_tope', HORA_TOPE)
        ahora = comun.ahora_local()
        for r in self.search([('estado', '=', 'curso')]):
            inicio = a_local(r.inicio)
            dia = inicio.date()
            tope = hora_del_dia(dia, hora_tope)
            sigues = r._sigues()
            if sigues and sigues['cerrar'] and (not tope or sigues['cierre'] < a_utc(tope)):
                r._cerrar(sigues.get('motivo') or 'sin_respuesta', sigues['cierre'])
            elif tope and inicio < tope <= ahora:
                r._cerrar('fin_auto', a_utc(tope))
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
