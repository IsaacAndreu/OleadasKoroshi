# -*- coding: utf-8 -*-
# =============================================================================
# Montar y puntuar un reparto para las k primeras OUT. Copia literal de la v12f (accion 1883):
# evaluar() lineas 396-458, cajas_de/cerrada/litros 463-518, repartir_personas 521-533,
# montar_una 536-649 y montar 703-726.
# La clase Calculo guarda lo que en la accion eran variables globales (coste por pasillo, lineas de cada
# OUT, segundos de cada linea...). Las rellena v12f.preparar().
# =============================================================================
from . import volumen
from .cierre import cerrar_cadena
from .particion import particion, repartir_zx


def numero_k(nombre):
    if nombre[:1] != 'K':
        return 9999
    num = ''
    for ch in nombre[1:]:
        if ch.isdigit():
            num += ch
        else:
            break
    return num and int(num) or 9999


class Calculo(object):

    def __init__(self, p):
        self.p = p
        self.medidas = volumen.Medidas(p['LITROS_CAJA'], p['CIERRE_MIN'], p['LITROS_TIPO'], p['LITROS_DEFECTO'])
        self.ZONAS_MUELLE = p['ZONAS_MUELLE']
        self.capacidad = 0.0
        self.seg_lect = 0.0
        self.seg_lin = 0.0
        self.orden = []         # pids en orden de prioridad (tienda)
        self.coste_out = {}     # pid -> {pasillo: segundos}
        self.zx_out = {}        # pid -> {hueco: segundos}
        self.uds_out = {}
        self.info_ml = {}       # ml -> (pasillo o -1, lineal, clave_hueco)
        self.qty_ml = {}
        self.seg_ml = {}
        self.ml_rec = {}        # ml -> dict de la linea
        self.mls_out = {}
        self.out_rec = {}       # pid -> dict de la OUT
        self.lit_cache = {}

    # ---------------- volumen ----------------
    def cajas_de(self, litros):
        return volumen.cajas_de(litros, self.medidas)

    def cerrada(self, litros):
        return volumen.cerrada(litros, self.medidas)

    def lit_ml(self, ml_id):
        if ml_id not in self.lit_cache:
            ml = self.ml_rec[ml_id]
            self.lit_cache[ml_id] = volumen.litros_ud(ml['volume'], ml['default_code'], self.medidas) * \
                self.qty_ml[ml_id]
        return self.lit_cache[ml_id]

    def litros_de(self, ml_ids):
        t = 0.0
        for x in ml_ids:
            t += self.lit_ml(x)
        return t

    def segundos_de(self, ml_ids):
        t = 0.0
        for x in ml_ids:
            t += self.seg_ml[x]
        return t

    def tiempo_grupo(self, ml_ids):
        # lo que tarda una persona en coger estas lineas para una OUT: lecturas (hueco + articulo) y lineales
        lect = {}
        lins = {}
        for x in ml_ids:
            ml = self.ml_rec[x]
            lect[(ml['location_id'], ml['product_id'])] = 1
            if self.info_ml[x][1]:
                lins[self.info_ml[x][1]] = 1
        return len(lect) * self.seg_lect + len(lins) * self.seg_lin

    # ---------------- corte de zonas ----------------
    def evaluar(self, k, wm):
        p = self.p
        ZONAS = p['ZONAS']
        ZONAS_MUELLE = self.ZONAS_MUELLE
        MUELLE_FIJO = p['MUELLE_FIJO']
        peso = {}
        zx = {}
        for pid in self.orden[:k]:
            for pa in self.coste_out[pid]:
                peso[pa] = peso.get(pa, 0.0) + self.coste_out[pid][pa] * wm.get(pa, 1.0)
            for h in self.zx_out[pid]:
                zx[h] = zx.get(h, 0.0) + self.zx_out[pid][h]
        pas = sorted(peso.keys())
        lista = []
        for pa in pas:
            lista.append(peso[pa])
        tiempos, tramos = particion(lista, ZONAS - ZONAS_MUELLE)
        lista_zx = []
        for h in sorted(zx.keys()):
            lista_zx.append((h, zx[h]))
        if ZONAS_MUELLE > 0 and not MUELLE_FIJO:   # v12f: con MUELLE_FIJO las zonas de muelle van por ubicacion
            pesos_zx = []
            for c in lista_zx:
                pesos_zx.append(c[1])
            t_zx, tr_zx = particion(pesos_zx, ZONAS_MUELLE)
            dur = 0.0
            for t in tiempos:
                if t > dur:
                    dur = t
            trozos = []
            for j in range(len(tr_zx)):
                claves = []
                for idx in range(tr_zx[j][0], tr_zx[j][1]):
                    claves.append(lista_zx[idx][0])
                trozos.append([-1, claves, t_zx[j]])
                if t_zx[j] > dur:
                    dur = t_zx[j]
            return dur, pas, tiempos, tramos, trozos
        if MUELLE_FIJO:
            # v12e: cada zona fija del muelle entera a la persona de lineal que antes acaba
            grupos_m = []
            for suf, txt in MUELLE_FIJO:
                grupos_m.append([suf, txt, [], 0.0])
            for c in lista_zx:
                g = grupos_m[-1]
                for gm in grupos_m:
                    if gm[1] and gm[1] in c[0]:
                        g = gm
                        break
                g[2].append(c[0])
                g[3] += c[1]
            fin_p = list(tiempos)
            trozos = []
            for g in sorted(grupos_m, key=lambda x: -x[3]):
                if not g[2]:
                    continue
                z = -1
                if fin_p and not p['MUELLE_EQUIPO_PROPIO']:
                    z = fin_p.index(min(fin_p))
                    fin_p[z] += g[3]
                trozos.append([z, g[2], g[3], g[0]])
            trozos.sort(key=lambda x: x[3])
            dur = fin_p and max(fin_p) or sum([t[2] for t in trozos])
            return dur, pas, tiempos, tramos, trozos
        dur, trozos = repartir_zx(tiempos, lista_zx, self.capacidad)
        return dur, pas, tiempos, tramos, trozos

    def repartir_personas(self, seg_z, zonas):
        # v12f: todas las zonas empiezan a la vez con su equipo fijo. Minimo 1 persona por zona; cada persona que
        # queda va a la zona que mas tardaria. Asi todas acaban lo mas a la vez posible.
        pers = {}
        for zn in zonas:
            pers[zn] = 1
        for i in range(self.p['PERSONAS'] - len(zonas)):
            peor = zonas[0]
            for zn in zonas:
                if seg_z[zn] / pers[zn] > seg_z[peor] / pers[peor]:
                    peor = zn
            pers[peor] += 1
        return pers

    def montar_una(self, k, wm):
        p = self.p
        ZONA_OTRAS = p['ZONA_OTRAS']
        MUELLE_FIJO = p['MUELLE_FIJO']
        dur9, pasillos, tiempos, tramos, trozos_zx = self.evaluar(k, wm)
        pares = []
        for pid in self.orden[:k]:
            q = self.out_rec[pid]
            pares.append((numero_k(q['partner_name'] or ''), q['name'], pid))
        pares.sort()
        pids = []
        for par in pares:
            pids.append(par[2])
        zona_pas = {}
        orden_zonas = []
        obj_z = {}
        for z in range(len(tramos)):
            nombre_z = 'D%d' % (z + 1)
            orden_zonas.append(nombre_z)
            obj_z[nombre_z] = max(tiempos[z], 1.0)
            for idx in range(tramos[z][0], tramos[z][1]):
                zona_pas[pasillos[idx]] = nombre_z
        zona_hueco = {}
        hace_zx = {}
        for t in range(len(trozos_zx)):
            nombre_x = len(trozos_zx) > 1 and ('%s%d' % (ZONA_OTRAS, t + 1)) or ZONA_OTRAS
            if len(trozos_zx[t]) > 3:
                nombre_x = ZONA_OTRAS + trozos_zx[t][3]     # v12e: MU1, MU2 siempre con su numero
            orden_zonas.append(nombre_x)
            obj_z[nombre_x] = max(trozos_zx[t][2], 1.0)
            hace_zx[nombre_x] = trozos_zx[t][0] >= 0 and ('D%d' % (trozos_zx[t][0] + 1)) or ''
            for h in trozos_zx[t][1]:
                zona_hueco[h] = nombre_x
        pos_zona = {}
        for idx in range(len(orden_zonas)):
            pos_zona[orden_zonas[idx]] = idx
        zona_ml = {}
        for pid in pids:
            for x in self.mls_out[pid]:
                pa = self.info_ml[x][0]
                zona_ml[x] = pa < 0 and zona_hueco[self.info_ml[x][2]] or zona_pas[pa]
        carga = {}
        for zn in orden_zonas:
            carga[zn] = 0.0
        grupos = {}         # (pid, zona) -> [ml.id]
        zona_fin = {}       # ml.id -> zona que la coge
        fuera = 0.0
        for pid in pids:
            rec = []
            for x in self.mls_out[pid]:
                ml = self.ml_rec[x]
                rec.append((pos_zona[zona_ml[x]], self.info_ml[x][0], self.info_ml[x][1],
                            ml['location_complete_name'] or '', ml['default_code'] or '', x))
            rec.sort()
            trozos = []     # [zona, [ml.id]] en orden de recorrido
            for r in rec:
                zn = zona_ml[r[5]]
                if not trozos or trozos[-1][0] != zn:
                    trozos.append([zn, []])
                trozos[-1][1].append(r[5])
            cadenas = [[], []]
            cad_mu = {}
            for tz in trozos:
                if tz[0].startswith(ZONA_OTRAS):
                    if MUELLE_FIJO:
                        if tz[0] not in cad_mu:
                            cad_mu[tz[0]] = []
                            cadenas.append(cad_mu[tz[0]])
                        cad_mu[tz[0]].append(tz)
                    else:
                        cadenas[1].append(tz)
                else:
                    cadenas[0].append(tz)
            for cadena in cadenas:
                cerrar_cadena(cadena, carga, obj_z, self)
            for tz in trozos:
                if not tz[1]:
                    continue
                grupos[(pid, tz[0])] = tz[1]
                for x in tz[1]:
                    zona_fin[x] = tz[0]
                    if zona_ml[x] != tz[0]:
                        fuera += self.qty_ml[x]
        seg_z = {}
        for zn in orden_zonas:
            seg_z[zn] = 0.0
        for clave in grupos:
            seg_z[clave[1]] += self.tiempo_grupo(grupos[clave])
        pers = {}
        if MUELLE_FIJO and p['MUELLE_EQUIPO_PROPIO'] and orden_zonas:
            pers = self.repartir_personas(seg_z, orden_zonas)
            for zn in orden_zonas:
                seg_z[zn] = seg_z[zn] / pers[zn]     # v12f: tiempo de la zona con su equipo
        zx_de = {}
        for zn in hace_zx:
            if hace_zx[zn]:
                zx_de[hace_zx[zn]] = zx_de.get(hace_zx[zn], 0.0) + seg_z[zn]
        fin = 0.0
        for zn in orden_zonas:
            if zn.startswith(ZONA_OTRAS):
                if not hace_zx.get(zn) and seg_z[zn] > fin:
                    fin = seg_z[zn]
                continue
            if seg_z[zn] + zx_de.get(zn, 0.0) > fin:
                fin = seg_z[zn] + zx_de.get(zn, 0.0)
        return {'k': k, 'pids': pids, 'orden_zonas': orden_zonas, 'hace_zx': hace_zx, 'zx_de': zx_de,
                'zona_pas': zona_pas, 'zona_ml': zona_ml, 'zona_fin': zona_fin, 'grupos': grupos, 'seg_z': seg_z,
                'fin': fin, 'fuera': fuera, 'dur9': dur9, 'pers': pers}

    def montar(self, k):
        # v12: mover lineas entre zonas para cerrar cajas desequilibra las zonas. Se repite el corte de zonas dando mas
        # peso a los pasillos de las zonas que han quedado largas (ITER_EQUILIBRIO veces) y se queda el que acaba antes.
        ZONA_OTRAS = self.p['ZONA_OTRAS']
        wm = {}
        mejor = None
        for it in range(self.p['ITER_EQUILIBRIO']):
            r = self.montar_una(k, wm)
            if mejor is None or r['fin'] < mejor['fin']:
                mejor = r
            total = 0.0
            n_d = 0
            for zn in r['orden_zonas']:
                if not zn.startswith(ZONA_OTRAS):
                    total += r['seg_z'][zn]
                    n_d += 1
            if not n_d or total <= 0:
                break
            media = total / n_d
            nuevo = {}
            for pa in r['zona_pas']:
                zn = r['zona_pas'][pa]
                nuevo[pa] = wm.get(pa, 1.0) * ((r['seg_z'][zn] + 1.0) / media) ** 0.7
            wm = nuevo
        return mejor
