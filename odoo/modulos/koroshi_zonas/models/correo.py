# -*- coding: utf-8 -*-
# =============================================================================
# Correo de las zonas del dia: la accion 1868 dentro del modulo (fase 3). Su cron (201) esta desactivado desde
# el 27/10. Diferencias con la 1868: el estado del reparto sale de la ejecucion de hoy (no de la primera linea de
# un ir.logging), los destinatarios de la configuracion (no escritos en el codigo) y se anade el % de cajas
# cerradas previsto. El mapa, el resumen y el detalle por zona son los mismos. Escribe un mail.mail (y lo envia).
# =============================================================================
import datetime
import logging

import pytz

from odoo import api, models
from odoo.addons.koroshi_base import comun

from . import lector

_logger = logging.getLogger(__name__)

COMPANY_ID = comun.COMPANY_ID     # v1.4.0: de koroshi_base
TZ = comun.TZ
COLORES = ['#2f7d4f', '#1f5fbf', '#b5562a', '#7a4bb0', '#b08a12', '#0e7c86', '#b03a6c', '#5b6b1e', '#6b6a65']


def esc(s):
    return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def lineal(nombre):
    for t in (nombre or '').replace('/', ' ').split(' '):
        if len(t) > 1 and t[0] == 'L' and t[1:].isdigit():
            return int(t[1:])
    return 0


class KoroshiZonasCorreo(models.AbstractModel):
    _name = 'koroshi.zonas.correo'
    _description = 'KOROSHI Zonas - correo de las zonas del día'

    @api.model
    def _estado_hoy(self, hoy):
        Ej = self.env['koroshi.zonas.ejecucion'].sudo()
        ej = Ej.search([('fecha', '=', hoy), ('modo', '=', 'real')], order='id desc', limit=1) or \
            Ej.search([('fecha', '=', hoy)], order='id desc', limit=1)
        if not ej:
            return 'No hay ejecucion del reparto de hoy', ''
        primera = (ej.informe or '').split('\n')[0] or dict(ej._fields['estado'].selection).get(ej.estado, '')
        extra = ej.comparacion and (' | sombra: %s' % dict(ej._fields['comparacion'].selection)[ej.comparacion]) or ''
        # v1.3.0: el aviso de hora de fin (y las OUT de dias anteriores), arriba del correo
        for l in (ej.informe or '').split('\n'):
            # v1.5.0: y las lineas HORA DE FIN (a que hora se acaba y cuantas personas harian falta)
            # v1.8.0: y las lineas TIPO DE DIA (reposicion o implantacion)
            if (l.startswith('AVISO:') or l.startswith('OUT de dias anteriores') or l.startswith('HORA DE FIN:')
                    or l.startswith('TIPO DE DIA:')):
                extra += ' | %s' % l
        return '%s (%s)%s' % (primera, ej.name, extra), ej.informe or ''

    @api.model
    def html(self, dia=None):
        tz = pytz.timezone(TZ)
        ahora = datetime.datetime.now(tz)
        hoy = dia or ahora.date()
        ddmm = hoy.strftime('%d%m')
        lotes = self.env['stock.picking.batch'].sudo().search(
            [('name', '=like', 'Z-%s-%%' % ddmm), ('company_id', '=', COMPANY_ID)], order='name')
        lotes = lotes.filtered(lambda l: lector.partir_nombre_lote(l.name))     # sin las de almacen (SALE...)
        estado, informe = self._estado_hoy(hoy)
        color = {}
        mapa = {}
        resumen = []
        detalle = []
        total_uds = 0
        for i, lote in enumerate(lotes):
            zona = lector.partir_nombre_lote(lote.name)[1]
            color[zona] = COLORES[i % len(COLORES)]
            filas = []
            uds = 0
            tiendas = {}
            lineales = {}
            for o in lote.picking_ids:
                nota = o.note or ''
                caja = ''
                if 'CAJA ' in nota:
                    caja = nota.split('CAJA ')[1].split(' ')[0]
                tienda = (o.partner_id.name or '').split(', ')[-1].split(' - ')[0]
                tiendas[tienda] = 1
                for ml in o.move_line_ids:
                    q = ml.product_uom_qty or ml.qty_done
                    if not q:
                        continue
                    loc = ml.location_id
                    if (loc.name or '')[:3] in ('KO_', 'TT_') and loc.location_id:
                        loc = loc.location_id
                    ln = lineal(loc.name)
                    if ln:
                        lineales[ln] = 1
                        mapa[ln] = zona
                    uds += q
                    filas.append((loc.complete_name or '', loc.name or '', ml.product_id.display_name or '', q, caja,
                                  tienda))
            total_uds += uds
            lin = sorted(lineales.keys())
            resumen.append('<tr><td style="padding:4px 8px"><b style="color:%s">%s</b></td>'
                           '<td style="padding:4px 8px;text-align:right">%d</td>'
                           '<td style="padding:4px 8px;text-align:right">%d</td>'
                           '<td style="padding:4px 8px;text-align:right">%d</td><td style="padding:4px 8px">%s</td></tr>' % (
                               color[zona], esc(lote.name), uds, len(lote.picking_ids), len(tiendas),
                               lin and ('L%d - L%d' % (lin[0], lin[-1])) or 'fuera de lineal'))
            filas = sorted(filas, key=lambda f: f[0])
            t = ['<h3 style="color:%s;margin:22px 0 6px">%s · %d uds · %d lineas</h3>' % (
                color[zona], esc(lote.name), uds, len(filas)),
                '<table style="border-collapse:collapse;font-size:12px"><tr style="background:#eee">'
                '<th style="padding:3px 6px;text-align:left">Ubicacion</th><th style="padding:3px 6px;text-align:left">'
                'Articulo</th><th style="padding:3px 6px">Uds</th><th style="padding:3px 6px">Caja</th>'
                '<th style="padding:3px 6px;text-align:left">Tienda</th></tr>']
            for f in filas:
                t.append('<tr><td style="padding:2px 6px;border-bottom:1px solid #eee">%s</td>'
                         '<td style="padding:2px 6px;border-bottom:1px solid #eee">%s</td>'
                         '<td style="padding:2px 6px;border-bottom:1px solid #eee;text-align:right">%d</td>'
                         '<td style="padding:2px 6px;border-bottom:1px solid #eee">%s</td>'
                         '<td style="padding:2px 6px;border-bottom:1px solid #eee">%s</td></tr>' % (
                             esc(f[1]), esc(f[2]), f[3], esc(f[4]), esc(f[5])))
            t.append('</table>')
            detalle.append(''.join(t))
        celdas = []
        fila = []
        maxl = mapa and max(mapa.keys()) or 0
        for n in range(1, maxl + 1):
            z = mapa.get(n)
            if z:
                fila.append('<td title="L%d %s" style="width:30px;height:24px;text-align:center;font-size:10px;'
                            'color:#fff;background:%s">%d<br>%s</td>' % (n, z, color[z], n, z))
            else:
                fila.append('<td style="width:30px;height:24px;text-align:center;font-size:10px;color:#999;'
                            'background:#f2f2f2">%d</td>' % n)
            if len(fila) == 20:
                celdas.append('<tr>%s</tr>' % ''.join(fila))
                fila = []
        if fila:
            celdas.append('<tr>%s</tr>' % ''.join(fila))
        partes = ['<div style="font-family:Arial,sans-serif;color:#222">',
                  '<h2 style="margin:0 0 4px">Zonas de picking %s/%s</h2>' % (ddmm[:2], ddmm[2:]),
                  '<p style="margin:0 0 12px;color:#555">Reparto: <b>%s</b></p>' % esc(estado)]
        if lotes:
            partes.append('<p>%d zonas · %d uds</p>' % (len(lotes), total_uds))
            partes.append('<table style="border-collapse:collapse;font-size:13px"><tr style="background:#eee">'
                          '<th style="padding:4px 8px;text-align:left">Zona</th><th style="padding:4px 8px">Uds</th>'
                          '<th style="padding:4px 8px">OUT</th><th style="padding:4px 8px">Tiendas</th>'
                          '<th style="padding:4px 8px;text-align:left">Lineales</th></tr>%s</table>' % ''.join(resumen))
            partes.append('<h3 style="margin:22px 0 6px">Mapa de lineales</h3><table style="border-collapse:separate;'
                          'border-spacing:2px">%s</table>' % ''.join(celdas))
            partes.append(''.join(detalle))
        else:
            partes.append('<p><b>No hay agrupaciones de zona de hoy (Z-%s-...).</b></p>' % ddmm)
            if informe:
                partes.append('<pre style="font-size:12px">%s</pre>' % esc(informe[:6000]))
        partes.append('</div>')
        return ddmm, len(lotes), total_uds, ''.join(partes)

    @api.model
    def cron_enviar(self):
        destinatarios = self.env['koroshi.zonas.config'].obtener().correo_destinatarios
        if not destinatarios:
            _logger.info('KOROSHI Zonas: correo del dia sin destinatarios en la configuracion; no se envia')
            return False
        ddmm, n_lotes, uds, html = self.html()
        correo = self.env['mail.mail'].sudo().create({
            'subject': 'KOROSHI zonas de picking %s/%s: %d zonas, %d uds' % (ddmm[:2], ddmm[2:], n_lotes, uds),
            'email_to': destinatarios,
            'body_html': html,
            'auto_delete': False,
        })
        correo.send()
        _logger.info('KOROSHI Zonas: correo del dia enviado a %s (%d zonas, %d uds)', destinatarios, n_lotes, uds)
        return True
