# -*- coding: utf-8 -*-
# =============================================================================
# Etiquetas de zona: la accion 1843 "KOROSHI Etiquetas zona" dentro del modulo (fase 3).
# Diferencia con la 1843: las cajas de cada OUT salen de la tabla del reparto (koroshi.zonas.ejecucion.out,
# las mismas del "CAJAS n"), no de volver a calcularlas. Si la OUT no esta en la tabla, se calculan como la
# 1843 con los litros por caja de la configuracion. Lo demas es igual: reserva matriculas CJ de la secuencia de
# Zebra (zebra.label) con la nota 'ETQ ZONA <OUT>', reutiliza las que ya tenga y abre el informe
# koroshi.report_etiqueta_zona. Escribe lo mismo que la 1843 (zebra.label y un mensaje en la OUT), nada mas.
# =============================================================================
import datetime

from odoo import api, models
from odoo.exceptions import UserError

from ..motor import volumen

COMPANY_ID = 8
INFORME = 'koroshi.report_etiqueta_zona'
NOTA = 'ETQ ZONA '
MAX_CAJAS_OUT = 12


class KoroshiZonasEtiquetas(models.AbstractModel):
    _name = 'koroshi.zonas.etiquetas'
    _description = 'KOROSHI Zonas - etiquetas de zona'

    def _cajas_tabla(self, picking):
        fila = self.env['koroshi.zonas.ejecucion.out'].sudo().search(
            [('picking_id', '=', picking.id), ('prevision_conocida', '=', True),
             ('ejecucion_id.estado', 'in', ('hecho', 'historico'))], order='id desc', limit=1)
        return fila and fila.cajas_previstas or None

    @api.model
    def imprimir(self, picking_ids, modo='REAL'):
        if 'zebra.label' not in self.env:
            raise UserError('No esta el modelo zebra.label (matriculas de Zebra): no se puede imprimir.')
        Picking = self.env['stock.picking']
        outs = Picking.browse(picking_ids).exists()
        informe = self.env['ir.actions.report'].search([('report_name', '=', INFORME)], limit=1)
        errores = []
        if not outs:
            errores.append('No hay OUT: seleccionalas en la lista')
        if not informe:
            errores.append('No existe el informe %s' % INFORME)
        if errores:
            raise UserError('ETIQUETAS DE ZONA - NO SE HA HECHO NADA\n\n' + '\n'.join(errores))
        medidas = self.env['koroshi.zonas.config'].obtener().medidas()
        plan = []
        saltadas = []
        for p in outs:
            if p.company_id.id != COMPANY_ID or p.picking_type_code != 'outgoing' or p.state in ('done', 'cancel'):
                saltadas.append('%s: %s' % (p.name, p.state))
                continue
            litros = 0.0
            uds = 0.0
            for ml in p.move_line_ids:
                q = ml.product_uom_qty
                if q <= 0:
                    continue
                litros += volumen.litros_ud(ml.product_id.volume, ml.product_id.default_code, medidas) * q
                uds += q
            cajas = self._cajas_tabla(p)
            origen = 'reparto'
            if not cajas:
                cajas = volumen.cajas_de(litros, medidas)
                origen = 'calculo'
            cajas = max(1, min(cajas, MAX_CAJAS_OUT))
            nota = p.note or ''
            pos = nota.find('CAJA ')
            caja_tienda = pos >= 0 and nota[pos + 5:pos + 7] or ''
            zona = p.batch_id and p.batch_id.name.split('-')[-1] or ''
            ya = self.env['zebra.label'].search([('note', '=', NOTA + p.name)])
            plan.append(((zona, caja_tienda, p.name), (zona, caja_tienda, p, cajas, litros, uds, ya, origen)))
        plan = sorted(plan, key=lambda x: x[0])
        secuencia = self.env['ir.sequence'].search([('code', '=', 'zebra.label.code')], limit=1)
        siguiente = secuencia and secuencia.number_next_actual or 0
        nuevas_total = 0
        texto = ['KOROSHI ETIQUETAS ZONA - ' + (modo == 'REAL' and 'HECHO' or 'DIAGNOSTICO (NO SE HA ESCRITO NADA)'),
                 'OUT: %d' % len(plan), '',
                 'Zona | caja | OUT | tienda | pedido | uds | litros | etiquetas (de donde) | matriculas']
        imprimir = Picking
        for k, t in plan:
            zona, caja_tienda, p, cajas, litros, uds, ya, origen = t
            faltan = max(0, cajas - len(ya))
            cjs = ya.sorted('sequence_number').mapped('name')
            if faltan and modo == 'REAL':
                nuevas = self.env['zebra.label'].create_next_labels(quantity=faltan, note=NOTA + p.name)
                nuevas.write({'state': 'printed', 'print_date': datetime.datetime.now()})
                cjs += nuevas.sorted('sequence_number').mapped('name')
                p.message_post(body='Etiquetas de zona %s: %s' % (zona, ', '.join(cjs)))
            elif faltan:
                for i in range(faltan):
                    cjs.append('CJ%09d*' % (siguiente + nuevas_total + i))
            nuevas_total += faltan
            imprimir |= p
            nombre = p.partner_id.name or ''
            texto.append('   %s | %s | %s | %s | %s | %d | %d | %d (%s) | %s' % (
                zona, caja_tienda, p.name, nombre[:1] == 'K' and nombre or nombre.split(', ')[-1], p.origin or '',
                uds, litros, max(cajas, len(ya)), origen, ', '.join(cjs)))
        texto.append('')
        texto.append('Matriculas nuevas: %d%s' % (nuevas_total, modo != 'REAL' and
                                                   ' (las marcadas con * se crearian; no se ha gastado ninguna)' or ''))
        if saltadas:
            texto.append('No se imprimen (hechas o canceladas): ' + ', '.join(saltadas))
        if modo != 'REAL':
            raise UserError('\n'.join(texto))
        return informe.report_action(imprimir)
