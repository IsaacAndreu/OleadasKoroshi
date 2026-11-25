# -*- coding: utf-8 -*-
"""Resumen de una copia SQLite: filas, unidades por zona y lo raro. Comparación con el Excel MASTER del 06/11.
Solo lee la copia (sqlite3); no habla con Odoo."""

EXCEL_0611 = {'nave2': 422873, 'zona_0': 236866, 'zona_z': 135132,
              'fuente': 'bin/versiones/20261106_1630_MASTER-zonas-0-y-Z-layout-estanterias-cajas_v1.xlsx'}
MAX_EJEMPLOS = 40


def _uno(bd, sql, *args):
    return bd.execute(sql, args).fetchone()[0] or 0


def resumen(bd):
    r = {'filas': {t: _uno(bd, 'SELECT COUNT(*) FROM %s' % t)
                   for t in ('ubicaciones', 'stock', 'productos', 'tipos_operacion', 'salidas')}}
    r['ubicaciones_por_tipo'] = dict(bd.execute(
        "SELECT tipo || CASE WHEN activa THEN '' ELSE ' (archivada)' END, COUNT(*) FROM ubicaciones GROUP BY 1 "
        'ORDER BY 2 DESC').fetchall())
    r['uds_total'] = _uno(bd, 'SELECT SUM(cantidad) FROM stock')
    r['uds_por_zona'] = dict(bd.execute(
        "SELECT COALESCE(p.zona, 'producto sin leer'), SUM(s.cantidad) FROM stock s LEFT JOIN productos p "
        'ON p.id = s.producto_id GROUP BY 1 ORDER BY 2 DESC').fetchall())
    r['uds_nave2_por_zona'] = dict(bd.execute(
        "SELECT COALESCE(p.zona, 'producto sin leer'), SUM(s.cantidad) FROM stock s JOIN ubicaciones u "
        'ON u.id = s.ubicacion_id LEFT JOIN productos p ON p.id = s.producto_id WHERE u.en_nave GROUP BY 1 '
        'ORDER BY 2 DESC').fetchall())
    r['uds_nave2_por_tipo'] = dict(bd.execute(
        "SELECT u.tipo || CASE WHEN u.tipo = 'contenedor' THEN COALESCE((SELECT ' en ' || p.tipo FROM ubicaciones p "
        "WHERE p.id = u.padre_id), '') ELSE '' END, SUM(s.cantidad) FROM stock s JOIN ubicaciones u "
        'ON u.id = s.ubicacion_id WHERE u.en_nave GROUP BY 1 ORDER BY 2 DESC').fetchall())
    r['uds_fuera_nave2_por_ruta'] = dict(bd.execute(
        "SELECT COALESCE(u.ruta, '?'), SUM(s.cantidad) FROM stock s LEFT JOIN ubicaciones u ON u.id = s.ubicacion_id "
        'WHERE NOT COALESCE(u.en_nave, 0) GROUP BY 1 ORDER BY 2 DESC LIMIT 15').fetchall())
    r['uds_nave2_permanente'] = _uno(
        bd, 'SELECT SUM(s.cantidad) FROM stock s JOIN ubicaciones u ON u.id = s.ubicacion_id JOIN productos p '
            "ON p.id = s.producto_id WHERE u.en_nave AND p.temporada IN ('PERMANENTE')")
    r['temporadas'] = dict(bd.execute(
        "SELECT COALESCE(NULLIF(p.temporada, ''), '(sin)'), SUM(s.cantidad) FROM stock s JOIN productos p "
        'ON p.id = s.producto_id GROUP BY 1 ORDER BY 2 DESC LIMIT 25').fetchall())
    raro = {}
    raro['nombres_en_nave_que_no_encajan'] = {
        'n': _uno(bd, "SELECT COUNT(*) FROM ubicaciones WHERE en_nave AND tipo = 'otra' AND activa"),
        'ejemplos': [x[0] for x in bd.execute(
            "SELECT ruta FROM ubicaciones WHERE en_nave AND tipo = 'otra' AND activa ORDER BY ruta LIMIT ?",
            (MAX_EJEMPLOS,))]}
    raro['contenedores_sin_hueco_padre'] = {
        'n': _uno(bd, "SELECT COUNT(*) FROM ubicaciones WHERE tipo = 'contenedor' AND activa AND hueco_id IS NULL "
                      'AND en_nave'),
        'ejemplos': ['%s: %s contenedores, %s uds' % (a.strip(), _n(b), _n(c)) for a, b, c in bd.execute(
            "SELECT COALESCE(p.tipo, '?') || ' ' || CASE WHEN p.tipo = 'otra' THEN p.ruta ELSE '' END, COUNT(*), "
            'SUM((SELECT COALESCE(SUM(s.cantidad), 0) FROM stock s WHERE s.ubicacion_id = u.id)) '
            'FROM ubicaciones u LEFT JOIN ubicaciones p ON p.id = u.padre_id '
            "WHERE u.tipo = 'contenedor' AND u.activa AND u.hueco_id IS NULL AND u.en_nave GROUP BY 1 ORDER BY 2 DESC")]}
    raro['huecos_con_mas_de_4_niveles'] = [list(x) for x in bd.execute(
        "SELECT printf('L%02d P%02d', lineal, posicion), COUNT(DISTINCT nivel), GROUP_CONCAT(DISTINCT nivel) "
        "FROM ubicaciones WHERE tipo = 'hueco' AND activa GROUP BY lineal, posicion HAVING COUNT(DISTINCT nivel) > 4 "
        'ORDER BY lineal, posicion LIMIT ?', (MAX_EJEMPLOS,))]
    raro['niveles'] = dict(bd.execute(
        "SELECT 'C' || nivel, COUNT(*) FROM ubicaciones WHERE tipo = 'hueco' AND activa GROUP BY nivel").fetchall())
    raro['productos_sin_temporada'] = {
        'productos': _uno(bd, "SELECT COUNT(*) FROM productos WHERE temporada = ''"),
        'uds': _uno(bd, "SELECT SUM(s.cantidad) FROM stock s JOIN productos p ON p.id = s.producto_id "
                        "WHERE p.temporada = ''")}
    raro['productos_con_volumen_estimado'] = _uno(bd, 'SELECT COUNT(*) FROM productos WHERE litros_estimado')
    raro['productos_sin_volumen_ni_familia'] = _uno(bd, 'SELECT COUNT(*) FROM productos WHERE litros IS NULL')
    raro['stock_negativo'] = {'filas': _uno(bd, 'SELECT COUNT(*) FROM stock WHERE cantidad < 0'),
                              'uds': _uno(bd, 'SELECT SUM(cantidad) FROM stock WHERE cantidad < 0')}
    raro['stock_en_ubicacion_no_descargada'] = _uno(
        bd, 'SELECT COUNT(*) FROM stock s LEFT JOIN ubicaciones u ON u.id = s.ubicacion_id WHERE u.id IS NULL')
    raro['contenedores_activos_a_cero'] = _uno(
        bd, "SELECT COUNT(*) FROM ubicaciones u WHERE u.tipo = 'contenedor' AND u.activa AND NOT EXISTS "
            '(SELECT 1 FROM stock s WHERE s.ubicacion_id = u.id AND s.cantidad != 0)')
    r['raro'] = raro
    r['salidas_por_tipo'] = [list(x) for x in bd.execute(
        'SELECT t.nombre, t.codigo, COUNT(s.id), MIN(s.fecha), MAX(s.fecha) FROM tipos_operacion t '
        'LEFT JOIN salidas s ON s.tipo_operacion_id = t.id GROUP BY t.id HAVING COUNT(s.id) > 0 ORDER BY 3 DESC')]
    nave = sum(r['uds_nave2_por_zona'].values())
    r['comparacion_excel_0611'] = {
        'nave2': [nave, EXCEL_0611['nave2']],
        'zona_0': [r['uds_nave2_por_zona'].get('0', 0), EXCEL_0611['zona_0']],
        # El Excel del 06/11 contaba PERMANENTE en zona 0; desde el 23/11 va en Z. Para comparar, se mueve.
        '0+perm.': [r['uds_nave2_por_zona'].get('0', 0) + r.get('uds_nave2_permanente', 0), EXCEL_0611['zona_0']],
        'Z-perm.': [r['uds_nave2_por_zona'].get('Z', 0) - r.get('uds_nave2_permanente', 0), EXCEL_0611['zona_z']],
        'zona_z': [r['uds_nave2_por_zona'].get('Z', 0), EXCEL_0611['zona_z']],
    }
    return r


def _n(x):
    return '{:,.0f}'.format(x or 0).replace(',', '.')


def como_texto(r, meta):
    L = ['Copia de Odoo del %s (%s, bd %s). Salidas desde %s (%s). %s s, %s peticiones.'
         % (meta.get('fecha_descarga'), meta.get('servidor'), meta.get('bd'), meta.get('desde_salidas') or '—',
            meta.get('salidas_de_odoo'), meta.get('segundos'), meta.get('peticiones')), '']
    L.append('Filas: ' + ', '.join('%s %s' % (k, _n(v)) for k, v in r['filas'].items()))
    L.append('Ubicaciones por tipo: ' + ', '.join('%s %s' % (k, _n(v)) for k, v in r['ubicaciones_por_tipo'].items()))
    L.append('')
    L.append('Unidades en total: %s' % _n(r['uds_total']))
    L.append('  por zona: ' + ', '.join('%s %s' % (k, _n(v)) for k, v in r['uds_por_zona'].items()))
    L.append('  en NAVE2 por zona: ' + ', '.join('%s %s' % (k, _n(v)) for k, v in r['uds_nave2_por_zona'].items()))
    L.append('  en NAVE2 por tipo de ubicación: ' + ', '.join('%s %s' % (k, _n(v))
                                                             for k, v in r['uds_nave2_por_tipo'].items()))
    L.append('  fuera de NAVE2: ' + ', '.join('%s %s' % (k, _n(v)) for k, v in r['uds_fuera_nave2_por_ruta'].items()))
    L.append('  temporadas: ' + ', '.join('%s %s' % (k, _n(v)) for k, v in r['temporadas'].items()))
    L.append('')
    L.append('Comparación con el Excel MASTER del 06/11 (uds en NAVE2: ahora / entonces / diferencia):')
    for k, (ahora, antes) in r['comparacion_excel_0611'].items():
        L.append('  %-8s %10s %10s %10s' % (k, _n(ahora), _n(antes), _n(ahora - antes)))
    L.append('')
    x = r['raro']
    L.append('Lo raro:')
    L.append('  nombres en NAVE2 que no encajan con «Lnn Pnn Cn»: %s %s' % (
        _n(x['nombres_en_nave_que_no_encajan']['n']), '; '.join(x['nombres_en_nave_que_no_encajan']['ejemplos'][:15])))
    L.append('  contenedores activos en NAVE2 cuyo padre no es un hueco: %s (por padre: %s)' % (
        _n(x['contenedores_sin_hueco_padre']['n']), '; '.join(x['contenedores_sin_hueco_padre']['ejemplos'][:10])))
    L.append('  niveles de hueco: ' + ', '.join('%s %s' % (k, _n(v)) for k, v in sorted(x['niveles'].items())))
    L.append('  posiciones con más de 4 niveles: %d %s' % (len(x['huecos_con_mas_de_4_niveles']),
                                                           '; '.join('%s (%s)' % (a, c) for a, _, c in
                                                                     x['huecos_con_mas_de_4_niveles'][:10])))
    L.append('  productos sin temporada: %s (%s uds)' % (_n(x['productos_sin_temporada']['productos']),
                                                         _n(x['productos_sin_temporada']['uds'])))
    L.append('  productos con volumen estimado por familia: %s; sin volumen ni familia: %s'
             % (_n(x['productos_con_volumen_estimado']), _n(x['productos_sin_volumen_ni_familia'])))
    L.append('  stock negativo: %s filas (%s uds)' % (_n(x['stock_negativo']['filas']), _n(x['stock_negativo']['uds'])))
    L.append('  stock en ubicaciones no descargadas: %s' % _n(x['stock_en_ubicacion_no_descargada']))
    L.append('  contenedores activos a cero (sin archivar): %s' % _n(x['contenedores_activos_a_cero']))
    L.append('')
    L.append('Salidas por tipo de operación (líneas, primera y última fecha):')
    for nombre, codigo, n, f1, f2 in r['salidas_por_tipo']:
        L.append('  %-40s %-9s %9s  %s — %s' % (nombre, codigo, _n(n), (f1 or '')[:10], (f2 or '')[:10]))
    return '\n'.join(L) + '\n'
