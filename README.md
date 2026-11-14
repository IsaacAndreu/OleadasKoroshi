# OleadasKoroshi

Herramientas del almacén KOROSHI (Effective Logistics, compañía 8, NAU-2) sobre Odoo 13 Enterprise en
producción (nath.tuctuc.com). Las reglas de trabajo están en [CLAUDE.md](CLAUDE.md).

## Qué hay en el repositorio

| Ruta | Qué es |
|---|---|
| `odoo/modulos/` | Módulos Odoo propios (lo que se despliega). |
| `odoo/*.py` | Acciones de servidor y scripts sueltos (diagnóstico, simulaciones de oleadas, partición por zonas). |
| `odoo/referencia/` | Material de referencia. |
| `bin/` | ZIP de cada versión de módulo, scripts de instalación con fecha y copias de acciones de servidor. |
| `bin/versiones/` | Versiones anteriores de acciones, crons y módulos (nunca se sobrescriben). |
| `PedidosMultiples/`, `App.config`, `*.csproj` | Programa de escritorio .NET de pedidos múltiples. |
| `PdaKoroshiAndroid/` | App Android de la PDA. |

## Mapa de módulos (`odoo/modulos`)

Versiones según el manifest del repo; la instalada en el servidor puede ir por delante.

### PDA y preparación

| Módulo | Versión | Qué hace | Depende de (propios) |
|---|---|---|---|
| `koroshi_operarios` | 2.11.1 | Cola de pedidos por operario en la PDA (tarjeta una vez, siguiente pedido solo); tiempo y uds por pedido. | — |
| `koroshi_preparacion` | 3.28.1 | Preparar la OUT dentro de Lecturas: leer, cerrar caja con la CJ y validar; agrupaciones Z-. | operarios, faltantes, consumibles |
| `koroshi_pda_app` | 1.0.0 | Lecturas como app instalable en la PDA. | operarios |
| `koroshi_caja_existente` | 1.3.0 | Leer una CJ ya hecha para meter uds en esa caja. | — |
| `koroshi_faltantes` | 1.4.1 | Pieza que no está: buscar otra ubicación, cambiar reserva, llevar a FALTANTE. | operarios |
| `koroshi_contenedores` | 1.3.0 | Mover contenedores KO_/TT_ a otra ubicación con sus prendas y reservas. | operarios |
| `koroshi_actividades` | 1.1.0 | Registro de tiempo de manipulaciones con tarjeta en el portátil; inversa: matrícula por caja. | operarios |

### Planificación, seguimiento e informes

| Módulo | Versión | Qué hace | Depende de (propios) |
|---|---|---|---|
| `koroshi_zonas` | 1.2.0 | Partir pedidos de tienda por zonas buscando el máximo de cajas cerradas (motor v12f, cron en sombra). | kpi |
| `koroshi_monitor` | 1.24.0 | Pantalla en directo de las agrupaciones por zonas (Z-ddmm-D1..D5, ZX). | warehouse_map |
| `koroshi_kpi` | 1.5.0 | KPI diarios: uds, profundidad por SKU, peso, volumen, metros y segundos por prenda. | — |
| `koroshi_informe` | 1.0.1 | Correo diario, semanal y mensual de productividad. | operarios, kpi, preparacion, menu |
| `koroshi_menu` | 2.1.0 | App KOROSHI (Hoy, Faltantes, Personas, Almacén, KPI, Configuración). | kpi, operarios, preparacion, zonas, warehouse_map, monitor, consumibles, faltantes, contenedores |
| `koroshi_warehouse_map` | 0.1.20261106.44 | Mapa editable y operativo de picking de NAU-2. | — |
| `koroshi_consumibles` | 1.3.0 | Control de cajas y materiales fuera del stock de prendas. | warehouse_map |
| `koroshi_delegacion` | 1.0.0 | Campo Delegación en los albaranes. | — |
| `koroshi_rendiment` | 1.1.0 | Botones Previsto y Stock de la ficha de producto rápidos. | — |
| `oriola_monitor` | 1.0.0 | Monitor de picking del almacén Oriola - Amposta (solo lee). | — |

### Transportistas e integraciones

| Módulo | Versión | Qué hace | Estado |
|---|---|---|---|
| `koroshi_xpo_bultos` | 1.1.0 | XPO: cajas distintas y 15 kg / 0,09 m3 por bulto. | — |
| `koroshi_s4t_envios` | 1.1.0 | Envía a S4T (`POST /shipments`) transportista, tracking, bultos, peso y volumen. | Instalado, en modo diagnóstico |
| `koroshi_s4t_traspasos` | 1.0.0 | Descarga de S4T devoluciones e-commerce y correcciones de traspasos. | Sin instalar |

Los dos de S4T usan host y `X-Api-Key` de `s4t.config` (módulo `api_s4t_batch_update_PROD`, de Effective).

## Cómo se despliega

1. **Versión nueva en el repo**: subir `version` en `__manifest__.py` y añadir la línea al historial del
   manifest. Antes, confirmar la `installed_version` real en el servidor.
2. **ZIP** en `bin/AAAAMMDD_<modulo>_vX.Y.Z.zip`, con la carpeta del módulo en la raíz del ZIP. Generarlo con
   Python (`zipfile`), no con `Compress-Archive`.
3. **Script** `bin/instalar_<modulo>_vX.Y.Z_AAAA-MM-DD.sh`, copiando el último como plantilla. Hace:
   - valida el ZIP (íntegro, con `__manifest__.py` y la versión esperada) antes de tocar nada,
   - comprueba el servicio `nath-erp` y la ruta de addons (`/opt/nath-erp/nath/enterprise-addons`),
   - copia de seguridad del módulo instalado en `/opt/nath-erp/copias_modulos`,
   - sustituye la carpeta, reinicia Odoo y comprueba que responde (si no, vuelve a la copia).
4. **En el servidor** (lo hace el responsable, no se automatiza), con el ZIP en `/home/it_nath_group`:
   ```bash
   bash instalar_<modulo>_vX.Y.Z_AAAA-MM-DD.sh check
   ```
   ```bash
   sudo AUTO_CONFIRM=1 bash instalar_<modulo>_vX.Y.Z_AAAA-MM-DD.sh install
   ```
   El reinicio corta Odoo ~1 minuto: fuera de horas y sin nadie validando en las PDA.
5. **En Odoo**: Aplicaciones → Actualizar el módulo.
