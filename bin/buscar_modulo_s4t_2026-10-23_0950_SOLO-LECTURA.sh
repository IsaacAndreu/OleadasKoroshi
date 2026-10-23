#!/usr/bin/env bash
# =============================================================================
# Buscar el modulo de integracion S4T en el servidor de Odoo y empaquetarlo para revisarlo.
# SOLO LEE: no cambia nada de Odoo, ni ficheros de modulos, ni la base de datos, ni reinicia nada.
# Lo unico que escribe es el paquete y el informe en tu carpeta (~):
#   ~/s4t_modulo_<fecha>.tar.gz   (las carpetas de los modulos S4T, sin .pyc)
#   ~/s4t_informe_<fecha>.txt     (todo lo que sale por pantalla)
#
# Uso:  sudo bash buscar_modulo_s4t_2026-10-23_0950_SOLO-LECTURA.sh
# Despues pasame los dos ficheros (o pega aqui el informe).
# =============================================================================
set -uo pipefail
FECHA=$(date +%Y-%m-%d_%H%M)
HOME_USR=$(getent passwd "${SUDO_USER:-$USER}" | cut -d: -f6)
INFORME="$HOME_USR/s4t_informe_$FECHA.txt"
PAQUETE="$HOME_USR/s4t_modulo_$FECHA.tar.gz"
ODOO_DB="${ODOO_DB:-NATH_PRODUCTION}"
exec > >(tee "$INFORME") 2>&1

echo "== Buscar modulo S4T ($FECHA) - SOLO LECTURA =="

# ---------------- Odoo: configuracion y addons_path
PROC=$(ps -eo args | grep -E 'odoo-bin|openerp-server' | grep -v grep | head -1 || true)
ODOO_USER=$(ps -eo user:32,args | grep -E 'odoo-bin|openerp-server' | grep -v grep | head -1 | awk '{print $1}' || true)
ODOO_CONF=${ODOO_CONF:-$(echo "$PROC" | grep -oE '(-c|--config)[ =][^ ]+' | head -1 | sed -E 's/^(-c|--config)[ =]//' || true)}
echo "configuracion: ${ODOO_CONF:-?}"
ADDONS_PATH=$( [ -n "$ODOO_CONF" ] && grep -E '^\s*addons_path\s*=' "$ODOO_CONF" | head -1 | sed -E 's/^[^=]*=\s*//' | tr -d ' ' || true)
echo "addons_path: $ADDONS_PATH"

# ---------------- Modulos que mencionan S4T (nombre de carpeta o manifest)
echo
echo "== Modulos con 's4t' en el nombre o en el manifest =="
MODS=()
for d in $(echo "$ADDONS_PATH" | tr ',' ' '); do
    [ -d "$d" ] || continue
    for m in "$d"/*/; do
        m=${m%/}
        [ -f "$m/__manifest__.py" ] || [ -f "$m/__openerp__.py" ] || continue
        if echo "$(basename "$m")" | grep -qi 's4t' || grep -qiE 's4t|sap.?for.?textile|s4 ?t' "$m"/__manifest__.py "$m"/__openerp__.py 2>/dev/null; then
            MODS+=("$m")
            echo "-- $m"
            grep -E "'(name|version|summary|depends|author)'" "$m/__manifest__.py" 2>/dev/null | sed 's/^/     /'
        fi
    done
done
if [ ${#MODS[@]} -eq 0 ]; then
    echo "No he encontrado ninguno por el nombre. Busco 's4t' dentro de los .py (puede tardar)..."
    for d in $(echo "$ADDONS_PATH" | tr ',' ' '); do
        [ -d "$d" ] || continue
        grep -rliE 's4t' --include='*.py' "$d" 2>/dev/null | sed -E "s#^($d/[^/]+)/.*#\1#" | sort -u
    done | while read -r m; do echo "-- $m"; done
fi

# ---------------- Base de datos: modulos instalados y modelos/campos S4T (solo SELECT)
echo
echo "== Base de datos $ODOO_DB (solo consultas) =="
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
sql "select name, state, latest_version, author, shortdesc from ir_module_module where name ilike '%s4t%' or shortdesc ilike '%s4t%' order by name"
sql "select model, name from ir_model where model ilike '%s4t%' or name ilike '%s4t%' order by model"
sql "select model, name, ttype, field_description from ir_model_fields where (name ilike '%s4t%' or model ilike '%s4t%') order by model, name limit 200"
sql "select id, name, model_id, state from ir_act_server where name ilike '%s4t%' or name ilike '%sincron%' order by id"
sql "select id, name, active, interval_number, interval_type, nextcall from ir_cron where cron_name ilike '%s4t%' or cron_name ilike '%sincron%' order by id" 2>/dev/null || \
sql "select c.id, a.name, c.active, c.interval_number, c.interval_type, c.nextcall from ir_cron c join ir_act_server a on a.id = c.ir_actions_server_id where a.name ilike '%s4t%' or a.name ilike '%sincron%' order by c.id"

# ---------------- Donde se mencionan las CJ / paquetes en esos modulos
echo
echo "== Dentro de los modulos S4T: menciones a paquetes / CJ / bultos =="
for m in "${MODS[@]}"; do
    echo "-- $m"
    find "$m" -type f \( -name '*.py' -o -name '*.xml' \) | sort | sed 's/^/   fichero: /'
    grep -rnE "quant.package|result_package|package_id|\bCJ|bulto|zebra" --include='*.py' --include='*.xml' "$m" 2>/dev/null | head -80 | sed 's/^/   /'
done

# ---------------- Paquete para revisarlo (sin .pyc ni __pycache__)
echo
if [ ${#MODS[@]} -gt 0 ]; then
    tar --exclude='__pycache__' --exclude='*.pyc' -czf "$PAQUETE" "${MODS[@]}" 2>/dev/null && \
        chown "${SUDO_USER:-$USER}" "$PAQUETE" 2>/dev/null
    echo "Paquete: $PAQUETE ($(du -h "$PAQUETE" | cut -f1))"
else
    echo "No hay paquete: no he encontrado el modulo por el nombre. Pasame este informe."
fi
chown "${SUDO_USER:-$USER}" "$INFORME" 2>/dev/null
echo "Informe: $INFORME"
echo "No se ha cambiado nada."
