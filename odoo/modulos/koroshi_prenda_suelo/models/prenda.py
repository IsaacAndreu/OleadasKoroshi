# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Prenda en el suelo v1.0.0 - «¿A dónde va esta prenda?».
# Diseño: bin/versiones/diseno-prenda-en-el-suelo_2026-11-20.md (visto bueno de Isaac el 23/11/2026).
#
# Se lee una prenda encontrada en el suelo y se dice a dónde va, en este orden (la primera que se cumpla):
#   A  es un faltante pendiente (koroshi_faltantes): «Encontrada» la devuelve de FALTANTE a su hueco;
#   B  la pide una OUT que alguien está haciendo ahora: a quién dársela, dónde está y hacia dónde va;
#   C  la pide una OUT sin empezar: a su hueco reservado (allí la coge quien la prepare);
#   D  no la pide nadie: al hueco donde Odoo tiene stock de esa prenda, el más cercano;
#   E  Odoo no la tiene en ningún hueco: al sitio del parámetro koroshi_prenda_suelo.sitio_sin_hueco.
# Dónde está cada operario sale de su última lectura en Lecturas (koroshi.preparacion.lectura); los metros, de la
# ruta de koroshi_preparacion (models/ruta.py). Quien la encuentra puede leer el hueco que tiene delante.
#
# SOLO LEE, salvo dos cosas: apunta cada búsqueda en koroshi.prenda.suelo (tabla propia) y, en el caso A, si el
# operario pulsa «Encontrada», llama a koroshi.faltante.marcar_encontrado (lo mismo que el asistente de la oficina).
# No lee prendas dentro de OUT, no cierra cajas, no valida y no añade campos a tablas de Odoo.
# =============================================================================
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare

from odoo.addons.koroshi_base import comun
from odoo.addons.koroshi_faltantes.models.faltante import nombre_corto
from odoo.addons.koroshi_preparacion.models import ruta

from .. import logica

PARAM_SITIO = 'koroshi_prenda_suelo.sitio_sin_hueco'
SITIO_DEFECTO = 'la mesa de los jefes'
MAX_LINEAS = 300


class KoroshiPrendaSuelo(models.Model):
    _name = 'koroshi.prenda.suelo'
    _description = 'KOROSHI Prenda encontrada en el suelo'
    _order = 'fecha desc, id desc'

    name = fields.Char('Prenda', compute='_compute_name', store=True)
    fecha = fields.Datetime('Fecha', required=True, default=fields.Datetime.now, index=True)
    dia = fields.Date('Día', compute='_compute_dia', store=True, index=True)
    employee_id = fields.Many2one('hr.employee', 'La encontró', index=True, ondelete='set null')
    user_id = fields.Many2one('res.users', 'Usuario', default=lambda s: s.env.uid, ondelete='set null')
    codigo = fields.Char('Código leído')
    product_id = fields.Many2one('product.product', 'Artículo', index=True, ondelete='set null')
    ubicacion_operario_id = fields.Many2one('stock.location', 'Estaba en', ondelete='set null',
                                            help='Hueco leído por quien la encontró o el de su última lectura')
    caso = fields.Selection(logica.CASOS, 'Caso', index=True)
    destino = fields.Char('Qué dijo la PDA')
    destino_ubicacion_id = fields.Many2one('stock.location', 'A qué hueco', ondelete='set null')
    picking_id = fields.Many2one('stock.picking', 'OUT', ondelete='set null')
    para_employee_id = fields.Many2one('hr.employee', 'Para quién', ondelete='set null')
    faltante_id = fields.Many2one('koroshi.faltante', 'Faltante', ondelete='set null')
    resultado = fields.Selection([
        ('pendiente', 'Sin contestar'),
        ('hecho', 'Hecho'),
        ('no_sirve', 'No sirve'),
        ('encontrada', 'Faltante encontrado'),
    ], 'Resultado', default='pendiente', required=True, index=True)
    nota = fields.Char('Nota')
    company_id = fields.Many2one('res.company', 'Empresa', required=True, default=lambda s: s.env.company)

    @api.depends('product_id', 'codigo')
    def _compute_name(self):
        for r in self:
            r.name = r.product_id.display_name or r.codigo or ''

    @api.depends('fecha')
    def _compute_dia(self):
        for r in self:
            r.dia = comun.dia_local(r.fecha)

    # ------------------------------------------------------------------ de dónde
    @api.model
    def _ubi_corta(self, loc):
        return nombre_corto(loc) if loc else ''

    @api.model
    def _parada(self, loc):
        return ruta.parada(loc.complete_name) if loc else None

    @api.model
    def producto_por_codigo(self, codigo):
        """Variante por EAN (y UPC con 0 delante), código alternativo o referencia interna; vacío si no hay."""
        codigo = (codigo or '').strip()
        posibles = [codigo]
        if codigo.isdigit() and len(codigo) == 12:
            posibles.append('0' + codigo)
        if codigo.isdigit() and len(codigo) == 13 and codigo.startswith('0'):
            posibles.append(codigo[1:])
        Product = self.env['product.product'].sudo().with_context(active_test=False)
        p = Product.search([('barcode', 'in', posibles)], limit=1)
        if not p and 'product.barcode' in self.env:
            p = self.env['product.barcode'].sudo().search([('name', 'in', posibles)], limit=1).product_id
        if not p and codigo:
            p = Product.search([('default_code', '=', codigo)], limit=1)
        return p

    @api.model
    def ubicacion_por_codigo(self, codigo):
        """Hueco interno de la compañía por su código de barras; vacío si no es un sitio."""
        loc = self.env['stock.location'].sudo().search(
            [('barcode', '=', (codigo or '').strip()), ('usage', '=', 'internal'),
             ('company_id', 'in', [comun.COMPANY_ID, False])], limit=2)
        return loc if len(loc) == 1 else self.env['stock.location']

    @api.model
    def _ultima_lectura(self, emp, desde):
        """(ubicación, fecha) de la última prenda que ha leído en Lecturas desde esa hora; (vacío, None) si nada."""
        Lectura = self.env['koroshi.preparacion.lectura'].sudo()
        lec = Lectura.search([('employee_id', '=', emp.id), ('move_line_id', '!=', False), ('tipo', '=', 'leer'),
                              ('resultado', '=', 'ok'), ('fecha', '>=', desde)], order='fecha desc, id desc', limit=1)
        if not lec or not lec.move_line_id.exists():
            return self.env['stock.location'], None
        return Lectura._ubi(lec.move_line_id), lec.fecha

    @api.model
    def _minutos(self, fecha, ahora):
        return (ahora - fecha).total_seconds() / 60.0 if fecha else None

    @api.model
    def _posicion(self, emp, ubicacion, ahora):
        """Dónde está quien la encontró: el hueco que ha leído o su última lectura de hace poco."""
        if ubicacion:
            return ubicacion, 'leído'
        if emp:
            desde = fields.Datetime.subtract(ahora, minutes=logica.MINUTOS_POSICION)
            loc, _fecha = self._ultima_lectura(emp, desde)
            if loc:
                return loc, 'tu última lectura'
        return self.env['stock.location'], ''

    # ------------------------------------------------------------------ qué la pide
    @api.model
    def _lineas_pendientes(self, product):
        """Líneas de OUT sin validar con esa prenda por leer, en un hueco interno de la compañía."""
        mls = self.env['stock.move.line'].sudo().search([
            ('product_id', '=', product.id),
            ('state', 'not in', ('done', 'cancel', 'draft')),
            ('picking_id.picking_type_code', '=', 'outgoing'),
            ('picking_id.state', 'not in', ('done', 'cancel', 'draft')),
            ('picking_id.company_id', '=', comun.COMPANY_ID),
            ('location_id.usage', '=', 'internal'),
        ], limit=MAX_LINEAS)
        return mls.filtered(lambda l: float_compare(l.qty_done, l.product_uom_qty,
                                                    precision_rounding=l.product_uom_id.rounding) < 0)

    @api.model
    def _tareas_en_curso(self, pickings):
        """{picking.id: tarea} de las tareas de Lecturas en curso de esas OUT (sola o en su agrupación)."""
        Tarea = self.env['koroshi.operario.tarea'].sudo()
        batches = pickings.mapped('batch_id')
        dom = [('estado', '=', 'curso'), '|', ('picking_id', 'in', pickings.ids), ('batch_id', 'in', batches.ids)]
        res = {}
        for t in Tarea.search(dom, order='inicio desc'):
            for p in t._pickings():
                if p.id in pickings.ids and p.id not in res:
                    res[p.id] = t
        return res

    @api.model
    def _siguiente(self, tarea):
        """Ubicación de la siguiente línea que le queda por leer en su ruta (el orden de Lecturas)."""
        Lectura = self.env['koroshi.preparacion.lectura'].sudo()
        mls = tarea._pickings().mapped('move_line_ids').filtered(
            lambda l: l.state not in ('done', 'cancel') and float_compare(
                l.qty_done, l.product_uom_qty, precision_rounding=l.product_uom_id.rounding) < 0)
        mls = Lectura._ordenar(mls)
        return Lectura._ubi(mls[0]) if mls else self.env['stock.location']

    @api.model
    def _faltantes(self, product):
        return self.env['koroshi.faltante'].sudo().search(
            [('product_id', '=', product.id), ('estado', 'in', ('pendiente', 'no_existe')),
             ('cantidad_faltant', '>', 0),   # sin uds en FALTANTE (o en pérdidas) no hay nada que devolver
             ('company_id', '=', comun.COMPANY_ID)], order='fecha desc', limit=5)

    @api.model
    def _faltante_json(self, f):
        if f.en_ronda:
            puede, motivo = False, 'Está en la ronda %s: léela en esa INT (Lecturas).' % (
                f.ronda_move_id.picking_id.name or '')
        elif float_compare(f.cantidad_faltant, 1, precision_rounding=f.product_id.uom_id.rounding) > 0:
            puede, motivo = False, ('Es un faltante de %d uds: llévala a %s y que la oficina lo marque.'
                                    % (f.cantidad_faltant, self._sitio_sin_hueco()))
        elif f.ubicacion_vieja_id.usage != 'internal':
            puede, motivo = False, 'Su hueco no es una ubicación interna: llévala a %s.' % self._sitio_sin_hueco()
        else:
            puede, motivo = True, ''
        return {'id': f.id, 'out': f.picking_id.name or 'Puesto a 0', 'hueco': self._ubi_corta(f.ubicacion_vieja_id),
                'fecha': comun.a_local(f.fecha).strftime('%d/%m %H:%M') if f.fecha else '',
                'puede': puede, 'motivo': motivo}

    @api.model
    def _huecos_con_stock(self, product):
        """{ubicación: uds} donde Odoo tiene la prenda, solo huecos de lineal o de muelle (como faltantes)."""
        Faltante = self.env['koroshi.faltante'].sudo()
        quants = self.env['stock.quant'].sudo().search(
            [('product_id', '=', product.id), ('quantity', '>', 0), ('location_id.usage', '=', 'internal'),
             ('location_id.company_id', 'in', [comun.COMPANY_ID, False])])
        res = {}
        for q in quants:
            if not Faltante._excluida(q.location_id):
                res[q.location_id] = res.get(q.location_id, 0.0) + q.quantity
        return res

    @api.model
    def _sitio_sin_hueco(self):
        return self.env['ir.config_parameter'].sudo().get_param(PARAM_SITIO) or SITIO_DEFECTO

    # ------------------------------------------------------------------ la búsqueda
    @api.model
    def buscar(self, product, emp, ubicacion, sin_faltantes=False, codigo=''):
        """Todo lo que enseña la PDA y el registro apuntado. emp y ubicacion pueden venir vacíos."""
        ahora = fields.Datetime.now()
        origen_loc, origen_fuente = self._posicion(emp, ubicacion, ahora)
        origen = self._parada(origen_loc)

        # A: faltantes pendientes de esta prenda
        faltantes = self.env['koroshi.faltante'] if sin_faltantes else self._faltantes(product)

        # B y C: OUT que la piden
        mls = self._lineas_pendientes(product)
        pickings = mls.mapped('picking_id')
        tareas = self._tareas_en_curso(pickings) if pickings else {}
        personas, sin_empezar, vistas, activas = [], [], set(), {}
        for ml in mls:
            uds = ml.product_uom_qty - ml.qty_done
            t = tareas.get(ml.picking_id.id)
            if t and t.id not in activas:
                minutos_tarea = self._minutos(t._ultima_actividad(), ahora)
                activas[t.id] = minutos_tarea is not None and minutos_tarea <= logica.MINUTOS_ACTIVA
            activa = bool(t) and activas[t.id]
            if activa:
                if (t.id, ml.picking_id.id) in vistas:
                    continue
                vistas.add((t.id, ml.picking_id.id))
                actual, fecha = self._ultima_lectura(t.employee_id, t.inicio)
                siguiente = self._siguiente(t)
                personas.append({
                    'employee_id': t.employee_id.id, 'nombre': t.employee_id.name or '',
                    'out': ml.picking_id.name, 'picking_id': ml.picking_id.id,
                    'agrupacion': t.batch_id.name if t.tipo == 'agrupacion' else '',
                    'hueco_linea': self._ubi_corta(ml.location_id), 'hueco_linea_id': ml.location_id.id,
                    'esta_en': self._ubi_corta(actual), 'va_a': self._ubi_corta(siguiente),
                    'minutos': self._minutos(fecha, ahora), 'uds': uds,
                    'actual': self._parada(actual), 'siguiente': self._parada(siguiente),
                })
            else:
                sin_empezar.append({'out': ml.picking_id.name, 'picking_id': ml.picking_id.id,
                                    'hueco': self._ubi_corta(ml.location_id), 'hueco_id': ml.location_id.id,
                                    'parada': self._parada(ml.location_id), 'uds': uds,
                                    'nombre': ml.location_id.complete_name or '',
                                    'en_curso_sin_leer': bool(t)})
        personas = logica.ordenar_personas(personas, ruta.distancia, origen)[:logica.MAX_PERSONAS]
        sin_empezar = logica.ordenar_huecos(sin_empezar, ruta.distancia, origen)[:logica.MAX_SIN_EMPEZAR]

        # D: huecos con stock (también se enseñan en B y C como «si no»)
        huecos = [{'hueco': self._ubi_corta(loc), 'hueco_id': loc.id, 'uds': uds, 'parada': self._parada(loc),
                   'nombre': loc.complete_name or ''} for loc, uds in self._huecos_con_stock(product).items()]
        huecos = logica.ordenar_huecos(huecos, ruta.distancia, origen)[:logica.MAX_HUECOS]

        caso = logica.caso(faltantes, personas, sin_empezar, huecos)
        vals = {'employee_id': emp.id if emp else False, 'codigo': codigo, 'product_id': product.id,
                'ubicacion_operario_id': origen_loc.id or False, 'caso': caso,
                'company_id': comun.COMPANY_ID}
        sitio = self._sitio_sin_hueco()
        if caso == 'A':
            f = faltantes[0]
            vals.update(destino='Faltante de %s: a %s' % (f.picking_id.name or 'puesto a 0',
                                                          self._ubi_corta(f.ubicacion_vieja_id)),
                        faltante_id=f.id, picking_id=f.picking_id.id or False,
                        destino_ubicacion_id=f.ubicacion_vieja_id.id)
        elif caso == 'B':
            p = personas[0]
            vals.update(destino='A %s (%s)' % (p['nombre'], p['out']), picking_id=p['picking_id'],
                        para_employee_id=p['employee_id'], destino_ubicacion_id=p['hueco_linea_id'])
        elif caso == 'C':
            s = sin_empezar[0]
            vals.update(destino='A su hueco %s (%s sin empezar)' % (s['hueco'], s['out']),
                        picking_id=s['picking_id'], destino_ubicacion_id=s['hueco_id'])
        elif caso == 'D':
            vals.update(destino='A su hueco %s (no la pide nadie)' % huecos[0]['hueco'],
                        destino_ubicacion_id=huecos[0]['hueco_id'])
        else:
            vals.update(destino='A %s (Odoo no la tiene en ningún hueco)' % sitio)
        registro = self.sudo().create(vals)

        # A la PDA solo lo que pinta (sin las paradas ni el nombre completo de la ubicación, que eran para ordenar)
        for p in personas:
            for k in ('actual', 'siguiente'):
                p.pop(k, None)
            p['minutos_txt'] = logica.texto_minutos(p['minutos'])
        for h in sin_empezar + huecos:
            for k in ('parada', 'nombre'):
                h.pop(k, None)
        for x in personas + sin_empezar + huecos:
            x['metros_txt'] = logica.texto_metros(x.get('metros'))
        return {
            'ok': True, 'tipo': 'resultado', 'registro_id': registro.id, 'caso': caso,
            'producto': {'id': product.id, 'nombre': product.display_name or '', 'ean': product.barcode or ''},
            'desde': self._ubi_corta(origen_loc), 'desde_fuente': origen_fuente,
            'faltantes': [self._faltante_json(f) for f in faltantes],
            'personas': personas, 'sin_empezar': sin_empezar, 'huecos': huecos, 'sitio': sitio,
        }

    # ------------------------------------------------------------------ lo que contesta el operario
    def contestar(self, resultado, emp=None):
        self.ensure_one()
        if resultado not in ('hecho', 'no_sirve'):
            raise UserError('Respuesta no válida.')
        vals = {'resultado': resultado}
        if emp and not self.employee_id:
            vals['employee_id'] = emp.id
        self.sudo().write(vals)
        return True

    def encontrada(self, emp=None):
        """Caso A: de FALTANTE a su hueco (koroshi.faltante.marcar_encontrado, lo mismo que en la oficina)."""
        self.ensure_one()
        f = self.faltante_id.sudo()
        if not f:
            raise UserError('Esta búsqueda no es de un faltante.')
        datos = self._faltante_json(f)
        if not datos['puede']:
            raise UserError(datos['motivo'])
        f.marcar_encontrado(f.ubicacion_vieja_id)
        quien = (emp or self.employee_id).name or self.env.user.name
        f.write({'nota': ('%s Encontrada en el suelo por %s (PDA).' % (f.nota or '', quien)).strip()})
        self.sudo().write({'resultado': 'encontrada', 'employee_id': (emp or self.employee_id).id or False})
        return datos['hueco']
