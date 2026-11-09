# Prueba fuera de horas: koroshi_faltantes v1.1 (09/11/2026)

La v1.1 añade la **ronda de revisión** (una INT con los faltantes). Sustituye al plan v1.0: el paso 6 es nuevo y el 7 cambia un poco.

Esta prueba **escribe stock de verdad en nath.tuctuc.com**: cambia reservas y hace movimientos a y desde EFFEC/FALTANT.
- Solo se hace **con el OK de Isaac** y **fuera de horas** (sin PDAs trabajando), igual que cualquier instalación.
- No se pulsa nunca «Forzar disponibilidad».
- No se valida la OUT de prueba: validarla enviaría stock al cliente.
- No se borra nada.

## 0. Antes

1. Copia de seguridad de la base de datos (o confirmar que el backup de esa noche está hecho).
2. Comprobar que hay estos ZIP en `bin/`:
   - `20261109_koroshi_operarios_v1.2.zip` (la v1.2 es compatible: la pantalla y las tareas no cambian);
   - `20261109_koroshi_faltantes_v1.1.zip`.
3. Instalar en este orden, fuera de horas:
   1. `koroshi_operarios`, porque `koroshi_faltantes` depende de él y hoy no está instalado;
   2. `koroshi_faltantes`.
4. Comprobar, después de instalar:
   - [ ] *Inventario > Configuración > Ubicaciones*: existe **EFFEC/FALTANT**.
     - Es interna y su padre es **EFFEC**, no EFFEC/Stock.
     - Su código de barras es `FALTANT` y la empresa es EFFECTIVE LOGISTICS.
   - [ ] Menú *Inventario > KOROSHI Faltantes* con *Faltante (PDA)*, *Revisión de faltantes*, *Crear ronda de
     revisión*, *Rondas de faltantes (INT)* y *Puestos a 0 hoy*.
   - [ ] *Ajustes > Técnico > Acciones planificadas*: existe **KOROSHI Faltantes: actualizar rondas** (cada 15 min).
   - [ ] La pantalla de Operarios tiene el botón rojo **Faltante**.
   - [ ] La app de código de barras abre una OUT normal como siempre. Este módulo no la toca, pero se mira igualmente.

## 1. OUT de prueba

Se crea una OUT a mano. Así no se toca ningún pedido real.
1. *Inventario > Transferencias > Crear*, tipo **6665 STOCK GENERAL KOROSHI: Órdenes de entrega**, origen EFFEC/Stock, a un
   contacto de pruebas, con referencia de origen `PRUEBA FALTANTES`.
2. Añadir 1 ud de cada uno de estos artículos. El 09/11 tenían stock libre en varias cajas; mirar que siga siendo así:

   | | Artículo | Id | Para probar |
   |---|---|---|---|
   | A | `2421JA51-000030-XL` | 582392 | reubicar (4 cajas en L18 P35 C1) |
   | B | `2421PL26-000030-XXL` | 583467 | línea con algo leído |
   | C | `2421SU30-000123-M` | 584152 | «No está en ningún sitio» |

3. **Marcar como por realizar** y **Comprobar disponibilidad**. Apuntar el nombre de la OUT (`EFFEC/OUT/…`).
4. Para cada artículo, apuntar la **caja reservada** (*Operaciones detalladas*). Apuntar también, en *Inventario > Informes >
   Existencias* filtrando por el artículo, la **cantidad** y lo **reservado** de cada caja y de FALTANT. Esta es la foto de
   antes.

## 2. Reubicar (artículo A)

1. PDA (o navegador): pantalla **Faltante**. Leer la OUT y el EAN de A.
   - [ ] Sale **Reservada en** con la caja apuntada y 1 ud.
   - [ ] Salen hasta 5 ubicaciones con stock libre: no sale la reservada y salen primero las del mismo lineal (L18).
2. Leer **otra caja** de la lista.
   - [ ] Mensaje verde «Hecho: la línea pasa a … 1.0 ud a FALTANT».
3. Comprobar en Odoo:
   - [ ] *Operaciones detalladas* de la OUT: la línea de A ahora es de la caja nueva y la OUT sigue **Preparada**.
   - [ ] Existencias de A:
     - caja nueva: reservado **+1**;
     - caja vieja: reservado **−1** y cantidad **−1**;
     - FALTANT: cantidad **+1**, reservado 0.
   - [ ] *Inventario > Informes > Movimientos*: hay un movimiento hecho «KOROSHI Faltante EFFEC/OUT/…» de la caja vieja a
     FALTANT.
   - [ ] *Revisión de faltantes*: hay una línea **Pendiente**, de tipo **Reubicado**, con OUT, artículo, ubicación vieja y
     nueva, usuario y, si se leyó tarjeta, operario.

## 3. Casos que no deben cambiar nada

Antes y después de cada uno, mirar en las existencias de A que nada haya cambiado.
- [ ] Leer otra vez el EAN de A y después la **misma caja donde ya está reservada** → mensaje rojo «Es la misma ubicación…».
- [ ] Leer una ubicación **sin stock** de A → «En … no hay stock libre…».
- [ ] Leer un código que **no es una ubicación** (p. ej. otro EAN) en el paso de la ubicación → «… no es una ubicación».
- [ ] Artículo B: en la app de código de barras, abrir la OUT, **leer 1 ud de B** y salir con la flecha atrás. En Faltante,
  leer la OUT y el EAN de B → «Esta línea ya tiene 1.0 uds leídas…» y no se puede hacer nada.
  - Después, en la OUT, quitar lo leído de B: dejar `qty_done` a 0.

## 4. «No está en ningún sitio» (artículo C)

1. En Faltante: leer la OUT y el EAN de C y pulsar **No está en ningún sitio**.
   - [ ] La primera pulsación cambia el texto a «Pulsa otra vez para confirmar» y no hace nada.
   - [ ] Si se espera 5 s, vuelve al texto normal.
2. Pulsar dos veces.
   - [ ] Mensaje verde «la línea queda sin reserva…».
3. Comprobar en Odoo:
   - [ ] La OUT ya no tiene línea de C. El movimiento de C queda **Esperando / Parcialmente disponible**, y la OUT
     **no** está cancelada.
   - [ ] Existencias de C: caja vieja con reservado **−1** y cantidad **−1**; FALTANT con **+1**.
   - [ ] En Revisión hay una línea de tipo **Sin alternativa**, Pendiente.

## 5. Volver a la OUT y Operarios

- [ ] En Faltante, **Volver a la OUT**: se abre la OUT en la app de código de barras y A sale con la caja nueva.
  - Salir con la **flecha atrás**. No validar.
- [ ] Desde la pantalla de **Operarios**, pulsar **Faltante**, leer la OUT, **Volver a la OUT** y la flecha atrás: tiene
  que volver a **Operarios**, no a Faltante.
- [ ] Si la OUT es de una agrupación `Z-`, **Volver a la OUT** abre la agrupación. Solo se puede probar si hay una
  agrupación Z- de prueba; si no, se prueba el primer día de uso.

## 6. Ronda de revisión (INT)

Para este paso hacen falta en FALTANT los dos faltantes de los pasos 2 (A) y 4 (C).

1. *Crear ronda de revisión*.
   - [ ] Se abre una INT nueva `EFFEC/INT/…`, con origen `RONDA FALTANTES dd/mm hh:mm`, de **EFFEC/FALTANT** a EFFEC/Stock.
   - [ ] Tiene **2 líneas**: A hacia su caja vieja y C hacia su caja vieja, ordenadas por lineal. Las dos están
     **reservadas** (estado *Preparado*).
   - [ ] En *Revisión de faltantes*, A y C tienen la columna **Ronda** con esa INT. Los botones Encontrado / No encontrado
     no salen.
   - [ ] Volver a pulsar *Crear ronda de revisión* → «No hay faltantes pendientes…». No se crea una segunda INT con los
     mismos.
   - [ ] Comprobar que ninguna OUT ha reservado en FALTANT: en Existencias de FALTANT, lo reservado debe coincidir solo
     con las líneas de esta INT.
2. **PDA:** abrir la INT en la app de código de barras.
   - [ ] Las líneas salen en orden de lineal. Si no, apuntarlo: es solo comodidad.
   - **A:** leer el artículo A y **otra caja** distinta de la vieja, como si se hubiera encontrado en la caja de al lado.
   - **C:** no leer nada.
3. **Validar** → Odoo pregunta por lo que falta → **Crear pedido pendiente**.
   - [ ] La INT queda *Hecho* y se crea una INT pendiente nueva con la línea de C.
4. Esperar al cron (15 min) o, para no esperar, *Ajustes > Técnico > Acciones planificadas > KOROSHI Faltantes:
   actualizar rondas > Ejecutar manualmente*.
   - [ ] A: **Encontrado**, con *Devuelto a* = la caja leída en el paso 2, no la vieja.
   - [ ] En Existencias de A: FALTANT con **−1** y la caja leída con **+1**.
   - [ ] C: sigue **Pendiente**, con *Ronda* = la INT pendiente nueva y *Rondas* = 2.
5. Abrir la INT pendiente de C en la PDA, no leer nada y **Validar → Sin pedido pendiente**.
   - Si Odoo no deja validar sin nada leído, **cancelar esa INT** y mirar el punto 7.
   - [ ] Después del cron: C pasa a **No encontrado**. Hay un movimiento de FALTANT a *Inventory adjustment* (pérdidas) y
     la nota dice «No encontrado en la ronda …».
   - ⚠️ Esto manda 1 ud de C a pérdidas **de verdad**. Si la ud existe físicamente, devolverla al final con un ajuste de
     inventario de +1 en su caja (paso 8). Si se prefiere no tocar pérdidas, hacer solo el punto 7.
6. Caso suelto: *Revisión de faltantes* → cualquier faltante pendiente **fuera** de ronda → **Encontrado** → elegir su
   caja.
   - [ ] Sigue funcionando como en la v1.0.
7. **INT cancelada:** crear una ronda con un faltante pendiente y **Cancelar** la INT entera.
   - [ ] Después del cron, el faltante vuelve a **Pendiente sin ronda**, con la nota «Ronda … cancelada». **No** pasa a
     No encontrado.
8. [ ] *Puestos a 0 hoy* abre la lista de movimientos «Cantidad de producto actualizada» de hoy. Puede estar vacía.
9. [ ] La lista de revisión se puede exportar a Excel: seleccionar > Acción > Exportar.

## 7. Deshacer y dejarlo como estaba

1. OUT de prueba:
   - **Anular reserva**, y después **Cancelar**: así queda cancelada, no borrada;
   - si quedó algo leído, quitarlo antes.
2. Si el paso 6.5 ha enviado C a pérdidas y la ud existe: **ajuste de inventario +1** en su caja.
3. Comprobar que las existencias de A, B y C son **las de la foto del paso 1** (A puede estar en otra caja del mismo hueco:
   la del paso 6.2), y que FALTANT queda con 0 y sin rondas abiertas.
4. **Si algo ha ido mal a medias**:
   - La pantalla hace todo o nada: si da error no ha cambiado nada. Aun así, comparar con la foto.
   - **Una línea que se ha quedado en otra caja:** en la OUT, *Anular reserva* + *Comprobar disponibilidad* (Odoo
     vuelve a reservar donde haya). Nunca «Forzar disponibilidad».
   - **Uds que se han quedado en FALTANT:**
     - fuera de ronda: devolverlas con **Encontrado**, o con una transferencia interna de FALTANT a la caja;
     - en una ronda abierta: hacer la INT, o cancelarla y el faltante vuelve a pendiente.
   - **Una ud mandada a pérdidas por error:** ajuste de inventario de +1 en la caja, igual que ahora cuando se pone a 0
     por error.
5. **Para no usarlo:** quitar el botón no hace falta. Basta con no entrar en la pantalla. **No desinstalar** con faltantes
   pendientes en FALTANT ni con rondas abiertas: primero hay que revisarlos.

## 8. Después de la prueba

- En *Ajustes > Usuarios*, «Almacén Nath» y «Almacen 2»: **Acción inicial = Operarios** (koroshi_operarios), solo con OK.
- Explicar al equipo que **ya no se pone a 0 desde la PDA**: se usa **Faltante**. Mirar *Puestos a 0 hoy* los primeros
  días.
