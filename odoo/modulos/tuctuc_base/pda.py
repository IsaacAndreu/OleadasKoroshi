# -*- coding: utf-8 -*-
# =============================================================================
# TUCTUC Base - ayudas de las rutas de la PDA (con Odoo). Clon de koroshi_base/pda.py 1.2.1, multicompañía.
#     from odoo.addons.tuctuc_base import pda
#     pda.comprobar_grupo(request.env, 'No tienes permiso para ...')
#     emp = pda.empleado_valido(request.env, employee_id)
#     p = pda.buscar_producto(request.env, codigo)
#     picking = pda.con_compania(picking)        # el registro con la compañía del documento activa
#     pda.parametro(request.env, 'tuctuc_base.prefijos_ean', comun.PREFIJOS_EAN)
# =============================================================================
from odoo.exceptions import UserError

from . import comun

GRUPO_ALMACEN = 'stock.group_stock_user'
SIN_TARJETA = 'Pasa antes tu tarjeta de operario.'
TARJETA_NO_VALE = ('Esa tarjeta ya no vale (operario de baja, sin tarjeta o de otra empresa). Pasa otra vez tu '
                   'tarjeta.')
SIN_COMPANIA = ('Tu usuario de Odoo no tiene la compañía %s. Pide que te la den (Ajustes > Usuarios) para trabajar '
                'con este documento.')


def parametro(env, clave, defecto=''):
    """Parámetro del sistema (con sudo); si no existe o está vacío, el valor por defecto."""
    return env['ir.config_parameter'].sudo().get_param(clave) or defecto


def lista_parametro(env, clave, defecto=''):
    """Parámetro con varios valores separados por comas, como lista."""
    return comun.lista(parametro(env, clave, defecto))


def prefijos_ean(env):
    return lista_parametro(env, 'tuctuc_base.prefijos_ean', comun.PREFIJOS_EAN)


def prefijos_contenedor(env):
    return lista_parametro(env, 'tuctuc_base.prefijos_contenedor', comun.PREFIJOS_CONTENEDOR)


def tipos_oleada(env):
    return lista_parametro(env, 'tuctuc_base.tipos_oleada', comun.TIPOS_OLEADA)


def patron_caja(env):
    return parametro(env, 'tuctuc_base.patron_caja', comun.PATRON_CAJA)


def texto_turnos(env):
    return parametro(env, comun.PARAM_TURNOS, comun.TURNOS)


def companias(env):
    """Compañías de la PDA (las de los almacenes activos de tuctuc.almacen)."""
    return env['tuctuc.almacen'].companias()


def con_compania(registros, compania=None):
    """Los registros con la compañía del documento como compañía activa (allowed_company_ids empieza por ella) y, detrás,
    las demás compañías de la PDA que tenga el usuario. Así Odoo crea paquetes, movimientos y lo que haga falta con la
    compañía del documento aunque en la PDA esté marcada otra. Si el usuario no tiene esa compañía: UserError."""
    env = registros.env
    if compania is None:
        compania = registros[:1].sudo().company_id if 'company_id' in registros._fields else env.company
    if not compania:
        return registros
    usuario = env.user.company_ids
    if compania not in usuario:
        raise UserError(SIN_COMPANIA % compania.name)
    otras = [c.id for c in companias(env) if c in usuario and c != compania]
    return registros.with_context(allowed_company_ids=[compania.id] + otras)


def comprobar_grupo(env, mensaje='No tienes permiso para esto.', grupo=GRUPO_ALMACEN):
    """UserError(mensaje) si el usuario de Odoo de la PDA no está en el grupo (por defecto, Inventario / Usuario)."""
    if not env.user.has_group(grupo):
        raise UserError(mensaje)


def es_empleado_valido(env, emp):
    """Empleado activo, con tarjeta (ID de credencial) y sin empresa o de una empresa del usuario de Odoo de la PDA."""
    if not emp or not emp.active or not (emp.barcode or '').strip():
        return False
    return not emp.company_id or emp.company_id in env.user.company_ids


def empleado_valido(env, employee_id, obligatorio=True, mensaje=SIN_TARJETA):
    """Operario (hr.employee, con sudo) de la tarjeta que manda la PDA; tiene que cumplir es_empleado_valido. Si no
    vale, UserError. Sin id: UserError(mensaje) si es obligatorio; si no, vacío."""
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
    """Prenda leída (product.product en el env que se pasa; vacío si no hay). Se prueba, por orden: EAN (y UPC/EAN con
    o sin 0 delante), código alternativo (product.barcode, si está instalado), referencia interna y, con por_nombre, el
    nombre exacto de un artículo sin compañía o de una compañía de la PDA. Busca con sudo.
    archivados: también artículos archivados (pueden tener stock)."""
    Product = env['product.product']
    variantes = comun.variantes_codigo(codigo)
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
        p = Buscar.search([('name', '=', codigo), ('company_id', 'in', companias(env).ids + [False])], limit=1)
    return Product.browse(p.id) if p else Product.browse()
