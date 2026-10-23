#!/usr/bin/env bash
# =============================================================================
# ACTUALIZAR el modulo KOROSHI KPI (koroshi_kpi), ya instalado, a la v1.3 (Faltas por dia),
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
# pulsar Actualizar en KOROSHI KPI en Odoo (Aplicaciones), o decirmelo y lo hago yo.
# =============================================================================
set -uo pipefail

MODULOS="koroshi_kpi"
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
echo "KOROSHI - actualizar KPI v1.3 - Faltas por dia ($( [ "$INSTALAR" = "1" ] && echo 'MODO ACTUALIZAR' || echo 'MODO SOLO COMPROBAR: no se cambia nada'))"

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
    verde "Ahora en Odoo: Aplicaciones > KOROSHI KPI > Actualizar (o dimelo y lo hago yo)"
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
AA==
