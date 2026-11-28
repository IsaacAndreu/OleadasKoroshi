# -*- coding: utf-8 -*-
{
    'name': 'TUCTUC Base',
    'summary': 'Lo común de la PDA de la nave de Oriola - Amposta: almacenes y compañías, hora del almacén, parámetros',
    'description': """
Base de los módulos tuctuc_* (la PDA de Lecturas, preparación, faltantes y compactar en odoo.tuctuc.com).
Clon de koroshi_base 1.2.1: decisión de Isaac del 27/11/2026, módulos nuevos para esta nave sin tocar los koroshi_*.
Diseño: bin/versiones/tuctuc_pda/20261127_diseno-clon-tuctuc-pda_v1.md.

La nave es una, pero en Odoo son tres compañías con su almacén: PRIME COLLECTIONS (WH-OR), MODA INTIMA (MODAI) y
UNITED BRANDS (UBRAN); MODA INTIMA tiene además MIECI (ECI). No hay compañía fija (en koroshi_base era
COMPANY_ID = 8): la compañía sale de cada documento.

- Modelo tuctuc.almacen (Inventario > Configuración > TUCTUC PDA: almacenes): los almacenes que usan la PDA, con su
  SORTER, su ubicación de faltantes y la zona de picking. Al instalar se crean WH-OR, MODAI, UBRAN y MIECI (si existen).
  activos(), companias(), de_ubicacion(ubicación), de_picking(albarán).
- comun.py (Python puro, tests sin Odoo en tests/): TZ, ahora_local(), hoy_local(), rango_dia_utc(dia),
  rango_dias_utc(), a_local(), dia_local(), turno_de(entrada), variantes_codigo(), es_caja(codigo),
  nombre_corto(ubicacion) (sin el almacén ni Stock/STOCK delante), lista(texto), empieza_por(codigo, prefijos).
- pda.py (rutas de la PDA): con_compania(registros) (la compañía del documento como compañía activa),
  comprobar_grupo(), empleado_valido(), buscar_producto(), parametro() y los prefijos y tipos de los parámetros.
- static/src/js/comun.js: odoo.define('tuctuc_base.comun'): esCaja, tarjeta de operario compartida
  (tuctuc_operarios_pda_<usuario>) y lector «leer al parar».
- Parámetros (noupdate): tuctuc_base.turnos, tuctuc_base.prefijos_ean (8447333,8435689),
  tuctuc_base.prefijos_contenedor (KO_,TT_,UB_,MI_), tuctuc_base.tipos_oleada (WEB, WEB B&B, PED. INICIAL: van por INT
  al SORTER) y tuctuc_base.patron_caja (BOX + 7 cifras).

v1.0.0 (27/11/2026): primera versión, clon multicompañía de koroshi_base 1.2.1 para odoo.tuctuc.com.
v1.0.1 (28/11/2026): prefijo de contenedor MI_ (MODA INTIMA, visto en tuctuc el 28/11) en comun.PREFIJOS_CONTENEDOR
y en el parámetro tuctuc_base.prefijos_contenedor. El parámetro es noupdate: en una base que ya tenga la 1.0.0
instalada hay que añadir MI_ a mano (aún no está instalada en ninguna). Y al instalar, si hay dos almacenes con el
mismo código (en tuctuc, MODAI y MIECI también en PRIME, ids 251 y 252), se coge el más antiguo (MODAI 109).
MIECI (ECI - MODA INTIMA, id 110) entra también en la PDA al instalar (Isaac, 28/11), con la zona de picking vacía
(sus huecos cuelgan de MIECI/Stock, sin N1).
""",
    'version': '13.0.1.0.1',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/parametros.xml',
        'data/almacenes.xml',
        'views/assets.xml',
        'views/almacen_views.xml',
    ],
    'installable': True,
    'application': False,
}
