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

Solo lee: no cambia nada en Odoo.
""",
    'version': '13.0.1.13.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'stock', 'stock_picking_batch'],
    'data': [
        'views/assets.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
}
