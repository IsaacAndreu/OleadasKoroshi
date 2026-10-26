#!/usr/bin/env bash
# =============================================================================
# ACTUALIZAR el modulo KOROSHI KPI (koroshi_kpi), ya instalado, a la v1.4 (Hoja de carga XPO),
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
echo "KOROSHI - actualizar KPI v1.4 - Hoja de carga XPO ($( [ "$INSTALAR" = "1" ] && echo 'MODO ACTUALIZAR' || echo 'MODO SOLO COMPROBAR: no se cambia nada'))"

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
+Syf5bN8ls/yWT7/TM//A6JDGMwAkAEA
