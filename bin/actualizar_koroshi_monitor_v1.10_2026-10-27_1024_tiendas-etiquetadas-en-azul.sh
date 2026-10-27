#!/usr/bin/env bash
# =============================================================================
# ACTUALIZAR el modulo KOROSHI Monitor (koroshi_monitor), ya instalado, a la version 1.10 que va dentro de este
# script (tiendas con etiqueta del transportista en azul). Con comprobaciones antes de tocar nada.
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
echo "KOROSHI - actualizar Monitor v1.10 ($( [ "$INSTALAR" = "1" ] && echo 'MODO ACTUALIZAR' || echo 'MODO SOLO COMPROBAR: no se cambia nada'))"

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
