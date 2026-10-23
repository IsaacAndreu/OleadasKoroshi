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
z+3n9nP7uf2s8Pn/osXHfgC4AQA=
