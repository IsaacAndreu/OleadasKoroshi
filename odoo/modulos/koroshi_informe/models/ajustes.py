# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Informe: sus parametros en «Ajustes KOROSHI» (koroshi_menu). Hereda la pantalla sin cambiar koroshi_menu:
# lee y guarda solo sus claves koroshi_informe.* y deja el resto a koroshi_menu.
# =============================================================================
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError

# campo -> (clave, tipo, defecto)
PARAMETROS_INFORME = {
    'inf_destinatarios': ('koroshi_informe.destinatarios', 'char', ''),
    'inf_diario': ('koroshi_informe.diario', 'bool', '1'),
    'inf_hora_diario': ('koroshi_informe.hora_diario', 'char', '17:00'),
    'inf_semanal': ('koroshi_informe.semanal', 'bool', '1'),
    'inf_mensual': ('koroshi_informe.mensual', 'bool', '1'),
    'inf_hora_resumen': ('koroshi_informe.hora_resumen', 'char', '08:00'),
    'inf_minutos_ranking': ('koroshi_informe.minutos_ranking', 'int', '60'),
    'inf_excluir': ('koroshi_informe.excluir', 'char', ''),
}
SI = ('1', 'true', 'True', 'si', u'sí')
RE_CORREO = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


class KoroshiAjustesInforme(models.TransientModel):
    _inherit = 'koroshi.ajustes'

    inf_destinatarios = fields.Char('Informe de productividad: correos',
                                    help='La responsable y el jefe de almacén. Separados por coma. Vacío = no se manda.')
    inf_diario = fields.Boolean('Mandar el diario')
    inf_hora_diario = fields.Char('Hora del diario', help='HH:MM. Antes de mandarlo se recalculan la ficha KPI y las '
                                                          'faltas del día.')
    inf_semanal = fields.Boolean('Mandar el semanal (lunes)', help='La semana anterior contra la de antes.')
    inf_mensual = fields.Boolean('Mandar el mensual (día 1)', help='El mes anterior contra el de antes.')
    inf_hora_resumen = fields.Char('Hora del semanal y el mensual', help='HH:MM')
    inf_minutos_ranking = fields.Integer('Mejores y récords desde (min)',
                                         help='Minutos trabajando con tarjeta en el día para entrar en «mejores» y '
                                              'récords.')
    inf_excluir = fields.Char('No sacar estos operarios', help='Códigos de tarjeta separados por coma (pruebas).')

    @api.model
    def default_get(self, campos):
        res = super(KoroshiAjustesInforme, self).default_get(campos)
        icp = self.env['ir.config_parameter'].sudo()
        for campo, (clave, tipo, defecto) in PARAMETROS_INFORME.items():
            if campo not in campos:
                continue
            valor = icp.get_param(clave, defecto)
            if valor is False or valor is None:
                valor = defecto
            if tipo == 'bool':
                res[campo] = valor in SI
            elif tipo == 'int':
                try:
                    res[campo] = int(valor)
                except ValueError:
                    res[campo] = int(defecto)
            else:
                res[campo] = valor or False
        return res

    def action_guardar(self):
        self.ensure_one()
        for campo in ('inf_hora_diario', 'inf_hora_resumen'):
            if self[campo] and not self._hora_valida(self[campo]):
                raise UserError(_('%s tiene que ser HH:MM (por ejemplo 17:00).') % self._fields[campo].string)
        if self.inf_minutos_ranking < 0:
            raise UserError(_('Los números no pueden ser negativos.'))
        correos = [x for x in re.split(r'[,;\s]+', self.inf_destinatarios or '') if x]
        malos = [x for x in correos if not RE_CORREO.match(x)]
        if malos:
            raise UserError(_('Correo no válido: %s') % ', '.join(malos))
        icp = self.env['ir.config_parameter'].sudo()
        cambios = []
        for campo, (clave, tipo, defecto) in PARAMETROS_INFORME.items():
            valor = self[campo]
            if tipo == 'bool':
                nuevo = valor and '1' or '0'
            elif tipo == 'int':
                nuevo = str(valor or 0)
            elif campo == 'inf_destinatarios':
                nuevo = ', '.join(correos)
            else:
                nuevo = (valor or '').strip()
            actual = icp.get_param(clave)
            if actual is False or actual is None:
                actual = defecto
            if actual != nuevo:
                icp.set_param(clave, nuevo or False)      # vacio = se quita el parametro (value es obligatorio)
                cambios.append(self._fields[campo].string)
        accion = super(KoroshiAjustesInforme, self).action_guardar()
        if cambios:
            ctx = dict(accion.get('context') or {})
            msg = ctx.get('koroshi_aviso') or ''
            if msg.startswith(_('No había nada que cambiar')):
                msg = _('Guardado: %s.') % ', '.join(cambios)
            else:
                msg = '%s %s' % (msg, _('Informe: %s.') % ', '.join(cambios))
            ctx['koroshi_aviso'] = msg.strip()
            accion['context'] = ctx
        return accion
