# =============================================================================
# SINCRONIZAR RESULTADO DE PEDIDOS CON S4T (KOROSHI)              v6.2 17/11/2026
# Accion de servidor 1800, la lanza el cron 186 "S4T - Sync pedidos 17:00".
#
# Envia a Koroshi las unidades servidas y la caja destino de cada articulo,
# igual que el boton verde SINCRONIZAR S4T manual.
#
# Solo sincroniza pedidos con TODAS las entregas OUT finalizadas.
# Las entregas canceladas no bloquean la sincronizacion (desde el 17/11 tampoco
# en el modulo de Effective: lo arregla koroshi_s4t_sync 1.0.0, que hay que tener
# instalado para que los pedidos con backorders canceladas salgan).
#
# v2 (11/11/2026): SOLO pedidos cuyas OUT tienen TRANSPORTISTA y ETIQUETA.
# v3 (12/11/2026): TODOS los pedidos con las OUT finalizadas (SOLO_CON_TRANSPORTISTA = False).
# v4 (15/11/2026): otra vez SOLO con transportista (y etiqueta).
# v5 (15/11/2026): basta el TRANSPORTISTA (carrier_id) en todas las OUT; sin etiqueta.
#
# v6 (17/11/2026), Isaac:
#   1) CANCELAR_BACKORDERS: en los pedidos de TIENDA (tipo 38, direccion K##, nunca
#      Zalando) con todo lo demas hecho, las backorders con 0 reservado y nada leido
#      se cancelan (no se borran: borrar OUT deja el pedido con huecos) y el pedido
#      sigue. Suelen ser faltantes. Si una backorder tiene ALGO reservado, el pedido
#      no se envia (espera). SOLO_DIAS_ANTERIORES = True: solo las creadas antes de
#      hoy (hora del almacen), las de hoy aun pueden reservar; False = tambien las de hoy.
#   2) CAJA_PEQUENA: no se envia un pedido con una caja (CJ) de 3 uds o menos si
#      tiene otra caja donde juntarla («Juntar cajas» en expediciones). Cuando se
#      junta (la pequena queda vacia), sale en la siguiente pasada. Con una sola
#      caja no hay donde juntarla: se envia.
#
# v6.1 (17/11/2026), Isaac: los pedidos de TIENDA hechos y sin nada que juntar se
#   envian aunque no tengan transportista (TIENDAS_SIN_TRANSPORTISTA = True).
#   Zalando y los demas tipos siguen pidiendo transportista (SOLO_CON_TRANSPORTISTA).
#
# v6.2 (17/11/2026), Isaac: los pedidos de ZALANDO (direccion de entrega ZALANDO) se
#   envian cuando todas sus OUT estan validadas, sin transportista (lo recoge Zalando y
#   en Odoo nunca lo tienen; hasta el 15/11, con la v3, salian asi). A Zalando no se le
#   cancelan backorders (eso es solo de tiendas) y la regla de la caja pequena es solo
#   de tiendas (Zalando va por paquetes y a S4T se le manda sin caja).
#
# DIAGNOSTICO = True -> no envia ni cancela nada: solo escribe en el Registro que haria.
# Limite de 150 candidatos por pasada como proteccion de rendimiento.
# Los errores de un pedido no detienen el resto de la ejecucion.
# =============================================================================

DESDE = '2026-08-01 00:00:00'
SOLO_CON_TRANSPORTISTA = True
TIENDAS_SIN_TRANSPORTISTA = True
ZALANDO_SIN_TRANSPORTISTA = True
CANCELAR_BACKORDERS = True
SOLO_DIAS_ANTERIORES = True
CAJA_PEQUENA = 3
TIPO_TIENDA = 38
DIAGNOSTICO = False


# =============================================================================
# INICIO DE HOY (hora del almacen) EN UTC, para no cancelar backorders de hoy
# =============================================================================

madrid = timezone('Europe/Madrid')
inicio_hoy_utc = madrid.localize(datetime.datetime.combine(
    datetime.datetime.now(madrid).date(), datetime.time(0, 0))).astimezone(timezone('UTC')).replace(tzinfo=None)


def es_tienda(order):
    """Tipo 38 y direccion de entrega K## (nunca Zalando)."""
    if order.s_order_type_id.id != TIPO_TIENDA:
        return False
    nombre = (order.partner_shipping_id.name or '').strip().upper()
    if 'ZALANDO' in (order.partner_shipping_id.display_name or '').upper():
        return False
    return len(nombre) > 1 and nombre[0] == 'K' and nombre[1].isdigit()


def es_zalando(order):
    """v6.2: direccion de entrega de Zalando."""
    return 'ZALANDO' in (order.partner_shipping_id.display_name or '').upper()


def backorder_cancelable(p):
    """Backorder sin nada reservado ni leido (y de dias anteriores si SOLO_DIAS_ANTERIORES)."""
    if not p.backorder_id or p.state in ('done', 'cancel'):
        return False
    if SOLO_DIAS_ANTERIORES and p.create_date >= inicio_hoy_utc:
        return False
    if sum(p.move_lines.mapped('reserved_availability')) > 0:
        return False
    if any(p.move_line_ids.mapped('qty_done')):
        return False
    return True


def cajas_pequenas(picks):
    """CJ de CAJA_PEQUENA uds o menos, si el pedido tiene mas de una caja."""
    uds = {}
    for ml in picks.mapped('move_line_ids'):
        if ml.result_package_id:
            uds[ml.result_package_id.name] = uds.get(ml.result_package_id.name, 0) + ml.qty_done
    if len(uds) < 2:
        return []
    return ['%s=%d' % (k, v) for k, v in sorted(uds.items()) if 0 < v <= CAJA_PEQUENA]


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
lista_canceladas = []
lista_caja_pequena = []


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

        pendientes = picks.filtered(lambda p: p.state != 'done')
        if pendientes:
            # v6: tienda con todo lo demas hecho y solo backorders vacias de dias anteriores -> se cancelan
            hechas = picks - pendientes
            if (CANCELAR_BACKORDERS and hechas and es_tienda(order)
                    and all(backorder_cancelable(p) for p in pendientes)):
                lista_canceladas.append('%s (%s)' % (order.name, ', '.join(pendientes.mapped('name'))))
                if not DIAGNOSTICO:
                    pendientes.action_cancel()
                    env.cr.commit()
                picks = hechas
            else:
                # Si queda alguna OUT pendiente, esperamos a la siguiente pasada.
                saltados_pendientes += 1
                continue

        # v5: todas las OUT con transportista (la v2 y la v4 pedian tambien la etiqueta).
        if (SOLO_CON_TRANSPORTISTA and not (TIENDAS_SIN_TRANSPORTISTA and es_tienda(order))
                and not (ZALANDO_SIN_TRANSPORTISTA and es_zalando(order))):
            faltan = picks.filtered(lambda p: not p.carrier_id)
            if faltan:
                saltados_sin_transportista += 1
                lista_sin_transportista.append('%s (%s)' % (
                    order.name, ', '.join(faltan.mapped('name'))))
                continue

        # v6: una caja pequena que aun se puede juntar a otra: se espera (v6.2: solo tiendas)
        pequenas = cajas_pequenas(picks) if es_tienda(order) else []
        if pequenas:
            lista_caja_pequena.append('%s (%s)' % (order.name, ', '.join(pequenas)))
            continue

        if DIAGNOSTICO:
            lista_enviaria.append('%s (%s)' % (
                order.name, ', '.join([p.carrier_tracking_ref or p.carrier_id.name or p.name for p in picks])))
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

resumen = ('SYNC S4T v6.2%s: %d candidatos, %d procesados, %d con excepcion, '
           '%d sin entregas OUT, %d con entregas pendientes, %d sin transportista, '
           '%d con caja pequena, %d con backorders canceladas'
           % (DIAGNOSTICO and ' (DIAGNOSTICO, NO SE HA ENVIADO NI CANCELADO NADA)' or '',
              len(pedidos), ok, ko, saltados_sin_picks, saltados_pendientes,
              saltados_sin_transportista, len(lista_caja_pequena), len(lista_canceladas)))
if lista_canceladas:
    resumen += '\nBackorders %s (%d): %s' % (
        DIAGNOSTICO and 'que se cancelarian' or 'canceladas', len(lista_canceladas), '; '.join(lista_canceladas[:60]))
if lista_caja_pequena:
    resumen += '\nEsperando a juntar la caja pequena (%d): %s' % (
        len(lista_caja_pequena), '; '.join(lista_caja_pequena[:60]))
if lista_enviaria:
    resumen += '\nSe enviarian (%d): %s' % (len(lista_enviaria), '; '.join(lista_enviaria))
if lista_sin_transportista:
    resumen += '\nHechos pero sin transportista (%d): %s' % (
        len(lista_sin_transportista), '; '.join(lista_sin_transportista[:60]))
log(resumen)
