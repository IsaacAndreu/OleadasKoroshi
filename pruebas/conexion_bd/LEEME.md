# Prueba de la conexión de PedidosMultiples a PostgreSQL

Programa de consola que usa el `ConnectionSQL.cs` real de PedidosMultiples (enlazado, no copiado) y el Npgsql 8.0.3
de `lib\`. No abre ninguna ventana del programa ni escribe en ninguna base.

Compilar (desde esta carpeta):

    dotnet build -c Release -p:TargetFrameworkRootPath=<carpeta de los ensamblados de referencia de .NET 4.8>

## 1. Prueba local (sin red)

    bin\Release\net48\prueba_conexion_bd.exe

Levanta dos servidores PostgreSQL **falsos** en 127.0.0.1: uno sin SSL y otro con SSL y un certificado autofirmado.
Comprueba Prefer, Require y Disable con NATH y con TUCTUC. También comprueba que, sin claves en el `.config`, salen
el host y el puerto de siempre y que un valor mal escrito no deja el programa sin conexión. Si el host no es
127.0.0.1, se para antes de conectar. Debe acabar con `TODO BIEN`.

## 2. Contra un servidor de PRUEBA (cuando exista)

    bin\Release\net48\prueba_conexion_bd.exe nath <ip-de-prueba> [puerto] [Prefer|Require|Disable]
    bin\Release\net48\prueba_conexion_bd.exe tuctuc <ip-de-prueba> [puerto] [Prefer|Require|Disable]

- Solo lee: `select version(), current_database()` y si la conexión va con SSL (`pg_stat_ssl`).
- **Se niega a conectar a 34.90.144.125 y 104.199.5.207** (producción).
- La base debe llamarse como en producción (`NATH_PRODUCTION` / `TUCTUC_PRODUCTION`): ese nombre no se lee del `.config`.
- El servidor de prueba tiene que dejar entrar a la IP pública del PC desde el que se prueba.
