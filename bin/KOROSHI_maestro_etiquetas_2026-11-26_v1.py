"""Maestro de artículos para etiquetar (KOROSHI), con el formato que pide el almacén al reetiquetar.

v1 (26/11/2026): primera versión. Sustituye a pedir el maestro a S4T a mano (correo de Evaldas, 31/07/2026).

Formato de salida (CSV con «;», una fila por SKU):
    CodigoDeArticulo;EAN_OLD;EAN_AECOC;ARTICULO;COLOR;DESCRIPCION;TALLA;TallaEU;TallaUS;TallaUK;TallaIT;
    EAN1_ART2_COL3_DES4_TAL5_EU6_US7_UK8_IT9

Origen de cada columna: el CSV de la API de S4T «GET /api/service/products/by-season/{temporada}/csv»
(columnas id, referencia, sku, eans, nombre_producto, color_id, nombre_color, talla, ...):
    CodigoDeArticulo = sku
    EAN_OLD          = el EAN de «eans» que empieza por 8100 (solo en temporadas antiguas)
    EAN_AECOC        = el primer EAN de «eans» que empieza por 8445
    ARTICULO         = referencia
    COLOR            = color_id sin ceros a la izquierda (000017 -> 17)
    DESCRIPCION      = nombre_color (así viene en el maestro antiguo: «GRANATE / MAROON»)
    TALLA            = talla
    TallaEU/US/UK/IT = tabla de equivalencias (--tallas); S4T no las da por la API. Sin tabla, van vacías.
    Última columna   = "EAN_AECOC|ARTICULO|color_id|DESCRIPCION|TALLA|EU|US|UK|IT", entre comillas.

Uso:
    # Con CSV ya descargados de la API (no hace falta clave):
    python bin/KOROSHI_maestro_etiquetas_2026-11-26_v1.py --entrada products_I27.csv products_V27.csv \
        --salida maestro_etiquetas.csv [--tallas tallas_equivalencias.csv]

    # Descargando de la API: la clave se lee de la variable de entorno S4T_API_KEY (nunca del código):
    $env:S4T_API_KEY = '...'
    python bin/KOROSHI_maestro_etiquetas_2026-11-26_v1.py --temporadas I27 V27 --salida maestro_etiquetas.csv

Tabla de equivalencias (--tallas), CSV con «;»: TIPO;TALLA;TallaEU;TallaUS;TallaUK;TallaIT
    TIPO = letras 5 y 6 de la referencia (2621JA62 -> JA). TIPO «*» vale para todos los tipos.
    Una fila con TIPO concreto gana a la de «*». Las filas con las cuatro tallas vacías no cuentan.

Solo lee: no escribe nada en Odoo ni en S4T.
"""
import argparse
import csv
import io
import os
import sys
import urllib.request

URL_API = 'http://82.223.131.45:3232/api/service/products/by-season/{temporada}/csv'
CABECERA = ['CodigoDeArticulo', 'EAN_OLD', 'EAN_AECOC', 'ARTICULO', 'COLOR', 'DESCRIPCION', 'TALLA',
            'TallaEU', 'TallaUS', 'TallaUK', 'TallaIT', 'EAN1_ART2_COL3_DES4_TAL5_EU6_US7_UK8_IT9']


def descargar(temporada):
    clave = os.environ.get('S4T_API_KEY')
    if not clave:
        sys.exit('Falta la variable de entorno S4T_API_KEY (la clave de la API de S4T).')
    peticion = urllib.request.Request(URL_API.format(temporada=temporada), headers={'X-Api-Key': clave})
    with urllib.request.urlopen(peticion, timeout=120) as respuesta:
        texto = respuesta.read().decode('utf-8-sig')
    if texto.lstrip().startswith('{'):
        sys.exit('La API no ha devuelto un CSV para %s: %s' % (temporada, texto[:200]))
    return texto


def leer_tallas(ruta):
    tabla = {}
    if not ruta:
        return tabla
    with open(ruta, encoding='utf-8-sig', newline='') as f:
        for fila in csv.DictReader(f, delimiter=';'):
            tallas = tuple((fila.get(c) or '').strip() for c in ('TallaEU', 'TallaUS', 'TallaUK', 'TallaIT'))
            if any(tallas):
                tabla[((fila.get('TIPO') or '*').strip().upper(), (fila.get('TALLA') or '').strip().upper())] = tallas
    return tabla


def separar_eans(eans):
    lista = [e.strip() for e in eans.replace(';', '|').replace(' ', '|').split('|') if e.strip()]
    viejo = next((e for e in lista if e.startswith('8100')), '')
    aecoc = [e for e in lista if not e.startswith('8100')]
    return viejo, (aecoc[0] if aecoc else ''), aecoc[1:]


def convertir(textos, tabla_tallas):
    filas, avisos, vistos = [], [], set()
    sin_tallas = set()
    for texto in textos:
        for r in csv.DictReader(io.StringIO(texto)):
            sku = (r.get('sku') or '').strip()
            if not sku or sku in vistos:
                continue
            vistos.add(sku)
            if (r.get('activo') or 'True').strip().lower() == 'false':
                continue
            viejo, aecoc, otros = separar_eans(r.get('eans') or '')
            if otros:
                avisos.append('%s: más de un EAN AECOC (%s); se usa %s' % (sku, ', '.join([aecoc] + otros), aecoc))
            if not aecoc:
                avisos.append('%s: sin EAN AECOC' % sku)
            referencia = (r.get('referencia') or '').strip()
            color_id = (r.get('color_id') or '').strip()
            color = color_id.lstrip('0') or color_id
            descripcion = (r.get('nombre_color') or '').strip()
            talla = (r.get('talla') or '').strip()
            tipo = referencia[4:6].upper()
            eq = tabla_tallas.get((tipo, talla.upper())) or tabla_tallas.get(('*', talla.upper()))
            if not eq:
                eq = ('', '', '', '')
                sin_tallas.add((tipo, talla))
            compuesta = '|'.join([aecoc, referencia, color_id, descripcion, talla] + list(eq))
            try:
                posicion = int(r.get('posicion_talla') or 0)
            except ValueError:
                posicion = 0
            orden = (referencia, color_id, posicion, talla)
            filas.append((orden, [sku, viejo, aecoc, referencia, color, descripcion, talla] + list(eq) + [compuesta]))
    filas = [f for _, f in sorted(filas, key=lambda x: x[0])]
    return filas, avisos, sin_tallas


def escribir(ruta, filas, codificacion):
    with open(ruta, 'w', encoding=codificacion, errors='replace', newline='') as f:
        f.write(';'.join(CABECERA) + '\r\n')
        for fila in filas:
            # Igual que el maestro antiguo: solo la última columna va entre comillas.
            f.write(';'.join(fila[:-1]) + ';"' + fila[-1].replace('"', '""') + '"\r\n')


def main():
    p = argparse.ArgumentParser(description='Maestro de artículos para etiquetar (KOROSHI)')
    origen = p.add_mutually_exclusive_group(required=True)
    origen.add_argument('--entrada', nargs='+', help='CSV ya descargados de la API (by-season/.../csv)')
    origen.add_argument('--temporadas', nargs='+', help='Temporadas a descargar de la API, p. ej. I27 V27')
    p.add_argument('--salida', required=True, help='CSV de salida')
    p.add_argument('--tallas', help='Tabla de equivalencias TIPO;TALLA;TallaEU;TallaUS;TallaUK;TallaIT')
    p.add_argument('--codificacion', default='utf-8-sig',
                   help='utf-8-sig (por defecto, se abre bien en Excel) o cp1252 si el programa de etiquetas lo pide')
    a = p.parse_args()

    if a.entrada:
        textos = [open(r, encoding='utf-8-sig').read() for r in a.entrada]
    else:
        textos = [descargar(t) for t in a.temporadas]
    filas, avisos, sin_tallas = convertir(textos, leer_tallas(a.tallas))
    escribir(a.salida, filas, a.codificacion)

    print('Escrito %s: %d SKU.' % (a.salida, len(filas)))
    print('Con EAN_OLD: %d. Con tallas EU/US/UK/IT: %d.' % (
        sum(1 for f in filas if f[1]), sum(1 for f in filas if any(f[7:11]))))
    if sin_tallas:
        print('Sin equivalencia de talla: %d combinaciones tipo/talla.' % len(sin_tallas))
    for aviso in avisos[:30]:
        print('AVISO', aviso)
    if len(avisos) > 30:
        print('... y %d avisos más' % (len(avisos) - 30))


if __name__ == '__main__':
    main()
