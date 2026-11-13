# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class KoroshiConsumableItem(models.Model):
    _name = 'koroshi.consumable.item'
    _description = 'Artículo consumible KOROSHI'
    _order = 'active desc, name asc'

    name = fields.Char(string='Artículo', required=True)
    code = fields.Char(string='Código interno', index=True)
    category = fields.Char(string='Categoría')
    uom = fields.Selection([
        ('unidad', 'Unidades'),
        ('caja', 'Cajas'),
        ('paquete', 'Paquetes'),
        ('rollo', 'Rollos'),
        ('otro', 'Otra unidad'),
    ], string='Unidad', required=True, default='unidad')
    initial_qty = fields.Float(
        string='Total inicial', digits=(16, 2), default=0.0,
        help='Cantidad conocida al poner en marcha el control. Betty puede revisarla con un ajuste posterior.',
    )
    minimum_qty = fields.Float(
        string='Mínimo de aviso', digits=(16, 2), default=0.0,
        help='Si el stock actual baja hasta este valor, aparece como bajo mínimo.',
    )
    # v1.3: correo cuando baja al mínimo o se agota
    aviso_emails = fields.Char(
        string='Avisar por correo a',
        help='Correos separados por comas. Llega un correo cuando el stock baja al mínimo de aviso y otro si se agota '
             '(una vez cada vez que cruza; si se repone y vuelve a bajar, otra vez).')
    company_id = fields.Many2one(
        'res.company', string='Compañía', required=True,
        default=lambda self: self.env.user.company_id, index=True,
    )
    active = fields.Boolean(default=True)
    note = fields.Text(string='Notas')
    movement_ids = fields.One2many(
        'koroshi.consumable.move', 'item_id', string='Movimientos',
    )
    current_qty = fields.Float(
        string='Stock actual', compute='_compute_totals', store=True,
        digits=(16, 2),
    )
    total_consumed = fields.Float(
        string='Total consumido', compute='_compute_totals', store=True,
        digits=(16, 2),
    )
    total_entries = fields.Float(
        string='Total entradas', compute='_compute_totals', store=True,
        digits=(16, 2),
    )
    stock_status = fields.Selection([
        ('ok', 'Correcto'),
        ('low', 'Bajo mínimo'),
        ('empty', 'Agotado'),
    ], string='Estado', compute='_compute_totals', store=True)
    last_move_date = fields.Datetime(
        string='Último movimiento', compute='_compute_last_move', store=True,
    )
    # v1.2: cajas que el operario elige en la PDA al cerrar una caja (Lecturas). Cada caja cerrada resta 1.
    es_caja = fields.Boolean(
        string='Es una caja (se elige en la PDA)',
        help='Sale en Lecturas (PDA) al cerrar una caja. Cada caja cerrada de este tipo resta 1 del stock.',
    )
    nombre_pda = fields.Char(
        string='Nombre en la PDA', help='Corto, para el botón de la PDA (p. ej. «Grande»). Vacío = el nombre.')
    secuencia = fields.Integer(string='Orden en la PDA', default=10)
    en_lecturas = fields.Boolean(
        string='Se elige en Lecturas', default=True,
        help='Sale en la PDA al cerrar una caja de tienda (CJ / Zalando). Las online (web) van por INT al SORTER y no '
             'cierran caja en Lecturas: déjalo sin marcar.')
    largo_mm = fields.Integer(string='Largo (mm)')
    ancho_mm = fields.Integer(string='Ancho (mm)')
    alto_mm = fields.Integer(string='Alto (mm)')
    volumen_m3 = fields.Float(string='Volumen (m3)', digits=(12, 4), compute='_compute_volumen', store=True)
    packaging_id = fields.Many2one(
        'product.packaging', string='Tipo de paquete en Odoo', readonly=True, copy=False,
        help='Se crea solo: es el «Tipo de paquete» que se pone a la caja (stock.quant.package) al cerrarla.')

    _sql_constraints = [
        ('code_company_unique', 'unique(code, company_id)',
         'El código interno debe ser único dentro de la compañía.'),
    ]

    @api.depends('initial_qty', 'minimum_qty', 'movement_ids.quantity',
                 'movement_ids.movement_type')
    def _compute_totals(self):
        for item in self:
            consumed = sum(
                move.quantity for move in item.movement_ids
                if move.movement_type == 'consumption'
            )
            entries = sum(
                move.quantity for move in item.movement_ids
                if move.movement_type == 'entry'
            )
            corrections = sum(
                move.quantity for move in item.movement_ids
                if move.movement_type == 'adjustment'
            )
            current = item.initial_qty + entries - consumed + corrections
            item.total_consumed = consumed
            item.total_entries = entries
            item.current_qty = current
            if current <= 0:
                item.stock_status = 'empty'
            elif item.minimum_qty and current <= item.minimum_qty:
                item.stock_status = 'low'
            else:
                item.stock_status = 'ok'

    def _avisar_si_cruza(self, antes):
        """v1.3: si con este consumo el stock cruza el mínimo de aviso (o llega a 0), correo a aviso_emails. Nunca
        para el consumo (ni el cierre de la caja en la PDA)."""
        self.ensure_one()
        try:
            correos = [c.strip() for c in (self.aviso_emails or '').replace(';', ',').split(',') if c.strip()]
            if not correos:
                return False
            ahora = self.current_qty
            if antes > 0 >= ahora:
                que = 'se ha AGOTADO'
            elif self.minimum_qty and antes > self.minimum_qty >= ahora:
                que = 'está bajo el mínimo'
            else:
                return False
            nombre = self.display_name
            cuerpo = ('<p><b>%s</b> %s.</p><p>Stock actual: <b>%s</b> · mínimo de aviso: %s.</p>'
                      '<p>Inventario &gt; Consumibles. Cuando llegue más, regístralo como entrada.</p>') % (
                nombre, que, round(ahora, 2), round(self.minimum_qty, 2))
            with self.env.cr.savepoint():
                self.env['mail.mail'].sudo().create({
                    'subject': 'Consumibles: %s %s (quedan %s)' % (nombre, que, round(ahora, 2)),
                    'body_html': cuerpo,
                    'email_to': ', '.join(correos),
                    'auto_delete': True,
                })
            return True
        except Exception:
            _logger.exception('KOROSHI Consumibles: no se ha podido avisar de %s', self.display_name)
            return False

    @api.depends('largo_mm', 'ancho_mm', 'alto_mm')
    def _compute_volumen(self):
        for item in self:
            item.volumen_m3 = (item.largo_mm or 0) * (item.ancho_mm or 0) * (item.alto_mm or 0) / 1e9

    # ------------------------------------------------------------------ v1.2: cajas
    def _medidas_texto(self):
        self.ensure_one()
        if self.largo_mm and self.ancho_mm and self.alto_mm:
            return '%sx%sx%s' % (self.largo_mm, self.ancho_mm, self.alto_mm)
        return ''

    def _sincronizar_packaging(self):
        """El «Tipo de paquete» de Odoo de cada caja: mismo nombre y medidas en cm (como los que ya hay)."""
        Pack = self.env['product.packaging'].sudo()
        for item in self.filtered('es_caja'):
            vals = {'name': item.name, 'length': int(round((item.largo_mm or 0) / 10.0)),
                    'width': int(round((item.ancho_mm or 0) / 10.0)),
                    'height': int(round((item.alto_mm or 0) / 10.0))}
            if item.packaging_id:
                item.packaging_id.write(vals)
            else:
                vals['product_id'] = False
                item.with_context(koroshi_sin_sincronizar=True).write({'packaging_id': Pack.create(vals).id})

    @api.model
    def create(self, vals):
        item = super(KoroshiConsumableItem, self).create(vals)
        if item.es_caja:
            item._sincronizar_packaging()
        return item

    def write(self, vals):
        res = super(KoroshiConsumableItem, self).write(vals)
        if not self.env.context.get('koroshi_sin_sincronizar') and \
                set(vals) & {'es_caja', 'name', 'largo_mm', 'ancho_mm', 'alto_mm'}:
            self._sincronizar_packaging()
        return res

    @api.model
    def cajas_pda(self, company=None):
        """Las cajas para elegir en la PDA: [{id, nombre, medidas}] en su orden."""
        company = company or self.env.user.company_id
        items = self.sudo().search([('es_caja', '=', True), ('en_lecturas', '=', True), ('active', '=', True),
                                    ('company_id', '=', company.id)], order='secuencia, name')
        return [{'id': i.id, 'nombre': i.nombre_pda or i.name, 'medidas': i._medidas_texto()} for i in items]

    @api.model
    def consumir_caja(self, item_id, nota=''):
        """Resta 1 caja (desde la PDA). Nunca para el cierre de la caja: si no hay stock, queda en negativo
        («Agotado») para que Betty lo corrija; si algo falla, se apunta en el log."""
        item = self.sudo().browse(int(item_id or 0)).exists()
        if not item or not item.es_caja:
            return False
        try:
            with self.env.cr.savepoint():
                self.env['koroshi.consumable.move'].sudo().with_context(koroshi_permitir_negativo=True).create({
                    'item_id': item.id, 'movement_type': 'consumption', 'quantity': 1.0,
                    'note': (nota or '')[:250], 'responsible_id': self.env.user.id})
            return True
        except Exception:
            _logger.exception('KOROSHI Consumibles: no se ha podido restar la caja %s', item.display_name)
            return False

    @api.model
    def _cajas_koroshi_iniciales(self):
        """v1.2 (al instalar): las cajas de KOROSHI. Busca por código; si ya existe solo la marca como caja."""
        empresa = self.env['res.company'].sudo().browse(8).exists() or self.env.user.company_id
        cajas = [   # v1.2.1: la online no sale en Lecturas (lo online va por INT al SORTER, sin caja)
            ('KCAJA590X390X400', 'CAJA KOROSHI 590X390X400', 'Grande', 10, (590, 390, 400), True),
            ('KCAJA600X400X400', 'CAJA 600X400X400', '60x40x40', 20, (600, 400, 400), True),
            ('KCAJAMEDIANA', 'CAJA KOROSHI MEDIANA', 'Mediana', 30, (0, 0, 0), True),
            ('KCAJA280X280X120', 'CAJA KOROSHI ONLINE 280X280X120', 'Online', 40, (280, 280, 120), False),
        ]
        for code, name, corto, sec, (l, a, h), lecturas in cajas:
            item = self.sudo().with_context(active_test=False).search(
                [('code', '=', code), ('company_id', '=', empresa.id)], limit=1)
            vals = {'es_caja': True, 'nombre_pda': corto, 'secuencia': sec, 'en_lecturas': lecturas}
            if item:
                if not item.largo_mm and l:
                    vals.update({'largo_mm': l, 'ancho_mm': a, 'alto_mm': h})
                item.write(vals)
            else:
                vals.update({'code': code, 'name': name, 'uom': 'unidad', 'company_id': empresa.id,
                             'largo_mm': l, 'ancho_mm': a, 'alto_mm': h})
                self.sudo().create(vals)
        return True

    @api.depends('movement_ids.date')
    def _compute_last_move(self):
        for item in self:
            dates = item.movement_ids.mapped('date')
            item.last_move_date = max(dates) if dates else False

    @api.constrains('initial_qty', 'minimum_qty')
    def _check_quantities(self):
        for item in self:
            if item.initial_qty < 0:
                raise ValidationError(_('El total inicial no puede ser negativo.'))
            if item.minimum_qty < 0:
                raise ValidationError(_('El mínimo de aviso no puede ser negativo.'))

    def action_register_consumption(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Registrar consumo'),
            'res_model': 'koroshi.consumable.move',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_item_id': self.id,
                'default_movement_type': 'consumption',
            },
        }


class KoroshiConsumableMove(models.Model):
    _name = 'koroshi.consumable.move'
    _description = 'Movimiento de consumible KOROSHI'
    _order = 'date desc, id desc'

    item_id = fields.Many2one(
        'koroshi.consumable.item', string='Artículo', required=True,
        ondelete='cascade', index=True,
    )
    date = fields.Datetime(
        string='Fecha y hora', required=True, default=fields.Datetime.now,
        index=True,
    )
    movement_type = fields.Selection([
        ('consumption', 'Consumo'),
        ('entry', 'Entrada'),
        ('adjustment', 'Corrección'),
    ], string='Tipo', required=True, default='consumption', index=True)
    quantity = fields.Float(
        string='Cantidad', required=True, digits=(16, 2),
        help='Usa una cantidad positiva para consumos y entradas. En una corrección puede ser positiva o negativa.',
    )
    responsible_id = fields.Many2one(
        'res.users', string='Registrado por', required=True,
        default=lambda self: self.env.user, readonly=True,
    )
    company_id = fields.Many2one(
        related='item_id.company_id', string='Compañía', store=True, readonly=True,
    )
    note = fields.Char(string='Motivo / observaciones')
    signed_quantity = fields.Float(
        string='Impacto en stock', compute='_compute_signed_quantity',
        digits=(16, 2),
    )

    @api.depends('movement_type', 'quantity')
    def _compute_signed_quantity(self):
        for move in self:
            move.signed_quantity = (
                -move.quantity if move.movement_type == 'consumption'
                else move.quantity
            )

    @api.constrains('movement_type', 'quantity')
    def _check_quantity(self):
        for move in self:
            if move.movement_type in ('consumption', 'entry') and move.quantity <= 0:
                raise ValidationError(_('Los consumos y entradas deben tener una cantidad positiva.'))
            if move.movement_type == 'adjustment' and not move.quantity:
                raise ValidationError(_('Una corrección no puede tener cantidad cero.'))

    @api.model
    def create(self, vals):
        move_type = vals.get('movement_type', 'consumption')
        item = self.env['koroshi.consumable.item'].browse(vals.get('item_id')).exists()
        quantity = float(vals.get('quantity') or 0.0)
        if item and move_type == 'consumption' and quantity > item.current_qty + 0.0001 and \
                not self.env.context.get('koroshi_permitir_negativo'):   # v1.2: la PDA no se para
            raise ValidationError(_(
                'No se pueden registrar %(qty)s %(unit)s: el stock actual de %(item)s es %(available)s.'
            ) % {
                'qty': quantity,
                'unit': dict(item._fields['uom'].selection).get(item.uom, item.uom),
                'item': item.display_name,
                'available': item.current_qty,
            })
        antes = item.current_qty if item else 0.0
        move = super(KoroshiConsumableMove, self).create(vals)
        if item and move_type == 'consumption':
            item._avisar_si_cruza(antes)   # v1.3
        return move

    def write(self, vals):
        for move in self:
            move_type = vals.get('movement_type', move.movement_type)
            quantity = float(vals.get('quantity', move.quantity) or 0.0)
            item = self.env['koroshi.consumable.item'].browse(
                vals.get('item_id', move.item_id.id)).exists()
            if item and move_type == 'consumption':
                available = item.current_qty
                if item.id == move.item_id.id:
                    available -= move.signed_quantity
                if quantity > available + 0.0001:
                    raise ValidationError(_(
                        'No se pueden dejar %(qty)s unidades consumidas: el stock disponible de %(item)s es %(available)s.'
                    ) % {
                        'qty': quantity,
                        'item': item.display_name,
                        'available': available,
                    })
        return super(KoroshiConsumableMove, self).write(vals)

    def unlink(self):
        raise ValidationError(_(
            'Los movimientos no se borran para conservar la trazabilidad. Registra una corrección.'
        ))
