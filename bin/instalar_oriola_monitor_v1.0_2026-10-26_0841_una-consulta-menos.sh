#!/usr/bin/env bash
# =============================================================================
# INSTALAR el modulo nuevo "Monitor picking Oriola" (oriola_monitor) en el servidor de odoo.tuctuc.com.
# Con comprobaciones antes de tocar nada. El modulo solo lee: no cambia nada en Odoo.
#
# Uso (en el servidor de odoo.tuctuc.com):
#   sudo bash ESTE_SCRIPT.sh            -> SOLO COMPRUEBA. No escribe ni reinicia nada.
#   sudo INSTALAR=1 bash ESTE_SCRIPT.sh -> comprueba y, si todo esta bien y escribes SI, copia la carpeta.
#
# Que comprueba: Odoo corriendo y su configuracion; en que carpeta de modulos va (la de los modulos OCA,
# donde esta delivery_package_number, o la que digas con ADDONS_DIR=...); que no hay ya otro oriola_monitor;
# que el codigo compila y los xml estan bien; base de datos y tipo de albaran de salida de WH-OR; y cuanto
# tardan HOY las consultas que hara el monitor (solo SELECT, con limite de 15 s).
# Que hace al instalar: solo copia la carpeta oriola_monitor. NO reinicia Odoo (un modulo nuevo no lo
# necesita). Despues, en Odoo: Aplicaciones > Actualizar lista de aplicaciones > buscar "Monitor picking
# Oriola" > Instalar (o dimelo y lo hago yo). Mejor en un momento tranquilo: al instalar, Odoo recarga.
# Para quitarlo: desinstalar en Aplicaciones y borrar la carpeta.
# =============================================================================
set -uo pipefail

MODULO=oriola_monitor
ODOO_DB="${ODOO_DB:-TUCTUC_PRODUCTION}"
INSTALAR="${INSTALAR:-0}"
TMP=$(mktemp -d /tmp/oriola_mon.XXXXXX)
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
echo "Monitor picking Oriola - instalar ($( [ "$INSTALAR" = "1" ] && echo 'MODO INSTALAR' || echo 'MODO SOLO COMPROBAR: no se cambia nada'))"

paso "0. Modulo que va dentro del script"
if ! sed -n '/^__ORIOLA_TGZ__$/,$p' "$0" | sed '1d' | base64 -d > "$TMP/m.tgz" 2>/dev/null || ! tar -xzf "$TMP/m.tgz" -C "$TMP" 2>/dev/null; then
    rojo "   El paquete de dentro del script esta danado (copia incompleta?)"; exit 1
fi
[ -f "$TMP/$MODULO/__manifest__.py" ] && ok "$MODULO: version $(version "$TMP/$MODULO")" || mal "falta $MODULO dentro del script"

paso "1. Odoo y configuracion"
PROC=$(ps -eo args | grep -E 'odoo-bin|openerp-server' | grep -v grep | head -1 || true)
[ -n "$PROC" ] && ok "Odoo corriendo" || mal "no encuentro ningun proceso de Odoo corriendo"
ODOO_USER=$(ps -eo user:32,args | grep -E 'odoo-bin|openerp-server' | grep -v grep | head -1 | awk '{print $1}' || true)
ODOO_PY=$(echo "$PROC" | awk '{print $1}'); case "$ODOO_PY" in *python*) : ;; *) ODOO_PY=python3 ;; esac
[ -z "${ODOO_CONF:-}" ] && ODOO_CONF=$(echo "$PROC" | grep -oE '(-c|--config)[ =][^ ]+' | head -1 | sed -E 's/^(-c|--config)[ =]//' || true)
if [ -n "${ODOO_CONF:-}" ] && [ -r "$ODOO_CONF" ]; then ok "configuracion: $ODOO_CONF"; else mal "no encuentro la configuracion (forzar con ODOO_CONF=...)"; ODOO_CONF=""; fi
conf() { [ -n "$ODOO_CONF" ] && grep -E "^\s*$1\s*=" "$ODOO_CONF" | head -1 | sed -E 's/^[^=]*=\s*//' | tr -d ' ' || true; }
echo "   workers: $(conf workers) · limit_time_real: $(conf limit_time_real) · usuario: ${ODOO_USER:-?}"

paso "2. Carpeta de modulos"
ADDONS_PATH=$(conf addons_path)
for d in $(echo "$ADDONS_PATH" | tr ',' ' '); do
    [ -d "$d" ] && echo "   $d ($(ls -1 "$d" 2>/dev/null | wc -l) modulos)"
    [ -e "$d/$MODULO" ] && mal "ya hay un $MODULO en $d: no toco nada"
    if [ -z "${ADDONS_DIR:-}" ] && [ -d "$d/delivery_package_number" ]; then ADDONS_DIR="$d"; fi
done
if [ -n "${ADDONS_DIR:-}" ] && [ -d "$ADDONS_DIR" ]; then
    case ",$ADDONS_PATH," in *",$ADDONS_DIR,"*) ok "se pondra en: $ADDONS_DIR (cambiar con ADDONS_DIR=...)" ;;
        *) mal "$ADDONS_DIR no esta en el addons_path de Odoo" ;; esac
    DUENO=$(stat -c '%U:%G' "$ADDONS_DIR" 2>/dev/null || echo "")
    LIBRE=$(df -Pk "$ADDONS_DIR" 2>/dev/null | awk 'NR==2 {print $4}')
    if [ -n "$LIBRE" ] && [ "$LIBRE" -gt 10240 ]; then ok "$((LIBRE / 1024)) MB libres"; else mal "poco espacio libre en $ADDONS_DIR"; fi
else
    mal "no se en que carpeta ponerlo: dimelo con ADDONS_DIR=/ruta (una de las de arriba)"
fi

paso "3. Codigo"
for f in $(cd "$TMP" && find $MODULO -name '*.py'); do
    "$ODOO_PY" -m py_compile "$TMP/$f" 2>"$TMP/err" && ok "compila $f" || mal "no compila $f: $(cat "$TMP/err")"
done
for f in $(cd "$TMP" && find $MODULO -name '*.xml'); do
    "$ODOO_PY" -c "import sys, xml.dom.minidom as m; m.parse(sys.argv[1])" "$TMP/$f" 2>/dev/null && ok "xml bien: $f" || mal "xml mal formado: $f"
done

paso "4. Base de datos $ODOO_DB (solo SELECT)"
DB_HOST=$(conf db_host); DB_PORT=$(conf db_port); DB_USER=$(conf db_user); DB_PASS=$(conf db_password)
[ "$DB_HOST" = "False" ] && DB_HOST=""; [ "$DB_PORT" = "False" ] && DB_PORT=""; [ "$DB_PASS" = "False" ] && DB_PASS=""
sql() {
    if [ -n "$DB_HOST" ] || [ -n "$DB_PASS" ]; then
        PGPASSWORD="$DB_PASS" psql -X -A -t ${DB_HOST:+-h "$DB_HOST"} ${DB_PORT:+-p "$DB_PORT"} -U "${DB_USER:-odoo}" -d "$ODOO_DB" -c "$1" 2>&1
    else
        sudo -u "${DB_USER:-${ODOO_USER:-odoo}}" psql -X -A -t -d "$ODOO_DB" -c "$1" 2>&1
    fi
}
if R=$(sql "select 1"); [ "$R" = "1" ]; then
    ok "conecto con la base de datos (sin ensenar contrasenas)"
    E=$(sql "select coalesce((select state from ir_module_module where name='$MODULO'), 'no esta')")
    [ "$E" = "no esta" ] || [ "$E" = "uninstalled" ] && ok "$MODULO aun no instalado en Odoo ($E)" || aviso "$MODULO ya aparece en Odoo con estado '$E'"
    for m in stock stock_picking_batch web; do
        [ "$(sql "select state from ir_module_module where name='$m'")" = "installed" ] && ok "$m instalado" || mal "$m no esta instalado"
    done
    TIPO=$(sql "select t.id from stock_picking_type t join stock_warehouse w on w.id = t.warehouse_id where w.code = 'WH-OR' and t.code = 'outgoing' order by t.id limit 1")
    if [ -n "$TIPO" ]; then ok "tipo de salida de WH-OR: id $TIPO"; else mal "no encuentro el tipo de albaran de salida del almacen WH-OR"; TIPO=0; fi
    echo "   Lo que tardan hoy las consultas del monitor (con limite de 15 s, solo leen):"
    HOY=$(TZ=Europe/Madrid date +%Y-%m-%d)
    INI="(timestamp '$HOY 00:00' at time zone 'Europe/Madrid' at time zone 'UTC')"
    for q in \
        "hechas hoy|select count(*) from stock_picking p where p.picking_type_id = $TIPO and p.state = 'done' and p.date_done >= $INI" \
        "abiertas|select count(*) from stock_picking p where p.picking_type_id = $TIPO and p.state in ('assigned','confirmed','waiting')" \
        "lecturas hoy|select count(*) from stock_move_line ml where ml.picking_id in (select id from stock_picking p where p.picking_type_id = $TIPO and (p.state in ('assigned','confirmed','waiting') or (p.state = 'done' and p.date_done >= $INI))) and ml.qty_done > 0 and ml.write_date >= $INI" ; do
        N=${q%%|*}; Q=${q#*|}
        T0=$(date +%s%N); R=$(sql "set statement_timeout = 15000; $Q" | tail -1); T1=$(date +%s%N)
        MS=$(( (T1 - T0) / 1000000 ))
        if echo "$R" | grep -qi "error\|cancel"; then mal "$N: $R"; elif [ "$MS" -gt 5000 ]; then aviso "$N: $R filas en $MS ms (lento)"; else ok "$N: $R en $MS ms"; fi
    done
else
    aviso "no puedo conectar con la base de datos por psql: no compruebo la base de datos"
fi

echo
if [ "$ERRORES" -gt 0 ]; then rojo "RESULTADO: $ERRORES problema(s). No se ha tocado nada. Pasame lo que ha salido."; exit 1; fi
if [ "$AVISOS" -gt 0 ]; then verde "RESULTADO: todo bien ($AVISOS aviso(s) en amarillo). No se ha tocado nada."; else verde "RESULTADO: todo bien. No se ha tocado nada."; fi
if [ "$INSTALAR" != "1" ]; then echo "Para instalar:  sudo INSTALAR=1 bash $0"; exit 0; fi

echo
amarillo "Se va a copiar $MODULO en $ADDONS_DIR. No se reinicia Odoo."
read -r -p "Escribe SI para seguir: " RESP </dev/tty
if [ "$RESP" != "SI" ]; then echo "Cancelado. No se ha tocado nada."; exit 0; fi
paso "Instalando"
cp -a "$TMP/$MODULO" "$ADDONS_DIR/$MODULO" && { [ -z "$DUENO" ] || chown -R "$DUENO" "$ADDONS_DIR/$MODULO"; } && \
    ok "$MODULO puesto en $ADDONS_DIR/$MODULO (version $(version "$ADDONS_DIR/$MODULO"))" || { rojo "fallo al copiar: borro lo copiado"; rm -rf "$ADDONS_DIR/$MODULO"; exit 1; }
verde "Ahora en Odoo: Aplicaciones > Actualizar lista de aplicaciones > buscar 'Monitor picking Oriola' > Instalar (o dimelo y lo hago yo)."
echo "Para quitarlo: desinstalar en Aplicaciones y despues  sudo rm -rf $ADDONS_DIR/$MODULO"
exit 0
__ORIOLA_TGZ__
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
XwDIAAA=
