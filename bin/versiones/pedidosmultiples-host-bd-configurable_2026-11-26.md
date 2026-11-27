# PedidosMultiples 0.8.1.0: servidor de las bases configurable (migración Google Cloud → OVH)

26/11/2026. Preparado y **sin publicar**. Relacionado: `estudio-migracion-servidores_2026-11-26.md` (1.0, 7 y 7.6).

## Qué se ha cambiado

| Archivo:línea | Cambio |
|---|---|
| `PedidosMultiples/ConnectionSQL.cs:25` | El host de NATH sale de `db_host_nath`; si falta, es `34.90.144.125`. Se añaden puerto y SSL (`PuertoYSsl("nath")`). |
| `PedidosMultiples/ConnectionSQL.cs:29` | Igual para TUCTUC: `db_host_tuctuc`, y si falta `104.199.5.207`. |
| `PedidosMultiples/ConnectionSQL.cs:43` | `Ajuste()`: lee la clave de `App.config`; si falta o está vacía, devuelve el valor de siempre. |
| `PedidosMultiples/ConnectionSQL.cs:59` | `PuertoYSsl()`: `db_port_*` (5432 por defecto) y `db_ssl_mode_*` (Prefer por defecto). Un puerto o un modo mal escritos se tratan como 5432 y Prefer. |
| `App.config:97-106` | Claves nuevas con los valores de hoy: `db_host_nath`, `db_port_nath`, `db_ssl_mode_nath`, `db_host_tuctuc`, `db_port_tuctuc`, `db_ssl_mode_tuctuc`. |
| `Properties/AssemblyInfo.cs:16-17` | Versión 0.8.1.0 (las 0.8.0.10 y 0.8.0.11 ya existen en la rama de TUCTUC; ver abajo). |
| `pruebas/conexion_bd/` | Programa de prueba (ver su `LEEME.md`). |

**Credenciales: no se han tocado.** Siguen en `ConnectionSQL.cs`, en el mismo sitio. Solo ha cambiado el trozo `Host=…`, y
se ha añadido `;Port=…;SSL Mode=…` al final de la cadena.

**Con un `.config` antiguo (sin las claves nuevas), el programa conecta exactamente igual que hoy**: mismo host,
puerto 5432 y `SSL Mode=Prefer`, que ya es lo que hace Npgsql 8 por defecto.

Paquete: `bin/20261126_PedidosMultiples_0.8.1.0.zip` (exe + pdb, sin `.config`, para que cada PC conserve el suyo).
Compilado con `dotnet msbuild` como desde el 20/11: el `.config` de cada PC tiene que llevar ya la redirección de
`System.Resources.Extensions` (la lleva `App.config` desde `e373ad6`).

## Cómo se ha probado

- `pruebas/conexion_bd`, con el `ConnectionSQL.cs` real y Npgsql 8.0.3, contra servidores PostgreSQL **falsos en
  127.0.0.1**. Resultado, 8 de 8:
  - servidor sin SSL + Prefer → conecta sin SSL (como hoy);
  - servidor con SSL + Prefer → TLS 1.2;
  - servidor con SSL + Require → TLS 1.2, con certificado autofirmado (Require no valida el certificado);
  - servidor sin SSL + Require → error «SSL connection requested…» (esperado);
  - con SSL + Disable → sin SSL;
  - NATH con Require y con Prefer;
  - valor mal escrito → Prefer.
- Sin claves en el `.config` → `104.199.5.207` / `34.90.144.125`, puerto 5432, Prefer (solo se mira la cadena, no se conecta).
- El modo «servidor de prueba» se niega a conectar a las dos IP de producción (comprobado).
- Compilación de 0.8.1.0 sin errores. En el exe descompilado, `ConnectionSQL` lleva el cambio.

## Qué no se ha podido probar

- Un PostgreSQL de verdad con SSL (el de OVH aún no existe): la autenticación real (usuario y contraseña) y una consulta.
- El programa entero en un PC. No se ha ejecutado contra producción, como se pidió.
- Que el `.config` de cada PC de KOROSHI lleve la redirección de `System.Resources.Extensions`.

## Cómo probar contra el servidor de prueba (sin tocar producción)

1. `pruebas/conexion_bd`: `prueba_conexion_bd.exe nath <ip> [puerto] [Require]`. Tiene que salir `OK: PostgreSQL … | SSL: si`.
2. El programa entero, en un PC que no sea del almacén:
   - copiar la carpeta `bin/Release` a una carpeta aparte;
   - en su `PedidosMultiples.exe.config`, poner `db_host_nath` = IP de prueba (y `db_ssl_mode_nath` si pide SSL);
   - poner `db_host_tuctuc` = `127.0.0.1`, para que TUCTUC no pueda llegar a producción;
   - poner `koroshi_modo_prueba` = `true`;
   - poner `odoo_url` = Odoo de prueba, nunca `nath.tuctuc.com`.
   Abrir solo la empresa de KOROSHI y cargar una oleada.

## Qué hay que hacer el día del cambio de KOROSHI

1. Con la IP nueva: `prueba_conexion_bd.exe nath <ip-nueva> 5432 <Prefer|Require>` desde la oficina.
2. Dos opciones:
   - **a)** En cada PC, cambiar `db_host_nath` (y `db_ssl_mode_nath` si hace falta) en `PedidosMultiples.exe.config`.
   - **b)** Sacar la 0.8.1.1 con el valor por defecto de `db_host_nath` cambiado en `ConnectionSQL.cs:25` y publicarla.
   Para que la b) funcione hace falta que la 0.8.1.0 ya esté instalada en todos los PC antes del corte. Si no, los PC
   que estén en 0.8.0.9 no leen el `.config`: con exe nuevo y `.config` viejo van al valor por defecto del exe.
3. En enero, lo mismo con `db_host_tuctuc` (`ConnectionSQL.cs:29`).

## Actualizador: KOROSHI y TUCTUC separados (decidido por Isaac el 26/11)

Hasta la 0.8.0.9, **los PedidosMultiples de KOROSHI y de TUCTUC compartían el XML del actualizador**
(`updates/pedidos_multiples_odoo.xml`). Desde el 23/11 ese XML ofrece la 0.8.0.11 de TUCTUC: un PC de KOROSHI que
pulse «Buscar actualizaciones» instalaría la versión de TUCTUC y perdería lo de EFFE.

- **TUCTUC se queda con `pedidos_multiples_odoo.xml`** (sus portátiles ya lo usan).
- **KOROSHI pasa a `pedidos_multiples_koroshi.xml`** desde la 0.8.1.0: `PedidosMultiples/InitialForm.cs:5540` y
  `:5544`. Solo cambia el nombre del fichero; las credenciales de esa línea no se han tocado.
- XML preparado y **sin subir**: `bin/pedidos_multiples_koroshi.xml`. Apunta a
  `PedidosMultiples - Desktop/PedidosMultiples0810_koroshi.zip`, que es el zip `bin/20261126_PedidosMultiples_0.8.1.0.zip`
  con ese nombre.
- **Los PC de KOROSHI que siguen en 0.8.0.9 todavía leen el XML compartido**, así que la 0.8.1.0 hay que ponérsela
  **a mano una vez** (copiar el exe). A partir de ahí se actualizan desde su propio XML.
- **Hasta entonces, en los PC de KOROSHI no se debe pulsar «Buscar actualizaciones».**

La versión de TUCTUC (0.8.0.11) también se conecta a las dos IP: necesita el mismo cambio antes de diciembre.
