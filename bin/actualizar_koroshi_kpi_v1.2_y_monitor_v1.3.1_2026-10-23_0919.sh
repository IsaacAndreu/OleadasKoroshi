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
