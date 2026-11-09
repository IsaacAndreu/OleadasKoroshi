#!/usr/bin/env bash
set -euo pipefail
# KOROSHI Monitor v1.18.1 (operarios por codigo OP1, OP2...; acabado al validar). Uso:
#   bash actualizar_koroshi_monitor_v1.18.1.sh check
#   sudo AUTO_CONFIRM=1 bash actualizar_koroshi_monitor_v1.18.1.sh install
# Despues: Aplicaciones > "KOROSHI Monitor zonas" > Actualizar, y Ctrl+F5. Fuera de horas: reinicia Odoo.
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
MODE="${1:-check}"
ZIP="${2:-/home/it_nath_group/20261109_koroshi_monitor_v1.18.1.zip}"
exec bash "$SCRIPT_DIR/actualizar_koroshi_modulo_desde_zip.sh" "$MODE" "$ZIP" koroshi_monitor
