#!/usr/bin/env bash
set -euo pipefail
# KOROSHI Operarios v1.2 (grupo "ver productividad" + informe diario 17:00). Uso:
#   bash actualizar_koroshi_operarios_v1.2.sh check
#   sudo AUTO_CONFIRM=1 bash actualizar_koroshi_operarios_v1.2.sh install
# Despues: Aplicaciones > Actualizar lista > "KOROSHI Operarios" > Instalar (o Actualizar), y Ctrl+F5.
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
MODE="${1:-check}"
ZIP="${2:-/home/it_nath_group/20261109_koroshi_operarios_v1.2.zip}"
exec bash "$SCRIPT_DIR/actualizar_koroshi_modulo_desde_zip.sh" "$MODE" "$ZIP" koroshi_operarios
