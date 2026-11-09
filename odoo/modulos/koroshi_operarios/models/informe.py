# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Operarios - informe diario por email (v1.2).
#
# Cron cada 15 min (data/cron.xml): a partir de la hora del parametro koroshi_operarios.informe_hora
# (17:00, hora de Madrid, cuando se plega) manda una vez al dia el informe del dia a
# koroshi_operarios.informe_destinatarios (separados por coma). Si ese dia no hay tareas ni OUT validadas,
# no manda nada. El menu "Enviar informe de hoy ahora" lo manda en el momento (para probar) sin marcar
# el dia como enviado.
#
# Parametros (Ajustes > Tecnico > Parametros del sistema):
#   koroshi_operarios.informe_destinatarios   emails separados por coma
#   koroshi_operarios.informe_hora            HH:MM (por defecto 17:00)
#   koroshi_operarios.informe_servidor        nombre del servidor de correo saliente (por defecto NATH)
#   koroshi_operarios.informe_ultimo          ultimo dia enviado (lo escribe el cron)
#
# Solo lee tareas y albaranes; escribe el parametro informe_ultimo y crea el mail.mail.
# =============================================================================
import datetime
import html
import re

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .tarea import ZONA_HORARIA

COMPANY_ID = 8          # EFFECTIVE LOGISTICS, S.L.
P = 'koroshi_operarios.informe_'
RE_OP = re.compile(r'^([A-Za-z]+)0*(\d+)$')


def codigo_corto(barcode):
    m = RE_OP.match((barcode or '').strip())
    return m and '%s%s' % (m.group(1).upper(), m.group(2)) or (barcode or '?')


def hm(minutos):
    m = int(round(minutos or 0))
    return '%d:%02d' % (m // 60, m % 60)


class KoroshiOperarioInforme(models.AbstractModel):
    _name = 'koroshi.operario.informe'
    _description = 'KOROSHI Operarios: informe diario'

    # ------------------------------------------------------------------ datos
    @api.model
    def _limites(self, dia):
        tz = pytz.timezone(ZONA_HORARIA)
        ini = tz.localize(datetime.datetime(dia.year, dia.month, dia.day)).astimezone(pytz.utc).replace(tzinfo=None)
        return ini, ini + datetime.timedelta(days=1)

    @api.model
    def _hora(self, dt):
        if not dt:
            return ''
        return pytz.utc.localize(dt).astimezone(pytz.timezone(ZONA_HORARIA)).strftime('%H:%M')

    @api.model
    def _datos(self, dia):
        Tarea = self.env['koroshi.operario.tarea'].sudo()
        ahora = fields.Datetime.now()
        ini, fin = self._limites(dia)
        tareas = Tarea.search([('dia', '=', dia)], order='inicio asc')
        ops = {}
        for t in tareas:
            e = t.employee_id
            o = ops.setdefault(e.id, {
                'op': codigo_corto(e.barcode), 'nombre': e.name or '', 'tareas': 0, 'acabadas': 0,
                'dejadas': 0, 'sin_cerrar': 0, 'curso': 0, 'uds': 0.0, 'min': 0.0, 'ini': None, 'fin': None,
            })
            o['tareas'] += 1
            if t.estado == 'curso':
                # abierta a la hora del informe: hasta ahora
                o['curso'] += 1
                o['uds'] += max(Tarea._uds_leidas(t._pickings()) - (t.uds_inicio or 0.0), 0.0)
                o['min'] += max((ahora - t.inicio).total_seconds() / 60.0, 0.0)
                t_fin = ahora
            else:
                o['acabadas' if t.estado == 'acabada' else ('dejadas' if t.estado == 'dejada' else 'sin_cerrar')] += 1
                o['uds'] += t.uds or 0.0
                o['min'] += t.minutos or 0.0
                t_fin = t.fin
            if t.inicio and (not o['ini'] or t.inicio < o['ini']):
                o['ini'] = t.inicio
            if t_fin and (not o['fin'] or t_fin > o['fin']):
                o['fin'] = t_fin
        filas = sorted(ops.values(), key=lambda o: (int(re.sub(r'\D', '', o['op']) or 0), o['op']))
        for o in filas:
            o['uh'] = o['min'] >= 1 and int(round(o['uds'] * 60.0 / o['min'])) or 0

        # OUT validadas ese dia (EFFEC) y las que no estan en ninguna tarea
        hechas = self.env['stock.picking'].sudo().search([
            ('company_id', '=', COMPANY_ID),
            ('picking_type_code', '=', 'outgoing'),
            ('state', '=', 'done'),
            ('date_done', '>=', ini), ('date_done', '<', fin),
        ])
        cerca = Tarea.search([('inicio', '>=', ini - datetime.timedelta(days=1)), ('inicio', '<', fin)])
        cubiertas = cerca.mapped('picking_id')
        for t in cerca.filtered(lambda x: x.tipo == 'agrupacion'):
            cubiertas |= t.batch_id.picking_ids
        sin = hechas - cubiertas
        uds_hechas = sum(m.quantity_done for m in hechas.mapped('move_lines'))
        uds_sin = sum(m.quantity_done for m in sin.mapped('move_lines'))
        return {
            'dia': dia, 'filas': filas, 'tareas': tareas,
            'hechas': hechas, 'sin': sin, 'uds_hechas': uds_hechas, 'uds_sin': uds_sin,
        }

    # ------------------------------------------------------------------ html
    @api.model
    def _html(self, d):
        e = lambda s: html.escape('' if s is None else str(s))
        n = lambda x: '{:,.0f}'.format(x or 0).replace(',', '.')
        th = 'style="text-align:left;padding:4px 8px;border-bottom:2px solid #999;background:#f2f2f2"'
        thr = 'style="text-align:right;padding:4px 8px;border-bottom:2px solid #999;background:#f2f2f2"'
        td = 'style="padding:4px 8px;border-bottom:1px solid #ddd"'
        tdr = 'style="padding:4px 8px;border-bottom:1px solid #ddd;text-align:right"'
        filas = d['filas']
        uds = sum(o['uds'] for o in filas)
        mins = sum(o['min'] for o in filas)
        h = ['<div style="font-family:Arial,sans-serif;font-size:13px;color:#222">']
        h.append('<h2 style="margin:0 0 4px">KOROSHI Operarios · %s</h2>' % d['dia'].strftime('%d/%m/%Y'))
        h.append('<p style="margin:0 0 12px;color:#666">Informe de las %s. Tareas leídas con tarjeta en la PDA '
                 '(tarjeta + OUT). Lo que sigue abierto cuenta hasta ahora.</p>' % self._hora(fields.Datetime.now()))
        cob = d['hechas'] and 100.0 * (len(d['hechas']) - len(d['sin'])) / len(d['hechas']) or 0
        h.append('<table style="border-collapse:collapse;margin-bottom:16px"><tr>')
        for valor, texto in [
            (len(filas), 'operarios'),
            (n(uds), 'uds leídas'),
            (hm(mins), 'horas (h:mm)'),
            (mins >= 1 and n(uds * 60.0 / mins) or '–', 'u/h de media'),
            ('%d / %d' % (len(d['hechas']) - len(d['sin']), len(d['hechas'])), 'OUT validadas con operario'),
        ]:
            h.append('<td style="padding:8px 14px;border:1px solid #ddd;text-align:center">'
                     '<div style="font-size:20px;font-weight:bold">%s</div><div style="color:#666">%s</div></td>'
                     % (valor, texto))
        h.append('</tr></table>')

        if filas:
            h.append('<table style="border-collapse:collapse;min-width:640px"><thead><tr>')
            h.append(''.join('<th %s>%s</th>' % (th, c) for c in ['Código', 'Nombre', 'Empieza', 'Acaba']))
            h.append(''.join('<th %s>%s</th>' % (thr, c) for c in
                             ['Pedidos', 'Acabados', 'Dejados', 'Sin cerrar', 'Abiertos', 'Uds', 'Tiempo', 'u/h']))
            h.append('</tr></thead><tbody>')
            for o in filas:
                h.append('<tr><td %s><b>%s</b></td><td %s>%s</td><td %s>%s</td><td %s>%s</td>' % (
                    td, e(o['op']), td, e(o['nombre']), td, self._hora(o['ini']), td, self._hora(o['fin'])))
                h.append(''.join('<td %s>%s</td>' % (tdr, v) for v in [
                    o['tareas'], o['acabadas'], o['dejadas'] or '', o['sin_cerrar'] or '', o['curso'] or '',
                    n(o['uds']), hm(o['min']), '<b>%s</b>' % (o['uh'] or '–')]))
                h.append('</tr>')
            h.append('<tr><td %s colspan="4"><b>Total</b></td>' % td)
            h.append(''.join('<td %s><b>%s</b></td>' % (tdr, v) for v in [
                sum(o['tareas'] for o in filas), sum(o['acabadas'] for o in filas),
                sum(o['dejadas'] for o in filas) or '', sum(o['sin_cerrar'] for o in filas) or '',
                sum(o['curso'] for o in filas) or '', n(uds), hm(mins), mins >= 1 and n(uds * 60.0 / mins) or '–']))
            h.append('</tr></tbody></table>')
        else:
            h.append('<p><b>Hoy nadie ha leído su tarjeta.</b></p>')

        if d['sin']:
            nombres = ', '.join(e(p.name.replace('EFFEC/OUT/', '')) for p in d['sin'][:60])
            h.append('<p style="margin-top:16px"><b>OUT validadas hoy sin operario: %d</b> (%s uds, %.0f %% de las OUT '
                     'validadas tienen operario). %s%s</p>' % (
                         len(d['sin']), n(d['uds_sin']), cob, nombres, len(d['sin']) > 60 and '…' or ''))
        h.append('<p style="color:#888;font-size:11px;margin-top:16px">Uds = uds leídas entre que el operario lee la OUT '
                 'y la valida, la deja («Dejar aquí») o empieza otra. Tiempo = de la lectura de la OUT al cierre. '
                 'Detalle en Inventario › KOROSHI Operarios › Productividad.</p></div>')
        return ''.join(h)

    # ------------------------------------------------------------------ envio
    @api.model
    def _param(self, clave, defecto=''):
        return self.env['ir.config_parameter'].sudo().get_param(P + clave, defecto) or defecto

    @api.model
    def enviar(self, dia=None):
        """Manda el informe de ese dia (hoy por defecto). Devuelve el mail.mail."""
        if not dia:
            dia = datetime.datetime.now(pytz.timezone(ZONA_HORARIA)).date()
        destinatarios = ','.join(x.strip() for x in self._param('destinatarios').split(',') if x.strip())
        if not destinatarios:
            raise UserError(_('Falta el parametro %sdestinatarios') % P)
        self.env['koroshi.operario.tarea'].cron_cerrar()        # cierra lo ya validado antes de contar
        d = self._datos(dia)
        servidor = self.env['ir.mail_server'].sudo().search([('name', '=', self._param('servidor', 'NATH'))], limit=1)
        empresa = self.env['res.company'].sudo().browse(COMPANY_ID)
        remitente = (servidor.smtp_user if servidor and '@' in (servidor.smtp_user or '') else '') \
            or empresa.email or self.env.user.email or ''
        uds = sum(o['uds'] for o in d['filas'])
        mail = self.env['mail.mail'].sudo().create({
            'subject': 'KOROSHI Operarios %s: %d operarios, %s uds' % (
                dia.strftime('%d/%m'), len(d['filas']), '{:,.0f}'.format(uds).replace(',', '.')),
            'email_from': remitente,
            'email_to': destinatarios,
            'body_html': self._html(d),
            'mail_server_id': servidor.id or False,
            'auto_delete': False,
        })
        mail.send()
        return mail

    @api.model
    def action_enviar_hoy(self):
        mail = self.enviar()
        # Odoo 13 no tiene display_notification: se ensena el correo (estado enviado / error) si se puede leer
        if self.env.user.has_group('base.group_system'):
            return {'type': 'ir.actions.act_window', 'name': _('Informe enviado'), 'res_model': 'mail.mail',
                    'res_id': mail.id, 'view_mode': 'form', 'target': 'new'}
        return {'type': 'ir.actions.act_window_close'}

    @api.model
    def cron_informe(self):
        """Cada 15 min: a partir de la hora del parametro, una vez al dia."""
        tz = pytz.timezone(ZONA_HORARIA)
        ahora = datetime.datetime.now(tz)
        hora = self._param('hora', '17:00')
        try:
            hh, mm = [int(x) for x in hora.split(':')]
        except ValueError:
            hh, mm = 17, 0
        hoy = ahora.date()
        if (ahora.hour, ahora.minute) < (hh, mm) or self._param('ultimo') == hoy.isoformat():
            return True
        ini, fin = self._limites(hoy)
        hay = self.env['koroshi.operario.tarea'].sudo().search_count([('dia', '=', hoy)]) or \
            self.env['stock.picking'].sudo().search_count([
                ('company_id', '=', COMPANY_ID), ('picking_type_code', '=', 'outgoing'),
                ('state', '=', 'done'), ('date_done', '>=', ini), ('date_done', '<', fin)])
        # se marca antes de mandar: si el correo falla no se reintenta cada 15 min (queda en Correos tecnicos)
        self.env['ir.config_parameter'].sudo().set_param(P + 'ultimo', hoy.isoformat())
        if hay:
            self.enviar(hoy)
        return True
