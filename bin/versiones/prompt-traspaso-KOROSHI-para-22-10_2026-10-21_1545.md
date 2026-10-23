# Traspaso de contexto: proyecto KOROSHI (picking por zonas) — para seguir el 22/10/2026

Eres mi asistente en el repo `C:\dev\OleadasKoroshi` (GitHub privado). Explícame las cosas en **catalán**; el código y los comentarios, en **castellano**. Te dejo abajo todo lo que hay hecho hasta el 21/10/2026, 15:45.

## Reglas de trabajo (obligatorias)
1. **NUNCA ejecutes el programa PedidosMultiples.** Escribe en las bases de datos de PRODUCCIÓN (Postgres y SQL Server). Solo puedes compilarlo: `msbuild PedidosMultiples.csproj /p:Configuration=Release`. Yo copio solo el .exe al PC de la U.
2. No toques el AutoUpdater (`pedidos_multiples_odoo.xml`), ni la URL de actualización, ni la versión (0.8.0.9).
3. No enseñes credenciales en los resúmenes: pon ***. El repo tiene credenciales en App.config y en el código.
4. No hagas push si no te lo pido. Ahora mismo no hay nada en commit.
5. Cambios mínimos. No cambies el comportamiento de las otras empresas (NATH, ALAN, CODE, TCN, TTUC).
6. Acciones de servidor de Odoo 13 (safe_eval):
   - nunca f-strings (siempre `%`);
   - sin `import`, sin comprensiones de listas y sin `reversed()`;
   - `log(...)` siempre ANTES de `raise Warning(...)`.
7. Antes de cualquier acción de Odoo que escriba, haz una versión **DIAGNÓSTICO** que no escriba nada y acabe con `raise Warning`. La ejecuto yo en la acción de pruebas **id 1837** (modelo stock.picking) y te paso el resultado.
8. Pregúntame antes de instalar nada o de tocar ficheros fuera del repo.
9. **No sobrescribas nunca versiones.** Cada página, plano o acción nueva va a `bin/` o `bin/versiones/` con fecha y hora en el nombre (`_AAAA-MM-DD_HHMM_vN-descripcion`).
10. Nunca escribas contraseñas de Odoo. Prohibido "Force Availability" y prohibido el botón "Hecho" de las agrupaciones.
11. Todos los cálculos de oleadas y picking se hacen sobre **10.000 u/día**.

## Sistema
- **Odoo 13 Enterprise**, BD `NATH_PRODUCTION`, https://nath.tuctuc.com. KOROSHI es la empresa **Effective Logistics, company_id = 8**.
- **Pedidos de tienda**: tipo "PED. TIENDAS". Un pedido es una tienda y un albarán OUT (`EFFEC/OUT/…`). El origen es el pedido `S-…`.
- **Matrículas de caja**:
  - modelo `zebra.label`, código "CJ…" (ej. CJ665004351);
  - secuencia `zebra.label.code`;
  - se crean con `create_next_labels(quantity=, note=)`.
- **Transportista XPO**: módulos `delivery_xpo` y `merge_delivery_shipment`. Hay un envío por tienda con el número final de bultos. La etiqueta XPO se genera al final, por tienda; no se puede hacer por caja al principio.
- **PDA**: app de códigos de barras de Odoo + módulos de Brain Station 23. Todas las PDA entran con el usuario "Almacén Nath".
- **Programa "Pedidos Múltiples"** (C#, en la U, para las oleadas):
  - El 21/10 se arregló un cast en `PedidosMultiples/OdooAccion.cs` (`BuscarPickingId`: `search` devuelve `int[]`; se usa `as Array`).
  - En `bin/Release/PedidosMultiples.exe.config` se corrigió el usuario a `@nath.es`.

## Qué pasó el 21/10 (prueba real)
- **Oleada + U** (B-KOR-2110-01):
  - 10 tiendas, 1.482 u cogidas.
  - Picking de 6:10 a ~8:25, unas 180 u/h por persona.
  - La U leyó a unas 277 u/h. En total, unas 8 h 30 de principio a fin.
  - Incidencias:
    - Líneas "fantasma" de la PDA al escanear un artículo equivocado, que daban el error "El registro no existe (stock.move)". Se arregló con `odoo/KOROSHI_borrar_lineas_fantasma_INT.py`.
    - Alguien pulsó Force Availability. Se deshizo con `odoo/KOROSHI_deshacer_force_availability.py`.
- **Zonas sin U** (Z-2110-D1…D5 + ZX = NAVE2):
  - 25 tiendas y 1.696 u, partidas en 118 OUT.
  - De 9:35 a 12:59, unas 491 u/h de equipo, con 7–8 personas. Las cajas salen ya cerradas.
  - **Conclusión: el método elegido es el de zonas.**
- Se cancelaron 12 pedidos pendientes "En espera" para que S4T sincronice.
- KPI para el jefe, ya enviados:

  | Método | Personas | s/u |
  |---|---|---|
  | Oleada | 5 picking + 1 U | ~52 |
  | Zonas | 7–8 | ~51–58 |

## Acciones y registros de Odoo ya creados
| Qué | ID en Odoo | Fichero en el repo |
|---|---|---|
| Partir pedidos en OUT por zona | acción de servidor (se pega en 1837 o en la suya) | `odoo/KOROSHI_partir_OUT_zonas.py` |
| Etiquetas de zona (reserva la CJ e imprime) | **ir.actions.server 1843** "KOROSHI Etiquetas zona", menú **Acción**, **MODO = 'REAL'** | `odoo/KOROSHI_etiquetas_zona.py` (en el repo pone DIAGNOSTICO; en Odoo está en REAL) |
| Informe de la etiqueta | **ir.actions.report 1842** "KOROSHI Etiqueta zona", qweb-pdf. **Quitado del menú Imprimir** (desde Imprimir salía sin CJ) | — |
| Plantilla QWeb | **ir.ui.view 6035**, key `koroshi.report_etiqueta_zona` | `odoo/KOROSHI_report_etiqueta_zona.xml` (igual que Odoo, v6) |
| Formato de papel | **report.paperformat 19** "KOROSHI 4x6 (101,6 x 152,4)" | — |
| Crear los INT por zona para la oleada (v4: un movimiento por artículo) | sin probar todavía en 1837 | `odoo/KOROSHI_crear_INT_zonas.py` |
| Instrucciones de la etiqueta | — | `odoo/KOROSHI_etiqueta_zona_INSTRUCCIONES.md` |

**Acción de partir OUT por zonas:**
- **Qué coge:** OUT de "PED. TIENDAS" creadas hoy, en estado Preparada, sin ninguna unidad leída, que no sean de una oleada B-KOR ni vengan del SORTER.
- **Cómo reparte:**
  - Divide los lineales en N_ZONAS zonas con el mismo tiempo de trabajo, con SEG_HUECO = 20, SEG_UD = 4 y SEG_LINEAL = 15.
  - Cada OUT se queda en su zona principal. Por cada otra zona crea una OUT nueva con el mismo origen S-….
- **Agrupaciones:**
  - Una por zona: `Z-ddmm-D1…`.
  - Si hay más de 25 tiendas, hace rondas: `Z-ddmm-R1-D1…`.
- **Nota de cada OUT:** `Z-ddmm-D3 | CAJA 05 | K34 … | PEDIDO S-…`.
- **Modos:** DIAGNOSTICO, SIMULAR (hace y deshace) y REAL.
- **Copia preparada para el 22/10:** `bin/KOROSHI_partir_OUT_zonas_2026-10-21_1530_v4-8-zonas-todas-las-tiendas_DIAGNOSTICO.py`, con N_PEDIDOS = 200, N_ZONAS = 8, TIENDAS_POR_RONDA = 25 y ELEGIR = 'GRANDES'.

**Acción de etiquetas de zona (1843):**
- Por cada OUT seleccionada, calcula las cajas por volumen: **LITROS_CAJA = 80**, como máximo 12 cajas.
  - Con el volumen de Odoo; si falta, con los litros por tipo según `default_code[4:6]`.
  - Calibrada con 97 OUT: ninguna se quedó corta.
- Reserva las matrículas CJ con la nota `ETQ ZONA <OUT>`. Si ya existen, las reutiliza y no gasta nuevas.
- Abre el PDF del informe 1842, con una etiqueta por CJ.
- Se salta las OUT que ya están hechas o canceladas.

**Etiqueta 4x6" (de arriba abajo):**
1. Zona (D3) y "CAJA TIENDA" nº.
2. Banda negra con **DELEGACIÓN · TRANSIT 24/48 h**.
3. Tienda (K34 …) con la ciudad y las unidades al lado.
4. **PEDIDO S-…** en grande, con su código de barras.
5. "CAJA n" y "· tienda también en D2 · D5…" (solo en OUT de agrupaciones Z-).
6. Código de barras de la OUT.
7. Código de barras de la matrícula CJ.

En la plantilla, las delegaciones están en un diccionario `knum → (nombre, horas)`. Si la tienda no está en la lista, sale "PROV. + provincia".

**Faltan en la lista de delegaciones: K17, K77, K82, K85, K86.** La K48 salía dos veces; se puso VALENCIA 24 h, pendiente de confirmar. Me pasarán más delegaciones: hay que añadirlas al diccionario de la vista 6035 y del XML del repo (versión nueva en `bin/`).

## Cómo trabajar con Odoo
- Desde el panel del navegador, con mi sesión ya iniciada, por JSON-RPC: `fetch('/web/dataset/call_kw', …)` con `context: {allowed_company_ids: [8]}`.
- Para leer, sin problema.
- **Para escribir, solo con mi permiso explícito en cada caso.**
- Vista previa de la etiqueta sin imprimir: `/report/html/koroshi.report_etiqueta_zona/<picking_id>?context={"allowed_company_ids":[8]}`. Sin el context da 403.
- OUT de prueba: 20305 (picking id 380532, K86), con CJ665004351.

## Plan para el 22/10 (8 personas, 8 zonas)
1. Pegar la copia v4 de la acción de partir en la acción de pruebas y ejecutarla en **DIAGNOSTICO**. Revisar el reparto de zonas, las rondas y las OUT que se salta. Después **SIMULAR** y después **REAL**.
2. Por cada agrupación Z-2210-Dx: Inventario › Transferencias › filtrar por la agrupación › seleccionar todas las OUT › **Acción › KOROSHI Etiquetas zona**. Sale una etiqueta por caja prevista, con su CJ.
3. Cada operario hace su zona con la PDA (escanea la OUT, coge, escanea la CJ al cerrar la caja y valida).
4. Al final, juntar las cajas de cada tienda en expediciones (la delegación en la etiqueta ayuda) y generar el XPO por tienda.
5. Ir midiendo: hora de inicio y fin por zona, unidades, cajas reales frente a etiquetas e incidencias.

## Pendiente / ideas
- Añadir las delegaciones que lleguen y confirmar la K48.
- Poner el fichero del repo `odoo/KOROSHI_etiquetas_zona.py` en MODO = 'REAL', igual que en Odoo.
- En las OUT partidas, las columnas "Demanded/Reserved Quantity" de la lista salen infladas (son campos guardados copiados del original). Las unidades reales están bien.
- Etiqueta de "bulto agrupado": varias cajas pequeñas de una tienda en un solo bulto, con una CJ de bulto y la lista de CJ que contiene.
- Probar en 1837 la acción de INT v4 antes de usarla en la acción programada de oleadas.
- Hacer commit de todo lo que hay en `bin/` y `odoo/` cuando yo lo diga.
