# KOROSHI Operarios (v2.11.0, 13/11/2026)

Saber quién coge cada pedido sin crear usuarios de Odoo. Cada operario es un **empleado** con una tarjeta.
Desde la v2 el operario lee su tarjeta **una vez** y la PDA le va abriendo sola los pedidos de su cola.
El tiempo se cierra solo cuando se valida el pedido.

## v2.11.0: quién está en pausa y pedidos que deja más de uno (13/11/2026)

- En Lecturas, «Cogiendo ahora» enseña también quién está **en pausa**: «⏸ Nombre · en pausa · OUT · desde 13:02».
  Desaparece cuando vuelve (lee su tarjeta y empieza).
- Si un pedido lo deja **un segundo operario** el mismo día con «Dejar este pedido», ya no queda libre: va a
  **expediciones** con la nota «Dejado por X, Y», para que lo revisen.
- La pausa también se puede hacer desde el menú ☰ de la preparación (koroshi_preparacion 3.26).
- El tiempo de pausa no cuenta como trabajado: la pausa cierra la tarea.

## v2.10.0: Pausa y «Dejar este pedido» (13/11/2026)

- Botón **«Pausa (comer, café)»** debajo de Saltar: el tiempo de la OUT se para, la PDA queda libre y, al volver y
  leer la tarjeta, la misma OUT sale la primera. Es como «Fin de turno» pero sin el «Hasta mañana».
- En **Saltar**, motivo nuevo **«Dejar este pedido (que lo haga otro)»**: la OUT queda libre para otro operario y a quien
  la deja no se le vuelve a dar en todo el día (si la lee a mano, sí la puede coger).
- Los motivos se cambian en Inventario > KOROSHI Operarios > Motivos para saltar (destinos nuevos «libre» y «pausa»).

## v2.9.0: leer una OUT de una zona abre solo esa OUT (13/11/2026)

- Si se lee una OUT que está en una agrupación de zona (Z-), se abre **solo esa OUT** (antes se abría la zona entera).
  Para hacer la zona entera, se lee el nombre de la Z-.
- Si otro operario está haciendo ahora la zona entera, no deja: «OUT… es de la zona Z-… y la está haciendo X».
- Una zona con alguna OUT cogida suelta ya no se da entera en automático.
- Sin tarjeta, igual: la OUT sola.

## v2.8.0: «¿Unirte a X?» solo si X la está haciendo ahora (12/11/2026)

- La pregunta ya no es «¿Ayudar a X?» sino **«¿Unirte a X?»** (botones «Sí, unirme» / «No»). El aviso del compañero
  puesto desde Colas también: «Te unes a X con OUT…» (antes «Ayudas a X…»).

- **La está haciendo ahora** = tiene el pedido abierto y se ha leído algo (leer, deshacer, caja, validar en
  Preparación; o una línea del pedido con la app de código de barras: lo más reciente de las dos) en los últimos `koroshi_operarios.minutos_sin_leer` minutos (**15**
  por defecto; Ajustes › Técnico › Parámetros del sistema). Recién empezado sin leer nada también cuenta.
- Si alguien la está haciendo ahora: «¿Unirte a X?» (OUT suelta) o «X la está haciendo» (agrupación).
- Si **nadie** la está haciendo (la dejó con «Dejar aquí», se paró, se fue sin dejarla, o estaba en la cola de otro
  sin empezar): **quien la lee se la queda sin preguntar nada**. La tarea parada del otro se cierra como *dejada*
  («La siguió otro operario») a la hora de su última lectura, para no contarle el tiempo parado, y la asignación pasa
  a quien la lee. Las que están en Expediciones siguen bloqueadas hasta que las libere el responsable.
- El monitor (v1.21) usa lo mismo para la **alarma de bloqueo**: pedido abierto y sin leer más de esos minutos, en rojo.

## v2.7.0: Salir lleva al inicio de Odoo; icono «Lecturas (PDA)» (11/11/2026)

- **Salir** (y «Sí, salir»): la PDA queda libre para otro operario, como antes, y se abre la pantalla de inicio de
  Odoo con todas las apps (`show_home_menu`). La salida automática por inactividad se queda en Lecturas.
- Icono **Lecturas (PDA)** en la pantalla de inicio (menú raíz `menu_koroshi_lecturas_app`, sin grupos: lo ven todos
  los usuarios). Abre Lecturas. El menú de siempre (Inventario → KOROSHI Operarios → Lecturas (PDA)) sigue.

## v2.6.0: mismo aspecto que Preparación (11/11/2026)

- Pantalla de Lecturas plana, negro sobre blanco, como Preparación en Lecturas v3.11: cabecera negra con el operario,
  la OUT que está haciendo en banda negra, Continuar en verde, Faltante en naranja, Saltar con borde negro, la cola
  como lista.
- En la PDA (pantalla de 600 px o menos) no sale la barra de menús de Odoo (`body.o_ko_en_lecturas`).
- Odoo 13 esconde todo lo que lleva `aria-hidden="true"`: avatar, iconos, spinner y marcas usan `role="presentation"`.
- «Oficina» se llama **Expediciones** (motivo de saltar «Queda en expediciones», pestaña y filtro «En expediciones»).
  Solo cambia el texto: la clave `oficina` y los datos guardados siguen igual.

## En la PDA (v2.0)

1. Pantalla **Operarios** (acción inicial del usuario de la PDA): «Lee tu tarjeta».
2. El operario lee **su tarjeta una vez**. La PDA se queda con él hasta que pulsa **Salir (otro operario)**, aunque se
   recargue la página. Leer otra tarjeta cambia de operario.
3. Se abre **sola** la primera OUT de su cola en la app de código de barras (o la agrupación `Z-` en *procesar
   agrupación*). No hay que escanear el pedido.
4. Al **validar**, vuelve a esta pantalla y se abre **sola la siguiente**. Si no quedan: «No tienes más pedidos. Pide a tu
   responsable».
5. Con la **flecha atrás** (sin validar) se queda en la pantalla con la OUT en curso y tres botones:
   - **Continuar:** la vuelve a abrir.
   - **Saltar:** se elige el motivo (ver abajo) y se abre la siguiente.
   - **Faltante** (koroshi_faltantes v1.2): la OUT ya va puesta, solo hay que leer el EAN.
6. Se puede seguir **leyendo una OUT a mano**: si está libre, pasa a ser suya y se abre. Si la tiene otro operario o
   está en oficina, sale el aviso. La que estaba haciendo vuelve la primera de su cola.
7. **Sin tarjeta**, leer una OUT la abre igual, pero no cuenta en productividad.

### Saltar

Desde la v2.2.1 solo hay **2 motivos**:

| Motivo | Adónde va |
|---|---|
| No hay stock / en espera | **Oficina**: no se da a nadie hasta que el responsable la libere |
| Fin de turno (la sigo mañana) | **Sigue suya y la primera**. La PDA queda libre. Al día siguiente, al leer la tarjeta, se abre esa |

«Falta material», «Muy grande» y «Otro» quedan **archivados** (no borrados) por `data/motivos_v221.xml`, que los vuelve
a archivar en cada actualización del módulo (para recuperarlos, quitar ese fichero del manifiesto). Los motivos y su destino se cambian en *KOROSHI Operarios > Motivos para saltar*. Saltar cierra la tarea como
*dejada* (motivo «Saltada»). Al volver a empezarla se abre otra tarea, así la noche no cuenta.

## Reparto (responsable, v2.0)

- *KOROSHI Operarios > Reparto de hoy*: el modo del día. Si no existe, se crea copiando el del último día.
  - **A · Automático:** cuando un operario pide la siguiente, se le da la OUT libre más antigua.
  - **B · Por pasillos:** cada operario tiene un tramo de lineales (pestaña *Tramos*, p. ej. 40–60). Se le da la OUT
    libre más antigua cuyo lineal más bajo reservado está en su tramo. Si no queda ninguna y está marcado, la más
    antigua.
  - **C · Solo manual:** solo lo que reparte el responsable.
  - **Siempre** se da primero lo asignado a mano.
  - *Repartir agrupaciones enteras (Z-)*: **apagado** de inicio. Encendido, una agrupación cuenta como un pedido.
    Apagado, las OUT de agrupaciones `Z-` no se dan solas.
  - *Solo OUT preparadas*: en A y B solo se dan OUT en estado Preparado.
- **Asignar a mano:** lista de albaranes (o de agrupaciones), seleccionar y *Acción > Asignar a operario*. Se pueden
  poner al final o los primeros de su cola.
- *KOROSHI Operarios > Colas*: lo asignado por operario. Se puede reordenar (arrastrar), cambiar de operario,
  **Primera**, **Quitar** y, las de oficina, **Liberar** (vuelven a estar libres).
- Una OUT o agrupación solo puede estar en una cola a la vez (índice único en la base de datos): dos PDA nunca reciben
  la misma.
- Cada 5 min (cron de cierre) lo validado o cancelado pasa a *hecha*.

## Entrar directo y tarjeta obligatoria (v2.2)

- **La OUT se abre directamente.** Al entrar en *Lecturas (PDA)* con el operario ya guardado en la PDA (al iniciar
  sesión, desde el menú o al recargar), se abre sola la OUT que está haciendo o la siguiente de su cola. Al leer la
  tarjeta o una OUT, igual. **Continuar / Saltar / Faltante** solo salen al volver con la **flecha atrás sin haber
  validado** (que es cuando hacen falta para el faltante). Para todos los usuarios.
- **Tarjeta obligatoria:** grupo **«KOROSHI Operarios: tarjeta obligatoria»**, vacío al instalar. Para sus usuarios, en
  Lecturas sin tarjeta **no se abre nada**: «Lee primero tu tarjeta». Lo comprueba también el servidor
  (`/koroshi/operarios/leer`). Los demás usuarios siguen igual (sin tarjeta se abre y no cuenta).
- **Lecturas al iniciar sesión:** en el usuario, *Preferencias > Acción inicial* = **Operarios**.
- **Para probar sin afectar al almacén:** solo **Departament IT** en el grupo y con la Acción inicial. **No tocar
  «Almacén Nath»** hasta decidirlo (mejor un usuario solo para las PDA).
  - Quitarlo: vaciar la *Acción inicial* del usuario y sacarlo del grupo (*Ajustes > Usuarios y compañías > Grupos*, en
    modo desarrollador).
- **Pantalla bloqueada sin tarjeta (v2.2.2):** para los usuarios del grupo, mientras no hay operario en Lecturas
  **no sale la barra de Odoo** (ni el menú de aplicaciones ni el del usuario) **ni el botón «Menú código de barras»**,
  y el texto es solo «Lee tu tarjeta». Solo se puede leer la tarjeta. Al leerla vuelve todo (barra y Menú), y con
  **Salir (otro operario)** se bloquea otra vez. Los demás usuarios lo ven todo igual que antes.
- **Límite:** con operario, el botón **Menú** lleva al menú de código de barras (hace falta para inventarios y demás)
  y desde allí se puede abrir una OUT de otro, sin pasar por su cola. Eso no se puede impedir sin tocar la app
  `stock_barcode`. Escribir una URL a mano en el navegador tampoco se puede impedir desde aquí (en la PDA no hay
  barra de direcciones a la vista).

## Pantalla nueva de Lecturas (v2.3)

Solo cambia el **aspecto** y se añaden ayudas. Funciona igual que la v2.2.2: abre directo al leer la tarjeta,
Continuar / Saltar / Faltante al volver con la flecha atrás, los 2 motivos, el grupo *tarjeta obligatoria*, la misma
clave de la PDA (`koroshi_operarios_pda_2`) y las mismas rutas (solo devuelven datos de más, de lectura).
**Almacén Nath** y los usuarios fuera del grupo hacen lo mismo que hoy (pueden leer una OUT sin tarjeta).

- **Pantalla bloqueada «Lee tu tarjeta»** (solo tarjeta obligatoria): ocupa toda la pantalla. El punto verde
  parpadeando = el lector está listo; gris con «Toca la pantalla» = se ha perdido el foco (tocar y vuelve). Si se lee
  una OUT sin tarjeta sale en rojo «Esto es un pedido. Primero tu tarjeta.».
- **Cabecera:** círculo con las iniciales (color según el nombre), nombre, contador del día y **Salir**.
- **Botones grandes:** **Continuar** verde; debajo, en la misma fila, **Faltante** naranja y **Saltar** gris.
- **Avisos** con icono y color: verde (bien, se van solos a los 4 s), azul (info), naranja (atención), rojo (mal).
- **Salir** y **leer la tarjeta de otro** piden confirmación en una hoja abajo («¿Salir, X?» / «¿Cambiar a Y?»).
  Si deja un pedido a medias, lo avisa (sigue siendo suyo).
- **Saltar:** hoja abajo con los motivos como tarjetas; el que pide nota no deja confirmar sin escribirla.
- **Abriendo:** mientras se abre la OUT, pantalla «Abriendo KO/OUT/… para X» con ruedecita (no leer nada).
- **¡Hecho!:** al validar, pantalla verde con la siguiente y cuenta atrás de 3 s; **Parar aquí** la detiene.
- **Sin conexión:** banda roja arriba, no se lee nada (avisa) y se reintenta cada 5 s; al volver la conexión se quita.
- **Sonido y vibración** al leer (bien / mal). Se apaga con el altavoz de abajo (se guarda en la PDA).
- **Salida por inactividad:** parámetro `koroshi_operarios.minutos_inactividad` (*Ajustes > Técnico > Parámetros
  del sistema*). `0` = desactivado (de inicio). Con p. ej. `20`, si en la PDA no se toca nada en 20 min (y no está
  dentro de un pedido), sale el operario. No se pisa al actualizar.
- **Menú ☰:** con tarjeta obligatoria hay que **mantenerlo pulsado 2 s** (para que no se abra sin querer). Los
  demás usuarios, un toque.
- **Datos (solo lectura):** del pedido en curso tienda, zona, líneas, uds, minutos y barra de uds leídas; la cola
  numerada («Después te tocan»); «Cogiendo ahora» plegado con el n.º de operarios; y el contador del día (pedidos y
  uds, como en *Productividad*).
- Respeta *reducir movimiento* del sistema (sin animaciones) y usa colores de alto contraste. Sin librerías externas.
- **koroshi_faltantes** no cambia: su botón sigue detrás de `.o_ko_dejar` y la pantalla lo pinta naranja y delante de
  Saltar con CSS.

## Bloques y etiquetas (v2.1)

El operario necesita la etiqueta de zona (código de la OUT + matrícula CJ) para cerrar la caja y validar. Como en
automático la OUT se decidía en el momento, nadie sabía qué etiqueta darle. Desde la v2.1 se reparte **por bloques**:

1. *Reparto de hoy*: elegir el modo (A o B) y poner los **operarios de hoy** (pestaña *Operarios de hoy*; en modo B,
   con su tramo de lineales).
2. **Repartir ahora**: llena la cola de cada operario hasta *Pedidos por bloque* (10 de inicio), uno a cada uno por
   turnos, con la OUT libre más antigua (A) o de su tramo (B).
3. **Imprimir etiquetas**: un PDF con, por cada operario, una hoja con su nombre y sus pedidos, y detrás sus
   etiquetas de zona en el orden en que la PDA se las abrirá. Las matrículas las reserva la acción de siempre
   *KOROSHI Etiquetas zona* (si la OUT ya las tenía, las reutiliza). Solo imprime las que aún no se han impreso.
4. Cuando a alguien le quedan *Avisar cuando le queden* (3) o menos, su línea sale en **naranja**: **Dar bloque** e
   **Imprimir** en su línea.

- Con la cola vacía la PDA dice «No tienes más pedidos. Pide a tu responsable». Si se enciende *Si se le acaba la
  cola, darle otra solo (sin etiqueta)*, la PDA le da la siguiente sola, como en la v2.0, y usará una CJ preimpresa.
- **Reimprimir:** *Colas*, seleccionar y *Acción > Imprimir etiquetas*. Filtro *Sin etiqueta impresa*.
- Si una OUT saltada pasa a otro operario, la etiqueta en papel tiene que ir con ella.
- En modo C no hay *Repartir ahora*: se asigna a mano y se imprime con *Imprimir* (en la línea del operario) o desde
  *Colas*.

## En la PDA (v1.1, sustituido por la v2.0)

1. Al entrar en Odoo con el usuario de la PDA sale la pantalla **Operarios**, con el mensaje «Lee tu tarjeta».
   - Para que salga, en *Ajustes > Usuarios*, ficha de «Almacén Nath» (y «Almacen 2»), se pone **Acción inicial = Operarios**.
2. El operario lee **su tarjeta** y sale su nombre.
3. Lee **la OUT** del papel. Empieza el tiempo y la OUT **se abre en la app de código de barras**:
   - una OUT suelta se abre igual que si se leyera en el menú de código de barras;
   - si es de una agrupación `Z-`, se abre la agrupación en *procesar agrupación*.
4. Al **validar**, la app de código de barras vuelve atrás y sale otra vez esta pantalla, lista para la siguiente tarjeta.
   - Con la flecha atrás, sin validar, también vuelve. Ahí puede hacer *tarjeta + Dejar aquí* o leer otra OUT.
5. El botón **Menú código de barras** sirve para el resto de tareas (inventario, mover ubicaciones...).
   - Lo que se abra desde ese menú vuelve a ese menú y no cuenta tiempo.

No cambia la app de código de barras. La pantalla usa las mismas llamadas que su menú:
`/stock_barcode/scan_from_main_menu` para las OUT y el botón `start_batch_processing` para las agrupaciones.

## Cómo se usa

1. **Crear los operarios:** menú *Inventario > KOROSHI Operarios > Crear operarios*. Se escribe un nombre por línea.
   - Cada uno se crea como empleado de EFFEC con el código `OP0001`, `OP0002`... en *ID de credencial* y la etiqueta *Operario KOROSHI*.
   - No se crea ningún usuario.
2. **Tarjetas:** *KOROSHI Operarios > Operarios*, seleccionarlos y luego *Imprimir > Imprimir Identificación*.
3. **En la PDA:** pantalla *KOROSHI Operarios > Lecturas (PDA)*, la acción inicial del usuario. Ver arriba.
   - **Empezar:** leer la tarjeta y después el pedido.
     - El pedido es el código de la OUT, el que sale en *Transferir agrupación* y en el albarán.
     - Si la OUT es de una agrupación de zonas (`Z-...`), la tarea es de toda la agrupación.
     - También vale el nombre de la agrupación.
   - **Dejarlo a medias:** leer la tarjeta y pulsar **Dejar aquí**.
   - Si el operario empieza otro pedido, el anterior se cierra solo como *dejado*.
   - La tarjeta vale 90 s para leer el pedido.
4. **Cierre automático (cron cada 5 min):**
   - Si el pedido o la agrupación está validado, la tarea pasa a *acabada*, con la hora de validación.
   - Lo que sigue abierto de días anteriores pasa a *sin cerrar*, con la hora de la última lectura.
5. **Informes:**
   - *Tareas*: hoy, por defecto.
   - *Productividad*: tabla dinámica de operario por día, con uds y minutos, de los últimos 7 días.
   - *OUT validadas hoy sin operario*: muestra quién no usa la tarjeta.

## Qué cuenta

- **Uds de una tarea** = uds leídas (`qty_done`) del pedido o la agrupación al cerrar, menos las leídas al empezar.
  - Si un pedido lo deja uno y lo sigue otro, cada uno tiene las suyas.
  - Si dos personas cogen la misma agrupación a la vez, las uds del rato se cuentan en las dos tareas.
- **Minutos** = desde la lectura del pedido hasta la validación, *Dejar aquí* u otro pedido.
- **Uds/hora** = uds × 60 / minutos.

## Quién ve los nombres (v1.2)

- Solo el grupo **KOROSHI Operarios: ver productividad** ve *Tareas*, *Productividad*, *OUT validadas hoy sin operario*,
  *Operarios*, *Crear operarios* y *Enviar informe*. Al instalar lo tiene solo el administrador (Departament IT).
  Se da en *Ajustes > Usuarios > (usuario) > Permisos técnicos / Otros*.
- Los usuarios de la PDA («Almacén Nath», «Almacen 2») son *responsables* de inventario: por eso no basta con ese
  grupo. En la PDA solo ven *Lecturas (PDA)*.
- El monitor picking (`koroshi_monitor` v1.18) solo enseña códigos (OP1, OP2...), nunca nombres.

## Informe diario por email (v1.2)

- A las **17:00** (hora de Madrid) se manda el informe del día: operarios (código y nombre), pedidos acabados,
  dejados y abiertos, uds, tiempo y u/h, y las OUT validadas sin operario. Si ese día no hay nada, no se manda.
- Cron *KOROSHI Operarios: informe diario por email* cada 15 min; manda una vez al día a partir de la hora.
- Parámetros (*Ajustes > Técnico > Parámetros del sistema*), no se pisan al actualizar:
  - `koroshi_operarios.informe_destinatarios`: emails separados por coma.
  - `koroshi_operarios.informe_hora`: `17:00`.
  - `koroshi_operarios.informe_servidor`: servidor de correo saliente, `NATH`.
  - `koroshi_operarios.informe_ultimo`: último día enviado (lo escribe el cron).
- Para probar: menú *KOROSHI Operarios > Enviar informe de hoy ahora* (no marca el día como enviado).

## Seguridad

- Solo escribe en sus tablas (`koroshi.operario.tarea`, `.asignacion`, `.dia`, `.tramo`, `.motivo`) y, desde el
  asistente, crea `hr.employee`.
- **No añade campos** a `stock.picking`, `stock.move(.line)`, `stock.picking.batch` ni `stock.picking.type`.
  Ojo: el 03/11 un campo en `stock.picking.type` tumbó la PDA.
- No toca la app de código de barras.
- La pantalla usa rutas propias (`/koroshi/operarios/*`) y escribe con `sudo` solo en su tabla.
  La tarjeta se busca en todas las empresas.
- Los empleados sin usuario no son usuarios de Odoo. Hay que confirmar con el partner si el contrato
  cuenta los empleados de RRHH como *Light Users*.
- Hay que informar a la plantilla y a sus representantes antes de usarlo para medir el rendimiento.

## Ficheros

```
models/tarea.py              koroshi.operario.tarea + cron + informe sin operario
wizard/crear_operarios.py    crear operarios de golpe
models/reparto.py            v2: cola (asignacion), reparto del dia, tramos, motivos
wizard/asignar.py            v2: Accion > Asignar a operario (albaranes y agrupaciones)
controllers/main.py          /koroshi/operarios/leer, /operario, /siguiente, /saltar, /motivos, /dejar, /estado
views/reparto_views.xml      v2: Reparto de hoy, Colas, Motivos, asistente
views/etiquetas_report.xml   v2.1: hoja con el nombre del operario + accion Imprimir etiquetas en Colas
data/motivos.xml             v2: motivos para saltar (noupdate)
data/motivos_v221.xml        v2.2.1: archiva 3 motivos (solo quedan No hay stock y Fin de turno)
data/parametros.xml          v2.3: koroshi_operarios.minutos_inactividad (noupdate, 0 = desactivado)
views/assets.xml             css y js en web.assets_backend
static/src/js/operarios_pantalla.js  accion de cliente koroshi_operarios_pantalla
static/src/xml/operarios.xml        plantilla de la pantalla
static/src/css/operarios.css        estilos de la pantalla (v2.3)
views/tarea_views.xml        lista, ficha, pivot, grafico, filtros, acciones
data/cron.xml                cron de cierre (5 min)
data/categoria.xml           etiqueta "Operario KOROSHI"
```
