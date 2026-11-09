# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Operarios',
    'summary': 'Cola de pedidos por operario en la PDA: tarjeta una vez, el siguiente pedido se abre solo; tiempo y uds por persona',
    'description': """
Productividad por operario sin usuarios de Odoo (KOROSHI, Effective Logistics).

- Cada operario es un empleado (hr.employee) con un codigo en "ID de credencial" (OP0001...).
  No es un usuario de Odoo. Asistente para crear muchos de golpe y tarjetas con "Imprimir Identificacion".
- Pantalla de lecturas dentro de Odoo (Inventario > KOROSHI Operarios > Lecturas (PDA)). Se pone como
  "Accion inicial" del usuario de la PDA: sale al entrar.
  tarjeta + OUT = empieza y abre la OUT en la app de codigo de barras; al validar, la app vuelve sola a esta
  pantalla. tarjeta + "Dejar aqui" = lo deja a medias. Si empieza otro pedido, el anterior se cierra solo.
- Si la OUT es de una agrupacion de zonas (Z-...), la tarea es de toda la agrupacion y se abre en
  "procesar agrupacion".
- Cada 5 minutos se cierran solas las tareas cuyo pedido o agrupacion ya esta validado. A medianoche lo
  que sigue abierto queda "Sin cerrar".
- Uds de cada tarea = uds leidas del pedido al cerrar - uds leidas al empezar.
- Informes: tareas por operario y dia (lista, tabla dinamica, grafico) y OUT validadas hoy sin operario.

Solo escribe en sus propias tablas y en hr.employee (crear operarios). No anade campos a albaranes,
movimientos, agrupaciones ni tipos de operacion, y no cambia la app de codigo de barras (la llama igual
que su menu: /stock_barcode/scan_from_main_menu y start_batch_processing).

v1.0 (09/11/2026): primera version (pagina suelta /koroshi/operarios).
v1.1 (09/11/2026): la pantalla es una accion de cliente de Odoo: abre la OUT en la app de codigo de barras
y al validar se vuelve a ella. Fuera la pagina suelta.
v1.2 (09/11/2026): los nombres con la productividad (Tareas, Productividad, Operarios, Crear operarios) solo los ve
el grupo "KOROSHI Operarios: ver productividad" (los usuarios de la PDA son responsables de inventario y los veian).
Informe diario por email a las 17:00 (parametros koroshi_operarios.informe_*) y menu "Enviar informe de hoy ahora".
v2.0 (09/11/2026): cola de pedidos por operario. Tarjeta una vez (la PDA se queda con el operario hasta "Salir");
la PDA abre sola el siguiente pedido y, al validar, el siguiente. "Saltar" con motivo (oficina, final de su cola o fin
de turno: sigue suyo y el primero al dia siguiente). Reparto de hoy: modo automatico, por pasillos o solo manual;
siempre primero lo asignado a mano (Accion > Asignar a operario en albaranes y agrupaciones). Tablas nuevas
koroshi.operario.asignacion / dia / tramo / motivo. Sin tarjeta la OUT se abre igual pero no cuenta.
v2.1 (09/11/2026): reparto por bloques. Reparto de hoy: operarios de hoy, "Repartir ahora" (llena la cola de cada uno
hasta N pedidos) e "Imprimir etiquetas" (por persona: hoja con su nombre + sus etiquetas de zona en orden; reserva las
matriculas con la accion "KOROSHI Etiquetas zona" de siempre). Linea en naranja cuando le quedan pocos. Con la cola
vacia la PDA ya no da otra sola, salvo que se encienda "darle otra solo (sin etiqueta)".
""",
    'version': '13.0.2.1.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'mail', 'hr', 'stock', 'stock_picking_batch', 'stock_barcode'],
    'data': [
        'security/grupo.xml',
        'security/ir.model.access.csv',
        'data/categoria.xml',
        'data/motivos.xml',
        'data/cron.xml',
        'data/informe.xml',
        'views/assets.xml',
        'views/tarea_views.xml',
        'views/wizard_views.xml',
        'views/reparto_views.xml',
        'views/etiquetas_report.xml',
        'views/menu.xml',
    ],
    'qweb': [
        'static/src/xml/operarios.xml',
    ],
    'installable': True,
    'application': False,
}
