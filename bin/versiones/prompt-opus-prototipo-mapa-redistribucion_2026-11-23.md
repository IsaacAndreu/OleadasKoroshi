# Prompt para Opus 5.5: prototipo del mapa de la nave (programa de redistribución) — 23/11/2026

Pegar tal cual en una sesión nueva con Opus 5.5, abierta en `C:\dev\OleadasKoroshi`.

---

Quiero un **prototipo del mapa de la nave** para decidir cómo se verá el programa de redistribución de zonas del
almacén KOROSHI. Es solo para enseñármelo y elegir: no es el programa final. Contesta y escribe todo en castellano.

## Antes de empezar

Lee `CLAUDE.md` (reglas no negociables). Lo que te afecta aquí:

- Todo en castellano: código, comentarios, textos de pantalla.
- **No se conecta a Odoo ni al servidor.** El prototipo trabaja solo con ficheros que ya están en el repo.
- No se toca ningún módulo de `odoo/modulos/`. Esto es un programa aparte.
- Nunca sobrescribir una versión: si rehaces el prototipo, carpeta o fichero nuevo con fecha y versión.
- No copiar credenciales de `PedidosMultiples/` ni de `App.config`.

## Contexto en cinco líneas

- La nave NAU-2 tiene 136 lineales (L01–L136). Cada lineal tiene posiciones (P00–P17 a la izquierda del pasillo
  central, P18 en adelante a la derecha) y cada posición tiene niveles (C1–C4). La ubicación de Odoo es
  `L03 P05 C4`. Dentro de cada ubicación hay contenedores `KO_…` / `TT_…` con las prendas.
- Hay dos zonas, definidas por la temporada del producto y no por la ubicación: **Z = Outlet** (temporadas viejas)
  y **0** (temporada actual, I27 + V27). Hoy están mezcladas.
- El objetivo de la redistribución es **tener cada modelo junto** (hoy el mismo modelo está en varios lineales y eso
  provoca faltantes) y ahorrar metros de picking.
- Los mapas que hicimos el 06/11 no me gustan nada y no quiero que se parezcan:
  `bin/versiones/20261106_1600_warehouse_planner_NAU2_zonas-antes-despues_v43b.html` y
  `bin/versiones/20261106_1900_SIMULADOR-nau2-zonas-0-y-Z-plano_v3-master-OI2627-odoo-hoy.html`.
  Ábrelos para ver qué evitar: mezclan editor y visor, los paneles tapan el plano, toda la nave va en un recuadro
  pequeño con celdas ilegibles, los colores son fijos sin escala y los datos van incrustados en el HTML.

## Datos que puedes usar (solo estos)

- `bin/versiones/20261106_1630_MASTER-zonas-0-y-Z-layout-estanterias-cajas_v1.xlsx`
  - hoja **Layout hoy**: una fila por lineal y una columna por posición (P00…), con la zona de cada posición;
  - hoja **Por lineal**: posiciones, ubicaciones de Odoo, posiciones ocupadas, % de ocupación, unidades, unidades
    de zona 0 y de zona Z por lineal;
  - hoja **Layout compactado Z5+01**: sirve de «después» para la vista antes/después;
  - hoja **Medidas estanterias**: medidas reales de la estantería (120 × 160 × 40 cm).
- Geometría en metros: `odoo/modulos/koroshi_kpi/models/kpi.py`, funciones `_x(lineal)`, `_y(pos)`, `BASE`
  (expedición) y `CRUCES` (pasillos transversales). Cópiala al prototipo (no importes el módulo de Odoo).

Antes de dibujar, abre las hojas y dime **qué medidas dan de verdad esos datos** y a qué detalle (por posición o
solo por lineal). **No inventes datos.** Lo que no esté en los ficheros (por ejemplo, contenedores de un hueco o
modelos por posición) se enseña con un ejemplo pequeño marcado en pantalla como «DATOS DE EJEMPLO», nunca mezclado
con lo real.

## Qué tiene que hacer el prototipo

1. **Solo visor.** No se edita ni se dibuja el plano: la geometría sale de los datos.
2. **Tres niveles de zoom:**
   - **Nave**: una celda por posición, en metros reales, con el pasillo central, los transversales y expedición.
   - **Lineal en alzado**: al tocar un lineal, sus posiciones × niveles C1–C4.
   - **Hueco**: al tocar una celda del alzado, la lista de sus contenedores (aquí, datos de ejemplo).
3. **Una medida cada vez**, elegida en un desplegable (las que permitan los datos: zona, % de ocupación, unidades,
   % de zona Z…), con **escala de color que también filtra** (arrastrar la escala apaga lo que queda fuera).
4. **Encima de la medida, solo contornos y flechas**: límite de zona y, como ejemplo, 5–10 flechas de movimientos
   «de este hueco a este otro».
5. **Antes y después lado a lado**, con el zoom y el desplazamiento sincronizados, y un botón de «diferencia».
6. **Buscador**: escribir un lineal o un modelo y que se iluminen sus celdas (el modelo, con datos de ejemplo).
7. Texto al pasar el ratón con los datos de la celda. Botón para guardar la vista como PNG.
8. Los datos van en un JSON aparte, generado por un script de Python desde el Excel; la página no los lleva dentro.
9. Que se lea bien en una pantalla de portátil sin hacer zoom a ciegas: el plano ocupa casi toda la pantalla y los
   controles van en una barra estrecha arriba.

## Con qué hacerlo

- **Apache ECharts** (serie `custom` para los rectángulos en metros, `visualMap` para la escala con filtro, series
  de líneas para las flechas). Un único fichero JS con versión fija, sin Node ni compilación.
- Python solo para sacar el JSON del Excel (`openpyxl`) y para servir la carpeta en local.
- Si a mitad ves que ECharts no da para algún punto (sobre todo el 5 y el rendimiento del alzado), dímelo con el
  motivo antes de cambiar de librería; la alternativa pensada es deck.gl con vista plana.

## Dónde va

- Carpeta nueva `redistribucion/prototipo-mapa_2026-11-23_v1/` en la raíz del repo: `extraer_datos.py`,
  `datos.json`, `index.html`, `mapa.js`, `README.md` (cómo se arranca y de dónde sale cada dato).
- Añade una entrada a `.claude/launch.json` para servir esa carpeta en local (mira las que ya hay) y compruébalo
  en el navegador tú mismo: sin errores en consola, los tres niveles, el filtro de la escala y el antes/después.
- No hagas commit: me lo enseñas y decido yo.

## Qué quiero al acabar

- Capturas de la nave, de un lineal en alzado y del antes/después.
- Qué medidas son reales y cuáles de ejemplo.
- Qué no has podido hacer o no te convence, y qué datos de Odoo harían falta para que los tres niveles fueran
  reales (tablas y campos).
- Después, parar y esperar mi visto bueno.
