#!/usr/bin/env bash
# KOROSHI - Actividades v1.1.0 (registro de tiempo de manipulaciones + inversa con matriculas).
# NO esta en el servidor: esto lo INSTALA nuevo (comprobado el 14/11/2026).
# Copia 1 modulo y reinicia UNA vez:
#   koroshi_actividades v1.1.0   (depende de koroshi_operarios, que NO cambia; lee s4t.matricula si existe)
# Al instalarlo se crean 2 crons que solo escriben en las tablas del modulo:
#   - cada 5 min: pausa de las 13:00 y cierre de las 17:00 de los tramos de tiempo
#   - cada 15 min: uds del teorico de las cajas de inversa leidas antes de importar su matricula
# No anade campos a albaranes, movimientos, tipos de operacion ni empleados.
# Valida el ZIP antes de tocar nada; si falla, no copia nada ni reinicia.
# Uso (con el ZIP en /home/it_nath_group):
#   bash instalar_koroshi_actividades_v1.1.0_2026-11-14.sh check
#   sudo AUTO_CONFIRM=1 bash instalar_koroshi_actividades_v1.1.0_2026-11-14.sh install
# El reinicio corta Odoo ~1 minuto: hacerlo fuera de horas, sin nadie validando en las PDA.
set -euo pipefail

MODE="${1:-check}"
ZIP_DIR="${ZIP_DIR:-/home/it_nath_group}"
ADDONS_DIR="${ADDONS_DIR:-/opt/nath-erp/nath/enterprise-addons}"
ODOO_SERVICE="${ODOO_SERVICE:-nath-erp}"
BACKUP_DIR="${BACKUP_DIR:-/opt/nath-erp/copias_modulos}"
TMP="$(mktemp -d /tmp/koroshi_actividades.XXXXXX)"
STAMP="$(date +%Y-%m-%d_%H%M%S)"
ERRORS=0
MODULE="koroshi_actividades"
ZIP="$ZIP_DIR/20261114_koroshi_actividades_v1.1.0.zip"
VERSION="13.0.1.1.0"
BACKUP=""
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
if ! command -v unzip >/dev/null 2>&1; then
    red "Falta unzip en el servidor."; exit 1
fi

echo "KOROSHI - Actividades v1.1.0 ($([ "$MODE" = install ] && echo 'MODO INSTALAR' || echo 'MODO COMPROBACION'))"

echo
echo "== 1. Validar el ZIP antes de tocar nada =="
if [ ! -f "$ZIP" ]; then
    bad "No existe $ZIP"
elif ! unzip -tqq "$ZIP"; then
    bad "ZIP danado: $ZIP"
else
    unzip -l "$ZIP" > "$TMP/lista"
    if ! grep -qE "[[:space:]]${MODULE}/__manifest__\.py$" "$TMP/lista"; then
        bad "Falta ${MODULE}/__manifest__.py en el ZIP"
    else
        unzip -q "$ZIP" -d "$TMP"
        if grep -q "'version': '$VERSION'" "$TMP/$MODULE/__manifest__.py"; then
            ok "$MODULE: ZIP valido, version $VERSION"
        else
            bad "$MODULE: el manifest no tiene la version $VERSION"
        fi
    fi
fi
if [ -d "$ADDONS_DIR/$MODULE" ]; then
    actual="$(grep -oE "'version': '[^']+'" "$ADDONS_DIR/$MODULE/__manifest__.py" 2>/dev/null || true)"
    echo "        ahora en el servidor: ${actual:-sin version} -> se ACTUALIZARA"
else
    echo "        no esta en el servidor -> se INSTALARA nuevo"
fi
if [ -d "$ADDONS_DIR/koroshi_operarios" ]; then
    ope="$(grep -oE "'version': '[^']+'" "$ADDONS_DIR/koroshi_operarios/__manifest__.py" 2>/dev/null || true)"
    echo "        koroshi_operarios en el servidor: ${ope:-sin version} (lo necesita; no se toca)"
else
    bad "koroshi_operarios no esta en $ADDONS_DIR: koroshi_actividades lo necesita"
fi

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
echo "== 3. Copia de seguridad =="
mkdir -p "$BACKUP_DIR"
OWNER="$(stat -c '%U:%G' "$ADDONS_DIR" 2>/dev/null || true)"
if [ -d "$ADDONS_DIR/$MODULE" ]; then
    BACKUP="$BACKUP_DIR/${MODULE}_$STAMP"
    cp -a "$ADDONS_DIR/$MODULE" "$BACKUP"
    ok "Copia $MODULE: $BACKUP"
else
    yellow "   $MODULE es nuevo; no habia copia anterior"
fi

echo
echo "== 4. Copiar el modulo sin reiniciar =="
if ! rm -rf "${ADDONS_DIR:?}/$MODULE" || ! cp -a "$TMP/$MODULE" "$ADDONS_DIR/$MODULE"; then
    red "Error copiando el modulo. Restaurando como estaba..."
    rm -rf "${ADDONS_DIR:?}/$MODULE"
    if [ -n "$BACKUP" ] && [ -d "$BACKUP" ]; then cp -a "$BACKUP" "$ADDONS_DIR/$MODULE"; fi
    red "No se ha reiniciado Odoo porque la copia no termino bien."
    exit 1
fi
if [ -n "$OWNER" ] && [ "$OWNER" != 'root:root' ]; then chown -R "$OWNER" "$ADDONS_DIR/$MODULE"; fi
ok "$MODULE copiado"

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
    red "Para volver atras: copia $BACKUP a $ADDONS_DIR/$MODULE y reinicia."
    exit 1
fi
green "Odoo reiniciado y respondiendo."
echo
echo "Ahora en Odoo (Aplicaciones, quitando el filtro 'Aplicaciones'):"
echo "  1. Actualizar lista de aplicaciones"
echo "  2. 'KOROSHI Actividades (registro de tiempo)' -> Instalar (v1.1.0)"
echo "  3. Ctrl+F5. App nueva 'Actividades' en la pantalla de inicio y menu Inventario > KOROSHI Operarios >"
echo "     Actividades (manipulaciones). Los informes los ve el grupo 'KOROSHI Operarios: ver productividad'."
echo "  4. Prueba: pasar una tarjeta OP..., tocar 'Inversa', leer una matricula de s4t.matricula (p. ej. CJ080000717)."
echo "Vuelta atras: en Aplicaciones, Desinstalar 'KOROSHI Actividades' (solo borra sus tablas), y borrar $ADDONS_DIR/$MODULE."
