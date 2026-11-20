# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Actividades (registro de tiempo)',
    'summary': 'Manipulaciones: cada persona pasa su tarjeta en el portátil, elige qué hace y empieza, pausa o acaba. '
               'Tiempo por persona y actividad, sin contar uds.',
    'description': """
Registro de tiempo por actividad para manipulaciones (KOROSHI, Effective Logistics NAU-2).

Sustituye la hoja donde se apuntaba a mano la hora de empezar y de acabar.

- Pantalla para el portátil de la zona (Inventario > KOROSHI Operarios > Actividades (portátil), y como app
  «Actividades» en la pantalla de inicio). Pueden estar varias personas a la vez: cada una con su tiempo.
- Cada persona pasa su tarjeta de operario (la misma de Lecturas: hr.employee, ID de credencial OP...) o escribe su
  código y Enter. Elige la actividad: Manipulación marketplace, Tiendas, Web, Manipulación devoluciones, Inversa,
  Bolsas y etiquetas... (se cambian en Actividades > Configuración, sin tocar código).
- Botones: Empezar (tocar una actividad), Pausar, Seguir, Fin. Tocar otra actividad = cambiar (se cierra la anterior).
- 13:00: quien siga trabajando queda en pausa a las 13:00 (comida). 17:00: se cierra todo lo que siga abierto.
  Horas en parámetros koroshi_actividades.hora_pausa y koroshi_actividades.hora_cierre ('' = no hacerlo).
- No cuenta uds: solo tiempo. Informes: tramos (lista, tabla dinámica, gráfico) y jornada por persona y día
  (entrada, salida, horas trabajadas, pausas).

Solo escribe en sus propias tablas (koroshi.actividad, koroshi.actividad.registro, koroshi.inversa.caja). No añade campos a albaranes,
movimientos, tipos de operación ni empleados. Depende de koroshi_operarios solo para las tarjetas y el grupo
«KOROSHI Operarios: ver productividad».

v1.0.0 (13/11/2026): primera versión.
v1.1.0 (14/11/2026): inversa. Las actividades con «Lee matrículas» (Inversa) piden leer la matrícula (CJ + 9 cifras)
de cada caja de tienda al abrirla: cajas por persona y día, tiempo de cada caja (hasta la siguiente lectura, la pausa
o el fin) y uds del teórico (s4t.matricula, solo lectura; si aún no está importada, un cron lo completa). La pantalla
enseña la caja abierta con sus familias y su palet (parámetro koroshi_actividades.inversa_destinos), avisa de las CJ665
(cajas nuestras) y de las matrículas ya leídas, y deja anular la última lectura. Quien está en Inversa queda como
persona de esa pantalla: sus matrículas no piden tarjeta. Tabla nueva koroshi.inversa.caja e informe «Inversa: cajas
leídas». Auditoría 13/11 (fase 2.8): un tramo olvidado de otro día ya no se cierra a las 23:59 (cuenta 0 min y queda
marcado para revisar) y un índice único impide dos tramos abiertos de la misma persona.
v1.2.0 (14/11/2026): auditoria 13/11, fase 3. Las rutas piden el permiso de Inventario (stock.group_stock_user): antes, con sudo(), cualquier usuario con sesion podia usarlas. La persona que manda la pantalla (employee_id o tarjeta) se
comprueba: activa, con tarjeta y de una empresa del usuario.
v1.3.0 (16/11/2026): auditoria 13/11, fase 6 (pasar a koroshi_base). La hora del almacen sale de
koroshi_base.comun (antes, su propia ZONA_HORARIA). Mismo resultado. Sin campos ni vistas nuevas. Depende de
koroshi_base.
v1.3.1 (18/11/2026): icono propio (cronometro morado). Era una copia del de Lecturas (L con codigo de barras) y en la
pantalla de inicio no se distinguian. El menu usa static/description/icon_actividades.png (nombre nuevo, para que
Odoo vuelva a leer la imagen al actualizar); icon.png es la misma imagen. Solo imagen.
v1.4.0 (19/11/2026): «¿Sigues?» (peticion de Isaac: se van a las 14:00 sin pulsar «Fin» y el tramo seguia abierto
hasta el cierre de las 17:00, contando horas que no se trabajaron). Estas actividades no leen nada, asi que se pregunta:
desde koroshi_actividades.sigues_desde (13:00), a quien lleva minutos_sigues (30) sin dar señal (pasar la tarjeta,
empezar, seguir o leer una matricula) su fila del portatil parpadea con «¿Sigues? Pasa tu tarjeta» y el portatil pita
cada minuto. Pasar la tarjeta es «Sigo». Si en minutos_respuesta (15) nadie la pasa, el cron cierra el tramo con el
motivo nuevo «No contesto ¿Sigues?» (queda en pausa; con «Seguir» vuelve): a las 13:00 si no dio señal desde entonces,
si no a la hora en que se le pregunto. Campo nuevo «Ultima señal» (confirmado) en koroshi.actividad.registro (tabla
propia). Tres parametros nuevos (noupdate). El cierre de las 17:00 sigue como red.
v1.5.0 (19/11/2026): tarjetas de actividad en el tablero del responsable (koroshi_operarios 2.20.0, que tiene que
estar instalada ANTES; diseño bin/versiones/diseno-tablero-responsable_2026-11-19_v5.md). En «Por repartir» sale una
pieza por cada actividad activa; Almacén 2 la arrastra a la columna de un operario. Cuando le toca, su PDA no abre
nada: «Tu responsable te pide · Manipulación devoluciones · Ve al portátil de Actividades», sin botones. La tarjeta
se acaba cuando la persona pulsa «Fin» en el portátil (acabar(): la de esa actividad o, si no, la primera; cambiar
de actividad o la pausa no la acaban). La PDA lo mira cada 30 s y pasa sola a lo siguiente. La tarjeta no cuenta
como pedido ni abre tarea de productividad (el tiempo es el del portátil). Tipo «actividad» y campo actividad_id en
la tabla propia de asignaciones de koroshi_operarios; nada en stock.*. Si el tablero falla, el Fin se hace igual.
v1.6.0 (20/11/2026): entrada única de la PDA por áreas (Isaac 20/11; diseño
bin/versiones/diseno-pda-entrada-unica_2026-11-20_v2.md). Pantalla nueva «Inicio (PDA)» (icono «Inicio PDA»): el
operario pasa la tarjeta una vez (la misma de Lecturas, Contenedores y Faltante) y elige área: Recepciones, Picking,
Compactación, Devoluciones, Inversa, Expediciones o Extra. Entrar en un área = empezar una de sus actividades: el
tiempo va a la misma tabla de tramos que el portátil (un tramo abierto por persona; cambiar de área cierra el
anterior) y después se abre su pantalla (Picking = Lecturas, Compactación = Contenedores, Recepcionar = app de código
de barras, Inversa = Actividades con la persona puesta). Pausa, Salir (para el tiempo y olvida la tarjeta) y
«¿Sigues?» en la PDA (aviso rojo y pitido). «Gestión» (Monitor, Tablero...) solo para los operarios de «Jefes en la
PDA» (por la tarjeta: todas las PDA entran con «Almacén Nath»). Botón «◀ Áreas» para volver desde las otras pantallas
y señal de vida cada 2 min si la tarjeta se usa en ellas (el «¿Sigues?» no cierra a quien está leyendo). Campos nuevos
en las tablas propias: «Área (PDA)», «Abre» y «En el portátil» en koroshi.actividad y «Área» (guardado) en
koroshi.actividad.registro; tablas nuevas koroshi.pda.jefe y koroshi.pda.enlace. Actividades nuevas (noupdate):
Picking, Compactación, Descargar camión, Recepcionar, Cargar camión, Montar cajas, Meter en caja lo de expediciones,
Cartón, Limpieza y Reubicar material; ninguna sale en el portátil, que sigue igual. Las de partida reciben su área
(migrations/13.0.1.6.0): marketplace, tiendas, web y bolsas en Recepciones; devoluciones; inversa. Informe «Horas por
área» (solo tramos: la u/h de picking sigue saliendo de las tareas de koroshi_operarios, no se suma). Tablero del
responsable (koroshi_operarios 2.23.0): _tablero_areas() da el área del tramo abierto, y ya no se crean piezas de
actividad en «Por repartir» (las ya dadas siguen hasta su Fin). No toca cron_cerrar ni el «¿Sigues?» del servidor.
v1.7.0 (20/11/2026): cierre por turno (Isaac 20/11; diseño bin/versiones/diseno-cierre-por-turno_2026-11-20.md, v2).
Antes, pausa (hora_pausa) y cierre (hora_cierre, 17:00) iguales para todos: quien se iba a las 14:00 quedaba abierto
hasta las 17:00. Ahora el turno sale de la hora de entrada (primer tramo o primera tarea de Lecturas del día; regla
koroshi_base.turnos, koroshi_base 1.1.0): entra antes de las 7 = 6-14; de 7 a 11 = 8-13 y 14-17. Al acabar cada tramo
del turno se pregunta «¿Sigues?» a quien no ha dado señal desde esa hora; sin respuesta en minutos_respuesta (15), se
cierra A ESA HORA (13:00 = pausa automática; 14:00 / 17:00 = cierre automático). Si contesta, se le pregunta cada
minutos_sigues (30). Quien entra después de las 11 sigue con el «¿Sigues?» de la 1.4. hora_pausa y hora_cierre ya no
se usan; tope nuevo hora_tope (22:00) para lo que nadie cierre. Sin koroshi_base 1.1.0 se comporta como la 1.4.
v1.8.0 (20/11/2026): «la lectura manda» (entrada única de la PDA, fase 4; Isaac 20/11: sí). Cron nuevo cada 5 min
(models/lectura_manda.py): quien lee en Lecturas / Preparación pasa a Picking y quien mueve contenedores a
Compactación, aunque en el Inicio eligiera otra área: el tramo anterior se cierra («Cambió de actividad») a la hora de
la primera lectura nueva y el nuevo empieza ahí (nota «Por lectura»). Si estaba en pausa y vuelve a leer, se le abre
desde esa lectura. Leer cuenta como señal para el «¿Sigues?». Solo a quien ya tiene hoy algún tramo con área: a quien
no usa el Inicio no se le crea nada. En Picking y Compactación, koroshi_actividades.minutos_sin_lecturas (15; 0 =
nunca) sin leer cierra el tramo a la hora de la última lectura (motivo nuevo «Sin lecturas», cuenta como pausa). Va por
cron y no dentro de la lectura: si falla, la PDA no se entera (cada persona en su savepoint). Sin depender de
koroshi_contenedores. Solo escribe en koroshi.actividad.registro. No toca cron_cerrar ni _sigues().
v1.8.1 (20/11/2026): icono propio para «Inicio PDA» (Isaac 20/11: «faltaria un logo nou»). Era el mismo
cronómetro morado que «Actividades» y en la pantalla de inicio no se distinguían. Ahora casa blanca sobre verde con
cuatro áreas (una en amarillo): static/description/icon_inicio_pda.png. Solo imagen y el web_icon del menú.
v1.8.2 (20/11/2026): arreglos del Inicio (PDA) vistos por Soporte en la prueba del 20/11 (lleva el icono de la 1.8.1).
1) Al volver con «◀ Áreas» (o recargar) con la tarjeta ya puesta se quedaba en «Cargando…»: start() pedía el estado
antes de que Odoo enganchara la pantalla y no lo pedía nunca más. Ahora se pide igual, y on_attach_callback y la
vigilancia de 15 s lo vuelven a pedir si sigue sin datos. 2) A 375 px la columna derecha de áreas se salía
(grid 1fr: crecía hasta COMPACTACIÓN / EXPEDICIONES): minmax(0, 1fr), corte de palabra y letra algo menor en
pantallas estrechas. 3) El aviso («Hola, ...») empujaba las áreas y al irse subían: el dedo caía en otra. Ahora flota
encima de la cabecera y no ocupa sitio (tocarlo lo quita). Solo JS y CSS del Inicio; servidor y datos sin cambios.
""",
    'version': '13.0.1.8.2',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'hr', 'barcodes', 'koroshi_base', 'koroshi_operarios'],
    'data': [
        'security/ir.model.access.csv',
        'data/actividades.xml',
        'data/areas_pda.xml',        # v1.6.0
        'data/parametros.xml',
        'data/cron.xml',
        'views/assets.xml',
        'views/views.xml',
        'views/tablero_views.xml',   # v1.5.0
        'views/menu.xml',
    ],
    'qweb': [
        'static/src/xml/actividades.xml',
        'static/src/xml/inicio_pda.xml',   # v1.6.0
    ],
    'installable': True,
    'application': False,
}
