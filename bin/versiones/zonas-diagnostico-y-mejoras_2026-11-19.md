# koroshi_zonas: diagnóstico y mejoras posibles (19/11/2026)

Sesión «Zonas: mejorar» (sale de la coordinación). **No se ha tocado código ni datos.** Leído el módulo
(13.0.1.4.0, igual en el servidor: `installed_version` = `latest_version` = 13.0.1.4.0) y, solo leyendo por la web de
nath.tuctuc.com, sus ejecuciones, mediciones y las lecturas de las agrupaciones Z-.

Isaac quiere mejorar (19/11): **acabar a la hora** y **pasar de sombra a real**.

## 1. Qué hace hoy

- El reparto de verdad lo sigue haciendo la acción 1883 (v12f), lanzada por el **cron 202 a las 04:00 UTC** (05:00).
- El módulo calcula en sombra a las 03:50 UTC (cron 208): un DIAGNÓSTICO «como la 1883» y otro con lo nuevo de la 1.3.0
  (OUT de días anteriores y urgencia primero). A las 04:30 UTC (cron 209) compara con lo que ha partido el 202.
- Cada hora registra las OUT de las Z- (cron 206) y cada noche mide las cajas reales (cron 207).
- El correo del día (cron 210) está **desactivado** y sin destinatarios. El informe solo sale en el canal «KOROSHI Partir OUT zonas».
- Configuración en el servidor: 12 personas, 5 zonas, 06:00–12:00, **Todo en una ronda** marcado, 52 s/lectura,
  21 s/lineal, 80 L por caja, cierre al 80 %, mínimo 2.000 uds para partir y 7 días atrás.

## 2. Qué ha recogido en sombra (12/11 a 19/11)

| Día | Sombra | Comparación con el 202 |
|---|---|---|
| 12/11 | menos de 2.000 uds, no se parte | sin 202 |
| 13/11 | 49 OUT, 3.670 uds | **IGUAL** |
| 14/11 y 15/11 | vacío (fin de semana) | sin 202 |
| 16/11 | 49 OUT, 7.738 uds | **IGUAL** |
| 17/11 | 47 OUT, 2.472 uds | **IGUAL** (2.334 líneas, 0 distintas) |
| 18/11 | 1.828 uds, no se parte | sin 202 |
| 19/11 | 48 OUT, 2.564 uds | **IGUAL** (2.273 líneas, 0 distintas) |

**El cálculo del módulo es idéntico al de la 1883 los 4 días en que se partió.** El diagnóstico con lo nuevo de la 1.3.0
dio el 19/11 el mismo reparto (no había OUT viejas ni hacía falta recortar).

Hay dos SIMULAR lanzados a mano (12/11 y 16/11): los dos «vacíos», porque se lanzaron cuando el 202 ya lo había
partido todo. **El camino que escribe (partir, agrupar, nota) no se ha ejecutado nunca en el servidor con OUT de verdad.**

### Cajas (medición nocturna)

| Día | Cajas reales | Cerradas | OUT cerradas | Cajas previstas → reales (OUT limpias) |
|---|---|---|---|---|
| 10/11 | 494 | 88,1 % | 66,5 % | — |
| 11/11 | 452 | 78,8 % | 26,7 % | — |
| 13/11 | 199 | 71,9 % | 39,6 % | 266 previstas |
| 16/11 | 541 | 75,4 % | 22,7 % | 547 → 495 (+10 %) |
| 17/11 | 219 | 71,2 % | 42,9 % | 252 → 211 (+19 %) |

- D1-D3 cierran el 71–84 % de sus cajas. **MU1 y MU2 casi nunca** (0–19 %): sus 1–3 uds por tienda acaban en la caja
  de otra OUT (caja compartida). Es lo esperado para el muelle.
- El modelo de litros sigue previendo un 10–20 % más de cajas de las reales (80 L contra los ~93 L del MASTER). Esto es
  la fase 5 (litros); Isaac no lo ha elegido ahora.

### Corrección del 19/11 por la tarde: tiempos con las lecturas de la PDA

La tabla de abajo salió de la hora de modificación de las líneas (`write_date`). Esa hora cambia también al meter en
caja y al validar, así que **la «cola» de 1-2 h era en buena parte falsa**. Con las lecturas de la PDA
(`koroshi.preparacion.lectura`: hora exacta y operario) sale esto:

| Día | Previsto | Primera lectura | 95 % de las uds | Última lectura | Personas que leen |
|---|---|---|---|---|---|
| 17/11 | ~4 h de trabajo (D3 248 min) | 08:19 (D1 leyó algo suelto a las 06:07) | 12:17–12:21 | **12:34** (4 h 15 desde las 08:19) | 10 (María hace MU y luego ayuda en D1) |
| 19/11 | **9:49** | 06:02 | 09:15–09:23 | **09:31** | 10 |
| 13/11 | 11:26 | — | — | — | casi sin lecturas: ese día aún no se leía en Lecturas |

**El modelo de tiempo acierta.** El 19/11 se acabó 18 min antes de lo previsto, y el 17/11 la duración fue la prevista.
Lo que hace acabar tarde es **la hora de empezar** (el 17/11, a las 08:19) y **los días que no caben** (16/11). El
muelle no es la cola: María lo acaba pronto y pasa a ayudar. La mejora E pierde prioridad.

### Tiempo: previsto contra real (hora del almacén), primera versión con `write_date`

Sacado de la hora de lectura de las líneas de cada agrupación. Todas se leen con el usuario compartido «Almacén», así que
**no se sabe cuántas personas había de verdad** en cada zona (la configuración dice 12).

| Día | Previsto (empezando a las 06:00) | Empiezan de verdad | 95 % de las uds leídas | Última lectura |
|---|---|---|---|---|
| 13/11 (3.670 uds) | 11:26 | 06:15 | 10:47–11:11 | D 11:10–12:45; MU 12:54 |
| 17/11 (2.472 uds) | 10:08 (duración ~4 h 05) | **08:14–08:38** | 12:24–12:31 | D2 14:25; MU 14:47 |
| 19/11 (2.564 uds) | 9:49 | 06:15 | a las 08:40 ya iban por el ~70 % | en curso |
| 16/11 (7.738 uds) | **18:10** | 06:30–07:15 | — | acabaron el **17/11** (D2 a las 12:12) |

**Corrección a lo que dije en la pregunta:** el modelo de tiempo (52 s/lectura) **acierta bien** con el grueso del
trabajo. El 13/11 previó las 11:26 y el 95 % estaba a las 11:10. El 17/11 previó 4 h 05 de trabajo y fueron ~4 h desde
que se empezó. Lo que hace acabar tarde es otra cosa:

1. **La hora real de inicio.** El 17/11 se empezó a las 08:14, 2 h tarde. El cálculo supone las 06:00 y nadie lo
   corrige. No se sabe por qué se empezó tarde (¿pedidos tarde, gente, otra tarea?).
2. **La cola.** El último 5 % de las uds tarda entre 1 y 2 h más (13/11: de 11:10 a 12:45; 17/11: de 12:30 a 14:25).
   El muelle (MU1 y MU2, una persona cada una) es lo último en acabar todos los días, aunque se prevé de 15 a 80 min.
   No he podido separar cuánto de la cola son faltantes, restos de frontera o muelle.
3. **Los días que no caben.** El 16/11 entraron 7.738 uds con «Todo en una ronda»: el informe ya decía las 18:10 a las
   05:00, pero solo en el canal. Nadie recortó ni pidió más gente, y se acabó al día siguiente.
4. **Capacidad.** Con este ritmo y 12 personas, en 06:00–12:00 caben unas **3.900 uds**. Un día de **10.000 uds**
   necesita unas **30 personas** en zonas para salir a las 12:00, o ~25 para salir a las 13:00 (cálculo lineal con
   52 s/lectura; falta confirmar las personas reales de los días medidos).

## 3. Mejoras posibles

Riesgo para la PDA: qué puede notar un operario si sale mal.

| # | Mejora | Para qué | Impacto | Riesgo PDA | Qué toca |
|---|---|---|---|---|---|
| A | **Aviso a primera hora**: a las 05:00 el informe dice «con 12 personas acabáis a las HH:MM; para las 12:00 hacen falta N». Correo a los jefes (activar el cron 210, que ya existe) | Acabar a la hora | Alto en días grandes (16/11): se sabe a las 05:00, no a las 14:00 | **Nulo** (solo texto y correo) | koroshi_zonas (informe y correo) + destinatarios en la configuración |
| B | **Previsto contra real cada noche**: guardar en la ejecución la hora de inicio, la del 95 % y la última lectura por zona, y su diferencia con lo previsto | Calibrar y ver la cola | Medio: deja de hacer falta mirarlo a mano | **Nulo** (sus tablas) | koroshi_zonas (medición nocturna) |
| C | **Recalcular a la hora real de inicio**: botón «Recalcular ahora» (hora de inicio = AHORA y personas de hoy) que da la nueva hora de fin sin partir de nuevo | Acabar a la hora | Medio | **Nulo** si solo diagnostica | koroshi_zonas (botón) |
| D | **Recortar los días que no caben**: desmarcar «Todo en una ronda». Entran primero las OUT viejas y las tiendas de 48 h (ya hecho en la 1.3.0); el resto, a otra tanda (R2) o tradicional | Acabar a la hora | Alto en días grandes | **Medio**: OUT que se quedan sin partir; hay que decidir quién las coge | Configuración (solo funciona en modo real) |
| E | **Muelle**: que MU1+MU2 sea una sola zona o que la coja quien acabe antes, en vez de 1 persona fija que acaba la última | Cola | Medio (1–2 h de cola) | **Medio**: cambia el reparto que ven en la PDA | motor (v12f) y forma de trabajar |
| F | **Ensayar la escritura antes de pasar a real**: en sombra, cambiar el diagnóstico «como la 1883» por un SIMULAR (parte dentro de un savepoint y lo deshace) a las 04:50, antes del 202 | Pasar a real | Imprescindible: hoy el camino que parte nunca se ha probado en el servidor | **Bajo**: se deshace siempre y a esa hora no hay PDA; bloquea las OUT unos segundos | koroshi_zonas (cron_partir) |
| G | **Pasar a real**: después de F con 3–5 días buenos, el mismo día desactivar el cron 202 y poner `modo_cron = real`. La 1883 se queda para lanzarla a mano si algo falla | Pasar a real | Quita la acción de 1.137 líneas y deja los parámetros en pantalla | **Medio el primer día**: si una comprobación falla, REAL no parte nada (todo o nada) y ese día va en tradicional hasta lanzar la 1883 a mano | Configuración + cron 202 (lo hace Isaac) |
| H | Litros (fase 5): 80 L → ~93 L o litros por tipo con las cajas reales | Más cajas cerradas | Previsión de cajas un 10–20 % más fiel | Bajo | No elegido ahora |

### Orden que propongo

1. **F + A + B en una versión (1.5.0)**: nada cambia para las PDA. Cada mañana se ensaya el reparto de verdad, sale el
   aviso con la hora de fin y las personas que hacen falta, y cada noche el previsto contra real.
2. Con 3–5 días de SIMULAR sin errores: **G** (pasar a real), en un día flojo y con alguien a las 05:00 para mirar el canal.
3. Después de G: **D** y **E**, que solo tienen sentido con el módulo partiendo. Antes hay que decidir con almacén qué
   se hace con lo que no cabe y cómo se coge el muelle.
4. **C** cuando haga falta (si vuelve a pasar lo del 17/11).

### Preguntas para Isaac

- ¿Por qué se empezó a las 08:14 el 17/11? Si pasa a menudo, C sube de prioridad.
- ¿Cuántas personas había de verdad en zonas el 13/11 y el 17/11? Con eso se confirma el 52 s/lectura y la cuenta de
  los 10.000 uds.
- Aviso A: ¿a quién se manda el correo de las 05:00?
- Pasar a real (G): ¿quién mira el canal a las 05:00 el primer día y lanza la 1883 a mano si hace falta?

## 4. Qué no se ha podido comprobar

- Personas reales por zona: todas las lecturas van con el usuario «Almacén». koroshi_operarios tiene asignaciones por
  agrupación, pero no lo he cruzado.
- La causa de la cola: faltantes, restos de frontera o muelle.
- El 19/11 aún estaba en curso al leerlo (~08:40).
