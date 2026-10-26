# Monitor picking Oriola (`oriola_monitor`)

Módulo para **odoo.tuctuc.com** (base de datos TUCTUC_PRODUCTION, almacén Oriola - Amposta, WH-OR).
Es otro servidor que el de KOROSHI: este módulo no comparte nada con `koroshi_monitor`.

Menú **Inventario › Monitor picking**. Solo lee.

## Qué enseña

- **Arriba:** OUT validadas, uds servidas, cajas, uds leídas, personas leyendo (y cuántas en los últimos 15 min),
  uds por hora-persona; hoy, además, OUT listas para coger y en espera.
- **Por persona:** cada PDA tiene su usuario, así que no hace falta estimar. Muestra uds y líneas leídas, OUT tocadas
  y validadas, cajas, primera y última lectura, horas activas y uds por hora. Las horas activas son los cuartos de hora
  con lecturas, más los huecos de hasta 30 min entre ellos.
- **Almacén automático y sistema** (Almacen Automatizado, OdooBot): aparte, sin contar como personas.
- **Uds leídas por hora**, separando personas y automático.
- **Por canal**, según el origen del albarán (APP-S, ECI, WT#, VP…): lo hecho ese día y, hoy, lo listo y en espera,
  con la OUT abierta más antigua.
- **Lotes** (B-WEB, B-ECI, B-VP…) que aún tienen OUT sin hacer.

## Para no cargar el servidor

- Todo va en SQL agregado, solo sobre las OUT del tipo de salida de WH-OR.
- Cada consulta tiene un límite de 15 s (`statement_timeout`).
- El resultado se guarda en memoria 90 s (10 min los días pasados) y lo comparten todas las pantallas. Un solo
  cálculo a la vez.
- La pantalla pide datos cada 2 min y solo si la pestaña se está viendo. El botón Refrescar no recalcula si el dato
  tiene menos de 20 s.

## Configuración

Parámetro del sistema `oriola_monitor.picking_type_id`: el id del tipo de albarán. Si no está, usa el de salida
del almacén con código `WH-OR`.

## Instalar

`bin/instalar_oriola_monitor_v1.0_<fecha>.sh` en el servidor de odoo.tuctuc.com:

1. `sudo bash …` para comprobar.
2. `sudo INSTALAR=1 bash …` para copiar la carpeta.

No reinicia Odoo. Después, en Aplicaciones: Actualizar lista de aplicaciones › Monitor picking Oriola › Instalar.

## Límites

Las «uds leídas» cuentan las líneas con cantidad hecha según el usuario y la hora de su última escritura. Si un
proceso nocturno reescribe líneas, pueden aparecer lecturas a horas raras (el 23/10 se vieron a la 1 y a las 2 de la
madrugada).
