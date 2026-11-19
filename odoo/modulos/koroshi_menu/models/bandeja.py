# -*- coding: utf-8 -*-
# =============================================================================
# v2.4 (16/11/2026, auditoría 13/11, fase 7, ideas 2 y 3): Bandeja del encargado.
#
# Una pantalla con todo lo que alguien tiene que mirar, en vez de buscarlo en cinco sitios. Dos pestañas:
#   - Pendiente: Lecturas paradas, faltantes, lecturas rechazadas de cola, pedidos sin OUT, reparto de zonas con
#     aviso, jobs fallidos, envíos S4T rechazados, traspasos S4T con error, tramos de actividad por revisar.
#   - Integraciones: crons KOROSHI y S4T (si van con retraso), cola root.s4t_sync, OUT de XPO sin etiqueta y el
#     resumen de la última pasada del sync de pedidos S4T.
# v2.6 (19/11/2026, Isaac): lo de arriba era de IT, no del jefe de almacén. Tres pestañas:
#   - Hoy (jefe): tiendas de hoy, camión XPO, leído sin caja, validado fuera de caja, operarios parados.
#   - Pendiente (jefe): faltantes, stock 0 con pedidos esperando, web (reservas y canceladas), S4T que afecta a
#     clientes (envíos y traspasos), OUT de XPO sin etiqueta, tramos de actividad por revisar.
#   - IT (solo administradores): Lecturas paradas, lecturas rechazadas de cola, pedidos sin OUT, reparto de zonas
#     con aviso, jobs fallidos, sync y cola S4T, crons.
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
# v2.6
TIPO_TIENDAS = 'PED. TIENDAS'   # sale.order.s_order_type_id.name de los pedidos de tienda (como monitor y zonas)
HORA_TIENDAS = '13:00'          # a esta hora las OUT de tienda con reserva deberían estar hechas (koroshi_menu.hora_tiendas)
HORA_CAMION = '15:00'           # a esta hora el camión XPO debería estar cerrado (koroshi_menu.hora_camion)
MINUTOS_SIN_CAJA = 60           # una lectura fuera de caja más vieja que esto, en una OUT sin validar: rojo


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
    pestana = fields.Selection([('hoy', 'Hoy'), ('pendiente', 'Pendiente'), ('it', 'IT')], 'Pestaña')
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
    resumen_it = fields.Char('Resumen IT', readonly=True)
    hoy_ids = fields.One2many('koroshi.bandeja.linea', 'bandeja_id', 'Hoy', domain=[('pestana', '=', 'hoy')],
                              readonly=True)
    pendiente_ids = fields.One2many('koroshi.bandeja.linea', 'bandeja_id', 'Pendiente',
                                    domain=[('pestana', '=', 'pendiente')], readonly=True)
    it_ids = fields.One2many('koroshi.bandeja.linea', 'bandeja_id', 'IT', domain=[('pestana', '=', 'it')],
                             readonly=True)

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
            ('hoy', self._tiendas_hoy), ('hoy', self._camion), ('hoy', self._leido_sin_caja),
            ('hoy', self._validado_sin_caja), ('hoy', self._operarios_parados),
            ('pendiente', self._faltantes), ('pendiente', self._stock_cero), ('pendiente', self._web),
            ('pendiente', self._s4t_envios), ('pendiente', self._s4t_traspasos), ('pendiente', self._xpo),
            ('pendiente', self._actividades),
            ('it', self._lecturas_paradas), ('it', self._rechazadas), ('it', self._pedidos_sin_out),
            ('it', self._zonas), ('it', self._jobs_fallidos), ('it', self._sync_s4t), ('it', self._cola_s4t),
            ('it', self._crons),
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
        self.write({'generado': ahora,
                    'resumen': self._texto_resumen([r for r in lineas if r['pestana'] != 'it']),
                    'resumen_it': self._texto_resumen([r for r in lineas if r['pestana'] == 'it'])})

    @staticmethod
    def _texto_resumen(lineas):
        rojos = len([r for r in lineas if r.get('semaforo') == 'rojo'])
        ambar = len([r for r in lineas if r.get('semaforo') == 'ambar'])
        return '%d en rojo, %d en ámbar' % (rojos, ambar) if (rojos or ambar) else 'Todo en verde'

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

    # ------------------------------------------------------------------ v2.6: Hoy (jefe de almacén)
    def _param_hora(self, clave, defecto):
        """'13:00' -> (minutos desde las 00:00, texto). Hora del almacén."""
        texto = self.env['ir.config_parameter'].sudo().get_param(P + clave, defecto) or defecto
        try:
            h, m = [int(x) for x in texto.strip().split(':')]
            return h * 60 + m, '%02d:%02d' % (h, m)
        except (ValueError, TypeError):
            h, m = [int(x) for x in defecto.split(':')]
            return h * 60 + m, defecto

    def _es_tarde(self, ahora, clave, defecto):
        limite, texto = self._param_hora(clave, defecto)
        loc = comun.a_local(ahora)
        return loc.hour * 60 + loc.minute >= limite, texto

    def _dom_tiendas(self):
        """OUT de pedidos de tienda (los mismos que monitor y zonas: tipo de pedido «PED. TIENDAS»)."""
        dom = [('company_id', '=', comun.COMPANY_ID), ('picking_type_code', '=', 'outgoing')]
        if 's_order_type_id' in self.env['sale.order']._fields:
            dom.append(('sale_id.s_order_type_id.name', '=', TIPO_TIENDAS))
        else:
            dom.append(('origin', 'not like', 'W-%'))
        return dom

    @staticmethod
    def _nombres(recs, n=6):
        return ', '.join(recs[:n].mapped('name')) + (len(recs) > n and '…' or '')

    def _tiendas_hoy(self, ahora):
        """OUT de tienda: cuántas quedan con reserva (por preparar), cuántas esperan stock y cuántas se validaron hoy."""
        Pk = self.env['stock.picking'].sudo()
        dom = self._dom_tiendas()
        hoy_ini = comun.inicio_dia_utc(comun.hoy_local())
        listas = Pk.search(dom + [('state', '=', 'assigned')], order='scheduled_date asc')
        sin_stock = Pk.search_count(dom + [('state', 'in', ('confirmed', 'waiting'))])
        hechas = Pk.search_count(dom + [('state', '=', 'done'), ('date_done', '>=', hoy_ini)])
        tarde, hora = self._es_tarde(ahora, 'hora_tiendas', HORA_TIENDAS)
        detalle = '%d por preparar (con reserva), %d esperando stock, %d validadas hoy.' % (
            len(listas), sin_stock, hechas)
        if listas and tarde:
            detalle += ' Son más de las %s.' % hora
        return [{'semaforo': listas and tarde and 'rojo' or 'verde', 'que': 'Tiendas: OUT por preparar',
                 'cuantos': len(listas), 'detalle': detalle,
                 'accion': listas and {'res_model': 'stock.picking', 'domain': [('id', 'in', listas.ids)],
                                       'name': 'OUT de tienda por preparar'} or None}]

    def _camion(self, ahora):
        """Camión XPO de hoy: cerrado y correo a XPO enviado (Monitor > Consulta de envíos > Cerrar camión)."""
        if 'koroshi.envio.cierre' not in self.env:
            return []
        que = 'Camión XPO de hoy'
        hoy = comun.hoy_local()
        cierre = self.env['koroshi.envio.cierre'].sudo().search(
            [('dia', '=', hoy), ('company_id', '=', comun.COMPANY_ID)], limit=1)
        if cierre:
            correo = cierre.mail_id
            mal = bool(correo) and correo.state == 'exception'
            if mal:
                texto_correo = 'El correo a XPO NO ha salido: %s' % (correo.failure_reason or '')[:80]
            else:
                texto_correo = 'Correo a XPO enviado%s.' % (cierre.envios > 1 and ' (%d veces)' % cierre.envios or '')
            return [{'semaforo': mal and 'rojo' or 'verde', 'que': que, 'cuantos': cierre.bultos,
                     'detalle': 'Cerrado a las %s por %s: %d tiendas, %d bultos. %s' % (
                         _hm(cierre.fecha_envio)[-5:], cierre.usuario_id.name or '-', cierre.tiendas, cierre.bultos,
                         texto_correo),
                     'accion': {'res_model': 'koroshi.envio.cierre', 'domain': [('id', '=', cierre.id)],
                                'name': 'Cierre del camión de hoy'}}]
        hoy_ini = comun.inicio_dia_utc(hoy)
        validadas = self.env['stock.picking'].sudo().search_count(self._dom_tiendas() + [
            ('state', '=', 'done'), ('date_done', '>=', hoy_ini), ('carrier_id.name', 'ilike', 'XPO')])
        if not validadas:
            return [{'semaforo': 'gris', 'que': que,
                     'detalle': 'Sin cerrar: hoy aún no hay OUT de tienda de XPO validadas.'}]
        tarde, hora = self._es_tarde(ahora, 'hora_camion', HORA_CAMION)
        return [{'semaforo': tarde and 'rojo' or 'ambar', 'que': que, 'cuantos': validadas,
                 'detalle': 'SIN CERRAR: %d OUT de tienda de XPO validadas hoy y el correo a XPO no ha salido%s. '
                            'Monitor > Consulta de envíos > Cerrar camión.' % (
                                validadas, tarde and ' (son más de las %s)' % hora or '')}]

    def _leido_sin_caja(self, ahora):
        """Prendas leídas en la PDA que no están en ninguna caja, en OUT sin validar (las MU2 del 18/11)."""
        if 'koroshi.preparacion.lectura' not in self.env:
            return []
        L = self.env['koroshi.preparacion.lectura'].sudo()
        if 'en_caja' not in L._fields:
            return []
        dom = [('tipo', '=', 'leer'), ('resultado', '=', 'ok'), ('deshecha', '=', False), ('en_caja', '=', False),
               ('move_line_id', '!=', False), ('move_line_id.result_package_id', '=', False),
               ('picking_id.state', 'not in', ('done', 'cancel'))]
        lecturas = L.search(dom, order='fecha asc')
        outs = lecturas.mapped('picking_id')
        vieja = lecturas[:1]
        minutos = vieja and vieja.fecha and _minutos(vieja.fecha, ahora) or 0
        sem = not outs and 'verde' or (minutos > MINUTOS_SIN_CAJA and 'rojo' or 'ambar')
        return [{'semaforo': sem, 'que': 'Leído sin caja (OUT sin validar)', 'cuantos': len(outs),
                 'detalle': outs and '%d prendas leídas fuera de caja en %d OUT (la más vieja hace %d min): %s' % (
                     len(lecturas), len(outs), minutos, self._nombres(outs)) or '',
                 'accion': outs and {'res_model': 'stock.picking', 'domain': [('id', 'in', outs.ids)],
                                     'name': 'OUT leídas sin caja'} or None}]

    def _validado_sin_caja(self, ahora):
        """OUT de tienda validadas hoy con prendas servidas fuera de caja: a S4T llegan sin caja (Excel de Miguel)."""
        que = 'Tiendas: validadas con prendas sin caja'
        hoy_ini = comun.inicio_dia_utc(comun.hoy_local())
        outs = self.env['stock.picking'].sudo().search(self._dom_tiendas() + [
            ('state', '=', 'done'), ('date_done', '>=', hoy_ini)])
        if not outs:
            return [self._contar(0, que)]
        lineas = self.env['stock.move.line'].sudo().search([
            ('picking_id', 'in', outs.ids), ('qty_done', '>', 0), ('result_package_id', '=', False),
            ('state', '!=', 'cancel')])
        malas = lineas.mapped('picking_id')
        return [self._contar(len(malas), que, '%d uds sin caja en %d OUT validadas hoy: %s' % (
            int(sum(lineas.mapped('qty_done'))), len(malas), self._nombres(malas)),
            {'res_model': 'stock.picking', 'domain': [('id', 'in', malas.ids)],
             'name': 'OUT validadas con prendas sin caja'})]

    def _operarios_parados(self, ahora):
        """Operarios con una OUT abierta que llevan rato sin leer, y tareas o actividades abiertas de otro día."""
        env = self.env
        res = []
        hoy_ini = comun.inicio_dia_utc(comun.hoy_local())
        if 'koroshi.operario.tarea' in env:
            T = env['koroshi.operario.tarea'].sudo()
            limite = hasattr(T, '_minutos_sin_leer_max') and T._minutos_sin_leer_max() or 15
            parados = []
            for t in T.search([('estado', '=', 'curso'), ('inicio', '>=', hoy_ini)]):
                minutos = int(t._minutos_sin_leer(ahora)) if hasattr(t, '_minutos_sin_leer') else 0
                if minutos >= limite:
                    parados.append((minutos, t))
            parados.sort(key=lambda x: -x[0])
            texto = ', '.join('%s (%d min, %s)' % (t.employee_id.name or '?', m,
                                                    t.picking_id.name or t.batch_id.name or '')
                              for m, t in parados[:6])
            res.append({'semaforo': parados and 'ambar' or 'verde', 'que': 'Operarios parados',
                        'cuantos': len(parados),
                        'detalle': parados and 'Con una OUT abierta y sin leer hace más de %d min: %s' % (
                            limite, texto) or '',
                        'accion': parados and {'res_model': 'koroshi.operario.tarea',
                                               'domain': [('id', 'in', [t.id for _m, t in parados])],
                                               'name': 'Operarios parados'} or None})
        viejas = []
        if 'koroshi.operario.tarea' in env:
            viejas += [t.employee_id.name for t in env['koroshi.operario.tarea'].sudo().search(
                [('estado', '=', 'curso'), ('inicio', '<', hoy_ini)])]
        if 'koroshi.actividad.registro' in env:
            viejas += [r.employee_id.name for r in env['koroshi.actividad.registro'].sudo().search(
                [('estado', '=', 'curso'), ('inicio', '<', hoy_ini)])]
        if viejas:
            res.append({'semaforo': 'ambar', 'que': 'Abiertos de otro día', 'cuantos': len(viejas),
                        'detalle': ', '.join(n or '?' for n in viejas[:8])})
        return res

    # ------------------------------------------------------------------ v2.6: Pendiente (jefe de almacén)
    def _stock_cero(self, ahora):
        """Artículos con pedidos esperando stock y 0 uds en el almacén según Odoo: hay que buscarlos o ajustarlos."""
        que = 'Stock 0 con pedidos esperando'
        M = self.env['stock.move'].sudo()
        dom = [('company_id', '=', comun.COMPANY_ID), ('picking_code', '=', 'outgoing'),
               ('state', 'in', ('confirmed', 'partially_available')),
               ('picking_id.state', 'not in', ('done', 'cancel', 'draft'))]
        esperan = {g['product_id'][0]: g['product_uom_qty']
                   for g in M.read_group(dom, ['product_id', 'product_uom_qty'], ['product_id']) if g['product_id']}
        if not esperan:
            return [self._contar(0, que)]
        con = set(g['product_id'][0] for g in self.env['stock.quant'].sudo().read_group(
            [('product_id', 'in', list(esperan)), ('location_id.usage', '=', 'internal'),
             ('company_id', '=', comun.COMPANY_ID), ('quantity', '>', 0)], ['product_id'], ['product_id'])
            if g['product_id'])
        sin = [pid for pid in esperan if pid not in con]
        uds = int(sum(esperan[pid] for pid in sin))
        return [self._contar(len(sin), que,
                             '%d artículos a 0 en Odoo con %d uds pedidas: buscarlos o ajustar el stock.' % (
                                 len(sin), uds),
                             {'res_model': 'stock.move', 'domain': dom + [('product_id', 'in', sin)],
                              'name': 'Pedidos esperando artículos a 0'}, rojo=False)]

    def _web(self, ahora):
        """Pedidos web: OUT sin agrupar (completas y con reserva incompleta) y canceladas de hoy (correo a Betty)."""
        if 'koroshi.web.corte' not in self.env:
            return []
        C = self.env['koroshi.web.corte'].sudo()
        res = []
        outs = C._candidatas(ahora)
        incompletas = outs.filtered(lambda p: not C._reserva_completa(p))
        completas = outs - incompletas
        res.append({'semaforo': incompletas and 'ambar' or 'verde', 'que': 'Web: OUT sin agrupar',
                    'cuantos': len(outs),
                    'detalle': outs and '%d completas, %d con reserva incompleta: %s' % (
                        len(completas), len(incompletas), self._nombres(incompletas or completas)) or '',
                    'accion': outs and {'res_model': 'stock.picking', 'domain': [('id', 'in', outs.ids)],
                                        'name': 'OUT web sin agrupar'} or None})
        hoy_ini = comun.inicio_dia_utc(comun.hoy_local())
        cortes = C.search([('fecha', '>=', hoy_ini), ('n_canceladas', '>', 0)])
        if cortes:
            n = sum(cortes.mapped('n_canceladas'))
            mal = cortes.filtered(lambda c: not c.mail_id or c.mail_id.state == 'exception')
            res.append({'semaforo': mal and 'rojo' or 'verde', 'que': 'Web: canceladas hoy', 'cuantos': n,
                        'detalle': mal and 'El correo a Betty de %d corte(s) no ha salido.' % len(mal)
                        or '%d OUT canceladas; correo a Betty enviado.' % n,
                        'accion': {'res_model': 'koroshi.web.corte', 'domain': [('id', 'in', cortes.ids)],
                                   'name': 'Cortes web de hoy'}})
        return res


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
        dom = [('state', 'in', ('rechazado', 'error', 'corregir'))]   # v2.6: también error y por corregir
        n = self.env['koroshi.s4t.envio'].sudo().search_count(dom)
        return [self._contar(n, 'Envíos a S4T rechazados o con error', 'Pedidos que S4T no tiene como enviados',
                             {'res_model': 'koroshi.s4t.envio', 'domain': dom,
                              'name': 'Envíos a S4T rechazados o con error'})]

    def _s4t_traspasos(self, ahora):
        if 'koroshi.s4t.traspaso' not in self.env:
            return []
        T = self.env['koroshi.s4t.traspaso'].sudo()   # v2.6: también los pendientes de entrar
        err = [('state', '=', 'error')]
        nuevos = [('state', '=', 'nuevo')]
        n_err, n_nuevo = T.search_count(err), T.search_count(nuevos)
        return [self._contar(n_err, 'Traspasos S4T con error', 'Devoluciones o correcciones que no han entrado',
                             {'res_model': 'koroshi.s4t.traspaso', 'domain': err, 'name': 'Traspasos S4T con error'}),
                self._contar(n_nuevo, 'Traspasos S4T pendientes de entrar', 'Sin recepción creada todavía',
                             {'res_model': 'koroshi.s4t.traspaso', 'domain': nuevos,
                              'name': 'Traspasos S4T pendientes'}, rojo=False)]

    def _actividades(self, ahora):
        if 'koroshi.actividad.registro' not in self.env:
            return []
        dom = [('nota', 'ilike', 'revisar'), ('create_date', '>=', ahora - datetime.timedelta(days=7))]
        n = self.env['koroshi.actividad.registro'].sudo().search_count(dom)
        return [self._contar(n, 'Tramos de actividad por revisar', 'Olvidados abiertos (últimos 7 días)',
                             {'res_model': 'koroshi.actividad.registro', 'domain': dom,
                              'name': 'Tramos por revisar'}, rojo=False)]

    # ------------------------------------------------------------------ IT (antes «Integraciones»)
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
