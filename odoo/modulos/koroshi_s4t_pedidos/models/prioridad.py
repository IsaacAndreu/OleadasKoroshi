# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Pedidos S4T - v1.1.0 (23/11/2026): reserva de las tiendas por prioridad.
#
# Isaac (23/11): que el stock reservado siga la misma prioridad que «Cada tienda en cada zona» del Monitor: numero de
# pedido S4T, el mas bajo primero. Hoy se lo queda quien confirmo o reservo antes.
#
# Una vez al dia (cron 03:30 UTC, 20 min antes de que koroshi_zonas parta) o a mano:
#   1. OUT de PED. TIENDAS abiertas (confirmed/assigned) que nadie ha empezado: sin lineas leidas, sin cajas, sin
#      lote que no sea la agrupacion del dia (TIENDA...), sin puesto de operario, fuera del SORTER. Las ya partidas
#      por zonas tienen lote Z-: no entran. Nunca Zalando, About ni web (otro tipo de pedido).
#   2. Por cada articulo EN DISPUTA (a una le falta y otra de numero mas alto tiene reservado): quitar la reserva de
#      sus movimientos y volver a reservar uno a uno del numero mas bajo al mas alto. Todo el articulo en un
#      savepoint: si algo falla, ese articulo queda como estaba.
#   3. Modo (parametro koroshi_s4t_pedidos.prioridad_modo): 'simular' (por defecto) hace lo mismo y lo deshace
#      articulo a articulo; 'real' guarda (commit por articulo); 'apagado' no hace nada.
#   4. Informe: koroshi.s4t.prioridad con las lineas que ganan o pierden unidades.
# Sin campos en tablas compartidas.
# v1.2.0 (revision general 23/11, R15), antes de pasar a real:
#   - «no empezada» se vuelve a mirar DENTRO del savepoint de cada articulo (el reparto tarda y hay commit por
#     articulo: una OUT que alguien empieza a leer mientras tanto ya no se toca; ese articulo se salta).
#   - el boton no deja repartir en horario de trabajo (koroshi_s4t_pedidos.prioridad_horario, 06:00-17:00).
#   - se para koroshi_s4t_pedidos.prioridad_margen_zonas min (5) antes del cron de koroshi_zonas «partir OUT» (lee su
#     siguiente hora; no toca koroshi_zonas), y no empieza si ya le toca a zonas. Lo hecho hasta ahi queda.
# =============================================================================
import datetime
import logging
import time

import psycopg2

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.service.model import PG_CONCURRENCY_ERRORS_TO_RETRY

from odoo.addons.koroshi_base import comun
from odoo.addons.queue_job.exception import RetryableJobError

from .. import logica
from .comun_jobs import candado, guardar

_logger = logging.getLogger(__name__)

ESTADOS_MOVE = ('confirmed', 'partially_available', 'assigned')


class _Deshacer(Exception):
    """Para deshacer el savepoint de un articulo en modo simular."""


class _Saltar(Exception):
    """v1.2.0: una OUT del articulo se ha empezado mientras se repartia: ese articulo no se toca."""


class PrioridadEjecucion(models.Model):
    _name = 'koroshi.s4t.prioridad'
    _description = 'KOROSHI: reparto de la reserva de tiendas por prioridad'
    _order = 'id desc'

    name = fields.Char('Ejecución', readonly=True)
    fecha = fields.Datetime('Fecha', readonly=True, default=fields.Datetime.now)
    modo = fields.Selection([('simular', 'Simular (no cambia nada)'), ('real', 'Real')], readonly=True)
    origen = fields.Selection([('cron', 'Cron'), ('manual', 'A mano')], readonly=True)
    segundos = fields.Float('Segundos', readonly=True, digits=(16, 1))
    n_out = fields.Integer('OUT de tienda miradas', readonly=True)
    n_saltadas = fields.Integer('OUT saltadas (empezadas)', readonly=True)
    n_articulos = fields.Integer('Artículos en disputa', readonly=True)
    n_lineas = fields.Integer('Líneas que cambian', readonly=True)
    n_errores = fields.Integer('Artículos con error', readonly=True)
    resumen = fields.Text('Resumen', readonly=True)
    linea_ids = fields.One2many('koroshi.s4t.prioridad.linea', 'ejecucion_id', 'Cambios', readonly=True)

    # ------------------------------------------------------------------ entradas

    @api.model
    def cron_repartir(self):
        return self._lanzar('cron')

    @api.model
    def accion_repartir(self):
        # v1.2.0 (R15): con el almacen trabajando no se reparte a mano (quita y vuelve a poner reservas de OUT que se
        # estan preparando). Tampoco en simular: bloquea las lineas mientras prueba cada articulo
        horario = (self.env['ir.config_parameter'].sudo().get_param(logica.PARAM_PRIORIDAD_HORARIO)
                   or logica.HORARIO_DEFECTO)
        ahora = comun.ahora_local()
        if logica.en_horario(ahora.hour, ahora.minute, horario):
            raise UserError(_('No se reparte por prioridad en horario de trabajo (%s, parametro %s): quitaria '
                              'reservas a OUT que se estan preparando. Hazlo fuera de ese horario o espera al cron.')
                            % (horario, logica.PARAM_PRIORIDAD_HORARIO))
        if self._parar_por_zonas():
            raise UserError(_('Ahora no: esta a punto de empezar (o en marcha) el reparto de zonas. Espera a que '
                              'acabe.'))
        ejecucion = self._lanzar('manual')
        if not ejecucion:
            return {'type': 'ir.actions.act_window_close'}
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reparto por prioridad'),
            'res_model': self._name,
            'res_id': ejecucion.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ------------------------------------------------------------------ reparto

    @api.model
    def _lanzar(self, origen):
        modo = logica.modo_prioridad(
            self.env['ir.config_parameter'].sudo().get_param(logica.PARAM_PRIORIDAD_MODO))
        if modo == 'apagado':
            _logger.info('KOROSHI S4T PRIORIDAD: apagado (%s = apagado)', logica.PARAM_PRIORIDAD_MODO)
            return False
        yo = self.sudo().with_context(allowed_company_ids=[comun.COMPANY_ID], force_company=comun.COMPANY_ID)
        try:
            with candado(yo.env.cr, logica.CLAVE_PRIORIDAD, 0, 'Reparto por prioridad'):
                return yo._repartir(modo, origen)
        except RetryableJobError:
            _logger.warning('KOROSHI S4T PRIORIDAD: ya hay otro reparto en marcha; este no hace nada')
            return False

    @api.model
    def _parar_por_zonas(self):
        """v1.2.0 (R15): True si falta poco para el cron «partir OUT» de koroshi_zonas o ya le toca. Solo lee su
        siguiente hora (sin koroshi_zonas instalado, nunca)."""
        cron = self.env.ref('koroshi_zonas.cron_koroshi_zonas_partir', raise_if_not_found=False)
        if not cron or not cron.sudo().active:
            return False
        margen = logica.leer_entero(self.env['ir.config_parameter'].sudo().get_param(logica.PARAM_PRIORIDAD_MARGEN),
                                    logica.MARGEN_ZONAS_DEFECTO, 0)
        return logica.parar_por_zonas(datetime.datetime.utcnow(), cron.sudo().nextcall, margen)

    def _en_cola(self, outs):
        en_cola = set()
        if outs and 'koroshi.operario.asignacion' in self.env:
            for a in self.env['koroshi.operario.asignacion'].search_read(
                    [('picking_id', 'in', outs.ids), ('tipo', '=', 'out'),
                     ('estado', 'in', ('cola', 'curso', 'oficina'))], ['picking_id']):
                en_cola.add(a['picking_id'][0])
        return en_cola

    def _sorter(self):
        return self.env['stock.location'].search([('barcode', '=', 'SORTER'),
                                                  ('company_id', '=', comun.COMPANY_ID)], limit=1)

    def _prefijo(self):
        return (self.env['ir.config_parameter'].sudo().get_param(logica.PARAM_PRIORIDAD_LOTE)
                or logica.PREFIJO_LOTE_TIENDA)

    def _motivo_empezada(self, p, prefijo, sorter, en_cola):
        """Por que esta OUT no se toca ('' = se puede tocar). v1.2.0: lo usan _candidatas y la comprobacion de
        dentro del savepoint de cada articulo."""
        lote = p.batch_id if 'batch_id' in p._fields else False
        if p.state not in ('confirmed', 'assigned'):
            return 'estado %s' % p.state
        if logica.numero_pedido(p.origin) == logica.SIN_PEDIDO:
            return 'sin numero de pedido'
        if lote and not (lote.name or '').startswith(prefijo):
            return 'en el lote %s' % lote.name
        if p.id in en_cola:
            return 'en el puesto de un operario'
        if sorter and p.location_id == sorter:
            return 'sale del SORTER'
        for ml in p.move_line_ids:
            if ml.qty_done > 0:
                return 'ya tiene unidades leidas'
            if ml.result_package_id:
                return 'ya tiene cajas'
            if sorter and ml.location_id == sorter:
                return 'tiene lineas en el SORTER'
        return ''

    def _comprobar_sin_empezar(self, move_ids):
        """v1.2.0 (R15): dentro del savepoint del articulo, con lo ultimo de la base: si alguna OUT de sus movimientos
        se ha empezado (o ha cambiado de lote o de puesto) desde que se miro, _Saltar."""
        self.env['base'].flush()
        self.env.cache.invalidate()
        pickings = self.env['stock.move'].browse(move_ids).mapped('picking_id')
        prefijo, sorter, en_cola = self._prefijo(), self._sorter(), self._en_cola(pickings)
        for p in pickings:
            motivo = self._motivo_empezada(p, prefijo, sorter, en_cola)
            if motivo:
                raise _Saltar('%s %s: %s' % (p.name, p.origin or '', motivo))

    def _candidatas(self):
        """(OUT validas, [textos de saltadas])"""
        env = self.env
        prefijo = self._prefijo()
        outs = env['stock.picking'].search([
            ('company_id', '=', comun.COMPANY_ID),
            ('picking_type_code', '=', 'outgoing'),
            ('state', 'in', ('confirmed', 'assigned')),
            ('sale_id.s_order_type_id.name', '=', logica.TIPO_TIENDAS),
        ], order='id')
        sorter = self._sorter()
        en_cola = self._en_cola(outs)
        validas = env['stock.picking']
        saltadas = []
        for p in outs:
            motivo = self._motivo_empezada(p, prefijo, sorter, en_cola)
            if motivo:
                saltadas.append('%s %s: %s' % (p.name, p.origin or '', motivo))
            else:
                validas |= p
        return validas, saltadas

    def _por_articulo(self, outs):
        """{product_id: [dict de movimiento]} solo de los articulos en disputa."""
        grupos = {}
        for p in outs:
            numero = logica.numero_pedido(p.origin)
            for m in p.move_lines:
                if m.state not in ESTADOS_MOVE:
                    continue
                grupos.setdefault(m.product_id.id, []).append({
                    'id': m.id, 'picking_id': p.id, 'numero': numero,
                    'pedido': m.product_uom_qty, 'reservado': m.reserved_availability,
                })
        return {prod: sorted(movs, key=logica.clave_prioridad)
                for prod, movs in grupos.items() if logica.en_disputa(movs)}

    def _reservado(self, move_ids):
        moves = self.env['stock.move'].browse(move_ids)
        moves.invalidate_cache()
        return {m.id: m.reserved_availability for m in moves}

    def _repartir_articulo(self, move_ids):
        """Quitar la reserva y volver a reservar en orden. move_ids ya ordenados por prioridad."""
        Move = self.env['stock.move']
        Move.browse(move_ids)._do_unreserve()
        for mid in move_ids:
            m = Move.browse(mid)
            if m.state in ('confirmed', 'partially_available'):
                m._action_assign()
        return self._reservado(move_ids)

    def _repartir(self, modo, origen):
        inicio = time.time()
        cr = self.env.cr
        outs, saltadas = self._candidatas()
        disputa = self._por_articulo(outs)
        mov_info = {}
        for movs in disputa.values():
            for m in movs:
                mov_info[m['id']] = m
        antes_total = {}
        despues_total = {}
        errores = []
        saltados = []           # v1.2.0: articulos con una OUT empezada mientras tanto
        parado = ''             # v1.2.0: se ha parado antes del reparto de zonas
        if modo == 'real':
            guardar(self.env)   # v1.2.0: transaccion nueva: la comprobacion de cada articulo ve lo ultimo de la base
        for n_articulo, (prod_id, movs) in enumerate(disputa.items()):
            if self._parar_por_zonas():
                parado = 'PARADO antes del reparto de zonas: %d de %d articulos sin mirar.' % (
                    len(disputa) - n_articulo, len(disputa))
                break
            ids = [m['id'] for m in movs]
            antes = {m['id']: m['reservado'] for m in movs}
            despues = None
            for intento in range(2):
                try:
                    with cr.savepoint():
                        self._comprobar_sin_empezar(ids)   # v1.2.0 (R15): con lo ultimo de la base
                        despues = self._repartir_articulo(ids)
                        # Todo a la base dentro del savepoint: lo que se deshace es la base, no solo la cache
                        self.env['base'].flush()
                        if modo == 'simular':
                            raise _Deshacer()
                    if modo == 'real':
                        guardar(self.env)
                    break
                except _Deshacer:
                    # Nada de lo simulado puede quedarse en la cache ni pendiente de escribir
                    self.env.clear()
                    break
                except _Saltar as e:
                    self.env.clear()
                    saltados.append('articulo %s: %s' % (prod_id, e))
                    break
                except psycopg2.OperationalError as e:
                    if e.pgcode not in PG_CONCURRENCY_ERRORS_TO_RETRY or intento:
                        errores.append('articulo %s: %s' % (prod_id, e))
                        despues = None
                        if modo == 'real':
                            cr.rollback()
                        self.env.clear()
                        break
                    cr.rollback()
                    self.env.clear()
                    time.sleep(1)
                except Exception as e:  # el savepoint ya lo ha deshecho: ese articulo queda como estaba
                    self.env.clear()
                    errores.append('articulo %s: %s' % (prod_id, e))
                    despues = None
                    break
            if despues is None:
                continue
            antes_total.update(antes)
            despues_total.update(despues)

        # Informe: por OUT y articulo
        lineas = {}
        for mid, a, d in logica.cambios(antes_total, despues_total):
            info = mov_info[mid]
            m = self.env['stock.move'].browse(mid)
            clave = (info['picking_id'], m.product_id.id)
            fila = lineas.setdefault(clave, {'antes': 0.0, 'despues': 0.0, 'numero': info['numero'], 'move': m})
            fila['antes'] += a
            fila['despues'] += d
        Picking = self.env['stock.picking']
        vals_lineas = []
        for (pid, prod), f in sorted(lineas.items(), key=lambda x: (x[1]['numero'], x[0])):
            p = Picking.browse(pid)
            vals_lineas.append((0, 0, {
                'picking_id': pid, 'pedido': p.origin or '', 'tienda': p.partner_id.name or '',
                'product_id': prod, 'antes': f['antes'], 'despues': f['despues'],
                'diferencia': f['despues'] - f['antes'],
            }))
        segundos = time.time() - inicio
        resumen = ['Modo %s: %d OUT de tienda miradas, %d saltadas, %d articulos en disputa, %d lineas cambian, '
                   '%d errores, %.0f s.' % (modo.upper(), len(outs) + len(saltadas), len(saltadas), len(disputa),
                                            len(vals_lineas), len(errores), segundos)]
        if modo == 'simular':
            resumen.append('SIMULAR: no se ha cambiado ninguna reserva. Esto es lo que haria en real.')
        if parado:
            resumen.append(parado)
        if saltados:
            resumen.append('Articulos saltados (una OUT se ha empezado mientras se repartia; se quedan como estaban):')
            resumen += ['  ' + s for s in saltados[:100]]
        if errores:
            resumen.append('Errores (esos articulos se quedan como estaban):')
            resumen += ['  ' + e for e in errores[:50]]
        if saltadas:
            resumen.append('OUT saltadas (no se tocan):')
            resumen += ['  ' + s for s in saltadas[:300]]
        ejecucion = self.create({
            'name': 'Prioridad %s %s' % (comun.ahora_local().strftime('%d/%m %H:%M'), modo),
            'modo': modo, 'origen': origen, 'segundos': segundos,
            'n_out': len(outs) + len(saltadas), 'n_saltadas': len(saltadas), 'n_articulos': len(disputa),
            'n_lineas': len(vals_lineas), 'n_errores': len(errores), 'resumen': '\n'.join(resumen),
            'linea_ids': vals_lineas,
        })
        _logger.info('KOROSHI S4T PRIORIDAD: %s', resumen[0])
        return ejecucion


class PrioridadLinea(models.Model):
    _name = 'koroshi.s4t.prioridad.linea'
    _description = 'KOROSHI: cambio de reserva por prioridad'
    _order = 'id'

    ejecucion_id = fields.Many2one('koroshi.s4t.prioridad', 'Ejecución', required=True, ondelete='cascade',
                                   index=True)
    picking_id = fields.Many2one('stock.picking', 'OUT', ondelete='set null')
    pedido = fields.Char('Pedido')
    tienda = fields.Char('Tienda')
    product_id = fields.Many2one('product.product', 'Artículo', ondelete='set null')
    antes = fields.Float('Reservado antes')
    despues = fields.Float('Reservado después')
    diferencia = fields.Float('Diferencia')
