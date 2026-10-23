# Instalar el módulo KOROSHI Monitor zonas — pasos

Ficheros (en `bin/`):
- `koroshi_monitor_2026-10-22_0825_v1.zip` — el módulo
- `instalar_koroshi_monitor_2026-10-22_0830.sh` — el script que lo instala en el servidor

## 1. Copiar los dos ficheros al servidor (desde este PC, PowerShell)

Cambiar `usuario` y `servidor` por los vuestros (el del servidor donde corre Odoo, `/opt/nath-erp/odoo13`):

```powershell
cd C:\dev\OleadasKoroshi\bin
scp koroshi_monitor_2026-10-22_0825_v1.zip instalar_koroshi_monitor_2026-10-22_0830.sh usuario@servidor:/tmp/
```

(Con WinSCP o FileZilla vale igual: dejar los dos ficheros en `/tmp/` del servidor.)

## 2. Entrar al servidor y ejecutar el script

```bash
ssh usuario@servidor
sudo bash /tmp/instalar_koroshi_monitor_2026-10-22_0830.sh /tmp/koroshi_monitor_2026-10-22_0825_v1.zip
```

El script:
1. Busca el Odoo que está corriendo: configuración, `addons_path`, usuario y servicio.
2. **Enseña lo que ha encontrado y pregunta `¿Seguir? [s/N]`** — revisar que la carpeta
   "Se instala en" es la de vuestros módulos propios y la base de datos es `NATH_PRODUCTION`.
3. Si ya había un `koroshi_monitor`, lo guarda como `koroshi_monitor_backup_<fecha>`.
4. Descomprime el módulo y le pone el dueño del usuario de Odoo.
5. Para Odoo, instala el módulo en la base de datos (o lo actualiza) y vuelve a arrancar Odoo.
   **Odoo está parado unos segundos/minuto.** Mejor hacerlo en un momento tranquilo.
6. Al final dice cómo volver atrás.

Si no acierta algo, se le puede decir a mano, por ejemplo:

```bash
sudo ADDONS_DIR=/opt/nath-erp/addons ODOO_SERVICE=odoo13 bash /tmp/instalar_koroshi_monitor_2026-10-22_0830.sh /tmp/koroshi_monitor_2026-10-22_0825_v1.zip
```

Variables: `ODOO_CONF`, `ADDONS_DIR`, `ODOO_SERVICE`, `ODOO_USER`, `ODOO_BIN`, `ODOO_PYTHON`, `ODOO_DB`.

## 3. Comprobar en Odoo

1. Recargar Odoo con **Ctrl+F5**.
2. **Inventario › Operaciones › Monitor zonas**.
3. Debe salir «Cómo van las agrupaciones Z-2210» con los datos de ahora.

Si sale un error, copiarlo (y el log que dice el script, `/tmp/instalar_koroshi_monitor_<fecha>.log`).

## Si el script no encuentra odoo-bin

Instala los ficheros y reinicia Odoo igualmente; el módulo se instala a mano:
modo desarrollador › **Aplicaciones › Actualizar lista de aplicaciones** › buscar
«KOROSHI Monitor zonas» (quitar el filtro «Aplicaciones») › **Instalar**.
