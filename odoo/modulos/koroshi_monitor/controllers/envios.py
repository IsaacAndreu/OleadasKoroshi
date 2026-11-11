# -*- coding: utf-8 -*-
"""Consulta sencilla de expediciones para oficina.

Agrupa todas las OUT de un pedido y compara los bultos declarados en Odoo con
las matriculas de caja realmente usadas. Es una pantalla de solo lectura.
"""
import datetime
import io
import re

import pytz
import xlsxwriter

from odoo import fields, http
from odoo.http import content_disposition, request


COMPANY_ID = 8
MAX_COINCIDENCIAS = 40
MAX_OUTS = 250
RE_TIENDA = re.compile(r'\bK\d+ - .*$')
TIPO_TIENDAS = 'PED. TIENDAS'


class KoroshiConsultaEnvios(http.Controller):

    @staticmethod
    def _tienda(picking):
        nombre = picking.partner_id.name or ''
        encontrada = RE_TIENDA.search(nombre)
        return encontrada.group(0) if encontrada else nombre.split(', ')[-1]

    @staticmethod
    def _hora(dt):
        if not dt:
            return ''
        local = fields.Datetime.context_timestamp(request.env.user, dt)
        return local.strftime('%d/%m/%Y %H:%M')

    @staticmethod
    def _estado(picking):
        return {
            'draft': 'Borrador',
            'waiting': 'En espera',
            'confirmed': 'Preparando',
            'assigned': 'Preparando',
            'done': 'Expedido',
            'cancel': 'Cancelado',
        }.get(picking.state, picking.state or '')

    @staticmethod
    def _cajas_por_out(env, picks):
        cajas_por_out = {}
        if not picks:
            return cajas_por_out
        lineas = env['stock.move.line'].sudo().search_read([
            ('picking_id', 'in', picks.ids),
            ('state', '!=', 'cancel'),
            ('qty_done', '>', 0),
            ('result_package_id', '!=', False),
        ], ['picking_id', 'result_package_id'])
        for linea in lineas:
            pid = linea['picking_id'][0]
            cajas_por_out.setdefault(pid, set()).add(linea['result_package_id'][0])
        return cajas_por_out

    def _agrupar(self, env, picks):
        """Una fila por pedido, contando cada matricula CJ una sola vez."""
        cajas_por_out = self._cajas_por_out(env, picks)

        grupos = {}
        for p in picks:
            if p.sale_id:
                clave = 'sale:%d' % p.sale_id.id
            elif p.origin:
                clave = 'origin:%s' % p.origin
            else:
                clave = 'out:%d' % p.id
            grupo = grupos.setdefault(clave, {
                'pedido': p.origin or (p.sale_id and p.sale_id.name) or p.name,
                'tiendas': set(),
                'transportistas': set(),
                # XPO y GLS guardan su numero de expedicion en carrier_tracking_ref.
                'expediciones': set(),
                'bultos': 0,
                'cajas_ids': set(),
                'outs': [],
                '_fechas': [],
                '_todos_done': True,
                '_alguno_done': False,
            })
            grupo['tiendas'].add(self._tienda(p))
            if p.carrier_id:
                grupo['transportistas'].add(p.carrier_id.name or '')
            if p.carrier_tracking_ref:
                grupo['expediciones'].add(p.carrier_tracking_ref)
            cajas = cajas_por_out.get(p.id, set())
            grupo['bultos'] += p.number_of_packages or 0
            grupo['cajas_ids'].update(cajas)
            fecha = p.date_done or p.scheduled_date or p.create_date
            if fecha:
                grupo['_fechas'].append(fecha)
            grupo['_todos_done'] = grupo['_todos_done'] and p.state == 'done'
            grupo['_alguno_done'] = grupo['_alguno_done'] or p.state == 'done'
            grupo['outs'].append({
                'id': p.id,
                'out': (p.name or '').replace('EFFEC/OUT/', ''),
                'estado': self._estado(p),
                'bultos': p.number_of_packages or 0,
                'cajas': len(cajas),
                'transportista': p.carrier_id and p.carrier_id.name or '',
                'expedicion': p.carrier_tracking_ref or '',
                'fecha': self._hora(p.date_done),
            })

        resultados = []
        for grupo in grupos.values():
            cajas = len(grupo.pop('cajas_ids'))
            fechas = grupo.pop('_fechas')
            todos_done = grupo.pop('_todos_done')
            alguno_done = grupo.pop('_alguno_done')
            grupo['tienda'] = ' · '.join(sorted([x for x in grupo.pop('tiendas') if x]))
            grupo['transportista'] = ' · '.join(sorted([x for x in grupo.pop('transportistas') if x]))
            grupo['expediciones'] = sorted(grupo['expediciones'])
            grupo['cajas'] = cajas
            grupo['comprobable'] = bool(cajas or todos_done)
            grupo['coincide'] = grupo['bultos'] == cajas
            grupo['estado'] = 'Expedido' if todos_done else ('Parcial' if alguno_done else 'Preparando')
            grupo['_orden'] = max(fechas) if fechas else fields.Datetime.from_string('1970-01-01 00:00:00')
            grupo['fecha'] = self._hora(grupo['_orden']) if fechas else ''
            grupo['outs'].sort(key=lambda x: x['out'])
            resultados.append(grupo)

        resultados.sort(key=lambda g: g['_orden'], reverse=True)
        for grupo in resultados:
            grupo.pop('_orden')
        return resultados

    @http.route('/koroshi_monitor/consulta_envios', type='json', auth='user')
    def consulta_envios(self, texto=None, apartado='tiendas', **kw):
        texto = (texto or '').strip()
        apartado = apartado if apartado in ('tiendas', 'web') else 'tiendas'
        if len(texto) < 2:
            return {'resultados': [], 'texto': texto, 'apartado': apartado, 'minimo': True, 'limitado': False}

        env = request.env(context=dict(request.env.context, allowed_company_ids=[COMPANY_ID]))
        Pick = env['stock.picking'].sudo()
        base = [
            ('company_id', '=', COMPANY_ID),
            ('picking_type_code', '=', 'outgoing'),
            ('state', '!=', 'cancel'),
        ]
        if apartado == 'web':
            base.append(('origin', '=like', 'W-%'))
        else:
            base.append(('sale_id.s_order_type_id.name', '=', TIPO_TIENDAS))
        dominio_texto = [
            '|', '|', '|',
            ('origin', 'ilike', texto),
            ('name', 'ilike', texto),
            ('partner_id.name', 'ilike', texto),
            ('carrier_tracking_ref', 'ilike', texto),
        ]
        coincidencias = Pick.search(base + dominio_texto, order='date_done desc, id desc',
                                    limit=MAX_COINCIDENCIAS)
        if not coincidencias:
            return {'resultados': [], 'texto': texto, 'apartado': apartado, 'minimo': False, 'limitado': False}

        # Si la busqueda encuentra una sola OUT o una etiqueta, se recuperan tambien
        # las otras OUT del mismo pedido para que Betty vea el total real.
        sale_ids = coincidencias.mapped('sale_id').ids
        origenes = list(set([p.origin for p in coincidencias if p.origin]))
        hermanos = Pick.browse()
        if sale_ids and origenes:
            hermanos = Pick.search(base + ['|', ('sale_id', 'in', sale_ids), ('origin', 'in', origenes)],
                                   order='date_done desc, id desc', limit=MAX_OUTS)
        elif sale_ids:
            hermanos = Pick.search(base + [('sale_id', 'in', sale_ids)],
                                   order='date_done desc, id desc', limit=MAX_OUTS)
        elif origenes:
            hermanos = Pick.search(base + [('origin', 'in', origenes)],
                                   order='date_done desc, id desc', limit=MAX_OUTS)
        picks = coincidencias | hermanos

        return {
            'resultados': self._agrupar(env, picks),
            'texto': texto,
            'apartado': apartado,
            'minimo': False,
            'limitado': len(coincidencias) >= MAX_COINCIDENCIAS or len(picks) >= MAX_OUTS,
        }

    def _rango_utc(self, desde, hasta):
        tz = pytz.timezone(request.env.user.tz or 'Europe/Madrid')
        hoy = datetime.datetime.now(pytz.utc).astimezone(tz).date()
        try:
            dia_desde = datetime.datetime.strptime(desde or '', '%Y-%m-%d').date()
        except ValueError:
            dia_desde = hoy
        try:
            dia_hasta = datetime.datetime.strptime(hasta or '', '%Y-%m-%d').date()
        except ValueError:
            dia_hasta = dia_desde
        if dia_hasta < dia_desde:
            dia_desde, dia_hasta = dia_hasta, dia_desde
        inicio = tz.localize(datetime.datetime.combine(dia_desde, datetime.time.min)).astimezone(
            pytz.utc).replace(tzinfo=None)
        fin = tz.localize(datetime.datetime.combine(dia_hasta + datetime.timedelta(days=1),
                                                     datetime.time.min)).astimezone(pytz.utc).replace(tzinfo=None)
        return dia_desde, dia_hasta, inicio, fin

    @staticmethod
    def _formatos_excel(libro):
        base = {'font_name': 'Arial', 'font_size': 10, 'valign': 'vcenter'}
        return {
            'titulo': libro.add_format(dict(base, bold=True, font_size=14, align='left', bottom=2,
                                             bottom_color='#315B85')),
            'cab': libro.add_format(dict(base, bold=True, font_color='#FFFFFF', bg_color='#315B85',
                                          align='center', text_wrap=True, border=1, border_color='#FFFFFF')),
            'txt': libro.add_format(dict(base, bottom=1, bottom_color='#D9DEE5')),
            'wrap': libro.add_format(dict(base, bottom=1, bottom_color='#D9DEE5', text_wrap=True)),
            'num': libro.add_format(dict(base, bottom=1, bottom_color='#D9DEE5', num_format='#,##0')),
            'fecha': libro.add_format(dict(base, bottom=1, bottom_color='#D9DEE5',
                                            num_format='dd/mm/yyyy hh:mm')),
            'ok': libro.add_format(dict(base, bottom=1, bottom_color='#D9DEE5', bg_color='#ECFDF3',
                                         font_color='#067647', bold=True, align='center')),
            'mal': libro.add_format(dict(base, bottom=1, bottom_color='#D9DEE5', bg_color='#FFF0EE',
                                          font_color='#B42318', bold=True, align='center')),
            'total': libro.add_format(dict(base, bold=True, bg_color='#E8EEF6', top=2,
                                            top_color='#315B85')),
            'total_num': libro.add_format(dict(base, bold=True, bg_color='#E8EEF6', top=2,
                                                top_color='#315B85', num_format='#,##0')),
            'nota': libro.add_format(dict(base, italic=True, font_color='#667085')),
        }

    def _excel_tiendas(self, env, picks, etiqueta, dia_desde, dia_hasta):
        salida = io.BytesIO()
        libro = xlsxwriter.Workbook(salida, {'in_memory': True})
        f = self._formatos_excel(libro)
        hoja = libro.add_worksheet('Tiendas')
        grupos = self._agrupar(env, picks)
        cab = ['Fecha', 'Pedido', 'Tienda', 'OUT', 'Transportista', 'Nº expedición',
               'Bultos Odoo', 'Cajas preparadas', 'Coincide']
        hoja.merge_range(0, 0, 0, len(cab) - 1,
                         'PEDIDOS DE TIENDA · %s · %s' % (
                             etiqueta, dia_desde.strftime('%d/%m/%Y') if dia_desde == dia_hasta else
                             '%s - %s' % (dia_desde.strftime('%d/%m/%Y'), dia_hasta.strftime('%d/%m/%Y'))),
                         f['titulo'])
        hoja.write_row(2, 0, cab, f['cab'])
        for fila, grupo in enumerate(grupos, start=3):
            try:
                fecha = datetime.datetime.strptime(grupo['fecha'], '%d/%m/%Y %H:%M')
            except (TypeError, ValueError):
                fecha = None
            valores = [fecha, grupo['pedido'], grupo['tienda'], ', '.join([o['out'] for o in grupo['outs']]),
                       grupo['transportista'] or etiqueta, ', '.join(grupo['expediciones']),
                       grupo['bultos'], grupo['cajas'], 'SÍ' if grupo['coincide'] else 'NO']
            formatos = [f['fecha'], f['txt'], f['wrap'], f['wrap'], f['txt'], f['txt'],
                        f['num'], f['num'], f['ok'] if grupo['coincide'] else f['mal']]
            for col, valor in enumerate(valores):
                if valor is None:
                    hoja.write_blank(fila, col, None, formatos[col])
                else:
                    hoja.write(fila, col, valor, formatos[col])
        total = 3 + len(grupos)
        hoja.write(total, 0, 'TOTAL', f['total'])
        hoja.write(total, 1, len(grupos), f['total_num'])
        for col in range(2, 6):
            hoja.write_blank(total, col, None, f['total'])
        hoja.write(total, 6, sum([g['bultos'] for g in grupos]), f['total_num'])
        hoja.write(total, 7, sum([g['cajas'] for g in grupos]), f['total_num'])
        hoja.write_blank(total, 8, None, f['total'])
        hoja.write(total + 2, 0,
                   'Bultos Odoo = lo declarado al transportista. Cajas preparadas = matrículas CJ distintas.',
                   f['nota'])
        for col, ancho in enumerate([18, 20, 35, 24, 18, 24, 13, 16, 11]):
            hoja.set_column(col, col, ancho)
        hoja.freeze_panes(3, 0)
        hoja.autofilter(2, 0, max(2, total - 1), len(cab) - 1)
        hoja.set_landscape()
        hoja.fit_to_pages(1, 0)
        libro.close()
        return salida.getvalue(), len(grupos)

    def _excel_web(self, env, picks, etiqueta, dia_desde, dia_hasta):
        salida = io.BytesIO()
        libro = xlsxwriter.Workbook(salida, {'in_memory': True})
        f = self._formatos_excel(libro)
        hoja = libro.add_worksheet('Web')
        cab = ['Fecha de transferencia', 'Documento origen', 'Referencia', 'Marca', 'Transportista',
               'Done Quantity', 'Bultos Odoo', 'Cajas preparadas', 'Nº expedición', 'Coincide']
        hoja.merge_range(0, 0, 0, len(cab) - 1,
                         'PEDIDOS WEB · %s · %s' % (
                             etiqueta, dia_desde.strftime('%d/%m/%Y') if dia_desde == dia_hasta else
                             '%s - %s' % (dia_desde.strftime('%d/%m/%Y'), dia_hasta.strftime('%d/%m/%Y'))),
                         f['titulo'])
        hoja.write_row(2, 0, cab, f['cab'])
        unidades = {}
        for dato in env['stock.move.line'].sudo().read_group(
                [('picking_id', 'in', picks.ids)], ['qty_done'], ['picking_id'], lazy=False):
            unidades[dato['picking_id'][0]] = dato['qty_done']
        cajas = self._cajas_por_out(env, picks)
        tz = pytz.timezone(request.env.user.tz or 'Europe/Madrid')
        for fila, p in enumerate(picks.sorted(key=lambda x: (x.date_done or x.create_date, x.name)), start=3):
            fecha = p.date_done and pytz.utc.localize(p.date_done).astimezone(tz).replace(tzinfo=None) or None
            marca = getattr(p, 'x_studio_marca', False)
            marca = marca and getattr(marca, 'name', '') or ''
            n_cajas = len(cajas.get(p.id, set()))
            bultos = p.number_of_packages or 0
            coincide = bultos == n_cajas
            valores = [fecha, p.origin or '', p.name or '', marca, etiqueta, unidades.get(p.id, 0),
                       bultos, n_cajas, p.carrier_tracking_ref or '', 'SÍ' if coincide else 'NO']
            formatos = [f['fecha'], f['txt'], f['txt'], f['txt'], f['txt'], f['num'], f['num'], f['num'],
                        f['txt'], f['ok'] if coincide else f['mal']]
            for col, valor in enumerate(valores):
                if valor is None:
                    hoja.write_blank(fila, col, None, formatos[col])
                else:
                    hoja.write(fila, col, valor, formatos[col])
        total = 3 + len(picks)
        hoja.write(total, 0, 'TOTAL', f['total'])
        hoja.write(total, 1, len(picks), f['total_num'])
        for col in range(2, 5):
            hoja.write_blank(total, col, None, f['total'])
        hoja.write(total, 5, sum(unidades.values()), f['total_num'])
        hoja.write(total, 6, sum([(p.number_of_packages or 0) for p in picks]), f['total_num'])
        hoja.write(total, 7, len(set().union(*[cajas.get(p.id, set()) for p in picks])) if picks else 0,
                   f['total_num'])
        hoja.write_blank(total, 8, None, f['total'])
        hoja.write_blank(total, 9, None, f['total'])
        hoja.write(total + 2, 0,
                   'Formato basado en las hojas de pedidos web de Betty. Se añaden bultos, cajas y expedición.',
                   f['nota'])
        for col, ancho in enumerate([22, 21, 21, 13, 16, 14, 13, 16, 24, 11]):
            hoja.set_column(col, col, ancho)
        hoja.freeze_panes(3, 0)
        hoja.autofilter(2, 0, max(2, total - 1), len(cab) - 1)
        hoja.set_landscape()
        hoja.fit_to_pages(1, 0)
        libro.close()
        return salida.getvalue(), len(picks)

    @http.route('/koroshi_monitor/consulta_envios.xlsx', type='http', auth='user')
    def consulta_envios_excel(self, apartado='tiendas', transportista=None, desde=None, hasta=None, **kw):
        apartado = apartado if apartado in ('tiendas', 'web') else 'tiendas'
        permitidos = {'tiendas': ('xpo', 'gls'), 'web': ('gls', 'seur')}
        transportista = transportista if transportista in permitidos[apartado] else permitidos[apartado][0]
        etiquetas = {'xpo': 'XPO SAS', 'gls': 'GLS', 'seur': 'SEUR'}
        etiqueta = etiquetas[transportista]
        dia_desde, dia_hasta, inicio, fin = self._rango_utc(desde, hasta)
        env = request.env(context=dict(request.env.context, allowed_company_ids=[COMPANY_ID]))
        dominio = [
            ('company_id', '=', COMPANY_ID),
            ('picking_type_code', '=', 'outgoing'),
            ('state', '=', 'done'),
            ('date_done', '>=', inicio),
            ('date_done', '<', fin),
        ]
        if apartado == 'tiendas':
            dominio += [('sale_id.s_order_type_id.name', '=', TIPO_TIENDAS),
                        ('carrier_id.name', 'ilike', 'XPO' if transportista == 'xpo' else 'GLS')]
        elif transportista == 'seur':
            # Las dos muestras de Betty separan los pedidos web por su numeracion:
            # W-000... = SEUR; el resto de W-... = GLS.
            dominio.append(('origin', '=like', 'W-000%'))
        else:
            dominio += [('origin', '=like', 'W-%'), ('origin', 'not like', 'W-000%')]
        picks = env['stock.picking'].sudo().search(dominio, order='date_done, id')
        if apartado == 'web':
            contenido, _n = self._excel_web(env, picks, etiqueta, dia_desde, dia_hasta)
        else:
            contenido, _n = self._excel_tiendas(env, picks, etiqueta, dia_desde, dia_hasta)
        nombre = 'envios_%s_%s_%s.xlsx' % (
            apartado, transportista, dia_desde.strftime('%Y-%m-%d') if dia_desde == dia_hasta else
            '%s_%s' % (dia_desde.strftime('%Y-%m-%d'), dia_hasta.strftime('%Y-%m-%d')))
        return request.make_response(contenido, headers=[
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', content_disposition(nombre)),
        ])
