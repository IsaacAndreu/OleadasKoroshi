# -*- coding: utf-8 -*-
# =============================================================================
# TUCTUC Base - almacenes que usan la PDA (uno por compañía de la nave de Oriola - Amposta).
# La nave es una, pero en Odoo son tres compañías con su almacén: PRIME COLLECTIONS (WH-OR), MODA INTIMA (MODAI) y
# UNITED BRANDS (UBRAN). Cada fila dice qué almacén usa la PDA y sus ubicaciones especiales (SORTER, faltantes) y la
# zona de picking. Los módulos tuctuc_* sacan de aquí las compañías (en koroshi_* era COMPANY_ID = 8).
# =============================================================================
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Almacenes que se crean al instalar (si existen en la base de datos): código del almacén de Odoo
CODIGOS_INICIALES = ('WH-OR', 'MODAI', 'UBRAN')


class TuctucAlmacen(models.Model):
    _name = 'tuctuc.almacen'
    _description = 'TUCTUC PDA: almacén que usa la PDA'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Orden', default=10)
    active = fields.Boolean(string='Activo', default=True,
                            help='Si se desactiva, la PDA deja de trabajar con este almacén y su compañía.')
    warehouse_id = fields.Many2one('stock.warehouse', string='Almacén', required=True, ondelete='restrict')
    name = fields.Char(related='warehouse_id.name', string='Nombre', readonly=True)
    codigo = fields.Char(related='warehouse_id.code', string='Código', readonly=True)
    company_id = fields.Many2one(related='warehouse_id.company_id', string='Compañía', store=True, readonly=True)
    sorter_id = fields.Many2one(
        'stock.location', string='SORTER', domain=[('usage', '=', 'internal')],
        help='Ubicación del sorter: las INT de las oleadas (WEB, PED. INICIAL...) van de la estantería aquí, sin caja. '
             'Vacío si el almacén no tiene sorter.')
    faltantes_id = fields.Many2one(
        'stock.location', string='Ubicación de faltantes', domain=[('usage', '=', 'internal')],
        help='Donde van las unidades que no se encuentran al preparar (la usa tuctuc_faltantes).')
    zona_picking = fields.Char(
        string='Zona de picking', default='N1',
        help='Primer tramo de las ubicaciones de picking después de Stock (WH-OR/Stock/N1/...).')

    _sql_constraints = [
        ('warehouse_unico', 'unique(warehouse_id)', 'Ese almacén ya está en la lista de la PDA.'),
    ]

    # ------------------------------------------------------------------ consultas para los módulos tuctuc_*
    @api.model
    def activos(self):
        """Almacenes activos de la PDA (con sudo: los lee cualquier ruta de la PDA)."""
        return self.sudo().search([])

    @api.model
    def companias(self):
        """Compañías de los almacenes activos (res.company)."""
        return self.activos().mapped('company_id')

    @api.model
    def de_ubicacion(self, location):
        """Almacén de la PDA al que pertenece la ubicación (vacío si ninguno). Por parent_path, sin consultar más."""
        location = location.sudo()
        ruta = location.parent_path or ''
        for alm in self.activos():
            vista = alm.warehouse_id.view_location_id
            if vista.parent_path and ruta.startswith(vista.parent_path):
                return alm
        return self.browse()

    @api.model
    def de_picking(self, picking):
        """Almacén de la PDA de un albarán: el del tipo de operación o, si no tiene, el de la ubicación de origen."""
        picking = picking.sudo()
        wh = picking.picking_type_id.warehouse_id
        if wh:
            alm = self.activos().filtered(lambda a: a.warehouse_id == wh)
            if alm:
                return alm[:1]
        return self.de_ubicacion(picking.location_id)

    # ------------------------------------------------------------------ alta al instalar
    @api.model
    def _crear_iniciales(self):
        """Al instalar (data/almacenes.xml, noupdate): una fila por cada almacén de CODIGOS_INICIALES que exista, con su
        SORTER (<código>/SORTER) y su ubicación de faltantes (la primera FALTAS... dentro del almacén), si las hay.
        Lo que no exista se salta: se completa a mano en Inventario > Configuración > TUCTUC PDA: almacenes."""
        Wh = self.env['stock.warehouse'].sudo().with_context(active_test=False)
        Loc = self.env['stock.location'].sudo()
        orden = 10
        for codigo in CODIGOS_INICIALES:
            wh = Wh.search([('code', '=', codigo)], limit=1)
            if not wh or self.sudo().with_context(active_test=False).search([('warehouse_id', '=', wh.id)]):
                continue
            sorter = Loc.search([('complete_name', '=', '%s/SORTER' % codigo), ('usage', '=', 'internal')], limit=1)
            faltas = Loc.search([('location_id', 'child_of', wh.view_location_id.id), ('usage', '=', 'internal'),
                                 ('name', '=like', 'FALTAS%')], order='id', limit=1)
            self.sudo().create({'sequence': orden, 'warehouse_id': wh.id, 'sorter_id': sorter.id or False,
                                'faltantes_id': faltas.id or False})
            _logger.info('TUCTUC Base: almacén %s en la PDA (SORTER %s, faltantes %s)', codigo,
                         sorter.complete_name or '-', faltas.complete_name or '-')
            orden += 10
        return True
