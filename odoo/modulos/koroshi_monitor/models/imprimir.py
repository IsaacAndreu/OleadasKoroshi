# -*- coding: utf-8 -*-
# =============================================================================
# v1.42.0 (23/11/2026): seccion «Imprimir» del Monitor picking (Isaac, nota de voz del 23/11: que lo de imprimir
# de picking este en un solo sitio, el Monitor, y que el operario pulse un boton y le salga todo).
#   - Web: la lista de picking de cada agrupacion WEB_ddmmaa_nn de hoy: el «Picking Operations» del INT Stock -> SORTER
#     que nace de ella (origen = nombre de la agrupacion), que es el que lleva las ubicaciones. El «Batch Transfer» de
#     la agrupacion solo lista las OUT desde SORTER, sin ubicaciones: sale solo si la agrupacion aun no tiene INT.
#   - Zalando y About You: la lista de picking («Picking Operations») de sus OUT reservadas sin validar.
#   - INT: la lista de picking de los traspasos internos de hoy reservados sin validar.
# Solo lee e imprime: no escribe nada (las etiquetas de zona, que si crean matriculas, siguen en koroshi_zonas).
# =============================================================================
from odoo import api, models
from odoo.exceptions import UserError
from odoo.addons.koroshi_base import comun

INFORME_LOTE = 'stock_picking_batch.report_picking_batch'     # «Batch Transfer»
INFORME_OUT = 'stock.report_picking'                          # «Picking Operations»
MARKETPLACES = (('zalando', 'ZALANDO', 'Zalando'), ('aboutyou', 'ABOUT YOU', 'About You'))


class KoroshiMonitorImprimir(models.AbstractModel):
    _name = 'koroshi.monitor.imprimir'
    _description = 'KOROSHI Monitor - imprimir listas de picking'

    def _hoy(self):
        return comun.rango_dia_utc(comun.hoy_local())

    def _lotes_web(self):
        ini, fin = self._hoy()
        return self.env['stock.picking.batch'].search(
            [('name', '=like', 'WEB\\_%'), ('state', '!=', 'cancel'),
             ('create_date', '>=', ini), ('create_date', '<', fin)], order='name')

    def _ints_de_lote(self, lote):
        return self.env['stock.picking'].search(
            [('company_id', '=', comun.COMPANY_ID), ('picking_type_code', '=', 'internal'), ('origin', '=', lote.name),
             ('state', '!=', 'cancel')], order='name')

    def _outs_marketplace(self, texto):
        return self.env['stock.picking'].search(
            [('company_id', '=', comun.COMPANY_ID), ('picking_type_code', '=', 'outgoing'), ('state', '=', 'assigned'),
             ('partner_id.display_name', 'ilike', texto)], order='name')

    def _ints(self):
        ini, fin = self._hoy()
        return self.env['stock.picking'].search(
            [('company_id', '=', comun.COMPANY_ID), ('picking_type_code', '=', 'internal'), ('state', '=', 'assigned'),
             ('create_date', '>=', ini), ('create_date', '<', fin)], order='name')

    @api.model
    def pendientes(self):
        """Lo que sale en la seccion «Imprimir»: [{clave, ref, nombre, n, titulo}] (n = 0 -> boton apagado)."""
        res = []
        for lote in self._lotes_web():
            outs = lote.picking_ids.filtered(lambda p: p.state != 'cancel')
            res.append({'clave': 'web', 'ref': lote.id, 'nombre': 'Web ' + lote.name, 'n': len(outs),
                        'titulo': 'Lista de picking de la agrupación %s (%d OUT)' % (lote.name, len(outs))})
        if not res:
            res.append({'clave': 'web', 'ref': 0, 'nombre': 'Web', 'n': 0,
                        'titulo': 'Hoy no hay agrupación web (WEB_)'})
        for clave, texto, nombre in MARKETPLACES:
            n = len(self._outs_marketplace(texto))
            res.append({'clave': clave, 'ref': 0, 'nombre': nombre, 'n': n,
                        'titulo': 'Lista de picking de las OUT de %s reservadas sin validar (%d)' % (nombre, n)})
        n = len(self._ints())
        res.append({'clave': 'int', 'ref': 0, 'nombre': 'INT', 'n': n,
                    'titulo': 'Lista de picking de los traspasos internos de hoy sin validar (%d)' % n})
        return res

    def _informe(self, report_name):
        informe = self.env['ir.actions.report'].search([('report_name', '=', report_name)], limit=1)
        if not informe:
            raise UserError('No existe el informe %s: no se puede imprimir.' % report_name)
        return informe

    @api.model
    def imprimir(self, clave, ref=0):
        """Devuelve la accion del PDF. clave: 'web' (ref = id de la agrupacion WEB_), 'zalando', 'aboutyou', 'int'."""
        if clave == 'web':
            lote = self._lotes_web().filtered(lambda b: b.id == ref)
            if not lote:
                raise UserError('La agrupación web ya no está (cancelada o no es de hoy). Recarga el Monitor.')
            ints = self._ints_de_lote(lote)
            if ints:
                return self._informe(INFORME_OUT).report_action(ints)
            return self._informe(INFORME_LOTE).report_action(lote)
        if clave == 'int':
            registros = self._ints()
            vacio = 'No hay traspasos internos (INT) de hoy sin validar.'
        else:
            marketplace = [m for m in MARKETPLACES if m[0] == clave]
            if not marketplace:
                raise UserError('No sé imprimir «%s».' % clave)
            registros = self._outs_marketplace(marketplace[0][1])
            vacio = 'No hay OUT de %s reservadas sin validar.' % marketplace[0][2]
        if not registros:
            raise UserError(vacio)
        return self._informe(INFORME_OUT).report_action(registros)
