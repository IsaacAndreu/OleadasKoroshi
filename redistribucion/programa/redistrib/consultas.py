# -*- coding: utf-8 -*-
"""Qué se lee de Odoo: dominios y campos. Funciones puras (sin conexión), para poder probarlas sin Odoo.

Lo que se ha comprobado en el código del repo antes de escribir esto (23/11/2026):
- Contenedores KO_/TT_: son `stock.location` (usage internal) hijas del hueco, no paquetes. Así los mueve y
  los archiva koroshi_contenedores (controllers/main.py: PREFIJOS, `Loc.search([('location_id', '=', hueco.id)…`,
  `c.write({'location_id': destino.id})`), y se niega a tocar un contenedor si algún quant lleva package_id.
- Temporada: `product.template.season_id` (su `.name`: I27, V27…), como en bin/KOROSHI_crear_INT_zonas_PLANIFICADA.py.
  El campo no es de un módulo KOROSHI: se confirma con fields_get en «probar conexión».
- Modelo, color y talla: del código del producto «MODELO-COLOR-TALLA» (odoo/KOROSHI_exportar_tallas_MASTER_SHELL…:
  `codigo.split('-')`). Familia: letras 5 y 6 del modelo (RE_TIPO de koroshi_kpi). Volumen: `product.product.volume` (m³).
"""
import datetime

from .odoo_lectura import COMPANIA

PATRON_CONTENEDOR = ['|', ('name', '=like', r'KO\_%'), ('name', '=like', r'TT\_%')]
SIN_ARCHIVAR = {'active_test': False}

# Campos que hacen falta (paso B). «probar conexión» comprueba que existen antes de bajar nada.
CAMPOS_NECESARIOS = {
    'stock.location': ['name', 'complete_name', 'location_id', 'barcode', 'active', 'usage', 'company_id'],
    'stock.quant': ['location_id', 'product_id', 'quantity', 'reserved_quantity', 'package_id', 'company_id'],
    'product.product': ['default_code', 'name', 'barcode', 'product_tmpl_id', 'volume', 'weight', 'active'],
    'product.template': ['season_id'],
    'stock.move.line': ['product_id', 'location_id', 'location_dest_id', 'qty_done', 'date', 'state',
                        'picking_id', 'move_id'],
}


def dominio_lineas_hechas(campos_linea, desde, codigo_tipo):
    """Líneas de movimiento hechas desde `desde` (fecha) de un tipo de operación ('outgoing', 'internal').
    Usa company_id y picking_code de la línea si existen en este Odoo; si no, va por el albarán."""
    dominio = [('state', '=', 'done'), ('date', '>=', desde.strftime('%Y-%m-%d 00:00:00'))]
    dominio.append(('company_id', '=', COMPANIA) if 'company_id' in campos_linea
                   else ('move_id.company_id', '=', COMPANIA))
    dominio.append(('picking_code', '=', codigo_tipo) if 'picking_code' in campos_linea
                   else ('picking_id.picking_type_id.code', '=', codigo_tipo))
    dominio.append(('location_id.usage', '=', 'internal'))
    return dominio


def conteos(campos_linea, hoy=None, semanas_calor=4, desde_historico=None):
    """Lista de (etiqueta, modelo, dominio, contexto) que cuenta «probar conexión» con search_count.
    `campos_linea` = campos de stock.move.line en este Odoo (de fields_get)."""
    hoy = hoy or datetime.date.today()
    desde_calor = hoy - datetime.timedelta(weeks=semanas_calor)
    desde_historico = desde_historico or hoy - datetime.timedelta(days=365)
    compania = [('company_id', '=', COMPANIA)]
    internas = compania + [('usage', '=', 'internal')]
    lista = [
        ('Ubicaciones internas activas', 'stock.location', internas, {}),
        ('Ubicaciones internas archivadas', 'stock.location', internas + [('active', '=', False)], SIN_ARCHIVAR),
        # Nombre real (muestra del 23/11): «00006 - L01 P19 C2», código de barras «L01 P19 C2», padre NAVE2
        ('  de ellas, con «L.. P.. C.» en el nombre (huecos de lineal)', 'stock.location',
         internas + [('name', '=ilike', '%L% P% C%')], {}),
        ('  de ellas, dentro de NAVE2', 'stock.location', internas + [('complete_name', 'ilike', '/NAVE2/')], {}),
        ('  contenedores KO_/TT_ activos', 'stock.location', internas + PATRON_CONTENEDOR, {}),
        ('  contenedores KO_/TT_ archivados', 'stock.location', internas + [('active', '=', False)] + PATRON_CONTENEDOR,
         SIN_ARCHIVAR),
        ('  muelle (nombre MU-…)', 'stock.location', internas + [('name', '=ilike', 'MU-%')], {}),
        ('  N1- (en la ruta completa)', 'stock.location', internas + [('complete_name', 'ilike', '/N1-')], {}),
        ('Stock (quants) en ubicaciones internas', 'stock.quant', compania + [('location_id.usage', '=', 'internal')], {}),
        ('  con cantidad distinta de 0', 'stock.quant',
         compania + [('location_id.usage', '=', 'internal'), ('quantity', '!=', 0)], {}),
        ('  con cantidad negativa', 'stock.quant',
         compania + [('location_id.usage', '=', 'internal'), ('quantity', '<', 0)], {}),
        ('  con paquete (package_id)', 'stock.quant',
         compania + [('location_id.usage', '=', 'internal'), ('package_id', '!=', False)], {}),
        ('Productos con stock en la compañía 8', 'product.product',
         [('stock_quant_ids.company_id', '=', COMPANIA), ('stock_quant_ids.location_id.usage', '=', 'internal')],
         SIN_ARCHIVAR),
        ('Líneas de salida hechas, últimas %d semanas (calor)' % semanas_calor, 'stock.move.line',
         dominio_lineas_hechas(campos_linea, desde_calor, 'outgoing'), {}),
        ('Líneas internas hechas, últimas %d semanas (INT de zonas)' % semanas_calor, 'stock.move.line',
         dominio_lineas_hechas(campos_linea, desde_calor, 'internal'), {}),
        ('Líneas de salida hechas desde %s (histórico)' % desde_historico.strftime('%d/%m/%Y'), 'stock.move.line',
         dominio_lineas_hechas(campos_linea, desde_historico, 'outgoing'), {}),
    ]
    return lista


def campos_que_faltan(campos_por_modelo):
    """{modelo: [campos que no están]} comparando CAMPOS_NECESARIOS con lo que devolvió fields_get."""
    falta = {}
    for modelo, necesarios in CAMPOS_NECESARIOS.items():
        hay = campos_por_modelo.get(modelo) or {}
        no = [c for c in necesarios if c not in hay]
        if no:
            falta[modelo] = no
    return falta
