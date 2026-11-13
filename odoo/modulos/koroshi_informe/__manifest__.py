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
""",
    'version': '13.0.1.0.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['mail', 'koroshi_operarios', 'koroshi_kpi', 'koroshi_preparacion', 'koroshi_menu'],
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
