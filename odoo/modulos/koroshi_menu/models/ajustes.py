# -*- coding: utf-8 -*-
# =============================================================================
# v1.1: Ajustes KOROSHI en una sola pantalla (Inventario > Configuracion > KOROSHI > Ajustes KOROSHI).
# Los mismos parametros de siempre (ir.config_parameter, Ajustes > Tecnico > Parametros del sistema), con nombre y
# explicacion. Al abrir se leen; con «Guardar» se escriben solo los que han cambiado. No cambia nada mas.
# =============================================================================
from odoo import _, api, fields, models
from odoo.exceptions import UserError

# campo -> (clave del parametro, tipo, valor por defecto si no existe)
PARAMETROS = {
    'prep_activa': ('koroshi_preparacion.activa', 'bool', '1'),
    'prep_empleados': ('koroshi_preparacion.empleados', 'char', ''),
    'prep_agrupaciones': ('koroshi_preparacion.agrupaciones', 'bool', '1'),
    'prep_orden': ('koroshi_preparacion.orden', 'sel', 'ubicacion'),
    'prep_minutos_alarma': ('koroshi_preparacion.minutos_alarma', 'int', '4'),   # v1.2
    'prep_horario_alarma': ('koroshi_preparacion.horario_alarma', 'char',
                            '06:00-10:00,10:15-13:00,14:00-17:00'),   # v1.3
    'ops_minutos_sin_leer': ('koroshi_operarios.minutos_sin_leer', 'int', '15'),
    'ops_minutos_inactividad': ('koroshi_operarios.minutos_inactividad', 'int', '0'),
    'ops_uds_a_dos': ('koroshi_operarios.uds_a_dos', 'int', '150'),
    'ops_informe_destinatarios': ('koroshi_operarios.informe_destinatarios', 'char', ''),
    'ops_informe_hora': ('koroshi_operarios.informe_hora', 'char', '17:00'),
    'falt_validar_sola': ('koroshi_faltantes.validar_sola', 'bool', '1'),
    'falt_pedido_pendiente': ('koroshi_faltantes.pedido_pendiente', 'sel', 'no'),
    'kpi_dias_falta_repetida': ('koroshi_kpi.dias_falta_repetida', 'int', '3'),
    'pda_usuarios': ('koroshi_pda_app.usuarios', 'char', ''),
}
SI = ('1', 'true', 'True', 'si', u'sí')


class KoroshiAjustes(models.TransientModel):
    _name = 'koroshi.ajustes'
    _description = 'KOROSHI: ajustes en una pantalla'

    # Preparacion en Lecturas
    prep_activa = fields.Boolean('Preparación en Lecturas activa',
                                 help='Si se apaga, la PDA vuelve a abrir la app de código de barras de siempre.')
    prep_empleados = fields.Char('Operarios con Preparación',
                                 help='Códigos de tarjeta separados por coma, o * para todos.')
    prep_agrupaciones = fields.Boolean('Agrupaciones (Z-) también en Preparación',
                                       help='Si se apaga, las agrupaciones de zona van con la app de siempre.')
    prep_orden = fields.Selection([('ubicacion', 'Por ubicación (como la app de código de barras)'),
                                   ('ruta', 'Ruta optimizada (menos metros)')], 'Orden de las líneas')
    prep_minutos_alarma = fields.Integer(
        'Alarma en la PDA: minutos sin leer',
        help='Con la OUT abierta en la pantalla de preparar y estos minutos sin leer ninguna prenda, la PDA pita sin '
             'parar y parpadea en rojo hasta que lea una prenda o salga con ←. 0 = sin alarma. Por defecto 4.')
    prep_horario_alarma = fields.Char(
        'Alarma en la PDA: horario',
        help='Tramos en que puede sonar la alarma, HH:MM-HH:MM separados por coma (hora de la PDA). Fuera de estos '
             'tramos no suena ni cuenta. Por defecto 06:00-10:00,10:15-13:00,14:00-17:00 (sin la pausa ni la comida).')
    # Operarios y monitor
    ops_minutos_sin_leer = fields.Integer(
        'Minutos sin leer = parado',
        help='Un pedido abierto sin leer nada en estos minutos: el monitor lo marca en rojo y quien lo lea se lo '
             'queda sin preguntar «¿Unirte a X?».')
    ops_minutos_inactividad = fields.Integer('Salir solo de Lecturas tras (min)',
                                             help='La PDA sale sola de Lecturas tras estos minutos sin tocarla. '
                                                  '0 = nunca.')
    ops_uds_a_dos = fields.Integer('OUT «para hacer a dos» desde (uds)',
                                   help='En Colas, las OUT sueltas con al menos estas uds. 0 = nunca.')
    ops_informe_destinatarios = fields.Char('Informe diario: correos', help='Separados por coma.')
    ops_informe_hora = fields.Char('Informe diario: hora', help='HH:MM')
    # Faltantes
    falt_validar_sola = fields.Boolean('Validar la OUT sola al acabar los faltantes',
                                       help='Si ya no queda nada por coger. Apagado: solo con el botón «Validar OUT».')
    falt_pedido_pendiente = fields.Selection([('no', 'No crear pedido pendiente'), ('si', 'Crear pedido pendiente'),
                                              ('preguntar', 'Preguntar al operario')],
                                             'Si Odoo pregunta por el pedido pendiente')
    # KPI
    kpi_dias_falta_repetida = fields.Integer('Faltas repetidas: días seguidos',
                                             help='Un artículo con falta estos días seguidos sale en '
                                                  '«Faltas repetidas».')
    aviso = fields.Char('Aviso', readonly=True)
    # PDA
    pda_usuarios = fields.Char('Usuarios con la app de PDA', help='Ids de usuario separados por coma, o * para todos.')

    @api.model
    def default_get(self, campos):
        res = super(KoroshiAjustes, self).default_get(campos)
        if 'aviso' in campos:
            res['aviso'] = self.env.context.get('koroshi_aviso') or False
        icp = self.env['ir.config_parameter'].sudo()
        for campo, (clave, tipo, defecto) in PARAMETROS.items():
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
        icp = self.env['ir.config_parameter'].sudo()
        if self.ops_informe_hora and not self._hora_valida(self.ops_informe_hora):
            raise UserError(_('La hora del informe tiene que ser HH:MM (por ejemplo 17:00).'))
        if self.prep_horario_alarma and not self._horario_valido(self.prep_horario_alarma):
            raise UserError(_('El horario de la alarma tiene que ser tramos HH:MM-HH:MM separados por coma, con el '
                              'inicio antes del final (por ejemplo 06:00-10:00,10:15-13:00,14:00-17:00).'))
        for n in ('ops_minutos_sin_leer', 'ops_minutos_inactividad', 'ops_uds_a_dos', 'kpi_dias_falta_repetida',
                  'prep_minutos_alarma'):
            if self[n] < 0:
                raise UserError(_('Los números no pueden ser negativos.'))
        if self.kpi_dias_falta_repetida < 2:
            raise UserError(_('Faltas repetidas: como mínimo 2 días seguidos.'))
        cambios = []
        for campo, (clave, tipo, defecto) in PARAMETROS.items():
            valor = self[campo]
            if tipo == 'bool':
                nuevo = valor and '1' or '0'
            elif tipo == 'int':
                nuevo = str(valor or 0)
            else:
                nuevo = (valor or '').strip()
            actual = icp.get_param(clave)
            if actual is False or actual is None:
                actual = defecto
            if actual != nuevo:
                icp.set_param(clave, nuevo)
                cambios.append(self._fields[campo].string)
        if cambios:
            msg = _('Guardado: %s.') % ', '.join(cambios)
        else:
            msg = _('No había nada que cambiar.')
        # Odoo 13 no tiene notificaciones desde Python: se vuelve a abrir la pantalla con el aviso arriba
        accion = self.env.ref('koroshi_menu.action_koroshi_ajustes').read()[0]
        accion['context'] = {'koroshi_aviso': msg}
        return accion

    @api.model
    def _horario_valido(self, texto):
        """v1.3: 06:00-10:00,10:15-13:00 (cada tramo con el inicio antes del final; 24:00 vale como final)."""
        for tramo in texto.split(','):
            tramo = tramo.strip()
            if not tramo:
                continue
            partes = tramo.split('-')
            if len(partes) != 2:
                return False
            ini, fin = partes[0].strip(), partes[1].strip()
            if not self._hora_valida(ini) or not (self._hora_valida(fin) or fin == '24:00'):
                return False
            a = int(ini[:-3]) * 60 + int(ini[-2:])
            b = int(fin[:-3]) * 60 + int(fin[-2:])
            if a >= b:
                return False
        return True

    @api.model
    def _hora_valida(self, texto):
        partes = (texto or '').strip().split(':')
        if len(partes) != 2 or not partes[0].isdigit() or not partes[1].isdigit():
            return False
        return 0 <= int(partes[0]) <= 23 and 0 <= int(partes[1]) <= 59
