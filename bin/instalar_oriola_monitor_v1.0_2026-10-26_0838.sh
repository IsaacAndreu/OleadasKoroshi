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
2tKWtrSlLW35vcr/AQo8jAcAyAAA
