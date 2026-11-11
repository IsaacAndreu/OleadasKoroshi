# COPIA del codigo en produccion el 11/11/2026 (accion de servidor 1800, la que lanza el cron 186
# "S4T - Sync pedidos 17:00"). Ultima modificacion en Odoo: 25/09/2026 06:31 UTC.
# Para volver atras: pegar este codigo en la accion 1800.

# =============================================================================
# SINCRONIZAR RESULTADO DE PEDIDOS CON S4T (KOROSHI)
#
# Envia a Koroshi las unidades servidas y la caja destino de cada articulo,
# igual que el boton verde SINCRONIZAR S4T manual.
#
# Solo sincroniza pedidos con TODAS las entregas OUT finalizadas.
#
# Si existe alguna entrega OUT pendiente, el pedido se salta y se volvera
# a comprobar en la siguiente ejecucion.
#
# Las entregas canceladas no bloquean la sincronizacion.
#
# HORARIO:
#   Ejecutar cada 1 hora.
#
# Limite de 150 candidatos por pasada como proteccion de rendimiento.
#
# Los errores de un pedido no detienen el resto de la ejecucion.
# El pedido que falle se volvera a intentar en la siguiente pasada
# porque seguira con x_s4t_status != READY.
# =============================================================================


DESDE = '2026-08-01 00:00:00'


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


# =============================================================================
# PROCESAR PEDIDOS
# =============================================================================

for order in pedidos:

    try:

        # ---------------------------------------------------------------------
        # Obtener todas las entregas OUT no canceladas.
        # ---------------------------------------------------------------------

        picks = order.picking_ids.filtered(
            lambda p:
                p.picking_type_id.code == 'outgoing'
                and p.state != 'cancel'
        )


        # ---------------------------------------------------------------------
        # Sin entregas OUT: no hacemos nada.
        # ---------------------------------------------------------------------

        if not picks:
            saltados_sin_picks += 1
            continue


        # ---------------------------------------------------------------------
        # Si queda alguna OUT pendiente, esperamos a la siguiente pasada.
        #
        # Esto tambien cubre backorders o nuevas entregas creadas al validar
        # una transferencia anterior.
        # ---------------------------------------------------------------------

        if any(p.state != 'done' for p in picks):
            saltados_pendientes += 1
            continue


        # ---------------------------------------------------------------------
        # Todas las OUT estan DONE: sincronizar con Koroshi.
        # ---------------------------------------------------------------------

        env['s4t.order.sync'].action_sync_order(order)

        env.cr.commit()

        ok += 1

        log(
            'SYNC S4T: %s -> %s'
            % (
                order.name,
                order.x_s4t_status or 'BUIT'
            )
        )


    except Exception as e:

        # ---------------------------------------------------------------------
        # Un error en un pedido no debe parar el resto.
        # ---------------------------------------------------------------------

        env.cr.rollback()

        ko += 1

        log(
            'SYNC S4T ERROR %s: %s'
            % (
                order.name,
                str(e)
            ),
            level='error'
        )


# =============================================================================
# RESUMEN DE LA PASADA
#
# Se escribe siempre, aunque no haya pasado nada, para poder confirmar en
# el Registro que el cron se ha ejecutado esa hora.
# =============================================================================

log(
    'SYNC S4T: %d candidatos, %d procesados, %d con excepcion, '
    '%d sin entregas OUT, %d con entregas pendientes'
    % (
        len(pedidos),
        ok,
        ko,
        saltados_sin_picks,
        saltados_pendientes
    )
)
