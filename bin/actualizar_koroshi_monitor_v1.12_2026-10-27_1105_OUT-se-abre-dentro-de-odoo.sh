#!/usr/bin/env bash
# =============================================================================
# ACTUALIZAR el modulo KOROSHI Monitor (koroshi_monitor), ya instalado, a la version 1.12 que va dentro de este
# script (clic en una OUT la abre dentro de Odoo). Con comprobaciones antes de tocar nada.
#
# Uso (en el servidor de Odoo):
#   sudo bash ESTE_SCRIPT.sh            -> SOLO COMPRUEBA. No escribe ni reinicia nada.
#   sudo INSTALAR=1 bash ESTE_SCRIPT.sh -> comprueba y, si todo esta bien y escribes SI, actualiza.
#
# Que comprueba: Odoo corriendo, su configuracion y el servicio; que cada modulo esta instalado en la
# base de datos y SOLO en la carpeta de modulos; que los ficheros nuevos estan enteros, los .py compilan
# y los .xml estan bien; espacio en disco. Si algo falla, para y no toca nada.
# Que hace al actualizar: copia de cada carpeta actual en /opt/nath-erp/copias_modulos/<modulo>_<fecha>,
# pone las nuevas, reinicia Odoo (las PDA ~1 minuto sin conexion) y espera a que responda. Despues hay que
# pulsar Actualizar en el modulo en Odoo (Aplicaciones), o decirmelo y lo hago yo.
# =============================================================================
set -uo pipefail

MODULOS="koroshi_monitor"
ADDONS_DIR="${ADDONS_DIR:-/opt/nath-erp/nath/enterprise-addons}"
ODOO_SERVICE="${ODOO_SERVICE:-nath-erp}"
ODOO_DB="${ODOO_DB:-NATH_PRODUCTION}"
INSTALAR="${INSTALAR:-0}"
COPIAS=/opt/nath-erp/copias_modulos
TMP=$(mktemp -d /tmp/koroshi_act.XXXXXX)
ERRORES=0
AVISOS=0

rojo() { printf '\033[31m%s\033[0m\n' "$*"; }
verde() { printf '\033[32m%s\033[0m\n' "$*"; }
amarillo() { printf '\033[33m%s\033[0m\n' "$*"; }
ok() { verde "   OK  $*"; }
mal() { rojo "   MAL $*"; ERRORES=$((ERRORES + 1)); }
aviso() { amarillo "   OJO $*"; AVISOS=$((AVISOS + 1)); }
paso() { echo; echo "== $* =="; }
version() { grep -oE "'[0-9]+\.[0-9.]+'" "$1/__manifest__.py" 2>/dev/null | head -1; }
trap 'rm -rf "$TMP"' EXIT

if [ "$(id -u)" != "0" ]; then rojo "Hay que ejecutarlo con sudo:  sudo bash $0"; exit 1; fi
echo "KOROSHI - actualizar Monitor v1.12 ($( [ "$INSTALAR" = "1" ] && echo 'MODO ACTUALIZAR' || echo 'MODO SOLO COMPROBAR: no se cambia nada'))"

paso "0. Modulos que van dentro del script"
if ! sed -n '/^__KOROSHI_TGZ__$/,$p' "$0" | sed '1d' | base64 -d > "$TMP/m.tgz" 2>/dev/null || ! tar -xzf "$TMP/m.tgz" -C "$TMP" 2>/dev/null; then
    rojo "   El paquete de dentro del script esta danado (copia incompleta?)"; exit 1
fi
for m in $MODULOS; do
    if [ -f "$TMP/$m/__manifest__.py" ]; then ok "$m nuevo: version $(version "$TMP/$m")"; else mal "falta $m dentro del script"; fi
done

paso "1. Odoo, configuracion y servicio"
PROC=$(ps -eo args | grep -E 'odoo-bin|openerp-server' | grep -v grep | head -1 || true)
[ -n "$PROC" ] && ok "Odoo corriendo" || mal "no encuentro ningun proceso odoo-bin corriendo"
ODOO_USER=$(ps -eo user:32,args | grep -E 'odoo-bin|openerp-server' | grep -v grep | head -1 | awk '{print $1}' || true)
ODOO_PY=$(echo "$PROC" | awk '{print $1}'); case "$ODOO_PY" in *python*) : ;; *) ODOO_PY=python3 ;; esac
[ -z "${ODOO_CONF:-}" ] && ODOO_CONF=$(echo "$PROC" | grep -oE '(-c|--config)[ =][^ ]+' | head -1 | sed -E 's/^(-c|--config)[ =]//' || true)
if [ -n "${ODOO_CONF:-}" ] && [ -r "$ODOO_CONF" ]; then ok "configuracion: $ODOO_CONF"; else mal "no encuentro la configuracion (forzar con ODOO_CONF=...)"; ODOO_CONF=""; fi
if systemctl show -p LoadState "$ODOO_SERVICE" 2>/dev/null | grep -q "=loaded$"; then
    systemctl is-active --quiet "$ODOO_SERVICE" && ok "servicio $ODOO_SERVICE en marcha" || mal "el servicio $ODOO_SERVICE no esta en marcha"
else
    mal "no existe el servicio $ODOO_SERVICE (forzar con ODOO_SERVICE=...)"
fi

paso "2. Modulos instalados ahora (carpetas)"
ADDONS_PATH=""
[ -n "$ODOO_CONF" ] && ADDONS_PATH=$(grep -E '^\s*addons_path\s*=' "$ODOO_CONF" | head -1 | sed -E 's/^[^=]*=\s*//' | tr -d ' ')
DUENO=$(stat -c '%U:%G' "$ADDONS_DIR" 2>/dev/null || echo "")
for m in $MODULOS; do
    for d in $(echo "$ADDONS_PATH" | tr ',' ' '); do
        if [ -e "$d/$m" ] && [ "$(readlink -f "$d")" != "$(readlink -f "$ADDONS_DIR")" ]; then mal "hay otro $m en $d: no se cual usa Odoo, no toco nada"; fi
    done
    if [ -f "$ADDONS_DIR/$m/__manifest__.py" ]; then ok "$m en $ADDONS_DIR (version actual $(version "$ADDONS_DIR/$m"))"; else mal "$m no esta en $ADDONS_DIR"; fi
done

paso "3. Base de datos $ODOO_DB"
conf() { [ -n "$ODOO_CONF" ] && grep -E "^\s*$1\s*=" "$ODOO_CONF" | head -1 | sed -E 's/^[^=]*=\s*//' | tr -d ' ' || true; }
DB_HOST=$(conf db_host); DB_PORT=$(conf db_port); DB_USER=$(conf db_user); DB_PASS=$(conf db_password)
[ "$DB_HOST" = "False" ] && DB_HOST=""; [ "$DB_PORT" = "False" ] && DB_PORT=""; [ "$DB_PASS" = "False" ] && DB_PASS=""
sql() {
    if [ -n "$DB_HOST" ] || [ -n "$DB_PASS" ]; then
        PGPASSWORD="$DB_PASS" psql -X -A -t ${DB_HOST:+-h "$DB_HOST"} ${DB_PORT:+-p "$DB_PORT"} -U "${DB_USER:-odoo}" -d "$ODOO_DB" -c "$1" 2>/dev/null
    else
        sudo -u "${DB_USER:-${ODOO_USER:-odoo}}" psql -X -A -t -d "$ODOO_DB" -c "$1" 2>/dev/null
    fi
}
if R=$(sql "select 1"); [ "$R" = "1" ]; then
    ok "conecto con la base de datos (sin ensenar contrasenas)"
    for m in $MODULOS; do
        E=$(sql "select state from ir_module_module where name='$m'")
        [ "$E" = "installed" ] && ok "$m instalado en Odoo" || mal "$m no esta instalado (estado '$E')"
    done
else
    aviso "no puedo conectar con la base de datos por psql: no compruebo el estado de los modulos"
fi

paso "4. Codigo nuevo"
if "$ODOO_PY" -c "import sys" 2>/dev/null; then
    for f in $(cd "$TMP" && find $MODULOS -name '*.py'); do
        "$ODOO_PY" -m py_compile "$TMP/$f" 2>"$TMP/err" && ok "compila $f" || mal "no compila $f: $(cat "$TMP/err")"
    done
    for f in $(cd "$TMP" && find $MODULOS -name '*.xml'); do
        "$ODOO_PY" -c "import sys, xml.dom.minidom as m; m.parse(sys.argv[1])" "$TMP/$f" 2>/dev/null && ok "xml bien: $f" || mal "xml mal formado: $f"
    done
else
    aviso "no encuentro el Python de Odoo; no compruebo el codigo"
fi

paso "5. Espacio en disco"
LIBRE=$(df -Pk "$ADDONS_DIR" 2>/dev/null | awk 'NR==2 {print $4}')
if [ -n "$LIBRE" ] && [ "$LIBRE" -gt 51200 ]; then ok "$((LIBRE / 1024)) MB libres"; else mal "poco espacio libre en $ADDONS_DIR"; fi

echo
if [ "$ERRORES" -gt 0 ]; then rojo "RESULTADO: $ERRORES problema(s). No se ha tocado nada. Pasame lo que ha salido."; exit 1; fi
if [ "$AVISOS" -gt 0 ]; then verde "RESULTADO: todo bien ($AVISOS aviso(s) en amarillo). No se ha tocado nada."; else verde "RESULTADO: todo bien. No se ha tocado nada."; fi
if [ "$INSTALAR" != "1" ]; then echo "Para actualizar:  sudo INSTALAR=1 bash $0"; exit 0; fi

echo
amarillo "Se van a cambiar $MODULOS por las versiones nuevas (con copia) y REINICIAR $ODOO_SERVICE (las PDA ~1 minuto sin conexion)."
read -r -p "Escribe SI para seguir: " RESP </dev/tty
if [ "$RESP" != "SI" ]; then echo "Cancelado. No se ha tocado nada."; exit 0; fi
paso "Actualizando"
FECHA=$(date +%Y-%m-%d_%H%M)
mkdir -p "$COPIAS"
for m in $MODULOS; do
    cp -a "$ADDONS_DIR/$m" "$COPIAS/${m}_$FECHA" || { rojo "no se ha podido hacer la copia de $m: no sigo"; exit 1; }
    ok "copia de $m: $COPIAS/${m}_$FECHA"
done
for m in $MODULOS; do
    rm -rf "$ADDONS_DIR/$m" && cp -a "$TMP/$m" "$ADDONS_DIR/$m" && { [ -z "$DUENO" ] || chown -R "$DUENO" "$ADDONS_DIR/$m"; } && ok "$m nuevo puesto (version $(version "$ADDONS_DIR/$m"))" || {
        rojo "fallo al poner $m: vuelvo a poner las versiones anteriores"
        for x in $MODULOS; do rm -rf "$ADDONS_DIR/$x"; cp -a "$COPIAS/${x}_$FECHA" "$ADDONS_DIR/$x"; done
        exit 1; }
done
systemctl restart "$ODOO_SERVICE"
for i in $(seq 1 30); do
    sleep 2
    if systemctl is-active --quiet "$ODOO_SERVICE" && curl -s -o /dev/null -m 3 http://127.0.0.1:8069/web/login 2>/dev/null; then break; fi
done
if systemctl is-active --quiet "$ODOO_SERVICE"; then
    ok "$ODOO_SERVICE reiniciado y en marcha"
    verde "Ahora en Odoo: Aplicaciones > KOROSHI Monitor zonas > Actualizar (o dimelo y lo hago yo). Despues Ctrl+F5 en el monitor."
else
    rojo "$ODOO_SERVICE NO ha arrancado. Ultimas lineas del registro:"
    journalctl -u "$ODOO_SERVICE" -n 30 --no-pager
    rojo "Para volver atras:"
    for m in $MODULOS; do rojo "  sudo rm -rf $ADDONS_DIR/$m && sudo cp -a $COPIAS/${m}_$FECHA $ADDONS_DIR/$m"; done
    rojo "  sudo systemctl restart $ODOO_SERVICE"
fi
exit 0
__KOROSHI_TGZ__
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
ufvcfe4+d5+7z93n7nP3+Sf4/H9Gb5N+AEABAA==
