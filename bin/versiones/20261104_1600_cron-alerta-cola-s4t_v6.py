# =============================================================================
# COLA S4T: DESATASCO AUTOMATICO + ALERTA (queue_job)            v6 04/11/2026
#
# v6: PASO 3, vigilancia de lo que la cola no ve:
#     a) NO ENTRAN PEDIDOS: el cron "S4T - Get Orders" crea un "S4T Fetch
#        orders" cada 15 min (oct-nov: 2.890 seguidos, un solo hueco de 75 min).
#        Si el ultimo se creo hace mas de MIN_SIN_FETCH min -> correo urgente.
#     b) JOBS FAILED: cualquier job del canal en "failed" que no se haya
#        avisado antes -> correo con el error (los que marca este cron ya se
#        avisan en el PASO 1 y no se repiten).
#     c) FEEDS SIN PEDIDO: feeds S4T de los ultimos DIAS_FEEDS dias en
#        Borrador/Error con mas de MIN_FEED min, o "Creado" sin pedido de
#        venta -> correo (una vez por feed).
#     d) LIMPIEZA: del parametro de reencolados se quitan los jobs que ya no
#        estan en cola.
#     El PASO 3 va dentro de try/except: si falla, no para el desatasco.
# v5: el limite para dar por atascado un "crear pedido" depende de las
#     unidades del feed: max(MIN_PEDIDO, unidades x SEG_POR_UNIDAD).
#     Historico (sep-nov): 0,6-1,5 s/ud, maximo 38 min con 1.542 uds.
#     Con 4 s/ud: 1.107 uds -> 74 min, 1.542 -> 103 min, 3.000 -> 200 min.
#     Mientras un pedido grande sigue dentro de su limite, no salta la
#     alerta de cola parada (la cola esta trabajando, no detenida).
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
MIN_PEDIDO = 60           # crear pedido: atascado si > 60 min en started (minimo)
SEG_POR_UNIDAD = 4        # ...o si > unidades x 4 s, si eso da mas de 60 min
MAX_REENCOLAR = 2         # veces que se reencola un pedido antes de marcarlo failed
MIN_AVISO = 30            # cola parada si ningun job S4T termina en 30 min
MIN_REPETIR_AVISO = 60    # no repetir el correo de cola parada antes de 60 min
PARAM_ULTIMO_AVISO = 'koroshi.alerta_cola_s4t.ultimo_aviso'
PARAM_REENCOLADOS = 'koroshi.alerta_cola_s4t.reencolados'

MIN_SIN_FETCH = 45        # sin "S4T Fetch orders" nuevo en 45 min -> no entran pedidos
NOMBRE_FETCH = 'S4T Fetch orders'
MIN_FEED = 60             # feed en Borrador/Error mas de 60 min -> revisar
DIAS_FEEDS = 7            # solo se miran los feeds de la ultima semana
PARAM_AVISO_FETCH = 'koroshi.alerta_cola_s4t.ultimo_aviso_fetch'
PARAM_FAILED_AVISADOS = 'koroshi.alerta_cola_s4t.failed_avisados'
PARAM_FEEDS_AVISADOS = 'koroshi.alerta_cola_s4t.feeds_avisados'

Job = env['queue.job'].sudo()
Param = env['ir.config_parameter'].sudo()
ahora = datetime.datetime.utcnow()


def _minutos(desde):
    return (ahora - desde).total_seconds() / 60


def _feed_de(job):
    numero_feed = job.name.replace(PREFIJO_PEDIDO, '').strip()
    return env['s4t.order.feed'].sudo().search([('s4t_order_number', '=', numero_feed)], limit=1)


def _unidades(feed):
    if not feed:
        return 0
    return int(sum(feed.line_ids.mapped('s4t_quantity')))


def _limite_pedido(unidades):
    return max(MIN_PEDIDO, unidades * SEG_POR_UNIDAD / 60.0)


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

    feed = _feed_de(job)
    unidades = _unidades(feed)
    if minutos <= _limite_pedido(unidades):
        log('COLA S4T: %s lleva %.0f min con %d uds, dentro de su limite (%.0f min)'
            % (job.name, minutos, unidades, _limite_pedido(unidades)))
        continue

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

    # Un pedido grande en curso dentro de su limite = la cola trabaja, no esta parada.
    pedido_grande_trabajando = False
    for j in esperando.filtered(lambda x: x.state == 'started' and x.method_name == METODO_PEDIDO
                                and x.date_started):
        if _minutos(j.date_started) <= _limite_pedido(_unidades(_feed_de(j))):
            pedido_grande_trabajando = True

    if sin_avanzar > MIN_AVISO and min_desde_aviso > MIN_REPETIR_AVISO and not pedido_grande_trabajando:
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


# --- PASO 3: vigilancia (no entran pedidos, failed, feeds sin pedido, limpieza) ---
vigilancia = []   # textos cortos para la linea de resumen


def _lista_param(nombre):
    res = []
    for x in (Param.get_param(nombre) or '').split(','):
        if x:
            res.append(x)
    return res


try:
    # a) No entran pedidos
    ultimo_fetch = Job.search([('channel', '=', CANAL), ('name', '=', NOMBRE_FETCH)],
                              order='date_created desc', limit=1)
    if ultimo_fetch:
        min_sin_fetch = _minutos(ultimo_fetch.date_created)
        if min_sin_fetch > MIN_SIN_FETCH:
            vigilancia.append('sin fetch %.0f min' % min_sin_fetch)
            aviso_fetch = Param.get_param(PARAM_AVISO_FETCH)
            min_desde = 99999
            if aviso_fetch:
                min_desde = _minutos(datetime.datetime.strptime(aviso_fetch, '%Y-%m-%d %H:%M:%S'))
            if min_desde > MIN_REPETIR_AVISO:
                cron_get = env['ir.cron'].sudo().with_context(active_test=False).search(
                    [('name', '=', 'S4T - Get Orders')], limit=1)
                estado_cron = 'no encontrado'
                if cron_get:
                    estado_cron = '%s, proxima ejecucion %s UTC' % (
                        'activo' if cron_get.active else 'DESACTIVADO', cron_get.nextcall)
                _enviar_correo(
                    'URGENTE: no entran pedidos de S4T en Koroshi (%.0f min)' % min_sin_fetch,
                    '<p><b>ALERTA: hace %.0f minutos que no se descargan pedidos de S4T.</b></p>'
                    '<p>Normalmente se crea un "%s" cada 15 min. El ultimo se creo el %s UTC.</p>'
                    '<p>Cron "S4T - Get Orders": %s.</p>'
                    '<p>Revisar en Odoo: Ajustes &gt; Tecnico &gt; Acciones planificadas.</p>'
                    % (min_sin_fetch, NOMBRE_FETCH, ultimo_fetch.date_created.strftime('%d/%m %H:%M'),
                       estado_cron))
                log('ALERTA S4T SIN FETCH: %.0f min sin "%s" (%s)' % (min_sin_fetch, NOMBRE_FETCH, estado_cron))
                if not SIMULACION:
                    Param.set_param(PARAM_AVISO_FETCH, ahora.strftime('%Y-%m-%d %H:%M:%S'))

    # b) Jobs failed no avisados
    failed = Job.search([('channel', '=', CANAL), ('state', '=', 'failed')], order='date_created desc')
    avisados = _lista_param(PARAM_FAILED_AVISADOS)
    nuevos_failed = failed.filtered(lambda x: x.uuid not in avisados
                                    and not (x.exc_info or '').startswith('Marcado failed por cron'))
    if nuevos_failed:
        vigilancia.append('%d failed' % len(nuevos_failed))
        tabla = ''
        for j in nuevos_failed[:60]:
            error = ''
            for x in (j.exc_info or '').split(chr(10)):
                if x.strip():
                    error = x.strip()[:300]
            tabla += '<tr><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                j.name, j.date_created.strftime('%d/%m %H:%M'), error)
        _enviar_correo(
            'Koroshi: %d jobs de S4T han fallado' % len(nuevos_failed),
            '<p><b>Estos jobs de la cola S4T (Koroshi) han acabado en error.</b></p>'
            '<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse">'
            '<tr style="background:#f0f0f0"><th>Job</th><th>Creado (UTC)</th><th>Error</th></tr>%s</table>'
            '<p>Revisar en Odoo: Ajustes &gt; Tecnico &gt; Cola de trabajos, estado Fallido.</p>' % tabla)
        log('ALERTA S4T FAILED: %s' % nuevos_failed.mapped('name'))
    if not SIMULACION:
        # Solo se guardan los que siguen en failed, para que el parametro no crezca.
        Param.set_param(PARAM_FAILED_AVISADOS, ','.join(failed.mapped('uuid')))

    # c) Feeds sin pedido de venta
    Feed = env['s4t.order.feed'].sudo()
    desde_feeds = ahora - datetime.timedelta(days=DIAS_FEEDS)
    hace_min_feed = ahora - datetime.timedelta(minutes=MIN_FEED)
    feeds_mal = Feed.search([('create_date', '>=', desde_feeds), ('create_date', '<', hace_min_feed),
                             '|', ('state', 'in', ('draft', 'error')),
                             '&', ('state', '=', 'done'), ('sale_order_id', '=', False)])
    feeds_avisados = _lista_param(PARAM_FEEDS_AVISADOS)
    nuevos_feeds = feeds_mal.filtered(lambda x: str(x.id) not in feeds_avisados)
    if nuevos_feeds:
        vigilancia.append('%d feeds sin pedido' % len(nuevos_feeds))
        tabla = ''
        for fd in nuevos_feeds[:60]:
            msg = ''
            for x in (fd.response_msg or '').split(chr(10)):
                if x.strip():
                    msg = x.strip()[:300]
            tabla += '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                fd.name, fd.s4t_client_name or '', fd.state, fd.create_date.strftime('%d/%m %H:%M'), msg)
        _enviar_correo(
            'Koroshi: %d pedidos de S4T sin pedido de venta' % len(nuevos_feeds),
            '<p><b>Estos pedidos han llegado de S4T pero no tienen pedido de venta en Odoo.</b></p>'
            '<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse">'
            '<tr style="background:#f0f0f0"><th>Feed</th><th>Cliente</th><th>Estado</th>'
            '<th>Llegado (UTC)</th><th>Ultimo mensaje</th></tr>%s</table>'
            '<p>Revisar en Odoo: Integracion S4T &gt; Order feeds.</p>' % tabla)
        log('ALERTA S4T FEEDS SIN PEDIDO: %s' % nuevos_feeds.mapped('name'))
    if not SIMULACION:
        Param.set_param(PARAM_FEEDS_AVISADOS, ','.join(feeds_mal.mapped(lambda x: str(x.id))))

    # d) Limpieza del parametro de reencolados
    if reencolados and not SIMULACION:
        en_cola = Job.search([('uuid', 'in', list(reencolados.keys())),
                              ('state', 'in', ('pending', 'enqueued', 'started'))]).mapped('uuid')
        trozos = []
        for k in reencolados:
            if k in en_cola:
                trozos.append('%s:%s' % (k, reencolados[k]))
        quedan = ','.join(trozos)
        if quedan != (Param.get_param(PARAM_REENCOLADOS) or ''):
            Param.set_param(PARAM_REENCOLADOS, quedan)
except Exception as e:
    log('COLA S4T VIGILANCIA ERROR: %s' % str(e), level='error')
    vigilancia.append('ERROR vigilancia')


# --- RESUMEN: una linea por ejecucion ---
ultimo = Job.search([('channel', '=', CANAL), ('state', '=', 'done')], order='date_done desc', limit=1)
log('COLA S4T%s: %d esperando, %d en curso, ultimo terminado hace %s min, %d acciones, %d errores%s'
    % (' (SIMULACION)' if SIMULACION else '',
       len(esperando),
       len(esperando.filtered(lambda j: j.state == 'started')),
       ('%.0f' % _minutos(ultimo.date_done)) if ultimo and ultimo.date_done else '?',
       len(filas), len(errores),
       (' | ' + ', '.join(vigilancia)) if vigilancia else ''))
