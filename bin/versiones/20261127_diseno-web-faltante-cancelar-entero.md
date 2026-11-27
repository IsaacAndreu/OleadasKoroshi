# Pedido web con faltante en picking: cancelarlo entero. Diseño v1 (27/11/2026)

Sin código. Espera el visto bueno de Isaac y la respuesta a la pregunta 1.

Encargo (Isaac, 27/11): «los pedidos de web quan estan fent picking y no hi ha 100 % se deberia cancelar cuando le den
a faltante ese pedido».

## Lo que dicen los datos (solo lectura, 27/11 ~13:00)

Versiones en el servidor = repo: preparacion 3.38.1, faltantes 1.12.0, agrupaciones_web 1.1.0.

1. **Las OUT web no pasan por el «Faltante» de la PDA.** De los 719 registros de `koroshi.faltante` desde el 17/11,
   ninguno es de una OUT `W-`. Las web se preparan en el PC con **PedidosMultiples**: escribe `qty_done` por SQL
   (`InitialForm.cs:134`) y valida con `action_done` (`OdooClient.cs:161`). PedidosMultiples no tiene ningún botón de
   «faltante».
2. **No se validan incompletas.** De las 750 OUT web validadas desde el 18/11, solo 1 salió con menos uds:
   `EFFEC/OUT/26842` (W-0000058643, 20/11, «Almacen 2», 1 de 3).
3. **Lo que se ve en la foto son W a medias, sin validar.** Hay 4 OUT web con algo leído y una línea sin reserva,
   todas en la agrupación **`INCOMPLETO`** (id 1150, creada a mano por «Almacen 2» el 23/11):

   | OUT | Pedido | Leído | Línea sin reserva | Qué le pasó |
   |---|---|---|---|---|
   | OUT/26287 | W-0000059271 | 2 de 3 | 2622BL25-000323-M | 18/11 07:48: «KOROSHI Faltante EFFEC/INT/67388» llevó la ud a FALTANTE |
   | OUT/26430 | W-0000059368 | 1 de 2 | 2522XC00-000003-40 | 19/11 05:29: «KOROSHI Faltante EFFEC/INT/67393» |
   | OUT/26437 | W-0000059378 | 2 de 3 | 2521SU08-000003-XL | 19/11 05:35: lo mismo (INT/67393); hoy hay 2 en L31 P29 C1, reservadas para otra |
   | OUT/26864 | W-5920002802 | 2 de 3 | 2521TR30-000139-L | Odoo ve **14 libres** en L24 P35 C1, pero la ronda dice «no está» cada día (5 veces del 23 al 27/11) |

   Es decir: la prenda no estaba, la **ronda de faltantes** (INT) la mandó a FALTANTE y la línea de la web se quedó sin
   reserva. La OUT se queda a medias para siempre: el corte de las 06:00/12:00 **no la cancela** porque está en una
   agrupación y tiene algo leído (regla de la 1.0.0: «una OUT con algo leído no se cancela nunca»).
4. W-0000059610 (el ejemplo del encargo): el faltante de Pep (5 uds en L52 P19 C1) es de `EFFEC/OUT/25316-2`, una OUT
   de **tienda**, no de la web. A la web le afecta porque el hueco queda sin esas uds.

**Conclusión:** hoy no hay un «Faltante» en una OUT web que se pueda interceptar en `koroshi_preparacion`. Tocar la PDA
no arreglaría estas 4.

## Propuesta: solo en `koroshi_agrupaciones_web` (1.2.0)

Ni PDA, ni `koroshi_preparacion`, ni `koroshi_faltantes`, ni campos nuevos.

En cada corte (06:00 y 12:00), además de lo de ahora:

- **Web a medias**: OUT web (W-, PED. ONLINE, no Zalando/About You) sin validar, **con algo leído**, con alguna línea
  sin reserva y **más de N horas** desde que se agrupó (parámetro `horas_medias`, 4 por defecto).
  - Esté en `WEB_…`, en `INCOMPLETO` o sin agrupación.
  - Con `cancelar_medias` = 1: se quita lo leído (`qty_done` a 0), se saca de la agrupación y se cancela la OUT entera
    (`action_cancel`, como las demás). Nota en la OUT: «Cancelada en el corte: faltaba X. Devolver las prendas leídas
    a su ubicación: SKU → L.. P.. C..».
  - Con `cancelar_medias` = 0 (así se instala): solo sale en el correo como «a revisar», sin tocar nada.
- **Correo** a Betty e Isaac, el mismo del corte, con una sección nueva: «Canceladas con prendas ya cogidas: devolverlas
  a su sitio», con OUT, pedido, SKU y ubicación de cada prenda leída.
- **Dónde dejar las prendas**: la ubicación de la que se leyeron (la de la línea). Si se prefiere una ubicación fija
  («DEVOLVER WEB» o similar), decirlo.

Esto cubre las 4 de `INCOMPLETO` y cualquier W que se quede a medias en PedidosMultiples.

## Lo que no hace

- **La pantalla de la PDA no dice «Pedido web cancelado: deja las prendas en …»**, porque las web no se preparan con la
  PDA. Si un día se preparan con ella (pregunta 1), se añade en `koroshi_faltantes`: «No está» en una OUT web cancela la
  OUT entera.
- **PedidosMultiples no cambia** (programa del PC, credenciales en el repo; regla de secretos). Si se quiere el aviso
  en el PC al no encontrar una prenda, eso va aparte.
- **OUT/26864** (Odoo ve 14 y la ronda dice que no están): no es de este encargo. Hace falta un recuento de L24 P35 C1.

## Preguntas para Isaac

1. **¿Dónde marcan «faltante» en las web: en el PC (PedidosMultiples) o en la PDA?** Los datos dicen que en la PDA
   nunca. Si es en el PC, ¿qué hacen: dejan la OUT apartada y la pasa la oficina a `INCOMPLETO`?
2. **¿Cuántas horas** espera una web a medias antes de cancelarse? Propongo 4: una W cogida a las 06:00 se cancela en
   el corte de las 12:00 si sigue a medias.
3. **¿Se instala con `cancelar_medias` = 0** (un día solo en el correo) y después a 1, como se hizo con las otras?
4. Las prendas leídas de una web cancelada: **¿a su ubicación** o a una ubicación fija?

## Cómo se probaría

- Test sin Odoo de la selección (`tests/test_reparto.py`).
- «Simular corte ahora» en el servidor: las 4 de `INCOMPLETO` tienen que salir en «a medias».
- Primer día con `cancelar_medias` = 0: comparar el correo con la agrupación `INCOMPLETO`.
- PDA real: nada (no la toca).
