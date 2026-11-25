# -*- coding: utf-8 -*-
"""Descarga de Odoo a una copia SQLite. Solo lee (todo pasa por el cliente de odoo_lectura).

- Una copia por descarga: copias/AAAAMMDD_HHMM_odoo.sqlite. Mientras se baja se llama «….parcial»; solo se
  renombra al acabar bien, así una descarga cortada nunca parece buena. Si el nombre ya existe, para.
- Ubicaciones, stock y productos se bajan enteros cada vez (~250.000 filas).
- Salidas (stock.move.line hechas de los tipos de salida e internos del almacén de KOROSHI, en una sola tanda):
  la primera vez desde la fecha
  que se diga; las siguientes se copian de la copia anterior y solo se piden a Odoo las líneas con fecha desde la
  última descarga menos MARGEN_DIAS, por páginas ordenadas por id (las que ya estaban se sustituyen). Al acabar
  se compara el número de líneas por tipo con search_count en Odoo: si no cuadra, se avisa.
- Ninguna consulta usa campos no guardados (picking_code): se filtra por el tipo del albarán.

`cliente` es un ClienteLectura (o uno falso en las pruebas): solo se usan leer_paginado, llamar('read'),
campos y contar.
"""
import datetime
import json
import sqlite3
import time
from pathlib import Path

from . import productos as P
from . import resumen as R
from . import ubicaciones as U
from .odoo_lectura import COMPANIA

MARGEN_DIAS = 3
LOTE_READ = 2000
SIN_ARCHIVAR = {'active_test': False}
CODIGOS_SALIDA = ('outgoing', 'internal')
# Almacén de KOROSHI (warehouse_id de stock.picking.type, leído el 23/11): sus tipos son 45-49, 289 y 290.
# Los otros 49 tipos de la compañía 8 (MODALADA, TARAS, PROBODELT, CONSUMIBLES…) no se bajan.
ALMACEN_KOROSHI = '6665 STOCK GENERAL KOROSHI'

ESQUEMA = """
CREATE TABLE meta (clave TEXT PRIMARY KEY, valor TEXT);
CREATE TABLE ubicaciones (id INTEGER PRIMARY KEY, nombre TEXT, ruta TEXT, padre_id INTEGER, codigo_barras TEXT,
    activa INTEGER, tipo TEXT, lineal INTEGER, posicion INTEGER, nivel INTEGER, en_nave INTEGER, hueco_id INTEGER);
CREATE TABLE stock (id INTEGER PRIMARY KEY, ubicacion_id INTEGER, producto_id INTEGER, cantidad REAL, reservado REAL);
CREATE TABLE productos (id INTEGER PRIMARY KEY, referencia TEXT, nombre TEXT, ean TEXT, plantilla_id INTEGER,
    modelo TEXT, color TEXT, talla TEXT, familia TEXT, temporada TEXT, zona TEXT, volumen_m3 REAL, litros REAL,
    litros_estimado INTEGER, peso_kg REAL, activo INTEGER);
CREATE TABLE tipos_operacion (id INTEGER PRIMARY KEY, nombre TEXT, codigo TEXT, almacen TEXT, activo INTEGER);
CREATE TABLE salidas (id INTEGER PRIMARY KEY, producto_id INTEGER, origen_id INTEGER, destino_id INTEGER,
    cantidad REAL, fecha TEXT, tipo_operacion_id INTEGER, albaran TEXT);
CREATE INDEX i_ubic_padre ON ubicaciones(padre_id);
CREATE INDEX i_ubic_hueco ON ubicaciones(hueco_id);
CREATE INDEX i_stock_ubic ON stock(ubicacion_id);
CREATE INDEX i_stock_prod ON stock(producto_id);
CREATE INDEX i_sal_origen ON salidas(origen_id);
CREATE INDEX i_sal_fecha ON salidas(fecha);
"""


def _id(valor):
    """Many2one de XML-RPC ([id, 'nombre'] o False) -> id o None."""
    return valor[0] if isinstance(valor, (list, tuple)) and valor else None


def _nombre(valor):
    return valor[1] if isinstance(valor, (list, tuple)) and len(valor) > 1 else None


def clasificar_en_bd(bd):
    """Rellena las columnas deducidas (tipo de ubicación, hueco, modelo, zona, litros…) a partir de las columnas
    tal como vienen de Odoo. Se llama al acabar la descarga y, con reglas nuevas, sobre una copia en memoria
    («python programa.py resumen»): la copia bajada no se toca."""
    datos = []
    for i, nombre, ruta, codigo in bd.execute('SELECT id, nombre, ruta, codigo_barras FROM ubicaciones').fetchall():
        k = U.clasificar(nombre, ruta, codigo or '')
        datos.append((k['tipo'], k['lineal'], k['posicion'], k['nivel'], int(k['en_nave']), i))
    bd.executemany('UPDATE ubicaciones SET tipo = ?, lineal = ?, posicion = ?, nivel = ?, en_nave = ?, hueco_id = NULL '
                   'WHERE id = ?', datos)
    # Todo hijo de un hueco es un contenedor (KO_/TT_, pero también GC_, ECIGC_, MI_, números…).
    bd.execute("UPDATE ubicaciones SET tipo = 'contenedor', lineal = NULL, posicion = NULL, nivel = NULL "
               "WHERE tipo <> 'hueco' AND padre_id IN (SELECT id FROM ubicaciones WHERE tipo = 'hueco')")
    # Hueco de cada fila: el propio hueco; para un contenedor, su padre si el padre es hueco.
    bd.execute("UPDATE ubicaciones SET hueco_id = id WHERE tipo = 'hueco'")
    bd.execute("UPDATE ubicaciones SET hueco_id = (SELECT p.id FROM ubicaciones p WHERE p.id = ubicaciones.padre_id "
               "AND p.tipo = 'hueco') WHERE tipo = 'contenedor'")
    datos = []
    for i, ref, nombre, temp, vol in bd.execute(
            'SELECT id, referencia, nombre, temporada, volumen_m3 FROM productos').fetchall():
        modelo, color, talla = P.partir_codigo(ref, nombre)
        fam = P.familia(modelo)
        litros, estimado = P.litros(vol, fam)
        datos.append((modelo, color, talla, fam, P.zona(temp or ''), litros, int(estimado), i))
    bd.executemany('UPDATE productos SET modelo = ?, color = ?, talla = ?, familia = ?, zona = ?, litros = ?, '
                   'litros_estimado = ? WHERE id = ?', datos)
    bd.commit()


def copias_completas(carpeta):
    return sorted(Path(carpeta).glob('*_odoo.sqlite'))


class Descarga:

    def __init__(self, cliente, carpeta, pagina=2000, avisar=print, ahora=None, reloj=time.monotonic):
        self.c = cliente
        self.carpeta = Path(carpeta)
        self.pagina = pagina
        self.avisar = avisar
        self.ahora = ahora or datetime.datetime.now()
        self.reloj = reloj

    # ------------------------------------------------------------------ pasos
    def _paginas(self, modelo, dominio, campos, contexto=None, que=''):
        n, t = 0, self.reloj()
        for filas in self.c.leer_paginado(modelo, dominio, campos, pagina=self.pagina, contexto=contexto):
            n += len(filas)
            yield filas
            self.avisar('  %s: %d filas (%.0f s)' % (que or modelo, n, self.reloj() - t))

    def ubicaciones(self, bd):
        dominio = [('company_id', '=', COMPANIA), ('usage', '=', 'internal')]
        campos = ['name', 'complete_name', 'location_id', 'barcode', 'active']
        for filas in self._paginas('stock.location', dominio, campos, SIN_ARCHIVAR, 'ubicaciones'):
            datos = []
            for f in filas:
                k = U.clasificar(f['name'], f['complete_name'], f['barcode'] or '')
                datos.append((f['id'], f['name'], f['complete_name'], _id(f['location_id']), f['barcode'] or None,
                              int(bool(f['active'])), k['tipo'], k['lineal'], k['posicion'], k['nivel'],
                              int(k['en_nave'])))
            bd.executemany('INSERT INTO ubicaciones (id, nombre, ruta, padre_id, codigo_barras, activa, tipo, lineal, '
                           'posicion, nivel, en_nave) VALUES (?,?,?,?,?,?,?,?,?,?,?)', datos)

    def stock(self, bd):
        dominio = [('company_id', '=', COMPANIA), ('location_id.usage', '=', 'internal'), ('quantity', '!=', 0)]
        campos = ['location_id', 'product_id', 'quantity', 'reserved_quantity']
        for filas in self._paginas('stock.quant', dominio, campos, que='stock'):
            bd.executemany('INSERT INTO stock VALUES (?,?,?,?,?)',
                           [(f['id'], _id(f['location_id']), _id(f['product_id']), f['quantity'],
                             f['reserved_quantity']) for f in filas])

    def productos(self, bd):
        ids = [r[0] for r in bd.execute('SELECT DISTINCT producto_id FROM stock WHERE producto_id IS NOT NULL '
                                        'ORDER BY producto_id')]
        filas_p, plantillas = [], set()
        for i in range(0, len(ids), LOTE_READ):
            filas = self.c.llamar('product.product', 'read',
                                  [ids[i:i + LOTE_READ], ['default_code', 'name', 'barcode', 'product_tmpl_id',
                                                          'volume', 'weight', 'active']], {'context': SIN_ARCHIVAR})
            filas_p += filas
            plantillas.update(_id(f['product_tmpl_id']) for f in filas if f['product_tmpl_id'])
            self.avisar('  productos: %d de %d' % (len(filas_p), len(ids)))
        temporada = {}
        plantillas = sorted(plantillas)
        for i in range(0, len(plantillas), LOTE_READ):
            for f in self.c.llamar('product.template', 'read', [plantillas[i:i + LOTE_READ], ['season_id']],
                                   {'context': SIN_ARCHIVAR}):
                temporada[f['id']] = P.nombre_temporada(f['season_id'])
            self.avisar('  plantillas (temporada): %d de %d' % (min(i + LOTE_READ, len(plantillas)), len(plantillas)))
        bd.executemany('INSERT INTO productos (id, referencia, nombre, ean, plantilla_id, temporada, volumen_m3, '
                       'peso_kg, activo) VALUES (?,?,?,?,?,?,?,?,?)',
                       [(f['id'], f['default_code'] or None, f['name'], f['barcode'] or None, _id(f['product_tmpl_id']),
                         temporada.get(_id(f['product_tmpl_id']), ''), f['volume'] or 0, f['weight'] or 0,
                         int(bool(f['active']))) for f in filas_p])

    def tipos_operacion(self, bd):
        filas = self.c.llamar('stock.picking.type', 'search_read',
                              [[('company_id', '=', COMPANIA), ('code', 'in', list(CODIGOS_SALIDA))]],
                              {'fields': ['name', 'code', 'warehouse_id', 'active'], 'limit': 1000,
                               'context': SIN_ARCHIVAR})
        bd.executemany('INSERT INTO tipos_operacion VALUES (?,?,?,?,?)',
                       [(f['id'], f['name'], f['code'], _nombre(f['warehouse_id']), int(bool(f['active'])))
                        for f in filas])
        return [f['id'] for f in filas]

    def salidas(self, bd, desde, anterior):
        """`desde`: fecha (date) del histórico. `anterior`: ruta de la copia anterior o None."""
        campos_linea = self.c.campos('stock.move.line')
        compania = (('company_id', '=', COMPANIA) if 'company_id' in campos_linea
                    else ('move_id.company_id', '=', COMPANIA))
        fecha_desde = desde.strftime('%Y-%m-%d 00:00:00')
        pedir_desde = fecha_desde
        if anterior:
            bd.execute('ATTACH DATABASE ? AS ant', (str(anterior),))
            bd.execute('INSERT INTO salidas SELECT * FROM ant.salidas WHERE fecha >= ?', (fecha_desde,))
            ultima = bd.execute("SELECT valor FROM ant.meta WHERE clave = 'fecha_descarga'").fetchone()[0]
            bd.commit()
            bd.execute('DETACH DATABASE ant')
            margen = datetime.datetime.fromisoformat(ultima) - datetime.timedelta(days=MARGEN_DIAS)
            pedir_desde = max(fecha_desde, margen.strftime('%Y-%m-%d %H:%M:%S'))
            self.avisar('  salidas: %d líneas de la copia anterior; se piden a Odoo desde %s'
                        % (bd.execute('SELECT COUNT(*) FROM salidas').fetchone()[0], pedir_desde))
        # Una sola tanda (no tipo por tipo: con los tipos de pocas líneas PostgreSQL recorría la tabla entera cada vez)
        # y solo los tipos del almacén de KOROSHI. El tipo de cada línea se saca luego de su albarán.
        tipos = [r[0] for r in bd.execute('SELECT id FROM tipos_operacion WHERE almacen = ?', (ALMACEN_KOROSHI,))]
        if not tipos:
            raise ValueError('No hay tipos de operación del almacén «%s»' % ALMACEN_KOROSHI)
        base = [('state', '=', 'done'), compania, ('picking_id.picking_type_id', 'in', tipos)]
        campos = ['product_id', 'location_id', 'location_dest_id', 'qty_done', 'date', 'picking_id']
        nuevos_albaranes = set()
        for filas in self._paginas('stock.move.line', base + [('date', '>=', pedir_desde)], campos, que='salidas'):
            bd.executemany('INSERT OR REPLACE INTO salidas VALUES (?,?,?,?,?,?,?,?)',
                           [(f['id'], _id(f['product_id']), _id(f['location_id']), _id(f['location_dest_id']),
                             f['qty_done'], f['date'], None, _nombre(f['picking_id'])) for f in filas])
            nuevos_albaranes.update((_id(f['picking_id']), f['id']) for f in filas if f['picking_id'])
        # Tipo de operación de cada línea nueva, por su albarán (read de stock.picking en lotes de 2.000)
        por_albaran = {}
        for a, linea in nuevos_albaranes:
            por_albaran.setdefault(a, []).append(linea)
        ids = sorted(por_albaran)
        for k in range(0, len(ids), LOTE_READ):
            leidos = self.c.llamar('stock.picking', 'read', [ids[k:k + LOTE_READ], ['picking_type_id']],
                                   {'context': SIN_ARCHIVAR})
            bd.executemany('UPDATE salidas SET tipo_operacion_id = ? WHERE id = ?',
                           [(_id(a['picking_type_id']), linea) for a in leidos for linea in por_albaran[a['id']]])
            self.avisar('  albaranes (tipo de operación): %d de %d' % (min(k + LOTE_READ, len(ids)), len(ids)))
        avisos = []
        if anterior:      # comprobar que el incremental no se ha dejado nada
            local = bd.execute('SELECT COUNT(*) FROM salidas WHERE fecha >= ?', (fecha_desde,)).fetchone()[0]
            en_odoo = self.c.contar('stock.move.line', base + [('date', '>=', fecha_desde)])
            if en_odoo != local:
                avisos.append('Salidas: %d en la copia y %d en Odoo. Repetir con --completa.' % (local, en_odoo))
        return avisos

    # ------------------------------------------------------------------ todo junto
    def ejecutar(self, desde=None, con_salidas=True, completa=False):
        self.carpeta.mkdir(parents=True, exist_ok=True)
        final = self.carpeta / ('%s_odoo.sqlite' % self.ahora.strftime('%Y%m%d_%H%M'))
        parcial = final.with_name(final.name + '.parcial')
        if final.exists() or parcial.exists():
            raise FileExistsError('Ya existe %s: no se sobrescribe ninguna copia.' % final.name)
        previas = copias_completas(self.carpeta)
        anterior = previas[-1] if previas else None
        desde_anterior = None
        if anterior:
            with sqlite3.connect(anterior) as a:
                fila = a.execute("SELECT valor FROM meta WHERE clave = 'desde_salidas'").fetchone()
                desde_anterior = datetime.date.fromisoformat(fila[0]) if fila and fila[0] else None
        if desde is None:
            desde = desde_anterior
        if con_salidas and desde is None:
            raise ValueError('Primera descarga: hay que decir desde cuándo bajar las salidas (--desde AAAA-MM-DD)')
        # Incremental solo si la copia anterior ya tenía salidas desde esa fecha o antes.
        base_salidas = anterior if (con_salidas and not completa and desde_anterior and desde_anterior <= desde) else None

        inicio = self.reloj()
        bd = sqlite3.connect(parcial)
        try:
            bd.executescript(ESQUEMA)
            self.avisar('Ubicaciones…')
            self.ubicaciones(bd)
            bd.commit()
            self.avisar('Stock…')
            self.stock(bd)
            bd.commit()
            self.avisar('Productos…')
            self.productos(bd)
            bd.commit()
            self.tipos_operacion(bd)
            clasificar_en_bd(bd)
            avisos = []
            if con_salidas:
                self.avisar('Salidas desde %s%s…' % (desde, ' (incremental)' if base_salidas else ''))
                avisos = self.salidas(bd, desde, base_salidas)
            elif anterior:
                self.avisar('Salidas: no se piden a Odoo; se copian de %s' % anterior.name)
                bd.execute('ATTACH DATABASE ? AS ant', (str(anterior),))
                bd.execute('INSERT INTO salidas SELECT * FROM ant.salidas')
                bd.commit()
                bd.execute('DETACH DATABASE ant')
            bd.commit()
            meta = {
                'fecha_descarga': self.ahora.isoformat(timespec='seconds'),
                'servidor': getattr(self.c, 'url', ''), 'bd': getattr(self.c, 'bd', ''),
                'desde_salidas': desde.isoformat() if desde else '',
                'salidas_de_odoo': 'si' if con_salidas else ('copiadas de %s' % anterior.name if anterior else 'no'),
                'copia_anterior': anterior.name if anterior else '',
                'segundos': '%.0f' % (self.reloj() - inicio),
                'peticiones': str(getattr(self.c, 'peticiones', '')),
                'avisos': json.dumps(avisos, ensure_ascii=False),
            }
            bd.executemany('INSERT INTO meta VALUES (?,?)', meta.items())
            res = R.resumen(bd)
            bd.execute('INSERT INTO meta VALUES (?,?)', ('resumen', json.dumps(res, ensure_ascii=False)))
            bd.commit()
        finally:
            bd.close()
        parcial.rename(final)
        texto = R.como_texto(res, meta)
        final.with_suffix('.resumen.txt').write_text(texto, encoding='utf-8')
        return final, res, avisos, texto
