# Tablero KOROSHI

**Una página con el estado de verdad.** Cada chat lo lee al empezar y actualiza su línea al acabar (y en el mismo
commit). El detalle de cada tema va en su chat, en `TRASPASO_AUDITORIA.md` o en `bin/versiones/`; aquí solo una línea.

Última revisión: 17/11/2026 tarde (plan v3; koroshi_monitor lo tiene el chat del Excel de envíos).

## Cómo se usa

1. **Antes de tocar un módulo**, mirar «En curso»: si otro chat lo tiene cogido, no se toca (CLAUDE.md, regla 6).
   Si está libre, apuntarse: una línea con el módulo, el chat y el siguiente paso.
2. **Al sacar una versión**, pasarla a «Hecho y sin instalar» (o actualizar su fila).
3. **Al acabar el tema**, borrar la línea de «En curso» y archivar el chat.
4. **Ideas nuevas**: al chat coordinador («Traspaso KOROSHI: reparto por zonas»), que abre el chat que toque.

## Congelación (17/11/2026): levantada el 18/11/2026

Isaac la levantó el 18/11 para koroshi_contenedores 1.5.0 (compactar huecos), que es urgente. Se vuelve a programar con
las reglas de siempre: una versión, una instalación a la vez.

## En curso

| Tema | Módulo cogido | Chat | Siguiente paso |
|---|---|---|---|
| Coordinación y traspaso de la auditoría | — | Traspaso KOROSHI: reparto por zonas | Plan v3 instalado entero el 17/11 por la tarde |
| Cierre del camión XPO: formato de Erika | — (1.34.0 instalada 18/11 15:53; el módulo lo tiene «Millores del Monitor picking») | Resumen reunión 18/11 (lo coge del chat «Excel de envíos para tiendas», con el sí de Isaac) | Destinatarios ya cambiados a la lista XPO (18/11 ~16:00). Falta cerrar un camión de prueba |
| Mejoras del Monitor de picking: «Siguiente tienda» y operarios sin nombres | koroshi_monitor (1.36.0 instalada 19/11 12:03; **1.37.0 instalada 19/11 15:36 hora local**: Almacén Nath sin nombres ni Producción/Envíos) | Millores del Monitor picking | Probar en una PDA con Almacén Nath tras Ctrl+F5. **Próxima versión**: poner en `data/parametros.xml` el CC del cierre igual que en el servidor (los 5 de XPO + expediciones@koroshi.tv, cambiado a mano el 19/11 ~16:05), con su línea de historial |
| Ronda de faltantes en Lecturas | koroshi_faltantes (1.7.0) + koroshi_preparacion (3.33.0), instaladas 17/11 14:45 | Faltantes (la sesión de los faltantes y la sync S4T) | Probar una ronda pequeña en una PDA; la oficina decide cuándo «Pasar los puestos a 0» |
| Contenedores: compactar huecos | koroshi_contenedores (1.7.0 instalada 19/11 ~09:50; **1.8.0 instalada 19/11 ~11:46**: el buscador encuentra contenedores, ubicaciones, lineales y artículos; **1.8.1 instalada ~11:50**: solo ubicaciones de EFFEC, UBRAN repetía los huecos; **1.8.2 instalada 19/11 12:20**: lineales de MU (MU-01 da su inventario, 72 huecos)) | Contenedores (compactar) | Ctrl+F5 en las PDA; después Ctrl+F5 y probar en PDA; pendiente: qué quieren «verificar» al compactar |
| Resumen de productividad por correo | ? (informe / kpi) | Resumen de productividad por correo | Rellenar |
| Carga del camión por CJ | ? (monitor / s4t_envios) | Carga del camión por CJ | Rellenar; spec en `intent/carga-camion-bultos/` |
| Pedidos pendientes por reasignar | ? | Pedidos pendientes por reasignar | Rellenar |
| Cierre por inactividad (15 min) y u/h sin sesiones olvidadas | Ninguno (suelta koroshi_actividades: ya lo puede coger el Tablero para la 1.5.0). Instaladas: operarios 2.19.0 + monitor 1.35.0 (18/11) y actividades 1.4.0 «¿Sigues?» (19/11 15:42 hora local) | Cierre por inactividad | Probar en el portátil de manipulaciones mañana después de las 13:00: fila que parpadea, pitido, pasar la tarjeta = sigo |
| Alarma PDA si el operario no lee | ? (operarios / preparacion) | PDA: alarma sonora | Rellenar |
| Sync S4T (acción 1800 v6.3, koroshi_s4t_sync) | koroshi_s4t_sync | Sincronización de pedidos con transportista | Rellenar |
| Envíos a S4T en REAL (koroshi_s4t_envios 1.3.0) | — (sin código) | Esta | 17/11 ~16:50: `modo=real`, cron «Envios a S4T» ACTIVO cada 15 min, `desde`=17/11 23:00 UTC (pedidos con fecha de pedido desde el 18/11 00:00). Probado con S-6665004194 (XPO, 3 bultos): S4T READY. Vigilar los primeros envíos del 18/11 (GLS pasa a SHIPPED) |
| Correos pendientes | — | Correus per enviar | — |
| Traspasos S4T en REAL (devoluciones web) | koroshi_s4t_traspasos (1.3.0 instalada 19/11 09:44 hora local; `modo`=real y cron 218 ACTIVO cada 15 min desde 19/11 10:56) | Traspasos S4T (19/11) | DEV de las 4 primeras (EFFEC/DEV/000079-000082, sin validar). 17 correcciones registradas; 1 en error (artículo korowoman2-000003-S no está en Odoo). Vigilar que entren solas las de los 2 palets cuando S4T migre la página antigua de OMS4TEX |
| Agrupaciones web por corte (06:00 y 11:00) y cancelación de las no reservadas | koroshi_agrupaciones_web (1.0.0 instalada 18/11 16:25; `activo`=1 desde 18/11, `cancelar`=1 desde 19/11 08:30) | Agrupaciones web por corte | 19/11 06:00: primera WEB_191126_01 automática (45 OUT, 82 uds). Comprobar la primera cancelación de las 11:00 y el correo a isaac.andreu@nath.es y betty@nath.es |

| Zonas: mejorar (acabar a la hora, pasar a real y orden por pedido) | koroshi_zonas (1.6.0 INSTALADA el 19/11 a las 12:10, en sombra; incluye la 1.5.0) | Zonas: mejorar | 1.5.0: la sombra pasa a ser un SIMULAR (ensayo de partir), aviso de hora de fin y personas que faltan, y previsto contra real con las lecturas de la PDA. 1.6.0: las CAJA y las etiquetas por número de pedido S-6665 (lo pide Sonia, 19/11); en almacén no se nota hasta pasar a real o cambiar la 1883 (líneas 374 y 541). Lo del monitor («Siguiente tienda», «Sacar estas antes») pasado a la sesión del monitor. Plan acordado con Isaac (19/11): la 1883 no se toca (queda solo para lanzarla a mano). El 20/11 a las 04:50/05:30 mirar el ensayo SIMULAR en el canal; si dice BIEN, esa tarde, con el sí de Isaac, desactivar el cron 202 y poner modo_cron = real (primer reparto del módulo el 21/11, por número de pedido). Rondas por pedido (quitar «Todo en una ronda») después, hablándolo con almacén. Además: rellenar los destinatarios del correo y activar el cron 210 si se quiere el aviso por correo. Diagnóstico: `bin/versiones/zonas-diagnostico-y-mejoras_2026-11-19.md` |
| Pedidos S4T grandes sin «could not serialize» (Zalando, ~330 líneas) | koroshi_s4t_pedidos (**1.0.1 instalada 19/11 10:30 UTC**) + cron 192 v7 (`bin/versiones/20261119_cron-alerta-cola-s4t_v7.py`, sin pegar) | Feed S4T sin serialize | Diseño v2: `bin/versiones/diseno-feed-s4t-sin-serialize_2026-11-19_v2.md`. S-6665004459 entró 10:35-10:39 UTC (crear <1 min, confirmar 20 s, reservar 138 s: 258 reservadas, 71 sin stock). Falta pegar la v7 en el cron 192 (probarla antes con SIMULACION = True). Probar con el primer Zalando grande |
| Recepción por packing list (tablet en el muelle: caja a caja a un puesto, avance y discrepancias) | koroshi_recepcion_pl (módulo nuevo, **solo diseño**) | Recepciones por packing list | Diseño en `bin/versiones/diseno-recepciones-packing-list_2026-11-19.md`. **Espera** (19/11): Isaac lo pregunta a Maite (packing list y plantilla), a José Luis (cómo nace hoy la recepción del contenedor, el «shipping», paso a stock) y al almacén (puestos, tablet). Preguntas repartidas al final del punto 8 |
| Buscador de stock (oficina, solo lectura) | koroshi_buscador_stock (1.2.0 instalada 19/11 12:50 hora local: buscar por trozo enseña primero lo que tiene stock y oculta lo que está a 0) | Buscador de stock | Probado en producción (solo lectura): EAN, trozo, lineal L94, hueco y KO_. Falta que Betty lo use (Inventario > Buscador de stock, arriba) y Ctrl+F5 en la oficina. |
| Tablero del responsable: columna por operario con tareas que se arrastran (zonas, agrupaciones, notas, actividades) | **koroshi_operarios 2.20.0 + koroshi_actividades 1.5.0 INSTALADAS 19/11 16:16 hora local**; **operarios 2.21.0 INSTALADA 19/11 16:43 hora local** (icono Tablero = pantalla con 5 formatos A-E para que el jefe elija el 20/11; clásico en un botón; vista en producción con 24 operarios). Almacén Nath (PDA, es admin) entró en el grupo por la 2.21.0: quitado a mano 16:50. **2.21.1 INSTALADA 19/11 16:56 hora local**: tablero por usuario (Almacen 2, Departament IT, Ismael), ya no por ser admin (comprobado). Una pantalla cargada durante el upgrade dio «Template koroshi_operarios.Pantalla not found»: se arregla recargando (Ctrl+F5) (reinicio + un solo upgrade de operarios; log limpio salvo un «bad query DELETE ir_attachment» de los assets) | Tablero del responsable (19/11) | Icono «Tablero» solo para Almacén 2 (ya en el grupo). Visto en producción: «Por repartir» con nota, 6 actividades y OUT libres; una columna por operario. Falta: Ctrl+F5 en las PDA y probar en PDA real (zona en la columna, nota, actividad con «Fin», arrastrar en el PC con Almacén 2). Para que una columna vacía dé la siguiente libre: «darle otra solo» encendido en Reparto de hoy |
| Revisar caja en la PDA (partir una CJ en dos cuando se juntan dos cajas) | — (**solo diseño**; propone koroshi_preparacion, hoy cogido por «Ronda de faltantes») | Revisar box (19/11) | Diseño v1 en `bin/versiones/diseno-revisar-box-partir_2026-11-19.md`. Espera a Isaac: P1 (¿se descubre antes o después de validar?) a P5. Recomendado: primero solo OUT sin validar (reutiliza `mover_caja`) y bloquear con el pedido READY en S4T |
| Misma tarjeta de operario en todas las pantallas de la PDA (Lecturas, Contenedores, Faltante) | koroshi_operarios 2.22.1 + koroshi_contenedores 1.9.1 + koroshi_faltantes 1.8.1 (**INSTALADAS 20/11 ~10:33 hora local**, un reinicio y un solo upgrade de operarios, que actualizó también las otras dos; tarjeta 60 min, parámetro koroshi_operarios.minutos_tarjeta = 60, ruta comprobada) | Soporte KOROSHI 20/11 (pedidos, stock y permisos) | Ctrl+F5 en las PDA (Lecturas se recarga sola). Probar en PDA: tarjeta en Lecturas → abrir Contenedores sin pasarla; tarjeta en Contenedores → volver a Lecturas con ese operario |
| Devoluciones sin Excel: «Ubicar devoluciones» en la PDA (fase 1) y el proceso entero (fase 2) | koroshi_devoluciones (módulo nuevo, **solo diseño**) | Devoluciones (20/11) | Diseño v1 en `bin/versiones/diseno-devoluciones_2026-11-20.md`. **Espera** a Isaac (P1-P5: solo apuntar o mover stock, qué se lee al final, módulo nuevo) y a Betty (punto 5: qué código M1/M2/M3 es cada opción, si «reetiquetar y embolsar» son dos conceptos, si se cobra ubicar sin manipular) |
| PDA: entrada única por áreas (Recepciones, Picking, Compactación, Devoluciones, Inversa, Expediciones, Extra y Gestión para jefes; tiempo por área) | — (**solo diseño**; propone koroshi_actividades 1.6.0, después pda_app y operarios, uno por sesión) | PDA, entrada única por áreas (20/11) | Diseño v1 en `bin/versiones/diseno-pda-entrada-unica_2026-11-20.md`. **Espera** a Isaac: preguntas 1-5 (sobre todo cómo se sabe que es jefe y dónde van las actividades del portátil). Antes de programar, coordinar Actividades con «Cerrar sesión a los 15 min» (cierre por turno) |

Las filas con «?» las rellena su chat la próxima vez que se abra.

## Esperando a alguien

| Qué | A quién | Desde | Dónde |
|---|---|---|---|
| Envíos y bultos (manual, v3 informal) | S4T | 16/11 | `bin/versiones/correo-s4t-envios-bultos_2026-11-17_v3-informal.md` |
| Devoluciones web | S4T | 17/11 | `bin/versiones/correo-s4t-devoluciones-web_2026-11-17.md` |
| Teórico por matrícula | S4T | 14/11 | `bin/versiones/pregunta-s4t-teorico-matriculas_2026-11-14_1457.md` |
| Devoluciones online | Sonia | 17/11 | `bin/versiones/correo-devoluciones-online-respuesta-sonia_2026-11-17_v2.md` |
| Dónde van las fotos (fase 6) | Isaac | 16/11 | `TRASPASO_AUDITORIA.md` |
| Push forzado de la historia limpia (fase 6) | Isaac | 16/11 | `TRASPASO_AUDITORIA.md` |

## Hecho y sin instalar

El plan v3 (`bin/versiones/plan-actualizacion-koroshi_2026-11-17_v3.md`) quedó instalado el 17/11 por la tarde:
faltantes 1.7.0 y preparacion 3.33.0 (14:45) y monitor 1.33.0 (14:47) y 1.33.1 (15:08, cifra de u/h real), hora del almacén. **Antes de instalar algo nuevo,
volver a leer la `installed_version`** (el servidor puede ir por delante del repo).

**Instalado el 17/11 a las 15:28**: koroshi_actividades 1.3.0 (nuevo) y koroshi_menu **2.4.2** (sus menús en Personas y
Configuración). La 2.4.2 sale de la 2.4.1 en la rama `koroshi_menu-2.4` (etiqueta `koroshi_menu/v2.4.2`), no de la 2.5.0
de `main`: una 2.5.x tendrá que llevar estos menús.

**Instalado el 19/11 a las 14:24**: koroshi_menu **2.5.1** (menú de jefes + menús de actividades + jefes en «S4T API /
User»). Jefes: Administración, Almacen 2, BackOffice, Departament IT y Jose Ismael Fonollosa. Almacén Nath (PDA) sigue
en S4T API / User y Admin. Falta: Ctrl+F5 y comprobar con Almacén Nath que Lecturas, Contenedores, Actividades,
Monitor y S4T siguen igual, y con Almacen 2 que abre matrículas y packing feed de S4T.

**Instalado el 19/11 a las 15:36 y 15:41**: koroshi_monitor **1.37.0** (quien no es jefe ve el monitor con códigos,
sin Personas y horas, Producción ni Envíos) y koroshi_menu **2.5.2** («Consulta de envíos» solo jefes). La TV entra
con Almacen 2 (jefe). Falta: Ctrl+F5 y mirarlo con Almacén Nath en una PDA.

**Instalado el 19/11 a las 16:31**: koroshi_menu **2.6.1** (la 2.6.0 falló al actualizar: grupo sin módulo en la
vista; nueva comprobación E8). Bandeja del encargado para el jefe: Hoy y Pendiente; IT solo para «KOROSHI: IT»
(Departament IT). Horas en koroshi_menu.hora_tiendas (13:00) y koroshi_menu.hora_camion (15:00). Falta: verla con
Almacen 2 después de Ctrl+F5.

**No instalar todavía** (decidido): koroshi_delegacion.

**Al día**: s4t_traspasos 1.3.0 (19/11 09:44, modo real desde 10:56), agrupaciones_web 1.0.0 (18/11 16:25; encendido, cancela desde el 19/11), contenedores 1.8.2 (lineales MU, 19/11 12:20), actividades 1.4.0 («¿Sigues?», 19/11 15:42), menu 2.6.1 (bandeja del jefe, 19/11 16:31), faltantes 1.7.0, preparacion 3.33.0, monitor 1.37.0 (sin nombres para no jefes, 19/11 15:36), base 1.0.0, operarios 2.19.0 (cierre por inactividad, 18/11 16:11), kpi 1.9.0, warehouse_map .46, consumibles 1.4.0, xpo_bultos 1.3.0,
pda_app 1.1.0, caja_existente 1.4.0, zonas 1.4.0 (en sombra), informe 1.2.0, s4t_envios 1.3.0,
s4t_sync 1.0.0, sesiones 1.0.0, rendiment 1.1.0.
