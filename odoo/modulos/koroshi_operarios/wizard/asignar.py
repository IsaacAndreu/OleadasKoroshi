# -*- coding: utf-8 -*-
# KOROSHI Operarios v2 - el responsable asigna OUT o agrupaciones a un operario (Accion > Asignar a operario
# en la lista de albaranes o de agrupaciones). Solo escribe en koroshi.operario.asignacion.
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..models.tarea import PREFIJOS_ZONA


class KoroshiOperarioAsignar(models.TransientModel):
    _name = 'koroshi.operario.asignar'
    _description = 'KOROSHI Asignar pedidos a un operario'

    employee_id = fields.Many2one('hr.employee', 'Operario', required=True)
    picking_ids = fields.Many2many('stock.picking', string='Pedidos (OUT)')
    batch_ids = fields.Many2many('stock.picking.batch', string='Agrupaciones')
    al_principio = fields.Boolean('Ponerlos los primeros de su cola',
                                  help='Si no, van al final de lo que ya tiene asignado.')

    @api.model
    def default_get(self, campos):
        res = super().default_get(campos)
        modelo = self.env.context.get('active_model')
        ids = self.env.context.get('active_ids') or []
        if modelo == 'stock.picking':
            res['picking_ids'] = [(6, 0, ids)]
        elif modelo == 'stock.picking.batch':
            res['batch_ids'] = [(6, 0, ids)]
        return res

    def action_asignar(self):
        self.ensure_one()
        Asig = self.env['koroshi.operario.asignacion'].sudo()
        emp = self.employee_id
        if not self.picking_ids and not self.batch_ids:
            raise UserError(_('No hay pedidos seleccionados.'))
        objetivos = []
        for p in self.picking_ids:
            if p.state in ('done', 'cancel'):
                raise UserError(_('%s ya esta validada o cancelada.') % p.name)
            if p.batch_id and (p.batch_id.name or '').startswith(PREFIJOS_ZONA):
                raise UserError(_('%s es de la agrupacion %s: asigna la agrupacion entera (lista de agrupaciones).')
                                % (p.name, p.batch_id.name))
            objetivos.append(('out', p))
        for b in self.batch_ids:
            if b.state in ('done', 'cancel'):
                raise UserError(_('La agrupacion %s ya esta hecha o cancelada.') % b.name)
            objetivos.append(('agrupacion', b))
        if self.al_principio:
            objetivos.reverse()     # cada uno se pone delante del anterior: quedan en el orden elegido
        hechos = 0
        for tipo, obj in objetivos:
            viva = Asig._viva_de(picking=obj if tipo == 'out' else None, lote=obj if tipo == 'agrupacion' else None)
            sec = Asig._primera_secuencia(emp) if self.al_principio else Asig._ultima_secuencia(emp)
            if viva:
                if viva.estado == 'curso' and viva.employee_id != emp:
                    raise UserError(_('%s la esta haciendo ahora %s. Quitala primero en Colas.')
                                    % (viva.name, viva.employee_id.name))
                if viva.estado != 'curso':
                    viva.write({'employee_id': emp.id, 'estado': 'cola', 'secuencia': sec, 'origen': 'manual'})
                hechos += 1
                continue
            vals = {'employee_id': emp.id, 'tipo': tipo, 'origen': 'manual', 'estado': 'cola', 'secuencia': sec,
                    'company_id': obj.company_id.id or self.env.company.id}
            if tipo == 'out':
                vals.update({'picking_id': obj.id, 'batch_id': obj.batch_id.id or False})
            else:
                vals['batch_id'] = obj.id
            if not Asig._crear_segura(vals):
                raise UserError(_('%s acaba de cogerla otra PDA. Vuelve a intentarlo.') % obj.name)
            hechos += 1
        # v2.13: Odoo 13 no tiene la accion display_notification (daba error despues de asignar): se abre la cola
        # del operario con el resultado en el titulo
        return {
            'type': 'ir.actions.act_window',
            'name': _('%s pedido(s) asignados a %s') % (hechos, emp.name),
            'res_model': 'koroshi.operario.asignacion',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', emp.id), ('estado', 'in', ('cola', 'curso'))],
            'target': 'current',
        }
