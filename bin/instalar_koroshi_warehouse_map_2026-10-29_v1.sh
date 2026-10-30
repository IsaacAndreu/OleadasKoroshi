#!/usr/bin/env bash
# =============================================================================
# KOROSHI Mapa de almacén NAU-2 · comprobación e instalación en Odoo 13
#
# Uso recomendado, en el servidor de Odoo:
#   bash instalar_koroshi_warehouse_map_2026-10-29_v1.sh check /ruta/modulo.zip
#   sudo bash instalar_koroshi_warehouse_map_2026-10-29_v1.sh install /ruta/modulo.zip
#
# Variables opcionales para no depender de la detección automática:
#   ODOO_CONF=/etc/odoo/odoo.conf
#   ADDONS_DIR=/opt/nath-erp/custom_addons
#   ODOO_SERVICE=odoo
#   ODOO_USER=odoo
#   ODOO_BIN=/opt/nath-erp/odoo13/odoo-bin
#   ODOO_PYTHON=/opt/nath-erp/venv/bin/python
#   ODOO_DB=NATH_PRODUCTION
#   AUTO_CONFIRM=1
#
# El modo check no copia, no reinicia servicios y no escribe en Odoo.
# El modo install vuelve a comprobarlo todo, hace una copia de seguridad
# renombrando el módulo anterior, instala/actualiza y reinicia el servicio.
# =============================================================================
set -euo pipefail

MODULO="koroshi_warehouse_map"
MODE="${1:-}"
ZIP="${2:-}"
ODOO_DB="${ODOO_DB:-NATH_PRODUCTION}"
FECHA="$(date +%Y-%m-%d_%H%M%S)"
TMP=""

rojo() { printf '\033[31m%s\033[0m\n' "$*"; }
verde() { printf '\033[32m%s\033[0m\n' "$*"; }
amarillo() { printf '\033[33m%s\033[0m\n' "$*"; }
paso() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
fallo() { rojo "$*"; exit 1; }

limpiar() {
    if [ -n "$TMP" ] && [ -d "$TMP" ]; then
        rm -rf -- "$TMP"
    fi
}
trap limpiar EXIT

if [ "$MODE" != "check" ] && [ "$MODE" != "install" ]; then
    cat <<'USO'
Uso:
  bash script.sh check /ruta/20261029_0911_koroshi_warehouse_map_odoo13_v2.zip
  sudo bash script.sh install /ruta/20261029_0911_koroshi_warehouse_map_odoo13_v2.zip

Modos:
  check    Comprueba el paquete y el entorno. No cambia Odoo.
  install  Comprueba, instala/actualiza el módulo y reinicia Odoo.
USO
    exit 2
fi

[ -n "$ZIP" ] || fallo "Falta el ZIP del módulo."
[ -f "$ZIP" ] || fallo "No existe el ZIP: $ZIP"
command -v unzip >/dev/null 2>&1 || fallo "Falta unzip en el servidor."

ZIP="$(cd "$(dirname "$ZIP")" && pwd)/$(basename "$ZIP")"

detectar_entorno() {
    paso "Detectando el entorno de Odoo"

    local proceso primero rutas ruta
    proceso="$(ps -eo user:32,args 2>/dev/null | grep -E 'odoo-bin|openerp-server|odoo ' | grep -v grep | head -1 || true)"
    if [ -n "$proceso" ]; then
        echo "   Proceso: $proceso"
        ODOO_USER="${ODOO_USER:-$(echo "$proceso" | awk '{print $1}')}"
        if [ -z "${ODOO_CONF:-}" ]; then
            ODOO_CONF="$(echo "$proceso" | grep -oE '(-c|--config)[ =][^ ]+' | head -1 | sed -E 's/^(-c|--config)[ =]//' || true)"
        fi
        if [ -z "${ODOO_BIN:-}" ]; then
            ODOO_BIN="$(echo "$proceso" | grep -oE '[^ ]*odoo-bin' | head -1 || true)"
        fi
        if [ -z "${ODOO_PYTHON:-}" ]; then
            primero="$(echo "$proceso" | awk '{print $2}')"
            case "$primero" in *python*) ODOO_PYTHON="$primero" ;; esac
        fi
    fi

    if [ -z "${ODOO_CONF:-}" ]; then
        for ruta in /etc/odoo/odoo.conf /etc/odoo13.conf /etc/odoo-server.conf /opt/nath-erp/odoo13.conf; do
            if [ -f "$ruta" ]; then ODOO_CONF="$ruta"; break; fi
        done
    fi
    [ -n "${ODOO_CONF:-}" ] || fallo "No encuentro ODOO_CONF. Usa ODOO_CONF=/ruta/odoo.conf."
    [ -f "$ODOO_CONF" ] || fallo "No existe ODOO_CONF: $ODOO_CONF"

    ADDONS_PATH="$(grep -E '^[[:space:]]*addons_path[[:space:]]*=' "$ODOO_CONF" | head -1 | cut -d= -f2- | tr -d ' ' || true)"
    [ -n "$ADDONS_PATH" ] || fallo "No encuentro addons_path en $ODOO_CONF"
    if [ -z "${ADDONS_DIR:-}" ]; then
        IFS=',' read -ra rutas <<< "$ADDONS_PATH"
        for ruta in "${rutas[@]}"; do
            case "$ruta" in
                */odoo/addons|*/odoo13/addons|*/odoo/odoo/addons|*/odoo13/odoo/addons) continue ;;
            esac
            if [ -d "$ruta" ]; then ADDONS_DIR="$ruta"; break; fi
        done
    fi
    [ -n "${ADDONS_DIR:-}" ] || fallo "No encuentro ADDONS_DIR dentro de addons_path."
    [ -d "$ADDONS_DIR" ] || fallo "No existe ADDONS_DIR: $ADDONS_DIR"
    case "$ADDONS_DIR" in
        /|/etc|/opt|/var|/usr) fallo "ADDONS_DIR demasiado general: $ADDONS_DIR" ;;
    esac

    if [ -z "${ODOO_SERVICE:-}" ] && command -v systemctl >/dev/null 2>&1; then
        ODOO_SERVICE="$(systemctl list-units --type=service --all --no-legend 2>/dev/null | awk '{print $1}' | grep -iE 'odoo|nath|openerp' | head -1 || true)"
        ODOO_SERVICE="${ODOO_SERVICE%.service}"
    fi

    ODOO_PYTHON="${ODOO_PYTHON:-$(command -v python3 || command -v python || true)}"
    echo "   Configuración : $ODOO_CONF"
    echo "   addons_path   : $ADDONS_PATH"
    echo "   Se instalará en: $ADDONS_DIR/$MODULO"
    echo "   Usuario Odoo  : ${ODOO_USER:-?}"
    echo "   Servicio      : ${ODOO_SERVICE:-no detectado}"
    echo "   odoo-bin      : ${ODOO_BIN:-no detectado}"
    echo "   Python        : ${ODOO_PYTHON:-no detectado}"
    echo "   Base de datos : $ODOO_DB"
}

comprobar_paquete() {
    paso "Comprobando el paquete del módulo"
    unzip -l "$ZIP" | grep -q "${MODULO}/__manifest__.py" || fallo "El ZIP no contiene ${MODULO}/__manifest__.py"
    unzip -l "$ZIP" | grep -q "${MODULO}/static/src/html/warehouse_planner_20261029_v1.html" || fallo "Falta el plano HTML del módulo"
    unzip -l "$ZIP" | grep -q "${MODULO}/controllers/main.py" || fallo "Falta el controlador del módulo"
    unzip -l "$ZIP" | grep -q "${MODULO}/views/menu.xml" || fallo "Falta el menú de Odoo"

    TMP="$(mktemp -d -t koroshi_warehouse_check.XXXXXX)"
    unzip -q "$ZIP" -d "$TMP"
    [ -f "$TMP/$MODULO/__manifest__.py" ] || fallo "No se ha podido extraer el módulo"
    [ -n "${ODOO_PYTHON:-}" ] || fallo "No encuentro Python para validar el módulo"

    "$ODOO_PYTHON" - "$TMP/$MODULO" <<'PY'
import ast
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

root = Path(sys.argv[1])
manifest = ast.literal_eval((root / '__manifest__.py').read_text(encoding='utf-8'))
required = {'name', 'version', 'depends', 'data', 'installable'}
missing = sorted(required.difference(manifest))
if missing:
    raise SystemExit('Faltan claves en __manifest__.py: %s' % ', '.join(missing))
if not manifest.get('installable'):
    raise SystemExit('El módulo está marcado como no instalable')
for path in root.rglob('*.py'):
    compile(path.read_text(encoding='utf-8'), str(path), 'exec')
for path in root.rglob('*.xml'):
    ET.parse(str(path))
print('   Python, manifest y XML: OK')
print('   Nombre: %s' % manifest['name'])
print('   Versión: %s' % manifest['version'])
print('   Dependencias: %s' % ', '.join(manifest['depends']))
PY

    rm -rf -- "$TMP"
    TMP=""
    verde "   Paquete válido: $ZIP"
}

detectar_entorno
comprobar_paquete

if [ "$MODE" = "check" ]; then
    paso "Resultado de la comprobación"
    verde "CHECK OK: no se ha copiado el módulo, no se ha reiniciado Odoo y no se ha escrito en la base de datos."
    exit 0
fi

if [ "$(id -u)" -ne 0 ]; then
    fallo "El modo install debe ejecutarse como root o con sudo."
fi

paso "Confirmación de instalación"
echo "   Se instalará/actualizará $MODULO en $ADDONS_DIR"
echo "   Se hará una copia de seguridad si ya existe y se reiniciará ${ODOO_SERVICE:-Odoo}"
if [ "${AUTO_CONFIRM:-0}" != "1" ]; then
    read -r -p "¿Continuar? [s/N] " RESPUESTA
    case "$RESPUESTA" in s|S|si|SI|sí|Sí) ;; *) echo "Cancelado. No se ha cambiado nada."; exit 0 ;; esac
fi

DESTINO="$ADDONS_DIR/$MODULO"
if [ -d "$DESTINO" ]; then
    PASO_BACKUP="$ADDONS_DIR/${MODULO}_backup_${FECHA}"
    paso "Guardando la versión anterior"
    mv -- "$DESTINO" "$PASO_BACKUP"
    echo "   Copia guardada en: $PASO_BACKUP"
fi

paso "Instalando los archivos del módulo"
TMP="$(mktemp -d -t koroshi_warehouse_install.XXXXXX)"
unzip -q "$ZIP" -d "$TMP"
cp -a -- "$TMP/$MODULO" "$DESTINO"
rm -rf -- "$TMP"
TMP=""

if [ -n "${ODOO_USER:-}" ] && id "$ODOO_USER" >/dev/null 2>&1; then
    chown -R "$ODOO_USER": "$DESTINO"
fi
find "$DESTINO" -type d -exec chmod 755 {} \;
find "$DESTINO" -type f -exec chmod 644 {} \;
verde "   Archivos instalados en $DESTINO"

if [ -n "${ODOO_SERVICE:-}" ] && command -v systemctl >/dev/null 2>&1; then
    paso "Parando el servicio $ODOO_SERVICE"
    systemctl stop "$ODOO_SERVICE"
fi

if [ -n "${ODOO_BIN:-}" ] && [ -x "$ODOO_BIN" ] && [ -n "${ODOO_PYTHON:-}" ]; then
    if [ -n "${PASO_BACKUP:-}" ]; then ACCION="-u"; QUE="Actualizando"; else ACCION="-i"; QUE="Instalando"; fi
    LOG="/tmp/koroshi_warehouse_map_${FECHA}.log"
    paso "$QUE $MODULO en $ODOO_DB"
    if [ -n "${ODOO_USER:-}" ] && id "$ODOO_USER" >/dev/null 2>&1; then
        EJECUTOR=(sudo -u "$ODOO_USER")
    else
        EJECUTOR=()
    fi
    if "${EJECUTOR[@]}" "$ODOO_PYTHON" "$ODOO_BIN" -c "$ODOO_CONF" -d "$ODOO_DB" "$ACCION" "$MODULO" --stop-after-init --no-http --logfile="$LOG"; then
        if grep -qE 'ERROR|CRITICAL' "$LOG"; then
            amarillo "   Odoo terminó, pero hay ERROR/CRITICAL en $LOG"
            grep -E 'ERROR|CRITICAL' "$LOG" | tail -20 || true
        else
            verde "   Instalación/actualización de Odoo terminada: $LOG"
        fi
    else
        rojo "   Falló la instalación/actualización. Log: $LOG"
        tail -40 "$LOG" 2>/dev/null || true
        exit 1
    fi
else
    amarillo "No se ha encontrado odoo-bin ejecutable. Copia instalada; termina desde Aplicaciones > Actualizar lista."
fi

if [ -n "${ODOO_SERVICE:-}" ] && command -v systemctl >/dev/null 2>&1; then
    paso "Arrancando el servicio $ODOO_SERVICE"
    systemctl start "$ODOO_SERVICE"
    sleep 5
    systemctl is-active --quiet "$ODOO_SERVICE" && verde "   $ODOO_SERVICE está en marcha" || {
        rojo "   $ODOO_SERVICE no ha arrancado correctamente"
        journalctl -u "$ODOO_SERVICE" -n 30 --no-pager || true
        exit 1
    }
fi

paso "Instalación terminada"
verde "Abre Odoo y entra en: Inventario > KOROSHI · Almacén > Mapa NAU-2"
echo "Copia de seguridad anterior: ${PASO_BACKUP:-no había módulo previo}"
