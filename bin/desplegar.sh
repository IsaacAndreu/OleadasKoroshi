#!/usr/bin/env bash
# =============================================================================
# KOROSHI - desplegar.sh (auditoria 13/11, fase 6, 14/11/2026)
# Un solo script para copiar modulos Odoo al servidor, en vez de uno por version.
#
# Uso (con los ZIP en ZIP_DIR, por defecto /home/it_nath_group):
#   bash desplegar.sh check   <modulo> <version> [<modulo> <version> ...]
#   sudo AUTO_CONFIRM=1 bash desplegar.sh install <modulo> <version> [<modulo> <version> ...]
# Ejemplo:
#   bash desplegar.sh check koroshi_zonas 1.3.0
#   bash desplegar.sh check koroshi_xpo_bultos 1.2.0 koroshi_s4t_envios 1.2.0
#
# Para cada modulo busca UN ZIP AAAAMMDD_<modulo>_v<version>.zip y comprueba, antes de tocar nada:
#   - que el ZIP esta sano y solo trae la carpeta <modulo>/ con su __manifest__.py;
#   - que el manifest tiene la version 13.0.<version>;
#   - que en el servidor no esta ya esa version ni una mas nueva (nunca se sobrescribe ni se baja una version);
#   - que lo que pide en 'depends' esta en el servidor o en esta misma tanda (los modulos que no son koroshi_ /
#     oriola_ pueden estar en otra ruta de addons: solo se avisa).
# Si algo falla no copia nada ni reinicia. Si todo esta bien: copia de seguridad, copia y UN solo reinicio.
# Despues, en Odoo: Aplicaciones > Actualizar lista > Actualizar cada modulo (este script no lo hace).
# El reinicio corta Odoo ~1 minuto: hacerlo fuera de horas, sin nadie validando en las PDA.
#
# PRUEBA_LOCAL=1: solo para probar el script fuera del servidor (sin systemctl, sin root, sin reinicio).
# =============================================================================
set -euo pipefail

MODE="${1:-}"
shift || true
ZIP_DIR="${ZIP_DIR:-/home/it_nath_group}"
ADDONS_DIR="${ADDONS_DIR:-/opt/nath-erp/nath/enterprise-addons}"
ODOO_SERVICE="${ODOO_SERVICE:-nath-erp}"
BACKUP_DIR="${BACKUP_DIR:-/opt/nath-erp/copias_modulos}"
PRUEBA_LOCAL="${PRUEBA_LOCAL:-0}"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/koroshi_desplegar.XXXXXX")"
STAMP="$(date +%Y-%m-%d_%H%M%S)"
ERRORS=0
MODULOS=()
VERSIONES=()
BACKUPS=()
trap 'rm -rf "$TMP"' EXIT

red(){ printf '\033[31m%s\033[0m\n' "$*"; }
green(){ printf '\033[32m%s\033[0m\n' "$*"; }
yellow(){ printf '\033[33m%s\033[0m\n' "$*"; }
ok(){ green "   OK  $*"; }
bad(){ red "   MAL $*"; ERRORS=$((ERRORS + 1)); }

uso(){ red "Uso: $0 check|install <modulo> <version> [<modulo> <version> ...]"; exit 2; }

[ "$MODE" = "check" ] || [ "$MODE" = "install" ] || uso
[ $# -ge 2 ] && [ $(($# % 2)) -eq 0 ] || uso
while [ $# -gt 0 ]; do
    case "$1" in *[!a-z0-9_]*|'') red "Nombre de modulo raro: '$1'"; exit 2;; esac
    case "$2" in *[!0-9.]*|'') red "Version rara para $1: '$2' (va sin el 13.0., p. ej. 1.3.0)"; exit 2;; esac
    for m in "${MODULOS[@]:-}"; do [ "$m" = "$1" ] && { red "$1 esta dos veces"; exit 2; }; done
    MODULOS+=("$1")
    VERSIONES+=("${2#13.0.}")
    shift 2
done

if [ "$PRUEBA_LOCAL" = "1" ]; then
    [ "$MODE" = "install" ] && yellow "PRUEBA_LOCAL=1: se copia en $ADDONS_DIR pero NO se reinicia nada."
elif [ "$MODE" = "install" ] && [ "$(id -u)" != "0" ]; then
    red "Para instalar hay que usar sudo."; exit 1
fi
command -v unzip >/dev/null 2>&1 || { red "Falta unzip en el servidor."; exit 1; }

# version del manifest ('13.0.1.3.0') de un fichero; vacio si no hay
version_de(){ grep -oE "'version'[[:space:]]*:[[:space:]]*'[^']+'" "$1" 2>/dev/null | head -1 | sed -E "s/.*'([^']+)'$/\1/" || true; }
# 1 si $1 < $2 (versiones con puntos)
menor(){ [ "$1" != "$2" ] && [ "$(printf '%s\n%s\n' "$1" "$2" | sort -V | head -1)" = "$1" ]; }
# modulos de 'depends' del manifest
depends_de(){
    tr '\n' ' ' < "$1" | grep -oE "'depends'[[:space:]]*:[[:space:]]*\[[^]]*\]" | grep -oE "'[a-z0-9_]+'" | tr -d "'" \
        | grep -v '^depends$' || true
}

echo "KOROSHI - desplegar ($([ "$MODE" = install ] && echo 'MODO INSTALAR' || echo 'MODO COMPROBACION')): ${MODULOS[*]}"

echo
echo "== 1. Validar los ZIP antes de tocar nada =="
for i in "${!MODULOS[@]}"; do
    mod="${MODULOS[$i]}"; ver="${VERSIONES[$i]}"; esperada="13.0.$ver"
    zips=()
    for z in "$ZIP_DIR"/[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]_"${mod}"_v"${ver}".zip; do
        [ -f "$z" ] && zips+=("$z")
    done
    if [ "${#zips[@]}" -eq 0 ]; then
        bad "$mod $ver: no hay ningun $ZIP_DIR/AAAAMMDD_${mod}_v${ver}.zip"; continue
    fi
    if [ "${#zips[@]}" -gt 1 ]; then
        bad "$mod $ver: hay ${#zips[@]} ZIP con esa version (${zips[*]}): dejar solo uno"; continue
    fi
    zip="${zips[0]}"
    if ! unzip -tqq "$zip"; then bad "$mod: ZIP danado: $zip"; continue; fi
    unzip -Z1 "$zip" > "$TMP/lista_$mod"
    otras="$(grep -v "^${mod}/" "$TMP/lista_$mod" | head -3 || true)"
    if [ -n "$otras" ]; then bad "$mod: el ZIP trae cosas fuera de ${mod}/: $otras"; continue; fi
    if ! grep -qx "${mod}/__manifest__.py" "$TMP/lista_$mod"; then bad "$mod: falta ${mod}/__manifest__.py"; continue; fi
    mkdir -p "$TMP/zip_$mod"
    unzip -q "$zip" -d "$TMP/zip_$mod"
    enzip="$(version_de "$TMP/zip_$mod/$mod/__manifest__.py")"
    if [ "$enzip" != "$esperada" ]; then
        bad "$mod: el manifest del ZIP dice '${enzip:-sin version}', no $esperada"; continue
    fi
    ok "$mod: $(basename "$zip"), version $esperada"
    if [ -d "$ADDONS_DIR/$mod" ]; then
        actual="$(version_de "$ADDONS_DIR/$mod/__manifest__.py")"
        if [ "$actual" = "$esperada" ]; then
            bad "$mod: el servidor ya tiene $esperada. Nunca se sobrescribe una version: sacar una nueva."
        elif [ -n "$actual" ] && menor "$esperada" "$actual"; then
            bad "$mod: el servidor tiene $actual, MAS NUEVA que $esperada. No se baja de version."
        else
            echo "        en el servidor: ${actual:-sin version} -> se ACTUALIZA a $esperada"
        fi
    else
        echo "        no esta en el servidor -> se copia NUEVO (instalarlo en Odoo es otra decision)"
    fi
done

for i in "${!MODULOS[@]}"; do
    mod="${MODULOS[$i]}"
    [ -f "$TMP/zip_$mod/$mod/__manifest__.py" ] || continue
    for dep in $(depends_de "$TMP/zip_$mod/$mod/__manifest__.py"); do
        en_tanda=0
        for m in "${MODULOS[@]}"; do [ "$m" = "$dep" ] && en_tanda=1; done
        [ "$en_tanda" = "1" ] && continue
        case "$dep" in base|web|mail|stock|sale|sale_stock|product|account|stock_picking_batch|hr|barcodes|\
                       queue_job|delivery|purchase|portal|bus|resource|uom) continue;; esac
        if [ -d "$ADDONS_DIR/$dep" ]; then
            echo "        $mod necesita $dep: en el servidor ($(version_de "$ADDONS_DIR/$dep/__manifest__.py"))"
        else
            case "$dep" in
                koroshi_*|oriola_*) bad "$mod necesita $dep y no esta en $ADDONS_DIR ni en esta tanda";;
                # los de fuera (delivery_xpo...) pueden estar en otra ruta de addons: solo se avisa
                *) yellow "   OJO $mod necesita $dep: no esta en $ADDONS_DIR; comprobar que Odoo lo tiene en otra ruta";;
            esac
        fi
    done
done

echo
echo "== 2. Validar Odoo y la ruta de addons =="
if [ "$PRUEBA_LOCAL" = "1" ]; then
    yellow "   PRUEBA_LOCAL=1: no se mira el servicio $ODOO_SERVICE"
elif systemctl show -p LoadState "$ODOO_SERVICE" 2>/dev/null | grep -q '=loaded$'; then
    systemctl is-active --quiet "$ODOO_SERVICE" && ok "Servicio $ODOO_SERVICE activo" || bad "Servicio $ODOO_SERVICE no esta activo"
else
    bad "No existe el servicio $ODOO_SERVICE"
fi
[ -d "$ADDONS_DIR" ] && ok "Ruta de addons: $ADDONS_DIR" || bad "No existe $ADDONS_DIR"

if [ "$ERRORS" -gt 0 ]; then
    red "RESULTADO: $ERRORS problema(s). No se ha tocado nada ni se ha reiniciado Odoo."; exit 1
fi
if [ "$MODE" = "check" ]; then
    green "RESULTADO: todo correcto. No se ha tocado nada ni se ha reiniciado Odoo."
    echo "Para instalar: sudo AUTO_CONFIRM=1 bash $0 install $(for i in "${!MODULOS[@]}"; do printf '%s %s ' "${MODULOS[$i]}" "${VERSIONES[$i]}"; done)"
    exit 0
fi

if [ "${AUTO_CONFIRM:-0}" != "1" ]; then
    echo
    yellow "Se copiaran ${#MODULOS[@]} modulo(s) y se reiniciara Odoo UNA vez al final (~1 minuto sin Odoo)."
    read -r -p "Escribe SI para continuar: " answer </dev/tty
    [ "$answer" = "SI" ] || { echo "Cancelado. No se ha tocado nada."; exit 0; }
fi

echo
echo "== 3. Copias de seguridad =="
mkdir -p "$BACKUP_DIR"
OWNER="$(stat -c '%U:%G' "$ADDONS_DIR" 2>/dev/null || true)"
for mod in "${MODULOS[@]}"; do
    if [ -d "$ADDONS_DIR/$mod" ]; then
        b="$BACKUP_DIR/${mod}_$STAMP"
        cp -a "$ADDONS_DIR/$mod" "$b"
        BACKUPS+=("$mod=$b")
        ok "Copia $mod: $b"
    else
        BACKUPS+=("$mod=")
        yellow "   $mod es nuevo; no habia copia anterior"
    fi
done

restaurar(){
    red "Error copiando. Se deja todo como estaba..."
    for par in "${BACKUPS[@]}"; do
        m="${par%%=*}"; b="${par#*=}"
        rm -rf "${ADDONS_DIR:?}/$m"
        if [ -n "$b" ] && [ -d "$b" ]; then cp -a "$b" "$ADDONS_DIR/$m"; fi
    done
    red "No se ha reiniciado Odoo."
    exit 1
}

echo
echo "== 4. Copiar los modulos sin reiniciar =="
for mod in "${MODULOS[@]}"; do
    rm -rf "${ADDONS_DIR:?}/$mod" && cp -a "$TMP/zip_$mod/$mod" "$ADDONS_DIR/$mod" || restaurar
    if [ -n "$OWNER" ] && [ "$OWNER" != 'root:root' ] && [ "$PRUEBA_LOCAL" != "1" ]; then
        chown -R "$OWNER" "$ADDONS_DIR/$mod"
    fi
    ok "$mod copiado ($(version_de "$ADDONS_DIR/$mod/__manifest__.py"))"
done

echo
if [ "$PRUEBA_LOCAL" = "1" ]; then
    yellow "== 5. PRUEBA_LOCAL=1: sin reinicio =="
else
    echo "== 5. UNICO reinicio de Odoo =="
    systemctl restart "$ODOO_SERVICE"
    ready=0
    for attempt in $(seq 1 30); do
        if systemctl is-active --quiet "$ODOO_SERVICE" && curl -fsS -m 3 -o /dev/null http://127.0.0.1:8069/web/login; then
            ready=1; break
        fi
        sleep 2
    done
    if [ "$ready" != "1" ]; then
        red "Odoo no responde tras el reinicio. Consulta: sudo journalctl -u $ODOO_SERVICE -n 80 --no-pager"
        red "Para volver atras, copiar cada copia de seguridad a $ADDONS_DIR y reiniciar:"
        for par in "${BACKUPS[@]}"; do red "   ${par%%=*}: ${par#*=}"; done
        exit 1
    fi
    green "Odoo reiniciado y respondiendo."
fi
echo
echo "Ahora en Odoo (Aplicaciones, quitando el filtro 'Aplicaciones'):"
echo "  1. Actualizar lista de aplicaciones"
echo "  2. Actualizar, en este orden: ${MODULOS[*]}"
echo "  3. Ctrl+F5 en los navegadores y en las PDA"
echo "Vuelta atras (copias de seguridad):"
for par in "${BACKUPS[@]}"; do echo "   ${par%%=*}: ${par#*=}"; done
