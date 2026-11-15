# =============================================================================
# SINCRONIZAR RESULTADO DE PEDIDOS CON S4T (KOROSHI)                v4 15/11/2026
# Accion de servidor 1800, la lanza el cron 186 "S4T - Sync pedidos 17:00".
#
# Envia a Koroshi las unidades servidas y la caja destino de cada articulo,
# igual que el boton verde SINCRONIZAR S4T manual.
#
# Solo sincroniza pedidos con TODAS las entregas OUT finalizadas.
# Las entregas canceladas no bloquean la sincronizacion.
#
# v2 (11/11/2026): ademas, SOLO se envian los pedidos cuyas OUT tienen
#   TRANSPORTISTA (carrier_id) y ETIQUETA del transportista (carrier_tracking_ref).
#   Asi Koroshi recibe las cajas cuando ya no se van a juntar ni cambiar.
#   Los pedidos con las OUT hechas pero sin transportista o sin etiqueta se
#   saltan y se cuentan aparte; se volveran a mirar en la siguiente pasada.
#   SOLO_CON_TRANSPORTISTA = False -> se comporta como la v1.
#   DIAGNOSTICO = True -> no envia nada: solo escribe en el Registro que haria.
#
# v3 (12/11/2026): Isaac pide enviar TODOS los pedidos con las OUT finalizadas,
#   tengan o no transportista y etiqueta: SOLO_CON_TRANSPORTISTA = False.
#   Para volver a la v2 basta con ponerlo a True.
#
# v4 (15/11/2026): Isaac pide volver a enviar SOLO los pedidos con transportista:
#   SOLO_CON_TRANSPORTISTA = True (como la v2: todas las OUT con transportista y
#   con etiqueta). Para enviar otra vez todos, ponerlo a False (v3).
#
# Limite de 150 candidatos por pasada como proteccion de rendimiento.
# Los errores de un pedido no detienen el resto de la ejecucion.
# El pedido que falle se volvera a intentar en la siguiente pasada
# porque seguira con x_s4t_status != READY.
# =============================================================================

DESDE = '2026-08-01 00:00:00'
SOLO_CON_TRANSPORTISTA = True
DIAGNOSTICO = False


# =============================================================================
# BUSQUEDA DE PEDIDOS CANDIDATOS
# =============================================================================

pedidos = env['sale.order'].search([
    ('name', 'like', 'S-6665%'),
    ('state', 'in', ['sale', 'done']),
    ('s4t_remote_id', '!=', 0),
    ('x_s4t_status', '!=', 'READY'),
    ('date_order', '>=', DESDE),
], order='date_order asc', limit=150)


# =============================================================================
# CONTADORES PARA EL RESUMEN FINAL
# =============================================================================

ok = 0
ko = 0
saltados_sin_picks = 0
saltados_pendientes = 0
saltados_sin_transportista = 0
lista_sin_transportista = []
lista_enviaria = []


# =============================================================================
# PROCESAR PEDIDOS
# =============================================================================

for order in pedidos:

    try:

        # Todas las entregas OUT no canceladas.
        picks = order.picking_ids.filtered(
            lambda p:
                p.picking_type_id.code == 'outgoing'
                and p.state != 'cancel'
        )

        # Sin entregas OUT: no hacemos nada.
        if not picks:
            saltados_sin_picks += 1
            continue

        # Si queda alguna OUT pendiente, esperamos a la siguiente pasada.
        if any(p.state != 'done' for p in picks):
            saltados_pendientes += 1
            continue

        # v2: todas las OUT con transportista y con etiqueta del transportista.
        if SOLO_CON_TRANSPORTISTA:
            faltan = picks.filtered(lambda p: not p.carrier_id or not p.carrier_tracking_ref)
            if faltan:
                saltados_sin_transportista += 1
                lista_sin_transportista.append('%s (%s)' % (
                    order.name, ', '.join(faltan.mapped('name'))))
                continue

        if DIAGNOSTICO:
            lista_enviaria.append('%s (%s)' % (
                order.name, ', '.join([p.carrier_tracking_ref for p in picks])))
            continue

        # Todo listo: sincronizar con Koroshi.
        env['s4t.order.sync'].action_sync_order(order)

        env.cr.commit()

        ok += 1

        log('SYNC S4T: %s -> %s' % (order.name, order.x_s4t_status or 'BUIT'))

    except Exception as e:

        # Un error en un pedido no debe parar el resto.
        env.cr.rollback()
        ko += 1
        log('SYNC S4T ERROR %s: %s' % (order.name, str(e)), level='error')


# =============================================================================
# RESUMEN DE LA PASADA
# Se escribe siempre, aunque no haya pasado nada, para poder confirmar en
# el Registro que el cron se ha ejecutado.
# =============================================================================

resumen = ('SYNC S4T%s: %d candidatos, %d procesados, %d con excepcion, '
           '%d sin entregas OUT, %d con entregas pendientes, %d sin transportista o sin etiqueta'
           % (DIAGNOSTICO and ' (DIAGNOSTICO, NO SE HA ENVIADO NADA)' or '',
              len(pedidos), ok, ko, saltados_sin_picks, saltados_pendientes,
              saltados_sin_transportista))
if lista_enviaria:
    resumen += '\nSe enviarian (%d): %s' % (len(lista_enviaria), '; '.join(lista_enviaria))
if lista_sin_transportista:
    resumen += '\nHechos pero sin transportista o sin etiqueta (%d): %s' % (
        len(lista_sin_transportista), '; '.join(lista_sin_transportista[:60]))
log(resumen)
