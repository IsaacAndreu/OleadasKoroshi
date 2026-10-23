#!/usr/bin/env bash
# =============================================================================
# Instalar el modulo KOROSHI KPI (koroshi_kpi) en Odoo 13 - con comprobaciones antes de tocar nada.
#
# Uso (en el servidor de Odoo):
#   sudo bash ESTE_SCRIPT.sh            -> SOLO COMPRUEBA. No escribe ni reinicia nada.
#   sudo INSTALAR=1 bash ESTE_SCRIPT.sh -> comprueba y, si todo esta bien y confirmas, instala.
#
# Que comprueba:
#   1. Que Odoo esta corriendo y encuentra su configuracion, el addons_path y el servicio.
#   2. Que la carpeta de modulos existe y esta en el addons_path.
#   3. Que NO hay ya un koroshi_kpi en ninguna carpeta del addons_path (no sobrescribe nada).
#   4. Que en la base de datos no hay ya un modulo koroshi_kpi ni tablas/modelos koroshi.kpi.*.
#   5. Que estan instalados los modulos de los que depende (stock, sale_stock).
#   6. Que el modulo que va dentro esta entero (los ficheros que tocan) y que los .py compilan
#      con el Python de Odoo y los .xml estan bien formados.
#   7. Que hay sitio en disco.
# Si algo falla, para y no toca nada.
#
# Que hace al instalar (solo con INSTALAR=1 y despues de confirmar):
#   a. Copia la carpeta koroshi_kpi en la carpeta de modulos (nueva, no pisa nada) con el dueno de Odoo.
#   b. Reinicia el servicio de Odoo (las PDA se quedan ~1 minuto sin conexion).
#   c. Espera a que Odoo responda.
#   d. El modulo se instala desde Odoo: Aplicaciones > Actualizar lista > KOROSHI KPI > Instalar
#      (asi, si diera un error, Odoo lo ensena y no se queda a medias).
#
# El modulo solo crea sus propias tablas (koroshi_kpi_dia, koroshi_kpi_peso_tipo), un menu y una
# tarea nocturna. No cambia albaranes, stock ni productos.
# Para quitarlo: Aplicaciones > KOROSHI KPI > Desinstalar, y borrar la carpeta.
#
# Variables que se pueden forzar si la deteccion no acierta:
#   ADDONS_DIR=/opt/nath-erp/nath/enterprise-addons  ODOO_SERVICE=nath-erp  ODOO_CONF=/etc/odoo.conf
#   ODOO_DB=NATH_PRODUCTION
# =============================================================================
set -uo pipefail

MODULO=koroshi_kpi
ADDONS_DIR="${ADDONS_DIR:-/opt/nath-erp/nath/enterprise-addons}"
ODOO_SERVICE="${ODOO_SERVICE:-nath-erp}"
ODOO_DB="${ODOO_DB:-NATH_PRODUCTION}"
INSTALAR="${INSTALAR:-0}"
TMP=$(mktemp -d /tmp/koroshi_kpi_inst.XXXXXX)
ERRORES=0
AVISOS=0

rojo() { printf '\033[31m%s\033[0m\n' "$*"; }
verde() { printf '\033[32m%s\033[0m\n' "$*"; }
amarillo() { printf '\033[33m%s\033[0m\n' "$*"; }
ok() { verde "   OK  $*"; }
mal() { rojo "   MAL $*"; ERRORES=$((ERRORES + 1)); }
aviso() { amarillo "   OJO $*"; AVISOS=$((AVISOS + 1)); }
paso() { echo; echo "== $* =="; }
limpiar() { rm -rf "$TMP"; }
trap limpiar EXIT

if [ "$(id -u)" != "0" ]; then
    rojo "Hay que ejecutarlo con sudo:  sudo bash $0"
    exit 1
fi
echo "KOROSHI KPI - instalador ($( [ "$INSTALAR" = "1" ] && echo 'MODO INSTALAR' || echo 'MODO SOLO COMPROBAR: no se cambia nada'))"

# ---------------------------------------------------------------- modulo empaquetado
paso "0. Modulo que va dentro del script"
if ! sed -n '/^__KOROSHI_KPI_TGZ__$/,$p' "$0" | sed '1d' | base64 -d > "$TMP/modulo.tgz" 2>/dev/null; then
    rojo "   No se puede leer el modulo de dentro del script (copia incompleta?)"; exit 1
fi
if ! tar -xzf "$TMP/modulo.tgz" -C "$TMP" 2>/dev/null; then
    rojo "   El modulo de dentro del script esta danado (copia incompleta?)"; exit 1
fi
for f in __init__.py __manifest__.py models/__init__.py models/kpi.py security/ir.model.access.csv \
         data/peso_tipo.xml data/cron.xml views/kpi_views.xml; do
    if [ -s "$TMP/$MODULO/$f" ]; then ok "$f"; else mal "falta $f"; fi
done
echo "   version: $(grep -oE "'[0-9]+.[0-9.]+'" "$TMP/$MODULO/__manifest__.py" | head -1)"

# ---------------------------------------------------------------- Odoo corriendo
paso "1. Odoo, configuracion y servicio"
PROC=$(ps -eo args | grep -E 'odoo-bin|openerp-server' | grep -v grep | head -1 || true)
if [ -n "$PROC" ]; then ok "Odoo corriendo"; else mal "no encuentro ningun proceso odoo-bin corriendo"; fi
ODOO_USER=$(ps -eo user:32,args | grep -E 'odoo-bin|openerp-server' | grep -v grep | head -1 | awk '{print $1}' || true)
[ -n "$ODOO_USER" ] && ok "usuario de Odoo: $ODOO_USER"
ODOO_PY=$(echo "$PROC" | awk '{print $1}')
case "$ODOO_PY" in *python*) : ;; *) ODOO_PY=python3 ;; esac
if [ -z "${ODOO_CONF:-}" ]; then
    ODOO_CONF=$(echo "$PROC" | grep -oE '(-c|--config)[ =][^ ]+' | head -1 | sed -E 's/^(-c|--config)[ =]//' || true)
fi
if [ -n "${ODOO_CONF:-}" ] && [ -r "$ODOO_CONF" ]; then ok "configuracion: $ODOO_CONF"; else mal "no encuentro el fichero de configuracion (forzar con ODOO_CONF=...)"; ODOO_CONF=""; fi
if [ "$(systemctl show -p LoadState --value "$ODOO_SERVICE" 2>/dev/null)" = "loaded" ]; then
    systemctl is-active --quiet "$ODOO_SERVICE" && ok "servicio $ODOO_SERVICE en marcha" || mal "el servicio $ODOO_SERVICE no esta en marcha"
else
    mal "no existe el servicio $ODOO_SERVICE (forzar con ODOO_SERVICE=...). Servicios parecidos: $(systemctl list-units --type=service --all --no-legend 2>/dev/null | awk '{print $1}' | grep -iE 'odoo|nath|erp' | tr '\n' ' ')"
fi

# ---------------------------------------------------------------- carpeta de modulos
paso "2. Carpeta de modulos"
ADDONS_PATH=""
[ -n "$ODOO_CONF" ] && ADDONS_PATH=$(grep -E '^\s*addons_path\s*=' "$ODOO_CONF" | head -1 | sed -E 's/^[^=]*=\s*//' | tr -d ' ')
if [ -d "$ADDONS_DIR" ]; then ok "$ADDONS_DIR existe"; else mal "$ADDONS_DIR no existe"; fi
if [ -n "$ADDONS_PATH" ]; then
    EN_PATH=0
    for d in $(echo "$ADDONS_PATH" | tr ',' ' '); do
        [ "$(readlink -f "$d" 2>/dev/null)" = "$(readlink -f "$ADDONS_DIR" 2>/dev/null)" ] && EN_PATH=1
    done
    if [ "$EN_PATH" = "1" ]; then ok "$ADDONS_DIR esta en el addons_path de Odoo"; else mal "$ADDONS_DIR NO esta en el addons_path ($ADDONS_PATH)"; fi
else
    aviso "no he podido leer el addons_path; compruebo solo $ADDONS_DIR"
fi
DUENO=$(stat -c '%U:%G' "$ADDONS_DIR" 2>/dev/null || echo "")
[ -n "$DUENO" ] && ok "dueno de la carpeta: $DUENO"

# ---------------------------------------------------------------- no sobrescribir
paso "3. Que no haya ya un $MODULO (no se sobrescribe nada)"
YA=0
for d in $(echo "$ADDONS_PATH,$ADDONS_DIR" | tr ',' ' '); do
    if [ -e "$d/$MODULO" ]; then mal "ya existe $d/$MODULO: no lo toco (si es una version vieja, muevela tu antes)"; YA=1; fi
done
[ "$YA" = "0" ] && ok "no hay ninguna carpeta $MODULO en el addons_path"

# ---------------------------------------------------------------- base de datos
paso "4. Base de datos $ODOO_DB"
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
    E=$(sql "select state from ir_module_module where name='$MODULO'")
    if [ -z "$E" ] || [ "$E" = "uninstalled" ]; then ok "el modulo $MODULO no esta instalado${E:+ (registrado como no instalado)}"; else mal "el modulo $MODULO ya esta en la base de datos con estado '$E'"; fi
    T=$(sql "select count(*) from information_schema.tables where table_name like 'koroshi_kpi%'")
    [ "$T" = "0" ] && ok "no hay tablas koroshi_kpi*" || mal "ya hay $T tablas koroshi_kpi* en la base de datos"
    M=$(sql "select count(*) from ir_model where model like 'koroshi.kpi%'")
    [ "$M" = "0" ] && ok "no hay modelos koroshi.kpi.*" || mal "ya hay $M modelos koroshi.kpi.* en Odoo"
    for dep in stock sale_stock; do
        S=$(sql "select state from ir_module_module where name='$dep'")
        [ "$S" = "installed" ] && ok "dependencia $dep instalada" || mal "la dependencia $dep no esta instalada ($S)"
    done
    F=$(sql "select count(*) from ir_model_fields where model='sale.order' and name='s_order_type_id'")
    [ "$F" = "1" ] && ok "existe el tipo de pedido (sale.order.s_order_type_id)" || aviso "no existe sale.order.s_order_type_id: habra que dejar vacio 'Tipo de pedido' en las fichas"
else
    aviso "no puedo conectar con la base de datos por psql: no compruebo si ya hay algo instalado (Odoo lo dira al instalar)"
fi

# ---------------------------------------------------------------- codigo del modulo
paso "5. Codigo del modulo"
if "$ODOO_PY" -c "import sys" 2>/dev/null; then
    for f in $(cd "$TMP/$MODULO" && find . -name '*.py'); do
        if "$ODOO_PY" -m py_compile "$TMP/$MODULO/$f" 2>"$TMP/err"; then ok "compila $f"; else mal "no compila $f: $(cat "$TMP/err")"; fi
    done
    for f in $(cd "$TMP/$MODULO" && find . -name '*.xml'); do
        if "$ODOO_PY" -c "import sys, xml.dom.minidom as m; m.parse(sys.argv[1])" "$TMP/$MODULO/$f" 2>/dev/null; then ok "xml bien: $f"; else mal "xml mal formado: $f"; fi
    done
    "$ODOO_PY" -c "import pytz" 2>/dev/null && ok "pytz disponible" || aviso "no encuentro pytz en $ODOO_PY (si Odoo usa otro Python, no pasa nada)"
else
    aviso "no encuentro el Python de Odoo; no compruebo el codigo"
fi

# ---------------------------------------------------------------- disco
paso "6. Espacio en disco"
LIBRE=$(df -Pk "$ADDONS_DIR" 2>/dev/null | awk 'NR==2 {print $4}')
if [ -n "$LIBRE" ] && [ "$LIBRE" -gt 51200 ]; then ok "$((LIBRE / 1024)) MB libres"; else mal "poco espacio libre en $ADDONS_DIR"; fi

# ---------------------------------------------------------------- resumen
echo
if [ "$ERRORES" -gt 0 ]; then
    rojo "RESULTADO: $ERRORES problema(s). No se ha tocado nada. Arreglalos o dime que ha salido."
    exit 1
fi
if [ "$AVISOS" -gt 0 ]; then verde "RESULTADO: todo bien ($AVISOS aviso(s) en amarillo). No se ha tocado nada."; else verde "RESULTADO: todo bien. No se ha tocado nada."; fi
if [ "$INSTALAR" != "1" ]; then
    echo "Para instalar:  sudo INSTALAR=1 bash $0"
    exit 0
fi

# ---------------------------------------------------------------- instalar
echo
amarillo "Se va a copiar $MODULO en $ADDONS_DIR y REINICIAR $ODOO_SERVICE (las PDA ~1 minuto sin conexion)."
read -r -p "Escribe SI para seguir: " RESP </dev/tty
if [ "$RESP" != "SI" ]; then echo "Cancelado. No se ha tocado nada."; exit 0; fi
paso "Instalando"
cp -a "$TMP/$MODULO" "$ADDONS_DIR/$MODULO" && ok "copiado en $ADDONS_DIR/$MODULO" || { rojo "no se ha podido copiar"; exit 1; }
[ -n "$DUENO" ] && chown -R "$DUENO" "$ADDONS_DIR/$MODULO" && ok "dueno $DUENO"
systemctl restart "$ODOO_SERVICE"
for i in $(seq 1 30); do
    sleep 2
    if systemctl is-active --quiet "$ODOO_SERVICE" && curl -s -o /dev/null -m 3 http://127.0.0.1:8069/web/login 2>/dev/null; then break; fi
done
if systemctl is-active --quiet "$ODOO_SERVICE"; then
    ok "$ODOO_SERVICE reiniciado y en marcha"
    verde "Ahora en Odoo: Aplicaciones > Actualizar lista de aplicaciones > buscar 'KOROSHI KPI' > Instalar"
else
    rojo "$ODOO_SERVICE NO ha arrancado. Ultimas lineas del registro:"
    journalctl -u "$ODOO_SERVICE" -n 30 --no-pager
    rojo "Para volver atras: sudo rm -rf $ADDONS_DIR/$MODULO && sudo systemctl restart $ODOO_SERVICE"
fi
exit 0
__KOROSHI_KPI_TGZ__
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
U59+z+l/r71EwwDIAAA=
