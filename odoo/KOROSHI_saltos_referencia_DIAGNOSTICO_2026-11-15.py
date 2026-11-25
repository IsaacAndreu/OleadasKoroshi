# -*- coding: utf-8 -*-
"""
KOROSHI - Diagnóstico de «saltos» por referencia (v1.0, 15/11/2026). SOLO LECTURA.

Para cada talla/color de las referencias que se le pasen, saca de Odoo:
  - dónde está el stock (cantidad, reservado, libre), incluida EFFEC/FALTANTE;
  - uds entradas, servidas, pedidas (sin cancelar) y última salida;
  - líneas de pedido sin servir (y si el pedido está cancelado, quién y cuándo);
  - uds puestas a 0 / mandadas a pérdidas (ajustes de inventario) y faltantes registrados (koroshi.faltante);
  - un veredicto: SALTO PROBABLE (había stock y no se sirvió, o stock perdido por ajuste/FALTANTE),
    AGOTADO (se pidió y no había stock) u OK.

No escribe nada: solo search_read por XML-RPC. Se ejecuta desde el PC, no en el servidor.
Credenciales por variables de entorno (nunca en el código):
  ODOO_URL (p. ej. https://nath.tuctuc.com), ODOO_DB, ODOO_USER, ODOO_PASSWORD

Uso:
  python odoo/KOROSHI_saltos_referencia_DIAGNOSTICO_2026-11-15.py 2622PT92-000003
  python odoo/KOROSHI_saltos_referencia_DIAGNOSTICO_2026-11-15.py 2622PT92-000003-36 2621CL56
  python odoo/KOROSHI_saltos_referencia_DIAGNOSTICO_2026-11-15.py --csv saltos.csv 2622PT92 2622PT50

Caso que lo originó: correo de Sonia (Koroshi) del 14/11 sobre 2622PT92 color 3 talla 36.
"""
import argparse
import csv
import os
import sys
import xmlrpc.client

COMPANY_ID = 8          # Effective Logistics (igual que koroshi_base.comun)
FALTANTE = 'EFFEC/FALTANTE'


def conectar():
    falta = [v for v in ('ODOO_URL', 'ODOO_DB', 'ODOO_USER', 'ODOO_PASSWORD') if not os.environ.get(v)]
    if falta:
        sys.exit('Faltan variables de entorno: %s' % ', '.join(falta))
    url, db = os.environ['ODOO_URL'].rstrip('/'), os.environ['ODOO_DB']
    uid = xmlrpc.client.ServerProxy(url + '/xmlrpc/2/common').authenticate(
        db, os.environ['ODOO_USER'], os.environ['ODOO_PASSWORD'], {})
    if not uid:
        sys.exit('Usuario o clave incorrectos')
    obj = xmlrpc.client.ServerProxy(url + '/xmlrpc/2/object', allow_none=True)
    ctx = {'allowed_company_ids': [COMPANY_ID]}

    def leer(modelo, dominio, campos, orden=None):
        kw = {'fields': campos, 'context': ctx}
        if orden:
            kw['order'] = orden
        return obj.execute_kw(db, uid, os.environ['ODOO_PASSWORD'], modelo, 'search_read', [dominio], kw)

    return leer


def nombre_loc(loc):
    return (loc and loc[1] or '').replace('EFFEC/Stock/NAVE2/', '')


def diagnosticar(leer, producto):
    pid = producto['id']
    quants = leer('stock.quant', [('product_id', '=', pid), ('location_id.usage', '=', 'internal')],
                  ['location_id', 'quantity', 'reserved_quantity'])
    lineas = leer('stock.move.line', [('product_id', '=', pid), ('state', '=', 'done')],
                  ['date', 'reference', 'qty_done', 'location_id', 'location_dest_id'], 'date asc')
    ventas = leer('sale.order.line', [('product_id', '=', pid)],
                  ['order_id', 'product_uom_qty', 'qty_delivered', 'state', 'create_date'])
    try:
        faltantes = leer('koroshi.faltante', [('product_id', '=', pid)], ['display_name'])
    except xmlrpc.client.Fault:
        faltantes = []

    en_stock = [q for q in quants if q['location_id'][1].startswith('EFFEC/Stock')]
    en_faltante = sum(q['quantity'] for q in quants if q['location_id'][1] == FALTANTE)
    libre = sum(q['quantity'] - q['reserved_quantity'] for q in en_stock)
    entradas = sum(l['qty_done'] for l in lineas if 'Vendors' in (l['location_id'][1] or ''))
    salidas = [l for l in lineas if 'Customers' in (l['location_dest_id'][1] or '')]
    perdidas = [l for l in lineas if 'Inventory adjustment' in (l['location_dest_id'][1] or '')
                or 'Inventory loss' in (l['location_dest_id'][1] or '')]
    pedido = sum(v['product_uom_qty'] for v in ventas if v['state'] != 'cancel')
    servido = sum(v['qty_delivered'] for v in ventas)
    sin_servir = [v for v in ventas if v['qty_delivered'] < v['product_uom_qty']]

    if perdidas or en_faltante:
        veredicto = 'SALTO PROBABLE: stock perdido por ajuste o en FALTANTE; buscar en la nave'
    elif [v for v in sin_servir if v['state'] != 'cancel'] and libre > 0:
        veredicto = 'SALTO PROBABLE: hay stock libre y pedidos sin servir'
    elif pedido > servido and libre <= 0:
        veredicto = 'AGOTADO: se pide y no hay stock'
    else:
        veredicto = 'OK en Odoo: todo lo pedido se ha servido'

    return {
        'producto': producto['name'], 'ean': producto.get('barcode') or '',
        'ubicaciones': '; '.join('%s q=%g r=%g' % (nombre_loc(q['location_id']), q['quantity'],
                                                   q['reserved_quantity']) for q in quants),
        'libre': libre, 'en_faltante': en_faltante, 'entradas': entradas,
        'servidas': sum(l['qty_done'] for l in salidas), 'pedidas': pedido, 'servido_pedidos': servido,
        'ultima_salida': salidas and salidas[-1]['date'][:10] or '',
        'sin_servir': '; '.join('%s %g/%g %s' % (v['order_id'][1], v['qty_delivered'], v['product_uom_qty'],
                                                 v['state']) for v in sin_servir),
        'a_perdidas': '; '.join('%s %s %g' % (l['date'][:10], nombre_loc(l['location_id']), l['qty_done'])
                                for l in perdidas),
        'faltantes': len(faltantes), 'veredicto': veredicto,
    }


def main():
    ap = argparse.ArgumentParser(description='Diagnóstico de saltos por referencia (solo lectura)')
    ap.add_argument('referencias', nargs='+', help='Referencia o principio (2622PT92-000003, 2622PT92-000003-36)')
    ap.add_argument('--csv', help='Guardar también en este CSV')
    args = ap.parse_args()
    leer = conectar()

    filas = []
    for ref in args.referencias:
        productos = leer('product.product', [('name', '=ilike', ref + '%')], ['name', 'barcode'], 'name asc')
        if not productos:
            print('%s: no se encuentra ningún artículo' % ref)
            continue
        for p in productos:
            f = diagnosticar(leer, p)
            filas.append(f)
            print('\n== %s (EAN %s)' % (f['producto'], f['ean']))
            print('   Stock:      %s' % (f['ubicaciones'] or 'sin stock'))
            print('   Libre: %g · en FALTANTE: %g' % (f['libre'], f['en_faltante']))
            print('   Entradas %g · servidas %g · pedidas %g · última salida %s'
                  % (f['entradas'], f['servidas'], f['pedidas'], f['ultima_salida'] or '-'))
            if f['sin_servir']:
                print('   Sin servir: %s' % f['sin_servir'])
            if f['a_perdidas']:
                print('   A pérdidas: %s' % f['a_perdidas'])
            if f['faltantes']:
                print('   Faltantes registrados: %d' % f['faltantes'])
            print('   -> %s' % f['veredicto'])

    if args.csv and filas:
        with open(args.csv, 'w', newline='', encoding='utf-8-sig') as fh:
            w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()), delimiter=';')
            w.writeheader()
            w.writerows(filas)
        print('\nGuardado en %s' % args.csv)


if __name__ == '__main__':
    main()
