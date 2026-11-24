# Diseño: frenar los pedidos de tienda duplicados o cancelados en S4T antes de las zonas (24/11/2026, v1)

Solo diseño. No hay código, ni versión, ni ZIP. Espera el visto bueno de Isaac (preguntas al final).

## 1. Qué pasó el 24/11 y qué falló

KOROSHI mandó los mismos 49 pedidos de tienda tres veces (S-6665004614–4662 a la 01:00, 4663–4711 a la 01:19,
4712–4760 a la 01:58). S4T canceló las dos primeras tandas; en Odoo entraron las tres, el reparto de las 04:50 las
metió todas en Z-2411-D1/D2/D3/MU2 y JUNTAR, y se prepararon pedidos cancelados y duplicados (unas 450 uds a DEV,
OUT canceladas y recreadas a mano toda la mañana). Detalle: `20261124_OUT-de-pedidos-cancelados-S4T_sacar-de-zonas.md`
y `20261124_pedidos-apuntados-isaac_triplicados.md`.

Comprobado en el código (regla 10):

- El reparto coge **todas** las OUT `assigned` del tipo «PED. TIENDAS» creadas desde medianoche (y de días anteriores
  con `dias_atras`): `odoo/modulos/koroshi_zonas/models/lector.py:57-64`. No mira si hay dos pedidos de la misma
  tienda ni el estado en S4T.
- En Odoo no hay nada que lea el estado CANCELLED de S4T (`correo-s4t-cancelaciones-bidireccional_2026-11-20.md`,
  sin respuesta de S4T).
- **Ojo, segunda puerta**: aunque una OUT quede fuera de las zonas, el reparto automático de operarios la da como
  «OUT suelta» (sin agrupación Z-): `odoo/modulos/koroshi_operarios/models/reparto.py:426-443`. Apartarla solo en
  zonas no basta.
- **Ojo, tercera**: la reserva por prioridad (`koroshi_s4t_pedidos` 1.2.0, sin instalar; cron 03:30 UTC) reserva
  primero el número S4T **más bajo**. Una noche como la del 24/11 daría el stock a las tandas canceladas (las más
  bajas) y dejaría corta la buena. Ya pasó sin ese cron: K72 4627 quedó en 46 pedidas / 37 reservadas.

## 2. Qué se comprueba

Cada noche, sobre los pedidos S- de tienda (tipo «PED. TIENDAS», compañía 8) **creados en la noche**: desde las 14:00
hora local del día anterior (parámetro) hasta el momento de la comprobación.

**A. Duplicados por tienda.** Tienda = dirección de entrega `K##`. Si una tienda tiene más de un pedido en la noche,
sus pedidos quedan **retenidos**, todos (motivo «duplicado»).

**B. Cancelados en S4T.** Se pregunta a la API de S4T el estado de los pedidos de la noche. Los CANCELLED quedan
retenidos (motivo «cancelado en S4T»). Solo GET y siempre `viewed=true` (nunca `viewed=false`: marcaría los nuevos
como vistos). En código de módulo con `requests` y timeout de 30 s; la clave, de `s4t.config`.

**A + B juntos (propuesta, P1).** Si una tienda tiene varios pedidos y S4T dice que **solo uno** sigue vivo, ese pasa
normal a las zonas y se retienen solo los cancelados. Así el 24/11 habrían ido a zonas los 49 buenos (tanda 01:58) y
se habrían quedado fuera los 98 cancelados, sin esperar a nadie. Si S4T no contesta o hay más de un vivo, se retienen
todos los de esa tienda, como pide la regla A.

**Si S4T no contesta**: la comprobación A se hace igual; el aviso dice «S4T sin respuesta: no se ha mirado si hay
cancelados». Nunca para el reparto de zonas.

**Nunca cancela nada.** Retener = no entra en zonas ni en el reparto de operarios hasta que una persona decide.

### Lo que falta saber de la API (P0)

No he podido confirmar qué endpoint da el estado: `openapi.json` pide usuario (HTTP 401) y en el repo no está el
resultado de la acción 1987 («pedidos del día en la API», 24/11). En `20261124_pedidos-apuntados-isaac_triplicados.md`
pone «los que salen CANCELLED en la API», así que parece que `GET /orders/b2b?viewed=true` trae un campo de estado.
Hace falta la salida de la 1987 (nombre del campo, valores, si se puede filtrar por número o fecha, y cuánto tarda
paginando). Sin eso, la parte B no se programa: la A funciona sola.

### ¿Hay noches normales con dos pedidos de la misma tienda? (antes de encender)

No lo sé. Con las salidas del 10/07 al 20/11 (`20261120_salidas_MASTER_odoo.csv`, por fecha de **salida**) hay 216
tienda-día con más de un S-, pero esa fecha no es la de entrada y no distingue noches. He dejado una acción de **solo
lectura** que lo cuenta por fecha de creación del pedido, 90 días:
`bin/versiones/20261124_accion-contar-pedidos-tienda-por-noche_SOLO-LECTURA.py`. Si salen noches normales con dos
pedidos (p. ej. implantación + reposición), la regla A necesita una excepción (P3).

## 3. Dónde se engancha

Propuesta: **un módulo nuevo pequeño, `koroshi_retener_tiendas`**, con la comprobación, la tabla y la pantalla, y dos
enganches de pocas líneas en los módulos que reparten trabajo. Sin campos nuevos en `stock.picking`,
`stock.picking.type` ni `stock.move.line` (regla 7): todo va en una tabla propia.

**Tabla propia `koroshi.pedido.retenido`** (una fila por pedido retenido): pedido (`sale.order`), tienda, noche,
motivo (duplicado / cancelado en S4T / los dos), estado S4T leído, otros pedidos de la tienda esa noche, estado
(retenido / preparar / cancelado a mano), quién decide y cuándo.

**Cuándo se comprueba**:
1. El cron de zonas (`cron_partir`, `koroshi_zonas/models/ejecucion.py:647`) llama a la comprobación **justo antes
   de leer** las OUT, dentro de un try: si falla, se reparte como hoy y se avisa. Así el orden está garantizado
   (no depende de la hora de dos crons).
2. Un cron propio a las 05:45 hora local por si entra algo después de las 04:50, y para mandar el aviso antes de las
   06:00 si hay retenidos sin decidir.

**Enganches** (cada uno solo si existe la tabla, para que nada dependa del módulo nuevo):
- `koroshi_zonas/models/lector.py`: quitar de `candidatas` las OUT de pedidos retenidos y apuntarlas en
  `saltadas_lector` con el motivo (salen en el informe del reparto). Unas 10 líneas. Con `prueba_ids` o
  `prueba_agrupacion` no se toca nada.
- `koroshi_operarios/models/reparto.py:431`: `('id', 'not in', OUT retenidas)` en el dominio de las OUT sueltas.
  2-3 líneas.
- `koroshi_s4t_pedidos` (reserva por prioridad, sin instalar): saltarse los retenidos. Se hace en la misma sesión que
  la tenga, no en esta (P4).

**Alternativa que toca menos y descarto**: solo el módulo nuevo, quitando la reserva a las OUT retenidas (pasan a «En
espera» y ni zonas ni operarios las cogen, porque buscan `assigned`). No sirve sola: el planificador de Odoo, la
reserva por prioridad o un «Comprobar disponibilidad» las vuelven a reservar y entonces sí se reparten como sueltas.
Sí la propongo como **complemento** para los cancelados en S4T (P2).

## 4. Qué ve el responsable

- **Correo** a las 04:50 (con el reparto) y a las 05:45 si sigue habiendo retenidos sin decidir, a los del parámetro
  `koroshi_retener_tiendas.avisar` (de inicio isaac.andreu@nath.es): asunto «KOROSHI: N pedidos de tienda retenidos
  (M tiendas)» y la lista tienda → pedidos:

  ```
  K48 (3 pedidos esta noche)
     S-6665004614  01:00  185 uds  S4T: CANCELLED   RETENIDO
     S-6665004663  01:19  185 uds  S4T: CANCELLED   RETENIDO
     S-6665004712  01:58  367 uds  S4T: PENDING     a zonas (único vivo en S4T)
  ```
- La misma lista en el **informe del reparto** (canal «KOROSHI Partir OUT zonas»), en «saltadas».
- **Pantalla** Inventario > KOROSHI Zonas > Pedidos retenidos (lista agrupada por tienda, en rojo los de hoy sin
  decidir), con dos botones por pedido:
  - **Preparar este**: deja de estar retenido. Sus OUT van como sueltas al reparto de operarios (las zonas de hoy ya
    están hechas) o a la siguiente ronda de zonas (P5).
  - **Ya cancelado en Odoo**: solo apunta la decisión; la cancelación la hace la persona en la OUT, como siempre.
- En el **Monitor**, un aviso «N pedidos retenidos» enlazado a esa lista: fase 2, porque `koroshi_monitor` 1.44.0
  está sin instalar y la tiene otra sesión.

## 5. Choques con otras sesiones (regla 6)

- **`koroshi_zonas`**: la 1.7.0 (avisos y vigilante) está hecha **sin instalar** por «Correcciones revisión general»,
  y «Zonas: mejorar» tiene prevista la 1.8.0 (modo del día). Además, `bin/versiones/diseno-zonas-modo-del-dia_2026-11-20.md`
  tiene ahora 26 líneas sin commitear: alguien la está tocando. El enganche en zonas lo tiene que hacer quien tenga el
  módulo, o Isaac me lo pasa; la versión sería la siguiente libre (1.8.0 o 1.9.0).
- **`koroshi_operarios`** (2.24.0): no veo en TABLERO quién la tiene ahora; preguntar antes.
- **`koroshi_s4t_pedidos`** (reserva por prioridad): «Feed S4T sin serialize» / «Correcciones revisión general».
- Este cambio toca **tres módulos** (nuevo + zonas + operarios): lo digo antes de empezar, como pide la regla 6.

## 6. Orden de instalación propuesto

1. Lanzar la acción de solo lectura (contar noches) y pasarme la salida de la 1987 (P0, P3).
2. `koroshi_retener_tiendas` 1.0.0 en **modo aviso**: comprueba, guarda y manda el correo, pero los enganches no
   apartan nada (parámetro `modo` = aviso). Una semana mirando si lo que retendría cuadra.
3. Enganches en zonas y operarios, instalados uno a uno, fuera de horas, nunca el mismo día antes de las 04:50 sin
   avisar.
4. `modo` = real.

## 7. Preguntas para Isaac

- **P0.** ¿Me pasas la salida de la acción 1987 de esta mañana (campos de estado de `/orders/b2b?viewed=true`)?
- **P1.** Con S4T contestando, si una tienda tiene varios pedidos y solo uno vivo en S4T, ¿ese pasa solo a zonas? (Yo
  diría que sí.) ¿O siempre se retienen todos y decide una persona?
- **P2.** A los cancelados en S4T, ¿les quito la reserva al retenerlos y vuelvo a reservar el pedido vivo de la misma
  tienda? (El 24/11 habría evitado el 46/37 de K72.) A los duplicados sin respuesta de S4T, no.
- **P3.** ¿Hay noches normales en que una tienda recibe dos pedidos (implantación + reposición, por ejemplo)? Lo dirá
  la acción de solo lectura.
- **P4.** ¿La reserva por prioridad (`koroshi_s4t_pedidos` 1.2.0) se ajusta antes de instalarla para saltarse los
  retenidos? Hoy daría el stock a las tandas canceladas.
- **P5.** Un pedido que se libera después de las 04:50, ¿va como OUT suelta o esperamos a la segunda ronda de zonas?
- **P6.** ¿Quién hace el enganche en `koroshi_zonas` y en `koroshi_operarios` (las sesiones que los tienen o esta)?
- **P7.** ¿A quién va el correo, además de a ti? (Erika, Betty, el jefe del turno de mañana.)

## 8. Hecho el 24/11 (con el «sí, adelante» de Isaac): koroshi_retener_tiendas 1.0.0, SIN INSTALAR

- Módulo nuevo `odoo/modulos/koroshi_retener_tiendas` (tabla propia, sin campos en tablas compartidas). Se instala en
  **modo aviso** (`koroshi_retener_tiendas.modo` = aviso: revisa, guarda y manda el correo; no aparta nada) y **sin
  preguntar a S4T** (`koroshi_retener_tiendas.s4t` = 0) hasta tener P0. Lo de P1 va como está en el diseño (el único
  vivo en S4T pasa).
- Sin hacer todavía: P2 (quitar la reserva a los cancelados), los enganches en `koroshi_zonas` y `koroshi_operarios`
  (P6: los tienen otras sesiones) y el ajuste de la reserva por prioridad (P4). Hasta entonces, el modo real no
  aparta nada aunque se encienda.

## 9. Comprobado en producción el 24/11 (solo lectura) y koroshi_retener_tiendas 1.1.0, SIN INSTALAR

- **P0 resuelta.** La acción 1987 no había llegado a funcionar: da `NameError: requests` (las acciones de servidor no
  tienen `requests`); al lanzarla no hizo nada. El estado está en el dashboard de S4T «Órdenes B2B», que llama a
  `GET /api/service/dashboard/orders/data?type=B2B&almacen_id=2&status=&date_from=&date_to=` (cabecera `x-api-key`),
  con `numero_orden` y `status` (PENDING / READY / CANCELLED). No lleva `viewed`. El 24/11 da **99 CANCELLED**
  (las dos tandas y S-6665004737, cancelada después). La 1.1.0 pregunta ahí y viene con `s4t` = 1.
- **La tienda no está en el cliente del pedido**: `partner_id` es «DIGITAL E-GLOBAL XPERIENCE, SL»; la tienda es la
  dirección de entrega, contacto hijo con `name` = «K60 - LOS PRADOS». El módulo ya leía `partner_shipping_id.name`.
  En 120 días, 3.393 pedidos y todos tienen tienda K##.
- **P3 resuelta (duplicados).** Con «toda la noche desde las 14:00» salen 13 noches con alguna tienda repetida; 11
  son un pedido de tarde (14:15, 15:00, 17:15) más el de la noche, a 9-11 h, pedidos distintos. Con «pedidos de la
  tienda a menos de 3 h uno de otro, entrados antes de las 04:40» solo salen **2 noches: 07/10 (50 tiendas, 100
  pedidos) y 24/11 (49 tiendas, 147 pedidos)**, los dos incidentes reales. Ningún falso aviso. Parámetro
  `ventana_horas` = 3.

## 10. koroshi_retener_tiendas 1.2.0 (24/11), SIN INSTALAR: pedidos con menos de 20 uds reservadas

- **Lo pide Isaac:** un pedido de tienda con menos de 20 uds **reservadas en Odoo** no se prepara ni va a zonas,
  aunque en S4T pida 20 o más (cuenta el stock que hay). Correo aparte a betty@nath.es, j.luis@nath.es e
  isaac.andreu@nath.es con tienda, pedido, pedidas y reservadas. Sale una vez por pedido (a las 04:40 o a las 05:45).
- **Cancelar como en la web**: hecho pero **apagado** (`cancelar_pocas` = 0). Con 1, cancela sus OUT igual que el
  corte de pedidos web: solo las que no tienen nada leído, no están validadas, no están en una agrupación Z- ni en la
  cola de un operario, cada una en su savepoint; nota en el chatter de la OUT y la fila pasa a «Cancelado en Odoo».
  Antes de encenderlo, decidir qué ve S4T de un pedido de tienda cancelado en Odoo (hoy no hay nada que se lo diga;
  ver `correo-s4t-cancelaciones-bidireccional_2026-11-20.md`).
- **Medido en Odoo (solo lectura, 35 días)**: pedidos de tienda por noche que piden menos de 20 uds: entre 0 y 25
  (12/11: 25 de 47; 20/11: 14 de 51; 30/10: 17 de 48; la mayoría de noches 0-5). Con lo reservado serán algunos más.
  Mínimo en el parámetro `minimo_uds` (0 = apagado).

## 11. koroshi_retener_tiendas 1.3.0 (24/11), SIN INSTALAR: cancelar encendido

Isaac dice que sí a cancelar: `cancelar_pocas` = 1 de inicio. Los pedidos de tienda con menos de 20 uds reservadas
se cancelan (sus OUT, como las de la web) en la revisión de las 04:40, también en modo aviso. En S4T siguen PENDING.
