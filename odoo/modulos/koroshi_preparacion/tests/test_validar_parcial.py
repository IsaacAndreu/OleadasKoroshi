# -*- coding: utf-8 -*-
# v3.38: OUT de tienda «Validar incompleto» (Isaac, 26/11: «que facin validar i crear parcial»): con líneas sin leer, el
# primer Validar contesta 'quedan' con 'incompleto': True y el segundo valida lo leído (ya en cajas) y deja el resto
# reservado en un pedido pendiente, como Validar -> «Crear pedido pendiente» en el ordenador.
# Se pasan en una base de PRUEBAS (nunca en producción):
#   odoo-bin -d <base_de_pruebas> -u koroshi_preparacion --test-enable --test-tags /koroshi_preparacion --stop-after-init
import inspect
from unittest.mock import patch

from odoo.tests import common, tagged

LECTURA = 'odoo.addons.koroshi_preparacion.models.lectura.COMPANY_ID'
AGRUPACION = 'odoo.addons.koroshi_preparacion.models.agrupacion.COMPANY_ID'
EAN = '8445962999992'


@tagged('post_install', '-at_install', 'koroshi_preparacion')
class TestValidarParcial(common.TransactionCase):

    def setUp(self):
        super(TestValidarParcial, self).setUp()
        for destino in (LECTURA, AGRUPACION):
            p = patch(destino, self.env.company.id)
            p.start()
            self.addCleanup(p.stop)
        put = type(self.env['stock.picking']).put_in_pack
        if 'package_name' not in inspect.signature(put).parameters:
            self.skipTest('put_in_pack(package_name) es de stock_barcode_optimization: no está en esta base')
        self.L = self.env['koroshi.preparacion.lectura']
        almacen = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        self.tipo_out = almacen.out_type_id
        self.stock = almacen.lot_stock_id
        self.cliente = self.env.ref('stock.stock_location_customers')
        self.producto = self.env['product.product'].create({
            'name': 'KPTEST-000002-M', 'type': 'product', 'barcode': EAN, 'default_code': 'KPTEST2'})
        self.env['stock.quant']._update_available_quantity(self.producto, self.stock, 20)
        self.tienda = self.env['res.partner'].create({'name': 'TIENDA PRUEBA KP PARCIAL'})
        self.operario = self.env['hr.employee'].create({'name': 'Operario prueba KP parcial', 'barcode': 'KPTEST-OP2'})
        self.out = self.env['stock.picking'].create({
            'picking_type_id': self.tipo_out.id, 'location_id': self.stock.id, 'location_dest_id': self.cliente.id,
            'partner_id': self.tienda.id, 'company_id': self.env.company.id,
            'move_lines': [(0, 0, {'name': self.producto.name, 'product_id': self.producto.id,
                                   'product_uom_qty': 5, 'product_uom': self.producto.uom_id.id,
                                   'location_id': self.stock.id, 'location_dest_id': self.cliente.id})]})
        self.out.action_confirm()
        self.out.action_assign()
        self.assertTrue(self.out.move_line_ids, 'La OUT de prueba no se ha reservado')

    def _leer_y_cerrar(self, n, cj='CJ999000101'):
        for i in range(n):
            self.L.leer(self.out, self.operario, EAN, 'kp-par-%s' % i)
        self.assertTrue(self.L.caja(self.out, self.operario, cj, 'kp-par-caja')['ok'])

    def test_primer_toque_ofrece_validar_incompleto(self):
        self._leer_y_cerrar(2)
        r = self.L.validar(self.out, self.operario, id_lectura='kp-par-v1')
        self.assertEqual(r['que'], 'quedan')
        self.assertTrue(r.get('incompleto'))
        self.assertNotEqual(self.out.state, 'done')

    def test_segundo_toque_valida_y_deja_el_resto_reservado(self):
        self._leer_y_cerrar(2)
        self.L.validar(self.out, self.operario, id_lectura='kp-par-v1')
        r = self.L.validar(self.out, self.operario, incompleto=True, id_lectura='kp-par-v2')
        self.assertEqual(r['que'], 'validada', r.get('msg'))
        self.assertTrue(r.get('incompleta'))
        self.assertEqual(self.out.state, 'done')
        self.assertEqual(sum(self.out.move_line_ids.mapped('qty_done')), 2)
        resto = self.out.backorder_ids
        self.assertEqual(len(resto), 1)
        self.assertEqual(sum(resto.move_lines.mapped('product_uom_qty')), 3)
        self.assertEqual(resto.state, 'assigned', 'El resto tiene que seguir reservado')
        self.assertEqual(sum(resto.move_line_ids.mapped('product_uom_qty')), 3)

    def test_sin_caja_no_valida(self):
        self.L.leer(self.out, self.operario, EAN, 'kp-par-sc')
        r = self.L.validar(self.out, self.operario, incompleto=True, id_lectura='kp-par-sc-v')
        self.assertEqual(r['que'], 'sin_caja')
        self.assertNotEqual(self.out.state, 'done')

    def test_parametro_apagado_como_antes(self):
        self.env['ir.config_parameter'].sudo().set_param('koroshi_preparacion.validar_parcial', '0')
        self._leer_y_cerrar(2)
        r = self.L.validar(self.out, self.operario, id_lectura='kp-par-off1')
        self.assertEqual(r['que'], 'quedan')
        self.assertFalse(r.get('incompleto'))
        r = self.L.validar(self.out, self.operario, incompleto=True, id_lectura='kp-par-off2')
        self.assertEqual(r['que'], 'quedan')
        self.assertNotEqual(self.out.state, 'done')

    def test_zona_no(self):
        self.env['stock.picking.batch'].create({'name': 'Z-TEST-PAR', 'picking_ids': [(6, 0, self.out.ids)]})
        self.assertFalse(self.L._parcial(self.out))

    def test_tienda_si(self):
        self.assertTrue(self.L._parcial(self.out))
