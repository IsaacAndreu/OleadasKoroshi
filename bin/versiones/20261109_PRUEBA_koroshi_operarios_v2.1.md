# Prueba fuera de horas: koroshi_operarios v2.1 + koroshi_faltantes v1.2 (09/11/2026)

Sustituye a `20261109_PRUEBA_koroshi_operarios_v2.0.md` (la v2.0 no se llegó a instalar).

ZIP: `20261109_koroshi_operarios_v2.1.zip` y `20261109_koroshi_faltantes_v1.2.zip`.
Script: `actualizar_koroshi_operarios_v2.1_faltantes_v1.2_2026-11-09.sh` (`check` y después `install`).
Después: Aplicaciones > Actualizar lista > *KOROSHI Operarios* Actualizar > *KOROSHI Faltantes* Actualizar > Ctrl+F5.

Usar el operario de prueba **Isaac (OP9990001)** y otro de prueba (Isaac2, OP9980001). No validar OUT reales.

## 1. Instalación

- [ ] Menús nuevos en *KOROSHI Operarios*: **Reparto de hoy**, **Colas**, **Motivos para saltar** (solo IT,
  Almacén Nath y Almacen 2).
- [ ] *Motivos para saltar*: 5 motivos (sin stock → oficina, falta material → final, muy grande → oficina,
  fin de turno → sigue suya, otro → oficina y pide texto).
- [ ] En la lista de albaranes y de agrupaciones: *Acción > Asignar a operario*.

## 2. Reparto manual

1. *Reparto de hoy* → modo **C · Solo manual**. Guardar.
2. Lista de albaranes → seleccionar 2 OUT preparadas sueltas → *Asignar a operario* → Isaac.
   - [ ] En *Colas* salen las 2 en «En cola», origen «Responsable».
   - [ ] Asignar una de ellas a Isaac2 la pasa a Isaac2 (no se duplica).

## 3. PDA

1. *Lecturas (PDA)* → leer **OP9990001**.
   - [ ] Sale «Isaac» y se abre **sola** la primera OUT. En *Colas* pasa a «Haciéndose» y hay una tarea en *Tareas*.
2. **Flecha atrás** (sin validar).
   - [ ] Se queda en la pantalla con «Estás haciendo …» y los botones **Continuar**, **Saltar**, **Faltante**.
   - [ ] **Continuar** la vuelve a abrir.
3. Flecha atrás → **Faltante**.
   - [ ] La OUT ya está puesta: pide el EAN. (No completar el faltante en una OUT real: «Salir».)
4. Recargar la página (F5).
   - [ ] Sigue saliendo Isaac sin leer la tarjeta y no se abre nada solo.
5. **Saltar → Falta material**.
   - [ ] Se abre sola la siguiente. La saltada sale al final de su cola.
6. **Saltar → Fin de turno**.
   - [ ] La PDA queda libre («Hasta mañana, Isaac»). En *Colas* esa OUT sigue de Isaac, la primera.
   - [ ] Leer OP9990001 otra vez: se abre esa misma primero.
7. **Saltar → No hay stock**.
   - [ ] La OUT pasa a «En oficina». *Colas* > filtro «En oficina» > **Liberar** → queda libre.
8. **Salir (otro operario)** → leer OP9980001 → con la cola vacía y modo manual: «No tienes más pedidos».

## 4. Bloques y etiquetas (v2.1)

Antes: en *Ajustes > Técnico > Acciones de servidor*, comprobar que **KOROSHI Etiquetas zona** está en
`MODO = 'REAL'` (si está en DIAGNOSTICO, «Imprimir etiquetas» enseña el diagnóstico y no imprime).
**Ojo:** imprimir reserva matrículas CJ de verdad (como la acción de siempre). Probar con bloque **2** para gastar pocas.

1. *Reparto de hoy* → **A · Automático**, *Pedidos por bloque* = **2**, *Avisar cuando le queden* = **1**,
   *darle otra solo (sin etiqueta)* **apagado**. Pestaña *Operarios de hoy*: Isaac e Isaac2 (sin tramo). Guardar.
2. **Repartir ahora**.
   - [ ] «Le quedan» = 2 en los dos y «Sin etiqueta» = 2. En *Colas*: 4 OUT distintas, las más antiguas libres,
     repartidas una a uno y otra a otro.
   - [ ] Volver a pulsar **Repartir ahora**: «No se ha repartido nada» (ya tienen el bloque lleno).
3. **Imprimir etiquetas**.
   - [ ] Se abre un PDF: hoja «ISAAC · 2 pedidos» con sus 2 OUT, sus etiquetas de zona en ese orden; después la
     hoja de ISAAC2 y las suyas. Tamaño 4x6 en la Zebra.
   - [ ] «Sin etiqueta» = 0. En *Colas* la columna *Etiqueta impresa* con la hora.
   - [ ] Volver a pulsar **Imprimir etiquetas**: «No hay pedidos en cola sin etiqueta».
   - [ ] *Colas* → seleccionar una → *Acción > Imprimir etiquetas*: la reimprime **con la misma matrícula** (no gasta).
4. PDA con Isaac (OP9990001): se abre sola su **primera** OUT de la hoja. **Saltar → No hay stock** (a oficina).
   - [ ] Se abre la segunda. La línea de Isaac en *Operarios de hoy* sale en **naranja** (le queda 1).
5. **Saltar → No hay stock** otra vez.
   - [ ] «No tienes más pedidos. Pide a tu responsable» (no le da otra sola).
6. En la línea de Isaac: **Dar bloque** y después **Imprimir**.
   - [ ] Le entran 2 nuevas y sale el PDF solo de Isaac con esas 2.
7. Encender *darle otra solo (sin etiqueta)*, y con Isaac2 saltar hasta vaciar su cola.
   - [ ] La PDA le da la siguiente sola (sin etiqueta impresa), como en la v2.0.
8. **B · Por pasillos**: tramo de Isaac 70–80, *dar la más antigua si no hay* desmarcado. **Dar bloque** en su línea.
   - [ ] Solo le entran OUT reservadas en L70–L80, o «No se ha repartido nada» si no hay.
9. Dos PDA a la vez con *darle otra solo* encendido: Isaac e Isaac2 leen la tarjeta con la cola vacía.
   - [ ] Reciben OUT **distintas**.

## 5. Dejarlo como estaba

- *Colas*: **Quitar** todo lo de Isaac e Isaac2 (las tareas abiertas se cierran como dejadas).
- *Colas*, filtro *En oficina*: **Liberar** las saltadas en la prueba.
- *Reparto de hoy*: dejar el modo que se vaya a usar (**C · Solo manual** si aún no se quiere repartir solo),
  quitar a Isaac e Isaac2 de *Operarios de hoy* y poner el bloque que se vaya a usar (10).
- Las matrículas CJ reservadas en la prueba quedan apuntadas a esas OUT («ETQ ZONA …»): si se vuelven a imprimir,
  se reutilizan. No hace falta borrarlas.
- Ninguna OUT validada ni faltante hecho en la prueba.

## Si algo falla

- Volver a la versión anterior instalada: copiar las carpetas de la copia de seguridad que deja el script, reiniciar y *Actualizar*.
  Las tablas nuevas quedan en la base de datos sin usar; no molestan.
