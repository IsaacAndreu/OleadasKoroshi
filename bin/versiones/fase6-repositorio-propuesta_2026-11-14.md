# Fase 6 de la auditoría 13/11: repositorio (propuesta)

14/11/2026. **No se ha ejecutado nada de la propuesta**: no se ha sacado ningún fichero de git, no se ha creado
ninguna etiqueta y no se ha tocado ningún módulo. Lo único nuevo es `bin/desplegar.sh`, que no sustituye a nada hasta
que se apruebe.

## 1. Binarios en git

### Cuánto ocupa (medido el 14/11)

- `.git`: **1,4 GB** (1,35 GB empaquetados, 117 commits). Remoto: GitHub privado.
- Lo que más pesa, en toda la historia:

| Tipo | Historia | Dónde |
|---|---|---|
| jpg | 530 MB | 4.488 fotos de producto en `bin/versiones/2026111x_imagenes_koroshi*` (2.366 antiguas, 1.848 de la CDN, 171, 103) |
| apk | 113 MB | 8 APK de prueba de la PDA (`bin/versiones/pda_koroshi_android_test_2026-10-29*`) más los `.idsig` |
| pdf | 74 MB | manuales, informes |
| html | 55 MB | versiones de páginas y planos (regla «cada página con nombre y fecha») |
| dll / exe | 37 MB | `bin/Release`: el programa de escritorio |
| xlsx | 26 MB | volcados y planos |
| zip | 10 MB | 137 ZIP de módulos en `bin/` |

### Propuesta

1. **Una etiqueta por versión** de módulo: `koroshi_zonas/v1.3.0`, sobre el commit que sube el manifest. Anotada y
   **nunca se mueve**: esta es ahora la regla de «no sobrescribir». Si hay que cambiar algo, se saca una versión
   nueva.
2. **ZIP generado desde la etiqueta** en vez de guardarlo en git:

   ```bash
   git -c core.autocrlf=false archive --format=zip -o bin/20261114_koroshi_zonas_v1.3.0.zip koroshi_zonas/v1.3.0:odoo/modulos koroshi_zonas
   ```

   Probado el 14/11 con HEAD: salen los mismos 41 ficheros que el ZIP hecho con Python, con el mismo contenido. La
   única diferencia es el final de línea: con `core.autocrlf=false` salen **todos en LF**. Los ZIP de ahora salen de
   la copia de trabajo, donde 59 ficheros de `odoo/modulos` están en CRLF (por `core.autocrlf=true`). Odoo los acepta,
   pero LF es lo correcto en Linux. El `-c core.autocrlf=false` es obligatorio: sin él, `git archive` también los pasa
   a CRLF.
3. **Dejar de subir binarios** (`.gitignore` y `git rm --cached`, que conserva los ficheros en el disco):
   - `bin/*.zip` y `bin/builds/`: se regeneran desde la etiqueta.
   - `*.apk` e `*.idsig`: se adjuntan a una *release* de GitHub con su etiqueta (`pda/vX.Y.Z`).
   - `bin/versiones/*imagenes*`: a una carpeta de Drive o a otro repositorio. No son código.
   - HTML, PDF y XLSX de `bin/versiones` se pueden quedar: pesan poco y la regla de las versiones con fecha los usa.
4. **La historia sigue ocupando 1,35 GB.** Para reducirla hay que reescribirla (`git filter-repo`) y hacer *force
   push*, y todos los clones tienen que volver a clonar. Es destructivo e irreversible, así que no se propone hacerlo
   ahora: decide el responsable. Si no se hace, a partir de aquí el repositorio deja de crecer.
5. **`bin/Release` no se toca.** Es el programa de escritorio: el AutoUpdater y la versión 0.8.0.9 están prohibidos, y
   `PedidosMultiples.exe.Config` tiene credenciales pendientes de rotar.

## 2. `bin/desplegar.sh` (hecho, sin estrenar)

Un solo script en vez de uno por versión:

```bash
bash desplegar.sh check koroshi_zonas 1.3.0
sudo AUTO_CONFIRM=1 bash desplegar.sh install koroshi_xpo_bultos 1.2.0 koroshi_s4t_envios 1.2.0
```

- Para cada módulo busca **un único** `AAAAMMDD_<modulo>_v<version>.zip` en `/home/it_nath_group`.
- Comprueba:
  - que el ZIP está sano;
  - que solo trae `<modulo>/` con su manifest;
  - que la versión del manifest coincide con la pedida;
  - que **en el servidor no está ya esa versión ni una más nueva** (no sobrescribe ni baja versiones);
  - las dependencias:
    - un `koroshi_*` u `oriola_*` que falte es un error;
    - un módulo de fuera (p. ej. `delivery_xpo`) solo da aviso, porque puede estar en otra ruta de addons.
- Si algo falla no toca nada.
- Si todo está bien: copia de seguridad de cada módulo, copia, **un solo reinicio** y la lista de módulos que hay que
  actualizar en Odoo, por orden.
- Mira la versión de la carpeta del servidor, no la `installed_version` de la base de datos. Antes de sacar una
  versión, la regla 3 sigue pidiendo mirar la base de datos.
- Probado en local con `PRUEBA_LOCAL=1` (sin systemctl ni reinicio) y carpetas falsas, con el ZIP real de
  koroshi_zonas 1.3.0:
  - comprobación correcta;
  - instalación con copia de seguridad;
  - errores bien detectados en:
    - la misma versión ya en el servidor;
    - una versión más nueva en el servidor;
    - un ZIP que no existe;
    - dos ZIP con la misma versión;
    - un ZIP con una carpeta de más;
    - una dependencia koroshi que falta;
    - parámetros raros (`../x`).
  - Además:
    - una dependencia de la misma tanda se da por buena;
    - la versión se acepta con o sin `13.0.`.
- **No probado en el servidor** (systemctl, chown, reinicio): es lo mismo que hacen los scripts de ahora.

Si se aprueba, la regla 2 de CLAUDE.md pasa a ser: subir la versión del manifest, poner la línea en el historial,
crear la etiqueta y generar el ZIP desde la etiqueta. Se instala con `desplegar.sh` y no se escribe un script por
versión. Los scripts viejos se quedan como historia.

## 3. `koroshi_base`: lo repetido

### Lo que se repite hoy

| Qué | Dónde | Observación |
|---|---|---|
| `COMPANY_ID = 8` | 15 ficheros, 10 módulos (caja_existente, informe, kpi ×2, monitor ×2, pda_app, preparacion, s4t_traspasos, warehouse_map, xpo_bultos, zonas ×4) | |
| `'Europe/Madrid'` | 15 ficheros, 9 módulos (actividades, faltantes, kpi ×3, monitor ×2, operarios, s4t_traspasos, warehouse_map, zonas ×4 y oriola_monitor) | koroshi_monitor usa **la zona del usuario** y Madrid solo si no tiene. Los demás usan Madrid siempre |
| Límites del día en Madrid → UTC | `_rango_utc` en kpi/falta.py:59, kpi/kpi.py:327, monitor/envios.py:213 y zonas/ejecucion.py:150; cálculos sueltos en actividades, informe, hoja_carga, warehouse_map, zonas/lector y oriola_monitor | Las cuatro `_rango_utc` hacen lo mismo con firmas distintas |
| Matrícula de caja `^CJ\d{9}$` | Python: preparacion/lectura.py:27, caja_existente/stock_picking.py:30, actividades/inversa.py:27. JS: preparacion.js:57, actividades.js:26 | En JS no distingue mayúsculas (`/i`); en Python sí. `lectura.leer()` (lectura.py:659) no pasa el código a mayúsculas: una «cj…» en minúsculas no se reconocería como caja. Los lectores mandan mayúsculas: es teórico |

### Propuesta

- **Módulo nuevo `koroshi_base` 1.0.0**:
  - solo depende de `base`;
  - sin modelos, sin datos y sin tablas;
  - expone `odoo.addons.koroshi_base.comun` con:
    - `COMPANY_ID`, `TZ`, `RE_CJ`;
    - `es_matricula(codigo)`, que pasa a mayúsculas;
    - `hoy_local()`, `ahora_local()`;
    - `rango_dia_utc(dia)` y `rango_dias_utc(desde, hasta)`;
  - un JS pequeño con `RE_CJ` para las pantallas.
  - Con tests sin Odoo, como los del motor de zonas.
- **Paso a paso, un módulo por versión** (y por sesión):
  - cada módulo añade `koroshi_base` a `depends`, cambia sus constantes por las de `comun` y sube versión;
  - primero se instala `koroshi_base` (`desplegar.sh` respeta el orden);
  - orden propuesto, de menos a más riesgo para la PDA: zonas, kpi, informe, xpo_bultos, s4t_traspasos,
    warehouse_map, monitor, faltantes, caja_existente, actividades, operarios y, al final, preparacion y pda_app;
  - oriola_monitor no es de KOROSHI: no se toca;
  - preparacion va fuera de horas y con prueba en una PDA real.
- No cambia el comportamiento, salvo dos cosas que hay que decidir:
  1. ¿El monitor sigue con la zona del usuario o pasa a Madrid siempre?
  2. ¿Se acepta «cj» en minúsculas en Python, como en JS?
- **Trabajo**:
  - `koroshi_base`: poco.
  - Cada módulo: poco (sustituir y probar).
  - Toca 13 módulos KOROSHI: 13 versiones y 13 instalaciones. Se puede repartir en varias semanas sin prisa, porque hoy no
    falla nada.

## 4. Qué hace falta decidir

1. Etiquetas y ZIP desde la etiqueta: ¿sí? (cambia la regla 2 de CLAUDE.md).
2. Sacar los binarios de git a partir de ahora: ¿sí? ¿Las fotos a Drive o a otro repositorio?
3. Reescribir la historia para bajar de 1,4 GB: ¿sí o no? (destructivo; lo haría el responsable).
4. `desplegar.sh` como único script de instalación: ¿sí?
5. `koroshi_base`: ¿sí? Y las dos preguntas del punto 3 (zona del monitor y «cj» en minúsculas).
