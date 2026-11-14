#!/usr/bin/env bash
# KOROSHI - Fase 3 de la auditoria 13/11: integraciones y permisos (14/11/2026).
#   ANTES: el script de la fase 2 (operarios 2.12, informe 1.1, kpi 1.6, consumibles 1.4, monitor 1.26). Estos
#   ZIP los incluyen (operarios, kpi y monitor), pero koroshi_informe 1.1.0 solo esta en el de la fase 2.
#   koroshi_xpo_bultos    v1.2.0 (sobre 1.1.0): bultos_de() / valores_xpo(): una sola cuenta de bultos, peso, volumen.
#   koroshi_s4t_envios    v1.2.0 (sobre 1.1.0): OUT pendiente no para el pedido; errores reintentables / rechazados
#                         con aviso; respuesta en lista; cron por turnos. Depende de koroshi_xpo_bultos. SIGUE EN
#                         MODO DIAGNOSTICO con el cron archivado.
#   koroshi_s4t_traspasos v1.1.0 (sobre 1.0.0, SIN INSTALAR en Odoo): savepoint por traspaso con el JSON crudo,
#                         conciliacion diaria, reintentos. Solo se copia la carpeta: instalarlo es otra decision.
#   koroshi_operarios     v2.13.0 (sobre 2.12.0): rutas con permiso de Inventario; employee_id comprobado;
#                         «Asignar a operario» sin display_notification.
#   koroshi_actividades   v1.2.0 (sobre 1.1.0, SIN INSTALAR en Odoo): rutas con permiso; persona comprobada.
#   koroshi_monitor       v1.27.0 (sobre 1.26.0): rutas con permiso; cache compartida 20 s; sin refresco con la
#                         pestana oculta; Z-ddmm- con fecha de creacion.
#   koroshi_kpi           v1.7.0 (sobre 1.6.0): hoja de carga con permiso.
#   koroshi_menu          v2.2.0 (sobre 2.1.0): Guardar de Ajustes KOROSHI solo para el responsable de Inventario.
#   Nada en tablas de stock. Campo nuevo solo en koroshi_s4t_traspaso (intentos).
#   En Odoo: Actualizar XPO bultos, Envios a S4T, Operarios, Monitor, KPI y Menu.
# Valida los ZIP antes de tocar nada; si falla, no copia nada ni reinicia.
# Uso (con el ZIP en /home/it_nath_group):
#   bash instalar_koroshi_fase3_auditoria_2026-11-14.sh check
#   sudo AUTO_CONFIRM=1 bash instalar_koroshi_fase3_auditoria_2026-11-14.sh install
# El reinicio corta Odoo ~1 minuto: hacerlo fuera de horas, sin nadie validando en las PDA.
set -euo pipefail

MODE="${1:-check}"
ZIP_DIR="${ZIP_DIR:-/home/it_nath_group}"
ADDONS_DIR="${ADDONS_DIR:-/opt/nath-erp/nath/enterprise-addons}"
ODOO_SERVICE="${ODOO_SERVICE:-nath-erp}"
BACKUP_DIR="${BACKUP_DIR:-/opt/nath-erp/copias_modulos}"
TMP="$(mktemp -d /tmp/koroshi_fase3.XXXXXX)"
STAMP="$(date +%Y-%m-%d_%H%M%S)"
ERRORS=0
BACKUPS=()
trap 'rm -rf "$TMP"' EXIT

red(){ printf '\033[31m%s\033[0m\n' "$*"; }
green(){ printf '\033[32m%s\033[0m\n' "$*"; }
yellow(){ printf '\033[33m%s\033[0m\n' "$*"; }
ok(){ green "   OK  $*"; }
bad(){ red "   MAL $*"; ERRORS=$((ERRORS + 1)); }

if [ "$MODE" != "check" ] && [ "$MODE" != "install" ]; then
    red "Uso: $0 check|install"; exit 2
fi
if [ "$MODE" = "install" ] && [ "$(id -u)" != "0" ]; then
    red "Para instalar hay que usar sudo."; exit 1
fi

# modulo|zip|version esperada en el manifest
declare -a MODULES=(
    "koroshi_xpo_bultos|$ZIP_DIR/20261114_koroshi_xpo_bultos_v1.2.0.zip|13.0.1.2.0"
    "koroshi_s4t_envios|$ZIP_DIR/20261114_koroshi_s4t_envios_v1.2.0.zip|13.0.1.2.0"
    "koroshi_s4t_traspasos|$ZIP_DIR/20261114_koroshi_s4t_traspasos_v1.1.0.zip|13.0.1.1.0"
    "koroshi_operarios|$ZIP_DIR/20261114_koroshi_operarios_v2.13.0.zip|13.0.2.13.0"
    "koroshi_actividades|$ZIP_DIR/20261114_koroshi_actividades_v1.2.0.zip|13.0.1.2.0"
    "koroshi_monitor|$ZIP_DIR/20261114_koroshi_monitor_v1.27.0.zip|13.0.1.27.0"
    "koroshi_kpi|$ZIP_DIR/20261114_koroshi_kpi_v1.7.0.zip|13.0.1.7.0"
    "koroshi_menu|$ZIP_DIR/20261114_koroshi_menu_v2.2.0.zip|13.0.2.2.0"
)

echo "KOROSHI - Fase 3 integraciones y permisos ($([ "$MODE" = install ] && echo 'MODO INSTALAR' || echo 'MODO COMPROBACION'))"

if ! command -v unzip >/dev/null 2>&1; then
    red "Falta unzip en el servidor."; exit 1
fi

echo
echo "== 1. Validar los ZIP antes de tocar nada =="
for entry in "${MODULES[@]}"; do
    IFS='|' read -r module zip version <<< "$entry"
    echo "--- $module ---"
    if [ ! -f "$zip" ]; then bad "No existe $zip"; continue; fi
    if ! unzip -tqq "$zip"; then bad "ZIP danado: $zip"; continue; fi
    unzip -l "$zip" > "$TMP/${module}.list"
    if ! grep -qE "[[:space:]]${module}/__manifest__\.py$" "$TMP/${module}.list"; then
        bad "Falta ${module}/__manifest__.py en el ZIP"; continue
    fi
    unzip -q "$zip" -d "$TMP"
    if [ ! -f "$TMP/$module/__manifest__.py" ]; then
        bad "No se pudo extraer $module"; continue
    fi
    if grep -q "'version': '$version'" "$TMP/$module/__manifest__.py"; then
        ok "$module: ZIP valido, version $version"
    else
        bad "$module: el manifest no tiene la version $version"
    fi
    if [ -d "$ADDONS_DIR/$module" ]; then
        actual="$(grep -oE "'version': '[^']+'" "$ADDONS_DIR/$module/__manifest__.py" 2>/dev/null || true)"
        echo "        ahora en el servidor: ${actual:-sin version} -> se ACTUALIZARA"
    else
        echo "        no esta en el servidor -> se INSTALARA nuevo"
    fi
done

echo
echo "--- fase 2 (tiene que ir antes) ---"
if grep -q "'version': '13.0.1.1.0'" "$ADDONS_DIR/koroshi_informe/__manifest__.py" 2>/dev/null; then
    echo "        koroshi_informe 1.1.0 copiado: la fase 2 ya esta"
else
    yellow "        koroshi_informe no es la 1.1.0: pasar ANTES el script de la fase 2 (si no, el correo y el KPI no"
    yellow "        usan la cifra unica)."
fi
for dep in delivery_xpo api_s4t_batch_update_PROD koroshi_contenedores; do
    if [ -d "$ADDONS_DIR/$dep" ] || find /opt/nath-erp -maxdepth 4 -type d -name "$dep" 2>/dev/null | grep -q .; then
        echo "        $dep: presente (no se toca)"
    else
        yellow "        $dep: no encontrado en las rutas habituales (comprobar en Odoo)"
    fi
done

echo "== 2. Validar Odoo y la ruta de addons =="
if systemctl show -p LoadState "$ODOO_SERVICE" 2>/dev/null | grep -q '=loaded$'; then
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
    echo "Para instalar: sudo AUTO_CONFIRM=1 bash $0 install"
    exit 0
fi

if [ "${AUTO_CONFIRM:-0}" != "1" ]; then
    echo
    yellow "Se copiaran los 8 modulos y se reiniciara Odoo UNA vez al final (~1 minuto sin Odoo)."
    read -r -p "Escribe SI para continuar: " answer </dev/tty
    [ "$answer" = "SI" ] || { echo "Cancelado. No se ha tocado nada."; exit 0; }
fi

echo
echo "== 3. Copias de seguridad =="
mkdir -p "$BACKUP_DIR"
OWNER="$(stat -c '%U:%G' "$ADDONS_DIR" 2>/dev/null || true)"
for entry in "${MODULES[@]}"; do
    IFS='|' read -r module zip version <<< "$entry"
    if [ -d "$ADDONS_DIR/$module" ]; then
        backup="$BACKUP_DIR/${module}_$STAMP"
        cp -a "$ADDONS_DIR/$module" "$backup"
        BACKUPS+=("$module|$backup")
        ok "Copia $module: $backup"
    else
        BACKUPS+=("$module|")
        yellow "   $module es nuevo; no habia copia anterior"
    fi
done

echo
echo "== 4. Copiar los modulos sin reiniciar =="
rollback(){
    red "Error copiando el modulo. Restaurando como estaba..."
    for pair in "${BACKUPS[@]}"; do
        IFS='|' read -r module backup <<< "$pair"
        rm -rf "${ADDONS_DIR:?}/$module"
        if [ -n "$backup" ] && [ -d "$backup" ]; then cp -a "$backup" "$ADDONS_DIR/$module"; fi
    done
}
for entry in "${MODULES[@]}"; do
    IFS='|' read -r module zip version <<< "$entry"
    if ! rm -rf "${ADDONS_DIR:?}/$module" || ! cp -a "$TMP/$module" "$ADDONS_DIR/$module"; then
        rollback
        red "No se ha reiniciado Odoo porque la copia no termino bien."
        exit 1
    fi
    if [ -n "$OWNER" ] && [ "$OWNER" != 'root:root' ]; then chown -R "$OWNER" "$ADDONS_DIR/$module"; fi
    ok "$module copiado"
done

echo
echo "== 5. UNICO reinicio de Odoo =="
systemctl restart "$ODOO_SERVICE"
ready=0
for attempt in $(seq 1 30); do
    if systemctl is-active --quiet "$ODOO_SERVICE" && curl -fsS -m 3 -o /dev/null http://127.0.0.1:8069/web/login; then
        ready=1
        break
    fi
    sleep 2
done
if [ "$ready" != "1" ]; then
    red "Odoo no responde tras el reinicio. Consulta: sudo journalctl -u $ODOO_SERVICE -n 80 --no-pager"
    red "Para volver atras: copia las carpetas de $BACKUP_DIR/*_$STAMP a $ADDONS_DIR, borra las nuevas y reinicia."
    exit 1
fi
green "Odoo reiniciado y respondiendo."
echo
echo "Ahora en Odoo (Aplicaciones, quitando el filtro 'Aplicaciones'):"
echo "  1. Actualizar lista de aplicaciones"
echo "  2. Modo desarrollador > Aplicaciones, Actualizar: KOROSHI XPO bultos (v1.2.0), KOROSHI Envios a S4T (v1.2.0),"
echo "     KOROSHI Operarios (v2.13.0), KOROSHI Monitor (v1.27.0), KOROSHI KPI (v1.7.0) y KOROSHI Menu (v2.2.0)."
echo "     koroshi_s4t_traspasos y koroshi_actividades NO estan instalados: solo quedan copiados."
echo "  3. Ctrl+F5 en el PC y en las PDA (Monitor, Lecturas, Operarios)."
echo "  4. Comprobar con un usuario de PDA: Lecturas y el Monitor funcionan igual (piden el permiso de Inventario, que"
echo "     el 14/11 tienen los 6 usuarios de la empresa 8). Si a alguien le sale 'Hace falta el permiso de"
echo "     Inventario', darle Inventario > Usuario."
echo "  5. Ajustes KOROSHI > Guardar con el responsable: guarda. Con otro usuario: 'Solo el responsable...'."
echo "  6. Asignar a operario (albaranes): ya no da error al acabar; abre la cola del operario."
echo "  7. S4T envios sigue en modo diagnostico: «Recalcular» en un pedido con una OUT pendiente ya crea sus envios."
echo "     Opcional: parametro koroshi_s4t_envios.avisar con los correos para los rechazos."
echo "Vuelta atras: copiar $BACKUP_DIR/<modulo>_$STAMP de cada uno a $ADDONS_DIR, reiniciar y Actualizar"
echo "  (xpo_bultos 1.1.0, s4t_envios 1.1.0, operarios 2.12.0, monitor 1.26.0, kpi 1.6.0, menu 2.1.0). El campo"
echo "  'intentos' de traspasos y el estado 'rechazado' de envios no molestan a las versiones de antes."
