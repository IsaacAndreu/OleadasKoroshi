# -*- coding: utf-8 -*-
# v1.12.0 (26/11/2026): correo diario con el % de faltante (Isaac, 26/11: «cada día a las 17:00 a mi correo»).
#
# Cron cada 15 min: a partir de la hora de koroshi_faltantes.correo_hora (17:00, hora del almacén), una vez al día,
# recalcula la tabla y manda a koroshi_faltantes.correo_destinatarios un resumen: cuántos SKU, modelo-color y modelos
# hay en cada alerta y las listas de SKU y modelo-color en alarma o crítico. Solo escribe en su tabla, en sus
# parámetros (último día enviado) y en mail.mail.
import html
import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.addons.koroshi_base import comun

_logger = logging.getLogger(__name__)

P = 'koroshi_faltantes.'
DEF_DESTINATARIOS = 'isaac.andreu@nath.es'
DEF_HORA = '17:00'
MAX_SKU = 60
MAX_COLOR = 30

ESTILO_TD = 'padding:3px 6px;border-bottom:1px solid #ddd;font-size:13px'
ESTILO_TH = 'padding:4px 6px;background:#DDEBF7;text-align:left;font-size:13px'
COLOR_ALERTA = {'critico': '#9C0006', 'alarma': '#C00000', 'vigilar': '#9C5700', 'ok': '#555555'}


def _n(x, dec=0):
    """Número a la española: 1.234 / 12,34."""
    texto = ('{:,.%df}' % dec).format(x or 0)
    return texto.replace(',', '#').replace('.', ',').replace('#', '.')


class KoroshiFaltanteRelativoCorreo(models.Model):
    _inherit = 'koroshi.faltante.relativo'

    # ------------------------------------------------------------------ parámetros
    @api.model
    def _param(self, clave, defecto=''):
        return self.env['ir.config_parameter'].sudo().get_param(P + clave, defecto)

    @api.model
    def _destinatarios(self):
        texto = self._param('correo_destinatarios', DEF_DESTINATARIOS) or ''
        return ','.join(x.strip() for x in re.split(r'[,;\s]+', texto) if x.strip())

    @api.model
    def _hora_correo(self):
        texto = (self._param('correo_hora', DEF_HORA) or DEF_HORA).strip()
        try:
            hh, mm = (int(x) for x in texto.split(':'))
            if 0 <= hh < 24 and 0 <= mm < 60:
                return hh, mm
        except ValueError:
            pass
        _logger.warning('KOROSHI %% faltante: %scorreo_hora = %r no es HH:MM; uso %s', P, texto, DEF_HORA)
        return 17, 0

    # ------------------------------------------------------------------ componer
    @api.model
    def _tabla(self, filas, con_sku):
        cab = ['SKU' if con_sku else 'Modelo-color', '%', 'Alerta', 'Faltante', 'Recibido', 'Bajas', 'Altas',
               'En FALTANTE', 'Stock', 'Faltas 7 días', 'Última baja']
        h = ['<table style="border-collapse:collapse"><tr>%s</tr>' % ''.join(
            '<th style="%s">%s</th>' % (ESTILO_TH, c) for c in cab)]
        etiquetas = dict(self._fields['alerta'].selection)
        for f in filas:
            ult = comun.a_local(f.ultimo_ajuste).strftime('%d/%m') if f.ultimo_ajuste else ''
            celdas = [html.escape(f.name), _n(f.pct, 2) + ' %', etiquetas.get(f.alerta, ''), _n(f.faltante),
                      _n(f.recibido), _n(f.bajas), _n(f.altas), _n(f.en_faltante), _n(f.stock), _n(f.faltas_7d), ult]
            color = COLOR_ALERTA.get(f.alerta, '#000')
            h.append('<tr>%s</tr>' % ''.join(
                '<td style="%s;%s">%s</td>' % (ESTILO_TD, 'color:%s;font-weight:bold' % color if i < 3 else '', c)
                for i, c in enumerate(celdas)))
        h.append('</table>')
        return ''.join(h)

    @api.model
    def componer_correo(self):
        hoy = comun.hoy_local()
        _vig, alarma, critico = self._umbrales()
        todo = self.sudo().search([])
        calculado = max(todo.mapped('calculado')) if todo else False
        resumen = []
        for nivel, nombre in (('sku', 'SKU'), ('color', 'Modelo-color'), ('modelo', 'Modelos')):
            filas = todo.filtered(lambda r: r.nivel == nivel)
            cuenta = {a: len(filas.filtered(lambda r: r.alerta == a)) for a in ('critico', 'alarma', 'vigilar')}
            resumen.append('<tr><td style="%s">%s</td><td style="%s;color:%s"><b>%s</b></td>'
                           '<td style="%s;color:%s"><b>%s</b></td><td style="%s">%s</td><td style="%s">%s</td></tr>' % (
                               ESTILO_TD, nombre, ESTILO_TD, COLOR_ALERTA['critico'], cuenta['critico'], ESTILO_TD,
                               COLOR_ALERTA['alarma'], cuenta['alarma'], ESTILO_TD, cuenta['vigilar'], ESTILO_TD,
                               _n(len(filas))))
        sku = self.sudo().search([('nivel', '=', 'sku'), ('alerta', 'in', ('alarma', 'critico'))],
                                 order='faltas_7d desc, pct desc, faltante desc')
        color = self.sudo().search([('nivel', '=', 'color'), ('alerta', 'in', ('alarma', 'critico'))],
                                   order='pct desc, faltante desc')
        tot_sku = todo.filtered(lambda r: r.nivel == 'sku')
        rec = sum(tot_sku.mapped('recibido'))
        falt = sum(tot_sku.mapped('faltante'))
        asunto = 'KOROSHI · %% de faltante · %s · %d SKU en alarma (%d críticos)' % (
            hoy.strftime('%d/%m/%Y'), len(sku), len(sku.filtered(lambda r: r.alerta == 'critico')))
        cuerpo = [
            '<div style="font-family:Arial,sans-serif">',
            '<h3 style="margin:0 0 6px">%% de faltante · %s</h3>' % hoy.strftime('%d/%m/%Y'),
            '<p style="margin:0 0 10px;font-size:13px">Faltante = bajas − altas por ajuste + uds en FALTANTE. '
            '%% = faltante ÷ recibido de proveedor. Alarma desde el %s %%, crítico desde el %s %%. En modelo-color no '
            'se compensan tallas. Calculado: %s.</p>' % (
                _n(alarma, 0), _n(critico, 0),
                comun.a_local(calculado).strftime('%d/%m %H:%M') if calculado else '—'),
            '<p style="margin:0 0 10px;font-size:13px">Global (prendas): faltante %s uds sobre %s recibidas = '
            '<b>%s %%</b>.</p>' % (_n(falt), _n(rec), _n(falt * 100.0 / rec if rec else 0, 2)),
            '<table style="border-collapse:collapse;margin-bottom:14px"><tr>%s</tr>%s</table>' % (
                ''.join('<th style="%s">%s</th>' % (ESTILO_TH, c)
                        for c in ('Nivel', 'Críticos', 'Alarma', 'Vigilar', 'Total')), ''.join(resumen)),
            '<h4 style="margin:10px 0 4px">SKU en alarma o crítico (primero los que más faltas dan en tiendas)%s</h4>'
            % (' · los %d primeros de %d' % (MAX_SKU, len(sku)) if len(sku) > MAX_SKU else ''),
            self._tabla(sku[:MAX_SKU], True) if sku else '<p>Ninguno.</p>',
            '<h4 style="margin:14px 0 4px">Modelo-color en alarma o crítico%s</h4>'
            % (' · los %d primeros de %d' % (MAX_COLOR, len(color)) if len(color) > MAX_COLOR else ''),
            self._tabla(color[:MAX_COLOR], False) if color else '<p>Ninguno.</p>',
            '<p style="margin-top:14px;font-size:12px;color:#666">Lista completa en Odoo: Inventario › KOROSHI '
            'Faltantes › %% de faltante por SKU / modelo-color / modelo.</p></div>',
        ]
        return asunto, ''.join(cuerpo)

    # ------------------------------------------------------------------ enviar
    @api.model
    def enviar_correo(self, destinatarios=None):
        destinatarios = destinatarios or self._destinatarios()
        if not destinatarios:
            raise UserError(_('Faltan los correos (parámetro %scorreo_destinatarios).') % P)
        asunto, cuerpo = self.componer_correo()
        servidor = self.env['ir.mail_server'].sudo().search([('name', '=', self._param('correo_servidor', 'NATH'))],
                                                            limit=1)
        empresa = self.env['res.company'].sudo().browse(comun.COMPANY_ID)
        remitente = (servidor.smtp_user if servidor and '@' in (servidor.smtp_user or '') else '') \
            or empresa.email or self.env.user.email or ''
        mail = self.env['mail.mail'].sudo().create({
            'subject': asunto, 'email_from': remitente, 'email_to': destinatarios, 'body_html': cuerpo,
            'mail_server_id': servidor.id or False, 'auto_delete': False,
        })
        mail.send()
        if mail.state == 'exception':
            _logger.error('KOROSHI %% faltante: el correo %s no ha salido (%s); vuelve a la cola de correo.', mail.id,
                          (mail.failure_reason or '')[:300])
            mail.mark_outgoing()
        return mail

    @api.model
    def action_enviar_correo(self):
        """Menú «Enviar ahora el correo de % de faltante»: recalcula y lo manda (para probar)."""
        self.recalcular()
        mail = self.enviar_correo()
        if self.env.user.has_group('base.group_system'):
            return {'type': 'ir.actions.act_window', 'name': _('Correo enviado'), 'res_model': 'mail.mail',
                    'res_id': mail.id, 'view_mode': 'form', 'target': 'new'}
        return {'type': 'ir.actions.act_window_close'}

    @api.model
    def cron_correo(self):
        """Cada 15 min: una vez al día, a partir de la hora del parámetro, recalcula y manda el correo."""
        ahora = comun.ahora_local()
        hoy = ahora.date().isoformat()
        if (ahora.hour, ahora.minute) < self._hora_correo() or self._param('correo_ultimo') == hoy:
            return True
        if not self._destinatarios():
            return True
        icp = self.env['ir.config_parameter'].sudo()
        icp.set_param(P + 'correo_ultimo', hoy)      # antes de mandar: si falla, no se repite cada 15 min
        try:
            with self.env.cr.savepoint():
                self.recalcular()
        except Exception:
            # si no se puede recalcular (otro recálculo en marcha), se manda con lo de la última hora
            _logger.exception('KOROSHI %% faltante: no se ha podido recalcular antes del correo del %s', hoy)
        try:
            with self.env.cr.savepoint():
                self.enviar_correo()
        except Exception:
            _logger.exception('KOROSHI %% faltante: no se ha podido mandar el correo del %s', hoy)
        return True
