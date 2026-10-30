#!/usr/bin/env bash
# =============================================================================
# ACTUALIZAR el modulo KOROSHI Monitor (koroshi_monitor), ya instalado, a la version 1.13 que va dentro de este
# script (nombre del monitor en las migas de pan). Con comprobaciones antes de tocar nada.
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
echo "KOROSHI - actualizar Monitor v1.14 ($( [ "$INSTALAR" = "1" ] && echo 'MODO ACTUALIZAR' || echo 'MODO SOLO COMPROBAR: no se cambia nada'))"

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
Vs/qWT2rZ/WsntWzev5/fP4fSnWHYgBoAQA=
