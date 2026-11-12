#!/usr/bin/env bash
# KOROSHI - Ver que PESO (y volumen) mandan delivery_xpo y delivery_gls_asm al generar la etiqueta.
# SOLO LECTURA: no copia, no cambia ni reinicia nada.
# Uso en el servidor:
#   bash ver_peso_xpo_gls_2026-11-12_SOLO-LECTURA.sh > peso_xpo_gls.txt 2>&1
set -uo pipefail

BASE="${BASE:-/opt/nath-erp/nath}"
TAPAR='s/(cust|sk|pk)_(live|test)_[A-Za-z0-9]+/\1_\2_***/g; s/((api[_-]?key|token|password|passwd|secret|usuario|user|clave)[^=:]*[=:][[:space:]]*)["'"'"'][^"'"'"']+["'"'"']/\1"***"/Ig'

for MOD in delivery_xpo delivery_gls_asm koroshi_xpo_bultos; do
    DIR=$(find "$BASE" -maxdepth 3 -type d -name "$MOD" 2>/dev/null | head -1)
    echo "################ $MOD: ${DIR:-NO ENCONTRADO} ################"
    [ -z "$DIR" ] && continue
    echo "=== Lineas con peso / volumen / bultos (con 4 lineas de contexto) ==="
    grep -rniE -C4 'peso|weight|kilos|kg|volum|bultos|TotalUnidades' "$DIR" --include='*.py' | sed -E "$TAPAR"
    echo
done
