# Prompt para Fable: programa de redistribución de zonas (Outlet, Z y 0) — 23/11/2026

> Pegar tal cual en una sesión nueva con Fable, abierta en `C:\dev\OleadasKoroshi`.

---

Quiero diseñar contigo un programa para el almacén. **No escribas código todavía**: quiero tu propuesta de diseño,
qué harías distinto de lo que tengo pensado y qué te falta saber. Contesta en castellano.

## Quién soy y dónde estamos

Soy Isaac, de informática, y estoy aprendiendo logística: el jefe me propone como responsable de logística. Almacén
KOROSHI (moda; Effective Logistics, compañía 8 de Odoo, nave NAU-2). Odoo 13 Enterprise en producción
(nath.tuctuc.com). Los operarios preparan pedidos con PDA todo el día: cualquier fallo en Odoo se nota al momento.

Antes de nada lee `CLAUDE.md` (reglas no negociables), `TABLERO.md` (qué está en curso) y `README.md` (mapa de
módulos).

## Qué quiero

**Compactar = hacer una nueva distribución de la zona Outlet, la zona Z y la zona 0.** El layout actual está muy
mal y hay que mejorarlo. El programa tiene que ayudarme a:

1. **Ver cómo está ahora** cada zona: qué hay en cada hueco, ocupación frente a su capacidad, modelos mezclados o
   repartidos en muchos huecos, mercancía que no se mueve. Mejor como **mapa** que como lista.
2. **Definir reglas** de qué va en cada zona y dónde (por ejemplo: Outlet = lo que no es de la temporada actual; lo
   que más rota más cerca de expedición, con ABC; cada modelo junto en el mínimo de huecos; respetar volumen y peso).
3. **Proponer la nueva distribución** (otro mapa) con sus números: huecos liberados, metros de picking ahorrados.
   Poder cambiar reglas y recalcular.
4. **Sacar el plan de movimientos**: «este contenedor, de este hueco a este otro», por tandas y en orden, en hoja o
   CSV. Los mueve la gente con la PDA, con lo que ya existe (`koroshi_contenedores`).

Más adelante también quiero meter aquí lo que ahora hago en Excel (MASTER, desviaciones; ver abajo).

## Decisión ya tomada: programa aparte, no módulo de Odoo

- Programa en **Python** en mi PC, con **pantalla web local** (tablas, filtros, mapas, exportar a Excel).
- Lee Odoo **solo en lectura**: un usuario de Odoo de solo lectura por XML-RPC (aún no existe; lo crearía yo),
  descarga a **SQLite local** cuando se lo pido y trabaja sobre esa copia.
- **No escribe nada en Odoo.** La ejecución física sigue en la PDA.
- Motivos: no arriesgar la PDA (actualizar módulos echa a la gente de la sesión unos minutos y arrastra a los
  dependientes), poder cambiarlo cada día sin empaquetar ni instalar, y no tocar tablas compartidas.
- Si discrepas, dímelo con argumentos.

## Reglas que el programa debe respetar (de CLAUDE.md)

- Todo en castellano: código, comentarios, pantallas y documentos.
- No tocar datos de producción; las pruebas reales, solo reversibles.
- Nada en el servidor sin mi permiso explícito, comando a comando. Contraseñas y claves nunca en el código (van
  en la configuración local); no copiar las credenciales versionadas de `PedidosMultiples/`/`App.config`.
- Nunca sobrescribir versiones: cada versión con su nombre y fecha en `bin/versiones/`.

## Lo que ya existe y sirve de base

### En Odoo / PDA
- `odoo/modulos/koroshi_contenedores`: en la PDA, escanear un hueco → sus contenedores (KO_/TT_, sububicaciones)
  con uds; mover uno o varios a otro hueco; archivar vacíos. Diseño de la 1.5.0 (compactar un hueco: elegir,
  archivar, mover) en `bin/versiones/diseno-koroshi_contenedores-1.5.0_2026-11-18.md`.
- `koroshi_buscador_stock`: buscador de stock de oficina (EAN, referencia, hueco, lineal, contenedor).
- Huecos tipo lineal / palet / columna, nombres como `L94-P2-C1`. Los «Z1–Z5» de los scripts de reparto por zonas
  de picking (`bin/KOROSHI_crear_INT_zonas_*.py`) son **tramos de lineales** (I/D, lineal 1–136), no la zona física Z.
  **Pendiente confirmar** qué ubicaciones de Odoo forman las zonas Outlet, Z y 0.

### Excels (en `bin/versiones/`)
- **Libro 1 MASTER** `261120_KOROSHI_1_MASTER_OI_26-27_v13.xlsx`: una fila por modelo (467 modelos de la OI 26/27):
  comprado (packing list), recibido, pendiente, salidas, stock, implantación y reposición por tienda (51 tiendas
  físicas; implantación = uds a cada tienda en los 5 días siguientes a su primer envío), web, otros (About You,
  Zalando, muestras), fechas de recepción e implantación. Datos de Odoo del 20/11.
- **Libro 2 Recepción y desviaciones** `261123_KOROSHI_2_Recepcion_y_desviaciones_v2.xlsx`: desviación por SKU
  (stock Odoo − (recibido − salidas)), índice por modelo-color y por modelo (falta + sobra en valor absoluto),
  cruce de tallas y entre colores, seguimiento del objetivo 95 % localizado/regularizado.
- **Libro 3 Layout y ubicaciones** `261120_KOROSHI_3_Layout_y_ubicaciones_v2.xlsx`: Matriz artículos,
  Clasificación ABC, Parámetros, Tipos de hueco, Caja por modelo, Ubicación por modelo, Pedido tipo,
  Prestatgeries, Inventario columnas, Por talla, Ubicación virtual, Caja combinada, Datos MASTER. **Prestatgeries e
  Inventario columnas están vacías**: faltan las fotos del recuento de estanterías y columnas (las tengo yo).

### Datos y scripts de extracción (solo lectura)
- `odoo/KOROSHI_exportar_tallas_MASTER_SHELL_2026-11-20.py` → `bin/versiones/20261120_tallas_MASTER_odoo.csv`
  (3.726 SKU: modelo, color, talla, referencia, EAN, peso y volumen de ficha, recibido, pendiente, salidas, stock).
- `odoo/KOROSHI_salidas_tiendas_MASTER_SHELL_2026-11-20.py` → salidas a clientes por día (100.116 filas, 355.154
  uds) y `20261120_recepciones_MASTER_odoo.csv` (1ª/última recepción por modelo).
- Se ejecutaron con `odoo-bin shell` en el servidor, a mano y con permiso. El programa nuevo debería sustituir esto.

## Datos y parámetros conocidos

- Caja de envío 60×40×33 (≈0,079 m³); caja llena real ≈ **0,084 m³ de volumen Odoo (~10 uds, muy variable)**:
  estimar por volumen, no por unidades. Caja de almacén del Excel: 93 L, máximo 18 kg.
- Volumen de ficha = el del packing list por modelo (igual en todas las tallas); **peso en ficha = 0**; ~1/3 de
  productos sin volumen.
- ABC: A hasta 80 % de salidas, B hasta 95 %. Temporada actual 26 (Parámetros del libro 3).
- Volumen de referencia para picking: **día de 10.000 uds** (media real ~4.600, puntas 20.000). Ritmos medidos:
  picking por oleada ~180 u/h·persona, tradicional ~81, puesto U ~250 u/h.
- Pedidos de tienda: días de implantación (artículo compartido por muchas tiendas, ~mitad del volumen) y de
  reposición (1,3–3 tiendas por SKU). Web es poco (2.860 uds de la OI 26/27).

## Lo que no sé y quiero que me ayudes a decidir

1. Cómo definir capacidad de cada hueco (volumen útil, nº de contenedores, nº de cajas) con lo que puedo medir.
2. Qué reglas de slotting tienen sentido aquí (rotación, implantación vs reposición, familia, temporada, tallas
   juntas o separadas).
3. Cómo representar el mapa de la nave para que sea útil y mantenible (¿coordenadas por lineal/posición?).
4. Cómo generar el plan de movimientos para que sea ejecutable por tandas sin parar el picking.
5. Estructura del proyecto (carpetas, módulos Python, SQLite, librerías para la pantalla) y por qué fases empezar.

Dame primero el diseño y la lista de preguntas para mí; luego decidimos.
