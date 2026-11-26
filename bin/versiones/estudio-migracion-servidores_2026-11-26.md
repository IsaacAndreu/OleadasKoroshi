# Estudio: sacar los servidores de Nath/KOROSHI de Google Cloud (26/11/2026)

**Solo estudio y plan.** No se ha conectado nada al servidor, no se ha creado ninguna cuenta y no se ha contratado
nada. Todo sale del repositorio, de la memoria del proyecto y de páginas públicas de precios (fuentes al final, con
fecha). Lo que no se puede saber desde aquí está en **Preguntas para Isaac** (apartado 5), con el comando de solo
lectura para responderlo.

## 0. Resumen para Isaac

> **Actualizado el 26/11 (~10:30) con los datos reales de la consola de Google Cloud** (mirada en solo lectura con
> permiso de Isaac; apartado 1.0). Cambian las cifras y la recomendación de 4.1.

- **Hoy GCP cuesta unos 4.260 €/mes** (previsión de noviembre): **~3.660 € tuctuc** y **~980 € KOROSHI**. Cloud SQL es
  el 80 %.
- **El 41 % de la factura (~1.760 €/mes) es el «soporte extendido» de PostgreSQL 11.** Google cobra un recargo por
  seguir en una versión sin soporte. Se elimina **subiendo PostgreSQL a 15 o 16**, se migre o no.
- **Dos caminos**, y no son excluyentes:
  1. **Quedarse en GCP y subir PostgreSQL** (más limpiar lo que sobra): de ~4.260 a **~2.000-2.400 €/mes**. Menos
     riesgo: no cambia ni la IP ni el proveedor.
  2. **Migrar a OVHcloud** (con PostgreSQL nuevo): **~1.400-1.900 €/mes** las dos plataformas. Ahorro de **~2.400-2.900
     €/mes** (55-65 %), con más trabajo y más riesgo.
- **Hay más de lo que parece.** En el proyecto `nath-269506` hay, como mínimo, **dos Odoo y dos bases de datos
  gestionadas (Cloud SQL)**: el de KOROSHI (`nath.tuctuc.com`) y el de tuctuc (`odoo.tuctuc.com`). La base de datos
  **no está en la VM**: es Cloud SQL, y probablemente es lo que más se paga.
- **Recomendación: OVHcloud Public Cloud** (Francia), con una VM para Odoo y otra para PostgreSQL en la misma red
  privada (vRack), por cada Odoo. Alternativa: **Scaleway** (París) si se quiere la base de datos gestionada, como
  ahora. Hetzner es lo más barato por máquina, pero ha subido precios dos veces en 2026 y es alemán.
- **Ahorro: ver 4.1** (con la factura real). Lo que más pesa es tuctuc (~3.660 €/mes), no KOROSHI (~980 €/mes).
- **Primero KOROSHI o primero tuctuc, nunca los dos a la vez.** Propuesta: **KOROSHI primero** (base de 62 GB, más
  rápida de copiar, y sirve de ensayo); tuctuc después (220 GB, alta disponibilidad, TPV de tiendas), que es donde
  está el dinero.
- **Lo más urgente, se migre o no: subir PostgreSQL 11 → 15/16.** Son ~1.760 €/mes que se van en el recargo.
- **Corte: de 2 a 4 h, de madrugada en domingo**, con vuelta atrás preparada (GCP sigue encendido y sin tocar hasta
  que se dé por bueno).
- **Tres cosas que pueden romperse y no se ven a simple vista**:
  1. El programa de escritorio **PedidosMultiples** se conecta **directo a las IP de Cloud SQL**
     (`PedidosMultiples/ConnectionSQL.cs:24` y `:28`). Al mover la base, hay que cambiarlas y sacar versión del
     programa; si no, deja de funcionar el lunes.
  2. **Correo saliente y listas blancas por IP** (S4T, transportistas, SPF del dominio). Scaleway y Hetzner bloquean
     el puerto 25 por defecto.
  3. **La copia de prueba puede hablar con S4T, XPO o GLS como si fuera producción.** Hay que «neutralizarla» antes de
     arrancarla (apartado 3.3).

## 1. Inventario de lo que hay ahora

### 1.0 Datos reales de la consola de Google Cloud (26/11/2026, solo lectura)

Mirado en la consola: VM, discos, snapshots, IP, Cloud SQL, redes autorizadas, firewall, buckets, DNS y facturación.
No se ha pulsado nada que cambie algo ni se ha entrado por SSH (el SSH del navegador añade claves a la VM, y eso ya es
un cambio).

**Máquinas virtuales**

| VM | Zona | Tipo | vCPU / RAM | Disco | IP externa (fija) | Creada |
|---|---|---|---|---|---|---|
| `nath-erp-prod` (KOROSHI) | europe-west4-b | `n2d-custom-8-18432` (AMD Milan) | 8 / 18 GB | 300 GB SSD (`nath-erp-prod-cmek`) | **34.91.253.46** | 26/06/2020 |
| `tuctuc-erp-prod-eu-w1b` | europe-west1-b | `n2-custom-14-49152` (Intel Cascade Lake) | 14 / 48 GB | 300 GB SSD (`tuctuc-erp-prod-eu-cmek`) | **35.241.160.100** | 01/10/2020 |

Ninguna de las dos tiene copias programadas de disco (sin snapshot schedule ni backup plan).

**Cloud SQL** (las dos con PostgreSQL 11.22, edición Enterprise, IP pública, sin IP privada)

| Instancia | Región | vCPU / RAM | Disco (usado / total) | Alta disponibilidad | Copias | IP | IP de salida |
|---|---|---|---|---|---|---|---|
| `nath-erp-production` | europe-west4-b | 8 / 24 GB | **62 / 100 GB**, sin crecimiento automático | **No** (zonal) | Diarias (~20:40-21:00 UTC+1); **sin recuperación a un momento dado** | 34.90.144.125 | 34.91.252.159 |
| `tuctuc-erp-prod-eu` | europe-west1-d | 16 / 104 GB | **220 / 390 GB**, con crecimiento automático | **Sí** (regional) | Diarias + recuperación a un momento dado | 104.199.5.207 | — |

Avisos de la propia consola: «versión antigua que necesita soporte extendido» y «permite conexiones directas sin
cifrar» en las dos.

**Quién entra a las bases (redes autorizadas)**, las mismas en las dos instancias:

| Nombre en Cloud SQL | IP | Qué es (a confirmar) |
|---|---|---|
| OdooServer / Odoo-Server | 34.91.253.46 / 35.241.160.100 | La VM de cada Odoo |
| Oriola1 | 46.24.177.93 | Oficina (la de `App.config`, PedidosMultiples) |
| Oriola2 | 80.103.98.47 | Otra conexión de Oriola |
| Oriola3 / OriolaMagatzem2 | 84.78.198.137 | Almacén |
| Oriola-Radio | 46.24.5.48 | Enlace radio |
| **Ionos** | 82.223.30.89 | **Un servidor en Ionos que lee la base directamente** (¿web, integración?): P16 |
| **Looker1 / Looker2** | 142.251.74.0/23, 74.125.0.0/16 | **Looker Studio**: hay informes que leen la base directamente: P17 |

Todo esto hay que **reproducirlo en el servidor nuevo** (o cambiarlo en cada cliente) el día del corte.

**Firewall (red `default`)**

- Entrada abierta a todo Internet: 80, 443, **8069-8071** (Odoo directo, sin nginx), **22 (SSH)**, **3389 (RDP)**,
  **5432** (etiqueta `postgres`, sin uso), ICMP. Lo de 8069, 3389 y 5432 sobra; en el servidor nuevo, solo 80/443 y
  SSH limitado.
- **Salida restringida** (`selective-egress` + `block-unnecessary-egress`): solo tcp 25, 53, 80, 443, 465, 587,
  **3232**, 5432 y udp 53, 123. Todo lo demás se bloquea (480 bloqueos hoy). El **3232** lo usa alguna integración
  (P18). El puerto 25 de salida está permitido en el proyecto.

**Otras cosas del proyecto**

| Qué | Detalle | Coste aprox. | Comentario |
|---|---|---|---|
| Discos sueltos | `nath-erp-prod-w4b` y `tuctuc-erp-prod-eu-wlb`, 300 GB SSD cada uno, **sin VM** | ~55-65 €/mes | Copias antiguas: sobran (confirmar antes) |
| Snapshots | `nath-prova-snap` (57,6 GB, 07/10/2026) y `snapshot-tucutc-prod-1-oct-20` (4,8 GB, 2020) | pocos € | |
| IP fijas sin usar | `nath-tes-app-1` 34.87.30.109 y `nath-tuctuc-test` 34.126.81.151 (Singapur) | ~13 €/mes | Sobran |
| Buckets | `nath-erp-dev-data` (Asia, Nearline, 2021), `nath-erp-dev-data-eu` (Bélgica, Nearline, 2025), **`nath-stock-feed-q7m4x2`** (Bélgica, **público**, creado el 19/11/2026) | ~47 €/mes (sobre todo Asia, ~2,6 TB) | El público es un feed de stock: ¿quién lo lee? (P19) |
| DNS | Sin zonas en Cloud DNS | — | El DNS de `tuctuc.com` está fuera de GCP (P8) |
| Facturación | Cuenta **Prime Collections S.L.**; el proyecto pasó a esta cuenta a finales de octubre (factura de octubre: 440 €, solo unos días) | — | Los meses anteriores están en otra cuenta (P20) |

**Facturación de noviembre (1-26/11: 4.141,67 €; previsión del mes: 4.263,63 €)**

| Servicio | 1-26/11 |
|---|---|
| Cloud SQL | 3.421,20 € |
| Compute Engine | 668,72 € (con −90,94 € de descuentos por uso continuado) |
| Cloud Storage | 47,52 € |
| Red y Logging | 4,24 € |

Por plataforma (SKU de noviembre, llevado a 30 días):

| | tuctuc (Bélgica) | KOROSHI (Países Bajos) |
|---|---|---|
| Cloud SQL: **soporte extendido PostgreSQL 11** | 1.194,98 € → **~1.380 €/mes** | 328,62 € → **~380 €/mes** |
| Cloud SQL: vCPU + RAM + disco | 1.579,88 € → ~1.820 €/mes | 306,18 € → ~355 €/mes |
| VM (CPU + RAM, con descuento) | 336,10 € → ~390 €/mes | 149,25 € → ~170 €/mes |
| Discos SSD de VM (incluidos los sueltos) | 59,76 € → ~70 €/mes | 65,74 € → ~75 €/mes |
| **Total aprox.** | **~3.660 €/mes** | **~980 €/mes** |

Más ~65 €/mes comunes (buckets de Asia, IP de Singapur, tráfico).

### 1.1 Lo que se sabe desde el repo y la memoria

| Pieza | Qué se sabe | Dónde se ha visto |
|---|---|---|
| **VM Odoo KOROSHI** | `nath-erp-prod`, proyecto `nath-269506`, zona `europe-west4-b` (Países Bajos). Servicio systemd `nath-erp`. Odoo 13 Enterprise **anterior** a la rama 13.0 actual de GitHub (código propio del servidor). | encargo; `odoo/modulos/koroshi_rendiment/README.md:16-18` |
| Rutas | Addons: `/opt/nath-erp/nath/enterprise-addons` (módulos KOROSHI), `/opt/nath-erp/nath/custom_addons` (módulos de Effective, p. ej. `api_s4t_batch_update_PROD`), núcleo en `/opt/nath-erp/odoo13/...`. Conf: `/opt/nath-erp/nath-erp.conf`. Log: `/var/log/odoo/nath-erp.log`. Copias de módulos: `/opt/nath-erp/copias_modulos`. ZIP de subida: `/home/it_nath_group`. | `bin/desplegar.sh:35-38`; memoria |
| Configuración Odoo | `workers = 16`, `limit_time_real = 9999`; `[queue_job] channels = root:3,root.s4t_sync:1` (línea 66 del conf). | `koroshi_rendiment/README.md:21`; memoria (03/11) |
| Sesiones | En disco, `/home/ubuntu/.local/share/Odoo/sessions` (~17.000 ficheros). **Hay que copiarlas** o todas las PDA salen de la sesión. | memoria (17/11) |
| **Base de datos KOROSHI** | **Cloud SQL, PostgreSQL 11.22**, IP pública `34.90.144.125`, base `NATH_PRODUCTION`. No hay `postgres` local. Volumen orientativo: `stock_move` 3,9 M filas, `stock_move_line` 3,7 M, `stock_quant` 1,46 M, `stock_location` 527 k. | `koroshi_rendiment/README.md:18-23`; memoria |
| **nginx** | 1.10.3 (muy antiguo: sugiere Ubuntu 16.04/Debian 9), `listen 443 ssl http2`, más `/etc/nginx/conf.d/koroshi_http2.conf` (`http2_max_field_size 16k; http2_max_header_size 64k`). **Sin ese fichero, Odoo sale en blanco.** | memoria (17/11) |
| Certificado TLS | No se sabe quién lo emite (¿Let's Encrypt/certbot?). | P8 |
| **Cola `queue_job`** | Canal `root.s4t_sync` a capacidad 1. Tras cualquier reinicio, un job que quedó en `started` bloquea el canal: reencolar. | memoria (03/11) |
| **Crons que importan** (hora del almacén) | Zonas a las **04:50** (`koroshi_zonas`); cortes de agrupaciones web **06:00 y 12:00**; cron **186** sync S4T; cron **192** alerta cola S4T cada 15 min; informes por correo. | memoria; TABLERO.md |
| Integraciones | **S4T** (`PUT /orders/batch-update`, envíos y traspasos; la clave está en `s4t.config` de la BD), **XPO** y **GLS** (etiquetas), marketplaces y transportistas varios en módulos de terceros (Veepee, El Corte Inglés, Sending, CEX, Nacex…). | memoria; URLs del repo |
| Correo saliente | Servidor de correo de Odoo llamado `NATH` (informes, avisos de cola S4T, cancelados a Betty). Proveedor SMTP desconocido. | `koroshi_informe/README.md:135` |
| **Impresión** | `koroshi_impresion`: cola en Odoo + **agente en el portátil de Expediciones** que entra por `https://nath.tuctuc.com` (`bin/agente_impresion/config.ejemplo.ini:5`). Sale por la URL: no cambia si se mantiene el nombre. Los PDF dependen de **wkhtmltopdf** del servidor. | README; `bin/agente_impresion/` |
| **PDA** | Chrome/PWA (`koroshi_pda_app`) contra `https://nath.tuctuc.com` por wifi, con service worker. Sale por la URL. | `odoo/modulos/koroshi_pda_app/README.md:14` |
| **PedidosMultiples** (escritorio .NET) | Se conecta **directamente a PostgreSQL**: `Host=34.90.144.125` (NATH) y `Host=104.199.5.207` (TUCTUC). Las IP públicas de la oficina (`public_ip` `46.24.177.93` en `App.config:28`) deben estar autorizadas en Cloud SQL. Actualizador en la red local (`192.168.0.50`). | `PedidosMultiples/ConnectionSQL.cs:24,28` (no se copian credenciales) |
| Programas externos | Programa de redistribución (XML-RPC con «Departament IT») contra `nath.tuctuc.com`. Sale por la URL. | memoria (23/11) |
| **Segundo Odoo: tuctuc** | VM `tuctuc-erp-prod-eu-w1b`, zona `europe-west1-b` (Bélgica), servicio `tuctuc-erp`, base `TUCTUC_PRODUCTION` en **Cloud SQL PostgreSQL 11.22** (`104.199.5.207`), `workers = 29`. `stock_quant` 6,8 M filas (844 MB), ~760.000 ubicaciones. TPV y tiendas. | `bin/versiones/20261124_traspaso_rendimiento_odoo-tuctuc.md:13-19,231`; `tuctuc_rendimiento/README.md:17` |
| Fuera de GCP (no cambia) | NAS `nathserver.synology.me`, SQL Server local `192.168.0.3`, actualizador `192.168.0.50`. | `PedidosMultiples/InitialForm.cs` |

### 1.2 Lo que se deduce (a confirmar)

- Tamaños y costes: **ya confirmados en 1.0** (KOROSHI 8 vCPU/18 GB + base 8 vCPU/24 GB; tuctuc 14 vCPU/48 GB + base
  16 vCPU/104 GB con alta disponibilidad). El pico de CPU de las dos bases en las últimas 24 h ha sido del ~86 %: no
  conviene quedarse cortos de CPU en la base.
- **PostgreSQL 11 está sin soporte desde noviembre de 2023**, y Google lo cobra como «soporte extendido» (~1.760 €/mes
  entre las dos bases). Ningún proveedor gestionado lo ofrece ya: migrar es también **subir de versión de
  PostgreSQL** (o montarlo a mano en una VM). Ver riesgo R2.
- El sistema operativo de la VM parece muy antiguo (por la versión de nginx). La VM nueva **no** puede ser una copia
  exacta del sistema: hay que reproducir el entorno de Python de Odoo 13 (versión de Python, `pip freeze`,
  wkhtmltopdf 0.12.5 «with patched qt»).

## 2. Comparativa de proveedores

Precios **sin IVA**, en euros/mes, consultados el **26/11/2026**. Las cifras de terceros se han contrastado entre
sí; antes de contratar, confirmarlas en la calculadora de cada proveedor.

### 2.1 Máquinas equivalentes

Equivalente buscado: **8 vCPU / 32 GB** para Odoo (como `n2-standard-8`) y otra igual para PostgreSQL.

| Proveedor | Máquina | vCPU / RAM | €/mes | Notas |
|---|---|---|---|---|
| **GCP** (hoy, referencia) | `n2-standard-8`, europe-west4 | 8 / 32 | **~230 €** (~250 $) bajo demanda; ~180 € con compromiso de 1 año | S8, S9. Más Cloud SQL aparte. |
| **OVHcloud** Public Cloud | `b3-32` | 8 / 32, 200 GB local | **173 €** (antes 149 €; subida del 01/10/2026) | S1, S2. Desde el 01/10 el **disco local y la IPv4 se cobran aparte** (S3). Savings Plan: −15 % a 12 meses, −30 % a 36. |
| | `b3-64` | 16 / 64, 400 GB | **343 €** | S2. Para Odoo + PostgreSQL en una sola máquina. |
| **Scaleway** | `POP2-8C-32G` (París) | 8 / 32 | **~212 €** (0,29 €/h) | S4, S5. |
| | Base de datos gestionada `DB-POP2-8C-32G` | 8 / 32 | **~415 €** (0,5684 €/h, la columna más alta; las otras dos columnas de la página, 0,31 y 0,25 €/h, no están rotuladas en la fuente: confirmar) | S6. PostgreSQL gestionado, con copias. |
| **Hetzner** Cloud | `CCX33` (dedicada) | 8 / 32, 240 GB | **~138 €** (antes 62 €; subida de junio de 2026) | S7, S11. |
| | `CCX43` | 16 / 64, 360 GB | **~276 €** | S7. |

### 2.2 Disco, copias, IP, red y SLA

| | **OVHcloud** | **Scaleway** | **Hetzner** | **GCP** (hoy) |
|---|---|---|---|---|
| Disco de bloque | Block Storage aparte; disco local desde el 01/10 a ~0,000172 $/GB·h (≈0,13 $/GB·mes) (S3) | Block 5K 0,0993 €/GB·mes; 15K 0,1489 €/GB·mes (S6) | Volúmenes 0,0572 €/GB·mes (S12) | PD SSD/balanced |
| Snapshots y copias | Snapshots y copias automáticas de instancia de pago por GB (precio no confirmado aquí) | Snapshots/copias 0,03 €/GB·mes (S6) | Copias automáticas = +20 % del precio de la máquina (7 copias); snapshots ~0,014 €/GB·mes (S12) | Cloud SQL: copias automáticas incluidas |
| IP fija | IPv4 pública aparte desde el 01/10 (S3); IP adicional («Additional IP»), precio no confirmado | IP flexible | IPv4 primaria 0,50 €/mes; flotante ~3 €/mes (S12) | IP estática |
| Red privada | **vRack** entre máquinas (sin confirmar aquí si se cobra) | VPC privada | Redes privadas | VPC |
| Salida de datos | Sin coste de tráfico | Incluida con límites | 20 TB/mes incluidos | De pago |
| Centros de datos UE | Francia (Gravelines, Roubaix, Estrasburgo, París), Alemania, Polonia, **Madrid** (local zone) | París, Ámsterdam, Varsovia | Alemania (Núremberg, Falkenstein), Finlandia | Países Bajos (west4), Bélgica (west1), **Madrid** (southwest1) |
| Latencia estimada desde Barcelona | París/Roubaix ~20-25 ms; Madrid ~10 ms | París ~20 ms | Alemania ~30-40 ms | Países Bajos ~35 ms (lo de hoy) |
| SLA | Instancias Public Cloud: SLA publicado (no confirmado aquí; confirmar % y compensación) | SLA por gama de instancia (confirmar) | **99,9 %** mensual por servidor desde el 16/03/2026, compensación solo en crédito (S12) | 99,9 % VM / 99,95 % Cloud SQL con HA |
| Soporte | Soporte en castellano (oficina en España); niveles de pago | Francés/inglés; niveles de pago | Inglés/alemán, básico | De pago |
| Correo saliente (puerto 25) | Revisar en la cuenta | **Bloqueado por defecto**: pedir que lo abran | **Bloqueado por defecto** (25 y 465) | Bloqueado (25) |
| RGPD | Empresa francesa, datos en la UE | Empresa francesa (grupo Iliad) | Empresa alemana | Empresa de EE. UU. (CLOUD Act) |

Las latencias son **estimaciones**. Antes de decidir, medirlas desde el almacén (apartado 5, P12). Desde Barcelona,
cualquiera de ellas es igual o mejor que la de hoy; para la PDA lo que importa es que **Odoo y PostgreSQL estén en el
mismo centro de datos** (hoy, VM y Cloud SQL lo están).

### 2.3 Opciones de montaje (por cada Odoo)

| Opción | Qué es | €/mes aprox. (KOROSHI) | Pros | Contras |
|---|---|---|---|---|
| **A. OVH, dos VM** (recomendada) | `b3-32` Odoo + `b3-32` PostgreSQL en vRack | ~346 € + discos/IP ≈ **380-420 €**; con Savings Plan 12 m ≈ **330-370 €** | Francés, soporte en castellano, sin coste de tráfico, se puede elegir la versión de PostgreSQL | Las copias de PostgreSQL las gestiona Soporte (pgBackRest o `pg_dump` nocturno a Object Storage) |
| **B. Scaleway, BD gestionada** | `POP2-8C-32G` Odoo + `DB-POP2-8C-32G` gestionada | ~212 + ~415 ≈ **630 €** (menos si la tarifa de 0,31 €/h es la que corresponde) | Como hoy: copias y parches de la base los hace el proveedor | Más caro; PostgreSQL gestionado solo en versiones recientes |
| **C. Una sola máquina** | Odoo + PostgreSQL juntos (`b3-64` OVH o `CCX43` Hetzner) | **276-380 €** | Lo más barato y sin latencia entre Odoo y la base | Un fallo para todo; un reinicio de la máquina para las dos cosas |
| **D. Hetzner, dos VM** | `CCX33` + `CCX33` | ~280 € + volúmenes + copias ≈ **330 €** | Lo más barato con dos máquinas | Subidas de precio de hasta +170 % en 2026; alemán; soporte básico |

## 3. Plan de migración sin parar el almacén

Principio: **producción en GCP no se toca hasta el corte**, y después sigue encendida y sin tocar unos días como
vuelta atrás. Un Odoo cada vez (primero uno, luego el otro, con al menos una semana entre medias).

### 3.1 Antes (2-3 semanas; nada de esto afecta al almacén)

1. Isaac responde las preguntas del apartado 5 y elige proveedor y opción.
2. Contratar (lo hace Isaac) y montar las dos VM en la red privada; abrir el puerto de PostgreSQL solo a la VM de
   Odoo, a la IP de la oficina (`46.24.177.93`, para PedidosMultiples) y a quien diga P10.
3. Reproducir el entorno de Odoo: **misma copia del código del servidor** (núcleo de `/opt/nath-erp`, porque no es
   el de GitHub), `enterprise-addons`, `custom_addons`, mismo Python y `pip freeze`, **wkhtmltopdf 0.12.5 con qt
   parcheado**, mismo `nath-erp.conf` (workers, `queue_job` con `root.s4t_sync:1`, límites), nginx con
   `koroshi_http2.conf`. Mejor nginx reciente que 1.10.
4. Elegir la versión de PostgreSQL (riesgo R2): ensayar con **PostgreSQL 15** (soporte hasta noviembre de 2027) y,
   si algo falla con Odoo 13, quedarse en **11** en la VM propia (opción A) mientras se arregla.
5. Copiar el filestore con `rsync` (en caliente, se puede repetir).
6. Primera copia de la base: `pg_dump -Fd -j 4` desde la VM de GCP contra Cloud SQL (solo lectura) y `pg_restore -j
   8` en el servidor nuevo. **Medir cuánto tarda**: ese tiempo decide el corte.
7. **Neutralizar la copia** antes de arrancar Odoo (apartado 3.3).

### 3.2 Pruebas en el servidor nuevo (sin tocar producción)

Entrar por un nombre de prueba (p. ej. `nuevo-nath.tuctuc.com`, o por IP con el fichero `hosts` en un PC):

- Abrir Odoo, el monitor, Lecturas y preparación en **una PDA** contra la copia.
- Generar las etiquetas: zona, CJ, GLS/XPO (PDF de wkhtmltopdf igual que en producción), con el agente de
  impresión de prueba apuntando a la URL de prueba.
- Lanzar a mano las acciones pesadas (Previsto, Stock, zonas en modo diagnóstico) y comparar tiempos con producción.
- PedidosMultiples contra la base nueva (versión de prueba del programa, no la de los PC).
- Instalar un módulo con `desplegar.sh check` para comprobar que las rutas cuadran.

### 3.3 Neutralizar la copia de prueba (imprescindible)

Antes de arrancar Odoo sobre la copia, en la base restaurada (lo hace Soporte, con la lista revisada por Isaac):

- Desactivar **todos los crons** (`ir_cron.active = false`) y el `queue_job` (`[queue_job]` sin canales o
  `server_wide_modules` sin `queue_job`).
- Desactivar los **servidores de correo saliente** y entrante.
- Vaciar o apuntar a pruebas la configuración de **S4T** (`s4t.config`), **XPO**, **GLS**, marketplaces y
  transportistas.
- Cambiar `web.base.url` a la URL de prueba.
- No registrar la copia en Odoo SA como otra base (desactivar el cron de «publisher warranty» y no tocar el
  `database.uuid`; ver P9).

**Si no se hace, la copia puede mandar pedidos a S4T, crear etiquetas reales o enviar correos a clientes.**

### 3.4 Corte (domingo de madrugada, 2-4 h)

Ventana propuesta: **domingo de 01:00 a 05:00**, antes del cron de zonas de las 04:50 (o desactivarlo esa noche y
lanzarlo a mano). Confirmar con P13 que el domingo no se trabaja.

| Cuándo | Qué |
|---|---|
| −48 h | Bajar el **TTL** del registro DNS de `nath.tuctuc.com` a 300 s. |
| −24 h | Último `rsync` del filestore. Certificado listo en el servidor nuevo (copiado por Soporte o emitido por DNS-01). Aviso a jefes de turno. |
| 01:00 | Parar Odoo en GCP (`systemctl stop nath-erp`) o ponerlo en mantenimiento en nginx. Comprobar que no hay jobs en `started`. |
| 01:05 | `pg_dump` final de Cloud SQL → `pg_restore` en el nuevo (tiempo medido en 3.1). Si tarda demasiado, ver «Alternativa: réplica». |
| | `rsync` final del filestore y de **las sesiones** (`/home/ubuntu/.local/share/Odoo/sessions`), para que las PDA no salgan. |
| | **No neutralizar**: esta es la buena. Comprobar `web.base.url`, crons activos, `queue_job` con su canal. |
| | Arrancar Odoo nuevo. Pruebas rápidas por `hosts`. |
| | Cambiar el **DNS** de `nath.tuctuc.com` a la IP nueva. |
| | PedidosMultiples: publicar la versión con el host nuevo en el actualizador (`192.168.0.50`). |
| 05:00 | Lista de comprobación (3.6). Si algo grave falla → vuelta atrás. |

**Alternativa: réplica lógica.** Si el `pg_dump`/`pg_restore` tarda más de ~2 h, montar replicación lógica de Cloud SQL
(PostgreSQL 11) a la base nueva: activar el flag `cloudsql.logical_decoding` (reinicia Cloud SQL unos minutos: hacerlo
otra noche, con su propio aviso), crear la publicación y dejar que sincronice. El corte se queda en ~30 min (parar,
esperar a que la réplica esté al día, ajustar secuencias, arrancar). Más complejo: solo si hace falta.

### 3.5 Vuelta atrás

- GCP no se borra ni se para del todo: VM y Cloud SQL quedan como estaban (Odoo parado).
- Si falla el corte antes de abrir el almacén: DNS a la IP vieja, arrancar `nath-erp` en GCP, PedidosMultiples
  vuelve a la versión anterior. Lo hecho en el servidor nuevo se descarta (nadie ha trabajado en él).
- Si se detecta tarde (ya con trabajo en el nuevo): no volver a GCP sin más, porque se perderían datos. Arreglar en
  el nuevo; si no hay forma, copiar la base del nuevo a Cloud SQL (otro corte).
- **Dar de baja GCP solo 2-4 semanas después**, con una copia final de Cloud SQL guardada (en el NAS o en Object
  Storage).

### 3.6 Lista de comprobación después del corte

- [ ] `https://nath.tuctuc.com` abre con certificado válido; no sale en blanco (traducciones; `koroshi_http2.conf`).
- [ ] **PDA**: entrar, Lecturas, leer una caja, preparación; sin «Sesión expirada» (sesiones copiadas).
- [ ] Monitor y pantallas de oficina.
- [ ] **Crons**: zonas (04:50), agrupaciones web (06:00), 186 sync S4T, 192 alerta cola; ver `ir_cron.lastcall`.
- [ ] **`queue_job`**: sin `unknown channel root.s4t_sync` en el log; ningún job atascado en `started`.
- [ ] **S4T**: llega un pedido nuevo y sale un batch-update; cierre de camión.
- [ ] **XPO / GLS**: sacar una etiqueta real (una tienda de prueba) y comprobar que el transportista no rechaza la IP
      nueva.
- [ ] **Impresión**: el agente del portátil de Expediciones recoge un trabajo y la Zebra imprime.
- [ ] **Correo saliente**: el informe diario y un aviso llegan (y no van a spam: SPF).
- [ ] **PedidosMultiples** en los PC de oficina, contra la base nueva.
- [ ] Programa de redistribución (XML-RPC).
- [ ] Copias de seguridad de la base nueva: la primera ha corrido y se ha probado a restaurar.
- [ ] Monitorización: disco, CPU y alerta si Odoo no responde (lo que hoy dé GCP).

## 4. Riesgos y coste

### 4.1 Ahorro (con la factura real de noviembre de 2026)

**GCP hoy: ~4.260 €/mes** (tuctuc ~3.660 €, KOROSHI ~980 €, comunes ~65 €; detalle en 1.0).

**Camino 1: quedarse en GCP y ordenar** (sin cambiar de proveedor)

| Medida | Ahorro aprox./mes | Riesgo |
|---|---|---|
| Subir las dos bases de PostgreSQL 11 a 15/16 (actualización de versión mayor de Cloud SQL, con ensayo en un clon) | **~1.760 €** | Medio: las mismas pruebas de Odoo 13 que en R2; corte de ~30-60 min por base |
| Borrar los dos discos sueltos, las dos IP de Singapur y los buckets de Asia que no se usen (tras confirmarlo) | ~120 € | Bajo |
| Compromiso de uso de 1 año en Cloud SQL y VM (~−25 %) | ~400-500 € | Bajo (se paga un año) |
| **GCP ordenado** | **de ~4.260 a ~2.000-2.400 €/mes** | |

**Camino 2: migrar a OVHcloud** (también con PostgreSQL nuevo)

| | KOROSHI | tuctuc |
|---|---|---|
| Odoo | `b3-32` (8/32): 173 € | `b3-64` (16/64): 343 € |
| PostgreSQL | `b3-32` (8/32): 173 € | Máquina 16 vCPU/128 GB (gama r3 o b3-128): **~450-700 €** (precio a confirmar) |
| Réplica de reserva (en vez de la alta disponibilidad de Cloud SQL) | No (hoy no la tiene) | Otra igual: ~450-700 € (opcional) |
| Discos, IP, copias, Object Storage | ~40-80 € | ~80-150 € |
| **Total/mes** | **~390-430 €** | **~870-1.200 €** sin réplica; **~1.300-1.900 €** con réplica |

- **Total migrado: ~1.300-1.650 €/mes sin réplica en tuctuc, ~1.700-2.300 € con réplica.** Con Savings Plan de 12
  meses, un 10-15 % menos.
- **Ahorro frente a hoy: ~2.000-2.900 €/mes (50-65 %).** Frente a «GCP ordenado» (camino 1), el ahorro extra de
  migrar es de **~300-1.000 €/mes**: hay que ponerlo al lado de las 90-150 h de trabajo y del riesgo de cambiar todo.
- Scaleway y Hetzner salen en el mismo orden de magnitud (2.2/2.3); Scaleway con base gestionada sería algo más caro.

**Decisión de Isaac (26/11, tarde): migrar a OVH con PostgreSQL 11 tal cual y subir de versión ya dentro de OVH.**
Confirmado que se puede: el «soporte extendido» es un recargo de Google Cloud SQL (desde el 01/02/2025, hasta el
01/02/2028; https://docs.cloud.google.com/sql/docs/extended-support). En una VM propia de OVH solo se paga la máquina,
sea cual sea la versión. PostgreSQL 11 se instala con los paquetes del archivo oficial
(https://apt-archive.postgresql.org) o con la imagen oficial `postgres:11` de Docker. Ventajas: el traspaso cambia lo
mínimo (misma versión, mismo `pg_dump`) y la subida se ensaya después en un clon barato en OVH (`pg_upgrade`). Contra:
PostgreSQL 11 no tiene parches de seguridad. Por eso, en OVH la base solo se abre a la red privada y a la lista
blanca de 1.0 (oficina, almacén, Ionos, Looker), y la subida a 15/16 se hace en los 2-3 meses siguientes.

**Recomendación anterior (antes de la decisión):** primero el **camino 1** (subir PostgreSQL y limpiar), que da la mayor parte del ahorro con poco
riesgo y además deja la base en una versión que sirve en cualquier proveedor. Después, si Isaac quiere el ahorro
extra, el **camino 2** con OVH, empezando por KOROSHI. La subida de PostgreSQL es la misma pieza en los dos caminos:
no se trabaja dos veces.

### 4.2 Horas de trabajo (Soporte, orientativo)

| Fase | Horas |
|---|---|
| Montar VM, sistema, nginx, certificados, Python/Odoo 13, wkhtmltopdf | 12-20 |
| PostgreSQL, copias y restauración probada, monitorización | 8-12 |
| Copia, neutralización y pruebas (con un responsable del almacén) | 10-16 |
| PedidosMultiples: versión con el host nuevo | 2-4 |
| Corte y comprobaciones | 4-6 (de noche) |
| **Total por Odoo** | **~35-60 h** (el segundo, algo menos) |

### 4.3 Riesgos principales

| # | Riesgo | Cómo se evita |
|---|---|---|
| R1 | La copia de prueba habla con S4T/XPO/GLS o manda correos | Neutralizar (3.3) antes del primer arranque; revisarlo con Isaac |
| R2 | Odoo 13 con PostgreSQL ≥ 12 se comporta distinto (CTE, permisos del esquema `public` en PG 15, extensiones) | Ensayar con la copia; si falla, PostgreSQL 11 en VM propia (opción A) |
| R3 | El entorno de Python/wkhtmltopdf no es igual: PDF distintos, etiquetas mal | Copiar versiones exactas; comparar PDF de zona, CJ y GLS/XPO |
| R4 | PedidosMultiples deja de conectar (IP fija en el código) | Versión nueva del programa preparada antes; IP de la oficina autorizada |
| R5 | Listas blancas por IP (S4T, transportistas) o SPF del correo | P10 y P11 antes de fijar fecha; pedir el cambio con días de margen |
| R6 | Las PDA salen de la sesión | Copiar el directorio de sesiones en el corte |
| R7 | El corte tarda más de lo previsto | Medirlo en el ensayo; réplica lógica si pasa de ~2 h; vuelta atrás |
| R8 | Licencia Enterprise: Odoo 13 ya no tiene soporte oficial y la base va con su `database.uuid` | Mantener la misma base (mismo uuid) y avisar a quien lleve el contrato (P9) |
| R9 | Copias de la base: hoy las hace Cloud SQL sin que nadie lo piense | Copias automáticas + copia diaria fuera del proveedor (NAS o Object Storage) + prueba de restauración mensual |
| R10 | Precios que suben (OVH subió el 01/10; Hetzner dos veces en 2026) | Savings Plan a 12 meses; volver a comparar cada año |
| R11 | Dejar de pagar GCP antes de tiempo o borrar sin copia final | Baja a las 2-4 semanas, con copia final guardada |

### 4.4 Cuánto tarda y quién hace cada parte (añadido el 26/11, a petición de Isaac)

Reparto: **Claude** prepara scripts, comprobaciones, listas y documentos en el repo; **Isaac** (o Soporte) ejecuta en
el servidor y en los proveedores, siempre con su sí, paso a paso; **otros** son quienes tienen que contestar o
hacer algo fuera de nuestro alcance.

| Fase | Qué | Claude | Isaac / Soporte | Otros | Horas de trabajo | Días de calendario |
|---|---|---|---|---|---|---|
| 0. Datos | Contestar P1-P8 (máquinas, factura, tamaños, IP, DNS) | Prepara los comandos `gcloud` de solo lectura y vuelca los resultados en este estudio | Los lanza en Cloud Shell o la consola y pega la salida | — | 1-2 h | 1-2 días |
| 1. Decisión y contrato | Elegir proveedor y opción; pedir presupuesto | Ajusta el ahorro con la factura real; prepara la petición de presupuesto | Decide, crea la cuenta y contrata (Claude no crea cuentas ni contrata) | Comercial de OVH/Scaleway | 2-4 h | 3-7 días |
| 2. Avisos externos | Listas blancas, SPF, DNS, contrato Enterprise | Redacta los correos a S4T, XPO, GLS, quien lleve el DNS y quien lleve Odoo Enterprise | Los envía | S4T, transportistas, proveedor de DNS/correo, Odoo/partner | 1-2 h | **1-3 semanas** (esperar respuestas; es lo que más tarda) |
| 3. Montar el servidor | Sistema, nginx, certificados, Python/Odoo 13, wkhtmltopdf, PostgreSQL, copias, monitorización | Escribe los scripts de instalación (`bin/migracion/…`) con comprobaciones (`check` antes de `install`, como `desplegar.sh`) y la lista de versiones exactas | Ejecuta los scripts con su sí; copia el código y la configuración de la VM vieja (tienen claves: Claude no las toca) | — | 20-30 h | 1 semana |
| 4. Copia y neutralización | `pg_dump`/`pg_restore`, `rsync` del filestore, neutralizar | Script de copia y SQL de neutralización (3.3) con su comprobación posterior | Lo lanza; mide el tiempo de la copia | — | 4-8 h | 1-2 días |
| 5. Pruebas | Lista de 3.2 y 3.6 contra la copia | Prepara la lista, los scripts de comparación (tiempos, PDF de etiquetas) y una versión de PedidosMultiples con el host nuevo | Prueba en oficina | **Un responsable del almacén con una PDA** (1-2 h); quien lleve PedidosMultiples | 8-12 h | 3-5 días |
| 6. Ensayo del corte | Corte completo sobre la copia, cronometrado | Guion del corte minuto a minuto y guion de vuelta atrás | Lo ensaya | — | 3-4 h | 1 noche |
| 7. Corte real | Domingo 01:00-05:00 | Guion y lista de comprobación; durante el corte, revisa salidas y logs que Isaac le pase | Ejecuta todo (DNS, parar, copiar, arrancar) | Quien lleve el DNS si no es Isaac | 4-6 h | 1 noche |
| 8. Vigilancia y baja de GCP | Primera semana; baja a las 2-4 semanas | Revisa logs, crons y cola S4T que Isaac le pase; lista para dar de baja | Mira el almacén el lunes a primera hora; da de baja GCP con copia final | — | 3-5 h | 2-4 semanas |

**Total por Odoo: ~45-75 h de trabajo**, de las que **Isaac/Soporte ~30-45 h** (sobre todo las fases 3 y 7) y el
resto preparación de Claude. **En calendario: 4-6 semanas** desde que se tengan los datos de la fase 0, sobre todo por
esperar a terceros (fase 2) y por hacer el corte en domingo. El segundo Odoo, ~2-3 semanas más y algo menos de
trabajo (los scripts ya estarán hechos).

Lo que **solo** puede hacer Isaac u otra persona: crear la cuenta y pagar, entrar en el servidor y ejecutar, copiar
configuraciones con claves, cambiar el DNS, hablar con S4T/transportistas/Odoo y probar con la PDA en el almacén.

La fase 0 ya está casi hecha: los datos de la consola están en 1.0. Faltan los de dentro de las VM (P4, P5), que
requieren entrar por SSH.

Si solo se hace el **camino 1** (subir PostgreSQL en GCP): ensayo en un clon de cada base (Isaac lo crea; Claude
prepara las pruebas de Odoo 13), ~15-25 h por base y una noche de corte de ~30-60 min por base. En calendario, 2-3
semanas para las dos.

## 5. Preguntas para Isaac

Todos los comandos son **de solo lectura**. Los de `gcloud` se pueden lanzar desde Cloud Shell, en la consola de
Google Cloud.

| # | Pregunta | Cómo responderla |
|---|---|---|
| P1 | ~~Máquinas y tamaños~~ | **Respondida (1.0)**: dos VM, sin más. |
| P2 | ~~Coste mensual~~ | **Respondida (1.0)**: ~4.260 €/mes en noviembre. Faltan los meses anteriores (P20). |
| P3 | ~~Bases de Cloud SQL~~ | **Respondida (1.0)**: 62 GB usados (KOROSHI) y 220 GB (tuctuc). El tamaño exacto de cada base, con `select pg_size_pretty(pg_database_size(current_database()))` desde Odoo o PedidosMultiples. |
| P4 | ¿Cuánto ocupa el filestore? **(pendiente: hace falta SSH)** | En la VM: `sudo du -sh /home/ubuntu/.local/share/Odoo/filestore/*` (o la ruta de `data_dir` en `nath-erp.conf`: `grep data_dir /opt/nath-erp/nath-erp.conf`) |
| P5 | ¿Qué sistema operativo y versiones hay? **(pendiente: hace falta SSH; la pestaña «OS info» de la consola sale vacía)** | En la VM: `cat /etc/os-release; python3 --version; nginx -v; wkhtmltopdf --version` |
| P6 | ~~IP autorizadas en Cloud SQL~~ | **Respondida (1.0)**: oficina/almacén Oriola, Ionos y Looker. |
| P7 | ~~Otros servicios~~ | **Respondida (1.0)**: 3 buckets, discos e IP sueltos; sin Cloud DNS ni balanceadores. |
| P8 | ¿Quién lleva el DNS de `tuctuc.com` y quién emite el certificado? | `nslookup -type=NS tuctuc.com` (desde cualquier PC); en la VM: `sudo ls /etc/letsencrypt/live 2>/dev/null; grep -r ssl_certificate /etc/nginx/` |
| P9 | ¿Quién lleva el contrato de Odoo Enterprise (Odoo SA, Effective, un partner)? ¿Hay que avisar del cambio de servidor? | Odoo → Ajustes → (pie de la página) código de suscripción y fecha de caducidad |
| P10 | ¿S4T, XPO, GLS u otros tienen nuestra IP en una lista blanca, o nos llaman ellos a nosotros (webhooks)? | Preguntar a S4T y transportistas. IP de salida de la VM: `curl -s ifconfig.me` en la VM |
| P11 | ¿Qué servidor de correo usa el `NATH` de Odoo (Gmail, Office 365, propio)? ¿El SPF del dominio incluye la IP de la VM? | Odoo → Ajustes → Técnico → Servidores de correo saliente; `nslookup -type=TXT nath.es` |
| P12 | Latencia real desde el almacén | Desde un PC del almacén: `ping` a las IP de prueba de cada proveedor (páginas de *looking glass* / speedtest de OVH, Scaleway y Hetzner) y a `nath.tuctuc.com` para comparar |
| P13 | ¿Se trabaja en el almacén los domingos de madrugada? ¿Y en tuctuc (TPV, tiendas)? | — |
| P14 | ¿Quién es «Soporte» y tiene experiencia con PostgreSQL? Decide entre opción A (base en VM) y B (gestionada). | — |
| P15 | ¿Se migra también tuctuc, y en qué orden? | — |
| P16 | ¿Qué es el servidor de **Ionos** (82.223.30.89) que entra a las dos bases? ¿Quién lo lleva? | — |
| P17 | ¿Qué informes de **Looker Studio** leen las bases directamente y quién los usa? | Looker Studio → Fuentes de datos |
| P18 | ¿Qué integración usa el **puerto 3232** de salida? | Preguntar a Soporte, o en la VM: `sudo ss -tnp \| grep :3232` |
| P19 | ¿Quién lee el bucket **público** `nath-stock-feed-q7m4x2` (creado el 19/11)? ¿Debe ser público? | — |
| P20 | ¿Qué cuenta de facturación pagaba antes de finales de octubre y cuánto costaba? ¿Los dos discos sueltos, las IP de Singapur y los buckets de Asia se pueden borrar? | Consola → Facturación → la otra cuenta → Informes |

## 6. Siguiente paso propuesto

1. Isaac decide entre camino 1 (subir PostgreSQL en GCP) y camino 1 + 2 (después migrar), y responde P13-P20.
2. Se pide presupuesto a OVHcloud (y a Scaleway como contraste) con las máquinas de 2.3, y se mide la latencia (P12).
3. Con el sí de Isaac, Soporte monta el servidor nuevo y se hace el ensayo completo con la copia neutralizada.
4. Fecha de corte solo cuando el ensayo haya salido bien y P10/P11 estén resueltos.

## Fuentes (consultadas el 26/11/2026)

- S1. OVHcloud, lista de precios Public Cloud — https://www.ovhcloud.com/en/public-cloud/prices/
- S2. OVHcloud, «Public Cloud new pricing details, starting October 1, 2026» (b3-32: 149 → 173 €; b3-64: 299 → 343 €) — https://blog.ovhcloud.com/en/posts/public-cloud-pricing-update-october-2026/
- S3. OVHcloud, «Public Cloud: à la carte model starting October 1, 2026» (disco local e IPv4 aparte; Savings Plan 12/36 meses) — https://blog.ovhcloud.com/en/posts/public-cloud-pricing-model-update-2026/
- S4. Scaleway, precios de instancias (POP2-8C-32G 0,29 €/h, ~211,70 €/mes) — https://www.scaleway.com/en/pricing/virtual-instances/
- S5. Cloud Mercato, POP2-8C-32G — https://pcr.cloud-mercato.com/providers/scaleway/flavors/pop2-8c-32g/pricing
- S6. Scaleway, precios de bases de datos gestionadas y almacenamiento — https://www.scaleway.com/en/pricing/managed-databases/
- S7. TrackVPS, «Hetzner price increase 2026» (CCX33 138,49 €; CCX43 275,99 €) — https://trackvps.com/hetzner-price-increase
- S8. Google Cloud, precios de máquinas de uso general — https://cloud.google.com/products/compute/pricing/general-purpose
- S9. gcloud-compute.com, n2-standard-8 por región — https://gcloud-compute.com/n2-standard-8.html
- S10. ClickHouse, «Cloud SQL for PostgreSQL alternatives (2026)» (Cloud SQL 8 vCPU/32 GB/500 GB HA ≈ 979 $/mes en us-central1) — https://clickhouse.com/resources/engineering/cloud-sql-postgres-alternatives
- S11. Better Stack, «Hetzner Cloud Review 2026» — https://betterstack.com/community/guides/web-servers/hetzner-cloud-review/
- S12. CloudTally, «Hetzner Cloud pricing 2026» (SLA 99,9 %, copias +20 %, volúmenes 0,0572 €/GB, IPv4 0,50 €) — https://cloudtally.eu/hetzner-cloud-prices
- S13. webhosting.today, subidas de Hetzner en 2026 — https://webhosting.today/2026/06/18/hetzners-price-increases-reached-209-the-30-headline-applied-to-a-different-tier/

Lo marcado como «no confirmado aquí» (SLA exacto de OVH y Scaleway, precio de IP adicional y vRack de OVH, snapshots
de OVH) hay que mirarlo en la calculadora del proveedor al pedir presupuesto.
