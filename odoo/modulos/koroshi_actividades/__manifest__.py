# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Actividades (registro de tiempo)',
    'summary': 'Manipulaciones: cada persona pasa su tarjeta en el portátil, elige qué hace y empieza, pausa o acaba. '
               'Tiempo por persona y actividad, sin contar uds.',
    'description': """
Registro de tiempo por actividad para manipulaciones (KOROSHI, Effective Logistics NAU-2).

Sustituye la hoja donde se apuntaba a mano la hora de empezar y de acabar.

- Pantalla para el portátil de la zona (Inventario > KOROSHI Operarios > Actividades (portátil), y como app
  «Actividades» en la pantalla de inicio). Pueden estar varias personas a la vez: cada una con su tiempo.
- Cada persona pasa su tarjeta de operario (la misma de Lecturas: hr.employee, ID de credencial OP...) o escribe su
  código y Enter. Elige la actividad: Manipulación marketplace, Tiendas, Web, Manipulación devoluciones, Inversa,
  Bolsas y etiquetas... (se cambian en Actividades > Configuración, sin tocar código).
- Botones: Empezar (tocar una actividad), Pausar, Seguir, Fin. Tocar otra actividad = cambiar (se cierra la anterior).
- 13:00: quien siga trabajando queda en pausa a las 13:00 (comida). 17:00: se cierra todo lo que siga abierto.
  Horas en parámetros koroshi_actividades.hora_pausa y koroshi_actividades.hora_cierre ('' = no hacerlo).
- No cuenta uds: solo tiempo. Informes: tramos (lista, tabla dinámica, gráfico) y jornada por persona y día
  (entrada, salida, horas trabajadas, pausas).

Solo escribe en sus propias tablas (koroshi.actividad, koroshi.actividad.registro, koroshi.inversa.caja). No añade campos a albaranes,
movimientos, tipos de operación ni empleados. Depende de koroshi_operarios solo para las tarjetas y el grupo
«KOROSHI Operarios: ver productividad».

v1.0.0 (13/11/2026): primera versión.
v1.1.0 (14/11/2026): inversa. Las actividades con «Lee matrículas» (Inversa) piden leer la matrícula (CJ + 9 cifras)
de cada caja de tienda al abrirla: cajas por persona y día, tiempo de cada caja (hasta la siguiente lectura, la pausa
o el fin) y uds del teórico (s4t.matricula, solo lectura; si aún no está importada, un cron lo completa). La pantalla
enseña la caja abierta con sus familias y su palet (parámetro koroshi_actividades.inversa_destinos), avisa de las CJ665
(cajas nuestras) y de las matrículas ya leídas, y deja anular la última lectura. Quien está en Inversa queda como
persona de esa pantalla: sus matrículas no piden tarjeta. Tabla nueva koroshi.inversa.caja e informe «Inversa: cajas
leídas». Auditoría 13/11 (fase 2.8): un tramo olvidado de otro día ya no se cierra a las 23:59 (cuenta 0 min y queda
marcado para revisar) y un índice único impide dos tramos abiertos de la misma persona.
""",
    'version': '13.0.1.1.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'hr', 'barcodes', 'koroshi_operarios'],
    'data': [
        'security/ir.model.access.csv',
        'data/actividades.xml',
        'data/parametros.xml',
        'data/cron.xml',
        'views/assets.xml',
        'views/views.xml',
        'views/menu.xml',
    ],
    'qweb': [
        'static/src/xml/actividades.xml',
    ],
    'installable': True,
    'application': False,
}
