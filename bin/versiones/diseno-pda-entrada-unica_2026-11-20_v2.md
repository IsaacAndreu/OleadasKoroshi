# PDA: entrada única por áreas — diseño v2 (20/11/2026, sin código)

Sale de la v1 (`diseno-pda-entrada-unica_2026-11-20.md`, no se toca), con las respuestas de Isaac del 20/11 y lo
acordado con la sesión del Tablero. Todo lo que no cambia aquí sigue como en la v1 (apartados 2 a 5).

## Respuestas de Isaac (20/11)

| # | Pregunta | Respuesta | Qué cambia |
|---|---|---|---|
| 1 | Áreas | Bien así: Recepciones, Picking, Compactación, Devoluciones, Inversa, Expediciones y Extra | «Reubicar material» no es un área: va como opción de **Extra** (se puede mover en Configuración) |
| 2 | ¿Cómo se sabe que es jefe? | **Por la tarjeta** (A) | Lista de operarios jefes en Configuración. El jefe pasa su tarjeta en cualquier PDA y le sale **Gestión** |
| 3 | Actividades del portátil (Marketplace, Tiendas, Web, Bolsas y etiquetas) | «Creo que en **Recepciones**» | Van en Recepciones. Como el área es un campo de la actividad, se cambia en Configuración sin sacar versión si luego no encaja |
| 4 | ¿Quitar el administrador a «Almacén Nath»? | Basta con que la PDA no llegue a la pantalla de inicio de Odoo | No se toca el usuario. El Inicio no tiene barra de Odoo y ninguna salida lleva a la pantalla de inicio |
| 5 | ¿«La lectura manda»? | **Sí** | Leer una OUT pasa a Picking, mover un contenedor a Compactación, leer una matrícula de inversa a Inversa |

Reparto de las actividades que ya hay (data/actividades.xml):

| Actividad | Área |
|---|---|
| Manipulación marketplace | Recepciones |
| Tiendas | Recepciones |
| Web | Recepciones |
| Bolsas y etiquetas | Recepciones |
| Manipulación devoluciones | Devoluciones |
| Inversa (lee matrículas) | Inversa |

Nuevas: una principal por área (Picking, Compactación, Expediciones…), «Descargar camión» (Recepciones),
«Cargar camión» y «Montar cajas» (Expediciones), y en Extra: Cartón, Limpieza y Reubicar material.

## Gestión por tarjeta

- Campo «Jefe en la PDA» en una **tabla propia** de Actividades (`koroshi.pda.jefe`: operario), no en `hr.employee`.
  Pantalla en Configuración para añadir o quitar.
- Si el operario de la tarjeta está en la lista, el Inicio enseña **Gestión**: Monitor, Tablero, Integración S4T
  (matrículas, packing feed) y cajas escaneadas. Abre las acciones que ya existen.
- Ojo: en la PDA, esas pantallas se abren con el usuario «Almacén Nath». Lo que vea depende de los permisos de ese
  usuario, no del jefe. Por ejemplo, el Monitor sin nombres (1.37.0) seguirá sin nombres en la PDA. Para verlo
  completo, el jefe sigue entrando con su usuario en el PC.

## Acuerdo con el Tablero (20/11)

- El Tablero hace `koroshi_operarios` 2.23.0 (aprobada por Isaac). Lleva `_tablero_areas(empleados)` en
  `koroshi.operario.asignacion` → {employee_id: {'area', 'desde', 'detalle'}}. Sin área = no sale.
- Actividades lo sobrescribe con el tramo abierto (`actividad_id.area`). Va en la 1.6.0, porque el campo área llega
  ahí, y quita del todo las tarjetas de actividad de la 1.5.0.
- El «Salir» de Lecturas (fase 3) va en una operarios posterior a la 2.23.0: el Tablero avisa cuando la suelte.

## Orden (uno por sesión)

| Fase | Módulo | Qué |
|---|---|---|
| 1 | `koroshi_actividades` 1.6.0 | Área, «Abre» y «Solo jefes» en `koroshi.actividad`; tabla `koroshi.pda.jefe`; datos de áreas y Extra; pantalla «Inicio (PDA)» con «◀ Áreas» flotante; informe «Horas por área»; `_tablero_areas`; fuera las tarjetas de actividad del tablero |
| 2 | `koroshi_pda_app` 1.2.0 | La app abre el Inicio |
| — | Isaac, a mano | Acción inicial de «Almacén Nath» = Inicio (PDA), cuando la 1.6.0 se haya probado con Departament IT |
| 3 | `koroshi_operarios` (después de la 2.23.0) | «Salir» de Lecturas vuelve al Inicio |
| 4 | `koroshi_actividades` 1.7.0 | «La lectura manda» y cierre del área a los 15 min sin leer |

- Antes de la fase 1: preguntar la `installed_version` de `koroshi_actividades` (el repo dice 1.5.0) y confirmar con
  la sesión del cierre por turno que no la va a coger a la vez.
- Ver qué modelo usar: es un módulo de la PDA que toca el tiempo de la gente, así que Opus en high (CLAUDE.md).
