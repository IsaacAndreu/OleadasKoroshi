#!/usr/bin/env bash
# =============================================================================
# ACTUALIZAR el modulo KOROSHI Monitor (koroshi_monitor), ya instalado, a la version 1.9 que va dentro de este
# script (R1 y R2 separadas, zonas sin arrastrar). Con comprobaciones antes de tocar nada.
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
echo "KOROSHI - actualizar Monitor v1.9 ($( [ "$INSTALAR" = "1" ] && echo 'MODO ACTUALIZAR' || echo 'MODO SOLO COMPROBAR: no se cambia nada'))"

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
QAEA
