# Prototipo del mapa NAU-2 — v2 (23/11/2026)

Segunda versión del visor, con el «listón» del prompt v2
(`bin/versiones/prompt-opus-prototipo-mapa-redistribucion_2026-11-23_v2-interactivo.md`) y las ideas de
programas de slotting (Mecalux, Optioryx, Georgia Tech, MWPVL, FlexSim). La v1 sigue en `../prototipo-mapa_2026-11-23_v1/`.

No se conecta a Odoo ni al servidor: solo lee el Excel MASTER del 06/11 que está en el repo.

## Cómo se arranca

```powershell
python extraer_datos.py
```

```powershell
python -m http.server 8777 --bind 127.0.0.1 --directory C:/dev/OleadasKoroshi/redistribucion/prototipo-mapa_2026-11-23_v2
```

Abrir <http://127.0.0.1:8777>. En Claude Code: `mapa-nau2-prototipo-v2` en `.claude/launch.json`.
Librerías con versión fija y sin compilar: d3 7.9.0 (cdnjs) y la fuente Inter (Google Fonts). Sin internet hay
que bajar `d3.min.js` a esta carpeta.

**Cambio de librería frente a la v1:** Canvas 2D + d3 en lugar de ECharts. Con ECharts no salían bien la cortina
(no se puede recortar media serie), la selección por arrastre (`brush` no funciona con series `custom`), el
resaltado de una celda con su lineal y las flechas animadas que se pueden tocar. Las 5.400 celdas se dibujan en
canvas sin problema.

## Qué hace

| | |
|---|---|
| Modos | **Hoy** (una medida), **Plan Z5+01**, **Cortina** (hoy a la izquierda y plan a la derecha; se arrastra la línea), **Lado a lado** (zoom sincronizado; se ponen uno encima del otro o lado a lado según lo que dé más píxeles por metro) y **Diferencia** |
| Niveles | Nave → lineal en alzado (con un plano en miniatura de dónde está) → hueco. Rastro arriba, <kbd>Esc</kbd> sube un nivel |
| Ratón | Pasar resalta la celda, su lineal, su número arriba y su fila en la lista (y al revés). Clic fija; se pueden fijar dos (A y B) y se comparan. Doble clic acerca. <kbd>Mayús</kbd>+arrastrar selecciona y suma |
| Escala | Medidas de categorías: un clic en una categoría la apaga; doble clic deja solo esa. Medidas numéricas: histograma; arrastrando sobre él se elige un tramo y el resto se apaga |
| Encima | Límite de zona (0/Z), zona de oro (< 40 m a pie de expedición) y movimientos animados (ejemplo; al tocar uno se marcan su origen y su destino) |
| Panel | Cifras del plan frente a hoy, lista de lineales enlazada con el plano, fijadas, selección y movimientos ordenados por metros ahorrados |
| Otros | Tema claro y oscuro. El estado va en la dirección (`#modo=…&lineal=…`): se puede recargar o pasar el enlace. PNG de lo que se ve |

## De dónde sale cada dato

| Dato | Detalle | Origen | ¿Real? |
|---|---|---|---|
| Zona hoy (0 / Z / mezclada / vacía) | por posición | hoja «Layout hoy» | Sí (Odoo 06/11) |
| Zona del plan Z5+01 | por posición | hoja «Layout compactado Z5+01» (solo color de celda; dos colores sin leyenda, deducidos) | Sí |
| Ocupación, uds, % 0/Z, SKU, modelos-color, litros, temporadas, uds a mover | **solo por lineal** | hoja «Por lineal» | Sí |
| Metros a expedición | por posición | calculado en `extraer_datos.py` con `_x`, `_y`, `BASE` y `CRUCES` de kpi.py (misma regla que `metros_ruta`) | Calculado |
| Cifras «plan frente a hoy» | nave | cuentas de las dos hojas de layout + metros calculados | Real / calculado |
| Niveles C1–C4 | — | no hay dato por nivel; se pintan con la zona de su posición | No hay dato |
| Contenedores, modelo buscado, movimientos | — | `ejemplo()` en `extraer_datos.py` | **DATOS DE EJEMPLO** |

Supuestos de geometría: los de la v1 (lado par/impar, 40 cm de fondo, P00 de 0,6 m, P37–P42 con el paso de
P25–P36 y el muelle dibujado aparte). Además, zona de oro = 40 m y altura cómoda = C2–C3 (con C1 abajo).

## Qué haría falta de Odoo para que todo sea real

- `stock.location`: nombre `Lnn Pnn Cn`, activa: qué niveles existen. L121–L136 tienen 8,7 ubicaciones por
  posición, así que ahí no son 4 niveles.
- `stock.quant`: ubicación, producto, paquete y cantidad, para la ocupación por hueco y por nivel.
- `stock.quant.package`: los contenedores KO_ y TT_.
- `product.product` / `product.template`: modelo, color, talla, `season_id` y `volume`, para el buscador de modelo
  y la dispersión del modelo.
- `stock.move.line` hechas de salida: rotación por hueco, para el calor de picking que tienen Mecalux y MWPVL.

## Capturas

En `capturas/`, por rondas de autocrítica: `ronda0_*` (primera versión), `ronda1_*` y `ronda2_*`.
