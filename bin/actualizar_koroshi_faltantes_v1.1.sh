#!/usr/bin/env bash
set -euo pipefail
# KOROSHI Faltantes v1.1 (pantalla Faltante + ronda de revision INT). Necesita koroshi_operarios instalado antes. Uso:
#   bash actualizar_koroshi_faltantes_v1.1.sh check
#   sudo AUTO_CONFIRM=1 bash actualizar_koroshi_faltantes_v1.1.sh install
# Despues: Aplicaciones > Actualizar lista > "KOROSHI Faltantes" > Instalar, y Ctrl+F5.
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
MODE="${1:-check}"
ZIP="${2:-/home/it_nath_group/20261109_koroshi_faltantes_v1.1.zip}"
exec bash "$SCRIPT_DIR/actualizar_koroshi_modulo_desde_zip.sh" "$MODE" "$ZIP" koroshi_faltantes
