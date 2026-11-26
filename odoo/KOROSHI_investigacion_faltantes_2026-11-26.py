# -*- coding: utf-8 -*-
# KOROSHI - Investigación de faltantes y cancelaciones por falta (v1.0, 26/11/2026). Solo lee ficheros locales.
# Datos: leídos de Odoo (nath.tuctuc.com, compañía 8) el 26/11/2026 por la mañana por JSON-RPC, solo lectura.
#   - Las cifras agregadas van escritas abajo (cada una con su consulta en el informe .md).
#   - El detalle por SKU va en bin/versiones/20261126_investigacion-faltantes_datos-sku_v1.txt
#     (sku|líneas falta|tiendas|uds falta|recibido|salido|ajuste baja|ajuste alta|stock|reservado|stock por zona).
#   - El packing list sale de bin/versiones/20261124_conciliacion-PL-vs-odoo_koroshi_v1.xlsx (hoja «Por modelo-color»).
# Uso: python -I -X utf8 KOROSHI_investigacion_faltantes_2026-11-26.py <datos-sku.txt> <conciliacion.xlsx> <salida.xlsx>
import sys
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ENT, CONC, OUT = sys.argv[1:4]
AZ = PatternFill('solid', fgColor='DDEBF7')
AM = PatternFill('solid', fgColor='FFF2CC')
B = Font(bold=True)
FUENTE = 'Fuente: Odoo nath.tuctuc.com, compañía 8, leído el 26/11/2026 (solo lectura).'

wb = openpyxl.Workbook()


def hoja(titulo, cab, filas, anchos, nota=None, primera=False):
    ws = wb.active if primera else wb.create_sheet()
    ws.title = titulo[:31]
    ws['A1'] = titulo
    ws['A1'].font = Font(bold=True, size=13)
    ws['A2'] = nota or FUENTE
    ws['A2'].alignment = Alignment(wrap_text=False)
    r = 4
    for i, h in enumerate(cab, 1):
        c = ws.cell(r, i, h)
        c.font = B
        c.fill = AZ
        c.alignment = Alignment(wrap_text=True, vertical='top')
    for f in filas:
        r += 1
        for i, v in enumerate(f, 1):
            c = ws.cell(r, i, v)
            if isinstance(v, str) and v.startswith('»'):
                c.value = v[1:]
                c.font = B
                c.fill = AM
    for i, w in enumerate(anchos, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = 'A5'
    return ws


# ---------- Resumen: causas por peso ----------
hoja('Resumen - causas por peso',
     ['Causa', 'SKU', 'Líneas de falta 16-25/11', '% líneas', 'Uds de falta (contadas cada día)', 'Pares tienda-SKU',
      'Qué dice el dato', 'Probado / hipótesis'],
     [
         ['B · Stock 0 porque se dio de baja por ajuste (lo recibido no ha salido entero)', 240, 2798, 0.734, 3126, 839,
          'Ajuste neto −504 uds en esos 240 SKU. 145 SKU perdieron 1 sola ud y dan 1.074 líneas.', 'Dato'],
         ['C · Hay stock en Odoo pero no en un sitio servible (FALTANTE, SORTER, DEVOLUCIÓN, TARKO) o reservado',
          139, 691, 0.181, 748, 324, 'FALTANTE 88 SKU/146 uds; SORTER 11/16; DEVOLUCIÓN 9/11; TARKO 20/37; hueco 38/177.',
          'Dato'],
         ['A · Agotado de verdad: todo lo recibido ya salió (recibido = salido)', 91, 319, 0.084, 336, 192,
          'KOROSHI pide reponer artículos sin unidades en el almacén.', 'Dato'],
         ['D · Nunca recibido', 2, 6, 0.002, 6, 3, '', 'Dato'],
         ['»Total', 472, 3814, 1, 4216, 1358, 'Solo 1.507 uds únicas (pares tienda-SKU): el resto son repeticiones diarias.', ''],
     ], [70, 8, 12, 9, 14, 12, 70, 14],
     nota=FUENTE + ' Base: koroshi.kpi.falta con fecha 16/11–25/11 (3.814 líneas). Clase por SKU con stock.move hecho '
                   '(proveedor, clientes, Inventory adjustment/Scrap) y stock.quant interno de hoy.', primera=True)
ws = wb['Resumen - causas por peso']
for r in range(5, 10):
    ws.cell(r, 4).number_format = '0.0%'

# ---------- P1: ajustes ----------
hoja('P1 Ajustes por tipo',
     ['Tipo (nombre del movimiento)', 'De dónde sale (código)', 'Movimientos', 'Uds', 'Rastro del operario', 'Notas'],
     [
         ['Cantidad de producto actualizada', 'Núcleo de Odoo: stock_quant.py:585 (_set_inventory_quantity, modo inventario, '
          'grupo responsable de inventario). Ningún módulo KOROSHI lo crea.', 782, 3048, 'Ninguno: solo usuario Odoo '
          '(Almacén Nath 841 de 860 movimientos)', 'Incluye SUMI 1.956 uds (08-09/10). Prendas: 743 movimientos / 1.055 uds'],
         ['INV:… (ajuste de inventario)', 'stock.inventory del núcleo (Inventario › Ajustes) o app de código de barras', 53, 5039,
          'Ninguno', 'Pack calcetines 2611UN10 2.024 uds (29/09); SUMI 2.723 uds (23-24/11). Prendas: 41 movimientos / 292 uds'],
         ['KOROSHI contenedor …: poner a cero / cambiar cantidad (Nombre)', 'koroshi_contenedores controllers/main.py:462-511, 627 '
          '(desde v1.5.0, 18/11)', 25, 341, 'Sí: nombre en el movimiento y koroshi.contenedor.movimiento.employee_id',
          'Todos «Jordi Pujol»'],
     ], [42, 60, 12, 10, 40, 60],
     nota=FUENTE + ' stock.move hecho, origen hijo de EFFEC/Stock (id 85), destino Inventory adjustment (id 81), desde 01/08/2026.')

hoja('P1 Puestas a 0 (CPA) prendas',
     ['Corte', 'Valor', 'Movimientos', 'Uds'],
     [['»Por mes', '', '', ''],
      ['Mes', 'agosto', 220, 237], ['Mes', 'septiembre', 188, 241], ['Mes', 'octubre', 160, 277],
      ['Mes', 'noviembre (hasta 26/11)', 175, 300],
      ['»Por cantidad', '', '', ''],
      ['Uds por movimiento', '1', 609, 609], ['Uds por movimiento', '2', 81, 162], ['Uds por movimiento', '3', 23, 69],
      ['Uds por movimiento', '4 o más', 30, 215],
      ['»Por usuario', '', '', ''],
      ['Usuario', 'Almacén Nath (almacen@nath.es, compartido)', 734, ''], ['Usuario', 'Almacen 2', 9, ''],
      ['»Por día de la semana', '', '', ''],
      ['Día', 'lunes', 207, ''], ['Día', 'martes', 102, ''], ['Día', 'miércoles', 154, ''], ['Día', 'jueves', 137, ''],
      ['Día', 'viernes', 137, ''], ['Día', 'sábado', 6, ''],
      ['»Por hora (hora del almacén)', '', '', ''],
      ['Hora', '06', 28, ''], ['Hora', '07', 64, ''], ['Hora', '08', 65, ''], ['Hora', '09', 92, ''], ['Hora', '10', 71, ''],
      ['Hora', '11', 112, ''], ['Hora', '12', 144, ''], ['Hora', '13', 28, ''], ['Hora', '14', 29, ''], ['Hora', '15', 46, ''],
      ['Hora', '16', 62, ''], ['Hora', '17', 2, ''],
      ['»Por lineal (los 15 con más; 122 lineales en total)', '', '', ''],
      ['Lineal', 'L84', 32, ''], ['Lineal', 'L86', 31, ''], ['Lineal', 'L37', 26, ''], ['Lineal', 'L87', 24, ''],
      ['Lineal', 'L88', 23, ''], ['Lineal', 'L51', 17, ''], ['Lineal', 'L83', 16, ''], ['Lineal', 'L42', 15, ''],
      ['Lineal', 'L81', 14, ''], ['Lineal', 'L41', 13, ''], ['Lineal', 'L15', 13, ''], ['Lineal', 'L85', 12, ''],
      ['Lineal', 'L53', 11, ''], ['Lineal', 'L10', 11, ''], ['Lineal', 'L70', 11, ''],
      ['»Cómo se hacen', '', '', ''],
      ['Ráfagas (huecos seguidos a menos de 3 min)', 'sueltos', 306, ''],
      ['Ráfagas', 'de 2', 178, ''], ['Ráfagas', 'de 3', 105, ''], ['Ráfagas', 'de 4 a 9 (lineales distintos)', 154, ''],
      ['Ubicación', 'contenedor dentro de un hueco', 675, ''], ['Ubicación', 'hueco sin contenedor u otra', 68, ''],
      ['»¿Había una OUT preparándose en ese hueco?', '', '', ''],
      ['OUT del mismo SKU y ubicación', 'a ±2 h', 162, ''], ['OUT del mismo SKU y ubicación', 'en las 24 h anteriores', 101, ''],
      ['OUT del mismo SKU y ubicación', 'ninguna', 477, ''], ['Otra operación', 'a ±2 h', 3, ''],
      ['»¿Casan con Faltantes (koroshi.faltante)?', '', '', ''],
      ['CPA desde el 09/11', 'total', 128, ''], ['Con faltante del mismo SKU a ±3 días', '', 2, ''],
      ['Con faltante del mismo SKU y ubicación', '', 0, ''], ['Faltantes con move_cero_id', '', 0, ''],
      ], [44, 44, 12, 10],
     nota=FUENTE + ' stock.move «Cantidad de producto actualizada», EFFEC → Inventory adjustment, desde 01/08/2026, solo '
                   'prendas (código NNNNLLNN, sin packs 2611UN10-000323). Hora: UTC+2 hasta el 25/10, UTC+1 después.')

# ---------- P2: detalle por SKU y PL ----------
pl = {}
wbc = openpyxl.load_workbook(CONC, read_only=True, data_only=True)
for f in wbc['Por modelo-color'].iter_rows(min_row=6, values_only=True):
    if f[0]:
        pl[(str(f[0]), str(f[1]))] = f
        pl.setdefault((str(f[0]), '*'), f) if 'sin desglose' in str(f[1]) else None

grupo, filas = None, {'B': [], 'C': [], 'A': []}
for lin in open(ENT, encoding='utf-8'):
    lin = lin.strip()
    if not lin:
        continue
    if lin.startswith('#'):
        grupo = lin[1:]
        continue
    p = lin.split('|')
    clase = grupo
    if grupo in ('C', 'A'):
        clase, p = p[0], p[1:]
    sku = p[0].replace('~', '-0000')
    n = [float(x) for x in p[1:10]]
    zona = p[10] if len(p) > 10 else ''
    mod, col = sku[:8], sku.split('-')[1] if '-' in sku else ''
    c = pl.get((mod, col)) or pl.get((mod, '*'))
    plc = [c[2], c[5], c[7], c[9]] if c else ['', '', '', 'Sin línea en la conciliación']
    filas[grupo].append([clase, sku] + n[:3] + [n[3], n[4], n[5], n[6], n[5] - n[6],
                                             round((n[5] - n[6]) / n[3], 4) if n[3] else '', n[7], n[8], zona] + plc)

cab = ['Clase', 'SKU', 'Líneas falta', 'Tiendas', 'Uds falta', 'Recibido', 'Salido a clientes', 'Baja por ajuste',
       'Alta por ajuste', 'Ajuste neto (baja − alta)', 'Faltante relativo (neto ÷ recibido)', 'Stock hoy', 'Reservado',
       'Stock por zona (H hueco, F FALTANTE, S SORTER, D DEVOL., T TARKO)', 'PL llegado (modelo-color)',
       'Recibido Odoo (modelo-color)', 'Diferencia PL (modelo-color)', 'Clase PL (conciliación 24/11)']
anch = [6, 22, 9, 8, 8, 9, 9, 9, 9, 10, 11, 8, 9, 22, 11, 11, 11, 40]
for g, t in (('B', 'P2 Stock 0 por ajuste (B)'), ('C', 'P3 Con stock en Odoo (C)'), ('A', 'P2 Agotados (A y D)')):
    ws = hoja(t, cab, filas[g], anch,
              nota=FUENTE + ' Los 70 SKU con más líneas de falta de cada grupo (A/D: 40). PL = conciliación del 24/11 por '
                            'modelo-color (el PL no trae talla).')
    for r in range(5, 5 + len(filas[g])):
        ws.cell(r, 11).number_format = '0.00%'

hoja('P2 Cómo se perdió (B)',
     ['Corte', 'Valor', 'SKU o movimientos', 'Uds', 'Líneas de falta'],
     [['»Uds netas perdidas por SKU', '', 'SKU', '', 'Líneas'],
      ['Ajuste neto', '1 ud', 145, 145, 1074], ['Ajuste neto', '2-3 uds', 64, '', 849],
      ['Ajuste neto', '4-10 uds', 25, '', 625], ['Ajuste neto', 'más de 10', 6, '', 250],
      ['»Bajas por ajuste de los 240 SKU (todas las fechas)', '', 'Movimientos', 'Uds', ''],
      ['Tamaño', '1-3 uds sueltas', 276, 347, ''], ['Tamaño', '4 o más (parte de caja)', 21, 130, ''],
      ['Tamaño', 'Caja entera: igual a lo que entró en esa ubicación y no salió nada de ella', 6, 50, ''],
      ['Tipo', 'Cantidad de producto actualizada', 286, 448, ''], ['Tipo', 'INV:…', 15, 77, ''],
      ['Tipo', 'KOROSHI contenedor', 2, 2, ''], ['Altas por ajuste en esos SKU', '', '', 23, ''],
      ['»Cruce de talla o color (temporada 26)', '', '', '', ''],
      ['Bajas en SKU con falta', '', '', 510, ''],
      ['Compensable con sobrante de otra talla del mismo modelo-color', '34 modelo-color', '', 68, ''],
      ['Compensable con sobrante de otro color o talla del mismo modelo', '38 modelos', '', 102, ''],
      ['Cruce entre colores (todas las temporadas)', '14 modelos', '', 39, ''],
      ['»Stock negativo (quants internos < 0)', '', 'Quants', 'Uds', ''],
      ['Compañía 8', '', 98, -185, ''], ['SKU con falta', '', 22, -44, ''], ['… de ellos en grupo B', '', 16, -31, ''],
      ['»Recepciones abiertas (estado «reservado») en SKU de A y B', '', 'Movimientos', 'Uds', 'SKU'],
      ['IN/00174, 00233, 00247, 00287, 00291, 00304, 00320, 00323, 00371 (jun-sep) y IN/00394 (23/11)', '', 17, 1257, 16],
      ], [70, 40, 14, 10, 12],
     nota=FUENTE + ' stock.move.line hechos de los 240 SKU del grupo B (18.430 líneas) y stock.move/quant de 2.145 '
                   'artículos hermanos (mismos 256 modelos).')

hoja('P2 Historias (muestra)',
     ['SKU', 'Líneas falta', 'Recepción (fecha: uds > hueco)', 'Salidas a clientes (movs/uds, última)', 'Ajustes',
      'Lectura'],
     [['2622VS17-000003-S', 61, '12/08: 13 > L83 P21 C1; 27 > L84 P22 C1; 45 > L83 P23 C2; 45 > L83 P23 C1', '64 / 119, última 29/09',
       '28/08 INV:Inventory −13 en L83 P21 C1', 'Caja entera: las 13 que se ubicaron en L83 P21 C1 se dan de baja 16 días después, '
       'sin ninguna salida desde ese hueco. Recepción/ubicación.'],
      ['2622JA17-000003-XXL', 50, '24/09: 5 × 15 > L130 P12 C2', '60 / 60, última 11/11', '11/11 CPA −15 en L130 P12 C2',
       'Una caja de 15 que no aparece el día que se acaba lo demás.'],
      ['2621PL06-000039-XXL', 58, '14/08: 32 > L87 P28 C2; 20 + 16 > L88 P29 C1', '54 / 60, última 02/10',
       '15/09 CPA −1 L88 P29 C1; 02/10 CPA −7 L87 P28 C2', 'Parte de caja (7) y 1 suelta.'],
      ['2622JA00-000003-L', 47, '23/09: 9 líneas, 126 uds en L127-L130', '66 / 115, última 19/10', '20/10 CPA −11 L128 P15 C2',
       'Parte de caja (11) al día siguiente de la última salida.'],
      ['2621PT90-000130-M', 46, '30/07: 222 uds en L51-L54', '133 / 213, última 02/11', '04/11 CPA −2; 05/11 CPA −7 (L52 P09 C1)',
       'Se agota lo visible y se ajusta el resto.'],
      ['2622BL11-000003-L', '—', '10/08: 87 > L82 P20 C1; 13 + 46 > L83 P25 C2', '83 / 145, última 28/09', '19/08 CPA −1 L82 P20 C1',
       '1 ud suelta.'],
      ['2621PT01-000062-34', 11, '23/10: 35 + 24 > MU-07 P13 C2', '38 / 58, última 13/11', '13/11 CPA −1 MU-07 P13 C2',
       '1 ud suelta el mismo día de la última salida. Tiene recepción abierta IN/00174 (210 uds) desde junio.'],
      ['2621XC04 (modelo)', '25 + 25', 'Color 000019: tallas 40 y 44 bajas 11 y 13', 'Color 000003: tallas 42, 43, 44 altas 16, 12 y 4',
       '28/08: −10 y −10 en cajas KO_300726 (L74, L76)', 'Cruce de colores dentro del modelo (lo que contaba Sonia): '
       'falta en 000019 y sobra en 000003.'],
      ], [22, 10, 50, 26, 44, 70],
     nota=FUENTE + ' stock.move.line hechos de cada SKU, todas las fechas.')

# ---------- P3 resumen ----------
hoja('P3 Por qué no se sirvió',
     ['Dónde está el stock de Odoo', 'SKU', 'Uds', 'Reservadas', 'Líneas de falta (SKU solo ahí)', '¿Servible por la OUT?'],
     [['FALTANTE (ubicación de lo que el operario no encontró)', 88, 146, 35, 326, 'No: es lo que se dio por no encontrado; '
       'pendiente de ronda (ninguna ronda hecha)'],
      ['Hueco (L.., MU)', 38, 177, 44, 74, 'Sí, si de verdad está'],
      ['FALTANTE + hueco', 18, '', '', 59, ''],
      ['SORTER', 11, 16, 0, 103, 'No hasta que se ubica'],
      ['DEVOLUCIÓN', 9, 11, 0, 59, 'No hasta que se ubica'],
      ['DEVOLUCIÓN + FALTANTE + SORTER', 1, '', '', 33, ''],
      ['TARKO (taras)', 20, 37, 0, 25, 'No: taras'],
      ['FALTANTE + TARKO', 6, '', '', 9, ''],
      ['»Stock libre en hueco y aun así cancelado', '', '', '', '', ''],
      ['SKU con stock libre en hueco', 18, 134, '', 46, 'Motivo: cancelado 35, no cogido 10, pendiente 1'],
      ['… con faltante registrado por el operario en ese mismo hueco', 16, '', '', '', '17 «sin alternativa» pendientes + 1 '
       '«reubicado»: Odoo dice que hay y el operario dice que no'],
      ['»Cuándo llegó el stock del hueco', '', '', '', '', ''],
      ['Ya estaba antes de la 1.ª falta (entró por recepción)', 26, 152, 39, '', ''],
      ['Llegó entre faltas (contenedor «añadir prendas»)', 9, 19, 3, '', ''],
      ['Llegó después de la última falta', 2, 2, 0, '', ''],
      ], [56, 8, 8, 11, 16, 60],
     nota=FUENTE + ' stock.quant interno de los 139 SKU del grupo C; koroshi.faltante (563 registros).')

# ---------- P4 S4T ----------
hoja('P4 S4T regularizaciones',
     ['Regularización (s4t.stock.regularization)', 'Creada (UTC)', 'Estado', 'Líneas', 'Uds netas', 'Respuesta S4T'],
     [['REG-00006665-20260807111719', '07/08/2026', '', 1, '', ''],
      ['REG-00006665-20260807111841', '07/08/2026', 'partial', 14, '', ''],
      ['REG-00006665-20260807111857', '07/08/2026 11:18', 'partial', 25, -26, 'PARTIAL: 25 línea(s) procesada(s)'],
      ['REG-00006665-20260807111929', '07/08/2026 11:19', 'applied', 24, 25, 'APPLIED: 23 línea(s) procesada(s)'],
      ['REG-00006665-20260807120734', '07/08/2026 12:07', 'partial', 12, -16, 'PARTIAL: 12 línea(s) procesada(s)'],
      ['REG-00006665-20260814113631', '14/08/2026 11:36', 'draft (no enviada)', 24, -50, ''],
      ['»Ajustes de prendas en EFFEC desde el 14/08 (no enviados a S4T)', '', '', 'Movimientos', 'Uds', ''],
      ['Bajas', 'Cantidad de producto actualizada', '', 608, 914, '511 SKU'],
      ['Bajas', 'INV:…', '', 35, 255, '24 SKU'],
      ['Bajas', 'KOROSHI contenedor', '', 25, 341, '24 SKU'],
      ['Altas', 'Cantidad de producto actualizada', '', 23, 40, '21 SKU'],
      ['Altas', 'INV:…', '', 311, 576, '251 SKU'],
      ['Altas', 'KOROSHI contenedor (añadir prendas, desde 18/11)', '', 432, 1234, '238 SKU'],
      ], [44, 30, 18, 12, 10, 36],
     nota=FUENTE + ' En el repo no hay código que llame a /stock/regularization ni /stock/snapshot (búsqueda en odoo/).')

# ---------- P5 volumen ----------
hoja('P5 Volumen por mes',
     ['Mes', 'Bajas CPA', 'Bajas INV', 'Bajas contenedor', 'Total bajas', 'Altas CPA', 'Altas INV', 'Altas contenedor',
      'Total altas', 'Neto (altas − bajas)'],
     [['agosto', 237, 52, 0, 289, 13, 128, 0, 141, -148],
      ['septiembre', 241, 0, 0, 241, 11, 7, 0, 18, -223],
      ['octubre', 277, 24, 0, 301, 14, 44, 0, 58, -243],
      ['noviembre (hasta 26/11)', 300, 216, 341, 857, 5, 421, 1234, 1660, 803],
      ['»Total', 1055, 292, 341, 1688, 43, 600, 1234, 1877, 189],
      ['»Temporada OI 26/27 (3.661 SKU «26…», todas las fechas)', '', '', '', '', '', '', '', '', ''],
      ['Recibido de proveedor', 541627, '', '', '', '', '', '', '', ''],
      ['Salido a clientes', 378115, '', '', '', '', '', '', '', ''],
      ['Devuelto por clientes', 144, '', '', '', '', '', '', '', ''],
      ['Bajas por ajuste', 1940, '', '', '', '', '', '', '', ''],
      ['Altas por ajuste', 1751, '', '', '', '', '', '', '', ''],
      ['Stock hoy', 163467, '', '', '', '', '', '', '', ''],
      ['Recibido − salido + devuelto − bajas + altas', 163467, '', '', '', '', '', '', '', 'Cuadra exacto'],
      ['Ajuste neto ÷ recibido', '0,035 %', '', '', '', '', '', '', '', ''],
      ['Bajas brutas ÷ recibido', '0,36 %', '', '', '', '', '', '', '', ''],
      ['Valor', 'No se puede: coste 0 y precio 1 € en Odoo', '', '', '', '', '', '', '', 'Pedir precio de coste a KOROSHI'],
      ], [44, 12, 10, 12, 10, 10, 10, 12, 10, 12],
     nota=FUENTE + ' Prendas de EFFEC (sin SUMI ni pack 2611UN10-000323), Inventory adjustment/Scrap, desde 01/08/2026.')

# ---------- P6 KPI ----------
hoja('P6 KPI diario vs únicas',
     ['Día', 'Líneas', 'Uds', 'OUT', 'Pedidos', 'Pedidos repetidos', 'Pares tienda-SKU', 'Pares nuevos', 'Uds nuevas',
      'SKU', 'SKU nuevos', 'Tiendas'],
     [['16/11', 384, 420, 39, 27, 0, 384, 384, 420, 268, 89, 27],
      ['17/11', 441, 485, 48, 45, 0, 441, 434, 477, 289, 38, 45],
      ['18/11', 471, 518, 40, 40, 0, 471, 84, 90, 291, 11, 40],
      ['19/11', 481, 531, 50, 46, 0, 481, 61, 65, 298, 25, 46],
      ['20/11', 381, 412, 46, 46, 0, 381, 107, 110, 254, 3, 46],
      ['23/11', 510, 573, 67, 49, 0, 510, 124, 127, 318, 31, 49],
      ['24/11', 578, 637, 56, 52, 0, 509, 54, 54, 309, 24, 46],
      ['25/11', 568, 640, 55, 46, 0, 568, 110, 123, 372, 57, 45],
      ['»Total 16-25/11', 3814, 4216, '', '', '', 1358, 1358, 1507, 472, '', 50],
      ['»Días que sale cada par tienda-SKU', '', '', '', '', '', '', '', '', '', '', ''],
      ['1 día', 450], ['2 días', 278], ['3 días', 253], ['4 días', 100], ['5 días', 98], ['6 días', 165], ['7 días', 12],
      ['8 días', 2],
      ], [24, 8, 8, 6, 8, 10, 10, 10, 10, 8, 8, 8],
     nota=FUENTE + ' koroshi.kpi.falta, fecha 16/11–25/11. «Pares nuevos» = tienda-SKU que no había salido antes desde '
                   'el 16/11 (el 16 y el 17 cuentan todo como nuevo). Pedidos repetidos = 0: cada día es un pedido S- nuevo.')

wb.save(OUT)
print('Escrito', OUT)
