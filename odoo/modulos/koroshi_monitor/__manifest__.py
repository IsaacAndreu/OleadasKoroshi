# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Monitor zonas',
    'summary': 'Pantalla en directo de como van las agrupaciones de picking por zonas (Z-ddmm-D1..D5, ZX)',
    'description': """
Monitor de las agrupaciones por zonas de KOROSHI.

Menu Inventario > Operaciones > Monitor zonas. Ensena, para la agrupacion elegida
(por defecto la ultima Z-...): unidades leidas y pendientes por zona, OUT hechas /
cogiendose / sin empezar, el cuadro de cada tienda en cada zona y la lista de OUT
por zona con lineales, huecos y horas. Se refresca solo cada minuto.

v1.1: tambien modo "Tiendas <dia>" para cuando se coge una OUT por pedido (sin zonas):
ritmo del equipo, hora prevista de fin, uds por hora y lo que ha tardado cada OUT.

v1.2: en "Tiendas", cajas cerradas por OUT, hace cuanto se cerro la ultima (aviso si una
OUT lleva mas de 20 min sin cerrar caja) y personas cogiendo ahora.

v1.3: "Personas y horas" para cualquier dia (tambien dias anteriores y zonas): personas,
horas-persona, horas de reloj, uds por hora-persona, uds por persona y segundos por prenda,
estimados por las cajas cerradas. Menu en la barra de Inventario, al lado de KOROSHI KPI.

v1.4: OUT "Parcial" (ya cogido todo lo que hay, faltan prendas sin stock) con su color y "Sin stock"
(en espera); el avance y la hora de fin cuentan solo lo que hay en stock; lista de faltantes por OUT
y articulo al final de la pantalla.

v1.5: los pedidos pendientes en espera (sin stock) no salen (solo se cuentan); columna "Sin stock" en
vez de numeros negativos al lado de lo leido; fuera la tarjeta de faltan de arriba.
v1.6: fuera la lista de faltantes de abajo y la columna "Sin stock": las faltas estan en
KOROSHI KPI > Faltas por dia (modulo koroshi_kpi v1.3).
v1.7: tiendas: franja grande arriba (% hecho, hora de fin, uds por coger), filas con color segun el estado,
"Sin empezar" y "Hechas" plegadas, y Modo pantalla (sin menu de Odoo, letra grande) para la pantalla del almacen.
v1.8: las OUT que ya tienen cogido todo lo que hay (solo faltan prendas sin stock o no encontradas) o que llevan mas de
20 min sin cerrar caja salen como HECHAS (sin validar, con lo que falta), no como "parcial".
v1.9: R1 y R2 en pantallas separadas; zonas con 8 o mas zonas (D6-D8, ZX1...) sin arrastrar: pagina mas ancha, zonas en orden
y la matriz tienda x zona con casillas compactas (uds leidas/total; la OUT y el estado al pasar el raton).
Tiendas con todas sus OUT hechas: lista "listas para juntar" y su fila en gris en la matriz (no cambia de sitio).
Zonas a todo el ancho de la pantalla, casillas que llenan la columna.
v1.10: tercer estado de la tienda en la matriz: con la etiqueta del transportista (numero de seguimiento) en todas
sus OUT = terminada, fila en azul oscuro. Leyenda de colores encima de la matriz.
v1.11: cada casilla de la matriz (y el numero de OUT de las listas) se puede pulsar: abre la OUT en otra pestana.
v1.12: el clic abre la OUT dentro de Odoo (migas para volver al monitor): funciona tambien en la PDA; Ctrl+clic en otra pestana.
v1.13: las migas de pan dicen 'Monitor picking' (antes salia sin nombre).
v1.14: zonas: en cada casilla de la matriz, debajo de las uds, los bultos (cajas cerradas) de esa OUT; columna
Bultos por tienda y bultos en el resumen y la lista de cada zona. En rojo si la OUT esta hecha y los bultos de
Odoo (los que van a XPO) no coinciden con las cajas cerradas.

v1.17: en el modo Tiendas se puede filtrar por estado y transporte, buscar por tienda/OUT/pedido/etiqueta,
ordenar con doble clic en los encabezados y ver transportista y etiqueta. La gráfica de unidades por hora
desglosa el total por OUT con un color estable para cada una.

v1.17.1: las OUT hechas con transportista o etiqueta aparecen con fondo azul y el monitor ocupa todo el ancho.

v1.18: operarios por codigo (OP1, OP2...), nunca por nombre, si esta instalado koroshi_operarios: columna Operario
en Tiendas y zonas y tabla Operarios (que coge ahora, uds, minutos, u/h del dia). Sin ese modulo, igual que antes.
v1.18.2: una caja usada en dos OUT (koroshi_caja_existente) cuenta solo en su OUT duena (K8 10/11: salian 6 bultos).
v1.18.1: OUT o agrupacion ya validada = operario acabado al momento, sin esperar al cron de cierre (5 min).

v1.19: pantalla "Consulta de envios" para oficina, separada en Tiendas y Web. Busca por pedido, OUT, tienda o
expedicion; agrupa las OUT, compara bultos declarados con cajas CJ distintas y permite copiar o compartir. Descarga
Excel por fechas y transportista: Tiendas (XPO SAS / GLS) y Web (GLS / SEUR).
v1.19.1: en zonas, cada OUT abierta cuenta como una persona en "Personas y horas"; ya no se cuenta una persona
por zona.
v1.19.2: boton "Consulta envios / Excel" dentro de la cabecera del Monitor picking.
v1.19.3: corrige el error movil "this.$el.swipe is not a function" de los Kanban de Odoo 13: carga
TouchSwipe antes y protege Inventario si el plugin no estuviera disponible.
v1.19.4: una OUT solo cuenta como persona durante los 5 minutos posteriores a su ultima actividad. Los huecos
largos por picos o faltantes ya no inflan personas ni horas-persona.
v1.19.5: el Excel Web contiene solo las seis columnas pedidas. En Tiendas GLS solo salen expediciones
con etiqueta generada y se cuentan como maximo cinco etiquetas por pedido; las cajas restantes van juntadas.
v1.19.6: boton visible para volver de Consulta de envios al Monitor picking.
v1.19.7: tabla Operarios: con dos operarios en la misma OUT (koroshi_operarios v2.5 / preparacion v3.4) cada uno
cuenta en curso solo sus uds, no las del compañero. Con versiones anteriores, igual que antes.
v1.20.0: Consulta de envios. Excel de Tiendas por la fecha de la ETIQUETA del transportista (adjunto
LabelXPO_... / gls_label_... de la OUT), no por la de validacion: el 11 -> 11 saca todo lo etiquetado el 11 aunque
el pedido sea del 9 o del 10. Columna "Fecha etiqueta" y "Observacion". Recuadro "Anadir un pedido u OUT al Excel
de un dia" (Tiendas y Web): se guarda en el modelo nuevo koroshi.envio.extra, sale en el Excel de ese dia junto al
resto y se puede quitar. Textos que estaban en catalan, en castellano.
v1.20.1: "Personas y horas" en zonas: cada OUT es una persona desde que empieza cada caja hasta que la cierra. Los
huecos entre cajas de hasta 20 min (PARADA_MIN) cuentan como trabajo y la primera caja empieza el tiempo tipico
entre cajas antes (mediana del dia). Con la ventana fija de 5 min se perdia ese tiempo y las u/h por persona salian
infladas (Z-1111: 167 u/h en vez de ~114). Tiendas, igual que antes.
v1.20.2: "Personas cogiendo ahora" (Tiendas, hoy) = operarios de Lecturas con una tarea abierta (OUT, INT de web o
agrupacion) + OUT de tiendas cogiendose sin operario (caja cerrada en los ultimos 20 min). Cada persona cuenta una
vez: la OUT que ya tiene operario no suma otra. Antes solo contaban las OUT (el operario de la INT de web no salia).
Las u/h por persona solo con los que cogen OUT de tiendas.
v1.21.0 (12/11/2026): alarma de bloqueo. Un operario con un pedido abierto en Lecturas que lleva mas de
koroshi_operarios.minutos_sin_leer minutos (15) sin leer nada sale en un aviso en rojo arriba (codigo, pedido y minutos)
y su codigo en rojo en la OUT y en la tabla de operarios. Necesita koroshi_operarios 2.8 (si no, no sale nada).
v1.22.0 (12/11/2026): Consulta de envios, Tiendas: transportista "Todos (con y sin transportista)". Excel con todos
los pedidos de tienda validados en esas fechas, tengan o no transportista ("Sin transportista" en la columna), mas los
anadidos a mano de cualquier transportista. XPO y GLS siguen por fecha de etiqueta.
v1.23.0 (12/11/2026): Excel de Tiendas (XPO, GLS y Todos) con UNA FILA POR TIENDA: a la izquierda la tienda, todos sus
pedidos y todas sus OUT; columnas nuevas "Uds pedidas" y "Done Quantity" (uds hechas). Tiendas ordenadas por numero K.
v1.23.1 (12/11/2026): columna "Cajas por pedido (expedicion)" en el Excel de Tiendas: una linea por pedido con su
numero de expedicion y sus cajas CJ (para hacer el Excel de GLS; al agrupar por tienda se perdia).
v1.23.2 (12/11/2026): Excel de Tiendas XPO: solo cuentan las OUT con su PROPIA etiqueta XPO (adjunto LabelXPO_). Una OUT
con el mismo numero de expedicion pero sin etiqueta no se registro en XPO: no suma bultos ni cajas y sale en Observacion
("No cuenta: OUT ... sin etiqueta XPO"). K81 12/11, expedicion 121771203: XPO 17 bultos, el Excel daba 18. GLS igual.

Solo lee pedidos y expediciones: lo unico que escribe son las OUT anadidas a mano (koroshi.envio.extra).
v1.24.0 (13/11/2026): en la tabla de Operarios, quien esta en pausa (comer, cafe): «⏸ Pausa OUT» y la hora en
Desde (con koroshi_operarios 2.11 o mas).
v1.25.0 (14/11/2026): en la tabla de Operarios, la fila entera en rojo con «🔔 ALARMA · N min sin leer» cuando
la PDA le está pitando (mismos minutos y horario que la alarma de parado de koroshi_preparacion).
v1.26.0 (14/11/2026): auditoria 13/11, fase 2. La u/h de la tabla de Operarios (vista por dia) es la de koroshi_operarios 2.12
(resumen_operario_dia: sin los parados), la misma que Productividad, el correo y el KPI. Con operarios anteriores, como antes.
v1.27.0 (14/11/2026): auditoria 13/11, fase 3. Las rutas piden el permiso de Inventario (stock.group_stock_user): antes, con sudo(), cualquier usuario con sesion podia usarlas. Cache compartida con candado (20 s) como oriola_monitor: un
solo calculo a la vez. Con la pestana oculta no se refresca. Z-ddmm- sin ano: solo agrupaciones creadas de 7
dias antes a 10 despues de ese dia.
v1.28.0 (16/11/2026): auditoria 13/11, fase 6 (pasar a koroshi_base). La empresa sale de koroshi_base.comun. La hora
sigue siendo la del usuario (decidido el 16/11; sin zona, la del almacen). Arregla los dias del cambio de hora: el dia
de una Z-ddmm- y el dia elegido en la vista de tiendas sumaban 24 h fijas (el 25/10, 25 h, perdia la ultima hora).
Sin campos ni vistas nuevas. Depende de koroshi_base.
v1.29.0 (17/11/2026): Consulta de envios > Tiendas: «Cerrar camion XPO y enviar manifiesto». Ver resumen del dia (tiendas,
pedidos, bultos, cajas y diferencias sin resolver) y, al confirmar, manda el Excel XPO del dia por correo a XPO con copia
(parametros koroshi_monitor.manifiesto_para y _cc, noupdate). Uno al dia; se puede reenviar corregido. Se guarda en el
modelo nuevo koroshi.envio.cierre (menu «Cierres de camion XPO»), que koroshi_s4t_envios 1.3 usa para mandar el is_final
a S4T cuando el camion ha salido. Si el correo no sale, no queda cerrado. Solo XPO (GLS fuera, decidido el 17/11). Nada
automatico. Sin campos en tablas compartidas. Depende tambien de mail.
v1.30.0 (17/11/2026): operarios con nombre + codigo («Ana Garcia · OP3») en la tabla Operarios, la columna Operario,
la matriz de zonas, el aviso de parados y el Modo pantalla (antes, desde la v1.18, solo el codigo). Lo pidio Isaac el
17/11. El buscador tambien encuentra por nombre. Se ordena y se busca la u/h por el codigo, como antes. Sin campos ni
vistas nuevas.
v1.31.0 (17/11/2026): pantalla nueva «Producción por hora» (boton en el Monitor picking y menu KOROSHI). Por operario
(nombre + codigo): uds y u/h de CADA HORA del dia, sus pedidos (uds, minutos efectivos y u/h de cada uno) y la fila
EQUIPO con las uds de cada hora, la u/h por persona y cuantos operarios. Lo pidio Isaac el 17/11 (transcript: «cada
hora cuantas me saca»). Uds de cada hora = las uds de cada pedido repartidas por la hora de sus lecturas en la PDA
(koroshi_preparacion); sin lecturas (app de siempre), por el tiempo, marcado con «~». Minutos de cada hora = sin los
parados de 15 min o mas. Los totales son la misma cifra que la tabla Operarios y Productividad (tarea._medir de
koroshi_operarios 2.12+). Excel por dia o rango (hojas Por hora, Resumen y Pedidos). Desplegable de 14 dias; hoy se
refresca cada 2 min. Solo lee: sin campos, sin modelos nuevos. Pruebas sin Odoo en tests/test_produccion_calc.py.v1.32.0 (17/11/2026): revision de Producción por hora con el responsable. u/h REAL como cifra principal (uds entre el
tiempo de presencia: del primer pedido del dia al ultimo, con cerrar cajas y huecos dentro; «Andres paga la hora
entera»; Diana 9-10: 42 uds = 42 u/h, no 65) y u/h picking (la de antes) al lado; en cada casilla minutos leyendo y
perdidos; verde/rojo contra el ritmo estandar (100 u/h real, parametro koroshi_monitor.ritmo_estandar); selector Todo /
Tiendas / Web / Marketplace / Otros (tipo del pedido de venta); franja del dia: total, hecho, pendiente, horas que
quedan y hora de fin (hoy con las OUT de tienda abiertas de dias anteriores). Excel con presencia, perdidos y u/h real.
Monitor: «Personas y horas» sale de los operarios de verdad (koroshi_operarios) y no de las cajas cerradas (Z-1711
daba 141 u/h y media de 4 personas con 12 operarios); sin operarios, la estimacion de siempre. Misma formula de u/h
real que el correo (koroshi_informe), acordada el 17/11. Solo lee: sin campos ni modelos nuevos.
v1.33.0 (17/11/2026): Excel de Tiendas XPO y cierre del camion. «Bultos Odoo» = lo declarado a XPO al hacer la etiqueta
(nota «XPO: declarados N bultos» de koroshi_xpo_bultos, una vez por expedicion); sin nota, los bultos de las OUT como
antes. Y las OUT hechas del mismo pedido sin nº de expedicion (validadas despues de la etiqueta) salen en la fila: OUT,
uds y cajas, con aviso en Observacion. K1 17/11, S-6665004320 (121771266): la etiqueta se hizo desde 26076, que uso
«Caja existente» en la caja de 26077 (0 bultos propios); 26077 se valido despues, sin numero: el Excel daba 6 bultos y
NO; a XPO se declararon 7 y son 7. Del 12 al 17/11 solo cambia K1. Solo lee: sin campos ni modelos nuevos.
v1.33.1 (17/11/2026): «Personas y horas»: la cifra de u/h real salia pequena y gris, no como las otras tarjetas, y
sin el rojo/verde. La regla del texto de debajo (.km-kpi span) tambien pillaba el <span> de color de la cifra; ahora
solo el hijo directo (.km-kpi > span). Solo CSS.
v1.34.0 (18/11/2026): cierre del camion XPO con el formato que pide XPO (Erika, reunion del 18/11). El correo sale
con el asunto «PREVISIÓN XPO AMPOSTA dd/mm/aaaa» y el Excel «Envios Koroshi AMPOSTA dd-mm-aaaa.xlsx» con solo 6 columnas,
como el de Amposta: Fecha salida, Nº expedicion, Nombre tienda, Bultos, Volumen m3 y Peso Neto. Una fila por expedicion;
bultos = los declarados a XPO (mismas cuentas que el Excel de Tiendas), volumen y peso con el criterio de XPO (0,09 m3 y
15 kg por bulto, igual que koroshi_xpo_bultos). Provisional hasta que la informatica de KOROSHI lo mande desde su API.
El Excel completo de Tiendas sigue en el boton de descarga. Destinatarios nuevos en parametros.xml (lista de XPO), pero
por el noupdate hay que cambiarlos a mano en el servidor. Calculo en controllers/xpo_calc.py con tests sin Odoo
(tests/test_xpo_calc.py). Solo lee: sin campos ni modelos nuevos.
v1.35.0 (18/11/2026): «Produccion por hora» sin las sesiones olvidadas (peticion de Isaac: tareas abiertas sin leer
salian cada hora con «0 min leyendo · 60 perd.» y hundian la u/h real). Los ratos de 15 min o mas sin hacer nada ya
no son presencia: presencia = tiempo leyendo + huecos de menos de 15 min entre pedidos (cerrar caja, precintar, palé).
Fuera los parados de 15 min o mas dentro de un pedido, lo que lleva ahora parado una tarea abierta y los huecos largos
entre pedidos (desayuno incluido). Perdido = esos huecos cortos. Umbral = koroshi_operarios.minutos_sin_leer (15).
Va con koroshi_operarios 2.19.0 (cierra sola la tarea a los 15 min). Calculo en controllers/produccion_calc.py, tests
sin Odoo actualizados. Solo lee.
v1.36.0 (19/11/2026): las tiendas por numero de pedido (peticion de Sonia y de Isaac: se preparan por el nº S-6665...,
de menor a mayor, no por K##). Arriba del Monitor (zonas y tiendas, tambien en modo pantalla), «Siguiente tienda»: los
3 pedidos de tienda abiertos con el numero mas bajo (K, nº de pedido, zona y caja de cada OUT, uds por coger y uds
leidas sin caja); al cerrarse todas sus OUT pasa el siguiente. Debajo, en rojo, «Sacar estas antes»: OUT abiertas de
pedidos con numero menor que el de un pedido ya cerrado del todo (con zona, caja, uds leidas y en caja). El 19/11
habria salido con las OUT de Z-1911-MU2 leidas a las 6:30 sin caja ni validar. Solo PED. TIENDAS (nunca Zalando ni
web) y sin los pedidos pendientes en espera ni los backorders. Calculo en controllers/prioridad_calc.py con tests sin
Odoo (tests/test_prioridad_calc.py). Solo lee: sin campos ni modelos nuevos.
v1.37.0 (19/11/2026): los operarios no ven nombres ni productividad (peticion de Isaac). Quien no esta en el grupo
koroshi_menu.grupo_jefes (el usuario «Almacén Nath» de las PDA) ve el Monitor con el codigo de cada operario (OP3) en vez
del nombre, sin «Personas y horas», sin los minutos ni la u/h de cada operario y sin los botones «Producción por hora» y
«Consulta envíos / Excel». Esas dos pantallas (y el cierre del camion y el Excel de envios, que van dentro) dan «solo
para responsables» si se abren igualmente: se comprueba en el servidor, no solo en la pantalla. Los nombres ni siquiera
salen del servidor (cache separada para jefes y operarios). Los jefes (y la tele, que entra con Almacen 2) lo ven todo
como antes. Sin el grupo en la base de datos (koroshi_menu sin instalar), todos lo ven todo. Sin dependencia nueva.
Los menus para Almacén Nath se quitan en koroshi_menu.
v1.38.0 (20/11/2026): «Produccion por hora» con los descansos del turno (Isaac 20/11: regla de la empresa). El turno
sale de la hora de la primera tarea del dia (koroshi_base 1.1, comun.turno_de y el parametro koroshi_base.turnos).
Turno de 6 a 14: se descuentan 15 min de presencia; primero cuentan los ratos de 15 min o mas que ya no eran presencia
y lo que falte sale de los huecos cortos entre pedidos mas largos (nunca del tiempo leyendo), asi baja el «perd.» de
esa hora. Partido (08-13 y 14-17): de 13 a 14 solo cuenta lo leido. Con un filtro (y «Personas y horas») no cambia.
Con koroshi_base 1.0 no hay turnos y todo queda como en la 1.37. Calculo en controllers/produccion_calc.py
(presencia_con_turno), tests sin Odoo. Tambien: en data/parametros.xml el CC del cierre del camion pasa a ser el del
servidor (con expediciones@koroshi.tv); el registro es noupdate, asi que solo deja el repo igual que el servidor.
v1.39.0 (23/11/2026): «Cada tienda en cada zona» ordenada por prioridad (peticion de Isaac): numero de pedido S4T
(S-6665..., el mas bajo primero), el mismo orden que «Siguiente tienda». Antes, por numero de tienda K##. Columna nueva
«Prio.» con la posicion y el final del numero de pedido. Tambien siguen ese orden las listas «Tiendas listas para juntar»
y «Les falta 1 o 2 zonas». Solo pantalla (monitor.js y monitor.css).
""",
    'version': '13.0.1.39.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'mail', 'stock', 'stock_picking_batch', 'koroshi_base', 'koroshi_warehouse_map'],
    'data': [
        'security/ir.model.access.csv',
        'data/parametros.xml',
        'views/assets.xml',
        'views/menu.xml',
        'views/cierre_views.xml',
    ],
    'installable': True,
    'application': False,
}
