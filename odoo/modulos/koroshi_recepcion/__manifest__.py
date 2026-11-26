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
- «Recepcionar»: quien recepciona escribe cuántos palés usa (y, si quiere, cuántas cajas hay). Se crean los palés
  que falten (PAL-01 A, PAL-01 B…, dentro de EFFEC/Stock/NAVE2/RECEPCION; se reutilizan), con etiquetas 4x6 para la
  Zebra del PC de Recepciones. Desde la 1.1.0 no se crean KO_: las cajas solo llevan la etiqueta del proveedor.
- Leer, a ciegas (no se enseña lo que traen las IN): palé y cara, caja (su nº escrito a mano y, si se quiere, el
  ORDER NUMBER de su etiqueta: si no es de ninguna IN del contenedor, avisa), prenda (código de barras o buscador:
  últimos 4 números del EAN o un trozo del modelo) y cantidad. Anular una lectura mientras no esté en stock. Contra el
  doble toque de la PDA: botones bloqueados hasta la respuesta y un token por lectura.
- Comparar (responsable): teórico de las IN contra lo leído, por modelo y talla, con dónde está cada prenda (palé /
  caja), y por caja: leídas, huecos en la numeración y cajas de otro pedido. Exportar a Excel (CSV con «;»), solo el responsable o la oficina (lleva el teórico: la lectura es a ciegas).
  En la oficina, la comparación también es una lista con filtros. El teórico se guarda (foto) antes de la primera
  validación: después Odoo suma la sobra a la demanda de la IN y ya no se vería.
- Validar (responsable: su tarjeta en «Responsables de recepción»; en la oficina, Inventario / Administrador): pone
  las líneas hechas en las IN, con destino el palé de cada caja (1.1.0), y valida cada IN con algo leído. Lo que no ha llegado
  queda en una IN pendiente (backorder), como hoy, y se enlaza sola al contenedor: es el «shipment incompleto» que se
  reabre cuando llegan las cajas («Reabrir», o un contenedor nuevo con esa IN). «Validar lo leído hasta ahora» hace
  lo mismo y la lectura sigue. Solo se validan las IN donde se han puesto líneas. Lo que sobra de un artículo que
  viene en las IN va a stock (es real) y sale como «sobra»; lo de un artículo que no viene en ninguna IN abierta NO
  pasa a stock, y el contenedor no se cierra mientras quede (anularlo o enlazar su IN). Una IN solo puede estar en una
  recepción abierta y tiene que ser de KOROSHI. Todo o nada: si algo falla, no se valida nada.

Solo tablas propias (koroshi.recepcion, .lectura, .comparacion, .teorico, .tanda, .responsable). No añade campos a
stock.picking, stock.picking.type ni stock.move.line: crea ubicaciones (KO_ y PAL-), líneas hechas de las IN y valida
la IN con lo de Odoo. El KO_ se pone después, al ordenar y ubicar. No toca Contenedores, Lecturas, preparación ni S4T. Depende de koroshi_ubicaciones (nombres de
los KO_ y papel 4x6): instalar koroshi_ubicaciones antes.

Parámetro opcional koroshi_recepcion.tipo_in_id: el id del tipo de operación de las IN (si no está, se busca el de
entrada de la compañía 8 que llega a EFFEC/RECEP_KO: el 44 en producción el 23/11).

v1.0.0 (23/11/2026): primera versión (diseño v6 aprobado por Isaac el 23/11).
v1.0.1 (23/11/2026): el campo teorico_ids (la foto del teórico) no existía en Odoo: su definición acababa en coma y
  quedaba como una tupla («Trailing comma after field definition» en el log al instalar la 1.0.0). Con la 1.0.0
  fallaban la comparación, la ficha de la oficina, cambiar las IN y validar. Solo se quita la coma; comprobar.py lo
  detecta desde ahora (E9).
v1.1.0 (26/11/2026): urgente (Isaac): la recepción ya no usa el contenedor de control KO_. Las cajas llegan solo con
  la etiqueta del proveedor (REFERENCE, ORDER NUMBER = origen de la IN, talla y uds a mano, nº de caja a rotulador).
  «Recepcionar» solo crea los palés (las cajas son opcionales, para ver huecos); no crea ni imprime KO_. Cada lectura:
  nº de caja escrito a mano (obligatorio), nº de pedido de la etiqueta (opcional; si no es el origen de ninguna IN del
  contenedor, avisa en pantalla), artículo y cantidad, en el palé y cara activos; varias líneas con el mismo nº si la
  caja lleva varios artículos; aviso si la caja ya está leída en otro palé. Al validar, el destino de las líneas hechas
  es el palé (PAL-NN A/B). Comparación, ficha y Excel: cajas leídas, huecos en la numeración y cajas con un pedido que
  no es de este contenedor. El KO_ se pondrá al ordenar y ubicar (fase 2). Las lecturas de la 1.0.x con KO_ siguen
  validándose a su KO_. Campos nuevos solo en koroshi.recepcion.lectura (caja, caja_txt, pedido, pedido_ajeno);
  contenedor_id deja de ser obligatorio.
v1.2.0 (26/11/2026): opción A de Isaac (sustituye a la 1.1.0, que no llegó a instalarse): «es quedarà en pendiente fins
  que es fiquen a llegir les prendes». Por cada caja que llega solo se apunta nº de caja (a mano), modelo (REFERENCE
  de la etiqueta: buscador de modelos o leer el EAN de una prenda y quedarse con su modelo), uds totales de la caja y
  palé/cara; el pedido de la etiqueta, opcional. NO toca stock ni las IN: no crea líneas hechas ni valida («Validar»
  lo rechaza si hay cajas por modelo). «Terminar (cerrar)» deja la recepción cerrada y las IN pendientes y libres para
  leer las prendas al ubicar; «Reabrir» vale también para las cerradas. Comparación, pantalla y Excel por modelo: cajas
  y uds llegadas frente a las uds de las IN de ese modelo (suma de sus SKU) y dónde está cada caja (palé / caja); más
  huecos en la numeración y cajas con pedido de otro contenedor. Avisos al guardar: pedido ajeno, caja ya en otro
  palé, modelo que no viene en las IN, la misma caja y modelo dos veces. Campos nuevos solo en tablas propias
  (lectura.modelo_leido, comparacion.cajas; producto_id de la lectura deja de ser obligatorio; estado «cerrada»).
v1.2.1 (26/11/2026): la 1.1.0 sí se instaló (26/11 08:57) y se está recepcionando con ella (artículo y cantidad por
  caja). La 1.2.0 no dejaba «Terminar» con prendas leídas sin pasar a stock, y sin responsables nadie puede validar:
  el contenedor se quedaba sin cerrar. Ahora se cierra igual (opción A: la IN queda pendiente) y esas lecturas cuentan
  en la comparación por modelo.
v1.3.0 (26/11/2026): primer día de uso real (Isaac): «necesito un buscador» y «que estigue lo de escribir i en intro es
  agafe». Buscador de IN al crear el contenedor o cambiar sus IN: por nombre (IN/00396 o 396), pedido (0000002172 o
  2172), referencia del proveedor (x_studio_order_remarks o nota) o principio de un código de artículo (2711JA22); lo
  marcado se guarda entre búsquedas y la matrícula escrita no se borra. En «Leer cajas» todo se escribe con el teclado
  de la PDA: Intro acepta el campo y pasa al siguiente (nº de caja → pedido → modelo → uds); en el modelo, Intro busca
  y si hay uno solo lo coge; en uds, Intro = Guardar (las uds son un campo escribible; el teclado de pantalla sigue).
  Un EAN leído en cualquiera de esos campos se toma como prenda (su modelo), como con el lector.
""",
    'version': '13.0.1.3.0',
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
