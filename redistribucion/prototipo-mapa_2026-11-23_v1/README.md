# Prototipo del mapa NAU-2 — v1 (23/11/2026)

Visor (no editor) para decidir cómo se verá el programa de redistribución de zonas. No se conecta a Odoo ni al
servidor: solo lee el Excel MASTER del 06/11 que está en el repo.

## Cómo se arranca

```powershell
python extraer_datos.py
```

```powershell
python -m http.server 8776 --bind 127.0.0.1 --directory C:/dev/OleadasKoroshi/redistribucion/prototipo-mapa_2026-11-23_v1
```

Abrir <http://127.0.0.1:8776>. En Claude Code está en `.claude/launch.json` como `mapa-nau2-prototipo-v1`.
ECharts 5.5.1 se carga de jsdelivr (versión fija); sin internet hay que bajar `echarts.min.js` a esta carpeta y
cambiar la ruta en `index.html`.

## Uso

- Rueda = zoom, arrastrar = mover, clic en una celda = alzado del lineal, clic en el alzado = hueco, Esc = subir.
- Medida: desplegable. Escala abajo: arrastrar los extremos apaga lo que queda fuera; en las de categorías, clic
  en una categoría la apaga.
- «Límite de zona»: línea entre posiciones vecinas de zona 0 y Z. «Flechas»: movimientos de ejemplo.
- «Antes / después»: hoy y plan Z5+01 con el mismo zoom; se ponen uno encima del otro o lado a lado, lo que dé
  más píxeles por metro. «Diferencia»: pinta qué cambia de cada posición.
- Buscador: `L45`, `L45 P05`, `MU-03`, temporada `I16` (real, por lineal) o `MODELO-EJEMPLO-A` (ejemplo).

## De dónde sale cada dato

| Dato | Detalle | Origen | ¿Real? |
|---|---|---|---|
| Zona hoy (0 / Z / mezclada / vacía) | por posición | hoja «Layout hoy», texto de la celda (gris = vacía, sin relleno = no existe) | Sí (Odoo 06/11) |
| Zona en el plan Z5+01 | por posición | hoja «Layout compactado Z5+01», **solo color de celda** traducido con la leyenda de la hoja. Dos colores no tienen leyenda (naranja claro = Z vacía, amarillo claro = muelle vacío): deducidos | Sí, salvo esas dos etiquetas |
| Ocupación, uds, uds 0/Z/otras, % 0/Z, SKU, modelos-color, litros, temporadas, uds a mover P1/P2 | **solo por lineal** | hoja «Por lineal» | Sí (litros: estimados en el propio Excel) |
| Uds por posición ocupada | por lineal | calculado: uds / posiciones ocupadas | Calculado |
| Geometría en metros | por posición | copia de `_x`, `_y`, `BASE`, `CRUCES` de `koroshi_kpi/models/kpi.py` | Aproximada (ver supuestos) |
| Niveles C1–C4 | — | el Excel no trae nada por nivel: se pintan con la zona de su posición | No hay dato |
| Contenedores de un hueco, modelos, flechas | — | `extraer_datos.py`, función `ejemplo()` | **DATOS DE EJEMPLO** |

Supuestos de geometría (kpi.py solo da centros): lineal par a la izquierda de su pasillo e impar a la derecha;
40 cm de fondo (hoja «Medidas estanterias»); P00 de 0,6 m en el pasillo central; P37–P42 existen en el Excel pero
kpi.py las aplasta en P36, aquí siguen el mismo paso; el muelle (MU-00…14) no tiene sitio en kpi.py y se dibuja
aparte a la derecha.

Ojo: L121–L136 tienen 156 ubicaciones para 18 posiciones (8,7 por posición): ahí no son 4 niveles.

## Qué haría falta de Odoo para que los tres niveles sean reales

- Nave y alzado: `stock.location` (nombre `Lnn Pnn Cn`, `location_id`, `active`, `barcode`) para saber qué niveles
  existen de verdad; `stock.quant` (`location_id`, `product_id`, `quantity`, `package_id`) agrupado por ubicación.
- Hueco: `stock.quant.package` (nombre KO_/TT_) y `product.product` / `product.template` (referencia, modelo,
  color, talla, `season_id`, `volume`).
- Rotación (ABC por hueco): `stock.move.line` hechas de salida (`location_id`, `product_id`, `qty_done`, `date`).
