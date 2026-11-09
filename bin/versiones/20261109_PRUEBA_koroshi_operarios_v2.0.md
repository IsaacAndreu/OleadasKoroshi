# Prueba fuera de horas: koroshi_operarios v2.0 + koroshi_faltantes v1.2 (09/11/2026)

ZIP: `20261109_koroshi_operarios_v2.0.zip` y `20261109_koroshi_faltantes_v1.2.zip`.
Script: `actualizar_koroshi_operarios_v2.0_faltantes_v1.2_2026-11-09.sh` (`check` y después `install`).
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

## 4. Automático y pasillos

1. *Reparto de hoy* → **A · Automático**.
   - [ ] Isaac2 lee la tarjeta: se le asigna sola la OUT preparada más antigua sin agrupación Z- y se abre.
   - [ ] Isaac lee la tarjeta en otra PDA a la vez: recibe **otra** OUT, nunca la misma.
2. **B · Por pasillos**, tramo de Isaac 70–80, *dar la más antigua si no hay* desmarcado.
   - [ ] Se le da una OUT reservada en L70–L80, o «No tienes más pedidos» si no hay.

## 5. Dejarlo como estaba

- *Colas*: **Quitar** todo lo de Isaac e Isaac2 (las tareas abiertas se cierran como dejadas).
- *Reparto de hoy*: dejar el modo que se vaya a usar (**C · Solo manual** si aún no se quiere repartir solo).
- Ninguna OUT validada ni faltante hecho en la prueba.

## Si algo falla

- Volver a la v1.2 / v1.1: copiar las carpetas de la copia de seguridad que deja el script, reiniciar y *Actualizar*.
  Las tablas nuevas quedan en la base de datos sin usar; no molestan.
