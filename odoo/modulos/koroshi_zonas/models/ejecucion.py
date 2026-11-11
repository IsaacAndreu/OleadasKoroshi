# -*- coding: utf-8 -*-
# =============================================================================
# Una ejecucion = un lanzamiento del reparto por zonas (un prefijo de agrupaciones Z-ddmm- o Z-ddmm-R2-).
# Fase 1: solo MEDIR. Las agrupaciones Z- que ya hay (las hace la accion 1883) se registran como
# ejecuciones de modo 'historico' y se miden sus cajas reales. No escribe nada fuera de sus tablas.
# =============================================================================
import datetime
import json
import logging

import pytz

from odoo import api, fields, models

from ..motor import medir as motor_medir
from ..motor import volumen
from . import lector

_logger = logging.getLogger(__name__)

COMPANY_ID = lector.COMPANY_ID
TZ = 'Europe/Madrid'
HISTORICO_DESDE = datetime.date(2026, 10, 22)
DIAS_CRON = 7                   # el cron vuelve a medir los ultimos dias (OUT que se validan tarde)
PARAM_REGLA_DUENO = 'koroshi_zonas.regla_dueno'


class KoroshiZonasEjecucion(models.Model):
    _name = 'koroshi.zonas.ejecucion'
    _description = 'KOROSHI Zonas - ejecución del reparto por zonas'
    _order = 'fecha desc, prefijo desc'

    name = fields.Char('Nombre', compute='_compute_name', store=True)
    fecha = fields.Date('Día', required=True, index=True)
    prefijo = fields.Char('Prefijo de agrupaciones', required=True, index=True, help='Z-ddmm- o Z-ddmm-R2-')
    modo = fields.Selection([('historico', 'Histórico (hecha por la acción 1883)'),
                             ('diagnostico', 'Diagnóstico'), ('simular', 'Simular'), ('real', 'Real')],
                            'Modo', required=True, default='historico')
    company_id = fields.Many2one('res.company', 'Compañía', required=True, default=COMPANY_ID)
    out_ids = fields.One2many('koroshi.zonas.ejecucion.out', 'ejecucion_id', 'OUT')

    # Medicion (fase 1)
    medicion = fields.Selection([('sin_medir', 'Sin medir'), ('parcial', 'En parte (hay OUT sin validar)'),
                                 ('medida', 'Medida')], 'Medición', default='sin_medir', readonly=True)
    medido_el = fields.Datetime('Medido el', readonly=True)
    parametros_medicion = fields.Text('Parámetros de la medición', readonly=True)
    informe_medicion = fields.Text('Informe de la medición', readonly=True)
    n_out = fields.Integer('OUT', readonly=True)
    n_out_medidas = fields.Integer('OUT medidas', readonly=True)
    n_out_cerradas = fields.Integer('OUT en caja cerrada', readonly=True)
    cajas_previstas = fields.Integer('Cajas previstas', readonly=True, help='Solo de las OUT con previsión conocida')
    cajas_estimadas = fields.Integer('Cajas estimadas con lo cogido', readonly=True)
    cajas_reales = fields.Integer('Cajas reales', readonly=True)
    cajas_cerradas = fields.Integer('Cajas cerradas reales', readonly=True)
    cajas_compartidas = fields.Integer('Cajas compartidas', readonly=True)
    pct_cajas_cerradas = fields.Float('% cajas cerradas', readonly=True, digits=(16, 1), group_operator='avg')
    pct_outs_cerradas = fields.Float('% OUT en caja cerrada', readonly=True, digits=(16, 1), group_operator='avg')

    @api.depends('prefijo', 'modo')
    def _compute_name(self):
        etiqueta = dict(self._fields['modo'].selection)
        for r in self:
            r.name = '%s (%s)' % ((r.prefijo or '').rstrip('-'), etiqueta.get(r.modo, ''))

    # ------------------------------------------------------------------ parametros
    def _medidas(self):
        return volumen.Medidas()

    def _regla_dueno(self):
        regla = self.env['ir.config_parameter'].sudo().get_param(PARAM_REGLA_DUENO, 'primera_linea')
        return regla in motor_medir.REGLAS_DUENO and regla or 'primera_linea'

    # ------------------------------------------------------------------ registrar OUT
    @api.model
    def _rango_utc(self, desde, hasta):
        tz = pytz.timezone(TZ)
        ini = tz.localize(datetime.datetime.combine(desde, datetime.time.min)).astimezone(pytz.utc)
        fin = tz.localize(datetime.datetime.combine(hasta + datetime.timedelta(days=1),
                                                    datetime.time.min)).astimezone(pytz.utc)
        return ini.replace(tzinfo=None), fin.replace(tzinfo=None)

    @api.model
    def registrar_rango(self, desde, hasta):
        """Crea (o completa) las ejecuciones y sus filas de OUT de las agrupaciones Z- creadas entre
        esas fechas (hora de Espana). Lee la prevision (CAJAS n) de la nota: si ya estaba leida, no la pisa."""
        ini, fin = self._rango_utc(desde, hasta)
        lotes = self.env['stock.picking.batch'].sudo().search([
            ('company_id', '=', COMPANY_ID), ('name', '=like', 'Z-%'),
            ('create_date', '>=', ini), ('create_date', '<', fin)], order='create_date, id')
        por_prefijo = {}
        for lote in lotes:
            partes = lector.partir_nombre_lote(lote.name)
            if partes:
                por_prefijo.setdefault(partes[0], []).append((lote, partes[1]))
        tz = pytz.timezone(TZ)
        ejecuciones = self.browse()
        for prefijo, lista in por_prefijo.items():
            primero = lista[0][0]
            fecha = pytz.utc.localize(primero.create_date).astimezone(tz).date()
            ej = self.search([('prefijo', '=', prefijo), ('company_id', '=', COMPANY_ID),
                              ('modo', 'in', ('historico', 'real'))], limit=1)
            if not ej:
                ej = self.create({'prefijo': prefijo, 'fecha': fecha, 'modo': 'historico'})
            ej._registrar_outs(lista)
            ejecuciones |= ej
        return ejecuciones

    def _registrar_outs(self, lista):
        self.ensure_one()
        Fila = self.env['koroshi.zonas.ejecucion.out'].sudo()
        ya = {}
        for f in self.out_ids:
            ya[f.picking_id.id] = f
        for lote, zona in lista:
            for p in lote.picking_ids:
                if p.state == 'cancel' or p.picking_type_code != 'outgoing' or p.company_id.id != COMPANY_ID:
                    continue
                previstas = lector.cajas_de_nota(p.note)
                fila = ya.get(p.id)
                if fila:
                    if not fila.prevision_conocida and previstas is not None:
                        fila.write({'cajas_previstas': previstas, 'prevision_conocida': True})
                    continue
                ya[p.id] = Fila.create({
                    'ejecucion_id': self.id,
                    'picking_id': p.id,
                    'lote_id': lote.id,
                    'zona': zona,
                    'pedido': p.origin or '',
                    'tienda': p.partner_id.name or '',
                    'cajas_previstas': previstas or 0,
                    'prevision_conocida': previstas is not None,
                })

    # ------------------------------------------------------------------ medir
    def action_medir(self):
        # Cada ejecucion en su savepoint: si una falla no queda a medias y las demas se miden igual
        for ej in self:
            try:
                with self.env.cr.savepoint():
                    ej._medir()
            except Exception:
                _logger.exception('KOROSHI Zonas: no se ha podido medir %s', ej.prefijo)
                if len(self) == 1:
                    raise
        return True

    def _medir(self):
        self.ensure_one()
        medidas = self._medidas()
        regla = self._regla_dueno()
        filas = self.out_ids
        picks = filas.mapped('picking_id')
        lineas = lector.lineas_para_medir(self.env, picks, medidas)
        por_out, por_caja = motor_medir.medir(lineas, picks.ids, medidas, regla)
        hechas = set(picks.filtered(lambda p: p.state == 'done').ids)
        for f in filas:
            r = por_out.get(f.picking_id.id)
            f.write({
                'medida': f.picking_id.id in hechas,
                'uds': r['uds'],
                'litros': r['litros'],
                'cajas_estimadas': r['cajas_estimadas'],
                'cerrada_estimada': r['cerrada_estimada'],
                'cajas_reales': r['cajas_reales'],
                'cajas_cerradas': r['cajas_cerradas'],
                'cajas_compartidas': r['cajas_compartidas'],
                'cajas_ajenas': r['cajas_ajenas'],
                'uds_en_ajenas': r['uds_en_ajenas'],
                'uds_sin_caja': r['uds_sin_caja'],
                'cerrada': r['cerrada'],
            })
        medidas_out = {}
        previstas = {}
        zona_de = {}
        for f in filas:
            pid = f.picking_id.id
            zona_de[pid] = f.zona or ''
            if pid in hechas:
                medidas_out[pid] = por_out[pid]
                if f.prevision_conocida:
                    previstas[pid] = f.cajas_previstas
        tot = motor_medir.resumen(medidas_out, previstas)
        por_zona = {}
        for zona in sorted(set(zona_de.values())):
            sub = {}
            for pid in medidas_out:
                if zona_de[pid] == zona:
                    sub[pid] = medidas_out[pid]
            por_zona[zona] = motor_medir.resumen(sub, previstas)
        g = tot['grupos']
        self.write({
            'medicion': (not hechas and 'sin_medir') or (len(hechas) < len(picks) and 'parcial') or 'medida',
            'medido_el': fields.Datetime.now(),
            'parametros_medicion': json.dumps({'medidas': medidas.como_dict(), 'regla_dueno': regla},
                                              sort_keys=True),
            'informe_medicion': self._texto_informe(tot, por_zona, filas, regla, medidas),
            'n_out': len(picks),
            'n_out_medidas': tot['outs'],
            'n_out_cerradas': tot['outs_cerradas'],
            'cajas_previstas': g['limpias']['previstas'] + g['con_compartida']['previstas'],
            'cajas_estimadas': g['limpias']['estimadas'] + g['con_compartida']['estimadas'],
            'cajas_reales': tot['cajas_reales'],
            'cajas_cerradas': tot['cajas_cerradas'],
            'cajas_compartidas': tot['cajas_compartidas'],
            'pct_cajas_cerradas': tot['pct_cajas_cerradas'],
            'pct_outs_cerradas': tot['pct_outs_cerradas'],
        })

    def _texto_informe(self, tot, por_zona, filas, regla, medidas):
        lin = []
        lin.append('MEDICION %s - %s' % (self.prefijo, self.fecha and self.fecha.strftime('%d/%m/%Y') or ''))
        lin.append('Caja de %d L; cerrada si no es compartida y lleva al menos el %d%%. Dueno de caja compartida: %s.' % (
            medidas.litros_caja, round(medidas.cierre_min * 100), regla))
        lin.append('OUT medidas: %d | en caja cerrada: %d (%.1f%%) | cajas reales %d | cerradas %d (%.1f%%) | '
                   'compartidas %d' % (tot['outs'], tot['outs_cerradas'], tot['pct_outs_cerradas'],
                                       tot['cajas_reales'], tot['cajas_cerradas'], tot['pct_cajas_cerradas'],
                                       tot['cajas_compartidas']))
        lin.append('')
        lin.append('Por zona: OUT | cajas reales | cerradas | % | compartidas')
        for zona in sorted(por_zona):
            z = por_zona[zona]
            lin.append('   %-5s %4d OUT | %4d cajas | %4d cerradas | %5.1f%% | %d compartidas' % (
                zona, z['outs'], z['cajas_reales'], z['cajas_cerradas'], z['pct_cajas_cerradas'],
                z['cajas_compartidas']))
        lin.append('')
        lin.append('Previsto contra real (solo OUT con CAJAS n en la nota):')
        for clave, titulo in (('limpias', 'OUT limpias (error del modelo de litros y de lo cogido)'),
                              ('con_compartida', 'OUT con caja compartida (caja existente)')):
            g = tot['grupos'][clave]
            lin.append('   %s: %d OUT (%d con prevision) | previstas %d | estimadas con lo cogido %d | reales %d' % (
                titulo, g['outs'], g['outs_con_prevision'], g['previstas'], g['estimadas_con_prevision'],
                g['reales_con_prevision']))
        sin_prev = len(filas.filtered(lambda f: not f.prevision_conocida))
        if sin_prev:
            lin.append('   %d OUT sin CAJAS n en la nota (pisada por otro proceso)' % sin_prev)
        distintas = filas.filtered(lambda f: f.medida and f.prevision_conocida and f.diferencia)
        if distintas:
            lin.append('')
            lin.append('OUT con cajas reales distintas de las previstas (%d):' % len(distintas))
            for f in distintas.sorted(lambda x: (x.zona or '', x.picking_id.name))[:80]:
                lin.append('   %s | %s | %s | previstas %d, estimadas %d, reales %d | %s' % (
                    f.zona or '', f.picking_id.name, f.tienda or '', f.cajas_previstas, f.cajas_estimadas,
                    f.cajas_reales, dict(f._fields['causa'].selection).get(f.causa, '')))
            if len(distintas) > 80:
                lin.append('   ... y %d mas' % (len(distintas) - 80))
        return '\n'.join(lin)

    # ------------------------------------------------------------------ crons y acciones
    @api.model
    def _hoy(self):
        return datetime.datetime.now(pytz.timezone(TZ)).date()

    @api.model
    def cron_capturar(self):
        """Cada hora: registra las OUT de las agrupaciones Z- de hoy y lee el CAJAS n de su nota antes de
        que otro proceso la pise. No mide."""
        hoy = self._hoy()
        self.registrar_rango(hoy, hoy)
        return True

    @api.model
    def cron_medir(self):
        """Cada noche: registra y mide los ultimos DIAS_CRON dias."""
        hoy = self._hoy()
        self.registrar_rango(hoy - datetime.timedelta(days=DIAS_CRON), hoy).action_medir()
        return True

    @api.model
    def medir_historico(self):
        """Registra y mide todo desde HISTORICO_DESDE (22/10/2026). Se puede lanzar las veces que haga falta."""
        ejecuciones = self.registrar_rango(HISTORICO_DESDE, self._hoy())
        ejecuciones.action_medir()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ejecuciones medidas',
            'res_model': 'koroshi.zonas.ejecucion',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', ejecuciones.ids)],
        }
