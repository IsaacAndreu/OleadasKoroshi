# -*- coding: utf-8 -*-
"""Programa de Windows de redistribución de NAU-2 (KOROSHI) · 26/11/2026.

Se abre con doble clic en «Redistribucion NAU-2.bat» (o `pythonw ventana.py`). Solo lee:
- las matrices de KOROSHI en bin/versiones (la última versión de cada una, ver redistrib/fuentes.py);
- la última copia de Odoo de copias/ (se baja aparte, con «python programa.py descargar» y el sí de Isaac).
No se conecta a Odoo ni escribe en Odoo ni en las matrices. Lo que exporta va a Excels nuevos con fecha y hora.

Pestañas: Fuentes · Compactación zona 0 (por lineal) · Plano · Cajas a 0 (retirar) · Cajas a mover.
"""
import datetime
import os
import sys
import traceback
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

from redistrib import compactar as C
from redistrib import configuracion, fuentes, mapa_json
from redistrib.descarga import copias_completas

TITULO = 'Redistribución NAU-2 · KOROSHI'
RAIZ = configuracion.CARPETA.parent                     # redistribucion/
CARPETA_V2 = RAIZ / 'prototipo-mapa_2026-11-23_v2'      # geometría de la nave (copia de kpi.py)

COLORES = {          # estado de la posición en la compactación
    'libre entera': '#2fa37f', 'libera niveles': '#9bd8c2', 'recibe cajas': '#2f6fdb',
    'retirar cajas a 0': '#e0a526', 'sin cambios': '#b8c7e6', 'fuera': '#e3e6ea',
}
NOMBRES = {
    'libre entera': 'Posición libre entera', 'libera niveles': 'Se vacía algún nivel', 'recibe cajas': 'Recibe cajas',
    'retirar cajas a 0': 'Solo retirar cajas a 0', 'sin cambios': 'Zona 0 sin cambios', 'fuera': 'Zona Z / sin stock',
}


def esp(v, d=0):
    if v is None or v == '':
        return ''
    if isinstance(v, (int, float)):
        return ('{:,.%df}' % d).format(v).replace(',', 'X').replace('.', ',').replace('X', '.')
    return str(v)


# ============================================================================================== cálculo (en hilo)
def calcular(aviso):
    """Todo lo que enseña el programa, desde la última copia y las últimas matrices. No habla con Odoo."""
    aviso('Buscando la última copia de Odoo y las matrices…')
    copia = copias_completas(configuracion.CARPETA / 'copias')[-1]
    master = fuentes.matriz(1)
    if not master:
        raise ValueError('No encuentro la matriz KOROSHI_1_MASTER en %s' % fuentes.CARPETA_MATRICES)
    r = C.ReglasCompactar()
    aviso('Leyendo %s (litros por modelo)…' % master.ruta.name)
    lt = C.leer_master(master.ruta)
    aviso('Leyendo la copia de Odoo %s…' % copia.name)
    datos = C.cargar(copia, CARPETA_V2, lt, r)
    aviso('Clasificando modelos (ABC × tamaño)…')
    mcs = C.clasificar(datos, r)
    aviso('Calculando la compactación…')
    pasos, res = C.compactar(datos, mcs, r)
    aviso('Repartiendo tallas por altura…')
    alturas = C.tallas_por_altura(datos, mcs, r)
    ko_propios, ko_lineal = C.ko_mixta(datos, mcs, r)
    mcs_lineal = {}
    for c in datos['cajas'].values():
        for x in c['lineas']:
            if x['zona'] == '0':
                mcs_lineal.setdefault(c['hueco'][0], set()).add(x['mc'])
    aviso('Buscando cajas a 0…')
    vacias = C.cajas_a_cero(copia, datos, r)
    aviso('Preparando lineales y plano…')
    mapa = C.para_mapa(copia, datos, mcs, pasos, res, vacias, r)
    bd = mapa_json.abrir_copia(copia)
    niveles = {}
    for l, p, n in bd.execute(
            "SELECT lineal, posicion, nivel FROM ubicaciones WHERE tipo = 'hueco' AND en_nave AND activa "
            "AND lineal IS NOT NULL AND posicion IS NOT NULL"):
        if r.lineales[0] <= l <= r.lineales[1]:
            niveles.setdefault((l, p), set()).add(n or 1)
    bd.close()
    for f in mapa['lineales']:            # huecos que se liberan en el lineal: lo que más rinde, primero
        f['liberados'] = f['solo_cajas_a_0'] + f['se_vacian_compactando']
    orden = sorted(mapa['lineales'], key=lambda f: (-f['liberados'], f['cajas_a_0'] + f['cajas_a_mover'], f['l']))
    return {'copia': copia, 'master': master, 'reglas': r, 'mcs': mcs, 'pasos': pasos, 'resumen': res,
            'vacias': vacias, 'mapa': mapa, 'posiciones': sorted(niveles), 'niveles': niveles, 'orden': orden,
            'alturas': alturas, 'mcs_lineal': mcs_lineal, 'ko_propios': ko_propios, 'ko_lineal': ko_lineal}


COLS_ALTURAS = ['Modelo-color', 'Familia', 'ABC', 'Líneas 28 días', 'Abajo · alturas 1–2 (tallas)',
                'Arriba · alturas 3–4 (tallas)', 'Arriba del todo · restos', 'Uds abajo', 'Uds arriba', 'Uds restos',
                'Cajas abajo', 'Cajas arriba', 'Cajas restos', 'Tallas con KO propia (3+ cajas)']


def filas_alturas(res, solo=None):
    filas = []
    for mc, a in res['alturas'].items():
        if solo is not None and mc not in solo:
            continue
        m = res['mcs'][mc]
        filas.append([mc, m['familia'], m['abc'], m['lineas'], ', '.join(a['abajo']), ', '.join(a['arriba']), ', '.join(a['restos']),
                      round(a['uds']['abajo']), round(a['uds']['arriba']), round(a['uds']['restos']),
                      a['cajas']['abajo'], a['cajas']['arriba'], a['cajas']['restos'],
                      ', '.join(t for t in a['abajo'] + a['arriba'] + a['restos'] if (mc, t) in res['ko_propios']) or '— (una KO para todo)'])
    return sorted(filas, key=lambda f: (-f[3], f[0]))


AYUDA_ALTURAS = ('Una KO por hueco, modelo-color y altura (no una por caja). Las tallas de cada modelo-color, por sus '
                 'propias líneas de 28 días. Cada columna (C1–C4 de Odoo) tiene 4 cajas de alto: abajo (alturas 1–2, '
                 'lo cómodo) las más pedidas hasta más o menos la mitad de sus unidades; el resto, arriba (3–4); los '
                 'restos de talla (≤ 2 uds o ≤ 5 %), arriba del todo. Las alturas aún no existen en Odoo. '
                 'Cajas = uds ÷ uds por caja de 84 L (MASTER). KO mixta (Isaac 26/11): una talla con stock para 3 cajas o '
                 'más lleva su propia KO; las demás tallas del modelo-color comparten una KO en el hueco.')


# ============================================================================================== estado de un hueco
COLOR_NIVEL = {
    'libre al retirar': ('#2fa37f', 'Queda libre al retirar las cajas vacías'),
    'se vacía': ('#7fcdb0', 'Se vacía: sus cajas van a otro hueco'),
    'recibe': ('#2f6fdb', 'Recibe cajas de otro hueco'),
    'retirar vacías': ('#e0a526', 'Tiene cajas vacías que retirar (y se queda)'),
    'sin cambios': ('#b8c7e6', 'Zona 0, sin cambios'),
    'z': ('#e3e6ea', 'Zona Z o sin nada'),
}


def estado_nivel(fila, fuera):
    """fila = [nivel, paso, sale, recibe, ceros, litros hoy, litros después] de compactar.para_mapa."""
    if fila is None:
        return 'z'
    _, paso, _, recibe, ceros, hoy, _ = fila
    if fuera:                      # posición de la Z: solo cuenta si el hueco tiene cajas vacías y nada más
        return 'libre al retirar' if ceros and not hoy else 'z'
    if paso:
        return 'se vacía'
    if ceros and not hoy:
        return 'libre al retirar'
    if recibe:
        return 'recibe'
    if ceros:
        return 'retirar vacías'
    return 'sin cambios' if hoy else 'z'


class Trabajo(QtCore.QObject):
    aviso = QtCore.Signal(str)
    hecho = QtCore.Signal(object)
    fallo = QtCore.Signal(str)

    def ejecutar(self):
        try:
            self.hecho.emit(calcular(self.aviso.emit))
        except Exception as e:          # se enseña en pantalla; nunca lleva contraseñas (no se usan aquí)
            self.fallo.emit('%s\n\n%s' % (e, traceback.format_exc(limit=3)))


# ============================================================================================== tablas
class ModeloTabla(QtCore.QAbstractTableModel):
    def __init__(self, cols, filas=(), numericas=(), color=None):
        super().__init__()
        self.cols, self.filas, self.numericas, self.color = cols, list(filas), set(numericas), color

    def poner(self, filas):
        self.beginResetModel()
        self.filas = list(filas)
        self.endResetModel()

    def rowCount(self, _=QtCore.QModelIndex()):
        return len(self.filas)

    def columnCount(self, _=QtCore.QModelIndex()):
        return len(self.cols)

    def headerData(self, s, o, rol=Qt.DisplayRole):
        if rol == Qt.DisplayRole and o == Qt.Horizontal:
            return self.cols[s]
        return None

    def data(self, i, rol=Qt.DisplayRole):
        v = self.filas[i.row()][i.column()]
        if rol == Qt.DisplayRole:
            if isinstance(v, float) and self.cols[i.column()].startswith('%'):
                return esp(v * 100, 0) + ' %'
            return esp(v, 1 if isinstance(v, float) and v != int(v) else 0) if isinstance(v, (int, float)) else str(v)
        if rol == Qt.UserRole:                      # para ordenar (L99 antes que L100)
            if isinstance(v, str) and len(v) > 1 and v[0] == 'L' and v[1:4].strip().isdigit():
                return int(v[1:4]) * 1000 + (int(v[5:8]) if v[5:8].isdigit() else 0)
            return v if v is not None else -1
        if rol == Qt.TextAlignmentRole and i.column() in self.numericas:
            return int(Qt.AlignRight | Qt.AlignVCenter)
        if rol == Qt.BackgroundRole and self.color:
            c = self.color(self.filas[i.row()], i.column())
            return QtGui.QColor(c) if c else None
        return None


class Filtro(QtCore.QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.texto = ''
        self.setSortRole(Qt.UserRole)

    def poner(self, t):
        self.texto = t.strip().upper()
        self.invalidateFilter()

    def filterAcceptsRow(self, fila, padre):
        if not self.texto:
            return True
        m = self.sourceModel()
        return any(self.texto in str(v).upper() for v in m.filas[fila])


def exportar(padre, nombre, cols, filas):
    """Excel nuevo con fecha y hora. No sobrescribe."""
    import openpyxl
    from openpyxl.styles import Font
    sello = datetime.datetime.now().strftime('%Y%m%d_%H%M')
    defecto = str(RAIZ / ('%s_%s.xlsx' % (nombre, sello)))
    ruta, _ = QtWidgets.QFileDialog.getSaveFileName(padre, 'Exportar a Excel', defecto, 'Excel (*.xlsx)')
    if not ruta:
        return
    if Path(ruta).exists():
        QtWidgets.QMessageBox.warning(padre, TITULO, 'Ya existe %s.\nNo se sobrescribe: elige otro nombre.' % ruta)
        return
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = nombre[:31]
    ws.append(cols)
    for c in ws[1]:
        c.font = Font(bold=True)
    for f in filas:
        ws.append(list(f))
    ws.freeze_panes = 'A2'
    wb.save(ruta)
    QtWidgets.QMessageBox.information(padre, TITULO, 'Guardado en\n%s' % ruta)


class PanelTabla(QtWidgets.QWidget):
    """Tabla con filtro, orden por columna y «Exportar a Excel»."""
    doble = QtCore.Signal(list)

    def __init__(self, nombre, cols, numericas=(), ayuda='', color=None):
        super().__init__()
        self.nombre = nombre
        self.modelo = ModeloTabla(cols, numericas=numericas, color=color)
        self.filtro = Filtro()
        self.filtro.setSourceModel(self.modelo)
        lay = QtWidgets.QVBoxLayout(self)
        arriba = QtWidgets.QHBoxLayout()
        self.caja = QtWidgets.QLineEdit()
        self.caja.setPlaceholderText('Filtrar (texto en cualquier columna: L67, KO_090726, 2621JA50…)')
        self.caja.textChanged.connect(lambda t: (self.filtro.poner(t), self._cuenta()))
        self.cuenta = QtWidgets.QLabel()
        b = QtWidgets.QPushButton('Exportar a Excel')
        b.clicked.connect(self._exportar)
        arriba.addWidget(self.caja, 1)
        arriba.addWidget(self.cuenta)
        arriba.addWidget(b)
        lay.addLayout(arriba)
        if ayuda:
            a = QtWidgets.QLabel(ayuda)
            a.setWordWrap(True)
            a.setStyleSheet('color:#586374')
            lay.addWidget(a)
        self.vista = QtWidgets.QTableView()
        self.vista.setModel(self.filtro)
        self.vista.setSortingEnabled(True)
        self.vista.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.vista.setAlternatingRowColors(True)
        self.vista.verticalHeader().setVisible(False)
        self.vista.doubleClicked.connect(lambda i: self.doble.emit(self.modelo.filas[self.filtro.mapToSource(i).row()]))
        lay.addWidget(self.vista, 1)

    def poner(self, filas):
        self.modelo.poner(filas)
        self.filtro.sort(-1)                                   # el orden en que llegan (el del cálculo)
        self.vista.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)
        self.vista.resizeColumnsToContents()
        for c in range(self.modelo.columnCount()):
            self.vista.setColumnWidth(c, min(self.vista.columnWidth(c), 320))
        self._cuenta()

    def _cuenta(self):
        self.cuenta.setText('%s filas' % esp(self.filtro.rowCount()))

    def _exportar(self):
        filas = [self.modelo.filas[self.filtro.mapToSource(self.filtro.index(i, 0)).row()]
                 for i in range(self.filtro.rowCount())]
        exportar(self, self.nombre, self.modelo.cols, filas)


# ============================================================================================== plano
MODOS_PLANO = {
    # modo: (título del botón, explicación, [(color, texto de la leyenda)])
    'hoy': ('Hoy', 'Cómo está la zona 0 hoy: cuanto más oscuro, más lleno.',
            [('#dbe6fb', 'Poco lleno (< 25 %)'), ('#8fb0ee', 'A medias'), ('#2f5fd0', 'Lleno (> 60 %)'),
             ('#e3e6ea', 'Zona Z / sin nada')]),
    'paso1': ('Paso 1 · Retirar vacías', 'Dónde hay cajas vacías que retirar. En verde, las posiciones que quedan '
              'libres solo con eso.',
              [('#2fa37f', 'Queda libre al retirar'), ('#e0a526', 'Retirar cajas vacías'), ('#dfe6f3', 'Zona 0, nada que retirar'),
               ('#e3e6ea', 'Zona Z / sin nada')]),
    'paso2': ('Paso 2 · Juntar cajas', 'De dónde salen las cajas (verde) y adónde van (azul). Clic en una posición: '
              'flechas y lista de lo que hay que hacer.',
              [('#7fcdb0', 'Sus cajas se llevan a otro hueco'), ('#2f6fdb', 'Recibe cajas'), ('#dfe6f3', 'Zona 0, sin cambios'),
               ('#e3e6ea', 'Zona Z / sin nada')]),
    'final': ('Resultado', 'Cómo queda al acabar los dos pasos.',
              [(COLORES[e], NOMBRES[e]) for e in C.ESTADOS_MAPA]),
}


class Plano(QtWidgets.QGraphicsView):
    """Planta de la nave: una celda por posición. Se colorea por paso (hoy, retirar vacías, juntar cajas,
    resultado). Clic en una posición: sus instrucciones y flechas; doble clic: abrir su lineal."""
    lineal_elegido = QtCore.Signal(str)
    posicion_elegida = QtCore.Signal(int, int)
    ESCALA = 12.0          # píxeles por metro

    def __init__(self):
        super().__init__()
        self.setScene(QtWidgets.QGraphicsScene(self))
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setBackgroundBrush(QtGui.QColor('#eef0f3'))
        self.lineales = {}      # 'L67' -> QRectF
        self.celdas = {}        # (l, p) -> QGraphicsRectItem
        self.flechas = []
        self.marca = None
        self.modo = 'final'
        self.res = None

    # ---------------------------------------------------------------- ratón
    def wheelEvent(self, ev):
        f = 1.2 if ev.angleDelta().y() > 0 else 1 / 1.2
        self.scale(f, f)

    def _celda_en(self, ev):
        it = self.itemAt(ev.position().toPoint())
        return it.data(1) if it is not None and it.data(1) else None

    def mousePressEvent(self, ev):
        self._clic = ev.position().toPoint()
        super().mousePressEvent(ev)

    def mouseReleaseEvent(self, ev):
        super().mouseReleaseEvent(ev)
        if getattr(self, '_clic', None) is not None and (ev.position().toPoint() - self._clic).manhattanLength() < 4:
            lp = self._celda_en(ev)
            if lp:
                self.posicion_elegida.emit(lp[0], lp[1])
        self._clic = None

    def mouseDoubleClickEvent(self, ev):
        lp = self._celda_en(ev)
        if lp:
            self.lineal_elegido.emit('L%02d' % lp[0])
        else:
            super().mouseDoubleClickEvent(ev)

    # ---------------------------------------------------------------- dibujo
    def pintar(self, res):
        self.res = res
        G = mapa_json._geometria(CARPETA_V2)
        s = self.scene()
        s.clear()
        self.lineales, self.celdas, self.flechas, self.marca = {}, {}, [], None
        k = self.ESCALA
        y_max = max(G._y(p) + G._paso(p) for _, p in res['posiciones']) + 2
        self.y_max = y_max
        # pasillos transversales (geometría de kpi.py)
        x_min = min(G._x_celda(l)[0] for l, _ in res['posiciones']) - 1
        x_max = max(G._x_celda(l)[1] for l, _ in res['posiciones']) + 1
        for y0, y1, nom in ((6.5, 9.0, 'Pasillo transversal'), (29.0, 31.0, 'Pasillo central'), (43.0, 45.5, 'Pasillo transversal')):
            s.addRect(x_min * k, (y_max - y1) * k, (x_max - x_min) * k, (y1 - y0) * k, QtGui.QPen(Qt.NoPen),
                      QtGui.QBrush(QtGui.QColor('#e2e6ec')))
            t = s.addSimpleText(nom.upper(), QtGui.QFont('Segoe UI', 8, QtGui.QFont.Bold))
            t.setBrush(QtGui.QColor('#9aa3af'))
            t.setPos(x_min * k + 6, (y_max - (y0 + y1) / 2) * k - 6)
        sin_borde = QtGui.QPen(Qt.NoPen)
        for l, p in res['posiciones']:
            try:
                x0, x1 = G._x_celda(l)
                yc, paso = G._y(p), G._paso(p)
            except Exception:
                continue
            y0, y1 = yc - paso / 2 + 0.05, yc + paso / 2 - 0.05
            rect = QtCore.QRectF(x0 * k, (y_max - y1) * k, (x1 - x0) * k, (y1 - y0) * k)
            it = s.addRect(rect, sin_borde, QtGui.QBrush(QtGui.QColor('#e3e6ea')))
            it.setData(1, (l, p))
            self.celdas[(l, p)] = it
            nom = 'L%02d' % l
            self.lineales[nom] = self.lineales[nom].united(rect) if nom in self.lineales else rect
        fuente = QtGui.QFont('Segoe UI', 8, QtGui.QFont.Bold)
        for nom, rc in self.lineales.items():
            n = int(nom[1:])
            for y, desplaza in ((rc.bottom() + 2, 11), (rc.top() - 14, -11)):     # número arriba y abajo
                t = s.addSimpleText(str(n), fuente)
                t.setBrush(QtGui.QColor('#586374'))
                t.setPos(rc.center().x() - t.boundingRect().width() / 2, y + (desplaza if n % 2 else 0))
        bx, by = G.BASE
        s.addEllipse(bx * k - 9, (y_max - by) * k - 9, 18, 18, QtGui.QPen(Qt.NoPen), QtGui.QBrush(QtGui.QColor('#d92d20')))
        t = s.addSimpleText('EXPEDICIÓN · muelles', QtGui.QFont('Segoe UI', 10, QtGui.QFont.Bold))
        t.setBrush(QtGui.QColor('#d92d20'))
        t.setPos(bx * k - 60, (y_max - by) * k + 12)
        self.colorear(self.modo)
        self.encajar()

    def centro(self, l, p):
        it = self.celdas.get((l, p))
        return it.rect().center() if it else None

    def colorear(self, modo):
        self.modo = modo
        if not self.res:
            return
        pos = self.res['mapa']['posiciones']
        cap = self.res['reglas'].litros_hueco
        for (l, p), it in self.celdas.items():
            d = pos.get('L%02d|%d' % (l, p))
            filas = d['n'] if d else []
            fuera = not d or d['e'] == 'fuera'
            ceros = any(f[4] for f in filas)
            solo_ceros_fuera = fuera and any(f[4] and not f[5] for f in filas)
            if modo == 'hoy':
                if fuera:
                    c = '#e3e6ea'
                else:
                    lleno = sum(f[5] for f in filas) / (cap * max(1, len(self.res['niveles'].get((l, p), ())) or 1))
                    c = '#dbe6fb' if lleno < 0.25 else '#8fb0ee' if lleno < 0.6 else '#2f5fd0'
            elif modo == 'paso1':
                if not ceros:
                    c = '#e3e6ea' if fuera else '#dfe6f3'
                elif solo_ceros_fuera or (not fuera and not any(f[5] for f in filas)):
                    c = '#2fa37f'
                elif fuera:
                    c = '#e3e6ea'
                else:
                    c = '#e0a526'
            elif modo == 'paso2':
                if fuera:
                    c = '#e3e6ea'
                elif any(f[1] for f in filas):
                    c = '#7fcdb0'
                elif any(f[3] for f in filas):
                    c = '#2f6fdb'
                else:
                    c = '#dfe6f3'
            else:
                c = COLORES[d['e'] if d else 'fuera']
            it.setBrush(QtGui.QBrush(QtGui.QColor(c)))
            it.setToolTip('<b>L%02d P%02d</b><br>Clic: qué hay que hacer aquí · doble clic: abrir el lineal' % (l, p))

    def encajar(self):
        """La nave entera en pantalla (al pintar y la primera vez que se enseña)."""
        self.resetTransform()
        self.fitInView(self.scene().itemsBoundingRect().adjusted(-20, -20, 20, 20), Qt.KeepAspectRatio)
        self.encajada = self.isVisible()

    def showEvent(self, ev):
        super().showEvent(ev)
        if not getattr(self, 'encajada', True):
            QtCore.QTimer.singleShot(0, self.encajar)

    def quitar_marcas(self):
        s = self.scene()
        for f in self.flechas:
            s.removeItem(f)
        self.flechas = []
        if self.marca is not None:
            s.removeItem(self.marca)
            self.marca = None

    def flecha(self, a, b, color):
        """Flecha de a hacia b (puntos de la escena)."""
        s = self.scene()
        pluma = QtGui.QPen(QtGui.QColor(color), 2.2)
        pluma.setCapStyle(Qt.RoundCap)
        if (a - b).manhattanLength() < 1:            # mismo sitio (otro nivel): un círculo
            self.flechas.append(s.addEllipse(a.x() - 7, a.y() - 7, 14, 14, pluma))
            return
        linea = QtCore.QLineF(a, b)
        self.flechas.append(s.addLine(linea, pluma))
        ang = linea.angle()
        punta = QtGui.QPolygonF([b,
                                 b + QtCore.QLineF.fromPolar(10, ang + 155).p2(),
                                 b + QtCore.QLineF.fromPolar(10, ang - 155).p2()])
        self.flechas.append(s.addPolygon(punta, QtGui.QPen(Qt.NoPen), QtGui.QBrush(QtGui.QColor(color))))
        for f in self.flechas[-2:]:
            f.setZValue(5)

    def marcar(self, rect, color='#d92d20'):
        self.marca = self.scene().addRect(rect.adjusted(-3, -3, 3, 3), QtGui.QPen(QtGui.QColor(color), 3))
        self.marca.setZValue(6)

    def ensenar_movimientos(self, movs, marco, acercar=True):
        """movs = [((l, p) desde, (l, p) hasta, sale_de_aquí)]: flechas verdes las que salen, azules las que entran."""
        self.quitar_marcas()
        for de, a, sale in movs:
            ca, cb = self.centro(*de), self.centro(*a)
            if ca is not None and cb is not None:
                self.flecha(ca, cb, '#0f7b5a' if sale else '#1d4fc4')
        if marco is not None:
            self.marcar(marco)
            if acercar:
                zona = marco
                for f in self.flechas:
                    zona = zona.united(f.boundingRect())
                self.fitInView(zona.adjusted(-120, -60, 120, 60), Qt.KeepAspectRatio)

    def ir_a_lineal(self, nom, movs=()):
        rc = self.lineales.get(nom)
        if rc:
            self.ensenar_movimientos(movs, rc)

# ============================================================================================== piezas de pantalla
ESTILO = """
QWidget { font-family: 'Segoe UI'; font-size: 10.5pt; color: #18202b; }
QMainWindow, #fondo { background: #f4f5f7; }
#menu { background: #18202b; border: 0; }
#menu::item { color: #d5dbe3; padding: 14px 18px; font-size: 11.5pt; }
#menu::item:selected { background: #2f5fd0; color: white; }
#menu::item:hover:!selected { background: #263142; }
.tarjeta, #tarjeta { background: white; border: 1px solid #e4e7ec; border-radius: 10px; }
QPushButton { background: white; border: 1px solid #cfd5dd; border-radius: 6px; padding: 6px 14px; }
QPushButton:hover { border-color: #2f5fd0; }
QPushButton#principal { background: #2f5fd0; color: white; border: 0; font-weight: 600; padding: 8px 18px; }
QPushButton#principal:hover { background: #2550b5; }
QLineEdit { background: white; border: 1px solid #cfd5dd; border-radius: 6px; padding: 5px 8px; }
QTableView { background: white; border: 1px solid #e4e7ec; gridline-color: #eef0f3; selection-background-color: #e8eefc;
             selection-color: #18202b; alternate-background-color: #f8f9fb; }
QHeaderView::section { background: #f8f9fb; border: 0; border-bottom: 1px solid #e4e7ec; padding: 6px; font-weight: 600; }
QListWidget#lineales { background: white; border: 1px solid #e4e7ec; border-radius: 8px; }
QListWidget#lineales::item { padding: 8px 10px; border-bottom: 1px solid #f0f2f5; }
QListWidget#lineales::item:selected { background: #e8eefc; color: #18202b; }
QStatusBar { background: white; color: #586374; }
"""


def etiqueta(html, tam=None, color=None, ajustar=True):
    q = QtWidgets.QLabel(html)
    q.setTextFormat(Qt.RichText)
    q.setWordWrap(ajustar)
    estilo = []
    if tam:
        estilo.append('font-size:%dpt' % tam)
    if color:
        estilo.append('color:%s' % color)
    if estilo:
        q.setStyleSheet(';'.join(estilo))
    return q


class Paso(QtWidgets.QFrame):
    """Tarjeta grande de un paso del plan de trabajo."""

    def __init__(self, numero, color, titulo, texto_boton, al_pulsar):
        super().__init__()
        self.setObjectName('tarjeta')
        self.setStyleSheet('#tarjeta { background: white; border: 1px solid #e4e7ec; border-left: 8px solid %s; '
                           'border-radius: 10px; }' % color)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.addWidget(etiqueta('<span style="color:%s;font-weight:700">PASO %d</span>' % (color, numero), 10))
        lay.addWidget(etiqueta('<b>%s</b>' % titulo, 15))
        self.cifra = etiqueta('', 30)
        self.cifra.setStyleSheet('font-size:30pt;font-weight:700;color:%s' % color)
        lay.addWidget(self.cifra)
        self.texto = etiqueta('', 10.5, '#586374')
        lay.addWidget(self.texto, 1)
        b = QtWidgets.QPushButton(texto_boton)
        b.setObjectName('principal')
        b.clicked.connect(al_pulsar)
        lay.addWidget(b, 0, Qt.AlignLeft)

    def poner(self, cifra, texto):
        self.cifra.setText(cifra)
        self.texto.setText(texto)


class Inicio(QtWidgets.QWidget):
    """Plan de trabajo: qué hacer, en qué orden y por qué lineal empezar."""
    abrir_lineal = QtCore.Signal(str)
    abrir_lista = QtCore.Signal(int)

    def __init__(self):
        super().__init__()
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(24, 18, 24, 18)
        lay.setSpacing(14)
        self.cab = etiqueta('<span style="font-size:20pt;font-weight:700">Plan de trabajo · zona 0</span>')
        self.sub = etiqueta('Calculando…', 10.5, '#586374')
        lay.addWidget(self.cab)
        lay.addWidget(self.sub)
        fila = QtWidgets.QHBoxLayout()
        fila.setSpacing(14)
        self.p1 = Paso(1, '#e0a526', 'Retirar las cajas vacías', 'Ver la lista', lambda: self.abrir_lista.emit(0))
        self.p2 = Paso(2, '#2f6fdb', 'Juntar cajas (compactar)', 'Ver la lista', lambda: self.abrir_lista.emit(1))
        self.p3 = Paso(3, '#2fa37f', 'Lineales que podrían quedar vacíos', 'Ver los lineales', lambda: self.abrir_lista.emit(2))
        for p in (self.p1, self.p2, self.p3):
            fila.addWidget(p, 1)
        lay.addLayout(fila)
        lay.addWidget(etiqueta('<span style="font-size:13pt;font-weight:700">Por dónde empezar</span>'
                               '<span style="color:#586374">  ·  los lineales donde más huecos se liberan. '
                               'Clic para ver el lineal y su hoja de trabajo.</span>'))
        self.lista = QtWidgets.QTableWidget(0, 6)
        self.lista.setHorizontalHeaderLabels(['Orden', 'Lineal', 'Huecos que se liberan', 'Cajas vacías a retirar',
                                              'Cajas a mover', 'Huecos en uso hoy → después'])
        self.lista.verticalHeader().setVisible(False)
        self.lista.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.lista.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.lista.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.lista.cellClicked.connect(lambda f, c: self.abrir_lineal.emit(self.lista.item(f, 1).text()))
        lay.addWidget(self.lista, 1)
        self.aviso = etiqueta('', 9.5, '#b45309')
        lay.addWidget(self.aviso)

    def poner(self, res):
        m, r = res['mapa'], res['resumen']
        rc = m['resumen']
        vacias = rc['cajas_a_cero_zona0'] + rc['cajas_solo_a_cero_desde_l44']
        self.sub.setText('Datos de Odoo del %s · %s v%d · propuesta sin probar en la nave'
                         % (r['fecha_copia'], res['master'].nombre, res['master'].version))
        self.p1.poner(esp(vacias), 'cajas que en Odoo están a 0. Comprobar que están vacías y retirarlas.<br>'
                      '<b>%s huecos</b> quedan libres solo con esto, sin mover ninguna prenda.'
                      % esp(rc['huecos_solo_a_cero_desde_l44']))
        ko = [sum(v[0] for v in res['ko_lineal'].values()), sum(v[1] for v in res['ko_lineal'].values())]
        self.p2.poner(esp(r['cajas_a_mover']), 'cajas a llevar a otro hueco del mismo lineal o de al lado '
                      '(%s uds).<br><b>%s huecos</b> más quedan libres.<br>KO mixta: <b>%s → %s</b> KO en la zona 0.'
                      % (esp(r['uds_a_mover']), esp(r['huecos_liberados']), esp(ko[0]), esp(ko[1])))
        self.p3.poner(esp(rc['lineales_vaciables']), 'de %d lineales de la 0 quedarían tan vacíos que su contenido '
                      'cabría en los demás.<br><i>Estimación por volumen: falta medir lo que cabe en un palé.</i>'
                      % len(m['lineales']))
        orden = res['orden']
        self.lista.setRowCount(len(orden))
        for i, f in enumerate(orden):
            valores = [i + 1, f['l'], f['liberados'], f['cajas_a_0'], f['cajas_a_mover'],
                       '%s → %s' % (esp(f['huecos_hoy']), esp(f['huecos_despues']))]
            for j, v in enumerate(valores):
                it = QtWidgets.QTableWidgetItem(esp(v) if isinstance(v, (int, float)) else v)
                it.setTextAlignment(int(Qt.AlignCenter))
                if j == 1:
                    it.setFont(QtGui.QFont('Segoe UI', 10, QtGui.QFont.Bold))
                self.lista.setItem(i, j, it)
        self.aviso.setText('FALTA MEDIDA: ' + ' '.join(m['falta_medida']))


class Alzado(QtWidgets.QGraphicsView):
    """Un lineal visto de frente: posiciones de izquierda a derecha y, en cada una, sus columnas C1–C4 una al lado de
    otra (cada columna, 4 cajas de alto)."""

    def __init__(self):
        super().__init__()
        self.setScene(QtWidgets.QGraphicsScene(self))
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setBackgroundBrush(QtGui.QColor('#f4f5f7'))
        self.setMinimumHeight(230)

    def pintar(self, res=None, l=None):
        if res is not None:
            self.res, self.l = res, l
        res, l = getattr(self, 'res', None), getattr(self, 'l', None)
        if res is None:
            return
        s = self.scene()
        s.clear()
        pos = res['mapa']['posiciones']
        ps = sorted(p for (ll, p) in res['niveles'] if ll == l)
        if not ps:
            return
        # C1–C4 son COLUMNAS (Isaac 26/11), una al lado de otra; cada columna es una barra de 4 cajas de alto.
        # El lineal va en dos filas (primera mitad de posiciones arriba, segunda abajo) para que se lea.
        vw, vh = max(400, self.viewport().width() - 40), max(200, self.viewport().height() - 30)
        mitad = (len(ps) + 1) // 2
        filas_ps = [ps[:mitad], ps[mitad:]]
        hueco_p = 6                                  # separación entre posiciones
        W = max(5.0, (vw - mitad * hueco_p) / (mitad * 4))
        H = max(40.0, vh / 2 - 34)
        fuente = QtGui.QFont('Segoe UI', 7)
        negrita = QtGui.QFont('Segoe UI', 8 if W >= 9 else 7, QtGui.QFont.Bold)
        for fila_i, fila_ps in enumerate(filas_ps):
          y0 = fila_i * (H + 34)
          for j, p in enumerate(fila_ps):
            d = pos.get('L%02d|%d' % (l, p))
            filas = {f[0]: f for f in d['n']} if d else {}
            x0 = j * (4 * W + hueco_p)
            for n in range(1, 5):
                x, y, H_ = x0 + (n - 1) * W, y0, H
                existe = n in res['niveles'][(l, p)]
                if not existe:
                    continue
                e = estado_nivel(filas.get(n), d is None or d['e'] == 'fuera')
                rect = s.addRect(x, y, W, H_, QtGui.QPen(QtGui.QColor('white'), 1), QtGui.QBrush(QtGui.QColor(COLOR_NIVEL[e][0])))
                for k in (1, 2, 3):                  # rayas finas: las 4 cajas de alto de la columna
                    s.addLine(x + 1, y + H_ * k / 4, x + W - 1, y + H_ * k / 4, QtGui.QPen(QtGui.QColor(255, 255, 255, 90), 1))
                f = filas.get(n)
                txt = '<b>L%02d P%02d C%d</b> (columna; 4 cajas de alto)<br>%s' % (l, p, n, COLOR_NIVEL[e][1])
                if f:
                    txt += '<br>Litros: %s hoy → %s después' % (esp(f[5]), esp(f[6]))
                    if f[1]:
                        txt += '<br>Paso %d de la lista: %d cajas salen' % (f[1], f[2])
                    if f[3]:
                        txt += '<br>Entran %d cajas' % f[3]
                    if f[4]:
                        txt += '<br>%d cajas vacías que retirar' % f[4]
                rect.setToolTip(txt)
            t = s.addSimpleText('P%02d' % p, negrita)
            t.setPos(x0 + (4 * W - t.boundingRect().width()) / 2, y0 + H + 3)
            if W >= 12:
                for n in range(1, 5):
                    c = s.addSimpleText(str(n), fuente)
                    c.setBrush(QtGui.QColor('#8b95a3'))
                    c.setPos(x0 + (n - 1) * W + (W - c.boundingRect().width()) / 2, y0 + H + 17)
        self.setSceneRect(s.itemsBoundingRect().adjusted(-10, -10, 10, 10))
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        QtCore.QTimer.singleShot(0, self.pintar)


def hoja_lineal(padre, res, l):
    """Excel para imprimir con las tareas de un lineal: 1) cajas vacías que retirar, 2) cajas que mover."""
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    nom = 'L%02d' % l
    m = res['mapa']
    ceros = [c for c in m['ceros'] if c[0].startswith(nom + ' ')]
    sale = [p for p in m['pasos'] if p[1].startswith(nom + ' ')]
    entra = [p for p in m['pasos'] if p[8].startswith(nom + ' ') and not p[1].startswith(nom + ' ')]
    sello = datetime.datetime.now().strftime('%Y%m%d_%H%M')
    defecto = str(RAIZ / ('hoja-trabajo_%s_%s.xlsx' % (nom, sello)))
    ruta, _ = QtWidgets.QFileDialog.getSaveFileName(padre, 'Hoja de trabajo de %s' % nom, defecto, 'Excel (*.xlsx)')
    if not ruta:
        return
    if Path(ruta).exists():
        QtWidgets.QMessageBox.warning(padre, TITULO, 'Ya existe %s.\nNo se sobrescribe: elige otro nombre.' % ruta)
        return
    wb = openpyxl.Workbook()
    fina = Side(style='thin', color='BBBBBB')
    borde = Border(left=fina, right=fina, top=fina, bottom=fina)

    def hoja(ws, titulo, cols, filas, anchos):
        ws.append(['%s · %s' % (nom, titulo)])
        ws['A1'].font = Font(size=16, bold=True)
        ws.append(['Datos de Odoo del %s · propuesta del programa de redistribución · marcar «Hecho» al acabar'
                   % res['resumen']['fecha_copia']])
        ws['A2'].font = Font(size=9, color='666666')
        ws.append([])
        ws.append(cols + ['Hecho'])
        for c in ws[4]:
            c.font = Font(bold=True, color='FFFFFF')
            c.fill = PatternFill('solid', fgColor='2F5FD0')
            c.border = borde
        for f in filas:
            ws.append(list(f) + ['☐'])
            for c in ws[ws.max_row]:
                c.border = borde
                c.alignment = Alignment(vertical='center', wrap_text=True)
        for i, a in enumerate(anchos + [8], 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = a
        ws.print_options.gridLines = False
        ws.page_setup.orientation = 'landscape'
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.print_title_rows = '4:4'
        if not filas:
            ws.append(['Nada que hacer en este lineal.'])

    ws = wb.active
    ws.title = '1 Retirar vacías'
    hoja(ws, '1 · Cajas vacías que retirar', ['Hueco', 'Caja', 'Cajas con stock que se quedan', 'Nota'],
         [[c[0], c[2], c[5], 'NEGATIVO en Odoo: no retirar, avisar' if c[3] else
           'Si tiene prendas, no se retira: avisar'] for c in ceros], [14, 20, 16, 40])
    hoja(wb.create_sheet('2 Sacar cajas'), '2 · Cajas que salen de este lineal (por paso)',
         ['Paso', 'Desde', 'Caja', 'Modelo-color', 'Tallas (uds)', 'Uds', 'Llevar a'],
         [[p[0], p[1], p[2], p[3], p[4], p[5], p[8]] for p in sale], [7, 14, 20, 22, 26, 7, 14])
    hoja(wb.create_sheet('3 Entran cajas'), '3 · Cajas que llegan a este lineal',
         ['Paso', 'Viene de', 'Caja', 'Modelo-color', 'Tallas (uds)', 'Uds', 'Dejar en'],
         [[p[0], p[1], p[2], p[3], p[4], p[5], p[8]] for p in entra], [7, 14, 20, 22, 26, 7, 14])
    wb.save(ruta)
    if QtWidgets.QMessageBox.question(padre, TITULO, 'Hoja guardada en\n%s\n\n¿Abrirla ahora?' % ruta) == \
            QtWidgets.QMessageBox.Yes:
        os.startfile(ruta)


class VistaLineal(QtWidgets.QWidget):
    """Un lineal: su alzado con colores y lo que hay que hacer en él, con la hoja para imprimir."""

    def __init__(self):
        super().__init__()
        self.res = None
        self.l = None
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        izq = QtWidgets.QVBoxLayout()
        izq.addWidget(etiqueta('<b style="font-size:12pt">Lineales</b><br><span style="color:#586374">en orden de '
                               'trabajo (más huecos liberados primero)</span>'))
        self.busca = QtWidgets.QLineEdit()
        self.busca.setPlaceholderText('Buscar: 67, L67…')
        self.busca.textChanged.connect(self._filtrar)
        izq.addWidget(self.busca)
        self.lista = QtWidgets.QListWidget()
        self.lista.setObjectName('lineales')
        self.lista.setFixedWidth(250)
        self.lista.currentItemChanged.connect(lambda it, _: it and self.mostrar(it.data(Qt.UserRole)))
        izq.addWidget(self.lista, 1)
        lay.addLayout(izq)
        der = QtWidgets.QVBoxLayout()
        arriba = QtWidgets.QHBoxLayout()
        self.titulo = etiqueta('', 20)
        arriba.addWidget(self.titulo, 1)
        b_plano = QtWidgets.QPushButton('Ver en el plano')
        b_plano.clicked.connect(lambda: self.ver_plano(self.l))
        self.b_hoja = QtWidgets.QPushButton('Imprimir hoja de trabajo (Excel)')
        self.b_hoja.setObjectName('principal')
        self.b_hoja.clicked.connect(lambda: hoja_lineal(self, self.res, self.l))
        arriba.addWidget(b_plano)
        arriba.addWidget(self.b_hoja)
        der.addLayout(arriba)
        self.cifras = etiqueta('', 11)
        der.addWidget(self.cifras)
        ley = QtWidgets.QHBoxLayout()
        for k, (col, txt) in COLOR_NIVEL.items():
            ley.addWidget(etiqueta('<span style="background:%s">&nbsp;&nbsp;&nbsp;&nbsp;</span> %s' % (col, txt), 9, ajustar=False))
        ley.addStretch(1)
        der.addLayout(ley)
        self.alzado = Alzado()
        der.addWidget(self.alzado, 2)
        self.pest = QtWidgets.QTabWidget()
        self.t_ceros = PanelTabla('retirar', ['Hueco', 'Caja', 'Cajas con stock que se quedan', 'Aviso'], numericas=(2,))
        self.t_sale = PanelTabla('sacar', ['Paso', 'Desde', 'Caja', 'Modelo-color', 'Tallas (uds)', 'Uds', 'Llevar a'],
                                 numericas=(0, 5))
        self.t_entra = PanelTabla('entran', ['Paso', 'Viene de', 'Caja', 'Modelo-color', 'Tallas (uds)', 'Uds', 'Dejar en'],
                                  numericas=(0, 5))
        self.t_alt = PanelTabla('tallas-por-altura', COLS_ALTURAS, numericas=(3,) + tuple(range(7, 13)), ayuda=AYUDA_ALTURAS)
        self.pest.addTab(self.t_ceros, '1 · Retirar vacías')
        self.pest.addTab(self.t_sale, '2 · Sacar cajas')
        self.pest.addTab(self.t_entra, '3 · Entran cajas')
        self.pest.addTab(self.t_alt, '4 · Tallas por altura')
        der.addWidget(self.pest, 3)
        lay.addLayout(der, 1)
        self.ver_plano = lambda l: None

    def poner(self, res):
        self.res = res
        self.lista.clear()
        for f in res['orden']:
            it = QtWidgets.QListWidgetItem('%s   ·   %s huecos libres\n%s vacías · %s a mover'
                                           % (f['l'], esp(f['liberados']), esp(f['cajas_a_0']), esp(f['cajas_a_mover'])))
            it.setData(Qt.UserRole, int(f['l'][1:]))
            self.lista.addItem(it)
        if self.lista.count():
            self.lista.setCurrentRow(0)

    def _filtrar(self, t):
        t = t.strip().upper().lstrip('L')
        for i in range(self.lista.count()):
            it = self.lista.item(i)
            it.setHidden(bool(t) and not str(it.data(Qt.UserRole)).startswith(t))

    def elegir(self, l):
        for i in range(self.lista.count()):
            if self.lista.item(i).data(Qt.UserRole) == l:
                self.busca.clear()
                self.lista.setCurrentRow(i)
                return
        self.mostrar(l)

    def mostrar(self, l):
        if self.res is None:
            return
        self.l = l
        nom = 'L%02d' % l
        m = self.res['mapa']
        f = next((x for x in m['lineales'] if x['l'] == nom), None)
        self.titulo.setText('<b>%s</b>' % nom)
        if f:
            self.cifras.setText(
                'Huecos en uso: <b>%s</b> hoy → <b>%s</b> después  ·  '
                'huecos que se liberan: <b>%s</b>  ·  posiciones libres enteras: <b>%s</b>  ·  KO: <b>%s → %s</b>%s'
                % (esp(f['huecos_hoy']), esp(f['huecos_despues']), esp(f['liberados']), esp(f['libres_enteras']),
                   esp(self.res['ko_lineal'].get(l, [0, 0])[0]), esp(self.res['ko_lineal'].get(l, [0, 0])[1]),
                   '<br><span style="color:#2fa37f"><b>Podría quedar vacío entero</b> (estimación por volumen)</span>'
                   if f['vaciar_entero'] else ''))
        else:
            self.cifras.setText('Este lineal no es de la zona 0.')
        self.alzado.pintar(self.res, l)
        self.t_ceros.poner([[c[0], c[2], c[5], 'NEGATIVO en Odoo: no retirar' if c[3] else '']
                            for c in m['ceros'] if c[0].startswith(nom + ' ')])
        self.t_sale.poner([[p[0], p[1], p[2], p[3], p[4], p[5], p[8]] for p in m['pasos'] if p[1].startswith(nom + ' ')])
        self.t_entra.poner([[p[0], p[1], p[2], p[3], p[4], p[5], p[8]] for p in m['pasos']
                            if p[8].startswith(nom + ' ') and not p[1].startswith(nom + ' ')])
        self.pest.setTabText(0, '1 · Retirar vacías (%d)' % self.t_ceros.modelo.rowCount())
        self.pest.setTabText(1, '2 · Sacar cajas (%d)' % self.t_sale.modelo.rowCount())
        self.pest.setTabText(2, '3 · Entran cajas (%d)' % self.t_entra.modelo.rowCount())
        self.t_alt.poner(filas_alturas(self.res, self.res['mcs_lineal'].get(l, set())))
        self.pest.setTabText(3, '4 · Tallas por altura (%d modelos)' % self.t_alt.modelo.rowCount())


def hueco_de(txt):
    """'L67 P16 C1' -> (67, 16, 1)."""
    try:
        l, p, n = txt.split()
        return int(l[1:]), int(p[1:]), int(n[1:])
    except (ValueError, AttributeError):
        return None


class PantallaPlano(QtWidgets.QWidget):
    """El plano para explicar el trabajo: botones por paso, leyenda y, al hacer clic en una posición, qué hay que
    hacer en cada nivel con flechas en el plano."""
    abrir_lineal = QtCore.Signal(int)

    def __init__(self):
        super().__init__()
        self.res = None
        self.sel = None
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        barra = QtWidgets.QHBoxLayout()
        self.grupo = QtWidgets.QButtonGroup(self)
        for i, (modo, (titulo, _, _)) in enumerate(MODOS_PLANO.items()):
            b = QtWidgets.QPushButton(titulo)
            b.setCheckable(True)
            b.setProperty('modo', modo)
            b.setStyleSheet('QPushButton:checked { background:#2f5fd0; color:white; border:0; font-weight:600; }')
            self.grupo.addButton(b, i)
            barra.addWidget(b)
            if modo == 'final':
                b.setChecked(True)
        self.grupo.buttonClicked.connect(lambda b: self.poner_modo(b.property('modo')))
        barra.addStretch(1)
        barra.addWidget(etiqueta('Rueda: zoom · arrastrar: mover · <b>clic</b>: qué hacer · <b>doble clic</b>: lineal',
                                 9, '#586374', False))
        lay.addLayout(barra)
        self.explica = etiqueta('', 10.5, '#18202b')
        lay.addWidget(self.explica)
        self.leyenda = QtWidgets.QHBoxLayout()
        lay.addLayout(self.leyenda)
        medio = QtWidgets.QHBoxLayout()
        self.plano = Plano()
        self.plano.posicion_elegida.connect(self.elegir)
        self.plano.lineal_elegido.connect(lambda nom: self.abrir_lineal.emit(int(nom[1:])))
        medio.addWidget(self.plano, 1)
        panel = QtWidgets.QFrame()
        panel.setObjectName('tarjeta')
        panel.setFixedWidth(380)
        pl = QtWidgets.QVBoxLayout(panel)
        self.texto = QtWidgets.QTextBrowser()
        self.texto.setOpenLinks(False)
        self.texto.setStyleSheet('border:0')
        self.texto.anchorClicked.connect(self._enlace)
        pl.addWidget(self.texto, 1)
        self.b_lin = QtWidgets.QPushButton('Abrir el lineal y su hoja de trabajo')
        self.b_lin.setObjectName('principal')
        self.b_lin.clicked.connect(lambda: self.sel and self.abrir_lineal.emit(self.sel[0]))
        pl.addWidget(self.b_lin)
        b_todo = QtWidgets.QPushButton('Ver la nave entera')
        b_todo.clicked.connect(lambda: (self.plano.quitar_marcas(), self.plano.encajar()))
        pl.addWidget(b_todo)
        medio.addWidget(panel)
        lay.addLayout(medio, 1)
        self.poner_modo('final')
        self.texto.setHtml('<h3>Haz clic en una posición del plano</h3><p style="color:#586374">Aquí sale qué hay que '
                           'hacer en cada nivel: qué cajas vacías retirar, qué cajas sacar y adónde llevarlas, y qué '
                           'cajas llegan. En el plano se dibujan las flechas.</p>')

    def poner(self, res):
        self.res = res
        m = res['mapa']
        self.ceros = {}
        for c in m['ceros']:
            h = hueco_de(c[0])
            if h:
                self.ceros.setdefault(h, []).append(c)
        self.sale, self.entra = {}, {}
        for p in m['pasos']:
            a, b = hueco_de(p[1]), hueco_de(p[8])
            if a and b:
                self.sale.setdefault(a[:2], []).append((a, b, p))
                self.entra.setdefault(b[:2], []).append((a, b, p))
        self.plano.pintar(res)

    def poner_modo(self, modo):
        titulo, texto, ley = MODOS_PLANO[modo]
        for b in self.grupo.buttons():
            b.setChecked(b.property('modo') == modo)
        self.explica.setText('<b>%s.</b> %s' % (titulo, texto))
        while self.leyenda.count():
            w = self.leyenda.takeAt(0).widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        for col, txt in ley:
            self.leyenda.addWidget(etiqueta('<span style="background:%s">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span> %s' % (col, txt),
                                            ajustar=False))
        self.leyenda.addStretch(1)
        self.plano.colorear(modo)

    def movimientos_lineal(self, l):
        movs = []
        for (ll, p), xs in list(self.sale.items()) + list(self.entra.items()):
            if ll == l:
                for a, b, _ in xs:
                    movs.append((a[:2], b[:2], a[0] == l))
        return movs

    def ir_a_lineal(self, l):
        self.sel = None
        self.plano.ir_a_lineal('L%02d' % l, self.movimientos_lineal(l))
        n_sale = sum(len(v) for (ll, _), v in self.sale.items() if ll == l)
        n_entra = sum(len(v) for (ll, _), v in self.entra.items() if ll == l)
        self.texto.setHtml('<h2>L%02d</h2><p>Flechas <span style="color:#0f7b5a"><b>verdes</b></span>: cajas que salen '
                           '(%d). <span style="color:#1d4fc4"><b>Azules</b></span>: cajas que llegan de otros lineales (%d).'
                           '</p><p style="color:#586374">Clic en una posición para ver el detalle.</p>' % (l, n_sale, n_entra))

    def elegir(self, l, p):
        if not self.res:
            return
        self.sel = (l, p)
        d = self.res['mapa']['posiciones'].get('L%02d|%d' % (l, p))
        estado = NOMBRES[d['e']] if d else NOMBRES['fuera']
        html = ['<h2 style="margin:0">L%02d P%02d</h2><p style="color:#586374;margin-top:2px">%s</p>' % (l, p, estado)]
        movs = []
        hay = False
        for n in sorted(self.res['niveles'].get((l, p), ())):
            h = (l, p, n)
            partes = []
            cs = self.ceros.get(h, [])
            if cs:
                partes.append('<p style="margin:4px 0"><span style="background:#e0a526;color:white;padding:1px 5px">'
                              '&nbsp;RETIRAR VACÍAS&nbsp;</span> %d caja%s: %s<br><span style="color:#586374">Comprobar '
                              'que están vacías. Si tiene prendas, no se retira: avisar.</span></p>'
                              % (len(cs), '' if len(cs) == 1 else 's', ', '.join('<b>%s</b>' % c[2] for c in cs)))
            for a, b, x in self.sale.get((l, p), []):
                if a == h:
                    partes.append('<p style="margin:4px 0"><span style="background:#0f7b5a;color:white">&nbsp;SACAR&nbsp;'
                                  '</span> <b>%s</b> · %s · %s uds<br>→ llevar a <b>%s</b> <span style="color:#586374">'
                                  '(paso %s)</span></p>' % (x[2], x[3], esp(x[5]), x[8], x[0]))
                    movs.append((a[:2], b[:2], True))
            for a, b, x in self.entra.get((l, p), []):
                if b == h:
                    partes.append('<p style="margin:4px 0"><span style="background:#1d4fc4;color:white">&nbsp;LLEGA&nbsp;'
                                  '</span> <b>%s</b> · %s · %s uds<br>← viene de <b>%s</b> <span style="color:#586374">'
                                  '(paso %s)</span></p>' % (x[2], x[3], esp(x[5]), x[1], x[0]))
                    movs.append((a[:2], b[:2], False))
            if partes:
                hay = True
            html.append('<h3 style="margin:10px 0 2px">Nivel C%d</h3>%s' % (n, ''.join(partes) or
                                                                         '<p style="color:#586374;margin:2px 0">Nada que hacer.</p>'))
        if not hay:
            html.append('<p><b>En esta posición no hay nada que hacer.</b></p>')
        self.texto.setHtml(''.join(html))
        it = self.plano.celdas.get((l, p))
        self.plano.ensenar_movimientos(movs, it.rect() if it else None, acercar=False)

    def _enlace(self, url):
        pass


# ============================================================================================== ventana
class Ventana(QtWidgets.QMainWindow):
    SECCIONES = ['Inicio', 'Por lineal', 'Plano de la nave', 'Listas completas', 'Fuentes de datos']

    def __init__(self):
        super().__init__()
        self.setWindowTitle(TITULO)
        self.resize(1440, 900)
        self.res = None
        fondo = QtWidgets.QWidget()
        fondo.setObjectName('fondo')
        h = QtWidgets.QHBoxLayout(fondo)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        lado = QtWidgets.QVBoxLayout()
        lado.setContentsMargins(0, 0, 0, 0)
        marca = etiqueta('<div style="color:white;font-size:13pt;font-weight:700;padding:16px">NAU-2<br>'
                         '<span style="font-size:9pt;font-weight:400;color:#9aa3af">Redistribución KOROSHI</span></div>')
        marca.setStyleSheet('background:#18202b;padding:14px 18px')
        lado.addWidget(marca)
        self.menu = QtWidgets.QListWidget()
        self.menu.setObjectName('menu')
        self.menu.setFixedWidth(210)
        self.menu.addItems(self.SECCIONES)
        lado.addWidget(self.menu, 1)
        self.b_calc = QtWidgets.QPushButton('↻  Recalcular')
        self.b_calc.setStyleSheet('background:#263142;color:white;border:0;border-radius:0;padding:12px')
        self.b_calc.clicked.connect(self.recalcular)
        lado.addWidget(self.b_calc)
        h.addLayout(lado)
        self.pila = QtWidgets.QStackedWidget()
        h.addWidget(self.pila, 1)
        self.setCentralWidget(fondo)
        self.estado = QtWidgets.QLabel()
        self.statusBar().addWidget(self.estado, 1)

        # 0 Inicio
        self.inicio = Inicio()
        self.inicio.abrir_lineal.connect(lambda nom: self.ver_lineal(int(nom[1:])))
        self.inicio.abrir_lista.connect(self.ver_lista)
        self.pila.addWidget(self.inicio)
        # 1 Por lineal
        self.vlin = VistaLineal()
        self.vlin.ver_plano = self.ver_en_plano
        self.pila.addWidget(self.vlin)
        # 2 Plano
        self.pplano = PantallaPlano()
        self.pplano.abrir_lineal.connect(self.ver_lineal)
        self.plano = self.pplano.plano
        self.pila.addWidget(self.pplano)
        # 3 Listas completas
        self.listas = QtWidgets.QTabWidget()
        self.t_ceros = PanelTabla(
            'cajas-vacias_retirar', ['Hueco', 'Zona del hueco', 'Caja', 'Aviso', 'Cajas vacías en el hueco',
                                     'Cajas con stock en el hueco', 'En la compactación', 'Metros a expedición'],
            numericas=(4, 5, 7),
            ayuda='Cajas que en Odoo están a 0. Comprobar en la nave que están vacías y retirarlas. Si una tiene '
                  'prendas, no se retira: es una diferencia de stock. Doble clic: abrir el lineal.')
        self.t_ceros.doble.connect(lambda f: self.ver_lineal(int(f[0][1:4])))
        self.t_pasos = PanelTabla(
            'cajas-a-mover', ['Paso', 'Desde', 'Caja', 'Modelo-color', 'Tallas (uds)', 'Uds', 'Clase', 'Resto de talla',
                              'Hasta', 'Metros (desde)', 'Metros (hasta)'],
            numericas=(0, 5, 9, 10),
            ayuda='Primero los huecos que se vacían moviendo menos cajas. Las cajas de un mismo modelo-color van juntas; '
                  'nunca dos colores del mismo modelo en un hueco; lo de clase A, lo más cerca. Doble clic: abrir el lineal.')
        self.t_pasos.doble.connect(lambda f: self.ver_lineal(int(f[1][1:4])))
        verde = lambda f, c: '#d7f0e6' if f[1] == 'sí' else None
        self.t_lin = PanelTabla(
            'lineales', ['Lineal', 'Podría quedar vacío (estimación)', 'Huecos en uso hoy',
                         'Huecos en uso después', 'Posiciones libres enteras', 'Huecos que se liberan', 'Cajas vacías',
                         'Cajas a mover', 'Uds a mover', 'KO hoy', 'KO después (mixta)'],
            numericas=range(2, 11), color=verde,
            ayuda='«Podría quedar vacío» es una estimación por volumen: lo suyo cabe en el sitio libre de los lineales que '
                  'se quedan (hasta el 90 %). No mira distancias ni reglas de mezcla. Doble clic: abrir el lineal.')
        self.t_lin.doble.connect(lambda f: self.ver_lineal(int(f[0][1:])))
        self.listas.addTab(self.t_ceros, 'Cajas vacías (retirar)')
        self.listas.addTab(self.t_pasos, 'Cajas a mover')
        self.listas.addTab(self.t_lin, 'Lineales')
        self.t_alt = PanelTabla('tallas-por-altura', COLS_ALTURAS, numericas=(3,) + tuple(range(7, 13)), ayuda=AYUDA_ALTURAS)
        self.listas.addTab(self.t_alt, 'Tallas por altura')
        cont = QtWidgets.QWidget()
        QtWidgets.QVBoxLayout(cont).addWidget(self.listas)
        self.pila.addWidget(cont)
        # 4 Fuentes
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)
        lay.setContentsMargins(24, 18, 24, 18)
        lay.addWidget(etiqueta('<span style="font-size:18pt;font-weight:700">De dónde salen los datos</span><br>'
                               '<span style="color:#586374">La última versión de cada matriz de KOROSHI en '
                               '<code>bin/versiones</code> y la última copia de Odoo. El programa solo las lee: '
                               'si sacáis una versión nueva, pulsad «Recalcular».</span>'))
        self.t_fuentes = PanelTabla('fuentes', ['Fuente', 'Fichero', 'Versión', 'Fecha', 'Versiones anteriores',
                                                'Para qué se usa', 'Ruta'],
                                    numericas=(2, 4), ayuda='Doble clic en una fila: abrir el fichero.')
        self.t_fuentes.doble.connect(lambda f: f[-1] and os.startfile(str(f[-1])))
        lay.addWidget(self.t_fuentes, 1)
        b1 = QtWidgets.QPushButton('Abrir la carpeta de matrices')
        b1.clicked.connect(lambda: os.startfile(str(fuentes.CARPETA_MATRICES)))
        lay.addWidget(b1, 0, Qt.AlignLeft)
        self.pila.addWidget(w)

        self.menu.currentRowChanged.connect(self.pila.setCurrentIndex)
        self.menu.setCurrentRow(0)
        self.pintar_fuentes()
        QtCore.QTimer.singleShot(50, self.recalcular)

    def pintar_fuentes(self, res=None):
        filas = []
        for m in fuentes.matrices():
            filas.append(['Matriz %d · %s' % (m.numero, m.nombre), m.ruta.name, m.version, m.fecha, m.anteriores, m.uso, m.ruta])
        try:
            copia = copias_completas(configuracion.CARPETA / 'copias')[-1]
            fecha = res['resumen']['fecha_copia'] if res else ''
            filas.append(['Copia de Odoo (solo lectura)', copia.name, '', fecha, '', 'Stock, contenedores, huecos y salidas', copia])
        except IndexError:
            filas.append(['Copia de Odoo', 'NO HAY NINGUNA', '', '', '', 'Bajarla con «python programa.py descargar» (con el sí de Isaac)', ''])
        self.t_fuentes.poner(filas)

    def recalcular(self):
        self.b_calc.setEnabled(False)
        self.b_calc.setText('Calculando…')
        self.hilo = QtCore.QThread(self)
        self.trabajo = Trabajo()
        self.trabajo.moveToThread(self.hilo)
        self.hilo.started.connect(self.trabajo.ejecutar)
        self.trabajo.aviso.connect(self.estado.setText)
        self.trabajo.hecho.connect(self.listo)
        self.trabajo.fallo.connect(self.fallo)
        self.trabajo.hecho.connect(self.hilo.quit)
        self.trabajo.fallo.connect(self.hilo.quit)
        self.hilo.start()

    def fallo(self, texto):
        self.b_calc.setEnabled(True)
        self.b_calc.setText('↻  Recalcular')
        self.estado.setText('Error')
        QtWidgets.QMessageBox.critical(self, TITULO, texto)

    def listo(self, res):
        self.res = res
        self.b_calc.setEnabled(True)
        self.b_calc.setText('↻  Recalcular')
        m, r = res['mapa'], res['resumen']
        self.pintar_fuentes(res)
        self.inicio.poner(res)
        self.vlin.poner(res)
        self.t_lin.poner([[f['l'], 'sí' if f['vaciar_entero'] else '', f['huecos_hoy'],
                           f['huecos_despues'], f['libres_enteras'], f['liberados'], f['cajas_a_0'],
                           f['cajas_a_mover'], f['uds_a_mover']] + res['ko_lineal'].get(int(f['l'][1:]), [0, 0])
                          for f in res['orden']])
        self.t_ceros.poner(m['ceros'])
        self.t_pasos.poner(m['pasos'])
        self.t_alt.poner(filas_alturas(res))
        self.pplano.poner(res)
        self.estado.setText('Listo · datos de Odoo del %s · %s' % (r['fecha_copia'], res['master'].ruta.name))

    def ver_lineal(self, l):
        self.menu.setCurrentRow(1)
        self.vlin.elegir(l)

    def ver_lista(self, i):
        self.menu.setCurrentRow(3)
        self.listas.setCurrentIndex(i)

    def ver_en_plano(self, l):
        self.menu.setCurrentRow(2)
        self.pplano.poner_modo('paso2')
        QtCore.QTimer.singleShot(30, lambda: self.pplano.ir_a_lineal(l))


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(TITULO)
    app.setStyle('Fusion')
    app.setStyleSheet(ESTILO)
    v = Ventana()
    v.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()


