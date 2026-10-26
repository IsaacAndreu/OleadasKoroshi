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
