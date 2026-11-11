#!/usr/bin/env bash
# KOROSHI Monitor v1.19.2 - actualizador AUTONOMO (11/11/2026).
# Deja este script y 20261111_koroshi_monitor_v1.19.2.zip en /home/it_nath_group y ejecuta:
#   sudo bash actualizar_koroshi_monitor_v1.19.2_autonomo.sh check
#   sudo AUTO_CONFIRM=1 bash actualizar_koroshi_monitor_v1.19.2_autonomo.sh install
#
# Despues: Odoo > Aplicaciones > KOROSHI Monitor zonas > Actualizar, y Ctrl+F5.
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ZIP_NAME="20261111_koroshi_monitor_v1.19.2.zip"
ZIP_DEF="$SCRIPT_DIR/$ZIP_NAME"
[ -f "$ZIP_DEF" ] || ZIP_DEF="/home/it_nath_group/$ZIP_NAME"

MODE="${1:-check}"
ZIP="${2:-$ZIP_DEF}"
MODULE="koroshi_monitor"
EXPECTED_VERSION="13.0.1.19.2"
ADDONS_DIR="${ADDONS_DIR:-/opt/nath-erp/nath/enterprise-addons}"
ODOO_SERVICE="${ODOO_SERVICE:-nath-erp}"
BACKUP_DIR="${BACKUP_DIR:-/opt/nath-erp/copias_modulos}"
TMP="$(mktemp -d /tmp/koroshi_monitor.XXXXXX)"
ERRORS=0
trap 'rm -rf "$TMP"' EXIT

red(){ printf '\033[31m%s\033[0m\n' "$*"; }
green(){ printf '\033[32m%s\033[0m\n' "$*"; }
yellow(){ printf '\033[33m%s\033[0m\n' "$*"; }
ok(){ green "   OK  $*"; }
bad(){ red "   MAL $*"; ERRORS=$((ERRORS + 1)); }
step(){ echo; echo "== $* =="; }

if [ "$MODE" != "check" ] && [ "$MODE" != "install" ]; then
    red "Modo incorrecto. Usa check o install."; exit 2
fi
if [ ! -f "$ZIP" ]; then
    red "No existe el ZIP: $ZIP"; exit 1
fi
if [ "$MODE" = "install" ] && [ "$(id -u)" != "0" ]; then
    red "Para instalar hay que usar sudo."; exit 1
fi
if ! command -v unzip >/dev/null 2>&1; then
    red "Falta unzip en el servidor."; exit 1
fi

echo "KOROSHI Monitor v1.19.2 ($([ "$MODE" = install ] && echo 'INSTALAR' || echo 'COMPROBAR'))"

step "1. Comprobar el ZIP"
if unzip -tqq "$ZIP"; then ok "ZIP legible: $ZIP"; else bad "El ZIP esta dañado"; fi
unzip -l "$ZIP" > "$TMP/zip-list.txt"
if grep -qE "[[:space:]]${MODULE}/__manifest__\.py$" "$TMP/zip-list.txt"; then
    ok "El ZIP contiene $MODULE"
else
    bad "Falta ${MODULE}/__manifest__.py dentro del ZIP"
fi
unzip -q "$ZIP" -d "$TMP"
SOURCE="$TMP/$MODULE"
if [ -d "$SOURCE" ]; then ok "Carpeta del modulo extraida"; else bad "No existe $SOURCE"; fi
if [ -f "$SOURCE/__manifest__.py" ] && grep -q "'version': '$EXPECTED_VERSION'" "$SOURCE/__manifest__.py"; then
    ok "Version correcta: $EXPECTED_VERSION"
else
    bad "El manifest no es la version $EXPECTED_VERSION"
fi
for required in controllers/envios.py static/src/js/envios.js static/src/css/envios.css static/src/js/monitor.js; do
    if [ -f "$SOURCE/$required" ]; then ok "Incluye $required"; else bad "Falta $required"; fi
done
if grep -q 'km-envios' "$SOURCE/static/src/js/monitor.js"; then
    ok "Incluye el boton de envios dentro del Monitor picking"
else
    bad "No aparece el boton km-envios en monitor.js"
fi

step "2. Comprobar Odoo y las rutas"
if systemctl show -p LoadState "$ODOO_SERVICE" 2>/dev/null | grep -q '=loaded$'; then
    if systemctl is-active --quiet "$ODOO_SERVICE"; then
        ok "Servicio $ODOO_SERVICE activo"
    else
        bad "Servicio $ODOO_SERVICE parado"
    fi
else
    bad "No existe el servicio $ODOO_SERVICE"
fi
if [ -d "$ADDONS_DIR" ]; then ok "Ruta de addons: $ADDONS_DIR"; else bad "No existe $ADDONS_DIR"; fi
if [ -f "$ADDONS_DIR/$MODULE/__manifest__.py" ]; then
    ok "Modulo actual encontrado: $ADDONS_DIR/$MODULE"
else
    yellow "El modulo no existe todavia; se instalara como nuevo."
fi

if [ "$ERRORS" -gt 0 ]; then
    red "RESULTADO: $ERRORS problema(s). No se ha cambiado nada."; exit 1
fi
if [ "$MODE" = "check" ]; then
    green "RESULTADO: comprobacion correcta. No se ha cambiado nada."
    echo "Para instalar: sudo AUTO_CONFIRM=1 bash '$0' install '$ZIP'"
    exit 0
fi

if [ "${AUTO_CONFIRM:-0}" != "1" ]; then
    yellow "Se hara una copia, se actualizara $MODULE y se reiniciara $ODOO_SERVICE."
    read -r -p "Escribe SI para continuar: " answer </dev/tty
    [ "$answer" = "SI" ] || { echo "Cancelado. No se ha cambiado nada."; exit 0; }
fi

step "3. Copia de seguridad e instalacion"
STAMP="$(date +%Y-%m-%d_%H%M%S)"
BACKUP=""
mkdir -p "$BACKUP_DIR"
if [ -d "$ADDONS_DIR/$MODULE" ]; then
    BACKUP="$BACKUP_DIR/${MODULE}_$STAMP"
    cp -a "$ADDONS_DIR/$MODULE" "$BACKUP"
    ok "Copia de seguridad: $BACKUP"
fi
rm -rf "$ADDONS_DIR/$MODULE"
if ! cp -a "$SOURCE" "$ADDONS_DIR/$MODULE"; then
    red "No se ha podido copiar la nueva version."
    if [ -n "$BACKUP" ] && [ -d "$BACKUP" ]; then
        rm -rf "$ADDONS_DIR/$MODULE"
        cp -a "$BACKUP" "$ADDONS_DIR/$MODULE"
        yellow "Se ha restaurado la copia anterior."
    fi
    exit 1
fi
OWNER="$(stat -c '%U:%G' "$ADDONS_DIR" 2>/dev/null || true)"
if [ -n "$OWNER" ] && [ "$OWNER" != 'root:root' ]; then
    chown -R "$OWNER" "$ADDONS_DIR/$MODULE"
fi
ok "$MODULE $EXPECTED_VERSION copiado en $ADDONS_DIR"

step "4. Reiniciar Odoo"
systemctl restart "$ODOO_SERVICE"
RESPONDE=0
for attempt in $(seq 1 30); do
    if systemctl is-active --quiet "$ODOO_SERVICE" && curl -fsS -m 3 -o /dev/null http://127.0.0.1:8069/web/login; then
        RESPONDE=1
        break
    fi
    sleep 2
done
if [ "$RESPONDE" = "1" ]; then
    green "$ODOO_SERVICE reiniciado y respondiendo."
    echo
    echo "ULTIMO PASO EN ODOO:"
    echo "  Aplicaciones > busca 'KOROSHI Monitor zonas' > Actualizar"
    echo "  Despues pulsa Ctrl+F5 en el navegador."
    [ -n "$BACKUP" ] && echo "  Copia anterior: $BACKUP"
else
    red "$ODOO_SERVICE no responde correctamente."
    echo "Revisa: sudo journalctl -u '$ODOO_SERVICE' -n 100 --no-pager"
    [ -n "$BACKUP" ] && echo "Copia para volver atras: $BACKUP"
    exit 1
fi
