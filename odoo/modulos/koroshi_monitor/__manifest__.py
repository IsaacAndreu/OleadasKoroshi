# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Monitor zonas',
    'summary': 'Pantalla en directo de como van las agrupaciones de picking por zonas (Z-ddmm-D1..D5, ZX)',
    'description': """
Monitor de las agrupaciones por zonas de KOROSHI.

Menu Inventario > Operaciones > Monitor zonas. Ensena, para la agrupacion elegida
(por defecto la ultima Z-...): unidades leidas y pendientes por zona, OUT hechas /
cogiendose / sin empezar, el cuadro de cada tienda en cada zona y la lista de OUT
por zona con lineales, huecos y horas. Se refresca solo cada minuto.

v1.1: tambien modo "Tiendas <dia>" para cuando se coge una OUT por pedido (sin zonas):
ritmo del equipo, hora prevista de fin, uds por hora y lo que ha tardado cada OUT.

v1.2: en "Tiendas", cajas cerradas por OUT, hace cuanto se cerro la ultima (aviso si una
OUT lleva mas de 20 min sin cerrar caja) y personas cogiendo ahora.

v1.3: "Personas y horas" para cualquier dia (tambien dias anteriores y zonas): personas,
horas-persona, horas de reloj, uds por hora-persona, uds por persona y segundos por prenda,
estimados por las cajas cerradas. Menu en la barra de Inventario, al lado de KOROSHI KPI.

v1.4: OUT "Parcial" (ya cogido todo lo que hay, faltan prendas sin stock) con su color y "Sin stock"
(en espera); el avance y la hora de fin cuentan solo lo que hay en stock; lista de faltantes por OUT
y articulo al final de la pantalla.

v1.5: los pedidos pendientes en espera (sin stock) no salen (solo se cuentan); columna "Sin stock" en
vez de numeros negativos al lado de lo leido; fuera la tarjeta de faltan de arriba.
v1.6: fuera la lista de faltantes de abajo y la columna "Sin stock": las faltas estan en
KOROSHI KPI > Faltas por dia (modulo koroshi_kpi v1.3).
v1.7: tiendas: franja grande arriba (% hecho, hora de fin, uds por coger), filas con color segun el estado,
"Sin empezar" y "Hechas" plegadas, y Modo pantalla (sin menu de Odoo, letra grande) para la pantalla del almacen.
v1.8: las OUT que ya tienen cogido todo lo que hay (solo faltan prendas sin stock o no encontradas) o que llevan mas de
20 min sin cerrar caja salen como HECHAS (sin validar, con lo que falta), no como "parcial".
v1.9: R1 y R2 en pantallas separadas; zonas con 8 o mas zonas (D6-D8, ZX1...) sin arrastrar: pagina mas ancha, zonas en orden
y la matriz tienda x zona con casillas compactas (uds leidas/total; la OUT y el estado al pasar el raton).
Tiendas con todas sus OUT hechas: lista "listas para juntar" y su fila en gris en la matriz (no cambia de sitio).
Zonas a todo el ancho de la pantalla, casillas que llenan la columna.
v1.10: tercer estado de la tienda en la matriz: con la etiqueta del transportista (numero de seguimiento) en todas
sus OUT = terminada, fila en azul oscuro. Leyenda de colores encima de la matriz.
v1.11: cada casilla de la matriz (y el numero de OUT de las listas) se puede pulsar: abre la OUT en otra pestana.
v1.12: el clic abre la OUT dentro de Odoo (migas para volver al monitor): funciona tambien en la PDA; Ctrl+clic en otra pestana.
v1.13: las migas de pan dicen 'Monitor picking' (antes salia sin nombre).
v1.14: zonas: en cada casilla de la matriz, debajo de las uds, los bultos (cajas cerradas) de esa OUT; columna
Bultos por tienda y bultos en el resumen y la lista de cada zona. En rojo si la OUT esta hecha y los bultos de
Odoo (los que van a XPO) no coinciden con las cajas cerradas.

v1.17: en el modo Tiendas se puede filtrar por estado y transporte, buscar por tienda/OUT/pedido/etiqueta,
ordenar con doble clic en los encabezados y ver transportista y etiqueta. La gráfica de unidades por hora
desglosa el total por OUT con un color estable para cada una.

v1.17.1: las OUT hechas con transportista o etiqueta aparecen con fondo azul y el monitor ocupa todo el ancho.

v1.18: operarios por codigo (OP1, OP2...), nunca por nombre, si esta instalado koroshi_operarios: columna Operario
en Tiendas y zonas y tabla Operarios (que coge ahora, uds, minutos, u/h del dia). Sin ese modulo, igual que antes.
v1.18.2: una caja usada en dos OUT (koroshi_caja_existente) cuenta solo en su OUT duena (K8 10/11: salian 6 bultos).
v1.18.1: OUT o agrupacion ya validada = operario acabado al momento, sin esperar al cron de cierre (5 min).

v1.19: pantalla "Consulta de envios" para oficina, separada en Tiendas y Web. Busca por pedido, OUT, tienda o
expedicion; agrupa las OUT, compara bultos declarados con cajas CJ distintas y permite copiar o compartir. Descarga
Excel por fechas y transportista: Tiendas (XPO SAS / GLS) y Web (GLS / SEUR).
v1.19.1: en zonas, cada OUT abierta cuenta como una persona en "Personas y horas"; ya no se cuenta una persona
por zona.
v1.19.2: boton "Consulta envios / Excel" dentro de la cabecera del Monitor picking.
v1.19.3: corrige el error movil "this.$el.swipe is not a function" de los Kanban de Odoo 13: carga
TouchSwipe antes y protege Inventario si el plugin no estuviera disponible.
v1.19.4: una OUT solo cuenta como persona durante los 5 minutos posteriores a su ultima actividad. Los huecos
largos por picos o faltantes ya no inflan personas ni horas-persona.
v1.19.5: el Excel Web contiene solo las seis columnas pedidas. En Tiendas GLS solo salen expediciones
con etiqueta generada y se cuentan como maximo cinco etiquetas por pedido; las cajas restantes van juntadas.
v1.19.6: boton visible para volver de Consulta de envios al Monitor picking.
v1.19.7: tabla Operarios: con dos operarios en la misma OUT (koroshi_operarios v2.5 / preparacion v3.4) cada uno
cuenta en curso solo sus uds, no las del compañero. Con versiones anteriores, igual que antes.
v1.20.0: Consulta de envios. Excel de Tiendas por la fecha de la ETIQUETA del transportista (adjunto
LabelXPO_... / gls_label_... de la OUT), no por la de validacion: el 11 -> 11 saca todo lo etiquetado el 11 aunque
el pedido sea del 9 o del 10. Columna "Fecha etiqueta" y "Observacion". Recuadro "Anadir un pedido u OUT al Excel
de un dia" (Tiendas y Web): se guarda en el modelo nuevo koroshi.envio.extra, sale en el Excel de ese dia junto al
resto y se puede quitar. Textos que estaban en catalan, en castellano.
v1.20.1: "Personas y horas" en zonas: cada OUT es una persona desde que empieza cada caja hasta que la cierra. Los
huecos entre cajas de hasta 20 min (PARADA_MIN) cuentan como trabajo y la primera caja empieza el tiempo tipico
entre cajas antes (mediana del dia). Con la ventana fija de 5 min se perdia ese tiempo y las u/h por persona salian
infladas (Z-1111: 167 u/h en vez de ~114). Tiendas, igual que antes.

Solo lee pedidos y expediciones: lo unico que escribe son las OUT anadidas a mano (koroshi.envio.extra).
""",
    'version': '13.0.1.20.1',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'stock', 'stock_picking_batch', 'koroshi_warehouse_map'],
    'data': [
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
}
