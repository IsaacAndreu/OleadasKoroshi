# =============================================================================
# COLA S4T: ALERTA + DESATASCO AUTOMATICO (queue_job)
#
# Los jobs "S4T Create sale.order from feed 6..." (pedidos de tienda) tardan
# normalmente menos de 1 minuto cada uno, y entran en oleadas de 30-50 sobre
# las 04:15. Una oleada asi se vacia en pocos minutos en condiciones normales.
#
# Caso real 21/09: un pedido de 3000 unidades se atasco en "started" (el
# servidor no aguanto procesarlo) y bloqueo la entrada de otros 19 pedidos
# detras, que se quedaron en "pending" toda la noche.
#
# Este cron hace dos cosas:
#
#   1. DESATASCO AUTOMATICO: si un job lleva mas de MINUTOS_FORZAR minutos
#      en estado "started" (normalmente porque es un pedido muy grande que
#      el servidor no puede procesar), se fuerza a "done" para que la cola
#      pueda seguir. Se avisa SIEMPRE por correo con el job exacto forzado,
#      para poder revisar despues si el pedido se creo bien.
#
#   2. ALERTA DE COLA PARADA: si tras el paso 1 todavia hay jobs pendientes
#      y hace mas de MINUTOS_AVISO minutos que ninguno ha llegado a "done",
#      se avisa de que la cola sigue sin avanzar (puede haber mas de un
#      job grande, o algun otro problema).
#
# El log solo escribe algo cuando se actua de verdad (se fuerza un job o se
# envia la alerta de cola parada), para no llenar el Registro cada 15 min.
#
# Se ejecuta cada 15 minutos.
# =============================================================================

EMAIL_DESTINO = 'isaac.andreu@nath.es'
EMAIL_CC = 'betty@nath.es'
EMAIL_ORIGEN = 'logisticaefl@nath.es'

MINUTOS_FORZAR = 150   # 2,5 horas: forzar a done un job "started" atascado
MINUTOS_AVISO = 15     # 15 min: avisar si la cola no avanza
PATRON_JOB = 'S4T Create sale.order from feed 6%'


def _enviar_correo(asunto, body_html):
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
    return mail


# --- PASO 1: desatasco automatico de jobs "started" muy antiguos ---
limite_forzar = datetime.datetime.utcnow() - datetime.timedelta(minutes=MINUTOS_FORZAR)

jobs_para_forzar = env['queue.job'].search([
    ('name', 'like', PATRON_JOB),
    ('state', '=', 'started'),
    ('date_started', '<=', limite_forzar),
])

if jobs_para_forzar:
    forzados = [(j.name, j.uuid, (datetime.datetime.utcnow() - j.date_started).total_seconds() / 60)
               for j in jobs_para_forzar]

    try:
        jobs_para_forzar.write({'state': 'done'})
        env.cr.commit()

        filas = "".join([
            "<tr><td>%s</td><td>%s</td><td>%.0f</td></tr>" % (nombre, uuid, minutos)
            for nombre, uuid, minutos in forzados
        ])

        body = """
        <p><b>Se ha desatascado automaticamente la cola de pedidos de Koroshi.</b></p>
        <p>Los siguientes jobs llevaban mas de %d minutos en "En curso" sin
        terminar (probablemente por ser pedidos muy grandes que el servidor
        no puede procesar), y se han forzado a "Hecho" para que los pedidos
        siguientes puedan entrar.</p>
        <table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse">
        <tr style="background:#f0f0f0">
            <th>Job</th><th>UUID</th><th>Minutos atascado</th>
        </tr>
        %s
        </table>
        <p><b>Revisar:</b> comprobar que el pedido de cada uno de estos jobs
        se ha creado correctamente en Ventas. Si no aparece, puede que haga
        falta reintentarlo a mano con "Reintentar" desde el feed
        correspondiente en Integracion S4T.</p>
        """ % (MINUTOS_FORZAR, filas)

        _enviar_correo(
            "Cola Koroshi desatascada automaticamente (%d jobs forzados)" % len(forzados),
            body)

        log("DESATASCO S4T: %d jobs forzados a done -> %s"
            % (len(forzados), [n for n, u, m in forzados]))

    except Exception as e:
        env.cr.rollback()
        log("DESATASCO S4T ERROR: %s" % str(e), level='error')


# --- PASO 2: alerta si, tras el desatasco, la cola sigue sin avanzar ---
pendientes = env['queue.job'].search([
    ('name', 'like', PATRON_JOB),
    ('state', 'in', ('pending', 'started')),
])

if pendientes:
    ultimo_done = env['queue.job'].search([
        ('name', 'like', PATRON_JOB),
        ('state', '=', 'done'),
    ], order='date_done desc', limit=1)

    if ultimo_done:
        minutos_sin_avanzar = (datetime.datetime.utcnow() - ultimo_done.date_done).total_seconds() / 60
    else:
        pendientes_tmp = pendientes.sorted(key=lambda j: j.date_created)
        minutos_sin_avanzar = (datetime.datetime.utcnow() -
                               pendientes_tmp[0].date_created).total_seconds() / 60

    if minutos_sin_avanzar > MINUTOS_AVISO:
        pendientes_ordenados = pendientes.sorted(key=lambda j: j.date_created)
        mas_antiguo = pendientes_ordenados[0]
        minutos_esperando_antiguo = (datetime.datetime.utcnow() - mas_antiguo.date_created).total_seconds() / 60

        filas = "".join([
            "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                j.name,
                j.state,
                j.date_created.strftime('%d/%m %H:%M'),
                int((datetime.datetime.utcnow() - j.date_created).total_seconds() / 60)
            )
            for j in pendientes_ordenados
        ])

        body = """
        <p><b>ALERTA: la cola de pedidos de tienda de Koroshi (S4T) sigue sin
        avanzar.</b></p>
        <p>Llevan mas de <b>%.0f minutos</b> sin que ningun pedido llegue a
        completarse, y hay <b>%d</b> pedidos esperando.</p>
        <p>El mas antiguo (<b>%s</b>) lleva esperando %d minutos.</p>
        <p>Si esto persiste, puede haber mas de un job atascado a la vez, o
        un problema distinto al de pedidos grandes. Revisar en Odoo:
        Ajustes &gt; Tecnico &gt; Cola de trabajos.</p>
        <table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse">
        <tr style="background:#f0f0f0">
            <th>Job</th><th>Estado</th><th>Creado</th><th>Minutos esperando</th>
        </tr>
        %s
        </table>
        """ % (minutos_sin_avanzar, len(pendientes), mas_antiguo.name,
               minutos_esperando_antiguo, filas)

        try:
            _enviar_correo(
                "URGENTE: cola de pedidos de tienda Koroshi detenida (%d esperando)"
                % len(pendientes),
                body)

            log("Alerta cola S4T tiendas: ENVIADA (%d pendientes, %.1f min sin avanzar, "
                "mas antiguo: %s)" % (len(pendientes), minutos_sin_avanzar, mas_antiguo.name))

        except Exception as e:
            log("Alerta cola S4T tiendas ERROR: %s" % str(e), level='error')