# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Recuentos - rutas de la pantalla «Referencia» (fase 1, SOLO LECTURA).
# Diseño: bin/versiones/diseno-comprobar-inventario_2026-11-20_v3.md
# /referencia: un modelo (2621XC04), una variante o un EAN -> todas sus variantes (color x talla) con lo que dice
#   Odoo, y los sitios (hueco o contenedor) en orden de recorrido. También salen los sitios donde se quitó stock de la
#   referencia en los últimos DIAS_AJUSTES días (ajuste a pérdidas de inventario), aunque Odoo diga 0: es donde puede
#   estar lo que falta.
# /caja: lo que dice Odoo que hay en un sitio (todas las referencias).
# Con sudo y solo lectura: no crea, no escribe y no mueve nada. Solo ubicaciones internas de la compañía 8.
# =============================================================================
import datetime

from odoo import fields, http
from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.koroshi_base import comun

from .. import logica

PREFIJOS_CONTENEDOR = ('KO_', 'TT_')
DIAS_AJUSTES = 90          # ajustes a pérdidas de inventario que se enseñan (días hacia atrás)
MAX_VARIANTES = 300
MAX_SITIOS = 200
MAX_MODELOS = 20           # modelos sugeridos si lo escrito es un trozo
MAX_CAJA = 80              # líneas como máximo al abrir un sitio
MIN_TROZO = 4


def _literal(texto):
    """El texto tal cual para un =like / =ilike («_» y «%» son comodines en SQL)."""
    return (texto or '').replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def _es_contenedor(nombre):
    return (nombre or '').upper()[:3] in PREFIJOS_CONTENEDOR


def _fecha(dt):
    loc = comun.a_local(dt)
    return loc.strftime('%d/%m/%Y %H:%M') if loc else ''


class KoroshiRecuentos(http.Controller):

    def _comprobar_usuario(self):
        if not request.env.user.has_group('stock.group_stock_user'):
            raise UserError('No tienes permiso para ver el inventario.')

    # ------------------------------------------------------------------ artículos
    def _por_codigo(self, codigo):
        """Variante por EAN (y UPC con 0 delante), código alternativo o referencia interna; vacío si no hay."""
        posibles = [codigo]
        if codigo.isdigit() and len(codigo) == 12:
            posibles.append('0' + codigo)
        if codigo.isdigit() and len(codigo) == 13 and codigo.startswith('0'):
            posibles.append(codigo[1:])
        Product = request.env['product.product'].sudo().with_context(active_test=False)
        p = Product.search([('barcode', 'in', posibles)], limit=1)
        if not p and 'product.barcode' in request.env:
            p = request.env['product.barcode'].sudo().search([('name', 'in', posibles)], limit=1).product_id
        if not p:
            p = Product.search([('default_code', '=', codigo)], limit=1)
        return p

    def _variantes(self, modelo):
        """Todas las variantes del modelo (también las archivadas: pueden tener stock). La referencia está en el
        nombre (9.116 artículos no tienen referencia interna) o en la referencia interna."""
        # v1.1.0: por la plantilla y sin traducción (lang en_US): el nombre del artículo es traducible y buscarlo
        # con el idioma del usuario pasaba por las traducciones (1 s en producción; así, 0,4 s).
        if not modelo:
            return request.env['product.product']
        patron = _literal(modelo) + '-%'
        Product = request.env['product.product'].sudo().with_context(active_test=False, lang='en_US')
        Tmpl = request.env['product.template'].sudo().with_context(active_test=False, lang='en_US')
        de_la_compania = ('company_id', 'in', [comun.COMPANY_ID, False])
        tmpls = Tmpl.search([de_la_compania, '|', ('name', '=like', patron), ('name', '=', modelo)])
        variantes = Product.search([('product_tmpl_id', 'in', tmpls.ids)], limit=MAX_VARIANTES) if tmpls else Product
        variantes |= Product.search([de_la_compania, ('default_code', '=like', patron)], limit=MAX_VARIANTES)
        return variantes

    def _variantes_recuento(self, modelo):
        """Las variantes de un recuento: las del modelo o, si el artículo no lleva «-», él solo."""
        variantes = self._variantes(modelo)
        if not variantes:
            Product = request.env['product.product'].sudo().with_context(active_test=False, lang='en_US')
            variantes = Product.search([('company_id', 'in', [comun.COMPANY_ID, False]), '|',
                                        ('default_code', '=', modelo), ('name', '=', modelo)], limit=1)
        return variantes

    def _modelos_que_empiezan(self, texto):
        """Modelos distintos cuyo nombre empieza por el trozo escrito (para elegir)."""
        Tmpl = request.env['product.template'].sudo().with_context(lang='en_US')
        tmpls = Tmpl.search([('company_id', 'in', [comun.COMPANY_ID, False]),
                             ('name', '=ilike', _literal(texto) + '%')], limit=400)
        vistos = []
        for t in tmpls:
            m = logica.modelo_de(t.name)
            if m and m not in vistos:
                vistos.append(m)
        return sorted(vistos)[:MAX_MODELOS]

    def _nombre_variante(self, p):
        return p.default_code or p.name or ''

    # ------------------------------------------------------------------ sitios
    def _sitio_de(self, loc):
        """(hueco, contenedor) de una ubicación: el contenedor KO_/TT_ cuelga del hueco."""
        if _es_contenedor(loc.name):
            return loc.location_id, loc
        return loc, None

    def _sitio_vacio(self, loc):
        hueco, cont = self._sitio_de(loc)
        return {
            'id': loc.id,
            'hueco': logica.hueco_corto(hueco.name),
            'hueco_largo': hueco.complete_name or '',
            'contenedor': cont.name if cont else '',
            'filas': {},            # producto_id -> {'uds', 'reservadas'}
            'ajuste': None,
            '_orden': logica.clave_recorrido(hueco.name),
        }

    # ------------------------------------------------------------------ rutas
    @http.route('/koroshi/recuentos/referencia', type='json', auth='user')
    def referencia(self, texto='', **kw):
        self._comprobar_usuario()
        texto = (texto or '').strip()
        if not texto:
            return {'error': 'Escribe o lee una referencia (2621XC04) o una prenda.'}
        persona = self._persona_por_codigo(texto)        # v1.1.0: la tarjeta de operario
        if persona:
            return {'tipo': 'persona', 'persona': persona}
        prenda = self._por_codigo(texto)
        modelo = logica.modelo_de(self._nombre_variante(prenda) if prenda else texto)
        variantes = self._variantes(modelo)
        if not variantes and prenda:
            variantes = prenda          # artículo sin «-»: se enseña él solo
        if not variantes:
            if len(texto) < MIN_TROZO:
                return {'error': 'No hay ninguna referencia %s. Escribe al menos %d caracteres.' % (texto, MIN_TROZO)}
            modelos = self._modelos_que_empiezan(texto)
            if len(modelos) == 1:
                return self.referencia(texto=modelos[0])
            if not modelos:
                return {'error': 'No hay ninguna referencia que empiece por %s.' % texto}
            return {'tipo': 'modelos', 'texto': texto, 'modelos': modelos}
        return self._datos_referencia(modelo, variantes, prenda)

    def _datos_referencia(self, modelo, variantes, prenda):
        ids = variantes.ids
        Quant = request.env['stock.quant'].sudo()
        quants = Quant.search([('product_id', 'in', ids), ('location_id.usage', '=', 'internal'),
                               ('company_id', '=', comun.COMPANY_ID),
                               '|', ('quantity', '!=', 0), ('reserved_quantity', '!=', 0)])
        sitios = {}
        for q in quants:
            s = sitios.get(q.location_id.id)
            if s is None:
                s = sitios[q.location_id.id] = self._sitio_vacio(q.location_id)
            f = s['filas'].setdefault(q.product_id.id, {'uds': 0.0, 'reservadas': 0.0})
            f['uds'] += q.quantity
            f['reservadas'] += q.reserved_quantity

        # Stock quitado a mano (ajuste a pérdidas de inventario) en los últimos DIAS_AJUSTES días, por sitio
        desde = fields.Datetime.now() - datetime.timedelta(days=DIAS_AJUSTES)
        moves = request.env['stock.move'].sudo().search([
            ('product_id', 'in', ids), ('state', '=', 'done'), ('date', '>=', desde),
            ('location_id.usage', '=', 'internal'), ('location_dest_id.usage', '=', 'inventory'),
            ('company_id', '=', comun.COMPANY_ID)], order='date desc', limit=500)
        ajustes_uds = 0.0
        for mv in moves:
            loc = mv.location_id
            s = sitios.get(loc.id)
            if s is None:
                if len(sitios) >= MAX_SITIOS:
                    continue
                s = sitios[loc.id] = self._sitio_vacio(loc)
            a = s['ajuste']
            if a is None:            # el primero es el más reciente (order date desc)
                a = s['ajuste'] = {'uds': 0.0, 'veces': 0, 'fecha': _fecha(mv.date), 'que': mv.name or '',
                                   'quien': mv.create_uid.name or ''}
            a['uds'] += mv.product_qty
            a['veces'] += 1
            ajustes_uds += mv.product_qty

        # Variantes: color x talla
        info = {}
        for p in variantes:
            _m, color, talla = logica.partes(self._nombre_variante(p))
            info[p.id] = {'color': color or '—', 'talla': talla or '—'}
        colores = sorted({v['color'] for v in info.values()})
        tallas = sorted({v['talla'] for v in info.values()}, key=logica.clave_talla)
        celdas = {c: {t: {'uds': 0.0, 'reservadas': 0.0, 'existe': False} for t in tallas} for c in colores}
        for pid, v in info.items():
            celdas[v['color']][v['talla']]['existe'] = True
        for s in sitios.values():
            for pid, f in s['filas'].items():
                v = info.get(pid)
                if v:
                    c = celdas[v['color']][v['talla']]
                    c['uds'] += f['uds']
                    c['reservadas'] += f['reservadas']

        lista = []
        for s in sorted(sitios.values(), key=lambda x: (x['_orden'], x['contenedor'])):
            filas = []
            for pid, f in s['filas'].items():
                v = info.get(pid, {'color': '?', 'talla': '?'})
                filas.append({'color': v['color'], 'talla': v['talla'], 'uds': f['uds'],
                              'reservadas': f['reservadas']})
            filas.sort(key=lambda r: (r['color'], logica.clave_talla(r['talla'])))
            uds = sum(r['uds'] for r in filas)
            lista.append({
                'id': s['id'], 'hueco': s['hueco'], 'hueco_largo': s['hueco_largo'], 'contenedor': s['contenedor'],
                'filas': filas, 'uds': uds, 'reservadas': sum(r['reservadas'] for r in filas),
                'negativo': any(r['uds'] < 0 for r in filas),
                'varios_colores': len({r['color'] for r in filas if r['uds'] > 0}) > 1,
                'ajuste': s['ajuste'],
                # Odoo ya no tiene nada de la referencia aquí, pero se quitó a mano: hay que mirar
                'solo_ajuste': s['ajuste'] is not None and not any(r['uds'] or r['reservadas'] for r in filas),
            })
        lista = lista[:MAX_SITIOS]

        return {
            'tipo': 'referencia',
            'modelo': modelo,
            'leida': self._nombre_variante(prenda) if prenda else '',
            'n_variantes': len(variantes),
            'colores': colores,
            'tallas': tallas,
            'celdas': celdas,
            'total': sum(c['uds'] for fila in celdas.values() for c in fila.values()),
            'reservadas': sum(c['reservadas'] for fila in celdas.values() for c in fila.values()),
            'sitios': lista,
            'dias_ajustes': DIAS_AJUSTES,
            'ajustes_uds': ajustes_uds,
            'hora': comun.ahora_local().strftime('%d/%m/%Y %H:%M'),
            'recuento_abierto': self._recuento_abierto(modelo),     # v1.1.0
        }

    @http.route('/koroshi/recuentos/caja', type='json', auth='user')
    def caja(self, ubicacion_id=False, modelo='', **kw):
        self._comprobar_usuario()
        loc = request.env['stock.location'].sudo().browse(int(ubicacion_id or 0)).exists()
        if not loc or loc.usage != 'internal' or loc.company_id.id not in (comun.COMPANY_ID, False):
            return {'error': 'Ese sitio no existe o no es del almacén.'}
        hueco, cont = self._sitio_de(loc)
        quants = request.env['stock.quant'].sudo().search(
            [('location_id', '=', loc.id), '|', ('quantity', '!=', 0), ('reserved_quantity', '!=', 0)])
        modelo = (modelo or '').upper()
        filas = []
        for q in quants:
            nombre = self._nombre_variante(q.product_id)
            filas.append({'nombre': nombre, 'uds': q.quantity, 'reservadas': q.reserved_quantity,
                          'de_la_referencia': bool(modelo) and logica.modelo_de(nombre) == modelo})
        filas.sort(key=lambda r: (not r['de_la_referencia'], r['nombre']))
        return {
            'id': loc.id,
            'hueco': logica.hueco_corto(hueco.name),
            'hueco_largo': hueco.complete_name or '',
            'contenedor': cont.name if cont else '',
            'filas': filas[:MAX_CAJA],
            'mas': max(0, len(filas) - MAX_CAJA),
            'uds': sum(r['uds'] for r in filas),
            'referencias': len(filas),
        }

    # ================================================================== v1.1.0: fase 2, el recuento leído
    # Solo apunta (koroshi.recuento y sus tablas). NO toca el stock: aplicar la diferencia es la fase 3.
    # A ciegas: la PDA nunca recibe lo que dice Odoo mientras se cuenta; solo «cuadra» o «vuelve a leerla».

    def _persona_por_codigo(self, codigo):
        emp = request.env['hr.employee'].sudo().search([('barcode', '=', (codigo or '').strip())], limit=1)
        return {'id': emp.id, 'nombre': emp.name} if emp else None

    def _empleado(self, employee_id):
        emp = request.env['hr.employee'].sudo().browse(int(employee_id or 0)).exists()
        if not emp:
            raise UserError('Pasa antes tu tarjeta de operario.')
        return emp

    def _recuento(self, recuento_id):
        rec = request.env['koroshi.recuento'].sudo().browse(int(recuento_id or 0)).exists()
        if not rec:
            raise UserError('Ese recuento no existe.')
        return rec

    def _recuento_abierto(self, modelo):
        rec = request.env['koroshi.recuento'].sudo().search(
            [('referencia', '=', modelo), ('estado', '=', 'contando')], limit=1)
        return {'id': rec.id, 'name': rec.name} if rec else None

    def _variantes_de(self, rec):
        """Las variantes guardadas al empezar el recuento (si no hay, se buscan)."""
        return rec.producto_ids or self._variantes_recuento(rec.referencia)

    def _activa(self, rec):
        return request.env['koroshi.recuento.caja'].sudo().search(
            [('recuento_id', '=', rec.id), ('estado', '=', 'contando')], limit=1)

    def _info_variantes(self, variantes):
        info = {}
        for p in variantes:
            _m, color, talla = logica.partes(self._nombre_variante(p))
            info[p.id] = (color or '—', talla or '—')
        return info

    def _contado(self, caja, vuelta):
        """{producto_id: uds} leídas (y no anuladas ni descartadas) en una vuelta de la caja."""
        cuenta = {}
        for lec in self._lecturas(caja, vuelta):
            if lec.producto_id:
                cuenta[lec.producto_id.id] = cuenta.get(lec.producto_id.id, 0) + 1
        return cuenta

    def _lecturas(self, caja, vuelta):
        """Prendas contadas (no anuladas ni descartadas) de una vuelta, buscadas en la base de datos (no en el
        one2many en memoria, que puede no tener las recién creadas)."""
        return request.env['koroshi.recuento.lectura'].sudo().search(
            [('caja_id', '=', caja.id), ('vuelta', '=', vuelta), ('resultado', '=', 'contada')], order='id')

    def _cajas(self, rec):
        return request.env['koroshi.recuento.caja'].sudo().search([('recuento_id', '=', rec.id)], order='orden, id')

    def _estado(self, rec, msg='', tipo='', **extra):
        """Lo que ve la PDA: las cajas y lo leído en la caja abierta. Nunca lo que dice Odoo."""
        activa = self._activa(rec)
        cuenta = []
        ultima = ''
        if activa:
            info = self._info_variantes(self._variantes_de(rec))
            for pid, uds in self._contado(activa, activa.vuelta).items():
                color, talla = info.get(pid, ('?', '?'))
                cuenta.append({'color': color, 'talla': talla, 'uds': uds})
            cuenta.sort(key=lambda r: (r['color'], logica.clave_talla(r['talla'])))
            lecs = self._lecturas(activa, activa.vuelta)
            if lecs:
                ultima = self._nombre_variante(lecs[-1].producto_id)
        res = {
            'ok': True, 'tipo': tipo or 'recuento', 'msg': msg,
            'recuento': {'id': rec.id, 'name': rec.name, 'referencia': rec.referencia, 'estado': rec.estado},
            'cajas': [{'id': c.id, 'hueco': c.hueco, 'contenedor': c.contenedor or '', 'estado': c.estado,
                       'vuelta': c.vuelta, 'fuera_de_lista': c.fuera_de_lista, 'con_ajuste': c.con_ajuste}
                      for c in self._cajas(rec)],
            'activa': {'id': activa.id, 'hueco': activa.hueco, 'contenedor': activa.contenedor or '',
                       'vuelta': activa.vuelta} if activa else None,
            'cuenta': cuenta,
            'leidas': sum(r['uds'] for r in cuenta),
            'ultima': ultima,
        }
        res.update(extra)
        return res

    def _envolver(self, funcion):
        """Errores de uso -> {'ok': False, 'msg'} (la PDA pita y lo dice), deshaciendo lo que se hubiera escrito."""
        try:
            return funcion()
        except UserError as e:
            request.env.cr.rollback()
            return {'ok': False, 'msg': e.args[0] if e.args else str(e)}

    def _ubicacion_por_codigo(self, codigo):
        """Hueco (código de barras) o contenedor (KO_/TT_, por el nombre) de la compañía 8; vacío si no es un sitio."""
        Loc = request.env['stock.location'].sudo()
        dom = [('company_id', 'in', [comun.COMPANY_ID, False]), ('usage', '=', 'internal')]
        loc = Loc.search([('barcode', '=', codigo)] + dom)
        if not loc and _es_contenedor(codigo):
            loc = Loc.search([('name', '=', codigo.upper())] + dom)
        if len(loc) > 1:
            raise UserError('Hay %d sitios con el código %s. Avisa a IT.' % (len(loc), codigo))
        return loc

    def _empezar_caja(self, caja, emp):
        if caja.estado in ('cuadra', 'confirmada', 'para_jefe', 'no_existe'):
            raise UserError('%s ya está cerrada (%s).' % (caja.contenedor or caja.hueco,
                                                          dict(caja._fields['estado'].selection)[caja.estado]))
        caja.write({'estado': 'contando', 'vuelta': max(caja.vuelta, 1), 'vuelta_inicio': fields.Datetime.now(),
                    'employee_id': emp.id})

    @http.route('/koroshi/recuentos/empezar', type='json', auth='user')
    def empezar(self, modelo='', employee_id=False, **kw):
        """Empieza el recuento de una referencia (o sigue el que esté abierto). Las cajas salen de los sitios de la
        pantalla «Referencia»: con stock o reservas de la referencia, y donde se quitó a mano en 90 días."""
        self._comprobar_usuario()

        def hacer():
            emp = self._empleado(employee_id)
            m = logica.modelo_de(modelo)
            abierto = self._recuento_abierto(m)
            if abierto:
                return self._estado(self._recuento(abierto['id']), 'Sigue el recuento %s.' % abierto['name'])
            variantes = self._variantes_recuento(m)
            if not variantes:
                raise UserError('No hay ninguna referencia %s.' % m)
            datos = self._datos_referencia(m, variantes, None)
            rec = request.env['koroshi.recuento'].sudo().create({
                'referencia': m, 'employee_id': emp.id, 'company_id': comun.COMPANY_ID, 'motivo': 'mano',
                'producto_ids': [(6, 0, variantes.ids)],
                'caja_ids': [(0, 0, {'orden': i + 1, 'ubicacion_id': s['id'], 'hueco': s['hueco'],
                                     'contenedor': s['contenedor'], 'con_ajuste': bool(s['ajuste'])})
                             for i, s in enumerate(datos['sitios'])],
            })
            return self._estado(rec, 'Recuento %s: %d sitios. Lee la primera caja.' % (rec.name, len(rec.caja_ids)))
        return self._envolver(hacer)

    @http.route('/koroshi/recuentos/estado', type='json', auth='user')
    def estado(self, recuento_id=False, **kw):
        self._comprobar_usuario()
        return self._envolver(lambda: self._estado(self._recuento(recuento_id)))

    @http.route('/koroshi/recuentos/abrir_caja', type='json', auth='user')
    def abrir_caja(self, recuento_id=False, caja_id=False, employee_id=False, **kw):
        """Empezar una caja tocándola en la lista (etiqueta rota), en vez de leerla."""
        self._comprobar_usuario()

        def hacer():
            emp = self._empleado(employee_id)
            rec = self._recuento(recuento_id)
            activa = self._activa(rec)
            caja = self._cajas(rec).filtered(lambda c: c.id == int(caja_id or 0))
            if not caja:
                raise UserError('Esa caja no es de este recuento.')
            if activa and activa != caja:
                raise UserError('Acaba antes %s: pulsa «Caja hecha».' % (activa.contenedor or activa.hueco))
            self._empezar_caja(caja, emp)
            return self._estado(rec, 'Contando %s. Lee cada prenda.' % (caja.contenedor or caja.hueco))
        return self._envolver(hacer)

    @http.route('/koroshi/recuentos/leer', type='json', auth='user')
    def leer(self, recuento_id=False, codigo='', employee_id=False, **kw):
        """Una lectura de la PDA: la tarjeta, una caja/hueco (empieza a contarla) o una prenda (se cuenta en la caja
        abierta). Cada prenda leída queda apuntada, sea de la referencia o no."""
        self._comprobar_usuario()

        def hacer():
            texto = (codigo or '').strip()
            if not texto:
                raise UserError('Lectura vacía.')
            persona = self._persona_por_codigo(texto)
            if persona:
                return {'ok': True, 'tipo': 'persona', 'persona': persona}
            emp = self._empleado(employee_id)
            rec = self._recuento(recuento_id)
            if rec.estado != 'contando':
                raise UserError('El recuento %s ya está terminado.' % rec.name)
            activa = self._activa(rec)
            Lectura = request.env['koroshi.recuento.lectura'].sudo()
            if activa:
                variantes = self._variantes_de(rec)
                prenda = self._por_codigo(texto)
                if prenda and prenda in variantes:
                    Lectura.create({'recuento_id': rec.id, 'caja_id': activa.id, 'vuelta': activa.vuelta,
                                    'codigo': texto, 'producto_id': prenda.id, 'resultado': 'contada',
                                    'employee_id': emp.id})
                    return self._estado(rec, tipo='contada', bien=True)
                if prenda:
                    Lectura.create({'recuento_id': rec.id, 'caja_id': activa.id, 'vuelta': activa.vuelta,
                                    'codigo': texto, 'producto_id': prenda.id, 'resultado': 'otra',
                                    'employee_id': emp.id})
                    return self._estado(rec, '%s no es de %s: NO se cuenta. Déjala aparte.'
                                        % (self._nombre_variante(prenda), rec.referencia), tipo='otra', bien=False)
                if self._ubicacion_por_codigo(texto):
                    raise UserError('Estás contando %s: pulsa «Caja hecha» antes de leer otra caja.'
                                    % (activa.contenedor or activa.hueco))
                Lectura.create({'recuento_id': rec.id, 'caja_id': activa.id, 'vuelta': activa.vuelta,
                                'codigo': texto, 'resultado': 'desconocida', 'employee_id': emp.id})
                return self._estado(rec, 'No sé qué es «%s»: NO se cuenta.' % texto, tipo='desconocida', bien=False)
            # Sin caja abierta: tiene que ser una caja o un hueco
            loc = self._ubicacion_por_codigo(texto)
            if not loc:
                if self._por_codigo(texto):
                    raise UserError('Primero lee la caja (KO_…) o el hueco; después, las prendas.')
                raise UserError('No sé qué es «%s». Lee la caja (KO_…) o el hueco.' % texto)
            cajas = self._cajas(rec)
            caja = cajas.filtered(lambda c: c.ubicacion_id == loc)
            if not caja:
                hijas = cajas.filtered(lambda c: c.ubicacion_id.location_id == loc)
                if hijas:
                    raise UserError('En %s hay que leer el contenedor: %s.'
                                    % (logica.hueco_corto(loc.name), ', '.join(hijas.mapped('contenedor'))))
                hueco, cont = self._sitio_de(loc)
                caja = request.env['koroshi.recuento.caja'].sudo().create({
                    'recuento_id': rec.id, 'orden': max(cajas.mapped('orden') or [0]) + 1,
                    'ubicacion_id': loc.id, 'hueco': logica.hueco_corto(hueco.name),
                    'contenedor': cont.name if cont else '', 'fuera_de_lista': True})
                self._empezar_caja(caja, emp)
                return self._estado(rec, '%s no estaba en la lista: se añade. Lee cada prenda.'
                                    % (caja.contenedor or caja.hueco), tipo='caja', bien=True)
            caja = caja[:1]
            self._empezar_caja(caja, emp)
            return self._estado(rec, 'Contando %s (%d.ª lectura). Lee cada prenda.'
                                % (caja.contenedor or caja.hueco, caja.vuelta), tipo='caja', bien=True)
        return self._envolver(hacer)

    @http.route('/koroshi/recuentos/quitar', type='json', auth='user')
    def quitar(self, recuento_id=False, employee_id=False, **kw):
        """«Quitar la última»: la última prenda contada de la caja abierta queda ANULADA (no se borra)."""
        self._comprobar_usuario()

        def hacer():
            self._empleado(employee_id)
            rec = self._recuento(recuento_id)
            activa = self._activa(rec)
            if not activa:
                raise UserError('No hay ninguna caja abierta.')
            lecs = self._lecturas(activa, activa.vuelta)
            if not lecs:
                raise UserError('No hay nada que quitar en esta caja.')
            ultima = lecs[-1]
            ultima.write({'resultado': 'anulada', 'anulada_fecha': fields.Datetime.now()})
            return self._estado(rec, 'Quitada: %s.' % self._nombre_variante(ultima.producto_id))
        return self._envolver(hacer)

    @http.route('/koroshi/recuentos/no_existe', type='json', auth='user')
    def no_existe(self, recuento_id=False, caja_id=False, employee_id=False, **kw):
        self._comprobar_usuario()

        def hacer():
            emp = self._empleado(employee_id)
            rec = self._recuento(recuento_id)
            caja = self._cajas(rec).filtered(lambda c: c.id == int(caja_id or 0))
            if not caja:
                raise UserError('Esa caja no es de este recuento.')
            if caja.estado not in ('pendiente', 'contando') or self._contado(caja, caja.vuelta):
                raise UserError('Esta caja ya tiene prendas leídas: pulsa «Caja hecha».')
            caja.write({'estado': 'no_existe', 'fecha': fields.Datetime.now(), 'employee_id': emp.id})
            return self._estado(rec, '%s: el sitio no existe (apuntado).' % (caja.contenedor or caja.hueco))
        return self._envolver(hacer)

    @http.route('/koroshi/recuentos/caja_hecha', type='json', auth='user')
    def caja_hecha(self, recuento_id=False, employee_id=False, **kw):
        """Cierra la vuelta de la caja abierta: compara lo leído con lo que dice Odoo AHORA (menos lo leído en OUT sin
        validar). Cuadra -> cerrada. No cuadra -> otra vuelta (sin decir la cifra). Si se ha movido stock de la caja
        mientras se contaba, la vuelta no vale: se descartan sus lecturas y se vuelve a leer."""
        self._comprobar_usuario()

        def hacer():
            emp = self._empleado(employee_id)
            rec = self._recuento(recuento_id)
            caja = self._activa(rec)
            if not caja:
                raise UserError('No hay ninguna caja abierta.')
            loc = caja.ubicacion_id
            if not loc:
                raise UserError('El sitio de esta caja ya no existe en Odoo. Pulsa «No existe».')
            ids = self._variantes_de(rec).ids
            ahora = fields.Datetime.now()
            MoveLine = request.env['stock.move.line'].sudo()
            movidas = MoveLine.search_count([
                ('state', '=', 'done'), ('date', '>=', caja.vuelta_inicio), ('product_id', 'in', ids),
                '|', ('location_id', '=', loc.id), ('location_dest_id', '=', loc.id)])
            if movidas:
                self._lecturas(caja, caja.vuelta).write(
                    {'resultado': 'descartada', 'anulada_fecha': ahora})
                caja.write({'vuelta_inicio': ahora, 'movimientos': caja.movimientos + 1})
                return self._estado(rec, 'Se ha movido stock de esta caja mientras contabas: vuelve a leerla '
                                         'entera.', tipo='releer', bien=False)
            odoo = {}
            for q in request.env['stock.quant'].sudo().search([('location_id', '=', loc.id),
                                                               ('product_id', 'in', ids)]):
                odoo[q.product_id.id] = odoo.get(q.product_id.id, 0) + q.quantity
            en_curso = {}
            for ml in MoveLine.search([('location_id', '=', loc.id), ('product_id', 'in', ids),
                                       ('state', 'not in', ('done', 'cancel')), ('qty_done', '>', 0)]):
                en_curso[ml.product_id.id] = en_curso.get(ml.product_id.id, 0) + ml.qty_done
            esperado = {p: odoo.get(p, 0) - en_curso.get(p, 0) for p in set(odoo) | set(en_curso)}
            contado = self._contado(caja, caja.vuelta)
            Linea = request.env['koroshi.recuento.linea'].sudo()
            for pid in set(odoo) | set(en_curso) | set(contado):
                Linea.create({'caja_id': caja.id, 'vuelta': caja.vuelta, 'producto_id': pid,
                              'odoo': odoo.get(pid, 0), 'en_curso': en_curso.get(pid, 0),
                              'esperado': esperado.get(pid, 0), 'contado': contado.get(pid, 0),
                              'diferencia': contado.get(pid, 0) - esperado.get(pid, 0)})
            lineas = Linea.search([('caja_id', '=', caja.id)])
            contados = []
            for v in range(1, caja.vuelta):
                contados.append({l.producto_id.id: l.contado for l in lineas if l.vuelta == v})
            contados.append(contado)
            decision, siguiente = logica.decidir(caja.vuelta, contados, esperado)
            nombre = caja.contenedor or caja.hueco
            if decision == 'releer':
                caja.write({'vuelta': siguiente, 'vuelta_inicio': ahora, 'employee_id': emp.id})
                return self._estado(rec, 'No cuadra: vuelve a leer %s entera (%d.ª lectura).' % (nombre, siguiente),
                                    tipo='releer', bien=False)
            vals = {'estado': decision, 'fecha': ahora, 'employee_id': emp.id}
            if decision in ('cuadra', 'confirmada'):
                lineas.filtered(lambda l: l.vuelta == caja.vuelta).write({'final': True})
                vals.update({'odoo': sum(esperado.values()), 'contado': sum(contado.values()),
                             'diferencia': sum(contado.values()) - sum(esperado.values())})
            caja.write(vals)
            textos = {'cuadra': '%s: cuadra.' % nombre,
                      'confirmada': '%s: diferencia confirmada (apuntada).' % nombre,
                      'para_jefe': '%s: tres lecturas distintas. Queda para el jefe.' % nombre}
            return self._estado(rec, textos[decision] + ' Lee la siguiente caja.', tipo=decision,
                                bien=decision != 'para_jefe')
        return self._envolver(hacer)

    @http.route('/koroshi/recuentos/terminar', type='json', auth='user')
    def terminar(self, recuento_id=False, employee_id=False, forzar=False, **kw):
        """Termina el recuento. Con cajas sin contar, primero lo pregunta (forzar). Ahora sí enseña el resultado:
        por variante, lo que decía Odoo y lo leído, en las cajas cerradas. NO toca el stock (fase 3)."""
        self._comprobar_usuario()

        def hacer():
            self._empleado(employee_id)
            rec = self._recuento(recuento_id)
            if rec.estado != 'contando':
                raise UserError('El recuento %s ya está terminado.' % rec.name)
            activa = self._activa(rec)
            if activa:
                raise UserError('Acaba antes %s: pulsa «Caja hecha».' % (activa.contenedor or activa.hueco))
            cajas = self._cajas(rec)
            faltan = cajas.filtered(lambda c: c.estado == 'pendiente')
            if faltan and not forzar:
                return {'ok': False, 'preguntar': True,
                        'msg': 'Quedan %d cajas sin contar. ¿Terminar igualmente? Quedarán como «Sin contar».'
                               % len(faltan)}
            if 'para_jefe' in cajas.mapped('estado'):
                estado = 'para_jefe'
            elif any(c.estado == 'confirmada' and c.diferencia for c in cajas):
                estado = 'diferencias'
            else:
                estado = 'coincide'
            rec.write({'estado': estado, 'fin': fields.Datetime.now()})
            info = self._info_variantes(self._variantes_de(rec))
            por_var = {}
            for l in request.env['koroshi.recuento.linea'].sudo().search([('recuento_id', '=', rec.id),
                                                                          ('final', '=', True)]):
                d = por_var.setdefault(l.producto_id.id, {'odoo': 0.0, 'leido': 0.0})
                d['odoo'] += l.esperado
                d['leido'] += l.contado
            filas = []
            for pid, d in por_var.items():
                color, talla = info.get(pid, ('?', '?'))
                filas.append({'color': color, 'talla': talla, 'odoo': d['odoo'], 'leido': d['leido'],
                              'diferencia': d['leido'] - d['odoo']})
            filas.sort(key=lambda r: (r['color'], logica.clave_talla(r['talla'])))
            return self._estado(rec, tipo='terminado', resumen={
                'estado': dict(rec._fields['estado'].selection)[estado],
                'filas': filas,
                'sin_contar': len(faltan),
                'para_jefe': len(cajas.filtered(lambda c: c.estado == 'para_jefe')),
                'no_existe': len(cajas.filtered(lambda c: c.estado == 'no_existe')),
            })
        return self._envolver(hacer)
