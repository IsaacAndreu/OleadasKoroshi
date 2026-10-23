#!/usr/bin/env bash
# =============================================================================
# ACTUALIZAR el modulo KOROSHI Monitor (koroshi_monitor), ya instalado, a la v1.7 (franja grande y modo pantalla),
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
echo "KOROSHI - actualizar Monitor v1.7 - modo pantalla ($( [ "$INSTALAR" = "1" ] && echo 'MODO ACTUALIZAR' || echo 'MODO SOLO COMPROBAR: no se cambia nada'))"

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
