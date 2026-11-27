# Prompt para Fable 5.2: revisión crítica de todo lo que tenemos (27/11/2026)

Modelo: Fable 5.2, esfuerzo high. Sesión SOLO DE LECTURA Y REVISIÓN.

---

Eres revisor externo. Tu trabajo es encontrar lo que está mal, lo que se contradice, lo que falta y lo que se nos ha
pasado por alto en el trabajo de las últimas dos semanas del almacén KOROSHI (Effective Logistics, compañía 8, nave
NAU-2, Odoo 13 EE en nath.tuctuc.com). No eres el autor: no defiendas lo hecho, cuestiónalo con datos. Todo en
castellano.

## Antes de empezar

Lee CLAUDE.md, TABLERO.md y README.md de C:\dev\OleadasKoroshi, y la memoria del proyecto (MEMORY.md y las notas que
enlaza, en C:\Users\tuctuc\.claude\projects\C--dev-OleadasKoroshi\memory\). Son las reglas y el contexto.

## Reglas de esta revisión (no negociables)

- Solo leer. No tocar código, ni módulos, ni versiones, ni git. No escribir en Odoo. No instalar nada.
- Si consultas Odoo, solo lectura (search_read, read_group, search_count) por JSON-RPC desde una pestaña con sesión,
  context {allowed_company_ids:[8]}. Si no hace falta, no lo consultes: la copia diaria del programa ya tiene datos.
- Cada observación con su prueba: archivo:línea, cifra con su origen, o consulta. Si es una sospecha sin comprobar,
  ponlo como «hipótesis» y di qué dato la confirmaría. No inventes nada (Isaac lo pide expresamente).
- Hay otras sesiones trabajando en estos temas: no les escribas ni edites sus ficheros.

## Qué hay que revisar (lee los documentos, no te fíes de este resumen)

### 1. Redistribución y compactación de la nave
- Programa: redistribucion/programa/ (README.md, programa.py, redistrib/compactar.py, pruebas/). Orden `compactar-0`.
- Reglas: redistribucion/fase2_reglas-a-decidir_2026-11-24.md y redistribucion/fase2b_compactacion-zona0_2026-11-26.md.
- Resultados: redistribucion/compactacion-zona0_20261126_*.xlsx (el último es el bueno).
- Estanterías zona Z: redistribucion/estanterias-zona-z_hojas-20261102_transcripcion-20261127.csv (de las hojas a mano
  del 02/11, L01–L43; la zona 0 está casi entera en L44–L136 y de ahí no hay hojas).
- Mapas: redistribucion/prototipo-mapa_2026-11-26_v4.
- Diseño en Odoo: bin/versiones/diseno-compactacion-odoo-retirar-vacias-juntar-cajas_2026-11-26_v6.md (y v1–v5 para ver
  cómo ha cambiado) y bin/versiones/diseno-compactacion-zona-z-tareas_2026-11-27_v1.md (tareas en la PDA, 8 preguntas
  abiertas a Isaac).
- Datos conocidos: libera ~1.216 de 3.329 huecos de la 0 (36,5 %); fase 1 (solo KO enteras) 1.711 columnas con 2.779 KO
  (tope 8 cajas) o 1.650 con 2.631 (tope 7); 6.167 KO con la opción A. C1–C4 en Odoo son columnas (palés), 4 cajas de
  alto; 19.190 de 39.246 contenedores de L44+ están a 0 en Odoo. Decisiones 13 (altura de caja) y 14 (cajas de fondo por
  columna) pendientes.
- Criterios de Isaac (reunión 26/11): primero lo que sale, contando la profundidad (líneas, no unidades); talla completa
  para el multimarca; en un hueco compartido modelos lo más distintos posible; el mismo artículo no se mezcla; restos
  de talla al fondo; no ordenar por colección. Estimación suya: liberar 30–40 % del suelo, ~70 % con Z.

### 2. Zonas de preparación
- bin/versiones/diseno-zonas-modo-del-dia_2026-11-20.md, diseno-zonas-criterio-tiempo-cajas-picos_2026-11-26.md,
  diseno-zonas-que-aprenden_2026-11-26.md y el módulo odoo/modulos/koroshi_zonas (1.10.0 sin instalar).

### 3. Faltantes
- Investigación: bin/versiones/20261126_investigacion-faltantes_v1.md (+ .xlsx) y faltante relativo
  20261127_faltante-relativo_koroshi_v1.html. Ronda: 20261124_ronda-faltantes-prioritarios_koroshi_v1.xlsx.
- Módulo: odoo/modulos/koroshi_faltantes.
- Datos conocidos (24/11): 2.666 líneas canceladas 16–23/11 sobre 386 SKU, 73–88 % repetidas cada día; 223 SKU a 0 por
  ajustes de inventario (497 uds, usuario compartido «Almacén Nath»); 459 faltantes desde el 01/11, 3 encontrados; la
  ronda INT/67387 (126 líneas) abierta sin tocar.

## Qué quiero que respondas

1. **Errores**: cálculos, supuestos o reglas que estén mal o no cuadren con los datos (p. ej. capacidad de hueco de
   770 L, cajas a 0 que ocupan sitio, ABC por líneas de 28 días en final de temporada).
2. **Contradicciones** entre documentos, versiones del diseño, el programa y lo que decidió Isaac.
3. **Lo que se nos ha pasado por alto**: riesgos para la PDA y el almacén (recuerda: campos nuevos en tablas
   compartidas tumbaron la PDA el 03/11), interacción compactación ↔ zonas ↔ faltantes ↔ recepción, devoluciones,
   final de temporada (chaquetas), datos de Odoo que no cuadran con la nave, quién ejecuta y cuánto tarda.
4. **Mejoras** concretas, ordenadas por impacto (huecos liberados, horas, errores evitados) frente a esfuerzo.
5. **Orden recomendado** de lo pendiente y qué decisiones de Isaac bloquean más cosas (con tu recomendación en cada una).
6. Qué datos faltan para decidir y cómo conseguirlos con el menor trabajo en la nave.

## Entrega

Un único documento: bin/versiones/revision-fable-compactacion-zonas-faltantes_2026-11-27_v1.md, con un resumen de una
página al principio (lo 10 más importante) y después el detalle por apartado. Cada punto: qué, prueba, impacto,
propuesta. Sin commit. Al acabar, para y espera a Isaac.
