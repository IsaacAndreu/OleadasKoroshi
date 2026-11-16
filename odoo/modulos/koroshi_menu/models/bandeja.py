# -*- coding: utf-8 -*-
# =============================================================================
# v2.4 (16/11/2026, auditoría 13/11, fase 7, ideas 2 y 3): Bandeja del encargado.
#
# Una pantalla con todo lo que alguien tiene que mirar, en vez de buscarlo en cinco sitios. Dos pestañas:
#   - Pendiente: Lecturas paradas, faltantes, lecturas rechazadas de cola, pedidos sin OUT, reparto de zonas con
#     aviso, jobs fallidos, envíos S4T rechazados, traspasos S4T con error, tramos de actividad por revisar.
#   - Integraciones: crons KOROSHI y S4T (si van con retraso), cola root.s4t_sync, OUT de XPO sin etiqueta y el
#     resumen de la última pasada del sync de pedidos S4T.
# Cada línea: semáforo, qué es, cuántas, detalle y «Abrir» (lleva a la lista donde se resuelve).
#
# Solo LEE (con sudo). Las tablas son transitorias y propias (koroshi.bandeja y koroshi.bandeja.linea): se calculan
# al abrir y Odoo las borra solo. Cada fuente se mira solo si su módulo está instalado ('modelo' in env), así que no
# añade dependencias. Si una fuente falla, sale su línea en gris con el error y el resto sigue.
# =============================================================================
import datetime
import json
import logging

from odoo import api, fields, models
from odoo.addons.koroshi_base import comun

_logger = logging.getLogger(__name__)

P = 'koroshi_menu.'
MINUTOS_SIN_LECTURAS = 30       # Lecturas: sin ninguna lectura de la PDA en estos minutos de horario = rojo
DIAS_SIN_OUT = 7                # pedidos sin OUT: los creados estos días
MINUTOS_CRON_AMBAR = 15         # un cron que debía haber pasado hace más de esto: ámbar
MINUTOS_CRON_ROJO = 60          # y más de esto: rojo
MINUTOS_COLA_AMBAR = 30         # un job pendiente más viejo que esto: ámbar
ORDEN = {'rojo': 0, 'ambar': 1, 'gris': 2, 'verde': 3}


def _hm(dt):
    loc = comun.a_local(dt)
    return loc and loc.strftime('%d/%m %H:%M') or ''


def _minutos(desde, hasta):
    return int((hasta - desde).total_seconds() // 60)


def _minutos_en_horario(tramos, desde, hasta):
    """Minutos de [desde, hasta) (minutos desde las 00:00) que caen dentro de los tramos de horario."""
    return sum(max(0, min(hasta, b) - max(desde, a)) for a, b in tramos)


class KoroshiBandejaLinea(models.TransientModel):
    _name = 'koroshi.bandeja.linea'
    _description = 'KOROSHI: línea de la bandeja del encargado'
    _order = 'orden, secuencia'

    bandeja_id = fields.Many2one('koroshi.bandeja', ondelete='cascade')
    pestana = fields.Selection([('pendiente', 'Pendiente'), ('integraciones', 'Integraciones')], 'Pestaña')
    secuencia = fields.Integer()
    orden = fields.Integer()
    semaforo = fields.Selection([('rojo', 'Rojo'), ('ambar', 'Ámbar'), ('verde', 'Verde'), ('gris', 'Sin datos')],
                                'Estado')
    marca = fields.Char(' ')
    que = fields.Char('Qué')
    cuantos = fields.Integer('Cuántos')
    detalle = fields.Char('Detalle')
    accion = fields.Text('Acción')       # JSON: {'xmlid': ...} o {'res_model', 'domain', 'name'}

    def action_abrir(self):
        self.ensure_one()
        a = json.loads(self.accion or '{}')
        if not a:
            return False
        if a.get('xmlid'):
            res = self.env.ref(a['xmlid']).read()[0]
            if a.get('domain') is not None:
                res['domain'] = a['domain']
            return res
        return {
            'type': 'ir.actions.act_window',
            'name': a.get('name') or self.que,
            'res_model': a['res_model'],
            'view_mode': 'tree,form',
            'views': [(False, 'tree'), (False, 'form')],
            'domain': a.get('domain') or [],
            'context': {'create': False},
            'target': 'current',
        }


class KoroshiBandeja(models.TransientModel):
    _name = 'koroshi.bandeja'
    _description = 'KOROSHI: bandeja del encargado'

    generado = fields.Datetime('Calculado el', readonly=True)
    resumen = fields.Char('Resumen', readonly=True)
    pendiente_ids = fields.One2many('koroshi.bandeja.linea', 'bandeja_id', 'Pendiente',
                                    domain=[('pestana', '=', 'pendiente')], readonly=True)
    integracion_ids = fields.One2many('koroshi.bandeja.linea', 'bandeja_id', 'Integraciones',
                                      domain=[('pestana', '=', 'integraciones')], readonly=True)

    # ------------------------------------------------------------------ abrir
    @api.model
    def action_abrir_bandeja(self):
        """Menú «Bandeja del encargado» y botón «Actualizar»: calcula y abre la bandeja."""
        bandeja = self.create({})
        bandeja._calcular()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bandeja del encargado',
            'res_model': 'koroshi.bandeja',
            'res_id': bandeja.id,
            'view_mode': 'form',
            'views': [(self.env.ref('koroshi_menu.view_koroshi_bandeja_form').id, 'form')],
            'target': 'current',
            'flags': {'mode': 'readonly'},
        }

    def action_actualizar(self):
        return self.action_abrir_bandeja()

    # ------------------------------------------------------------------ cálculo
    def _param_int(self, clave, defecto):
        try:
            return int(self.env['ir.config_parameter'].sudo().get_param(P + clave, defecto))
        except (TypeError, ValueError):
            return defecto

    def _calcular(self):
        self.ensure_one()
        ahora = fields.Datetime.now()
        lineas = []
        fuentes = [
            ('pendiente', self._lecturas_paradas), ('pendiente', self._faltantes), ('pendiente', self._rechazadas),
            ('pendiente', self._pedidos_sin_out), ('pendiente', self._zonas), ('pendiente', self._jobs_fallidos),
            ('pendiente', self._s4t_envios), ('pendiente', self._s4t_traspasos), ('pendiente', self._actividades),
            ('integraciones', self._sync_s4t), ('integraciones', self._cola_s4t), ('integraciones', self._xpo),
            ('integraciones', self._crons),
        ]
        for pestana, fuente in fuentes:
            try:
                with self.env.cr.savepoint():
                    res = fuente(ahora) or []
            except Exception as e:   # una fuente rota no tumba la bandeja: sale en gris con el error
                _logger.exception('KOROSHI Bandeja: %s', fuente.__name__)
                res = [{'semaforo': 'gris', 'que': fuente.__name__.strip('_').replace('_', ' ').capitalize(),
                        'detalle': 'No se ha podido leer: %s' % (str(e)[:150])}]
            for r in res:
                r['pestana'] = pestana
                lineas.append(r)
        Linea = self.env['koroshi.bandeja.linea']
        for i, r in enumerate(lineas):
            sem = r.get('semaforo') or 'gris'
            Linea.create({
                'bandeja_id': self.id, 'pestana': r['pestana'], 'secuencia': i, 'orden': ORDEN.get(sem, 9),
                'semaforo': sem, 'marca': {'rojo': '●', 'ambar': '●', 'verde': '✓', 'gris': '–'}.get(sem, ''),
                'que': r.get('que'), 'cuantos': r.get('cuantos') or 0, 'detalle': (r.get('detalle') or '')[:250],
                'accion': json.dumps(r['accion']) if r.get('accion') else False,
            })
        rojos = len([r for r in lineas if r.get('semaforo') == 'rojo'])
        ambar = len([r for r in lineas if r.get('semaforo') == 'ambar'])
        self.write({'generado': ahora,
                    'resumen': '%d en rojo, %d en ámbar' % (rojos, ambar) if (rojos or ambar) else 'Todo en verde'})

    @staticmethod
    def _contar(n, que, detalle='', accion=None, rojo=True):
        return {'semaforo': n and (rojo and 'rojo' or 'ambar') or 'verde', 'que': que, 'cuantos': n,
                'detalle': detalle if n else '', 'accion': accion if n else None}

    # ------------------------------------------------------------------ Pendiente
    def _lecturas_paradas(self, ahora):
        """Nadie guarda lecturas en Preparación en horario de trabajo, con operarios trabajando hoy. El 13-16/11 la
        PDA no guardaba nada (columna sin crear) y no lo vio nadie: las lecturas fallaban antes de apuntarse."""
        env = self.env
        if 'koroshi.preparacion.lectura' not in env:
            return []
        L = env['koroshi.preparacion.lectura'].sudo()
        que = 'Lecturas de la PDA'
        activa = env['ir.config_parameter'].sudo().get_param('koroshi_preparacion.activa', '1')
        if activa in ('0', 'False', 'false', ''):
            return [{'semaforo': 'gris', 'que': que, 'detalle': 'Preparación en Lecturas apagada'}]
        umbral = self._param_int('minutos_sin_lecturas', MINUTOS_SIN_LECTURAS)
        loc = comun.a_local(ahora)
        minuto = loc.hour * 60 + loc.minute
        tramo = [t for t in L.horario_alarma() if t[0] <= minuto < t[1]] if hasattr(L, 'horario_alarma') else []
        ultima = L.search([], order='id desc', limit=1)
        texto = ultima and 'Última lectura: %s' % _hm(ultima.create_date) or 'Ninguna lectura todavía'
        hoy_ini = comun.inicio_dia_utc(comun.hoy_local())
        trabajando = 'koroshi.operario.tarea' in env and \
            env['koroshi.operario.tarea'].sudo().search_count([('inicio', '>=', hoy_ini)])
        if not tramo or not trabajando:
            return [{'semaforo': 'verde', 'que': que, 'detalle': texto + (
                ' (fuera de horario)' if not tramo else ' (hoy nadie ha abierto Lecturas)')}]
        # minutos DE HORARIO (sin pausas ni comida) desde la ultima lectura, o desde el inicio del dia si es de antes
        desde = comun.a_local(ultima.create_date) if ultima else None
        desde_min = desde.hour * 60 + desde.minute if desde and desde.date() == loc.date() else 0
        sin = _minutos_en_horario(L.horario_alarma(), desde_min, minuto)
        if sin < umbral:
            return [{'semaforo': 'verde', 'que': que, 'detalle': texto}]
        return [{'semaforo': 'rojo', 'que': que, 'cuantos': sin,
                 'detalle': '%d min de horario sin ninguna lectura guardada con %d operarios hoy en Lecturas. %s. '
                            'Mirar si la PDA da error al guardar.' % (sin, trabajando, texto),
                 'accion': {'res_model': 'koroshi.preparacion.lectura', 'domain': [], 'name': 'Lecturas'}}]

    def _faltantes(self, ahora):
        if 'koroshi.faltante' not in self.env:
            return []
        F = self.env['koroshi.faltante'].sudo()
        dom = [('estado', '=', 'pendiente')]
        n = F.search_count(dom)
        viejo = F.search(dom, order='fecha asc', limit=1)
        return [self._contar(n, 'Faltantes pendientes', viejo and 'El más antiguo: %s' % _hm(viejo.fecha) or '',
                             {'xmlid': 'koroshi_faltantes.action_koroshi_faltante_revision', 'domain': dom},
                             rojo=False)]

    def _rechazadas(self, ahora):
        L = 'koroshi.preparacion.lectura' in self.env and self.env['koroshi.preparacion.lectura'].sudo()
        if not L or 'diferida' not in L._fields:
            return []
        dom = [('diferida', '=', True), ('resultado', '=', 'error')]
        n = L.search_count(dom)
        viejo = L.search(dom, order='id asc', limit=1)
        return [self._contar(n, 'Lecturas rechazadas de cola de la PDA',
                             viejo and 'La más antigua: %s' % _hm(viejo.create_date) or '',
                             {'xmlid': 'koroshi_preparacion.action_koroshi_preparacion_rechazadas_cola'})]

    def _pedidos_sin_out(self, ahora):
        """Pedidos confirmados de la empresa sin ninguna entrega: posible OUT borrada (K72 el 13/11)."""
        dom = [('company_id', '=', comun.COMPANY_ID), ('state', '=', 'sale'), ('picking_ids', '=', False),
               ('create_date', '>=', ahora - datetime.timedelta(days=DIAS_SIN_OUT)),
               ('create_date', '<', ahora - datetime.timedelta(minutes=30))]
        pedidos = self.env['sale.order'].sudo().search(dom, order='create_date asc')
        return [self._contar(len(pedidos), 'Pedidos sin OUT (¿OUT borrada?)',
                             ', '.join(pedidos[:6].mapped('name')) + (len(pedidos) > 6 and '…' or ''),
                             {'res_model': 'sale.order', 'domain': [('id', 'in', pedidos.ids)],
                              'name': 'Pedidos sin OUT'})]

    def _zonas(self, ahora):
        if 'koroshi.zonas.ejecucion' not in self.env:
            return []
        E = self.env['koroshi.zonas.ejecucion'].sudo()
        hoy_ini = comun.inicio_dia_utc(comun.hoy_local())
        dom = [('lanzado_el', '>=', hoy_ini), '|', '|', ('estado', 'in', ('error', 'fallos')),
               ('informe', 'ilike', 'AVISO:'), ('informe', 'ilike', 'NO SE HA PARTIDO')]
        ejecs = E.search(dom)
        return [self._contar(len(ejecs), 'Reparto de zonas de hoy con aviso', ', '.join(ejecs.mapped('name')),
                             {'res_model': 'koroshi.zonas.ejecucion', 'domain': [('id', 'in', ejecs.ids)],
                              'name': 'Reparto de zonas con aviso'}, rojo=False)]

    def _jobs_fallidos(self, ahora):
        if 'queue.job' not in self.env:
            return []
        J = self.env['queue.job'].sudo()
        dom = [('state', '=', 'failed')]
        n = J.search_count(dom)
        viejo = J.search(dom, order='date_created asc', limit=1)
        return [self._contar(n, 'Jobs fallidos (queue_job)', viejo and 'El más antiguo: %s (%s)' % (
            _hm(viejo.date_created), viejo.channel or '') or '', {'res_model': 'queue.job', 'domain': dom,
                                                                  'name': 'Jobs fallidos'})]

    def _s4t_envios(self, ahora):
        if 'koroshi.s4t.envio' not in self.env:
            return []
        dom = [('state', '=', 'rechazado')]
        n = self.env['koroshi.s4t.envio'].sudo().search_count(dom)
        return [self._contar(n, 'Envíos rechazados por S4T', '', {'res_model': 'koroshi.s4t.envio', 'domain': dom,
                                                                   'name': 'Envíos rechazados por S4T'})]

    def _s4t_traspasos(self, ahora):
        if 'koroshi.s4t.traspaso' not in self.env:
            return []
        dom = [('state', '=', 'error')]
        n = self.env['koroshi.s4t.traspaso'].sudo().search_count(dom)
        return [self._contar(n, 'Traspasos S4T con error', '', {'res_model': 'koroshi.s4t.traspaso', 'domain': dom,
                                                                 'name': 'Traspasos S4T con error'})]

    def _actividades(self, ahora):
        if 'koroshi.actividad.registro' not in self.env:
            return []
        dom = [('nota', 'ilike', 'revisar'), ('create_date', '>=', ahora - datetime.timedelta(days=7))]
        n = self.env['koroshi.actividad.registro'].sudo().search_count(dom)
        return [self._contar(n, 'Tramos de actividad por revisar', 'Olvidados abiertos (últimos 7 días)',
                             {'res_model': 'koroshi.actividad.registro', 'domain': dom,
                              'name': 'Tramos por revisar'}, rojo=False)]

    # ------------------------------------------------------------------ Integraciones
    def _sync_s4t(self, ahora):
        """Resumen de la última pasada del sync de pedidos S4T (cron 186): lo deja en ir.logging con func = nombre."""
        cron = self.env['ir.cron'].sudo().with_context(active_test=False).search(
            [('name', 'ilike', 'S4T - Sync pedidos')], limit=1)
        if not cron:
            return []
        log = self.env['ir.logging'].sudo().search([('func', '=', cron.name), ('message', 'like', 'SYNC S4T: %candidatos%')],
                                                   order='id desc', limit=1)
        texto = log and (log.message or '').split('\n')[0][:200] or 'Sin resumen en el registro'
        sem = 'verde'
        if not cron.active:
            sem = 'gris'
        elif log and _minutos(log.create_date, ahora) > MINUTOS_CRON_ROJO:
            sem = 'ambar'
        return [{'semaforo': sem, 'que': 'Sync de pedidos S4T: última pasada', 'detalle': '%s · %s' % (
            log and _hm(log.create_date) or '-', texto)}]   # sin «Abrir»: el registro es de Ajustes > Técnico

    def _cola_s4t(self, ahora):
        if 'queue.job' not in self.env:
            return []
        J = self.env['queue.job'].sudo()
        canal = [('channel', '=', 'root.s4t_sync')]
        pend = J.search(canal + [('state', 'in', ('pending', 'enqueued', 'started'))], order='date_created asc')
        fallidos = J.search_count(canal + [('state', '=', 'failed')])
        viejo = pend[:1]
        espera = viejo and _minutos(viejo.date_created, ahora) or 0
        sem = fallidos and 'rojo' or (espera > MINUTOS_COLA_AMBAR and 'ambar') or 'verde'
        return [{'semaforo': sem, 'que': 'Cola S4T (root.s4t_sync)', 'cuantos': len(pend) + fallidos,
                 'detalle': '%d en espera%s, %d fallidos' % (len(pend), viejo and ' (el más viejo, %d min)' % espera
                                                             or '', fallidos),
                 'accion': {'res_model': 'queue.job', 'domain': canal + [('state', '!=', 'done')],
                            'name': 'Cola S4T'}}]

    def _xpo(self, ahora):
        hoy_ini = comun.inicio_dia_utc(comun.hoy_local())
        dom = [('company_id', '=', comun.COMPANY_ID), ('picking_type_code', '=', 'outgoing'), ('state', '=', 'done'),
               ('date_done', '>=', hoy_ini), ('carrier_id.delivery_type', 'like', 'xpo'),
               ('carrier_tracking_ref', '=', False)]
        outs = self.env['stock.picking'].sudo().search(dom)
        return [self._contar(len(outs), 'OUT de XPO validadas hoy sin etiqueta', ', '.join(outs[:6].mapped('name')),
                             {'res_model': 'stock.picking', 'domain': [('id', 'in', outs.ids)],
                              'name': 'OUT de XPO sin etiqueta'})]

    def _crons(self, ahora):
        """Crons KOROSHI y S4T activos: si debían haber pasado y no han pasado (Odoo parado, cron atascado)."""
        crons = self.env['ir.cron'].sudo().search(['|', ('name', 'ilike', 'KOROSHI'), ('name', 'ilike', 'S4T')],
                                                  order='name')
        res = []
        for c in crons:
            retraso = _minutos(c.nextcall, ahora)
            sem = retraso > MINUTOS_CRON_ROJO and 'rojo' or retraso > MINUTOS_CRON_AMBAR and 'ambar' or 'verde'
            res.append({'semaforo': sem, 'que': 'Cron: %s' % c.name, 'cuantos': max(retraso, 0) if sem != 'verde' else 0,
                        'detalle': 'Última: %s · siguiente: %s%s' % (
                            _hm(c.lastcall) or '-', _hm(c.nextcall),
                            sem != 'verde' and ' · %d min de retraso' % retraso or '')})   # sin «Abrir»: es de Técnico
        return res
