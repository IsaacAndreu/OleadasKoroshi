#!/usr/bin/env bash
# =============================================================================
# ACTUALIZAR el modulo KOROSHI Monitor (koroshi_monitor), ya instalado, a la version 1.11 que va dentro de este
# script (tiendas etiquetadas en azul y OUT clicables). Con comprobaciones antes de tocar nada.
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
echo "KOROSHI - actualizar Monitor v1.11 ($( [ "$INSTALAR" = "1" ] && echo 'MODO ACTUALIZAR' || echo 'MODO SOLO COMPROBAR: no se cambia nada'))"

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
3Sf78/8AUBJB0wBAAQA=
