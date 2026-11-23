# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Base',
    'summary': 'Constantes y utilidades comunes de los modulos KOROSHI (compania, hora del almacen, matricula CJ)',
    'description': """
Lo que se repetia en los modulos KOROSHI (auditoria 13/11, fase 6), en un solo sitio:
- comun.py (Python puro, con tests sin Odoo en tests/):
  COMPANY_ID (8), TZ (Europe/Madrid), RE_CJ y es_matricula(codigo), ahora_local(), hoy_local(),
  inicio_dia_utc(dia), rango_dia_utc(dia), rango_dias_utc(desde, hasta), a_local(dt), dia_local(dt).
  rango_dia_utc tiene en cuenta el cambio de hora (dias de 23 y 25 horas).
- static/src/js/comun.js: odoo.define('koroshi_base.comun') con esMatricula(codigo) para las pantallas.
Sin modelos ni tablas (desde la 1.1.0, un parametro: koroshi_base.turnos). Los modulos pasan a usarlo uno a uno, cada uno con
su version (el primero, koroshi_zonas 1.4.0).

v1.0.0 (14/11/2026): primera version (auditoria 13/11, fase 6).
v1.1.0 (20/11/2026): turno por hora de entrada (Isaac 20/11: cierre por turno en vez de las 17:00 para todos).
comun.turno_de(entrada) da los tramos, la hora de fin y el descanso del turno de quien entra a esa hora, con la regla
del parametro koroshi_base.turnos (nuevo, noupdate): antes de las 07:00, 06:00-14:00 con 15 min de descanso; antes de
las 11:00, 08:00-13:00 y 14:00-17:00; despues, sin turno. Tambien leer_turnos() y texto_turnos(env). Solo lo usan los
modulos que pasen a usarlo (actividades, operarios, monitor, informe), cada uno con su version. Tests sin Odoo.
v1.2.0 (23/11/2026): revision general del 23/11 (O4, O5, R16). Lo que estaba copiado en cada pantalla de la PDA, en un
solo sitio. pda.py (rutas): comprobar_grupo(env, mensaje), empleado_valido(env, employee_id) (la tarjeta que manda la
PDA tiene que existir, estar activa y ser de la compania; si no, «Pasa otra vez tu tarjeta») y buscar_producto(env,
codigo) (EAN y UPC con o sin 0, codigo alternativo, referencia interna y nombre; comun.variantes_codigo, con tests).
comun.js: comun.tarjeta (leer, guardar, vigente, minutos: la tarjeta compartida koroshi_operarios_pda_<usuario>) y el
lector comun.leerAlParar (lee cuando el lector para 150 ms; con soloRafaga, solo lo que llega de golpe, para los
campos donde tambien se escribe a mano), esFinDeLectura y cancelarLector. Sin modelos, vistas ni parametros nuevos:
basta copiar y reiniciar (no hace falta -u, que actualizaria los ~23 modulos que dependen de este). Lo usan
contenedores 1.15, faltantes 1.10, devoluciones 1.3, recuentos 1.2, prenda_suelo 1.1 y preparacion 3.35: instalar
esta antes que ellos.
v1.2.1 (23/11/2026): empleado_valido usa la misma regla que koroshi_operarios (v2.13): activo, con tarjeta (ID de
credencial) y sin empresa o de una empresa del usuario de la PDA (la 1.2.0 pedia la compania 8 y no miraba la
tarjeta). Nueva es_empleado_valido(env, emp), que devuelve si/no (para Prenda en el suelo). Sustituye a la 1.2.0, que
no se ha instalado.
""",
    'version': '13.0.1.2.1',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['base', 'web'],
    'data': [
        'data/parametros.xml',
        'views/assets.xml',
    ],
    'installable': True,
    'application': False,
}
