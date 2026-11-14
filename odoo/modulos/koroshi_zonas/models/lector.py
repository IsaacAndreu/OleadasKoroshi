# -*- coding: utf-8 -*-
# =============================================================================
# Lector: lee de Odoo y construye los datos planos que recibe el motor. Solo lee.
# =============================================================================
from odoo.addons.koroshi_base import comun

from ..motor import nombres
from ..motor import volumen

COMPANY_ID = comun.COMPANY_ID   # EFFECTIVE LOGISTICS, S.L. (v1.4.0: de koroshi_base)
CAMPOS_LINEA = ['id', 'picking_id', 'result_package_id', 'qty_done', 'product_id']

# v1.1.2: los nombres se leen con motor/nombres.py (con tests)
partir_nombre_lote = nombres.partir_nombre_lote
cajas_de_nota = nombres.cajas_de_nota
zona_de_nota = nombres.zona_de_nota


def contexto_compania(env):
    ctx = dict(env.context)
    ctx['allowed_company_ids'] = [COMPANY_ID]
    return ctx


def datos_reparto(env, contexto, ahora_local, p):
    """Datos planos para motor.v12f.repartir(), leidos como los lee la accion 1883 (lineas 109-317):
    mismo search, mismo orden de OUT y mismo orden de p.move_line_ids (el coste de cada linea depende
    del orden). ahora_local: datetime con zona horaria (Europe/Madrid). p: parametros del motor.
    v1.3.0 (auditoria 13/11, fase 5): con DIAS_ATRAS > 0 tambien son candidatas las OUT abiertas de los DIAS_ATRAS
    dias anteriores (la 1883 solo miraba las creadas hoy y las de ayer ya no se partian nunca). Van marcadas con
    'de_antes'. Las de dias anteriores que ya estan en la cola de un operario (koroshi_operarios) no se tocan."""
    import datetime
    import pytz
    ctx = contexto_compania(env)
    Picking = env['stock.picking'].with_context(ctx)
    Batch = env['stock.picking.batch'].with_context(ctx)
    tz = pytz.timezone(p['ZONA_HORARIA'])
    medianoche = tz.localize(ahora_local.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None))
    desde = medianoche.astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S')
    dias_atras = max(int(p.get('DIAS_ATRAS') or 0), 0)
    desde_busqueda = desde
    if dias_atras:
        antes = tz.localize(medianoche.replace(tzinfo=None) - datetime.timedelta(days=dias_atras))
        desde_busqueda = antes.astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S')
    hoy = ahora_local.strftime('%d%m')
    sorter = env['stock.location'].with_context(ctx).search([('barcode', '=', 'SORTER'),
                                                             ('company_id', '=', p['COMPANY_ID'])], limit=1)
    prueba_agr = contexto.get('prueba_agrupacion')
    prueba_ids = contexto.get('prueba_ids')
    if prueba_ids:
        candidatas = Picking.browse(prueba_ids).exists()
    elif prueba_agr:
        candidatas = Picking.search([('company_id', '=', p['COMPANY_ID']), ('picking_type_code', '=', 'outgoing'),
                                     ('batch_id.name', '=like', prueba_agr + '%'), ('state', '!=', 'cancel')],
                                    order='name asc')
    else:
        candidatas = Picking.search([
            ('company_id', '=', p['COMPANY_ID']),
            ('picking_type_code', '=', 'outgoing'),
            ('state', '=', 'assigned'),
            ('sale_id.s_order_type_id.name', '=', p['TIPO_PEDIDO']),
            ('create_date', '>=', desde_busqueda),
        ], order='name asc')
    # v1.3.0: de dias anteriores (solo sin prueba). Las que estan en la cola de un operario se quedan como estan.
    de_antes = set()
    en_cola = {}
    if dias_atras and not prueba_ids and not prueba_agr:
        de_antes = set(o.id for o in candidatas if o.create_date and
                       o.create_date.strftime('%Y-%m-%d %H:%M:%S') < desde)
        if de_antes and 'koroshi.operario.asignacion' in env:
            for a in env['koroshi.operario.asignacion'].sudo().search_read(
                    [('picking_id', 'in', list(de_antes)), ('tipo', '=', 'out'),
                     ('estado', 'in', ('cola', 'curso', 'oficina'))], ['picking_id', 'employee_id']):
                en_cola[a['picking_id'][0]] = a['employee_id'] and a['employee_id'][1] or ''
    outs = []
    saltadas = []
    for o in candidatas:
        if o.id in en_cola:
            saltadas.append('%s (%s): de un dia anterior y en la cola de %s' % (
                o.name, o.partner_id.name or '', en_cola[o.id] or 'un operario'))
            continue
        demanda = 0.0
        for m in o.move_lines:
            if m.state not in ('done', 'cancel'):
                demanda += m.product_uom_qty
        lineas = []
        for ml in o.move_line_ids:
            ub = ml.location_id
            lineas.append({
                'id': ml.id,
                'move_id': ml.move_id.id,
                'qty': ml.product_uom_qty,
                'qty_done': ml.qty_done,
                'location_id': ub.id,
                'location_complete_name': ub.complete_name or '',
                'location_name': ub.name or '',
                'parent_id': ub.location_id.id or False,
                'parent_complete_name': ub.location_id.complete_name or '',
                'product_id': ml.product_id.id,
                'default_code': ml.product_id.default_code or False,
                'volume': ml.product_id.volume or 0.0,
            })
        tipo = o.sale_id and o.sale_id.s_order_type_id and o.sale_id.s_order_type_id.name or ''
        outs.append({
            'id': o.id,
            'name': o.name,
            'company_id': o.company_id.id,
            'picking_type_code': o.picking_type_code,
            'state': o.state,
            'tipo_pedido': tipo,
            'batch_name': o.batch_id.name or '',
            'location_id': o.location_id.id,
            'partner_name': o.partner_id.name or '',
            'origin': o.origin or '',
            'create_date': o.create_date and o.create_date.strftime('%Y-%m-%d %H:%M:%S') or '',
            'demanda': demanda,
            'lineas': lineas,
        })
        if o.id in de_antes:
            outs[-1]['de_antes'] = True     # v1.3.0
    return {
        'ahora': ahora_local.strftime('%Y-%m-%d %H:%M:%S'),
        'sorter_id': sorter.id or None,
        'lotes_existentes': Batch.search([('name', '=like', 'Z-%s-%%' % hoy)]).mapped('name'),
        'outs': outs,
        'saltadas_lector': saltadas,        # v1.3.0
    }


def lineas_para_medir(env, pickings, medidas):
    """Lineas leidas (qty_done > 0, sin cancelar) de estas OUT y de cualquier otra OUT que use sus cajas.
    Devuelve la lista de dicts que espera motor.medir.medir()."""
    Line = env['stock.move.line'].sudo()
    propias = Line.search_read([('picking_id', 'in', pickings.ids), ('state', '!=', 'cancel'),
                                ('qty_done', '>', 0)], CAMPOS_LINEA, order='id')
    cajas = list(set([x['result_package_id'][0] for x in propias if x['result_package_id']]))
    otras = []
    if cajas:
        otras = Line.search_read([('result_package_id', 'in', cajas), ('state', '!=', 'cancel'),
                                  ('qty_done', '>', 0), ('picking_id', 'not in', pickings.ids)],
                                 CAMPOS_LINEA, order='id')
    todas = propias + otras
    ids_prod = list(set([x['product_id'][0] for x in todas if x['product_id']]))
    prod = {}
    for p in env['product.product'].sudo().with_context(active_test=False).browse(ids_prod).read(
            ['volume', 'default_code']):
        prod[p['id']] = volumen.litros_ud(p['volume'], p['default_code'], medidas)
    lineas = []
    for x in todas:
        if not x['picking_id']:
            continue
        lit_ud = x['product_id'] and prod.get(x['product_id'][0], medidas.litros_defecto) or medidas.litros_defecto
        lineas.append({
            'id': x['id'],
            'out_id': x['picking_id'][0],
            'caja_id': x['result_package_id'] and x['result_package_id'][0] or None,
            'uds': x['qty_done'],
            'litros': lit_ud * x['qty_done'],
        })
    return lineas
