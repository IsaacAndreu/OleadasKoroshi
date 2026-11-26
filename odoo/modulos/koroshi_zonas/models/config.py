# -*- coding: utf-8 -*-
# =============================================================================
# Fase 3: los parametros del reparto, en pantalla (antes, escritos en el codigo de la accion 1883).
# Un registro por compania (la 8). Valores iniciales = los de la v12f: el reparto no cambia.
# Litros por tipo de prenda: la tabla de koroshi_kpi (koroshi.kpi.peso.tipo), una sola para todo.
# =============================================================================
import datetime
import json
import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.koroshi_base import comun

from ..motor import aprender
from ..motor import modelo
from ..motor import volumen

_logger = logging.getLogger(__name__)

COMPANY_ID = comun.COMPANY_ID     # v1.4.0: de koroshi_base
DIAS_RITMO = 21                   # v1.8.0: zonas-dia de las ultimas 3 semanas para proponer el ritmo
PARAM_LITROS_V12F = 'koroshi_zonas.litros_v12f_aplicados'


class KoroshiZonasConfig(models.Model):
    _name = 'koroshi.zonas.config'
    _description = 'KOROSHI Zonas - configuración del reparto'

    name = fields.Char('Nombre', default='Configuración del reparto por zonas', readonly=True)
    company_id = fields.Many2one('res.company', 'Compañía', required=True, default=COMPANY_ID)

    # ---------------- Cron ----------------
    modo_cron = fields.Selection([('sombra', 'Sombra: diagnóstico y comparar con el cron 202 (no parte nada)'),
                                  ('real', 'Real: parte las OUT (el cron 202 tiene que estar desactivado)')],
                                 'Modo del cron', required=True, default='sombra',
                                 help='Sombra: el módulo calcula antes que el cron 202 y luego compara lo que '
                                      'ha hecho el 202 con lo que habría hecho el módulo. Real: el módulo parte.')
    canal = fields.Char('Canal del informe', default='KOROSHI Partir OUT zonas',
                        help='Canal de Conversaciones donde se publica el informe (vacío = no se publica)')
    correo_destinatarios = fields.Char('Correo del día: destinatarios',
                                       help='Separados por comas. El correo de las zonas del día (antes la acción 1868)')

    # ---------------- Equipo y horario ----------------
    personas = fields.Integer('Personas', default=12, help='Total de personas cogiendo')
    zonas = fields.Integer('Zonas', default=5, help='Total de zonas: de lineal + 2 de muelle (MU1, MU2)')
    hora_inicio = fields.Char('Hora de inicio', default='06:00', help="HH:MM o 'AHORA'")
    hora_fin = fields.Char('Hora de fin', default='12:00', help='HH:MM')
    una_ronda = fields.Boolean('Todo en una ronda', default=True,
                               help='Marcado: entran todas las OUT y la hora de fin solo sale en el informe. '
                                    'Sin marcar: solo las que caben antes de la hora de fin (el resto, otra tanda)')
    rendimiento = fields.Float('Rendimiento', default=1.0, help='1.0 = ritmo del 22/10; 1.2 = un 20 % más rápido')
    seg_lectura = fields.Float('Segundos por lectura', default=52.0, help='OUT + hueco + producto. Calibrado el 22/10')
    seg_lineal = fields.Float('Segundos por lineal', default=21.0, help='Por cada lineal que visita cada OUT')

    # ---------------- Mínimos ----------------
    min_uds_pedido = fields.Integer('Mínimo de uds por pedido', default=15,
                                    help='Un pedido con menos uds reservadas no se coge (queda pendiente)')
    min_uds_zonas = fields.Integer('Mínimo de uds para partir por zonas', default=2000,
                                   help='Si entran menos, no se parte nada (picking tradicional)')

    # ---------------- Cajas ----------------
    litros_caja = fields.Float('Litros por caja', default=80.0, digits=(16, 1),
                               help='El único valor de litros por caja: lo usan el reparto, las etiquetas y la '
                                    'medición. Según el MASTER OI 26/27 la caja grande es de ~93 L (fase 5)')
    cierre_min = fields.Float('Caja cerrada desde', default=0.8, digits=(16, 2),
                              help='Fracción de la caja: 0,8 = la última caja llega al 80 %')
    peso_carga = fields.Float('Peso de la carga al cerrar cajas', default=2.0)
    iter_equilibrio = fields.Integer('Vueltas de equilibrio', default=4)
    tiendas_48h = fields.Char('Tiendas de 48 h', help='Números de tienda (K7 = 7) separados por comas. Se marcan '
                                                         'en el informe y, si no cabe todo, entran antes (v1.3.0)')
    # v1.3.0 (auditoria 13/11, fase 5)
    dias_atras = fields.Integer('OUT de días anteriores', default=7,
                                help='También se reparten las OUT abiertas creadas hasta estos días antes (sin '
                                     'agrupación de zona y sin nada leído). 0 = solo las de hoy, como la acción 1883')
    orden_urgencia = fields.Boolean('Si no cabe todo, primero lo urgente', default=True,
                                    help='Sin "Todo en una ronda": entran primero las OUT de días anteriores y las '
                                         'tiendas de 48 h; después, por número de pedido o de tienda (v1.6.0). Sin '
                                         'marcar: solo por ese orden, como la acción 1883')
    # v1.6.0 (19/11/2026): lo pide KOROSHI
    orden_pedido = fields.Boolean('Ordenar por número de pedido', default=True,
                                  help='Las CAJA del carro y de las etiquetas se numeran por número de pedido '
                                       '(S-6665..., el primero que entra es la CAJA 01) y, si no cabe todo, entran '
                                       'antes los pedidos más antiguos. Sin marcar: por número de tienda (K1, K2...), '
                                       'como la acción 1883')
    ver_out = fields.Integer('OUT que se listan en el informe', default=400)

    # v1.9.0: elegir cada dia cuantas zonas de lineal (prueba varias y se queda con la que acaba antes)
    zonas_auto = fields.Boolean('Elegir cada día cuántas zonas', default=False,
                                help='Marcado: antes de partir se calcula el reparto con cada número de zonas de lineal '
                                     'de la lista y se usa el que acaba antes (con menos zonas si acaba casi igual). '
                                     'El muelle (MU1, MU2) se suma. Sin marcar: siempre las zonas de arriba')
    zonas_probar = fields.Char('Zonas de lineal a probar', default='3,4,5',
                               help='Separadas por comas. Sin contar las 2 de muelle')

    # v1.8.0: zonas que aprenden. Ritmo real de las ultimas semanas (lecturas de la PDA); se aplica con un boton.
    ritmo_texto = fields.Text('Ritmo real', compute='_compute_ritmo')
    seg_lectura_prop = fields.Float('Segundos por lectura propuestos', compute='_compute_ritmo')
    seg_lineal_prop = fields.Float('Segundos por lineal propuestos', compute='_compute_ritmo')

    _sql_constraints = [('company_uniq', 'unique(company_id)', 'Ya hay una configuración para esta compañía.')]

    @api.constrains('personas', 'zonas', 'litros_caja', 'cierre_min', 'hora_inicio', 'hora_fin', 'dias_atras')
    def _comprobar(self):
        for r in self:
            if r.personas < 1 or r.zonas < 1:
                raise ValidationError('Personas y zonas tienen que ser al menos 1.')
            if not 0 <= r.dias_atras <= 30:
                raise ValidationError('OUT de días anteriores: de 0 a 30 días.')
            if r.litros_caja <= 0 or not 0 < r.cierre_min <= 1:
                raise ValidationError('Litros por caja > 0 y "caja cerrada desde" entre 0 y 1.')
            for h, puede_ahora in ((r.hora_inicio, True), (r.hora_fin, False)):
                if puede_ahora and h == 'AHORA':
                    continue
                partes = (h or '').split(':')
                if len(partes) != 2 or not partes[0].isdigit() or not partes[1].isdigit():
                    raise ValidationError('Las horas van como HH:MM (inicio también puede ser AHORA): %s' % h)

    def _filas_ritmo(self):
        """v1.8.0: (lecturas, lineales por OUT, segundos-persona, dia, zona) de las zonas de lineal (D1...Dn) de los
        repartos medidos del todo en los ultimos DIAS_RITMO dias."""
        desde = comun.hoy_local() - datetime.timedelta(days=DIAS_RITMO)
        filas = []
        for ej in self.env['koroshi.zonas.ejecucion'].sudo().search([
                ('company_id', '=', self.company_id.id), ('fecha', '>=', desde), ('medicion', '=', 'medida'),
                ('ritmo_zonas', '!=', False), ('modo', 'in', ('real', 'historico'))], order='fecha'):
            for zona, t in sorted(json.loads(ej.ritmo_zonas).items()):
                if zona[:1] == 'D' and zona[1:].isdigit() and t.get('lecturas') and t.get('seg_persona'):
                    filas.append((t['lecturas'], t['lineales_out'], t['seg_persona'], ej.fecha, zona))
        return filas

    def _compute_ritmo(self):
        for r in self:
            filas = r._filas_ritmo()
            prop = aprender.proponer([f[:3] for f in filas], r.seg_lectura, r.seg_lineal)
            r.seg_lectura_prop = prop and prop['seg_lectura_prop'] or 0.0
            r.seg_lineal_prop = prop and prop['seg_lineal_prop'] or 0.0
            if not prop:
                r.ritmo_texto = ('Aún no hay bastantes días medidos: %d zonas-día de %d necesarias (zonas de lineal de '
                                 'los repartos medidos de las últimas %d días). Cada noche se suma lo de ese día.' % (
                                     len(filas), aprender.MIN_FILAS, DIAS_RITMO))
                continue
            dias = sorted(set(f[3] for f in filas))
            r.ritmo_texto = (
                'Con %d zonas-día (%s a %s), lo que tarda de verdad cada zona se explica así:\n'
                '  %.1f s por lectura + %.1f s por cada lineal que visita cada OUT (error medio %.1f %%).\n'
                'Con el ritmo de ahora (%.0f s y %.0f s) el error medio es del %.1f %%.\n'
                'Propuesto: %d s por lectura y %d s por lineal. Es el mismo peso que lo real, escalado para que el '
                'trabajo total del día sea el de ahora: la hora de fin prevista no cambia, cambian las fronteras '
                '(las zonas anchas pesan más).' % (
                    prop['n'], dias[0].strftime('%d/%m'), dias[-1].strftime('%d/%m'), prop['seg_lectura'],
                    prop['seg_lineal'], prop['error_prop'], r.seg_lectura, r.seg_lineal, prop['error_ahora'],
                    prop['seg_lectura_prop'], prop['seg_lineal_prop']))

    def accion_usar_ritmo(self):
        """v1.8.0: pone el ritmo propuesto en la configuracion (lo decide un jefe; no se cambia solo)."""
        self.ensure_one()
        if not self.seg_lectura_prop or not self.seg_lineal_prop:
            raise ValidationError('Aún no hay ritmo propuesto: faltan días medidos.')
        _logger.info('KOROSHI Zonas: ritmo cambiado por %s: %.0f/%.0f -> %.0f/%.0f s', self.env.user.login,
                     self.seg_lectura, self.seg_lineal, self.seg_lectura_prop, self.seg_lineal_prop)
        self.write({'seg_lectura': self.seg_lectura_prop, 'seg_lineal': self.seg_lineal_prop})
        return True

    @api.model
    def obtener(self):
        """La configuracion de la compania 8; si no hay, la crea con los valores de la v12f."""
        cfg = self.sudo().search([('company_id', '=', COMPANY_ID)], limit=1)
        if not cfg:
            vals = modelo.config_por_defecto()
            vals['company_id'] = COMPANY_ID
            cfg = self.sudo().create(vals)
        return cfg

    def _litros_tipo(self):
        tabla = {}
        for t in self.env['koroshi.kpi.peso.tipo'].sudo().search([]):
            if t.codigo and t.litros:
                tabla[t.codigo] = t.litros
        return tabla

    def cambios_motor(self):
        """Los parametros para el motor (motor.modelo.parametros) con lo que hay en pantalla."""
        self.ensure_one()
        cfg = {}
        for campo in modelo.CAMPOS_CONFIG:
            cfg[campo] = self[campo]
        cfg['tiendas_48h'] = self.tiendas_48h or ''
        return modelo.cambios_desde_config(cfg, self._litros_tipo(), volumen.LITROS_DEFECTO)

    def medidas(self):
        """Caja para la medicion y las etiquetas: el mismo valor que el reparto."""
        self.ensure_one()
        return volumen.Medidas(self.litros_caja, self.cierre_min, self._litros_tipo(), volumen.LITROS_DEFECTO)

    @api.model
    def aplicar_litros_v12f(self):
        """Decision del 11/11/2026 (opcion C): una sola tabla de litros por tipo, la de koroshi_kpi, con los
        valores de la v12f (que salen del MASTER OI 26/27). Solo los 14 tipos de la v12f; el resto de tipos del
        KPI no cambia. Se hace UNA vez (parametro koroshi_zonas.litros_v12f_aplicados): despues la tabla la
        cambian las personas (y la fase 5 propone)."""
        Param = self.env['ir.config_parameter'].sudo()
        if Param.get_param(PARAM_LITROS_V12F):
            return False
        Tipo = self.env['koroshi.kpi.peso.tipo'].sudo()
        cambios = []
        for codigo, litros in sorted(volumen.LITROS_TIPO.items()):
            t = Tipo.search([('codigo', '=', codigo)], limit=1)
            if t:
                if abs((t.litros or 0.0) - litros) > 1e-9:
                    cambios.append('%s %s -> %s' % (codigo, t.litros, litros))
                    t.write({'litros': litros})
            else:
                Tipo.create({'codigo': codigo, 'litros': litros, 'name': codigo})
                cambios.append('%s nuevo %s' % (codigo, litros))
        Param.set_param(PARAM_LITROS_V12F, fields.Datetime.now())
        _logger.info('KOROSHI Zonas: litros por tipo de la v12f en koroshi.kpi.peso.tipo: %s', ', '.join(cambios))
        return True
