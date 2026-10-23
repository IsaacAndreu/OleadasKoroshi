#!/usr/bin/env bash
# =============================================================================
# Empaquetar el modulo delivery_package_number (OCA) para revisarlo: es el que suma / resta
# "Numero de bultos" cuando la PDA crea o borra niveles de paquete, y deja bultos negativos.
#
# SOLO LEE: no cambia nada de Odoo, ni modulos, ni base de datos, ni reinicia nada.
# Escribe solo en tu carpeta (~):
#   ~/delivery_package_number_<fecha>.tar.gz   (el modulo, sin .pyc)
#   ~/delivery_package_number_<fecha>.txt      (lo que sale por pantalla: ficheros y codigo de los modelos)
#
# Uso:  sudo bash empaquetar_delivery_package_number_2026-10-23_1100_SOLO-LECTURA.sh
# =============================================================================
set -uo pipefail
FECHA=$(date +%Y-%m-%d_%H%M)
HOME_USR=$(getent passwd "${SUDO_USER:-$USER}" | cut -d: -f6)
INFORME="$HOME_USR/delivery_package_number_$FECHA.txt"
PAQUETE="$HOME_USR/delivery_package_number_$FECHA.tar.gz"
exec > >(tee "$INFORME") 2>&1

PROC=$(ps -eo args | grep -E 'odoo-bin|openerp-server' | grep -v grep | head -1 || true)
ODOO_CONF=${ODOO_CONF:-$(echo "$PROC" | grep -oE '(-c|--config)[ =][^ ]+' | head -1 | sed -E 's/^(-c|--config)[ =]//' || true)}
ADDONS_PATH=$( [ -n "$ODOO_CONF" ] && grep -E '^\s*addons_path\s*=' "$ODOO_CONF" | head -1 | sed -E 's/^[^=]*=\s*//' | tr -d ' ' || true)

echo "== delivery_package_number ($FECHA) - SOLO LECTURA =="
M=""
for d in $(echo "$ADDONS_PATH" | tr ',' ' '); do
    [ -d "$d/delivery_package_number" ] && M="$d/delivery_package_number" && echo "modulo: $M"
done
if [ -z "$M" ]; then echo "No encuentro la carpeta delivery_package_number en el addons_path: $ADDONS_PATH"; exit 1; fi

echo
echo "== Ficheros =="
find "$M" -type f ! -name '*.pyc' | sort | sed 's/^/   /'

echo
echo "== Manifest =="
cat "$M/__manifest__.py"

for f in $(find "$M" -type f -name '*.py' ! -path '*/tests/*' | sort); do
    echo
    echo "== $f =="
    cat -n "$f"
done

tar --exclude='__pycache__' --exclude='*.pyc' -czf "$PAQUETE" -C "$(dirname "$M")" "$(basename "$M")" && \
    chown "${SUDO_USER:-$USER}" "$PAQUETE" "$INFORME" 2>/dev/null
echo
echo "Paquete: $PAQUETE"
echo "Informe: $INFORME"
echo "No se ha cambiado nada."
