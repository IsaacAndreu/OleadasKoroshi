# KOROSHI Menú de Inventario (`koroshi_menu`)

Ordena los menús KOROSHI de Inventario. Antes había **5 menús** en la barra de arriba (KOROSHI KPI, KOROSHI
Operarios, KOROSHI Zonas, KOROSHI · Operaciones, KOROSHI Faltantes) con 35 opciones; la barra tenía 11 menús.
Ahora la barra tiene 7 y KOROSHI solo lo de cada día.

## Dónde está cada cosa

**Inventario › KOROSHI** (lo que se abre cada día)

- Monitor picking · Consulta de envíos
- Reparto de hoy · Colas (grupo «ver productividad»)
- Mapa NAU-2 · Hoja de carga XPO de hoy
- Faltante (PDA) · Revisión de faltantes
- Registrar consumo

**Inventario › Informes › KOROSHI** (consultar datos)

- KPI por día · Comparativa de semanas · Faltas por día · Faltas repetidas (revisar) · Pesos y litros por tipo
- Productividad · Tareas · OUT validadas hoy sin operario · Lecturas de preparación (grupo «ver productividad»)
- Ejecuciones de zonas · Cajas cerradas por día y zona · Diagnóstico de zonas de hoy
- Rondas de faltantes (INT) · Historial de consumibles

**Inventario › Configuración › KOROSHI** (se toca poco)

- **Ajustes KOROSHI** (responsables): todos los parámetros KOROSHI en una pantalla (v1.1)
- Operarios · Crear operarios · Motivos para saltar (grupo «ver productividad»)
- Consumibles: artículos · Consumibles: totales iniciales
- Zonas: configuración · simular hoy · medir desde el 22/10 (responsables)
- Configuración de planos (responsables) · Sesiones operativas
- Crear ronda de revisión · Puestos a 0 hoy (responsables) · Recalcular faltas de hoy

**Lecturas (PDA)** no está en el menú: tiene su icono en la pantalla de inicio (koroshi_operarios v2.7).

## Cómo funciona

- Crea sus propios menús con las **mismas acciones y los mismos grupos** que los de antes.
- Archiva (`active = False`) los 5 menús KOROSHI de antes y «Hoja de carga XPO de hoy» de Informes. Al actualizar
  esos módulos siguen archivados (el `menuitem` no toca `active`).
- **Informes** y **Configuración** de Inventario solo los ven los administradores de Inventario. El 12/11/2026 los 6
  usuarios con Inventario son administradores: nadie pierde nada.
- Si un módulo KOROSHI añade un menú nuevo, sale dentro de su menú viejo (archivado, no se ve): hay que añadirlo aquí.
- **Desinstalar** este módulo deja todo como antes (`uninstall_hook` vuelve a activar los menús).

No cambia datos ni otros módulos. Los menús que no son de KOROSHI (B2B fields Update History, Informes de Odoo…)
no se tocan.

## Versiones

- **v1.0.0 (12/11/2026):** primera versión.
- **v1.1.0 (12/11/2026):** **Ajustes KOROSHI**: los parámetros KOROSHI (orden de Preparación, agrupaciones, minutos sin
  leer, salida por inactividad, OUT a dos, informe diario, faltantes, faltas repetidas, usuarios de la PDA) en una
  pantalla, con nombre y explicación. Solo escribe los que cambian; siguen en Parámetros del sistema como siempre.
  Menús nuevos de koroshi_kpi 1.5 en Informes › KOROSHI: **Comparativa de semanas** y **Faltas repetidas (revisar)**.
  Necesita koroshi_kpi 1.5.0 y koroshi_operarios 2.8.0 instalados antes.
