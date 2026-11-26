# -*- coding: utf-8 -*-
# v1.11.0 (26/11/2026): % de faltante por SKU, modelo-color y modelo (investigación de faltantes del 26/11,
# bin/versiones/20261126_investigacion-faltantes_v1.md, punto 7).
#
#   faltante (uds) = bajas por ajuste − altas por ajuste + lo que está en FALTANTE
#                  = (recibido − salido + devuelto) − (stock − lo que está en FALTANTE)
#   % faltante     = faltante ÷ recibido de proveedor × 100, con dos decimales.
#
# En modelo-color y modelo no se compensan tallas ni colores: «faltante» es la suma de lo que falta en cada SKU y
# «sobrante», la de lo que sobra (lo de más en otra talla no tapa lo que falta en esta).
#
# Tabla propia que se rellena entera con SQL (cron cada hora y menú «Recalcular»): leer stock_move entero cada vez
# que se abre la pantalla sería lento. Solo lee stock_move, stock_quant, stock_location, productos y, si existe,
# koroshi_kpi_falta. Solo escribe en su tabla (y, desde la v1.12.0, el correo diario: relativo_correo.py). No
# añade campos a tablas compartidas.
import logging
from datetime import timedelta

from psycopg2 import OperationalError
from psycopg2.extras import execute_values

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.addons.koroshi_base import comun

_logger = logging.getLogger(__name__)

# Prendas: «2621CL52-000039-XXL» (4 cifras, 2 letras, 2 cifras). Deja fuera SUMI y demás consumibles.
PATRON_PRENDA = '^[0-9]{4}[A-Z]{2}[0-9]{2}-'

PARAM_VIGILAR = 'koroshi_faltantes.vigilar_pct'
PARAM_ALARMA = 'koroshi_faltantes.alarma_pct'
PARAM_CRITICO = 'koroshi_faltantes.critico_pct'
DEF_VIGILAR, DEF_ALARMA, DEF_CRITICO = 2.0, 7.0, 10.0

ALERTAS = [('ok', 'Bien'), ('vigilar', 'Vigilar'), ('alarma', 'Alarma'), ('critico', 'Crítico')]

SQL_MOVIMIENTOS = """
    SELECT m.product_id,
           SUM(CASE WHEN ls.usage = 'supplier' AND ld.usage = 'internal' THEN m.product_qty
                    WHEN ls.usage = 'internal' AND ld.usage = 'supplier' THEN -m.product_qty ELSE 0 END),
           SUM(CASE WHEN ls.usage = 'internal' AND ld.usage = 'customer' THEN m.product_qty ELSE 0 END),
           SUM(CASE WHEN ls.usage = 'customer' AND ld.usage = 'internal' THEN m.product_qty ELSE 0 END),
           SUM(CASE WHEN ls.usage = 'internal' AND ld.usage = 'inventory' THEN m.product_qty ELSE 0 END),
           SUM(CASE WHEN ls.usage = 'inventory' AND ld.usage = 'internal' THEN m.product_qty ELSE 0 END),
           MAX(CASE WHEN ls.usage = 'internal' AND ld.usage = 'inventory' THEN m.date END),
           pt.name
      FROM stock_move m
      JOIN stock_location ls ON ls.id = m.location_id
      JOIN stock_location ld ON ld.id = m.location_dest_id
      JOIN product_product pp ON pp.id = m.product_id
      JOIN product_template pt ON pt.id = pp.product_tmpl_id
     WHERE m.state = 'done' AND m.company_id = %(cia)s AND pt.name ~ %(patron)s
     GROUP BY m.product_id, pt.name
"""

SQL_STOCK = """
    SELECT q.product_id,
           SUM(q.quantity),
           SUM(CASE WHEN l.parent_path LIKE %(faltant)s THEN q.quantity ELSE 0 END)
      FROM stock_quant q
      JOIN stock_location l ON l.id = q.location_id
     WHERE l.usage = 'internal' AND q.company_id = %(cia)s
     GROUP BY q.product_id
"""

SQL_FALTAS = """
    SELECT product_id, COUNT(*), COUNT(DISTINCT tienda)
      FROM koroshi_kpi_falta
     WHERE fecha >= %(desde)s
     GROUP BY product_id
"""

COLUMNAS = ('nivel', 'name', 'product_id', 'modelo', 'color', 'recibido', 'salido', 'devuelto', 'bajas', 'altas',
            'en_faltante', 'stock', 'faltante', 'sobrante', 'neto', 'pct', 'skus', 'faltas_7d', 'tiendas_7d',
            'ultimo_ajuste', 'alerta', 'calculado', 'company_id', 'create_uid', 'create_date', 'write_uid',
            'write_date')


class KoroshiFaltanteRelativo(models.Model):
    _name = 'koroshi.faltante.relativo'
    _description = 'KOROSHI % de faltante (faltante ÷ recibido)'
    _order = 'pct desc, faltante desc, name'

    nivel = fields.Selection([('sku', 'SKU'), ('color', 'Modelo-color'), ('modelo', 'Modelo')], 'Nivel',
                             required=True, index=True, readonly=True)
    name = fields.Char('SKU / modelo', required=True, index=True, readonly=True)
    product_id = fields.Many2one('product.product', 'Artículo', readonly=True, index=True)
    modelo = fields.Char('Modelo', index=True, readonly=True)
    color = fields.Char('Color', readonly=True)
    recibido = fields.Float('Recibido', digits=(16, 0), readonly=True, help='De proveedor (menos lo devuelto a él).')
    salido = fields.Float('Salido', digits=(16, 0), readonly=True, help='A clientes (tiendas, web, marketplaces).')
    devuelto = fields.Float('Devuelto', digits=(16, 0), readonly=True, help='De clientes a una ubicación interna.')
    bajas = fields.Float('Bajas por ajuste', digits=(16, 0), readonly=True,
                         help='A «Inventory adjustment» o «Scrap»: puestas a 0, ajustes de inventario, contenedores, '
                              'no encontrados de la ronda.')
    altas = fields.Float('Altas por ajuste', digits=(16, 0), readonly=True)
    en_faltante = fields.Float('En FALTANTE', digits=(16, 0), readonly=True,
                               help='Uds en la ubicación FALTANTE: no encontradas y aún sin revisar en una ronda.')
    stock = fields.Float('Stock hoy', digits=(16, 0), readonly=True, help='Interno, FALTANTE incluido.')
    faltante = fields.Float('Faltante (uds)', digits=(16, 0), readonly=True,
                            help='SKU: bajas − altas + en FALTANTE, si es positivo. Modelo-color y modelo: suma de lo '
                                 'que falta en cada SKU (no se compensa con lo que sobra en otro).')
    sobrante = fields.Float('Sobrante (uds)', digits=(16, 0), readonly=True,
                            help='SKU: lo que hay de más que lo recibido − salido. Grupos: suma de los SKU con sobrante.')
    neto = fields.Float('Neto (uds)', digits=(16, 0), readonly=True, help='Faltante − sobrante.')
    pct = fields.Float('% faltante', digits=(16, 2), readonly=True, group_operator=False,
                       help='Faltante ÷ recibido × 100. Lo que pidió Andrés (KOROSHI) el 18/11.')
    skus = fields.Integer('SKU', readonly=True, help='SKU con algo recibido dentro del modelo-color o modelo.')
    faltas_7d = fields.Integer('Faltas 7 días', readonly=True,
                               help='Líneas de pedido de tienda canceladas o sin servir por falta en los últimos 7 días '
                                    '(koroshi.kpi.falta).')
    tiendas_7d = fields.Integer('Tiendas 7 días', readonly=True)
    ultimo_ajuste = fields.Datetime('Última baja', readonly=True)
    alerta = fields.Selection(ALERTAS, 'Alerta', readonly=True, index=True)
    calculado = fields.Datetime('Calculado', readonly=True)
    company_id = fields.Many2one('res.company', 'Empresa', readonly=True)

    # ------------------------------------------------------------------ umbrales
    @api.model
    def _umbrales(self):
        icp = self.env['ir.config_parameter'].sudo()

        def leer(clave, defecto):
            try:
                return float(icp.get_param(clave, defecto))
            except (TypeError, ValueError):
                _logger.warning('KOROSHI %% faltante: parámetro %s no es un número; uso %s', clave, defecto)
                return defecto
        return leer(PARAM_VIGILAR, DEF_VIGILAR), leer(PARAM_ALARMA, DEF_ALARMA), leer(PARAM_CRITICO, DEF_CRITICO)

    @staticmethod
    def _alerta(pct, faltante, umbrales):
        vigilar, alarma, critico = umbrales
        if faltante < 1:
            return 'ok'
        if pct >= critico:
            return 'critico'
        if pct >= alarma:
            return 'alarma'
        if pct >= vigilar:
            return 'vigilar'
        return 'ok'

    # ------------------------------------------------------------------ recálculo
    @api.model
    def recalcular(self):
        """Vacía la tabla y la vuelve a llenar. Cron cada hora y menú «Recalcular»."""
        if not (self.env.su or self.env.user.has_group('stock.group_stock_manager')):
            raise AccessError(_('Solo los responsables de almacén pueden recalcular el % de faltante.'))
        cr = self.env.cr
        try:
            cr.execute('LOCK TABLE koroshi_faltante_relativo IN EXCLUSIVE MODE NOWAIT')
        except OperationalError:
            raise UserError(_('Ya se está recalculando el % de faltante. Prueba otra vez en un minuto.'))
        inicio = fields.Datetime.now()
        cia = comun.COMPANY_ID
        faltant = self.env.ref('koroshi_faltantes.ubicacion_faltant', raise_if_not_found=False)
        faltant_path = (faltant.parent_path + '%') if faltant and faltant.parent_path else '-'

        cr.execute(SQL_MOVIMIENTOS, {'cia': cia, 'patron': PATRON_PRENDA})
        movs = cr.fetchall()
        cr.execute(SQL_STOCK, {'cia': cia, 'faltant': faltant_path})
        stock = {r[0]: (r[1] or 0.0, r[2] or 0.0) for r in cr.fetchall()}
        faltas = {}
        cr.execute("SELECT to_regclass('koroshi_kpi_falta')")
        if cr.fetchone()[0]:
            desde = comun.hoy_local() - timedelta(days=7)
            cr.execute(SQL_FALTAS, {'desde': desde})
            faltas = {r[0]: (r[1], r[2]) for r in cr.fetchall()}

        umbrales = self._umbrales()
        uid = self.env.uid
        filas, grupos = [], {}
        for pid, rec, sal, dev, baj, alt, ult, nombre in movs:
            rec, sal, dev, baj, alt = (x or 0.0 for x in (rec, sal, dev, baj, alt))
            if rec <= 0:
                continue
            st, en_f = stock.get(pid, (0.0, 0.0))
            neto = baj - alt + en_f
            falt, sobr = max(neto, 0.0), max(-neto, 0.0)
            pct = round(falt * 100.0 / rec, 2)
            partes = nombre.split('-')
            modelo = partes[0]
            color = partes[1] if len(partes) > 1 else ''
            n7, t7 = faltas.get(pid, (0, 0))
            filas.append(('sku', nombre, pid, modelo, color, rec, sal, dev, baj, alt, en_f, st, falt, sobr, neto, pct,
                          1, n7, t7, ult, self._alerta(pct, falt, umbrales)))
            for nivel, clave in (('color', '%s-%s' % (modelo, color)), ('modelo', modelo)):
                g = grupos.setdefault((nivel, clave), {'modelo': modelo, 'color': color if nivel == 'color' else '',
                                                       'v': [0.0] * 10, 'skus': 0, 'n7': 0, 't7': 0, 'ult': None})
                for i, x in enumerate((rec, sal, dev, baj, alt, en_f, st, falt, sobr, neto)):
                    g['v'][i] += x
                g['skus'] += 1
                g['n7'] += n7
                g['t7'] = max(g['t7'], t7)
                if ult and (not g['ult'] or ult > g['ult']):
                    g['ult'] = ult
        for (nivel, clave), g in grupos.items():
            rec, sal, dev, baj, alt, en_f, st, falt, sobr, neto = g['v']
            pct = round(falt * 100.0 / rec, 2) if rec else 0.0
            filas.append((nivel, clave, None, g['modelo'], g['color'], rec, sal, dev, baj, alt, en_f, st, falt, sobr,
                          neto, pct, g['skus'], g['n7'], g['t7'], g['ult'], self._alerta(pct, falt, umbrales)))

        cr.execute('DELETE FROM koroshi_faltante_relativo')
        execute_values(cr, 'INSERT INTO koroshi_faltante_relativo (%s) VALUES %%s' % ', '.join(COLUMNAS),
                       [f + (inicio, cia, uid, inicio, uid, inicio) for f in filas], page_size=1000)
        self.invalidate_cache()
        _logger.info('KOROSHI %% faltante: %d filas (%d SKU) en %.1f s', len(filas), len(movs),
                     (fields.Datetime.now() - inicio).total_seconds())
        return True

    @api.model
    def action_recalcular(self):
        self.recalcular()
        return self.env.ref('koroshi_faltantes.action_koroshi_faltante_relativo_sku').read()[0]

    @api.model
    def cron_recalcular(self):
        try:
            self.recalcular()
        except UserError as e:
            _logger.info('KOROSHI %% faltante: cron saltado (%s)', e)

    # ------------------------------------------------------------------ botones de la lista
    def action_ver(self):
        """SKU: sus movimientos hechos. Modelo-color o modelo: sus SKU."""
        self.ensure_one()
        if self.nivel == 'sku':
            return {
                'type': 'ir.actions.act_window',
                'name': _('Movimientos de %s') % self.name,
                'res_model': 'stock.move.line',
                'view_mode': 'tree,form',
                'domain': [('product_id', '=', self.product_id.id), ('state', '=', 'done')],
            }
        dominio = [('nivel', '=', 'sku'), ('modelo', '=', self.modelo)]
        if self.nivel == 'color':
            dominio.append(('color', '=', self.color))
        return {
            'type': 'ir.actions.act_window',
            'name': _('SKU de %s') % self.name,
            'res_model': 'koroshi.faltante.relativo',
            'view_mode': 'tree',
            'views': [(self.env.ref('koroshi_faltantes.view_koroshi_faltante_relativo_tree').id, 'tree')],
            'search_view_id': self.env.ref('koroshi_faltantes.view_koroshi_faltante_relativo_search').id,
            'domain': dominio,
        }
