# Plan del módulo de mapa interactivo de la NAU-2

Fecha: 29/10/2026 08:32  
Ámbito: KOROSHI, compañía 8, nave NAU-2  
Punto de partida: `warehouse_planner_NAU2_24_2026-10-29_0900_celdas.html`

## 1. Objetivo

Convertir el planner actual en una herramienta que la jefa pueda usar sin tocar código para:

- ver el plano de la nave de 210 × 60 m;
- añadir, mover, girar, copiar y borrar elementos;
- editar las propiedades de una ubicación o zona;
- crear tipos nuevos de estantería, celda, zona u objeto;
- activar y desactivar capas de información;
- guardar cada cambio como una versión recuperable;
- buscar una ubicación `L## P## C#` y localizarla en el plano;
- consultar después datos de Odoo sin modificar stock ni expediciones.

La herramienta tendrá dos usos claramente separados: **Ver** para consultar el plano y **Editar** para modificarlo. La administración del catálogo quedará reservada a responsables.

## 2. Principio de diseño

La jefa no debe ver JSON, coordenadas ni nombres técnicos salvo que los necesite. La pantalla debe hablar en términos de “Añadir estantería”, “Editar ubicación”, “Guardar versión” y “Mostrar aire”.

El archivo actual seguirá siendo una referencia y no se sobrescribirá. Primero se hará un editor local con datos JSON; cuando ese editor esté validado, se convertirá en el módulo `koroshi_layout` de Odoo. Así se puede probar la forma de trabajar antes de conectarlo a producción.

## 3. Cómo será la pantalla

### Pantalla principal

- Barra superior: `Ver`, `Editar`, `Guardar versión`, `Abrir versión`, `Deshacer`, `Rehacer`, `Buscar`, `Imprimir`.
- Lateral izquierdo: catálogo de elementos agrupado en Estanterías, Pasillos, Celdas, Zonas y Otros.
- Centro: plano ampliable de la nave, con rejilla, cotas y ajuste a rejilla.
- Lateral derecho: propiedades del elemento seleccionado.
- Parte inferior: mensaje de estado, versión abierta y aviso de cambios sin guardar.

### Propiedades editables

Al seleccionar un elemento se mostrará un formulario sencillo con:

- nombre visible y código interno;
- tipo de elemento;
- ubicación `L## P## C#`, cuando corresponda;
- posición, anchura, fondo y giro;
- niveles, huecos y capacidad en litros;
- familia y temporada asignadas;
- color, etiqueta y notas;
- visibilidad por capa.

Los campos se validarán al salir del formulario. Un dato incorrecto generará un aviso claro y no se perderá el resto de cambios.

### Crear un tipo nuevo

El botón `+ Nuevo tipo` abrirá un formulario con nombre, grupo, forma, medidas, color, icono y, si es una celda, columnas, pisos y litros por hueco. Al guardar, el nuevo tipo aparecerá automáticamente en la paleta y en la leyenda. No habrá que programar una nueva rama de dibujo.

## 4. Capas y vistas

Las capas se podrán encender y apagar sin cambiar el layout:

1. estructura de la nave;
2. pasillos y lineales;
3. ocupación;
4. aire libre;
5. familias;
6. temporada y plan final;
7. PDAs y último escaneo.

Cada capa tendrá su propia leyenda. La vista inicial será limpia; la jefa podrá activar una capa cuando quiera explicar una decisión. Las capas AIRE, FAMILIAS y PLAN reutilizarán los datos PF del planner v24, pero quedarán separados de la geometría.

## 5. Guardado y versiones

Nunca se actualizará una versión histórica. El botón será `Guardar nueva versión` y pedirá nombre y comentario, por ejemplo: `Plan invierno 2026 · mover outlet a C3-C4`.

Cada versión guardará:

- fecha y hora;
- usuario que la creó;
- comentario;
- catálogo utilizado;
- elementos y propiedades;
- capas y configuración de vista;
- origen de los datos de ocupación.

En local se usará `localStorage` como autoguardado y archivos JSON con fecha y hora para copia. En Odoo, las versiones se conservarán como registros y se podrá abrir cualquiera sin borrar la actual. Habrá estados `Borrador`, `Validada` y `Archivada`.

## 6. Datos y arquitectura propuesta

### Fase local

- `catalogo.json`: tipos de elementos, medidas, colores, iconos y reglas de dibujo.
- `layout-NAU2_<fecha>.json`: elementos colocados, posición, giro y propiedades.
- `capas-NAU2_<fecha>.json`: ocupación, aire, familias, temporada y plan.
- Un renderizador genérico para rectángulos, líneas, polígonos e iconos.
- Un adaptador especial para los lineales, porque sus marcas PF necesitan conservar la lógica actual.
- Konva.js empaquetado localmente en el HTML o en el módulo; no depender de un CDN para trabajar en la nave.

### Módulo Odoo 13 `koroshi_layout`

Modelos iniciales:

- `koroshi.layout`: nave, compañía, nombre, versión actual, estado y JSON del layout.
- `koroshi.layout.version`: instantánea inmutable del layout, autor, fecha, comentario y estado.
- `koroshi.layout.type`: catálogo de tipos editable por responsables.
- `koroshi.layout.location`: relación entre elemento, código `L## P## C#` y `stock.location`.

El JSON será la fuente de la geometría para que guardar y cargar sea rápido. Las relaciones que haya que buscar desde Odoo, como ubicación, familia o permisos, tendrán campos propios. La vista web se cargará desde un controlador del módulo y guardará mediante JSON-RPC.

## 7. Plan de ejecución

### Fase 0 · Definición y seguridad

Confirmar el sistema de coordenadas, el significado de cada tipo, el fondo real de las estanterías y la celda 4. Preparar una copia de referencia del planner v24 y una lista de pruebas. El módulo quedará limitado a la compañía 8 y no tocará crons, expediciones, stock ni acciones de otros almacenes.

### Fase 1 · Editor local funcional

Extraer del planner v24 los tipos actuales: palés, racks, pasillos PP1/PP2/VM1–4/VV1–2, celdas 1–4, zonas, luminarias, altillos, garita, filtraciones y bajantes. Generar el catálogo y convertir el layout actual de la NAU-2 a JSON.

Construir selección, arrastre, giro, copia, borrado con confirmación, ajuste a rejilla, selección múltiple, alineación, búsqueda, propiedades, deshacer/rehacer, guardar y cargar. Añadir las capas AIRE, FAMILIAS y PLAN y verificar que coinciden con v24.

### Fase 2 · Uso sencillo para la jefa

Pulir la interfaz en castellano, ocultar opciones avanzadas, añadir ayuda breve junto a cada botón, mensajes de guardado, aviso de cambios sin guardar, exportación PNG/PDF y un modo de solo lectura. Probar tareas reales: mover una zona, crear una celda, localizar L43 y guardar dos versiones.

### Fase 3 · Módulo Odoo

Crear la estructura `koroshi_layout`, menús, vistas, grupos de seguridad y carga del editor. Importar el catálogo y el layout validado. Permitir que responsables editen y que el resto consulte. Las pruebas se harán primero en diagnóstico/pruebas y solo para KOROSHI.

### Fase 4 · Datos en vivo de solo lectura

Añadir ocupación desde `stock.quant`, picks y movimientos, y último escaneo de cada PDA. Si un dato no está disponible, se mostrará “Sin dato” y no se inventará una posición. Esta fase no cambiará ningún documento logístico.

### Fase 5 · Piloto y formación

Probar con la jefa y un usuario de almacén durante varios días. Comparar el mapa con la nave, comprobar que las versiones se recuperan y preparar una guía de una página con cuatro operaciones: buscar, editar, guardar y volver atrás.

## 8. Validaciones importantes

El editor debe avisar, sin bloquear innecesariamente, cuando:

- un elemento sale de los límites 210 × 60 m;
- hay dos elementos con el mismo código de ubicación;
- el código no cumple `L## P## C[1-4]`;
- una celda tiene medidas o litros imposibles;
- se intenta borrar un elemento con información asociada;
- hay cambios pendientes antes de cerrar o cargar otra versión.

Para el mapa inicial se comprobarán 136 lineales, las celdas 1–4, las zonas de outlet y Z, los niveles bajos y altos y las capas PF. Se hará una prueba de exportar, importar y volver a exportar para asegurar que el layout no cambia.

## 9. Criterio de terminado del primer entregable

El primer entregable estará listo cuando la jefa pueda, sin tocar código:

1. abrir el mapa actual de NAU-2;
2. buscar una ubicación y verla resaltada;
3. mover o girar un elemento y editar sus propiedades;
4. crear un tipo de celda nuevo desde la pantalla;
5. activar AIRE, FAMILIAS y PLAN;
6. guardar una nueva versión y recuperar la anterior;
7. exportar el mapa para imprimirlo.

La comprobación técnica será que el editor use el catálogo y un renderizador genérico, que el layout se importe sin pérdida y que los datos de Odoo queden en modo lectura hasta que se valide el piloto.

## 10. Orden recomendado y esfuerzo orientativo

La primera versión útil puede dividirse en tres bloques: editor local y migración del v24, aproximadamente 6–8 jornadas; módulo Odoo con versiones y permisos, 5–8 jornadas; capas en vivo y piloto, 4–6 jornadas. Son estimaciones para ordenar el trabajo, no una fecha cerrada: el punto que más puede moverlas es la calidad de la relación entre códigos `L## P## C#` y ubicaciones de Odoo.

La decisión que conviene tomar antes de programar es esta: validar primero el editor local con la jefa usando el mapa real y, solo cuando la forma de trabajar esté aprobada, instalar `koroshi_layout` en el entorno de pruebas de Odoo.
