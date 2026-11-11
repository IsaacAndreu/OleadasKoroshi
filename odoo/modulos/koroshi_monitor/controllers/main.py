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
PERSONA_INACTIVA_MIN = 5  # tiendas: una OUT sin lecturas/cajas durante este tiempo deja de contar como persona
# zonas (v1.20.1): entre dos cajas de la misma OUT, hasta PARADA_MIN minutos se sigue cogiendo (ver _personas)

RE_LINEAL = re.compile(r' L(\d+) ')
RE_MU = re.compile(r'^(MU-\d+)')
RE_TIENDA = re.compile(r'\bK\d+ - .*$')

RE_OP = re.compile(r'^([A-Za-z]+)0*(\d+)$')


def codigo_op(emp):
    """v1.18: codigo corto del operario (tarjeta OP0003 -> OP3). En el monitor nunca sale el nombre."""
    b = (emp.barcode or '').strip()
    m = RE_OP.match(b)
    if m:
        return '%s%s' % (m.group(1).upper(), m.group(2))
    return b or 'OP?'


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
            carrier = getattr(p, 'carrier_id', False)
            transportista = carrier and carrier.name or ''
            etiqueta = getattr(p, 'carrier_tracking_ref', '') or ''
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
                # v1.10: etiqueta del transportista (XPO/GLS) hecha = numero de seguimiento en la OUT.
                # v1.17: se exponen también transportista y número de etiqueta para ordenar/filtrar.
                'etq': bool(etiqueta),
                'transportista': transportista,
                'etiqueta': etiqueta,
                '_bultos': p.number_of_packages or 0,     # v1.14: bultos que tiene Odoo en la OUT (los de XPO)
                'id': p.id,         # v1.11: para abrir la OUT desde el monitor
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
        # v1.18.2: una caja usada en dos OUT (koroshi_caja_existente: OUT pequena metida en la caja de otra OUT)
        # cuenta solo en su OUT duena, la de la primera linea que la uso (la misma regla que los bultos de Odoo)
        dueno_caja = {}
        if ids_caja:
            for ml in env['stock.move.line'].sudo().search_read(
                    [('result_package_id', 'in', ids_caja), ('state', '!=', 'cancel')],
                    ['picking_id', 'result_package_id'], order='id'):
                if ml['picking_id'] and ml['result_package_id'][0] not in dueno_caja:
                    dueno_caja[ml['result_package_id'][0]] = ml['picking_id'][0]
        por_hora = {}
        # Desglose por hora y OUT para que la franja inferior pueda mostrar
        # qué OUT compone cada total. Se mantiene el total agregado anterior
        # para no romper los KPIs existentes.
        por_hora_out = {}
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
                if ml['result_package_id'] and dueno_caja.get(ml['result_package_id'][0],
                                                               ml['picking_id'][0]) == ml['picking_id'][0]:
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
                por_hora_out.setdefault(h, {})
                out_row = por_hora_out[h].setdefault(f['id'], {
                    'id': f['id'], 'out': f['out'], 'tienda': f['tienda'], 'u': 0.0,
                })
                out_row['u'] += ml['qty_done']
                # v1.19.1: en la pantalla de zonas cada OUT abierta cuenta como una persona. Antes se usaba el lote
                # de zona (Z-ddmm-D1...) y todas las OUT de una zona contaban como una sola persona.
                # Fuera del modo zonas se conserva el criterio anterior de las oleadas B-KOR.
                lote = f['lote']
                quien = ml['picking_id'][0] if prefijo else (lote.startswith('B-KOR') and 'U' or ml['picking_id'][0])
                dia['marcas'].append((fields.Datetime.context_timestamp(request.env.user, w), quien))
        return filas, por_hora, dia, por_hora_out

    def _personas(self, dia, leidas, zonas=False):
        """Horas-persona estimadas por actividad real de cada OUT.

        Tiendas: cada lectura/caja mantiene su OUT activa durante PERSONA_INACTIVA_MIN minutos. Las ventanas
        consecutivas de una misma OUT se unen, pero no se rellena ningun hueco mayor.

        Zonas (v1.20.1): una persona hace una OUT. Cada caja es el FINAL de su trabajo: la OUT cuenta como persona
        desde que empieza la caja hasta que la cierra. Entre dos cajas de la misma OUT, si pasan PARADA_MIN minutos
        o menos, la persona sigue cogiendo (llenando la caja siguiente); si pasan mas, la OUT estaba parada (pico,
        faltante) y ese hueco no cuenta. La primera caja de cada tramo empieza antes de cerrarse: se le da el tiempo
        tipico de una caja de ese dia (mediana entre cajas). Con 5 min fijos (v1.19.4) se perdia el tiempo entre
        cajas (mediana ~7 min) y las u/h por persona salian infladas (Z-1111: 167 en vez de ~114).
        """
        marcas_por_out = {}
        for dt, quien in dia['marcas']:
            marcas_por_out.setdefault(quien, set()).add(dt)

        intervalos = []
        primera_caja = None
        if zonas:
            hueco_max = datetime.timedelta(minutes=PARADA_MIN)
            huecos = []
            for marcas in marcas_por_out.values():
                orden = sorted(marcas)
                for a, b in zip(orden, orden[1:]):
                    if b - a <= hueco_max:
                        huecos.append(b - a)
            huecos.sort()
            primera_caja = huecos and huecos[len(huecos) // 2] or datetime.timedelta(minutes=PERSONA_INACTIVA_MIN)
            for marcas in marcas_por_out.values():
                inicio = fin = None
                for dt in sorted(marcas):
                    if inicio is None:
                        inicio, fin = dt - primera_caja, dt
                    elif dt - fin <= hueco_max:
                        fin = dt
                    else:
                        intervalos.append((inicio, fin))
                        inicio, fin = dt - primera_caja, dt
                if inicio is not None:
                    intervalos.append((inicio, fin))
        else:
            margen = datetime.timedelta(minutes=PERSONA_INACTIVA_MIN)
            for marcas in marcas_por_out.values():
                inicio = fin = None
                for dt in sorted(marcas):
                    nuevo_fin = dt + margen
                    if inicio is None:
                        inicio, fin = dt, nuevo_fin
                    elif dt <= fin:
                        fin = max(fin, nuevo_fin)
                    else:
                        intervalos.append((inicio, fin))
                        inicio, fin = dt, nuevo_fin
                if inicio is not None:
                    intervalos.append((inicio, fin))

        hp = sum([(fin - inicio).total_seconds() for inicio, fin in intervalos]) / 3600.0
        eventos = []
        for inicio, fin in intervalos:
            eventos.append((inicio, 1))
            eventos.append((fin, -1))
        maximo = 0
        activas = 0
        # A la mateixa hora es processa primer el final: [08:00, 08:05) i [08:05, 08:10) no se solapen.
        for _dt, cambio in sorted(eventos, key=lambda x: (x[0], x[1])):
            activas += cambio
            maximo = max(maximo, activas)
        reloj = 0.0
        if dia['primera'] and dia['ultima']:
            reloj = (dia['ultima'] - dia['primera']).total_seconds() / 3600.0
        media = reloj > 0.05 and hp / reloj or 0
        if maximo:
            media = min(media, maximo)
        return {
            'hp': round(hp, 2), 'personas_max': maximo,
            'personas_media': round(media, 1),
            'horas_reloj': round(reloj, 2),
            'uds_hp': hp and int(round(leidas / hp)) or 0,
            'uds_persona': maximo and int(round(leidas / maximo)) or 0,
            's_ud': leidas and round(hp * 3600.0 / leidas, 1) or 0,
            'inactividad_min': PERSONA_INACTIVA_MIN,
            'zonas': bool(zonas),
            'hueco_max_min': PARADA_MIN,
            'primera_caja_min': primera_caja and round(primera_caja.total_seconds() / 60.0, 1) or 0,
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
            'z': f['z'], 'lote': f['lote'], 'caja': f['caja'], 'out': f['out'], 'tienda': f['tienda'], 'etq': f['etq'],
            'transportista': f['transportista'], 'etiqueta': f['etiqueta'], 'id': f['id'],
            'pedido': f['pedido'], 'u': f['u'], 'huecos': len(f['_huecos']), 'lin': lin or '-',
            'leido': f['leido'], 'est': est, 'ini': self._hora(f['_a']), 'fin': self._hora(fin_dt),
            'min': mins, 'cajas': len(f['_cajas']), 'bultos': f['_bultos'], '_a': f['_a'], '_b': f['_b'],
            'disp': f['disp'], 'falta': (est != 'hecha' or sin_validar) and falta or 0.0, 'faltas': f['faltas'],
            'sin_validar': sin_validar,
        }

    def _operarios(self, env, dominio, filas_por_id):
        """v1.18: quien coge cada OUT, con el modulo koroshi_operarios (si esta instalado; si no, nada).
        Solo codigos (OP1, OP2...), nunca nombres. Devuelve (por_picking, por_lote, resumen)."""
        if 'koroshi.operario.tarea' not in env.registry:
            return {}, {}, []
        ahora = fields.Datetime.now()
        tareas = env['koroshi.operario.tarea'].sudo().search(dominio, order='inicio asc')
        por_picking, por_lote, ops = {}, {}, {}
        for t in tareas:
            cod = codigo_op(t.employee_id)
            abierta = t.estado == 'curso'
            fin_real = None
            if abierta:
                # v1.18: el cron cierra cada 5 min; si la OUT o la agrupacion ya esta validada, aqui ya cuenta
                # como acabada (hora de validacion), sin esperar al cron
                pickings = t._pickings()
                if pickings and t._validado(pickings):
                    abierta = False
                    fin_real = max(t._hora_validacion(pickings), t.inicio)
            # agrupacion: todas las OUT del lote; OUT suelta: esa OUT
            if t.tipo == 'agrupacion' and t.batch_id:
                destino = por_lote.setdefault(t.batch_id.name, {'ops': [], 'ahora': []})
            elif t.picking_id:
                destino = por_picking.setdefault(t.picking_id.id, {'ops': [], 'ahora': []})
            else:
                destino = None
            if destino is not None:
                if cod not in destino['ops']:
                    destino['ops'].append(cod)
                if abierta and cod not in destino['ahora']:
                    destino['ahora'].append(cod)
            o = ops.setdefault(cod, {'op': cod, 'tareas': 0, 'acabadas': 0, 'dejadas': 0, 'uds': 0.0,
                                     'min': 0.0, 'ahora': '', 'desde': '', 'ini': None, 'ult': None})
            o['tareas'] += 1
            if t.estado == 'acabada' or fin_real:
                o['acabadas'] += 1
            elif t.estado in ('dejada', 'sin_cerrar'):
                o['dejadas'] += 1
            if t.estado == 'curso':
                # uds leidas hasta ahora (OUT suelta o agrupacion entera)
                # (operarios v2.5: a dos, cada uno solo lo suyo; con versiones anteriores, como antes)
                if hasattr(t, '_uds_hasta_ahora'):
                    o['uds'] += t._uds_hasta_ahora()
                else:
                    o['uds'] += max(t._uds_leidas(t._pickings()) - (t.uds_inicio or 0.0), 0.0)
                hasta = fin_real or ahora
                o['min'] += max((hasta - t.inicio).total_seconds() / 60.0, 0.0) if t.inicio else 0.0
                if abierta:
                    ref = t.batch_id.name if t.tipo == 'agrupacion' else (t.picking_id.name or '')
                    o['ahora'] = (ref or t.referencia or '').replace('EFFEC/OUT/', '')
                    o['desde'] = self._hora(t.inicio)
            else:
                o['uds'] += t.uds or 0.0
                o['min'] += t.minutos or 0.0
            if t.inicio and (not o['ini'] or t.inicio < o['ini']):
                o['ini'] = t.inicio
        resumen = []
        for cod in sorted(ops, key=lambda c: (int(re.sub(r'\D', '', c) or 0), c)):
            o = ops[cod]
            o['uh'] = o['min'] > 1 and int(round(o['uds'] * 60.0 / o['min'])) or 0
            o['uds'] = int(round(o['uds']))
            o['min'] = int(round(o['min']))
            o['ini'] = self._hora(o['ini'])
            o.pop('ult')
            resumen.append(o)
        return por_picking, por_lote, resumen

    def _poner_ops(self, D, por_picking, por_lote):
        for d in D:
            a = por_picking.get(d['id']) or {'ops': [], 'ahora': []}
            b = por_lote.get(d['lote']) or {'ops': [], 'ahora': []}
            d['ops'] = a['ops'] + [x for x in b['ops'] if x not in a['ops']]
            d['ops_ahora'] = a['ahora'] + [x for x in b['ahora'] if x not in a['ahora']]

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
            filas, por_hora, dia_z, por_hora_out = self._filas(env, picks, prefijo, z_ini, z_fin)
            D = []
            for f in filas.values():
                d = self._fila(f)
                d.pop('_a')
                d.pop('_b')
                if d['est'] == 'sinstock':      # v1.5: pedidos pendientes en espera: no son de esta agrupacion
                    continue
                D.append(d)
            D.sort(key=lambda d: d['out'])
            # v1.18: operarios (codigos) de las agrupaciones de este prefijo
            pp, pl, res['operarios'] = self._operarios(env, [('batch_id.name', '=like', prefijo + '%')], filas)
            self._poner_ops(D, pp, pl)
            res['D'] = D
            res['pedidos'] = len(set([d['pedido'] for d in D]))
            res['personas'] = self._personas(dia_z, sum([x[1] for x in por_hora.items()]), zonas=True)
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
        filas, por_hora, dia_t, por_hora_out = self._filas(env, picks, None, ini, fin)
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
        # v1.18: operarios (codigos) del dia
        pp, pl, res['operarios'] = self._operarios(env, [('dia', '=', dia)], filas)
        self._poner_ops(D, pp, pl)
        res['D'] = D
        res['pedidos'] = len(set([d['pedido'] for d in D]))
        res['equipo'] = equipo
        res['personas'] = self._personas(dia_t, leidas_dia)
        res['por_hora'] = [[h, int(por_hora[h])] for h in sorted(por_hora)]
        res['por_hora_out'] = [[h, list(por_hora_out[h].values())] for h in sorted(por_hora_out)]
        return res
