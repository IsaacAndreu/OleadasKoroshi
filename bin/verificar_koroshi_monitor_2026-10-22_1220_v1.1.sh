#!/usr/bin/env bash
# =============================================================================
# COMPROBAR (solo lee, NO cambia nada) que el modulo koroshi_monitor se puede instalar
# sin problemas ni pisar nada de otros modulos.
#
# Uso (en el servidor de Odoo):
#   sudo bash verificar_koroshi_monitor_2026-10-22_1220_v1.1.sh
#
# Que comprueba:
#   1. Encuentra el Odoo que corre (configuracion, addons_path, python, base de datos).
#   2. Version de Odoo = 13.
#   3. En las carpetas de modulos: que no exista ya otro "koroshi_monitor" y que ningun otro
#      modulo use la ruta /koroshi_monitor/, la accion de cliente 'koroshi_monitor' ni el
#      nombre JS 'koroshi_monitor.monitor'.
#   4. Los ficheros del modulo (van dentro de este script) compilan con el python de Odoo
#      y los XML son correctos. Se crean SOLO en una carpeta temporal que se borra al final.
#   5. En la base de datos (solo SELECT): que las dependencias (web, stock, stock_picking_batch)
#      estan instaladas, que no hay ya un modulo, ids XML, accion de cliente ni menu con esos
#      nombres, y que el menu padre Inventario > Operaciones existe.
#   6. Que la carpeta de modulos propios se puede escribir y hay espacio.
# Al final: resumen OK / AVISO / ERROR. Si no hay ERROR, se puede instalar.
#
# Variables para forzar la deteccion: ODOO_CONF, ADDONS_DIR, ODOO_PYTHON, ODOO_DB
# =============================================================================
set -uo pipefail

MODULO=koroshi_monitor
ODOO_DB="${ODOO_DB:-NATH_PRODUCTION}"
N_OK=0; N_AV=0; N_ER=0
ok()    { printf '  \033[32mOK\033[0m     %s\n' "$*"; N_OK=$((N_OK+1)); }
aviso() { printf '  \033[33mAVISO\033[0m  %s\n' "$*"; N_AV=$((N_AV+1)); }
error() { printf '  \033[31mERROR\033[0m  %s\n' "$*"; N_ER=$((N_ER+1)); }
paso()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }

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

# ---------------------------------------------------------------- 1. Detectar
paso "1. Odoo que esta corriendo"
PROC=$(ps -eo user:32,args | grep -E 'odoo-bin|openerp-server' | grep -v grep | head -1 || true)
if [ -n "$PROC" ]; then
    ok "Proceso: $(echo "$PROC" | cut -c1-160)"
    if [ -z "${ODOO_CONF:-}" ]; then
        ODOO_CONF=$(echo "$PROC" | grep -oE '(-c|--config)[ =][^ ]+' | head -1 | sed -E 's/^(-c|--config)[ =]//' || true)
    fi
    ODOO_BIN=$(echo "$PROC" | grep -oE '[^ ]*odoo-bin' | head -1 || true)
    if [ -z "${ODOO_PYTHON:-}" ]; then
        PRIMERO=$(echo "$PROC" | awk '{print $2}')
        case "$PRIMERO" in *python*) ODOO_PYTHON="$PRIMERO" ;; esac
    fi
else
    aviso "No veo ningun proceso odoo-bin corriendo"
fi
if [ -z "${ODOO_CONF:-}" ]; then
    for c in /etc/odoo/odoo.conf /etc/odoo13.conf /etc/odoo-server.conf /opt/nath-erp/odoo13.conf /opt/nath-erp/*.conf; do
        [ -f "$c" ] && ODOO_CONF="$c" && break
    done
fi
if [ -z "${ODOO_CONF:-}" ] || [ ! -f "$ODOO_CONF" ]; then
    error "No encuentro el fichero de configuracion de Odoo (pasalo con ODOO_CONF=...)"
    echo; echo "No se puede seguir comprobando."; exit 1
fi
ok "Configuracion: $ODOO_CONF"
ODOO_PYTHON="${ODOO_PYTHON:-python3}"
"$ODOO_PYTHON" -c 'import odoo' 2>/dev/null && ok "Python de Odoo: $ODOO_PYTHON" || aviso "$ODOO_PYTHON no importa 'odoo' (las comprobaciones de BD usan psycopg2 igualmente)"

ADDONS_PATH=$(grep -E '^\s*addons_path\s*=' "$ODOO_CONF" | head -1 | cut -d= -f2- | tr -d ' ')
IFS=',' read -ra RUTAS <<< "$ADDONS_PATH"
ok "addons_path: $ADDONS_PATH"
if [ -z "${ADDONS_DIR:-}" ]; then
    for r in "${RUTAS[@]}"; do
        case "$r" in */odoo/addons|*/odoo13/addons|*/odoo/odoo/addons|*/odoo13/odoo/addons) continue ;; esac
        [ -d "$r" ] && ADDONS_DIR="$r" && break
    done
fi
[ -n "${ADDONS_DIR:-}" ] && ok "Carpeta donde se instalaria: $ADDONS_DIR" || error "No hay carpeta de modulos propios en addons_path"

# ---------------------------------------------------------------- 2. Version
paso "2. Version de Odoo"
VER=$("$ODOO_PYTHON" -c 'import odoo.release as r; print(r.version)' 2>/dev/null || true)
if [ -z "$VER" ] && [ -n "${ODOO_BIN:-}" ]; then
    VER=$(grep -hoE "version_info = \([0-9]+" "$(dirname "$ODOO_BIN")/odoo/release.py" 2>/dev/null | grep -oE '[0-9]+$' || true)
fi
case "$VER" in
    13*) ok "Odoo $VER" ;;
    "") aviso "No he podido leer la version (el modulo es para Odoo 13)" ;;
    *) error "Odoo $VER: el modulo es para Odoo 13" ;;
esac

# ---------------------------------------------------------------- 3. Carpetas de modulos
paso "3. Choques con otros modulos en las carpetas de addons"
for r in "${RUTAS[@]}"; do
    [ -d "$r" ] || { aviso "La carpeta $r del addons_path no existe"; continue; }
    if [ -e "$r/$MODULO" ]; then
        if [ -f "$r/$MODULO/__manifest__.py" ] && grep -q "KOROSHI Monitor zonas" "$r/$MODULO/__manifest__.py"; then
            aviso "Ya hay una version de $MODULO en $r (el instalador la guarda como copia y la actualiza)"
        else
            error "Ya existe una carpeta $r/$MODULO que NO es este modulo: no instalar sin mirarla"
        fi
    fi
done
[ "$N_ER" = 0 ] && ok "No hay otro modulo llamado $MODULO"

CHOQUES=$(grep -rlE --include='*.py' --include='*.xml' --include='*.js' "/koroshi_monitor/|'koroshi_monitor'|\"koroshi_monitor\"|koroshi_monitor\.monitor" "${RUTAS[@]}" 2>/dev/null | grep -v "/$MODULO/" | head -20 || true)
if [ -n "$CHOQUES" ]; then
    error "Otros ficheros usan la ruta, la accion o el JS 'koroshi_monitor':"; echo "$CHOQUES" | sed 's/^/           /'
else
    ok "Ningun otro modulo usa la ruta /koroshi_monitor/, la accion de cliente 'koroshi_monitor' ni el JS 'koroshi_monitor.monitor'"
fi
CSS=$(grep -rl --include='*.css' --include='*.scss' --include='*.js' --include='*.xml' "o_koroshi_monitor\|km-cel\|km-barra" "${RUTAS[@]}" 2>/dev/null | grep -v "/$MODULO/" | head -5 || true)
[ -n "$CSS" ] && aviso "Otros ficheros usan las clases CSS del monitor: $CSS" || ok "Los estilos solo afectan a la pantalla del monitor (todo dentro de .o_koroshi_monitor)"

# ---------------------------------------------------------------- 4. Ficheros del modulo
paso "4. Ficheros del modulo (en una carpeta temporal, se borra al final)"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
crear_modulo "$TMP"
N=$(find "$TMP/$MODULO" -type f | wc -l)
ok "$N ficheros generados en $TMP (temporal)"
if "$ODOO_PYTHON" -m py_compile "$TMP/$MODULO/__init__.py" "$TMP/$MODULO/__manifest__.py" "$TMP/$MODULO/controllers/__init__.py" "$TMP/$MODULO/controllers/main.py" 2>"$TMP/py.err"; then
    ok "Python compila con el python de Odoo"
else
    error "Python no compila:"; sed 's/^/           /' "$TMP/py.err"
fi
for x in "$TMP/$MODULO"/views/*.xml; do
    if "$ODOO_PYTHON" -c "import sys, xml.dom.minidom as X; X.parse(sys.argv[1])" "$x" 2>"$TMP/xml.err"; then
        ok "XML correcto: views/$(basename "$x")"
    else
        error "XML con errores: views/$(basename "$x")"; sed 's/^/           /' "$TMP/xml.err"
    fi
done
# Lo que el modulo crea en Odoo: todo con el prefijo koroshi_monitor.
ok "El modulo solo crea: koroshi_monitor.assets_backend (anade 1 CSS y 1 JS a la web), koroshi_monitor.action_koroshi_monitor, koroshi_monitor.menu_koroshi_monitor"
ok "No hereda ni modifica vistas, modelos ni campos de otros modulos (solo lee stock.picking, stock.move, stock.move.line y stock.picking.batch)"

# ---------------------------------------------------------------- 5. Base de datos (solo SELECT)
paso "5. Base de datos $ODOO_DB (solo lectura)"
cat > "$TMP/bd.py" <<'FIN_PY'
import sys, configparser
import psycopg2
conf, db, modulo = sys.argv[1], sys.argv[2], sys.argv[3]
c = configparser.ConfigParser(); c.read(conf)
o = c['options'] if c.has_section('options') else {}
def g(k, d=None):
    v = o.get(k, d)
    return None if v in (None, '', 'False', 'false') else v
args = {'dbname': db}
for k, a in (('db_host', 'host'), ('db_port', 'port'), ('db_user', 'user'), ('db_password', 'password')):
    if g(k):
        args[a] = g(k)
try:
    cn = psycopg2.connect(**args)
except Exception as e:
    print('ERROR|No puedo conectar a la base de datos %s: %s' % (db, str(e).strip()))
    sys.exit(0)
cn.set_session(readonly=True)
cr = cn.cursor()
def uno(sql, p=()):
    cr.execute(sql, p); return cr.fetchall()
for dep in ('web', 'stock', 'stock_picking_batch'):
    r = uno("select state from ir_module_module where name=%s", (dep,))
    print(('OK|Dependencia %s instalada' % dep) if r and r[0][0] == 'installed'
          else ('ERROR|Dependencia %s NO instalada (%s)' % (dep, r and r[0][0] or 'no existe')))
r = uno("select state from ir_module_module where name=%s", (modulo,))
print(('AVISO|El modulo %s ya esta en la base de datos (estado %s): se actualizara' % (modulo, r[0][0])) if r
      else 'OK|El modulo %s no esta en la base de datos' % modulo)
r = uno("select module, name, model from ir_model_data where module=%s", (modulo,))
print(('AVISO|Ya hay %d ids XML de %s (de una instalacion anterior)' % (len(r), modulo)) if r
      else 'OK|No hay ids XML de %s: no se pisa nada' % modulo)
r = uno("select id, name from ir_act_client where tag=%s", (modulo,))
print(('ERROR|Ya hay una accion de cliente con tag %s: %s' % (modulo, r)) if r and not uno(
    "select 1 from ir_model_data where module=%s and model='ir.actions.client'", (modulo,))
      else 'OK|Ninguna otra accion usa el tag %s' % modulo)
r = uno("select d.id from ir_model_data d join ir_ui_menu m on m.id=d.res_id where d.module='stock' and d.name='menu_stock_warehouse_mgmt' and d.model='ir.ui.menu'")
print('OK|Existe el menu padre Inventario > Operaciones' if r else 'ERROR|No existe el menu stock.menu_stock_warehouse_mgmt')
r = uno("select 1 from ir_model_data where module='stock' and name='group_stock_user'")
print('OK|Existe el grupo Inventario / Usuario' if r else 'ERROR|No existe el grupo stock.group_stock_user')
r = uno("select id from ir_ui_menu where parent_id=(select res_id from ir_model_data where module='stock' and name='menu_stock_warehouse_mgmt') and name::text ilike %s", ('%Monitor zonas%',))
print(('AVISO|Ya hay un menu "Monitor zonas" en Inventario > Operaciones (ids %s)' % [x[0] for x in r]) if r
      else 'OK|No hay otro menu "Monitor zonas"')
r = uno("select count(*) from ir_ui_view where key like 'koroshi.%%'")
print('OK|Las vistas KOROSHI hechas a mano (koroshi.report_etiqueta_zona, ...: %d) usan la clave "koroshi.", distinta de "koroshi_monitor.": no se tocan' % r[0][0])
r = uno("select count(*) from stock_picking_batch where name like 'Z-%%'")
print('OK|Agrupaciones Z-... en la base de datos: %d (el monitor las lee)' % r[0][0])
cn.close()
FIN_PY
while IFS='|' read -r tipo texto; do
    case "$tipo" in OK) ok "$texto" ;; AVISO) aviso "$texto" ;; *) error "$texto" ;; esac
done < <("$ODOO_PYTHON" "$TMP/bd.py" "$ODOO_CONF" "$ODOO_DB" "$MODULO" 2>"$TMP/bd.err")
[ -s "$TMP/bd.err" ] && { error "Fallo al consultar la BD:"; sed 's/^/           /' "$TMP/bd.err"; }

# ---------------------------------------------------------------- 6. Permisos y espacio
paso "6. Permisos y espacio"
if [ -n "${ADDONS_DIR:-}" ]; then
    [ -w "$ADDONS_DIR" ] && ok "Se puede escribir en $ADDONS_DIR" || aviso "No se puede escribir en $ADDONS_DIR sin sudo (el instalador se ejecuta con sudo)"
    LIBRE=$(df -Pm "$ADDONS_DIR" | awk 'NR==2{print $4}')
    [ "${LIBRE:-0}" -gt 50 ] && ok "Espacio libre: ${LIBRE} MB" || error "Poco espacio libre: ${LIBRE:-?} MB"
fi

# ---------------------------------------------------------------- Resumen
printf '\n\033[1m== Resumen: %d OK, %d AVISO, %d ERROR\033[0m\n' "$N_OK" "$N_AV" "$N_ER"
if [ "$N_ER" -gt 0 ]; then
    printf '\033[31mHay errores: NO instalar todavia. Pasa esta salida para revisarla.\033[0m\n'
    exit 1
fi
printf '\033[32mSin errores: se puede instalar. No se ha cambiado nada.\033[0m\n'
