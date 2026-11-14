# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Actividades v1.1.0 - inversa: una caja de tienda (matrícula) abierta por una persona.
#
# Mientras alguien está en una actividad con «Lee matrículas» (Inversa), cada vez que abre una caja lee su
# matrícula (CJ + 9 cifras). No cuenta ni lee uds: las uds salen del teórico de la matrícula.
#   leer matrícula  -> se cierra la caja que tenía abierta (motivo «siguiente») y empieza la nueva
#   pausa / cambio / fin del tramo (también las automáticas de 13:00 y 17:00) -> se cierra la caja abierta
#   anular          -> la última lectura no cuenta y vuelve a quedar abierta la caja de antes
# Tiempo de una caja = desde que se lee hasta la siguiente lectura (o la pausa / el fin).
#
# Teórico: s4t.matricula / s4t.matricula.line (módulo de Effective api_s4t_batch_update_PROD, importación del
# Excel «EAN | CAJA»). Se busca por nombre de matrícula y solo se LEE. Si el módulo no está o la matrícula aún no
# se ha importado, la caja queda «sin teórico» y un cron la completa cuando aparece (últimos 14 días).
# Solo escribe en esta tabla.
# =============================================================================
import collections
import datetime
import json
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .registro import _tz, a_local

RE_MATRICULA = re.compile(r'^CJ\d{9}$')
PREFIJO_NUESTRA = 'CJ665'           # nuestras cajas de salida (almacén 6665): no son matrículas de tienda
RE_SKU = re.compile(r'^\d{4}([A-Z]{2})\d{2}-')   # 2521JA10-000061-S -> JA
DIAS_TEORICO = 14

# tramo cerrado -> caja cerrada
MOTIVO_CAJA = {'cambio': 'cambio', 'pausa': 'pausa', 'pausa_auto': 'auto', 'fin': 'fin', 'fin_auto': 'auto',
               'manual': 'manual'}


class KoroshiInversaCaja(models.Model):
    _name = 'koroshi.inversa.caja'
    _description = 'KOROSHI Inversa: caja de tienda (matrícula) abierta por una persona'
    _order = 'inicio desc, id desc'

    name = fields.Char('Matrícula', required=True, index=True)
    employee_id = fields.Many2one('hr.employee', 'Persona', required=True, index=True, ondelete='restrict')
    actividad_id = fields.Many2one('koroshi.actividad', 'Actividad', ondelete='set null')
    registro_id = fields.Many2one('koroshi.actividad.registro', 'Tramo', index=True, ondelete='set null')
    company_id = fields.Many2one('res.company', 'Empresa', required=True, default=lambda self: self.env.company)
    inicio = fields.Datetime('Abierta', required=True, default=fields.Datetime.now, index=True)
    fin = fields.Datetime('Cerrada')
    dia = fields.Date('Día', compute='_compute_dia', store=True, index=True)
    estado = fields.Selection([('abierta', 'Abierta'), ('cerrada', 'Cerrada'), ('anulada', 'Anulada')], 'Estado',
                              default='abierta', required=True, index=True)
    motivo_fin = fields.Selection([
        ('siguiente', 'Leyó la siguiente'),
        ('pausa', 'Pausa'),
        ('cambio', 'Cambió de actividad'),
        ('fin', 'Fin'),
        ('auto', 'Cierre o pausa automática'),
        ('manual', 'A mano'),
        ('anulada', 'Anulada'),
    ], 'Cómo se cerró')
    minutos = fields.Float('Minutos', compute='_compute_minutos', store=True, digits=(16, 1), group_operator='sum')
    teorico = fields.Boolean('Con teórico', help='La matrícula está importada y se saben sus uds')
    uds = fields.Integer('Uds (teórico)', group_operator='sum')
    skus = fields.Integer('SKU (teórico)', group_operator='sum')
    familias = fields.Char('Familias', help='Uds de la caja por familia del código (JA, PT, TR...)')
    familias_json = fields.Text('Familias (datos)')
    repetida = fields.Boolean('Leída otra vez', help='La matrícula ya se había leído antes y se contó igualmente')

    def init(self):
        # una sola caja abierta por persona (dos lecturas a la vez no pueden dejar dos abiertas)
        self.env.cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS koroshi_inversa_caja_una_abierta
            ON koroshi_inversa_caja (employee_id) WHERE estado = 'abierta'
        """)

    # ------------------------------------------------------------------ computes
    @api.depends('inicio')
    def _compute_dia(self):
        for c in self:
            c.dia = a_local(c.inicio).date() if c.inicio else False

    @api.depends('inicio', 'fin', 'estado')
    def _compute_minutos(self):
        for c in self:
            if c.estado == 'cerrada' and c.inicio and c.fin:
                c.minutos = max(0.0, (c.fin - c.inicio).total_seconds() / 60.0)
            else:
                c.minutos = 0.0

    # ------------------------------------------------------------------ teórico
    @api.model
    def _teorico(self, matricula):
        """Uds, SKU y familias de la matrícula según s4t.matricula. {} si no está."""
        if 's4t.matricula' not in self.env:
            return {}
        mat = self.env['s4t.matricula'].sudo().search([('name', '=', matricula)], order='id desc', limit=1)
        if not mat:
            return {}
        por_familia = collections.Counter()
        for linea in mat.line_ids:
            sku = (linea.sku or linea.product_id.name or '').strip()
            m = RE_SKU.match(sku)
            por_familia[m.group(1) if m else '??'] += linea.quantity or 0
        lista = [{'fam': f, 'uds': int(u)} for f, u in por_familia.most_common()]
        return {
            'teorico': True,
            'uds': int(mat.total_units or sum(por_familia.values())),
            'skus': len(mat.line_ids),
            'familias': ' · '.join('%s %d' % (x['fam'], x['uds']) for x in lista),
            'familias_json': json.dumps(lista),
        }

    @api.model
    def cron_teorico(self):
        """Completa las cajas de los últimos días que se leyeron antes de importar su matrícula."""
        desde = datetime.datetime.now(_tz()).date() - datetime.timedelta(days=DIAS_TEORICO)
        for c in self.search([('teorico', '=', False), ('estado', '!=', 'anulada'), ('dia', '>=', desde)]):
            datos = self._teorico(c.name)
            if datos:
                c.write(datos)
        return True

    # ------------------------------------------------------------------ helpers
    @api.model
    def _destinos(self):
        """Parámetro koroshi_actividades.inversa_destinos: 'JA=JA, PT=PT, XC ZC=ACC, *=RESTO' -> dict."""
        texto = self.env['ir.config_parameter'].sudo().get_param('koroshi_actividades.inversa_destinos', '')
        res = {}
        for trozo in texto.split(','):
            if '=' not in trozo:
                continue
            fams, destino = trozo.split('=', 1)
            for f in fams.split():
                res[f.strip().upper()] = destino.strip()
        return res

    def _json(self, destinos=None):
        self.ensure_one()
        destinos = destinos if destinos is not None else self._destinos()
        try:
            fams = json.loads(self.familias_json or '[]')
        except ValueError:
            fams = []
        for f in fams:
            f['destino'] = destinos.get(f['fam'], destinos.get('*', ''))
        return {
            'id': self.id, 'matricula': self.name, 'estado': self.estado,
            'inicio': fields.Datetime.to_string(self.inicio),
            'fin': fields.Datetime.to_string(self.fin) if self.fin else False,
            'minutos': round(self.minutos, 1), 'teorico': self.teorico, 'uds': self.uds, 'skus': self.skus,
            'familias': fams, 'repetida': self.repetida,
        }

    @api.model
    def abierta_de(self, employee):
        return self.search([('employee_id', '=', employee.id), ('estado', '=', 'abierta')], limit=1)

    def _cerrar(self, motivo, fin=None):
        for c in self:
            c.write({'estado': 'cerrada', 'motivo_fin': motivo, 'fin': max(fin or fields.Datetime.now(), c.inicio)})

    @api.model
    def cerrar_por_tramo(self, registro, motivo_tramo, fin):
        """Lo llama koroshi.actividad.registro al cerrar un tramo (a mano o el cron de 13:00 / 17:00)."""
        cajas = self.search([('registro_id', '=', registro.id), ('estado', '=', 'abierta')])
        cajas._cerrar(MOTIVO_CAJA.get(motivo_tramo, 'manual'), fin)

    @api.model
    def resumen(self, employee):
        """Lo que enseña la pantalla: caja abierta, contadores de hoy y las últimas cajas."""
        hoy = datetime.datetime.now(_tz()).date()
        cajas = self.search([('employee_id', '=', employee.id), ('dia', '=', hoy), ('estado', '!=', 'anulada')],
                            order='inicio desc, id desc')
        cerradas = cajas.filtered(lambda c: c.estado == 'cerrada')
        destinos = self._destinos()
        abierta = cajas.filtered(lambda c: c.estado == 'abierta')[:1]
        return {
            'abierta': abierta._json(destinos) if abierta else False,
            'cajas': len(cajas),
            'uds': sum(cajas.mapped('uds')),
            'sin_teorico': len(cajas.filtered(lambda c: not c.teorico)),
            'min_media': round(sum(cerradas.mapped('minutos')) / len(cerradas), 1) if cerradas else 0,
            'ultimas': [c._json(destinos) for c in cajas.filtered(lambda c: c.estado == 'cerrada')[:4]],
        }

    # ------------------------------------------------------------------ acciones de la pantalla
    @api.model
    def leer(self, employee, codigo, forzar=False):
        """Lectura de una matrícula. Devuelve (caja, aviso) o lanza UserError.
        Si la matrícula ya se había leído y no se fuerza: devuelve (False, {datos de la repetida})."""
        codigo = (codigo or '').strip().upper()
        if not RE_MATRICULA.match(codigo):
            raise UserError(_('%s no es una matrícula (CJ + 9 cifras).') % codigo)
        if codigo.startswith(PREFIJO_NUESTRA):
            raise UserError(_('%s es una caja nuestra de salida (CJ665…), no una caja de tienda.') % codigo)
        Registro = self.env['koroshi.actividad.registro']
        tramo = Registro.abierto_de(employee)
        if not tramo or not tramo.actividad_id.pide_matricula:
            raise UserError(_('%s: primero toca «Inversa» para empezar.') % employee.name)
        abierta = self.abierta_de(employee)
        if abierta and abierta.name == codigo:
            return abierta, _('%s ya es tu caja abierta.') % codigo
        previa = self.search([('name', '=', codigo), ('estado', '!=', 'anulada')], order='inicio desc', limit=1)
        if previa and not forzar:
            return False, {'matricula': codigo, 'quien': previa.employee_id.name,
                           'cuando': fields.Datetime.to_string(previa.inicio)}
        ahora = fields.Datetime.now()
        abierta._cerrar('siguiente', ahora)
        self.flush()    # el cierre va a la base antes de crear la nueva (índice: una sola caja abierta)
        vals = {'name': codigo, 'employee_id': employee.id, 'actividad_id': tramo.actividad_id.id,
                'registro_id': tramo.id, 'company_id': tramo.company_id.id, 'inicio': ahora,
                'repetida': bool(previa)}
        vals.update(self._teorico(codigo))
        caja = self.create(vals)
        aviso = '' if caja.teorico else _('%s aún no tiene teórico: cuenta la caja; las uds se pondrán solas '
                                          'cuando se importe.') % codigo
        return caja, aviso

    @api.model
    def anular_ultima(self, employee):
        """La última lectura de hoy no cuenta; si cerró la caja de antes, esa vuelve a quedar abierta."""
        hoy = datetime.datetime.now(_tz()).date()
        ultima = self.search([('employee_id', '=', employee.id), ('dia', '=', hoy), ('estado', '!=', 'anulada')],
                             order='inicio desc, id desc', limit=1)
        if not ultima:
            raise UserError(_('No hay ninguna lectura que anular.'))
        estaba_abierta = ultima.estado == 'abierta'
        ultima.write({'estado': 'anulada', 'motivo_fin': 'anulada', 'fin': ultima.fin or fields.Datetime.now()})
        self.flush()
        if estaba_abierta:
            anterior = self.search([('employee_id', '=', employee.id), ('dia', '=', hoy), ('estado', '=', 'cerrada'),
                                    ('motivo_fin', '=', 'siguiente'), ('inicio', '<=', ultima.inicio)],
                                   order='inicio desc, id desc', limit=1)
            tramo = self.env['koroshi.actividad.registro'].abierto_de(employee)
            if anterior and tramo and tramo.actividad_id.pide_matricula:
                anterior.write({'estado': 'abierta', 'motivo_fin': False, 'fin': False, 'registro_id': tramo.id})
        return ultima

    def action_cerrar_a_mano(self):
        self.filtered(lambda c: c.estado == 'abierta')._cerrar('manual')
        return True
