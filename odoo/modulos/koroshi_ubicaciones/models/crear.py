# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Ubicaciones: «Crear e imprimir» (pedido de Isaac, 23/11/2026).
# Un botón crea los contenedores o los huecos de un lineal y abre el PDF de sus etiquetas (Zebra 4x6), sin exportar
# nada. Otro vuelve a imprimir lo que ya existe. Solo crea stock.location (como se hacía a mano) y apunta cada tanda en
# su propia tabla (koroshi.ubicaciones.tanda). No añade campos a tablas de Odoo.
# Diseño: bin/versiones/diseno-crear-imprimir-lineales-contenedores_2026-11-23.md
# =============================================================================
from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.koroshi_base import comun
from odoo.addons.koroshi_ubicaciones import nombres as N

PADRE = 'EFFEC/Stock/NAVE2'     # donde nacen hoy los contenedores sueltos y los huecos de los lineales


class KoroshiUbicacionesTanda(models.Model):
    """Lo que se ha creado o vuelto a imprimir de una vez: quién, cuándo y qué ubicaciones (para reimprimir)."""
    _name = 'koroshi.ubicaciones.tanda'
    _description = 'KOROSHI: tanda de ubicaciones creadas o impresas'
    _order = 'id desc'

    name = fields.Char('Qué', required=True, readonly=True)
    tipo = fields.Selection([('contenedores', 'Contenedores'), ('lineal', 'Lineal'),
                             ('reimprimir', 'Volver a imprimir')], required=True, readonly=True)
    user_id = fields.Many2one('res.users', 'Quién', default=lambda s: s.env.user, readonly=True)
    fecha = fields.Datetime('Cuándo', default=fields.Datetime.now, readonly=True)
    cantidad = fields.Integer('Etiquetas', readonly=True)
    ubicacion_ids = fields.Many2many('stock.location', 'koroshi_ubicaciones_tanda_loc_rel', 'tanda_id', 'location_id',
                                     string='Ubicaciones', readonly=True)

    def action_imprimir(self):
        self.ensure_one()
        locs = self.ubicacion_ids.with_context(active_test=False)
        if not locs:
            raise UserError('Esta tanda no tiene ubicaciones.')
        return self.env['koroshi.ubicaciones.crear']._imprimir(locs)


class KoroshiUbicacionesCrear(models.TransientModel):
    _name = 'koroshi.ubicaciones.crear'
    _description = 'KOROSHI: crear e imprimir contenedores y lineales'

    def _padre_defecto(self):
        return self.env['stock.location'].search([('complete_name', '=', PADRE),
                                                  ('company_id', '=', comun.COMPANY_ID)], limit=1)

    modo = fields.Selection([('contenedores', 'Contenedores'), ('lineal', 'Lineal'),
                             ('reimprimir', 'Volver a imprimir')], 'Qué', required=True, default='contenedores')
    padre_id = fields.Many2one('stock.location', 'Dentro de', default=_padre_defecto,
                               domain=[('usage', '=', 'internal')])
    # contenedores
    prefijo = fields.Selection([('KO_', 'KO_'), ('TT_', 'TT_')], 'Prefijo', default='KO_')
    cantidad = fields.Integer('Cuántos', default=100)
    # lineal
    lineal = fields.Char('Lineal', help='L200 o MU-05')
    p_desde = fields.Integer('De la posición (P)', default=0)
    p_hasta = fields.Integer('A la posición (P)', default=0)
    c_desde = fields.Integer('De la altura (C)', default=1)
    c_hasta = fields.Integer('A la altura (C)', default=4)
    # volver a imprimir
    texto = fields.Char('Qué etiquetas', help='L94 · L94 P10-P20 · KO_171126 · KO_171126_001-050 · un nombre')
    # lo que va a pasar, antes de pulsar
    resumen = fields.Text('Se va a hacer', compute='_compute_resumen')
    se_puede = fields.Boolean(compute='_compute_resumen')

    # ------------------------------------------------------------------ cálculo (sin escribir nada)
    def _hoy(self):
        return comun.hoy_local()

    def _contenedores_a_crear(self):
        pref = N.prefijo_dia(self.prefijo or 'KO_', self._hoy())
        existentes = self.env['stock.location'].with_context(active_test=False).search(
            [('name', '=like', N.escapar_like(pref) + '%')]).mapped('name')
        return N.nombres_contenedores(pref, N.siguiente_numero(existentes, pref), self.cantidad)

    def _huecos_del_lineal(self, lineal):
        """{clave «L94 P35 C1»: ubicación} de los huecos que ya existen de un lineal (con o sin número delante,
        también archivados), de la compañía. Si hay dos con la misma clave, el que tiene código de barras."""
        lk = N.escapar_like(lineal) + ' P%'
        locs = self.env['stock.location'].with_context(active_test=False).search([
            ('company_id', 'in', [comun.COMPANY_ID, False]),
            '|', '|', ('barcode', '=like', lk), ('name', '=like', lk), ('name', '=like', '% - ' + lk)])
        res = {}
        for loc in locs:
            clave = N.clave_hueco(loc.name) or N.clave_hueco(loc.barcode)
            if clave and (clave not in res or (loc.barcode and not res[clave].barcode)):
                res[clave] = loc
        return res

    def _huecos_a_crear(self):
        """(nombres nuevos, nombres que ya existen)."""
        nuevos = N.nombres_lineal(self.lineal, self.p_desde, self.p_hasta, self.c_desde, self.c_hasta)
        ya = self._huecos_del_lineal(N.lineal_normalizado(self.lineal))
        # el código de barras es único por compañía: también choca un código igual en otra ubicación
        con_codigo = set(self.env['stock.location'].with_context(active_test=False).search(
            [('barcode', 'in', nuevos), ('company_id', '=', comun.COMPANY_ID)]).mapped('barcode'))
        return nuevos, [n for n in nuevos if n in ya or n in con_codigo]

    def _a_reimprimir(self):
        q = N.interpretar_reimpresion(self.texto)
        Loc = self.env['stock.location'].with_context(active_test=False)
        if q['tipo'] == 'lineal':
            huecos = self._huecos_del_lineal(q['lineal'])
            claves = sorted(huecos, key=N.partes_hueco)
            if q['p_desde'] is not None:
                claves = [k for k in claves if q['p_desde'] <= N.partes_hueco(k)[1] <= q['p_hasta']]
            locs = Loc.browse([huecos[k].id for k in claves])
        elif q['tipo'] == 'contenedores':
            todos = Loc.search([('name', '=like', N.escapar_like(q['prefijo']) + '%')], order='name')
            if q['desde'] is not None:
                todos = todos.filtered(lambda l: q['desde'] <= (N.numero_contenedor(l.name, q['prefijo']) or -1)
                                       <= q['hasta'])
            locs = todos.sorted(lambda l: (N.numero_contenedor(l.name, q['prefijo']) or 0, l.name))
        else:
            locs = Loc.search([('company_id', 'in', [comun.COMPANY_ID, False]), '|',
                               ('name', '=', q['nombre']), ('barcode', '=', q['nombre'])], limit=5)
        if len(locs) > N.MAX_UBICACIONES:
            raise ValueError('Son %d etiquetas: como mucho %d de una vez. Pide un trozo (L94 P10-P20).'
                             % (len(locs), N.MAX_UBICACIONES))
        return locs

    @api.depends('modo', 'prefijo', 'cantidad', 'lineal', 'p_desde', 'p_hasta', 'c_desde', 'c_hasta', 'texto',
                 'padre_id')
    def _compute_resumen(self):
        for w in self:
            try:
                w.resumen, w.se_puede = w._texto_resumen(), True
            except (ValueError, UserError) as e:
                w.resumen, w.se_puede = str(e.args[0] if e.args else e), False

    def _texto_resumen(self):
        if self.modo != 'reimprimir' and not self.padre_id:
            raise ValueError('Falta «Dentro de» (%s).' % PADRE)
        if self.modo == 'contenedores':
            nombres = self._contenedores_a_crear()
            return 'Se crean %d contenedores dentro de %s: %s.\nDespués se abre el PDF con sus %d etiquetas.' % (
                len(nombres), self.padre_id.complete_name, N.resumen_lista(nombres, 3), len(nombres))
        if self.modo == 'lineal':
            if not (self.lineal or '').strip():
                raise ValueError('Escribe el lineal (L200 o MU-05), de qué P a qué P y qué alturas.')
            nuevos, ya = self._huecos_a_crear()
            if ya:
                raise ValueError('No se crea nada: ya existen %d de estos huecos (%s). Cambia las posiciones o '
                                 'usa «Volver a imprimir».' % (len(ya), N.resumen_lista(ya, 4)))
            return 'Se crean %d huecos dentro de %s: %s.\nNombre y código de barras iguales (como MU-04 P18 C1).\n' \
                   'Después se abre el PDF con sus %d etiquetas.' % (
                       len(nuevos), self.padre_id.complete_name, N.resumen_lista(nuevos, 4), len(nuevos))
        locs = self._a_reimprimir()
        if not locs:
            raise ValueError('No encuentro nada con «%s».' % (self.texto or ''))
        return 'Se imprimen %d etiquetas: %s.' % (len(locs), N.resumen_lista(locs.mapped('name'), 4))

    # ------------------------------------------------------------------ botones
    def _imprimir(self, locs):
        return self.env.ref('koroshi_ubicaciones.action_etiqueta_ubicacion').report_action(locs)

    def _crear(self, nombres):
        Loc = self.env['stock.location'].sudo()   # crear ubicaciones es de «Inventario / Administrador»
        locs = Loc.browse()
        for n in nombres:
            locs |= Loc.create({'name': n, 'barcode': n, 'location_id': self.padre_id.id, 'usage': 'internal',
                                'company_id': comun.COMPANY_ID})
        return self.env['stock.location'].browse(locs.ids)

    def action_crear_imprimir(self):
        self.ensure_one()
        try:
            self._texto_resumen()
        except ValueError as e:
            raise UserError(str(e.args[0] if e.args else e))
        Tanda = self.env['koroshi.ubicaciones.tanda'].sudo()
        if self.modo == 'contenedores':
            nombres = self._contenedores_a_crear()
            locs = self._crear(nombres)
            que = '%d contenedores %s a %s' % (len(nombres), nombres[0], nombres[-1])
        elif self.modo == 'lineal':
            nombres, _ya = self._huecos_a_crear()
            locs = self._crear(nombres)
            que = 'Lineal %s: %d huecos %s a %s' % (N.lineal_normalizado(self.lineal), len(nombres), nombres[0],
                                                     nombres[-1])
        else:
            locs = self._a_reimprimir()
            que = 'Volver a imprimir «%s»: %d etiquetas' % (self.texto.strip(), len(locs))
        Tanda.create({'name': que, 'tipo': self.modo, 'user_id': self.env.user.id, 'cantidad': len(locs),
                      'ubicacion_ids': [(6, 0, locs.ids)]})
        return self._imprimir(locs)


class InformeEtiquetaUbicacion(models.AbstractModel):
    """Datos de cada etiqueta 4x6: qué va en grande y qué código de barras."""
    _name = 'report.koroshi_ubicaciones.etiqueta_ubicacion'
    _description = 'KOROSHI: etiqueta de hueco o contenedor'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['stock.location'].with_context(active_test=False).browse(docids)
        return {'doc_ids': docids, 'doc_model': 'stock.location', 'docs': docs, 'etiqueta': self._etiqueta}

    @api.model
    def _etiqueta(self, loc):
        from werkzeug.urls import url_quote
        codigo = loc.barcode or loc.name
        partes = N.partes_hueco(loc.name) or N.partes_hueco(loc.barcode or '')
        if partes:
            lineal, p, c = partes
            et = {'tipo': 'hueco', 'arriba': 'LINEAL', 'grande': lineal, 'medio': 'P%02d  ·  C%d' % (p, c)}
        elif (loc.name or '')[:3] in N.PREFIJOS_CONTENEDOR:
            et = {'tipo': 'contenedor', 'arriba': 'CONTENEDOR', 'grande': loc.name, 'medio': ''}
        else:
            et = {'tipo': 'otro', 'arriba': 'UBICACIÓN', 'grande': loc.name, 'medio': ''}
        et['codigo'] = codigo
        et['sin_codigo'] = not loc.barcode
        et['url'] = '/report/barcode/?type=Code128&value=%s&width=900&height=300&humanreadable=0' % url_quote(codigo)
        return et
