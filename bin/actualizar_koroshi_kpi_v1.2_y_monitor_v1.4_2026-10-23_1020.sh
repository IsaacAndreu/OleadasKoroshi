#!/usr/bin/env bash
# =============================================================================
# ACTUALIZAR los modulos KOROSHI KPI (koroshi_kpi) y KOROSHI Monitor (koroshi_monitor), ya instalados,
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
# pulsar Actualizar en los dos modulos en Odoo (Aplicaciones), o decirmelo y lo hago yo.
# =============================================================================
set -uo pipefail

MODULOS="koroshi_kpi koroshi_monitor"
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
echo "KOROSHI - actualizar KPI y Monitor ($( [ "$INSTALAR" = "1" ] && echo 'MODO ACTUALIZAR' || echo 'MODO SOLO COMPROBAR: no se cambia nada'))"

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
    verde "Ahora en Odoo: Aplicaciones > KOROSHI KPI > Actualizar, y KOROSHI Monitor zonas > Actualizar (o dimelo y lo hago yo)"
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
m8/N5+Zz87n53HyWf/4/SZIYLwDgAQA=
