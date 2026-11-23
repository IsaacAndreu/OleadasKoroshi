# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Base - ayudas de las rutas de la PDA (con Odoo). v1.2.0 (revision general 23/11, O5 y R16).
# Uso: from odoo.addons.koroshi_base import pda
#      pda.comprobar_grupo(request.env, 'No tienes permiso para ...')
#      emp = pda.empleado_valido(request.env, employee_id)
#      p = pda.buscar_producto(request.env, codigo)
# Antes cada modulo tenia su copia: la busqueda por EAN de Faltante no probaba el codigo alternativo ni el nombre, y la
# tarjeta que mandaba la PDA solo se miraba que existiera (preparacion ni eso).
# =============================================================================
from odoo.exceptions import UserError

from .comun import COMPANY_ID, variantes_codigo

GRUPO_ALMACEN = 'stock.group_stock_user'
SIN_TARJETA = 'Pasa antes tu tarjeta de operario.'
TARJETA_NO_VALE = ('Esa tarjeta ya no vale (operario de baja, sin tarjeta o de otra empresa). Pasa otra vez tu '
                   'tarjeta.')


def comprobar_grupo(env, mensaje='No tienes permiso para esto.', grupo=GRUPO_ALMACEN):
    """UserError(mensaje) si el usuario de Odoo de la PDA no esta en el grupo (por defecto, Inventario / Usuario)."""
    if not env.user.has_group(grupo):
        raise UserError(mensaje)


def es_empleado_valido(env, emp):
    """v1.2.1: la misma regla que koroshi_operarios._empleado_valido (v2.13, auditoria 13/11): empleado activo, con
    tarjeta (ID de credencial) y sin empresa o de una empresa del usuario de Odoo de la PDA."""
    if not emp or not emp.active or not (emp.barcode or '').strip():
        return False
    return not emp.company_id or emp.company_id in env.user.company_ids


def empleado_valido(env, employee_id, obligatorio=True, mensaje=SIN_TARJETA):
    """Operario (hr.employee, con sudo) de la tarjeta que manda la PDA; tiene que cumplir es_empleado_valido. Si no
    vale, UserError. Sin id: UserError(mensaje) si es obligatorio; si no, vacio."""
    Emp = env['hr.employee'].sudo()
    try:
        eid = int(employee_id or 0)
    except (TypeError, ValueError):
        eid = 0
    if not eid:
        if obligatorio:
            raise UserError(mensaje)
        return Emp.browse()
    emp = Emp.with_context(active_test=False).browse(eid).exists()
    if not es_empleado_valido(env, emp):
        raise UserError(TARJETA_NO_VALE)
    return emp.with_context(active_test=True)


def buscar_producto(env, codigo, archivados=False, por_nombre=True):
    """Prenda leida (product.product en el env que se pasa; vacio si no hay). Se prueba, por orden: EAN (y UPC/EAN con
    o sin 0 delante), codigo alternativo (product.barcode, si esta instalado), referencia interna y, con por_nombre, el
    nombre exacto (muchos articulos no tienen referencia interna: la referencia es el nombre). Busca con sudo.
    archivados: tambien articulos archivados (pueden tener stock)."""
    Product = env['product.product']
    variantes = variantes_codigo(codigo)
    if not variantes:
        return Product.browse()
    codigo = variantes[0]
    Buscar = Product.sudo().with_context(active_test=False) if archivados else Product.sudo()
    p = Buscar.search([('barcode', 'in', variantes)], limit=1)
    if not p and 'product.barcode' in env:
        p = env['product.barcode'].sudo().search([('name', 'in', variantes)], limit=1).product_id
    if not p:
        p = Buscar.search([('default_code', '=', codigo)], limit=1)
    if not p and por_nombre:
        p = Buscar.search([('name', '=', codigo), ('company_id', 'in', [COMPANY_ID, False])], limit=1)
    return Product.browse(p.id) if p else Product.browse()
