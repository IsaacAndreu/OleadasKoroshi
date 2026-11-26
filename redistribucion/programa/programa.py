# -*- coding: utf-8 -*-
"""Programa de redistribución de zonas de NAU-2 (KOROSHI). Fase 1: datos reales de Odoo en solo lectura.

Uso (desde esta carpeta):
  python programa.py guardar-clave          guarda la contraseña de Odoo en el almacén de Windows (no se ve)
  python programa.py probar-conexion        versión de Odoo, campos necesarios y cuántas filas tiene cada cosa
  python programa.py descargar [--desde AAAA-MM-DD] [--sin-salidas] [--completa]   copia nueva en copias/
  python programa.py copia-inventada        copia con datos inventados (sin Odoo)
  python programa.py resumen [copia]        resumen de una copia con las reglas actuales (no la modifica)
  python programa.py generar-mapa [copia]   datos del mapa v3 desde una copia (no habla con Odoo)
        [--desde AAAA-MM-DD]                desde cuándo contar el histórico de salidas (por defecto, hace un año)
  python programa.py compactar-0 [copia]    zona 0: clasificación ABC × tamaño y propuesta de compactación a Excel
        [--master fichero.xlsx]             MASTER del que salen los litros (por defecto, la última versión)
        [--mapa carpeta]                    deja también compactacion.json en el mapa (por defecto, el v4)

Nada de esto escribe en Odoo: todo pasa por redistrib/odoo_lectura.py, que solo deja leer.
"""
import argparse
import datetime
import sys
import time

from redistrib import configuracion, consultas
from redistrib.odoo_lectura import ClienteLectura, ErrorOdoo


MAPA_ACTUAL = 'prototipo-mapa_2026-11-26_v4'     # carpeta del mapa que se usa ahora (las anteriores no se tocan)


def _cliente(cfg):
    return ClienteLectura(cfg['url'], cfg['bd'], cfg['usuario'], configuracion.leer_clave(cfg['usuario']),
                          pausa=cfg['pausa'], timeout=cfg['timeout'])


def guardar_clave(_args):
    cfg = configuracion.leer_config()
    configuracion.guardar_clave(cfg['usuario'])
    print('Contraseña guardada en el almacén de credenciales de Windows (servicio %s, cuenta %s).'
          % (configuracion.SERVICIO_KEYRING, cfg['usuario']))


def probar_conexion(args):
    cfg = configuracion.leer_config()
    cliente = _cliente(cfg)
    inicio = time.monotonic()
    v = cliente.version()
    print('Odoo %s en %s (bd %s)' % (v.get('server_version'), cliente.url, cliente.bd))
    cliente.autenticar()
    print('Usuario %s: entrada correcta.\n' % cliente.usuario)

    campos = {m: cliente.campos(m) for m in consultas.CAMPOS_NECESARIOS}
    falta = consultas.campos_que_faltan(campos)
    print('Campos necesarios: %s' % ('todos están' if not falta else 'FALTAN %s' % falta))
    temporada = campos['product.template'].get('season_id')
    if temporada:
        print('  product.template.season_id -> %s (%s)' % (temporada.get('relation'), temporada.get('string')))
    linea = campos['stock.move.line']
    print('  stock.move.line: company_id %s, picking_code %s\n'
          % ('sí' if 'company_id' in linea else 'no', 'sí' if 'picking_code' in linea else 'no'))

    desde = datetime.date.fromisoformat(args.desde) if args.desde else None
    print('%-62s %10s %7s' % ('Qué', 'Filas', 'Seg.'))
    for etiqueta, modelo, dominio, contexto in consultas.conteos(linea, desde_historico=desde):
        t = time.monotonic()
        try:
            n = '{:,}'.format(cliente.contar(modelo, dominio, contexto)).replace(',', '.')
        except ErrorOdoo as e:
            n = 'ERROR'
            print('    %s' % str(e)[:300])
        print('%-62s %10s %7.1f' % (etiqueta, n, time.monotonic() - t))
    print('\n%d peticiones en %.0f s. No se ha escrito nada en Odoo.' % (cliente.peticiones, time.monotonic() - inicio))


def descargar(args):
    from redistrib.descarga import Descarga
    cfg = configuracion.leer_config()
    cliente = _cliente(cfg)
    desde = datetime.date.fromisoformat(args.desde) if args.desde else None
    ruta, _res, avisos, texto = Descarga(cliente, configuracion.CARPETA / 'copias', pagina=cfg['pagina']).ejecutar(
        desde=desde, con_salidas=not args.sin_salidas, completa=args.completa)
    print('\n' + texto)
    for a in avisos:
        print('AVISO: ' + a)
    print('Copia: %s\nNo se ha escrito nada en Odoo.' % ruta)


def copia_inventada(args):
    """Copia SQLite con datos INVENTADOS (sin Odoo), para probar el mapa y las listas."""
    from redistrib.descarga import Descarga
    from pruebas.odoo_falso import OdooFalso
    carpeta = configuracion.CARPETA / 'copias' / 'inventadas'
    ruta, _res, _av, texto = Descarga(OdooFalso(), carpeta).ejecutar(desde=datetime.date(2026, 10, 1))
    print(texto + '\nCopia INVENTADA: %s' % ruta)


def rehacer_resumen(args):
    """Resumen de una copia con las reglas de clasificación actuales, sobre una copia EN MEMORIA: el fichero
    bajado no se toca. Escribe <copia>.resumen_AAAAMMDD_HHMM.txt (nuevo; no pisa el anterior)."""
    import sqlite3
    from pathlib import Path
    from redistrib import resumen as R
    from redistrib.descarga import clasificar_en_bd, copias_completas
    ruta = Path(args.copia) if args.copia else copias_completas(configuracion.CARPETA / 'copias')[-1]
    origen = sqlite3.connect('file:%s?mode=ro' % ruta.as_posix(), uri=True)
    bd = sqlite3.connect(':memory:')
    origen.backup(bd)
    origen.close()
    clasificar_en_bd(bd)
    meta = dict(bd.execute('SELECT clave, valor FROM meta').fetchall())
    texto = R.como_texto(R.resumen(bd), meta)
    salida = ruta.with_name('%s.resumen_%s.txt' % (ruta.stem, datetime.datetime.now().strftime('%Y%m%d_%H%M')))
    salida.write_text(texto, encoding='utf-8')
    print(texto + '\nResumen en %s (la copia no se ha tocado).' % salida)


def generar_mapa(args):
    """Datos del mapa v3 (datos.json, huecos.json, modelos.json, listas.json) desde una copia. No habla con Odoo."""
    from pathlib import Path
    from redistrib import mapa_json
    from redistrib.descarga import copias_completas
    ruta = Path(args.copia) if args.copia else copias_completas(configuracion.CARPETA / 'copias')[-1]
    raiz = configuracion.CARPETA.parent
    salida = Path(args.mapa) if args.mapa else raiz / MAPA_ACTUAL
    datos, tam = mapa_json.generar(ruta, raiz / 'prototipo-mapa_2026-11-23_v2', salida)
    c = datos['cifras']
    print('Copia %s (Odoo %s) -> %s' % (ruta.name, datos['fecha_datos'], salida))
    print('  ' + ', '.join('%s %.1f MB' % (k, v / 1e6) for k, v in tam.items()))
    print('  %d posiciones; %d de %d modelos-color en más de un lineal; %d contenedores a cero; %d uds pendientes de ubicar'
          % (len(datos['posiciones']), c['mc_mas_de_1_lineal'], c['modelos_color'], c['contenedores_a_cero'],
             c['uds_pendiente']))


def compactar_0(args):
    """Clasificación de la zona 0 y propuesta de compactación, a Excel. No habla con Odoo."""
    from pathlib import Path
    from redistrib import compactar as C
    from redistrib.descarga import copias_completas
    ruta = Path(args.copia) if args.copia else copias_completas(configuracion.CARPETA / 'copias')[-1]
    raiz = configuracion.CARPETA.parent
    from redistrib import fuentes
    master = Path(args.master) if args.master else fuentes.matriz(1).ruta    # última versión del MASTER
    r = C.ReglasCompactar()
    datos = C.cargar(ruta, raiz / 'prototipo-mapa_2026-11-23_v2', C.leer_master(master), r)
    mcs = C.clasificar(datos, r)
    pasos, res = C.compactar(datos, mcs, r)
    vacias = C.cajas_a_cero(ruta, datos, r)
    salida = raiz / ('compactacion-zona0_%s.xlsx' % datetime.datetime.now().strftime('%Y%m%d_%H%M'))
    C.exportar_excel(salida, mcs, pasos, res, r, vacias=vacias)
    print('Copia %s, MASTER %s' % (ruta.name, master.name))
    for k, v in list(res.items()) + list(C.resumen_cajas_a_cero(vacias, r).items()):
        print('  %s: %s' % (k, v))
    print('Excel en %s' % salida)
    import json
    mapa = Path(args.mapa) if args.mapa else raiz / MAPA_ACTUAL
    if mapa.is_dir():
        j = C.para_mapa(ruta, datos, mcs, pasos, res, vacias, r)
        (mapa / 'compactacion.json').write_text(json.dumps(j, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        print('Mapa: %s (lineales que se podrían vaciar enteros, estimación: %d)'
              % (mapa / 'compactacion.json', j['resumen']['lineales_vaciables']))


def main(argv=None):
    p = argparse.ArgumentParser(description='Programa de redistribución NAU-2 (solo lectura de Odoo)')
    sub = p.add_subparsers(dest='orden', required=True)
    sub.add_parser('guardar-clave').set_defaults(funcion=guardar_clave)
    pc = sub.add_parser('probar-conexion')
    pc.add_argument('--desde', help='inicio del histórico de salidas (AAAA-MM-DD)')
    pc.set_defaults(funcion=probar_conexion)
    pd = sub.add_parser('descargar', help='copia nueva de Odoo en copias/AAAAMMDD_HHMM_odoo.sqlite')
    pd.add_argument('--desde', help='inicio del histórico de salidas (AAAA-MM-DD); obligatorio la primera vez')
    pd.add_argument('--sin-salidas', action='store_true', help='no pedir salidas a Odoo (se copian de la copia anterior)')
    pd.add_argument('--completa', action='store_true', help='volver a bajar todas las salidas, no solo las nuevas')
    pd.set_defaults(funcion=descargar)
    sub.add_parser('copia-inventada', help='copia con datos inventados, sin Odoo').set_defaults(funcion=copia_inventada)
    pg = sub.add_parser('generar-mapa', help='datos del mapa v3 desde una copia (no habla con Odoo)')
    pg.add_argument('copia', nargs='?', help='fichero .sqlite (por defecto, la última copia)')
    pg.add_argument('--mapa', help='carpeta del mapa (por defecto, %s)' % MAPA_ACTUAL)
    pg.set_defaults(funcion=generar_mapa)
    pr = sub.add_parser('resumen', help='resumen de una copia con las reglas actuales (no la modifica)')
    pr.add_argument('copia', nargs='?', help='fichero .sqlite (por defecto, la última copia)')
    pr.set_defaults(funcion=rehacer_resumen)
    pk = sub.add_parser('compactar-0', help='zona 0: clasificación y propuesta de compactación a Excel (no habla con Odoo)')
    pk.add_argument('copia', nargs='?', help='fichero .sqlite (por defecto, la última copia)')
    pk.add_argument('--master', help='Excel MASTER (por defecto, la última versión de KOROSHI_1_MASTER en bin/versiones)')
    pk.add_argument('--mapa', help='carpeta del mapa donde dejar compactacion.json (por defecto, %s)' % MAPA_ACTUAL)
    pk.set_defaults(funcion=compactar_0)
    args = p.parse_args(argv)
    try:
        args.funcion(args)
    except (configuracion.ErrorConfiguracion, ErrorOdoo, ValueError, FileExistsError) as e:
        sys.exit('ERROR: %s' % e)


if __name__ == '__main__':
    main()
