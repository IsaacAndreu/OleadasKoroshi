#!/usr/bin/env bash
# KOROSHI - Monitor v1.23.2 (Excel XPO: solo OUT con su propia etiqueta XPO).
# Copia 1 modulo y reinicia UNA vez:
#   koroshi_monitor v1.23.2  (solo cambia el Excel; Actualizar el modulo igualmente)
#   En Odoo: Actualizar koroshi_monitor. Ningun otro modulo cambia.
# Valida el ZIP antes de tocar nada; si falla, no copia nada ni reinicia.
# Uso (con el ZIP en /home/it_nath_group):
#   bash instalar_koroshi_monitor_v1.23.2_2026-11-12.sh check
#   sudo AUTO_CONFIRM=1 bash instalar_koroshi_monitor_v1.23.2_2026-11-12.sh install
# El reinicio corta Odoo ~1 minuto: hacerlo fuera de horas.
set -euo pipefail

MODE="${1:-check}"
ZIP_DIR="${ZIP_DIR:-/home/it_nath_group}"
ADDONS_DIR="${ADDONS_DIR:-/opt/nath-erp/nath/enterprise-addons}"
ODOO_SERVICE="${ODOO_SERVICE:-nath-erp}"
BACKUP_DIR="${BACKUP_DIR:-/opt/nath-erp/copias_modulos}"
TMP="$(mktemp -d /tmp/koroshi_monitor.XXXXXX)"
STAMP="$(date +%Y-%m-%d_%H%M%S)"
ERRORS=0
BACKUPS=()
trap 'rm -rf "$TMP"' EXIT

red(){ printf '\033[31m%s\033[0m\n' "$*"; }
green(){ printf '\033[32m%s\033[0m\n' "$*"; }
yellow(){ printf '\033[33m%s\033[0m\n' "$*"; }
ok(){ green "   OK  $*"; }
bad(){ red "   MAL $*"; ERRORS=$((ERRORS + 1)); }

if [ "$MODE" != "check" ] && [ "$MODE" != "install" ]; then
    red "Uso: $0 check|install"; exit 2
fi
if [ "$MODE" = "install" ] && [ "$(id -u)" != "0" ]; then
    red "Para instalar hay que usar sudo."; exit 1
fi

# modulo|zip|version esperada en el manifest
declare -a MODULES=(
    "koroshi_monitor|$ZIP_DIR/20261112_koroshi_monitor_v1.23.2.zip|13.0.1.23.2"
)

echo "KOROSHI - Monitor v1.23.2 ($([ "$MODE" = install ] && echo 'MODO INSTALAR' || echo 'MODO COMPROBACION'))"

if ! command -v unzip >/dev/null 2>&1; then
    red "Falta unzip en el servidor."; exit 1
fi

echo
echo "== 1. Validar el ZIP antes de tocar nada =="
for entry in "${MODULES[@]}"; do
    IFS='|' read -r module zip version <<< "$entry"
    echo "--- $module ---"
    if [ ! -f "$zip" ]; then bad "No existe $zip"; continue; fi
    if ! unzip -tqq "$zip"; then bad "ZIP danado: $zip"; continue; fi
    unzip -l "$zip" > "$TMP/${module}.list"
    if ! grep -qE "[[:space:]]${module}/__manifest__\.py$" "$TMP/${module}.list"; then
        bad "Falta ${module}/__manifest__.py en el ZIP"; continue
    fi
    unzip -q "$zip" -d "$TMP"
    if [ ! -f "$TMP/$module/__manifest__.py" ]; then
        bad "No se pudo extraer $module"; continue
    fi
    if grep -q "'version': '$version'" "$TMP/$module/__manifest__.py"; then
        ok "$module: ZIP valido, version $version"
    else
        bad "$module: el manifest no tiene la version $version"
    fi
    if [ -d "$ADDONS_DIR/$module" ]; then
        actual="$(grep -oE "'version': '[^']+'" "$ADDONS_DIR/$module/__manifest__.py" 2>/dev/null || true)"
        echo "        ahora en el servidor: ${actual:-sin version} -> se ACTUALIZARA"
    else
        echo "        no esta en el servidor -> se INSTALARA nuevo"
    fi
done

echo
echo "--- dependencias (no se tocan) ---"
for dep in koroshi_warehouse_map stock_picking_batch; do
    if [ -d "$ADDONS_DIR/$dep" ] || find /opt/nath-erp /usr/lib/python3/dist-packages/odoo -maxdepth 4 -type d -name "$dep" 2>/dev/null | grep -q .; then
        echo "        $dep: presente"
    else
        yellow "        $dep: no encontrado en las rutas habituales (comprobar que esta instalado en Odoo)"
    fi
done
if python3 -c "import xlsxwriter" 2>/dev/null; then echo "        xlsxwriter: presente"; else yellow "        xlsxwriter: no lo veo con python3 del sistema (ya lo usaba la v1.19)"; fi

echo
echo "== 2. Validar Odoo y la ruta de addons =="
if systemctl show -p LoadState "$ODOO_SERVICE" 2>/dev/null | grep -q '=loaded$'; then
    systemctl is-active --quiet "$ODOO_SERVICE" && ok "Servicio $ODOO_SERVICE activo" || bad "Servicio $ODOO_SERVICE no esta activo"
else
    bad "No existe el servicio $ODOO_SERVICE"
fi
[ -d "$ADDONS_DIR" ] && ok "Ruta de addons: $ADDONS_DIR" || bad "No existe $ADDONS_DIR"

if [ "$ERRORS" -gt 0 ]; then
    red "RESULTADO: $ERRORS problema(s). No se ha tocado nada ni se ha reiniciado Odoo."; exit 1
fi
if [ "$MODE" = "check" ]; then
    green "RESULTADO: todo correcto. No se ha tocado nada ni se ha reiniciado Odoo."
    echo "Para instalar: sudo AUTO_CONFIRM=1 bash $0 install"
    exit 0
fi

if [ "${AUTO_CONFIRM:-0}" != "1" ]; then
    echo
    yellow "Se copiara el modulo y se reiniciara Odoo UNA vez al final (~1 minuto sin Odoo)."
    read -r -p "Escribe SI para continuar: " answer </dev/tty
    [ "$answer" = "SI" ] || { echo "Cancelado. No se ha tocado nada."; exit 0; }
fi

echo
echo "== 3. Copias de seguridad =="
mkdir -p "$BACKUP_DIR"
OWNER="$(stat -c '%U:%G' "$ADDONS_DIR" 2>/dev/null || true)"
for entry in "${MODULES[@]}"; do
    IFS='|' read -r module zip version <<< "$entry"
    if [ -d "$ADDONS_DIR/$module" ]; then
        backup="$BACKUP_DIR/${module}_$STAMP"
        cp -a "$ADDONS_DIR/$module" "$backup"
        BACKUPS+=("$module|$backup")
        ok "Copia $module: $backup"
    else
        BACKUPS+=("$module|")
        yellow "   $module es nuevo; no habia copia anterior"
    fi
done

echo
echo "== 4. Copiar el modulo sin reiniciar =="
rollback(){
    red "Error copiando el modulo. Restaurando como estaba..."
    for pair in "${BACKUPS[@]}"; do
        IFS='|' read -r module backup <<< "$pair"
        rm -rf "${ADDONS_DIR:?}/$module"
        if [ -n "$backup" ] && [ -d "$backup" ]; then cp -a "$backup" "$ADDONS_DIR/$module"; fi
    done
}
for entry in "${MODULES[@]}"; do
    IFS='|' read -r module zip version <<< "$entry"
    if ! rm -rf "${ADDONS_DIR:?}/$module" || ! cp -a "$TMP/$module" "$ADDONS_DIR/$module"; then
        rollback
        red "No se ha reiniciado Odoo porque la copia no termino bien."
        exit 1
    fi
    if [ -n "$OWNER" ] && [ "$OWNER" != 'root:root' ]; then chown -R "$OWNER" "$ADDONS_DIR/$module"; fi
    ok "$module copiado"
done

echo
echo "== 5. UNICO reinicio de Odoo =="
systemctl restart "$ODOO_SERVICE"
ready=0
for attempt in $(seq 1 30); do
    if systemctl is-active --quiet "$ODOO_SERVICE" && curl -fsS -m 3 -o /dev/null http://127.0.0.1:8069/web/login; then
        ready=1
        break
    fi
    sleep 2
done
if [ "$ready" != "1" ]; then
    red "Odoo no responde tras el reinicio. Consulta: sudo journalctl -u $ODOO_SERVICE -n 80 --no-pager"
    red "Para volver atras: copia las carpetas de $BACKUP_DIR/*_$STAMP a $ADDONS_DIR, borra las nuevas y reinicia."
    exit 1
fi
green "Odoo reiniciado y respondiendo."
echo
echo "Ahora en Odoo (Aplicaciones, quitando el filtro 'Aplicaciones'):"
echo "  1. Actualizar lista de aplicaciones"
echo "  2. 'KOROSHI Monitor zonas' -> Actualizar  (v1.23.2; XPO solo OUT con etiqueta propia)"
echo "  3. Ctrl+F5 en el PC de oficina y abrir KOROSHI · Operaciones > Consulta de envios."
echo "Vuelta atras (v1.23.1): copiar"
echo "  $BACKUP_DIR/koroshi_monitor_$STAMP a $ADDONS_DIR/koroshi_monitor, reiniciar y Actualizar."
