#!/usr/bin/env bash
# KOROSHI - instala JUNTOS koroshi_monitor v1.18.2 y koroshi_caja_existente v1.2 con UN SOLO reinicio de Odoo (10/11/2026).
# Script autonomo: lleva dentro el instalador (no necesita actualizar_koroshi_modulo_desde_zip.sh).
# Los dos ZIP en la misma carpeta que este script o en /home/it_nath_group:
#   20261110_koroshi_monitor_v1.18.2.zip   20261110_koroshi_caja_existente_v1.2.zip
# Uso:
#   sudo bash actualizar_koroshi_monitor_v1.18.2_y_caja_existente_v1.2_un_reinicio.sh check
#   sudo AUTO_CONFIRM=1 bash actualizar_koroshi_monitor_v1.18.2_y_caja_existente_v1.2_un_reinicio.sh install
# install: primero comprueba los dos; si alguno falla no toca nada. Copia el monitor sin reiniciar y despues caja
# existente con el reinicio (30-60 s). Despues: Aplicaciones > actualizar los dos modulos.
set -euo pipefail
MODE="${1:-check}"
if [ "$MODE" != "check" ] && [ "$MODE" != "install" ]; then echo "Modo invalido. Usa check o install."; exit 2; fi
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
zip_de(){ if [ -f "$SCRIPT_DIR/$1" ]; then echo "$SCRIPT_DIR/$1"; else echo "/home/it_nath_group/$1"; fi; }
ZIP_MON="$(zip_de 20261110_koroshi_monitor_v1.18.2.zip)"
ZIP_CAJA="$(zip_de 20261110_koroshi_caja_existente_v1.2.zip)"
GEN="$(mktemp /tmp/koroshi_instalador.XXXXXX.sh)"
trap 'rm -f "$GEN"' EXIT
cat > "$GEN" <<'GENERICO'
#!/usr/bin/env bash
# Instalador seguro de un módulo KOROSHI empaquetado en ZIP.
# Uso: sudo bash actualizar_koroshi_modulo_desde_zip.sh check ZIP MODULO
#      sudo AUTO_CONFIRM=1 bash actualizar_koroshi_modulo_desde_zip.sh install ZIP MODULO
set -euo pipefail

MODE="${1:-check}"
ZIP="${2:-}"
MODULE="${3:-}"
ADDONS_DIR="${ADDONS_DIR:-/opt/nath-erp/nath/enterprise-addons}"
ODOO_SERVICE="${ODOO_SERVICE:-nath-erp}"
BACKUP_DIR="${BACKUP_DIR:-/opt/nath-erp/copias_modulos}"
TMP="$(mktemp -d /tmp/koroshi_zip.XXXXXX)"
ERRORS=0
trap 'rm -rf "$TMP"' EXIT

red(){ printf '\033[31m%s\033[0m\n' "$*"; }
green(){ printf '\033[32m%s\033[0m\n' "$*"; }
yellow(){ printf '\033[33m%s\033[0m\n' "$*"; }
ok(){ green "   OK  $*"; }
bad(){ red "   MAL $*"; ERRORS=$((ERRORS + 1)); }
step(){ echo; echo "== $* =="; }

if [ "$MODE" != "check" ] && [ "$MODE" != "install" ]; then
    red "Modo inválido. Usa check o install."; exit 2
fi
if [ -z "$ZIP" ] || [ -z "$MODULE" ]; then
    red "Uso: $0 check|install ZIP MODULO"; exit 2
fi
if [ ! -f "$ZIP" ]; then bad "No existe el ZIP: $ZIP"; exit 1; fi
if [ "$MODE" = "install" ] && [ "$(id -u)" != "0" ]; then
    red "Para instalar hay que usar sudo."; exit 1
fi
if ! command -v unzip >/dev/null 2>&1; then bad "Falta unzip en el servidor"; exit 1; fi

echo "KOROSHI - $MODULE ($([ "$MODE" = install ] && echo 'MODO INSTALAR' || echo 'MODO COMPROBACIÓN'))"
step "1. Comprobar ZIP"
if ! unzip -tqq "$ZIP"; then bad "El ZIP está dañado"; else ok "ZIP legible"; fi
unzip -l "$ZIP" > "$TMP/zip-list.txt"
if ! grep -qE "[[:space:]]${MODULE}/__manifest__\.py$" "$TMP/zip-list.txt"; then
    bad "El ZIP no contiene ${MODULE}/__manifest__.py"
else
    ok "Manifest encontrado para $MODULE"
fi
unzip -q "$ZIP" -d "$TMP"
SOURCE="$TMP/$MODULE"
if [ ! -d "$SOURCE" ]; then bad "No existe la carpeta $MODULE dentro del ZIP"; fi

step "2. Odoo y rutas"
if systemctl show -p LoadState "$ODOO_SERVICE" 2>/dev/null | grep -q '=loaded$'; then
    if systemctl is-active --quiet "$ODOO_SERVICE"; then ok "Servicio $ODOO_SERVICE activo"; else bad "Servicio $ODOO_SERVICE parado"; fi
else
    bad "No existe el servicio $ODOO_SERVICE"
fi
if [ -d "$ADDONS_DIR" ]; then ok "Ruta de addons: $ADDONS_DIR"; else bad "No existe $ADDONS_DIR"; fi
if [ -f "$ADDONS_DIR/$MODULE/__manifest__.py" ]; then
    ok "Módulo actual encontrado: $ADDONS_DIR/$MODULE"
else
    yellow "El módulo aún no existe: se instalará como nuevo"
fi

if [ "$ERRORS" -gt 0 ]; then
    red "RESULTADO: $ERRORS problema(s). No se ha tocado nada."; exit 1
fi
if [ "$MODE" = "check" ]; then
    green "RESULTADO: comprobación correcta. No se ha tocado nada."
    echo "Para instalar: sudo AUTO_CONFIRM=1 bash $0 install '$ZIP' '$MODULE'"
    exit 0
fi

if [ "${AUTO_CONFIRM:-0}" != "1" ]; then
    yellow "Se actualizará $MODULE y se reiniciará $ODOO_SERVICE una sola vez."
    read -r -p "Escribe SI para continuar: " answer </dev/tty
    [ "$answer" = "SI" ] || { echo "Cancelado. No se ha tocado nada."; exit 0; }
fi

step "3. Copia y actualización"
STAMP="$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
if [ -d "$ADDONS_DIR/$MODULE" ]; then
    cp -a "$ADDONS_DIR/$MODULE" "$BACKUP_DIR/${MODULE}_$STAMP"
    ok "Copia de seguridad: $BACKUP_DIR/${MODULE}_$STAMP"
fi
rm -rf "$ADDONS_DIR/$MODULE"
cp -a "$SOURCE" "$ADDONS_DIR/$MODULE"
OWNER="$(stat -c '%U:%G' "$ADDONS_DIR" 2>/dev/null || true)"
if [ -n "$OWNER" ] && [ "$OWNER" != 'root:root' ]; then chown -R "$OWNER" "$ADDONS_DIR/$MODULE"; fi
ok "$MODULE instalado en $ADDONS_DIR"

if [ "${NO_RESTART:-0}" = "1" ]; then
    green "${MODULE} preparado; se omitirá el reinicio porque forma parte de una actualización agrupada."
    exit 0
fi

step "4. Reinicio único"
systemctl restart "$ODOO_SERVICE"
for attempt in $(seq 1 30); do
    if systemctl is-active --quiet "$ODOO_SERVICE" && curl -fsS -m 3 -o /dev/null http://127.0.0.1:8069/web/login; then break; fi
    sleep 2
done
if systemctl is-active --quiet "$ODOO_SERVICE"; then
    green "$ODOO_SERVICE reiniciado y respondiendo."
    echo "Ahora pulsa Actualizar en Aplicaciones para $MODULE y haz Ctrl+F5."
else
    red "$ODOO_SERVICE no ha arrancado. Consulta: sudo journalctl -u $ODOO_SERVICE -n 80 --no-pager"
    exit 1
fi
GENERICO

echo "######## 1/2 COMPROBAR koroshi_monitor ########"
bash "$GEN" check "$ZIP_MON" koroshi_monitor
echo "######## 2/2 COMPROBAR koroshi_caja_existente ########"
bash "$GEN" check "$ZIP_CAJA" koroshi_caja_existente
if [ "$MODE" = "check" ]; then
    echo; echo "LOS DOS CORRECTOS. No se ha tocado nada."
    echo "Para instalar: sudo AUTO_CONFIRM=1 bash $0 install"
    exit 0
fi
echo; echo "######## INSTALAR koroshi_monitor (sin reiniciar) ########"
NO_RESTART=1 AUTO_CONFIRM=1 bash "$GEN" install "$ZIP_MON" koroshi_monitor
echo; echo "######## INSTALAR koroshi_caja_existente (y reinicio unico) ########"
AUTO_CONFIRM="${AUTO_CONFIRM:-0}" bash "$GEN" install "$ZIP_CAJA" koroshi_caja_existente
echo; echo "HECHO: los dos copiados y Odoo reiniciado una vez. Ahora actualizar los dos en Aplicaciones."
