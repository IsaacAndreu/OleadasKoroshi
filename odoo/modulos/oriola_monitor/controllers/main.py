# -*- coding: utf-8 -*-
# Monitor picking Oriola - datos para la pantalla (solo lee, no cambia nada).
#
# /oriola_monitor/datos (json, usuario con sesion y grupo de almacen). Para el dia pedido (por defecto hoy):
#   - hechas: OUT del tipo de salida de Oriola validadas ese dia, con sus uds y quien las valido;
#   - lecturas: lineas con cantidad hecha escritas ese dia, por usuario y cuarto de hora (cada PDA tiene usuario);
#   - cajas: paquetes creados ese dia en esas OUT, por usuario;
#   - pendiente ahora (solo hoy): OUT abiertas por canal (segun el origen) y por lote.
#
# Este Odoo es lento: todo va en SQL agregado, solo sobre las OUT del tipo de salida, con limite de 15 s
# por consulta; el resultado se guarda CACHE_HOY s (CACHE_PASADO los dias pasados) y lo comparten todas
# las pantallas, asi que da igual cuantas haya abiertas.
import datetime
import threading
import time

import pytz

from odoo import http
from odoo.http import request

TZ = 'Europe/Madrid'
PARAM_TIPO = 'oriola_monitor.picking_type_id'
ALMACEN = 'WH-OR'               # si no hay parametro, el tipo de salida de este almacen
CACHE_HOY = 90                  # segundos
CACHE_PASADO = 600
LIMITE_MS = 15000               # statement_timeout de cada consulta
DIAS_SELECTOR = 14
CUARTO = 15                     # minutos
HUECO_MAX = 2                   # cuartos sin lecturas entre dos con lecturas que cuentan como trabajo (30 min)
ACTIVO_MIN = 15                 # "cogiendo ahora" si ha leido en los ultimos 15 min

# Canal segun el origen del albaran (el primero que encaje); 'S' va al final porque APP-S y SRP- tambien empiezan por S
CANALES = [('APP-S', 'App (APP-S)'), ('ECI-', 'El Corte Inglés (ECI)'), ('WT#', 'Web (WT#)'), ('VP-', 'VP'),
           ('VBD-', 'VBD'), ('SRP-', 'SRP'), ('DP-', 'DP'), ('B-DP', 'DP'), ('RT/', 'Devoluciones (RT)'),
           ('Retorno', 'Devoluciones (RT)'), ('S', 'Pedidos S')]
# Usuarios que no son personas: el almacen automatico y el sistema
AUTOMATICOS = ('automatizado', 'odoobot', '__system__')

_cache = {}
_lock = threading.Lock()


def _canal(origen):
    o = origen or ''
    for pre, nombre in CANALES:
        if o.startswith(pre):
            return nombre
    return 'Otros'


class OriolaMonitor(http.Controller):

    def _tz(self):
        return pytz.timezone(request.env.user.tz or TZ)

    def _local(self, dt):
        """datetime UTC sin zona (como lo guarda Odoo) -> datetime local sin zona"""
        if not dt:
            return None
        return pytz.utc.localize(dt).astimezone(self._tz()).replace(tzinfo=None)

    def _hm(self, dt):
        return dt and self._local(dt).strftime('%H:%M') or ''

    def _limites(self, dia):
        """dia local (date) -> (inicio, fin) en UTC sin zona"""
        tz = self._tz()
        ini = tz.localize(datetime.datetime.combine(dia, datetime.time.min)).astimezone(pytz.utc).replace(tzinfo=None)
        fin = tz.localize(datetime.datetime.combine(dia + datetime.timedelta(days=1), datetime.time.min))
        return ini, fin.astimezone(pytz.utc).replace(tzinfo=None)

    def _tipo(self, env):
        """(id del tipo de albaran de salida, nombre, compania)"""
        Tipo = env['stock.picking.type'].sudo()
        val = env['ir.config_parameter'].sudo().get_param(PARAM_TIPO)
        tipo = val and val.isdigit() and Tipo.browse(int(val)).exists() or Tipo.browse()
        if not tipo:
            tipo = Tipo.search([('code', '=', 'outgoing'), ('warehouse_id.code', '=', ALMACEN)], limit=1)
        return tipo

    def _sql(self, consulta, params):
        cr = request.env.cr
        cr.execute(consulta, params)
        return cr.fetchall()

    def _calcular(self, tipo, dia, es_hoy):
        cr = request.env.cr
        cr.execute('SET LOCAL statement_timeout = %s', (LIMITE_MS,))
        ini, fin = self._limites(dia)
        t0 = time.time()

        # ---- OUT validadas ese dia
        hechas = self._sql("""
            SELECT p.id, p.origin, p.write_uid, p.date_done
              FROM stock_picking p
             WHERE p.picking_type_id = %s AND p.state = 'done' AND p.date_done >= %s AND p.date_done < %s
        """, (tipo.id, ini, fin))
        ids_hechas = [h[0] for h in hechas]

        # ---- OUT abiertas ahora (solo hoy): lo pendiente y lo que se esta leyendo
        abiertas = []
        if es_hoy:
            abiertas = self._sql("""
                SELECT p.id, p.origin, p.state, p.batch_id, p.scheduled_date
                  FROM stock_picking p
                 WHERE p.picking_type_id = %s AND p.state IN ('assigned', 'confirmed', 'waiting')
            """, (tipo.id,))
        ids_abiertas = [a[0] for a in abiertas]
        ids = ids_hechas + ids_abiertas

        uds_out = {}
        if ids_hechas:
            for pid, q in self._sql("""
                SELECT ml.picking_id, SUM(ml.qty_done) FROM stock_move_line ml
                 WHERE ml.picking_id = ANY(%s) GROUP BY ml.picking_id
            """, (ids_hechas,)):
                uds_out[pid] = q or 0.0
        pend_out = {}
        if ids_abiertas:
            for pid, q in self._sql("""
                SELECT m.picking_id, SUM(m.product_uom_qty) FROM stock_move m
                 WHERE m.picking_id = ANY(%s) AND m.state NOT IN ('done', 'cancel') GROUP BY m.picking_id
            """, (ids_abiertas,)):
                pend_out[pid] = q or 0.0

        # ---- Lecturas del dia por usuario y cuarto de hora (en UTC; se pasa a hora local abajo)
        # Una sola pasada por las lineas (es la consulta que mas tarda, ~1,5 s el 26/10): por usuario y cuarto,
        # con primera/ultima escritura y las OUT tocadas; el resumen por usuario se saca de aqui en Python
        lect = []
        cajas = []
        if ids:
            lect = self._sql("""
                SELECT ml.write_uid,
                       date_trunc('hour', ml.write_date)
                         + floor(date_part('minute', ml.write_date) / %s) * %s * interval '1 minute' AS q,
                       SUM(ml.qty_done), COUNT(*), MIN(ml.write_date), MAX(ml.write_date), array_agg(DISTINCT ml.picking_id)
                  FROM stock_move_line ml
                 WHERE ml.picking_id = ANY(%s) AND ml.qty_done > 0 AND ml.write_date >= %s AND ml.write_date < %s
                 GROUP BY 1, 2
            """, (CUARTO, CUARTO, ids, ini, fin))
            cajas = self._sql("""
                SELECT q.create_uid, COUNT(*)
                  FROM stock_quant_package q
                 WHERE q.id IN (SELECT DISTINCT ml.result_package_id FROM stock_move_line ml
                                 WHERE ml.picking_id = ANY(%s) AND ml.result_package_id IS NOT NULL
                                   AND ml.write_date >= %s AND ml.write_date < %s)
                   AND q.create_date >= %s AND q.create_date < %s
                 GROUP BY 1
            """, (ids, ini, fin, ini, fin))

        # ---- Lotes con OUT abiertas: cuantas hay en cada estado
        lotes = []
        id_lotes = list(set(a[3] for a in abiertas if a[3]))
        if id_lotes:
            filas = self._sql("""
                SELECT b.id, b.name, p.state, COUNT(*)
                  FROM stock_picking_batch b JOIN stock_picking p ON p.batch_id = b.id
                 WHERE b.id = ANY(%s)
                 GROUP BY b.id, b.name, p.state
            """, (id_lotes,))
            L = {}
            for bid, nombre, est, n in filas:
                l = L.setdefault(bid, {'lote': nombre, 'hechas': 0, 'listas': 0, 'espera': 0, 'canceladas': 0, 'uds': 0.0})
                if est == 'done':
                    l['hechas'] += n
                elif est == 'assigned':
                    l['listas'] += n
                elif est == 'cancel':
                    l['canceladas'] += n
                else:
                    l['espera'] += n
            for a in abiertas:
                if a[3] in L:
                    L[a[3]]['uds'] += pend_out.get(a[0], 0.0)
            lotes = sorted(L.values(), key=lambda x: x['lote'], reverse=True)

        # ---- Nombres de los usuarios
        uids = set(h[2] for h in hechas) | set(l[0] for l in lect) | set(c[0] for c in cajas)
        uids.discard(None)
        nombres = {}
        if uids:
            for uid, login, nombre in self._sql("""
                SELECT u.id, u.login, rp.name FROM res_users u JOIN res_partner rp ON rp.id = u.partner_id
                 WHERE u.id = ANY(%s)
            """, (list(uids),)):
                nombres[uid] = (nombre or login or str(uid), login or '')

        def es_auto(uid):
            nom, login = nombres.get(uid, ('', ''))
            txt = ('%s %s' % (nom, login)).lower()
            return uid == 1 or any(a in txt for a in AUTOMATICOS)

        # ---- Por persona
        P = {}

        def per(uid):
            return P.setdefault(uid, {'uid': uid, 'nombre': nombres.get(uid, (str(uid), ''))[0], 'auto': es_auto(uid),
                                      'uds': 0.0, 'lineas': 0, 'out_leidas': 0, 'validadas': 0, 'uds_validadas': 0.0,
                                      'cajas': 0, 'cuartos': set(), 'outs': set(), 'primera': None, 'ultima': None})

        por_hora = {}
        for uid, q, uds, n, mn, mx, outs in lect:
            p = per(uid)
            p['uds'] += uds or 0.0
            p['lineas'] += n
            p['outs'].update(outs or [])
            if mn and (not p['primera'] or mn < p['primera']):
                p['primera'] = mn
            if mx and (not p['ultima'] or mx > p['ultima']):
                p['ultima'] = mx
            ql = self._local(q)
            p['cuartos'].add(ql)
            h = ql.hour
            ph = por_hora.setdefault(h, {'h': h, 'personas': 0.0, 'auto': 0.0})
            ph[p['auto'] and 'auto' or 'personas'] += uds or 0.0
        for pid, origen, uid, dd in hechas:
            p = per(uid)
            p['validadas'] += 1
            p['uds_validadas'] += uds_out.get(pid, 0.0)
        for uid, n in cajas:
            per(uid)['cajas'] += n

        ahora = datetime.datetime.utcnow()
        personas, automaticos = [], []
        for p in P.values():
            # horas activas: cuartos con lecturas + huecos cortos entre ellos
            p['out_leidas'] = len(p.pop('outs'))
            cs = sorted(p.pop('cuartos'))
            n = len(cs)
            for a, b in zip(cs, cs[1:]):
                hueco = int((b - a).total_seconds() // (CUARTO * 60)) - 1
                if 0 < hueco <= HUECO_MAX:
                    n += hueco
            p['horas'] = round(n * CUARTO / 60.0, 2)
            p['uds_hora'] = p['horas'] and round(p['uds'] / p['horas']) or 0
            p['activo'] = bool(es_hoy and p['ultima'] and (ahora - p['ultima']).total_seconds() <= ACTIVO_MIN * 60)
            p['primera'], p['ultima'] = self._hm(p['primera']), self._hm(p['ultima'])
            (automaticos if p['auto'] else personas).append(p)
        personas.sort(key=lambda x: -x['uds'])
        automaticos.sort(key=lambda x: -x['uds'])

        # ---- Por canal: hechas ese dia y (hoy) lo abierto ahora
        C = {}

        def can(origen):
            nombre = _canal(origen)
            return C.setdefault(nombre, {'canal': nombre, 'hechas': 0, 'uds_hechas': 0.0, 'listas': 0, 'uds_listas': 0.0,
                                         'espera': 0, 'uds_espera': 0.0, 'mas_antigua': None})
        for pid, origen, uid, dd in hechas:
            c = can(origen)
            c['hechas'] += 1
            c['uds_hechas'] += uds_out.get(pid, 0.0)
        for pid, origen, est, bid, sched in abiertas:
            c = can(origen)
            k = est == 'assigned' and 'listas' or 'espera'
            c[k] += 1
            c['uds_' + k] += pend_out.get(pid, 0.0)
            if sched and (not c['mas_antigua'] or sched < c['mas_antigua']):
                c['mas_antigua'] = sched
        canales = sorted(C.values(), key=lambda x: -(x['listas'] + x['espera'] + x['hechas']))
        for c in canales:
            c['mas_antigua'] = c['mas_antigua'] and self._local(c['mas_antigua']).strftime('%d/%m/%Y') or ''

        uds_personas = sum(p['uds'] for p in personas)
        horas_personas = sum(p['horas'] for p in personas)
        return {
            'resumen': {
                'validadas': len(hechas),
                'uds_validadas': sum(uds_out.values()),
                'cajas': sum(n for uid, n in cajas),
                'uds_leidas': uds_personas + sum(p['uds'] for p in automaticos),
                'uds_personas': uds_personas,
                'uds_auto': sum(p['uds'] for p in automaticos),
                'personas': len(personas),
                'activas': len([p for p in personas if p['activo']]),
                'horas_personas': round(horas_personas, 2),
                'uds_hora_persona': horas_personas and round(uds_personas / horas_personas) or 0,
                'listas': len([a for a in abiertas if a[2] == 'assigned']),
                'uds_listas': sum(pend_out.get(a[0], 0.0) for a in abiertas if a[2] == 'assigned'),
                'espera': len([a for a in abiertas if a[2] != 'assigned']),
                'uds_espera': sum(pend_out.get(a[0], 0.0) for a in abiertas if a[2] != 'assigned'),
            },
            'personas': personas,
            'automaticos': automaticos,
            'por_hora': [por_hora[h] for h in sorted(por_hora)],
            'canales': canales,
            'lotes': lotes,
            'segundos': round(time.time() - t0, 2),
        }

    @http.route('/oriola_monitor/datos', type='json', auth='user')
    def datos(self, dia=None, refrescar=False, **kw):
        env = request.env
        if not env.user.has_group('stock.group_stock_user'):
            return {'error': 'Hace falta el permiso de Inventario para ver el monitor.'}
        tipo = self._tipo(env)
        if not tipo:
            return {'error': 'No encuentro el tipo de albarán de salida (parámetro %s o almacén %s).' % (PARAM_TIPO, ALMACEN)}
        hoy = datetime.datetime.now(self._tz()).date()
        try:
            d = dia and datetime.datetime.strptime(dia, '%Y-%m-%d').date() or hoy
        except ValueError:
            d = hoy
        es_hoy = d == hoy
        clave = (env.cr.dbname, tipo.id, d)
        ttl = es_hoy and CACHE_HOY or CACHE_PASADO
        # Un solo calculo a la vez: si otra pantalla esta calculando, se espera y se usa su resultado
        with _lock:
            guardado = _cache.get(clave)
            if guardado and time.time() - guardado[0] < ttl and not (refrescar and time.time() - guardado[0] > 20):
                res, cuando = guardado[1], guardado[0]
            else:
                res = self._calcular(tipo, d, es_hoy)
                cuando = time.time()
                _cache[clave] = (cuando, res)
                for k in [k for k, v in _cache.items() if time.time() - v[0] > CACHE_PASADO]:
                    _cache.pop(k, None)
        out = dict(res)
        out.update({
            'dia': d.strftime('%Y-%m-%d'),
            'es_hoy': es_hoy,
            'dias': [(hoy - datetime.timedelta(days=i)).strftime('%Y-%m-%d') for i in range(DIAS_SELECTOR)],
            'tipo': tipo.display_name,
            'calculado': datetime.datetime.fromtimestamp(cuando, self._tz()).strftime('%H:%M:%S'),
            'refresco_s': CACHE_HOY,
        })
        return out
