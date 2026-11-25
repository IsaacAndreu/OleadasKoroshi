# Prompt para Opus 5.5: programa de redistribución, fase 1 (datos reales de Odoo y «cómo está ahora») — 23/11/2026

Pegar tal cual en una sesión nueva con Opus 5.5, abierta en `C:\dev\OleadasKoroshi`.

---

Quiero la **fase 1 del programa de redistribución de zonas** del almacén KOROSHI: leer Odoo en solo lectura,
guardar una copia en mi PC y enseñar en el mapa cómo está hoy la nave con datos de verdad. Contesta y escribe todo
en castellano. Va en tres pasos y **paras al final de cada uno** a esperar mi visto bueno.

## Antes de empezar

Lee `CLAUDE.md` (reglas no negociables), la fila «Programa de redistribución» de `TABLERO.md` y
`redistribucion/prototipo-mapa_2026-11-23_v2/README.md` (el mapa elegido como base). Lo que te afecta:

- Todo en castellano: código, comentarios, textos de pantalla y documentos.
- Es un **programa aparte** en mi PC. No se toca nada de `odoo/modulos/`, no se instala ni se sube nada al
  servidor y **no se escribe nada en Odoo**.
- Nunca sobrescribir una versión: carpetas y copias nuevas con fecha.
- No copiar credenciales de `PedidosMultiples/` ni de `App.config`. No hagas commit: me lo enseñas y decido yo.

## Para qué sirve

- La nave NAU-2 tiene 136 lineales; la ubicación de Odoo es `L03 P05 C4` (lineal, posición, nivel).
- Dos zonas, definidas por la temporada del producto: **0** = temporada actual (I27 + V27) y **Z = Outlet** = todo
  lo demás. Hoy están mezcladas.
- **Objetivo principal: tener cada modelo junto.** Hoy el mismo modelo está en varios lineales y eso nos da
  faltantes. Segundo objetivo: ahorrar metros de picking.
- Lo del muelle (MU-), N1-, perchas y contenedores sin ubicación no entra en el reparto: se enseña aparte como
  «pendiente de ubicar».

## Cómo se lee Odoo (lo más delicado)

No puedo crear un usuario de solo lectura (los usuarios de Odoo se pagan). Se usa el usuario **Departament IT**,
que **sí puede escribir**. Por eso la solo lectura la tiene que garantizar el programa:

1. **Lista blanca de métodos.** Un único módulo (`odoo_lectura.py`) habla con Odoo por XML-RPC y solo deja pasar
   `search`, `search_read`, `read`, `search_count`, `read_group` y `fields_get` (más `version` y `authenticate`).
   Cualquier otro método lanza un error **antes** de enviar nada. Ningún otro fichero importa `xmlrpc`. Con una
   prueba automática que lo demuestre (`write`, `create`, `unlink`, un `action_…` y un método inventado).
2. **La contraseña no la ves ni la pides.** La guardo yo en el almacén de credenciales de Windows con `keyring`;
   dame el comando exacto para hacerlo. El programa la lee de ahí. Nunca se imprime, ni en errores ni en el
   registro. La dirección, la base de datos y el nombre de usuario van en `config.local.toml`, fuera de git
   (añade lo necesario a `.gitignore`, también las copias SQLite).
3. **Cada ejecución contra producción, con mi sí.** No lances tú ninguna lectura a nath.tuctuc.com sin que te lo
   diga en ese momento. Deja los comandos preparados y dime qué va a leer cada uno y cuánto calculas que tarda.
4. **Sin cargar el servidor.** Los operarios trabajan con PDA todo el día. Lecturas por páginas (2.000–5.000
   filas), una petición cada vez, con una pausa corta entre páginas, solo los campos necesarios y siempre con la
   compañía 8. La descarga grande del histórico de salidas se hace fuera de horas.

## Qué hay que comprobar antes de escribir el modelo de datos

No des por buenas estas tres cosas; míralas en el código y dime qué has encontrado:

- **Los contenedores KO_/TT_ son sububicaciones (`stock.location`) hijas del hueco**, no paquetes: así los trata
  `odoo/modulos/koroshi_contenedores/controllers/main.py`. El README del prototipo v2 habla de
  `stock.quant.package`; creo que está mal.
- **De dónde sale la temporada del producto**: mira cómo la sacan `bin/KOROSHI_crear_INT_zonas_PLANIFICADA.py` y
  `odoo/KOROSHI_exportar_tallas_MASTER_SHELL_2026-11-20.py` (también modelo, color, talla, familia y volumen).
- **Niveles**: L121–L136 tienen más de 4 ubicaciones por posición. Los nombres que no encajen con `Lnn Pnn Cn`
  se guardan y se listan; no se descartan en silencio.

Volumen: la ficha lleva el del packing list; ~1/3 de los productos no tiene y el peso es 0. Donde falte, usa los
litros medios por tipo de prenda de la tabla `TIPOS` de `odoo/modulos/koroshi_kpi/models/kpi.py`, marcando el dato
como estimado.

## Paso A — Cliente de solo lectura y prueba de conexión

- Estructura del programa en `redistribucion/programa/` (propón tú las carpetas; funciones puras separadas de la
  lectura y de la pantalla, para poder probarlas sin Odoo).
- `odoo_lectura.py` con la lista blanca y sus pruebas.
- Un comando «probar conexión» que solo lee la versión de Odoo y **cuenta** filas de cada modelo que se va a
  descargar (`search_count`), para saber el tamaño antes de bajar nada.
- **Parar.** Me das el comando de `keyring`, el de la prueba y qué cuentas esperas ver.

## Paso B — Descarga a SQLite

- Una copia por descarga, con fecha y hora en el nombre; nunca se pisa la anterior.
- Tablas mínimas: ubicaciones (con su padre, código de barras y si está activa), stock por ubicación y producto
  (cantidad y reservado), productos (referencia, EAN, modelo, color, talla, temporada, familia, volumen) y salidas
  hechas (producto, ubicación de origen, cantidad, fecha, tipo de operación) desde la fecha que yo diga.
- El histórico de salidas se baja incremental (por id), para que las siguientes veces sea rápido.
- Al acabar, un resumen: filas por tabla, unidades totales y por zona, y lo raro (nombres que no encajan, productos
  sin temporada o sin volumen, stock negativo). Compáralo con el Excel MASTER del 06/11 (422.873 uds en NAVE2;
  236.866 de zona 0 y 135.132 de zona Z entonces) y dime si las diferencias tienen sentido.
- Pruebas con una copia pequeña inventada (sin Odoo), para que el resto del programa se pueda probar siempre.
- **Parar.** Me das el comando de descarga, lo que leerá y el tiempo estimado; la lanzo yo o te digo cuándo.

## Paso C — El mapa con datos reales y las listas

Parte de `redistribucion/prototipo-mapa_2026-11-23_v2/` (Canvas 2D + d3; no vuelvas a ECharts) en una carpeta
nueva `_v3`. No cambies su aspecto ni su forma de usarse: cambia de dónde salen los datos.

- El mapa lee un JSON generado desde la copia SQLite elegida (se ve qué copia y de qué fecha).
- **Reales por hueco**: zona, ocupación (contenedores y litros), unidades, nº de modelos-color, niveles tal como
  existen en Odoo y contenedores de cada hueco con sus unidades. Fuera todos los «DATOS DE EJEMPLO» de estos puntos.
- **Medida nueva, la más importante: dispersión del modelo.** Para cada modelo-color, en cuántos lineales y huecos
  está. El buscador ilumina todos los huecos de un modelo de verdad.
- **Calor de picking**: salidas de las últimas 4 semanas por hueco (visitas, no unidades).
- Las cifras del «Plan Z5+01» eran una estimación del 06/11 sin probar: sácalas de la cabecera o márcalas bien
  claras como estimación antigua. Los movimientos siguen de ejemplo y marcados (son de la fase 3).
- **Listas**, con filtro y exportar a Excel:
  1. Modelos repartidos (de más a menos lineales), con sus huecos y unidades en cada uno.
  2. Contenedores a cero sin archivar, por hueco.
  3. Huecos con zona 0 y Z mezcladas.
  4. Stock sin salidas en N días (N lo elijo yo en pantalla).
  5. Pendiente de ubicar (muelle, N1-, sin ubicación).
- Al abrir el prototipo v2 una vez me salió el plano en blanco hasta recargar; mira si es un fallo de tamaño al
  cargar y arréglalo en la v3.
- Compruébalo tú en el navegador (entrada nueva en `.claude/launch.json`): sin errores en consola, los tres
  niveles, la dispersión y las listas.

## Qué quiero al acabar cada paso

Qué has hecho (`archivo:línea`), cómo lo has probado, qué no has podido probar y qué tengo que hacer o decidir yo.
En el paso C, además: capturas, los tres números que enseñaría a mi jefe (por ejemplo, cuántos modelos están en
más de un lineal) y qué datos faltan para la fase 2 (capacidad por tipo de hueco, reglas y propuesta).
