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
v1.4.0 (26/11/2026): Isaac: «tenir lo total i q vaiguen contant» (incluye la 1.3.0, que no llegó a instalarse). Total
  de cajas automático: suma de s4t_packages del packing list de S4T (s4t.packing.feed, solo se LEE; nunca se escribe
  en él) de los pedidos de las IN (feed.name = origin); un pedido con varios feed cuenta una vez, y se avisa si está
  marcado duplicado o si un pedido no tiene packing. Si se escriben las cajas a mano, manda lo escrito y se enseña
  también el del packing. Contador «leídas / total · faltan N» siempre visible al leer y en la ficha; los huecos de
  numeración van de 1 al total. No depende del módulo de S4T: sin él, el total es el escrito.
v1.4.1 (26/11/2026): «+1 caja» (Isaac: «si fem X modelo el escribim 1 vegada i dsp es anar sumant»; incluye la 1.3.0
  y la 1.4.0, que no se instalaron). Con el modelo activo puesto una vez (escrito + Intro, buscado o leyendo una
  prenda), cada toque del botón grande guarda una caja de ese modelo en el palé activo (si lo hay), sin nº ni uds;
  «−1» anula el último «+1». 2 s entre toques y un token por toque (doble toque). Contadores: «modelo: N cajas» y
  «leídas / total · faltan N». Comparación y Excel por modelo: cajas contadas y cajas del packing de S4T con ese
  modelo (caja física = lo de s4t_line_id antes del guion; solo lectura). Lectura detallada sin cambios. Lectura:
  campo «rapida» y palet_id deja de ser obligatorio; comparación: cajas_packing.
v1.5.0 (26/11/2026): Isaac: las etiquetas se imprimen en la Zebra de Expediciones por la cola de koroshi_impresion
  (código EXP1; otro, con el parámetro koroshi_recepcion.impresora). Depende de koroshi_impresion (ya instalado). En la
  PDA, «🖨 Etiquetas (última tanda)», «🖨 Etiquetas de los palés» (ficha) y «🖨 Etiqueta de PAL-NN X» (al leer, el palé
  tocado) mandan a la cola y dicen si la impresora no está conectada. Como los PAL-NN se reutilizan, «Recepcionar» no
  hace tanda de los que ya existen: «Etiquetas de los palés» hace una tanda con PAL-01 A … PAL-<palés> B de esta
  recepción (creando los que falten). En la oficina, «A la Zebra» y «PDF» en cada tanda y «Etiquetas de los palés a la
  Zebra» arriba. El aviso queda en el historial.
v1.6.0 (26/11/2026): Isaac: aprovechar lo que Mayte deja en cada IN (solo lectura). Los contenedores salen del
  carrier_tracking_ref de las IN marcadas (se pueden corregir; el muelle sigue siendo opcional). El packing list en
  Excel adjunto a la IN (o a su IN de origen) se lee en una tabla nueva koroshi.recepcion.pl: modelo, color, nº de
  caja (la numeración empieza en cada modelo: caja física = modelo + nº), tallas y uds, medidas y CBM por caja y por
  unidad (para el diseño futuro de «caja llena por volumen»). Se carga sola al crear o cambiar las IN, y con «↻
  Packing list». En «+1 caja» se puede poner el nº: dice qué lleva («caja 7 de JA12: 40 L»), cuenta las uds del PL
  y avisa si ese nº no está en el PL del modelo o ya se contó. «Faltan (nº)» por modelo en la PDA, y «Cajas en el
  PL» y «Nº que faltan» en la comparación y su Excel. Sin campos nuevos en stock.picking; no escribe en S4T.
v1.6.1 (26/11/2026): Isaac: el buscador de IN encuentra por contenedor (carrier_tracking_ref, varios con «+»;
  «MIEU4099960», «4099960» o un trozo valen) y, si no sale ninguna, dice que el contenedor no está en ninguna IN
  abierta; al marcar la IN se rellenan sus contenedores (corregibles). El buscador ya no mira la referencia del
  proveedor ni el BL, y la PDA deja de mostrarlos (campo y «Ref.»); en la ficha, la columna pasa a «Contenedores».
  Busca por contenedor, nº de IN, pedido y modelo. En la oficina el campo referencia sigue igual. Sin cambios en la BD.
v1.7.0 (26/11/2026): Isaac: (1) el modelo se autocompleta al escribir (a los 3 caracteres, sin Intro): primero los
  de las IN y del packing list de la recepción, después los de Odoo; tocar uno lo pone y, si solo queda uno, se pone
  solo. Un modelo que solo está en el PL también vale. (2) Vuelve el contenedor de control KO_ por caja: «🏷 Etiquetas
  KO» en la ficha crea N KO_ del día (hasta 500 de una vez, como en la 1.0.x), los apunta a la recepción y manda la
  tanda a la Zebra (EXP1); si la impresora falla, quedan creados y se reimprimen con «Etiquetas (última tanda)». En
  «Leer cajas» se lee el KO pegado en la caja (dice si ya tiene algo), el modelo y las uds; con el nº a mano y PL,
  propone las uds del PL. Con KO, el nº a mano y el palé son opcionales; la caja física es el KO. Avisa si el mismo
  KO lleva otro modelo. El nº a mano y «+1 caja» siguen como modo rápido. No toca stock (opción A: la IN queda
  pendiente). Sin campos nuevos en tablas compartidas; koroshi.recepcion.lectura.contenedor_id ya existía.
""",
    'version': '13.0.1.7.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'mail', 'stock', 'hr', 'koroshi_base', 'koroshi_menu', 'koroshi_ubicaciones',
                'koroshi_impresion'],
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
