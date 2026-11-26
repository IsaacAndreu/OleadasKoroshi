# -*- coding: utf-8 -*-
# =============================================================================
# Estructuras del motor.
#
# Entrada (datos planos, los construye models/lector.py o un volcado JSON):
#   datos = {
#     'ahora': 'AAAA-MM-DD HH:MM:SS',      # hora LOCAL (Europe/Madrid) del lanzamiento
#     'sorter_id': id o None,               # ubicacion SORTER
#     'lotes_existentes': [nombres de agrupaciones 'Z-ddmm-%' que ya hay hoy],
#     'outs': [ {                           # en el orden en que las devuelve Odoo
#         'id', 'name', 'company_id', 'picking_type_code', 'state', 'tipo_pedido',
#         'batch_name' ('' si no tiene), 'location_id', 'partner_name', 'origin',
#         'demanda': uds de los movimientos no hechos ni cancelados,
#         'lineas': [ {                     # stock.move.line en el orden de p.move_line_ids
#             'id', 'move_id', 'qty' (product_uom_qty), 'qty_done',
#             'location_id', 'location_complete_name', 'location_name',
#             'parent_id', 'parent_complete_name',
#             'product_id', 'default_code', 'volume' (m3) } ] } ]
#   }
# =============================================================================
import copy

# Valores de la v12f (accion 1883, lineas 56-90). NO cambiar en la fase 2.
POR_DEFECTO = {
    'MODO': 'REAL',
    'COMPANY_ID': 8,
    'TIPO_PEDIDO': 'PED. TIENDAS',
    'PERSONAS': 12,
    'ZONAS': 5,
    'MIN_UDS_PEDIDO': 15,
    'HORA_INICIO': '06:00',
    'HORA_FIN': '12:00',
    'RENDIMIENTO': 1.0,
    'SEG_LECTURA': 52,
    'SEG_LINEAL': 21,
    'TIENDAS_48H': [7, 24, 29, 37, 39, 40, 41, 43, 47, 49, 56, 57, 59, 60, 62, 63, 68, 76, 78, 79, 81],
    'LITROS_CAJA': 80.0,
    'LITROS_TIPO': {'JA': 8.0, 'XC': 12.0, 'ZB': 14.0, 'SU': 4.0, 'TR': 3.7, 'CL': 3.0, 'PT': 2.2, 'PL': 2.1,
                    'ML': 1.9, 'VS': 1.8, 'FA': 1.6, 'TP': 1.2, 'BL': 0.8, 'ZC': 0.6},
    'LITROS_DEFECTO': 3.0,
    'CIERRE_MIN': 0.8,
    'PESO_CARGA': 2.0,
    'ITER_EQUILIBRIO': 4,
    'UNA_RONDA': True,
    'MIN_UDS_ZONAS': 2000,
    'ZONAS_MUELLE': 'AUTO',
    'VER_OUT': 400,
    'ZONA_OTRAS': 'MU',
    'MUELLE_FIJO': [('1', '/N1-'), ('2', '')],
    'MUELLE_EQUIPO_PROPIO': True,
    'PREFIJO_AGRUPACION': 'TIENDA',
    'ZONA_HORARIA': 'Europe/Madrid',
    # v1.3.0 (auditoria 13/11, fase 5): lo que la 1883 no hacia. COMO_1883 los deja como ella.
    'DIAS_ATRAS': 7,            # OUT abiertas de hasta N dias antes tambien son candidatas (0 = solo las de hoy)
    'ORDEN_URGENCIA': True,     # si no cabe todo: primero las de dias anteriores y las tiendas de 48 h
    'AVISO_HORA_FIN': True,     # con UNA_RONDA, avisar en el informe si se acaba despues de HORA_FIN
    # v1.6.0 (19/11/2026): KOROSHI (Sonia) pide el orden del numero de pedido (S-6665...), no el de la tienda: numera
    # las CAJA (carro de la PDA y etiquetas) y, si no cabe todo, decide que entra antes.
    'ORDEN_PEDIDO': True,
}

# v1.3.0: con estos cambios el motor hace lo mismo que la accion 1883 (tests y calculo en sombra que se compara con
# el cron 202). v1.6.0: la 1883 ordena por tienda.
COMO_1883 = {'DIAS_ATRAS': 0, 'ORDEN_URGENCIA': False, 'AVISO_HORA_FIN': False, 'ORDEN_PEDIDO': False}


def parametros(cambios=None, contexto=None):
    """Parametros de la v12f, con los cambios dados y, encima, los del contexto de lanzamiento
    (personas, hora_inicio, hora_fin, una_ronda, zonas, zonas_muelle) como en las lineas 94-103."""
    p = copy.deepcopy(POR_DEFECTO)
    for k, v in (cambios or {}).items():
        if k not in p:
            raise KeyError('Parametro desconocido: %s' % k)
        p[k] = v
    ctx = contexto or {}
    p['PERSONAS'] = ctx.get('personas') or p['PERSONAS']
    p['HORA_INICIO'] = ctx.get('hora_inicio') or p['HORA_INICIO']
    p['HORA_FIN'] = ctx.get('hora_fin') or p['HORA_FIN']
    if 'una_ronda' in ctx:
        p['UNA_RONDA'] = ctx.get('una_ronda')
    p['ZONAS'] = ctx.get('zonas') or p['ZONAS']
    if 'zonas_muelle' in ctx:
        p['ZONAS_MUELLE'] = ctx.get('zonas_muelle')
    if p['ZONAS'] > p['PERSONAS']:
        p['ZONAS'] = p['PERSONAS']
    # v1.8.0: para probar un ritmo sin tocar la configuracion (diagnostico sin guardar)
    if ctx.get('seg_lectura'):
        p['SEG_LECTURA'] = float(ctx['seg_lectura'])
    if ctx.get('seg_lineal'):
        p['SEG_LINEAL'] = float(ctx['seg_lineal'])
    return p


# Fase 3: lo que se configura en koroshi.zonas.config (campo de Odoo -> parametro del motor). Lo que no esta
# aqui (muelle fijo, prefijos, tipo de pedido...) es estructura del reparto y cambia en la fase 4, no se configura.
CAMPOS_CONFIG = {
    'personas': 'PERSONAS',
    'zonas': 'ZONAS',
    'hora_inicio': 'HORA_INICIO',
    'hora_fin': 'HORA_FIN',
    'min_uds_pedido': 'MIN_UDS_PEDIDO',
    'min_uds_zonas': 'MIN_UDS_ZONAS',
    'rendimiento': 'RENDIMIENTO',
    'seg_lectura': 'SEG_LECTURA',
    'seg_lineal': 'SEG_LINEAL',
    'litros_caja': 'LITROS_CAJA',
    'cierre_min': 'CIERRE_MIN',
    'peso_carga': 'PESO_CARGA',
    'iter_equilibrio': 'ITER_EQUILIBRIO',
    'una_ronda': 'UNA_RONDA',
    'ver_out': 'VER_OUT',
    'dias_atras': 'DIAS_ATRAS',            # v1.3.0
    'orden_urgencia': 'ORDEN_URGENCIA',    # v1.3.0
    'orden_pedido': 'ORDEN_PEDIDO',        # v1.6.0
}


def lista_tiendas(texto):
    """'7, 24,29' -> [7, 24, 29]."""
    res = []
    for t in (texto or '').replace(';', ',').split(','):
        t = t.strip()
        if t.isdigit():
            res.append(int(t))
    return res


def cambios_desde_config(cfg, litros_tipo=None, litros_defecto=None):
    """cfg: dict con los campos de koroshi.zonas.config (CAMPOS_CONFIG y 'tiendas_48h' como texto).
    litros_tipo: {tipo: litros} de koroshi.kpi.peso.tipo. Devuelve los cambios para parametros()."""
    cambios = {}
    for campo, clave in CAMPOS_CONFIG.items():
        if campo in cfg and cfg[campo] is not None:
            v = cfg[campo]
            if isinstance(POR_DEFECTO[clave], float):
                v = float(v)
            cambios[clave] = v
    if 'tiendas_48h' in cfg:
        cambios['TIENDAS_48H'] = lista_tiendas(cfg['tiendas_48h'])
    if litros_tipo is not None:
        cambios['LITROS_TIPO'] = dict(litros_tipo)
    if litros_defecto is not None:
        cambios['LITROS_DEFECTO'] = float(litros_defecto)
    return cambios


def config_por_defecto():
    """Los valores de la v12f como campos de koroshi.zonas.config (para crear el registro)."""
    cfg = {}
    for campo, clave in CAMPOS_CONFIG.items():
        cfg[campo] = POR_DEFECTO[clave]
    cfg['tiendas_48h'] = ', '.join([str(x) for x in POR_DEFECTO['TIENDAS_48H']])
    return cfg


class Reparto(object):
    """Resultado de un reparto. Lo que necesita el escritor para partir y lo que se guarda."""

    def __init__(self):
        self.estado = ''            # 'vacio' | 'pocas_uds' | 'listo'
        self.modo = ''
        self.prefijo = ''
        self.orden_zonas = []
        self.zona_fin = {}          # ml.id -> zona que la coge
        self.plan = []              # [(out_id, {zona: [cajas, uds, litros, cerrada]}, principal, sin_res, caja)]
        self.pers = {}              # zona -> personas
        self.seg_z = {}             # zona -> segundos (de su equipo)
        self.fin = 0.0              # segundos de la zona mas larga
        self.ini_min = 0
        self.lineas = []            # texto del informe, linea a linea
        self.saltadas = []
        self.no_entran = []
        self.pasa_hora_fin = 0      # v1.3.0: minutos despues de la hora de fin (solo con UNA_RONDA)

    def cajas_zona(self):
        res = {}
        for out_id, por_z, principal, sin_res, caja in self.plan:
            for zn in por_z:
                res[(out_id, zn)] = por_z[zn][0]
        return res
