# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Recepción por contenedor: rutas de la pantalla (PDA o tablet) y la exportación.
# En la PDA todos entran con el mismo usuario de Odoo («Almacén Nath»): quién hace cada cosa va por la tarjeta del
# operario (hr.employee), y validar solo lo puede quien está en «Responsables de recepción».
# La lectura es a ciegas: estas rutas no dan el teórico de las IN salvo /comparar (responsable).
# =============================================================================
import logging

from odoo import fields, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import content_disposition, request

from odoo.addons.koroshi_base import comun
from odoo.addons.koroshi_recepcion import logica as L

_logger = logging.getLogger(__name__)

MAX_BUSCAR = 30
MAX_ULTIMAS = 15
DE_LA_COMPANIA = ('company_id', 'in', [comun.COMPANY_ID, False])


def _msg(e):
    return e.args[0] if e.args else str(e)


def _local(dt):
    loc = comun.a_local(dt)
    return loc and loc.strftime('%d/%m/%Y %H:%M') or ''


class KoroshiRecepcionPantalla(http.Controller):

    # ------------------------------------------------------------------ ayudas
    def _comprobar_usuario(self):
        if not request.env.user.has_group('stock.group_stock_user'):
            raise UserError('No tienes permiso para recepcionar.')

    def _recepcion(self, recepcion_id):
        r = request.env['koroshi.recepcion'].sudo().browse(int(recepcion_id or 0)).exists()
        if not r:
            raise UserError('No encuentro esa recepción.')
        return r

    def _empleado(self, employee_id, obligatorio=True):
        emp = request.env['hr.employee'].sudo().browse(int(employee_id or 0)).exists()
        if not emp and obligatorio:
            raise UserError('Primero pasa tu tarjeta de operario.')
        return emp

    def _responsable(self, employee_id):
        emp = self._empleado(employee_id)
        if not request.env['koroshi.recepcion.responsable'].es_responsable(emp):
            raise UserError('%s no es responsable de recepciones: no puede comparar ni validar.' % emp.name)
        return emp

    def _buscar_producto(self, codigo):
        """Prenda por EAN (y UPC/EAN con 0 delante), código alternativo, referencia interna o nombre (como en
        Contenedores)."""
        variantes = [codigo]
        if codigo.isdigit() and len(codigo) == 12:
            variantes.append('0' + codigo)
        if codigo.isdigit() and len(codigo) == 13 and codigo.startswith('0'):
            variantes.append(codigo[1:])
        Product = request.env['product.product'].sudo()
        p = Product.search([('barcode', 'in', variantes)], limit=1)
        if not p and 'product.barcode' in request.env:
            p = request.env['product.barcode'].sudo().search([('name', 'in', variantes)], limit=1).product_id
        if not p:
            p = Product.search([('default_code', '=', codigo)], limit=1)
        if not p:
            p = Product.search([('name', '=', codigo), DE_LA_COMPANIA], limit=1)
        return p

    def _prod(self, p, r=None):
        modelo, color, talla = L.partes_referencia(p.default_code or p.name)
        return {'id': p.id, 'nombre': p.display_name, 'modelo': ('%s-%s' % (modelo, color)) if color else modelo,
                'talla': talla, 'ean': p.barcode or '', 'base': L.modelo_de(p.default_code or p.name)}

    def _datos_recepcion(self, r, employee=None):
        ins = r._todas_las_in().sorted(lambda p: (p.scheduled_date or fields.Datetime.now(), p.id))
        ok = r.lectura_ids.filtered(lambda l: l.estado == 'ok')
        return {
            'id': r.id, 'name': r.name, 'matricula': r.matricula, 'referencia': r.referencia or '',
            'muelle': r.muelle or '', 'llegada': _local(r.fecha_llegada), 'state': r.state,
            'cajas': r.cajas, 'palets': r.palets, 'contenedores': len(r.contenedor_ids),
            'cajas_leidas': len({l.caja_txt for l in ok}), 'lecturas': len(ok),
            'uds_leidas': sum(ok.mapped('cantidad')), 'uds_validadas': sum(ok.filtered('validada').mapped('cantidad')),
            'ins': [{'id': p.id, 'name': p.name, 'origen': p.origin or '', 'ref': (p.x_studio_order_remarks or '').strip()
                     if 'x_studio_order_remarks' in p._fields else '', 'fecha': _local(p.scheduled_date),
                     'estado': dict(p._fields['state'].selection).get(p.state, p.state),
                     'uds': sum(p.move_lines.filtered(lambda m: m.state != 'cancel').mapped('product_uom_qty'))}
                    for p in ins],
            'palets_lista': [{'id': l.id, 'nombre': l.name} for l in r.palets_existentes()
                             if L.numero_palet(l.name)[0] <= (r.palets or 0)],
            'tanda_id': r.tanda_ids[:1].id or False,
            'responsable': bool(employee) and request.env['koroshi.recepcion.responsable'].es_responsable(employee),
        }

    def _ultimas(self, r):
        ls = r.lectura_ids.filtered(lambda l: l.estado == 'ok').sorted('id', reverse=True)[:MAX_ULTIMAS]
        return [{'id': l.id, 'caja': l.caja_txt, 'pedido': l.pedido or '', 'ajeno': l.pedido_ajeno,
                 'palet': l.palet_id.name, 'producto': l.producto_id.display_name or 'Modelo %s' % (l.modelo or '?'),
                 'uds': l.cantidad, 'quien': l.employee_id.name or '', 'hora': _local(l.fecha)[-5:],
                 'validada': l.validada} for l in ls]

    # ------------------------------------------------------------------ lista, nueva, ficha
    @http.route('/koroshi/recepcion/inicio', type='json', auth='user')
    def inicio(self, employee_id=False, **kw):
        try:
            self._comprobar_usuario()
            emp = self._empleado(employee_id, obligatorio=False)
            rs = request.env['koroshi.recepcion'].sudo().search([('state', 'in', ('pendiente', 'leyendo'))],
                                                                order='fecha_llegada desc, id desc', limit=50)
            # las validadas que dejaron IN pendientes (cajas que llegan después): para «Reabrir»
            validadas = request.env['koroshi.recepcion'].sudo().search(
                [('state', '=', 'validada')], order='fecha_llegada desc, id desc', limit=30)
            rs |= validadas.filtered(lambda x: x._in_abiertas())
            return {'ok': True, 'recepciones': [{
                'id': r.id, 'name': r.name, 'matricula': r.matricula, 'muelle': r.muelle or '',
                'llegada': _local(r.fecha_llegada), 'state': r.state, 'cajas': r.cajas,
                'cajas_leidas': len({l.caja_txt for l in r.lectura_ids if l.estado == 'ok'}),
                'ins': ', '.join(o for o in r.picking_ids.mapped('origin') if o)} for r in rs],
                'responsable': bool(emp) and request.env['koroshi.recepcion.responsable'].es_responsable(emp)}
        except UserError as e:
            request.env.cr.rollback()     # nada a medias
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/koroshi/recepcion/ins', type='json', auth='user')
    def ins(self, recepcion_id=False, **kw):
        """IN de KOROSHI abiertas para elegir las que trae un contenedor (con la referencia del proveedor y sus uds)."""
        try:
            self._comprobar_usuario()
            Rec = request.env['koroshi.recepcion'].sudo()
            abiertas = Rec.ins_abiertas()
            otras = Rec.search([('state', 'in', ('pendiente', 'leyendo')), ('id', '!=', int(recepcion_id or 0)),
                                ('picking_ids', 'in', abiertas.ids)])
            en_otra = {}
            for o in otras:
                for p in o.picking_ids:
                    en_otra[p.id] = '%s (%s)' % (o.name, o.matricula)
            con_ref = 'x_studio_order_remarks' in request.env['stock.picking']._fields
            return {'ok': True, 'ins': [{
                'id': p.id, 'name': p.name, 'origen': p.origin or '',
                'ref': (p.x_studio_order_remarks or '').strip() if con_ref else '',
                'fecha': _local(p.scheduled_date)[:10], 'backorder': bool(p.backorder_id),
                'uds': sum(p.move_lines.filtered(lambda m: m.state != 'cancel').mapped('product_uom_qty')),
                'en_otra': en_otra.get(p.id, '')} for p in abiertas]}
        except UserError as e:
            request.env.cr.rollback()     # nada a medias
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/koroshi/recepcion/crear', type='json', auth='user')
    def crear(self, matricula='', muelle='', referencia='', picking_ids=None, employee_id=False, **kw):
        try:
            self._comprobar_usuario()
            emp = self._empleado(employee_id)
            matricula = (matricula or '').strip().upper()
            if len(matricula) < 4:
                raise UserError('Escribe la matrícula del contenedor (la de la puerta o el lateral).')
            r = request.env['koroshi.recepcion'].sudo().create({
                'matricula': matricula, 'muelle': (muelle or '').strip(), 'referencia': (referencia or '').strip(),
                'picking_ids': [(6, 0, [int(i) for i in (picking_ids or [])])]})
            r.message_post(body='Creada desde la pantalla por %s.' % emp.name)
            return {'ok': True, 'recepcion': self._datos_recepcion(r, emp)}
        except UserError as e:
            request.env.cr.rollback()     # nada a medias
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/koroshi/recepcion/ficha', type='json', auth='user')
    def ficha(self, recepcion_id=False, employee_id=False, **kw):
        try:
            self._comprobar_usuario()
            r = self._recepcion(recepcion_id)
            emp = self._empleado(employee_id, obligatorio=False)
            return {'ok': True, 'recepcion': self._datos_recepcion(r, emp), 'ultimas': self._ultimas(r)}
        except UserError as e:
            request.env.cr.rollback()     # nada a medias
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/koroshi/recepcion/enlazar', type='json', auth='user')
    def enlazar(self, recepcion_id=False, picking_ids=None, employee_id=False, **kw):
        """Cambia las IN del contenedor. Con algo ya validado, solo se pueden añadir (lo comprueba el modelo)."""
        try:
            self._comprobar_usuario()
            emp = self._empleado(employee_id)
            r = self._recepcion(recepcion_id)
            r.write({'picking_ids': [(6, 0, [int(i) for i in (picking_ids or [])])]})
            r.message_post(body='IN cambiadas por %s: %s.' % (emp.name, ', '.join(r.picking_ids.mapped('name')) or '-'))
            return {'ok': True, 'recepcion': self._datos_recepcion(r, emp)}
        except UserError as e:
            request.env.cr.rollback()     # nada a medias
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/koroshi/recepcion/recepcionar', type='json', auth='user')
    def recepcionar(self, recepcion_id=False, cajas=0, palets=0, muelle='', employee_id=False, **kw):
        try:
            self._comprobar_usuario()
            emp = self._empleado(employee_id)
            r = self._recepcion(recepcion_id)
            tanda = r.recepcionar(cajas, palets, muelle, emp)
            return {'ok': True, 'recepcion': self._datos_recepcion(r, emp), 'tanda_id': tanda.id or False,
                    'tanda': tanda.name or ''}
        except (UserError, ValueError) as e:
            request.env.cr.rollback()     # nada a medias
            return {'ok': False, 'msg': _msg(e)}
        except Exception as e:            # p. ej. dos PDA creando KO_ a la vez: el mismo número
            request.env.cr.rollback()
            _logger.exception('koroshi_recepcion: error al recepcionar %s', recepcion_id)
            return {'ok': False, 'msg': 'No se ha creado nada (%s). Vuelve a probar en un momento.' % e}

    # ------------------------------------------------------------------ leer
    @http.route('/koroshi/recepcion/leer', type='json', auth='user')
    def leer(self, recepcion_id=False, codigo='', **kw):
        """Un código leído: tarjeta, palé (PAL-03 A), caja (KO_) o artículo (EAN o referencia)."""
        try:
            self._comprobar_usuario()
            codigo = (codigo or '').strip()
            if not codigo:
                raise UserError('Código vacío.')
            r = self._recepcion(recepcion_id) if recepcion_id else None
            emp = request.env['hr.employee'].sudo().search([('barcode', '=', codigo)], limit=1)
            if emp:
                return {'ok': True, 'tipo': 'persona', 'persona': {
                    'id': emp.id, 'nombre': emp.name,
                    'responsable': request.env['koroshi.recepcion.responsable'].es_responsable(emp)}}
            Loc = request.env['stock.location'].sudo()
            nombre_palet = L.palet_de(codigo)
            if nombre_palet:
                padre = request.env['koroshi.recepcion'].sudo().padre_palets()
                loc = padre and Loc.search([('location_id', '=', padre.id), ('name', '=', nombre_palet)], limit=1)
                if not loc:
                    raise UserError('El palé %s no existe todavía: créalo con «+ palés».' % nombre_palet)
                return {'ok': True, 'tipo': 'palet', 'palet': {'id': loc.id, 'nombre': loc.name}}
            if codigo.upper()[:3] in ('KO_', 'TT_'):
                loc = Loc.search([('usage', '=', 'internal'), DE_LA_COMPANIA, '|', ('name', '=', codigo.upper()),
                                  ('barcode', '=', codigo.upper())], limit=2)
                if not loc:
                    raise UserError('No encuentro la caja %s.' % codigo)
                if len(loc) > 1:
                    raise UserError('Hay %d ubicaciones llamadas %s. Avisa a IT.' % (len(loc), codigo))
                # 1.1.0: la caja es su nº escrito a mano; un KO_ leído vale como nº de caja (texto)
                return {'ok': True, 'tipo': 'caja', 'caja': {'id': False, 'nombre': loc.name}}
            p = self._buscar_producto(codigo)
            if p:
                return {'ok': True, 'tipo': 'producto', 'producto': self._prod(p)}
            raise UserError('No encuentro nada con «%s»: ni tarjeta, palé, caja ni artículo. Prueba con el buscador.'
                            % codigo)
        except UserError as e:
            request.env.cr.rollback()     # nada a medias
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/koroshi/recepcion/buscar', type='json', auth='user')
    def buscar(self, recepcion_id=False, texto='', **kw):
        """Buscador táctil: los últimos dígitos del EAN (8136) o un trozo del modelo o la descripción («27 onde»).
        Primero los artículos de las IN del contenedor (sin decir cuántos vienen: la lectura es a ciegas)."""
        try:
            self._comprobar_usuario()
            texto = (texto or '').strip()
            if len(texto) < 3:
                raise UserError('Escribe al menos 3 letras o los últimos 4 números del código de barras.')
            Product = request.env['product.product'].sudo()
            de_las_in = Product.browse()
            if recepcion_id:
                r = self._recepcion(recepcion_id)
                de_las_in = r._todas_las_in().mapped('move_lines.product_id')
            if L.es_final_ean(texto):
                dominio = [('barcode', '=like', '%' + texto)]
            else:
                dominio = []
                for trozo in texto.split():
                    dominio += ['|', ('default_code', 'ilike', trozo), ('name', 'ilike', trozo)]
            if kw.get('modelos'):
                # 1.2.0: lista de MODELOS (2711JA22), primero los de las IN del contenedor
                en_in = {L.modelo_de(p.default_code or p.name) for p in de_las_in}
                vistos = {}
                for p in Product.search(dominio + [DE_LA_COMPANIA], limit=500, order='default_code, id'):
                    m = L.modelo_de(p.default_code or p.name)
                    if m and m not in vistos:
                        vistos[m] = p
                lista = sorted(vistos, key=lambda m: (m not in en_in, m))[:MAX_BUSCAR]
                return {'ok': True, 'modelos': [{'modelo': m, 'nombre': (vistos[m].name or '')[:60],
                                                 'en_in': m in en_in} for m in lista],
                        'mas': len(vistos) > MAX_BUSCAR}
            primero = Product.search(dominio + [('id', 'in', de_las_in.ids)]) if de_las_in else Product.browse()
            resto = Product.search(dominio + [DE_LA_COMPANIA, ('id', 'not in', primero.ids)],
                                   limit=MAX_BUSCAR, order='default_code, id')
            lista = (primero.sorted(lambda p: (p.default_code or p.name or '')) | resto)[:MAX_BUSCAR]
            return {'ok': True, 'productos': [dict(self._prod(p), en_in=p in primero) for p in lista],
                    'mas': len(lista) >= MAX_BUSCAR}
        except UserError as e:
            request.env.cr.rollback()     # nada a medias
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/koroshi/recepcion/guardar', type='json', auth='user')
    def guardar(self, recepcion_id=False, caja='', pedido='', palet_id=False, producto_id=False, cantidad=0,
                employee_id=False, token=None, modelo='', **kw):
        """1.1.0: caja = el nº escrito a mano (texto); pedido = ORDER NUMBER de la etiqueta (opcional).
        1.2.0: con «modelo» (sin producto) = una caja apuntada por modelo con sus uds totales; no toca stock."""
        try:
            self._comprobar_usuario()
            emp = self._empleado(employee_id)
            r = self._recepcion(recepcion_id)
            palet = request.env['stock.location'].sudo().browse(int(palet_id or 0)).exists()
            if not palet:
                raise UserError('Falta el palé: tócalo arriba o lee su etiqueta.')
            if modelo and not producto_id:
                lectura = r.guardar_caja(caja, pedido, palet, modelo, cantidad, emp, token)
            else:
                prod = request.env['product.product'].sudo().browse(int(producto_id or 0)).exists()
                lectura = r.guardar_lectura(caja, pedido, palet, prod, cantidad, emp, token)
            avisos = r.avisos_lectura(lectura)
            return {'ok': True, 'msg': '%s · %s · %d uds → %s / caja %s' % (
                emp.name, lectura.producto_id.display_name or 'Modelo %s' % lectura.modelo, lectura.cantidad,
                lectura.palet_id.name,
                lectura.caja_txt), 'avisos': avisos,
                'recepcion': self._datos_recepcion(r, emp), 'ultimas': self._ultimas(r)}
        except (UserError, ValueError) as e:
            request.env.cr.rollback()     # nada a medias
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/koroshi/recepcion/anular', type='json', auth='user')
    def anular(self, lectura_id=False, employee_id=False, **kw):
        try:
            self._comprobar_usuario()
            emp = self._empleado(employee_id)
            l = request.env['koroshi.recepcion.lectura'].sudo().browse(int(lectura_id or 0)).exists()
            if not l:
                raise UserError('No encuentro esa lectura.')
            r = l.recepcion_id
            l.anular()
            r.message_post(body='Lectura anulada por %s: %s %d uds en la caja %s.' % (
                emp.name, l.producto_id.display_name or 'Modelo %s' % l.modelo, l.cantidad, l.caja_txt))
            return {'ok': True, 'recepcion': self._datos_recepcion(r, emp), 'ultimas': self._ultimas(r)}
        except UserError as e:
            request.env.cr.rollback()     # nada a medias
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/koroshi/recepcion/siguiente', type='json', auth='user')
    def siguiente(self, recepcion_id=False, **kw):
        try:
            self._comprobar_usuario()
            loc = self._recepcion(recepcion_id).siguiente_contenedor()
            if not loc:
                raise UserError('Ya no quedan cajas sin leer de esta recepción: crea más con «+ cajas».')
            return {'ok': True, 'caja': {'id': loc.id, 'nombre': loc.name}}
        except UserError as e:
            request.env.cr.rollback()     # nada a medias
            return {'ok': False, 'msg': _msg(e)}

    # ------------------------------------------------------------------ comparar y validar (responsable)
    @http.route('/koroshi/recepcion/comparar', type='json', auth='user')
    def comparar(self, recepcion_id=False, employee_id=False, **kw):
        try:
            self._comprobar_usuario()
            self._responsable(employee_id)
            r = self._recepcion(recepcion_id)
            # 1.2.0: por modelo (sin tallas): cajas, uds de las IN y uds llegadas, y dónde está cada caja
            lista = [{'modelo': f.modelo, 'cajas': f.cajas, 'teorico': f.teorico, 'leido': f.leido,
                      'diferencia': f.diferencia, 'estado': f.estado, 'donde': f.donde or '',
                      'problema': f.estado != 'ok', 'filas': []} for f in r.comparar()]
            cajas = r.resumen_cajas()
            return {'ok': True, 'modelos': lista,
                    'cajas': {'leidas': len(cajas['leidas']), 'esperadas': r.cajas or 0,
                              'huecos': [str(n) for n in cajas['huecos']], 'n_huecos': cajas['n_huecos'],
                              'ajenas': [{'caja': c, 'pedido': p} for c, p in cajas['ajenas']]},
                    'total': {'teorico': sum(m['teorico'] for m in lista), 'leido': sum(m['leido'] for m in lista)},
                    'sin_validar': sum(r.lectura_ids.filtered(lambda l: l.estado == 'ok' and not l.validada)
                                       .mapped('cantidad'))}
        except UserError as e:
            request.env.cr.rollback()     # nada a medias
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/koroshi/recepcion/validar', type='json', auth='user')
    def validar(self, recepcion_id=False, employee_id=False, parcial=False, **kw):
        try:
            self._comprobar_usuario()
            emp = self._responsable(employee_id)
            r = self._recepcion(recepcion_id)
            res = r.validar(parcial=bool(parcial), employee=emp)
            return {'ok': True, 'resultado': res, 'recepcion': self._datos_recepcion(r, emp)}
        except (UserError, ValidationError) as e:
            request.env.cr.rollback()     # nada a medias: ni líneas hechas ni IN validadas
            return {'ok': False, 'msg': 'No se ha validado nada. %s' % _msg(e)}
        except Exception as e:
            request.env.cr.rollback()
            _logger.exception('koroshi_recepcion: error al validar la recepción %s', recepcion_id)
            return {'ok': False, 'msg': 'No se ha validado nada: error de Odoo (%s). Avisa a IT.' % e}

    @http.route('/koroshi/recepcion/cerrar', type='json', auth='user')
    def cerrar(self, recepcion_id=False, employee_id=False, **kw):
        """1.2.0: terminar de apuntar cajas (cualquier operario con su tarjeta). No toca stock: la IN sigue pendiente."""
        try:
            self._comprobar_usuario()
            emp = self._empleado(employee_id)
            r = self._recepcion(recepcion_id)
            r.cerrar(emp)
            return {'ok': True, 'recepcion': self._datos_recepcion(r, emp)}
        except UserError as e:
            request.env.cr.rollback()
            return {'ok': False, 'msg': _msg(e)}

    @http.route('/koroshi/recepcion/reabrir', type='json', auth='user')
    def reabrir(self, recepcion_id=False, employee_id=False, **kw):
        try:
            self._comprobar_usuario()
            emp = self._responsable(employee_id)
            r = self._recepcion(recepcion_id)
            r.reabrir(emp)
            return {'ok': True, 'recepcion': self._datos_recepcion(r, emp)}
        except UserError as e:
            request.env.cr.rollback()
            return {'ok': False, 'msg': _msg(e)}

    # ------------------------------------------------------------------ exportar (Excel: CSV con «;»)
    @http.route('/koroshi/recepcion/exportar', type='http', auth='user')
    def exportar(self, recepcion_id=0, employee_id=0, **kw):
        # Lleva el teórico de las IN: solo el responsable (su tarjeta) o la oficina (Inventario / Administrador),
        # para que la lectura siga siendo a ciegas.
        emp = request.env['hr.employee'].sudo().browse(int(employee_id or 0)).exists()
        if not (request.env.user.has_group('stock.group_stock_manager') or (
                request.env.user.has_group('stock.group_stock_user')
                and request.env['koroshi.recepcion.responsable'].es_responsable(emp))):
            return request.not_found()
        r = request.env['koroshi.recepcion'].sudo().browse(int(recepcion_id or 0)).exists()
        if not r:
            return request.not_found()
        filas_comp = r.comparar()
        estados = dict(request.env['koroshi.recepcion.comparacion']._fields['estado'].selection)
        filas = [['Recepción', r.name, 'Matrícula', r.matricula, 'Muelle', r.muelle or '', 'Llegada',
                  _local(r.fecha_llegada)], [],
                 ['COMPARACIÓN (por modelo)'],
                 ['Modelo', 'Cajas', 'Uds de las IN', 'Uds llegadas', 'Diferencia', 'Estado',
                  'Dónde (palé / caja: uds)']]
        for f in filas_comp:
            filas.append([f.modelo, f.cajas, f.teorico, f.leido, f.diferencia, estados.get(f.estado, f.estado),
                          f.donde])
        cajas = r.resumen_cajas()
        origenes = r._origenes()
        filas += [[], ['CAJAS'], ['Cajas leídas', len(cajas['leidas']), 'Cajas según quien recepciona', r.cajas or ''],
                  ['Huecos en la numeración', cajas['n_huecos'], ', '.join(map(str, cajas['huecos'])) +
                   ('…' if cajas['huecos_mas'] else '')],
                  ['Cajas con pedido que no es de este contenedor', len(cajas['ajenas']),
                   ', '.join('caja %s (pedido %s)' % (c, p) for c, p in cajas['ajenas'])],
                  ['Pedidos de las IN', ', '.join(origenes)]]
        filas += [[], ['LECTURAS (caja a caja)'],
                  ['Caja', 'Pedido (etiqueta)', 'Pedido de otro contenedor', 'Palé', 'Modelo', 'Artículo', 'EAN',
                   'Uds', 'Operario', 'Cuándo', 'Pasada a stock']]
        for l in r.lectura_ids.filtered(lambda x: x.estado == 'ok').sorted(
                lambda x: (L.clave_caja(x.caja_txt), x.palet_id.name or '', x.id)):
            filas.append([l.caja_txt, l.pedido or '', 'sí' if L.pedido_ajeno(l.pedido, origenes) else '',
                          l.palet_id.name, l.modelo or '', l.producto_id.display_name or '', l.producto_id.barcode or '',
                          float(l.cantidad), l.employee_id.name or '', _local(l.fecha), 'sí' if l.validada else 'no'])
        datos = ('﻿' + L.csv_texto(filas)).encode('utf-8')
        nombre = 'recepcion_%s_%s.csv' % (r.name.replace('/', '-'), (r.matricula or '').replace('/', '-'))
        return request.make_response(datos, headers=[('Content-Type', 'text/csv; charset=utf-8'),
                                                     ('Content-Disposition', content_disposition(nombre))])
