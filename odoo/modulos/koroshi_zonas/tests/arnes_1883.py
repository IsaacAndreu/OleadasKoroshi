# -*- coding: utf-8 -*-
# =============================================================================
# Arnes: ejecuta el codigo ORIGINAL de la accion 1883 (tests/original/accion_1883_v12f.py, copia exacta,
# SHA-256 con LF 3d934fca...) sin Odoo, con un env de mentira construido con los mismos datos planos que
# recibe el motor (ver motor/modelo.py). Sirve para comparar el motor con la accion linea a linea.
# Solo cubre lo que usa la accion en DIAGNOSTICO (prueba_ids o prueba_agrupacion): no escribe nada.
# =============================================================================
import datetime as _dt
import os

import pytz

RUTA_ORIGINAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'original', 'accion_1883_v12f.py')


class AvisoOdoo(Exception):
    """Lo que en Odoo es raise Warning(...)."""


class Rec(object):
    def __init__(self, vacio=False, **campos):
        self._vacio = vacio
        for k, v in campos.items():
            setattr(self, k, v)

    def __bool__(self):
        return not self._vacio

    def __getattr__(self, nombre):
        # campo que no se ha dado: en Odoo un many2one vacio devuelve False en todo
        if nombre.startswith('_'):
            raise AttributeError(nombre)
        return False


VACIO = Rec(vacio=True, id=False, name=False, complete_name=False)


class RS(object):
    def __init__(self, recs):
        self._recs = list(recs)

    def __iter__(self):
        return iter(self._recs)

    def __len__(self):
        return len(self._recs)

    def __bool__(self):
        return bool(self._recs)

    def exists(self):
        return self

    def mapped(self, campo):
        return [getattr(r, campo) for r in self._recs]

    @property
    def ids(self):
        return [r.id for r in self._recs]


class ModeloFalso(object):
    def __init__(self, env, nombre):
        self.env = env
        self.nombre = nombre

    def with_context(self, ctx=None, **kw):
        return self

    def browse(self, ids=None):
        if ids is None:
            return RS([])
        if isinstance(ids, (list, tuple)):
            return RS([self.env._pickings[i] for i in ids if i in self.env._pickings])
        return self.env._pickings[ids]

    def search(self, dominio, order=None, limit=None):
        if self.nombre == 'stock.location':
            sid = self.env._datos.get('sorter_id')
            return sid and Rec(id=sid) or VACIO
        if self.nombre == 'stock.picking.batch':
            patron = dict((d[0], d[2]) for d in dominio)['name']
            prefijo = patron.rstrip('%')
            return RS([Rec(name=n) for n in self.env._datos.get('lotes_existentes') or [] if n.startswith(prefijo)])
        if self.nombre == 'stock.picking':
            campos = dict((d[0], d[2]) for d in dominio)
            if 'batch_id.name' not in campos:
                return RS(buscar_hoy(self.env._datos, campos))
            pref = campos['batch_id.name'].rstrip('%')
            sel = [p for p in self.env._pickings.values()
                   if p.company_id.id == campos['company_id'] and p.picking_type_code == 'outgoing'
                   and (p.batch_id.name or '').startswith(pref) and p.state != 'cancel']
            sel.sort(key=lambda p: p.name)
            return RS(sel)
        raise NotImplementedError(self.nombre)


def filtrar_hoy(datos, company_id, tipo_pedido, desde):
    """Lo que hace el search de la accion sin prueba (lineas 283-289) sobre los datos planos: el lector
    lo hace en Odoo con el mismo dominio. 'create_date' de cada OUT en UTC 'AAAA-MM-DD HH:MM:SS'."""
    sel = [o for o in datos['outs'] if o['company_id'] == company_id and o['picking_type_code'] == 'outgoing'
           and o['state'] == 'assigned' and o['tipo_pedido'] == tipo_pedido and o['create_date'] >= desde]
    sel.sort(key=lambda o: o['name'])
    return sel


def buscar_hoy(datos, campos):
    ids = [o['id'] for o in filtrar_hoy(datos, campos['company_id'], campos['sale_id.s_order_type_id.name'],
                                        campos['create_date'])]
    return [_ENV_ACTUAL[0]._pickings[i] for i in ids]


_ENV_ACTUAL = [None]


class EnvFalso(object):
    def __init__(self, datos, contexto):
        self._datos = datos
        self.context = dict(contexto or {})
        self._pickings = {}
        for o in datos['outs']:
            mls = []
            for ml in o['lineas']:
                padre = ml['parent_id'] and Rec(id=ml['parent_id'], complete_name=ml['parent_complete_name']) or VACIO
                ubic = Rec(id=ml['location_id'], complete_name=ml['location_complete_name'],
                           name=ml['location_name'], location_id=padre)
                prod = Rec(id=ml['product_id'], default_code=ml['default_code'], volume=ml['volume'],
                           display_name=ml['default_code'] or str(ml['product_id']))
                mls.append(Rec(id=ml['id'], qty_done=ml['qty_done'], product_uom_qty=ml['qty'],
                               location_id=ubic, product_id=prod))
            movs = RS([Rec(state='assigned', product_uom_qty=o['demanda'])])
            tipo = o['tipo_pedido'] and Rec(name=o['tipo_pedido']) or VACIO
            self._pickings[o['id']] = Rec(
                id=o['id'], name=o['name'], company_id=Rec(id=o['company_id']),
                picking_type_code=o['picking_type_code'], state=o['state'],
                sale_id=Rec(s_order_type_id=tipo, date_order=False),
                batch_id=o['batch_name'] and Rec(name=o['batch_name']) or VACIO,
                location_id=Rec(id=o['location_id']), partner_id=Rec(name=o['partner_name']),
                origin=o['origin'], move_line_ids=RS(mls), move_lines=movs)

    def __getitem__(self, nombre):
        return ModeloFalso(self, nombre)


def ejecutar_original(datos, contexto, modo=None):
    """Ejecuta la 1883 original. Devuelve (lineas del informe, R de la accion).
    modo='DIAGNOSTICO' cambia la linea MODO = 'REAL' (es lo unico que cambia la 1881, junto con el canal)."""
    ahora = _dt.datetime.strptime(datos['ahora'], '%Y-%m-%d %H:%M:%S')

    class DT(_dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return tz.localize(ahora) if tz else ahora

    class ModDT(object):
        datetime = DT
        date = _dt.date
        timedelta = _dt.timedelta

    registro = []
    env = EnvFalso(datos, contexto)
    _ENV_ACTUAL[0] = env
    ns = {
        'env': env,
        'datetime': ModDT,
        'timezone': pytz.timezone,
        'log': lambda texto, level='info': registro.append(texto),
        'Warning': AvisoOdoo,
    }
    with open(RUTA_ORIGINAL, encoding='utf-8') as f:
        codigo = f.read().replace('\r\n', '\n')
    if modo:
        assert codigo.count("\nMODO = 'REAL'\n") == 1
        codigo = codigo.replace("\nMODO = 'REAL'\n", "\nMODO = '%s'\n" % modo)
    texto = None
    try:
        exec(compile(codigo, RUTA_ORIGINAL, 'exec'), ns)
    except AvisoOdoo as e:
        texto = str(e)
    if texto is None:
        raise AssertionError('La accion original no ha acabado con aviso: en DIAGNOSTICO siempre acaba asi')
    return texto.split('\n'), ns.get('R')
