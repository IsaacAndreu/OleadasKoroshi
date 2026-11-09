# =============================================================================
# COLA S4T: DESATASCO AUTOMATICO + ALERTA (queue_job)            v4 03/11/2026
#
# v4: modo REAL. Una linea "COLA S4T" en el Registro en cada ejecucion.
#     Correo solo a isaac.andreu@nath.es (sin CC) cuando desatasca algo, cuando
#     la cola esta parada o cuando falla una accion de desatasco.
# v3: en SIMULACION escribe una linea de resumen en el Registro en cada
#     ejecucion, para ver que el cron corre aunque no haya nada que hacer.
#
# Cron "Alerta cola de S4T" (ir.cron id 192). Ejecutar cada 15 minutos.
#
# Por que v2:
#   - 21/09: un pedido de 3000 uds se quedo en "started" y bloqueo 19 pedidos.
#     La v1 solo vigilaba "S4T Create sale.order from feed 6...".
#   - 02/11 14:30: un "S4T Fetch orders" se quedo en "started" y la cola entera
#     del canal root.s4t_sync estuvo parada 17 horas, hasta que IT lo forzo a
#     mano a las 07:18 del 03/11. La v1 no lo habria visto, y ademas estaba
#     desactivada desde el 22/09.
#
# Que hace:
#   1. DESATASCO: cualquier job del canal root.s4t_sync que lleve demasiado
#      tiempo en "started" se saca de ahi para que la cola siga:
#        - Fetch orders, verificar matricula y demas jobs cortos
#          (normalmente tardan segundos): mas de MIN_CORTO min -> se reencola.
#        - Crear pedido (action_create_sale_order, normalmente 1-2 min,
#          maximo visto 38 min): mas de MIN_PEDIDO min ->
#            * si el feed ya tiene pedido de venta, el job se marca "done";
#            * si no, se reencola, hasta MAX_REENCOLAR veces;
#            * si ya se reencolo esas veces, se marca "failed" (queda a la
#              vista en Cola de trabajos y no bloquea a los demas).
#      Nunca se borra nada ni se fuerza disponibilidad.
#   2. ALERTA: si hay jobs S4T esperando y ninguno ha terminado en los ultimos
#      MIN_AVISO minutos, se avisa por correo. Para no repetir el correo cada
#      15 min, no se reenvia hasta pasados MIN_REPETIR_AVISO minutos.
#
# SIMULACION = True -> no cambia nada, solo escribe en el Registro lo que haria.
# =============================================================================

SIMULACION = False

EMAIL_DESTINO = 'isaac.andreu@nath.es'
EMAIL_CC = ''
EMAIL_ORIGEN = 'logisticaefl@nath.es'

CANAL = 'root.s4t_sync'
METODO_PEDIDO = 'action_create_sale_order'
PREFIJO_PEDIDO = 'S4T Create sale.order from feed '

MIN_CORTO = 20            # fetch / matricula / otros: atascado si > 20 min en started
MIN_PEDIDO = 60           # crear pedido: atascado si > 60 min en started
MAX_REENCOLAR = 2         # veces que se reencola un pedido antes de marcarlo failed
MIN_AVISO = 30            # cola parada si ningun job S4T termina en 30 min
MIN_REPETIR_AVISO = 60    # no repetir el correo de cola parada antes de 60 min
PARAM_ULTIMO_AVISO = 'koroshi.alerta_cola_s4t.ultimo_aviso'
PARAM_REENCOLADOS = 'koroshi.alerta_cola_s4t.reencolados'

Job = env['queue.job'].sudo()
Param = env['ir.config_parameter'].sudo()
ahora = datetime.datetime.utcnow()


def _minutos(desde):
    return (ahora - desde).total_seconds() / 60


def _enviar_correo(asunto, body_html):
    if SIMULACION:
        log('SIMULACION cola S4T: se enviaria correo "%s"' % asunto)
        return
    vals_mail = {
        'subject': asunto,
        'body_html': body_html,
        'email_to': EMAIL_DESTINO,
        'email_from': EMAIL_ORIGEN,
    }
    if EMAIL_CC:
        vals_mail['email_cc'] = EMAIL_CC
    mail = env['mail.mail'].sudo().create(vals_mail)
    mail.send()


# Cuantas veces se ha reencolado cada job de pedido (uuid -> veces).
# Se guarda en un parametro de sistema como "uuid:veces,uuid:veces".
reencolados = {}
for trozo in (Param.get_param(PARAM_REENCOLADOS) or '').split(','):
    if ':' in trozo:
        uuid_r, veces_r = trozo.split(':', 1)
        reencolados[uuid_r] = int(veces_r)


# --- PASO 1: desatasco de jobs "started" demasiado antiguos ---
acciones = []   # (job, accion, minutos)

for job in Job.search([('channel', '=', CANAL), ('state', '=', 'started')]):
    if not job.date_started:
        continue
    minutos = _minutos(job.date_started)

    if job.method_name != METODO_PEDIDO:
        if minutos > MIN_CORTO:
            acciones.append((job, 'reencolar', minutos))
        continue

    if minutos <= MIN_PEDIDO:
        continue

    numero_feed = job.name.replace(PREFIJO_PEDIDO, '').strip()
    feed = env['s4t.order.feed'].sudo().search([('s4t_order_number', '=', numero_feed)], limit=1)
    if feed and feed.sale_order_id:
        acciones.append((job, 'done', minutos))
    elif reencolados.get(job.uuid, 0) < MAX_REENCOLAR:
        acciones.append((job, 'reencolar', minutos))
    else:
        acciones.append((job, 'failed', minutos))

filas = []
errores = []
for job, accion, minutos in acciones:
    filas.append((job.name, job.uuid, accion, minutos))
    if SIMULACION:
        continue
    try:
        if accion == 'reencolar':
            job.requeue()
            if job.method_name == METODO_PEDIDO:
                reencolados[job.uuid] = reencolados.get(job.uuid, 0) + 1
        elif accion == 'done':
            job.write({'state': 'done', 'date_done': ahora,
                       'result': 'Marcado done por cron Alerta cola de S4T: el feed ya tenia pedido'})
        else:
            job.write({'state': 'failed',
                       'exc_info': 'Marcado failed por cron Alerta cola de S4T: atascado en started '
                                   '%.0f min y ya reencolado %d veces' % (minutos, MAX_REENCOLAR)})
        env.cr.commit()
    except Exception as e:
        env.cr.rollback()
        log('DESATASCO S4T ERROR %s: %s' % (job.name, str(e)), level='error')
        errores.append((job.name, accion, str(e)))

if errores:
    _enviar_correo(
        'ERROR: el cron Alerta cola de S4T no ha podido desatascar %d jobs' % len(errores),
        '<p><b>El desatasco automatico de la cola S4T (Koroshi) ha fallado.</b></p>'
        '<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse">'
        '<tr style="background:#f0f0f0"><th>Job</th><th>Accion</th><th>Error</th></tr>%s</table>'
        '<p>Revisar en Odoo: Ajustes &gt; Tecnico &gt; Cola de trabajos.</p>'
        % ''.join('<tr><td>%s</td><td>%s</td><td>%s</td></tr>' % e for e in errores))

if filas:
    log('DESATASCO S4T%s: %s' % (' (SIMULACION)' if SIMULACION else '',
                                 ['%s -> %s (%.0f min)' % (n, a, m) for n, u, a, m in filas]))
    if not SIMULACION:
        Param.set_param(PARAM_REENCOLADOS, ','.join('%s:%s' % (k, v) for k, v in reencolados.items()))
    tabla = ''.join('<tr><td>%s</td><td>%s</td><td>%s</td><td>%.0f</td></tr>' % f for f in filas)
    _enviar_correo(
        'Cola Koroshi desatascada automaticamente (%d jobs)' % len(filas),
        '<p><b>Se ha desatascado la cola de S4T (Koroshi).</b></p>'
        '<p>Estos jobs llevaban demasiado tiempo en "En curso":</p>'
        '<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse">'
        '<tr style="background:#f0f0f0"><th>Job</th><th>UUID</th><th>Accion</th><th>Minutos atascado</th></tr>'
        '%s</table>'
        '<p><b>reencolar</b>: vuelve a la cola y se reintenta solo. '
        '<b>done</b>: el pedido ya estaba creado. '
        '<b>failed</b>: revisar el feed en Integracion S4T y reintentarlo a mano.</p>' % tabla)


# --- PASO 2: alerta si la cola sigue sin avanzar ---
esperando = Job.search([('channel', '=', CANAL), ('state', 'in', ('pending', 'enqueued', 'started'))],
                       order='date_created asc')

if esperando:
    ultimo_done = Job.search([('channel', '=', CANAL), ('state', '=', 'done')], order='date_done desc', limit=1)
    if ultimo_done and ultimo_done.date_done:
        sin_avanzar = _minutos(ultimo_done.date_done)
    else:
        sin_avanzar = _minutos(esperando[0].date_created)

    ultimo_aviso = Param.get_param(PARAM_ULTIMO_AVISO)
    min_desde_aviso = 99999
    if ultimo_aviso:
        min_desde_aviso = _minutos(datetime.datetime.strptime(ultimo_aviso, '%Y-%m-%d %H:%M:%S'))

    if sin_avanzar > MIN_AVISO and min_desde_aviso > MIN_REPETIR_AVISO:
        tabla = ''.join('<tr><td>%s</td><td>%s</td><td>%s</td><td>%d</td></tr>' % (
            j.name, j.state, j.date_created.strftime('%d/%m %H:%M'), int(_minutos(j.date_created)))
            for j in esperando[:60])
        _enviar_correo(
            'URGENTE: cola S4T de Koroshi detenida (%d jobs esperando)' % len(esperando),
            '<p><b>ALERTA: la cola de S4T (Koroshi) no avanza.</b></p>'
            '<p>Hace <b>%.0f minutos</b> que no termina ningun job y hay <b>%d</b> esperando.</p>'
            '<p>Revisar en Odoo: Ajustes &gt; Tecnico &gt; Cola de trabajos, filtrando por canal %s.</p>'
            '<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse">'
            '<tr style="background:#f0f0f0"><th>Job</th><th>Estado</th><th>Creado (UTC)</th><th>Minutos esperando</th></tr>'
            '%s</table>' % (sin_avanzar, len(esperando), CANAL, tabla))
        log('ALERTA COLA S4T%s: %d esperando, %.0f min sin avanzar'
            % (' (SIMULACION)' if SIMULACION else '', len(esperando), sin_avanzar))
        if not SIMULACION:
            Param.set_param(PARAM_ULTIMO_AVISO, ahora.strftime('%Y-%m-%d %H:%M:%S'))


# --- RESUMEN: una linea por ejecucion ---
ultimo = Job.search([('channel', '=', CANAL), ('state', '=', 'done')], order='date_done desc', limit=1)
log('COLA S4T%s: %d esperando, %d en curso, ultimo terminado hace %s min, %d acciones, %d errores'
    % (' (SIMULACION)' if SIMULACION else '',
       len(esperando),
       len(esperando.filtered(lambda j: j.state == 'started')),
       ('%.0f' % _minutos(ultimo.date_done)) if ultimo and ultimo.date_done else '?',
       len(filas), len(errores)))
