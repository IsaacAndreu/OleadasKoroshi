#!/usr/bin/env bash
# KOROSHI - Fase 2 de la auditoria 13/11: una sola cifra de productividad (14/11/2026).
#   koroshi_operarios   v2.12.0 (sobre la v2.11.1): resumen_operario_dia() = la u/h unica (uds / minutos efectivos).
#                       Campos nuevos parado y efectivo SOLO en su tabla koroshi_operario_tarea; la migracion de
#                       koroshi_informe 1.1.0 recalcula las tareas que hay. Fuera su correo diario (cron 204 y menu: Odoo los borra al
#                       actualizar). Reparto: Z- y tramo filtrados antes del limite de 400.
#   koroshi_informe     v1.1.0  (sobre la v1.0.1): usa resumen_operario_dia; unico correo diario.
#   koroshi_kpi         v1.6.0  (sobre la v1.5.0): horas de picking de los operarios si cubren el 80 %; «no cogido» no
#                       desaparece al validar; al actualizar solo recalcula 7 dias; hoja de carga con koroshi_delegacion.
#                       Campos nuevos SOLO en su tabla koroshi_kpi_dia.
#   koroshi_consumibles v1.4.0  (sobre la v1.3.0): totales con una consulta; no se traga el choque de concurrencia.
#   koroshi_monitor     v1.26.0 (sobre la v1.25.0, que incluye; si el servidor sigue en 1.24.0, entran las dos): u/h
#                       de resumen_operario_dia.
#   Nada en tablas de stock (stock.picking, stock.picking.type, stock.move.line).
#   En Odoo: Actualizar KOROSHI Operarios, KOROSHI KPI, KOROSHI Informe, KOROSHI Consumibles y KOROSHI Monitor.
# Valida los ZIP antes de tocar nada; si falla, no copia nada ni reinicia.
# Uso (con el ZIP en /home/it_nath_group):
#   bash instalar_koroshi_operarios_v2.12.0_informe_v1.1.0_kpi_v1.6.0_consumibles_v1.4.0_monitor_v1.26.0_2026-11-14.sh check
#   sudo AUTO_CONFIRM=1 bash instalar_koroshi_operarios_v2.12.0_informe_v1.1.0_kpi_v1.6.0_consumibles_v1.4.0_monitor_v1.26.0_2026-11-14.sh install
# El reinicio corta Odoo ~1 minuto: hacerlo fuera de horas, sin nadie validando en las PDA.
set -euo pipefail

MODE="${1:-check}"
ZIP_DIR="${ZIP_DIR:-/home/it_nath_group}"
ADDONS_DIR="${ADDONS_DIR:-/opt/nath-erp/nath/enterprise-addons}"
ODOO_SERVICE="${ODOO_SERVICE:-nath-erp}"
BACKUP_DIR="${BACKUP_DIR:-/opt/nath-erp/copias_modulos}"
TMP="$(mktemp -d /tmp/koroshi_fase2.XXXXXX)"
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
    "koroshi_operarios|$ZIP_DIR/20261114_koroshi_operarios_v2.12.0.zip|13.0.2.12.0"
    "koroshi_kpi|$ZIP_DIR/20261114_koroshi_kpi_v1.6.0.zip|13.0.1.6.0"
    "koroshi_informe|$ZIP_DIR/20261114_koroshi_informe_v1.1.0.zip|13.0.1.1.0"
    "koroshi_consumibles|$ZIP_DIR/20261114_koroshi_consumibles_v1.4.0.zip|13.0.1.4.0"
    "koroshi_monitor|$ZIP_DIR/20261114_koroshi_monitor_v1.26.0.zip|13.0.1.26.0"
)

echo "KOROSHI - Fase 2 productividad ($([ "$MODE" = install ] && echo 'MODO INSTALAR' || echo 'MODO COMPROBACION'))"

if ! command -v unzip >/dev/null 2>&1; then
    red "Falta unzip en el servidor."; exit 1
fi

echo
echo "== 1. Validar los ZIP antes de tocar nada =="
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
for dep in koroshi_preparacion koroshi_faltantes koroshi_menu; do
    if [ -d "$ADDONS_DIR/$dep" ]; then
        v="$(grep -oE "'version': '[^']+'" "$ADDONS_DIR/$dep/__manifest__.py" 2>/dev/null || true)"
        echo "        $dep: ${v:-sin version} (se queda igual)"
    else
        yellow "        $dep: no esta en $ADDONS_DIR (koroshi_informe necesita koroshi_preparacion y koroshi_menu)"
    fi
done

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
    yellow "Se copiaran los 5 modulos y se reiniciara Odoo UNA vez al final (~1 minuto sin Odoo)."
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
echo "== 4. Copiar los modulos sin reiniciar =="
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
echo "  2. Modo desarrollador > Aplicaciones, en este orden: Actualizar KOROSHI Operarios (v2.12.0), KOROSHI KPI"
echo "     (v1.6.0), KOROSHI Informe (v1.1.0), KOROSHI Consumibles (v1.4.0) y KOROSHI Monitor (v1.26.0)."
echo "     En el log: 'KOROSHI Informe 1.1.0: N tareas de operarios recalculadas'."
echo "  3. Ajustes > Tecnico > Acciones planificadas: ya no debe estar 'KOROSHI Operarios: informe diario por email'"
echo "     (id 204). Si sigue, desactivarla a mano. Queda 'KOROSHI Informe: correo de productividad' (id 213)."
echo "  4. Ctrl+F5 en el PC y en las PDA (Monitor y Lecturas)."
echo "  5. Comprobar: KOROSHI Operarios > Tareas enseña 'Min parado' y 'Min efectivos'; una ficha KPI dice"
echo "     'Horas de picking de'; el Monitor y el correo dan la misma u/h por operario."
echo "Vuelta atras: copiar $BACKUP_DIR/<modulo>_$STAMP de cada uno a $ADDONS_DIR, reiniciar y Actualizar."
echo "  (operarios 2.11.1, kpi 1.5.0, informe 1.0.1, consumibles 1.3.0, monitor 1.25.0 o 1.24.0). Los campos nuevos"
echo "  (parado, efectivo, pick_hp_operarios, cobertura_operarios, fuente_horas) se quedan en sus tablas sin molestar."
echo "  El cron 204 borrado no vuelve solo: si hiciera falta, se recrea al actualizar la 2.11.1."
