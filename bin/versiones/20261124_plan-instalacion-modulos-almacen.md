# Plan de instalación de los módulos del almacén (24/11/2026)

Versiones del servidor leídas en producción el 24/11 ~16:00 (solo lectura, `ir.module.module`; disco = BD en todos).
Todo lo de este plan está commiteado, etiquetado y con su ZIP en `bin/` (comprobado el 24/11).
**Lo instala Isaac** (o quien él diga), fuera de horas (después de las 17:00), con `bin/desplegar.sh`.

## Lo que hay pendiente

| Módulo | Servidor | Para instalar | ZIP |
|---|---|---|---|
| koroshi_base | 1.1.0 | **1.2.1** | 20261123_koroshi_base_v1.2.1.zip |
| koroshi_faltantes | 1.9.0 | **1.10.0** | 20261123_koroshi_faltantes_v1.10.0.zip |
| koroshi_contenedores | 1.13.0 | **1.15.0** | 20261123_koroshi_contenedores_v1.15.0.zip |
| koroshi_preparacion | 3.33.0 | **3.35.0** | 20261123_koroshi_preparacion_v3.35.0.zip |
| koroshi_devoluciones | 1.2.0 | **1.3.0** | 20261123_koroshi_devoluciones_v1.3.0.zip |
| koroshi_recuentos | 1.1.0 | **1.2.0** | 20261123_koroshi_recuentos_v1.2.0.zip |
| koroshi_menu | 2.6.2 | **2.7.0** | 20261123_koroshi_menu_v2.7.0.zip |
| koroshi_monitor | 1.43.0 | **1.44.0** | 20261123_koroshi_monitor_v1.44.0.zip |
| koroshi_informe | 1.3.0 | **1.4.0** | 20261123_koroshi_informe_v1.4.0.zip |
| koroshi_zonas | 1.6.0 | **1.7.0** | 20261123_koroshi_zonas_v1.7.0.zip |
| koroshi_agrupaciones_web | 1.0.0 | **1.1.0** | 20261123_koroshi_agrupaciones_web_v1.1.0.zip |
| koroshi_s4t_envios | 1.3.0 | **1.4.0** | 20261123_koroshi_s4t_envios_v1.4.0.zip |
| koroshi_s4t_traspasos | 1.3.0 | **1.4.0** | 20261123_koroshi_s4t_traspasos_v1.4.0.zip |
| koroshi_s4t_pedidos | 1.0.1 | **1.2.0** | 20261123_koroshi_s4t_pedidos_v1.2.0.zip |
| koroshi_retener_tiendas | — (nuevo) | **1.3.0** | 20261124_koroshi_retener_tiendas_v1.3.0.zip |
| koroshi_prenda_suelo | — (nuevo) | **1.1.0** | 20261123_koroshi_prenda_suelo_v1.1.0.zip |

Ya están al día (el TABLERO decía «sin instalar»): actividades 1.8.3, informe 1.3.0, recuentos 1.1.0, ubicaciones 1.0.0.

## Reglas que mandan el orden

- `koroshi_base` 1.2.1 va primero: la piden contenedores 1.15, faltantes 1.10, preparación 3.35, devoluciones 1.3,
  recuentos 1.2 y prenda_suelo 1.1.
- El `-u` de un módulo actualiza también todos los que dependen de él. El `-u koroshi_base` arrastra casi todo
  KOROSHI. Por eso, en cada tanda, se copian solo los módulos de esa tanda, para que lo que se arrastre sea la
  versión que ya está.
- Una sola actualización a la vez: dos `-u` a la vez tumban el registro y la PDA (17/11).
- Un módulo nuevo se instala después de lo que necesita, nunca copiado a la vez que algo que dependa de él (17/11).
- Cada reinicio y cada `-u` sacan a las PDA unos minutos: después de las 17:00 y sin nadie validando.
- Zonas reparte a las 04:50, el vigilante nuevo va a las 05:15 y las agrupaciones web a las 06:00: las tandas tienen
  que estar acabadas y comprobadas antes.

## Tanda A, hoy después de las 17:00: base y pantallas de la PDA

1. Subir los 7 ZIP a `/home/it_nath_group`.
2. Comprobar sin tocar nada:
   `bash desplegar.sh check koroshi_base 1.2.1 koroshi_faltantes 1.10.0 koroshi_contenedores 1.15.0 koroshi_preparacion 3.35.0 koroshi_devoluciones 1.3.0 koroshi_recuentos 1.2.0 koroshi_menu 2.7.0`
3. Si todo sale OK:
   `sudo AUTO_CONFIRM=1 bash desplegar.sh install` con la misma lista (copia + un reinicio).
4. Odoo: Aplicaciones > Actualizar lista > **Actualizar solo `koroshi_base`**. Arrastra los otros 6 y el resto de
   KOROSHI con la versión que ya tienen.
5. Comprobar `installed_version` = `latest_version` de los 7. Preparación crea el parámetro
   `koroshi_preparacion.refresco_solo_s` = 30.
6. Ctrl+F5 en las PDA.

Mañana en una PDA: Lecturas (leer, caja, validar), Contenedores (Cambiar, «Es otro»), Faltante, Devoluciones >
Ubicar y Recuentos. La misma tarjeta en todas.

## Tanda B, hoy, solo si la A ha ido bien: retener pedidos de tienda duplicados (módulo nuevo)

1. `desplegar.sh check koroshi_retener_tiendas 1.3.0` y después `install` (otro reinicio corto).
2. Odoo: **Instalar** (no actualiza otros).
3. Atención: viene con `cancelar_pocas` = 1. Los pedidos de tienda con menos de 20 uds reservadas **no se preparan**
   (correo a Betty). Si Isaac prefiere empezar solo avisando, poner el parámetro a 0 antes de las 04:50.

## Tanda C, otro día fuera de horas: lo de detrás (sin PDA)

Uno a uno, cada uno con su `check`/`install` y su `-u`:

1. `koroshi_s4t_envios` 1.4.0: un error de red ya no cuenta como intento.
2. `koroshi_s4t_traspasos` 1.4.0.
3. `koroshi_agrupaciones_web` 1.1.0: reintento y correo si el corte falla.
4. `koroshi_zonas` 1.7.0: correo si el reparto falla y vigilante a las 05:15 (cron nuevo). No instalarlo el mismo
   día antes de las 04:50 sin avisar.
5. `koroshi_monitor` 1.44.0 y luego `koroshi_informe` 1.4.0. El `-u` de monitor arrastra menú e informe: copiar los
   dos juntos y actualizar solo monitor.
6. `koroshi_s4t_pedidos` 1.2.0: crea el cron de las 03:30 en SIMULAR. Una semana mirando los informes antes de pasar
   `prioridad_modo` a real.

## Tanda D, cuando la A esté probada en PDA: prenda en el suelo (módulo nuevo)

`koroshi_prenda_suelo` 1.1.0: instalar. Necesita preparación 3.35 y base 1.2.1. Probar en PDA los casos A-E. Solo
leer: «Encontrada» mueve stock de FALTANTE.

## Si algo falla

`desplegar.sh` hace copia de seguridad en `/opt/nath-erp/copias_modulos/<fecha>`. Si un `-u` da error, no se
reintenta a ciegas: se lee el log, se vuelve a la copia y se reinicia.
