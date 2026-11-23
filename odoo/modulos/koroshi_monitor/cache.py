# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Monitor - cache compartida entre pantallas, con un candado POR CLAVE (v1.44.0, revision general 23/11, R22).
# Python puro: se prueba con tests/test_cache.py, sin Odoo.
#
# Hasta la 1.43 habia un solo candado para todo, y durante todo el calculo: mientras una pantalla calculaba Z-2311-,
# las que pedian Tiendas (u otra agrupacion) esperaban sin necesidad. Ahora:
#   - misma clave: un solo calculo a la vez; las demas pantallas esperan y se llevan ese resultado (como antes);
#   - otra clave: no espera a nadie.
# El candado general solo se coge un momento para mirar o guardar en el diccionario, nunca durante un calculo.
# =============================================================================
import threading
import time

MAX_EDAD = 600      # lo guardado hace mas de 10 min se borra al guardar algo nuevo


class CachePorClave(object):

    def __init__(self, segundos, max_edad=MAX_EDAD, reloj=time.time):
        self.segundos = segundos
        self.max_edad = max_edad
        self._reloj = reloj
        self._datos = {}            # clave -> (momento, resultado)
        self._candados = {}         # clave -> threading.Lock (uno por clave)
        self._general = threading.Lock()

    def _vigente(self, clave, segundos):
        g = self._datos.get(clave)
        if g and self._reloj() - g[0] < segundos:
            return True, g[1]
        return False, None

    def obtener(self, clave, calcular, segundos=None):
        """El resultado guardado de `clave` si tiene menos de `segundos`; si no, calcular() (uno a la vez por clave)
        y se guarda. Si calcular() falla, no se guarda nada y el error sale (la siguiente pantalla lo vuelve a probar)."""
        segundos = self.segundos if segundos is None else segundos
        with self._general:
            ok, res = self._vigente(clave, segundos)
            if ok:
                return res
            candado = self._candados.setdefault(clave, threading.Lock())
        with candado:
            with self._general:     # otra pantalla lo ha calculado mientras esta esperaba
                ok, res = self._vigente(clave, segundos)
                if ok:
                    return res
            res = calcular()
            with self._general:
                ahora = self._reloj()
                self._datos[clave] = (ahora, res)
                for k in [k for k, v in self._datos.items() if ahora - v[0] > self.max_edad]:
                    self._datos.pop(k, None)
                    c = self._candados.get(k)
                    if c is not None and not c.locked():
                        self._candados.pop(k, None)
        return res

    def claves(self):
        with self._general:
            return list(self._datos)
