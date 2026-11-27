# -*- coding: utf-8 -*-
# Crear operarios de golpe: una línea por operario -> empleado con código en «ID de credencial» y la etiqueta
# «Operario TUCTUC». No crea usuarios de Odoo. Clon de koroshi_operarios (crear_operarios.py), con un cambio:
#
# LA MISMA TARJETA EN LOS DOS SERVIDORES (decisión de Isaac, 27/11/2026): los operarios son los mismos que en NATH
# (nath.tuctuc.com), con su tarjeta OP0001, OP0002... Para que la misma tarjeta valga aquí, cada línea puede llevar
# el código de NATH delante:
#       OP0007 Nombre Apellido     -> se crea con OP0007 (el de su tarjeta)
#       Nombre Apellido            -> se crea con el siguiente libre (OP + 4 cifras), como en NATH
# Un código que ya tenga otro empleado (aunque esté archivado) no se crea: se avisa y no se crea ninguno.
# Sin compañía por defecto: así valen para PRIME, MODA INTIMA y UNITED (tuctuc_base.pda.es_empleado_valido).
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError

RE_LINEA = re.compile(r'^([A-Za-z]+\d+)\s+(.+)$')


def partir_linea(linea, prefijo):
    """'OP0007 Ana Pérez' -> ('OP0007', 'Ana Pérez') si el código empieza por el prefijo; si no, (None, línea)."""
    linea = (linea or '').strip()
    m = RE_LINEA.match(linea)
    if m and m.group(1).upper().startswith(prefijo):
        return m.group(1).upper(), m.group(2).strip()
    return None, linea


class TuctucCrearOperarios(models.TransientModel):
    _name = 'tuctuc.crear.operarios'
    _description = 'TUCTUC Crear operarios'

    nombres = fields.Text('Operarios', required=True,
                          help='Uno por línea. Con el código de su tarjeta de NATH delante (OP0007 Nombre Apellido) '
                               'para que la misma tarjeta valga aquí; sin código, el siguiente libre.')
    prefijo = fields.Char('Prefijo del código', required=True, default='OP')
    company_id = fields.Many2one('res.company', 'Empresa',
                                 help='Vacío (lo normal): el operario vale para todas las compañías de la nave.')

    @api.model
    def _siguiente_numero(self, prefijo):
        Emp = self.env['hr.employee'].sudo().with_context(active_test=False)
        mayor = 0
        patron = re.compile(r'^%s(\d+)$' % re.escape(prefijo))
        for codigo in Emp.search([('barcode', '=like', prefijo + '%')]).mapped('barcode'):
            m = patron.match(codigo or '')
            if m and int(m.group(1)) > mayor:
                mayor = int(m.group(1))
        return mayor + 1

    def action_crear(self):
        self.ensure_one()
        prefijo = (self.prefijo or 'OP').strip().upper()
        lineas = [partir_linea(n, prefijo) for n in (self.nombres or '').splitlines() if n.strip()]
        if not lineas:
            raise UserError(_('Escribe al menos un operario'))
        Emp = self.env['hr.employee'].sudo()
        Todos = Emp.with_context(active_test=False)
        # códigos que vienen escritos: ni repetidos en la lista ni de otro empleado
        escritos = [c for c, _n in lineas if c]
        repetidos = sorted(set(c for c in escritos if escritos.count(c) > 1))
        if repetidos:
            raise UserError(_('Código repetido en la lista: %s') % ', '.join(repetidos))
        ocupados = Todos.search([('barcode', 'in', escritos)]) if escritos else Todos
        if ocupados:
            raise UserError(_('Estos códigos ya los tiene otro empleado (no se ha creado ninguno):\n%s')
                            % '\n'.join('%s: %s' % (e.barcode, e.name) for e in ocupados))
        categoria = self.env.ref('tuctuc_operarios.categoria_operario_tuctuc')
        numero = self._siguiente_numero(prefijo)
        creados = Emp.browse()
        for codigo, nombre in lineas:
            if not codigo:
                codigo = '%s%04d' % (prefijo, numero)
                while codigo in escritos:
                    numero += 1
                    codigo = '%s%04d' % (prefijo, numero)
                numero += 1
            creados |= Emp.create({
                'name': nombre,
                'barcode': codigo,
                'company_id': self.company_id.id or False,
                'category_ids': [(4, categoria.id)],
            })
        return {
            'type': 'ir.actions.act_window',
            'name': _('%s operario(s) creados') % len(creados),
            'res_model': 'hr.employee',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', creados.ids)],
            'target': 'current',
        }
