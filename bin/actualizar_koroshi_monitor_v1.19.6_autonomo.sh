#!/usr/bin/env bash
# KOROSHI Monitor v1.19.6 - actualizador autonomo (11/11/2026).
# Añade el boton para volver de Consulta de envios al Monitor picking.
#
# Uso:
#   sudo bash actualizar_koroshi_monitor_v1.19.6_autonomo.sh check
#   sudo AUTO_CONFIRM=1 bash actualizar_koroshi_monitor_v1.19.6_autonomo.sh install
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ZIP_NAME="20261111_koroshi_monitor_v1.19.6.zip"
ZIP="$SCRIPT_DIR/$ZIP_NAME"
[ -f "$ZIP" ] || ZIP="/home/it_nath_group/$ZIP_NAME"
MODE="${1:-check}"
MODULE="koroshi_monitor"
VERSION="13.0.1.19.6"
ADDONS_DIR="${ADDONS_DIR:-/opt/nath-erp/nath/enterprise-addons}"
ODOO_SERVICE="${ODOO_SERVICE:-nath-erp}"
BACKUP_DIR="${BACKUP_DIR:-/opt/nath-erp/copias_modulos}"
TMP="$(mktemp -d /tmp/koroshi_monitor.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

ok(){ printf '\033[32mOK  %s\033[0m\n' "$*"; }
bad(){ printf '\033[31mERROR  %s\033[0m\n' "$*"; exit 1; }

[ "$MODE" = check ] || [ "$MODE" = install ] || bad "Usa check o install."
[ -f "$ZIP" ] || bad "No existe $ZIP"
command -v unzip >/dev/null 2>&1 || bad "Falta unzip."
case "$ADDONS_DIR" in /*) ;; *) bad "ADDONS_DIR debe ser una ruta absoluta." ;; esac

unzip -tqq "$ZIP" || bad "El ZIP esta dañado."
unzip -q "$ZIP" -d "$TMP"
SOURCE="$TMP/$MODULE"
TARGET="${ADDONS_DIR%/}/$MODULE"
[ -f "$SOURCE/__manifest__.py" ] || bad "Falta $MODULE/__manifest__.py dentro del ZIP."
grep -q "'version': '$VERSION'" "$SOURCE/__manifest__.py" || bad "El ZIP no es la version $VERSION."
grep -q '^PERSONA_INACTIVA_MIN = 5' "$SOURCE/controllers/main.py" || bad "Falta el limite de 5 minutos."
[ -f "$SOURCE/static/src/js/mobile_swipe_guard.js" ] || bad "Falta la correccion movil anterior."
grep -Fq "'Done Quantity']" "$SOURCE/controllers/envios.py" || bad "El Excel Web no tiene las seis columnas esperadas."
grep -Fq "min(grupo['bultos'], 5)" "$SOURCE/controllers/envios.py" || bad "Falta el maximo de 5 etiquetas GLS."
grep -Fq "('carrier_tracking_ref', '!=', False)" "$SOURCE/controllers/envios.py" || bad "GLS no filtra etiquetas generadas."
grep -Fq "tag: 'koroshi_monitor'" "$SOURCE/static/src/js/envios.js" || bad "Falta el boton de vuelta al Monitor picking."
[ -d "$ADDONS_DIR" ] || bad "No existe $ADDONS_DIR"
systemctl show -p LoadState "$ODOO_SERVICE" 2>/dev/null | grep -q '=loaded$' || bad "No existe el servicio $ODOO_SERVICE."

ok "ZIP v1.19.6 correcto"
ok "Destino: $TARGET"
ok "Servicio: $ODOO_SERVICE"
if [ "$MODE" = check ]; then
    echo "No se ha cambiado nada. Para instalar:"
    echo "sudo AUTO_CONFIRM=1 bash '$0' install"
    exit 0
fi

[ "$(id -u)" = 0 ] || bad "Para instalar hay que usar sudo."
if [ "${AUTO_CONFIRM:-0}" != 1 ]; then
    read -r -p "Escribe SI para instalar $VERSION: " ANSWER </dev/tty
    [ "$ANSWER" = SI ] || { echo "Cancelado."; exit 0; }
fi

STAMP="$(date +%Y-%m-%d_%H%M%S)"
BACKUP=""
mkdir -p "$BACKUP_DIR"
if [ -d "$TARGET" ]; then
    BACKUP="${BACKUP_DIR%/}/${MODULE}_$STAMP"
    cp -a "$TARGET" "$BACKUP"
    ok "Copia anterior: $BACKUP"
fi

rm -rf "$TARGET"
if ! cp -a "$SOURCE" "$TARGET"; then
    [ -n "$BACKUP" ] && cp -a "$BACKUP" "$TARGET"
    bad "Fallo al copiar; se ha restaurado la copia anterior."
fi
OWNER="$(stat -c '%U:%G' "$ADDONS_DIR" 2>/dev/null || true)"
if [ -n "$OWNER" ] && [ "$OWNER" != root:root ]; then
    chown -R "$OWNER" "$TARGET"
fi
ok "$MODULE $VERSION instalado"

systemctl restart "$ODOO_SERVICE"
for attempt in $(seq 1 30); do
    if systemctl is-active --quiet "$ODOO_SERVICE" && curl -fsS -m 3 -o /dev/null http://127.0.0.1:8069/web/login; then
        ok "$ODOO_SERVICE reiniciado y respondiendo"
        echo "Ahora: Aplicaciones > KOROSHI Monitor zonas > Actualizar; despues Ctrl+F5."
        exit 0
    fi
    sleep 2
done
bad "$ODOO_SERVICE no responde. Revisa: journalctl -u $ODOO_SERVICE -n 100 --no-pager"


