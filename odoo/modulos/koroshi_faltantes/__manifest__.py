# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Faltantes',
    'summary': 'Pieza que no esta: buscar otra ubicacion con stock libre, cambiar la reserva y llevar la que '
               'falta a FALTANTE; revision diaria',
    'description': """
Faltantes de picking en la PDA (KOROSHI, Effective Logistics).

- Pantalla "Faltante" (accion de cliente) para la PDA. Se abre desde el menu o con el boton "Faltante" de la
  pantalla de Operarios (koroshi_operarios).
  OUT + EAN -> ubicacion reservada y hasta 5 ubicaciones con stock libre, por el lineal mas cercano.
  Leer la ubicacion de donde se coge -> la linea de la OUT pasa alli (write estandar de location_id: quita la
  reserva vieja y reserva strict en la nueva, solo de stock libre) y la unidad que falta va de la ubicacion
  vieja a EFFEC/FALTANTE. "No esta en ningun sitio" -> se quita la reserva de esa linea y la unidad va a
  FALTANTE. Todo o nada (savepoint).
- EFFEC/FALTANTE es interna pero esta fuera de EFFEC/Stock: ninguna OUT reserva alli.
- Revision diaria: Encontrado (de FALTANTE a la ubicacion elegida) / No encontrado (a perdidas de
  inventario). Exportable a Excel desde la lista.
- Informe "Puestos a 0 hoy": lo que se sigue poniendo a 0 desde la PDA sin pasar por esta pantalla.

No anade campos a albaranes, movimientos, lineas, agrupaciones ni tipos de operacion, no cambia la app de
codigo de barras, no usa "Forzar disponibilidad" ni escribe stock.quant a mano.

v1.0 (09/11/2026): primera version. Solo lineas enteras sin nada leido.
v1.1 (09/11/2026): ronda de revision. Boton "Crear ronda de revision": una INT normal con los faltantes
  pendientes (de FALTANTE a su ubicacion vieja, por lineal) que se hace con la app de codigo de barras.
  Cron cada 15 min: leido -> Encontrado; validada sin pedido pendiente -> No encontrado (a perdidas);
  con pedido pendiente -> sigue en la INT nueva.
v1.2 (09/11/2026): con KOROSHI Operarios v2, el boton Faltante de la pantalla de Operarios ya trae la OUT que esta
  haciendo el operario y el operario: solo hay que leer el EAN.
v1.3 (09/11/2026): los faltantes se marcan al final de la OUT sin leer el EAN: lista de lo que queda por coger
  (referencia, color / talla, ubicacion, uds), se marcan una o varias, una ubicacion recomendada por cada una y
  "Tampoco esta aqui" -> FALTANTE. Leer la ubicacion donde se esta elige la linea. Lineas con una parte leida: solo se
  toca lo que falta. Al acabar, si no queda nada por coger, la OUT se valida sola (validacion normal de Odoo) o con
  "Validar OUT"; si Odoo pregunta por el pedido pendiente, lo pregunta la PDA (parametros
  koroshi_faltantes.validar_sola y koroshi_faltantes.pedido_pendiente). Agrupaciones Z-: no se validan solas.
v1.3.1 (10/11/2026): la ubicacion se llama FALTANTE (antes FALTANT; misma ubicacion). Al validar despues de los
  faltantes, sin pedido pendiente y sin preguntar (parametro pedido_pendiente = no). Cada faltante deja una nota en
  el historial de la OUT (que, de donde, a donde, operario).
v1.4.0 (11/11/2026): mismo aspecto que Preparacion en Lecturas. La UBICACION va en grande y en negro (hueco y KO en la
  misma linea); la referencia del articulo, debajo y mas pequena. «Prueba en» = etiqueta negra; donde no esta, tachada.
  En PDA sin la barra de menus de Odoo.
v1.4.1 (11/11/2026): «Prueba en» se veia gris sobre negro (regla antigua); ahora en blanco. Debajo de la ubicacion,
  el nombre del articulo una sola vez (no el EAN ni el codigo repetido).
v1.5.0 (16/11/2026): auditoria 13/11, fase 6 (pasar a koroshi_base). La hora del almacen sale de koroshi_base.comun
  (antes, su propia ZONA_HORARIA). Arregla «Puestos a 0 hoy» el dia del cambio de hora: las 00:00 se sacaban
  cambiando la hora de «ahora» con el desfase de ahora, y quedaban una hora corridas. Sin campos ni vistas nuevas.
  Depende de koroshi_base. La pantalla Faltante de la PDA no cambia.
""",
    'version': '13.0.1.5.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'hr', 'stock', 'stock_picking_batch', 'stock_barcode', 'koroshi_base', 'koroshi_operarios'],
    'data': [
        'security/ir.model.access.csv',
        'data/ubicacion.xml',
        'data/ubicacion_v131.xml',
        'data/cron.xml',
        'data/parametros.xml',
        'views/assets.xml',
        'views/faltante_views.xml',
        'views/wizard_views.xml',
        'views/menu.xml',
    ],
    'qweb': [
        'static/src/xml/faltantes.xml',
    ],
    'installable': True,
    'application': False,
}
