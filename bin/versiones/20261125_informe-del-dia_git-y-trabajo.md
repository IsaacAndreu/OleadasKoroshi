# Informe del 25/11/2026: lo hecho hoy y estado de GitHub

Escrito a las ~15:00 (hora de aquí), después de juntar lo de GitHub con lo de este ordenador y subirlo todo.

## 1. GitHub

| | |
|---|---|
| **Traído de GitHub** | 4 commits de la otra sesión de tuctuc (noche del 24/11): lector, índices trigrama y de líneas de venta, reinicio 19:15 UTC; estudio y adaptación de los módulos KOROSHI a Prime; mejoras de la noche |
| **Cómo** | `merge`, no `rebase`: las etiquetas de hoy apuntan a los commits locales y un rebase las habría dejado colgando. Sin conflictos (TABLERO.md y el traspaso de tuctuc se juntaron solos) |
| **Subido** | 45 commits de hoy + el merge (`4b8d816..51a2c9e`) y 15 etiquetas nuevas |
| **Antes de subir** | Revisado el cambio entero (86 archivos): ninguna contraseña ni clave; las únicas palabras «token» son el antidoble toque de las pantallas de la PDA |
| **Perdido** | Nada. Los 3 archivos a medias de otras sesiones (`.claude/launch.json`, `.gitignore`, `bin/versiones/diseno-zonas-modo-del-dia_2026-11-20.md`) siguen igual, sin commitear |

Etiquetas subidas: koroshi_impresion/v1.0.0 · koroshi_juntar_cajas/v1.0.0, v1.1.0 · koroshi_monitor/v1.45.0, v1.46.0 ·
koroshi_preparacion/v3.36.0, v3.36.1 · koroshi_transportista/v1.0.0 a v1.5.0 (7) ·
nucleo_tuctuc/conciliacion-origen/2026-11-25.

**No subido, a propósito:**
- ZIP y tar.gz de hoy (15): están fuera de git por regla; se rehacen desde la etiqueta con `git archive`.
- 5 archivos de trabajo de hoy de otras sesiones, sin seguimiento (no son de esta sesión; los commitea quien los hizo
  o se deciden):
  - `bin/versiones/20261125_Envios-Koroshi-AMPOSTA_con-ordenes-y-prendas.xlsx`
  - `bin/versiones/20261125_envios_tiendas_GLS_XPO_por_tienda.xlsx`
  - `bin/versiones/20261125_OUT-tiendas-hechas-sin-salir_sin-DEV.md`
  - `bin/versiones/20261125_accion-1960_sync-manual-s4t_ANTES-4639.py`
  - `bin/versiones/correo-koroshi-K46-K9-pedidos-a-medias_2026-11-25.md`

## 2. KOROSHI (almacén): lo de hoy

| Módulo | Versión | Qué hace | Estado |
|---|---|---|---|
| koroshi_juntar_cajas (nuevo) | 1.0.0 | Juntar una CJ pequeña dentro de otra del mismo pedido y tienda, desde la PDA (Expediciones) | Instalada ~08:45 |
| | 1.1.0 | «Revisar caja»: partir una CJ con OUT validadas | Instalada ~09:43 |
| koroshi_impresion (nuevo) | 1.0.0 | Cola de impresión en Odoo para las impresoras USB de los PC del almacén | Instalada ~10:20 |
| Agente de impresión (PC) | 1.0.0 → 1.0.2 | Programa en el portátil de Expediciones que imprime la cola (EXP1, papel 4x6 apaisado de la GK420t) | Instalado en el portátil |
| koroshi_monitor | 1.45.0 + 1.46.0 | Etiquetas CJ sin leer para jefes («La he tirado»); «¿Dos cajas en una CJ?» por volumen | 1.46.0 instalada 10:29 |
| koroshi_transportista (nuevo) | 1.0.0 | Etiqueta GLS/XPO desde la PDA escaneando las CJ, impresa en el portátil | Instalada ~11:20 |
| | 1.1.0 / 1.1.1 | Leer una CJ por sus últimas 4-9 cifras; Intro del teclado Android | Instaladas ~12:10 / 12:22 |
| | 1.2.0 / 1.3.0 | GLS agrupado con cajas distintas (K41), marca SUMI; «Dejar fuera» una OUT de otro día (K46) | Instaladas ~12:42 |
| | 1.4.0 / 1.5.0 | Aviso de CJ impresas y vacías en Odoo (K24); aviso de transportista (GLS hasta 5 bultos); GLS/XPO ya no se marca solo | 1.5.0 instalada 14:04 |
| koroshi_preparacion | 3.36.0 / 3.36.1 | «Caja llena» por volumen en Lecturas (0,100 m³ la 600X400X400, 0,075 m³ la MEDIANA) | **Hecha, SIN INSTALAR** (servidor 3.35.0) |

Otros: TABLERO, agrupaciones web, el corte de las 11:00 pasa a las 12:00 desde el 26/11. Diseños escritos: juntar
cajas, revisar caja, imprimir desde la PDA, Transportista v2-v4 (decisiones de Isaac), «Caja llena» v1 y plan SUMI
por Lecturas v1.

## 3. odoo.tuctuc.com: conciliación Shopify/Mollie

- **Problema**: de 42 líneas solo se conciliaban 13 solas; el resto iba a la 43001000 sin casar la factura.
- **Causa**:
  1. Las facturas de venta (FW/…) solo llevan el pedido en el origen (WT#…), y Odoo no mira el origen al conciliar
     solo.
  2. La regla 330 se había cambiado a «Sugerir valores de contrapartida».
  - Quedan 50 apuntes abiertos en la 430 (−3.407,21 €) en los extractos 46154, 46155, 46265 y 46266.
- **Arreglo, instalado a las 14:30**:
  - Odoo también compara el origen de la factura (WT#) con la línea del banco.
  - La regla 330 vuelve a «Casar con las facturas existentes».
  - Prueba con rollback en el extracto 46266: 12 → 38 de 40 solas, 0 con otra factura.
  - Copia del archivo antiguo: `/opt/tuctuc-erp/copias_modulos/conciliacion_origen_2026-11-25_132845/`.
  - Etiqueta: `nucleo_tuctuc/conciliacion-origen/2026-11-25`.
- **Falta**: que contabilidad lo pruebe en pantalla (un extracto nuevo, o revertir antes el 46155, de 1 línea).
  - Dos líneas no entran por clientes duplicados (WT#351003, WT#351014): se casan a mano.

## 4. Pendiente

1. **Contabilidad**: probar la conciliación en real.
2. **koroshi_preparacion 3.36.1** (Caja llena): instalar con el sí de Isaac.
3. **tuctuc, cuando se decida**:
   - índice en `account_move_line.payment_id`: revertir una conciliación tarda minutos sin él;
   - arreglar los 50 apuntes abiertos de la 430;
   - exportación de stock a las tiendas.
4. **Los 5 archivos sin seguimiento** de la sección 1: que cada sesión los commitee o se descarten.
