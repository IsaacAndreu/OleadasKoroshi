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
