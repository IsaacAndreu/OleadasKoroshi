# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Operarios',
    'summary': 'Cola de pedidos por operario en la PDA: tarjeta una vez, el siguiente pedido se abre solo; tiempo y uds por persona',
    'description': """
Productividad por operario sin usuarios de Odoo (KOROSHI, Effective Logistics).

- Cada operario es un empleado (hr.employee) con un codigo en "ID de credencial" (OP0001...).
  No es un usuario de Odoo. Asistente para crear muchos de golpe y tarjetas con "Imprimir Identificacion".
- Pantalla de lecturas dentro de Odoo (Inventario > KOROSHI Operarios > Lecturas (PDA)). Se pone como
  "Accion inicial" del usuario de la PDA: sale al entrar.
  tarjeta + OUT = empieza y abre la OUT en la app de codigo de barras; al validar, la app vuelve sola a esta
  pantalla. tarjeta + "Dejar aqui" = lo deja a medias. Si empieza otro pedido, el anterior se cierra solo.
- Si la OUT es de una agrupacion de zonas (Z-...), la tarea es de toda la agrupacion y se abre en
  "procesar agrupacion".
- Cada 5 minutos se cierran solas las tareas cuyo pedido o agrupacion ya esta validado. A medianoche lo
  que sigue abierto queda "Sin cerrar".
- Uds de cada tarea = uds leidas del pedido al cerrar - uds leidas al empezar.
- Informes: tareas por operario y dia (lista, tabla dinamica, grafico) y OUT validadas hoy sin operario.

Solo escribe en sus propias tablas y en hr.employee (crear operarios). No anade campos a albaranes,
movimientos, agrupaciones ni tipos de operacion, y no cambia la app de codigo de barras (la llama igual
que su menu: /stock_barcode/scan_from_main_menu y start_batch_processing).

v1.0 (09/11/2026): primera version (pagina suelta /koroshi/operarios).
v1.1 (09/11/2026): la pantalla es una accion de cliente de Odoo: abre la OUT en la app de codigo de barras
y al validar se vuelve a ella. Fuera la pagina suelta.
v1.2 (09/11/2026): los nombres con la productividad (Tareas, Productividad, Operarios, Crear operarios) solo los ve
el grupo "KOROSHI Operarios: ver productividad" (los usuarios de la PDA son responsables de inventario y los veian).
Informe diario por email a las 17:00 (parametros koroshi_operarios.informe_*) y menu "Enviar informe de hoy ahora".
v2.0 (09/11/2026): cola de pedidos por operario. Tarjeta una vez (la PDA se queda con el operario hasta "Salir");
la PDA abre sola el siguiente pedido y, al validar, el siguiente. "Saltar" con motivo (oficina, final de su cola o fin
de turno: sigue suyo y el primero al dia siguiente). Reparto de hoy: modo automatico, por pasillos o solo manual;
siempre primero lo asignado a mano (Accion > Asignar a operario en albaranes y agrupaciones). Tablas nuevas
koroshi.operario.asignacion / dia / tramo / motivo. Sin tarjeta la OUT se abre igual pero no cuenta.
v2.1 (09/11/2026): reparto por bloques. Reparto de hoy: operarios de hoy, "Repartir ahora" (llena la cola de cada uno
hasta N pedidos) e "Imprimir etiquetas" (por persona: hoja con su nombre + sus etiquetas de zona en orden; reserva las
matriculas con la accion "KOROSHI Etiquetas zona" de siempre). Linea en naranja cuando le quedan pocos. Con la cola
vacia la PDA ya no da otra sola, salvo que se encienda "darle otra solo (sin etiqueta)".
v2.2 (09/11/2026): al entrar en Lecturas con el operario guardado (iniciar sesion, menu, recargar) la OUT se abre
directamente; Continuar / Saltar / Faltante solo al volver con la flecha atras sin validar. Grupo nuevo "KOROSHI
Operarios: tarjeta obligatoria" (vacio al instalar): sus usuarios no pueden abrir pedidos sin tarjeta (tambien lo
comprueba el servidor). Para probar: el usuario en el grupo y su Accion inicial = "Operarios".
v2.2.1 (10/11/2026): al saltar solo "No hay stock" y "Fin de turno" (los otros 3 motivos se archivan).
v2.2.2 (10/11/2026): grupo "tarjeta obligatoria": sin tarjeta la pantalla Lecturas queda bloqueada (sin barra de Odoo
ni boton "Menu codigo de barras"); solo se puede leer la tarjeta. Al leerla vuelve todo. Resto de usuarios igual.
v2.3.0 (10/11/2026): pantalla nueva de Lecturas (solo aspecto y ayudas; mismo funcionamiento y mismas rutas).
Con tarjeta obligatoria: pantalla completa "Lee tu tarjeta" con punto verde (lector preparado) o gris ("Toca la
pantalla"); si leen un pedido sin tarjeta, aviso rojo. Cabecera con iniciales y nombre del operario y "Salir" (pide
confirmar y avisa si deja un pedido a medias). Leer la tarjeta de otro operario pregunta "Cambiar a X?". Botones grandes:
Continuar (verde), Faltante (naranja) y Saltar (gris). Avisos con icono (bien / info / cuidado / mal); los verdes se
van solos. Saltar en una hoja con los motivos como tarjetas. Pantalla "Abriendo..." (no acepta lecturas mientras
abre) y "Hecho!" al volver con el pedido validado (el siguiente en 3 s o "Parar aqui"). Sin conexion: banda roja, no
acepta lecturas y reintenta cada 5 s. Sonido y vibracion bien/mal (se apagan por PDA). Pedido actual con tienda, zona,
lineas, uds, minutos y progreso; cola numerada; "Cogiendo ahora" plegado; contador del dia (pedidos y uds, como
Productividad). Menu como icono abajo (con tarjeta obligatoria, pulsacion larga de 2 s). Parametro nuevo
koroshi_operarios.minutos_inactividad (0 = desactivado): sale solo el operario tras esos minutos sin usar la PDA.
v2.3.1 (10/11/2026): en la PDA no sale nada de productividad: fuera el contador del dia (pedidos / uds), los
minutos del pedido y el texto "no cuenta en productividad" al abrir sin tarjeta.
v2.4.0 (11/11/2026): preparar a dos. Leer una OUT suelta que ya esta haciendo otro operario ya no da "esta asignada a
X": entra de AYUDANTE. La asignacion sigue siendo del titular; el ayudante tiene su propia tarea y lo que estaba haciendo
vuelve el primero de su cola. Aviso en la PDA "Te unes a X con OUT. Empieza por el final." Las agrupaciones (Z-) y las
OUT asignadas que aun no ha empezado nadie siguen igual.
v2.5.0 (11/11/2026): preparar a dos, segunda parte. Antes de entrar de ayudante se pregunta "¿Ayudar a X?" (Si / No).
Como mucho dos por OUT. En Colas: columnas Uds, "A dos" (OUT suelta con al menos koroshi_operarios.uds_a_dos uds,
150 por defecto; filtro "Grandes: para hacer a dos") y Ayudante: si se pone, cuando el titular empieza la OUT al
ayudante le sale sola en su PDA (sin preguntar; si ya la dejo una vez no se le vuelve a dar). Productividad: campos
"A dos" y "Compañero", filtros Preparadas a dos / solo y agrupar por "A dos / solo" (uds/hora a dos contra solo).
Metodo _uds_hasta_ahora para el monitor.
v2.6.0 (11/11/2026): la pantalla de Lecturas con el mismo aspecto que Preparacion en Lecturas («etiqueta de
estanteria»: plano, negro sobre blanco, cabecera negra, OUT en banda negra). En PDA (pantalla estrecha) sin la barra
de menus de Odoo. Iconos, avatar y spinner vuelven a verse (aria-hidden -> role="presentation"). «Oficina» pasa a
llamarse «Expediciones» en la PDA y en los menus (la clave interna sigue siendo 'oficina').
v2.7.0 (11/11/2026): «Salir» deja la PDA libre y lleva a la pantalla de inicio de Odoo (todas las apps). Icono nuevo
«Lecturas (PDA)» en la pantalla de inicio, para todos los usuarios, para volver a entrar. La salida automatica por
inactividad se queda en Lecturas.
v2.8.0 (12/11/2026): la pregunta pasa a ser «¿Unirte a X?» (Si, unirme / No) y el aviso «Te unes a X con OUT»; antes
«¿Ayudar a X?». Y solo se pregunta si X la esta haciendo AHORA (ha leido algo en los ultimos
koroshi_operarios.minutos_sin_leer minutos, 15 por defecto). Si nadie la esta haciendo (la dejo con «Dejar aqui», se paro
o se fue sin dejarla, o estaba en la cola de otro sin empezar), quien la lee se la queda sin preguntar nada: la tarea
parada del otro se cierra como dejada («La siguio otro operario») a la hora de su ultima lectura, y la asignacion pasa a
quien la lee. Las de Expediciones siguen bloqueadas. Agrupaciones: si otro la esta haciendo ahora, «X la esta haciendo».
Metodos _ultima_actividad, _minutos_sin_leer y _trabajando_ahora para el monitor (alarma de bloqueo).
v2.9.0 (13/11/2026): leer una OUT que es de una zona (Z-) abre SOLO esa OUT (antes, la zona entera). La zona entera,
leyendo el nombre de la Z-. Si otro esta haciendo ahora la zona entera: «OUT es de la zona Z- y la esta haciendo X».
Una zona con alguna OUT cogida suelta no se da entera en automatico. Sin tarjeta, igual: la OUT sola.
v2.10.0 (13/11/2026): boton «Pausa (comer, cafe)» en la PDA: el tiempo se para, la PDA queda libre y al leer la tarjeta
sale la misma OUT la primera (destino pausa). En Saltar, «Dejar este pedido (que lo haga otro)» (destino libre): queda
libre para otro y a quien la deja no se le vuelve a dar en el dia. Motivos nuevos en data/motivos_v2100.xml.
v2.11.0 (13/11/2026): en Lecturas, «Cogiendo ahora» enseña quien esta en pausa y desde que hora. Si un pedido lo
deja un segundo operario el mismo dia («Dejar este pedido»), va a expediciones con la nota «Dejado por X, Y».
Pausa tambien desde el menu de la preparacion (koroshi_preparacion 3.26).
v2.11.1 (13/11/2026): quien esta en pausa ya no sale en Lecturas (sale en el Monitor, koroshi_monitor 1.24:
asignacion.en_pausa()). Sin la ventana «Error de CORS desconocido» en las PDA (js/sin_error_cors.js:
window.onOriginError); los errores con fichero y linea siguen saliendo.
v2.12.0 (14/11/2026): auditoria 13/11, fase 2. Una sola cifra de productividad: resumen_operario_dia() (u/h = uds x 60 /
minutos efectivos, sin los huecos de 15 min sin leer). La usan Productividad, koroshi_informe, koroshi_kpi y koroshi_monitor.
Campos nuevos en la tabla propia de tareas: parado y efectivo (las 51 que hay las recalcula koroshi_informe 1.1.0). Sin media de u/h
al agrupar. Fuera el correo diario de este modulo (cron 204, accion y menu «Enviar informe de hoy ahora»): queda
el de koroshi_informe. Reparto: las OUT de zonas Z- y el tramo se filtran en la busqueda, antes del limite de 400.
v2.13.0 (14/11/2026): auditoria 13/11, fase 3. Las rutas piden el permiso de Inventario (stock.group_stock_user): antes, con sudo(), cualquier usuario con sesion podia usarlas. El employee_id que manda la PDA se comprueba (activo, con
tarjeta y de una empresa del usuario). «Asignar a operario» ya no usa display_notification (no existe en Odoo 13:
daba error despues de asignar): abre la cola del operario.
v2.14.0 (16/11/2026): auditoria 13/11, fase 6 (pasar a koroshi_base). La hora del almacen sale de koroshi_base.comun
(dia de la tarea, medianoche del cron de cierre, «hoy» de Lecturas y del reparto). ZONA_HORARIA se queda como nombre
(koroshi_informe <= 1.1 lo importa). Mismo resultado; sin campos ni vistas nuevas. Depende de koroshi_base.
v2.15.0 (17/11/2026): las PDA se recargan solas tras actualizar un modulo (antes habia que cerrar y abrir Odoo en
cada una para ver lo nuevo, p. ej. la pausa de koroshi_preparacion 3.30). /estado trae version_pantallas: huella de
latest_version de los modulos koroshi_* instalados + el parametro koroshi_operarios.recargar_pda (cambiarlo fuerza
la recarga). Si cambia, Lecturas se recarga sola en un momento seguro: en Lecturas, sin hoja ni capa, sin nada
escrito, con red y sin lecturas pendientes de koroshi_preparacion en la memoria de la PDA; dentro de una OUT espera
a volver. La primera vez, Ctrl+F5 a mano. Sin campos ni vistas nuevas.
v2.16.0 (17/11/2026): una OUT o agrupacion «en expediciones» (oficina: saltada con un motivo de expediciones o
dejada por dos operarios el mismo dia) ya no pide «Que la libere el responsable»: quien la lee en Lecturas se la
queda y sigue donde estaba (lo leido no se pierde). En la nota de la asignacion queda «Recogido por X». Siguen igual
los avisos de «la esta haciendo X» y de la zona entera. Sin campos ni vistas nuevas.
v2.17.0 (17/11/2026): motivo «Sin caja (bolsa, a expediciones)» (data/motivos_v2170.xml, destino expediciones)
para el botón «Sin caja» de koroshi_preparacion 3.32: OUT pequeñas que van en bolsa; la OUT no se valida y queda en
expediciones, que la mete en caja y la valida. /motivos lo marca con sin_caja y Lecturas no lo enseña en Saltar.
Sin campos ni vistas nuevas.
v2.18.0 (17/11/2026): pantalla «Operarios» propia (wizard/gestion_operarios.py, views/gestion_views.xml) para los
responsables, que no tienen permisos de Empleados (RRHH) y les daba error al imprimir la tarjeta o al ver los
operarios creados: cambiar nombre y codigo, quitar (se elimina sin historial; con historial se archiva), boton
«Crear operarios» y tarjeta KOROSHI (texto KOROSHI, nombre y codigo de barras, sin el logo de Effective). Crear
operarios vuelve a esa pantalla. La lista de Empleados queda en «Operarios (ficha de empleado)» (grupo RRHH).
Dos modelos temporales nuevos; sin campos en tablas existentes.
""",
    'version': '13.0.2.18.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'mail', 'hr', 'stock', 'stock_picking_batch', 'stock_barcode', 'koroshi_base'],
    'data': [
        'security/grupo.xml',
        'security/ir.model.access.csv',
        'data/categoria.xml',
        'data/motivos.xml',
        'data/motivos_v221.xml',
        'data/motivos_v2100.xml',
        'data/motivos_v2170.xml',   # v2.17
        'data/cron.xml',
        'data/parametros.xml',
        'data/informe.xml',
        'views/assets.xml',
        'views/tarea_views.xml',
        'views/wizard_views.xml',
        'views/gestion_views.xml',   # v2.18
        'views/reparto_views.xml',
        'views/etiquetas_report.xml',
        'views/menu.xml',
    ],
    'qweb': [
        'static/src/xml/operarios.xml',
    ],
    'installable': True,
    'application': False,
}
