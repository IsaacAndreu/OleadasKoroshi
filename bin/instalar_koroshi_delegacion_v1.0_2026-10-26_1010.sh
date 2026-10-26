#!/usr/bin/env bash
# =============================================================================
# INSTALAR el modulo nuevo "KOROSHI Delegacion en albaranes" (koroshi_delegacion) en el servidor de nath.tuctuc.com.
# Con comprobaciones antes de tocar nada. Anade a los albaranes el campo Delegacion (de la etiqueta "Delegacion ..."
# de la tienda) para Agrupar por > Delegacion en Inventario > Transferencias.
#
# Uso (en el servidor de odoo.tuctuc.com):
#   sudo bash ESTE_SCRIPT.sh            -> SOLO COMPROBAR. No escribe ni reinicia nada.
#   sudo INSTALAR=1 bash ESTE_SCRIPT.sh -> comprueba y, si todo esta bien y escribes SI, copia la carpeta.
#
# Que comprueba: Odoo corriendo y su configuracion; en que carpeta de modulos va (la de los modulos KOROSHI,
# donde esta koroshi_kpi, o la que digas con ADDONS_DIR=...); que no hay ya otro koroshi_delegacion;
# que el codigo compila y los xml estan bien; etiquetas de delegacion y cuantos albaranes se rellenaran.
# Que hace al instalar: solo copia la carpeta koroshi_delegacion. NO reinicia Odoo (un modulo nuevo no lo
# necesita). Despues, en Odoo: Aplicaciones > Actualizar lista > "KOROSHI Delegacion en albaranes" > Instalar
# (o dimelo y lo hago yo). Mejor a las 13:00: al instalar se anade la columna y se rellenan los albaranes.
# Para quitarlo: desinstalar en Aplicaciones y borrar la carpeta.
# =============================================================================
set -uo pipefail

MODULO=koroshi_delegacion
ODOO_DB="${ODOO_DB:-NATH_PRODUCTION}"
INSTALAR="${INSTALAR:-0}"
TMP=$(mktemp -d /tmp/koroshi_deleg.XXXXXX)
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
echo "KOROSHI Delegacion en albaranes - instalar ($( [ "$INSTALAR" = "1" ] && echo 'MODO INSTALAR' || echo 'MODO SOLO COMPROBAR: no se cambia nada'))"

paso "0. Modulo que va dentro del script"
if ! sed -n '/^__KOROSHI_DELEG_TGZ__$/,$p' "$0" | sed '1d' | base64 -d > "$TMP/m.tgz" 2>/dev/null || ! tar -xzf "$TMP/m.tgz" -C "$TMP" 2>/dev/null; then
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
    if [ -z "${ADDONS_DIR:-}" ] && [ -d "$d/koroshi_kpi" ]; then ADDONS_DIR="$d"; fi
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
    [ "$(sql "select state from ir_module_module where name='stock'")" = "installed" ] && ok "stock instalado" || mal "stock no esta instalado"
    C=$(sql "select count(*) from information_schema.columns where table_name='stock_picking' and column_name='koroshi_delegacion'")
    [ "$C" = "0" ] && ok "la columna koroshi_delegacion aun no existe" || aviso "ya existe la columna koroshi_delegacion en stock_picking"
    T=$(sql "select count(*) from res_partner_category where name like 'Delegación %'")
    [ "${T:-0}" -gt 0 ] && ok "etiquetas de delegacion: $T" || mal "no hay etiquetas 'Delegación ...' en los contactos"
    N=$(sql "select count(distinct r.partner_id) from res_partner_res_partner_category_rel r join res_partner_category c on c.id = r.category_id where c.name like 'Delegación %'")
    ok "tiendas con etiqueta de delegacion: $N"
    T0=$(date +%s%N)
    A=$(sql "set statement_timeout = 60000; select count(*) from stock_picking p where exists (select 1 from res_partner_res_partner_category_rel r join res_partner_category c on c.id = r.category_id where r.partner_id = p.partner_id and c.name like 'Delegación %')" | tail -1)
    T1=$(date +%s%N)
    ok "albaranes que se rellenaran al instalar: $A (contarlos ha tardado $(( (T1 - T0) / 1000000 )) ms)"
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
verde "Ahora en Odoo: Aplicaciones > Actualizar lista > 'KOROSHI Delegacion en albaranes' > Instalar (o dimelo y lo hago yo)."
echo "Para quitarlo: desinstalar en Aplicaciones y despues  sudo rm -rf $ADDONS_DIR/$MODULO"
exit 0
__KOROSHI_DELEG_TGZ__
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
lv4LepavOgBQAAA=
