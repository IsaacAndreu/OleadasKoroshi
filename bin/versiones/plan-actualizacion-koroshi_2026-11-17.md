# Plan para actualizar de golpe los módulos KOROSHI (17/11/2026)

Hecho con las versiones leídas en nath.tuctuc.com el 17/11 (solo lectura: installed_version = latest_version en
todos, también en koroshi_preparacion 3.29.0) y con la revisión de los cambios de cada módulo desde la versión del
servidor. No se ha instalado ni tocado nada.

## Qué se actualiza

| Módulo | Servidor | Nueva | ZIP en `bin/` |
|---|---|---|---|
| koroshi_base | — (nuevo) | 1.0.0 | 20261114_koroshi_base_v1.0.0.zip |
| koroshi_operarios | 2.11.1 | 2.14.0 | 20261116_… |
| koroshi_kpi | 1.5.0 | 1.9.0 | 20261116_… |
| koroshi_warehouse_map | 0.1.20261102.39 | 0.1.20261116.46 | 20261116_… |
| koroshi_consumibles | 1.3.0 | 1.4.0 | 20261114_… |
| koroshi_xpo_bultos | 1.1.0 | 1.3.0 | 20261116_… |
| koroshi_monitor | 1.24.0 | 1.28.0 | 20261116_… |
| koroshi_preparacion | 3.29.0 | 3.31.0 | 20261116_… |
| koroshi_faltantes | 1.4.1 | 1.5.0 | 20261116_… |
| koroshi_pda_app | 1.0.0 | 1.1.0 | 20261116_… |
| koroshi_caja_existente | 1.3.0 | 1.4.0 | 20261116_… |
| koroshi_zonas | 1.2.0 | 1.4.0 | 20261114_… |
| koroshi_informe | 1.0.1 | 1.2.0 | 20261116_… |
| koroshi_menu | 2.1.0 | **2.4.1** (no la 2.5.0) | 20261116_… |
| koroshi_s4t_envios | 1.1.0 | 1.2.0 (sigue en diagnóstico) | 20261114_… |

Al día: koroshi_contenedores 1.4.0 y koroshi_rendiment 1.1.0.
**No se instalan todavía:**
- koroshi_actividades: sus menús quedarían ocultos y su icono lo vería todo el mundo, también la PDA.
- koroshi_s4t_traspasos: la primera pasada crearía recepciones DEV de todo lo descargado desde el 01/07.
- koroshi_delegacion.

## Lo que no puede salir mal
1. **koroshi_base, instalado antes de copiar el resto.** Casi todos los módulos dependen ahora de él. Si Odoo arranca
   con el código nuevo y koroshi_base sin instalar, no carga esos módulos, y entre ellos está **preparacion (la PDA)**.
2. **Actualizar justo después del reinicio.** operarios 2.14 añade las columnas `parado` y `efectivo` a las tareas.
   Mientras Odoo corre con el código nuevo sin actualizar, falla todo lo que lee tareas (Lecturas, Monitor, cron
   cada 5 min): es lo mismo que pasó el 16/11.
3. **Fuera de horario y lejos de los crons:** 21:30 UTC (KPI), 03:50, 04:00 y 04:30 UTC (zonas). Buena ventana:
   ~17:30–21:00 hora del almacén, sin nadie en las PDA.

## Pasos (los ejecuta el responsable; cada uno con su visto bueno)

**Tanda 1: solo koroshi_base**
```bash
bash desplegar.sh check koroshi_base 1.0.0
sudo AUTO_CONFIRM=1 bash desplegar.sh install koroshi_base 1.0.0
```
Odoo › Aplicaciones › Actualizar lista › buscar «koroshi_base» › **Instalar**. No cambia nada visible: solo añade
un JS.

**Tanda 2: el resto, de una vez**
```bash
bash desplegar.sh check koroshi_operarios 2.14.0 koroshi_kpi 1.9.0 koroshi_warehouse_map 0.1.20261116.46 koroshi_consumibles 1.4.0 koroshi_xpo_bultos 1.3.0 koroshi_monitor 1.28.0 koroshi_preparacion 3.31.0 koroshi_faltantes 1.5.0 koroshi_pda_app 1.1.0 koroshi_caja_existente 1.4.0 koroshi_zonas 1.4.0 koroshi_informe 1.2.0 koroshi_menu 2.4.1 koroshi_s4t_envios 1.2.0
```
Si el check sale todo OK, el mismo comando con `sudo AUTO_CONFIRM=1 bash desplegar.sh install …`. **Nada más
arrancar**: Aplicaciones › Actualizar lista › koroshi_base › **Actualizar**. Al actualizar koroshi_base, Odoo actualiza
en la misma pasada todos los módulos instalados que dependen de él, en el orden correcto (operarios antes que
informe, kpi antes que menu). Es un solo clic, en vez de catorce.

## Después
- En el log: que no salga «Unmet dependencies», «Some modules are not loaded» ni «Unable to delete» (del cron 204).
- El cron 204 (segundo correo de las 17:00) desaparece. Los crons de kpi y zonas vuelven a su valor del XML.
  Ahora mismo coinciden con lo que hay.
- Ctrl+F5 en los PC y recargar todas las PDA.
- Zonas sigue en sombra (`modo_cron` = sombra): los cambios de reparto (7 días atrás, orden por urgencia) no afectan
  al trabajo real.

## Qué probar en una PDA real (con «Almacén Nath»; en OUT reales solo leer y deshacer)
- Leer tarjeta → sale la OUT. Lecturas guarda (mirar que la lectura aparece).
- Pausa ⏸ (dos toques) → «EN PAUSA» → ▶ Seguir: misma OUT y vuelve a leer.
- Faltante: aparece «Si no, aquí» con la segunda ubicación.
- Cerrar caja con tipo de caja (Consumibles 1.4): con dos PDA a la vez, que no dé error de servidor.
- Monitor en PC y en la tele: carga, sale la u/h y la alarma en rojo.
- Una expedición XPO: en el chatter de la OUT, «declarados N bultos» con el número de cajas.
- Almacen 2: icono «Bandeja» y Hoy › Previsión de cajas.

## Fallos conocidos que no impiden actualizar
- Ficha KPI: con zonas 1.4 sobre kpi 1.9, las cajas de zonas solo se ven en las fichas con método «mixto». Se arregla
  con una zonas 1.4.1 (un xpath).
- Monitor: la caché no distingue la zona horaria del usuario (todos los usuarios usan la de Madrid: sin efecto hoy).
- warehouse_map .39 no está en git; entre .35 y .46 no cambian modelos ni permisos, así que no se espera cambio de
  esquema.
