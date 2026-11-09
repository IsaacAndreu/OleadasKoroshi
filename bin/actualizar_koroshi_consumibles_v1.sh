#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
MODE="${1:-check}"
ZIP="${2:-/home/it_nath_group/20261102_koroshi_consumibles_v1.zip}"
exec bash "$SCRIPT_DIR/actualizar_koroshi_modulo_desde_zip.sh" "$MODE" "$ZIP" koroshi_consumibles
