# OleadasKoroshi

Herramientas del almacén KOROSHI (Effective Logistics, compañía 8, NAU-2) sobre Odoo 13 Enterprise en
producción (nath.tuctuc.com). Las reglas de trabajo están en [CLAUDE.md](CLAUDE.md).

## Qué hay en el repositorio

| Ruta | Qué es |
|---|---|
| `odoo/modulos/` | Módulos Odoo propios (lo que se despliega). |
| `odoo/*.py` | Acciones de servidor y scripts sueltos (diagnóstico, simulaciones de oleadas, partición por zonas). |
| `odoo/referencia/` | Material de referencia. |
| `bin/` | `empaquetar.py` (etiqueta + ZIP), `comprobar.py` (trampas conocidas, lo llama empaquetar), `desplegar.sh` (instalar en el servidor), `tabla_modulos.py` (la tabla de módulos de este README), scripts antiguos por versión y copias de acciones de servidor. Los ZIP ya no van en git. |
| `bin/versiones/` | Versiones anteriores de acciones, crons y módulos (nunca se sobrescriben). |
| `PedidosMultiples/`, `App.config`, `*.csproj` | Programa de escritorio .NET de pedidos múltiples. |
| `PdaKoroshiAndroid/` | App Android de la PDA. |

## Mapa de módulos (`odoo/modulos`)

Versiones según el manifest del repo; la instalada en el servidor puede ir por delante o por detrás (lo que está
instalado y lo que falta, en [TABLERO.md](TABLERO.md)). La tabla la genera `python bin/tabla_modulos.py` a partir de
los manifest: no se edita a mano, se vuelve a pasar después de sacar versiones.

<!-- tabla-modulos -->
| Módulo | Versión (repo) | Qué hace (summary del manifest) | Depende de (propios) |
|---|---|---|---|
| `koroshi_actividades` | 1.8.3 | Manipulaciones: cada persona pasa su tarjeta en el portátil, elige qué hace y empieza, pausa o acaba. Tiempo por persona y actividad, sin contar uds. | base, operarios |
| `koroshi_agrupaciones_web` | 1.1.0 | Cortes de pedidos web a las 06:00 y 11:00: cancela los que no tienen todo el stock (aviso a Betty) y agrupa los reservados del todo en WEB_ddmmaa_NN de hasta 100 uds | base, menu |
| `koroshi_base` | 1.2.1 | Constantes y utilidades comunes de los modulos KOROSHI (compania, hora del almacen, matricula CJ) | — |
| `koroshi_buscador_stock` | 1.2.0 | Pantalla de la oficina para buscar stock por EAN, referencia, trozo, hueco, lineal o contenedor. Solo lectura. | base, menu |
| `koroshi_caja_existente` | 1.4.0 | PDA: leer la matricula CJ de una caja ya hecha (misma OUT u otra OUT del mismo pedido) mete las uds en esa caja | base |
| `koroshi_consumibles` | 1.4.0 | Control sencillo de cajas y materiales fuera del stock de prendas | warehouse_map |
| `koroshi_contenedores` | 1.15.0 | Escanear contenedores KO_/TT_ y la ubicación de destino: se mueven con sus prendas y reservas. | base, operarios, faltantes |
| `koroshi_delegacion` | 1.0.0 | Campo Delegación en los albaranes (sale de la etiqueta "Delegación ..." de la tienda) para filtrar y agrupar | — |
| `koroshi_devoluciones` | 1.3.0 | Ubicar devoluciones sin Excel (opción, prendas y contenedor; informe por día, semana o mes) y llegadas de paquetes | base, operarios |
| `koroshi_faltantes` | 1.10.0 | Pieza que no esta: buscar otra ubicacion con stock libre, cambiar la reserva y llevar la que falta a FALTANTE; revision diaria | base, operarios |
| `koroshi_informe` | 1.4.0 | Correo diario, semanal y mensual de productividad del almacén KOROSHI para la responsable | base, operarios, kpi, preparacion, menu, monitor |
| `koroshi_kpi` | 1.9.0 | KPI diarios del almacen KOROSHI: uds, profundidad por SKU, peso, volumen, metros y segundos por prenda | base |
| `koroshi_menu` | 2.7.0 | Aplicación KOROSHI propia (Hoy, Faltantes, Personas, Almacén, KPI, Configuración) e icono de Monitor picking | base, kpi, operarios, preparacion, zonas, warehouse_map, monitor, consumibles, faltantes, contenedores, actividades |
| `koroshi_monitor` | 1.43.0 | Pantalla en directo de como van las agrupaciones de picking por zonas (Z-ddmm-D1..D5, ZX) | base, warehouse_map |
| `koroshi_operarios` | 2.24.0 | Cola de pedidos por operario en la PDA: tarjeta una vez, el siguiente pedido se abre solo; tiempo y uds por persona | base |
| `koroshi_pda_app` | 1.2.0 | Instala Lecturas (PDA) como una app: icono en la PDA y pantalla sin barra del navegador | base, operarios |
| `koroshi_prenda_suelo` | 1.1.0 | PDA: se lee una prenda encontrada en el suelo y dice a dónde va: faltante, compañero que la está preparando (dónde está y hacia dónde va), su hueco o la mesa de los jefes. | base, operarios, preparacion, faltantes |
| `koroshi_preparacion` | 3.35.0 | Preparar la OUT dentro de Lecturas (PDA): leer, cerrar caja con la CJ y validar sin salir a la app de código de barras | base, operarios, faltantes, consumibles |
| `koroshi_recepcion` | 1.0.1 | Recibir un contenedor marítimo caja a caja en la PDA o la tablet: caja KO_, palé A/B, prenda y cantidad, a ciegas; comparar con las IN y validarlas. | base, menu, ubicaciones |
| `koroshi_recuentos` | 1.2.0 | PDA: una referencia con todas sus tallas y colores, dónde está y cuánto dice Odoo, y su recuento leído a ciegas con registro de cada lectura (inventario dinámico). | base, operarios |
| `koroshi_rendiment` | 1.1.0 | Botones Previsto y Stock de la ficha de producto rapidos (Odoo 13 + PostgreSQL 11) | — |
| `koroshi_s4t_envios` | 1.4.0 | Envia a S4T (POST /shipments) el transportista, tracking, bultos, peso y volumen de cada pedido | xpo_bultos |
| `koroshi_s4t_pedidos` | 1.2.0 | Los pedidos S4T grandes (Zalando) entran sin «could not serialize»: crear, confirmar y reservar en jobs aparte, y nunca dos copias del mismo job a la vez | base |
| `koroshi_s4t_sync` | 1.0.0 | Deja sincronizar con S4T los pedidos con backorders canceladas (el resto de OUT hechas) | — |
| `koroshi_s4t_traspasos` | 1.4.0 | Descarga de S4T las devoluciones e-commerce y las correcciones de traspasos y las guarda en Odoo | base |
| `koroshi_sesiones` | 1.0.0 | Las sesiones con usuario no se borran nunca (Odoo 13 las borraba a los 7 dias sin usarse) | — |
| `koroshi_ubicaciones` | 1.0.0 | Un botón crea los contenedores KO_/TT_ o los huecos de un lineal y abre sus etiquetas 4x6. Otro vuelve a imprimirlas. | base, menu |
| `koroshi_warehouse_map` | 0.1.20261116.46 | Mapa editable y mapa operativo de picking para NAU-2 | base |
| `koroshi_xpo_bultos` | 1.3.0 | XPO: cajas distintas y 15 kg / 0,09 m3 por bulto en cada expedicion | base |
| `koroshi_zonas` | 1.7.0 | Partir los pedidos de tienda por zonas de picking buscando el maximo de cajas cerradas | kpi, base |
| `oriola_monitor` | 1.0.0 | Pantalla en directo de como va el picking del almacen Oriola - Amposta (solo lee) | — |
| `tuctuc_rendimiento` | 1.0.0 | Previsto, botón Stock y búsquedas más rápidos en odoo.tuctuc.com (Odoo 13 + PostgreSQL 11) | — |
<!-- /tabla-modulos -->

Los módulos de S4T usan host y `X-Api-Key` de `s4t.config` (módulo `api_s4t_batch_update_PROD`, de Effective).

## Cómo se despliega

Desde el 14/11/2026 (auditoría 13/11, fase 6): una etiqueta por versión, el ZIP sale de la etiqueta y un solo script
de instalación. Los scripts `bin/instalar_*` anteriores se quedan como historia.

1. **Versión nueva en el repo**: subir `version` en `__manifest__.py` y añadir la línea al historial del
   manifest. Antes, confirmar la `installed_version` real en el servidor. Commit.
2. **Etiqueta y ZIP**:
   ```bash
   python bin/empaquetar.py <modulo>
   ```
   Crea la etiqueta `<modulo>/vX.Y.Z` (anotada; **nunca se mueve**) y `bin/AAAAMMDD_<modulo>_vX.Y.Z.zip` con
   `git archive` (todo en LF). Para si el módulo tiene cambios sin commitear, si la etiqueta ya existe con otro
   contenido o si ya hay un ZIP de esa versión distinto: hay que sacar una versión nueva. La etiqueta necesita usuario
   de git (`GIT_COMMITTER_NAME` / `GIT_COMMITTER_EMAIL`).
   Antes de etiquetar pasa `bin/comprobar.py` (desde el 17/11/2026) y para si encuentra: `aria-hidden="true"`,
   `display_notification`, `report_name` sin punto, un campo nuevo en `stock.picking`, `stock.picking.type` o
   `stock.move.line` que no esté en `bin/campos_compartidos_aprobados.txt`, un módulo cambiado sin subir la versión,
   una versión sin su línea de historial, un `.py` que no compila, un campo que acaba en coma (E9) o una constante de
   `koroshi_base` copiada (E10: compañía, zona horaria o matrícula CJ; las que ya estaban, en
   `bin/constantes_pendientes.txt`, solo avisan). Avisa (sin parar) de los `<function>` con `noupdate`, de las rutas
   `auth='user'` que no comprueban ningún grupo y de los `except Exception` que no dejan rastro. Se puede pasar a mano en cualquier momento: `python bin/comprobar.py [modulo ...]`.
3. **En el servidor** (lo hace el responsable, no se automatiza), con los ZIP en `/home/it_nath_group` y
   `bin/desplegar.sh`:
   ```bash
   bash desplegar.sh check <modulo> <version> [<modulo> <version> ...]
   ```
   ```bash
   sudo AUTO_CONFIRM=1 bash desplegar.sh install <modulo> <version> [<modulo> <version> ...]
   ```
   Valida cada ZIP (íntegro, solo la carpeta del módulo, versión), que el servidor no tenga ya esa versión ni una más
   nueva y las dependencias; si algo falla no toca nada. Avisa también (desde el 23/11) de los módulos que el `-u` de
   cada uno actualiza a la vez, de un módulo nuevo del que depende otro de la misma tanda (instalarlo antes, en otra
   tanda) y de si es horario del almacén (06:00-17:00). Copia de seguridad en `/opt/nath-erp/copias_modulos`, copia y
   **un solo reinicio**. El reinicio corta Odoo ~1 minuto: fuera de horas y sin nadie validando en las PDA.
4. **En Odoo**: Aplicaciones → Actualizar la lista → Actualizar cada módulo, en el orden que dice el script.
