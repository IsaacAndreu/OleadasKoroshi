#!/usr/bin/env bash
# =============================================================================
# Buscar que modulo escribe el campo "Numero de bultos" (number_of_packages) de los albaranes.
# Motivo: 12 albaranes tienen bultos NEGATIVOS (EFFEC/OUT/21063 = -113...) y los escribe el usuario de
# las PDA ("Almacen Nath") mientras coge; ninguna accion ni automatismo de Odoo lo toca.
#
# SOLO LEE: no cambia nada de Odoo, ni modulos, ni base de datos, ni reinicia nada.
# Escribe solo el informe en tu carpeta: ~/number_of_packages_informe_<fecha>.txt
#
# Uso:  sudo bash buscar_number_of_packages_2026-10-23_1050_SOLO-LECTURA.sh
# Despues pasame el informe (o pega aqui lo que salga).
# =============================================================================
set -uo pipefail
FECHA=$(date +%Y-%m-%d_%H%M)
HOME_USR=$(getent passwd "${SUDO_USER:-$USER}" | cut -d: -f6)
INFORME="$HOME_USR/number_of_packages_informe_$FECHA.txt"
ODOO_DB="${ODOO_DB:-NATH_PRODUCTION}"
exec > >(tee "$INFORME") 2>&1

echo "== Quien escribe number_of_packages ($FECHA) - SOLO LECTURA =="
PROC=$(ps -eo args | grep -E 'odoo-bin|openerp-server' | grep -v grep | head -1 || true)
ODOO_USER=$(ps -eo user:32,args | grep -E 'odoo-bin|openerp-server' | grep -v grep | head -1 | awk '{print $1}' || true)
ODOO_CONF=${ODOO_CONF:-$(echo "$PROC" | grep -oE '(-c|--config)[ =][^ ]+' | head -1 | sed -E 's/^(-c|--config)[ =]//' || true)}
ADDONS_PATH=$( [ -n "$ODOO_CONF" ] && grep -E '^\s*addons_path\s*=' "$ODOO_CONF" | head -1 | sed -E 's/^[^=]*=\s*//' | tr -d ' ' || true)
echo "configuracion: ${ODOO_CONF:-?}"
echo "addons_path: $ADDONS_PATH"

# ---------------- 1. Modulos instalados que nombran el campo (Python y JS de las PDA)
echo
echo "== 1. Ficheros que nombran number_of_packages (.py y .js), con la linea =="
for d in $(echo "$ADDONS_PATH" | tr ',' ' '); do
    [ -d "$d" ] || continue
    grep -rn --include='*.py' --include='*.js' --include='*.xml' 'number_of_packages' "$d" 2>/dev/null \
        | grep -v '/i18n/' | grep -v '/tests/' | grep -v '\.min\.js' | cut -c1-260
done

# ---------------- 2. Lo mas sospechoso: restas, += / -= y writes del campo
echo
echo "== 2. Lineas que lo cambian (resta, -=, +=, write/update con el campo) =="
for d in $(echo "$ADDONS_PATH" | tr ',' ' '); do
    [ -d "$d" ] || continue
    grep -rnE --include='*.py' --include='*.js' \
        "number_of_packages['\"]?\s*[:=]\s*[^=]|number_of_packages\s*[-+]=|number_of_packages\s*-\s|-\s*1.*number_of_packages|number_of_packages.*-\s*1" \
        "$d" 2>/dev/null | grep -v '/i18n/' | grep -v '/tests/' | cut -c1-260
done

# ---------------- 3. Modulos de PDA / codigo de barras instalados (los que usa "Almacen Nath")
echo
echo "== 3. Modulos de codigo de barras / PDA instalados =="
conf() { [ -n "$ODOO_CONF" ] && grep -E "^\s*$1\s*=" "$ODOO_CONF" | head -1 | sed -E 's/^[^=]*=\s*//' | tr -d ' ' || true; }
DB_HOST=$(conf db_host); DB_PORT=$(conf db_port); DB_USER=$(conf db_user); DB_PASS=$(conf db_password)
[ "$DB_HOST" = "False" ] && DB_HOST=""; [ "$DB_PORT" = "False" ] && DB_PORT=""; [ "$DB_PASS" = "False" ] && DB_PASS=""
sql() {
    if [ -n "$DB_HOST" ] || [ -n "$DB_PASS" ]; then
        PGPASSWORD="$DB_PASS" psql -X -P pager=off ${DB_HOST:+-h "$DB_HOST"} ${DB_PORT:+-p "$DB_PORT"} -U "${DB_USER:-odoo}" -d "$ODOO_DB" -c "$1" 2>&1
    else
        sudo -u "${DB_USER:-${ODOO_USER:-odoo}}" psql -X -P pager=off -d "$ODOO_DB" -c "$1" 2>&1
    fi
}
sql "select name, state, latest_version, author from ir_module_module where state = 'installed' and (name ilike '%barcode%' or name ilike '%batch%' or name ilike '%package%' or name ilike '%bulto%' or author ilike '%brain%') order by name"

# ---------------- 4. Los albaranes con bultos negativos ahora mismo (solo SELECT)
echo
echo "== 4. Albaranes con bultos negativos =="
sql "select p.name, p.state, p.number_of_packages, p.write_date, u.login as escrito_por
     from stock_picking p left join res_users u on u.id = p.write_uid
     where p.number_of_packages < 0 order by p.write_date desc limit 30"

# ---------------- 5. Peticiones de la PDA al servidor que tocan bultos (registro de Odoo, ultimas 2000 lineas)
echo
echo "== 5. Registro de Odoo: llamadas recientes con 'package' / 'bulto' (si el log esta en fichero) =="
LOGF=$( [ -n "$ODOO_CONF" ] && grep -E '^\s*logfile\s*=' "$ODOO_CONF" | head -1 | sed -E 's/^[^=]*=\s*//' | tr -d ' ' || true)
if [ -n "$LOGF" ] && [ -r "$LOGF" ]; then
    tail -n 2000 "$LOGF" | grep -iE 'number_of_packages|put_in_pack|package|bulto' | tail -n 40 | cut -c1-260
else
    echo "(no hay fichero de log en la configuracion: ${LOGF:-ninguno})"
fi

chown "${SUDO_USER:-$USER}" "$INFORME" 2>/dev/null
echo
echo "Informe: $INFORME"
echo "No se ha cambiado nada."
