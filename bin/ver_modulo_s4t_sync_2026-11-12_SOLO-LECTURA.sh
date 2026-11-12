#!/usr/bin/env bash
# KOROSHI - Ver el modulo de sync S4T (s4t.order.sync) que usa el cron 186 / accion 1800.
# SOLO LECTURA: no copia, no cambia ni reinicia nada.
# Objetivo: saber que envia hoy a S4T (cajas, unidades, transportista, tracking...)
# antes de integrar POST /shipments.
# Uso en el servidor:
#   bash ver_modulo_s4t_sync_2026-11-12_SOLO-LECTURA.sh > s4t_sync_codigo.txt 2>&1
# y pasar s4t_sync_codigo.txt. Las lineas con clave/token/password salen tapadas.
set -uo pipefail

BASE="${BASE:-/opt/nath-erp}"

echo "=== Ficheros que definen s4t.order.sync ==="
FICHEROS=$(grep -rl --include='*.py' "s4t.order.sync" "$BASE" 2>/dev/null)
echo "$FICHEROS"
[ -z "$FICHEROS" ] && { echo "No se ha encontrado s4t.order.sync en $BASE"; exit 1; }

MODULOS=$(for f in $FICHEROS; do d=$(dirname "$f"); while [ "$d" != "/" ] && [ ! -f "$d/__manifest__.py" ]; do d=$(dirname "$d"); done; echo "$d"; done | sort -u)

for m in $MODULOS; do
    echo
    echo "################ MODULO: $m ################"
    echo "=== __manifest__.py ==="
    cat "$m/__manifest__.py"
    for f in $(find "$m" -name '*.py' -not -path '*/tests/*' -not -name '__init__.py' | sort); do
        echo
        echo "=== $f ==="
        # Tapar posibles secretos.
        sed -E -e 's/((api[_-]?key|token|password|passwd|secret|X-Api-Key)[^=:]*[=:][[:space:]]*)["'"'"'][^"'"'"']+["'"'"']/\1"***"/Ig' \
               -e 's/(cust|sk|pk)_(live|test)_[A-Za-z0-9]+/\1_\2_***/g' "$f"
    done
    echo
    echo "=== Vistas XML (solo nombres de campos y botones) ==="
    grep -rhoE '(field name|button name)="[^"]+"' "$m" --include='*.xml' | sort -u
done
