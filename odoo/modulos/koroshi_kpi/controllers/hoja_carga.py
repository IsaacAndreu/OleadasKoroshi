# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI KPI v1.4 - Hoja de carga XPO (Excel) por delegacion, para el almacen.
#
# /koroshi_kpi/hoja_carga            -> OUT con etiqueta XPO generada hoy (hora de Madrid)
# /koroshi_kpi/hoja_carga?fecha=...  -> la de ese dia (AAAA-MM-DD)
# /koroshi_kpi/hoja_carga?ids=1,2,3  -> las OUT seleccionadas en la lista de albaranes
#
# Hoja "Por delegacion": delegacion, tiendas, pedidos, uds, bultos y palets (bultos / cajas por palet,
# redondeando hacia arriba, minimo 1; las cajas por palet en una celda amarilla que se puede cambiar).
# Hoja "Detalle": una linea por pedido. Tiendas sin delegacion en la lista: van solas (su propio palet).
# Solo lee: no cambia nada en Odoo.
# =============================================================================
import datetime
import io
import re

import pytz
import xlsxwriter

from odoo import http
from odoo.http import request, content_disposition

COMPANY_ID = 8
TZ = 'Europe/Madrid'
CAJAS_PALET = 16            # el 23/10/2026: 355 bultos -> 32 palets, los que se cargaron
RE_K = re.compile(r'\bK(\d+) - .*$')

# Delegacion de transporte por tienda (la misma lista que la etiqueta de zona, 21/10/2026)
DELEGACIONES = {
    1: 'CASTELLBISBAL', 7: 'LEGANÉS', 8: 'PAMPLONA', 9: 'BILBAO', 10: 'BILBAO', 22: 'VITORIA', 24: 'VALLADOLID',
    26: 'FRANQUESES', 29: 'CORUÑA', 31: 'MURCIA', 33: 'ZARAGOZA', 34: 'CASTELLBISBAL', 37: 'SALAMANCA', 38: 'BILBAO',
    39: 'IRÚN', 40: 'VALLADOLID', 41: 'SANTANDER', 42: 'CASTELLBISBAL', 43: 'BENAVENTE', 44: 'GERONA', 45: 'LOGROÑO',
    46: 'IRÚN', 47: 'BENAVENTE', 48: 'VALENCIA', 49: 'IRÚN', 55: 'ZARAGOZA', 56: 'MÁLAGA', 57: 'SAN FERNANDO',
    58: 'BURGOS', 59: 'GRANADA', 60: 'GIJÓN', 61: 'VALENCIA', 62: 'LEGANÉS', 63: 'SAN FERNANDO', 65: 'CASTELLBISBAL',
    67: 'MURCIA', 68: 'SEVILLA', 69: 'TARRAGONA', 70: 'TARRAGONA', 72: 'CASTELLBISBAL', 73: 'LLEIDA', 74: 'CASTELLÓN',
    75: 'CASTELLBISBAL', 76: 'LEGANÉS', 78: 'SAN FERNANDO', 79: 'SAN FERNANDO', 80: 'GERONA', 81: 'SAN FERNANDO',
    83: 'IRÚN',
}


class KoroshiHojaCarga(http.Controller):

    def _outs(self, env, ids, fecha):
        Pick = env['stock.picking'].sudo()
        if ids:
            return Pick.browse(ids).filtered(lambda p: p.picking_type_code == 'outgoing' and p.state == 'done'), ''
        tz = pytz.timezone(TZ)
        dia = fecha or datetime.datetime.now(tz).date()
        ini = tz.localize(datetime.datetime.combine(dia, datetime.time.min)).astimezone(pytz.utc).replace(tzinfo=None)
        fin = ini + datetime.timedelta(days=1)
        etiquetas = env['ir.attachment'].sudo().search([('res_model', '=', 'stock.picking'),
                                                         ('name', '=like', 'LabelXPO_%'),
                                                         ('create_date', '>=', ini), ('create_date', '<', fin)])
        segs = list(set([a.name[len('LabelXPO_'):].replace('.pdf', '') for a in etiquetas]))
        outs = Pick.search([('company_id', '=', COMPANY_ID), ('picking_type_code', '=', 'outgoing'),
                            ('state', '=', 'done'), ('carrier_tracking_ref', 'in', segs)])
        return outs, dia.strftime('%d/%m/%Y')

    @http.route('/koroshi_kpi/hoja_carga', type='http', auth='user')
    def hoja_carga(self, ids=None, fecha=None, **kw):
        env = request.env(context=dict(request.env.context, allowed_company_ids=[COMPANY_ID]))
        lista = [int(x) for x in (ids or '').split(',') if x.strip().isdigit()]
        dia = fecha and datetime.datetime.strptime(fecha, '%Y-%m-%d').date() or None
        outs, titulo_dia = self._outs(env, lista, dia)

        # Una linea por pedido: tienda, seguimiento, uds hechas y bultos (suma de sus OUT)
        uds = {}
        for g in env['stock.move.line'].sudo().read_group([('picking_id', 'in', outs.ids)], ['qty_done'],
                                                           ['picking_id'], lazy=False):
            uds[g['picking_id'][0]] = g['qty_done']
        pedidos = {}
        negativos = []
        for p in outs:
            clave = p.origin or p.name
            nombre = p.partner_id.name or ''
            m = RE_K.search(nombre)
            tienda = m and m.group(0) or nombre.split(', ')[-1]
            knum = m and int(m.group(1)) or 0
            d = pedidos.setdefault(clave, {'tienda': tienda, 'knum': knum, 'segs': set(), 'uds': 0.0, 'bultos': 0})
            if p.carrier_tracking_ref:
                d['segs'].add(p.carrier_tracking_ref)
            d['uds'] += uds.get(p.id, 0.0)
            d['bultos'] += p.number_of_packages or 0
            if (p.number_of_packages or 0) < 0:
                negativos.append('%s %s (%d)' % (p.name.replace('EFFEC/OUT/', ''), tienda.split(' - ')[0],
                                                 p.number_of_packages))
        for clave, d in pedidos.items():
            d['deleg'] = DELEGACIONES.get(d['knum']) or ('K%d (va sola)' % d['knum'] if d['knum'] else d['tienda'])
        filas = sorted(pedidos.items(), key=lambda x: (x[1]['deleg'], x[1]['knum'], x[0]))

        salida = io.BytesIO()
        wb = xlsxwriter.Workbook(salida, {'in_memory': True})
        base = {'font_name': 'Arial', 'font_size': 10, 'border': 1, 'border_color': '#BFBFBF', 'valign': 'top'}
        f_txt = wb.add_format(base)
        f_wrap = wb.add_format(dict(base, text_wrap=True))
        f_num = wb.add_format(dict(base, num_format='#,##0'))
        f_cab = wb.add_format(dict(base, bold=True, font_color='#FFFFFF', bg_color='#1F4E78', align='center',
                                   valign='vcenter', text_wrap=True))
        f_tot = wb.add_format(dict(base, bold=True, bg_color='#FFF2CC'))
        f_totn = wb.add_format(dict(base, bold=True, bg_color='#FFF2CC', num_format='#,##0'))
        f_param = wb.add_format({'font_name': 'Arial', 'bold': True, 'font_color': '#0000FF', 'bg_color': '#FFFF00',
                                 'border': 1})
        f_bold = wb.add_format({'font_name': 'Arial', 'bold': True})
        f_nota = wb.add_format({'font_name': 'Arial', 'italic': True, 'font_color': '#808080'})
        f_tit = wb.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 13})

        ws = wb.add_worksheet('Por delegación')
        wd = wb.add_worksheet('Detalle')

        # ---- Detalle: una linea por pedido ----
        wd.write_row(0, 0, ['Delegación', 'Tienda', 'Pedido', 'Seguimiento', 'Unidades', 'Bultos'], f_cab)
        for i, (clave, d) in enumerate(filas, start=1):
            wd.write(i, 0, d['deleg'], f_txt)
            wd.write(i, 1, d['tienda'], f_txt)
            wd.write(i, 2, clave, f_txt)
            wd.write(i, 3, ', '.join(sorted(d['segs'])), f_txt)
            wd.write_number(i, 4, d['uds'], f_num)
            wd.write_number(i, 5, d['bultos'], f_num)
        n = len(filas)
        wd.write(n + 1, 0, 'TOTAL', f_tot)
        for c in range(1, 4):
            wd.write_blank(n + 1, c, None, f_tot)
        wd.write_formula(n + 1, 4, '=SUM(E2:E%d)' % (n + 1), f_totn, sum([d['uds'] for k, d in filas]))
        wd.write_formula(n + 1, 5, '=SUM(F2:F%d)' % (n + 1), f_totn, sum([d['bultos'] for k, d in filas]))
        for c, w in enumerate([24, 32, 16, 14, 10, 9]):
            wd.set_column(c, c, w)
        wd.freeze_panes(1, 0)
        if n:
            wd.autofilter(0, 0, n, 5)

        # ---- Por delegacion ----
        delegs = []
        info = {}
        for clave, d in filas:
            g = info.get(d['deleg'])
            if g is None:
                delegs.append(d['deleg'])
                g = info[d['deleg']] = {'tiendas': [], 'ped': [], 'uds': 0.0, 'bultos': 0}
            k = d['tienda'].split(' - ')[0]
            if k not in g['tiendas']:
                g['tiendas'].append(k)
            g['ped'].append(clave)
            g['uds'] += d['uds']
            g['bultos'] += d['bultos']
        fila0 = 2                       # fila 1: titulo, fila 2: cabecera (0-based: 0 titulo, 1 cabecera)
        ws.write(0, 0, 'Hoja de carga XPO' + (titulo_dia and (' · ' + titulo_dia) or ' · OUT seleccionadas'), f_tit)
        ws.write_row(1, 0, ['Delegación', 'Tiendas', 'Pedidos', 'Nº pedidos', 'Unidades', 'Bultos', 'Palets'], f_cab)
        ult = fila0 + len(delegs) - 1                   # ultima fila de datos (0-based)
        fila_tot = ult + 1
        fila_param = fila_tot + 2
        celda_param = '$B$%d' % (fila_param + 1)
        total_palets = 0
        for i, dl in enumerate(delegs):
            r = fila0 + i
            g = info[dl]
            palets = max(1, -(-g['bultos'] // CAJAS_PALET)) if g['bultos'] > 0 else 1
            total_palets += palets
            ws.write(r, 0, dl, f_txt)
            ws.write(r, 1, ', '.join(g['tiendas']), f_wrap)
            ws.write(r, 2, ', '.join(sorted(g['ped'])), f_wrap)
            ws.write_number(r, 3, len(g['ped']), f_num)
            ws.write_formula(r, 4, '=SUMIF(Detalle!$A$2:$A$%d,A%d,Detalle!$E$2:$E$%d)' % (n + 1, r + 1, n + 1),
                             f_num, g['uds'])
            ws.write_formula(r, 5, '=SUMIF(Detalle!$A$2:$A$%d,A%d,Detalle!$F$2:$F$%d)' % (n + 1, r + 1, n + 1),
                             f_num, g['bultos'])
            ws.write_formula(r, 6, '=MAX(1,ROUNDUP(F%d/%s,0))' % (r + 1, celda_param), f_num, palets)
        ws.write(fila_tot, 0, 'TOTAL', f_tot)
        ws.write_blank(fila_tot, 1, None, f_tot)
        ws.write_blank(fila_tot, 2, None, f_tot)
        if delegs:
            for c, letra, valor in ((3, 'D', len(filas)), (4, 'E', sum([info[x]['uds'] for x in delegs])),
                                    (5, 'F', sum([info[x]['bultos'] for x in delegs])), (6, 'G', total_palets)):
                ws.write_formula(fila_tot, c, '=SUM(%s%d:%s%d)' % (letra, fila0 + 1, letra, ult + 1), f_totn, valor)
        ws.write(fila_param, 0, 'Cajas por palet', f_bold)
        ws.write_number(fila_param, 1, CAJAS_PALET, f_param)
        ws.write(fila_param, 2, 'Palets = bultos / cajas por palet, redondeando hacia arriba (mínimo 1). '
                                'Cambia el número amarillo si hace falta.', f_nota)
        notas = ['Datos de Odoo: OUT validadas con etiqueta XPO. Las tiendas sin delegación van solas.']
        if negativos:
            notas.append('OJO, OUT con bultos negativos (revisar antes de cargar): ' + ', '.join(negativos))
        sin_etq = [k for k, d in filas if not d['segs']]
        if sin_etq:
            notas.append('Pedidos sin etiqueta XPO todavía: ' + ', '.join(sin_etq))
        for j, t in enumerate(notas):
            ws.write(fila_param + 1 + j, 0, t, f_nota)
        for c, w in enumerate([22, 22, 44, 10, 11, 9, 9]):
            ws.set_column(c, c, w)
        ws.freeze_panes(2, 0)
        if not delegs:
            ws.write(fila0, 0, 'No hay OUT con etiqueta XPO', f_nota)
        wb.close()

        nombre = 'hoja-carga-XPO_%s.xlsx' % (titulo_dia and titulo_dia.replace('/', '-') or 'seleccion')
        return request.make_response(salida.getvalue(), headers=[
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', content_disposition(nombre)),
        ])
