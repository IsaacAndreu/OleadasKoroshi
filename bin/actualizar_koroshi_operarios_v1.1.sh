#!/usr/bin/env bash
set -euo pipefail

# KOROSHI Operarios v1.1 (modulo nuevo). Uso:
#   bash actualizar_koroshi_operarios_v1.1.sh check
#   sudo AUTO_CONFIRM=1 bash actualizar_koroshi_operarios_v1.1.sh install
# Despues: Aplicaciones > Actualizar lista de aplicaciones > buscar "KOROSHI Operarios" > Instalar, y Ctrl+F5.
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
MODE="${1:-check}"
ZIP="${2:-/home/it_nath_group/20261109_koroshi_operarios_v1.1.zip}"
exec bash "$SCRIPT_DIR/actualizar_koroshi_modulo_desde_zip.sh" "$MODE" "$ZIP" koroshi_operarios
