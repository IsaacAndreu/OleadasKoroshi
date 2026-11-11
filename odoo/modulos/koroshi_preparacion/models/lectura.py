# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Preparación en Lecturas (v3.0.0) - lógica del servidor.
#
# La app de código de barras (stock_barcode + stock_barcode_optimization de Brain Station) solo hace en el servidor:
#   1) guardar qty_done de las move.line,
#   2) put_in_pack(package_name=<CJ>) en el diálogo «Nombre del Paquete»,
#   3) button_validate.
# Esta pantalla hace exactamente lo mismo, una lectura cada vez, y apunta cada lectura en koroshi.preparacion.lectura.
# Sin campos nuevos en las tablas de stock. Nunca escribe stock.quant ni fuerza disponibilidad.
# =============================================================================
import logging
import re

import json
from werkzeug.urls import url_quote
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero, html2plaintext

_logger = logging.getLogger(__name__)

COMPANY_ID = 8                      # EFFECTIVE LOGISTICS, S.L.
RE_CJ = re.compile(r'^CJ\d{9}$')    # matrícula de caja (igual que koroshi_caja_existente)
PREFIJOS_ZONA = ('Z-',)             # agrupaciones de zona: se preparan en la app de siempre
PARAM_ACTIVA = 'koroshi_preparacion.activa'
PARAM_EMPLEADOS = 'koroshi_preparacion.empleados'


class Ocupada(UserError):
    """v3.6: la OUT la está guardando otra petición (otra PDA o un reintento de esta). La PDA vuelve a probar en un
    momento con el mismo id_lectura, sin perder la lectura."""


class Lectura(models.Model):
    _name = 'koroshi.preparacion.lectura'
    _description = 'KOROSHI Preparación: lectura en la PDA'
    _order = 'id desc'

    fecha = fields.Datetime('Fecha', required=True, default=fields.Datetime.now, index=True)
    picking_id = fields.Many2one('stock.picking', 'OUT', index=True, ondelete='cascade')
    move_line_id = fields.Many2one('stock.move.line', 'Línea', ondelete='set null')
    employee_id = fields.Many2one('hr.employee', 'Operario', index=True, ondelete='set null')
    user_id = fields.Many2one('res.users', 'Usuario', default=lambda s: s.env.uid)
    tipo = fields.Selection([('leer', 'Leer'), ('deshacer', 'Deshacer'), ('caja', 'Caja'), ('validar', 'Validar')],
                            'Tipo', required=True)
    codigo = fields.Char('Código leído')
    producto = fields.Char('Producto')
    cantidad = fields.Float('Cantidad', digits=(16, 0))
    resultado = fields.Selection([('ok', 'Bien'), ('error', 'Error')], 'Resultado', required=True, default='ok')
    mensaje = fields.Char('Mensaje')
    id_lectura = fields.Char('Id de la lectura', index=True, help='La pone la PDA: si reintenta, no cuenta dos veces')
    deshecha = fields.Boolean('Deshecha')
    en_caja = fields.Char('Cerrada en la caja', index=True,
                          help='v3.3: la caja CJ donde ha ido esta lectura. Vacío = leída y aún fuera de caja.')

    # ------------------------------------------------------------------ parámetros
    @api.model
    def _param(self, clave, defecto=''):
        return self.env['ir.config_parameter'].sudo().get_param(clave, defecto) or defecto

    @api.model
    def empleado_activo(self, employee):
        """La pantalla nueva se usa si el módulo está activo y el operario está en la lista (o la lista es '*')."""
        if not employee or self._param(PARAM_ACTIVA, '1') in ('0', 'False', 'false', ''):
            return False
        lista = [x.strip().upper() for x in re.split(r'[,;\s]+', self._param(PARAM_EMPLEADOS, '')) if x.strip()]
        if '*' in lista:
            return True
        return (employee.barcode or '').upper() in lista or str(employee.id) in lista

    @api.model
    def picking_propio(self, picking):
        """OUT que se puede preparar aquí: salida de la company 8, sin agrupación de zona, ni hecha ni cancelada."""
        if not picking or picking.picking_type_code != 'outgoing' or picking.company_id.id != COMPANY_ID:
            return False
        if picking.state in ('done', 'cancel', 'draft'):
            return False
        if picking.batch_id and (picking.batch_id.name or '').startswith(PREFIJOS_ZONA):
            return False
        return True

    # ------------------------------------------------------------------ estado de la OUT
    @api.model
    def _lineas(self, picking):
        return picking.move_line_ids.sorted(
            lambda l: (l.location_id.complete_name or '', l.product_id.default_code or '', l.id))

    @api.model
    def _nombre(self, product):
        """v3.1: el nombre del producto sin repetir la referencia («[X] X» -> «X»)."""
        return product.name or product.display_name or ''

    @api.model
    def _talla(self, product):
        """v3.1: talla = atributo «Talla» si lo hay; si no, lo último del nombre MODELO-COLOR-TALLA (2511TR12-000002-XL -> XL)."""
        for v in product.product_template_attribute_value_ids:
            if 'TALLA' in (v.attribute_id.name or '').upper() or 'SIZE' in (v.attribute_id.name or '').upper():
                return v.name or ''
        partes = (product.name or '').split('-')
        if len(partes) >= 3 and 0 < len(partes[-1]) <= 5:
            return partes[-1]
        return ''

    @api.model
    def _corto(self, product):
        return self._nombre(product)

    @api.model
    def _sin_caja(self, picking):
        return picking.move_line_ids.filtered(
            lambda l: not l.result_package_id and float_compare(l.qty_done, 0, precision_digits=3) > 0)

    # ------------------------------------------------------------------ v3.3: preparar a dos
    @api.model
    def _clave(self, ml):
        """Orden de la ruta (el mismo de _lineas)."""
        return (ml.location_id.complete_name or '', ml.product_id.default_code or '', ml.id)

    @api.model
    def _grupo(self, picking, equipo):
        """v3.4: el registro del trabajo a dos (corte por la mitad y avisos). Se crea la primera vez que hay dos."""
        if len(equipo) < 2:
            return self.env['koroshi.preparacion.equipo']
        Equipo = self.env['koroshi.preparacion.equipo'].sudo()
        g = Equipo.search([('picking_id', '=', picking.id), ('titular_id', '=', equipo[0].id),
                           ('ayudante_id', '=', equipo[1].id)], limit=1)
        if g:
            return g
        # las líneas que quedan por coger, en el orden de la ruta: el ayudante empieza en la mitad
        pendientes = [ml for ml in self._lineas(picking) if not ml.result_package_id and float_compare(
            ml.qty_done, ml.product_uom_qty, precision_digits=3) < 0]
        corte = pendientes[len(pendientes) // 2] if pendientes else False
        clave = self._clave(corte) if corte else (u'￿', '', 0)
        return Equipo.create({'picking_id': picking.id, 'titular_id': equipo[0].id, 'ayudante_id': equipo[1].id,
                              'corte_ubicacion': clave[0], 'corte_ref': clave[1], 'corte_id': clave[2],
                              'lineas_pendientes': len(pendientes)})

    @api.model
    def _equipo(self, picking):
        """Operarios con la OUT empezada (tareas en curso de koroshi_operarios), el primero que empezó delante.
        El primero es el titular (va en el orden de la ruta); los demás, ayudantes (van desde el final)."""
        tareas = self.env['koroshi.operario.tarea'].sudo().search(
            [('picking_id', '=', picking.id), ('tipo', '=', 'out'), ('estado', '=', 'curso')], order='inicio asc, id asc')
        equipo = self.env['hr.employee'].sudo()
        for t in tareas:
            if t.employee_id not in equipo:
                equipo |= t.employee_id
        return equipo

    @api.model
    def _faltantes_companero(self, picking, employee, grupo):
        """v3.4: lo que el compañero ha mandado a faltantes o cambiado de ubicación desde que trabajan a dos.
        La PDA avisa una vez de cada uno (para no ir a buscar algo que ya no está)."""
        if not grupo or not employee or 'koroshi.faltante' not in self.env:
            return []
        otro = grupo.ayudante_id if employee == grupo.titular_id else grupo.titular_id
        res = []
        for f in self.env['koroshi.faltante'].sudo().search([('picking_id', '=', picking.id),
                                                             ('employee_id', '=', otro.id),
                                                             ('fecha', '>=', grupo.create_date)], order='id'):
            prod = self._corto(f.product_id)
            if f.tipo == 'sin_alternativa':
                txt = _('%s ha mandado a faltantes %s: no lo busques.') % (otro.name, prod)
            else:
                txt = _('%s ha cambiado %s a %s.') % (otro.name, prod, f.ubicacion_nueva_id.name or '')
            res.append({'id': f.id, 'texto': txt})
        return res

    @api.model
    def _lecturas_fuera_de_caja(self, picking):
        """{(move_line_id, employee_id): uds} leídas en esta pantalla y aún sin caja."""
        res = {}
        for l in self.sudo().search([('picking_id', '=', picking.id), ('tipo', '=', 'leer'), ('resultado', '=', 'ok'),
                                     ('deshecha', '=', False), ('en_caja', '=', False), ('move_line_id', '!=', False)]):
            k = (l.move_line_id.id, l.employee_id.id or False)
            res[k] = res.get(k, 0) + (l.cantidad or 0)
        return res

    @api.model
    def _reparto_sin_caja(self, picking, employee):
        """Uds fuera de caja de cada línea: (mias, de_otros) por move_line.id.
        Ayudante: mías = lo que ha leído él. Titular (o sin equipo): mías = todo lo que no es de los ayudantes, así lo
        leído en la app de código de barras o sin tarjeta sigue siendo del titular, como antes de la v3.3."""
        equipo = self._equipo(picking)
        res = {}
        if len(equipo) < 2:
            # solo (o el compañero ya se fue): todo lo leído es suyo y va a la caja, como antes de la v3.3
            for ml in self._sin_caja(picking):
                res[ml.id] = (ml.qty_done, 0.0)
            return res
        titular = equipo[0]
        es_titular = not employee or employee == titular or employee not in equipo
        por_linea = self._lecturas_fuera_de_caja(picking)
        for ml in self._sin_caja(picking):
            hechas = ml.qty_done
            if es_titular:
                otros = sum(v for (lid, eid), v in por_linea.items() if lid == ml.id and eid and eid != titular.id)
                otros = min(otros, hechas)
                mias = hechas - otros
            else:
                mias = min(por_linea.get((ml.id, employee.id), 0), hechas)
                otros = hechas - mias
            res[ml.id] = (mias, otros)
        return res

    @api.model
    def _completa(self, ml):
        return float_compare(ml.qty_done, ml.product_uom_qty, precision_digits=3) >= 0 and not float_is_zero(
            ml.product_uom_qty + ml.qty_done, precision_digits=3)

    @api.model
    def estado(self, picking, employee=None, ligero=False):
        """El estado de la OUT para pintar la pantalla.
        v3.5 ligero=True (tras leer / deshacer / refresco a dos): sin lo fijo de cada línea (nombre, talla, foto, EAN,
        ubicación), solo [id, pedidas, leídas, caja, completa] en el orden de la ruta y los totales. En una OUT de 141
        líneas pasa de ~46 KB a ~4 KB y el servidor no lee productos ni fotos. Si el cliente ve una línea que no
        conoce (put_in_pack del compañero parte líneas), pide /cargar entero."""
        lineas = []
        siguiente = False
        fotos = {}
        # v3.4: preparar a dos -> la OUT se parte por la mitad (en el orden de la ruta) cuando entra el ayudante.
        # Cada uno ve primero su mitad, de delante hacia atrás, y después lo que quede de la del otro desde el
        # extremo más lejano (así se encuentran en medio y no van a la misma ubicación).
        equipo = self._equipo(picking)
        ayudante = bool(employee) and len(equipo) > 1 and employee in equipo and employee != equipo[0]
        grupo = self._grupo(picking, equipo)
        ordenadas = self._lineas(picking)
        aviso = ''
        if grupo:
            corte = grupo._clave_corte()
            primera = ordenadas.filtered(lambda l: self._clave(l) < corte)
            segunda = ordenadas - primera
            if ayudante:
                ordenadas = segunda + primera.sorted(self._clave, reverse=True)
            else:
                ordenadas = primera + segunda.sorted(self._clave, reverse=True)
            if employee and employee == grupo.titular_id and not grupo.avisado_titular:
                aviso = _('%s se ha unido: hace la segunda mitad (desde %s).') % (
                    grupo.ayudante_id.name, grupo.corte_nombre())
                grupo.avisado_titular = True
        alternativos = {} if ligero else self._codigos_alternativos(ordenadas.mapped('product_id'))   # v3.7
        for ml in ordenadas:
            pedidas = ml.product_uom_qty
            leidas = ml.qty_done
            completa = self._completa(ml)
            if ligero:
                lineas.append([ml.id, round(pedidas), round(leidas), ml.result_package_id.name or '', completa])
                if not siguiente and not completa and not ml.result_package_id:
                    siguiente = ml.id
                continue
            p = ml.product_id
            if p.id not in fotos:
                # v3.1: solo el tamaño (bin_size), sin bajar la imagen; False = sin foto (no se pinta el icono de Odoo)
                fotos[p.id] = bool(p.with_context(bin_size=True).image_128)
            lineas.append({
                'id': ml.id,
                'producto_id': p.id,     # v3.0.1: foto /web/image/product.product/<id>/image_256
                'producto': p.display_name or '',
                'nombre': self._nombre(p),
                'talla': self._talla(p),
                'tiene_foto': fotos[p.id],
                'ref': p.default_code if p.default_code and p.default_code not in (p.barcode, p.name) else '',
                'ean': ml.product_id.barcode or '',
                'eans_alt': alternativos.get(p.id, []),     # v3.7: códigos de barras alternativos del producto
                'ubicacion': ml.location_id.name or '',
                'ubicacion_completa': ml.location_id.complete_name or '',
                # v3.7: al leer una ubicación, la pantalla salta a su línea (la caja KO_ o el hueco que la contiene)
                'ubicacion_codigos': [c for c in (ml.location_id.barcode, ml.location_id.location_id.barcode) if c],
                'pedidas': round(pedidas),
                'leidas': round(leidas),
                'caja': ml.result_package_id.name or '',
                'completa': completa,
            })
            if not siguiente and not completa and not ml.result_package_id:
                siguiente = ml.id
        cajas = {}
        for ml in picking.move_line_ids.filtered('result_package_id'):
            cajas.setdefault(ml.result_package_id.name, 0)
            cajas[ml.result_package_id.name] += ml.qty_done
        sin_caja = sum(self._sin_caja(picking).mapped('qty_done'))
        pedidas = sum(picking.move_line_ids.mapped('product_uom_qty'))
        leidas = sum(picking.move_line_ids.mapped('qty_done'))
        # v3.3: preparar a dos -> cada uno ve lo suyo fuera de caja y lo que le falta al compañero
        reparto = self._reparto_sin_caja(picking, employee)
        mias_sin_caja = sum(v[0] for v in reparto.values())
        otros_sin_caja = sum(v[1] for v in reparto.values())
        companeros = [e.name for e in equipo if not employee or e != employee]
        zona = ''
        if picking.batch_id and not (picking.batch_id.name or '').startswith(PREFIJOS_ZONA):
            zona = picking.batch_id.name or ''
        todo_leido = bool(lineas) and all((l[4] if ligero else l['completa']) for l in lineas)
        return {
            'ligero': ligero,
            'out': {
                'id': picking.id,
                'name': picking.name,
                'tienda': picking.partner_id.name or '',
                'origen': picking.origin or '',
                'estado': picking.state,
                'agrupacion': zona,
                'propia': self.picking_propio(picking),
                'nota': self._nota(picking),   # v3.7: las notas de la OUT, arriba
            },
            'lineas': lineas,
            'siguiente_id': siguiente,
            'sin_caja': round(sin_caja),
            'cajas': [{'nombre': k, 'uds': round(v)} for k, v in sorted(cajas.items())],
            'pedidas': round(pedidas),
            'leidas': round(leidas),
            'todo_leido': todo_leido,
            # v3.3: preparar a dos
            'a_dos': len(equipo) > 1,
            'rol': 'ayudante' if ayudante else ('titular' if len(equipo) > 1 else 'solo'),
            'companeros': companeros,
            'mitad': grupo.corte_nombre() if grupo else '',
            'aviso_equipo': aviso,
            'faltantes_companero': self._faltantes_companero(picking, employee, grupo),
            'mias_sin_caja': round(mias_sin_caja),
            'otros_sin_caja': round(otros_sin_caja),
        }

    # ------------------------------------------------------------------ ayudas
    @api.model
    def _codigos_alternativos(self, productos):
        """v3.7: {product_id: [códigos]} de product_multi_barcode (otros EAN del mismo artículo), para que la PDA
        también cuente al momento si se lee uno de esos."""
        res = {}
        if not productos or 'product.barcode' not in self.env:
            return res
        for b in self.env['product.barcode'].sudo().search([('product_id', 'in', productos.ids)]):
            if b.name:
                res.setdefault(b.product_id.id, []).append(b.name)
        return res

    @api.model
    def _nota(self, picking):
        """v3.7: las notas de la OUT en texto (pueden traer avisos de la oficina)."""
        nota = picking.note or ''
        if '<' in nota:
            nota = html2plaintext(nota)
        return nota.strip()[:500]

    @api.model
    def _bloquear(self, picking):
        """Una sola PDA escribe a la vez en la misma OUT."""
        try:
            # v3.6: en un savepoint, para que si no se puede bloquear la transacción siga sana (apuntar, estado)
            with self.env.cr.savepoint():
                self.env.cr.execute('SELECT id FROM stock_picking WHERE id = %s FOR UPDATE NOWAIT', (picking.id,))
        except Exception:
            raise Ocupada(_('Otra PDA está guardando en %s. Se vuelve a probar sola.') % picking.name)

    @api.model
    def _variantes(self, codigo):
        """El código tal cual y la conversión UPC (12) <-> EAN-13 con 0 delante (nomenclatura upc_ean_conv)."""
        res = [codigo]
        if codigo.isdigit() and len(codigo) == 12:
            res.append('0' + codigo)
        if codigo.isdigit() and len(codigo) == 13 and codigo.startswith('0'):
            res.append(codigo[1:])
        return res

    @api.model
    def _producto_de(self, picking, codigo):
        """Producto de la OUT con ese código: EAN principal, códigos alternativos (product_multi_barcode) o
        referencia interna. Devuelve (producto, en_la_out)."""
        variantes = self._variantes(codigo)
        productos = picking.move_line_ids.mapped('product_id')
        for p in productos:
            if p.barcode and p.barcode in variantes:
                return p, True
        if 'product.barcode' in self.env:
            alt = self.env['product.barcode'].sudo().search(
                [('name', 'in', variantes), ('product_id', 'in', productos.ids)], limit=1)
            if alt:
                return alt.product_id, True
        for p in productos:
            if p.default_code and p.default_code == codigo:
                return p, True
        # no es de la OUT: ¿es un producto?
        otro = self.env['product.product'].sudo().search([('barcode', 'in', variantes)], limit=1)
        if not otro and 'product.barcode' in self.env:
            alt = self.env['product.barcode'].sudo().search([('name', 'in', variantes)], limit=1)
            otro = alt.product_id
        return otro, False

    @api.model
    def _apuntar(self, picking, employee, tipo, codigo, resultado='ok', mensaje='', ml=None, cantidad=0,
                 id_lectura=False, producto=''):
        return self.sudo().create({
            'picking_id': picking.id if picking else False,
            'move_line_id': ml.id if ml else False,
            'employee_id': employee.id if employee else False,
            'tipo': tipo,
            'codigo': codigo,
            'producto': producto or (ml.product_id.display_name if ml else ''),
            'cantidad': cantidad,
            'resultado': resultado,
            'mensaje': (mensaje or '')[:250],
            'id_lectura': id_lectura or False,
        })

    @api.model
    def _repetida(self, id_lectura):
        if not id_lectura:
            return False
        return self.sudo().search([('id_lectura', '=', id_lectura)], limit=1)

    @api.model
    def _comprobar(self, picking):
        if not picking:
            raise UserError(_('No se encuentra la OUT.'))
        if picking.state == 'done':
            raise UserError(_('%s ya está validada.') % picking.name)
        if picking.state == 'cancel':
            raise UserError(_('%s está cancelada.') % picking.name)
        if not self.picking_propio(picking):
            raise UserError(_('%s no se prepara aquí: ábrela en la app de código de barras.') % picking.name)

    # ------------------------------------------------------------------ leer un producto
    @api.model
    def leer(self, picking, employee, codigo, id_lectura=False):
        """Suma 1 ud a la línea del producto leído. Devuelve {'ok', 'msg', 'linea_id', 'que'}."""
        codigo = (codigo or '').strip()
        previa = self._repetida(id_lectura)
        if previa:
            return {'ok': previa.resultado == 'ok', 'msg': previa.mensaje, 'linea_id': previa.move_line_id.id,
                    'que': 'repetida'}
        self._comprobar(picking)
        if RE_CJ.match(codigo):
            return {'ok': False, 'que': 'es_caja', 'msg': _('Es una caja: pulsa «Caja» antes de leerla.')}
        tarjeta = self.env['hr.employee'].sudo().search([('barcode', '=', codigo)], limit=1)
        if tarjeta:
            return {'ok': False, 'que': 'es_tarjeta',
                    'msg': _('Es la tarjeta de %s. Para cambiar de operario vuelve a Lecturas (←).') % tarjeta.name}
        producto, en_la_out = self._producto_de(picking, codigo)
        if not producto:
            ubicacion = self.env['stock.location'].sudo().search([('barcode', '=', codigo)], limit=1)
            if ubicacion:
                # v3.7: es una ubicación (las de la OUT las resuelve la PDA sola): no hay nada del pedido allí
                return {'ok': False, 'que': 'ubicacion',
                        'msg': _('En %s no hay nada de este pedido.') % (ubicacion.name or codigo)}
            msg = _('Código %s desconocido. No cuenta.') % codigo
            self._apuntar(picking, employee, 'leer', codigo, 'error', msg, id_lectura=id_lectura)
            return {'ok': False, 'que': 'desconocido', 'msg': msg}
        if not en_la_out:
            msg = _('%s no es de este pedido. No cuenta.') % self._corto(producto)
            self._apuntar(picking, employee, 'leer', codigo, 'error', msg, id_lectura=id_lectura,
                          producto=producto.display_name)
            return {'ok': False, 'que': 'no_es_del_pedido', 'msg': msg}
        self._bloquear(picking)
        lineas = self._lineas(picking).filtered(
            lambda l: l.product_id == producto and not l.result_package_id
            and float_compare(l.qty_done, l.product_uom_qty, precision_digits=3) < 0)
        if not lineas:
            total = sum(picking.move_line_ids.filtered(lambda l: l.product_id == producto).mapped('product_uom_qty'))
            msg = _('Ya tienes todas las uds de %s (%s). No cuenta.') % (self._corto(producto), round(total))
            self._apuntar(picking, employee, 'leer', codigo, 'error', msg, id_lectura=id_lectura,
                          producto=producto.display_name)
            return {'ok': False, 'que': 'completo', 'msg': msg}
        ml = lineas[0]
        primera = float_is_zero(sum(picking.move_line_ids.mapped('qty_done')), precision_digits=3)
        ml.write({'qty_done': ml.qty_done + 1})
        if primera and hasattr(picking, 'set_barcode_start_date'):
            # lo mismo que la app de Brain Station al primer producto (fecha de inicio de la preparación)
            try:
                with self.env.cr.savepoint():
                    picking.set_barcode_start_date()
            except Exception as e:  # solo informativo
                _logger.info('KOROSHI preparacion: set_barcode_start_date %s: %s', picking.name, e)
        hechas = sum(picking.move_line_ids.filtered(lambda l: l.product_id == producto).mapped('qty_done'))
        total = sum(picking.move_line_ids.filtered(lambda l: l.product_id == producto).mapped('product_uom_qty'))
        msg = '%s · %s de %s' % (self._corto(producto), round(hechas), round(total))
        self._apuntar(picking, employee, 'leer', codigo, 'ok', msg, ml=ml, cantidad=1, id_lectura=id_lectura)
        return {'ok': True, 'que': 'producto', 'msg': msg, 'linea_id': ml.id}

    # ------------------------------------------------------------------ deshacer la última
    @api.model
    def deshacer(self, picking, employee):
        self._comprobar(picking)
        self._bloquear(picking)
        dominio = [('picking_id', '=', picking.id), ('tipo', '=', 'leer'), ('resultado', '=', 'ok'),
                   ('deshecha', '=', False), ('en_caja', '=', False)]
        if employee:
            dominio.append(('employee_id', '=', employee.id))
        ultima = self.sudo().search(dominio, limit=1)
        if not ultima or not ultima.move_line_id:
            return {'ok': False, 'msg': _('No hay ninguna lectura tuya que deshacer en %s.') % picking.name}
        ml = ultima.move_line_id
        if ml.result_package_id:
            return {'ok': False, 'msg': _('%s ya está en la caja %s: no se puede deshacer.')
                    % (self._corto(ml.product_id), ml.result_package_id.name)}
        if float_compare(ml.qty_done, 1, precision_digits=3) < 0:
            ultima.deshecha = True
            return {'ok': False, 'msg': _('Esa línea ya no tiene uds leídas.')}
        n = min(max(int(round(ultima.cantidad or 1)), 1), int(round(ml.qty_done)))   # v3.7: puesta a mano = n uds
        ml.write({'qty_done': ml.qty_done - n})
        ultima.deshecha = True
        msg = _('Deshecha: %s (−%s)') % (self._corto(ml.product_id), n)
        self._apuntar(picking, employee, 'deshacer', ultima.codigo, 'ok', msg, ml=ml, cantidad=-n)
        return {'ok': True, 'msg': msg, 'linea_id': ml.id}

    # ------------------------------------------------------------------ v3.7: cantidad a mano
    @api.model
    def poner_cantidad(self, picking, employee, linea_id, cantidad, id_lectura=False):
        """Pone n uds de golpe en una línea (como el lápiz de la app de código de barras). Solo si ya se ha leído al
        menos una ud de esa línea (el producto está comprobado) y sin pasar de lo que falta."""
        previa = self._repetida(id_lectura)
        if previa:
            return {'ok': previa.resultado == 'ok', 'msg': previa.mensaje, 'linea_id': previa.move_line_id.id,
                    'que': 'repetida'}
        self._comprobar(picking)
        try:
            n = int(cantidad)
        except (TypeError, ValueError):
            n = 0
        if n < 1:
            return {'ok': False, 'msg': _('Pon una cantidad de 1 o más.')}
        self._bloquear(picking)
        ml = picking.move_line_ids.filtered(lambda l: l.id == int(linea_id or 0))
        if not ml:
            return {'ok': False, 'msg': _('Esa línea ya no está en %s. Vuelve a cargar la OUT.') % picking.name}
        if ml.result_package_id:
            return {'ok': False, 'msg': _('Esa línea ya está en la caja %s.') % ml.result_package_id.name}
        if float_compare(ml.qty_done, 1, precision_digits=3) < 0:
            return {'ok': False, 'msg': _('Lee primero una ud de %s con la pistola.') % self._corto(ml.product_id)}
        falta = int(round(ml.product_uom_qty - ml.qty_done))
        if n > falta:
            return {'ok': False, 'msg': _('En esta línea solo faltan %s uds.') % falta}
        ml.write({'qty_done': ml.qty_done + n})
        msg = _('%s · %s de %s (+%s a mano)') % (self._corto(ml.product_id), round(ml.qty_done),
                                                 round(ml.product_uom_qty), n)
        self._apuntar(picking, employee, 'leer', 'A MANO +%s' % n, 'ok', msg, ml=ml, cantidad=n,
                      id_lectura=id_lectura)
        return {'ok': True, 'que': 'cantidad', 'msg': msg, 'linea_id': ml.id}

    # ------------------------------------------------------------------ v3.7: imprimir
    @api.model
    def impresos(self, picking):
        """Lo que se puede volver a imprimir de la OUT, por si falta una etiqueta. Solo lectura: la etiqueta de caja
        pinta las matrículas que la OUT ya tiene reservadas (no reserva ninguna nueva)."""
        res = []
        Informe = self.env['ir.actions.report'].sudo()
        # v3.7.2: los informes PDF necesitan la empresa de la OUT (si no, Odoo contesta 403 por multiempresa)
        empresa = '?context=' + url_quote(json.dumps({'allowed_company_ids': [picking.company_id.id or self.env.company.id]}))
        if Informe.search([('report_name', '=', 'koroshi.report_etiqueta_zona')], limit=1):
            res.append({'nombre': _('Etiqueta de caja (OUT + matrícula)'),
                        'detalle': _('Las matrículas que ya tiene la OUT. Si no tiene, sale con la casilla vacía.'),
                        'url': '/report/pdf/koroshi.report_etiqueta_zona/%d%s' % (picking.id, empresa)})
        vistos = set()
        adjuntos = self.env['ir.attachment'].sudo().search(
            [('res_model', '=', 'stock.picking'), ('res_id', '=', picking.id), ('mimetype', '=', 'application/pdf'),
             '|', ('name', 'ilike', 'label'), ('name', 'ilike', 'etiq')], order='id desc')
        for a in adjuntos:
            if a.name in vistos:
                continue
            vistos.add(a.name)
            res.append({'nombre': _('Etiqueta del transportista'), 'detalle': a.name,
                        'url': '/web/content/%d' % a.id})   # v3.7.2: se abre (no se descarga)
        if Informe.search([('report_name', '=', 'stock.report_deliveryslip')], limit=1):
            res.append({'nombre': _('Albarán'), 'detalle': picking.name,
                        'url': '/report/pdf/stock.report_deliveryslip/%d%s' % (picking.id, empresa)})
        return res

    # ------------------------------------------------------------------ cerrar caja
    @api.model
    def caja(self, picking, employee, codigo, id_lectura=False):
        codigo = (codigo or '').strip().upper()
        previa = self._repetida(id_lectura)
        if previa:
            return {'ok': previa.resultado == 'ok', 'msg': previa.mensaje, 'que': 'repetida'}
        self._comprobar(picking)
        if not RE_CJ.match(codigo):
            return {'ok': False, 'msg': _('%s no es una etiqueta de caja (CJ + 9 cifras). Lee la etiqueta de la caja.')
                    % codigo}
        self._bloquear(picking)
        sin_caja = self._sin_caja(picking)
        if not sin_caja:
            return {'ok': False, 'msg': _('No hay nada leído fuera de caja: lee algún artículo antes de cerrar la caja.')}
        # v3.3: preparar a dos -> en la caja solo va lo que ha leído este operario
        reparto = self._reparto_sin_caja(picking, employee)
        uds = sum(v[0] for v in reparto.values())
        if float_is_zero(uds, precision_digits=3):
            return {'ok': False, 'msg': _('No tienes nada tuyo fuera de caja. Lo que queda (%s uds) es de tu compañero.')
                    % round(sum(v[1] for v in reparto.values()))}
        apartar = {lid: v[1] for lid, v in reparto.items() if v[1] > 0}
        try:
            with self.env.cr.savepoint():
                # lo del compañero se aparta un momento (qty_done sin lo suyo) para que put_in_pack no lo meta
                for ml in sin_caja.filtered(lambda l: l.id in apartar):
                    ml.write({'qty_done': reparto[ml.id][0]})
                # igual que el diálogo «Nombre del Paquete» de la app (Brain Station + koroshi_caja_existente)
                res = picking.put_in_pack(package_name=codigo)
                if isinstance(res, dict) and res.get('res_model'):
                    raise UserError(_('Odoo pide otra cosa al cerrar la caja (%s). Ciérrala en la app de código de '
                                      'barras.') % (res.get('name') or res.get('res_model')))
                # y se devuelve: put_in_pack deja en la línea de siempre lo que quedaba por coger, sin caja
                for ml in self.env['stock.move.line'].browse(list(apartar)).exists():
                    if ml.result_package_id or float_compare(ml.product_uom_qty - ml.qty_done, apartar[ml.id],
                                                             precision_digits=3) < 0:
                        raise UserError(_('No se ha podido separar lo de tu compañero en %s. Avisa a la oficina.')
                                        % self._corto(ml.product_id))
                    ml.write({'qty_done': ml.qty_done + apartar[ml.id]})
        except (UserError, ValidationError) as e:
            msg = e.name if hasattr(e, 'name') else str(e)
            self._apuntar(picking, employee, 'caja', codigo, 'error', msg, id_lectura=id_lectura)
            return {'ok': False, 'msg': msg}
        # las lecturas que han ido a esta caja (las de los demás siguen fuera)
        dominio = [('picking_id', '=', picking.id), ('tipo', '=', 'leer'), ('resultado', '=', 'ok'),
                   ('deshecha', '=', False), ('en_caja', '=', False)]
        if apartar:
            titular = self._equipo(picking)[:1]
            if employee and employee != titular:
                dominio.append(('employee_id', '=', employee.id))
            else:
                dominio += ['|', ('employee_id', '=', False), ('employee_id', '=', titular.id)]
        self.sudo().search(dominio).write({'en_caja': codigo})
        msg = _('Caja %s cerrada con %s uds.') % (codigo, round(uds))
        self._apuntar(picking, employee, 'caja', codigo, 'ok', msg, cantidad=uds, id_lectura=id_lectura)
        return {'ok': True, 'msg': msg}

    # ------------------------------------------------------------------ validar
    @api.model
    def validar(self, picking, employee, pedido_pendiente=None):
        """Misma validación que koroshi_faltantes (button_validate, todo o nada). Devuelve
        {'ok', 'que': 'validada' | 'quedan' | 'preguntar' | 'sin_caja' | 'no_validada', 'msg'}."""
        self._comprobar(picking)
        sin_caja = sum(self._sin_caja(picking).mapped('qty_done'))
        if float_compare(sin_caja, 0, precision_digits=3) > 0:
            reparto = self._reparto_sin_caja(picking, employee)
            mias = sum(v[0] for v in reparto.values())
            otros = sum(v[1] for v in reparto.values())
            if otros and not mias:
                # v3.3: preparar a dos
                return {'ok': False, 'que': 'sin_caja',
                        'msg': _('Falta que tu compañero cierre su caja (%s uds).') % round(otros)}
            return {'ok': False, 'que': 'sin_caja',
                    'msg': _('Hay %s uds sin caja: pulsa «Caja» y lee la etiqueta antes de validar.') % round(sin_caja)}
        a_dos = len(self._equipo(picking)) > 1
        if pedido_pendiente not in ('si', 'no'):
            fijo = self._param('koroshi_faltantes.pedido_pendiente', 'no')
            pedido_pendiente = fijo if fijo in ('si', 'no') else None
        Faltante = self.env['koroshi.faltante']
        try:
            r = Faltante.validar_out(picking, pedido_pendiente)
        except (UserError, ValidationError) as e:
            msg = e.name if hasattr(e, 'name') else str(e)
            self._apuntar(picking, employee, 'validar', picking.name, 'error', msg)
            return {'ok': False, 'que': 'no_validada', 'msg': msg}
        if r['estado'] == 'pendientes':
            if a_dos:
                # v3.3: preparar a dos
                faltan = sum(picking.move_line_ids.mapped('product_uom_qty')) - sum(
                    picking.move_line_ids.mapped('qty_done'))
                return {'ok': False, 'que': 'quedan', 'n': r['n'],
                        'msg': _('Faltan %s uds por leer entre los dos (%s líneas). Si es de tu compañero, espera a '
                                 'que acabe.') % (round(faltan), r['n'])}
            return {'ok': False, 'que': 'quedan', 'n': r['n'],
                    'msg': _('Quedan %s líneas por coger: léelas o pulsa «Faltante».') % r['n']}
        if r['estado'] == 'preguntar':
            return {'ok': True, 'que': 'preguntar', 'msg': _('Faltan uds. ¿Crear un pedido pendiente con lo que falta?')}
        msg = _('%s validada.') % picking.name
        self._apuntar(picking, employee, 'validar', picking.name, 'ok', msg)
        try:
            # cierra ya la tarea del operario (lo mismo que hace koroshi_faltantes al validar)
            with self.env.cr.savepoint():
                self.env['koroshi.operario.tarea'].sudo().cron_cerrar()
        except Exception:
            pass
        return {'ok': True, 'que': 'validada', 'msg': msg}


class Equipo(models.Model):
    """v3.4: una OUT preparada a dos. Guarda dónde se partió (la primera línea de la segunda mitad) y los avisos."""
    _name = 'koroshi.preparacion.equipo'
    _description = 'KOROSHI Preparación: OUT a dos'
    _order = 'id desc'

    picking_id = fields.Many2one('stock.picking', 'OUT', required=True, index=True, ondelete='cascade')
    titular_id = fields.Many2one('hr.employee', 'Titular (primera mitad)', required=True, ondelete='cascade')
    ayudante_id = fields.Many2one('hr.employee', 'Ayudante (segunda mitad)', required=True, ondelete='cascade')
    corte_ubicacion = fields.Char('Empieza la segunda mitad en')
    corte_ref = fields.Char('Referencia del corte')
    corte_id = fields.Integer('Línea del corte')
    lineas_pendientes = fields.Integer('Líneas pendientes al unirse')
    avisado_titular = fields.Boolean('Titular avisado')

    def _clave_corte(self):
        self.ensure_one()
        return (self.corte_ubicacion or '', self.corte_ref or '', self.corte_id or 0)

    def corte_nombre(self):
        """La ubicación corta (la última parte del nombre completo), para los avisos."""
        self.ensure_one()
        nombre = self.corte_ubicacion or ''
        if nombre.startswith(u'￿'):
            return _('el final')
        return nombre.rsplit('/', 2)[-2] if nombre.count('/') >= 2 else nombre
