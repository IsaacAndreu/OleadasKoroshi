# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Faltantes',
    'summary': 'Pieza que no esta: buscar otra ubicacion con stock libre, cambiar la reserva y llevar la que '
               'falta a FALTANT; revision diaria',
    'description': """
Faltantes de picking en la PDA (KOROSHI, Effective Logistics).

- Pantalla "Faltante" (accion de cliente) para la PDA. Se abre desde el menu o con el boton "Faltante" de la
  pantalla de Operarios (koroshi_operarios).
  OUT + EAN -> ubicacion reservada y hasta 5 ubicaciones con stock libre, por el lineal mas cercano.
  Leer la ubicacion de donde se coge -> la linea de la OUT pasa alli (write estandar de location_id: quita la
  reserva vieja y reserva strict en la nueva, solo de stock libre) y la unidad que falta va de la ubicacion
  vieja a EFFEC/FALTANT. "No esta en ningun sitio" -> se quita la reserva de esa linea y la unidad va a
  FALTANT. Todo o nada (savepoint).
- EFFEC/FALTANT es interna pero esta fuera de EFFEC/Stock: ninguna OUT reserva alli.
- Revision diaria: Encontrado (de FALTANT a la ubicacion elegida) / No encontrado (a perdidas de
  inventario). Exportable a Excel desde la lista.
- Informe "Puestos a 0 hoy": lo que se sigue poniendo a 0 desde la PDA sin pasar por esta pantalla.

No anade campos a albaranes, movimientos, lineas, agrupaciones ni tipos de operacion, no cambia la app de
codigo de barras, no usa "Forzar disponibilidad" ni escribe stock.quant a mano.

v1.0 (09/11/2026): primera version. Solo lineas enteras sin nada leido.
v1.1 (09/11/2026): ronda de revision. Boton "Crear ronda de revision": una INT normal con los faltantes
  pendientes (de FALTANT a su ubicacion vieja, por lineal) que se hace con la app de codigo de barras.
  Cron cada 15 min: leido -> Encontrado; validada sin pedido pendiente -> No encontrado (a perdidas);
  con pedido pendiente -> sigue en la INT nueva.
v1.2 (09/11/2026): con KOROSHI Operarios v2, el boton Faltante de la pantalla de Operarios ya trae la OUT que esta
  haciendo el operario y el operario: solo hay que leer el EAN.
v1.3 (09/11/2026): los faltantes se marcan al final de la OUT sin leer el EAN: lista de lo que queda por coger
  (referencia, color / talla, ubicacion, uds), se marcan una o varias, una ubicacion recomendada por cada una y
  "Tampoco esta aqui" -> FALTANT. Leer la ubicacion donde se esta elige la linea. Lineas con una parte leida: solo se
  toca lo que falta. Al acabar, si no queda nada por coger, la OUT se valida sola (validacion normal de Odoo) o con
  "Validar OUT"; si Odoo pregunta por el pedido pendiente, lo pregunta la PDA (parametros
  koroshi_faltantes.validar_sola y koroshi_faltantes.pedido_pendiente). Agrupaciones Z-: no se validan solas.
""",
    'version': '13.0.1.3.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'hr', 'stock', 'stock_picking_batch', 'stock_barcode', 'koroshi_operarios'],
    'data': [
        'security/ir.model.access.csv',
        'data/ubicacion.xml',
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
