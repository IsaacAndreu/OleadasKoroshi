#!/usr/bin/env bash
# =============================================================================
# ACTUALIZAR el modulo KOROSHI Monitor (koroshi_monitor), ya instalado, a la v1.6 (sin faltantes),
# a las versiones que van dentro de este script. Con comprobaciones antes de tocar nada.
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
# pulsar Actualizar en KOROSHI Monitor zonas en Odoo (Aplicaciones), o decirmelo y lo hago yo.
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
echo "KOROSHI - actualizar Monitor v1.6 - sin faltantes ($( [ "$INSTALAR" = "1" ] && echo 'MODO ACTUALIZAR' || echo 'MODO SOLO COMPROBAR: no se cambia nada'))"

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
    D=$(sql "select count(*) from (select fecha, metodo from koroshi_kpi_dia group by fecha, metodo having count(*) > 1) x")
    [ "$D" = "0" ] && ok "fichas KPI sin dia+metodo repetido" || mal "hay $D dias+metodo repetidos en las fichas KPI"
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
    verde "Ahora en Odoo: Aplicaciones > KOROSHI Monitor zonas > Actualizar (o dimelo y lo hago yo)"
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
