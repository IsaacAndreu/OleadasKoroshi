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
v1.6.0 (17/11/2026): la pantalla Faltante solo propone en «Prueba en», y solo acepta al leerla, una ubicacion de
  NAVE2: los huecos de los lineales y las cajas KO del muelle. Antes mandaba a coger de DEVOLUCIO_KOROSHI (y podia
  proponer CAJAS, PRUEBA o la raiz de Stock). ZONA_PICKING en models/faltante.py. Sin campos ni vistas nuevas.
v1.6.1 (17/11/2026): «muelle» es lo mismo que en koroshi_zonas: huecos MU-.. (MU2) y N1-L.. (MU1). Dentro de NAVE2
  solo vale un hueco de lineal o de muelle (con o sin caja KO): ya no se proponen las KO sueltas (recepcion sin
  ubicar) ni PERCHAS_KO. En la PDA el muelle se ve como «MU-01 P00 C1 · KO_...».
v1.7.0 (17/11/2026): RONDA EN LECTURAS Y PUESTOS A 0 DEL PICKING VIEJO (con koroshi_preparacion 3.33.0, instalar a la
  vez). La INT de la ronda se hace en Lecturas (la pantalla nueva), no en la app de codigo de barras: leer la prenda =
  esta; «No esta» = sigue pendiente (a la 2.a ronda sin aparecer, a perdidas); «La ubicacion no existe» = estado nuevo
  «Ubicacion no existe» (lo decide la oficina; Encontrado / No encontrado siguen disponibles). Se apunta el operario y
  la hora de cada linea. Informe PDF «Resultado de la ronda» (Imprimir en la lista) y menu «Resultado de las rondas».
  Menu «Pasar los puestos a 0 a faltantes»: lo puesto a 0 desde las PDA en la app de codigo de barras desde el
  1/11 (parametros koroshi_faltantes.puestos_a_cero_desde / _usuarios) pasa a faltantes de tipo «Puesto a 0», solo en
  lineales y muelle y si ahora no hay stock de ese articulo alli. No mueve stock: su ronda va de perdidas a la
  ubicacion y solo lo encontrado vuelve. Campos nuevos solo en koroshi.faltante (ronda_resultado, ronda_operario_id,
  ronda_fecha, move_cero_id; la OUT deja de ser obligatoria). Nada en albaranes, movimientos ni lineas.
v1.8.0 (20/11/2026): la tarjeta es la misma que en Lecturas y Contenedores (con koroshi_operarios 2.22.0 y
  koroshi_contenedores 1.9.0). Abierta sin venir de Lecturas, coge la tarjeta guardada en la PDA si tiene menos de
  15 min sin actividad, y la vuelve a coger al volver de una OUT; leer una tarjeta aquí la deja puesta en las otras
  pantallas. La del operario de la tarea de la OUT no se guarda. Solo JS; nada en el servidor ni en la base de datos.
v1.8.1 (20/11/2026): la tarjeta guardada vale lo que diga el parametro koroshi_operarios.minutos_tarjeta (60 por
  defecto), igual que en Contenedores. Necesita koroshi_operarios 2.22.1 (instalarla antes); sin ella se queda en 60.
v1.9.0 (23/11/2026): para koroshi_contenedores 1.13.0 (revisión general del 23/11, R1, R4 y R13). reubicar() y
  sin_alternativa() pueden pasar a Faltantes solo una parte de la línea (`cantidad`): «Cambiar» 5 -> 4 en
  Contenedores quitaba a la OUT las 5 y mandaba 5 a FALTANTE; ahora la OUT sigue con 4 allí y solo 1 va a otro hueco
  (o sale sin ella) y a FALTANTE. `origen` deja «Desde Contenedores (...)» en la nota del faltante y en el historial
  de la OUT. mejor_destino() busca el hueco más cercano con stock libre suficiente entre todos, no solo entre los 5
  primeros. La ronda (cron cada 15 min) pasa cada faltante en su savepoint con log: uno malo ya no para a los demás
  ni entra en la ronda siguiente. antes_de_archivar(): al archivar un contenedor, sus faltantes pendientes pasan a
  apuntar al hueco; con uno en una ronda abierta no se archiva. La pantalla Faltante de la PDA no cambia. Sin campos
  nuevos en ninguna tabla.
v1.10.0 (23/11/2026): revisión general del 23/11 (O4, O5, R16). Necesita koroshi_base 1.2.0 (instalarla antes). La
  tarjeta compartida sale de koroshi_base (comun.js). El campo de lectura de la pantalla Faltante ahora también lee
  cuando el lector para (las PDA no mandan Enter y la lectura podía quedarse escrita), pero solo lo que llega de golpe:
  lo que se escribe a mano («23649») sigue esperando al Enter. En las rutas, el operario que manda la PDA tiene que
  ser activo y de la compañía (si no, «Pasa otra vez tu tarjeta») y la prenda se busca como en las demás pantallas
  (también código alternativo, UPC con 0 y nombre). Sin campos nuevos.
v1.11.0 (26/11/2026): % de faltante (investigación de faltantes del 26/11, punto 7; lo que pidió Andrés el 18/11).
  Menús para responsables «% de faltante por SKU / por modelo-color / por modelo»: recibido, salido, devuelto, bajas
  y altas por ajuste, uds en FALTANTE, stock, faltante = bajas − altas + en FALTANTE, % = faltante ÷ recibido (dos
  decimales), faltas de tiendas en 7 días y última baja. Alerta por colores: vigilar ≥ 2 %, alarma ≥ 7 %, crítico
  ≥ 10 % (parámetros koroshi_faltantes.vigilar_pct / alarma_pct / critico_pct). En modelo-color y modelo no se
  compensan tallas ni colores. Tabla propia (koroshi.faltante.relativo) que llena un cron cada hora y el menú
  «Recalcular % de faltante», con SQL de solo lectura sobre movimientos y stock. Solo prendas (NNNNLLNN-…). Sin campos
  nuevos en tablas de Odoo; la PDA no cambia.
""",
    'version': '13.0.1.11.0',
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
        'data/parametros_relativo.xml',
        'views/assets.xml',
        'views/faltante_views.xml',
        'views/wizard_views.xml',
        'views/relativo_views.xml',
        'data/cron_relativo.xml',
        'views/menu.xml',
    ],
    'qweb': [
        'static/src/xml/faltantes.xml',
    ],
    'installable': True,
    'application': False,
}
