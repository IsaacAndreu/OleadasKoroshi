# -*- coding: utf-8 -*-
# =============================================================================
# Datos sinteticos con la forma de los de produccion (ubicaciones L.. P.. C.., MU-xx, N1-L..; varias OUT
# por pedido; tipos de prenda por referencia). Con semilla: siempre los mismos. Solo para comparar el motor
# con la accion original mientras no haya volcados reales.
# =============================================================================
import random

TIPOS = ['JA', 'XC', 'ZB', 'SU', 'TR', 'CL', 'PT', 'PL', 'ML', 'VS', 'FA', 'TP', 'BL', 'ZC', 'QQ']


def generar(semilla, n_pedidos=60, ahora='2026-11-10 05:00:00', sorter_id=999, raros=True):
    rnd = random.Random(semilla)
    productos = []
    for i in range(400):
        tipo = rnd.choice(TIPOS)
        codigo = rnd.random() < 0.02 and False or '2621%s%02d-%04d' % (tipo, rnd.randint(10, 99), i)
        volumen = rnd.random() < 0.15 and round(rnd.uniform(0.001, 0.012), 4) or 0.0
        productos.append((1000 + i, codigo, volumen))
    ubicaciones = []
    for i in range(300):
        r = rnd.random()
        if r < 0.75:
            lin = rnd.randint(1, 136)
            padre = 'EFFEC/Stock/NAVE2/%05d - L%02d P%02d C%d' % (28000 + i, lin, rnd.randint(1, 36), rnd.randint(1, 4))
        elif r < 0.88:
            padre = 'EFFEC/Stock/NAVE2/N1-L%02d P%02d C1' % (rnd.randint(1, 20), rnd.randint(1, 36))
        else:
            padre = 'EFFEC/Stock/NAVE2/MU-%02d' % rnd.randint(0, 14)
        ubicaciones.append((5000 + i, padre))
    outs = []
    id_out = 100
    id_ml = 10000
    for n in range(n_pedidos):
        k = rnd.randint(1, 90)
        tienda = 'K%d - TIENDA%d' % (k, k)
        if rnd.random() < 0.05:
            tienda = 'WEB %d' % n
        pedido = 'S-%010d' % (6665000000 + n)
        for j in range(rnd.randint(1, 6)):
            id_out += 1
            lineas = []
            demanda = 0.0
            for _ in range(rnd.randint(1, 30)):
                id_ml += 1
                pid, codigo, vol = rnd.choice(productos)
                uid, padre = rnd.choice(ubicaciones)
                qty = rnd.choice([1, 1, 1, 2, 2, 3, 4, 6]) * 1.0
                if raros and rnd.random() < 0.03:
                    qty = 0.0
                hijo = rnd.random() < 0.9
                lineas.append({
                    'id': id_ml, 'move_id': id_ml * 10, 'qty': qty, 'qty_done': 0.0,
                    'location_id': hijo and uid * 10 + rnd.randint(0, 3) or uid,
                    'location_complete_name': hijo and '%s/KO_%06d' % (padre, rnd.randint(0, 999999)) or padre,
                    'location_name': hijo and 'KO_x' or padre.split('/')[-1],
                    'parent_id': hijo and uid or 4000,
                    'parent_complete_name': hijo and padre or 'EFFEC/Stock/NAVE2',
                    'product_id': pid, 'default_code': codigo, 'volume': vol,
                })
                demanda += qty
            if rnd.random() < 0.3:
                lineas = list(reversed(lineas))     # el orden de p.move_line_ids no es siempre por id
            rid = rnd.random()
            estado = 'assigned'
            tipo = 'PED. TIENDAS'
            lote = rnd.random() < 0.5 and 'TIENDA-1011' or ''
            ubic = 8
            if raros:
                if rid < 0.03:
                    tipo = 'PED. WEB'
                elif rid < 0.05:
                    lote = 'B-KOR-0001'
                elif rid < 0.06:
                    ubic = sorter_id
                elif rid < 0.08:
                    estado = 'confirmed'
                elif rid < 0.10 and lineas:
                    lineas[0]['qty_done'] = 1.0
            outs.append({
                'id': id_out, 'name': 'EFFEC/OUT/%05d' % (24000 + id_out), 'company_id': 8,
                'picking_type_code': 'outgoing', 'state': estado, 'tipo_pedido': tipo, 'batch_name': lote,
                'location_id': ubic, 'partner_name': tienda, 'origin': pedido,
                'create_date': '2026-11-10 03:%02d:00' % rnd.randint(0, 59),
                'demanda': demanda + rnd.choice([0.0, 0.0, 2.0]), 'lineas': lineas,
            })
    rnd.shuffle(outs)
    return {'ahora': ahora, 'sorter_id': sorter_id, 'lotes_existentes': [], 'outs': outs}
