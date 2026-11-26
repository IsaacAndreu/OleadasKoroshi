# Copia de la accion de servidor 1800 (cron 186 «S4T - Sync pedidos 17:00») tal como estaba
# el 26/11/2026 ~11:55 hora local, ANTES de cambiar la busqueda (limite 150 lleno de pedidos sin OUT).
# =============================================================================
# SINCRONIZAR RESULTADO DE PEDIDOS CON S4T (KOROSHI)              v6.4 19/11/2026
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
# v6.3 (17/11/2026), Isaac: S-6665004081 y S-6665004251 (Zalando, OUT validadas) no salian
#   en ninguna pasada y el resumen no decia por que. Ahora el resumen dice el NOMBRE de cada
#   pedido saltado por «sin entregas OUT» y por «entregas pendientes» (con el estado de sus
#   OUT). No cambia que se envia.
#
# v6.4 (19/11/2026), Isaac, APLICADA EN PRODUCCION el 19/11/2026:
#   1) SIN_CAJA_BLOQUEA: un pedido de TIENDA con unidades hechas SIN caja (linea validada sin
#      result_package_id) no se envia: S4T recibiria prendas servidas que no estan en ninguna caja
#      (lo que dejaba «Juntar cajas» v4 y vio KOROSHI en el Excel del 19/11). Sale en el Registro
#      como «con uds sin caja» y hay que corregirlo a mano. Zalando y el resto de tipos no se miran.
#   2) ETIQUETA_CIERRA: si TODAS las OUT del pedido tienen etiqueta (carrier_tracking_ref), las cajas ya
#      no se pueden juntar (el bulto ya va en la etiqueta y el pedido ha salido): ya no se espera
#      por una caja pequena y se envia tal como ha salido.
#
# v6.5 (19/11/2026), Isaac: los pedidos de ABOUT YOU (direccion de entrega ABOUT YOU) se
#   envian cuando todas sus OUT estan validadas, sin transportista, igual que Zalando
#   (S-6665004403 y S-6665004406 se quedaban en «sin transportista»; ningun pedido ABOUT YOU
#   ha tenido nunca transportista con etiqueta). Si luego se le pone transportista y etiqueta,
#   el cron 211 (POST /shipments) lo pasa a SHIPPED. Sin cancelar backorders ni regla de caja
#   pequena (eso es solo de tiendas).
#
# v6.6 (20/11/2026), Isaac: los pedidos CREADOS el FECHA_MIN_UDS (hora del almacen) con menos de
#   MIN_UDS_PEDIDO uds pedidas no se sincronizan (ni se les cancelan backorders). Quedan frenados
#   hasta quitar la regla (FECHA_MIN_UDS = ''). Los de otros dias no se tocan.
#
# DIAGNOSTICO = True -> no envia ni cancela nada: solo escribe en el Registro que haria.
# Limite de 150 candidatos por pasada como proteccion de rendimiento.
# Los errores de un pedido no detienen el resto de la ejecucion.
# =============================================================================
#
# La v6.7 solo cambia la cabecera (nueva linea de historial y el limite) y esta busqueda. El resto
# del codigo queda igual en la accion 1800: para volver atras basta con restaurar esta busqueda:
#
# pedidos = env['sale.order'].search([
#     ('name', 'like', 'S-6665%'),
#     ('state', 'in', ['sale', 'done']),
#     ('s4t_remote_id', '!=', 0),
#     ('x_s4t_status', '!=', 'READY'),
#     ('date_order', '>=', DESDE),
# ], order='date_order asc', limit=150)
