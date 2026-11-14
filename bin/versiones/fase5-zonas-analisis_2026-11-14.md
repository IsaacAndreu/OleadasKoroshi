# Fase 5 de la auditoría 13/11: motor de koroshi_zonas (solo análisis)

14/11/2026. Leído el código de `odoo/modulos/koroshi_zonas` (13.0.1.2.0, el mismo que hay en el servidor) y, en
modo lectura, las acciones y crons de nath.tuctuc.com. **No se ha cambiado nada**, ni en el repo ni en el servidor.

## 1. ¿Hereda koroshi_zonas los tres fallos de la v10?

| Fallo de la v10 | ¿Lo hereda? | Dónde |
|---|---|---|
| Ordena solo por número de tienda, no por urgencia | **Sí** | `motor/v12f.py:159-160` |
| Las OUT de días anteriores dejan de ser candidatas | **Sí** | `models/lector.py:33` y `:51` |
| No revisa la capacidad después de juntar trozos | **No** (con matices) | `motor/evaluar.py:240-273`, `motor/v12f.py:206-215` |

### 1.1 Orden por número de tienda — heredado

- `v12f.py:159`: `prio.append((knum, '', 0, p_['name'], p_['id']))` y `prio.sort()`: el orden es K1, K2, K3...
  Es la misma línea que la acción 1883 (`tests/original/accion_1883_v12f.py:374`) y que la v10 (línea 333).
- `TIENDAS_48H` (`motor/modelo.py:36`, configurable) solo sirve para poner «(48h)» en el informe (`v12f.py:382`): no
  cambia el orden.
- La búsqueda binaria (`v12f.py:208-215`) se queda con `orden[:lo]`: si no cabe todo, siempre se quedan fuera las
  tiendas de número alto, sean urgentes o no.
- **Hoy no tiene efecto**: la configuración del servidor tiene «Todo en una ronda» marcado (`una_ronda = True`), y
  entonces `lo = hi` (`v12f.py:206-207`): entran todas las OUT y el orden no recorta nada. Pasa a importar el día que
  se desmarque «Todo en una ronda».

### 1.2 OUT de días anteriores — heredado

- `lector.py:33` calcula `desde` = medianoche local de hoy en UTC y `lector.py:51` filtra
  `('create_date', '>=', desde)`. Igual que la 1883 (línea 288) y la v10 (línea 248).
- Una OUT que no se partió el día que entró **no vuelve a ser candidata nunca**.
- Dato real (14/11, solo lectura): hay **77 OUT de KOROSHI abiertas creadas antes de hoy y sin agrupación**: 71 del
  13/11, 3 del 12/11, 1 del 10/11 y 2 del 26/06. Ninguna entrará en el reparto de mañana.

### 1.3 Capacidad después de juntar trozos — no heredado

- En la v10, `juntar_chicos` (línea 421) movía unidades entre zonas **después** de calcular el tiempo con
  `evaluar()`, y la capacidad no se volvía a mirar.
- En koroshi_zonas no hay paso de «juntar» posterior. El cierre de cajas y el resto pegado al trozo anterior se hacen
  dentro de `montar_una` (`cerrar_cadena`, `evaluar.py:240`), y el tiempo de cada zona (`seg_z`, `evaluar.py:253`) se
  calcula con los grupos ya cerrados. `fin` sale de esos grupos, y la búsqueda binaria comprueba
  `calc.montar(mid)['fin'] <= capacidad` (`v12f.py:210`).
- Matices (no son el fallo de la v10, pero conviene saberlos):
  1. Con «Todo en una ronda» (lo que hay ahora) **no se comprueba la capacidad**: entra todo aunque `fin` pase de las
     12:00. Es lo que se pidió, pero el informe debería avisar cuando `fin > capacidad`.
  2. `cierre.py:52-53`: cuando el último resto pequeño se pega al trozo anterior, su tiempo no se suma a `carga` de esa
     zona. Solo afecta a la heurística de dónde cortar las siguientes cadenas, no a `fin`.
  3. La búsqueda binaria supone que `fin` crece con el número de OUT. Con el reparto por zonas no está garantizado:
     podría quedarse con menos OUT de las que caben. Sin efecto mientras «Todo en una ronda» esté marcado.

## 2. Acciones y crons que se podrían borrar al pasar koroshi_zonas de sombra a real

**No se ha borrado ni desactivado nada.** Leído el 14/11. Ninguna de estas tiene `ir.model.data`, así que son
manuales (creadas pegando código), no del módulo.

### 2.1 Se pueden borrar el día que koroshi_zonas pase a real

| Tipo | Id | Nombre | Estado | Sustituta en koroshi_zonas |
|---|---|---|---|---|
| Cron | **202** | KOROSHI Partir OUT zonas v12 REAL (09/11 05:00) | **ACTIVO**, cada día 05:00; última 14/11 05:00 | cron 208 «partir OUT (sombra o real)» |
| Acción | **1883** | KOROSHI Partir OUT zonas v12 REAL (09/11 05:00) | la usa el cron 202 | acción 1924 |
| Acción | 1880 | KOROSHI Partir OUT zonas v12 - 3 REAL | manual | 1924 |
| Acción | 1881 | KOROSHI Partir OUT zonas v12 - 1 DIAGNOSTICO | manual | 1921 |
| Acción | 1882 | KOROSHI Partir OUT zonas v12 - 2 SIMULAR | manual | 1922 |
| Acción | 1843 | KOROSHI Etiquetas zona | en el menú Acción de albaranes | 1928 / 1929 (también en ese menú: hoy salen las dos) |

Orden: primero desactivar el cron 202 (sin él, el cron 208 deja de negarse a ir en real), dejar unos días el 202
desactivado por si hay que volver atrás, y después borrar 202, 1883, 1880-1882. El cron 209 «comparar con el cron
202» deja de tener sentido: se desactiva (es del módulo; quitarlo del XML en una versión nueva).

### 2.2 Ya inactivas: se pueden borrar ya (no las usa nada)

| Tipo | Id | Nombre | Estado |
|---|---|---|---|
| Cron | 200 | KOROSHI Partir OUT en 8 zonas (27/10 03:00) | inactivo; última 27/10 |
| Acción | 1867 | KOROSHI Partir OUT en 8 zonas (27/10 03:00) | la del cron 200 |
| Cron | 201 | KOROSHI Correo zonas del dia (27/10 03:20) | inactivo; última 27/10 |
| Acción | 1868 | KOROSHI Correo zonas del dia (27/10 03:20) | la del cron 201 (la sustituye el cron 210 del módulo, inactivo) |
| Acción | 1866 | KOROSHI Partir OUT zonas v9 (8 zonas, ZX repartida) | manual |
| Acción | 1852 | KOROSHI Partir OUT zonas v7 (6 a 11) | manual |

No hay acción de la v8 ni de la v10 en el servidor: solo están como archivos en `odoo/`.

### 2.3 Del método INT por zona (abandonado): borrar solo si se confirma que no se vuelve a él

| Tipo | Id | Nombre | Estado |
|---|---|---|---|
| Cron | 198 | KOROSHI repartir INT zonas | inactivo; última 22/10 |
| Acción | 1840 | KOROSHI repartir INT zonas | la del cron 198 |
| Acción | 1839 | KOROSHI Repartir INT por zona | manual |
| Acción | 1841 | Anti-oleadas (deshace el reparto INT de una oleada) | en el menú Acción de agrupaciones |

No van con koroshi_zonas: son otro método. Se listan porque salen en la misma búsqueda.

### 2.4 No tocar

- **1633 «Crear transfer para oleada»**: es del módulo `sorter_batch` (no es de KOROSHI).
- Acciones y crons del módulo koroshi_zonas (1916-1930; crons 206-210): se quedan.

## 3. Qué se propone arreglar (esperando visto bueno)

1. **OUT de días anteriores** (lo más urgente; hay 77 ahora): que el lector coja también las OUT abiertas de días
   anteriores sin agrupación Z-, con un límite de días (p. ej. 7) para no arrastrar las de junio.
2. **Orden por urgencia**: ordenar primero las tiendas de `TIENDAS_48H` y las OUT más antiguas, después por número de
   tienda. Hoy no cambia el resultado (una ronda), pero sí el día que no quepa todo.
3. **Aviso de capacidad** con «Todo en una ronda»: decir en el informe y en el correo «acaba a las HH:MM, después de la
   hora de fin».
4. Opcional: sumar a `carga` el resto pegado (`cierre.py:52`).

Todo es de koroshi_zonas (un solo módulo): versión 1.3.0. Tiene que pasar por sombra (cron 208 + comparar 209)
antes de ir a real, y comparar el resultado con el del cron 202 unos días.
