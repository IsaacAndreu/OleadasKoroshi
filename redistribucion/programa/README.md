# Programa de redistribución de zonas NAU-2 — fase 1 (23/11/2026)

Programa aparte, en el PC: lee Odoo **en solo lectura**, guarda una copia en SQLite y enseña en el mapa
(base: `../prototipo-mapa_2026-11-23_v2/`) cómo está hoy la nave. No toca `odoo/modulos/` ni el servidor.

## Estructura

```
programa/
  programa.py              órdenes: guardar-clave, probar-conexion (paso B: descargar; paso C: generar-mapa)
  config.ejemplo.toml      modelo de configuración (en git)
  config.local.toml        dirección, bd y usuario (FUERA de git)
  redistrib/
    odoo_lectura.py        ÚNICO fichero que habla con Odoo (XML-RPC), con la lista blanca
    configuracion.py       lee config.local.toml y la contraseña del almacén de Windows (keyring)
    consultas.py           qué se lee: dominios y campos (funciones puras)
    descarga.py            Odoo -> SQLite, por páginas ordenadas por id; salidas incrementales
    ubicaciones.py         qué es cada ubicación: hueco «Lnn Pnn Cn», contenedor, muelle, N1-, otra (pura)
    productos.py           modelo/color/talla, familia, temporada, zona y litros (pura; TIPOS se lee de kpi.py)
    resumen.py             filas, uds por zona, lo raro y comparación con el Excel del 06/11
    (paso C) medidas.py, mapa_json.py, listas.py   dispersión, calor, listas y JSON del mapa (puras)
  pruebas/                 unittest, sin Odoo ni red; odoo_falso.py = Odoo pequeño INVENTADO
  copias/                  AAAAMMDD_HHMM_odoo.sqlite + .resumen.txt, una por descarga (FUERA de git);
                           copias/inventadas/ = las de «copia-inventada»
```

## Solo lectura (lo que lo garantiza)

El usuario Departament IT puede escribir, así que la solo lectura la pone `redistrib/odoo_lectura.py`:

- Solo pasan `search`, `search_read`, `read`, `search_count`, `read_group` y `fields_get` (más `version` y
  `authenticate`). Cualquier otro método da `LecturaProhibida` antes de abrir conexión.
- Ningún otro fichero importa `xmlrpc` (lo comprueba una prueba).
- Siempre compañía 8 en el contexto, una petición cada vez con pausa (mínimo 0,3 s), máximo 5.000 filas por
  petición y lista de campos obligatoria.
- La contraseña está en el almacén de credenciales de Windows; no sale en pantalla, ni en errores, ni en repr.

## Programa de Windows (26/11/2026)

Se abre con doble clic en `../Redistribucion NAU-2.bat`: abre `dist/Redistribucion/Redistribucion.exe` si está
compilado y, si no, `pythonw ventana.py` (necesita PySide6 6.12.0).

**Compilar el .exe** (26/11/2026, PyInstaller 6, carpeta de ~170 MB fuera de git):
`python -m PyInstaller --noconfirm Redistribucion.spec`. El .exe usa las copias, las matrices y la configuración
del repo (`configuracion.CARPETA` = dos carpetas por encima del .exe), así que hay que dejarlo en
`dist/Redistribucion/`; si se copia a otro sitio, no encuentra los datos. Solo lee: no se conecta a Odoo y no escribe ni en
Odoo ni en las matrices.

- **Fuentes:** la última versión de cada matriz de KOROSHI en `bin/versiones` (`AAMMDD_KOROSHI_<n>_<nombre>_v<v>.xlsx`;
  `redistrib/fuentes.py`) y la última copia de Odoo. Si sale una versión nueva de una matriz, la coge sola.
  Hoy solo se usa la matriz 1 (MASTER: litros por modelo); la 2 y la 3 salen en la lista, pero aún no las usa
  ningún cálculo.
- **Inicio:** el plan de trabajo en tres pasos (1 retirar cajas vacías, 2 juntar cajas, 3 lineales que podrían
  quedar vacíos, como estimación por volumen) y por qué lineal empezar (donde más huecos se liberan).
- **Por lineal:** alzado del lineal (posiciones × columnas C1–C4, cada una de 4 cajas de alto, en colores) y sus tareas: retirar vacías, sacar cajas y
  cajas que entran. Botón «Imprimir hoja de trabajo (Excel)»: tres hojas con casilla «Hecho», en apaisado.
- **Plano de la nave:** botones Hoy · Paso 1 · Paso 2 · Resultado. Clic en una posición: qué hay que hacer en cada
  nivel, con flechas (verdes: salen; azules: llegan). Doble clic: abrir el lineal.
- **Listas completas** (cajas vacías, cajas a mover, lineales) con filtro y «Exportar a Excel» (fichero nuevo;
  no sobrescribe).

### Zona Z (outlet), desde el 27/11/2026

Arriba a la izquierda se elige la zona: **Zona 0 · palés (L44–L136)** o **Zona Z · outlet (L01–L43)**. La Z se
calcula en `redistrib/zona_z.py` (solo lee la copia):

- **Criterio (Isaac, 27/11):** 1) temporada, lo que más pesa; 2) dentro de la temporada, la familia que más vende,
  más cerca; 3) el modelo-color con su talla completa, junto. Temporadas en vivo / lento / muerto por rotación
  (uds vendidas en OUT el último año ÷ stock): vivo ≥ 0,5 (y la temporada más nueva de verano y de invierno),
  muerto < 0,2.
- **Estanterías:** `redistribucion/estanterias-zona-z_hojas-20261102_transcripcion-20261127.csv`, transcrito de
  las 8 hojas del 02/11/2026 (con 207 dudas apuntadas). Si en la hoja hay un número de posición escrito a mano
  encima del impreso, vale el escrito (Odoo llega a P42). Capacidad de una posición = la mayor de: huecos de la
  leyenda, o el percentil 90 de KO por posición que hay hoy en ese tipo (D10, C y E tienen ~2 KO por hueco). Se
  llena al 90 %.
- **Pasos:** 1 retirar cajas a 0 · 2 hacer sitio en los lineales cercanos (sacar lo lento y muerto) · 3 traer lo
  que vende · 4 el resto (puede esperar). La caja (KO) se mueve entera; el destino es el lineal.
- **Orden fino / medio / grueso:** una KO no se mueve si ya está en un lineal de su bloque (temporada + familia,
  temporada o solo vivo/lento/muerto). Con la copia del 26/11: ~35.000, ~34.400 o ~26.700 movimientos.

## Uso

```powershell
python -m pip install keyring
```

```powershell
python programa.py guardar-clave
```

```powershell
python programa.py probar-conexion
```

Pruebas (sin Odoo):

```powershell
python -m unittest discover -s pruebas -t . -v
```

## Comprobado en el código antes del modelo de datos

- **Contenedores KO_/TT_ = `stock.location`** hijas del hueco (usage internal), no `stock.quant.package`:
  `odoo/modulos/koroshi_contenedores/controllers/main.py` (PREFIJOS l. 21, hijos del hueco l. 93, mover =
  `c.write({'location_id': …})` l. 734; se niega si un quant lleva paquete, l. 439 y 523). El README de la v2
  se equivoca en esto; se corrige en la v3 (la v2 no se toca).
- **Temporada = `product.template.season_id.name`** (I27, V27…): `bin/KOROSHI_crear_INT_zonas_PLANIFICADA.py`
  l. 213 y `TEMPORADAS_ACTUALES = ['I27', 'V27']` l. 56. El campo no es de un módulo KOROSHI: «probar conexión»
  enseña a qué modelo apunta.
- **Modelo / color / talla** del código «MODELO-COLOR-TALLA» (`odoo/KOROSHI_exportar_tallas_MASTER_SHELL_2026-11-20.py`
  l. 97–106); **familia** = letras 5–6 del modelo (`RE_TIPO`, `koroshi_kpi/models/kpi.py` l. 21); **volumen** =
  `product.product.volume` (m³). Si falta, litros de `TIPOS` (kpi.py l. 26) marcados como estimados.
- **Niveles**: sin datos no se puede confirmar. En el Excel del 06/11, L121–L136 tienen 156 ubicaciones para
  18 posiciones (8,7 por posición): puede que sean contenedores KO_ contados como ubicaciones, no niveles. Se
  verá en la descarga; los nombres que no encajen se guardan y se listan.

## Descarga (paso B)

```powershell
python programa.py descargar --sin-salidas
```

```powershell
python programa.py descargar --desde 2025-11-24
```

- Cada descarga crea `copias/AAAAMMDD_HHMM_odoo.sqlite` (mientras baja, `….parcial`) y su `.resumen.txt`. Nunca
  se pisa una copia: si el nombre existe, para.
- Tablas: `ubicaciones` (con padre, código de barras, activa, tipo, lineal/posición/nivel y `hueco_id` del
  contenedor), `stock` (cantidad y reservado), `productos`, `tipos_operacion`, `salidas` y `meta`.
- Salidas = líneas hechas de los tipos de operación de salida e internos de la compañía 8, uno a uno (sin
  `picking_code`, que no está guardado y hacía lenta la consulta). La primera vez, desde `--desde`. Después,
  se copian de la copia anterior y solo se piden las de fecha desde la última descarga menos 3 días, por páginas
  ordenadas por id; al acabar se compara con `search_count` por tipo y, si no cuadra, avisa (`--completa`).
- `--sin-salidas`: no pide salidas a Odoo (las copia de la copia anterior, si hay).
- `python programa.py copia-inventada`: copia con datos inventados, para probar sin Odoo.
