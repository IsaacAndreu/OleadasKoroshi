# Diseño: KOROSHI Operarios v2, cola de pedidos por operario (09/11/2026)

Objetivo: que el operario lea su tarjeta **una vez** y la PDA le vaya abriendo sola las OUT que le tocan, sin
escanear el pedido. La productividad se cuenta sola.

## 1. En la PDA

1. **Tarjeta una vez al empezar el turno.** La PDA se queda con ese operario hasta que pulsa **Salir**. Se quita
   la ventana de 90 segundos.
2. La pantalla muestra **su cola**: «Te tocan: OUT 24008, OUT 24012, Z-0911-A…». La primera **se abre sola**.
3. **Al validar**, la app de código de barras vuelve atrás y se abre sola la siguiente. Si no quedan: «No tienes más,
   pide a tu responsable».
4. **Faltante:** flecha atrás y **Faltante**. Ya sabe qué OUT está haciendo: **solo hay que leer el EAN**.
   «Volver a la OUT» la reabre.
5. **Saltar** (en la pantalla, junto a la OUT en curso), con motivo. Ver punto 3.
6. Se puede seguir leyendo una OUT a mano, como ahora. Si no está en su cola, se le asigna en ese momento, siempre que
   no la tenga otro.

## 2. Cómo se asignan (el responsable elige el modo cada mañana)

*Inventario > KOROSHI Operarios > Reparto de hoy*: una pantalla con el modo del día y las colas de cada uno.

| Modo | Qué hace |
|---|---|
| **A · Automático** | Cuando el operario pide la siguiente, se le da la OUT libre **más antigua** (preparada y sin agrupación de zonas). |
| **B · Por pasillos** | El responsable da a cada operario un tramo de lineales (p. ej. L40–L60). Se le dan las OUT cuya primera ubicación reservada está en su tramo. Si no queda ninguna, opcionalmente pasa a Automático. |
| **C · Manual** | El responsable reparte OUT y agrupaciones a cada operario desde la pantalla. El operario solo recibe lo suyo. |

- **Mixto, por defecto:** primero lo asignado a mano (C) y, cuando se acaba, el modo del día (A o B).
- **Agrupaciones enteras (Z-…):** con un interruptor «Repartir agrupaciones enteras», **apagado** hasta hablarlo
  con el almacén. Encendido, una agrupación cuenta como un solo elemento de la cola y se abre en «procesar agrupación».
- **Bloqueo:** una OUT asignada es de ese operario. Dos PDA nunca reciben la misma. El responsable puede quitarla o
  pasarla a otro.

## 3. Saltar una OUT: depende del motivo

| Motivo | Adónde va |
|---|---|
| **No hay stock / en espera** | **Oficina:** queda sin asignar y marcada; no se da a nadie hasta que el responsable la revise. |
| **Falta material** (caja, etiquetas) | **Final de la cola** del mismo operario. Se le vuelve a dar después. |
| **Muy grande / que la haga otro** | **Oficina.** |
| **Fin de turno** (la deja a medias) | **Sigue siendo suya y la primera de su cola.** Al día siguiente, al leer la tarjeta, se le abre esa primero. |
| **Otro** (texto libre) | **Oficina.** |

El destino de cada motivo se podrá cambiar en Ajustes sin tocar el código.

Lo saltado queda apuntado (quién, cuándo, motivo) y se ve en *Reparto de hoy* y en el informe diario.

## 4. Productividad

- Igual que ahora: tarea = operario + OUT/agrupación, con inicio, fin y uds leídas.
- Empieza al abrirse la OUT y acaba al validarla. Saltar cierra la tarea como «Dejada».
- **Fin de turno:** la tarea se cierra como «Dejada» a esa hora. Al día siguiente empieza otra tarea con la misma OUT,
  para no contar las horas de la noche.

## 5. Técnico y seguridad

- Tabla nueva propia `koroshi.operario.asignacion` (operario, OUT o agrupación, orden, estado, motivo de salto) y
  `koroshi.operario.dia` (modo del día, tramos por operario).
- **No añade campos** a `stock.picking`, `stock.move`, `stock.move.line`, `stock.picking.batch` ni
  `stock.picking.type`. No toca la app de código de barras: abre las OUT igual que ahora
  (`scan_from_main_menu` / `start_batch_processing`).
- Para que dos PDA no reciban la misma OUT: bloqueo de fila en la tabla de asignaciones (`SELECT … FOR UPDATE SKIP
  LOCKED`).
- **Faltantes v1.2:** si no se lee la OUT, toma la de la tarea abierta del operario de la PDA.
- Versión **koroshi_operarios 13.0.2.0.0** y **koroshi_faltantes 13.0.1.2.0**. ZIP con fecha en `bin/`. Instalación
  fuera de horas y con OK.

## 6. Pendiente de decidir con el almacén

- ¿Se reparten agrupaciones enteras? (interruptor, apagado de inicio)
- ¿Qué modo se usará normalmente? (A, B o C)
