#!/usr/bin/env bash
# KOROSHI - Preparacion en Lecturas v3.7.2 (ubicacion, poner cantidad, notas, codigos alternativos, imprimir). Copia 1 modulo y
# reinicia UNA vez:
#   koroshi_preparacion v3.7.2   (ubicacion -> su linea, poner cantidad, notas de la OUT, codigos alternativos, imprimir)
#   En Odoo: Actualizar koroshi_preparacion. koroshi_pda_app (v1.0.0), koroshi_operarios (v2.5.0),
#   koroshi_faltantes y stock_barcode NO cambian.
# Valida el ZIP antes de tocar nada; si falla, no copia nada ni reinicia.
# Uso (con los 2 ZIP en /home/it_nath_group):
#   bash instalar_koroshi_preparacion_v3.7.2_2026-11-11.sh check
#   sudo AUTO_CONFIRM=1 bash instalar_koroshi_preparacion_v3.7.2_2026-11-11.sh install
# El reinicio corta Odoo ~1 minuto: hacerlo fuera de horas, sin nadie validando en las PDA.
set -euo pipefail

MODE="${1:-check}"
ZIP_DIR="${ZIP_DIR:-/home/it_nath_group}"
ADDONS_DIR="${ADDONS_DIR:-/opt/nath-erp/nath/enterprise-addons}"
ODOO_SERVICE="${ODOO_SERVICE:-nath-erp}"
BACKUP_DIR="${BACKUP_DIR:-/opt/nath-erp/copias_modulos}"
TMP="$(mktemp -d /tmp/koroshi_preparacion.XXXXXX)"
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
    "koroshi_preparacion|$ZIP_DIR/20261111_koroshi_preparacion_v3.7.2.zip|13.0.3.7.2"
)

echo "KOROSHI - Preparacion en Lecturas v3.7.2 ($([ "$MODE" = install ] && echo 'MODO INSTALAR' || echo 'MODO COMPROBACION'))"

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
echo "--- koroshi_faltantes (no se toca) ---"
if [ -d "$ADDONS_DIR/koroshi_faltantes" ]; then
    falt="$(grep -oE "'version': '[^']+'" "$ADDONS_DIR/koroshi_faltantes/__manifest__.py" 2>/dev/null || true)"
    echo "        en el servidor: ${falt:-sin version} (se queda igual)"
else
    bad "koroshi_faltantes no esta en el servidor: koroshi_preparacion lo necesita (valida con su validacion)"
fi
if [ -d "$ADDONS_DIR/koroshi_operarios" ] && grep -q "'version': '13.0.2.5.0'" "$ADDONS_DIR/koroshi_operarios/__manifest__.py"; then
    echo "        koroshi_operarios: v2.5.0 en el servidor (no se toca)"
else
    bad "koroshi_operarios v2.5.0 no esta en el servidor: koroshi_preparacion v3.5 y koroshi_pda_app lo necesitan"
fi
for dep in koroshi_caja_existente stock_barcode; do
    if [ -d "$ADDONS_DIR/$dep" ] || find /opt/nath-erp /usr/lib/python3/dist-packages/odoo -maxdepth 4 -type d -name "$dep" 2>/dev/null | grep -q .; then
        echo "        $dep: presente (no se toca)"
    else
        yellow "        $dep: no encontrado en las rutas habituales (comprobar que esta instalado en Odoo)"
    fi
done

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
echo "  2. 'KOROSHI Preparacion en Lecturas' -> Actualizar  (v3.7.2; los parametros activa / empleados no cambian)"
echo "  3. Ctrl+F5 en el PC y en las PDA (o cerrar y abrir la app Lecturas)."
echo "Vuelta atras: para la v3.5 copiar"
echo "  $BACKUP_DIR/koroshi_preparacion_$STAMP a $ADDONS_DIR/koroshi_preparacion, reiniciar y Actualizar."
