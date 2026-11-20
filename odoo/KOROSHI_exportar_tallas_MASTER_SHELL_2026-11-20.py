# -*- coding: utf-8 -*-
# KOROSHI - Exportar datos por talla para el MASTER OI 26/27 (v1.0, 20/11/2026). SOLO LECTURA.
# Versión para «odoo-bin shell» en el servidor (no necesita clave de Odoo). Mismo contenido que
# odoo/KOROSHI_exportar_tallas_MASTER_DIAGNOSTICO_2026-11-19.py, que va por XML-RPC desde el PC.
# Uso en el servidor:
#   odoo-bin shell -c /opt/nath-erp/nath-erp.conf -d NATH_PRODUCTION --no-http < este_fichero.py
# Escribe /tmp/koroshi_tallas_MASTER.csv. No escribe nada en la base de datos: termina con rollback.
import csv
import datetime

COMPANY_ID = 8
SALIDA = '/tmp/koroshi_tallas_MASTER.csv'
MODELOS = [
    '2621CL01', '2621CL03', '2621CL04', '2621CL05', '2621CL30', '2621CL31', '2621CL47', '2621CL48', '2621CL50', '2621CL51', '2621CL52', '2621CL53',
    '2621CL54', '2621CL56', '2621CL58', '2621CL59', '2621CL60', '2621CL61', '2621CL62', '2621CL63', '2621CL64', '2621JA00', '2621JA01', '2621JA03',
    '2621JA04', '2621JA05', '2621JA06', '2621JA07', '2621JA08', '2621JA09', '2621JA10', '2621JA11', '2621JA12', '2621JA13', '2621JA14', '2621JA15',
    '2621JA16', '2621JA17', '2621JA18', '2621JA19', '2621JA22', '2621JA23', '2621JA27', '2621JA28', '2621JA29', '2621JA31', '2621JA40', '2621JA41',
    '2621JA42', '2621JA44', '2621JA45', '2621JA46', '2621JA47', '2621JA49', '2621JA50', '2621JA51', '2621JA53', '2621JA54', '2621JA55', '2621JA56',
    '2621JA57', '2621JA59', '2621JA60', '2621JA61', '2621JA62', '2621JA63', '2621JA64', '2621JA65', '2621JA66', '2621JA67', '2621JA68', '2621JA69',
    '2621JA71', '2621JA84', '2621JA95', '2621JA96', '2621ML00', '2621ML02', '2621ML05', '2621ML07', '2621ML08', '2621ML09', '2621ML10', '2621ML12',
    '2621ML13', '2621ML14', '2621ML19', '2621ML20', '2621ML22', '2621ML25', '2621ML26', '2621ML36', '2621ML65', '2621PL04', '2621PL06', '2621PL08',
    '2621PL09', '2621PL12', '2621PL13', '2621PL21', '2621PL26', '2621PL27', '2621PL28', '2621PL44', '2621PL50', '2621PT03', '2621PT04', '2621PT05',
    '2621PT06', '2621PT07', '2621PT08', '2621PT09', '2621PT10', '2621PT11', '2621PT13', '2621PT14', '2621PT15', '2621PT17', '2621PT18', '2621PT20',
    '2621PT21', '2621PT22', '2621PT23', '2621PT26', '2621PT27', '2621PT28', '2621PT29', '2621PT30', '2621PT31', '2621PT32', '2621PT34', '2621PT35',
    '2621PT37', '2621PT39', '2621PT40', '2621PT41', '2621PT42', '2621PT44', '2621PT50', '2621PT51', '2621PT52', '2621PT54', '2621PT55', '2621PT60',
    '2621PT61', '2621PT62', '2621PT63', '2621PT64', '2621PT84', '2621PT85', '2621PT86', '2621PT87', '2621PT88', '2621PT89', '2621PT90', '2621SU01',
    '2621SU02', '2621SU03', '2621SU04', '2621SU06', '2621SU08', '2621SU09', '2621SU10', '2621SU13', '2621SU17', '2621SU18', '2621SU22', '2621SU23',
    '2621SU28', '2621SU32', '2621SU34', '2621SU36', '2621SU37', '2621SU38', '2621SU41', '2621SU52', '2621SU60', '2621SU61', '2621TR05', '2621TR07',
    '2621TR10', '2621TR13', '2621TR15', '2621TR17', '2621TR18', '2621TR24', '2621TR30', '2621TR32', '2621TR34', '2621TR35', '2621TR36', '2621TR41',
    '2621TR44', '2621TR45', '2621TR46', '2621TR48', '2621TR50', '2621TR56', '2621TR58', '2621TR59', '2621TR60', '2621TR61', '2621TR68', '2621TR70',
    '2621TR72', '2621TR73', '2621TR75', '2621TR76', '2621TR77', '2621XC02', '2621XC04', '2621XC05', '2621XC07', '2621ZC01', '2621ZC04', '2621ZC10',
    '2622BL00', '2622BL01', '2622BL02', '2622BL03', '2622BL04', '2622BL05', '2622BL06', '2622BL11', '2622BL12', '2622BL15', '2622BL21', '2622BL24',
    '2622BL25', '2622FA01', '2622FA02', '2622FA03', '2622FA05', '2622FA10', '2622FA19', '2622FA54', '2622FA69', '2622JA00', '2622JA02', '2622JA04',
    '2622JA07', '2622JA08', '2622JA10', '2622JA11', '2622JA12', '2622JA13', '2622JA14', '2622JA15', '2622JA16', '2622JA17', '2622JA18', '2622JA19',
    '2622JA24', '2622JA26', '2622JA30', '2622JA44', '2622JA48', '2622JA49', '2622JA50', '2622JA51', '2622JA54', '2622JA56', '2622JA59', '2622JA60',
    '2622JA61', '2622JA63', '2622JA72', '2622JA73', '2622JA75', '2622JA76', '2622JA77', '2622JA78', '2622JA88', '2622JA89', '2622JA90', '2622JA93',
    '2622ML00', '2622ML01', '2622ML02', '2622ML06', '2622ML07', '2622ML08', '2622ML09', '2622ML11', '2622ML13', '2622ML14', '2622ML15', '2622ML16',
    '2622ML17', '2622ML18', '2622ML19', '2622ML20', '2622ML21', '2622ML22', '2622ML25', '2622ML26', '2622ML31', '2622ML33', '2622ML37', '2622ML38',
    '2622ML41', '2622ML42', '2622ML51', '2622ML79', '2622ML84', '2622PT00', '2622PT01', '2622PT02', '2622PT04', '2622PT06', '2622PT07', '2622PT08',
    '2622PT09', '2622PT11', '2622PT12', '2622PT14', '2622PT15', '2622PT16', '2622PT17', '2622PT18', '2622PT20', '2622PT23', '2622PT24', '2622PT26',
    '2622PT27', '2622PT28', '2622PT29', '2622PT30', '2622PT33', '2622PT34', '2622PT39', '2622PT40', '2622PT41', '2622PT42', '2622PT46', '2622PT47',
    '2622PT48', '2622PT49', '2622PT50', '2622PT61', '2622PT62', '2622PT63', '2622PT65', '2622PT67', '2622PT69', '2622PT71', '2622PT92', '2622SU01',
    '2622SU02', '2622SU03', '2622SU06', '2622SU07', '2622SU09', '2622SU57', '2622TP07', '2622TP09', '2622TR00', '2622TR01', '2622TR02', '2622TR03',
    '2622TR04', '2622TR06', '2622TR08', '2622TR10', '2622TR11', '2622TR12', '2622TR15', '2622TR17', '2622TR18', '2622TR20', '2622TR21', '2622TR22',
    '2622TR25', '2622TR26', '2622TR27', '2622TR28', '2622TR30', '2622TR39', '2622TR40', '2622TR71', '2622TR72', '2622TR74', '2622TR76', '2622VS00',
    '2622VS01', '2622VS05', '2622VS06', '2622VS15', '2622VS16', '2622VS17', '2622VS19', '2622VS21', '2622VS25', '2622VS29', '2622VS31', '2622VS34',
    '2622VS36', '2622VS37', '2622VS39', '2622ZB04', '2622ZB06', '2622ZC05', '2623HA02', '2623HA03', '2624CL58', '2624JA02', '2624JA04', '2624JA07',
    '2624JA08', '2624JA12', '2624JA65', '2624JA67', '2624ML01', '2624ML02', '2624PT01', '2624PT03', '2624PT35', '2624PT60', '2624SU01', '2624SU03',
    '2624SU04', '2624TR01', '2624TR02', '2625JA01', '2625JA02', '2625JA03', '2625JA60', '2625ML01', '2625ML02', '2625ML26', '2625PT01', '2625PT02',
    '2625PT03', '2625PT04', '2625SU01', '2625SU02', '2625SU03', '2625TR02', '2625TR20', '2625TR21', '2625TR22', '2625VS05', '2625VS07', '2711JA02',
    '2711JA06', '2711JA08', '2711JA09', '2711JA11', '2711JA25', '2711JA26', '2711JA32', '2711JA71', '2711PT01', '2711PT19', '2711PT25', '2711PT33',
    '2711SU31', '2711SU33', '2711SU34', '2711SU38', '2711SU40', '2711SU42', '2711TR12', '2711TR34', '2711TR49', '2712PT05', '2712PT14',
]

Prod = env['product.product'].with_context(active_test=False)
productos = Prod.browse()
no_encontrados = []
for m in MODELOS:
    p = Prod.search([('name', '=ilike', m + '%')])
    if not p:
        no_encontrados.append(m)
    productos |= p
ids = productos.ids
Move = env['stock.move'].sudo()
Quant = env['stock.quant'].sudo()

def suma(modelo, dominio, campo):
    res = {}
    for i in range(0, len(ids), 500):
        trozo = ids[i:i + 500]
        for g in modelo.read_group(dominio + [('product_id', 'in', trozo)], [campo], ['product_id'], lazy=False):
            if g.get('product_id'):
                res[g['product_id'][0]] = g[campo] or 0.0
    return res

base = [('company_id', '=', COMPANY_ID)]
recibido = suma(Move, base + [('state', '=', 'done'), ('location_id.usage', '=', 'supplier')], 'product_qty')
salidas = suma(Move, base + [('state', '=', 'done'), ('location_dest_id.usage', '=', 'customer')], 'product_qty')
stock = suma(Quant, base + [('location_id.usage', '=', 'internal')], 'quantity')
pendiente, eta_min, eta_max = {}, {}, {}
for i in range(0, len(ids), 500):
    for mv in Move.search(base + [('product_id', 'in', ids[i:i + 500]), ('state', 'not in', ('done', 'cancel', 'draft')),
                                  ('location_id.usage', '=', 'supplier')]):
        pid = mv.product_id.id
        pendiente[pid] = pendiente.get(pid, 0.0) + mv.product_qty
        f = mv.date_expected and str(mv.date_expected)[:10] or ''
        if f:
            eta_min[pid] = min(eta_min.get(pid, f), f)
            eta_max[pid] = max(eta_max.get(pid, f), f)

hoy = str(datetime.date.today())
with open(SALIDA, 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.writer(fh, delimiter=';')
    w.writerow(['modelo', 'color', 'talla', 'referencia', 'ean', 'peso_kg_ficha', 'volumen_m3_ficha', 'recibido',
                'pendiente', 'fecha_prevista_primera', 'fecha_prevista_ultima', 'salidas', 'stock', 'aviso'])
    for p in productos:
        codigo = (p.name or '').split(' ')[0].strip('[]')
        t = codigo.split('-')
        pend = pendiente.get(p.id, 0.0)
        if pend and eta_min.get(p.id) and eta_min[p.id] < hoy:
            aviso = 'Fecha prevista pasada: debería haber llegado'
        elif pend:
            aviso = 'En camino'
        else:
            aviso = ''
        w.writerow([t[0], t[1] if len(t) > 1 else '', '-'.join(t[2:]), p.name, p.barcode or '', p.weight or 0,
                    p.volume or 0, recibido.get(p.id, 0.0), pend, eta_min.get(p.id, ''), eta_max.get(p.id, ''),
                    salidas.get(p.id, 0.0), stock.get(p.id, 0.0), aviso])
env.cr.rollback()
print('KOROSHI_FIN modelos=%d variantes=%d no_encontrados=%d %s' % (len(MODELOS), len(ids), len(no_encontrados), ' '.join(no_encontrados)))
