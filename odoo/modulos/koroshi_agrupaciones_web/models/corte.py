# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Agrupaciones web por corte horario (Isaac, 13/11 y 18/11/2026).
#
# En cada corte (parametro koroshi_agrupaciones_web.cortes, hora del almacen; por defecto 06:00 y 11:00):
#   1. CANCELA las OUT web creadas antes del corte que no estan al 100 % reservadas (sin agrupacion y sin nada
#      leido) y manda a Betty la lista, para que las cancele en el TPV de KOROSHI y rehagan el pedido con el stock
#      que si hay. Con koroshi_agrupaciones_web.cancelar = 0 solo apunta cuales cancelaria.
#   2. AGRUPA las OUT web 100 % reservadas sin agrupacion, en orden de llegada, en agrupaciones WEB_ddmmaa_NN de
#      hasta koroshi_agrupaciones_web.tope_uds uds (100). Una OUT nunca se parte. Quedan En curso, como las de la
#      oficina, y se preparan con PedidosMultiples (que coge los lotes WEB_).
#
# OUT web = salida de la compania 8, origen 'W-', tipo de pedido que no es MARKETPLACE ni TIENDAS y direccion que no
# es Zalando ni About You. Zalando y las tiendas no entran nunca.
# 100 % reservada = Preparada y ningun movimiento En espera / Esperando otra operacion / Parcialmente disponible.
# Todas las OUT web tienen move_type 'direct': con eso Odoo pone Preparada en cuanto hay UNA linea reservada.
#
# Sin campos en tablas compartidas: escribe en sus dos tablas, en stock.picking.batch (crea las WEB_), en el
# estado de las OUT que cancela (action_cancel, nunca se borran), en sus parametros y en mail.mail.
# =============================================================================
import datetime
import logging

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import html_escape

from odoo.addons.koroshi_base import comun
from odoo.addons.koroshi_agrupaciones_web import reparto

_logger = logging.getLogger(__name__)

P = 'koroshi_agrupaciones_web.'
ESTADOS_SIN_RESERVA = ('confirmed', 'waiting', 'partially_available')
ESTADOS_ABIERTOS = ('confirmed', 'waiting', 'assigned')
TIPOS_FUERA = ('MARKETPLACE', 'TIENDA')
DESTINOS_FUERA = ('ZALANDO', 'ABOUT YOU')
CANDADO = 8130001        # pg_try_advisory_xact_lock: dos cortes a la vez (cron y boton) no se pisan
MAX_INTENTOS = 3         # v1.1.0 (R10): veces que el cron vuelve a probar un corte que falla antes de dejarlo


class KoroshiWebCorte(models.Model):
    _name = 'koroshi.web.corte'
    _description = 'KOROSHI: corte de pedidos web (agrupar y cancelar)'
    _order = 'id desc'
    _rec_name = 'nombre'

    nombre = fields.Char('Corte', required=True, readonly=True)
    fecha = fields.Datetime('Hecho', default=fields.Datetime.now, readonly=True)
    hora_corte = fields.Datetime('Pedidos creados antes de', readonly=True)
    origen = fields.Selection([('cron', 'Automático'), ('boton', 'A mano')], 'Lanzado', readonly=True)
    simulacion = fields.Boolean('Simulación', readonly=True,
                                help='No se ha creado ni cancelado nada: es lo que haría.')
    cancelacion_activa = fields.Boolean('Cancelación encendida', readonly=True)
    batch_ids = fields.Many2many('stock.picking.batch', string='Agrupaciones creadas', readonly=True)
    linea_ids = fields.One2many('koroshi.web.corte.linea', 'corte_id', 'OUT', readonly=True)
    n_agrupadas = fields.Integer('OUT agrupadas', readonly=True)
    uds_agrupadas = fields.Integer('Uds agrupadas', readonly=True)
    n_canceladas = fields.Integer('OUT canceladas', readonly=True)
    resumen = fields.Text('Resumen', readonly=True)
    mail_id = fields.Many2one('mail.mail', 'Correo a Betty', readonly=True)

    # ------------------------------------------------------------------ parametros
    @api.model
    def _param(self, clave, defecto=''):
        return self.env['ir.config_parameter'].sudo().get_param(P + clave, defecto)

    @api.model
    def _set(self, clave, valor):
        self.env['ir.config_parameter'].sudo().set_param(P + clave, valor)

    @api.model
    def _si(self, clave, defecto='0'):
        return (self._param(clave, defecto) or '').strip().lower() in ('1', 'true', 'si', 'sí')

    @api.model
    def _entero(self, clave, defecto):
        try:
            return int((self._param(clave, str(defecto)) or '').strip())
        except ValueError:
            return defecto

    # ------------------------------------------------------------------ que es una OUT web
    @api.model
    def _es_web(self, p):
        if not (p.origin or '').startswith('W-') or not p.sale_id:
            return False
        venta = p.sale_id
        if 's_order_type_id' in venta._fields:
            tipo = (venta.s_order_type_id.name or '').upper()
            if any(t in tipo for t in TIPOS_FUERA):
                return False
        destino = ' '.join([venta.partner_shipping_id.display_name or '', p.partner_id.display_name or '']).upper()
        return not any(d in destino for d in DESTINOS_FUERA)

    @api.model
    def _reserva_completa(self, p):
        moves = p.move_lines.filtered(lambda m: m.state != 'cancel')
        return p.state == 'assigned' and bool(moves) and not moves.filtered(lambda m: m.state in ESTADOS_SIN_RESERVA)

    @api.model
    def _uds(self, p):
        return int(round(sum(p.move_lines.filtered(lambda m: m.state != 'cancel').mapped('product_uom_qty'))))

    @api.model
    def _candidatas(self, hasta_utc):
        """OUT web abiertas, sin agrupacion, creadas antes de hasta_utc y desde hace dias_atras dias."""
        dias = self._entero('dias_atras', 3)
        desde = comun.inicio_dia_utc(comun.hoy_local()) - datetime.timedelta(days=max(dias, 0))
        outs = self.env['stock.picking'].sudo().search([
            ('company_id', '=', comun.COMPANY_ID),
            ('picking_type_code', '=', 'outgoing'),
            ('origin', '=like', 'W-%'),
            ('state', 'in', list(ESTADOS_ABIERTOS)),
            ('batch_id', '=', False),
            ('create_date', '<', fields.Datetime.to_string(hasta_utc)),
            ('create_date', '>=', fields.Datetime.to_string(desde)),
        ], order='create_date asc, id asc')
        return outs.filtered(self._es_web)

    @api.model
    def _detalle(self, p):
        """Lineas 'REF nombre: reservadas/pedidas' de lo que falta, y las que si hay."""
        falta, hay = [], []
        for m in p.move_lines.filtered(lambda m: m.state != 'cancel'):
            ref = m.product_id.default_code or m.product_id.barcode or ''
            nombre = m.product_id.name or ''
            res, ped = int(round(m.reserved_availability)), int(round(m.product_uom_qty))
            texto = '%s %s: %d de %d' % (ref, nombre, res, ped)
            (hay if res >= ped else falta).append(texto)
        return falta, hay

    # ------------------------------------------------------------------ el corte
    @api.model
    def hacer_corte(self, hora_local, simulacion=False, origen='boton'):
        """Cancela las web incompletas y agrupa las completas creadas antes de hora_local (datetime con zona)."""
        self.env.cr.execute('SELECT pg_try_advisory_xact_lock(%s)', (CANDADO,))
        if not self.env.cr.fetchone()[0]:
            raise UserError(_('Ya se está haciendo un corte de pedidos web. Espera un minuto y vuelve a mirarlo.'))
        hasta_utc = hora_local.astimezone(pytz.utc).replace(tzinfo=None)
        cancelar = self._si('cancelar') and not simulacion
        tope = self._entero('tope_uds', 100)
        outs = self._candidatas(hasta_utc)
        Linea = self.env['koroshi.web.corte.linea'].sudo()
        corte = self.sudo().create({
            'nombre': '%s%s' % (hora_local.strftime('%d/%m/%Y %H:%M'), simulacion and ' (simulación)' or ''),
            'hora_corte': hasta_utc, 'origen': origen, 'simulacion': simulacion,
            'cancelacion_activa': self._si('cancelar'),
        })
        texto = []

        # 1. Cancelar las incompletas (sin nada leido)
        canceladas = []
        for p in outs.filtered(lambda x: not self._reserva_completa(x)):
            falta, hay = self._detalle(p)
            leido = any(p.move_line_ids.mapped('qty_done'))
            accion = 'leida' if leido else (cancelar and 'cancelada' or 'cancelaria')
            Linea.create({
                'corte_id': corte.id, 'picking_id': p.id, 'pedido': p.origin, 'uds': self._uds(p),
                'accion': accion, 'falta': '\n'.join(falta), 'hay': '\n'.join(hay),
                'creada': p.create_date,
            })
            if leido:
                continue
            canceladas.append((p, falta, hay))
        if cancelar:
            # v1.1.0 (R10): cada OUT en su savepoint. Si una no se puede cancelar, se queda como estaba, su línea lo
            # dice y el corte sigue (antes tumbaba el corte entero: ni canceladas ni agrupaciones)
            hechas, errores = [], []
            for p, falta, hay in canceladas:
                self.env['base'].flush()
                try:
                    with self.env.cr.savepoint():
                        p.action_cancel()
                        p.message_post(body=_('Cancelada por el corte de pedidos web de las %s: no estaba reservada '
                                              'del todo. Falta: %s') % (hora_local.strftime('%H:%M'),
                                                                         html_escape('; '.join(falta))))
                        self.env['base'].flush()
                    hechas.append((p, falta, hay))
                except Exception as e:
                    self.env.cache.invalidate()
                    _logger.exception('KOROSHI Agrupaciones web: no se ha podido cancelar %s', p.name)
                    errores.append('%s (%s): %s' % (p.name, p.origin or '', e))
                    Linea.search([('corte_id', '=', corte.id), ('picking_id', '=', p.id)]).write(
                        {'accion': 'error', 'falta': ('%s\nError al cancelar: %s' % ('\n'.join(falta), e)).strip()})
            canceladas = hechas
            if errores:
                texto.append('NO se han podido cancelar %d OUT: %s' % (len(errores), '; '.join(errores)))
                self._avisar('%d OUT web no se han podido cancelar en el corte de las %s' % (
                    len(errores), hora_local.strftime('%H:%M')), '\n'.join(errores))
        texto.append('%s %d OUT web sin reserva completa%s.' % (
            cancelar and 'Canceladas' or 'Se cancelarían', len(canceladas),
            not self._si('cancelar') and ' (cancelación apagada: koroshi_agrupaciones_web.cancelar = 0)' or ''))

        # 2. Agrupar las completas en orden de llegada
        completas = outs.filtered(self._reserva_completa)
        grupos = reparto.repartir([(p.id, self._uds(p)) for p in completas], tope)
        Batch = self.env['stock.picking.batch'].sudo()
        prefijo = 'WEB_%s_' % hora_local.strftime('%d%m%y')
        numero = reparto.siguiente_numero(Batch.search([('name', '=like', prefijo + '%')]).mapped('name'), prefijo)
        Picking = self.env['stock.picking'].sudo()
        uds_total = 0
        for ids in grupos:
            nombre = '%s%02d' % (prefijo, numero)
            numero += 1
            uds = sum(self._uds(p) for p in Picking.browse(ids))
            uds_total += uds
            for p in Picking.browse(ids):
                Linea.create({'corte_id': corte.id, 'picking_id': p.id, 'pedido': p.origin, 'uds': self._uds(p),
                              'accion': simulacion and 'agruparia' or 'agrupada', 'agrupacion': nombre,
                              'creada': p.create_date})
            texto.append('%s: %d OUT, %d uds' % (nombre, len(ids), uds))
            if simulacion:
                continue
            vals = {'name': nombre, 'picking_ids': [(6, 0, ids)]}
            if 'company_id' in Batch._fields:
                vals['company_id'] = comun.COMPANY_ID
            b = Batch.create(vals)
            # En curso escribiendo el estado, como KOROSHI_crear_oleadas: sin volver a reservar ni tocar las OUT
            b.write({'state': 'in_progress'})
            corte.batch_ids = [(4, b.id)]
        if not grupos:
            texto.append('No hay OUT web reservadas del todo para agrupar.')

        corte.write({
            'n_agrupadas': len(completas), 'uds_agrupadas': uds_total,
            'n_canceladas': len(canceladas) if cancelar else 0,
            'resumen': '\n'.join(texto),
        })
        if cancelar and canceladas:
            corte.mail_id = self._correo_canceladas(hora_local, canceladas)
        _logger.info('KOROSHI Agrupaciones web, corte %s: %s', corte.nombre, ' | '.join(texto))
        return corte

    # ------------------------------------------------------------------ correo a Betty
    @api.model
    def _correo_canceladas(self, hora_local, canceladas):
        destinatarios = ','.join(x.strip() for x in (self._param('correo_canceladas') or '').replace(';', ',').split(',')
                                 if x.strip())
        if not destinatarios:
            _logger.warning('KOROSHI Agrupaciones web: %d canceladas y sin correo_canceladas: no se avisa',
                            len(canceladas))
            return False
        filas = []
        for p, falta, hay in canceladas:
            filas.append('<tr><td style="padding:4px 8px;border:1px solid #ccc">%s</td>'
                         '<td style="padding:4px 8px;border:1px solid #ccc">%s</td>'
                         '<td style="padding:4px 8px;border:1px solid #ccc">%s</td>'
                         '<td style="padding:4px 8px;border:1px solid #ccc">%s</td></tr>' % (
                             html_escape(p.origin or ''),
                             html_escape(comun.a_local(p.sale_id.date_order or p.create_date).strftime('%d/%m %H:%M')),
                             '<br/>'.join(html_escape(x) for x in falta) or '-',
                             '<br/>'.join(html_escape(x) for x in hay) or '-'))
        cuerpo = (
            '<p>Hola Betty:</p>'
            '<p>En el corte de las %s se han cancelado en el almacén <b>%d pedidos web</b> que no tenían todo el '
            'stock. Hay que cancelarlos en el TPV de KOROSHI y rehacerlos con lo que sí hay.</p>'
            '<table style="border-collapse:collapse;font-size:13px">'
            '<tr><th style="padding:4px 8px;border:1px solid #ccc;text-align:left">Pedido</th>'
            '<th style="padding:4px 8px;border:1px solid #ccc;text-align:left">Fecha</th>'
            '<th style="padding:4px 8px;border:1px solid #ccc;text-align:left">Falta (reservado de pedido)</th>'
            '<th style="padding:4px 8px;border:1px solid #ccc;text-align:left">Sí hay</th></tr>%s</table>'
            '<p style="color:#888;font-size:12px">Correo automático de Odoo (koroshi_agrupaciones_web).</p>'
        ) % (hora_local.strftime('%H:%M'), len(canceladas), ''.join(filas))
        asunto = 'KOROSHI: %d pedidos web cancelados por falta de stock (%s)' % (
            len(canceladas), hora_local.strftime('%d/%m/%Y %H:%M'))
        servidor = self.env['ir.mail_server'].sudo().search([('name', '=', self._param('servidor', 'NATH'))], limit=1)
        empresa = self.env['res.company'].sudo().browse(comun.COMPANY_ID)
        remitente = (servidor.smtp_user if servidor and '@' in (servidor.smtp_user or '') else '') \
            or empresa.email or self.env.user.email or ''
        mail = self.env['mail.mail'].sudo().create({
            'subject': asunto, 'email_from': remitente, 'email_to': destinatarios, 'body_html': cuerpo,
            'mail_server_id': servidor.id or False, 'auto_delete': False,
        })
        try:
            with self.env.cr.savepoint():
                mail.send()
        except Exception:
            _logger.exception('KOROSHI Agrupaciones web: no se ha podido mandar el correo de canceladas')
        return mail.id

    # ------------------------------------------------------------------ cron y botones
    @api.model
    def cron_cortes(self):
        """Cada 15 min: hace el corte de hoy que toque. Con activo = 0 no hace nada."""
        if not self._si('activo'):
            return True
        ahora = comun.ahora_local()
        pendiente = reparto.corte_pendiente(ahora, reparto.cortes(self._param('cortes', '06:00,11:00')),
                                            self._param('ultimo_corte'), self._entero('margen_minutos', 120))
        if not pendiente:
            return True
        clave, hhmm, tarde = pendiente
        if tarde:
            self._set('ultimo_corte', clave)
            _logger.warning('KOROSHI Agrupaciones web: el corte %s llega tarde (%s): no se hace', clave,
                            ahora.strftime('%H:%M'))
            self._avisar('el corte %s NO se ha hecho (llega tarde)' % clave,
                         'El corte de pedidos web %s no se ha hecho: el cron ha llegado a las %s, más de %s min tarde. '
                         'Si hace falta, «Hacer el corte ahora» a mano.'
                         % (clave, ahora.strftime('%H:%M'), self._entero('margen_minutos', 120)))
            return True
        hora = comun.zona().localize(datetime.datetime.combine(ahora.date(), datetime.time(hhmm[0], hhmm[1])))
        # v1.1.0 (R10): ultimo_corte se apunta DESPUÉS de hacerlo. Si falla, se vuelve a probar en el siguiente cron
        # (15 min), hasta MAX_INTENTOS veces; al primer fallo y al dejarlo, correo a koroshi_agrupaciones_web.avisar
        self.env['base'].flush()
        try:
            with self.env.cr.savepoint():
                self.hacer_corte(hora, simulacion=False, origen='cron')
                self.env['base'].flush()
        except Exception as e:
            self.env.cache.invalidate()
            _logger.exception('KOROSHI Agrupaciones web: ha fallado el corte %s', clave)
            previo = (self._param('fallos') or '').split('|')
            n = int(previo[1]) + 1 if len(previo) == 2 and previo[0] == clave and previo[1].isdigit() else 1
            if n >= MAX_INTENTOS:
                self._set('ultimo_corte', clave)
                self._set('fallos', '')
                self._avisar('el corte %s NO se ha hecho (%d intentos)' % (clave, n),
                             'El corte de pedidos web %s ha fallado %d veces y se deja. Último error: %s\n'
                             'Si hace falta, «Hacer el corte ahora» a mano.' % (clave, n, e))
            else:
                self._set('fallos', '%s|%d' % (clave, n))
                if n == 1:
                    self._avisar('ha fallado el corte %s (se vuelve a probar)' % clave,
                                 'El corte de pedidos web %s ha fallado: %s\nEl cron lo vuelve a probar cada 15 min '
                                 '(hasta %d veces).' % (clave, e, MAX_INTENTOS))
            return True
        self._set('ultimo_corte', clave)
        self._set('fallos', '')
        return True

    @api.model
    def _avisar(self, asunto, texto):
        """v1.1.0 (R10): correo a koroshi_agrupaciones_web.avisar (separados por comas). Nunca rompe el corte: sin
        destinatarios o si el correo falla, queda en el log."""
        destinatarios = ','.join(x.strip() for x in (self._param('avisar') or '').replace(';', ',').split(',')
                                 if x.strip())
        _logger.warning('KOROSHI Agrupaciones web AVISO: %s', asunto)
        if not destinatarios:
            return False
        try:
            servidor = self.env['ir.mail_server'].sudo().search([('name', '=', self._param('servidor', 'NATH'))],
                                                                limit=1)
            with self.env.cr.savepoint():
                mail = self.env['mail.mail'].sudo().create({
                    'subject': 'KOROSHI Agrupaciones web: %s' % asunto, 'email_to': destinatarios,
                    'body_html': '<pre style="font-size:12px">%s</pre>' % html_escape(texto or ''),
                    'mail_server_id': servidor.id or False, 'auto_delete': False,
                })
                mail.send()
            return True
        except Exception:
            _logger.exception('KOROSHI Agrupaciones web: no se ha podido mandar el aviso «%s»', asunto)
            return False

    @api.model
    def _abrir(self, corte):
        return {'type': 'ir.actions.act_window', 'name': _('Corte de pedidos web'), 'res_model': self._name,
                'res_id': corte.id, 'view_mode': 'form', 'target': 'current'}

    @api.model
    def action_ver_outs(self, completas=True):
        """Lista de OUT web sin agrupar, 100 % reservadas o no (un filtro de busqueda no lo puede decir)."""
        hasta = datetime.datetime.utcnow() + datetime.timedelta(minutes=1)
        outs = self._candidatas(hasta).filtered(lambda p: bool(self._reserva_completa(p)) == bool(completas))
        return {
            'type': 'ir.actions.act_window', 'res_model': 'stock.picking', 'view_mode': 'tree,form',
            'name': completas and _('OUT web 100 %% reservadas (%d)') % len(outs)
            or _('OUT web con reserva incompleta (%d)') % len(outs),
            'domain': [('id', 'in', outs.ids)], 'context': {'create': False},
        }

    @api.model
    def action_simular_ahora(self):
        return self._abrir(self.hacer_corte(comun.ahora_local(), simulacion=True))

    @api.model
    def action_corte_ahora(self):
        return self._abrir(self.hacer_corte(comun.ahora_local(), simulacion=False))


class KoroshiWebCorteLinea(models.Model):
    _name = 'koroshi.web.corte.linea'
    _description = 'KOROSHI: OUT de un corte de pedidos web'
    _order = 'id'

    corte_id = fields.Many2one('koroshi.web.corte', 'Corte', required=True, ondelete='cascade', index=True)
    picking_id = fields.Many2one('stock.picking', 'OUT', ondelete='set null')
    pedido = fields.Char('Pedido')
    creada = fields.Datetime('OUT creada')
    uds = fields.Integer('Uds')
    accion = fields.Selection([
        ('agrupada', 'Agrupada'), ('agruparia', 'Se agruparía'),
        ('cancelada', 'Cancelada'), ('cancelaria', 'Se cancelaría'),
        ('leida', 'Sin reserva completa, pero ya tiene algo leído: no se toca'),
        ('error', 'No se ha podido cancelar (sigue como estaba)'),   # v1.1.0 (R10)
    ], 'Qué se ha hecho')
    agrupacion = fields.Char('Agrupación')
    falta = fields.Text('Falta (reservado de pedido)')
    hay = fields.Text('Sí hay')
