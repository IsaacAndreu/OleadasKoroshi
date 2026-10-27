#!/usr/bin/env bash
# =============================================================================
# ACTUALIZAR el modulo KOROSHI Monitor (koroshi_monitor), ya instalado, a la version 1.9 que va dentro de este
# script (R1 y R2 separadas, tiendas hechas en gris, todo el ancho). Con comprobaciones antes de tocar nada.
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
n9vn9rl9bp/b5wM//xdNtCKcAEABAA==
