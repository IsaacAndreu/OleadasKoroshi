#!/usr/bin/env bash
# =============================================================================
# Instalar / actualizar el modulo KOROSHI Monitor zonas (koroshi_monitor) en Odoo 13.
# AUTOCONTENIDO: el modulo va dentro de este script (no hace falta el zip).
#
# Uso (en el servidor de Odoo, como root o con sudo):
#   sudo bash crear_koroshi_monitor_2026-10-22_1220_v1.1.sh
#
# Que hace:
#   1. Busca el Odoo que esta corriendo: su fichero de configuracion, el addons_path,
#      el usuario con el que corre y el servicio (systemd).
#   2. Elige la carpeta de modulos propios (la del addons_path que no es la de Odoo).
#   3. Si ya hay un koroshi_monitor, lo copia a una copia de seguridad con fecha.
#   4. Crea los ficheros del modulo en esa carpeta y le pone el dueno del usuario de Odoo.
#   5. Reinicia el servicio de Odoo.
#   6. Instala (o actualiza, si ya estaba) el modulo en la base de datos.
#   Antes de cambiar nada ensena lo que ha encontrado y pide confirmacion.
#
# Variables que se pueden forzar si la deteccion no acierta:
#   ODOO_CONF=/etc/odoo/odoo.conf  ADDONS_DIR=/opt/nath-erp/addons_propios
#   ODOO_SERVICE=odoo  ODOO_USER=odoo  ODOO_BIN=/opt/nath-erp/odoo13/odoo-bin
#   ODOO_PYTHON=/opt/nath-erp/venv/bin/python  ODOO_DB=NATH_PRODUCTION
# =============================================================================
set -euo pipefail

MODULO=koroshi_monitor
ODOO_DB="${ODOO_DB:-NATH_PRODUCTION}"
FECHA=$(date +%Y-%m-%d_%H%M)

rojo() { printf '\033[31m%s\033[0m\n' "$*"; }
verde() { printf '\033[32m%s\033[0m\n' "$*"; }
crear_modulo() {
    # Escribe los ficheros del modulo en la carpeta $1
    local D="$1"
    mkdir -p "$D/koroshi_monitor"
    cat > "$D/koroshi_monitor/README.md" <<'FIN_KOROSHI_FICHERO'
# KOROSHI Monitor zonas (Odoo 13)

Pantalla en directo de cómo van las agrupaciones de picking por zonas (Z-ddmm-D1…D5, ZX).
Es la misma página que `bin/versiones/estado-OUT-agrupaciones-Z-*.html`, pero dentro de Odoo
y con datos al momento. **Solo lee: no cambia nada.**

- Menú: **Inventario › Operaciones › Monitor zonas** (usuarios de Inventario).
- Se refresca sola cada minuto; botón **Refrescar** para hacerlo al momento.
- Desplegable con las últimas agrupaciones (Z-2210, Z-2110…). Por defecto, la última.
- Se acuerda de qué zonas has abierto o cerrado en «OUT por zona» al refrescar.
- **v1.1:** en el desplegable salen también **«Tiendas <día>»** (hoy y 2 días antes) para cuando se coge
  **una OUT por pedido** sin zonas: % hecho, **ritmo del equipo (u/h)**, **hora prevista de fin**,
  unidades leídas por hora y cada OUT con lo que ha tardado y su ritmo. Si hoy hay agrupaciones de zona
  Z-ddmm, por defecto se abre esa; si no, «Tiendas (hoy)».

## Instalar

1. Copiar la carpeta `koroshi_monitor` (o descomprimir `bin/koroshi_monitor_2026-10-22_0825_v1.zip`)
   en una carpeta de módulos del servidor que esté en el `addons_path`
   (la de los módulos propios, junto a `/opt/nath-erp/odoo13`).
2. Reiniciar Odoo (hace falta para que lea el controlador Python).
3. En Odoo, modo desarrollador: **Aplicaciones › Actualizar lista de aplicaciones**.
4. Buscar **KOROSHI Monitor zonas** (quitar el filtro «Aplicaciones») e **Instalar**.
5. Abrir **Inventario › Operaciones › Monitor zonas**.

Para actualizar una versión nueva: copiar encima, reiniciar Odoo y en el módulo pulsar **Actualizar**.

## Qué calcula

Para cada OUT de las agrupaciones `<prefijo>*` de la empresa 8 (EFFECTIVE LOGISTICS):

| Dato | De dónde sale |
|---|---|
| Uds | Suma de `product_uom_qty` de los movimientos no cancelados |
| Leído | Suma de `qty_done` de las líneas |
| Estado | Hecha = OUT validada · Cogiéndose = algo leído · Sin empezar = nada leído |
| Huecos | Ubicaciones distintas de las líneas (`27009 - L59 P14 C1`) |
| Lineales | `L` mínimo–máximo de esas ubicaciones; en ZX, `MU-xx` |
| Empieza / última | Primera y última línea leída (`write_date`), o la hora de validación si está hecha |
| Caja | Número de caja de tienda de la nota de la OUT («CAJA nn») |

Ficheros: `controllers/main.py` (datos, ruta `/koroshi_monitor/datos`), `static/src/js/monitor.js`
(pantalla), `static/src/css/monitor.css`, `views/menu.xml`, `views/assets.xml`.
FIN_KOROSHI_FICHERO
    mkdir -p "$D/koroshi_monitor"
    cat > "$D/koroshi_monitor/__init__.py" <<'FIN_KOROSHI_FICHERO'
# -*- coding: utf-8 -*-
from . import controllers
FIN_KOROSHI_FICHERO
    mkdir -p "$D/koroshi_monitor"
    cat > "$D/koroshi_monitor/__manifest__.py" <<'FIN_KOROSHI_FICHERO'
# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Monitor zonas',
    'summary': 'Pantalla en directo de como van las agrupaciones de picking por zonas (Z-ddmm-D1..D5, ZX)',
    'description': """
Monitor de las agrupaciones por zonas de KOROSHI.

Menu Inventario > Operaciones > Monitor zonas. Ensena, para la agrupacion elegida
(por defecto la ultima Z-...): unidades leidas y pendientes por zona, OUT hechas /
cogiendose / sin empezar, el cuadro de cada tienda en cada zona y la lista de OUT
por zona con lineales, huecos y horas. Se refresca solo cada minuto.

v1.1: tambien modo "Tiendas <dia>" para cuando se coge una OUT por pedido (sin zonas):
ritmo del equipo, hora prevista de fin, uds por hora y lo que ha tardado cada OUT.

Solo lee: no cambia nada en Odoo.
""",
    'version': '13.0.1.1.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'stock', 'stock_picking_batch'],
    'data': [
        'views/assets.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
}
FIN_KOROSHI_FICHERO
    mkdir -p "$D/koroshi_monitor/controllers"
    cat > "$D/koroshi_monitor/controllers/__init__.py" <<'FIN_KOROSHI_FICHERO'
# -*- coding: utf-8 -*-
from . import main
FIN_KOROSHI_FICHERO
    mkdir -p "$D/koroshi_monitor/controllers"
    cat > "$D/koroshi_monitor/controllers/main.py" <<'FIN_KOROSHI_FICHERO'
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

RE_LINEAL = re.compile(r' L(\d+) ')
RE_MU = re.compile(r'^(MU-\d+)')


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
                'tienda': nombre.split(', ')[-1],
                'pedido': p.origin or '',
                'u': 0.0, 'leido': 0.0,
                '_huecos': set(), '_l': [], '_mu': set(),
                '_a': None, '_b': None,
                '_estado': p.state, '_done': p.date_done,
            }

        movs = env['stock.move'].sudo().search_read([('picking_id', 'in', picks.ids), ('state', '!=', 'cancel')],
                                                    ['picking_id', 'product_uom_qty'])
        for m in movs:
            filas[m['picking_id'][0]]['u'] += m['product_uom_qty']

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
        dia = {'primera': None, 'ultima': None}
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
        return filas, por_hora, dia

    def _fila(self, f):
        if f['_estado'] == 'done':
            est = 'hecha'
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
            'min': mins, '_a': f['_a'], '_b': f['_b'],
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
        ahora = fields.Datetime.now()
        res = {'prefijos': prefijos, 'etiquetas': etiquetas, 'prefijo': prefijo, 'D': [], 'pedidos': 0,
               'hora': self._hora(ahora), 'modo': prefijo.startswith('TIENDAS:') and 'tiendas' or 'zonas'}

        if res['modo'] == 'zonas':
            picks = env['stock.picking'].sudo().search([('batch_id.name', '=like', prefijo + '%'),
                                                        ('company_id', '=', COMPANY_ID)])
            filas, por_hora, dia_z = self._filas(env, picks, prefijo)
            D = []
            for f in filas.values():
                d = self._fila(f)
                d.pop('_a')
                d.pop('_b')
                D.append(d)
            D.sort(key=lambda d: d['out'])
            res['D'] = D
            res['pedidos'] = len(set([d['pedido'] for d in D]))
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
        for f in filas.values():
            d = self._fila(f)
            d['uh'] = d['min'] and round(d['leido'] * 60.0 / d['min']) or 0
            d.pop('_a')
            d.pop('_b')
            D.append(d)
        rango = {'curso': 0, 'pend': 1, 'hecha': 2}
        D.sort(key=lambda d: (rango[d['est']], d['est'] == 'hecha' and d['fin'] and -int(d['fin'].replace(':', '')) or 0,
                              d['out']))
        total = sum([d['u'] for d in D])
        leidas = sum([d['leido'] for d in D])
        pendientes = max(total - leidas, 0.0)
        leidas_dia = sum([x[1] for x in por_hora.items()])
        equipo = {'inicio': self._hora(primera), 'ultima': self._hora(ultima), 'uh': 0, 'fin_previsto': ''}
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
        res['por_hora'] = [[h, int(por_hora[h])] for h in sorted(por_hora)]
        return res
FIN_KOROSHI_FICHERO
    mkdir -p "$D/koroshi_monitor/static/src/css"
    cat > "$D/koroshi_monitor/static/src/css/monitor.css" <<'FIN_KOROSHI_FICHERO'
/* KOROSHI Monitor zonas: los mismos estilos que estado-OUT-agrupaciones-Z-*.html, solo dentro de .o_koroshi_monitor */
.o_koroshi_monitor {
    --km-bg: #f7f6f2; --km-card: #fff; --km-ink: #1d1d1b; --km-muted: #6b6a65; --km-line: #dedcd4; --km-bar: #e9e7e0;
    --km-ok: #2e9a52; --km-cur: #d08a00; --km-pend: #b9b6ad;
    --km-z1: #2f7d4f; --km-z2: #1f5fbf; --km-z3: #b5562a; --km-z4: #7a4bb0; --km-z5: #b08a12; --km-zx: #6b6a65;
    background: var(--km-bg); color: var(--km-ink); font-size: 15px; line-height: 1.45;
    height: 100%; overflow: auto;
}
.o_koroshi_monitor main { max-width: 1150px; margin: 0 auto; padding: 24px 16px 60px; }
.o_koroshi_monitor h1 { font-size: 26px; margin: 0; font-weight: 700; }
.o_koroshi_monitor h2 { font-size: 19px; margin: 30px 0 10px; font-weight: 700; }
.o_koroshi_monitor .km-cab { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 16px; justify-content: space-between; margin-bottom: 4px; }
.o_koroshi_monitor .km-ctl { display: flex; gap: 8px; align-items: center; }
.o_koroshi_monitor .km-ctl select { padding: 4px 8px; border: 1px solid var(--km-line); border-radius: 6px; background: var(--km-card); }
.o_koroshi_monitor .km-sub { color: var(--km-muted); margin: 0 0 18px; }
.o_koroshi_monitor .km-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; }
.o_koroshi_monitor .km-card { background: var(--km-card); border: 1px solid var(--km-line); border-radius: 10px; padding: 14px 16px; margin-bottom: 10px; }
.o_koroshi_monitor .km-kpi b { display: block; font-size: 26px; }
.o_koroshi_monitor .km-kpi span { color: var(--km-muted); font-size: 13px; }
.o_koroshi_monitor .km-z { display: inline-block; min-width: 34px; text-align: center; padding: 2px 8px; border-radius: 6px; color: #fff; font-weight: 800; }
.o_koroshi_monitor .km-zona { display: grid; grid-template-columns: 60px 1fr; gap: 12px; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--km-line); }
.o_koroshi_monitor .km-zona:last-child { border-bottom: 0; }
.o_koroshi_monitor .km-barra { height: 16px; background: var(--km-bar); border-radius: 8px; overflow: hidden; margin: 4px 0; display: flex; }
.o_koroshi_monitor .km-barra i { display: block; height: 100%; }
.o_koroshi_monitor .km-fila { display: flex; flex-wrap: wrap; gap: 4px 16px; font-size: 13.5px; color: var(--km-muted); }
.o_koroshi_monitor .km-fila b { color: var(--km-ink); }
.o_koroshi_monitor .km-ley { display: flex; gap: 16px; flex-wrap: wrap; font-size: 13px; color: var(--km-muted); margin: 6px 0 10px; }
.o_koroshi_monitor .km-ley i { display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 5px; vertical-align: -1px; }
.o_koroshi_monitor .km-scroll { overflow-x: auto; }
.o_koroshi_monitor table { border-collapse: collapse; width: 100%; font-size: 13.5px; }
.o_koroshi_monitor th, .o_koroshi_monitor td { padding: 6px 7px; border-bottom: 1px solid var(--km-line); text-align: left; white-space: nowrap; }
.o_koroshi_monitor th { color: var(--km-muted); font-size: 12px; font-weight: 600; }
.o_koroshi_monitor td.r, .o_koroshi_monitor th.r { text-align: right; }
.o_koroshi_monitor tr.km-tot td { font-weight: 700; }
.o_koroshi_monitor .m { font-family: ui-monospace, Consolas, monospace; font-size: 12.5px; }
.o_koroshi_monitor .km-cel { display: inline-block; min-width: 74px; padding: 3px 6px; border-radius: 5px; font-size: 12px; text-align: center; }
.o_koroshi_monitor .km-hecha { background: var(--km-ok); color: #fff; }
.o_koroshi_monitor .km-curso { background: var(--km-cur); color: #fff; }
.o_koroshi_monitor .km-pend { background: var(--km-bar); color: var(--km-muted); }
.o_koroshi_monitor .km-mini { width: 90px; height: 8px; background: var(--km-bar); border-radius: 4px; overflow: hidden; display: inline-block; vertical-align: middle; margin-right: 6px; }
.o_koroshi_monitor .km-mini i { display: block; height: 100%; }
.o_koroshi_monitor details { margin: 0; }
.o_koroshi_monitor details summary { cursor: pointer; font-weight: 700; padding: 6px 0; }
.o_koroshi_monitor .km-nota { color: var(--km-muted); font-size: 13px; }
.o_koroshi_monitor .km-hora { display: grid; grid-template-columns: 44px 1fr 60px; gap: 10px; align-items: center; font-variant-numeric: tabular-nums; }
.o_koroshi_monitor .km-hora .km-barra { margin: 3px 0; }
.o_koroshi_monitor .km-hora b { text-align: right; }
.o_koroshi_monitor td small { color: var(--km-muted); font-family: system-ui, sans-serif; }
FIN_KOROSHI_FICHERO
    mkdir -p "$D/koroshi_monitor/static/src/js"
    cat > "$D/koroshi_monitor/static/src/js/monitor.js" <<'FIN_KOROSHI_FICHERO'
odoo.define('koroshi_monitor.monitor', function (require) {
'use strict';
// KOROSHI Monitor zonas: misma pantalla que estado-OUT-agrupaciones-Z-*.html, con datos en
// directo de /koroshi_monitor/datos. Se refresca sola cada REFRESCO ms. Solo lee.

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');

var REFRESCO = 60000;
var ZS = ['D1', 'D2', 'D3', 'D4', 'D5', 'ZX'];
var COL = {D1: 'var(--km-z1)', D2: 'var(--km-z2)', D3: 'var(--km-z3)', D4: 'var(--km-z4)', D5: 'var(--km-z5)', ZX: 'var(--km-zx)'};
var EST = {hecha: 'Hecha', curso: 'Cogiéndose', pend: 'Sin empezar'};

function e(s) { return _.escape(s === undefined || s === null ? '' : String(s)); }
function n(x) { return Math.round(x).toLocaleString('es-ES'); }
function zt(z) { return '<span class="km-z" style="background:' + (COL[z] || 'var(--km-zx)') + '">' + e(z) + '</span>'; }

var Monitor = AbstractAction.extend({
    hasControlPanel: false,
    events: {
        'change .km-prefijo': '_onPrefijo',
        'click .km-refrescar': '_cargar',
        'click details > summary': '_onToggle',
    },

    init: function () {
        this._super.apply(this, arguments);
        this.prefijo = false;
        this.abiertas = {};
    },

    start: function () {
        var self = this;
        this.$el.addClass('o_koroshi_monitor');
        return this._super.apply(this, arguments).then(function () {
            self.$el.html('<main><p class="km-sub">Cargando…</p></main>');
            self._cargar();
            self.timer = setInterval(function () { self._cargar(); }, REFRESCO);
        });
    },

    destroy: function () {
        clearInterval(this.timer);
        this._super.apply(this, arguments);
    },

    _onPrefijo: function (ev) {
        this.prefijo = ev.target.value;
        this.abiertas = {};
        this._cargar();
    },

    _onToggle: function (ev) {
        // El clic en el titulo abre/cierra: se guarda como quedara para el siguiente refresco
        var det = ev.currentTarget.parentNode;
        var z = det.getAttribute('data-z');
        if (z) { this.abiertas[z] = !det.open; }
    },

    _cargar: function () {
        var self = this;
        return this._rpc({route: '/koroshi_monitor/datos', params: {prefijo: this.prefijo}}).then(function (r) {
            self.prefijo = r.prefijo;
            var scroll = self.el.scrollTop;
            self._pintar(r);
            self.el.scrollTop = scroll;
        });
    },

    _selector: function (r) {
        var et = r.etiquetas || {};
        return '<div class="km-ctl"><select class="km-prefijo">' + (r.prefijos || []).map(function (p) {
            return '<option value="' + e(p) + '"' + (p === r.prefijo ? ' selected' : '') + '>' + e(et[p] || p.replace(/-$/, '')) + '</option>';
        }).join('') + '</select><button class="btn btn-secondary km-refrescar">Refrescar</button></div>';
    },

    _pintar: function (r) {
        if (r.modo === 'tiendas') {
            return this._pintarTiendas(r);
        }
        var self = this;
        var D = r.D || [];
        var T = {u: 0, l: 0, h: 0, c: 0, p: 0};
        var Z = {};
        ZS.forEach(function (z) { Z[z] = {u: 0, l: 0, h: 0, c: 0, p: 0, uh: 0, n: 0}; });
        D.forEach(function (o) {
            if (!Z[o.z]) { Z[o.z] = {u: 0, l: 0, h: 0, c: 0, p: 0, uh: 0, n: 0}; ZS.push(o.z); }
            var z = Z[o.z], k = o.est === 'hecha' ? 'h' : o.est === 'curso' ? 'c' : 'p';
            z.n++; z.u += o.u; z.l += o.leido; z[k]++;
            if (o.est === 'hecha') { z.uh += o.u; }
            T.u += o.u; T.l += o.leido; T[k]++;
        });
        var zonas = ZS.filter(function (z) { return Z[z].n; });
        var pctT = T.u ? Math.round(100 * T.l / T.u) : 0;

        var h = '<main>';
        h += '<div class="km-cab"><h1>Cómo van las agrupaciones ' + e((r.prefijo || '').replace(/-$/, '')) + '</h1>';
        h += this._selector(r) + '</div>';
        h += '<p class="km-sub">' + r.pedidos + ' pedidos de tienda partidos por zona (' + D.length + ' OUT). Datos de Odoo a las <b>' + e(r.hora) +
            '</b>, se refresca solo cada minuto. Unidades reales (movimientos), no las columnas «Demanded/Reserved» de la lista de Odoo, que están mal en las OUT partidas.</p>';
        if (!D.length) {
            this.$el.html(h + '<p>No hay OUT en esta agrupación.</p></main>');
            return;
        }

        h += '<div class="km-grid">' + [
            [pctT + ' %', n(T.l) + ' de ' + n(T.u) + ' u leídas'],
            [T.h + ' / ' + D.length, 'OUT hechas'],
            [T.c, 'OUT cogiéndose ahora'],
            [T.p, 'OUT sin empezar'],
        ].map(function (k) { return '<div class="km-card km-kpi"><b>' + k[0] + '</b><span>' + k[1] + '</span></div>'; }).join('') + '</div>';

        // Totales
        h += '<h2>Totales: lo que llevan y lo que les falta</h2><div class="km-card km-scroll"><table><thead><tr><th>Zona</th><th class="r">Uds total</th><th class="r">Uds cogidas</th><th class="r">Uds que faltan</th><th class="r">%</th><th class="r">OUT total</th><th class="r">OUT hechas</th><th class="r">OUT cogiéndose</th><th class="r">OUT que faltan</th></tr></thead><tbody>';
        zonas.forEach(function (zn) {
            var z = Z[zn];
            h += '<tr><td>' + zt(zn) + '</td><td class="r">' + n(z.u) + '</td><td class="r">' + n(z.l) + '</td><td class="r"><b>' + n(z.u - z.l) + '</b></td><td class="r">' + (z.u ? Math.round(100 * z.l / z.u) : 0) + ' %</td><td class="r">' + z.n + '</td><td class="r">' + z.h + '</td><td class="r">' + z.c + '</td><td class="r"><b>' + (z.c + z.p) + '</b></td></tr>';
        });
        h += '<tr class="km-tot"><td>Total</td><td class="r">' + n(T.u) + '</td><td class="r">' + n(T.l) + '</td><td class="r">' + n(T.u - T.l) + '</td><td class="r">' + pctT + ' %</td><td class="r">' + D.length + '</td><td class="r">' + T.h + '</td><td class="r">' + T.c + '</td><td class="r">' + (T.c + T.p) + '</td></tr></tbody></table></div>';

        // Avance por zona
        h += '<h2>Avance por zona</h2><div class="km-ley"><span><i style="background:var(--km-ok)"></i>OUT hecha (validada)</span><span><i style="background:var(--km-cur)"></i>cogiéndose</span><span><i style="background:var(--km-pend)"></i>sin empezar</span></div><div class="km-card">';
        zonas.forEach(function (zn) {
            var z = Z[zn], pct = z.u ? Math.round(100 * z.l / z.u) : 0, ph = z.u ? 100 * z.uh / z.u : 0, pc = z.u ? Math.max(0, 100 * (z.l - z.uh) / z.u) : 0;
            h += '<div class="km-zona">' + zt(zn) + '<div><div class="km-fila"><span><b>' + n(z.l) + ' de ' + n(z.u) + ' u</b> (' + pct + ' %)</span><span>' + z.h + ' hechas · ' + z.c + ' cogiéndose · ' + z.p + ' sin empezar (de ' + z.n + ' OUT)</span></div>' +
                '<div class="km-barra"><i style="width:' + ph + '%;background:var(--km-ok)"></i><i style="width:' + pc + '%;background:var(--km-cur)"></i></div></div></div>';
        });
        h += '</div>';

        // Matriz tienda x zona
        var P = {}, orden = [];
        D.forEach(function (o) {
            if (!P[o.pedido]) { P[o.pedido] = {caja: o.caja, tienda: o.tienda, z: {}}; orden.push(o.pedido); }
            P[o.pedido].z[o.z] = o;
        });
        orden.sort(function (a, b) { return (parseInt(P[a].caja, 10) || 0) - (parseInt(P[b].caja, 10) || 0); });
        h += '<h2>Cada tienda en cada zona</h2><p class="km-nota">Cada casilla es una OUT: número de OUT y unidades leídas / total. Vacío = la tienda no tiene nada en esa zona.</p>';
        h += '<div class="km-card km-scroll"><table><thead><tr><th>Caja</th><th>Tienda</th><th>Pedido</th>' + zonas.map(function (z) { return '<th>' + zt(z) + '</th>'; }).join('') + '<th class="r">Leído</th></tr></thead><tbody>';
        orden.forEach(function (k) {
            var p = P[k], u = 0, l = 0;
            h += '<tr><td><b>' + e(p.caja) + '</b></td><td>' + e(p.tienda) + '</td><td class="m">' + e(k) + '</td>';
            zonas.forEach(function (z) {
                var o = p.z[z];
                if (!o) { h += '<td></td>'; return; }
                u += o.u; l += o.leido;
                h += '<td><span class="km-cel km-' + o.est + '" title="' + EST[o.est] + '">' + e(o.out) + '<br>' + n(o.leido) + '/' + n(o.u) + '</span></td>';
            });
            h += '<td class="r">' + n(l) + '/' + n(u) + '</td></tr>';
        });
        h += '</tbody></table></div>';

        // Listas por zona
        h += '<h2>OUT por zona</h2>';
        var rank = {curso: 0, pend: 1, hecha: 2};
        zonas.forEach(function (zn) {
            var L = D.filter(function (o) { return o.z === zn; });
            L.sort(function (a, b) { return rank[a.est] - rank[b.est] || (parseInt(a.caja, 10) || 0) - (parseInt(b.caja, 10) || 0); });
            var z = Z[zn];
            var abierta = zn in self.abiertas ? self.abiertas[zn] : (z.c || z.p);
            h += '<div class="km-card"><details data-z="' + e(zn) + '"' + (abierta ? ' open' : '') + '><summary>' + zt(zn) + ' ' + e(r.prefijo + zn) + ' · ' + n(z.l) + '/' + n(z.u) + ' u · ' + z.h + ' hechas, ' + z.c + ' cogiéndose, ' + z.p + ' sin empezar</summary>';
            h += '<div class="km-scroll"><table><thead><tr><th>Estado</th><th>Caja</th><th>OUT</th><th>Tienda</th><th>Pedido</th><th>Lineales</th><th class="r">Huecos</th><th>Leído</th><th>Empieza</th><th>Última / validada</th></tr></thead><tbody>';
            L.forEach(function (o) {
                var pct = o.u ? 100 * o.leido / o.u : 0, c = o.est === 'hecha' ? 'var(--km-ok)' : 'var(--km-cur)';
                h += '<tr><td><span class="km-cel km-' + o.est + '">' + EST[o.est] + '</span></td><td><b>' + e(o.caja) + '</b></td><td class="m">' + e(o.out) + '</td><td>' + e(o.tienda) + '</td><td class="m">' + e(o.pedido) + '</td><td>' + e(o.lin) + '</td><td class="r">' + o.huecos + '</td>' +
                    '<td><span class="km-mini"><i style="width:' + pct + '%;background:' + c + '"></i></span>' + n(o.leido) + '/' + n(o.u) + '</td><td>' + (o.est === 'hecha' ? '' : e(o.ini)) + '</td><td>' + e(o.fin) + '</td></tr>';
            });
            h += '</tbody></table></div></details></div>';
        });
        h += '</main>';
        this.$el.html(h);
    },
});

// Modo tiendas (v1.1): una OUT por pedido, sin zonas. Ritmo del equipo, hora prevista de fin,
// uds por hora y cada OUT con lo que ha tardado.
Monitor.include({
    _pintarTiendas: function (r) {
        var D = r.D || [];
        var eq = r.equipo || {};
        var T = {u: 0, l: 0, h: 0, c: 0, p: 0, uh: 0};
        D.forEach(function (o) {
            T.u += o.u; T.l += o.leido;
            T[o.est === 'hecha' ? 'h' : o.est === 'curso' ? 'c' : 'p']++;
        });
        var pct = T.u ? Math.round(100 * T.l / T.u) : 0;
        var et = r.etiquetas || {};
        var h = '<main>';
        h += '<div class="km-cab"><h1>Cómo van los pedidos de tienda · ' + e((et[r.prefijo] || '').replace('Tiendas ', '')) + '</h1>' + this._selector(r) + '</div>';
        h += '<p class="km-sub">' + r.pedidos + ' pedidos de tienda (' + D.length + ' OUT), una OUT por pedido. Datos de Odoo a las <b>' + e(r.hora) +
            '</b>, se refresca solo cada minuto. El ritmo es del equipo entero (todas las PDA usan el mismo usuario).</p>';
        if (!D.length) {
            this.$el.html(h + '<p>No hay OUT de tiendas ese día.</p></main>');
            return;
        }
        h += '<div class="km-grid">' + [
            [pct + ' %', n(T.l) + ' de ' + n(T.u) + ' u leídas'],
            [n(eq.uh || 0) + ' u/h', 'ritmo del equipo' + (eq.inicio ? ' (desde las ' + e(eq.inicio) + ')' : '')],
            [eq.fin_previsto ? e(eq.fin_previsto) : (T.u && T.l >= T.u ? 'hecho' : '–'), eq.fin_previsto ? 'acaba previsto a este ritmo' : (eq.ultima ? 'última lectura ' + e(eq.ultima) : 'hora prevista de fin')],
            [T.h + ' / ' + D.length, 'OUT hechas · ' + T.c + ' cogiéndose · ' + T.p + ' sin empezar'],
        ].map(function (k) { return '<div class="km-card km-kpi"><b>' + k[0] + '</b><span>' + k[1] + '</span></div>'; }).join('') + '</div>';

        // Uds leidas por hora
        var ph = r.por_hora || [];
        var max = 1;
        ph.forEach(function (x) { if (x[1] > max) { max = x[1]; } });
        h += '<h2>Unidades leídas por hora</h2><div class="km-card">';
        if (!ph.length) {
            h += '<p class="km-nota">Todavía no hay lecturas.</p>';
        }
        ph.forEach(function (x) {
            h += '<div class="km-hora"><span>' + (x[0] < 10 ? '0' : '') + x[0] + 'h</span><span class="km-barra"><i style="width:' + (100 * x[1] / max) +
                '%;background:var(--km-cur)"></i></span><b>' + n(x[1]) + '</b></div>';
        });
        h += '</div>';

        // Lista de OUT
        h += '<h2>OUT de tienda</h2><div class="km-card km-scroll"><table><thead><tr><th>Estado</th><th>Tienda</th><th>Pedido</th><th>OUT</th><th>Leído</th><th class="r">Huecos</th><th>Lineales</th><th>Empieza</th><th>Última / validada</th><th class="r">Min</th><th class="r">u/h</th></tr></thead><tbody>';
        D.forEach(function (o) {
            var p = o.u ? 100 * o.leido / o.u : 0, c = o.est === 'hecha' ? 'var(--km-ok)' : 'var(--km-cur)';
            h += '<tr><td><span class="km-cel km-' + o.est + '">' + EST[o.est] + '</span></td><td>' + e(o.tienda) + '</td><td class="m">' + e(o.pedido) + '</td><td class="m">' + e(o.out) +
                (o.lote ? '<br><small>' + e(o.lote) + '</small>' : '') + '</td>' +
                '<td><span class="km-mini"><i style="width:' + p + '%;background:' + c + '"></i></span>' + n(o.leido) + '/' + n(o.u) + '</td><td class="r">' + o.huecos + '</td><td>' + e(o.lin) +
                '</td><td>' + e(o.ini) + '</td><td>' + e(o.fin) + '</td><td class="r">' + (o.min || '') + '</td><td class="r">' + (o.uh || '') + '</td></tr>';
        });
        h += '</tbody></table></div></main>';
        this.$el.html(h);
    },
});

core.action_registry.add('koroshi_monitor', Monitor);
return Monitor;
});
FIN_KOROSHI_FICHERO
    mkdir -p "$D/koroshi_monitor/views"
    cat > "$D/koroshi_monitor/views/assets.xml" <<'FIN_KOROSHI_FICHERO'
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <template id="assets_backend" name="KOROSHI Monitor zonas assets" inherit_id="web.assets_backend">
        <xpath expr="." position="inside">
            <link rel="stylesheet" type="text/css" href="/koroshi_monitor/static/src/css/monitor.css"/>
            <script type="text/javascript" src="/koroshi_monitor/static/src/js/monitor.js"/>
        </xpath>
    </template>
</odoo>
FIN_KOROSHI_FICHERO
    mkdir -p "$D/koroshi_monitor/views"
    cat > "$D/koroshi_monitor/views/menu.xml" <<'FIN_KOROSHI_FICHERO'
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="action_koroshi_monitor" model="ir.actions.client">
        <field name="name">Monitor zonas KOROSHI</field>
        <field name="tag">koroshi_monitor</field>
    </record>

    <menuitem id="menu_koroshi_monitor"
              name="Monitor zonas"
              parent="stock.menu_stock_warehouse_mgmt"
              action="action_koroshi_monitor"
              sequence="99"
              groups="stock.group_stock_user"/>
</odoo>
FIN_KOROSHI_FICHERO
}

paso() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

if [ "$(id -u)" -ne 0 ]; then
    rojo "Hay que ejecutarlo con sudo (para copiar en la carpeta de Odoo y reiniciar el servicio)."
    exit 1
fi

# ---------------------------------------------------------------- 1. Detectar
paso "1. Buscando el Odoo que esta corriendo"
PROC=$(ps -eo user:32,args | grep -E 'odoo-bin|openerp-server|odoo ' | grep -v grep | head -1 || true)
if [ -n "$PROC" ]; then
    echo "   Proceso: $PROC"
    ODOO_USER="${ODOO_USER:-$(echo "$PROC" | awk '{print $1}')}"
    if [ -z "${ODOO_CONF:-}" ]; then
        ODOO_CONF=$(echo "$PROC" | grep -oE '(-c|--config)[ =][^ ]+' | head -1 | sed -E 's/^(-c|--config)[ =]//' || true)
    fi
    if [ -z "${ODOO_BIN:-}" ]; then
        ODOO_BIN=$(echo "$PROC" | grep -oE '[^ ]*odoo-bin' | head -1 || true)
    fi
    if [ -z "${ODOO_PYTHON:-}" ]; then
        PRIMERO=$(echo "$PROC" | awk '{print $2}')
        case "$PRIMERO" in *python*) ODOO_PYTHON="$PRIMERO" ;; esac
    fi
fi
if [ -z "${ODOO_CONF:-}" ]; then
    for c in /etc/odoo/odoo.conf /etc/odoo13.conf /etc/odoo-server.conf /opt/nath-erp/odoo13.conf /opt/nath-erp/*.conf; do
        [ -f "$c" ] && ODOO_CONF="$c" && break
    done
fi
[ -n "${ODOO_CONF:-}" ] && [ -f "$ODOO_CONF" ] || { rojo "No encuentro el fichero de configuracion de Odoo. Pasalo con ODOO_CONF=..."; exit 1; }
ODOO_PYTHON="${ODOO_PYTHON:-python3}"

if [ -z "${ODOO_SERVICE:-}" ]; then
    ODOO_SERVICE=$(systemctl list-units --type=service --all --no-legend 2>/dev/null | awk '{print $1}' | grep -iE 'odoo|nath|openerp' | head -1 || true)
    ODOO_SERVICE="${ODOO_SERVICE%.service}"
fi

ADDONS_PATH=$(grep -E '^\s*addons_path\s*=' "$ODOO_CONF" | head -1 | cut -d= -f2- | tr -d ' ')
if [ -z "${ADDONS_DIR:-}" ]; then
    # La primera carpeta del addons_path que no es la de los modulos estandar de Odoo
    IFS=',' read -ra RUTAS <<< "$ADDONS_PATH"
    for r in "${RUTAS[@]}"; do
        case "$r" in */odoo/addons|*/odoo13/addons|*/odoo/odoo/addons|*/odoo13/odoo/addons) continue ;; esac
        [ -d "$r" ] && ADDONS_DIR="$r" && break
    done
fi
[ -n "${ADDONS_DIR:-}" ] && [ -d "$ADDONS_DIR" ] || { rojo "No encuentro una carpeta de modulos propios en addons_path ($ADDONS_PATH). Pasala con ADDONS_DIR=..."; exit 1; }

echo "   Configuracion : $ODOO_CONF"
echo "   addons_path   : $ADDONS_PATH"
echo "   Se instala en : $ADDONS_DIR/$MODULO"
echo "   Usuario Odoo  : ${ODOO_USER:-?}"
echo "   Servicio      : ${ODOO_SERVICE:-? (no encontrado: habra que reiniciar a mano)}"
echo "   odoo-bin      : ${ODOO_BIN:-? (no encontrado: el modulo se instala desde Aplicaciones)}"
echo "   Base de datos : $ODOO_DB"

read -r -p "¿Seguir? Se reinicia Odoo (unos segundos sin servicio) [s/N] " OK
[ "$OK" = "s" ] || [ "$OK" = "S" ] || { echo "Cancelado. No se ha cambiado nada."; exit 0; }

# ---------------------------------------------------------------- 2. Copia de seguridad
YA_ESTABA=0
if [ -d "$ADDONS_DIR/$MODULO" ]; then
    YA_ESTABA=1
    paso "2. Ya hay un $MODULO: copia de seguridad"
    mv "$ADDONS_DIR/$MODULO" "$ADDONS_DIR/${MODULO}_backup_$FECHA"
    echo "   Guardado en $ADDONS_DIR/${MODULO}_backup_$FECHA"
    # Odoo carga cualquier carpeta con __manifest__.py: se renombra el de la copia para que no la cargue
    mv "$ADDONS_DIR/${MODULO}_backup_$FECHA/__manifest__.py" "$ADDONS_DIR/${MODULO}_backup_$FECHA/__manifest__.py.bak"
else
    paso "2. Primera instalacion (no habia $MODULO)"
fi

# ---------------------------------------------------------------- 3. Descomprimir
paso "3. Creando los ficheros del modulo"
crear_modulo "$ADDONS_DIR"
if [ -n "${ODOO_USER:-}" ] && id "$ODOO_USER" >/dev/null 2>&1; then
    chown -R "$ODOO_USER": "$ADDONS_DIR/$MODULO"
fi
find "$ADDONS_DIR/$MODULO" -type d -exec chmod 755 {} \;
find "$ADDONS_DIR/$MODULO" -type f -exec chmod 644 {} \;
ls -R "$ADDONS_DIR/$MODULO" | sed 's/^/   /'

# ---------------------------------------------------------------- 4. Parar, instalar y arrancar
if [ -n "${ODOO_SERVICE:-}" ]; then
    paso "4. Parando $ODOO_SERVICE"
    systemctl stop "$ODOO_SERVICE"
fi

if [ -n "${ODOO_BIN:-}" ]; then
    if [ "$YA_ESTABA" = 1 ]; then ACCION="-u"; QUE="Actualizando"; else ACCION="-i"; QUE="Instalando"; fi
    paso "5. $QUE $MODULO en $ODOO_DB"
    LOG=/tmp/instalar_${MODULO}_$FECHA.log
    if sudo -u "${ODOO_USER:-odoo}" "$ODOO_PYTHON" "$ODOO_BIN" -c "$ODOO_CONF" -d "$ODOO_DB" $ACCION "$MODULO" \
            --stop-after-init --no-http --logfile="$LOG"; then
        if grep -qE 'ERROR|CRITICAL' "$LOG"; then
            rojo "   Hay errores en el log: $LOG"
            grep -E 'ERROR|CRITICAL' "$LOG" | tail -20
        else
            verde "   Hecho sin errores (log: $LOG)"
        fi
    else
        rojo "   Ha fallado. Mira el log: $LOG"
        tail -30 "$LOG" || true
    fi
else
    paso "5. No he encontrado odoo-bin: instalar desde Odoo (Aplicaciones > Actualizar lista > KOROSHI Monitor zonas > Instalar)"
fi

if [ -n "${ODOO_SERVICE:-}" ]; then
    paso "6. Arrancando $ODOO_SERVICE"
    systemctl start "$ODOO_SERVICE"
    sleep 5
    systemctl is-active --quiet "$ODOO_SERVICE" && verde "   $ODOO_SERVICE en marcha" || { rojo "   $ODOO_SERVICE NO ha arrancado:"; journalctl -u "$ODOO_SERVICE" -n 30 --no-pager; }
else
    paso "6. Reinicia Odoo a mano (no he encontrado el servicio)"
fi

verde "
Listo. En Odoo: Inventario > Operaciones > Monitor zonas
(recargar la pagina con Ctrl+F5 para que cargue el JS nuevo).

Para volver atras:
  sudo rm -rf $ADDONS_DIR/$MODULO
  $( [ "$YA_ESTABA" = 1 ] && echo "sudo mv $ADDONS_DIR/${MODULO}_backup_$FECHA $ADDONS_DIR/$MODULO && sudo mv $ADDONS_DIR/$MODULO/__manifest__.py.bak $ADDONS_DIR/$MODULO/__manifest__.py" || echo "(y en Odoo: Aplicaciones > KOROSHI Monitor zonas > Desinstalar)" )
  sudo systemctl restart ${ODOO_SERVICE:-<servicio odoo>}"
