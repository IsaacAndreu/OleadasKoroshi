# -*- coding: utf-8 -*-
# v3.29: la PDA vuelve a mandar una petición con el MISMO id_lectura cuando no le llega la respuesta (Odoo lento, red
# que se corta). Estos tests comprueban que leer, caja, mover, deshacer y validar no se hacen dos veces, que validar
# contesta «validada» si ya lo está, la restricción única de «OUT a dos» y lo que se apunta como rechazado de cola.
# Se pasan en una base de PRUEBAS (nunca en producción):
#   odoo-bin -d <base_de_pruebas> -u koroshi_preparacion --test-enable --test-tags /koroshi_preparacion --stop-after-init
import inspect
from unittest.mock import patch

import psycopg2

from odoo.tests import common, tagged
from odoo.tools import mute_logger

LECTURA = 'odoo.addons.koroshi_preparacion.models.lectura.COMPANY_ID'
AGRUPACION = 'odoo.addons.koroshi_preparacion.models.agrupacion.COMPANY_ID'


@tagged('post_install', '-at_install', 'koroshi_preparacion')
class TestIdempotencia(common.TransactionCase):

    def setUp(self):
        super(TestIdempotencia, self).setUp()
        # la lógica solo prepara OUT de la compañía 8 (producción): en la base de pruebas, la compañía de la prueba
        for destino in (LECTURA, AGRUPACION):
            p = patch(destino, self.env.company.id)
            p.start()
            self.addCleanup(p.stop)
        self.L = self.env['koroshi.preparacion.lectura']
        almacen = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        self.tipo_out = almacen.out_type_id
        self.stock = almacen.lot_stock_id
        self.cliente = self.env.ref('stock.stock_location_customers')
        self.producto = self.env['product.product'].create({
            'name': 'KPTEST-000001-M', 'type': 'product', 'barcode': '8445962999991', 'default_code': 'KPTEST1'})
        self.env['stock.quant']._update_available_quantity(self.producto, self.stock, 20)
        self.tienda = self.env['res.partner'].create({'name': 'TIENDA PRUEBA KP'})
        self.operario = self.env['hr.employee'].create({'name': 'Operario prueba KP', 'barcode': 'KPTEST-OP1'})
        self.out = self._out(3)

    def _out(self, uds):
        out = self.env['stock.picking'].create({
            'picking_type_id': self.tipo_out.id, 'location_id': self.stock.id, 'location_dest_id': self.cliente.id,
            'partner_id': self.tienda.id, 'company_id': self.env.company.id,
            'move_lines': [(0, 0, {'name': self.producto.name, 'product_id': self.producto.id,
                                   'product_uom_qty': uds, 'product_uom': self.producto.uom_id.id,
                                   'location_id': self.stock.id, 'location_dest_id': self.cliente.id})]})
        out.action_confirm()
        out.action_assign()
        self.assertTrue(out.move_line_ids, 'La OUT de prueba no se ha reservado')
        return out

    def _leidas(self, out=None):
        return sum((out or self.out).move_line_ids.mapped('qty_done'))

    def _con_cajas(self):
        put = type(self.env['stock.picking']).put_in_pack
        if 'package_name' not in inspect.signature(put).parameters:
            self.skipTest('put_in_pack(package_name) es de stock_barcode_optimization: no está en esta base')

    # ------------------------------------------------------------ leer
    def test_leer_dos_veces_el_mismo_id_cuenta_una(self):
        r1 = self.L.leer(self.out, self.operario, '8445962999991', 'kp-leer-1')
        r2 = self.L.leer(self.out, self.operario, '8445962999991', 'kp-leer-1')
        self.assertTrue(r1['ok'])
        self.assertEqual(r2['que'], 'repetida')
        self.assertTrue(r2['ok'])
        self.assertEqual(self._leidas(), 1)
        self.L.leer(self.out, self.operario, '8445962999991', 'kp-leer-2')
        self.assertEqual(self._leidas(), 2)

    # ------------------------------------------------------------ deshacer
    def test_deshacer_dos_veces_el_mismo_id_deshace_una(self):
        self.L.leer(self.out, self.operario, '8445962999991', 'kp-d-1')
        self.L.leer(self.out, self.operario, '8445962999991', 'kp-d-2')
        r1 = self.L.deshacer(self.out, self.operario, 'kp-deshacer-1')
        r2 = self.L.deshacer(self.out, self.operario, 'kp-deshacer-1')
        self.assertTrue(r1['ok'])
        self.assertEqual(r2['que'], 'repetida')
        self.assertEqual(self._leidas(), 1)

    # ------------------------------------------------------------ caja
    def test_caja_dos_veces_el_mismo_id_cierra_una(self):
        self._con_cajas()
        self.L.leer(self.out, self.operario, '8445962999991', 'kp-c-1')
        r1 = self.L.caja(self.out, self.operario, 'CJ999000001', 'kp-caja-1')
        r2 = self.L.caja(self.out, self.operario, 'CJ999000001', 'kp-caja-1')
        self.assertTrue(r1['ok'], r1.get('msg'))
        self.assertEqual(r2['que'], 'repetida')
        # la repetida trae la caja y sus uds (la PDA enseña el número aunque no le llegara la primera respuesta)
        self.assertEqual(r2['caja'], 'CJ999000001')
        self.assertEqual(r2['uds'], 1)
        self.assertEqual(len(self.out.move_line_ids.mapped('result_package_id')), 1)

    def test_caja_rechazada_reintento_con_otro_id(self):
        # sin nada fuera de caja Odoo no la cierra; la PDA (v3.29) para la cola y reintenta con un id NUEVO
        self._con_cajas()
        r = self.L.caja(self.out, self.operario, 'CJ999000002', 'kp-caja-r1')
        self.assertFalse(r['ok'])
        self.L.leer(self.out, self.operario, '8445962999991', 'kp-c-2')
        r2 = self.L.caja(self.out, self.operario, 'CJ999000002', 'kp-caja-r2')
        self.assertTrue(r2['ok'], r2.get('msg'))

    # ------------------------------------------------------------ mover
    def test_mover_dos_veces_el_mismo_id_mueve_una(self):
        self._con_cajas()
        self.L.leer(self.out, self.operario, '8445962999991', 'kp-m-1')
        self.L.leer(self.out, self.operario, '8445962999991', 'kp-m-2')
        self.assertTrue(self.L.caja(self.out, self.operario, 'CJ999000003', 'kp-m-caja')['ok'])
        ml = self.out.move_line_ids.filtered('result_package_id')[:1]
        r1 = self.L.mover_caja(self.out, self.operario, ml.id, 1, 'FUERA', 'kp-mover-1')
        r2 = self.L.mover_caja(self.out, self.operario, ml.id, 1, 'FUERA', 'kp-mover-1')
        self.assertTrue(r1['ok'], r1.get('msg'))
        self.assertEqual(r2['que'], 'repetida')
        en_caja = sum(self.out.move_line_ids.filtered('result_package_id').mapped('qty_done'))
        self.assertEqual(en_caja, 1)   # salió 1 de las 2, no las 2

    # ------------------------------------------------------------ validar
    def test_validar_dos_veces_el_mismo_id(self):
        self._con_cajas()
        for i in range(3):
            self.L.leer(self.out, self.operario, '8445962999991', 'kp-v-%s' % i)
        self.assertTrue(self.L.caja(self.out, self.operario, 'CJ999000004', 'kp-v-caja')['ok'])
        r1 = self.L.validar(self.out, self.operario, id_lectura='kp-validar-1')
        self.assertEqual(r1['que'], 'validada', r1.get('msg'))
        self.assertEqual(self.out.state, 'done')
        r2 = self.L.validar(self.out, self.operario, id_lectura='kp-validar-1')
        self.assertTrue(r2['ok'])
        self.assertEqual(r2['que'], 'validada')
        # otro id (el operario pulsa Validar otra vez): también «validada», no un error
        r3 = self.L.validar(self.out, self.operario, id_lectura='kp-validar-2')
        self.assertTrue(r3['ok'])
        self.assertEqual(r3['que'], 'validada')

    # ------------------------------------------------------------ OUT a dos
    def test_equipo_pareja_unica(self):
        otro = self.env['hr.employee'].create({'name': 'Ayudante prueba KP'})
        Equipo = self.env['koroshi.preparacion.equipo']
        Equipo.create({'picking_id': self.out.id, 'titular_id': self.operario.id, 'ayudante_id': otro.id})
        with mute_logger('odoo.sql_db'), self.assertRaises(psycopg2.IntegrityError):
            with self.env.cr.savepoint():
                Equipo.create({'picking_id': self.out.id, 'titular_id': self.operario.id, 'ayudante_id': otro.id})
        # otra pareja en la misma OUT sí
        tercero = self.env['hr.employee'].create({'name': 'Otro ayudante prueba KP'})
        Equipo.create({'picking_id': self.out.id, 'titular_id': self.operario.id, 'ayudante_id': tercero.id})

    def test_grupo_no_duplica(self):
        otro = self.env['hr.employee'].create({'name': 'Ayudante prueba KP 2'})
        equipo = self.operario | otro
        g1 = self.L._grupo(self.out, equipo)
        g2 = self.L._grupo(self.out, equipo)
        self.assertEqual(g1, g2)
        self.assertEqual(self.env['koroshi.preparacion.equipo'].search_count([('picking_id', '=', self.out.id)]), 1)

    # ------------------------------------------------------------ estado ligero
    def test_estado_ligero_sin_lo_fijo(self):
        ligero = self.L.estado(self.out, self.operario, ligero=True)
        entero = self.L.estado(self.out, self.operario)
        for clave in ('out', 'tipos_caja', 'alarma_min', 'alarma_horario'):
            self.assertNotIn(clave, ligero)
            self.assertIn(clave, entero)
        for clave in ('lineas', 'pedidas', 'leidas', 'sin_caja', 'cajas', 'a_dos', 'out_estado'):
            self.assertIn(clave, ligero)
        self.assertEqual(ligero['out_estado'], self.out.state)

    # ------------------------------------------------------------ rechazadas de cola
    def test_rechazo_apuntado_una_vez_y_diferido(self):
        Dif = self.L.with_context(kp_diferida=True)
        r1 = Dif.apuntar_rechazo(self.out, self.operario, 'leer', '8445962999991', 'La OUT ya está validada.',
                                 'kp-rech-1')
        r2 = Dif.apuntar_rechazo(self.out, self.operario, 'leer', '8445962999991', 'La OUT ya está validada.',
                                 'kp-rech-1')
        self.assertTrue(r1)
        self.assertFalse(r2)
        apuntes = self.L.search([('id_lectura', '=', 'kp-rech-1')])
        self.assertEqual(len(apuntes), 1)
        self.assertTrue(apuntes.diferida)
        self.assertEqual(apuntes.resultado, 'error')

    def test_lectura_de_out_cancelada_no_cuenta(self):
        self.out.action_cancel()
        with self.assertRaises(Exception):
            self.L.leer(self.out, self.operario, '8445962999991', 'kp-cancelada-1')
        self.assertEqual(self._leidas(), 0)

    # ------------------------------------------------------------ agrupación: OUT vivas una vez por petición
    def test_vivas_una_vez_por_peticion(self):
        lote = self.env['stock.picking.batch'].create({'name': 'Z-TEST-D1', 'picking_ids': [(6, 0, self.out.ids)]})
        A = self.env['koroshi.preparacion.agrupacion'].con_memo()
        Clase = type(A)
        llamadas = []
        original = Clase._caja_tienda

        def contar(this, picking):
            llamadas.append(picking.id)
            return original(this, picking)
        with patch.object(Clase, '_caja_tienda', contar):
            v1 = A._vivas(lote)
            v2 = A._vivas(lote)
            self.assertEqual(v1, v2)
            self.assertEqual(len(llamadas), 1)
            A._olvidar()
            A._vivas(lote)
            self.assertEqual(len(llamadas), 2)
