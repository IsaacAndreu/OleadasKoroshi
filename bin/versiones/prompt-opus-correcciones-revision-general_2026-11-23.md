# Prompt para Opus 5.5: correcciones de la revisión general (23/11/2026)

Copiar todo lo que hay debajo de la línea en una sesión nueva con **Opus 5.5, esfuerzo high**, en la carpeta
`C:\dev\OleadasKoroshi`.

---

Vas a corregir, por entregas, lo que encontró la revisión general del 23/11/2026 en los módulos Odoo 13 EE del
almacén KOROSHI. Los operarios preparan pedidos con PDA todo el día: un fallo se nota en el almacén al momento.

## Antes de empezar

1. Lee `CLAUDE.md` (reglas no negociables), `TABLERO.md` y
   `bin/versiones/revision-general-fable_2026-11-23.md`. Los códigos R1, R2…, O1… y C1… de este prompt son los de
   ese informe: allí está cada hallazgo con su `archivo:línea`.
2. El informe sale de **leer** el código; nada se reprodujo en Odoo. Regla 10: antes de cada cambio, abre el código y
   confirma que el fallo existe tal como se describe. Si no lo puedes confirmar, dilo y no lo arregles a ciegas.
3. Pregunta a Isaac la `installed_version` real de cada módulo antes de sacar su versión (regla 3).
4. Apúntate en «En curso» de `TABLERO.md` con el módulo de la entrega en la que estés. `koroshi_preparacion` figura
   cogido por la sesión de la ronda de faltantes: pide a Isaac que lo suelte antes de la entrega 2.

## Cómo se trabaja

- **Una entrega cada vez, en el orden de abajo.** Al acabar cada una: versión subida en el manifest, línea de
  historial, commit con rutas (`git -c user.name="Isaac Andreu" -c user.email=isaacandreu76@gmail.com commit -- <rutas>`
  y el trailer `Co-Authored-By`), `python bin/empaquetar.py <modulo>` y la línea del TABLERO en el mismo commit.
- Después, el cierre de la regla 11: qué se ha cambiado (`archivo:línea`), cómo se ha probado, qué no se ha podido
  probar y qué hay que probar en una PDA real. **Para y espera el visto bueno de Isaac** antes de la siguiente.
- No se instala, ni se sube, ni se reinicia nada en el servidor. No se tocan datos de producción. Si necesitas datos
  reales, propón la consulta de solo lectura y espera.
- Ningún campo nuevo en `stock.picking`, `stock.picking.type` ni `stock.move.line` (regla 7). Si una solución lo
  pidiera, para y pregunta.
- Todo en castellano. Lo común, a `koroshi_base` (regla 8).
- Sin node en este PC: la sintaxis JS se comprueba con `cscript` (ver `TRASPASO_AUDITORIA.md`, «Cómo se trabaja»).
- Si una entrega toca dos módulos, dilo al empezarla (regla 6). Cada módulo lleva su propia versión.
- Añade pruebas donde ya las hay (`tests/` del módulo) para la lógica que se pueda probar sin Odoo.

## Entrega 1. Contenedores y Faltantes: «Cambiar» y «Poner a cero» (R1, R2, R3, R4, R13)

Toca **koroshi_contenedores** y **koroshi_faltantes**. Es lo más urgente: la 1.12.0 está instalada desde hoy.

Lo que quiere Isaac (dicho el 23/11): al compactar, si una KO tiene una prenda reservada para una OUT y físicamente
no está, esa prenda pasa a FALTANTE y la OUT la coge en otro lineal. Eso ya funciona cuando falta la línea entera.
Hay que arreglar:

- **R1. Solo la diferencia.** Hoy `_reservas_a_faltantes` mueve la línea entera (`necesario = ml.product_qty`). Con
  una línea de 5 y 4 reales, deben quedarse 4 reservadas en la KO y pasar a Faltantes solo 1 (reubicada a otro hueco
  o, si no hay, sin reserva). Mira si la rama parcial que ya tiene `koroshi_faltantes` (`_reservar_resto_en`) sirve
  para esto. La búsqueda de hueco alternativo no debe quedarse en los 5 más cercanos si ninguno tiene la cantidad.
- **R2. Lo leído sin validar.** «Cambiar» compara solo con lo reservado. Tiene que descontar lo ya leído pendiente
  de validar (como hace `koroshi_recuentos`) o parar con un aviso claro. Elige la opción más segura y explícala.
- **R3. «Añadir prendas» sin duplicar**: clave de reintento desde la PDA, como en `koroshi_devoluciones`.
- **R4. «Poner a cero» y «Archivar»**: la unidad en FALTANTE no puede quedar con vuelta a un contenedor archivado.
  Propón la solución (cerrar el faltante como no encontrado, o que «Archivar» mire los faltantes pendientes) y espera
  el sí si cambia lo que ve el operario.
- **R13. Ronda de faltantes**: savepoint y log por faltante en `sincronizar_rondas`, para que uno malo no pare el cron.
- De paso, en estos dos módulos: nota «desde Contenedores» en el faltante y línea de registro siempre (hallazgo de
  rastro), y `COMPANY_ID` desde `koroshi_base` (O6).

Casos que hay que dejar escritos para probar en PDA: los 1 a 5 del apartado 6 del informe.

## Entrega 2. Preparación: Validar, Lecturas y Caja (R5, R6, R7, R8, O2)

Toca **koroshi_preparacion** (y **koroshi_operarios** solo si hace falta un método para cerrar la tarea propia: dilo).

- **R6. Cronómetro en Validar**: una línea de `_logger.info` con los milisegundos de cada tramo (comprobaciones,
  `button_validate`, asistente de pedido pendiente, cierre de tarea, estado) y el transportista. No se optimiza a
  ciegas: con una semana de log se decide si XPO/S4T van a cola (eso es otra entrega, no esta).
- **R6. Cerrar solo la tarea propia** al validar, en vez de `cron_cerrar()` de todo el almacén.
- **R5.** `flush()` antes de `_con_estado` y fuera del `try`, para que un error de concurrencia no se trague.
- **R7. Lecturas se refresca**: ubicación en el estado ligero; si cambia, recarga entera; refresco periódico también
  yendo solo (unos 30 s; pon el intervalo en un parámetro).
- **R8. Botón Caja** desactivado y CJ ignorada mientras hay una caja en vuelo, con aviso «Cerrando caja…».
- **O2.** Tipo de caja preseleccionado con el último usado. Pregunta antes si el almacén lo quiere así.

## Entrega 3. Avisos cuando un cron falla (R9, R10, R11, R12, R18, R14)

Un módulo y una versión cada vez, en este orden. Destinatarios siempre en parámetros, nunca en el código.

1. **koroshi_zonas** (R9): `cron_partir` envuelto, correo si el estado no es «hecho», y vigilante a las 05:15 hora
   local: «¿hay reparto real de hoy?».
2. **koroshi_agrupaciones_web** (R10): `ultimo_corte` después de hacerlo, savepoint por OUT, correo si falla o se salta.
3. **koroshi_s4t_envios** (R11): los errores de red no cuentan como intento, cortar la pasada tras 3 fallos de red
   seguidos, correo resumen; crear el parámetro `avisar` en los datos del módulo.
4. **koroshi_s4t_traspasos** (R12): recalcular el producto al procesar y correo diario con los que están en error.
5. **koroshi_informe** (R18): comprobar el estado del correo tras enviar.
6. **koroshi_menu** (R14): en la bandeja, faltantes pendientes en rojo si pasan de N días.

Cuidado con Zalando y About You: no cambies qué se envía ni qué se cancela, solo quién se entera cuando falla.

## Entrega 4. Reserva de tiendas por prioridad (R15)

**koroshi_s4t_pedidos** (1.1.0 hecha y sin instalar: sale una versión nueva, no se sobrescribe). Volver a comprobar
«no empezada» dentro del savepoint de cada artículo, bloquear el botón manual en horario de trabajo y que no pueda
coincidir con el reparto de zonas (si eso obliga a tocar `koroshi_zonas`, dilo antes). Sigue entrando en SIMULAR.

## Entrega 5. «Cambiar artículo» para los errores de talla (R23)

**koroshi_contenedores**. Primero un diseño corto en `bin/versiones/` (qué ve el operario, qué movimientos de stock
hace, qué registro deja, qué pasa si hay reservas) y **espera el sí de Isaac** antes de programar.

## Entrega 6. Lo común en koroshi_base (O4, O5, R16, O6)

Primero **koroshi_base** (lector «leer al parar», tarjeta de operario, búsqueda de producto por EAN,
`_empleado_valido` y `_comprobar_grupo`). Después, pasar los módulos uno a uno, cada uno con su versión: faltantes,
devoluciones, recuentos, contenedores, preparación. `koroshi_prenda_suelo` 1.0.0 no está instalado: versión nueva.
Recuerda que actualizar operarios o base arrastra a los dependientes en la misma pasada: dilo en el cierre.

## Entrega 7. Herramientas del repo (R19, R20, O10)

Sin módulos: `bin/comprobar.py` (constantes de `koroshi_base` copiadas como error; ruta `auth='user'` sin grupo y
`except Exception` sin log como avisos; arreglar el E6 de `oriola_monitor`), `bin/desplegar.sh` (en `check`, listar
los dependientes que se actualizarán y avisar si es horario de trabajo) y `README.md` (tabla de módulos al día).

## Entrega 8. Monitor (R22, O7)

**koroshi_monitor**. Antes, pide a Isaac el resultado de la consulta C1 del informe (7.056 frente a 6.980). Después:
candado de la caché por clave, caché propia para `_prioridad`, y una etiqueta en pantalla que diga si la cifra es
«pedidas» o «reservadas». Mira en el TABLERO si la sesión «Millores del Monitor picking» lo tiene cogido.

## Fuera de este encargo (no lo hagas)

- Recepciones por contenedor (`koroshi_recepcion`): tiene su sesión y su diseño v6.
- Push del repo, rotar credenciales, correos a KOROSHI y a S4T, y cualquier cosa en el servidor: son de Isaac.
- `tuctuc_rendimiento` y odoo.tuctuc.com: otra sesión.
- Sacar XPO/S4T de la validación a una cola: solo después de ver los tiempos de la entrega 2.

Empieza por «Antes de empezar» y por la entrega 1. Al acabar cada entrega, para y espera a Isaac.
