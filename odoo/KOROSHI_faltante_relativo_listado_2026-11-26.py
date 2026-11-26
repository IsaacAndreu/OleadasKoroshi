# -*- coding: utf-8 -*-
# KOROSHI - Listado de % de faltante (faltante ÷ recibido) por SKU, modelo-color y modelo (v1.0, 26/11/2026).
# Solo lee un fichero local. Datos leídos de Odoo (compañía 8) el 26/11/2026 por la tarde por JSON-RPC, solo lectura:
#   stock.move hechos (proveedor ↔ interno, interno ↔ clientes, interno ↔ Inventory adjustment/Scrap),
#   stock.quant interno y en EFFEC/FALTANTE (id 695690), koroshi.kpi.falta desde el 19/11.
# Misma fórmula que koroshi_faltantes 1.11.0 (models/relativo.py), que aún no está instalado:
#   faltante = bajas − altas por ajuste + uds en FALTANTE (si es positivo); % = faltante ÷ recibido de proveedor.
#   En modelo-color y modelo se suma lo que falta en cada SKU (no se compensa con lo que sobra en otra talla) y se
#   divide por todo lo recibido del grupo.
# Fuera: el pack de calcetines 2611UN10-000323 (recuento del 29/09: −2.024 uds, la mitad justa de lo recibido; ver
# la hoja «Packs»).
# Entrada (bin/versiones/20261126_faltante-relativo_datos_v1.txt):
#   s|sku|recibido|salido|devuelto|bajas|altas|en_faltante|stock|faltas_7d|ultima_baja(mmdd)   (SKU con % ≥ 2)
#   c|modelo-color|recibido|faltante|sobrante|en_faltante|faltas_7d|skus|skus_con_falta        (≥ 2 %)
#   m|modelo|... igual que c
# Uso: python -I -X utf8 KOROSHI_faltante_relativo_listado_2026-11-26.py <datos.txt> <salida.xlsx>
import sys
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ENT, OUT = sys.argv[1:3]
AZ = PatternFill('solid', fgColor='DDEBF7')
ROJO = PatternFill('solid', fgColor='F4B6B6')
NAR = PatternFill('solid', fgColor='FCE4D6')
AMA = PatternFill('solid', fgColor='FFF2CC')
B = Font(bold=True)
FUENTE = ('Fuente: Odoo nath.tuctuc.com (compañía 8), leído el 26/11/2026 por la tarde, solo lectura. '
          'Faltante = bajas − altas por ajuste + uds en FALTANTE; % = faltante ÷ recibido de proveedor.')


def alerta(p):
    return 'Crítico (≥ 10 %)' if p >= 10 else 'Alarma (≥ 7 %)' if p >= 7 else 'Vigilar (≥ 2 %)' if p >= 2 else ''


def relleno(p):
    return ROJO if p >= 10 else NAR if p >= 7 else AMA if p >= 2 else None


def hoja(wb, titulo, nota, cab, filas, anchos, col_pct, primera=False):
    ws = wb.active if primera else wb.create_sheet()
    ws.title = titulo
    ws['A1'] = titulo
    ws['A1'].font = Font(bold=True, size=13)
    ws['A2'] = nota
    for i, h in enumerate(cab, 1):
        c = ws.cell(4, i, h)
        c.font = B
        c.fill = AZ
        c.alignment = Alignment(wrap_text=True, vertical='top')
    for r, f in enumerate(filas, 5):
        for i, v in enumerate(f, 1):
            ws.cell(r, i, v)
        if col_pct:
            p = f[col_pct - 1]
            ws.cell(r, col_pct).number_format = '0.00'
            if relleno(p):
                for i in (1, col_pct, col_pct + 1):
                    ws.cell(r, i).fill = relleno(p)
    for i, w in enumerate(anchos, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = 'B5'
    if filas:
        ws.auto_filter.ref = 'A4:%s%d' % (get_column_letter(len(cab)), 4 + len(filas))
    return ws


s, c, m = [], [], []
for lin in open(ENT, encoding='utf-8'):
    p = lin.rstrip('\n').split('|')
    if len(p) < 3:
        continue
    clave = p[1].replace('~', '-0000')
    if p[0] == 's':
        rec, sal, dev, baj, alt, enf, st, f7 = (float(x) for x in p[2:10])
        ult = ('%s/%s/2026' % (p[10][2:], p[10][:2])) if len(p) > 10 and p[10] else ''
        falt = max(baj - alt + enf, 0)
        pct = round(falt * 100 / rec, 2)
        s.append([clave, pct, alerta(pct), falt, rec, sal, dev, baj, alt, enf, st, f7, ult, clave[:2]])
    else:
        rec, falt, sob, enf, f7, n, nf = (float(x) for x in p[2:9])
        pct = round(falt * 100 / rec, 2)
        (c if p[0] == 'c' else m).append([clave, pct, alerta(pct), falt, rec, sob, enf, f7, int(n), int(nf), clave[:2]])

for lst in (s, c, m):
    lst.sort(key=lambda f: (-f[1], -f[3]))

wb = openpyxl.Workbook()
cuenta = lambda lst, lo, hi: sum(1 for f in lst if lo <= f[1] < hi)
res = []
for nombre, lst, total in (('SKU', s, 814), ('Modelo-color', c, 487), ('Modelo', m, 390)):
    res.append([nombre, cuenta(lst, 10, 1e9), cuenta(lst, 7, 10), cuenta(lst, 2, 7), total])
hoja(wb, 'Resumen', FUENTE,
     ['Nivel', 'Crítico (≥ 10 %)', 'Alarma (7-10 %)', 'Vigilar (2-7 %)', 'Con algo de faltante (cualquier %)'],
     res + [[], ['Global (prendas, sin packs)', 'Faltante 1.728 uds sobre 622.909 recibidas = 0,28 %'],
            ['Temporada OI 26/27', 'Faltante 1.538 uds sobre 541.627 recibidas = 0,28 %'],
            ['Sobrante (SKU con más stock que recibido − salido)', '51.616 uds, casi todo cargas iniciales de '
             'temporadas anteriores hechas como ajuste (no son sobrante real)'],
            [], ['Cómo leerlo', 'Un SKU al 10 % ha perdido 1 de cada 10 uds recibidas (dado de baja por ajuste o '
                 'en FALTANTE sin encontrar). Columna «Faltas 7 días» = líneas de pedido de tienda que no se han '
                 'servido por falta desde el 19/11.'],
            ['Ojo con lo poco recibido', 'Un SKU con 1-10 uds recibidas sale muy alto con 1 sola ud: filtrar '
             '«Recibido» para ver lo que pesa.']],
     [40, 18, 18, 18, 22], None, primera=True)
hoja(wb, 'SKU', FUENTE + ' Solo SKU con % ≥ 2.',
     ['SKU', '% faltante', 'Alerta', 'Faltante (uds)', 'Recibido', 'Salido', 'Devuelto', 'Bajas por ajuste',
      'Altas por ajuste', 'En FALTANTE', 'Stock hoy', 'Faltas tiendas 7 días', 'Última baja', 'Temporada'],
     s, [22, 10, 16, 10, 9, 9, 9, 10, 10, 10, 9, 11, 11, 9], 2)
hoja(wb, 'Modelo-color', FUENTE + ' No se compensan tallas. Solo con % ≥ 2.',
     ['Modelo-color', '% faltante', 'Alerta', 'Faltante (uds)', 'Recibido', 'Sobrante en otras tallas',
      'En FALTANTE', 'Faltas tiendas 7 días', 'SKU', 'SKU con falta', 'Temporada'],
     c, [20, 10, 16, 10, 9, 12, 10, 11, 7, 9, 9], 2)
hoja(wb, 'Modelo', FUENTE + ' No se compensan tallas ni colores. Solo con % ≥ 2.',
     ['Modelo', '% faltante', 'Alerta', 'Faltante (uds)', 'Recibido', 'Sobrante en otras tallas/colores',
      'En FALTANTE', 'Faltas tiendas 7 días', 'SKU', 'SKU con falta', 'Temporada'],
     m, [14, 10, 16, 10, 9, 14, 10, 11, 7, 9, 9], 2)
hoja(wb, 'Packs', 'Pack de calcetines 2611UN10-000323: fuera del listado. El 29/09 un ajuste de inventario quitó '
     'exactamente la mitad de lo recibido en cada talla. Hipótesis: se recibió en unidades y se cuenta en packs '
     '(o al revés). Revisar la unidad de medida antes de darlo por faltante.',
     ['SKU', 'Recibido', 'Salido', 'Bajas por ajuste (29/09)', 'Stock hoy', 'Bajas ÷ recibido'],
     [['2611UN10-000323-S', 202, 14, 101, 87, '50 %'], ['2611UN10-000323-M', 1042, 39, 521, 482, '50 %'],
      ['2611UN10-000323-L', 1162, 52, 581, 529, '50 %'], ['2611UN10-000323-XL', 940, 23, 470, 447, '50 %'],
      ['2611UN10-000323-XXL', 460, 15, 230, 215, '50 %'], ['2611UN10-000323-3XL', 242, 7, 121, 114, '50 %']],
     [22, 10, 10, 18, 10, 14], None)
wb.save(OUT)
print('Escrito', OUT, len(s), len(c), len(m))
