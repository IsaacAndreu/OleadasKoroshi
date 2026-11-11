# Prompt: módulo `koroshi_zonas` (Odoo 13)

Vas a diseñar y construir un módulo de Odoo 13 Enterprise llamado `koroshi_zonas` en `odoo/modulos/` de este repo. Sustituye a una acción de servidor de 1.137 líneas que hoy parte los pedidos de tienda por zonas de picking. Trabaja por fases y para al final de cada una para que yo la revise.

## Para qué sirve

Almacén de ropa KOROSHI (Effective Logistics, compañía 8 en Odoo). Cada madrugada los pedidos de tienda (OUT del tipo `PED. TIENDAS`) se parten en zonas: cada zona es una agrupación (`stock.picking.batch`) que prepara un equipo.

El objetivo de negocio es uno solo: **el máximo % de cajas cerradas**. Una caja cerrada es una caja que sale llena hacia la tienda sin que nadie tenga que juntar restos de varias zonas. Todo lo demás (acabar a la hora, equilibrar equipos) es una restricción, no el objetivo.

Hoy las zonas se deciden con números fijos escritos en el código. Quiero que sean **dinámicas**: que el propio motor pruebe varios repartos y elija el que más cajas cerradas da cumpliendo el horario.

## Cómo funciona hoy

- El cron 202 lanza cada día a las 04:00 UTC la acción de servidor 1883, "KOROSHI Partir OUT zonas v12 REAL". El código que corre es la v12f del 10/11/2026.
- Hay cuatro copias casi idénticas de ese código: 1880 (REAL), 1881 (DIAGNOSTICO), 1882 (SIMULAR) y 1883 (la del cron). Solo cambia `MODO`.
- El código está en el repo, una copia por acción: `bin/KOROSHI_partir_OUT_zonas_2026-11-10_v12f-todas-a-la-vez-MU1-MU2-equipo-propio_accion_1880.py` (y `_1881`, `_1882`, `_1883`). **La fuente de verdad es `_1883`, la que lanza el cron.** Ojo: `v12b` del 09/11 no es la última, es una prueba de 52 líneas sobre 9 OUT fijas.
- Informes de pruebas ya hechas: `bin/versiones/20261109_prueba_zonas/diag_z*.txt` (barrido de 1 a 12 zonas) y `bin/versiones/20261110_prueba_muelle/`. Resumen del trabajo reciente: `bin/versiones/20261111_1500_RESUMEN_trabajo_06-11_a_11-11_para-otro-claude.md`.
- El algoritmo, en resumen:
  1. Coge las OUT de hoy, preparadas, sin leer, que no salen del SORTER, con al menos `MIN_UDS_PEDIDO` (15) uds.
  2. Las ordena por número de tienda (K1, K2...).
  3. Corta los lineales en tramos seguidos minimizando el tramo más pesado (programación dinámica, función `particion`). El tiempo se estima con `SEG_LECTURA = 52` y `SEG_LINEAL = 21`.
  4. Lo de fuera de lineal (muelle) va a dos zonas fijas: MU1 (ubicaciones con `/N1-`) y MU2 (el resto).
  5. Estima las cajas de cada OUT por litros: `LITROS_CAJA = 80`, una tabla `LITROS_TIPO` por tipo de prenda, y da la caja por cerrada si la última llega a `CIERRE_MIN = 0.8`.
  6. Mueve líneas de frontera entre zonas vecinas para cerrar la última caja de cada OUT y reequilibra (`ITER_EQUILIBRIO = 4`).
  7. Crea las agrupaciones `Z-ddmm-D1..Dn`, `Z-ddmm-MU1`, `Z-ddmm-MU2` y escribe en la nota de cada OUT `... | CAJAS n`.
- Otras acciones relacionadas: 1843 "KOROSHI Etiquetas zona" (cuenta cajas con la misma fórmula de litros) y 1868 "KOROSHI Correo zonas del dia".

## Problemas que hay que resolver

1. **Cuatro copias del mismo código**, editadas a mano en producción, sin tests.
2. **Parámetros fijos en el código**: `PERSONAS = 12`, `ZONAS = 5`, horario 06:00–12:00, `TIENDAS_48H`, litros por tipo.
3. **El resultado vive en `stock.picking.note`** y otro proceso lo pisa con "Envio junto: ...". El 10/11 perdieron el `CAJAS n` 14 de 81 OUT.
4. **La caja cerrada se estima, no se mide.** Comparando `CAJAS n` con los bultos reales (`result_package_id` distintos por OUT):

   | Día | OUT comparadas | Cajas previstas | Bultos reales | OUT con menos bultos de los previstos |
   |---|---|---|---|---|
   | 10/11 | 67 | 193 | 173 | 20 |
   | 11/11 | 143 | 488 | 432 | 39 |

   El modelo de litros prevé un 10–12 % más de cajas. **Ojo, no está confirmada la causa**: `koroshi_caja_existente` deja que una OUT pequeña meta sus uds en la caja de otra OUT del mismo pedido y se valide con 0 bultos, y eso también baja la cuenta. Tienes que separar las dos causas antes de tocar los litros.
5. `ZONAS_MUELLE = 'AUTO'` ya prueba varias combinaciones, pero elige la que **acaba antes**, no la que más cajas cierra.
6. **La caja no mide lo mismo en todas partes**: 80 L en la v12f y en las etiquetas, 84 L (`VOL_CAJA = 0.084`) en la v11, 96 L si se calcula 60x40x40, 103 L (`LITROS_BAUL`) en el script de INT. Hay que dejar un solo valor, en configuración.
7. **El modelo de tiempo es optimista.** `SEG_LECTURA = 52` está calibrado el 22/10 y los documentos del 27/10 hablan de 70 a 115 s/ud reales. El último diagnóstico prevé acabar a las 13:35 con objetivo 12:00, y `UNA_RONDA = True` hace que `HORA_FIN` solo salga en el informe, no corte nada.
8. Una línea reservada va entera a una zona: el motor reagrupa lo que Odoo ya ha reservado, no elige de qué ubicación se coge.
9. El correo del día (1868) saca el estado leyendo la primera línea de un `ir.logging`, y el destinatario está escrito en el código.

## Paso 0, antes de escribir nada

1. Pídeme que confirme que el fichero `_1883` del repo es idéntico a lo que hay hoy en la acción 1883 de Odoo. Si no lo es, te paso el de Odoo.
2. Lee, como mínimo: ese código entero, `odoo/modulos/koroshi_monitor` (ya cuenta cajas cerradas por OUT con las matrículas CJ), `odoo/modulos/koroshi_warehouse_map` (tiene el plano de la nave y puede sustituir el parseo de `complete_name`), `odoo/modulos/koroshi_kpi` (ya tiene una ficha por día y método, incluido "zonas", litros por tipo y una estimación por cajas cerradas), `odoo/modulos/koroshi_caja_existente`, `odoo/modulos/koroshi_preparacion/models/ruta.py` (ruta óptima por la nave) y `odoo/modulos/koroshi_xpo_bultos`.
3. Dime qué reutilizas de cada uno y qué no. No dupliques la tabla de litros ni el KPI diario si ya existen: amplíalos o depende de ellos.

## Reglas del proyecto

Las he sacado de los módulos que ya hay. Si alguna te parece mala idea para este caso, dímelo antes de saltártela.

- Odoo 13, Python 3. Todo en español: nombres, ayudas, comentarios y mensajes.
- Manifest como los demás: `'author': 'NATH'`, `'category': 'Warehouse'`, `'license': 'LGPL-3'`, versión `13.0.x.y.z` y el historial de versiones con fecha dentro de `description`.
- **No añadas campos a `stock.picking`, `stock.move`, `stock.move.line` ni `stock.picking.batch`.** Los módulos existentes escriben solo en sus tablas propias, y hay un sync externo (S4T) sensible a cambios en los albaranes. Lo que haga falta guardar por OUT va en una tabla propia con un `many2one` a la OUT.
- Lo único que el módulo escribe fuera de sus tablas es lo que ya escribe la acción hoy: partir movimientos, crear agrupaciones y la nota. Nunca fuerces disponibilidad ni escribas `stock.quant`.
- Nunca canceles una OUT: una OUT cancelada bloquea el sync S4T.
- Todo filtrado por compañía 8.
- Commits convencionales, sin atribución de IA. No compiles ni instales nada por tu cuenta.

## Arquitectura que quiero

Separa el cálculo de Odoo. Es lo que hace posible testearlo.

```
koroshi_zonas/
  __manifest__.py
  motor/                 # Python puro, sin importar odoo
    modelo.py            # estructuras: Linea, Out, Zona, Reparto
    volumen.py           # litros por linea y cajas por OUT
    particion.py         # corte de lineales (la DP actual)
    cierre.py            # mover lineas de frontera para cerrar cajas
    evaluar.py           # puntua un Reparto: % cajas cerradas, hora de fin, equilibrio
    buscar.py            # genera candidatos y elige el mejor
  models/
    config.py            # koroshi.zonas.config: personas, horario, minimos, tiendas 48h
    ejecucion.py         # koroshi.zonas.ejecucion: una por lanzamiento, con modo y resultado
    ejecucion_out.py     # koroshi.zonas.ejecucion.out: zona, cajas previstas, cajas reales, cerrada
    lector.py            # lee de Odoo y construye las estructuras del motor
    escritor.py          # aplica un Reparto: partir, agrupar, nota
  data/cron.xml
  security/ir.model.access.csv
  views/
  tests/                 # tests del motor con datos reales anonimizados
```

- `motor/` no importa `odoo`. Recibe datos planos y devuelve un `Reparto`. Se testea con `pytest` o `unittest` sin levantar Odoo.
- DIAGNOSTICO, SIMULAR y REAL son un campo de `koroshi.zonas.ejecucion`, no tres copias. SIMULAR hace todo dentro de un savepoint y lo deshace.
- REAL es todo o nada: si falla una comprobación, no queda nada a medias.
- Cada ejecución guarda los parámetros con los que corrió y el informe, para poder comparar días.

## Fases

**Fase 1 — Medir.** Sin tocar el reparto actual. Tablas de ejecución y de OUT, y un cálculo nocturno que rellena las cajas reales a partir de `result_package_id` y marca cada OUT como cerrada o no. Define por escrito qué es "caja cerrada real" y enséñamelo antes de programarlo: cómo cuentan las OUT de 0 bultos de `koroshi_caja_existente`, y qué pasa con una caja compartida por dos OUT. Resultado: % real de cajas cerradas por día y por zona, con histórico desde el 22/10.

**Fase 2 — Mismo algoritmo, dentro del módulo.** Pasa la v12f a `motor/` sin cambiar el comportamiento. Criterio de aceptación: con las mismas OUT de entrada, el módulo en DIAGNOSTICO da exactamente el mismo reparto que la acción 1883. Compara con varios días reales (la acción admite `prueba_ids` y `prueba_agrupacion` en el contexto). Hasta que no coincida, no se pasa a la fase 3.

**Fase 3 — Configuración y sustitución.** Parámetros en `koroshi.zonas.config`. El cron pasa a llamar al módulo. Las acciones 1880–1883 se quedan desactivadas, no borradas, hasta que yo lo diga. Las acciones 1843 y 1868 leen las cajas de la tabla nueva en vez de la nota.

**Fase 4 — Zonas dinámicas.** `buscar.py` genera candidatos (número de zonas de lineal, cuántas de muelle, reparto de personas, puntos de corte) y `evaluar.py` los puntúa. Objetivo: máximo % de cajas cerradas. Restricciones: acabar antes de `HORA_FIN` con las personas que hay, ninguna OUT por debajo del mínimo de uds. A igualdad de cajas, gana el que acaba antes. El informe de la ejecución tiene que decir qué candidatos se probaron y por qué ganó el elegido.

**Fase 5 — Litros que se corrigen solos.** Con las cajas reales de la fase 1, ajusta los litros por tipo de prenda. Propón el método antes de implementarlo y enséñame cuánto baja el error con datos de días pasados. El ajuste se propone en pantalla y lo aprueba una persona: no se aplica solo.

## Cómo quiero que trabajes

- Antes de cada fase, dime en pocas líneas qué vas a hacer y qué decisiones tomas. Si hay una bifurcación de verdad, plantéamela con sus pros y contras y espera.
- No des por bueno nada de este documento sin comprobarlo en el código. Si algo no cuadra con lo que lees, dímelo.
- Rendimiento: la acción actual corre en segundos con unas 150 OUT y 6.000 uds. La búsqueda de la fase 4 no puede pasar de un par de minutos; dime la complejidad de lo que propongas.
- Al acabar cada fase: qué has hecho, qué has probado y con qué datos, y qué no has podido comprobar.
- No puedes entrar en Odoo. Lo que necesites de producción, pídemelo como una consulta concreta que yo pueda lanzar.
