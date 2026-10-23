#!/usr/bin/env bash
# =============================================================================
# ACTUALIZAR el modulo KOROSHI KPI (koroshi_kpi), ya instalado, a la version de dentro - con comprobaciones.
#
# Uso (en el servidor de Odoo):
#   sudo bash ESTE_SCRIPT.sh            -> SOLO COMPRUEBA. No escribe ni reinicia nada.
#   sudo INSTALAR=1 bash ESTE_SCRIPT.sh -> comprueba y, si todo esta bien y confirmas, instala.
#
# Que comprueba:
#   1. Que Odoo esta corriendo y encuentra su configuracion, el addons_path y el servicio.
#   2. Que la carpeta de modulos existe y esta en el addons_path.
#   3. Que el koroshi_kpi instalado esta SOLO en la carpeta de modulos (y que version tiene).
#   4. Que en la base de datos el modulo esta instalado y que las fichas no chocan con la regla nueva.
#   5. Que estan instalados los modulos de los que depende (stock, sale_stock).
#   6. Que el modulo que va dentro esta entero (los ficheros que tocan) y que los .py compilan
#      con el Python de Odoo y los .xml estan bien formados.
#   7. Que hay sitio en disco.
# Si algo falla, para y no toca nada.
#
# Que hace al instalar (solo con INSTALAR=1 y despues de confirmar):
#   a. Guarda una copia de la carpeta actual en /opt/nath-erp/copias_modulos/koroshi_kpi_<fecha> y pone la nueva.
#   b. Reinicia el servicio de Odoo (las PDA se quedan ~1 minuto sin conexion).
#   c. Espera a que Odoo responda.
#   d. El modulo se actualiza desde Odoo: Aplicaciones > KOROSHI KPI > Actualizar
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
echo "KOROSHI KPI - ACTUALIZADOR ($( [ "$INSTALAR" = "1" ] && echo 'MODO INSTALAR' || echo 'MODO SOLO COMPROBAR: no se cambia nada'))"

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
if systemctl show -p LoadState "$ODOO_SERVICE" 2>/dev/null | grep -q "=loaded$"; then
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
paso "3. El $MODULO instalado"
for d in $(echo "$ADDONS_PATH" | tr ',' ' '); do
    if [ -e "$d/$MODULO" ] && [ "$(readlink -f "$d")" != "$(readlink -f "$ADDONS_DIR")" ]; then mal "hay otro $MODULO en $d: no se cual usa Odoo, no toco nada"; fi
done
if [ -f "$ADDONS_DIR/$MODULO/__manifest__.py" ]; then
    ok "esta en $ADDONS_DIR/$MODULO (version $(grep -oE "'[0-9]+.[0-9.]+'" "$ADDONS_DIR/$MODULO/__manifest__.py" | head -1))"
else
    mal "no esta en $ADDONS_DIR/$MODULO: esto es para actualizar, usa el instalador"
fi

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
    [ "$E" = "installed" ] && ok "el modulo $MODULO esta instalado" || mal "el modulo $MODULO no esta instalado (estado '$E'): usa el instalador"
    D=$(sql "select count(*) from (select fecha, metodo from koroshi_kpi_dia group by fecha, metodo having count(*) > 1) x")
    [ "$D" = "0" ] && ok "las fichas no tienen dia+metodo repetido (regla nueva)" || mal "hay $D dias+metodo repetidos en las fichas"
    N=$(sql "select count(*) from koroshi_kpi_dia")
    ok "fichas guardadas: $N (se conservan)"
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
    echo "Para actualizar:  sudo INSTALAR=1 bash $0"
    exit 0
fi

# ---------------------------------------------------------------- instalar
echo
amarillo "Se va a cambiar $ADDONS_DIR/$MODULO por la version nueva (con copia) y REINICIAR $ODOO_SERVICE (las PDA ~1 minuto sin conexion)."
read -r -p "Escribe SI para seguir: " RESP </dev/tty
if [ "$RESP" != "SI" ]; then echo "Cancelado. No se ha tocado nada."; exit 0; fi
paso "Instalando"
COPIA=/opt/nath-erp/copias_modulos/${MODULO}_$(date +%Y-%m-%d_%H%M)
mkdir -p /opt/nath-erp/copias_modulos && cp -a "$ADDONS_DIR/$MODULO" "$COPIA" && ok "copia de la version anterior: $COPIA" || { rojo "no se ha podido hacer la copia: no toco nada"; exit 1; }
rm -rf "$ADDONS_DIR/$MODULO" && cp -a "$TMP/$MODULO" "$ADDONS_DIR/$MODULO" && ok "version nueva en $ADDONS_DIR/$MODULO" || { rojo "fallo al copiar: vuelvo a poner la anterior"; rm -rf "$ADDONS_DIR/$MODULO"; cp -a "$COPIA" "$ADDONS_DIR/$MODULO"; exit 1; }
[ -n "$DUENO" ] && chown -R "$DUENO" "$ADDONS_DIR/$MODULO" && ok "dueno $DUENO"
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
    rojo "Para volver atras: sudo rm -rf $ADDONS_DIR/$MODULO && sudo cp -a $COPIA $ADDONS_DIR/$MODULO && sudo systemctl restart $ODOO_SERVICE"
fi
exit 0
__KOROSHI_KPI_TGZ__
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
