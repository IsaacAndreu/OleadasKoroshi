# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Recepción por contenedor',
    'summary': 'Recibir un contenedor marítimo caja a caja en la PDA o la tablet: caja KO_, palé A/B, prenda y '
               'cantidad, a ciegas; comparar con las IN y validarlas.',
    'description': """
Recepción de contenedores (KOROSHI > Almacén > Recepción de contenedores; e Inventario > Recepción contenedores). Sale
de la reunión en el almacén del 23/11/2026 y su diseño v6 (bin/versiones/diseno-recepciones-packing-list_2026-11-23_v6.md).

- Contenedor: la matrícula (la de la puerta; Odoo no la tiene), el muelle y las IN de KOROSHI que trae (las crea
  OdooBot por API, una por pedido; se eligen de una lista de IN abiertas por fecha prevista). Lo crea el muelle al
  llegar o la oficina antes.
- «Recepcionar»: quien recepciona escribe cuántas cajas y cuántos palés ve. Se crea un contenedor de control KO_ por
  caja (KO_ddmmaa_NNN, como koroshi_ubicaciones) y los palés que falten (PAL-01 A, PAL-01 B…, dentro de
  EFFEC/Stock/NAVE2/RECEPCION; se reutilizan). Etiquetas 4x6 para la Zebra del PC de Recepciones; la de la caja lleva
  el muelle, el día y la matrícula.
- Leer, a ciegas (no se enseña lo que traen las IN): palé y cara, caja (etiqueta KO_ o «Siguiente caja»), prenda
  (código de barras o buscador: últimos 4 números del EAN o un trozo del modelo) y cantidad. El KO_ queda dentro de su
  palé. Anular una lectura mientras no esté en stock. Contra el doble toque de la PDA: botones bloqueados hasta la
  respuesta y un token por lectura.
- Comparar (responsable): teórico de las IN contra lo leído, por modelo y talla, con dónde está cada prenda (palé /
  caja). Exportar a Excel (CSV con «;»), solo el responsable o la oficina (lleva el teórico: la lectura es a ciegas).
  En la oficina, la comparación también es una lista con filtros. El teórico se guarda (foto) antes de la primera
  validación: después Odoo suma la sobra a la demanda de la IN y ya no se vería.
- Validar (responsable: su tarjeta en «Responsables de recepción»; en la oficina, Inventario / Administrador): pone
  las líneas hechas en las IN, con destino el KO_ de cada caja, y valida cada IN con algo leído. Lo que no ha llegado
  queda en una IN pendiente (backorder), como hoy, y se enlaza sola al contenedor: es el «shipment incompleto» que se
  reabre cuando llegan las cajas («Reabrir», o un contenedor nuevo con esa IN). «Validar lo leído hasta ahora» hace
  lo mismo y la lectura sigue. Solo se validan las IN donde se han puesto líneas. Lo que sobra de un artículo que
  viene en las IN va a stock (es real) y sale como «sobra»; lo de un artículo que no viene en ninguna IN abierta NO
  pasa a stock, y el contenedor no se cierra mientras quede (anularlo o enlazar su IN). Una IN solo puede estar en una
  recepción abierta y tiene que ser de KOROSHI. Todo o nada: si algo falla, no se valida nada.

Solo tablas propias (koroshi.recepcion, .lectura, .comparacion, .teorico, .tanda, .responsable). No añade campos a
stock.picking, stock.picking.type ni stock.move.line: crea ubicaciones (KO_ y PAL-), líneas hechas de las IN y valida
la IN con lo de Odoo. No toca Contenedores, Lecturas, preparación ni S4T. Depende de koroshi_ubicaciones (nombres de
los KO_ y papel 4x6): instalar koroshi_ubicaciones antes.

Parámetro opcional koroshi_recepcion.tipo_in_id: el id del tipo de operación de las IN (si no está, se busca el de
entrada de la compañía 8 que llega a EFFEC/RECEP_KO: el 44 en producción el 23/11).

v1.0.0 (23/11/2026): primera versión (diseño v6 aprobado por Isaac el 23/11).
""",
    'version': '13.0.1.0.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'mail', 'stock', 'hr', 'koroshi_base', 'koroshi_menu', 'koroshi_ubicaciones'],
    'data': [
        'security/ir.model.access.csv',
        'data/datos.xml',
        'views/assets.xml',
        'views/etiqueta_report.xml',
        'views/recepcion_views.xml',
    ],
    'qweb': ['static/src/xml/recepcion.xml'],
    'installable': True,
    'application': False,
}
