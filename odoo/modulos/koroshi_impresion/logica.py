# -*- coding: utf-8 -*-
"""
KOROSHI Impresión - lógica sin Odoo (se prueba con tests/test_logica.py).

La cola: la PDA (u otra pantalla) apunta un trabajo para una impresora; el agente del PC donde está esa impresora
pregunta cada pocos segundos, se lleva los pendientes, los imprime y dice si ha ido bien.
Diseño: bin/versiones/diseno-imprimir-desde-pda_2026-11-25_v4.md.
"""
import datetime

PENDIENTE = 'pendiente'
IMPRIMIENDO = 'imprimiendo'
IMPRESO = 'impreso'
ERROR = 'error'

SEGUNDOS_CONECTADA = 60          # sin noticias del agente en 1 min = «no conectada»
MINUTOS_ATASCADO = 5             # «imprimiendo» más de 5 min = el PC se apagó a mitad: vuelve a pendiente
MAX_INTENTOS = 3                 # a los 3 intentos queda en error
MAX_POR_VUELTA = 5               # trabajos que se lleva el agente en cada pregunta
DIAS_GUARDAR = 30                # los impresos se borran a los 30 días
MAX_COPIAS = 20


def conectada(ultimo_contacto, ahora, segundos=SEGUNDOS_CONECTADA):
    """True si el agente ha preguntado hace menos de `segundos`."""
    if not ultimo_contacto:
        return False
    return (ahora - ultimo_contacto).total_seconds() < segundos


def que_hacer_atascado(inicio, intentos, ahora, minutos=MINUTOS_ATASCADO, max_intentos=MAX_INTENTOS):
    """Un trabajo en «imprimiendo»: None si aún no toca, PENDIENTE para volver a probar o ERROR si ya van muchos."""
    if inicio and (ahora - inicio) < datetime.timedelta(minutes=minutos):
        return None
    return ERROR if (intentos or 0) >= max_intentos else PENDIENTE


def ids_de_texto(texto):
    """'12, 13,14' -> [12, 13, 14] (sin repetidos, en el mismo orden). Lanza ValueError si hay algo que no es número."""
    res = []
    for trozo in (texto or '').replace(';', ',').split(','):
        trozo = trozo.strip()
        if not trozo:
            continue
        n = int(trozo)
        if n <= 0:
            raise ValueError('id no válido: %s' % trozo)
        if n not in res:
            res.append(n)
    return res


def texto_de_ids(ids):
    return ','.join(str(int(i)) for i in ids)


def copias_validas(copias):
    """Número de copias entre 1 y MAX_COPIAS; lanza ValueError si no."""
    n = int(copias or 1)
    if n < 1 or n > MAX_COPIAS:
        raise ValueError('Copias fuera de rango (1-%d): %s' % (MAX_COPIAS, copias))
    return n


def unicos_por_contenido(adjuntos):
    """[{'id', 'checksum'}] -> ids sin repetir contenido (el mismo PDF adjunto a varias OUT se imprime una vez).
    Sin checksum, cuenta el id."""
    vistos = set()
    res = []
    for a in adjuntos:
        clave = a.get('checksum') or ('id', a.get('id'))
        if clave in vistos:
            continue
        vistos.add(clave)
        res.append(a['id'])
    return res


def comprobar_trabajo(adjunto_ids, informe, modelo, ids):
    """Qué se imprime: o adjuntos PDF, o un informe con sus registros. Devuelve el texto del error o None."""
    if adjunto_ids and (informe or modelo or ids):
        return 'Un trabajo es o un adjunto o un informe, no las dos cosas.'
    if adjunto_ids:
        return None
    if not informe:
        return 'Falta qué imprimir (adjunto o informe).'
    if '.' not in informe:
        return 'El informe tiene que ir como modulo.plantilla: %s' % informe
    if not modelo or not ids:
        return 'Falta el modelo o los registros del informe %s.' % informe
    return None
