# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI KPI: una ficha por dia y metodo (dia completo, tradicional, zonas, oleada) con lo que
# se saca de Odoo (uds, SKU, cajas, volumen, peso estimado, metros, horas y personas estimadas
# por las cajas cerradas) y lo que se apunta a mano (personas y horas de cada fase; si se
# apunta, manda sobre lo estimado). Con eso, los segundos por prenda de picking, packing/U y
# expedicion, y dentro del picking cuanto es andar y cuanto leer. Solo escribe en sus tablas.
# =============================================================================
import datetime
import logging
import re

import pytz

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

COMPANY_ID = 8                  # EFFECTIVE LOGISTICS, S.L.
TZ = 'Europe/Madrid'
RE_HUECO = re.compile(r'\bL(\d+) P(\d+)\b')
RE_TIPO = re.compile(r'^\d{4}([A-Z]{2})')

# Plano simplificado de la nave (el mismo de las paginas de recorridos): metros
# Tipo (letras 5 y 6 de la referencia) -> (que es segun koroshishop.com, gramos ESTIMADOS, litros medios en Odoo)
# La web no da pesos reales (0 g o 300 g fijos): pesar 10 prendas de cada tipo y corregir en la tabla de Odoo.
TIPOS = {
    'JA': ('Chaqueta / cazadora / abrigo', 800, 8.4),
    'TR': ('Jersey / punto', 400, 3.6),
    'PT': ('Pantalón / vaquero', 450, 2.5),
    'ML': ('Camiseta manga larga', 200, 1.5),
    'MC': ('Camiseta manga corta', 160, 1.2),
    'MS': ('Camiseta sin mangas', 130, 1.0),
    'SU': ('Sudadera', 500, 4.6),
    'CL': ('Camisa / sobrecamisa', 250, 3.3),
    'CC': ('Camisa niño', 150, 1.5),
    'BL': ('Blusa / camisa mujer', 180, 0.9),
    'TP': ('Top', 130, 1.5),
    'PL': ('Polo manga larga', 280, 2.0),
    'PC': ('Polo manga corta', 220, 1.5),
    'VS': ('Vestido / mono', 300, 1.9),
    'FA': ('Falda', 250, 1.6),
    'PS': ('Pantalón corto / bermuda', 250, 1.5),
    'WA': ('Bañador', 180, 1.0),
    'UN': ('Ropa interior', 100, 0.8),
    'ZN': ('Pijama', 350, 2.5),
    'XC': ('Calzado (par, con caja)', 900, 11.9),
    'ZT': ('Calcetines / leotardos', 80, 0.5),
    'ZC': ('Cinturón', 150, 0.8),
    'ZB': ('Bolso', 500, 14.5),
    'ZA': ('Mochila', 600, 10.0),
    'HA': ('Gorro / gorra', 100, 0.8),
    'HS': ('Bufanda / gorro y bufanda', 150, 1.0),
    'SG': ('Gafas de sol', 50, 0.3),
    'BI': ('Bisutería', 30, 0.1),
    'TS': ('Conjunto niña', 250, 1.5),
    'SM': ('Conjunto niño', 250, 1.5),
    'ZF': ('Pañuelo', 60, 0.2),
}

BASE = (26.0, 30.0)             # salida y vuelta (expediciones / SORTER)
CRUCES = (7.75, 30.0, 44.25)    # pasillos transversales


def _x(lineal):
    return 30 + 2 * (lineal // 2) - 0.5


def _y(pos):
    if pos <= 17:
        if pos == 0:
            return 29.3
        if pos <= 3:
            return 2 + (pos - 0.5) * 1.5
        return 9 + (pos - 3.5) * (20.0 / 14)
    pos = min(pos, 36)
    if pos <= 24:
        return 31 + (pos - 17.5) * (12.0 / 7)
    return 45.5 + (pos - 24.5) * (12.5 / 12)


def metros_ruta(huecos, desde_base=True):
    """Metros de un recorrido: sale de BASE, pasa por los huecos (lineal, posicion) en orden de
    pasillo y posicion, y vuelve. Cambiar de pasillo obliga a ir por el transversal mas corto.
    desde_base=False (zonas: el operario se queda en su zona): solo del primer hueco al ultimo."""
    puntos = sorted(set(huecos), key=lambda h: (h[0] // 2, h[1], h[0]))
    if not puntos:
        return 0.0
    if not desde_base:
        x, y = _x(puntos[0][0]), _y(puntos[0][1])
    else:
        x, y = BASE
        puntos = puntos + [None]
    d = 0.0
    for punto in puntos:
        tx, ty = BASE if punto is None else (_x(punto[0]), _y(punto[1]))
        if abs(tx - x) < 0.01:
            d += abs(ty - y)
        else:
            d += min([abs(y - c) + abs(ty - c) for c in CRUCES]) + abs(tx - x)
        x, y = tx, ty
    return d


def horas_persona(marcas):
    """marcas: [(datetime local, quien)]. Cuarto de hora a cuarto de hora, cuantos 'quien' distintos
    cierran caja; los huecos de hasta 30 min entre cuartos con actividad cuentan como trabajo (se sigue
    cogiendo aunque no se cierre caja). Devuelve (horas-persona, maximo a la vez)."""
    cuartos = {}
    for dt, quien in marcas:
        k = dt.toordinal() * 96 + (dt.hour * 60 + dt.minute) // 15
        cuartos.setdefault(k, set()).add(quien)
    hp = 0.0
    maximo = 0
    anterior = None
    for k in sorted(cuartos):
        n = len(cuartos[k])
        hp += n * 0.25
        maximo = max(maximo, n)
        if anterior is not None and 1 < k - anterior <= 3:
            hp += min(n, len(cuartos[anterior])) * 0.25 * (k - anterior - 1)
        anterior = k
    return hp, maximo


def tipo_producto(producto):
    m = RE_TIPO.match(producto.default_code or producto.name or '')
    return m and m.group(1) or ''


def metodo_de(picking):
    lote = picking.batch_id.name or ''
    if lote.startswith('Z-'):
        return 'zonas'
    if lote.startswith('B-KOR'):
        return 'oleada'
    return 'tradicional'


class KoroshiKpiPesoTipo(models.Model):
    _name = 'koroshi.kpi.peso.tipo'
    _description = 'KOROSHI KPI - peso y litros por tipo de prenda'
    _order = 'codigo'

    codigo = fields.Char('Tipo', required=True, help='Letras 5 y 6 de la referencia: 2421JA14-... = JA')
    name = fields.Char('Descripción')
    gramos = fields.Float('Peso por prenda (g)', help='Estimado: pesar 10 prendas del tipo y poner la media')
    litros = fields.Float('Litros por prenda', help='Solo se usa si el producto no tiene volumen en Odoo')
    estimado = fields.Boolean('Estimado', default=True, help='Desmarcar cuando se haya pesado de verdad')

    _sql_constraints = [('codigo_uniq', 'unique(codigo)', 'Ya hay una fila con ese tipo.')]


class KoroshiKpiDia(models.Model):
    _name = 'koroshi.kpi.dia'
    _description = 'KOROSHI KPI - dia y metodo'
    _order = 'fecha desc, metodo'

    fecha = fields.Date('Día', required=True, default=fields.Date.context_today)
    name = fields.Char('Nombre', compute='_compute_name', store=True)
    metodo = fields.Selection([('mixto', 'Día completo (todo)'), ('tradicional', 'Tradicional (1 OUT por pedido)'),
                               ('zonas', 'Zonas (Z-)'), ('oleada', 'Oleada + U (B-KOR)')], string='Método',
                              required=True, default='mixto',
                              help='Qué OUT cuenta la ficha: Zonas = agrupaciones Z-, Oleada = B-KOR, '
                                   'Tradicional = el resto; Día completo = todas')
    tipo_pedido = fields.Char('Tipo de pedido', default='PED. TIENDAS')
    notas = fields.Text('Notas')

    # ---------------- A mano: personas y horas (horas por persona). A 0 = se usa lo estimado ----------------
    pick_personas = fields.Integer('Personas picking')
    pick_horas = fields.Float('Horas picking (por persona)')
    pack_personas = fields.Integer('Personas packing / U')
    pack_horas = fields.Float('Horas packing / U (por persona)')
    exp_personas = fields.Integer('Personas expedición')
    exp_horas = fields.Float('Horas expedición (por persona)')
    velocidad = fields.Float('Velocidad andando (m/s)', default=1.0,
                             help='Con carro, contando paradas: 1 m/s = 3,6 km/h')

    # ---------------- De Odoo (boton Recalcular y cada noche) ----------------
    uds = fields.Float('Uds totales', readonly=True)
    lineas = fields.Integer('Líneas', readonly=True)
    skus = fields.Integer('SKU distintos', readonly=True)
    pedidos = fields.Integer('Pedidos', readonly=True)
    outs = fields.Integer('OUT', readonly=True)
    cajas = fields.Integer('Cajas (matrículas)', readonly=True)
    volumen_total = fields.Float('Volumen total (m³)', readonly=True, digits=(16, 3))
    uds_volumen_estimado = fields.Float('Uds con volumen estimado por tipo', readonly=True)
    peso_total = fields.Float('Peso total (kg)', readonly=True, digits=(16, 1))
    metros_total = fields.Float('Metros recorridos', readonly=True, digits=(16, 0))
    recorridos = fields.Integer('Recorridos (OUT/INT con huecos)', readonly=True)
    primera_caja = fields.Datetime('Primera caja', readonly=True)
    ultima_caja = fields.Datetime('Última caja', readonly=True)
    horas_reloj = fields.Float('Horas de reloj (1ª a última caja)', readonly=True)
    pick_hp_auto = fields.Float('Horas-persona picking (estimadas)', readonly=True,
                                help='Por las cajas cerradas cada cuarto de hora: cuántas OUT (o zonas) cierran caja a la vez')
    pick_personas_auto = fields.Integer('Personas picking (estimadas, máx. a la vez)', readonly=True)
    pack_hp_auto = fields.Float('Horas-persona U (estimadas)', readonly=True,
                                help='Oleada: horas del puesto de U leyendo y cerrando cajas (1 persona)')
    recalculado = fields.Datetime('Recalculado el', readonly=True)

    # ---------------- KPI (se recalculan solos al cambiar lo de arriba) ----------------
    horas_estimadas = fields.Boolean('Horas estimadas', compute='_compute_kpi', store=True,
                                     help='Alguna fase usa las horas estimadas por las cajas porque no se han apuntado')
    profundidad_sku = fields.Float('Profundidad por SKU (uds/SKU)', compute='_compute_kpi', store=True,
                                   group_operator='avg', digits=(16, 2))
    uds_caja = fields.Float('Uds por caja', compute='_compute_kpi', store=True, group_operator='avg', digits=(16, 1))
    peso_ud = fields.Float('Peso medio por ud (g)', compute='_compute_kpi', store=True, group_operator='avg', digits=(16, 0))
    volumen_ud = fields.Float('Volumen por ud (m³/ud)', compute='_compute_kpi', store=True, group_operator='avg',
                              digits=(16, 5))
    metros_ud = fields.Float('Metros por ud', compute='_compute_kpi', store=True, group_operator='avg', digits=(16, 2))
    hp_picking = fields.Float('Horas-persona picking', compute='_compute_kpi', store=True)
    hp_packing = fields.Float('Horas-persona packing / U', compute='_compute_kpi', store=True)
    hp_expedicion = fields.Float('Horas-persona expedición', compute='_compute_kpi', store=True)
    hp_total = fields.Float('Horas totales', compute='_compute_kpi', store=True)
    personas_total = fields.Integer('Personas (suma de fases)', compute='_compute_kpi', store=True,
                                    help='Si una persona hace dos fases cuenta dos veces')
    h_andando = fields.Float('Horas andando (picking)', compute='_compute_kpi', store=True)
    h_leyendo = fields.Float('Horas leyendo/cogiendo (picking)', compute='_compute_kpi', store=True)
    s_ud_picking = fields.Float('s/ud picking', compute='_compute_kpi', store=True, group_operator='avg', digits=(16, 1))
    s_ud_andando = fields.Float('s/ud andando', compute='_compute_kpi', store=True, group_operator='avg', digits=(16, 1))
    s_ud_leyendo = fields.Float('s/ud leyendo', compute='_compute_kpi', store=True, group_operator='avg', digits=(16, 1))
    s_ud_packing = fields.Float('s/ud packing / U', compute='_compute_kpi', store=True, group_operator='avg',
                                digits=(16, 1))
    s_ud_expedicion = fields.Float('s/ud expedición', compute='_compute_kpi', store=True, group_operator='avg',
                                   digits=(16, 1))
    s_ud_total = fields.Float('s/ud TOTAL', compute='_compute_kpi', store=True, group_operator='avg', digits=(16, 1))
    uds_hora_persona = fields.Float('Uds por hora-persona', compute='_compute_kpi', store=True, group_operator='avg',
                                    digits=(16, 0))
    uds_persona = fields.Float('Uds por persona', compute='_compute_kpi', store=True, group_operator='avg',
                               digits=(16, 0))

    _sql_constraints = [('fecha_uniq', 'unique(fecha, metodo)', 'Ya hay una ficha para ese día y método.')]

    @api.depends('fecha', 'metodo')
    def _compute_name(self):
        etiqueta = dict(self._fields['metodo'].selection)
        for r in self:
            r.name = r.fecha and '%s · %s' % (r.fecha.strftime('%d/%m/%Y'), etiqueta.get(r.metodo, '')) or ''

    @api.depends('uds', 'skus', 'cajas', 'peso_total', 'volumen_total', 'metros_total', 'velocidad',
                 'pick_personas', 'pick_horas', 'pack_personas', 'pack_horas', 'exp_personas', 'exp_horas',
                 'pick_hp_auto', 'pick_personas_auto', 'pack_hp_auto')
    def _compute_kpi(self):
        for r in self:
            u = r.uds or 0.0
            r.profundidad_sku = r.skus and u / r.skus or 0.0
            r.uds_caja = r.cajas and u / r.cajas or 0.0
            r.peso_ud = u and r.peso_total * 1000.0 / u or 0.0
            r.volumen_ud = u and r.volumen_total / u or 0.0
            r.metros_ud = u and r.metros_total / u or 0.0
            pick_manual = r.pick_personas * r.pick_horas
            pack_manual = r.pack_personas * r.pack_horas
            r.hp_picking = pick_manual or r.pick_hp_auto
            r.hp_packing = pack_manual or r.pack_hp_auto
            r.hp_expedicion = r.exp_personas * r.exp_horas
            r.horas_estimadas = bool((not pick_manual and r.pick_hp_auto) or (not pack_manual and r.pack_hp_auto))
            r.hp_total = r.hp_picking + r.hp_packing + r.hp_expedicion
            r.personas_total = ((pick_manual and r.pick_personas or r.pick_personas_auto) +
                                (pack_manual and r.pack_personas or (r.pack_hp_auto and 1 or 0)) + r.exp_personas)
            andando = r.velocidad and r.metros_total / r.velocidad / 3600.0 or 0.0
            r.h_andando = min(andando, r.hp_picking)
            r.h_leyendo = max(r.hp_picking - r.h_andando, 0.0)
            r.s_ud_picking = u and r.hp_picking * 3600.0 / u or 0.0
            r.s_ud_andando = u and r.h_andando * 3600.0 / u or 0.0
            r.s_ud_leyendo = u and r.h_leyendo * 3600.0 / u or 0.0
            r.s_ud_packing = u and r.hp_packing * 3600.0 / u or 0.0
            r.s_ud_expedicion = u and r.hp_expedicion * 3600.0 / u or 0.0
            r.s_ud_total = r.s_ud_picking + r.s_ud_packing + r.s_ud_expedicion
            r.uds_hora_persona = r.hp_total and u / r.hp_total or 0.0
            r.uds_persona = r.personas_total and u / r.personas_total or 0.0

    # ---------------- Calculo de lo que sale de Odoo ----------------
    def _rango_utc(self):
        tz = pytz.timezone(TZ)
        ini = tz.localize(datetime.datetime.combine(self.fecha, datetime.time.min))
        ini = ini.astimezone(pytz.utc).replace(tzinfo=None)
        return ini, ini + datetime.timedelta(days=1)

    def _lineas_dia(self):
        ini, fin = self._rango_utc()
        Line = self.env['stock.move.line'].sudo()
        base = [('picking_id.company_id', '=', COMPANY_ID), ('picking_id.picking_type_code', '=', 'outgoing'),
                ('qty_done', '>', 0)]
        if self.tipo_pedido:
            base.append(('picking_id.sale_id.s_order_type_id.name', '=', self.tipo_pedido))
        # Unidades del dia: las de las cajas cerradas ese dia; sin caja, las de las OUT validadas ese dia
        lineas = Line.search(base + [('result_package_id.create_date', '>=', ini),
                                     ('result_package_id.create_date', '<', fin)])
        lineas |= Line.search(base + [('result_package_id', '=', False), ('picking_id.date_done', '>=', ini),
                                      ('picking_id.date_done', '<', fin)])
        return lineas

    def action_recalcular(self):
        Pick = self.env['stock.picking'].sudo()
        Line = self.env['stock.move.line'].sudo()
        tz = pytz.timezone(TZ)
        tipos = {}
        defecto = (300.0, 3.0)
        for t in self.env['koroshi.kpi.peso.tipo'].sudo().search([]):
            tipos[t.codigo] = (t.gramos or defecto[0], t.litros or defecto[1])
        sorter = self.env['stock.location'].sudo().search([('barcode', '=', 'SORTER'),
                                                           ('company_id', '=', COMPANY_ID)], limit=1)
        en_sorter = set(sorter and self.env['stock.location'].sudo().search([('id', 'child_of', sorter.id)]).ids or [])
        for r in self:
            ini, fin = r._rango_utc()
            uds = vol = peso = vol_est = 0.0
            n_lineas = 0
            productos = set()
            pedidos = set()
            outs = set()
            cajas = {}          # caja -> (hora, quien la cierra)
            huecos = {}         # picking -> [(lineal, posicion)] para los metros
            for ml in r._lineas_dia():
                pk = ml.picking_id
                met = metodo_de(pk)
                if r.metodo != 'mixto' and met != r.metodo:
                    continue
                q = ml.qty_done
                p = ml.product_id
                g, l = tipos.get(tipo_producto(p), defecto)
                n_lineas += 1
                uds += q
                peso += g * q / 1000.0
                if p.volume > 0:
                    vol += p.volume * q
                else:
                    vol += l / 1000.0 * q
                    vol_est += q
                productos.add(p.id)
                pedidos.add(pk.origin or pk.name)
                outs.add(pk.id)
                if ml.result_package_id:
                    if met == 'zonas':
                        quien = ('Z', pk.batch_id.name)
                    elif met == 'oleada':
                        quien = ('U', 0)
                    else:
                        quien = ('OUT', pk.id)
                    cajas[ml.result_package_id.id] = (ml.result_package_id.create_date, quien)
                if ml.location_id.id not in en_sorter:      # las OUT de oleada salen del SORTER: se anda en los INT
                    h = RE_HUECO.search(ml.location_id.complete_name or '')
                    if h:
                        huecos.setdefault(pk.id, []).append((int(h.group(1)), int(h.group(2))))
            # Oleada: lo que se anda son los INT al SORTER cogidos ese dia
            if sorter and r.metodo in ('mixto', 'oleada'):
                for ml in Line.search([('picking_id.company_id', '=', COMPANY_ID),
                                       ('picking_id.picking_type_code', '=', 'internal'),
                                       ('picking_id.location_dest_id', '=', sorter.id),
                                       ('qty_done', '>', 0), ('write_date', '>=', ini), ('write_date', '<', fin)]):
                    h = RE_HUECO.search(ml.location_id.complete_name or '')
                    if h:
                        huecos.setdefault(ml.picking_id.id, []).append((int(h.group(1)), int(h.group(2))))
            metros = 0.0
            for pid, lista in huecos.items():
                lote = Pick.browse(pid).batch_id.name or ''
                metros += metros_ruta(lista, desde_base=not lote.startswith('Z-'))
            marcas_pick = []
            marcas_u = []
            for hora, quien in cajas.values():
                local = pytz.utc.localize(hora).astimezone(tz)
                (marcas_u if quien[0] == 'U' else marcas_pick).append((local, quien))
            pick_hp, pick_max = horas_persona(marcas_pick)
            u_hp = horas_persona(marcas_u)[0]
            horas = [c[0] for c in cajas.values()]
            r.write({
                'uds': uds, 'lineas': n_lineas, 'skus': len(productos), 'pedidos': len(pedidos), 'outs': len(outs),
                'cajas': len(cajas), 'volumen_total': vol, 'uds_volumen_estimado': vol_est, 'peso_total': peso,
                'metros_total': metros, 'recorridos': len(huecos),
                'primera_caja': horas and min(horas) or False, 'ultima_caja': horas and max(horas) or False,
                'horas_reloj': horas and (max(horas) - min(horas)).total_seconds() / 3600.0 or 0.0,
                'pick_hp_auto': pick_hp, 'pick_personas_auto': pick_max, 'pack_hp_auto': u_hp,
                'recalculado': fields.Datetime.now(),
            })
        # v1.3: el boton Recalcular de la ficha del dia completo saca tambien las faltas de ese dia
        for d in set(self.filtered(lambda x: x.metodo == 'mixto').mapped('fecha')):
            self.env['koroshi.kpi.falta'].recalcular_dia(d)
        return True

    @api.model
    def crear_fichas(self, dia):
        """Crea la ficha del dia completo y una por cada metodo que haya tenido actividad ese dia."""
        completo = self.search([('fecha', '=', dia), ('metodo', '=', 'mixto')], limit=1) or \
            self.create({'fecha': dia, 'metodo': 'mixto'})
        metodos = set([metodo_de(ml.picking_id) for ml in completo._lineas_dia()])
        for m in metodos:
            if not self.search([('fecha', '=', dia), ('metodo', '=', m)], limit=1):
                self.create({'fecha': dia, 'metodo': m})
        return self.search([('fecha', '=', dia)])

    @api.model
    def recalcular_todo(self):
        # Al instalar o actualizar el modulo: tabla de tipos al dia (solo filas aun 'estimadas') y fichas por
        # metodo de todos los dias que ya tienen ficha, recalculadas. Si algo falla, se apunta en el registro y
        # la actualizacion sigue (no se queda el modulo a medias).
        Tipo = self.env['koroshi.kpi.peso.tipo'].sudo()
        for codigo, (nombre, gramos, litros) in TIPOS.items():
            t = Tipo.search([('codigo', '=', codigo)], limit=1)
            if not t:
                Tipo.create({'codigo': codigo, 'name': nombre, 'gramos': gramos, 'litros': litros})
            elif t.estimado:
                t.write({'name': nombre, 'gramos': gramos, 'litros': litros})
        for d in sorted(set(self.search([]).mapped('fecha'))):
            try:
                with self.env.cr.savepoint():
                    self.crear_fichas(d).action_recalcular()        # v1.3: tambien las faltas del dia
            except Exception:
                _logger.exception('KOROSHI KPI: no se ha podido recalcular el %s', d)
        return True

    @api.model
    def cron_recalcular(self):
        # Cada noche: fichas de hoy y ayer (dia completo y cada metodo con actividad), recalculadas
        hoy = datetime.datetime.now(pytz.timezone(TZ)).date()
        for d in (hoy - datetime.timedelta(days=1), hoy):
            self.crear_fichas(d).action_recalcular()
        return True
