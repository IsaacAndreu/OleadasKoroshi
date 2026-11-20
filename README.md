# OleadasKoroshi

Herramientas del almacén KOROSHI (Effective Logistics, compañía 8, NAU-2) sobre Odoo 13 Enterprise en
producción (nath.tuctuc.com). Las reglas de trabajo están en [CLAUDE.md](CLAUDE.md).

## Qué hay en el repositorio

| Ruta | Qué es |
|---|---|
| `odoo/modulos/` | Módulos Odoo propios (lo que se despliega). |
| `odoo/*.py` | Acciones de servidor y scripts sueltos (diagnóstico, simulaciones de oleadas, partición por zonas). |
| `odoo/referencia/` | Material de referencia. |
| `bin/` | `empaquetar.py` (etiqueta + ZIP), `comprobar.py` (trampas conocidas, lo llama empaquetar), `desplegar.sh` (instalar en el servidor), scripts antiguos por versión y copias de acciones de servidor. Los ZIP ya no van en git. |
| `bin/versiones/` | Versiones anteriores de acciones, crons y módulos (nunca se sobrescriben). |
| `PedidosMultiples/`, `App.config`, `*.csproj` | Programa de escritorio .NET de pedidos múltiples. |
| `PdaKoroshiAndroid/` | App Android de la PDA. |

## Mapa de módulos (`odoo/modulos`)

Versiones según el manifest del repo; la instalada en el servidor puede ir por delante.

### Común

| Módulo | Versión | Qué hace | Depende de (propios) |
|---|---|---|---|
| `koroshi_base` | 1.0.0 | Lo común (`comun.py` y `koroshi_base.comun` en JS): compañía 8, hora del almacén, días en UTC con el cambio de hora, matrícula CJ. Sin tablas. Los módulos pasan a usarlo uno a uno (el primero, zonas 1.4.0). | — |

### PDA y preparación

| Módulo | Versión | Qué hace | Depende de (propios) |
|---|---|---|---|
| `koroshi_operarios` | 2.14.0 | Cola de pedidos por operario en la PDA (tarjeta una vez, siguiente pedido solo); tiempo y uds por pedido. | base |
| `koroshi_preparacion` | 3.31.0 | Preparar la OUT dentro de Lecturas: leer, cerrar caja con la CJ y validar; agrupaciones Z-. | base, operarios, faltantes, consumibles |
| `koroshi_pda_app` | 1.1.0 | Lecturas como app instalable en la PDA. | base, operarios |
| `koroshi_caja_existente` | 1.4.0 | Leer una CJ ya hecha para meter uds en esa caja. | base |
| `koroshi_faltantes` | 1.5.0 | Pieza que no está: buscar otra ubicación, cambiar reserva, llevar a FALTANTE. | base, operarios |
| `koroshi_contenedores` | 1.4.0 | Mover contenedores KO_/TT_ a otra ubicación con sus prendas y reservas. | operarios |
| `koroshi_devoluciones` | 1.0.0 | Ubicar devoluciones en la PDA sin Excel: opción de manipulación, prendas y contenedor; informe por día, semana o mes. | base, operarios; sin instalar |
| `koroshi_buscador_stock` | 1.2.0 | Buscador de stock de la oficina (EAN, referencia, trozo, hueco, lineal o contenedor), solo lectura. | base, menu |
| `koroshi_actividades` | 1.3.0 | Registro de tiempo de manipulaciones con tarjeta en el portátil; inversa: matrícula por caja. | base, operarios |

### Planificación, seguimiento e informes

| Módulo | Versión | Qué hace | Depende de (propios) |
|---|---|---|---|
| `koroshi_zonas` | 1.4.0 | Partir pedidos de tienda por zonas buscando el máximo de cajas cerradas (motor v12f, cron en sombra). | kpi |
| `koroshi_monitor` | 1.36.0 | Pantalla en directo de las agrupaciones por zonas (Z-ddmm-D1..D5, ZX), Consulta de envíos, Producción por hora (uds y u/h de cada operario hora a hora) y «Siguiente tienda» por nº de pedido. | base, warehouse_map |
| `koroshi_sesiones` | 1.0.0 | Las sesiones con usuario no se borran nunca (Odoo 13 las borraba a los 7 días sin usarse); las sin usuario, a los 7 días en el auto-vacuum diario. Sin tablas. | — |
| `koroshi_kpi` | 1.9.0 | KPI diarios: uds, profundidad por SKU, peso, volumen, metros y segundos por prenda; previsión de cajas por volumen. | base |
| `koroshi_informe` | 1.2.0 | Correo diario, semanal y mensual de productividad. | base, operarios, kpi, preparacion, menu |
| `koroshi_menu` | 2.5.0 | App KOROSHI (Hoy, Faltantes, Personas, Almacén, KPI, Configuración); bandeja del encargado. | base, kpi, operarios, preparacion, zonas, warehouse_map, monitor, consumibles, faltantes, contenedores |
| `koroshi_warehouse_map` | 0.1.20261116.46 | Mapa editable y operativo de picking de NAU-2. | base |
| `koroshi_consumibles` | 1.4.0 | Control de cajas y materiales fuera del stock de prendas. | warehouse_map |
| `koroshi_delegacion` | 1.0.0 | Campo Delegación en los albaranes. | — |
| `koroshi_rendiment` | 1.1.0 | Botones Previsto y Stock de la ficha de producto rápidos. | — |
| `oriola_monitor` | 1.0.0 | Monitor de picking del almacén Oriola - Amposta (solo lee). | — |

### Transportistas e integraciones

| Módulo | Versión | Qué hace | Estado |
|---|---|---|---|
| `koroshi_xpo_bultos` | 1.3.0 | XPO: cajas distintas y 15 kg / 0,09 m3 por bulto. | base |
| `koroshi_s4t_envios` | 1.2.0 | Envía a S4T (`POST /shipments`) transportista, tracking, bultos, peso y volumen. | Instalado, en modo diagnóstico |
| `koroshi_s4t_traspasos` | 1.2.0 | Descarga de S4T devoluciones e-commerce y correcciones de traspasos. | base; sin instalar |
| `koroshi_s4t_pedidos` | 1.0.1 | Pedidos S4T grandes sin «could not serialize»: candado por feed, confirmar y reservar en jobs aparte. | Instalado 19/11; falta el cron 192 v7 |

Los dos de S4T usan host y `X-Api-Key` de `s4t.config` (módulo `api_s4t_batch_update_PROD`, de Effective).

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
   una versión sin su línea de historial o un `.py` que no compila. Avisa (sin parar) de los `<function>` con
   `noupdate`. Se puede pasar a mano en cualquier momento: `python bin/comprobar.py [modulo ...]`.
3. **En el servidor** (lo hace el responsable, no se automatiza), con los ZIP en `/home/it_nath_group` y
   `bin/desplegar.sh`:
   ```bash
   bash desplegar.sh check <modulo> <version> [<modulo> <version> ...]
   ```
   ```bash
   sudo AUTO_CONFIRM=1 bash desplegar.sh install <modulo> <version> [<modulo> <version> ...]
   ```
   Valida cada ZIP (íntegro, solo la carpeta del módulo, versión), que el servidor no tenga ya esa versión ni una más
   nueva y las dependencias; si algo falla no toca nada. Copia de seguridad en `/opt/nath-erp/copias_modulos`, copia y
   **un solo reinicio**. El reinicio corta Odoo ~1 minuto: fuera de horas y sin nadie validando en las PDA.
4. **En Odoo**: Aplicaciones → Actualizar la lista → Actualizar cada módulo, en el orden que dice el script.
