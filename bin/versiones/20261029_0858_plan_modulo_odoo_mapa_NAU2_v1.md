# Módulo Odoo para el mapa NAU-2

## Objetivo

Mantener el planner original como mapa editable y añadir una segunda vista operativa para consultar, en tiempo real o casi real, la actividad de picking.

## Vistas

### 1. Mapa editable

- Usa el `warehouse_planner_NAU2_24_2026-10-29_0900_celdas.html` sin modificar su dibujo.
- Permite mover, duplicar, borrar y guardar layouts.
- Solo responsables autorizados podrán editar.
- Se conserva el guardado por versiones y la exportación JSON.

### 2. Mapa operativo

La pantalla muestra:

- Persona y PDA.
- OUT activo.
- Estado: en picking, en pausa o finalizado.
- Hora de inicio del OUT.
- Último picking confirmado.
- Ubicación del último escaneo (`L## P## C#`).
- Hora del último escaneo.
- Hora de finalización.
- Progreso estimado y trazado de la actividad sobre el plano.

La v6 incluye datos demo locales para probar la interfaz. No se conecta todavía a producción.

## Propuesta de modelos Odoo 13

Los nombres son una propuesta para revisar antes de crear el módulo:

- `koroshi.layout`: nave, nombre, versión, layout JSON, activo, compañía.
- `koroshi.layout.element`: elemento, tipo, posición, medidas, propiedades y código de ubicación.
- `koroshi.pick.event`: OUT, usuario, PDA, ubicación, tipo de evento, fecha/hora y compañía.
- `koroshi.pick.session`: OUT, usuario, PDA, inicio, último escaneo, fin, estado y progreso.

Para no sobrecargar Odoo, el mapa operativo puede leer eventos recientes y calcular la sesión actual en el navegador o mediante un endpoint específico.

## Flujo de datos previsto

1. El usuario abre el mapa operativo.
2. El módulo consulta sesiones y eventos de KOROSHI, compañía 8.
3. Cada evento actualiza la ubicación de la persona y el último picking.
4. La interfaz refresca la vista cada pocos segundos o mediante una acción manual.
5. Si no hay evento reciente, la persona aparece como sin señal o última posición conocida.

## Seguridad y despliegue

- Solo compañía 8.
- Vista operativa para usuarios autorizados.
- Edición de layouts únicamente para responsables.
- Primero se prueba en DIAGNÓSTICO.
- No se escriben datos de producción hasta validación explícita.
- No se guardan contraseñas en el HTML.

## Siguiente paso técnico

Validar con un ejemplo real de OUT qué modelo y qué evento representan exactamente el inicio, cada picking y el final. Después se sustituye `opsPeople` de la v6 por una respuesta JSON-RPC de Odoo, manteniendo el mapa y la interfaz.
