# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Transportista v1.1.0 - etiqueta GLS/XPO desde la PDA (área Expediciones), escaneando las CJ de la tienda.
# Diseño: bin/versiones/diseno-imprimir-desde-pda_2026-11-25_v4.md (visto bueno de Isaac el 25/11/2026).
#
# 1. Se escanean las CJ que hay físicamente. La primera fija la tienda (cliente de la OUT, «..., K24 - VALLADOLID»).
# 2. Odoo espera las cajas distintas de las OUT de esa tienda validadas, sin etiqueta, de los últimos 10 días y fuera
#    de un camión XPO cerrado. Una CJ de más = error con el porqué; una de menos = se dice cuál. Sin cuadrar no se
#    puede etiquetar (Isaac: bloquear siempre).
# 3. «Imprimir etiquetas»: lo mismo que hace hoy el portátil: poner el transportista a las OUT y
#      GLS (id 42): la acción 1834 v5 (una expedición; juntadas y cajas compartidas con el mismo tracking);
#      XPO (id 173): la acción 1771 (carrier.xpo_es_send_shipping, que con koroshi_xpo_bultos cuenta cajas distintas).
#    Se hace COMMIT justo después de la llamada al transportista: la expedición ya existe fuera y no se puede perder.
#    Después, el PDF que deja el transportista adjunto en las OUT va a la cola de impresión (koroshi_impresion) de la
#    impresora del portátil de Expediciones (parámetro koroshi_transportista.impresora, por defecto EXP1). El mismo
#    PDF adjunto a varias OUT se imprime una vez.
# 4. «Reimprimir»: vuelve a mandar a la cola el PDF de una expedición ya hecha (no registra nada).
# GLS -70 (ya existía en GLS): no se intenta recuperar aquí; se dice que se haga con la acción 1834 desde el portátil.
# No añade campos a tablas de Odoo: un registro propio (koroshi.transportista.registro).
# =============================================================================
import datetime
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.koroshi_base.comun import COMPANY_ID

from .. import logica

_logger = logging.getLogger(__name__)

CARRIER_GLS = 42            # «GLS / ASM España» (el que usa la acción 1834; 370 OUT del 17 al 25/11)
CARRIER_XPO = 173           # «XPO ES» (el que exige la acción 1771)
PARAM_IMPRESORA = 'koroshi_transportista.impresora'
CAMPO_BARRAS_GLS = 'gls_asm_public_tracking_ref'
PREFIJOS_ETIQUETA = ('LabelXPO_', 'gls_label_')


class KoroshiTransportistaRegistro(models.Model):
    _name = 'koroshi.transportista.registro'
    _description = 'KOROSHI - etiquetas de transportista sacadas desde la PDA'
    _order = 'fecha desc, id desc'
    _rec_name = 'tracking'

    fecha = fields.Datetime('Cuándo', default=fields.Datetime.now, readonly=True, index=True)
    employee_id = fields.Many2one('hr.employee', 'Operario', readonly=True)
    user_id = fields.Many2one('res.users', 'Usuario', default=lambda s: s.env.user, readonly=True)
    tipo = fields.Selection([('etiquetar', 'Etiquetar'), ('reimprimir', 'Reimprimir')], 'Qué', readonly=True)
    transportista = fields.Selection([(logica.GLS, 'GLS'), (logica.XPO, 'XPO')], 'Transportista', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Cliente', readonly=True)
    tienda = fields.Char('Tienda', readonly=True, index=True)
    tracking = fields.Char('Tracking', readonly=True, index=True)
    picking_ids = fields.Many2many('stock.picking', 'koroshi_transportista_registro_picking_rel', 'registro_id',
                                   'picking_id', 'OUT', readonly=True)
    cajas = fields.Text('CJ escaneadas', readonly=True)
    bultos = fields.Integer('Bultos', readonly=True)
    impresos = fields.Integer('PDF a la cola', readonly=True)
    resultado = fields.Text('Resultado', readonly=True)
    aviso = fields.Boolean('Con aviso', readonly=True)
    token = fields.Char('Token', readonly=True, index=True, copy=False)

    # ------------------------------------------------------------------ lectura
    @api.model
    def _paquete(self, cj):
        return self.env['stock.quant.package'].sudo().search([('name', '=', cj)], limit=1)

    @api.model
    def _lineas_caja(self, paquete):
        return self.env['stock.move.line'].sudo().search(
            [('result_package_id', '=', paquete.id), ('state', '!=', 'cancel'), ('qty_done', '>', 0),
             ('picking_id.picking_type_code', '=', 'outgoing'), ('picking_id.company_id', '=', COMPANY_ID)])

    @api.model
    def _en_cierre(self, pickings):
        if 'koroshi.envio.cierre' not in self.env or not pickings:
            return self.env['stock.picking']
        cierres = self.env['koroshi.envio.cierre'].sudo().search([('picking_ids', 'in', pickings.ids)])
        return cierres.mapped('picking_ids') & pickings

    @api.model
    def _desde(self):
        return fields.Datetime.now() - datetime.timedelta(days=logica.DIAS_PENDIENTES)

    @api.model
    def _pendientes(self, partner):
        """OUT de la tienda validadas, sin etiqueta, de los últimos 10 días y fuera de un camión cerrado."""
        dominio = [('company_id', '=', COMPANY_ID), ('picking_type_code', '=', 'outgoing'),
                   ('partner_id', '=', partner.id), ('state', '=', 'done'), ('carrier_tracking_ref', '=', False),
                   ('date_done', '>=', self._desde())]
        Picking = self.env['stock.picking'].sudo()
        if CAMPO_BARRAS_GLS in Picking._fields:
            dominio.append((CAMPO_BARRAS_GLS, '=', False))
        outs = Picking.search(dominio, order='date_done, id')
        return outs - self._en_cierre(outs)

    @api.model
    def _cajas_de(self, picking):
        """Las cajas distintas de una OUT (la misma regla que koroshi_xpo_bultos.bultos_de)."""
        lineas = picking.move_line_ids
        cajas = lineas.filtered(lambda ml: ml.qty_done > 0).mapped('result_package_id')
        return cajas or lineas.mapped('result_package_id')

    @api.model
    def _esperadas(self, outs):
        """{CJ: [OUT]} de las OUT pendientes."""
        res = {}
        for p in outs:
            for caja in self._cajas_de(p):
                res.setdefault(caja.name, []).append(p.name)
        return res

    @api.model
    def _datos_caja(self, cj, tienda):
        """Lo que hace falta para decir por qué una CJ no cuenta (logica.motivo_sobra)."""
        paquete = self._paquete(cj)
        d = {'existe': bool(paquete), 'juntada_en': '', 'outs': [], 'tienda': tienda}
        if not paquete:
            return d
        if 'koroshi.juntar.registro' in self.env:
            j = self.env['koroshi.juntar.registro'].sudo().search([('cj_pequena', '=', cj)], limit=1)
            if j and not self._lineas_caja(paquete):
                d['juntada_en'] = j.cj_destino
        pickings = self._lineas_caja(paquete).mapped('picking_id')
        cerradas = self._en_cierre(pickings)
        ahora = fields.Datetime.now()
        for p in pickings:
            d['outs'].append({'nombre': p.name, 'tienda': logica.tienda_de(p.partner_id.display_name),
                              'estado': p.state, 'tracking': p.carrier_tracking_ref or '',
                              'dias': (ahora - p.date_done).days if p.date_done else 0,
                              'en_cierre': p in cerradas})
        return d

    @api.model
    def _propuesto(self, partner, outs):
        """GLS o XPO: el que ya tengan las OUT o, si no, el de la última etiqueta de esta tienda."""
        tipos = set(logica.transportista_de(t) for t in outs.mapped('carrier_id.delivery_type')) - {''}
        if len(tipos) == 1:
            return tipos.pop()
        ultima = self.env['stock.picking'].sudo().search(
            [('company_id', '=', COMPANY_ID), ('picking_type_code', '=', 'outgoing'), ('partner_id', '=', partner.id),
             ('carrier_tracking_ref', '!=', False), ('carrier_id', '!=', False)], order='date_done desc', limit=1)
        return logica.transportista_de(ultima.carrier_id.delivery_type)

    @api.model
    def _etiquetadas(self, partner):
        """Las últimas expediciones de la tienda (para «Reimprimir»): [{tracking, transportista, outs, fecha}]."""
        outs = self.env['stock.picking'].sudo().search(
            [('company_id', '=', COMPANY_ID), ('picking_type_code', '=', 'outgoing'), ('partner_id', '=', partner.id),
             ('carrier_tracking_ref', '!=', False), ('date_done', '>=', self._desde())], order='date_done desc')
        res = {}
        for p in outs:
            e = res.setdefault(p.carrier_tracking_ref, {
                'tracking': p.carrier_tracking_ref, 'transportista': logica.NOMBRES.get(
                    logica.transportista_de(p.carrier_id.delivery_type), p.carrier_id.name or ''),
                'outs': [], 'fecha': fields.Date.to_string(p.date_done.date()) if p.date_done else ''})
            e['outs'].append(p.name)
        return list(res.values())[:3]

    @api.model
    def _partner_de_cj(self, cj):
        paquete = self._paquete(cj)
        if not paquete:
            raise UserError(_('%s no existe en Odoo.') % cj)
        pickings = self._lineas_caja(paquete).mapped('picking_id')
        if not pickings:
            j = self.env['koroshi.juntar.registro'].sudo().search([('cj_pequena', '=', cj)], limit=1) \
                if 'koroshi.juntar.registro' in self.env else None
            if j:
                raise UserError(_('%s está juntada dentro de %s: lee esa.') % (cj, j.cj_destino))
            raise UserError(_('%s está vacía: no tiene prendas en ninguna OUT.') % cj)
        partners = pickings.mapped('partner_id')
        if len(partners) > 1:
            raise UserError(_('%s tiene prendas de varias tiendas (%s): hay que mirarla en la oficina.') % (
                cj, ', '.join(partners.mapped('display_name'))))
        if not logica.tienda_de(partners.display_name):
            raise UserError(_('%s no es de una tienda (%s): esta pantalla es para tiendas.') % (
                cj, partners.display_name))
        return partners

    @api.model
    def cj_por_cifras(self, cifras, partner_id=False):
        """v1.1.0: la CJ que acaba en esas cifras, escritas a mano porque la etiqueta no se lee (Isaac, 25/11).
        Primero entre las cajas que espera la tienda de la pantalla; si no, entre las de cualquier OUT pendiente de
        etiqueta; si no, la única caja con ese final (para que la pantalla diga por qué no va). Varias = más cifras.
        Las líneas se filtran en Python: un dominio con punto (picking_id.state) haría IN con miles de OUT."""
        cifras = (cifras or '').strip()
        paquetes = self.env['stock.quant.package'].sudo().search([('name', '=like', 'CJ%' + cifras)], limit=500)
        if not paquetes:
            raise UserError(_('Ninguna caja (CJ) acaba en %s.') % cifras)
        partner = self.env['res.partner'].sudo().browse(int(partner_id)).exists() if partner_id else None
        if partner:
            cj, coinciden = logica.elegir_por_cifras(cifras, list(self._esperadas(self._pendientes(partner))))
            if cj:
                return cj
            if len(coinciden) > 1:
                raise UserError(_('Hay %d cajas de esta tienda que acaban en %s (%s): escribe más cifras.') % (
                    len(coinciden), cifras, ', '.join(coinciden)))
        desde = self._desde()
        lineas = self.env['stock.move.line'].sudo().search(
            [('result_package_id', 'in', paquetes.ids), ('qty_done', '>', 0), ('state', '=', 'done')])
        pendientes = lineas.filtered(
            lambda ml: ml.picking_id.picking_type_code == 'outgoing' and ml.picking_id.company_id.id == COMPANY_ID
            and not ml.picking_id.carrier_tracking_ref and ml.picking_id.date_done
            and ml.picking_id.date_done >= desde)
        cj, coinciden = logica.elegir_por_cifras(cifras, pendientes.mapped('result_package_id.name'))
        if cj:
            return cj
        if len(coinciden) > 1:
            raise UserError(_('Hay %d cajas pendientes de etiqueta que acaban en %s (%s): escribe más cifras.') % (
                len(coinciden), cifras, ', '.join(coinciden[:6])))
        cj, coinciden = logica.elegir_por_cifras(cifras, paquetes.mapped('name'))
        if cj:
            return cj
        raise UserError(_('Hay %d cajas que acaban en %s y ninguna está pendiente de etiqueta: escribe más cifras.') % (
            len(coinciden), cifras))

    @api.model
    def estado(self, leidas, partner_id=False):
        """Lo que enseña la pantalla. leidas: CJ escaneadas. La tienda: partner_id o la de la primera CJ."""
        leidas = [c.strip().upper() for c in (leidas or []) if (c or '').strip()]
        Partner = self.env['res.partner'].sudo()
        partner = Partner.browse(int(partner_id)).exists() if partner_id else Partner
        if not partner:
            if not leidas:
                raise UserError(_('Lee una caja (CJ).'))
            partner = self._partner_de_cj(leidas[0])
        tienda = logica.tienda_de(partner.display_name)
        outs = self._pendientes(partner)
        esperadas = self._esperadas(outs)
        c = logica.cuadre(leidas, esperadas)
        sobran = [{'cj': cj, 'motivo': logica.motivo_sobra(self._datos_caja(cj, tienda))} for cj in c['sobran']]
        hoy = fields.Datetime.now().date()
        lista_outs = [{'nombre': p.name, 'origen': p.origin or '', 'bultos': len(self._cajas_de(p)),
                       'dia': fields.Date.to_string(p.date_done.date()) if p.date_done else '',
                       'de_otro_dia': bool(p.date_done and p.date_done.date() < hoy)} for p in outs]
        sin_validar = self.env['stock.picking'].sudo().search(
            [('company_id', '=', COMPANY_ID), ('picking_type_code', '=', 'outgoing'), ('partner_id', '=', partner.id),
             ('state', 'in', ('confirmed', 'waiting', 'assigned'))])
        avisos = []
        if sin_validar:
            avisos.append(_('Hay %d OUT de esta tienda sin validar (%s): se quedan fuera de esta etiqueta.') % (
                len(sin_validar), ', '.join(sin_validar[:5].mapped('name'))))
        if any(o['de_otro_dia'] for o in lista_outs):
            avisos.append(_('Hay OUT de otros días sin etiqueta: van en la misma expedición (marcadas).'))
        return {
            'ok': True, 'partner_id': partner.id, 'tienda': tienda, 'outs': lista_outs,
            'cajas': [{'cj': cj, 'outs': esperadas[cj], 'leida': cj in c['bien']} for cj in sorted(esperadas)],
            'leidas': c['bien'], 'sobran': sobran, 'faltan': c['faltan'], 'n_leidas': c['leidas'],
            'n_esperadas': c['esperadas'], 'cuadra': c['ok'], 'avisos': avisos,
            'propuesto': self._propuesto(partner, outs), 'etiquetadas': self._etiquetadas(partner),
            'impresora': self._impresora_info(),
        }

    # ------------------------------------------------------------------ impresora
    @api.model
    def _codigo_impresora(self):
        return self.env['ir.config_parameter'].sudo().get_param(PARAM_IMPRESORA, 'EXP1')

    @api.model
    def _impresora_info(self):
        imp = self.env['koroshi.impresora'].sudo().search([('codigo', '=', self._codigo_impresora())], limit=1)
        if not imp:
            return {'nombre': '', 'conectada': False}
        return {'nombre': imp.name, 'conectada': imp.conectada}

    @api.model
    def _adjuntos_etiqueta(self, pickings, desde=None):
        dominio = [('res_model', '=', 'stock.picking'), ('res_id', 'in', pickings.ids),
                   ('mimetype', '=', 'application/pdf'), '|', ('name', '=like', PREFIJOS_ETIQUETA[0] + '%'),
                   ('name', '=like', PREFIJOS_ETIQUETA[1] + '%')]
        if desde:
            dominio.append(('create_date', '>=', desde))
        return self.env['ir.attachment'].sudo().search(dominio, order='id')

    @api.model
    def _imprimir(self, adjuntos, descripcion, operario):
        if not adjuntos:
            return {'impresos': 0, 'aviso': _('No ha llegado el PDF de la etiqueta: imprímela desde el portátil.')}
        r = self.env['koroshi.impresion.trabajo'].encolar(
            self._codigo_impresora(), descripcion=descripcion, adjunto_ids=adjuntos.ids, origen='transportista',
            operario=operario or '')
        return {'impresos': len(r['trabajos']), 'aviso': r.get('aviso') or '', 'impresora': r.get('impresora')}

    # ------------------------------------------------------------------ etiquetar
    @api.model
    def _bloquear(self, outs):
        """Que nadie más (otra PDA o el portátil) etiquete estas OUT a la vez."""
        try:
            self.env.cr.execute('SELECT id FROM stock_picking WHERE id IN %s FOR UPDATE NOWAIT', (tuple(outs.ids),))
        except Exception:
            _logger.info('Transportista: OUT bloqueadas por otro proceso: %s', outs.ids)
            raise UserError(_('Otra persona está etiquetando esta tienda ahora mismo. Espera un momento.'))

    @api.model
    def etiquetar(self, leidas, partner_id, transportista, employee=None, token=''):
        if transportista not in logica.TRANSPORTISTAS:
            raise UserError(_('Elige GLS o XPO.'))
        if token:
            ya = self.sudo().search([('token', '=', token)], limit=1)
            if ya:
                return {'ok': True, 'repetido': True, 'tracking': ya.tracking, 'resultado': ya.resultado}
        est = self.estado(leidas, partner_id)
        if not est['cuadra']:
            raise UserError(_('No cuadra: no se ha hecho nada. Leídas %d de %d.') % (est['n_leidas'],
                                                                                    est['n_esperadas']))
        partner = self.env['res.partner'].sudo().browse(est['partner_id'])
        outs = self._pendientes(partner)
        if not outs:
            raise UserError(_('Esta tienda no tiene OUT pendientes de etiqueta.'))
        self._bloquear(outs)
        outs.invalidate_cache()
        if any(outs.mapped('carrier_tracking_ref')):
            raise UserError(_('Alguna OUT ya tiene etiqueta (la ha hecho otra persona): vuelve a leer.'))
        inicio = fields.Datetime.now() - datetime.timedelta(seconds=2)
        operario = employee.name if employee else ''
        if transportista == logica.XPO:
            r = self._enviar_xpo(outs)
        else:
            r = self._enviar_gls(outs)
        # La expedición ya existe en el transportista: se guarda YA (tracking y transportista en las OUT), pase lo que
        # pase después (si algo falla más abajo, la ruta deshace solo lo posterior a este commit)
        self.env.cr.commit()
        texto = r['texto']
        reg = self.sudo().create({
            'employee_id': employee.id if employee else False, 'tipo': 'etiquetar', 'transportista': transportista,
            'partner_id': partner.id, 'tienda': est['tienda'], 'tracking': r.get('tracking') or '',
            'picking_ids': [(6, 0, outs.ids)], 'cajas': ', '.join(est['leidas']), 'bultos': est['n_esperadas'],
            'resultado': texto, 'aviso': bool(r.get('aviso')), 'token': token or False})
        for p in outs:
            p.message_post(body=_('Etiqueta %s sacada desde la PDA (Transportista) por %s: %d CJ escaneadas, '
                                  'todas cuadradas. %s') % (logica.NOMBRES[transportista], operario or '-',
                                                            est['n_esperadas'], texto))
        self.env.cr.commit()
        if not r.get('tracking'):
            return {'ok': False, 'msg': texto, 'hecho': True}
        imp = {'impresos': 0, 'aviso': ''}
        try:
            adjuntos = self._adjuntos_etiqueta(outs, desde=inicio)
            imp = self._imprimir(adjuntos, '%s %s · %s · %d bultos' % (
                logica.NOMBRES[transportista], r['tracking'], est['tienda'], est['n_esperadas']), operario)
        except Exception as e:  # noqa: BLE001 - la etiqueta ya está hecha: se dice y se puede reimprimir
            self.env.cr.rollback()
            _logger.exception('Transportista: etiqueta %s hecha pero no se ha podido mandar a imprimir', r['tracking'])
            imp = {'impresos': 0, 'aviso': _('Etiqueta hecha, pero no se ha podido mandar a imprimir (%s). Usa '
                                             '«Reimprimir».') % e}
        reg.sudo().write({'impresos': imp['impresos']})
        self.env.cr.commit()
        return {'ok': True, 'hecho': True, 'transportista': logica.NOMBRES[transportista], 'tracking': r['tracking'],
                'tienda': est['tienda'], 'bultos': est['n_esperadas'], 'outs': outs.mapped('name'),
                'texto': texto, 'aviso_envio': r.get('aviso') or '', 'impresos': imp['impresos'],
                'aviso_impresion': imp.get('aviso') or '', 'impresora': imp.get('impresora') or ''}

    @api.model
    def _error_texto(self, e):
        return str(e.args[0]) if getattr(e, 'args', None) else str(e)

    @api.model
    def _enviar_xpo(self, outs):
        """Acción 1771: transportista XPO en las OUT y xpo_es_send_shipping (koroshi_xpo_bultos: cajas distintas)."""
        carrier = self.env['delivery.carrier'].sudo().browse(CARRIER_XPO).exists()
        if not carrier or not hasattr(carrier, 'xpo_es_send_shipping'):
            raise UserError(_('No está el transportista XPO (id %d) en Odoo.') % CARRIER_XPO)
        outs.write({'carrier_id': carrier.id})
        try:
            res = carrier.xpo_es_send_shipping(outs)
        except UserError:
            raise
        except Exception as e:  # noqa: BLE001 - el error de XPO se enseña en la PDA tal cual
            _logger.exception('Transportista: error de XPO en %s', outs.mapped('name'))
            raise UserError(_('XPO ha dado un error: %s. No se ha hecho la etiqueta.') % self._error_texto(e))
        outs.invalidate_cache()
        trackings = set(outs.mapped('carrier_tracking_ref')) - {False, ''}
        if not trackings and isinstance(res, list) and res and isinstance(res[0], dict) and res[0].get('tracking_number'):
            outs.write({'carrier_tracking_ref': str(res[0]['tracking_number'])})
            trackings = {str(res[0]['tracking_number'])}
        if len(trackings) != 1:
            return {'tracking': ', '.join(sorted(trackings)), 'aviso': True,
                    'texto': _('XPO: OJO, las OUT han quedado con %d trackings (%s). Revisar en la oficina.') % (
                        len(trackings), ', '.join(sorted(trackings)) or 'ninguno')}
        tracking = trackings.pop()
        return {'tracking': tracking, 'texto': _('XPO %s registrada.') % tracking}

    @api.model
    def _enviar_gls(self, outs):
        """Acción 1834 v5 para una tienda: una expedición; juntadas y cajas compartidas con el mismo tracking."""
        carrier = self.env['delivery.carrier'].sudo().browse(CARRIER_GLS).exists()
        if not carrier or not hasattr(carrier, 'gls_asm_send_shipping'):
            raise UserError(_('No está el transportista GLS (id %d) en Odoo.') % CARRIER_GLS)
        rep = logica.reparto_gls([{'id': p.id, 'bultos': p.number_of_packages,
                                   'cajas': self._cajas_de(p).ids if p.has_packages else []} for p in outs])
        Picking = self.env['stock.picking'].sudo()
        enviar = Picking.browse(rep['enviar'])
        juntadas = Picking.browse(rep['juntadas'])
        outs.write({'carrier_id': carrier.id})
        try:
            res = carrier.gls_asm_send_shipping(enviar)
        except Exception as e:  # noqa: BLE001 - el error de GLS se enseña en la PDA tal cual
            msg = self._error_texto(e)
            _logger.warning('Transportista: error de GLS en %s: %s', enviar.mapped('name'), msg)
            if msg.strip().endswith('-70'):
                raise UserError(_('GLS dice que esta expedición YA EXISTE (-70). NO repetir: hacerlo desde el '
                                  'portátil con «Enviar al Expedidor» (acción 1834), que la recupera.'))
            raise UserError(_('GLS ha dado un error: %s. No se ha hecho la etiqueta.') % msg)
        vals = res[0] if res else {}
        enviar.invalidate_cache()
        tracking = vals.get('tracking_number') or (enviar[:1][CAMPO_BARRAS_GLS]
                                                  if CAMPO_BARRAS_GLS in enviar._fields else False)
        if not tracking:
            for p in enviar:
                p.message_post(body=_('GLS: enviada pero NO se ha recibido tracking. Revisar en GLS antes de '
                                      'reenviar.'))
            return {'tracking': '', 'aviso': True,
                    'texto': _('GLS: enviada pero NO ha devuelto tracking. NO repetir: avisar a la oficina para '
                               'revisarlo en GLS.')}
        tracking = str(tracking)
        enviar.write({'carrier_tracking_ref': tracking, 'carrier_id': carrier.id})
        for p in juntadas:
            p.write({'carrier_tracking_ref': tracking, 'carrier_id': carrier.id})
            if p.id in rep['compartidas']:
                p.message_post(body=_('GLS: las cajas de esta OUT ya van en otra OUT de la tienda (cajas '
                                      'compartidas). Va en la expedición %s.') % tracking)
            else:
                p.message_post(body=_('GLS: esta OUT no tiene bultos propios (juntada). Va en la expedición %s.')
                               % tracking)
        texto = _('GLS %s registrada.') % tracking
        aviso = rep['bultos_gls'] != rep['cajas']
        if aviso:
            texto += _(' OJO: GLS contará %d bultos y hay %d cajas (cajas cruzadas entre OUT). Avisar a la '
                       'oficina.') % (rep['bultos_gls'], rep['cajas'])
            for p in enviar:
                p.message_post(body=_('OJO GLS: esta expedición va con %d bultos y hay %d cajas (cajas compartidas '
                                      'entre OUT que no se han podido quitar). Avisar a GLS o corregirla.') % (
                    rep['bultos_gls'], rep['cajas']))
        return {'tracking': tracking, 'texto': texto, 'aviso': aviso}

    # ------------------------------------------------------------------ reimprimir
    @api.model
    def reimprimir(self, partner_id, tracking, employee=None):
        partner = self.env['res.partner'].sudo().browse(int(partner_id or 0)).exists()
        if not partner or not tracking:
            raise UserError(_('Falta la tienda o el tracking.'))
        outs = self.env['stock.picking'].sudo().search(
            [('company_id', '=', COMPANY_ID), ('partner_id', '=', partner.id), ('carrier_tracking_ref', '=', tracking)])
        if not outs:
            raise UserError(_('No hay OUT de esta tienda con el tracking %s.') % tracking)
        adjuntos = self._adjuntos_etiqueta(outs)
        if not adjuntos:
            raise UserError(_('El tracking %s no tiene el PDF de la etiqueta adjunto: imprímela desde el portátil.')
                            % tracking)
        # el último PDF de cada contenido (si GLS/XPO devolvió varios, el más nuevo)
        operario = employee.name if employee else ''
        imp = self._imprimir(adjuntos, 'Reimprimir %s · %s' % (tracking, logica.tienda_de(partner.display_name)),
                             operario)
        self.sudo().create({'employee_id': employee.id if employee else False, 'tipo': 'reimprimir',
                            'partner_id': partner.id, 'tienda': logica.tienda_de(partner.display_name),
                            'tracking': tracking, 'picking_ids': [(6, 0, outs.ids)], 'impresos': imp['impresos'],
                            'resultado': imp.get('aviso') or _('Reimpresa')})
        return {'ok': True, 'tracking': tracking, 'impresos': imp['impresos'], 'aviso_impresion': imp.get('aviso') or '',
                'impresora': imp.get('impresora') or ''}
