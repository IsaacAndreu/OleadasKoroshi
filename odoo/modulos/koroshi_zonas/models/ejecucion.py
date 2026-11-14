# -*- coding: utf-8 -*-
# =============================================================================
# Una ejecucion = un lanzamiento del reparto por zonas (un prefijo de agrupaciones Z-ddmm- o Z-ddmm-R2-).
# Fase 1: MEDIR. Las agrupaciones Z- que ya hay (las hace la accion 1883) se registran como
# ejecuciones de modo 'historico' y se miden sus cajas reales.
# Fase 2: LANZAR el reparto de la v12f (motor/v12f.py) en DIAGNOSTICO, SIMULAR o REAL. Un solo codigo;
# el modo es un campo. SIMULAR y REAL parten dentro de un savepoint: SIMULAR siempre lo deshace y REAL
# lo deshace si falla una comprobacion (todo o nada). La ejecucion queda guardada siempre, con los
# parametros, el contexto, los datos de entrada y el informe.
# =============================================================================
import base64
import datetime
import json
import logging

import pytz

from odoo import api, fields, models

from ..motor import medir as motor_medir
from ..motor import modelo
from ..motor import v12f
from . import escritor
from . import lector

CLAVES_CONTEXTO = ('personas', 'hora_inicio', 'hora_fin', 'una_ronda', 'zonas', 'zonas_muelle', 'prueba_ids',
                   'prueba_agrupacion')


class _Deshacer(Exception):
    """Para salir del savepoint deshaciendo lo escrito (SIMULAR o comprobaciones que fallan)."""

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

    name = fields.Char('Nombre', readonly=True)   # v1.1.1: se escribe en create/write (antes calculado)
    fecha = fields.Date('Día', required=True, index=True)
    prefijo = fields.Char('Prefijo de agrupaciones', required=True, index=True, help='Z-ddmm- o Z-ddmm-R2-')
    modo = fields.Selection([('historico', 'Histórico (hecha por la acción 1883)'),
                             ('diagnostico', 'Diagnóstico'), ('simular', 'Simular'), ('real', 'Real')],
                            'Modo', required=True, default='historico')
    company_id = fields.Many2one('res.company', 'Compañía', required=True, default=COMPANY_ID)
    out_ids = fields.One2many('koroshi.zonas.ejecucion.out', 'ejecucion_id', 'OUT')

    # Lanzamiento (fase 2)
    estado = fields.Selection([('historico', 'Histórico'), ('diagnostico', 'Diagnóstico (no escribe)'),
                               ('vacio', 'No entra ninguna OUT'), ('pocas_uds', 'Pocas uds: no se parte'),
                               ('simulado', 'Simulado (deshecho)'), ('fallos', 'Fallos: deshecho'),
                               ('error', 'Error: deshecho'), ('hecho', 'Hecho')],
                              'Resultado', default='historico', readonly=True)
    lanzado_el = fields.Datetime('Lanzado el', readonly=True)
    motor = fields.Char('Motor', readonly=True, help='Versión del cálculo: v12f = la de la acción 1883')
    contexto = fields.Text('Contexto', readonly=True, help='personas, horas, zonas, prueba_ids... con los que se lanzó')
    parametros = fields.Text('Parámetros del reparto', readonly=True)
    informe = fields.Text('Informe del reparto', readonly=True)
    datos_entrada = fields.Binary('Datos de entrada', attachment=True, readonly=True,
                                  help='JSON con las OUT y líneas que recibió el motor: reproduce el reparto sin Odoo')
    datos_entrada_nombre = fields.Char('Nombre del fichero de entrada', readonly=True)
    n_out_nuevas = fields.Integer('OUT nuevas', readonly=True)
    reparto_lineas = fields.Text('Zona de cada línea', readonly=True,
                                 help='JSON {id de stock.move.line: zona} del reparto calculado')

    # Fase 3: modo sombra (el cron calcula antes que el cron 202 y despues compara)
    sombra = fields.Boolean('Sombra', readonly=True, help='Cálculo del cron en modo sombra: no parte nada')
    comparacion = fields.Selection([('igual', 'Igual que el cron 202'), ('distinta', 'Distinta del cron 202'),
                                    ('sin_202', 'El cron 202 no ha partido')], 'Comparación', readonly=True)
    informe_comparacion = fields.Text('Informe de la comparación', readonly=True)

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

    def _nombre(self, prefijo, modo):
        etiqueta = dict(self._fields['modo'].selection)
        return '%s (%s)' % ((prefijo or '').rstrip('-'), etiqueta.get(modo, ''))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self._nombre(vals.get('prefijo'), vals.get('modo') or 'historico')
        return super(KoroshiZonasEjecucion, self).create(vals_list)

    def write(self, vals):
        res = super(KoroshiZonasEjecucion, self).write(vals)
        if 'prefijo' in vals or 'modo' in vals:
            for r in self:
                super(KoroshiZonasEjecucion, r).write({'name': self._nombre(r.prefijo, r.modo)})
        if 'fecha' in vals:     # la fecha de las filas sigue a la de la ejecucion
            self.mapped('out_ids').write({'fecha': vals['fecha']})
        return res

    @api.model
    def _rellenar_campos(self):
        """v1.1.1: rellena lo que la v1.1.0 dejo vacio (nombre de la ejecucion; dia, compania, diferencia y
        causa de las filas). Se llama al actualizar el modulo (data/rellenar.xml); no hace nada si ya esta.
        v1.1.2: borra las filas que la v1.1.0/v1.1.1 crearon con una agrupacion de almacen como zona ('SALE',
        'SALIO'...) y vuelve a registrar el historico: esas OUT van al dia y zona de su nota. Despues hay que
        volver a medir (menu Medir desde el 22/10). Solo toca las tablas del modulo."""
        Fila = self.env['koroshi.zonas.ejecucion.out'].sudo()
        malas = Fila.search([('ejecucion_id.modo', '=', 'historico')]).filtered(
            lambda f: not lector.partir_nombre_lote('Z-0000-' + (f.zona or '')))
        if malas:
            _logger.info('KOROSHI Zonas: se borran %d filas con zona de almacen y se vuelve a registrar', len(malas))
            malas.unlink()
            self.registrar_rango(HISTORICO_DESDE, self._hoy())
        for ej in self.sudo().search([]):
            nombre = self._nombre(ej.prefijo, ej.modo)
            if ej.name != nombre:
                super(KoroshiZonasEjecucion, ej).write({'name': nombre})
            filas = ej.out_ids.filtered(lambda f: f.fecha != ej.fecha or f.company_id != ej.company_id)
            if filas:
                filas.write({'fecha': ej.fecha, 'company_id': ej.company_id.id})
            ej.out_ids.filtered(lambda f: not f.causa)._escribir_causa()
        return True

    # ------------------------------------------------------------------ parametros
    def _medidas(self):
        return self.env['koroshi.zonas.config'].obtener().medidas()     # fase 3: el litros_caja de la config

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
        # v1.1.2: almacen agrupa a mano OUT de zonas (de ese dia y de dias antes) en agrupaciones que tambien
        # empiezan por Z- ('Z-2210-SALIO 22-10', 'Z-2710- SALE 28-10') para imprimir lo del transportista.
        # Esas no son zonas: cada OUT suya va al dia y la zona que dice SU nota ('Z-2210-D3 | CAJA ...').
        # Si la nota ya no lo dice, no se sabe de que zona era y no se cuenta (sale en el log).
        # Desde que el cron registra cada hora, cada OUT queda registrada con su zona el mismo dia.
        ini, fin = self._rango_utc(desde, hasta)
        Batch = self.env['stock.picking.batch'].sudo()
        lotes = Batch.search([('company_id', '=', COMPANY_ID), ('name', '=like', 'Z-%'),
                              ('create_date', '>=', ini), ('create_date', '<', fin)], order='create_date, id')
        por_prefijo = {}        # prefijo -> [(OUT, zona, agrupacion de zona o vacia)]
        fecha_de = {}           # prefijo -> dia (hora de Espana) de su primera agrupacion de zona
        tz = pytz.timezone(TZ)
        sin_zona = []
        for lote in lotes:
            partes = lector.partir_nombre_lote(lote.name)
            if partes:
                if partes[0] not in fecha_de:
                    fecha_de[partes[0]] = pytz.utc.localize(lote.create_date).astimezone(tz).date()
                for p in lote.picking_ids:
                    por_prefijo.setdefault(partes[0], []).append((p, partes[1], lote))
                continue
            for p in lote.picking_ids:              # agrupacion de almacen: la zona de la nota
                de_nota = lector.zona_de_nota(p.note)
                if de_nota:
                    por_prefijo.setdefault(de_nota[0], []).append((p, de_nota[1], Batch))
                elif p.picking_type_code == 'outgoing' and p.state != 'cancel':
                    sin_zona.append(p.name)
        if sin_zona:
            _logger.info('KOROSHI Zonas: %d OUT en agrupaciones de almacen sin zona en la nota: %s',
                         len(sin_zona), ', '.join(sin_zona[:50]))
        ejecuciones = self.browse()
        for prefijo, lista in por_prefijo.items():
            ej = self.search([('prefijo', '=', prefijo), ('company_id', '=', COMPANY_ID),
                              ('estado', 'in', ('historico', 'hecho'))], limit=1)
            if not ej:
                ej = self.create({'prefijo': prefijo, 'fecha': fecha_de.get(prefijo) or self._fecha_prefijo(prefijo),
                                  'modo': 'historico'})
            ej._registrar_outs(lista)
            ejecuciones |= ej
        return ejecuciones

    @api.model
    def _fecha_prefijo(self, prefijo):
        """Dia de un prefijo que solo se conoce por la nota: su primera agrupacion de zona y, si ya no hay,
        el ddmm del nombre con el ano de hoy."""
        tz = pytz.timezone(TZ)
        for lote in self.env['stock.picking.batch'].sudo().search(
                [('company_id', '=', COMPANY_ID), ('name', '=like', prefijo + '%')], order='create_date, id'):
            if lector.partir_nombre_lote(lote.name):
                return pytz.utc.localize(lote.create_date).astimezone(tz).date()
        hoy = self._hoy()
        return datetime.date(hoy.year, int(prefijo[4:6]), int(prefijo[2:4]))

    def _registrar_outs(self, lista):
        """lista: [(OUT, zona, agrupacion)]. Una fila por OUT; si ya estaba, solo completa la prevision."""
        self.ensure_one()
        Fila = self.env['koroshi.zonas.ejecucion.out'].sudo()
        ya = {}
        for f in self.out_ids:
            ya[f.picking_id.id] = f
        for p, zona, lote in lista:
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
                'lote_id': lote.id or False,
                'zona': zona,
                'pedido': p.origin or '',
                'tienda': p.partner_id.name or '',
                'cajas_previstas': previstas or 0,
                'prevision_conocida': previstas is not None,
            })

    # ------------------------------------------------------------------ medir
    def action_medir(self):
        # Cada ejecucion en su savepoint: si una falla no queda a medias y las demas se miden igual.
        # Solo se miden las que han partido OUT de verdad (historico y REAL hecho).
        for ej in self.filtered(lambda e: e.modo == 'historico' or (e.modo == 'real' and e.estado == 'hecho')):
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

    # ------------------------------------------------------------------ lanzar el reparto (fase 2)
    @api.model
    def probar(self, modo, contexto=None):
        """Fase 3: lanza el reparto y lo DESHACE todo (la ejecucion tambien) y no publica nada en el canal.
        Para probar sin dejar rastro. Devuelve {'informe', 'estado', 'prefijo', 'zona_fin'}."""
        res = {}
        try:
            with self.env.cr.savepoint():
                ej = self.with_context(koroshi_sin_publicar=True).lanzar(modo, contexto)
                res = {'informe': ej.informe, 'estado': ej.estado, 'prefijo': ej.prefijo,
                       'zona_fin': ej.reparto_lineas and json.loads(ej.reparto_lineas) or {}}
                self.env['base'].flush()
                raise _Deshacer()
        except _Deshacer:
            pass
        self.env.cache.invalidate()
        return res

    @api.model
    def lanzar(self, modo, contexto=None, sombra=False, como_1883=False):
        """Reparto de la v12f. modo: 'DIAGNOSTICO', 'SIMULAR' o 'REAL'. contexto: personas, hora_inicio,
        hora_fin, una_ronda, zonas, zonas_muelle, prueba_ids, prueba_agrupacion (como la accion 1883;
        con prueba_ids o prueba_agrupacion siempre es DIAGNOSTICO). Fase 3: los parametros salen de
        koroshi.zonas.config (el contexto manda sobre ellos). Devuelve la ejecucion.
        v1.3.0: como_1883 = sin lo nuevo de la 1.3.0 (modelo.COMO_1883), para comparar con el cron 202."""
        modo = (modo or '').upper()
        if modo not in ('DIAGNOSTICO', 'SIMULAR', 'REAL'):
            raise ValueError('Modo desconocido: %s' % modo)
        contexto = dict((k, v) for k, v in (contexto or {}).items() if k in CLAVES_CONTEXTO)
        cambios = self.env['koroshi.zonas.config'].obtener().cambios_motor()
        cambios['MODO'] = modo
        if como_1883:
            cambios.update(modelo.COMO_1883)
        p = modelo.parametros(cambios, contexto)
        ahora = datetime.datetime.now(pytz.timezone(p['ZONA_HORARIA']))
        datos = lector.datos_reparto(self.env, contexto, ahora, p)
        datos['contexto'] = contexto
        rep = v12f.repartir(datos, cambios, contexto)
        ej = self.create({
            'modo': rep.modo.lower(),
            'fecha': ahora.date(),
            'prefijo': rep.prefijo,
            'motor': 'v12f',
            'lanzado_el': fields.Datetime.now(),
            'contexto': json.dumps(contexto, sort_keys=True),
            'parametros': json.dumps(rep.parametros, sort_keys=True, default=list),
            'datos_entrada': base64.b64encode(json.dumps(datos).encode('utf-8')),
            'datos_entrada_nombre': 'koroshi_zonas_%s_%s.json' % (ahora.strftime('%Y%m%d_%H%M'), rep.modo.lower()),
            'reparto_lineas': json.dumps(dict((str(k), v) for k, v in rep.zona_fin.items()), sort_keys=True),
            'sombra': sombra,
        })
        lineas = list(rep.lineas)
        out_de = None
        n_nuevas = 0
        if rep.estado != 'listo':
            estado = rep.estado
        elif rep.modo == 'DIAGNOSTICO':
            estado = 'diagnostico'
        else:
            estado = 'error'
            fallos = []
            try:
                with self.env.cr.savepoint():
                    extra, fallos, todas_out, out_de = escritor.aplicar(self.env, rep)
                    lineas += extra
                    n_nuevas = len(todas_out) - len(rep.plan)
                    self.env['base'].flush()
                    if fallos:
                        lineas.insert(0, 'NO SE HA HECHO NADA (se ha deshecho todo)')
                        raise _Deshacer()
                    if rep.modo != 'REAL':
                        lineas.append('')
                        lineas.append('SIMULACION: se ha deshecho todo. Para hacerlo de verdad: modo REAL.')
                        raise _Deshacer()
                    lineas[0] = 'KOROSHI PARTIR OUT ZONAS v12 CAJA CERRADA - HECHO'
                    estado = 'hecho'
            except _Deshacer:
                estado = fallos and 'fallos' or 'simulado'
            except Exception as e:
                _logger.exception('KOROSHI Zonas: error al partir (%s)', rep.modo)
                lineas.insert(0, 'NO SE HA HECHO NADA (error: %s; se ha deshecho todo)' % e)
            if estado != 'hecho':
                out_de = None
                n_nuevas = 0
                self.env.cache.invalidate()
        ej._filas_plan(rep, out_de)
        ej.write({'informe': '\n'.join(lineas), 'estado': estado, 'n_out_nuevas': n_nuevas})
        _logger.info('\n'.join(lineas))
        ej._publicar()
        return ej

    def _filas_plan(self, rep, out_de):
        """Una fila por OUT y zona del plan. Sin partir (DIAGNOSTICO, SIMULAR, deshecho): la OUT original.
        Hecho: la OUT que ha quedado en cada zona, con su agrupacion."""
        self.ensure_one()
        Fila = self.env['koroshi.zonas.ejecucion.out'].sudo()
        for pid, por_z, principal, sin_res, caja in rep.plan:
            out = rep.calc.out_rec[pid]
            for zn in rep.orden_zonas:
                if zn not in por_z:
                    continue
                pick = out_de and out_de.get((pid, zn)) or None
                Fila.create({
                    'ejecucion_id': self.id,
                    'picking_id': pick and pick.id or pid,
                    'lote_id': pick and pick.batch_id.id or False,
                    'zona': zn,
                    'pedido': out['origin'] or '',
                    'tienda': out['partner_name'] or '',
                    'cajas_previstas': por_z[zn][0],
                    'prevision_conocida': True,
                })

    def _publicar(self, texto=None):
        """Publica el informe en el canal de la configuracion (el de la 1881), si existe. Si falla, sigue.
        Con el contexto koroshi_sin_publicar (probar) no publica nada."""
        if self.env.context.get('koroshi_sin_publicar'):
            return
        try:
            nombre = self.env['koroshi.zonas.config'].obtener().canal
            canal = nombre and self.env['mail.channel'].sudo().search([('name', '=', nombre)], limit=1)
            if canal:
                cuerpo = (texto or self.informe or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                canal.message_post(body='<pre style="font-size:12px">' + cuerpo + '</pre>', message_type='comment',
                                   subtype='mail.mt_comment')
        except Exception as e:
            _logger.warning('KOROSHI Zonas: no se ha podido publicar el informe en el canal: %s', e)

    def accion_abrir(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'koroshi.zonas.ejecucion',
            'view_mode': 'form',
            'res_id': self.id,
        }

    @api.model
    def accion_lanzar_hoy(self, modo):
        return self.lanzar(modo, self.env.context).accion_abrir()

    @api.model
    def accion_diagnostico_ids(self, ids):
        return self.lanzar('DIAGNOSTICO', dict(self.env.context, prueba_ids=ids)).accion_abrir()

    @api.model
    def accion_probar_ids(self, ids):
        """Diagnostico sin rastro de las OUT seleccionadas: lo enseña y no guarda ni publica nada."""
        from odoo.exceptions import UserError
        res = self.probar('DIAGNOSTICO', dict(self.env.context, prueba_ids=ids))
        raise UserError(res.get('informe') or 'Sin informe')

    # ------------------------------------------------------------------ cron del reparto (fase 3)
    @api.model
    def cron_partir(self):
        """Cron 'KOROSHI Zonas: partir OUT'. Modo sombra: DIAGNOSTICO que se guarda para compararlo despues
        con lo que haga el cron 202. Modo real: parte (el cron 202 tiene que estar desactivado)."""
        cfg = self.env['koroshi.zonas.config'].obtener()
        if cfg.modo_cron == 'real':
            cron202 = self.env['ir.cron'].sudo().search([('id', '=', 202), ('active', '=', True)])
            if cron202:
                texto = ('KOROSHI ZONAS: NO SE HA PARTIDO NADA. El cron 202 (accion 1883) sigue activo y el modulo '
                         'esta en modo real: partirian los dos. Desactiva el cron 202 o vuelve al modo sombra.')
                _logger.error(texto)
                self.browse()._publicar(texto)
                return False
            return self.lanzar('REAL')
        # v1.3.0: la sombra que se compara con el 202 se calcula como la 1883 (si no, nunca saldria igual). Despues,
        # un diagnostico con lo nuevo (OUT de dias anteriores, orden por urgencia, aviso de hora de fin) para ver
        # que cambiaria al pasar a real. No se compara.
        ej = self.lanzar('DIAGNOSTICO', sombra=True, como_1883=True)
        try:
            with self.env.cr.savepoint():
                self.lanzar('DIAGNOSTICO')
        except Exception:
            _logger.exception('KOROSHI Zonas: diagnostico con lo nuevo de la 1.3.0')
        return ej

    @api.model
    def cron_comparar(self):
        """Modo sombra, despues del cron 202: compara el calculo del modulo de hoy con lo que ha partido el 202."""
        from ..motor import comparar as motor_comparar
        hoy = self._hoy()
        for ej in self.search([('sombra', '=', True), ('fecha', '=', hoy), ('comparacion', '=', False)]):
            modulo = dict((int(k), v) for k, v in json.loads(ej.reparto_lineas or '{}').items())
            lotes = self.env['stock.picking.batch'].sudo().search([
                ('company_id', '=', COMPANY_ID), ('name', '=like', 'Z-%s-%%' % hoy.strftime('%d%m')),
                ('create_date', '>', ej.lanzado_el)])
            real = {}
            prefijos = []
            for lote in lotes:
                partes = lector.partir_nombre_lote(lote.name)
                if not partes:
                    continue
                if partes[0] not in prefijos:
                    prefijos.append(partes[0])
                for ml in lote.picking_ids.mapped('move_line_ids'):
                    if ml.product_uom_qty > 0 or ml.qty_done > 0:     # las mismas que reparte el motor
                        real[ml.id] = partes[1]
            if not real:
                ej.write({'comparacion': 'sin_202',
                          'informe_comparacion': 'El cron 202 no ha creado agrupaciones de zona despues del calculo '
                                                 'del modulo (%s).' % ej.lanzado_el})
                continue
            res = motor_comparar.comparar(modulo, real)
            texto = motor_comparar.texto(res, ej.prefijo, prefijos)
            ej.write({'comparacion': motor_comparar.es_igual(res) and 'igual' or 'distinta',
                      'informe_comparacion': texto})
            ej._publicar(texto)
        return True
