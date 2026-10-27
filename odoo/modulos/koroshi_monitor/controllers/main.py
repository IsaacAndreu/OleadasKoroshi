# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Monitor zonas - datos para la pantalla (solo lee, no cambia nada).
#
# /koroshi_monitor/datos (json, usuario con sesion). Dos modos segun 'prefijo':
#   - 'Z-2210-' (agrupaciones de zona): una fila por OUT con zona, caja de tienda, OUT,
#     tienda, pedido, uds (movimientos no cancelados), huecos (ubicaciones distintas),
#     lineales (Lmin-Lmax o MU-xx), uds leidas, estado (hecha = validada, curso = algo leido,
#     pend = nada leido), primera lectura y ultima lectura / hora de validacion.
#   - 'TIENDAS:2026-10-23' (v1.1, una OUT por pedido, sin zonas): las OUT de PED. TIENDAS
#     creadas o validadas ese dia, con lo mismo + minutos que ha tardado cada OUT y su ritmo,
#     el ritmo del equipo, las uds leidas por hora y la hora prevista de fin.
#     v1.2: cajas cerradas de cada OUT, hace cuanto se cerro la ultima (OUT parada si pasa de
#     PARADA_MIN) y personas cogiendo ahora (OUT en curso con caja cerrada hace poco).
#     v1.4: estados 'parcial' (cogido todo lo que hay, o sin cerrar caja hace mas de PARADA_MIN con prendas
#     sin coger: sin stock o no encontradas) y 'sinstock' (en espera);
#     disp = reservado + cogido; faltas = lo que pide el pedido y no hay (lista por OUT y articulo).
# Mismos calculos que las paginas estado-OUT-agrupaciones-Z-*.html de bin/versiones.
# =============================================================================
import datetime
import re

import pytz

from odoo import fields, http
from odoo.http import request

COMPANY_ID = 8          # EFFECTIVE LOGISTICS, S.L.
N_PREFIJOS = 15         # agrupaciones que salen en el desplegable
N_DIAS = 3              # dias de "Tiendas" que salen en el desplegable
TIPO_PEDIDO = 'PED. TIENDAS'
PARADA_MIN = 20         # OUT en curso sin cerrar caja en estos minutos = parada (no cuenta como persona activa)

RE_LINEAL = re.compile(r' L(\d+) ')
RE_MU = re.compile(r'^(MU-\d+)')
RE_TIENDA = re.compile(r'\bK\d+ - .*$')


class KoroshiMonitor(http.Controller):

    def _tz(self):
        return pytz.timezone(request.env.user.tz or 'Europe/Madrid')

    def _hoy_local(self):
        return datetime.datetime.now(pytz.utc).astimezone(self._tz()).date()

    def _prefijos(self, env):
        lotes = env['stock.picking.batch'].sudo().search([('name', '=like', 'Z-%')], order='id desc', limit=300)
        vistos = []
        for lote in lotes:
            prefijo = lote.name.rsplit('-', 1)[0] + '-'
            if prefijo not in vistos:
                vistos.append(prefijo)
            if len(vistos) >= N_PREFIJOS:
                break
        return vistos

    def _hora(self, dt):
        if not dt:
            return ''
        local = fields.Datetime.context_timestamp(request.env.user, dt)
        return '%d:%02d' % (local.hour, local.minute)

    def _minutos(self, dt):
        # minutos desde la medianoche local
        local = fields.Datetime.context_timestamp(request.env.user, dt)
        return local.hour * 60 + local.minute

    def _filas(self, env, picks, prefijo, desde=None, hasta=None):
        # desde/hasta (UTC): solo para el modo tiendas; por hora y primera/ultima lectura del equipo
        # cuentan solo las cajas cerradas dentro del dia elegido
        filas = {}
        for p in picks:
            nota = p.note or ''
            caja = ''
            if 'CAJA ' in nota:
                caja = nota.split('CAJA ')[1][:2].strip()
            nombre = p.partner_id.name or ''
            z = ''
            if prefijo and p.batch_id and (p.batch_id.name or '').startswith(prefijo):
                z = p.batch_id.name[len(prefijo):]
            filas[p.id] = {
                'z': z,
                'lote': p.batch_id.name or '',
                'caja': caja,
                'out': p.name.replace('EFFEC/OUT/', ''),
                # v1.7: 'K75 - C/ PELAYO, 12 (BARCELONA)' lleva coma: se coge desde la K
                'tienda': (RE_TIENDA.search(nombre) and RE_TIENDA.search(nombre).group(0)) or nombre.split(', ')[-1],
                'pedido': p.origin or '',
                'u': 0.0, 'leido': 0.0, 'disp': 0.0, 'faltas': [],
                '_huecos': set(), '_l': [], '_mu': set(),
                '_a': None, '_b': None, '_cajas': set(),
                '_estado': p.state, '_done': p.date_done,
            }

        # v1.4: lo que se puede coger (disp) = lo reservado + lo ya cogido de cada movimiento; lo que pide el
        # pedido y no hay (faltas) no se puede coger: va a pedido pendiente al validar
        movs = env['stock.move'].sudo().search_read([('picking_id', 'in', picks.ids), ('state', '!=', 'cancel')],
                                                    ['picking_id', 'product_uom_qty', 'reserved_availability',
                                                     'quantity_done', 'product_id'])
        for m in movs:
            f = filas[m['picking_id'][0]]
            f['u'] += m['product_uom_qty']
            disp = max(m['reserved_availability'] or 0.0, m['quantity_done'] or 0.0)
            f['disp'] += disp
            # por linea: [articulo, sin coger (pide - cogido), de ello sin stock (pide - reservado/cogido)]
            pend = m['product_uom_qty'] - (m['quantity_done'] or 0.0)
            if pend > 0.001 and f['_estado'] != 'done':
                f['faltas'].append([m['product_id'] and m['product_id'][1] or '?', pend,
                                    max(m['product_uom_qty'] - disp, 0.0)])

        lineas = env['stock.move.line'].sudo().search_read([('picking_id', 'in', picks.ids)],
                                                           ['picking_id', 'qty_done', 'location_id', 'write_date',
                                                            'result_package_id'])
        # Hora de cada lectura = hora de cierre de su caja (creacion de la matricula CJ). La hora de la
        # linea no sirve: el programa guarda todas las lineas de la OUT de golpe y cambia si luego se
        # toca la linea (juntar cajas). Sin caja: la hora de la linea.
        ids_caja = list(set([ml['result_package_id'][0] for ml in lineas if ml['result_package_id']]))
        hora_caja = {}
        for pq in env['stock.quant.package'].sudo().search_read([('id', 'in', ids_caja)], ['create_date']):
            hora_caja[pq['id']] = pq['create_date']
        por_hora = {}
        dia = {'primera': None, 'ultima': None, 'marcas': []}
        for ml in lineas:
            f = filas[ml['picking_id'][0]]
            partes = (ml['location_id'] and ml['location_id'][1] or '').split('/')
            hueco = partes[3] if len(partes) >= 5 else partes[-1]
            f['_huecos'].add(hueco)
            lin = RE_LINEAL.search(hueco)
            if lin:
                f['_l'].append(int(lin.group(1)))
            else:
                mu = RE_MU.search(hueco)
                if mu:
                    f['_mu'].add(mu.group(1))
            f['leido'] += ml['qty_done']
            if ml['qty_done'] > 0:
                if ml['result_package_id']:
                    f['_cajas'].add(ml['result_package_id'][0])
                w = ml['result_package_id'] and hora_caja.get(ml['result_package_id'][0]) or ml['write_date']
                if not f['_a'] or w < f['_a']:
                    f['_a'] = w
                if not f['_b'] or w > f['_b']:
                    f['_b'] = w
                if desde and (w < desde or w >= hasta):
                    continue
                if not dia['primera'] or w < dia['primera']:
                    dia['primera'] = w
                if not dia['ultima'] or w > dia['ultima']:
                    dia['ultima'] = w
                h = self._minutos(w) // 60
                por_hora[h] = por_hora.get(h, 0.0) + ml['qty_done']
                # quien cierra la caja: en zonas, la zona (una persona por zona); en oleada, la U; si no, la OUT
                lote = f['lote']
                quien = lote.startswith('Z-') and lote or (lote.startswith('B-KOR') and 'U' or ml['picking_id'][0])
                dia['marcas'].append((fields.Datetime.context_timestamp(request.env.user, w), quien))
        return filas, por_hora, dia

    def _personas(self, dia, leidas):
        """Horas-persona y personas estimadas por las cajas cerradas: cuarto de hora a cuarto de hora,
        cuantas OUT (o zonas) cierran caja a la vez; huecos de hasta 30 min cuentan como trabajo.
        Mismo calculo que el modulo KOROSHI KPI."""
        cuartos = {}
        for dt, quien in dia['marcas']:
            k = dt.toordinal() * 96 + (dt.hour * 60 + dt.minute) // 15
            cuartos.setdefault(k, set()).add(quien)
        hp = 0.0
        maximo = 0
        anterior = None
        for k in sorted(cuartos):
            n = len(cuartos[k])
            hp += n * 0.25
            maximo = max(maximo, n)
            if anterior is not None and 1 < k - anterior <= 3:
                hp += min(n, len(cuartos[anterior])) * 0.25 * (k - anterior - 1)
            anterior = k
        reloj = 0.0
        if dia['primera'] and dia['ultima']:
            reloj = (dia['ultima'] - dia['primera']).total_seconds() / 3600.0
        return {
            'hp': round(hp, 2), 'personas_max': maximo,
            'personas_media': reloj > 0.05 and round(hp / reloj, 1) or 0,
            'horas_reloj': round(reloj, 2),
            'uds_hp': hp and int(round(leidas / hp)) or 0,
            'uds_persona': maximo and int(round(leidas / maximo)) or 0,
            's_ud': leidas and round(hp * 3600.0 / leidas, 1) or 0,
        }

    def _fila(self, f):
        # v1.4: parcial = ya cogido todo lo que hay, solo falta lo que no hay (sin stock); sinstock = OUT en
        # espera sin nada que coger (pedido pendiente)
        # v1.8: si ya se ha cogido todo lo que hay y solo falta lo que no hay (sin stock), la OUT esta HECHA
        # aunque aun no se haya validado en Odoo (sin_validar); lo que falta se ensena aparte
        falta = max(f['u'] - f['disp'], 0.0)
        sin_validar = False
        if f['_estado'] == 'done':
            est = 'hecha'
        elif f['disp'] <= 0.001 and f['leido'] <= 0:
            est = 'sinstock'
        elif f['leido'] > 0 and f['leido'] >= f['disp'] - 0.001 and falta > 0.001:
            est = 'hecha'
            sin_validar = True
        elif f['leido'] > 0:
            est = 'curso'
        else:
            est = 'pend'
        lin = ''
        if f['_l']:
            lo, hi = min(f['_l']), max(f['_l'])
            lin = 'L%d' % lo if lo == hi else 'L%d-L%d' % (lo, hi)
        if f['_mu']:
            mus = sorted(f['_mu'])
            lin = (lin + ' · ' if lin else '') + mus[0] + ('…' + mus[-1] if len(mus) > 1 else '')
        fin_dt = f['_done'] if est == 'hecha' and f['_done'] else f['_b']
        mins = 0            # de la primera a la ultima lectura (la validacion puede ser mucho despues)
        if f['_a'] and f['_b'] and f['_b'] > f['_a']:
            mins = int((f['_b'] - f['_a']).total_seconds() // 60)
        return {
            'z': f['z'], 'lote': f['lote'], 'caja': f['caja'], 'out': f['out'], 'tienda': f['tienda'],
            'pedido': f['pedido'], 'u': f['u'], 'huecos': len(f['_huecos']), 'lin': lin or '-',
            'leido': f['leido'], 'est': est, 'ini': self._hora(f['_a']), 'fin': self._hora(fin_dt),
            'min': mins, 'cajas': len(f['_cajas']), '_a': f['_a'], '_b': f['_b'],
            'disp': f['disp'], 'falta': (est != 'hecha' or sin_validar) and falta or 0.0, 'faltas': f['faltas'],
            'sin_validar': sin_validar,
        }

    @http.route('/koroshi_monitor/datos', type='json', auth='user')
    def datos(self, prefijo=None, **kw):
        env = request.env(context=dict(request.env.context, allowed_company_ids=[COMPANY_ID]))
        hoy = self._hoy_local()
        dias = []
        for i in range(N_DIAS):
            dias.append('TIENDAS:%s' % (hoy - datetime.timedelta(days=i)).isoformat())
        zonas = self._prefijos(env)
        prefijos = dias + zonas
        if not prefijo or prefijo not in prefijos:
            z_hoy = 'Z-%s-' % hoy.strftime('%d%m')
            prefijo = z_hoy in zonas and z_hoy or dias[0]
        etiquetas = {}
        for d in dias:
            f = datetime.date(*[int(x) for x in d.split(':')[1].split('-')])
            etiquetas[d] = 'Tiendas %s%s' % (f.strftime('%d/%m'), f == hoy and ' (hoy)' or '')
        for z in zonas:
            etiquetas[z] = z.rstrip('-')
            # v1.9: si ese dia hay 2a ronda, la 1a se llama R1 en el selector
            if re.match(r'^Z-\d{4}-$', z) and [x for x in zonas if x.startswith(z + 'R')]:
                etiquetas[z] = z.rstrip('-') + ' R1'
        ahora = fields.Datetime.now()
        res = {'prefijos': prefijos, 'etiquetas': etiquetas, 'prefijo': prefijo, 'D': [], 'pedidos': 0,
               'hora': self._hora(ahora), 'modo': prefijo.startswith('TIENDAS:') and 'tiendas' or 'zonas'}

        if res['modo'] == 'zonas':
            picks = env['stock.picking'].sudo().search([('batch_id.name', '=like', prefijo + '%'),
                                                        ('company_id', '=', COMPANY_ID)])
            # v1.9: Z-ddmm- es la 1a ronda: sin las de las rondas siguientes (Z-ddmm-R2-...), que tienen su propia
            # pantalla y empiezan otra vez en la caja 01
            if re.match(r'^Z-\d{4}-$', prefijo):
                picks = picks.filtered(lambda p: not re.match(r'^R\d+-', (p.batch_id.name or '')[len(prefijo):]))
            # Personas y horas: solo las cajas cerradas el dia de la agrupacion (Z-ddmm-), no las que se
            # tocaron despues (juntar cajas, validar dias mas tarde)
            z_ini = z_fin = None
            m = re.match(r'^Z-(\d{2})(\d{2})-', prefijo)
            if m:
                try:
                    zd = datetime.date(hoy.year, int(m.group(2)), int(m.group(1)))
                    if zd > hoy:
                        zd = zd.replace(year=hoy.year - 1)
                    z_ini = self._tz().localize(datetime.datetime(zd.year, zd.month, zd.day)).astimezone(
                        pytz.utc).replace(tzinfo=None)
                    z_fin = z_ini + datetime.timedelta(days=1)
                except ValueError:
                    z_ini = z_fin = None
            filas, por_hora, dia_z = self._filas(env, picks, prefijo, z_ini, z_fin)
            D = []
            for f in filas.values():
                d = self._fila(f)
                d.pop('_a')
                d.pop('_b')
                if d['est'] == 'sinstock':      # v1.5: pedidos pendientes en espera: no son de esta agrupacion
                    continue
                D.append(d)
            D.sort(key=lambda d: d['out'])
            res['D'] = D
            res['pedidos'] = len(set([d['pedido'] for d in D]))
            res['personas'] = self._personas(dia_z, sum([x[1] for x in por_hora.items()]))
            res['personas']['inicio'] = self._hora(dia_z['primera'])
            res['personas']['ultima'] = self._hora(dia_z['ultima'])
            return res

        # ---------------- Modo tiendas: una OUT por pedido, el dia elegido ----------------
        dia = datetime.date(*[int(x) for x in prefijo.split(':')[1].split('-')])
        tz = self._tz()
        ini = tz.localize(datetime.datetime(dia.year, dia.month, dia.day)).astimezone(pytz.utc).replace(tzinfo=None)
        fin = ini + datetime.timedelta(days=1)
        picks = env['stock.picking'].sudo().search([
            ('company_id', '=', COMPANY_ID),
            ('picking_type_code', '=', 'outgoing'),
            ('state', '!=', 'cancel'),
            ('sale_id.s_order_type_id.name', '=', TIPO_PEDIDO),
            '|', '&', ('create_date', '>=', ini), ('create_date', '<', fin),
            '&', ('date_done', '>=', ini), ('date_done', '<', fin),
        ])
        filas, por_hora, dia_t = self._filas(env, picks, None, ini, fin)
        D = []
        primera = dia_t['primera']
        ultima = dia_t['ultima']
        es_hoy = dia == self._hoy_local()
        activas = 0
        n_pendientes = 0        # v1.5: OUT en espera sin stock (pedidos pendientes) que no se ensenan
        for f in filas.values():
            d = self._fila(f)
            # Solo se sabe la hora de cada caja cerrada: con n cajas, de la primera a la ultima van n-1
            # cajas; la OUT entera dura ~ (ultima - primera) * n / (n - 1). Con 1 caja no se sabe.
            if d['cajas'] >= 2 and d['min']:
                d['min'] = int(round(d['min'] * d['cajas'] / (d['cajas'] - 1.0)))
            else:
                d['min'] = 0
            d['uh'] = d['min'] and round(d['leido'] * 60.0 / d['min']) or 0
            d['hace'] = ''
            d['parada'] = False
            if d['est'] == 'curso' and d['_b'] and es_hoy:
                hace = int((ahora - d['_b']).total_seconds() // 60)
                d['hace'] = max(hace, 0)
                d['parada'] = hace > PARADA_MIN
                if not d['parada']:
                    activas += 1
            # v1.8: cogiendose pero sin cerrar caja hace mas de PARADA_MIN (o de un dia anterior) = ya no se esta
            # cogiendo: se da por HECHA (sin validar); lo que no se ha cogido (sin stock o no encontrado) es lo que falta.
            # Antes (v1.4) salia como "parcial".
            if d['est'] == 'curso' and (d['parada'] or not es_hoy):
                d['est'] = 'hecha'
                d['sin_validar'] = True
                d['falta'] = max(d['u'] - d['leido'], 0.0)
            if d['est'] == 'parcial':
                d['falta'] = max(d['u'] - d['leido'], 0.0)
            d.pop('_a')
            d.pop('_b')
            # v1.5: las OUT en espera sin nada reservado (pedidos pendientes que salen al validar con faltas)
            # no son trabajo de hoy: no se ensenan, solo se cuentan
            if d['est'] == 'sinstock':
                n_pendientes += 1
                continue
            D.append(d)
        res['sin_stock'] = n_pendientes
        rango = {'curso': 0, 'parcial': 1, 'pend': 2, 'hecha': 3, 'sinstock': 4}
        D.sort(key=lambda d: (rango[d['est']], d['est'] == 'hecha' and d['fin'] and -int(d['fin'].replace(':', '')) or 0,
                              d['out']))
        # pendiente de coger = solo lo que hay (reservado); lo que falta sin stock no cuenta para la hora de fin
        pendientes = sum([max(d['disp'] - d['leido'], 0.0) for d in D if d['est'] not in ('hecha', 'parcial')])
        leidas_dia = sum([x[1] for x in por_hora.items()])
        equipo = {'inicio': self._hora(primera), 'ultima': self._hora(ultima), 'uh': 0, 'fin_previsto': '',
                  'activas': activas, 'parada_min': PARADA_MIN,
                  'cajas': sum([d['cajas'] for d in D])}
        if primera:
            hasta = pendientes > 0 and dia == self._hoy_local() and ahora or (ultima or ahora)
            horas = (hasta - primera).total_seconds() / 3600.0
            if horas > 0.05:
                equipo['uh'] = int(round(leidas_dia / horas))   # solo lo cerrado ese dia
                if pendientes > 0 and equipo['uh'] > 0 and dia == self._hoy_local():
                    equipo['fin_previsto'] = self._hora(ahora + datetime.timedelta(hours=pendientes / equipo['uh']))
        res['D'] = D
        res['pedidos'] = len(set([d['pedido'] for d in D]))
        res['equipo'] = equipo
        res['personas'] = self._personas(dia_t, leidas_dia)
        res['por_hora'] = [[h, int(por_hora[h])] for h in sorted(por_hora)]
        return res
