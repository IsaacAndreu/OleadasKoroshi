# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Impresión v1.0.0 - cola de impresión para las impresoras USB de los PC del almacén.
# Diseño: bin/versiones/diseno-imprimir-desde-pda_2026-11-25_v4.md (visto bueno de Isaac el 25/11/2026).
#
# Las impresoras van por cable a un PC (sin red propia): Odoo no puede imprimir en ellas. La PDA apunta aquí un
# trabajo (un PDF: un adjunto ya hecho, p. ej. la etiqueta de GLS/XPO, o un informe QWeb de unos registros) para una
# impresora, y el agente de ese PC (bin/agente_impresion) pregunta cada pocos segundos, imprime y dice cómo ha ido.
#
# Lo que llama el agente (y nada más): agente_siguientes, agente_pdf, agente_hecho.
# Lo que llaman las pantallas: encolar.
# No añade campos a tablas de Odoo: dos tablas propias.
# =============================================================================
import base64
import datetime
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.koroshi_base import comun

from .. import logica

_logger = logging.getLogger(__name__)

ESTADOS = [
    (logica.PENDIENTE, 'Pendiente'),
    (logica.IMPRIMIENDO, 'Imprimiendo'),
    (logica.IMPRESO, 'Impreso'),
    (logica.ERROR, 'Error'),
]


class KoroshiImpresora(models.Model):
    _name = 'koroshi.impresora'
    _description = 'KOROSHI - impresora de un PC del almacén'
    _order = 'codigo'

    name = fields.Char('Nombre', required=True, help='Lo que se ve en la PDA, p. ej. «Zebra Expediciones».')
    codigo = fields.Char('Código', required=True,
                         help='El que pone el agente del PC en su config.ini (p. ej. EXP1). No se cambia una vez en '
                              'marcha: el agente dejaría de encontrar sus trabajos.')
    puesto = fields.Char('Puesto', help='Dónde está, p. ej. «Portátil de Expediciones».')
    activa = fields.Boolean('Activa', default=True)
    ultimo_contacto = fields.Datetime('Último contacto del agente', readonly=True)
    conectada = fields.Boolean('Conectada', compute='_compute_conectada',
                               help='El agente ha preguntado en el último minuto.')
    n_pendientes = fields.Integer('Pendientes', compute='_compute_conectada')
    n_errores = fields.Integer('Con error', compute='_compute_conectada')

    _sql_constraints = [('codigo_unico', 'unique(codigo)', 'Ya hay una impresora con ese código.')]

    def _compute_conectada(self):
        ahora = fields.Datetime.now()
        Trabajo = self.env['koroshi.impresion.trabajo']
        for imp in self:
            imp.conectada = logica.conectada(imp.ultimo_contacto, ahora)
            imp.n_pendientes = Trabajo.search_count(
                [('impresora_id', '=', imp.id), ('estado', 'in', (logica.PENDIENTE, logica.IMPRIMIENDO))])
            imp.n_errores = Trabajo.search_count([('impresora_id', '=', imp.id), ('estado', '=', logica.ERROR)])

    @api.model
    def _por_codigo(self, codigo):
        imp = self.sudo().search([('codigo', '=', (codigo or '').strip())], limit=1)
        if not imp:
            raise UserError(_('No hay ninguna impresora con el código %s.') % codigo)
        return imp


class KoroshiImpresionTrabajo(models.Model):
    _name = 'koroshi.impresion.trabajo'
    _description = 'KOROSHI - trabajo de la cola de impresión'
    _order = 'id desc'

    impresora_id = fields.Many2one('koroshi.impresora', 'Impresora', required=True, ondelete='restrict', index=True)
    descripcion = fields.Char('Qué', help='P. ej. «XPO 121771350 · K77 · 6 bultos».')
    origen = fields.Char('Pantalla', help='Desde dónde se pidió (p. ej. transportista).')
    adjunto_id = fields.Many2one('ir.attachment', 'PDF adjunto', ondelete='set null')
    informe = fields.Char('Informe', help='report_name del informe QWeb (modulo.plantilla), si no es un adjunto.')
    modelo = fields.Char('Modelo del informe')
    ids_registros = fields.Char('Registros del informe', help='ids separados por comas.')
    copias = fields.Integer('Copias', default=1)
    estado = fields.Selection(ESTADOS, 'Estado', default=logica.PENDIENTE, required=True, index=True)
    error_texto = fields.Text('Error')
    intentos = fields.Integer('Intentos', default=0)
    usuario_id = fields.Many2one('res.users', 'Usuario', default=lambda s: s.env.user, readonly=True)
    operario = fields.Char('Operario', help='El de la tarjeta en la PDA, si lo hay.')
    fecha_inicio = fields.Datetime('Recogido por el agente', readonly=True)
    fecha_impreso = fields.Datetime('Impreso', readonly=True)

    # ------------------------------------------------------------------ pantallas
    @api.model
    def encolar(self, impresora_codigo, descripcion='', adjunto_ids=None, informe=None, modelo=None, ids=None,
                copias=1, origen='', operario=''):
        """Apunta uno o varios trabajos para la impresora. adjunto_ids: PDF ya hechos (el mismo contenido una sola
        vez). informe + modelo + ids: un informe QWeb. Devuelve {'trabajos': [ids], 'conectada': bool, 'aviso': txt}."""
        imp = self.env['koroshi.impresora']._por_codigo(impresora_codigo)
        if not imp.activa:
            raise UserError(_('La impresora %s está desactivada.') % imp.name)
        if isinstance(ids, str):
            ids = logica.ids_de_texto(ids)
        error = logica.comprobar_trabajo(adjunto_ids, informe, modelo, ids)
        if error:
            raise UserError(error)
        try:
            copias = logica.copias_validas(copias)
        except ValueError as e:
            raise UserError(str(e))
        comunes = {'impresora_id': imp.id, 'descripcion': descripcion, 'copias': copias, 'origen': origen,
                   'operario': operario}
        nuevos = self.browse()
        if adjunto_ids:
            adjuntos = self.env['ir.attachment'].sudo().browse(adjunto_ids).exists()
            if len(adjuntos) != len(set(adjunto_ids)):
                raise UserError(_('No existen los adjuntos %s.') % adjunto_ids)
            no_pdf = adjuntos.filtered(lambda a: (a.mimetype or '') != 'application/pdf')
            if no_pdf:
                raise UserError(_('Solo se imprimen PDF: %s') % ', '.join(no_pdf.mapped('name')))
            unicos = logica.unicos_por_contenido([{'id': a.id, 'checksum': a.checksum} for a in adjuntos])
            for aid in unicos:
                nuevos |= self.sudo().create(dict(comunes, adjunto_id=aid))
        else:
            if not self.env['ir.actions.report'].sudo().search([('report_name', '=', informe)], limit=1):
                raise UserError(_('No existe el informe %s: no se puede imprimir.') % informe)
            nuevos |= self.sudo().create(dict(comunes, informe=informe, modelo=modelo,
                                              ids_registros=logica.texto_de_ids(ids)))
        conectada = logica.conectada(imp.ultimo_contacto, fields.Datetime.now())
        aviso = '' if conectada else _('%s no está conectada: saldrá cuando se encienda %s.') % (
            imp.name, imp.puesto or _('su PC'))
        _logger.info('Impresión: %d trabajo(s) en cola para %s (%s)', len(nuevos), imp.codigo, descripcion)
        return {'trabajos': nuevos.ids, 'conectada': conectada, 'aviso': aviso, 'impresora': imp.name}

    def accion_reintentar(self):
        """Oficina: vuelve a poner en cola los trabajos con error."""
        self.filtered(lambda t: t.estado == logica.ERROR).write(
            {'estado': logica.PENDIENTE, 'intentos': 0, 'error_texto': False, 'fecha_inicio': False})
        return True

    # ------------------------------------------------------------------ agente del PC
    def _rescatar_atascados(self, impresora):
        ahora = fields.Datetime.now()
        for t in self.sudo().search([('impresora_id', '=', impresora.id), ('estado', '=', logica.IMPRIMIENDO)]):
            nuevo = logica.que_hacer_atascado(t.fecha_inicio, t.intentos, ahora)
            if nuevo == logica.PENDIENTE:
                t.write({'estado': nuevo, 'fecha_inicio': False})
            elif nuevo == logica.ERROR:
                t.write({'estado': nuevo, 'error_texto': _('El agente no contestó en %d intentos.') % t.intentos})

    @api.model
    def agente_siguientes(self, impresora_codigo):
        """El agente pregunta: marca el contacto y se lleva hasta MAX_POR_VUELTA pendientes, por orden de llegada.
        FOR UPDATE SKIP LOCKED: si hubiera dos agentes con el mismo código, no se llevan el mismo trabajo."""
        imp = self.env['koroshi.impresora']._por_codigo(impresora_codigo)
        imp.sudo().write({'ultimo_contacto': fields.Datetime.now()})
        if not imp.activa:
            return []
        self._rescatar_atascados(imp)
        self.env.cr.execute(
            "SELECT id FROM koroshi_impresion_trabajo WHERE impresora_id = %s AND estado = %s "
            "ORDER BY id LIMIT %s FOR UPDATE SKIP LOCKED",
            (imp.id, logica.PENDIENTE, logica.MAX_POR_VUELTA))
        trabajos = self.sudo().browse([r[0] for r in self.env.cr.fetchall()])
        res = []
        for t in trabajos:
            t.write({'estado': logica.IMPRIMIENDO, 'fecha_inicio': fields.Datetime.now(), 'intentos': t.intentos + 1})
            res.append({'id': t.id, 'descripcion': t.descripcion or '', 'copias': t.copias or 1})
        return res

    @api.model
    def agente_pdf(self, trabajo_id):
        """El PDF del trabajo en base64 (el adjunto tal cual, o el informe generado aquí)."""
        t = self.sudo().browse(int(trabajo_id)).exists()
        if not t:
            raise UserError(_('No existe el trabajo %s.') % trabajo_id)
        if t.adjunto_id:
            datos = t.adjunto_id.datas
            if not datos:
                raise UserError(_('El adjunto %s está vacío.') % t.adjunto_id.name)
            return datos.decode() if isinstance(datos, bytes) else datos
        informe = self.env['ir.actions.report'].sudo().search([('report_name', '=', t.informe)], limit=1)
        if not informe:
            raise UserError(_('No existe el informe %s.') % t.informe)
        ids = logica.ids_de_texto(t.ids_registros)
        pdf, _formato = informe.with_context(allowed_company_ids=[comun.COMPANY_ID]).render_qweb_pdf(ids)
        return base64.b64encode(pdf).decode()

    @api.model
    def agente_hecho(self, trabajo_id, ok, texto=''):
        """El agente dice cómo ha ido. Error: vuelve a pendiente hasta MAX_INTENTOS; después queda en error."""
        t = self.sudo().browse(int(trabajo_id)).exists()
        if not t:
            return False
        if ok:
            t.write({'estado': logica.IMPRESO, 'fecha_impreso': fields.Datetime.now(), 'error_texto': False})
        else:
            estado = logica.ERROR if t.intentos >= logica.MAX_INTENTOS else logica.PENDIENTE
            t.write({'estado': estado, 'error_texto': (texto or '')[:2000], 'fecha_inicio': False})
            _logger.warning('Impresión: trabajo %s con error (%s): %s', t.id, t.impresora_id.codigo, texto)
        return True

    # ------------------------------------------------------------------ cron
    @api.model
    def _cron_limpiar(self):
        limite = fields.Datetime.now() - datetime.timedelta(days=logica.DIAS_GUARDAR)
        viejos = self.sudo().search([('estado', '=', logica.IMPRESO), ('fecha_impreso', '<', limite)])
        n = len(viejos)
        viejos.unlink()
        _logger.info('Impresión: %d trabajos impresos de más de %d días borrados', n, logica.DIAS_GUARDAR)
