# -*- coding: utf-8 -*-
"""
KOROSHI - Exportar datos por talla para el MASTER OI 26/27 (v1.0, 19/11/2026). SOLO LECTURA.

Para cada modelo del MASTER saca de Odoo, talla a talla (cada variante = modelo-color-talla):
  - recibido: uds entradas desde proveedor (movimientos hechos de entrada);
  - pendiente: uds de entradas aún no hechas, con la primera y la última fecha prevista (la «ETA»);
  - salidas: uds servidas a clientes (tiendas, web, otros);
  - stock: uds en ubicaciones internas de EFFEC/Stock;
  - peso y volumen de la ficha del artículo (si están rellenos).

Sirve para rellenar la hoja «Por talla» del MASTER y para separar en «Recepción vs compra» lo que está
en camino de lo que debería haber llegado (fecha prevista ya pasada).

No escribe nada: solo search_read y read_group por XML-RPC. Se ejecuta desde el PC, no en el servidor.
Credenciales por variables de entorno (nunca en el código):
  ODOO_URL (p. ej. https://nath.tuctuc.com), ODOO_DB, ODOO_USER, ODOO_PASSWORD

Uso:
  python odoo/KOROSHI_exportar_tallas_MASTER_DIAGNOSTICO_2026-11-19.py --master "bin/versiones/261119_MASTER_OI_26-27_KOROSHI_v8.xlsx"
  python odoo/KOROSHI_exportar_tallas_MASTER_DIAGNOSTICO_2026-11-19.py 2621JA67 2622TP09
  (--csv cambia el fichero de salida; por defecto tallas_MASTER_AAAAMMDD.csv en la carpeta actual)
"""
import argparse
import csv
import datetime
import os
import sys
import xmlrpc.client

COMPANY_ID = 8          # Effective Logistics (igual que koroshi_base.comun)
TROZO = 300             # productos por consulta


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
    clave = os.environ['ODOO_PASSWORD']

    def leer(modelo, dominio, campos, orden=None):
        kw = {'fields': campos, 'context': ctx}
        if orden:
            kw['order'] = orden
        return obj.execute_kw(db, uid, clave, modelo, 'search_read', [dominio], kw)

    def agrupar(modelo, dominio, campo_suma, por):
        """Suma campo_suma agrupando por el campo many2one «por». Devuelve {id: suma}."""
        filas = obj.execute_kw(db, uid, clave, modelo, 'read_group', [dominio, [campo_suma], [por]],
                               {'lazy': False, 'context': ctx})
        return {f[por][0]: f[campo_suma] or 0.0 for f in filas if f.get(por)}

    return leer, agrupar


def modelos_del_master(ruta):
    import openpyxl  # solo hace falta con --master
    wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    ws = wb['MASTER por modelo']
    modelos = []
    for fila in ws.iter_rows(min_row=8, min_col=4, max_col=4, values_only=True):
        if fila[0]:
            modelos.append(str(fila[0]).strip())
    return modelos


def partir_nombre(nombre):
    """'2622PT92-000003-36 ...' -> ('2622PT92', '000003', '36'). Si no encaja, deja vacío lo que falte."""
    codigo = (nombre or '').split(' ')[0].strip('[]')
    trozos = codigo.split('-')
    modelo = trozos[0] if trozos else ''
    color = trozos[1] if len(trozos) > 1 else ''
    talla = '-'.join(trozos[2:]) if len(trozos) > 2 else ''
    return modelo, color, talla


def en_trozos(lista, n):
    for i in range(0, len(lista), n):
        yield lista[i:i + n]


def main():
    ap = argparse.ArgumentParser(description='Exportar datos por talla para el MASTER (solo lectura)')
    ap.add_argument('modelos', nargs='*', help='Modelos (2621JA67 ...). Si se usa --master, no hace falta')
    ap.add_argument('--master', help='Excel del MASTER: se leen los modelos de «MASTER por modelo», columna D')
    ap.add_argument('--csv', help='Fichero de salida (por defecto tallas_MASTER_AAAAMMDD.csv)')
    args = ap.parse_args()

    modelos = list(args.modelos)
    if args.master:
        modelos += modelos_del_master(args.master)
    modelos = sorted(set(m for m in modelos if m))
    if not modelos:
        sys.exit('No hay modelos: pasa --master o una lista de modelos')
    salida = args.csv or 'tallas_MASTER_%s.csv' % datetime.date.today().strftime('%Y%m%d')

    leer, agrupar = conectar()

    # 1. Variantes de cada modelo
    productos = []
    for m in modelos:
        encontrados = leer('product.product', [('name', '=ilike', m + '%')],
                           ['name', 'barcode', 'weight', 'volume'], 'name asc')
        if not encontrados:
            print('%s: no se encuentra en Odoo' % m)
        productos += encontrados
    print('%d modelos, %d variantes' % (len(modelos), len(productos)))

    recibido, salidas, stock, pendiente = {}, {}, {}, {}
    eta_min, eta_max = {}, {}
    ids = [p['id'] for p in productos]
    for trozo in en_trozos(ids, TROZO):
        base = [('product_id', 'in', trozo), ('company_id', '=', COMPANY_ID)]
        # 2. Entradas hechas desde proveedor
        recibido.update(agrupar('stock.move', base + [('state', '=', 'done'),
                                                      ('location_id.usage', '=', 'supplier')],
                                'product_qty', 'product_id'))
        # 3. Salidas hechas a clientes
        salidas.update(agrupar('stock.move', base + [('state', '=', 'done'),
                                                     ('location_dest_id.usage', '=', 'customer')],
                               'product_qty', 'product_id'))
        # 4. Stock en ubicaciones internas
        stock.update(agrupar('stock.quant', [('product_id', 'in', trozo), ('company_id', '=', COMPANY_ID),
                                             ('location_id.usage', '=', 'internal')],
                             'quantity', 'product_id'))
        # 5. Entradas pendientes, con fecha prevista
        for mv in leer('stock.move', base + [('state', 'not in', ('done', 'cancel', 'draft')),
                                             ('location_id.usage', '=', 'supplier')],
                       ['product_id', 'product_qty', 'date_expected']):
            pid = mv['product_id'][0]
            pendiente[pid] = pendiente.get(pid, 0.0) + (mv['product_qty'] or 0.0)
            fecha = (mv['date_expected'] or '')[:10]
            if fecha:
                eta_min[pid] = min(eta_min.get(pid, fecha), fecha)
                eta_max[pid] = max(eta_max.get(pid, fecha), fecha)

    hoy = datetime.date.today().isoformat()
    filas = []
    for p in productos:
        pid = p['id']
        modelo, color, talla = partir_nombre(p['name'])
        pend = pendiente.get(pid, 0.0)
        if pend and eta_min.get(pid) and eta_min[pid] < hoy:
            aviso = 'Fecha prevista pasada: debería haber llegado'
        elif pend:
            aviso = 'En camino'
        else:
            aviso = ''
        filas.append({
            'modelo': modelo, 'color': color, 'talla': talla, 'referencia': p['name'],
            'ean': p.get('barcode') or '',
            'peso_kg_ficha': p.get('weight') or 0, 'volumen_m3_ficha': p.get('volume') or 0,
            'recibido': recibido.get(pid, 0.0), 'pendiente': pend,
            'fecha_prevista_primera': eta_min.get(pid, ''), 'fecha_prevista_ultima': eta_max.get(pid, ''),
            'salidas': salidas.get(pid, 0.0), 'stock': stock.get(pid, 0.0), 'aviso': aviso,
        })

    if not filas:
        sys.exit('No se ha encontrado ninguna variante')
    with open(salida, 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()), delimiter=';')
        w.writeheader()
        w.writerows(filas)
    print('Guardado en %s (%d filas). No se ha modificado nada en Odoo.' % (salida, len(filas)))


if __name__ == '__main__':
    main()
