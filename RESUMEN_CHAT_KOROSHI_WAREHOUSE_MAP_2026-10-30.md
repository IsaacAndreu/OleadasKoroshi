# Resumen del trabajo — Koroshi Warehouse Map / Odoo

Fecha de cierre del resumen: **30/10/2026**  
Almacén principal del módulo: **NAU-2**. El plano de NAU-1 se dejó como material de impresión y no forma parte del módulo operativo actual.

## 1. Objetivo del proyecto

Crear una herramienta integrada en Odoo para:

- Ver y editar el plano del almacén.
- Ver el mapa operativo de las OUT reales del día.
- Saber quién está trabajando, dónde está y qué OUT tiene asignada.
- Mostrar el recorrido real o simulado por pasillos y ubicaciones.
- Agrupar pedidos para picking por zonas y ubicaciones.
- Medir tiempos, kilómetros, paradas, unidades, cajas e incidencias.
- Preparar posteriormente un modo PDA/offline para los operarios.

El flujo acordado es:

`Odoo → selección de pedidos/OUT → agrupación → picking con PDA → incidencias → sincronización con Odoo`

## 2. Decisiones funcionales importantes

- Todo el texto de la interfaz debe estar en castellano.
- El nombre visible de cada OUT debe ser la tienda, porque normalmente una OUT corresponde a una tienda.
- El mapa operativo es exclusivamente para NAU-2.
- El mapa editable conserva el plano original; no se debe modificar el mapa central al mejorar la interfaz.
- El inicio del recorrido se toma desde el primer artículo validado, no desde la hora de creación de la OUT.
- La hora de creación de la OUT no sirve como inicio del picking porque puede confirmarse automáticamente durante la noche.
- El tiempo real se mide desde la validación del primer artículo hasta la validación del último artículo/cierre operativo.
- El recorrido debe respetar pasillos y entrar en el lineal para validar; no puede atravesar lineales ni desplazarse en diagonal sin sentido.
- Las ubicaciones de muelle `MU` pueden quedar fuera del plano actual; se identifican como una limitación de cartografía pendiente.
- Para bajar a los muelles, el recorrido debe usar el pasillo central.
- Si dos ubicaciones están juntas, se permite continuar lateralmente sin volver innecesariamente al pasillo central.
- Se añadieron tiempos configurables de apertura y cierre de caja como parte del proceso, inicialmente estimados en unos 20–30 segundos por evento.

## 3. Interfaz y mapas

Se evolucionó el prototipo desde varios HTML de prueba hasta una interfaz integrada en Odoo con:

- Mapa editable.
- Mapa operativo.
- Panel lateral izquierdo con filtros, OUT, personas, estados y acciones.
- Panel derecho contextual con detalle de la selección.
- Botón para volver a ver todas las OUT.
- Posibilidad de deseleccionar una OUT haciendo clic de nuevo.
- Centrado en la persona cuando se selecciona un operario.
- Leyenda de colores y estados.
- Filtros rápidos por estado.
- Selección de una OUT para ver su recorrido.
- Vista de estadísticas de OUT, unidades, ubicaciones, cajas e incidencias.
- Mapa de calor para zonas con más pasos, errores o actividad.
- Simulación reproducible con velocidad seleccionable.
- Arrastre del mapa con el botón derecho.
- Corrección para que el mapa de calor se pueda activar y desactivar correctamente.
- Corrección para que el punto de simulación no se mueva incorrectamente al arrastrar el mapa.

El diseño se fue simplificando para evitar exceso de cuadros en la parte superior y dejar las acciones principales visibles sin saturar la pantalla.

## 4. Simulación y recorrido

La simulación se planteó separando:

1. Paradas reales: una por ubicación física.
2. Tramos de pasillo entre ubicaciones.
3. Entrada desde el pasillo hasta el lineal (`L/P/C`).
4. Pausa de validación en la ubicación exacta.
5. Regreso al pasillo.
6. Eventos de apertura y cierre de caja.
7. Continuación hasta la siguiente ubicación.

La ruta debe:

- Usar el orden real de escaneo si Odoo lo proporciona.
- Optimizar por ubicación cuando no existe orden real.
- Evitar atravesar lineales.
- Mostrar cada ubicación de validación, no solo el número total de paradas.
- Empezar en el primer artículo validado.
- Contabilizar unidades, ubicaciones, distancia y tiempo estimado.

## 5. Datos que se definieron como necesarios

Cada línea de picking debe conservar el pedido/OUT al que pertenece. Los campos mínimos son:

- Pedido o referencia de picking.
- Tienda o cliente.
- Referencia del producto.
- EAN/código de barras.
- Cantidad solicitada.
- Cantidad validada.
- Ubicación.
- Orden real de lectura, si existe.
- Estado de reserva.
- Incidencias.
- Operario.
- Caja asociada.

También se identificó que `Referencia`, `Ubicación`, `Cantidad`, `Ean`, `Numeral` y `Leido` no bastan para separar correctamente las cantidades por pedido.

## 6. Funciones previstas para picking y PDA

- Escanear producto.
- Validar EAN.
- Descontar cantidad leída.
- Avanzar automáticamente al completar la línea.
- Avisar de producto incorrecto.
- Registrar faltante.
- Registrar cantidad insuficiente.
- Registrar ubicación vacía.
- Registrar EAN incorrecto.
- Registrar producto dañado.
- Registrar caja llena.
- Detectar sobrantes y lecturas duplicadas.
- Trabajar sin conexión.
- Guardar lecturas localmente.
- Sincronizar después sin duplicar lecturas.
- Separar de nuevo las cantidades por pedido antes de enviarlas a Odoo.

## 7. Estadísticas y seguimiento acordados

Por OUT y por operario se quiere poder ver:

- Unidades previstas y validadas.
- Líneas Odoo visibles y totales.
- Ubicaciones visitadas.
- Distancia estimada y real por pasillos.
- Tiempo estimado.
- Tiempo real desde primer artículo hasta último artículo.
- Tiempo por parada.
- Unidades por hora.
- Número de cajas.
- Aperturas y cierres de caja.
- Faltantes y otras incidencias.
- Productividad por operario.
- Comparación entre operarios.
- Zonas con más pasos, errores o atascos.
- OUT bloqueadas o con recorrido anómalo.

Se propusieron además alertas para demasiado tiempo parado, velocidad baja, lectura fuera de ruta y cambios de Odoo durante el picking.

## 8. Cambios reales realizados en el módulo Odoo

Módulo local:

`C:\dev\OleadasKoroshi\odoo\modulos\koroshi_warehouse_map`

Cambios principales de la versión v35:

- El controlador dejó de devolver solamente la última `stock.move.line`.
- Ahora recupera todas las líneas de movimiento disponibles del picking.
- Cada línea incluye ubicación, referencia, EAN, cantidad solicitada, cantidad realizada y cantidad validada.
- Se agrupan las líneas por ubicación física para dibujar correctamente el recorrido.
- Se añadió fallback a eventos PDA cuando no existen líneas de picking suficientes.
- Se mantiene un límite de seguridad de 2.000 líneas por picking.
- Se corrigió la aplicación de snapshots completos de Odoo para evitar conservar personas o OUT demo antiguas.
- El iframe de la acción Odoo apunta a la versión cache-busteada v35.
- El manifiesto del módulo se actualizó a `13.0.0.1.20261029.35`.
- Se validó la sintaxis Python de `controllers/main.py` con `py_compile`.

Archivos relevantes:

- `odoo\modulos\koroshi_warehouse_map\controllers\main.py`
- `odoo\modulos\koroshi_warehouse_map\static\src\html\warehouse_planner_20261029_v1.html`
- `odoo\modulos\koroshi_warehouse_map\static\src\js\warehouse_map_action.js`
- `odoo\modulos\koroshi_warehouse_map\static\src\css\warehouse_map.css`
- `odoo\modulos\koroshi_warehouse_map\__manifest__.py`
- `odoo\modulos\koroshi_warehouse_map\README.md`

## 9. Paquetes y scripts preparados

Paquete final preparado:

`C:\dev\OleadasKoroshi\bin\versiones\20261029_1700_koroshi_warehouse_map_odoo13_v35.zip`

Script PowerShell de subida:

`C:\dev\OleadasKoroshi\bin\subir_koroshi_warehouse_map_v35.ps1`

Scripts de actualización disponibles:

- `bin\actualizar_koroshi_warehouse_map_2026-10-29_v3.sh`
- `bin\actualizar_koroshi_warehouse_map_2026-10-29_v4.sh`
- `bin\actualizar_koroshi_warehouse_map_2026-10-29_v5.sh`
- `bin\actualizar_koroshi_warehouse_map_2026-10-29_v6.sh`
- `bin\actualizar_koroshi_warehouse_map_2026-10-29_v7.sh`

El procedimiento acordado es siempre usar `check` antes de `install`. El instalador hace un único reinicio del servicio; no se debe hacer `stop/start` por separado porque detiene el sistema innecesariamente.

Comandos del servidor:

```bash
bash /home/it_nath_group/actualizar_koroshi_warehouse_map_2026-10-29_v7.sh check \
  /home/it_nath_group/20261029_1700_koroshi_warehouse_map_odoo13_v35.zip
```

Después de revisar el resultado:

```bash
sudo AUTO_CONFIRM=1 bash /home/it_nath_group/actualizar_koroshi_warehouse_map_2026-10-29_v7.sh install \
  /home/it_nath_group/20261029_1700_koroshi_warehouse_map_odoo13_v35.zip
```

Tras la actualización, abrir el mapa en Odoo y hacer `Ctrl + F5`.

## 10. Diagnóstico de la incidencia de las ubicaciones

Se observó en la web que algunas OUT aparecían con una sola ubicación aunque tenían muchas unidades. La causa detectada era el contrato de datos de la versión anterior: el endpoint devolvía solo la última `stock.move.line` con cantidad realizada.

Por eso algunas OUT mostraban `1 ubicación`, mientras que otras sí mostraban 8 o más. La corrección v35 devuelve todas las líneas disponibles.

Si después de instalar v35 alguna OUT sigue mostrando una sola ubicación, hay que comprobar la fuente de Odoo: puede que esa OUT tenga realmente una sola `stock.move.line` con ubicación, o que sus ubicaciones no estén mapeadas en el plano. No se debe inventar una ruta que Odoo no proporciona.

## 11. Problemas de servidor revisados

Durante el chat `nath.tuctuc.com` llegó a mostrar `ERR_CONNECTION_TIMED_OUT`, aunque Odoo funcionaba localmente en el servidor.

Comprobaciones realizadas:

- `nath-erp.service` estaba activo.
- `nginx.service` estaba activo.
- Nginx escuchaba en 80 y 443.
- Odoo escuchaba en 8069.
- `curl` local a `127.0.0.1:8069/web/login` devolvía HTTP 200.
- La configuración de Nginx pasaba `nginx -t`.
- DNS resolvía `nath.tuctuc.com` a `34.91.253.46`.
- El problema era externo al proceso Odoo: conectividad/firewall/red pública o una incidencia temporal del GCP, no un fallo de la aplicación.

Después el acceso web volvió a funcionar.

## 12. Historial de prototipos

Se generaron muchas versiones de prueba HTML v1–v33 para iterar sobre:

- Escala y numeración del plano.
- Numeración vertical y horizontal.
- Navegación del mapa.
- Paneles y filtros.
- Operativo frente a editable.
- OUT, zonas, simulación y heatmap.
- Recorridos por pasillos.
- Eventos de caja.

Los prototipos históricos están en:

`C:\dev\OleadasKoroshi\bin\versiones`

El prototipo de NAU-1 se conserva para impresión, pero el módulo actual debe seguir centrado en NAU-2.

## 13. Pendiente para una siguiente fase

Antes de considerar el sistema plenamente productivo todavía conviene implementar y validar:

1. Eventos reales de apertura/cierre de caja desde PDA u Odoo.
2. Lecturas PDA por línea con identificador único e idempotencia.
3. Sincronización offline real y recuperación tras desconexión.
4. Reconciliación si Odoo cambia cantidades, ubicaciones o reservas durante el picking.
5. Reproducción histórica completa de una OUT.
6. Alertas operativas automáticas.
7. Control de capacidad de cajas, muelles, zonas y personas.
8. Versionado del mapa y recuperación de versiones anteriores.
9. Permisos por rol: dirección, encargados y operarios.
10. Modo PDA simplificado para pantalla pequeña y uso con guantes.
11. Mapeo de las ubicaciones de muelle `MU`.
12. Prueba con datos reales de varias OUT de un día completo.

## 14. Criterio de aceptación de la próxima prueba

Una prueba se considera correcta cuando:

- La OUT se identifica por tienda.
- Las unidades coinciden con Odoo.
- Las ubicaciones visibles coinciden con las `stock.move.line` reales.
- El recorrido no atraviesa lineales.
- El primer punto es el primer artículo validado.
- La simulación muestra paradas y ubicaciones concretas.
- El tiempo real no empieza por la creación nocturna de la OUT.
- Las incidencias se distinguen de los datos estimados.
- Se puede volver a la vista general sin quedarse centrado en una persona.
- La interfaz sigue funcionando después de recargar.

## Estado final del chat

La versión local v35 quedó preparada y empaquetada. La interfaz web se comprobó con datos reales de Odoo y mejoró la visualización de lineales. La siguiente acción segura es conservar esta versión, validar el paquete en el servidor y no hacer más cambios grandes hasta comprobar varias OUT reales.

