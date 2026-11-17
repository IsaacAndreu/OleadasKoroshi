# -*- coding: utf-8 -*-
# v2.18: pantalla «Operarios» para los responsables (grupo productividad), que no tienen permisos de
# Empleados (RRHH): cambiar nombre y codigo, quitar operarios, crear nuevos e imprimir la tarjeta KOROSHI.
# Todo con sudo() y solo sobre empleados con la etiqueta «Operario KOROSHI».
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class KoroshiOperariosGestion(models.TransientModel):
    _name = 'koroshi.operarios.gestion'
    _description = 'KOROSHI Operarios (crear, modificar, quitar, tarjetas)'

    linea_ids = fields.One2many('koroshi.operarios.gestion.linea', 'gestion_id', 'Operarios')
    ver_quitados = fields.Boolean('Ver tambien los quitados')

    @api.model
    def _categoria(self):
        return self.env.ref('koroshi_operarios.categoria_operario_koroshi')

    @api.model
    def _operarios(self, con_quitados=False):
        Emp = self.env['hr.employee'].sudo().with_context(active_test=not con_quitados)
        return Emp.search([('category_ids', 'in', self._categoria().ids),
                           ('company_id', 'in', self.env.companies.ids)], order='active desc, name')

    @api.model
    def _lineas(self, con_quitados=False):
        return [(0, 0, {'emp_id': e.id, 'nombre': e.name, 'codigo': e.barcode or '', 'activo': e.active})
                for e in self._operarios(con_quitados)]

    @api.model
    def default_get(self, campos):
        res = super().default_get(campos)
        if 'linea_ids' in campos:
            res['linea_ids'] = self._lineas()
        return res

    @api.onchange('ver_quitados')
    def _onchange_ver_quitados(self):
        self.linea_ids = [(5, 0, 0)] + self._lineas(self.ver_quitados)

    def _reabrir(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Operarios'),
            'res_model': self._name,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_guardar(self):
        self._guardar()
        return self._reabrir()

    def _guardar(self):
        """Guarda nombres, codigos y altas/bajas cambiados y quita los marcados."""
        self.ensure_one()
        categoria = self._categoria()
        Emp = self.env['hr.employee'].sudo().with_context(active_test=False)
        cambiados, quitados, archivados = [], [], []
        codigos = {}
        for linea in self.linea_ids:
            codigo = (linea.codigo or '').strip().upper()
            if linea.quitar or not codigo:
                continue
            if codigo in codigos:
                raise UserError(_('El codigo %s esta repetido (%s y %s).') % (codigo, codigos[codigo], linea.nombre))
            codigos[codigo] = linea.nombre
        for linea in self.linea_ids:
            emp = Emp.browse(linea.emp_id).exists()
            if not emp or categoria not in emp.category_ids:
                continue
            if linea.quitar:
                if self._quitar(emp):
                    quitados.append(linea.nombre)
                else:
                    archivados.append(linea.nombre)
                continue
            valores = {}
            nombre = (linea.nombre or '').strip()
            codigo = (linea.codigo or '').strip().upper()
            if not nombre:
                raise UserError(_('Falta el nombre del operario con codigo %s.') % (emp.barcode or '?'))
            if not codigo:
                raise UserError(_('Falta el codigo de %s: sin codigo no puede leer su tarjeta.') % nombre)
            if nombre != emp.name:
                valores['name'] = nombre
            if codigo != (emp.barcode or ''):
                otro = Emp.search([('barcode', '=', codigo), ('id', '!=', emp.id)], limit=1)
                if otro:
                    raise UserError(_('El codigo %s ya lo tiene %s.') % (codigo, otro.name))
                valores['barcode'] = codigo
            if linea.activo != emp.active:
                valores['active'] = linea.activo
            if valores:
                emp.write(valores)
                cambiados.append(nombre)
        _logger.info('KOROSHI OPERARIOS gestion (%s): cambiados %s; eliminados %s; dados de baja %s',
                     self.env.user.login, cambiados, quitados, archivados)

    @api.model
    def _quitar(self, emp):
        """Sin historial (tareas, colas) se elimina; con historial se da de baja (archivado) para no perder la
        productividad pasada. Devuelve True si se ha eliminado."""
        con_historial = (self.env['koroshi.operario.tarea'].sudo().search_count([('employee_id', '=', emp.id)])
                         or self.env['koroshi.operario.asignacion'].sudo().with_context(active_test=False)
                         .search_count([('employee_id', '=', emp.id)]))
        if not con_historial:
            try:
                with self.env.cr.savepoint():
                    emp.unlink()
                return True
            except Exception as e:  # p. ej. referencias de otros modulos
                _logger.info('KOROSHI OPERARIOS: %s no se puede eliminar (%s); se da de baja', emp.name, e)
        emp.write({'active': False})
        return False

    def action_crear(self):
        return self.env.ref('koroshi_operarios.action_koroshi_crear_operarios').read()[0]

    def action_imprimir(self):
        self.ensure_one()
        lineas = self.linea_ids.filtered('imprimir')
        if not lineas:
            raise UserError(_('Marca en la columna «Tarjeta» los operarios a imprimir.'))
        if lineas.filtered(lambda l: l.quitar):
            raise UserError(_('Hay operarios marcados a la vez para quitar y para imprimir la tarjeta.'))
        self._guardar()  # la tarjeta sale con el nombre y el codigo que se ven en pantalla
        return self.env.ref('koroshi_operarios.action_report_tarjeta_operario').report_action(self)

    def tarjetas(self):
        """Para el informe: los empleados de las lineas marcadas (ya guardados)."""
        ids = self.linea_ids.filtered('imprimir').mapped('emp_id')
        return self.env['hr.employee'].sudo().with_context(active_test=False).browse(ids).exists()


class KoroshiOperariosGestionLinea(models.TransientModel):
    _name = 'koroshi.operarios.gestion.linea'
    _description = 'KOROSHI Operarios: linea'
    _order = 'activo desc, nombre'

    gestion_id = fields.Many2one('koroshi.operarios.gestion', required=True, ondelete='cascade')
    # entero y no Many2one: los responsables no tienen permiso de leer hr.employee
    emp_id = fields.Integer('Empleado', readonly=True)
    nombre = fields.Char('Nombre')
    codigo = fields.Char('Codigo (tarjeta)')
    activo = fields.Boolean('Activo', default=True)
    imprimir = fields.Boolean('Tarjeta', help='Marcar para imprimir su tarjeta')
    quitar = fields.Boolean('Quitar', help='Al guardar: se elimina si no tiene historial; si lo tiene, se da de baja '
                                           '(deja de poder leer su tarjeta y no se pierde su productividad)')
