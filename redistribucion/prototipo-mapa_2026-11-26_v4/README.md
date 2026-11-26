# Mapa NAU-2 — v3 con datos reales de Odoo (24/11/2026)

Es la misma pantalla que la v2 (`../prototipo-mapa_2026-11-23_v2/`, Canvas 2D + d3) y se usa igual. Lo que cambia es
de dónde salen los datos: ahora vienen de una **copia SQLite de Odoo** que se baja en solo lectura con el programa
de `../programa/`. La v2 no se ha tocado.

## Cómo se arranca

Desde `../programa/` se generan los datos a partir de la última copia (o de la copia que se indique). Este paso
no se conecta a Odoo:

```powershell
python programa.py generar-mapa
```

Después se arranca el servidor:

```powershell
python -m http.server 8778 --bind 127.0.0.1 --directory C:/dev/OleadasKoroshi/redistribucion/prototipo-mapa_2026-11-24_v3
```

Se abre en <http://127.0.0.1:8778>. En Claude Code es `mapa-nau2-v3`, en `.claude/launch.json`.

Los datos van en cuatro ficheros JSON. Se regeneran, no van en git y suman unos 10 MB:

| Fichero | Qué lleva |
|---|---|
| `datos.json` | Posiciones y niveles |
| `huecos.json` | Lo que hay en cada hueco; se carga al abrir uno |
| `modelos.json` | Dónde está cada modelo-color |
| `listas.json` | Las listas 2 a 5 |

Librerías con versión fija:
- d3 7.9.0;
- SheetJS 0.18.5, solo para «Exportar a Excel»;
- la fuente Inter.

## Qué es real y qué no

| Dato | Origen | ¿Real? |
|---|---|---|
| Zona de cada hueco y de cada posición | Odoo: `stock.quant` + temporada (`product.template.season_id`). Zona 0 = I27 + V27; Z = el resto, PERMANENTE incluida | Sí |
| Niveles | `stock.location` tal como existen en Odoo (C1–C4; ninguna posición tiene más de 4) | Sí |
| Unidades, contenedores, modelos-color y SKU por hueco | `stock.quant` por ubicación; los contenedores son `stock.location` hijas del hueco (KO_, TT_, GC_, MI_…) | Sí |
| Contenido de cada hueco | Contenedores con su modelo-color, tallas y unidades | Sí |
| **Dispersión del modelo** | Para cada modelo-color, en cuántos lineales y huecos está. Por posición: media ponderada por unidades | Sí |
| **Calor de picking** | Visitas de las últimas 4 semanas: pares distintos albarán–hueco de las órdenes de entrega y de los traspasos internos que salen de la nave. No son unidades | Sí |
| Litros | Volumen de la ficha. Si falta, media de la familia (tabla `TIPOS` de kpi.py). El 20 % de los litros son estimados y 35.832 uds no tienen litros | En parte |
| Metros a expedición | Geometría de kpi.py (misma regla que `metros_ruta`) | Calculado |
| **Plan Z5+01** | Hoja del Excel del 06/11 | **ESTIMACIÓN ANTIGUA, SIN PROBAR** (marcada en pantalla) |
| Movimientos (flechas) | Inventados | **DATOS DE EJEMPLO** (son de la fase 3) |

Reglas para pintar:
- **Zona de una posición o de un hueco:** la de la mayoría de sus unidades. Se pinta «mezclada» si la otra zona tiene al menos el 10 %.
- **Lista 3:** cuenta cualquier hueco con unidades de las dos zonas.
- **Escala de color:** llega hasta el percentil 98. Lo que pasa de ahí se pinta con el color del tope.

## Qué hay nuevo respecto a la v2

- **Medidas por posición (todas reales):** dispersión del modelo (la medida por defecto), calor de picking, metros, unidades, % de niveles con stock, contenedores, litros, modelos-color y % de zona 0 / Z.
- **Buscador de modelos:**
  - un modelo-color (`2622JA77-000030`) o un modelo con todos sus colores (`2622JA77`) ilumina todos sus huecos;
  - en el panel salen los lineales, los huecos y las unidades.
- **Alzado:**
  - los niveles son los que existen en Odoo;
  - en cada hueco se ven las unidades y los contenedores.
- **Hueco:** sale la tabla de contenedores con modelo-color, tallas y unidades, y los contenedores a cero que tiene.
- **Listas** (botón «Listas»), con filtro y exportación a Excel. Al hacer clic en una fila se va al plano o al hueco:
  1. modelos repartidos, de más a menos lineales;
  2. contenedores a cero sin archivar;
  3. huecos con zona 0 y Z;
  4. stock sin salidas en N días (N se elige en pantalla);
  5. pendiente de ubicar: contenedores colgados de la nave, muelle, N1-, perchas…
- **Arreglo del plano en blanco al abrir.**
  - En la v2, si el plano se medía cuando el lienzo aún no tenía tamaño, el encuadre guardado salía de una escala absurda y la cámara se iba fuera de la nave.
  - Ahora solo se restaura un encuadre medido con tamaño real y con el centro dentro de la nave; si no, se enseña la nave entera.
  - Lo mismo vale para el encuadre que viene en la dirección.
  - El fallo original no lo he podido reproducir: el arreglo es para la causa más probable.

## Fuera del mapa

- **Odoo tiene 1.850 posiciones sin stock que no están en el Excel**, de L121 a L183 (casi todas de L137 en adelante). No se dibujan.
- **NAVE2 de TARKO y los almacenes MODAL y CONS** no son esta nave y no salen.

## Capturas

Están en `capturas/`, del 24/11, con datos de Odoo del 23/11 a las 17:07.
