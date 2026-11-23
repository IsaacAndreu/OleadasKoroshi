# Prompt para Fable: revisión general del almacén KOROSHI (23/11/2026)

Copiar todo lo que hay debajo de la línea en una sesión nueva con **Fable** (esfuerzo high), en la carpeta
`C:\dev\OleadasKoroshi`.

---

Eres el revisor de todo el trabajo de Odoo del almacén KOROSHI (Odoo 13 EE, nath.tuctuc.com, compañía 8). Durante
noviembre de 2026 se ha hecho mucho en poco tiempo, en unas 20 sesiones paralelas. Isaac (soporte del almacén)
quiere que alguien lo mire todo con calma y le diga:

1. **Qué nos estamos dejando**: cosas empezadas que no se han acabado, versiones empaquetadas sin instalar,
   preguntas sin contestar, pruebas en PDA que nadie ha hecho y diseños que esperan una respuesta.
2. **Qué no estamos haciendo y deberíamos hacer**: riesgos (stock, PDA parada, datos, seguridad, rendimiento),
   controles que faltan, cosas que se rompen sin que nadie se entere y procesos del almacén que siguen a mano.
3. **Qué se puede optimizar o simplificar**: duplicados entre módulos, código común que no está en `koroshi_base`,
   pantallas o pasos de más para el operario y cosas lentas.
4. **En qué orden**: una lista corta priorizada (lo que más duele al almacén primero), con esfuerzo estimado.

## Reglas

- **Solo leer.** No cambies código, no empaquetes, no instales y no toques el servidor ni la base de datos. Si para
  decidir algo necesitas datos reales, dilo y propón la consulta (solo lectura). Isaac decide.
- Todo en castellano.
- Cada afirmación con su fuente (`archivo:línea`, línea de TABLERO, memoria o commit). Si no lo has podido
  confirmar, dilo («sin confirmar»).
- No repitas lo que ya está bien: interesan los huecos.

## Qué leer (en este orden)

1. `CLAUDE.md`: las reglas no negociables. Comprueba también si se cumplen de verdad.
2. `TABLERO.md`: qué está en curso, qué espera a alguien y qué está hecho sin instalar.
3. `TRASPASO_AUDITORIA.md`: la auditoría del 13/11 por fases. ¿Qué quedó pendiente?
4. `README.md`: el mapa de módulos y el despliegue.
5. La memoria del proyecto: `C:\Users\tuctuc\.claude\projects\C--dev-OleadasKoroshi\memory\MEMORY.md` y sus
   ficheros. Son las lecciones aprendidas. ¿Hay alguna que el código aún no tiene en cuenta?
6. `git log --oneline -150` y las etiquetas (`git tag`): qué se ha hecho y en qué versiones.
7. `bin/versiones/`: diseños, correos y planes. Busca diseños que acabaron sin código o sin decisión, por ejemplo
   recepciones, reserva de tiendas por prioridad, prenda en el suelo, comprobar inventario, tablero del
   responsable y la inversa.
8. `odoo/modulos/*`: los módulos. Repasa en especial los que usa la PDA todo el día: `koroshi_operarios`,
   `koroshi_preparacion`, `koroshi_contenedores`, `koroshi_faltantes`, `koroshi_zonas` y `koroshi_actividades`.
9. `bin/comprobar.py`, `bin/empaquetar.py` y `bin/desplegar.sh`: ¿cubren las trampas que ya conocemos?

## Cosas ya vistas el 23/11 para que las tengas en cuenta (compruébalas, no las des por buenas)

- **Validar en Preparación** (`/koroshi/preparacion/validar`) tarda a menudo 30-50 s en el log del servidor (unas
  15 veces solo la mañana del 23/11). Es lo que hacen los operarios al acabar cada OUT.
- **Lecturas no se refresca sola**: si desde otra pantalla (Contenedores, Faltantes) se cambia la reserva de una
  línea a otro hueco, la PDA que tiene la OUT abierta sigue enseñando el hueco viejo hasta que sale y vuelve a entrar
  (`koroshi_preparacion/static/src/js/preparacion.js` `_aplicar` ~309-334; el estado «ligero» no trae ubicación).
- **PDA que «clica dos veces»**: un operario tenía 3 cajas y la pantalla le ponía 4 al cerrar caja.
- **Monitor**: unidades de zonas y de web que no cuadran (7.056 frente a 6.980).
- **Pedidos web de KOROSHI**: la serie principal 0000059xxx dejó de entrar el 20/11 a las 16:00, también en S4T.
  Entran las series 593/592/591. Nadie lo ha confirmado con KOROSHI.
- **Contenedores 1.11/1.12** (23/11): «Poner a cero» y «Cambiar» por debajo de lo reservado pasan las líneas por
  Faltantes. Es nuevo y no se ha probado en PDA.
- **Errores de talla** (llega una caja «34» que es «36»): no hay forma de cambiar unidades de un artículo a otro sin
  que la tienda lo note.
- **Imprimir desde la PDA**: aplazado (impresoras por cable a los PC). La idea es una cola en Odoo más un script en
  cada PC.
- **Secretos**: `App.config`, `bin/Release/PedidosMultiples.exe.Config` y varios `.cs` de `PedidosMultiples/`
  tienen credenciales versionadas pendientes de rotar.
- **Muchas versiones «hechas sin instalar»** en TABLERO (unas 8 líneas): ¿cuáles siguen teniendo sentido y cuáles
  se han quedado viejas?
- **Grabación del almacén del 23/11** (`C:\Users\tuctuc\Videos\Nueva grabación 32_1975.txt`): recepciones por
  contenedor (diseño v3 en `bin/versiones/`), ordenar por EAN, modelo, colección y familia con colores, picos,
  palets 1..N con cara A/B, trazabilidad de movimientos por operario y prioridades dichas en voz alta (moda íntima
  y la inversa primero; recepciones es lo que «hace sufrir»).
- **odoo.tuctuc.com** (otro Odoo, otro servidor) tarda de 5 a 20 min en buscar productos y en el stock agrupado.
  Ya hay una sesión aparte («Rendimiento odoo.tuctuc.com»): no lo dupliques, solo tenlo en cuenta.

## Qué entregar

Un único fichero nuevo `bin/versiones/revision-general-fable_2026-11-23.md` (no sobrescribas nada) con:

1. **Resumen en 10 líneas** para Isaac: lo más importante.
2. **Tabla «nos lo estamos dejando»**: qué, dónde (fuente), desde cuándo, quién tiene que hacer qué
   (Isaac / almacén / KOROSHI / S4T / una sesión) y riesgo si no se hace.
3. **Tabla «deberíamos hacer»**: riesgos y controles que faltan, con la propuesta.
4. **Tabla «optimizar o simplificar»**: con el ahorro esperado (tiempo de operario, segundos de pantalla,
   errores evitados).
5. **Plan priorizado**: las 10 primeras cosas, en orden, con esfuerzo (S/M/L), el módulo que tocan y si tocan
   tablas compartidas (`stock.picking`, `stock.picking.type`, `stock.move.line`: regla 7, hay que preguntar).
6. **Preguntas para Isaac**: solo las que bloquean algo, cada una con sus opciones.

Haz commit solo de ese fichero, con
`git -c user.name="Isaac Andreu" -c user.email=isaacandreu76@gmail.com commit -- bin/versiones/revision-general-fable_2026-11-23.md`
y el trailer `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`. Después, para y espera a Isaac.
