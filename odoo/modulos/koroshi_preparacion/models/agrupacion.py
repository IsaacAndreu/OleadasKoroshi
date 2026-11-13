# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Preparación en Lecturas (v3.15.0) - agrupaciones de zona (Z-) enteras en la pantalla nueva.
#
# Una agrupación Z- son varias OUT (una por tienda) de la misma zona. Se recorre UNA vez, en el orden de la ruta,
# con las líneas de todas sus OUT; cada pieza dice a qué caja de tienda va («CAJA 05 · K34 ...», de la nota de la OUT).
#   leer EAN  -> +1 ud en la línea que se ve (si es de ese artículo) o en la primera pendiente de la ruta
#   leer CJ   -> la caja de la tienda de esa etiqueta (zebra.label «ETQ ZONA <OUT>»): put_in_pack en SU OUT
#   Validar   -> cada OUT con su validación normal (la misma que las OUT sueltas), una detrás de otra.
# La agrupación no se toca (como hoy: se queda «En curso» con todas sus OUT validadas una a una).
# Escribe lo mismo que la pantalla de una OUT (qty_done, put_in_pack, button_validate) y lo apunta igual en
# koroshi.preparacion.lectura. Sin campos nuevos en las tablas de stock; nunca cancela ni fuerza disponibilidad.
# =============================================================================
import json
import re

from werkzeug.urls import url_quote
from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero

from .lectura import COMPANY_ID, PREFIJOS_ZONA, RE_CJ, Ocupada

RE_CAJA_NOTA = re.compile(r'\|\s*CAJA\s+(\d+)\b')   # 'Z-2210-D3 | CAJA 05 | K34 ...' ('CAJAS 3' no)
NOTA_ETIQUETA = 'ETQ ZONA '                          # zebra.label reservada por las etiquetas de zona


class Agrupacion(models.AbstractModel):
    _name = 'koroshi.preparacion.agrupacion'
    _description = 'KOROSHI Preparación: agrupación de zona entera'

    def _l(self):
        # contexto preparacion_lote: la lógica de una OUT acepta también las OUT de una agrupación Z-
        return self.env['koroshi.preparacion.lectura'].with_context(preparacion_lote=True)

    # ------------------------------------------------------------------ qué se prepara aquí
    @api.model
    def _vivas(self, lote):
        return lote.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel')).sorted(
            lambda p: (self._caja_tienda(p) or '99999', p.name or ''))

    @api.model
    def lote_propio(self, lote):
        """Agrupación Z- de la company 8 con OUT por hacer, todas de salida (las INT y lo demás, app de siempre)."""
        L = self._l()
        if not lote or not L.agrupaciones_activas() or not (lote.name or '').startswith(PREFIJOS_ZONA):
            return False
        if lote.company_id and lote.company_id.id != COMPANY_ID:
            return False
        vivas = self._vivas(lote)
        return bool(vivas) and all(L.picking_propio(p, en_lote=True) for p in vivas)

    @api.model
    def _comprobar(self, lote):
        if not lote:
            raise UserError(_('No se encuentra la agrupación.'))
        if not self._vivas(lote):
            raise UserError(_('%s ya no tiene OUT por hacer.') % lote.name)
        if not self.lote_propio(lote):
            raise UserError(_('%s no se prepara aquí: ábrela en la app de código de barras.') % lote.name)

    @api.model
    def _caja_tienda(self, picking):
        """'05' de la nota 'Z-1111-D1 | CAJA 05 | K34 ...' (el número de la caja de la tienda en el carro)."""
        m = RE_CAJA_NOTA.search(self.env['koroshi.preparacion.lectura']._nota(picking) or '')
        return m.group(1) if m else ''

    @api.model
    def _info(self, picking):
        return {'name': picking.name or '', 'tienda': picking.partner_id.name or '', 'caja': self._caja_tienda(picking)}

    @api.model
    def _destino(self, info):
        """«CAJA 05 · K34 TIENDA» (o la OUT si la nota no dice la caja)."""
        if info['caja']:
            return _('CAJA %s · %s') % (info['caja'], info['tienda'] or info['name'])
        return '%s · %s' % (info['name'], info['tienda']) if info['tienda'] else info['name']

    # ------------------------------------------------------------------ estado
    @api.model
    def estado(self, lote, employee=None, ligero=False):
        """El mismo formato que el de una OUT (la PDA pinta igual) + por línea su OUT y su caja de tienda, y la lista
        de OUT ('outs') con lo que tiene cada una fuera de caja."""
        L = self._l()
        vivas = self._vivas(lote)
        mls = vivas.mapped('move_line_ids')
        ordenadas = L._ordenar(mls)
        info = dict((p.id, self._info(p)) for p in vivas)
        fotos, alternativos = {}, {}
        if not ligero:
            productos = ordenadas.mapped('product_id')
            fotos = L._fotos(productos)
            alternativos = L._codigos_alternativos(productos)
        lineas = []
        siguiente = False
        for ml in ordenadas:
            completa = L._completa(ml)
            if ligero:
                lineas.append([ml.id, round(ml.product_uom_qty), round(ml.qty_done), ml.result_package_id.name or '',
                               completa])
            else:
                d = L._linea_json(ml, fotos, alternativos)
                i = info[ml.picking_id.id]
                d.update({'out_id': ml.picking_id.id, 'out_name': i['name'], 'tienda': i['tienda'],
                          'caja_tienda': i['caja']})
                lineas.append(d)
            if not siguiente and not completa and not ml.result_package_id:
                siguiente = ml.id
        outs = []
        sin_caja = 0.0
        cjs = self._cjs_de_outs(vivas)   # v3.22: la PDA sabe sin red de qué tienda es cada CJ
        for p in vivas:
            fuera = sum(L._sin_caja(p).mapped('qty_done'))
            sin_caja += fuera
            i = info[p.id]
            outs.append({'id': p.id, 'name': i['name'], 'tienda': i['tienda'], 'caja': i['caja'],
                         'destino': self._destino(i), 'sin_caja': round(fuera),
                         'pedidas': round(sum(p.move_line_ids.mapped('product_uom_qty'))),
                         'leidas': round(sum(p.move_line_ids.mapped('qty_done'))),
                         'cjs': cjs.get(p.name, [])})
        cajas = {}
        for ml in mls.filtered('result_package_id'):
            cajas.setdefault(ml.result_package_id.name, 0)
            cajas[ml.result_package_id.name] += ml.qty_done
        todo_leido = bool(lineas) and all((l[4] if ligero else l['completa']) for l in lineas)
        return {
            'ligero': ligero,
            'out': {
                'id': lote.id,
                'name': lote.name,
                'es_lote': True,          # v3.15: la PDA manda lote_id en vez de picking_id
                'con_caja': True,
                'tipo': 'Z',
                'tienda': _('%s tiendas') % len(vivas) if len(vivas) != 1 else (vivas.partner_id.name or ''),
                'origen': '',
                'estado': 'done' if not vivas else (lote.state or ''),
                'agrupacion': '',
                'propia': self.lote_propio(lote),
                'nota': '',
            },
            'outs': outs,
            'lineas': lineas,
            'siguiente_id': siguiente,
            'sin_caja': round(sin_caja),
            'cajas': [{'nombre': k, 'uds': round(v)} for k, v in sorted(cajas.items())],
            'pedidas': round(sum(mls.mapped('product_uom_qty'))),
            'leidas': round(sum(mls.mapped('qty_done'))),
            'todo_leido': todo_leido,
            # sin preparar a dos en las agrupaciones (la tarea es de toda la agrupación y de un operario)
            'a_dos': False,
            'rol': 'solo',
            'companeros': [],
            'mitad': '',
            'aviso_equipo': '',
            'faltantes_companero': [],
            'mias_sin_caja': round(sin_caja),
            'otros_sin_caja': 0,
            'alarma_min': L.minutos_alarma(),   # v3.22
            'alarma_horario': L.horario_alarma(),   # v3.23
        }

    # ------------------------------------------------------------------ leer un producto
    @api.model
    def leer(self, lote, employee, codigo, id_lectura=False, linea_id=False):
        """+1 ud del artículo leído: en la línea que se ve si es de ese artículo (linea_id) o en la primera pendiente
        de la ruta. Dice a qué caja de tienda va."""
        L = self._l()
        codigo = (codigo or '').strip()
        previa = L._repetida(id_lectura)
        if previa:
            return {'ok': previa.resultado == 'ok', 'msg': previa.mensaje, 'linea_id': previa.move_line_id.id,
                    'que': 'repetida'}
        self._comprobar(lote)
        if RE_CJ.match(codigo):
            return {'ok': False, 'que': 'es_caja', 'msg': _('Es una caja: pulsa «Caja» antes de leerla.')}
        tarjeta = self.env['hr.employee'].sudo().search([('barcode', '=', codigo)], limit=1)
        if tarjeta:
            return {'ok': False, 'que': 'es_tarjeta',
                    'msg': _('Es la tarjeta de %s. Para cambiar de operario vuelve a Lecturas (←).') % tarjeta.name}
        vivas = self._vivas(lote)
        ordenadas = L._ordenar(vivas.mapped('move_line_ids'))
        producto, en_lote = L._producto_entre(ordenadas.mapped('product_id'), codigo)
        if not producto:
            ubicacion = self.env['stock.location'].sudo().search([('barcode', '=', codigo)], limit=1)
            if ubicacion:
                return {'ok': False, 'que': 'ubicacion',
                        'msg': _('En %s no hay nada de esta agrupación.') % (ubicacion.name or codigo)}
            msg = L._msg_desconocido(codigo)   # v3.18
            L._apuntar(False, employee, 'leer', codigo, 'error', msg, id_lectura=id_lectura)
            return {'ok': False, 'que': 'desconocido', 'msg': msg}
        pendiente = lambda l: not l.result_package_id and float_compare(
            l.qty_done, l.product_uom_qty, precision_digits=3) < 0
        if not en_lote:
            hermanas = L._hermanas_en(ordenadas, producto)
            if hermanas:
                msg = _('Has leído la talla %s. Toca %s de %s. No cuenta.') % (
                    L._talla(producto), L._tallas_texto(hermanas), L._modelo(producto))
                L._apuntar(False, employee, 'leer', codigo, 'error', msg, id_lectura=id_lectura,
                           producto=producto.display_name)
                return {'ok': False, 'que': 'talla_hermana', 'msg': msg, 'linea_id': hermanas[0].id}
            msg = _('%s no es de esta agrupación. No cuenta.') % L._corto(producto)
            L._apuntar(False, employee, 'leer', codigo, 'error', msg, id_lectura=id_lectura,
                       producto=producto.display_name)
            return {'ok': False, 'que': 'no_es_del_pedido', 'msg': msg}
        candidatas = ordenadas.filtered(lambda l: l.product_id == producto and pendiente(l))
        if not candidatas:
            total = sum(ordenadas.filtered(lambda l: l.product_id == producto).mapped('product_uom_qty'))
            msg = _('Ya tienes todas las uds de %s (%s). No cuenta.') % (L._corto(producto), round(total))
            hermanas = L._hermanas_en(ordenadas, producto)
            if hermanas:
                msg = _('Ya tienes todas las de la talla %s. Falta %s de %s. No cuenta.') % (
                    L._talla(producto), L._tallas_texto(hermanas), L._modelo(producto))
            L._apuntar(False, employee, 'leer', codigo, 'error', msg, id_lectura=id_lectura,
                       producto=producto.display_name)
            if hermanas:
                return {'ok': False, 'que': 'talla_hermana', 'msg': msg, 'linea_id': hermanas[0].id}
            return {'ok': False, 'que': 'completo', 'msg': msg}
        preferida = candidatas.filtered(lambda l: l.id == int(linea_id or 0))
        ml = preferida or candidatas[0]
        L._bloquear(ml.picking_id)
        # otra PDA puede haberla completado o metido en caja justo antes de bloquear: se vuelve a mirar
        ml.invalidate_cache(['qty_done', 'result_package_id'], ml.ids)
        if not pendiente(ml):
            raise Ocupada(_('Otra PDA acaba de leer esa línea. Se vuelve a probar sola.'))
        res = L._sumar(ml.picking_id, employee, codigo, ml, id_lectura)
        destino = self._destino(self._info(ml.picking_id))
        res.update({'out_id': ml.picking_id.id, 'destino': destino,
                    'msg': '%s → %s (%s de %s)' % (L._corto(producto), destino, round(ml.qty_done),
                                                  round(ml.product_uom_qty))})
        return res

    # ------------------------------------------------------------------ deshacer / cantidad
    @api.model
    def deshacer(self, lote, employee):
        self._comprobar(lote)
        dominio = [('picking_id', 'in', self._vivas(lote).ids), ('tipo', '=', 'leer'), ('resultado', '=', 'ok'),
                   ('deshecha', '=', False), ('en_caja', '=', False)]
        if employee:
            dominio.append(('employee_id', '=', employee.id))
        ultima = self.env['koroshi.preparacion.lectura'].sudo().search(dominio, limit=1)
        if not ultima or not ultima.move_line_id:
            return {'ok': False, 'msg': _('No hay ninguna lectura tuya que deshacer en %s.') % lote.name}
        return self._l().deshacer(ultima.picking_id, employee)

    @api.model
    def poner_cantidad(self, lote, employee, linea_id, cantidad, id_lectura=False):
        self._comprobar(lote)
        ml = self.env['stock.move.line'].browse(int(linea_id or 0)).exists()
        if not ml or ml.picking_id not in self._vivas(lote):
            return {'ok': False, 'msg': _('Esa línea ya no está en %s. Vuelve a cargar la agrupación.') % lote.name}
        res = self._l().poner_cantidad(ml.picking_id, employee, linea_id, cantidad, id_lectura)
        if res.get('ok'):
            res['destino'] = self._destino(self._info(ml.picking_id))
        return res

    # ------------------------------------------------------------------ cerrar caja
    @api.model
    def _cjs_de_outs(self, pickings):
        """v3.22: {nombre de OUT: [CJ reservadas para ella]} (zebra.label con nota «ETQ ZONA <OUT>»)."""
        if not pickings or 'zebra.label' not in self.env:
            return {}
        notas = [NOTA_ETIQUETA + n for n in pickings.mapped('name')]
        res = {}
        for et in self.env['zebra.label'].sudo().search_read([('note', 'in', notas)], ['name', 'note']):
            res.setdefault((et['note'] or '')[len(NOTA_ETIQUETA):].strip(), []).append((et['name'] or '').upper())
        return res

    @api.model
    def _out_de_etiqueta(self, codigo):
        """La OUT para la que se reservó la matrícula (zebra.label con nota «ETQ ZONA <OUT>»), si la hay."""
        if 'zebra.label' not in self.env:
            return self.env['stock.picking']
        etiqueta = self.env['zebra.label'].sudo().search([('name', '=', codigo)], limit=1)
        nota = (etiqueta.note or '').strip() if etiqueta else ''
        if not nota.startswith(NOTA_ETIQUETA):
            return self.env['stock.picking']
        return self.env['stock.picking'].sudo().search([('name', '=', nota[len(NOTA_ETIQUETA):].strip())], limit=1)

    @api.model
    def caja(self, lote, employee, codigo, id_lectura=False, out_id=False):
        """La CJ leída dice la tienda (su etiqueta de zona): en esa caja va lo leído de SU OUT y aún sin caja.
        Si la etiqueta no es de ninguna OUT (CJ suelta): la OUT de la línea que se ve, o la única con algo leído."""
        L = self._l()
        codigo = (codigo or '').strip().upper()
        previa = L._repetida(id_lectura)
        if previa:
            return {'ok': previa.resultado == 'ok', 'msg': previa.mensaje, 'que': 'repetida'}
        self._comprobar(lote)
        if not RE_CJ.match(codigo):
            return {'ok': False, 'msg': _('%s no es una etiqueta de caja (CJ + 9 cifras). Lee la etiqueta de la caja.')
                    % codigo}
        vivas = self._vivas(lote)
        con_algo = vivas.filtered(lambda p: L._sin_caja(p))
        if not con_algo:
            return {'ok': False, 'msg': _('No hay nada leído fuera de caja: lee algún artículo antes de cerrar la caja.')}
        destino = self._out_de_etiqueta(codigo)
        if destino and destino not in vivas:
            return {'ok': False, 'msg': _('La caja %s es de %s (%s), no de esta agrupación. No se cierra.') % (
                codigo, destino.name, destino.partner_id.name or '')}
        if not destino:
            # una caja que ya tiene una OUT de la agrupación (se vuelve a abrir para meter más)
            ya = vivas.mapped('move_line_ids').filtered(lambda l: l.result_package_id.name == codigo)
            destino = ya[:1].picking_id
        if not destino and out_id:
            destino = con_algo.filtered(lambda p: p.id == int(out_id))
        if not destino and len(con_algo) == 1:
            destino = con_algo
        if not destino:
            return {'ok': False, 'que': 'caja_sin_tienda',
                    'msg': _('La caja %s no tiene tienda. Lee la etiqueta de la caja de la tienda (la de «CAJA nn»).')
                    % codigo}
        info = self._info(destino)
        if destino not in con_algo:
            return {'ok': False, 'msg': _('%s: no hay nada leído fuera de caja para esta tienda.') % self._destino(info)}
        res = L.caja(destino, employee, codigo, id_lectura)
        res['out_id'] = destino.id
        if res.get('ok'):
            res['msg'] = '%s: %s' % (self._destino(info), res.get('msg') or '')
        return res

    # ------------------------------------------------------------------ validar
    @api.model
    def validar(self, lote, employee, pedido_pendiente=None):
        """Todo leído (o en faltantes) y en caja -> cada OUT con su validación normal (button_validate, todo o nada
        por OUT). Si Odoo pregunta por el pedido pendiente, se pregunta una vez y vale para las que quedan."""
        L = self._l()
        self._comprobar(lote)
        vivas = self._vivas(lote)
        fuera = [(p, sum(L._sin_caja(p).mapped('qty_done'))) for p in vivas]
        fuera = [(p, n) for p, n in fuera if float_compare(n, 0, precision_digits=3) > 0]
        if fuera:
            detalle = ', '.join('%s (%s)' % (self._destino(self._info(p)), round(n)) for p, n in fuera)
            return {'ok': False, 'que': 'sin_caja',
                    'msg': _('Hay uds sin caja en %s: pulsa «Caja» y lee su etiqueta antes de validar.') % detalle}
        Faltante = self.env['koroshi.faltante']
        pendientes = Faltante.lineas_pendientes(vivas)
        if pendientes:
            return {'ok': False, 'que': 'quedan', 'n': len(pendientes),
                    'msg': _('Quedan %s líneas por coger: léelas o pulsa «Faltante».') % len(pendientes)}
        if pedido_pendiente not in ('si', 'no'):
            fijo = L._param('koroshi_faltantes.pedido_pendiente', 'no')
            pedido_pendiente = fijo if fijo in ('si', 'no') else None
        validadas = []
        errores = []
        for p in vivas:
            info = self._info(p)
            if float_is_zero(sum(p.move_line_ids.mapped('qty_done')), precision_digits=3):
                errores.append(_('%s: no hay nada leído') % self._destino(info))
                continue
            try:
                # la validación de las OUT sueltas (koroshi_faltantes), sin su «se valida desde la agrupación»
                r = Faltante._todo_o_nada(Faltante._validar_out, p, pedido_pendiente)
            except (UserError, ValidationError) as e:
                msg = e.name if hasattr(e, 'name') else str(e)
                L._apuntar(p, employee, 'validar', p.name, 'error', msg)
                errores.append('%s: %s' % (self._destino(info), msg))
                continue
            if r['estado'] == 'preguntar':
                self._cerrar_tareas()
                txt = _('Faltan uds. ¿Crear un pedido pendiente con lo que falta?')
                if validadas:
                    txt = _('%s OUT validadas. ') % len(validadas) + txt
                return {'ok': True, 'que': 'preguntar', 'msg': txt}
            L._apuntar(p, employee, 'validar', p.name, 'ok', _('%s validada (agrupación %s).') % (p.name, lote.name))
            validadas.append(p)
        self._cerrar_tareas()
        if errores:
            txt = (_('%s OUT validadas. ') % len(validadas) if validadas else '') + _('Sin validar: ') + '; '.join(errores)
            return {'ok': False, 'que': 'no_validada', 'msg': txt}
        return {'ok': True, 'que': 'validada', 'msg': _('%s: %s OUT validadas.') % (lote.name, len(validadas))}

    @api.model
    def _cerrar_tareas(self):
        try:
            # cierra ya la tarea del operario si la agrupación está entera (lo mismo que tras validar una OUT)
            with self.env.cr.savepoint():
                self.env['koroshi.operario.tarea'].sudo().cron_cerrar()
        except Exception:
            pass

    # ------------------------------------------------------------------ imprimir
    @api.model
    def impresos(self, lote):
        """Etiquetas de caja (OUT + matrícula) y albaranes de las OUT por hacer de la agrupación. Solo lectura."""
        vivas = self._vivas(lote)
        if not vivas:
            return []
        res = []
        Informe = self.env['ir.actions.report'].sudo()
        # v3.7.2: los PDF necesitan la empresa de la OUT en la dirección (si no, 403 por multiempresa)
        sufijo = '?context=' + url_quote(json.dumps({'allowed_company_ids': [vivas[0].company_id.id or COMPANY_ID]}))
        ids = ','.join(str(i) for i in vivas.ids)
        if Informe.search([('report_name', '=', 'koroshi.report_etiqueta_zona')], limit=1):
            res.append({'nombre': _('Etiquetas de caja de todas las tiendas'),
                        'detalle': _('%s OUT. Las matrículas que ya tienen reservadas.') % len(vivas),
                        'url': '/report/pdf/koroshi.report_etiqueta_zona/%s%s' % (ids, sufijo)})
        if Informe.search([('report_name', '=', 'stock.report_deliveryslip')], limit=1):
            res.append({'nombre': _('Albaranes de todas las tiendas'), 'detalle': lote.name,
                        'url': '/report/pdf/stock.report_deliveryslip/%s%s' % (ids, sufijo)})
        return res
