#!/usr/bin/env bash
set -euo pipefail
# KOROSHI Caja existente v1.1 (PDA: matricula CJ ya hecha de la misma OUT u otra OUT del mismo pedido = meter en esa caja). Uso:
#   bash actualizar_koroshi_caja_existente_v1.1.sh check
#   sudo AUTO_CONFIRM=1 bash actualizar_koroshi_caja_existente_v1.1.sh install
# Despues: Aplicaciones > Actualizar lista > "KOROSHI Caja existente" > Instalar. Fuera de horas: reinicia Odoo.
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
MODE="${1:-check}"
ZIP="${2:-/home/it_nath_group/20261110_koroshi_caja_existente_v1.1.zip}"
exec bash "$SCRIPT_DIR/actualizar_koroshi_modulo_desde_zip.sh" "$MODE" "$ZIP" koroshi_caja_existente
