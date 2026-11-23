# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Informe de productividad',
    'summary': 'Correo diario, semanal y mensual de productividad del almacén KOROSHI para la responsable',
    'description': """
Correo automatico de productividad del almacen KOROSHI (Effective Logistics NAU-2).

- Diario (17:00): uds y pedidos del dia contra el mismo dia de la semana pasada, operarios de hoy (pedidos, uds, tiempo,
  u/h, parado y contra sus ultimos 5 dias), mejores de los ultimos 5 dias y records, tiempos parados (pedidos abiertos
  sin leer y huecos de 15 min o mas), faltas del dia y esta semana contra la pasada.
- Semanal (lunes 08:00): la semana anterior contra la de antes. Mensual (dia 1, 08:00): el mes anterior contra el de
  antes.
- Destinatarios, horas y que se manda en Configuracion > KOROSHI > Ajustes KOROSHI. Sin correos no se manda nada.
- Informes > KOROSHI > Informe de productividad (correo): verlo sin mandarlo, mandarlo ahora y la tabla por operario
  y dia.

Lee tareas (koroshi_operarios), lecturas (koroshi_preparacion), fichas KPI y faltas (koroshi_kpi) y albaranes. Escribe
solo en su tabla, sus parametros y el correo; antes del diario recalcula la ficha KPI y las faltas del dia (lo mismo
que el boton Recalcular de la ficha).

v1.0.0 (12/11/2026): primera version.
v1.0.1 (13/11/2026): la vista de Ajustes se engancha al campo de KPI (Odoo 13 no deja usar string en un xpath; la
1.0.0 no se instalaba).
v1.1.0 (14/11/2026): auditoria 13/11, fase 2. La u/h de los operarios sale de koroshi_operarios 2.12
(resumen_operario_dia: la misma cifra en todas partes). Es el unico correo diario (el de koroshi_operarios se ha
quitado). Sin media de u/h al agrupar la tabla por operario y dia. «Horas estimadas» sale de la fuente de horas de la
ficha KPI (koroshi_kpi 1.6). Necesita koroshi_operarios 2.12 y koroshi_kpi 1.6.
v1.2.0 (16/11/2026): auditoria 13/11, fase 6 (pasar a koroshi_base). Empresa, hora del almacen y limites de dia
salen de koroshi_base.comun (antes, la zona horaria de koroshi_operarios). Mismo resultado: esos limites ya
estaban bien en los dias del cambio de hora. Sin campos ni vistas nuevas. Depende de koroshi_base.
v1.3.0 (20/11/2026): lo pidio el responsable el 17/11 («Andres paga la hora entera») y lo aprobo Isaac el 20/11. En
las tablas de operarios, junto a la u/h efectiva («mientras pica»): presencia, perdido (presencia - efectivo) y u/h
real (uds x 60 / presencia), en rojo por debajo del ritmo estandar del Monitor. Seccion nueva «Por tipo de trabajo»
(zonas Z-, tiendas sueltas, Zalando/Volldur, web, otros) en el diario, el semanal y el mensual, y en el mensual
«Produccion por hora del mes» (el equipo hora a hora). Presencia, tipos y horas salen de produccion_calc de
koroshi_monitor, la misma cuenta que la pantalla Produccion por hora: con koroshi_base 1.1 y koroshi_monitor 1.38 la
presencia descuenta los descansos del turno; con versiones anteriores, sin descansos. Tablas nuevas
koroshi.informe.tipo.dia y koroshi.informe.hora.dia, y campos presencia y u/h real en koroshi.informe.operario.dia
(todas propias). Al actualizar, el cron vuelve a calcular todos los dias guardados. Depende de koroshi_monitor.
v1.4.0 (23/11/2026): revision general del 23/11 (R18). Tras mandar el informe desde el cron se mira el estado del
correo: mail.send() no da error si el servidor de correo falla (deja el correo en «Excepcion») y el informe se daba
por enviado. Ahora queda en el log como ERROR, con el motivo, y el correo vuelve a la cola de Odoo para otro intento.
No cambia el contenido ni cuando se manda. Sin campos nuevos.
""",
    'version': '13.0.1.4.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['mail', 'koroshi_base', 'koroshi_operarios', 'koroshi_kpi', 'koroshi_preparacion', 'koroshi_menu',
                'koroshi_monitor'],
    'data': [
        'security/ir.model.access.csv',
        'data/parametros.xml',
        'data/cron.xml',
        'views/informe_views.xml',
        'views/ajustes.xml',
    ],
    'installable': True,
    'application': False,
}
