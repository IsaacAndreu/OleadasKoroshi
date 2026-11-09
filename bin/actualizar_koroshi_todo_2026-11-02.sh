#!/usr/bin/env bash
# Actualiza mapa, monitor y consumibles y reinicia Odoo UNA sola vez.
# No llama a otros instaladores y no reinicia durante la copia de cada módulo.
# Uso:
#   sudo bash actualizar_koroshi_todo_2026-11-02.sh check
#   sudo AUTO_CONFIRM=1 bash actualizar_koroshi_todo_2026-11-02.sh install
set -euo pipefail

MODE="${1:-check}"
ADDONS_DIR="${ADDONS_DIR:-/opt/nath-erp/nath/enterprise-addons}"
ODOO_SERVICE="${ODOO_SERVICE:-nath-erp}"
BACKUP_DIR="${BACKUP_DIR:-/opt/nath-erp/copias_modulos}"
TMP="$(mktemp -d /tmp/koroshi_all.XXXXXX)"
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

declare -a MODULES=(
    "koroshi_warehouse_map|/home/it_nath_group/20261102_warehouse_map_odoo13_v39.zip"
    "koroshi_monitor|/home/it_nath_group/20261102_koroshi_monitor_v1.16.zip"
    "koroshi_consumibles|/home/it_nath_group/20261102_koroshi_consumibles_v1.1.zip"
)

echo "KOROSHI - actualización agrupada ($([ "$MODE" = install ] && echo 'MODO INSTALAR' || echo 'MODO COMPROBACIÓN'))"

if ! command -v unzip >/dev/null 2>&1; then
    red "Falta unzip en el servidor."; exit 1
fi

echo
echo "== 1. Validar todos los ZIP antes de tocar nada =="
for entry in "${MODULES[@]}"; do
    IFS='|' read -r module zip <<< "$entry"
    echo "--- $module ---"
    if [ ! -f "$zip" ]; then bad "No existe $zip"; continue; fi
    if ! unzip -tqq "$zip"; then bad "ZIP dañado: $zip"; continue; fi
    unzip -l "$zip" > "$TMP/${module}.list"
    if ! grep -qE "[[:space:]]${module}/__manifest__\.py$" "$TMP/${module}.list"; then
        bad "Falta ${module}/__manifest__.py en el ZIP"; continue
    fi
    unzip -q "$zip" -d "$TMP"
    if [ ! -f "$TMP/$module/__manifest__.py" ]; then
        bad "No se pudo extraer $module"; continue
    fi
    ok "$module: ZIP válido y manifest encontrado"
done

echo
echo "== 2. Validar Odoo y la ruta de addons =="
if systemctl show -p LoadState "$ODOO_SERVICE" 2>/dev/null | grep -q '=loaded$'; then
    systemctl is-active --quiet "$ODOO_SERVICE" && ok "Servicio $ODOO_SERVICE activo" || bad "Servicio $ODOO_SERVICE no está activo"
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
    yellow "Se copiarán los tres módulos y se hará un único reinicio al final."
    read -r -p "Escribe SI para continuar: " answer </dev/tty
    [ "$answer" = "SI" ] || { echo "Cancelado. No se ha tocado nada."; exit 0; }
fi

echo
echo "== 3. Crear copias de seguridad de los tres módulos =="
mkdir -p "$BACKUP_DIR"
OWNER="$(stat -c '%U:%G' "$ADDONS_DIR" 2>/dev/null || true)"
for entry in "${MODULES[@]}"; do
    IFS='|' read -r module zip <<< "$entry"
    if [ -d "$ADDONS_DIR/$module" ]; then
        backup="$BACKUP_DIR/${module}_$STAMP"
        cp -a "$ADDONS_DIR/$module" "$backup"
        BACKUPS+=("$module|$backup")
        ok "Copia $module: $backup"
    else
        BACKUPS+=("$module|")
        yellow "$module es nuevo; no había copia anterior"
    fi
done

echo
echo "== 4. Copiar los tres módulos sin reiniciar =="
rollback(){
    red "Error copiando módulos. Intentando restaurar las copias anteriores..."
    for pair in "${BACKUPS[@]}"; do
        IFS='|' read -r module backup <<< "$pair"
        rm -rf "$ADDONS_DIR/$module"
        if [ -n "$backup" ] && [ -d "$backup" ]; then cp -a "$backup" "$ADDONS_DIR/$module"; fi
    done
}
for entry in "${MODULES[@]}"; do
    IFS='|' read -r module zip <<< "$entry"
    if ! rm -rf "$ADDONS_DIR/$module" || ! cp -a "$TMP/$module" "$ADDONS_DIR/$module"; then
        rollback
        red "No se ha reiniciado Odoo porque la copia no terminó correctamente."
        exit 1
    fi
    if [ -n "$OWNER" ] && [ "$OWNER" != 'root:root' ]; then chown -R "$OWNER" "$ADDONS_DIR/$module"; fi
    ok "$module copiado"
done

echo
echo "== 5. ÚNICO reinicio de Odoo =="
systemctl restart "$ODOO_SERVICE"
ready=0
for attempt in $(seq 1 30); do
    if systemctl is-active --quiet "$ODOO_SERVICE" && curl -fsS -m 3 -o /dev/null http://127.0.0.1:8069/web/login; then
        ready=1
        break
    fi
    sleep 2
done
if [ "$ready" = "1" ]; then
    green "Odoo reiniciado y respondiendo correctamente."
    echo "Ahora actualiza los tres módulos desde Aplicaciones y haz Ctrl+F5."
else
    red "Odoo no responde tras el único reinicio. Consulta: sudo journalctl -u $ODOO_SERVICE -n 80 --no-pager"
    exit 1
fi
