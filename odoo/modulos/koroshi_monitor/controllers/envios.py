# -*- coding: utf-8 -*-
"""Consulta sencilla de expediciones para oficina.

Agrupa todas las OUT de un pedido y compara los bultos declarados en Odoo con
las matriculas de caja realmente usadas. Solo lee pedidos y expediciones; lo unico
que escribe son las OUT añadidas a mano a un dia (modelo koroshi.envio.extra).

Excel de tiendas (v1.20): el dia es el de la ETIQUETA del transportista, no el de
validacion. Al generar la etiqueta, XPO y GLS dejan el PDF como adjunto de la OUT
(LabelXPO_<expedicion>.pdf / gls_label_<codigo>.pdf); su fecha de creacion es la de
la etiqueta. Comprobado el 11/11/2026: las 165 expediciones desde el 05/11 tienen ese
adjunto, y 217 OUT validadas el 10/11 se etiquetaron el 11/11.
"""
import datetime
import io
import re

import pytz
import xlsxwriter

from odoo import fields, http
from odoo.http import content_disposition, request
from odoo.addons.koroshi_base import comun   # v1.28: la empresa

from .main import _comprobar_grupo   # v1.27: permiso de Inventario


COMPANY_ID = comun.COMPANY_ID   # v1.28: de koroshi_base
MAX_COINCIDENCIAS = 40
MAX_OUTS = 250
RE_TIENDA = re.compile(r'\bK\d+ - .*$')
TIPO_TIENDAS = 'PED. TIENDAS'
# Adjuntos PDF que deja el transportista en la OUT al generar la etiqueta.
ETIQUETAS_ADJUNTO = ('LabelXPO_%', 'gls_label_%')
# v1.22: 'todos' = Excel de tiendas con todos los pedidos validados ese dia, con y sin transportista.
PERMITIDOS = {'tiendas': ('xpo', 'gls', 'todos'), 'web': ('gls', 'seur')}
NOMBRES_TRANSPORTISTA = {'xpo': 'XPO SAS', 'gls': 'GLS', 'seur': 'SEUR', 'todos': 'Todos'}
SIN_TRANSPORTISTA = 'Sin transportista'


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

    def _agrupar(self, env, picks, fechas=None):
        """Una fila por pedido, contando cada matricula CJ una sola vez.

        fechas: {id OUT: fecha} para usar otra fecha que la de validacion (la de la etiqueta).
        """
        fechas = fechas or {}
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
            fecha = fechas.get(p.id) or p.date_done or p.scheduled_date or p.create_date
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
                'fecha': self._hora(fechas.get(p.id) or p.date_done),
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
        _comprobar_grupo()   # v1.27
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
        tz = pytz.timezone(request.env.user.tz or comun.TZ)
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

    def _excel_tiendas(self, env, picks, etiqueta, dia_desde, dia_hasta, fechas=None, manuales=None, avisos=None):
        salida = io.BytesIO()
        libro = xlsxwriter.Workbook(salida, {'in_memory': True})
        f = self._formatos_excel(libro)
        hoja = libro.add_worksheet('Tiendas')
        grupos = self._agrupar(env, picks, fechas)
        manuales = manuales or set()
        es_gls = etiqueta == 'GLS'
        todos = etiqueta == NOMBRES_TRANSPORTISTA['todos']
        uds = self._uds_por_out(env, picks)

        # v1.23: una fila por TIENDA (antes una por pedido). A la izquierda, todos sus pedidos y OUT.
        tiendas = {}
        for g in grupos:
            # GLS genera como maximo cinco etiquetas por expedicion: se limita por pedido y luego se suma.
            bultos = min(g['bultos'], 5) if es_gls and g['expediciones'] else g['bultos']
            cajas = min(g['cajas'], 5) if es_gls else g['cajas']
            t = tiendas.setdefault(g['tienda'] or '—', {
                'pedidos': [], 'outs': [], 'transportistas': set(), 'expediciones': [], 'bultos': 0,
                'cajas': 0, 'cajas_cmp': 0, 'pedidas': 0, 'hechas': 0, 'fecha': None, 'a_mano': [],
                'sin_transportista': 0, 'detalle': [],
            })
            t['pedidos'].append(g['pedido'])
            # v1.23.1: cajas de cada pedido/expedicion, para el Excel de GLS (al agrupar por tienda se perdia).
            t['detalle'].append('%s%s: %d %s' % (
                g['pedido'], g['expediciones'] and ' (%s)' % ', '.join(g['expediciones']) or '',
                g['cajas'], g['cajas'] == 1 and 'caja' or 'cajas'))
            for o in g['outs']:
                t['outs'].append(o['out'])
                pedida, hecha = uds.get(o['id'], (0, 0))
                t['pedidas'] += pedida
                t['hechas'] += hecha
                if o['id'] in manuales:
                    t['a_mano'].append(o['out'])
            if g['transportista']:
                t['transportistas'].add(g['transportista'])
            else:
                t['sin_transportista'] += 1
            t['expediciones'] += [x for x in g['expediciones'] if x not in t['expediciones']]
            t['bultos'] += bultos
            t['cajas'] += g['cajas']
            t['cajas_cmp'] += cajas
            try:
                fecha = datetime.datetime.strptime(g['fecha'], '%d/%m/%Y %H:%M')
            except (TypeError, ValueError):
                fecha = None
            if fecha and (not t['fecha'] or fecha > t['fecha']):
                t['fecha'] = fecha

        def orden_tienda(nombre):
            numero = re.search(r'K(\d+)', nombre or '')
            return (int(numero.group(1)) if numero else 99999, nombre)

        cab = ['Tienda', 'Pedidos', 'OUT', 'Fecha validación' if todos else 'Fecha etiqueta', 'Transportista',
               'Nº expedición', 'Etiquetas GLS' if es_gls else 'Bultos Odoo', 'Cajas preparadas', 'Coincide',
               'Uds pedidas', 'Done Quantity', 'Cajas por pedido (expedición)', 'Observación']
        hoja.merge_range(0, 0, 0, len(cab) - 1,
                         'PEDIDOS DE TIENDA · %s · %s' % (
                             'TODOS (con y sin transportista)' if todos else etiqueta, dia_desde.strftime('%d/%m/%Y') if dia_desde == dia_hasta else
                             '%s - %s' % (dia_desde.strftime('%d/%m/%Y'), dia_hasta.strftime('%d/%m/%Y'))),
                         f['titulo'])
        hoja.write_row(2, 0, cab, f['cab'])
        nombres = sorted(tiendas.keys(), key=orden_tienda)
        for fila, nombre in enumerate(nombres, start=3):
            t = tiendas[nombre]
            coincide = t['bultos'] == t['cajas_cmp']
            transportista = ' · '.join(sorted(t['transportistas']))
            if t['sin_transportista']:
                transportista = (transportista + ' · ' if transportista else '') + (
                    SIN_TRANSPORTISTA if todos else etiqueta)
            observacion = ''
            if t['a_mano']:
                observacion = 'Añadido a mano' if len(t['a_mano']) == len(t['outs']) else \
                    'Añadido a mano: %s' % ', '.join(t['a_mano'])
            for ref in t['expediciones']:
                for aviso in (avisos or {}).get(ref, []):
                    observacion = (observacion + '\n' if observacion else '') + \
                        'No cuenta: %s con el nº %s pero sin etiqueta XPO' % (aviso, ref)
            valores = [nombre, ', '.join(t['pedidos']), ', '.join(sorted(t['outs'])), t['fecha'], transportista,
                       ', '.join(t['expediciones']), t['bultos'], t['cajas'], 'SÍ' if coincide else 'NO',
                       t['pedidas'], t['hechas'], '\n'.join(t['detalle']), observacion]
            formatos = [f['wrap'], f['wrap'], f['wrap'], f['fecha'], f['wrap'], f['wrap'],
                        f['num'], f['num'], f['ok'] if coincide else f['mal'], f['num'], f['num'], f['wrap'],
                        f['wrap']]
            for col, valor in enumerate(valores):
                if valor is None:
                    hoja.write_blank(fila, col, None, formatos[col])
                else:
                    hoja.write(fila, col, valor, formatos[col])
        total = 3 + len(nombres)
        hoja.write(total, 0, 'TOTAL %d tiendas' % len(nombres), f['total'])
        hoja.write(total, 1, '%d pedidos' % len(grupos), f['total'])
        hoja.write(total, 2, '%d OUT' % sum([len(t['outs']) for t in tiendas.values()]), f['total'])
        for col in range(3, 6):
            hoja.write_blank(total, col, None, f['total'])
        hoja.write(total, 6, sum([t['bultos'] for t in tiendas.values()]), f['total_num'])
        hoja.write(total, 7, sum([t['cajas'] for t in tiendas.values()]), f['total_num'])
        hoja.write_blank(total, 8, None, f['total'])
        hoja.write(total, 9, sum([t['pedidas'] for t in tiendas.values()]), f['total_num'])
        hoja.write(total, 10, sum([t['hechas'] for t in tiendas.values()]), f['total_num'])
        hoja.write_blank(total, 11, None, f['total'])
        hoja.write_blank(total, 12, None, f['total'])
        nota = ('Etiquetas GLS = solo expediciones con etiqueta generada, máximo 5 por pedido. '
                'Las cajas que excedan de 5 viajan juntadas.' if es_gls else
                'Bultos Odoo = lo declarado al transportista. Cajas preparadas = matrículas CJ distintas.')
        hoja.write(total + 2, 0, nota + ' Uds pedidas = lo que pide el pedido en esas OUT; Done Quantity = '
                   'uds hechas (leídas).', f['nota'])
        if todos:
            sin = len([g for g in grupos if not g['transportista']])
            hoja.write(total + 3, 0, 'Salen todos los pedidos de tienda validados en estas fechas, tengan o no '
                       'transportista (%d con transportista, %d sin transportista), más los añadidos a mano.'
                       % (len(grupos) - sin, sin), f['nota'])
        else:
            hoja.write(total + 3, 0, 'Salen los pedidos con la etiqueta del transportista creada en estas fechas, '
                       'aunque se validaran días antes, más los añadidos a mano en Consulta de envíos.', f['nota'])
        for col, ancho in enumerate([26, 22, 22, 17, 16, 18, 11, 11, 10, 11, 12, 34, 20]):
            hoja.set_column(col, col, ancho)
        hoja.freeze_panes(3, 1)
        hoja.autofilter(2, 0, max(2, total - 1), len(cab) - 1)
        hoja.set_landscape()
        hoja.fit_to_pages(1, 0)
        libro.close()
        return salida.getvalue(), len(nombres)

    @staticmethod
    def _uds_por_out(env, picks):
        """{id OUT: (uds pedidas, uds hechas)}. Pedidas = movimientos no cancelados; hechas = qty_done."""
        uds = {}
        if not picks:
            return uds
        for dato in env['stock.move'].sudo().read_group(
                [('picking_id', 'in', picks.ids), ('state', '!=', 'cancel')],
                ['product_uom_qty'], ['picking_id'], lazy=False):
            uds[dato['picking_id'][0]] = [dato['product_uom_qty'], 0]
        for dato in env['stock.move.line'].sudo().read_group(
                [('picking_id', 'in', picks.ids)], ['qty_done'], ['picking_id'], lazy=False):
            uds.setdefault(dato['picking_id'][0], [0, 0])[1] = dato['qty_done']
        return dict([(k, (v[0], v[1])) for k, v in uds.items()])

    def _excel_web(self, env, picks, etiqueta, dia_desde, dia_hasta):
        salida = io.BytesIO()
        libro = xlsxwriter.Workbook(salida, {'in_memory': True})
        f = self._formatos_excel(libro)
        hoja = libro.add_worksheet('Web')
        cab = ['Fecha de transferencia', 'Documento origen', 'Referencia', 'Marca', 'Transportista',
               'Done Quantity']
        hoja.merge_range(0, 0, 0, len(cab) - 1,
                         'PEDIDOS WEB · %s · %s' % (
                             etiqueta, dia_desde.strftime('%d/%m/%Y') if dia_desde == dia_hasta else
                             '%s - %s' % (dia_desde.strftime('%d/%m/%Y'), dia_hasta.strftime('%d/%m/%Y'))),
                         f['titulo'])
        hoja.write_row(1, 0, cab, f['cab'])
        unidades = {}
        for dato in env['stock.move.line'].sudo().read_group(
                [('picking_id', 'in', picks.ids)], ['qty_done'], ['picking_id'], lazy=False):
            unidades[dato['picking_id'][0]] = dato['qty_done']
        tz = pytz.timezone(request.env.user.tz or comun.TZ)
        for fila, p in enumerate(picks.sorted(key=lambda x: (x.date_done or x.create_date, x.name)), start=2):
            fecha = p.date_done and pytz.utc.localize(p.date_done).astimezone(tz).replace(tzinfo=None) or None
            marca = getattr(p, 'x_studio_marca', False)
            marca = marca and getattr(marca, 'name', '') or ''
            valores = [fecha, p.origin or '', p.name or '', marca, etiqueta, unidades.get(p.id, 0)]
            formatos = [f['fecha'], f['txt'], f['txt'], f['txt'], f['txt'], f['num']]
            for col, valor in enumerate(valores):
                if valor is None:
                    hoja.write_blank(fila, col, None, formatos[col])
                else:
                    hoja.write(fila, col, valor, formatos[col])
        for col, ancho in enumerate([22, 21, 21, 13, 16, 14]):
            hoja.set_column(col, col, ancho)
        hoja.freeze_panes(2, 0)
        hoja.autofilter(1, 0, max(1, 1 + len(picks)), len(cab) - 1)
        hoja.set_landscape()
        hoja.fit_to_pages(1, 0)
        libro.close()
        return salida.getvalue(), len(picks)

    @staticmethod
    def _env():
        return request.env(context=dict(request.env.context, allowed_company_ids=[COMPANY_ID]))

    @staticmethod
    def _dominio_apartado(apartado, transportista):
        """OUT de KOROSHI de ese apartado y transportista, sin condicion de fecha ni de estado."""
        dominio = [
            ('company_id', '=', COMPANY_ID),
            ('picking_type_code', '=', 'outgoing'),
            ('state', '!=', 'cancel'),
        ]
        if apartado == 'tiendas':
            dominio.append(('sale_id.s_order_type_id.name', '=', TIPO_TIENDAS))
            if transportista in ('xpo', 'gls'):
                dominio.append(('carrier_id.name', 'ilike', 'XPO' if transportista == 'xpo' else 'GLS'))
        elif transportista == 'seur':
            # Las dos muestras de Betty separan los pedidos web por su numeracion:
            # W-000... = SEUR; el resto de W-... = GLS.
            dominio.append(('origin', '=like', 'W-000%'))
        else:
            dominio += [('origin', '=like', 'W-%'), ('origin', 'not like', 'W-000%')]
        return dominio

    @staticmethod
    def _adjuntos_etiqueta(env, dominio_extra):
        dominio = [('res_model', '=', 'stock.picking'), '|',
                   ('name', '=like', ETIQUETAS_ADJUNTO[0]), ('name', '=like', ETIQUETAS_ADJUNTO[1])]
        return env['ir.attachment'].sudo().search_read(dominio + dominio_extra, ['res_id', 'create_date'])

    def _tiendas_por_etiqueta(self, env, transportista, inicio, fin):
        """OUT de tiendas cuya etiqueta del transportista se creo entre inicio y fin (UTC).

        La fecha de una expedicion es la de su PRIMERA etiqueta. Se miran todas las OUT con el
        mismo numero de expedicion (una OUT agrupada, p. ej. la -O de outlet, puede no tener
        adjunto propio). Devuelve (OUT, {id OUT: fecha de la etiqueta}, avisos).

        v1.23.2: en XPO cada OUT de la expedicion recibe su propio LabelXPO_. Una OUT de XPO con el
        numero pero SIN etiqueta propia no entro en lo registrado en XPO (K81 12/11: XPO 17, Excel 18):
        no cuenta; sale en avisos {nº expedicion: ['OUT 24900 (1 caja)', ...]}. GLS no cambia.
        """
        Pick = env['stock.picking'].sudo()
        base = self._dominio_apartado('tiendas', transportista) + [
            ('state', '=', 'done'), ('carrier_tracking_ref', '!=', False)]
        del_rango = self._adjuntos_etiqueta(env, [('create_date', '>=', inicio), ('create_date', '<', fin)])
        if not del_rango:
            return Pick.browse(), {}, {}
        con_etiqueta = Pick.search(base + [('id', 'in', list(set([a['res_id'] for a in del_rango])))])
        refs = list(set(con_etiqueta.mapped('carrier_tracking_ref')))
        if not refs:
            return Pick.browse(), {}, {}
        expediciones = Pick.search(base + [('carrier_tracking_ref', 'in', refs)])
        ref_por_out = dict([(p.id, p.carrier_tracking_ref) for p in expediciones])
        primera = {}
        con_adjunto = set()
        for adjunto in self._adjuntos_etiqueta(env, [('res_id', 'in', expediciones.ids)]):
            con_adjunto.add(adjunto['res_id'])
            ref = ref_por_out.get(adjunto['res_id'])
            fecha = adjunto['create_date']
            if ref and (ref not in primera or fecha < primera[ref]):
                primera[ref] = fecha
        # Etiqueta repetida otro dia con el mismo numero: cuenta solo el dia de la primera.
        picks = expediciones.filtered(lambda p: p.carrier_tracking_ref in primera and
                                      inicio <= primera[p.carrier_tracking_ref] < fin)
        avisos = {}
        if transportista == 'xpo':
            sin_etiqueta = picks.filtered(lambda p: p.id not in con_adjunto)
            if sin_etiqueta:
                cajas = self._cajas_por_out(env, sin_etiqueta)
                for p in sin_etiqueta:
                    n = len(cajas.get(p.id, set())) or p.number_of_packages or 0
                    avisos.setdefault(p.carrier_tracking_ref, []).append('OUT %s de %s (%d %s)' % (
                        (p.name or '').replace('EFFEC/OUT/', ''), p.origin or '', n, n == 1 and 'caja' or 'cajas'))
                picks = picks - sin_etiqueta
        fechas = dict([(p.id, primera[p.carrier_tracking_ref]) for p in picks])
        return picks, fechas, avisos

    @staticmethod
    def _extras(env, apartado, transportista, dia_desde, dia_hasta):
        dominio = [
            ('company_id', '=', COMPANY_ID),
            ('apartado', '=', apartado),
            ('dia', '>=', dia_desde),
            ('dia', '<=', dia_hasta),
        ]
        if transportista != 'todos':
            # En el Excel "Todos" salen los añadidos a mano de cualquier transportista.
            dominio.append(('transportista', '=', transportista))
        return env['koroshi.envio.extra'].search(dominio)

    @http.route('/koroshi_monitor/consulta_envios.xlsx', type='http', auth='user')
    def consulta_envios_excel(self, apartado='tiendas', transportista=None, desde=None, hasta=None, **kw):
        _comprobar_grupo()   # v1.27
        apartado = apartado if apartado in PERMITIDOS else 'tiendas'
        transportista = transportista if transportista in PERMITIDOS[apartado] else PERMITIDOS[apartado][0]
        etiqueta = NOMBRES_TRANSPORTISTA[transportista]
        dia_desde, dia_hasta, inicio, fin = self._rango_utc(desde, hasta)
        env = self._env()
        Pick = env['stock.picking'].sudo()
        fechas = {}
        avisos = {}
        if apartado == 'tiendas' and transportista != 'todos':
            # Por la fecha de la etiqueta del transportista, aunque la OUT se validara dias antes.
            picks, fechas, avisos = self._tiendas_por_etiqueta(env, transportista, inicio, fin)
        else:
            # Web, y Tiendas "Todos": OUT validadas en esas fechas (en Tiendas, con y sin transportista).
            picks = Pick.search(self._dominio_apartado(apartado, transportista) + [
                ('state', '=', 'done'), ('date_done', '>=', inicio), ('date_done', '<', fin)])
        # OUT añadidas a mano a alguno de estos dias, en el Excel de este transportista.
        extras = self._extras(env, apartado, transportista, dia_desde, dia_hasta)
        manuales = set(extras.mapped('picking_id').ids)
        picks = (picks | Pick.browse(list(manuales))).filtered(lambda p: p.state != 'cancel')
        picks = picks.sorted(key=lambda p: (p.date_done or p.create_date, p.id))
        if apartado == 'web':
            contenido, _n = self._excel_web(env, picks, etiqueta, dia_desde, dia_hasta)
        else:
            contenido, _n = self._excel_tiendas(env, picks, etiqueta, dia_desde, dia_hasta, fechas, manuales,
                                                avisos)
        nombre = 'envios_%s_%s_%s.xlsx' % (
            apartado, transportista, dia_desde.strftime('%Y-%m-%d') if dia_desde == dia_hasta else
            '%s_%s' % (dia_desde.strftime('%Y-%m-%d'), dia_hasta.strftime('%Y-%m-%d')))
        return request.make_response(contenido, headers=[
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', content_disposition(nombre)),
        ])

    # ------------------------------------------------------------------
    # OUT añadidas a mano a un dia
    # ------------------------------------------------------------------
    def _lista_extras(self, env, apartado, desde, hasta):
        dia_desde, dia_hasta, _inicio, _fin = self._rango_utc(desde, hasta)
        extras = env['koroshi.envio.extra'].search([
            ('company_id', '=', COMPANY_ID),
            ('apartado', '=', apartado),
            ('dia', '>=', dia_desde),
            ('dia', '<=', dia_hasta),
        ])
        filas = []
        for x in extras:
            p = x.picking_id.sudo()
            filas.append({
                'id': x.id,
                'dia': x.dia.strftime('%d/%m/%Y'),
                'transportista': NOMBRES_TRANSPORTISTA.get(x.transportista, x.transportista),
                'pedido': x.pedido or p.origin or '',
                'out': (p.name or '').replace('EFFEC/OUT/', ''),
                'out_id': p.id,
                'estado': self._estado(p),
                'expedicion': p.carrier_tracking_ref or '',
                'usuario': x.create_uid.name or '',
                'cuando': self._hora(x.create_date),
            })
        return filas

    @http.route('/koroshi_monitor/envios_extra/lista', type='json', auth='user')
    def envios_extra_lista(self, apartado='tiendas', desde=None, hasta=None, **kw):
        _comprobar_grupo()   # v1.27
        apartado = apartado if apartado in PERMITIDOS else 'tiendas'
        return {'extras': self._lista_extras(self._env(), apartado, desde, hasta)}

    @staticmethod
    def _buscar_outs(env, apartado, texto):
        """Una OUT por nombre (EFFEC/OUT/24601, OUT/24601 o 24601) o todas las OUT de un pedido."""
        Pick = env['stock.picking'].sudo()
        base = [('company_id', '=', COMPANY_ID), ('picking_type_code', '=', 'outgoing'), ('state', '!=', 'cancel')]
        if apartado == 'web':
            base.append(('origin', '=like', 'W-%'))
        else:
            base.append(('sale_id.s_order_type_id.name', '=', TIPO_TIENDAS))
        t = texto.strip().upper()
        picks = Pick.search(base + [('name', 'in', [t, 'EFFEC/' + t, 'EFFEC/OUT/' + t])])
        if not picks:
            picks = Pick.search(base + ['|', ('origin', '=', t), ('sale_id.name', '=', t)])
        return picks

    @http.route('/koroshi_monitor/envios_extra/anadir', type='json', auth='user')
    def envios_extra_anadir(self, apartado='tiendas', transportista=None, texto=None, dia=None,
                            desde=None, hasta=None, **kw):
        _comprobar_grupo()   # v1.27
        apartado = apartado if apartado in PERMITIDOS else 'tiendas'
        texto = (texto or '').strip()
        env = self._env()
        try:
            dia_fecha = datetime.datetime.strptime(dia or '', '%Y-%m-%d').date()
        except ValueError:
            return {'error': 'Elige el día al que quieres añadirlo.'}
        if len(texto) < 3:
            return {'error': 'Escribe el pedido o la OUT.'}
        picks = self._buscar_outs(env, apartado, texto)
        if not picks:
            return {'error': 'No encuentro «%s» en %s (o está cancelado).' % (
                texto, 'pedidos de tienda' if apartado == 'tiendas' else 'pedidos web')}
        Extra = env['koroshi.envio.extra']
        nuevas = []
        repetidas = []
        for p in picks:
            # Va al Excel de su transportista; si no se reconoce, al elegido en pantalla.
            if apartado == 'tiendas':
                nombre = (p.carrier_id.name or '').upper()
                trans = 'xpo' if 'XPO' in nombre else ('gls' if 'GLS' in nombre else transportista)
            else:
                trans = 'seur' if (p.origin or '').startswith('W-000') else 'gls'
            if trans not in PERMITIDOS[apartado]:
                trans = PERMITIDOS[apartado][0]
            nombre_out = (p.name or '').replace('EFFEC/OUT/', '')
            if Extra.search_count([('picking_id', '=', p.id), ('dia', '=', dia_fecha),
                                   ('apartado', '=', apartado), ('transportista', '=', trans)]):
                repetidas.append(nombre_out)
                continue
            Extra.create({
                'dia': dia_fecha,
                'apartado': apartado,
                'transportista': trans,
                'picking_id': p.id,
                'pedido': p.origin or (p.sale_id and p.sale_id.name) or '',
                'escrito': texto,
                'company_id': COMPANY_ID,
            })
            nuevas.append('%s (%s)' % (nombre_out, NOMBRES_TRANSPORTISTA[trans]))
        return {
            'nuevas': nuevas,
            'repetidas': repetidas,
            'extras': self._lista_extras(env, apartado, desde or dia, hasta or dia),
        }

    @http.route('/koroshi_monitor/envios_extra/quitar', type='json', auth='user')
    def envios_extra_quitar(self, extra_id=None, apartado='tiendas', desde=None, hasta=None, **kw):
        _comprobar_grupo()   # v1.27
        apartado = apartado if apartado in PERMITIDOS else 'tiendas'
        env = self._env()
        try:
            extra_id = int(extra_id or 0)
        except (TypeError, ValueError):
            extra_id = 0
        # Solo se quita la marca «añadido a mano»; la OUT no se toca.
        env['koroshi.envio.extra'].search([('id', '=', extra_id), ('company_id', '=', COMPANY_ID)]).unlink()
        return {'extras': self._lista_extras(env, apartado, desde, hasta)}
