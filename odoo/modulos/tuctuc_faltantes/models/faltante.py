# -*- coding: utf-8 -*-
# =============================================================================
# TUCTUC Faltantes - una pieza de una OUT que no esta donde dice Odoo.
# Clon de koroshi_faltantes 1.12.0 para odoo.tuctuc.com (nave de Oriola - Amposta). Cambios (27-28/11/2026):
#   - FALTANTE por almacén (WH-OR/FALTANTE, MODAI/FALTANTE, UBRAN/FALTANTE, fuera del stock: se crean al instalar,
#     data/ubicacion.xml) en tuctuc.almacen.faltantes_id, en vez de una sola FALTANTE de la compañía 8.
#   - Cada operación trabaja con la compañía de la OUT como compañía activa (tuctuc_base.pda.con_compania).
#   - Zona de picking N1 (tuctuc.almacen.zona_picking) en vez de NAVE2; sin agrupaciones Z- (en Oriola no hay).
#   - % de faltante y correo por compañía (relativo.py); puestos a 0 sin usuarios por defecto (parámetro vacío).
#
# Desde la pantalla "Faltante" de la PDA (controllers/main.py):
#   - reubicar():        la linea reservada pasa a otra ubicacion con stock libre y la unidad que falta
#                        va de la ubicacion vieja a FALTANTE.
#   - sin_alternativa(): no esta en ningun sitio: se quita la reserva de esa linea y la unidad que falta
#                        va de la ubicacion vieja a FALTANTE.
# En la oficina (revision diaria):
#   - action_no_encontrado(): de FALTANTE a perdidas de inventario.
#   - Encontrado (wizard/encontrado.py): de FALTANTE a la ubicacion que se elija.
# Ronda de revision (v1.1):
#   - crear_ronda(): una INT normal (tipo Transferencias internas) con una linea por faltante pendiente,
#     de FALTANTE a su ubicacion vieja, ordenada por lineal. Se hace en la PDA con la app de codigo de barras.
#   - sincronizar_rondas() (cron cada 15 min): linea hecha -> Encontrado (en la ubicacion donde se leyo);
#     INT validada "Sin pedido pendiente" -> lo no leido queda cancelado -> No encontrado (a perdidas);
#     "Crear pedido pendiente" -> sigue pendiente en la INT nueva; INT cancelada entera -> vuelve a pendiente.
# v1.7 Ronda en Lecturas (tuctuc_preparacion 3.33): la INT de la ronda se lee en la pantalla nueva. Por linea:
#   leer la prenda = esta; «No esta» / «La ubicacion no existe» = ronda_marcar() (quita la reserva de la linea y
#   apunta el resultado y el operario). Al validar: esta -> Encontrado; no esta -> sigue pendiente (a la
#   RONDAS_PERDIDAS.a ronda sin aparecer, a perdidas); la ubicacion no existe -> estado «Ubicacion no existe»
#   (la oficina decide). Informe «Resultado de la ronda».
# v1.7 Puestos a 0 del picking viejo: importar_puestos_a_cero() pasa a faltantes (tipo «Puesto a 0») lo que se puso
#   a 0 en la app de codigo de barras desde una fecha. Sus uds ya estan en perdidas: la ronda va de perdidas a la
#   ubicacion y solo si se encuentra vuelve al stock; si no, se queda como estaba.
# v1.9 (revision general 23/11, para koroshi_contenedores 1.13):
#   - reubicar() y sin_alternativa() aceptan `cantidad`: solo esa parte de la linea pasa a Faltantes; el resto
#     sigue reservado donde estaba (R1: «Cambiar» 5 -> 4 ya no quita a la OUT las 5). Y `origen`: de donde viene
#     (p. ej. «Desde Contenedores»), en la nota del faltante y en el historial de la OUT.
#   - mejor_destino(): el hueco mas cercano con stock libre suficiente, mirando todos, no solo los 5 primeros.
#   - sincronizar_rondas(): cada faltante en su savepoint, con log; uno malo ya no para el cron (R13).
#   - antes_de_archivar(): un contenedor que se archiva no deja faltantes pendientes con vuelta a el (R4).
#
# Como se cambia la reserva: se escribe location_id en la stock.move.line reservada (sin nada leido).
# Es el write estandar de Odoo 13: quita la reserva de la vieja y reserva en la nueva con strict=True,
# solo de stock libre (no quita nada a otra OUT). Nunca "Forzar disponibilidad" ni stock.quant a mano.
# Los movimientos a/desde FALTANTE son stock.move con su linea hecha (qty_done) y _action_done(),
# como hace Odoo al ajustar cantidades.
# Todo dentro de un savepoint: si algo falla, no se hace nada.
# No anade campos a albaranes, movimientos, lineas, agrupaciones ni tipos de operacion.
# =============================================================================
import logging
import re

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero, html_escape
from odoo.addons.tuctuc_base import comun, pda

_logger = logging.getLogger(__name__)

MAX_ALTERNATIVAS = 5
NOMBRE_PUESTA_A_CERO = 'Cantidad de producto actualizada'   # lo que escribe Odoo al poner a 0 desde la PDA
PREFIJOS_ZONA = ()                                           # agrupaciones que se abren enteras (en Oriola, ninguna)
ORIGEN_RONDA = 'RONDA FALTANTES'                             # origin de las INT de ronda (v1.7: Lecturas las reconoce)
RONDAS_PERDIDAS = 2                                          # v1.7: «No esta» en esta ronda -> a perdidas
PARAM_CERO_DESDE = 'tuctuc_faltantes.puestos_a_cero_desde'  # v1.7: desde que dia se pasan los puestos a 0
PARAM_CERO_USUARIOS = 'tuctuc_faltantes.puestos_a_cero_usuarios'   # v1.7: logins de las PDA (separados por comas)
CERO_DESDE_DEFECTO = '2026-11-28'
CERO_USUARIOS_DEFECTO = ''                                   # TUCTUC: vacío = no se importa nada
# Solo se coge de la zona de picking del almacén (tuctuc.almacen.zona_picking: N1 en Oriola) y dentro, solo de un
# hueco de lineal («06298 - L75 P38 C2»), con o sin contenedor KO_/TT_/UB_ dentro. Nunca de la raíz del stock ni de
# lo que no es un hueco (FALTAS_001, SORTER...).

RE_LINEAL = re.compile(r'\bL(\d+)\b')
RE_HUECO = re.compile(r'((?:L|MU-)\d+\s+P\d+\s+C\d+)')   # v1.6.1: tambien los huecos del muelle (MU-..)


def lineal_de(ubicacion):
    """Numero de lineal (L46 -> 46) de una ubicacion o de su hueco; None si no tiene."""
    m = RE_LINEAL.search(ubicacion.complete_name or '')
    return int(m.group(1)) if m else None


def nombre_corto(ubicacion):
    """'WH-OR/Stock/N1/06298 - L75 P38 C2/KO_300726_755' -> 'L75 P38 C2 · KO_300726_755'."""
    if not ubicacion:
        return ''
    completo = ubicacion.complete_name or ubicacion.name or ''
    m = RE_HUECO.search(completo)
    if m:
        hueco = m.group(1)
        return hueco if hueco in (ubicacion.name or '') else '%s · %s' % (hueco, ubicacion.name)
    return comun.nombre_corto(completo)   # sin el almacén ni Stock/STOCK (UBRAN lo escribe en mayúsculas)


class TuctucFaltante(models.Model):
    _name = 'tuctuc.faltante'
    _description = 'TUCTUC Faltante'
    _order = 'fecha desc, id desc'

    name = fields.Char('Faltante', compute='_compute_name', store=True)
    employee_id = fields.Many2one('hr.employee', 'Operario', index=True, ondelete='set null',
                                  help='Operario de la tarjeta o de la tarea abierta de esa OUT (tuctuc_operarios)')
    user_id = fields.Many2one('res.users', 'Usuario', required=True, default=lambda self: self.env.user,
                              ondelete='restrict')
    # v1.7: sin OUT en los puestos a 0 del picking viejo (no se sabe de que OUT eran)
    picking_id = fields.Many2one('stock.picking', 'OUT', index=True, ondelete='restrict')
    batch_id = fields.Many2one('stock.picking.batch', 'Agrupacion', related='picking_id.batch_id')
    product_id = fields.Many2one('product.product', 'Articulo', required=True, index=True, ondelete='restrict')
    cantidad = fields.Float('Uds de la linea', digits='Product Unit of Measure',
                            help='Uds de la linea de la OUT que no estaban')
    cantidad_faltant = fields.Float('Uds a FALTANTE', digits='Product Unit of Measure',
                                    help='Uds que se han movido a FALTANTE. Puede ser menos que la linea si en '
                                         'la ubicacion vieja ya no quedaba stock en Odoo.')
    ubicacion_vieja_id = fields.Many2one('stock.location', 'Ubicacion vieja', required=True, ondelete='restrict')
    ubicacion_nueva_id = fields.Many2one('stock.location', 'Ubicacion nueva', ondelete='restrict')
    linea_id = fields.Integer('Linea de la OUT', help='Id de la stock.move.line (solo informativo)')
    tipo = fields.Selection([
        ('reubicado', 'Reubicado'),
        ('sin_alternativa', 'Sin alternativa'),
        ('puesto_a_cero', 'Puesto a 0 (picking viejo)'),   # v1.7
    ], 'Tipo', required=True)
    estado = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('encontrado', 'Encontrado'),
        ('no_encontrado', 'No encontrado'),
        ('no_existe', 'Ubicacion no existe'),   # v1.7: marcado en la ronda; lo decide la oficina
    ], 'Estado', default='pendiente', required=True, index=True)
    fecha = fields.Datetime('Fecha', required=True, default=fields.Datetime.now, index=True)
    dia = fields.Date('Dia', compute='_compute_dia', store=True, index=True)
    move_faltant_id = fields.Many2one('stock.move', 'Movimiento a FALTANTE', ondelete='set null', readonly=True)
    move_revision_id = fields.Many2one('stock.move', 'Movimiento de la revision', ondelete='set null',
                                       readonly=True)
    ubicacion_revision_id = fields.Many2one('stock.location', 'Devuelto a', ondelete='set null', readonly=True)
    fecha_revision = fields.Datetime('Fecha revision', readonly=True)
    revisado_por = fields.Many2one('res.users', 'Revisado por', readonly=True, ondelete='set null')
    nota = fields.Char('Nota')
    ronda_picking_id = fields.Many2one('stock.picking', 'Ronda (INT)', index=True, ondelete='set null',
                                       readonly=True, help='INT de revision donde esta este faltante')
    ronda_move_id = fields.Many2one('stock.move', 'Movimiento de la ronda', index=True, ondelete='set null',
                                    readonly=True)
    rondas = fields.Integer('Rondas', readonly=True, help='Veces que ha salido en una ronda de revision')
    en_ronda = fields.Boolean('En ronda abierta', compute='_compute_en_ronda', search='_search_en_ronda')
    # v1.7: lo marcado en la ultima ronda (Lecturas) y quien
    ronda_resultado = fields.Selection([
        ('esta', 'Esta'),
        ('no_esta', 'No esta'),
        ('no_existe', 'La ubicacion no existe'),
    ], 'Resultado de la ronda', readonly=True)
    ronda_operario_id = fields.Many2one('hr.employee', 'Operario de la ronda', ondelete='set null', readonly=True)
    ronda_fecha = fields.Datetime('Hora de la ronda', readonly=True)
    move_cero_id = fields.Many2one('stock.move', 'Movimiento puesto a 0', index=True, ondelete='set null',
                                   readonly=True, help='v1.7: el movimiento a perdidas del picking viejo')
    company_id = fields.Many2one('res.company', 'Empresa', required=True,
                                 default=lambda self: self.env.company)

    # ------------------------------------------------------------------ computes
    @api.depends('picking_id', 'product_id')
    def _compute_name(self):
        for f in self:
            f.name = '%s - %s' % (f.picking_id.name or 'Puesto a 0', f.product_id.display_name or '')

    @api.depends('fecha')
    def _compute_dia(self):
        for f in self:
            f.dia = comun.dia_local(f.fecha) or False

    # ------------------------------------------------------------------ ubicaciones
    @api.model
    def _ubicacion_faltant(self, picking=None, ubicacion=None):
        """TUCTUC: la FALTANTE del almacén de la OUT (o de la ubicación), de tuctuc.almacen.faltantes_id."""
        Alm = self.env['tuctuc.almacen']
        alm = Alm.de_picking(picking) if picking else Alm.de_ubicacion(ubicacion) if ubicacion else Alm
        loc = alm.faltantes_id
        if not loc:
            raise UserError('El almacen %s no tiene ubicacion de faltantes: ponla en Inventario > Configuracion > '
                            'TUCTUC PDA: almacenes.' % (alm.codigo or (picking or ubicacion).display_name))
        return self.env['stock.location'].browse(loc.id)

    @api.model
    def _crear_ubicaciones_faltante(self):
        """Al instalar (data/ubicacion.xml, noupdate; decisión de Isaac del 28/11/2026): una ubicación FALTANTE por
        almacén de la PDA, FUERA del stock (<almacén>/FALTANTE, de su compañía), para que ninguna OUT reserve las uds
        que no se encuentran. Si ya hay una FALTANTE fuera del stock, se usa esa. Una ubicación de faltantes dentro
        del stock (WH-OR/Stock/N1/FALTAS_001, la pone tuctuc_base al instalar) se cambia por la nueva; FALTAS_001 no se
        toca."""
        Loc = self.env['stock.location'].sudo()
        for alm in self.env['tuctuc.almacen'].sudo().search([]):
            wh = alm.warehouse_id
            stock = wh.lot_stock_id
            actual = alm.faltantes_id
            if actual and not (stock.parent_path and (actual.parent_path or '').startswith(stock.parent_path)):
                continue   # ya tiene una fuera del stock
            loc = Loc.search([('location_id', '=', wh.view_location_id.id), ('name', '=', 'FALTANTE'),
                              ('usage', '=', 'internal')], limit=1)
            if not loc:
                loc = Loc.create({'name': 'FALTANTE', 'usage': 'internal', 'location_id': wh.view_location_id.id,
                                  'company_id': wh.company_id.id})
            alm.faltantes_id = loc
            _logger.info('TUCTUC Faltantes: %s usa %s', wh.code, loc.complete_name)
        return True

    def _faltant_de(self):
        """La FALTANTE donde estan las uds de este faltante: adonde fue su movimiento o la de su almacen."""
        self.ensure_one()
        return (self.move_faltant_id.location_dest_id or
                self._ubicacion_faltant(self.picking_id or None, self.ubicacion_vieja_id))

    @api.model
    def _raiz_stock(self, picking):
        """Stock donde se reserva (WH-OR/Stock, UBRAN/STOCK...). FALTANTE debe estar fuera."""
        raiz = picking.picking_type_id.warehouse_id.lot_stock_id or picking.location_id
        faltant = self._ubicacion_faltant(picking)
        if faltant.parent_path and raiz.parent_path and faltant.parent_path.startswith(raiz.parent_path):
            raise UserError('La ubicacion FALTANTE esta dentro de %s: las OUT podrian reservar en ella. '
                            'Muevela fuera antes de usar la pantalla.' % raiz.complete_name)
        return raiz

    @api.model
    def _ubicacion_perdidas(self, product, company):
        loc = product.with_context(force_company=company.id).property_stock_inventory
        if not loc:
            raise UserError('El articulo %s no tiene ubicacion de perdidas de inventario' % product.display_name)
        return loc

    def _origen(self):
        """v1.7: donde estan las uds del faltante: FALTANTE o, en un puesto a 0, perdidas de inventario."""
        self.ensure_one()
        if self.tipo == 'puesto_a_cero':
            return self._ubicacion_perdidas(self.product_id, self.company_id)
        return self._faltant_de()

    @api.model
    def _libre_por_ubicacion(self, product, dominio_ubicacion):
        """{ubicacion: uds libres (cantidad - reservado)} solo con libre > 0."""
        quants = self.env['stock.quant'].search(
            [('product_id', '=', product.id), ('quantity', '>', 0)] + dominio_ubicacion)
        libre = {}
        for q in quants:
            libre[q.location_id] = libre.get(q.location_id, 0.0) + q.quantity - q.reserved_quantity
        rounding = product.uom_id.rounding
        return {loc: qty for loc, qty in libre.items() if float_compare(qty, 0, precision_rounding=rounding) > 0}

    @api.model
    def _excluida(self, ubicacion):
        """True si no es de donde se coge para una OUT: fuera de la zona de picking de los almacenes de la PDA (N1)
        o, dentro, fuera de un hueco de lineal (FALTAS_001, SORTER, contenedores sueltos)."""
        completo = ubicacion.complete_name or ''
        partes = [p.strip() for p in completo.split('/')]
        zonas = set(z for z in self.env['tuctuc.almacen'].activos().mapped('zona_picking') if z)
        if not zonas.intersection(partes):
            return True
        return not RE_HUECO.search(completo)

    @api.model
    def _libre_en(self, product, ubicacion):
        """Uds libres justo en esa ubicacion (sin hijas)."""
        quants = self.env['stock.quant'].search([('product_id', '=', product.id),
                                                 ('location_id', '=', ubicacion.id)])
        return sum(q.quantity - q.reserved_quantity for q in quants)

    @api.model
    def _alternativas_ordenadas(self, product, ubicacion_vieja, raiz):
        """[(ubicacion, uds libres)] de TODAS las ubicaciones con stock libre del articulo dentro de raiz, sin la
        vieja, ordenadas por el lineal mas cercano al de la vieja y despues por mas uds libres."""
        libre = self._libre_por_ubicacion(product, [('location_id', 'child_of', raiz.id),
                                                    ('location_id.usage', '=', 'internal'),
                                                    ('location_id', '!=', ubicacion_vieja.id)])
        libre = {loc: qty for loc, qty in libre.items() if not self._excluida(loc)}   # v1.6
        lv = lineal_de(ubicacion_vieja)

        def orden(item):
            loc, qty = item
            lin = lineal_de(loc)
            distancia = abs(lin - lv) if (lin is not None and lv is not None) else 9999
            return (distancia, -qty, loc.complete_name or '')

        return sorted(libre.items(), key=orden)

    @api.model
    def alternativas(self, product, ubicacion_vieja, raiz):
        """Hasta MAX_ALTERNATIVAS ubicaciones con stock libre del articulo dentro de raiz, sin la vieja,
        ordenadas por el lineal mas cercano al de la vieja y despues por mas uds libres."""
        todas = self._alternativas_ordenadas(product, ubicacion_vieja, raiz)
        res = []
        for loc, qty in todas[:MAX_ALTERNATIVAS]:
            res.append({'id': loc.id, 'nombre': nombre_corto(loc), 'completo': loc.complete_name,
                        'libre': qty, 'lineal': lineal_de(loc)})
        return {'lista': res, 'total': len(todas)}

    @api.model
    def mejor_destino(self, product, ubicacion_vieja, raiz, necesario):
        """v1.9: la ubicacion mas cercana que tiene libres al menos `necesario` uds (en la unidad del articulo),
        mirando todas y no solo las MAX_ALTERNATIVAS primeras. Vacio si ninguna llega."""
        rounding = product.uom_id.rounding
        for loc, qty in self._alternativas_ordenadas(product, ubicacion_vieja, raiz):
            if float_compare(qty, necesario, precision_rounding=rounding) >= 0:
                return loc
        return self.env['stock.location']

    # ------------------------------------------------------------------ movimientos
    @api.model
    def _mover(self, product, qty, origen, destino, company, nombre, origin=''):
        """Movimiento interno hecho de qty uds (sin reservar: la linea ya va con qty_done)."""
        uom = product.uom_id
        move = self.env['stock.move'].create({
            'name': nombre,
            'origin': origin or nombre,
            'product_id': product.id,
            'product_uom': uom.id,
            'product_uom_qty': qty,
            'location_id': origen.id,
            'location_dest_id': destino.id,
            'company_id': company.id,
            'move_line_ids': [(0, 0, {
                'product_id': product.id,
                'product_uom_id': uom.id,
                'qty_done': qty,
                'location_id': origen.id,
                'location_dest_id': destino.id,
                'company_id': company.id,
            })],
        })
        move._action_done()
        if move.state != 'done':
            raise UserError('No se ha podido hacer el movimiento %s -> %s' % (origen.complete_name,
                                                                              destino.complete_name))
        return move

    # ------------------------------------------------------------------ comprobaciones
    @api.model
    def pendiente_de(self, ml):
        """Uds de la linea (en su unidad) que faltan por leer: reservado - leido (0 si ya esta todo)."""
        return max(ml.product_uom_qty - ml.qty_done, 0.0)

    @api.model
    def lineas_pendientes(self, pickings):
        """Lineas reservadas con algo por leer, en el orden de la app de codigo de barras: por el nombre
        completo de la ubicacion (una pagina por ubicacion) y dentro, por linea."""
        lineas = pickings.mapped('move_line_ids').filtered(
            lambda l: l.state not in ('done', 'cancel') and l.picking_id.state not in ('done', 'cancel') and
            float_compare(l.qty_done, l.product_uom_qty, precision_rounding=l.product_uom_id.rounding) < 0)
        return lineas.sorted(lambda l: (l.location_id.display_name or '', l.id))

    @api.model
    def comprobar_linea(self, ml):
        """La linea se puede tocar: reservada, con algo por leer y la OUT sin validar. Devuelve el motivo si no.
        v1.3: tambien lineas con una parte leida (solo se toca la parte que falta)."""
        if not ml or not ml.exists():
            return 'La linea ya no existe. Vuelve a leer la OUT.'
        if ml.picking_id.state in ('done', 'cancel'):
            return 'La OUT %s ya esta %s.' % (ml.picking_id.name, 'validada' if ml.picking_id.state == 'done'
                                               else 'cancelada')
        rounding = ml.product_uom_id.rounding
        if float_is_zero(ml.product_uom_qty, precision_rounding=rounding):
            return 'Esta linea no tiene nada reservado.'
        if float_compare(ml.qty_done, ml.product_uom_qty, precision_rounding=rounding) >= 0:
            return 'Esta linea ya esta leida entera: no falta nada.'
        if ml.state not in ('assigned', 'partially_available'):
            return 'La linea no esta reservada (estado %s).' % ml.state
        if ml.lot_id or ml.package_id or ml.owner_id:
            return 'La linea tiene lote, paquete o propietario: hazlo en la oficina.'
        return ''

    @api.model
    def _comprobar(self, ml):
        motivo = self.comprobar_linea(ml)
        if motivo:
            raise UserError(motivo)

    # ------------------------------------------------------------------ PDA
    @api.model
    def elegir_destino(self, ml, ubicacion_leida, raiz, necesario=None):
        """Ubicacion concreta (sin hijas con stock) donde reservar: la leida o, si es un hueco, la caja KO
        de dentro con mas stock libre. Error si no llega para lo que falta (necesario, en la unidad del
        articulo; de inicio la linea entera)."""
        product = ml.product_id
        necesario = ml.product_qty if necesario is None else necesario
        if not (ubicacion_leida.parent_path or '').startswith(raiz.parent_path or '-'):
            raise UserError('%s no esta dentro de %s.' % (ubicacion_leida.complete_name, raiz.complete_name))
        if ubicacion_leida.usage != 'internal':
            raise UserError('%s no es una ubicacion interna.' % ubicacion_leida.complete_name)
        if self._excluida(ubicacion_leida):   # v1.6
            raise UserError('De %s no se coge para las OUT: solo de los lineales y del muelle.'
                            % nombre_corto(ubicacion_leida))
        if ubicacion_leida == ml.location_id:
            raise UserError('Es la misma ubicacion donde ya esta reservada. Lee la ubicacion de donde has '
                            'cogido la pieza.')
        libre = self._libre_por_ubicacion(product, [('location_id', 'child_of', ubicacion_leida.id),
                                                    ('location_id', '!=', ml.location_id.id)])
        libre = {loc: q for loc, q in libre.items() if not self._excluida(loc)}   # v1.6
        if not libre:
            raise UserError('En %s no hay stock libre de este articulo en Odoo.' % nombre_corto(ubicacion_leida))
        destino, qty = max(libre.items(), key=lambda it: (it[1], -it[0].id))
        if float_compare(qty, necesario, precision_rounding=product.uom_id.rounding) < 0:
            raise UserError('En %s solo hay %s uds libres y faltan %s. No se ha cambiado nada.'
                            % (nombre_corto(destino), qty, necesario))
        return destino

    @api.model
    def _todo_o_nada(self, funcion, *args):
        """Ejecuta funcion en un savepoint y escribe en la base de datos antes de salir. Si falla, vuelve
        atras y limpia la cache del ORM para que no se escriba nada pendiente al acabar la peticion."""
        self.flush()
        try:
            with self.env.cr.savepoint():
                res = funcion(*args)
                self.flush()
                return res
        except Exception:
            self.env.clear()
            raise

    @api.model
    def _parte(self, ml, cantidad=None):
        """v1.9: (uds en la unidad de la linea, uds en la del articulo, es solo una parte) de lo que pasa a
        Faltantes. Sin cantidad, todo lo que falta por leer de la linea; con cantidad (unidad del articulo), solo
        eso, nunca mas de lo que falta por leer."""
        product = ml.product_id
        qty_linea = self.pendiente_de(ml)                                   # en la unidad de la linea
        qty_prod = ml.product_uom_id._compute_quantity(qty_linea, product.uom_id, rounding_method='HALF-UP')
        if cantidad is None or float_compare(cantidad, qty_prod, precision_rounding=product.uom_id.rounding) >= 0:
            return qty_linea, qty_prod, False
        if float_compare(cantidad, 0, precision_rounding=product.uom_id.rounding) <= 0:
            raise UserError('Cantidad no valida para pasar a Faltantes: %s.' % cantidad)
        qty_linea = product.uom_id._compute_quantity(cantidad, ml.product_uom_id, rounding_method='HALF-UP')
        return qty_linea, cantidad, True

    @staticmethod
    def _con_origen(texto, origen):
        """v1.9: «Desde Contenedores (...)» delante de la nota del faltante."""
        return ' '.join(t for t in (origen, texto) if t)

    @api.model
    def reubicar(self, ml, ubicacion_leida, employee=False, cantidad=None, origen=''):
        """La linea pasa a la ubicacion leida y la unidad que falta va a FALTANTE. Todo o nada.
        v1.9: con cantidad (unidad del articulo), solo esa parte; el resto de la linea sigue donde estaba."""
        F = pda.con_compania(self, ml.picking_id.sudo().company_id)   # TUCTUC: la compañía de la OUT
        return F._todo_o_nada(F._reubicar, ml.with_env(F.env), ubicacion_leida.with_env(F.env), employee, cantidad,
                              origen)

    @api.model
    def _reubicar(self, ml, ubicacion_leida, employee=False, cantidad=None, origen=''):
        self._comprobar(ml)
        picking, product = ml.picking_id, ml.product_id
        raiz = self._raiz_stock(picking)
        faltant = self._ubicacion_faltant(picking)
        company = picking.company_id
        vieja = ml.location_id
        rounding = ml.product_uom_id.rounding
        qty_linea, qty_prod, solo_parte = self._parte(ml, cantidad)
        # v1.3: con una parte leida, o v1.9 si solo pasa una parte, la linea se queda y lo que falta va aparte
        parcial = solo_parte or not float_is_zero(ml.qty_done, precision_rounding=rounding)
        destino = self.elegir_destino(ml, ubicacion_leida, raiz, qty_prod)

        if not parcial:
            # a) la reserva: write estandar de Odoo (quita en la vieja, reserva strict en la nueva)
            ml.write({'location_id': destino.id})
            self.flush()
            if float_compare(ml.product_uom_qty, qty_linea, precision_rounding=rounding) < 0:
                raise UserError('Odoo solo ha podido reservar %s de %s uds en %s. No se ha cambiado nada.'
                                % (ml.product_uom_qty, qty_linea, nombre_corto(destino)))
        else:
            # a') v1.3, linea con una parte leida: lo leido se queda en la linea; lo que falta se reserva aparte.
            #     v1.9: solo una parte: la linea baja en esa parte y esa parte se reserva aparte
            self._reservar_resto_en(ml, qty_prod, destino, queda=ml.product_uom_qty - qty_linea)

        # b) despues, la unidad que falta: de la vieja a FALTANTE (solo lo que Odoo tiene alli libre)
        move, movido, nota = self._a_faltant(product, qty_prod, vieja, faltant, company, picking)

        # c) el registro y (v1.3.1) la nota en la OUT
        self._nota_out(picking, employee, 'Faltante%s: %s %s uds no estaban en %s; se cogen en %s.'
                       % (' (%s)' % origen if origen else '', product.display_name, qty_linea, nombre_corto(vieja),
                          nombre_corto(destino)), movido)
        nota = self._con_origen(nota, origen)
        return self.create({
            'employee_id': employee.id if employee else False,
            'picking_id': picking.id,
            'product_id': product.id,
            'cantidad': qty_linea,
            'cantidad_faltant': movido,
            'ubicacion_vieja_id': vieja.id,
            'ubicacion_nueva_id': destino.id,
            'linea_id': ml.id,
            'tipo': 'reubicado',
            'move_faltant_id': move.id if move else False,
            'nota': nota,
            'company_id': company.id,
        })

    @api.model
    def _nota_out(self, picking, employee, texto, movido):
        """v1.3.1: deja escrito en el historial (chatter) de la OUT que se ha cambiado, quien y cuando."""
        texto += ' %s uds de la ubicación vieja a FALTANTE.' % movido if movido else ''
        if employee:
            texto += ' Operario: %s.' % employee.name
        picking.message_post(body=html_escape(texto))

    @api.model
    def sin_alternativa(self, ml, employee=False, cantidad=None, origen=''):
        """No esta en ningun sitio: se quita la reserva de esa linea (como "Anular reserva" pero solo de
        ella) y la unidad que falta va a FALTANTE. La OUT se valida sin esa pieza, como ahora.
        v1.9: con cantidad (unidad del articulo), solo esa parte; el resto de la linea sigue reservado."""
        F = pda.con_compania(self, ml.picking_id.sudo().company_id)   # TUCTUC: la compañía de la OUT
        return F._todo_o_nada(F._sin_alternativa, ml.with_env(F.env), employee, cantidad, origen)

    @api.model
    def _sin_alternativa(self, ml, employee=False, cantidad=None, origen=''):
        self._comprobar(ml)
        picking, product = ml.picking_id, ml.product_id
        self._raiz_stock(picking)
        faltant = self._ubicacion_faltant(picking)
        company = picking.company_id
        vieja = ml.location_id
        ml_id = ml.id
        qty_linea, qty_prod, solo_parte = self._parte(ml, cantidad)
        queda = ml.product_uom_qty - qty_linea    # lo leido (v1.3) o, v1.9, la parte que si esta

        if float_is_zero(queda, precision_rounding=ml.product_uom_id.rounding):
            # a) quitar la reserva de la linea: unlink estandar (devuelve la reserva al quant y recalcula
            #    el estado del movimiento)
            ml.unlink()
        else:
            # a') v1.3, linea con una parte leida: la reserva baja a lo leido (write estandar de
            #     product_uom_qty: devuelve al quant solo lo que falta). v1.9: o baja solo en la parte que no esta
            move = ml.move_id
            ml.write({'product_uom_qty': queda})
            self.flush()
            move._recompute_state()

        # b) la unidad que falta: de la vieja a FALTANTE
        move, movido, nota = self._a_faltant(product, qty_prod, vieja, faltant, company, picking)

        self._nota_out(picking, employee, 'Faltante%s: %s %s uds no estaban en %s ni en ninguna otra ubicación; '
                       'la OUT sale sin ellas.' % (' (%s)' % origen if origen else '', product.display_name,
                                                   qty_linea, nombre_corto(vieja)), movido)
        nota = self._con_origen(nota, origen)
        return self.create({
            'employee_id': employee.id if employee else False,
            'picking_id': picking.id,
            'product_id': product.id,
            'cantidad': qty_linea,
            'cantidad_faltant': movido,
            'ubicacion_vieja_id': vieja.id,
            'linea_id': ml_id,
            'tipo': 'sin_alternativa',
            'move_faltant_id': move.id if move else False,
            'nota': nota,
            'company_id': company.id,
        })

    @api.model
    def _reservar_resto_en(self, ml, qty_prod, destino, queda=None):
        """v1.3: linea con una parte leida. La linea se queda con lo leido (write estandar de
        product_uom_qty, que devuelve al quant lo que falta) y lo que falta se reserva en destino con el
        metodo estandar del movimiento (_update_reserved_quantity, strict: solo stock libre de esa
        ubicacion). Si no llega, error (el savepoint deshace todo).
        v1.9: queda = lo que se queda reservado en la linea (unidad de la linea); por defecto, lo leido."""
        move, product = ml.move_id, ml.product_id
        ml.write({'product_uom_qty': ml.qty_done if queda is None else queda})
        self.flush()
        disponible = self.env['stock.quant']._get_available_quantity(product, destino, strict=True)
        cogido = move._update_reserved_quantity(qty_prod, disponible, destino, strict=True)
        move._recompute_state()
        self.flush()
        if float_compare(cogido, qty_prod, precision_rounding=product.uom_id.rounding) < 0:
            raise UserError('Odoo solo ha podido reservar %s de %s uds en %s. No se ha cambiado nada.'
                            % (cogido, qty_prod, nombre_corto(destino)))
        return cogido

    # ------------------------------------------------------------------ validar (v1.3)
    @api.model
    def validar_out(self, picking, pedido_pendiente=None):
        """Valida la OUT con la validacion normal de Odoo (button_validate), todo o nada.
        pedido_pendiente: None = si Odoo pregunta por el pedido pendiente, devolver 'preguntar';
        'si' / 'no' = la respuesta. Devuelve {'estado': 'validada' | 'preguntar' | 'pendientes', 'n': lineas}."""
        if picking.state in ('done', 'cancel'):
            raise UserError('La OUT %s ya esta %s.' % (picking.name, 'validada' if picking.state == 'done'
                                                       else 'cancelada'))
        if picking.batch_id and (picking.batch_id.name or '').startswith(PREFIJOS_ZONA):
            raise UserError('%s es de la agrupacion %s: se valida desde la agrupacion.'
                            % (picking.name, picking.batch_id.name))
        pendientes = self.lineas_pendientes(picking)
        if pendientes:
            return {'estado': 'pendientes', 'n': len(pendientes)}
        if float_is_zero(sum(picking.move_line_ids.mapped('qty_done')), precision_digits=3):
            raise UserError('En %s no hay nada leido. Validala en la app de codigo de barras.' % picking.name)
        F = pda.con_compania(self, picking.sudo().company_id)   # TUCTUC: la compañía de la OUT
        return F._todo_o_nada(F._validar_out, picking.with_env(F.env), pedido_pendiente)

    @api.model
    def _validar_out(self, picking, pedido_pendiente):
        res = picking.button_validate()
        if isinstance(res, dict) and res.get('res_model'):
            modelo = res['res_model']
            if modelo != 'stock.backorder.confirmation':
                # transferencia inmediata, cantidades de mas, asistentes de otros modulos: no se fuerza nada
                raise UserError('Odoo pide otra cosa al validar (%s). Validala en la app de codigo de barras.'
                                % (res.get('name') or modelo))
            if pedido_pendiente not in ('si', 'no'):
                return {'estado': 'preguntar', 'n': 0}
            asistente = self.env[modelo].with_context(**(res.get('context') or {})).create(
                {'pick_ids': [(4, picking.id)]})
            if pedido_pendiente == 'si':
                asistente.process()
            else:
                asistente.process_cancel_backorder()
        if picking.state != 'done':
            raise UserError('Odoo no ha validado %s (estado %s). Validala en la app de codigo de barras.'
                            % (picking.name, picking.state))
        return {'estado': 'validada', 'n': 0}

    @api.model
    def _a_faltant(self, product, qty, vieja, faltant, company, picking):
        """Mueve a FALTANTE lo que falta, pero nunca mas de lo que Odoo tiene libre en la vieja (si no,
        Odoo quitaria reservas a otras OUT). Devuelve (move, uds movidas, nota)."""
        rounding = product.uom_id.rounding
        libre = self._libre_en(product, vieja)
        mover = min(qty, libre)
        if float_compare(mover, 0, precision_rounding=rounding) <= 0:
            return False, 0.0, 'En la ubicacion vieja ya no quedaba stock libre en Odoo: no se ha movido nada.'
        nota = ''
        if float_compare(mover, qty, precision_rounding=rounding) < 0:
            nota = 'En la ubicacion vieja solo quedaban %s uds libres en Odoo: se han movido esas.' % mover
        move = self._mover(product, mover, vieja, faltant, company,
                           'TUCTUC Faltante %s' % picking.name, picking.name)
        return move, mover, nota

    # ------------------------------------------------------------------ revision
    def _comprobar_revision(self):
        for f in self:
            if f.estado not in ('pendiente', 'no_existe'):   # v1.7: tambien «Ubicacion no existe»
                raise UserError('%s ya esta revisado.' % f.name)
            if f.en_ronda:
                raise UserError('%s esta en la ronda %s: se revisa en esa INT (Lecturas) o se cancela la INT.'
                                % (f.name, f.ronda_move_id.picking_id.name or ''))

    def action_no_encontrado(self):
        """De FALTANTE a perdidas de inventario (lo que antes se hacia poniendo a 0 en la PDA)."""
        self._comprobar_revision()
        for f in self:
            f._cerrar_no_encontrado()
        return True

    def _cerrar_no_encontrado(self, nota='', usuario=None):
        self.ensure_one()
        move = False
        # v1.7: un puesto a 0 ya esta en perdidas: no se mueve nada
        if self.tipo != 'puesto_a_cero' and not float_is_zero(self.cantidad_faltant,
                                                                  precision_rounding=self.product_id.uom_id.rounding):
            perdidas = self._ubicacion_perdidas(self.product_id, self.company_id)
            move = self._mover_desde_faltant(self, self._faltant_de(), perdidas)
        vals = {'estado': 'no_encontrado', 'move_revision_id': move.id if move else False,
                'ubicacion_revision_id': move.location_dest_id.id if move else False,
                'fecha_revision': fields.Datetime.now(), 'revisado_por': (usuario or self.env.user).id}
        if nota:
            vals['nota'] = ('%s %s' % (self.nota or '', nota)).strip()
        self.write(vals)

    def marcar_encontrado(self, ubicacion):
        """De FALTANTE a la ubicacion elegida (asistente Encontrado)."""
        self._comprobar_revision()
        if ubicacion.usage != 'internal':
            raise UserError('Elige una ubicacion interna.')
        for f in self:
            faltant = f._faltant_de()   # TUCTUC: la FALTANTE de su almacén
            if ubicacion == faltant:
                raise UserError('Elige una ubicacion distinta de FALTANTE.')
            move = False
            if not float_is_zero(f.cantidad_faltant, precision_rounding=f.product_id.uom_id.rounding):
                move = self._mover_desde_faltant(f, faltant, ubicacion)
            f.write({'estado': 'encontrado', 'move_revision_id': move.id if move else False,
                     'ubicacion_revision_id': ubicacion.id,
                     'fecha_revision': fields.Datetime.now(), 'revisado_por': self.env.user.id})
        return True

    def _mover_desde_faltant(self, f, faltant, destino):
        origen = f._origen()   # v1.7: FALTANTE o, en un puesto a 0, perdidas
        if origen.usage == 'internal':
            libre = self._libre_en(f.product_id, origen)
            if float_compare(libre, f.cantidad_faltant, precision_rounding=f.product_id.uom_id.rounding) < 0:
                raise UserError('En FALTANTE solo hay %s uds de %s y este faltante es de %s. Revisa FALTANTE.'
                                % (libre, f.product_id.display_name, f.cantidad_faltant))
        ref = f.picking_id.name or 'puesto a 0'
        return self._mover(f.product_id, f.cantidad_faltant, origen, destino, f.company_id,
                           'TUCTUC Revision faltante %s' % ref, ref)

    def action_encontrado(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Encontrado',
            'res_model': 'tuctuc.faltante.encontrado',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_model': self._name, 'active_ids': self.ids,
                        'default_ubicacion_id': self[:1].ubicacion_vieja_id.id},
        }

    # ------------------------------------------------------------------ ronda de revision (INT)
    @api.depends('ronda_move_id.state')
    def _compute_en_ronda(self):
        for f in self:
            f.en_ronda = bool(f.ronda_move_id and f.ronda_move_id.state not in ('done', 'cancel'))

    def _search_en_ronda(self, operator, value):
        dentro = [('ronda_move_id', '!=', False), ('ronda_move_id.state', 'not in', ('done', 'cancel'))]
        fuera = ['|', ('ronda_move_id', '=', False), ('ronda_move_id.state', 'in', ('done', 'cancel'))]
        return dentro if (operator == '=') == bool(value) else fuera

    def crear_ronda(self):
        """Crea la INT de revision con los faltantes seleccionados (o todos los pendientes si no hay
        seleccion) que tienen uds en FALTANTE y no estan ya en una ronda abierta. Una linea por faltante,
        de FALTANTE a su ubicacion vieja, por orden de lineal."""
        fallados = self._sincronizar()    # v1.9: los que no se han podido pasar no entran en la ronda nueva
        faltantes = self.exists() or self.search([('estado', '=', 'pendiente')])
        faltantes = faltantes.filtered(
            lambda f: f.estado == 'pendiente' and not f.en_ronda and f.id not in fallados and
            not float_is_zero(f.cantidad_faltant, precision_rounding=f.product_id.uom_id.rounding))
        if not faltantes:
            raise UserError('No hay faltantes pendientes con uds en FALTANTE que no esten ya en una ronda.')
        ahora = comun.ahora_local().strftime('%d/%m %H:%M')
        grupos = {}
        for f in faltantes:
            almacen = f.picking_id.picking_type_id.warehouse_id or f.ubicacion_vieja_id.get_warehouse()   # v1.7
            tipo = almacen.int_type_id
            if not tipo:
                raise UserError('El almacen de %s no tiene tipo de transferencia interna.' % f.name)
            # v1.7: una INT por origen (FALTANTE o, los puestos a 0, perdidas)
            clave = (tipo, f._origen())
            grupos.setdefault(clave, self.browse())
            grupos[clave] |= f
        Picking, Move = self.env['stock.picking'], self.env['stock.move']
        pickings = Picking.browse()
        for (tipo, faltant), grupo in grupos.items():
            company = grupo[0].company_id
            cero = faltant.usage != 'internal'
            picking = Picking.create({
                'picking_type_id': tipo.id,
                'location_id': faltant.id,
                'location_dest_id': (tipo.warehouse_id.lot_stock_id or tipo.default_location_dest_id).id,
                'origin': '%s %s%s' % (ORIGEN_RONDA, ahora, ' (PUESTOS A 0)' if cero else ''),
                'company_id': company.id,
                'move_type': 'direct',
            })
            moves = Move.browse()
            for i, f in enumerate(sorted(grupo, key=self._orden_ronda)):
                m = Move.create({
                    'name': 'TUCTUC Ronda faltante %s' % (f.picking_id.name or 'puesto a 0'),
                    'origin': f.picking_id.name or 'Puesto a 0',
                    'picking_id': picking.id,
                    'picking_type_id': tipo.id,
                    'sequence': i + 1,
                    'product_id': f.product_id.id,
                    'product_uom': f.product_id.uom_id.id,
                    'product_uom_qty': f.cantidad_faltant,
                    'location_id': faltant.id,
                    'location_dest_id': f.ubicacion_vieja_id.id,
                    'company_id': company.id,
                })
                f.write({'ronda_move_id': m.id, 'ronda_picking_id': picking.id, 'rondas': f.rondas + 1,
                         'ronda_resultado': False, 'ronda_operario_id': False, 'ronda_fecha': False})   # v1.7
                moves |= m
            # sin juntar lineas: cada faltante tiene la suya aunque sea el mismo articulo y ubicacion
            moves._action_confirm(merge=False)
            picking.action_assign()
            for f in grupo:
                if f.ronda_move_id.state != 'assigned':
                    f.nota = ('%s En %s no hay stock para la ronda %s.' % (
                        f.nota or '', faltant.name, picking.name)).strip()
            pickings |= picking
        if len(pickings) == 1:
            return {'type': 'ir.actions.act_window', 'name': 'Ronda de faltantes', 'res_model': 'stock.picking',
                    'res_id': pickings.id, 'view_mode': 'form', 'views': [(False, 'form')]}
        return {'type': 'ir.actions.act_window', 'name': 'Rondas de faltantes', 'res_model': 'stock.picking',
                'domain': [('id', 'in', pickings.ids)], 'view_mode': 'tree,form',
                'views': [(False, 'tree'), (False, 'form')]}

    @api.model
    def _orden_ronda(self, f):
        lin = lineal_de(f.ubicacion_vieja_id)
        return (lin if lin is not None else 9999, f.ubicacion_vieja_id.complete_name or '', f.id)

    @api.model
    def _resto_de_ronda(self, move):
        """El movimiento con lo no leido de una linea hecha a medias: en la misma INT (cancelado, si se
        valido sin pedido pendiente) o en su INT pendiente. Que no sea de otro faltante."""
        pickings = move.picking_id | self.env['stock.picking'].search([('backorder_id', '=', move.picking_id.id)])
        candidatos = self.env['stock.move'].search([
            ('picking_id', 'in', pickings.ids), ('product_id', '=', move.product_id.id),
            ('location_id', '=', move.location_id.id), ('id', '!=', move.id), ('state', '!=', 'done')],
            order='id desc')
        for c in candidatos:
            if not self.search_count([('ronda_move_id', '=', c.id)]):
                return c
        return self.env['stock.move']

    @api.model
    def sincronizar_rondas(self):
        """Pasa a los faltantes lo que se ha hecho en las INT de ronda. Lo llama el cron cada 15 min."""
        self._sincronizar()
        return True

    @api.model
    def _sincronizar(self):
        """v1.9 (R13): cada faltante en su savepoint. Si uno falla, se deshace solo el suyo, queda en el log con su
        id y el cron sigue con los demas (antes un faltante malo paraba la ronda entera cada 15 min). Devuelve los
        ids que han fallado (crear_ronda no los vuelve a meter en una ronda)."""
        pendientes = self.search([('estado', '=', 'pendiente'), ('ronda_move_id', '!=', False)])
        fallados = []
        for fid in pendientes.ids:
            try:
                self._todo_o_nada(self._sincronizar_uno, fid)
            except Exception:
                fallados.append(fid)
                _logger.exception('TUCTUC FALTANTES ronda: no se ha podido pasar el faltante id %s; se deja como '
                                  'estaba y se sigue con los demas', fid)
        if fallados:
            _logger.warning('TUCTUC FALTANTES ronda: %s de %s faltantes sin pasar (ids %s)', len(fallados),
                            len(pendientes), fallados)
        return fallados

    @api.model
    def _sincronizar_uno(self, fid):
        f = self.browse(fid).exists()
        if not f or f.estado != 'pendiente' or not f.ronda_move_id:
            return
        m = f.ronda_move_id
        rounding = f.product_id.uom_id.rounding
        if m.state not in ('done', 'cancel'):
            if m.picking_id and m.picking_id != f.ronda_picking_id:
                # "Crear pedido pendiente": la linea ha pasado a la INT nueva
                f.write({'ronda_picking_id': m.picking_id.id, 'rondas': f.rondas + 1})
            return
        if m.state == 'cancel':
            # v1.7: lo marcado en Lecturas manda
            ronda = m.picking_id.name or ''
            if f.ronda_resultado == 'no_existe':
                f.write({'estado': 'no_existe', 'ronda_move_id': False,
                         'fecha_revision': f.ronda_fecha or fields.Datetime.now(), 'revisado_por': m.write_uid.id,
                         'nota': ('%s Ronda %s: la ubicacion ya no existe.' % (f.nota or '', ronda)).strip()})
                return
            if f.ronda_resultado == 'no_esta':
                if f.tipo == 'puesto_a_cero' or f.rondas >= RONDAS_PERDIDAS:
                    f._cerrar_no_encontrado('No estaba en la ronda %s (%s.a ronda).' % (ronda, f.rondas),
                                            m.write_uid)
                else:
                    f.write({'ronda_move_id': False,
                             'nota': ('%s Ronda %s: no estaba; sigue pendiente (a la %s.a ronda sin aparecer, a '
                                      'perdidas).' % (f.nota or '', ronda, RONDAS_PERDIDAS)).strip()})
                return
            if m.picking_id.state == 'cancel':
                # se ha cancelado la INT entera: no es "no encontrado", vuelve a pendiente sin ronda
                f.write({'ronda_move_id': False, 'ronda_picking_id': False,
                         'nota': ('%s Ronda %s cancelada.' % (f.nota or '', m.picking_id.name or '')).strip()})
            else:
                f._cerrar_no_encontrado('No encontrado en la ronda %s.' % (m.picking_id.name or ''),
                                        m.write_uid)
            return
        # hecho: encontrado donde se haya leido
        hecho = m.product_uom._compute_quantity(m.quantity_done, f.product_id.uom_id)
        lineas = m.move_line_ids.filtered(lambda l: l.qty_done > 0)
        destino = lineas[:1].location_dest_id or m.location_dest_id
        if float_compare(hecho, f.cantidad_faltant, precision_rounding=rounding) < 0:
            # solo una parte: el resto sigue como otro faltante
            resto = f.cantidad_faltant - hecho
            otro = self._resto_de_ronda(m)
            nuevo = f.copy({
                'cantidad': resto, 'cantidad_faltant': resto, 'fecha': f.fecha,
                'ronda_move_id': otro.id if otro else False,
                'ronda_picking_id': otro.picking_id.id if otro else False,
                'nota': 'Resto de una linea encontrada a medias en %s.' % (m.picking_id.name or ''),
            })
            f.write({'cantidad': max(f.cantidad - resto, 0.0), 'cantidad_faltant': hecho})
            if otro and otro.state == 'cancel':
                nuevo._cerrar_no_encontrado('No encontrado en la ronda %s.' % (m.picking_id.name or ''),
                                            m.write_uid)
        f.write({'estado': 'encontrado', 'move_revision_id': m.id, 'ubicacion_revision_id': destino.id,
                 'fecha_revision': m.date or fields.Datetime.now(), 'revisado_por': m.write_uid.id,
                 'ronda_resultado': 'esta', 'ronda_fecha': f.ronda_fecha or m.date})

    # ------------------------------------------------------------------ v1.9: contenedor que se archiva (R4)
    @api.model
    def en_ronda_de(self, ubicaciones):
        """Faltantes pendientes con vuelta a alguna de esas ubicaciones que estan en una ronda abierta: mientras
        tanto no se archiva el contenedor (la INT de la ronda lleva la prenda alli)."""
        return self.search([('ubicacion_vieja_id', 'in', ubicaciones.ids), ('estado', '=', 'pendiente')]).filtered(
            'en_ronda')

    @api.model
    def antes_de_archivar(self, ubicaciones):
        """Se van a archivar estos contenedores (vacios). Los faltantes pendientes con vuelta a ellos pasan a
        apuntar al hueco donde estaba cada uno (la proxima ronda busca alli). Si alguno esta en una ronda abierta,
        error y no se cambia nada. Devuelve cuantos faltantes han cambiado."""
        en_ronda = self.en_ronda_de(ubicaciones)
        if en_ronda:
            raise UserError('No se archiva: %s tiene %d faltante(s) en la ronda %s. Espera a que se cierre la ronda.'
                            % (', '.join(en_ronda.mapped('ubicacion_vieja_id.name')), len(en_ronda),
                               ', '.join(en_ronda.mapped('ronda_picking_id.name'))))
        pendientes = self.search([('ubicacion_vieja_id', 'in', ubicaciones.ids), ('estado', '=', 'pendiente')])
        for f in pendientes:
            cont = f.ubicacion_vieja_id
            hueco = cont.location_id
            if not hueco or hueco.usage != 'internal':
                continue
            f.write({'ubicacion_vieja_id': hueco.id,
                     'nota': ('%s Contenedor %s archivado: la ronda lo busca en %s.'
                              % (f.nota or '', cont.name, nombre_corto(hueco))).strip()})
        return len(pendientes)

    # ------------------------------------------------------------------ v1.7: ronda en Lecturas
    @api.model
    def es_ronda(self, picking):
        """INT de una ronda de faltantes (la crea crear_ronda; tambien su pedido pendiente)."""
        return bool(picking) and picking.picking_type_code == 'internal' and \
            (picking.origin or '').startswith(ORIGEN_RONDA)

    @api.model
    def ronda_marcar(self, ml, resultado, employee=False):
        """Lecturas: «No esta» / «La ubicacion no existe» en una linea de la ronda. Quita la reserva de lo que no se
        ha leido (la linea desaparece de la pantalla) y apunta el resultado y el operario. Lo demas lo hace
        sincronizar_rondas() al validar la INT."""
        if resultado not in ('no_esta', 'no_existe'):
            raise UserError('Resultado desconocido: %s' % resultado)
        ml = ml.exists()
        if not ml:
            raise UserError('Esa linea ya no existe: vuelve a cargar la ronda.')
        picking = ml.picking_id
        if not self.es_ronda(picking):
            raise UserError('%s no es una ronda de faltantes.' % (picking.name or '-'))
        if picking.state in ('done', 'cancel'):
            raise UserError('La ronda %s ya esta %s.' % (picking.name, 'validada' if picking.state == 'done'
                                                         else 'cancelada'))
        faltantes = self.search([('ronda_move_id', '=', ml.move_id.id)])
        if not faltantes:
            raise UserError('Esta linea no es de ningun faltante de la ronda.')
        return self._todo_o_nada(self._ronda_marcar, ml, faltantes, resultado, employee)

    @api.model
    def _ronda_marcar(self, ml, faltantes, resultado, employee=False):
        move = ml.move_id
        if float_is_zero(ml.qty_done, precision_rounding=ml.product_uom_id.rounding):
            ml.unlink()
        else:
            ml.write({'product_uom_qty': ml.qty_done})
            self.flush()
            move._recompute_state()
        faltantes.write({'ronda_resultado': resultado, 'ronda_fecha': fields.Datetime.now(),
                         'ronda_operario_id': employee.id if employee else False})
        return {'ok': True}

    @api.model
    def ronda_antes_de_validar(self, picking, employee=False):
        """Lecturas, al validar la ronda: apunta el operario en lo que se ha leido (esta)."""
        faltantes = self.search([('ronda_move_id', 'in', picking.move_lines.ids), ('ronda_resultado', '=', False)])
        ahora = fields.Datetime.now()
        for f in faltantes:
            if any(f.ronda_move_id.move_line_ids.mapped('qty_done')):
                f.write({'ronda_resultado': 'esta', 'ronda_fecha': ahora,
                         'ronda_operario_id': employee.id if employee else False})
        return True

    @api.model
    def ronda_cerrar_sin_leer(self, picking):
        """Lecturas: ronda sin nada leido y todo marcado («No esta» / «No existe»): no hay nada que validar, se
        cancela la INT y sincronizar_rondas() aplica lo marcado."""
        if self.lineas_pendientes(picking):
            raise UserError('Quedan lineas sin marcar en %s.' % picking.name)
        picking.action_cancel()
        return {'estado': 'validada', 'n': 0}

    # ------------------------------------------------------------------ v1.7: puestos a 0 del picking viejo
    @api.model
    def importar_puestos_a_cero(self):
        """Pasa a faltantes (tipo «Puesto a 0») lo que se puso a 0 desde las PDA en la app de codigo de barras desde
        el dia del parametro tuctuc_faltantes.puestos_a_cero_desde. Solo en lineales y muelle (v1.6) y si ahora en
        esa ubicacion no hay stock de ese articulo (si lo hay, la ronda no sabria si es la pieza perdida). No mueve
        stock: las uds siguen en perdidas hasta que la ronda las encuentra. Se puede repetir: lo ya pasado no se
        vuelve a pasar."""
        Param = self.env['ir.config_parameter'].sudo()
        desde = fields.Date.to_date(Param.get_param(PARAM_CERO_DESDE, CERO_DESDE_DEFECTO))
        logins = [x.strip() for x in (Param.get_param(PARAM_CERO_USUARIOS, CERO_USUARIOS_DEFECTO) or '').split(',')
                  if x.strip()]
        usuarios = self.env['res.users'].sudo().with_context(active_test=False).search([('login', 'in', logins)])
        moves = self.env['stock.move'].search([
            ('name', '=', NOMBRE_PUESTA_A_CERO), ('state', '=', 'done'),
            ('date', '>=', fields.Datetime.to_string(comun.inicio_dia_utc(desde))),
            ('location_id.usage', '=', 'internal'), ('location_dest_id.usage', '=', 'inventory'),
            ('create_uid', 'in', usuarios.ids), ('company_id', 'in', self.env.companies.ids),
        ], order='date')
        ya = set(self.search([('move_cero_id', 'in', moves.ids)]).mapped('move_cero_id').ids)
        Quant = self.env['stock.quant']
        creados = self.browse()
        saltados = {'ya': 0, 'zona': 0, 'con_stock': 0}
        for m in moves:
            if m.id in ya:
                saltados['ya'] += 1
                continue
            if self._excluida(m.location_id):
                saltados['zona'] += 1
                continue
            hay = sum(Quant.search([('product_id', '=', m.product_id.id),
                                    ('location_id', '=', m.location_id.id)]).mapped('quantity'))
            if float_compare(hay, 0, precision_rounding=m.product_id.uom_id.rounding) > 0:
                saltados['con_stock'] += 1
                continue
            qty = m.product_uom._compute_quantity(m.quantity_done or m.product_uom_qty, m.product_id.uom_id)
            creados |= self.create({
                'user_id': m.create_uid.id,
                'product_id': m.product_id.id,
                'cantidad': qty,
                'cantidad_faltant': qty,
                'ubicacion_vieja_id': m.location_id.id,
                'tipo': 'puesto_a_cero',
                'fecha': m.date,
                'move_cero_id': m.id,
                'company_id': m.company_id.id,
                'nota': 'Puesto a 0 en la app de codigo de barras (picking viejo).',
            })
        _logger.info('TUCTUC FALTANTES puestos a 0 desde %s: %s pasados; saltados %s', desde, len(creados), saltados)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Puestos a 0 pasados: %s (ya estaban %s, fuera de lineal/muelle %s, con stock ahora %s)'
                    % (len(creados), saltados['ya'], saltados['zona'], saltados['con_stock']),
            'res_model': self._name,
            'view_mode': 'tree,form',
            'views': [(False, 'tree'), (False, 'form')],
            'domain': [('tipo', '=', 'puesto_a_cero'), ('estado', '=', 'pendiente')],
        }

    # ------------------------------------------------------------------ v1.7: informe de la ronda
    def lineas_informe(self):
        """Para el informe «Resultado de la ronda»: [(titulo, faltantes)] por resultado, por lineal."""
        def grupo(f):
            if f.estado == 'encontrado':
                return 0
            if f.estado == 'no_existe' or f.ronda_resultado == 'no_existe':
                return 2
            if f.ronda_resultado == 'no_esta' or f.estado == 'no_encontrado':
                return 1
            return 3
        titulos = ['Encontrado', 'No estaba', 'La ubicacion ya no existe', 'Sin hacer']
        res = []
        for i, titulo in enumerate(titulos):
            fs = self.filtered(lambda f: grupo(f) == i).sorted(
                lambda f: (lineal_de(f.ubicacion_vieja_id) or 9999, f.ubicacion_vieja_id.complete_name or ''))
            if fs:
                res.append((titulo, fs))
        return res

    # ------------------------------------------------------------------ informe
    @api.model
    def action_puestos_a_cero(self):
        """Movimientos de hoy hechos poniendo cantidades a 0 (o cambiandolas) en la PDA, sin pasar por
        la pantalla Faltante. Agrupados por usuario."""
        # v1.5: las 00:00 de hoy con su propio desfase (antes se cambiaba la hora de «ahora» y el dia del cambio de
        # hora quedaba una hora corrido)
        desde = fields.Datetime.to_string(comun.inicio_dia_utc(comun.hoy_local()))
        return {
            'type': 'ir.actions.act_window',
            'name': 'Puestos a 0 hoy',
            'res_model': 'stock.move',
            'view_mode': 'tree,form',
            'domain': [('name', '=', NOMBRE_PUESTA_A_CERO), ('state', '=', 'done'), ('date', '>=', desde),
                       ('location_dest_id.usage', '=', 'inventory')],
            'context': {'group_by': ['create_uid'], 'create': False},
        }
