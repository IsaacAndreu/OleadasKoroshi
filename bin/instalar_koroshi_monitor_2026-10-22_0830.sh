#!/usr/bin/env bash
# =============================================================================
# Instalar / actualizar el modulo KOROSHI Monitor zonas (koroshi_monitor) en Odoo 13.
#
# Uso (en el servidor de Odoo, como root o con sudo):
#   sudo bash instalar_koroshi_monitor_2026-10-22_0830.sh /tmp/koroshi_monitor_2026-10-22_0825_v1.zip
#
# Que hace:
#   1. Busca el Odoo que esta corriendo: su fichero de configuracion, el addons_path,
#      el usuario con el que corre y el servicio (systemd).
#   2. Elige la carpeta de modulos propios (la del addons_path que no es la de Odoo).
#   3. Si ya hay un koroshi_monitor, lo copia a una copia de seguridad con fecha.
#   4. Descomprime el zip en esa carpeta y le pone el dueno del usuario de Odoo.
#   5. Reinicia el servicio de Odoo.
#   6. Instala (o actualiza, si ya estaba) el modulo en la base de datos.
#   Antes de cambiar nada ensena lo que ha encontrado y pide confirmacion.
#
# Variables que se pueden forzar si la deteccion no acierta:
#   ODOO_CONF=/etc/odoo/odoo.conf  ADDONS_DIR=/opt/nath-erp/addons_propios
#   ODOO_SERVICE=odoo  ODOO_USER=odoo  ODOO_BIN=/opt/nath-erp/odoo13/odoo-bin
#   ODOO_PYTHON=/opt/nath-erp/venv/bin/python  ODOO_DB=NATH_PRODUCTION
# =============================================================================
set -euo pipefail

MODULO=koroshi_monitor
ZIP="${1:-}"
ODOO_DB="${ODOO_DB:-NATH_PRODUCTION}"
FECHA=$(date +%Y-%m-%d_%H%M)

rojo() { printf '\033[31m%s\033[0m\n' "$*"; }
verde() { printf '\033[32m%s\033[0m\n' "$*"; }
paso() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

if [ -z "$ZIP" ] || [ ! -f "$ZIP" ]; then
    rojo "Falta el zip. Uso: sudo bash $0 /ruta/koroshi_monitor_....zip"
    exit 1
fi
if [ "$(id -u)" -ne 0 ]; then
    rojo "Hay que ejecutarlo con sudo (para copiar en la carpeta de Odoo y reiniciar el servicio)."
    exit 1
fi
command -v unzip >/dev/null || { rojo "Falta 'unzip': apt-get install unzip"; exit 1; }

# ---------------------------------------------------------------- 1. Detectar
paso "1. Buscando el Odoo que esta corriendo"
PROC=$(ps -eo user:32,args | grep -E 'odoo-bin|openerp-server|odoo ' | grep -v grep | head -1 || true)
if [ -n "$PROC" ]; then
    echo "   Proceso: $PROC"
    ODOO_USER="${ODOO_USER:-$(echo "$PROC" | awk '{print $1}')}"
    if [ -z "${ODOO_CONF:-}" ]; then
        ODOO_CONF=$(echo "$PROC" | grep -oE '(-c|--config)[ =][^ ]+' | head -1 | sed -E 's/^(-c|--config)[ =]//' || true)
    fi
    if [ -z "${ODOO_BIN:-}" ]; then
        ODOO_BIN=$(echo "$PROC" | grep -oE '[^ ]*odoo-bin' | head -1 || true)
    fi
    if [ -z "${ODOO_PYTHON:-}" ]; then
        PRIMERO=$(echo "$PROC" | awk '{print $2}')
        case "$PRIMERO" in *python*) ODOO_PYTHON="$PRIMERO" ;; esac
    fi
fi
if [ -z "${ODOO_CONF:-}" ]; then
    for c in /etc/odoo/odoo.conf /etc/odoo13.conf /etc/odoo-server.conf /opt/nath-erp/odoo13.conf /opt/nath-erp/*.conf; do
        [ -f "$c" ] && ODOO_CONF="$c" && break
    done
fi
[ -n "${ODOO_CONF:-}" ] && [ -f "$ODOO_CONF" ] || { rojo "No encuentro el fichero de configuracion de Odoo. Pasalo con ODOO_CONF=..."; exit 1; }
ODOO_PYTHON="${ODOO_PYTHON:-python3}"

if [ -z "${ODOO_SERVICE:-}" ]; then
    ODOO_SERVICE=$(systemctl list-units --type=service --all --no-legend 2>/dev/null | awk '{print $1}' | grep -iE 'odoo|nath|openerp' | head -1 || true)
    ODOO_SERVICE="${ODOO_SERVICE%.service}"
fi

ADDONS_PATH=$(grep -E '^\s*addons_path\s*=' "$ODOO_CONF" | head -1 | cut -d= -f2- | tr -d ' ')
if [ -z "${ADDONS_DIR:-}" ]; then
    # La primera carpeta del addons_path que no es la de los modulos estandar de Odoo
    IFS=',' read -ra RUTAS <<< "$ADDONS_PATH"
    for r in "${RUTAS[@]}"; do
        case "$r" in */odoo/addons|*/odoo13/addons|*/odoo/odoo/addons|*/odoo13/odoo/addons) continue ;; esac
        [ -d "$r" ] && ADDONS_DIR="$r" && break
    done
fi
[ -n "${ADDONS_DIR:-}" ] && [ -d "$ADDONS_DIR" ] || { rojo "No encuentro una carpeta de modulos propios en addons_path ($ADDONS_PATH). Pasala con ADDONS_DIR=..."; exit 1; }

echo "   Configuracion : $ODOO_CONF"
echo "   addons_path   : $ADDONS_PATH"
echo "   Se instala en : $ADDONS_DIR/$MODULO"
echo "   Usuario Odoo  : ${ODOO_USER:-?}"
echo "   Servicio      : ${ODOO_SERVICE:-? (no encontrado: habra que reiniciar a mano)}"
echo "   odoo-bin      : ${ODOO_BIN:-? (no encontrado: el modulo se instala desde Aplicaciones)}"
echo "   Base de datos : $ODOO_DB"
echo "   Zip           : $ZIP"
unzip -l "$ZIP" | grep -q "$MODULO/__manifest__.py" || { rojo "El zip no tiene $MODULO/__manifest__.py"; exit 1; }

read -r -p "¿Seguir? Se reinicia Odoo (unos segundos sin servicio) [s/N] " OK
[ "$OK" = "s" ] || [ "$OK" = "S" ] || { echo "Cancelado. No se ha cambiado nada."; exit 0; }

# ---------------------------------------------------------------- 2. Copia de seguridad
YA_ESTABA=0
if [ -d "$ADDONS_DIR/$MODULO" ]; then
    YA_ESTABA=1
    paso "2. Ya hay un $MODULO: copia de seguridad"
    mv "$ADDONS_DIR/$MODULO" "$ADDONS_DIR/${MODULO}_backup_$FECHA"
    echo "   Guardado en $ADDONS_DIR/${MODULO}_backup_$FECHA"
    # Odoo carga cualquier carpeta con __manifest__.py: se renombra el de la copia para que no la cargue
    mv "$ADDONS_DIR/${MODULO}_backup_$FECHA/__manifest__.py" "$ADDONS_DIR/${MODULO}_backup_$FECHA/__manifest__.py.bak"
else
    paso "2. Primera instalacion (no habia $MODULO)"
fi

# ---------------------------------------------------------------- 3. Descomprimir
paso "3. Descomprimiendo"
TMP=$(mktemp -d)
unzip -q "$ZIP" -d "$TMP"
cp -r "$TMP/$MODULO" "$ADDONS_DIR/$MODULO"
rm -rf "$TMP"
if [ -n "${ODOO_USER:-}" ] && id "$ODOO_USER" >/dev/null 2>&1; then
    chown -R "$ODOO_USER": "$ADDONS_DIR/$MODULO"
fi
find "$ADDONS_DIR/$MODULO" -type d -exec chmod 755 {} \;
find "$ADDONS_DIR/$MODULO" -type f -exec chmod 644 {} \;
ls -R "$ADDONS_DIR/$MODULO" | sed 's/^/   /'

# ---------------------------------------------------------------- 4. Parar, instalar y arrancar
if [ -n "${ODOO_SERVICE:-}" ]; then
    paso "4. Parando $ODOO_SERVICE"
    systemctl stop "$ODOO_SERVICE"
fi

if [ -n "${ODOO_BIN:-}" ]; then
    if [ "$YA_ESTABA" = 1 ]; then ACCION="-u"; QUE="Actualizando"; else ACCION="-i"; QUE="Instalando"; fi
    paso "5. $QUE $MODULO en $ODOO_DB"
    LOG=/tmp/instalar_${MODULO}_$FECHA.log
    if sudo -u "${ODOO_USER:-odoo}" "$ODOO_PYTHON" "$ODOO_BIN" -c "$ODOO_CONF" -d "$ODOO_DB" $ACCION "$MODULO" \
            --stop-after-init --no-http --logfile="$LOG"; then
        if grep -qE 'ERROR|CRITICAL' "$LOG"; then
            rojo "   Hay errores en el log: $LOG"
            grep -E 'ERROR|CRITICAL' "$LOG" | tail -20
        else
            verde "   Hecho sin errores (log: $LOG)"
        fi
    else
        rojo "   Ha fallado. Mira el log: $LOG"
        tail -30 "$LOG" || true
    fi
else
    paso "5. No he encontrado odoo-bin: instalar desde Odoo (Aplicaciones > Actualizar lista > KOROSHI Monitor zonas > Instalar)"
fi

if [ -n "${ODOO_SERVICE:-}" ]; then
    paso "6. Arrancando $ODOO_SERVICE"
    systemctl start "$ODOO_SERVICE"
    sleep 5
    systemctl is-active --quiet "$ODOO_SERVICE" && verde "   $ODOO_SERVICE en marcha" || { rojo "   $ODOO_SERVICE NO ha arrancado:"; journalctl -u "$ODOO_SERVICE" -n 30 --no-pager; }
else
    paso "6. Reinicia Odoo a mano (no he encontrado el servicio)"
fi

verde "
Listo. En Odoo: Inventario > Operaciones > Monitor zonas
(recargar la pagina con Ctrl+F5 para que cargue el JS nuevo).

Para volver atras:
  sudo rm -rf $ADDONS_DIR/$MODULO
  $( [ "$YA_ESTABA" = 1 ] && echo "sudo mv $ADDONS_DIR/${MODULO}_backup_$FECHA $ADDONS_DIR/$MODULO && sudo mv $ADDONS_DIR/$MODULO/__manifest__.py.bak $ADDONS_DIR/$MODULO/__manifest__.py" || echo "(y en Odoo: Aplicaciones > KOROSHI Monitor zonas > Desinstalar)" )
  sudo systemctl restart ${ODOO_SERVICE:-<servicio odoo>}"
