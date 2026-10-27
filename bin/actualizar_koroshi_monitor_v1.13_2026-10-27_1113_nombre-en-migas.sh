#!/usr/bin/env bash
# =============================================================================
# ACTUALIZAR el modulo KOROSHI Monitor (koroshi_monitor), ya instalado, a la version 1.13 que va dentro de este
# script (nombre del monitor en las migas de pan). Con comprobaciones antes de tocar nada.
#
# Uso (en el servidor de Odoo):
#   sudo bash ESTE_SCRIPT.sh            -> SOLO COMPRUEBA. No escribe ni reinicia nada.
#   sudo INSTALAR=1 bash ESTE_SCRIPT.sh -> comprueba y, si todo esta bien y escribes SI, actualiza.
#
# Que comprueba: Odoo corriendo, su configuracion y el servicio; que cada modulo esta instalado en la
# base de datos y SOLO en la carpeta de modulos; que los ficheros nuevos estan enteros, los .py compilan
# y los .xml estan bien; espacio en disco. Si algo falla, para y no toca nada.
# Que hace al actualizar: copia de cada carpeta actual en /opt/nath-erp/copias_modulos/<modulo>_<fecha>,
# pone las nuevas, reinicia Odoo (las PDA ~1 minuto sin conexion) y espera a que responda. Despues hay que
# pulsar Actualizar en el modulo en Odoo (Aplicaciones), o decirmelo y lo hago yo.
# =============================================================================
set -uo pipefail

MODULOS="koroshi_monitor"
ADDONS_DIR="${ADDONS_DIR:-/opt/nath-erp/nath/enterprise-addons}"
ODOO_SERVICE="${ODOO_SERVICE:-nath-erp}"
ODOO_DB="${ODOO_DB:-NATH_PRODUCTION}"
INSTALAR="${INSTALAR:-0}"
COPIAS=/opt/nath-erp/copias_modulos
TMP=$(mktemp -d /tmp/koroshi_act.XXXXXX)
ERRORES=0
AVISOS=0

rojo() { printf '\033[31m%s\033[0m\n' "$*"; }
verde() { printf '\033[32m%s\033[0m\n' "$*"; }
amarillo() { printf '\033[33m%s\033[0m\n' "$*"; }
ok() { verde "   OK  $*"; }
mal() { rojo "   MAL $*"; ERRORES=$((ERRORES + 1)); }
aviso() { amarillo "   OJO $*"; AVISOS=$((AVISOS + 1)); }
paso() { echo; echo "== $* =="; }
version() { grep -oE "'[0-9]+\.[0-9.]+'" "$1/__manifest__.py" 2>/dev/null | head -1; }
trap 'rm -rf "$TMP"' EXIT

if [ "$(id -u)" != "0" ]; then rojo "Hay que ejecutarlo con sudo:  sudo bash $0"; exit 1; fi
echo "KOROSHI - actualizar Monitor v1.13 ($( [ "$INSTALAR" = "1" ] && echo 'MODO ACTUALIZAR' || echo 'MODO SOLO COMPROBAR: no se cambia nada'))"

paso "0. Modulos que van dentro del script"
if ! sed -n '/^__KOROSHI_TGZ__$/,$p' "$0" | sed '1d' | base64 -d > "$TMP/m.tgz" 2>/dev/null || ! tar -xzf "$TMP/m.tgz" -C "$TMP" 2>/dev/null; then
    rojo "   El paquete de dentro del script esta danado (copia incompleta?)"; exit 1
fi
for m in $MODULOS; do
    if [ -f "$TMP/$m/__manifest__.py" ]; then ok "$m nuevo: version $(version "$TMP/$m")"; else mal "falta $m dentro del script"; fi
done

paso "1. Odoo, configuracion y servicio"
PROC=$(ps -eo args | grep -E 'odoo-bin|openerp-server' | grep -v grep | head -1 || true)
[ -n "$PROC" ] && ok "Odoo corriendo" || mal "no encuentro ningun proceso odoo-bin corriendo"
ODOO_USER=$(ps -eo user:32,args | grep -E 'odoo-bin|openerp-server' | grep -v grep | head -1 | awk '{print $1}' || true)
ODOO_PY=$(echo "$PROC" | awk '{print $1}'); case "$ODOO_PY" in *python*) : ;; *) ODOO_PY=python3 ;; esac
[ -z "${ODOO_CONF:-}" ] && ODOO_CONF=$(echo "$PROC" | grep -oE '(-c|--config)[ =][^ ]+' | head -1 | sed -E 's/^(-c|--config)[ =]//' || true)
if [ -n "${ODOO_CONF:-}" ] && [ -r "$ODOO_CONF" ]; then ok "configuracion: $ODOO_CONF"; else mal "no encuentro la configuracion (forzar con ODOO_CONF=...)"; ODOO_CONF=""; fi
if systemctl show -p LoadState "$ODOO_SERVICE" 2>/dev/null | grep -q "=loaded$"; then
    systemctl is-active --quiet "$ODOO_SERVICE" && ok "servicio $ODOO_SERVICE en marcha" || mal "el servicio $ODOO_SERVICE no esta en marcha"
else
    mal "no existe el servicio $ODOO_SERVICE (forzar con ODOO_SERVICE=...)"
fi

paso "2. Modulos instalados ahora (carpetas)"
ADDONS_PATH=""
[ -n "$ODOO_CONF" ] && ADDONS_PATH=$(grep -E '^\s*addons_path\s*=' "$ODOO_CONF" | head -1 | sed -E 's/^[^=]*=\s*//' | tr -d ' ')
DUENO=$(stat -c '%U:%G' "$ADDONS_DIR" 2>/dev/null || echo "")
for m in $MODULOS; do
    for d in $(echo "$ADDONS_PATH" | tr ',' ' '); do
        if [ -e "$d/$m" ] && [ "$(readlink -f "$d")" != "$(readlink -f "$ADDONS_DIR")" ]; then mal "hay otro $m en $d: no se cual usa Odoo, no toco nada"; fi
    done
    if [ -f "$ADDONS_DIR/$m/__manifest__.py" ]; then ok "$m en $ADDONS_DIR (version actual $(version "$ADDONS_DIR/$m"))"; else mal "$m no esta en $ADDONS_DIR"; fi
done

paso "3. Base de datos $ODOO_DB"
conf() { [ -n "$ODOO_CONF" ] && grep -E "^\s*$1\s*=" "$ODOO_CONF" | head -1 | sed -E 's/^[^=]*=\s*//' | tr -d ' ' || true; }
DB_HOST=$(conf db_host); DB_PORT=$(conf db_port); DB_USER=$(conf db_user); DB_PASS=$(conf db_password)
[ "$DB_HOST" = "False" ] && DB_HOST=""; [ "$DB_PORT" = "False" ] && DB_PORT=""; [ "$DB_PASS" = "False" ] && DB_PASS=""
sql() {
    if [ -n "$DB_HOST" ] || [ -n "$DB_PASS" ]; then
        PGPASSWORD="$DB_PASS" psql -X -A -t ${DB_HOST:+-h "$DB_HOST"} ${DB_PORT:+-p "$DB_PORT"} -U "${DB_USER:-odoo}" -d "$ODOO_DB" -c "$1" 2>/dev/null
    else
        sudo -u "${DB_USER:-${ODOO_USER:-odoo}}" psql -X -A -t -d "$ODOO_DB" -c "$1" 2>/dev/null
    fi
}
if R=$(sql "select 1"); [ "$R" = "1" ]; then
    ok "conecto con la base de datos (sin ensenar contrasenas)"
    for m in $MODULOS; do
        E=$(sql "select state from ir_module_module where name='$m'")
        [ "$E" = "installed" ] && ok "$m instalado en Odoo" || mal "$m no esta instalado (estado '$E')"
    done
else
    aviso "no puedo conectar con la base de datos por psql: no compruebo el estado de los modulos"
fi

paso "4. Codigo nuevo"
if "$ODOO_PY" -c "import sys" 2>/dev/null; then
    for f in $(cd "$TMP" && find $MODULOS -name '*.py'); do
        "$ODOO_PY" -m py_compile "$TMP/$f" 2>"$TMP/err" && ok "compila $f" || mal "no compila $f: $(cat "$TMP/err")"
    done
    for f in $(cd "$TMP" && find $MODULOS -name '*.xml'); do
        "$ODOO_PY" -c "import sys, xml.dom.minidom as m; m.parse(sys.argv[1])" "$TMP/$f" 2>/dev/null && ok "xml bien: $f" || mal "xml mal formado: $f"
    done
else
    aviso "no encuentro el Python de Odoo; no compruebo el codigo"
fi

paso "5. Espacio en disco"
LIBRE=$(df -Pk "$ADDONS_DIR" 2>/dev/null | awk 'NR==2 {print $4}')
if [ -n "$LIBRE" ] && [ "$LIBRE" -gt 51200 ]; then ok "$((LIBRE / 1024)) MB libres"; else mal "poco espacio libre en $ADDONS_DIR"; fi

echo
if [ "$ERRORES" -gt 0 ]; then rojo "RESULTADO: $ERRORES problema(s). No se ha tocado nada. Pasame lo que ha salido."; exit 1; fi
if [ "$AVISOS" -gt 0 ]; then verde "RESULTADO: todo bien ($AVISOS aviso(s) en amarillo). No se ha tocado nada."; else verde "RESULTADO: todo bien. No se ha tocado nada."; fi
if [ "$INSTALAR" != "1" ]; then echo "Para actualizar:  sudo INSTALAR=1 bash $0"; exit 0; fi

echo
amarillo "Se van a cambiar $MODULOS por las versiones nuevas (con copia) y REINICIAR $ODOO_SERVICE (las PDA ~1 minuto sin conexion)."
read -r -p "Escribe SI para seguir: " RESP </dev/tty
if [ "$RESP" != "SI" ]; then echo "Cancelado. No se ha tocado nada."; exit 0; fi
paso "Actualizando"
FECHA=$(date +%Y-%m-%d_%H%M)
mkdir -p "$COPIAS"
for m in $MODULOS; do
    cp -a "$ADDONS_DIR/$m" "$COPIAS/${m}_$FECHA" || { rojo "no se ha podido hacer la copia de $m: no sigo"; exit 1; }
    ok "copia de $m: $COPIAS/${m}_$FECHA"
done
for m in $MODULOS; do
    rm -rf "$ADDONS_DIR/$m" && cp -a "$TMP/$m" "$ADDONS_DIR/$m" && { [ -z "$DUENO" ] || chown -R "$DUENO" "$ADDONS_DIR/$m"; } && ok "$m nuevo puesto (version $(version "$ADDONS_DIR/$m"))" || {
        rojo "fallo al poner $m: vuelvo a poner las versiones anteriores"
        for x in $MODULOS; do rm -rf "$ADDONS_DIR/$x"; cp -a "$COPIAS/${x}_$FECHA" "$ADDONS_DIR/$x"; done
        exit 1; }
done
systemctl restart "$ODOO_SERVICE"
for i in $(seq 1 30); do
    sleep 2
    if systemctl is-active --quiet "$ODOO_SERVICE" && curl -s -o /dev/null -m 3 http://127.0.0.1:8069/web/login 2>/dev/null; then break; fi
done
if systemctl is-active --quiet "$ODOO_SERVICE"; then
    ok "$ODOO_SERVICE reiniciado y en marcha"
    verde "Ahora en Odoo: Aplicaciones > KOROSHI Monitor zonas > Actualizar (o dimelo y lo hago yo). Despues Ctrl+F5 en el monitor."
else
    rojo "$ODOO_SERVICE NO ha arrancado. Ultimas lineas del registro:"
    journalctl -u "$ODOO_SERVICE" -n 30 --no-pager
    rojo "Para volver atras:"
    for m in $MODULOS; do rojo "  sudo rm -rf $ADDONS_DIR/$m && sudo cp -a $COPIAS/${m}_$FECHA $ADDONS_DIR/$m"; done
    rojo "  sudo systemctl restart $ODOO_SERVICE"
fi
exit 0
__KOROSHI_TGZ__
H4sIAAAAAAAAA+xc63LbSHb276mad+ix1gFgkxBJW/YsPXSilTQ7GsuWS7a3suZoWRABibBAgMZF
lriZVJ4mr5D/eZQ8Sb5zuhtoXCgrszNbqUpYLhvoy+nT3ed+DnyZpEm2CGfLJA7zJN2+9xv8Bvg9
29m5N3g6GD7bGfG/g8GQ29Xv3nBn9GwwePrk8c7g3mA4evJ0cE/s/BbINH9FlnupEPfyYo4/f48V
/1f9Lhv3P0/iPE2iKEizX40W7n7/z0ZPHqN/uDMYPf3/+/97/G67/6UXxu7q5m9egy746ZMnG+7/
ybMRaKN+/08fPxneE4NfYX9f/P0fv/8t0X/YF/PED+OLsSjy8/631PL1V1ti8mv+CODL45Pjtz8c
ileS1sQ6ib1M9IXv5UkmVl7qicjDv3HuRXiwsyRKRBQEPREnYu4tz0JPxJ7vOS6gEcDtJvVKSPbH
LIl7osgKLw0xM4lFFmRhEjuu2Ef/MvHxdxZcFLGwVmlwHn5MrDEBFMDG+tAfjYaDviVs7yItVt4c
M4NM+AEj7OCUYk+ch4QqNnH8/h2vQH09YPnRo5F5GMQ+3tHbk4BF2bYK/NBPgJ8PVJfJVbhEB+HN
u4znQeQBP6cnFkUwp+0UZ+G8xCLM8hAHhH4NNwrjwIvQZx8tw7h/tPSuRSJeve9fXztylSgIfS/r
iQC07ifCXgTzhScm4sqL0EE4zYs0S9DiRRcJD09K8CtgjR46eNkDoKs0XAZ0XQGYBv/eiCLKw2XV
sC0WSconIdcg7N3yhN8dHrze3307HkHM93HUo8c47KuhO+zx2dKR0tHqg8pCebwZzj4CxVA/IL85
2HeFAqWRnacB8Mywf723DLsOcGy0SVwTKGoZZstEPMK/cUHH/qkIBI4DYsCn05nTRmmJG5EVIg3z
ZXUWQSQbsHwkgk9FuAJ6hFJ1yow5b/6GqJmfQGNXuDc+j/NQH4QQ2PJozDSTiXmQpowuxmgUQALe
HK8FWCIBwfKghMCq47b5qDyaiFPCU0ZraPBvdk9293dnrw5fO0BmBZHODDdPLogSE+ExcgwjiBUJ
0BkxESt8JAarZJ44JtpPxoqYMnCQl85DL8IVEmTAzcFfdNDyYG96uA26QoaYSugMdSl3W6HJq+Ow
wCaZXoxnJhdBOubHLE/mlwAIXgliVlZ0aLQ/C93cC0SwnSDDhj3nuYYDxlmBjFNQQ3pF9/xISHSf
i3MvAkOhU+G8CoEVLljSH0BjMexD2BFfoub6G+GleTgvInU0r4iucLxeRG2Srog2Vt5FGDMd0oH1
MbVvCpb+h/5Dd5EvIzqLszDevsJFcY/7G0jhcAn0cxK5ASgoKBtSPJYvq5t8Ta/nabIUuMxEqI7z
MIh8CJJFnq+MbpfeRQkJG89ymr93/OrN7us/zw73cbjfivK3JQ6+//5g793hnw7E0fEfD9++O9x7
2xNv3SNs+fXszcnB94c/Hr/FpOGOMakmjul0M4i9mGg3oMPLVlFw4Z1FAcHYP9yl+Y9F7bdFgoCJ
7v47lsbZ/dsBvTt8czyDoDncPwY0yxQ51tdfGZQ7EaOBsUyNp5rEz9RJkkdLoInmYZtUQAFtAP5L
IGYUzwpvnodXnkNnenIwOzp8fbB7xMTsYtgqjAI7tcSR/ZP/yBGWw4NevW8O+IsNnUBD1Ai5j+ao
n85eYgyktPvwdxav+PVXc5BxJl5KZau0t0137u6V5qIzppHMacG5mOVrOwuic2rVp5IGUA0xE5dL
tAeRjgUltbhBfOUWYE03Xwvwl3VQpMkq2H7l+WnoSzxK2IvkZhYl4LNNS2jqdsuHOPls88JFPndc
LyvXJwguYes4PNquL6Wsg4zHQYHGV+ZyUZIHdHtonlose9xVOL+EKeWeefl8YZ26WeEntuNmAYTk
wp7aVuwtA6snrEkUXvLDh/4DyzmFkEz9IJ1YoU8UOEdPBMMgnzweDJxqRVIjTDDT06rxHAdGqIgw
ligZKLIGl5tgAZfjLICBm4LIw9y2+lho6EwHp5CHeKlPDM/LuXGSE3i5fgN+hZjrrchcsNUspwUO
bGbLoY54MREVr3eAPIMuv2zdrZzdoIfUUxfk5+b9YEHC288b0BUoyzKvEvSEE5ISzt3XhEMqJrjO
Z/QC+b1ctSiWF22haT3wxw8GI98SD6A3CLi7SAoMls/M+UGd1pQ06NzJVikrQBw+6RWxhHby4mS+
CCTM324vFfrioXg6AKWYm6jtgcxig1lgKYIfsp4mo55Ef/IarEfGDbDg5/pWecw29wr7/bs9mH3s
CrCHAAlN9ruyprPnpr2lzNLthjFaGWvmKlLOxhI06emWHUaijSfjoLFuQNaCwXW0VZzyX3+uc+KK
+IS33aA6kCIZ3SsII/AqCbkGu7FymLSaQcXW3u6Pu8IiyASlg1nUXOp1FWvLOc50eDodjyCJ8jRc
2U4TpyXYjLHC6eZxkM5CnyVEF4Lrbuy0jPDgKKyk5AMUfrWrdwMq5CGs7Tz7HOaLUlZ0bGrNiNUA
TEmClFNO63P4SqYrN/RP6WLaAK21NRbrXkcHSUb0daLbNZ7O25K2e1d3UuQMTcraYBXB3rUttnq2
YRtsk+C3nI6ZW2RdPxsL6+WzHSjhvW24OUe7fz6GlB4J+w+7J3sHR8evdx1LQOlesZngjdk1gI1c
CYeXHThJjgFadqn8tV6SZODwlW3qdC/SpFjZA8ehU5GNmtR6RGf94WnXUUgrmk8jSUOYwpsPtcCo
gTsANHY0yzey3csXaa3jddq53Ex6zRYdSm7DV7VmkRyMp2VRtndNpcORosmanRnPLBlunSlte94k
nnKe5WM2t5BdwW+b7ns4gDuVh5DFuZRW8GrijKxpdjjsf35zvP3Ho7eO0I57XEDOkWziKIYKIJBd
GbHf2IFhkH8CLmdJEoEl516ahmB1LMPWygz81LkvmF60gdDvNRAejqU09s7SMFWrKupjAc0mYh3g
z1pRlFDgRCqPC/S7KgJfUnEqbLpwRzpkpsOG1xtPuW2ln1xFUJ43HDhzuZYvJ8nIoff66mMBtvL0
BDJnCHggoFJlTMHYF9Zu2H9oCZpm34yCEmT7KeMQ0oU4JowtpR9xwBTvsS2mHer7ZkJ/y2gQWYft
u7nLb9pYcZUmfjHPZ0WynH3Kb6hJHm/gz7wrD9LzLAQ/33Qx551+1icKVQCCJH5jSSBw6tQV5ZLU
GZ1gQ/Kfs+lCknxZ28AprNSmwJ9CZsB0nQga2thdY6wKACy9axuDu/d9SrKJxQyG1Peiu5wWBiyd
GAl6qndvsXnCETrIIB0v6FVRDWhIIta+omqHLCSQbpQY0Q49pGSFbTW4sUMVqes6Csy277ol0ugE
6QX1DYasFLBNLeNOxTewAqRwa5MJBioBfaqdgamBEF0jA2y0wUhhtfCPxBKYdEcCVJfZtV26ix7v
7tQxJQ/fRQfTutTxyzj3l7Kn+jW59JPBPmRo52ESq67PaUiqhIXE37QmMz7M5NkKGsC7CJr8uSV+
UPHbuYz7Skt6UoZ159AfacAaqJDGp02xVwrOCOWfeDA4Qe2e2PvRccWRV86NPHMhvhAWwyEYcsyB
tzS5SD1Y8BcFBWUpoIgrI3Nb3Z5cQcWBL5JoFUCyqwxBFoqoCC5IrJvL4KI5vSCXsz8Wca7iMRmw
exvKsOe4jNnKJXi0a3iUfjZTpjYFA22yCKbLaNp1nORUs5yL2DGXmIO5Ngw/dYzzJxT0Qi0H4xPB
M8iXudpVsDaSsEG6ehcUdphadG+aqk6bZniJyHT1aWoxnmSUf2pMqyZB3rFD3kCcXCi0WMpFq4wr
6atV70sgrcy7xr7Nc9ysMqIv6QzyczhqY9NYk8GUZGq2atlEbos0d7ethshkm1OG8QB7+vhUxzpk
A8c6dkDZZGnIITCWW4pEm66QnL5v80tjHWweq5QhQG2hdw0lBMK4W0LDIi6lcxjnNgYq637oOA04
hHQHlGUhEXn1/jYkFCLLogOCxgU2udzwsqiQaJ2NdAikqscFlTLytLXrejdpsY7FN7PhLZhKN0Ah
u5HnO47gs5hsWo5JrmQy9wLy5BbQgtlgauqB087NUdiLUPakkv8svtOvt+yPBk/E51sBnmmAL/Tr
LQDPbgEonQWOERB28lVCnsjIUFdEgH4UxgrjItiIJ2TNtBQ05f7rrRtgN6bedho8VEmv8kxqjbet
UU7sXGKBZhmZ1kHBz47Y3hZPB+2xWuBOFyyZ1RtT0kIaQJTrvIVn6LcFvymkhAWpddaTUhsGKvNK
WU5+EjZlaHVeYqWy+M5zGplEASeTMfT9c9LDMWdHuz1SDlhPmLWTbjKWGKmgtREwsj70LRmqiFQg
zW4N+UP/5fGJGmW9tzTfNDRDB6vy5SgdVMpI+5dEUj/DluctOO2IKuuqXnlZPVq2nndQyVodDKb0
tcwvm1xx//59MtOyvr4PI8sbUI7D0wnpdnxzTGnlNGc/mvW112gwDExOQKvEu52oXLyiFZUuZpq5
CtbPddUCQeEI7uMBxa7LcCvntfLUO/M+JoZhxclTnTtlJ14GeulN1428fHPoYss1vFKZDmnaSH6u
Dp9MhtqdNpjyEpP93M2TJPXD2ItsRzwUv38KlrHRbMa88aqi9sSJw51G7FaiAmWY4wI9sLd92ZMB
I4cVhiQFw8IjZxTcaQQTvOtwSVaE0YZzD9IQG5qwfVTf5CVtLktgT/i2Wr8pM5l/YIeo7ullk+aB
BlRqjE0O3FFjTyVC7GbxS0/EbTujRDLMWDISpsx5Q4jdS/hi5YDvJuJxh1SUSOB07bhXQ1dPhG2s
MMQ/dg1kXwwbGBlnVksfRcnH5pGTHqpLfEL7NiGuwdh1Kd5vwHFAUbkXzTLwQuxnoKpt8fjpoLa4
kgWNMLW1oFAn7CDInQU82BGFMDVXz3AL6FV30ZhYDaLMEAFhXNmN3+GNaahAhvso9ccxgCYo4v9s
xmNKZNSMUTNQaBXwJhhpAKZVyKKUU1RFzDZ6nO6FaK7Cu9zXJiCydwOgbFZQrFINrm32oTp5gNCF
UO1t/9xKYynRe17PTcmwpSp5AR1U8chW1QsnljgYopt17LEM7TikJmXVCmDJogFzNVnEwqEgrr8i
IDps1IhPOg0sv6V6GUIv4+qmbiSpxukOWGotziUs4oeDvR92zdW8IqZ5+EdFUzHd0wVYHJY+phoS
AjhTIVSnjNXKpTEpiLOASh3YQTIEHfdLGaTCff0q6tZrxK+MJTDney8ygwDg9loca7IhjoUBlOji
YLuR7QoiCUDF+76b1ONj2kOh9m6AZYFSG6aeDGZtwnsxMRbtm2vyyago3d220D6id6lpSHeg0w2Y
C1tq+2h5iWokEaiZZ2cP1kwiqluJWqKW4qSLUEjFoIaAFBUh8FuXd2wdPeCsO+iLfOCErhlg2Pmm
vr7qtyV8p4UJOaQNVJYFGRlK1eoxnauTL02lFOI//4PyteyEq7UtNsSLTBZb2NZ//du/W6qlPywj
Bnh1cO7DcpLBCrg5P5dGs3ZvMYsPurzsMlyrBjAY5YwZtgZIkZShuYEtFfPSxZ2eUWioA4B25BkV
nSptAnMXu5gvEq6dghncPlOtWrVXaD6/2OCaKhxJE9h6bF+P7VCw5B61Te2meqUMMGCsSXborG/p
hPTKxC6a+ImaZDIXLfRADWUmFW3qmZpljg1t9EANnD47l2GztrZWaVH0q2eaUsiWgl/KVCYRhhkg
IpsAhEU9Kp/abwaEyxRqxc6EYkZbwd8cCgw5p0luJpfQ6KOlJCsDN/uY9lq6f8nj6KbU0ZnYqngJ
52DVac3kSXF2Vd1pE6RK9hoiXmYUKHFNpP5NRerYuKlTDKmo0zhVtthITLRshwqGNTYhdtkH/8R1
bzAu8sC2ugvQrZ7Ib1bBxKI6dLx4Rb6YWOQVam4mI4OHKiNDFTSoupiHDy8/m1YHfEqu0is9TFv5
nxM/nOc111N1YM0oSj4H/owK+7z4Bh5vNplW9ZiNYPNNGW+oauuMAVw02a45C8n/gAd4Ediy4LLp
fdA87UOXRd8PMpa+tGi/qtSjv/wA92P73k02CeE1hVmCVZYeuVAVXPnRgEa3rM+jyjwjCK2aybkj
3B/JaTWxRJ6KrlyhqHq90E1DaOxoPZOHRVV7WZ82gncqrTmnDdjWA//Bshkcrsrv5Gxdzc7kKpvI
YwWe0AzGrauCgE73Vrm1XXHwWvGj/XBK8vPa4WnXPE1HscdcG+SWhYBOU6OVGEy5nsZSJbPiQabu
8Ly2823aeo9wmDBJceyFL9qxVAC9vot1eRRN06FceE0Lr91UFi8RkvWRbOr+nk1dVebPtuvIg/kf
q1jUkM3LKKKE0slQVfmCfKDSmjUKIIs0cJdUAkQFsx/6P/l/ffJz/3dg4rUUL9Pr6iTlLWLOtRl7
WpP6P8Fpdji6t22MrYaToWEZeSqP0ow+UTFrTdFlKrUiSZZKNtQjKyW1pFXVmGQ947uXqjbP2teF
MlIh0ZSmoyWUd1jXDowpyXkqzatA1kJymv91VE4V8EnS4KO0aiUifBfZVIKUxroc1axupTxsZxFu
V/ltrbzLrMPVXIpbeNBZmXXXn21VMpcXwF+V4G0xmabgD33fXy77IGNFs0zA8qOHSKc8M9maofWi
YLcvE7aaeTLqu67LQUf5/REIPSsol7oKveaa5UdWNyJYrsJg7cGMyFMO4ak6Ig7rDYZ3ZpBb6vj0
FcmUOZzrPEhhSIMjz+DUrsYsdE24Jz/5j6gyeUP5YKMIsJku2hJvdBT0hkOZ2Xhjlaeq7pSWb/WB
QXmqDn98RhNlnVJzJUorp5zzZsu3nlju6YohqYXoexf6yihwmkoFphirh3P2IeqRPvotZZW+ce42
Dn70s6P+6Rvn306IddxInt5syE6s/ZYOIRV3Aw7qsS2+VFm6kePUG9q5QwOJNdWTANCGVcuV135Z
LklLTvTaHXG+5vFVpfwuWzDhOrBbXwLYWEDuBQ+w2vIFP8HocGrfBWxGs/qMQCOar8P4XBpvG1GU
NytRfbTR7OnaYnA9D1a5+JMXFcFBmibppov7IhV1ZR1m6/LkZO12Z9U2w+5J0A0U9xuGIS8ENj0n
Dckg3StCHS5aB+J+bXX7vCsj464SaEh4Drd0nnV1UnR3yi6PVB9l/GUs+1n07oxVqV9WxdIyUX5A
NuaQlixq4ehXJSO6r2FzdnJfm8J+8whdiizYl8HNRIlEf0yYs7vZGMsqcZ/zhvsdPVpxn6q4P9en
+JWHWVmP+y2xqQBIyckQlI2tc1FMLj0olaU9vaaqiNISKrOOYR4scdNfgj0l5xNnaKzCdgSvYIbR
vwDFyKK2oejOFhCOCwBWvSC13/iJV8ZnBuPOD1Prnwa0INQcqDtY5qXVdAf7PF/XJJ5hNrEQgIi6
RQYCHSUE6UlJQXpsicG7Cjspcu4u3P4nRlv9+r5gXvWao3XKlzxyeMN+oCcRe10ktGJ70oY63PY4
L6LiDDeb8ddbchHTuMRfxieErfDJv9CgfyBDp1ZOhcYXNBXn6XT0fYe/SBA3oUlAZbV5C0ytpwNI
rUC3S1fkt+gKGbpgNVFXEk0FocOLEwnS4PZqjIo6lkM0KxvecaY8cWatW6MX8uPJrJ5YjWeGtDcC
oVonqA84jQSMrsVtKQtHZ03KJIahGu6mCr+gBrfEWzJfM/pQ9SwwSxS5OtP8XnvM31DH2v7cHNG9
gsUf94fNhXje8zLfQ6lULESh338Vtpra1wApKRuLbWHHbJ65Yg9rDyU+cYmvW19DamUVG6Tsxkgm
XaccTOzymnWXCgbLxF7Z+NAEB1yMNyDlDu5a0Was0qiyQU+x4I5yTJVg9KtsCRUKcJpRD5NZxhYw
+vidwTW/pSJFzR8Cc28je1WdXWXRyDSMPr8ysi6ZoyvRTp/dq5C6jC709cQvB9S7dkDJGHrpiQ0j
jf3w4i+Mz/07LTYurarmbTB2NU8/mogWCcvkp/5fDqjkkr6VueP/QGBz/UvB0bWyksCRiV7F4lAO
La5Ri/GXWL6si+I0qcyitpKeOk2q07L2pv/aIHE4IGCkSt3m2rsyCkCJaYc+ZA/Vt+P3VZL6fif/
ddKQbV4Yf+SVK1rqtN1LKN2JRjXGjK6ftjKOxkAZ5ddU5etcr2/kLzo/VqjtRv9nFN34/qIlNjog
G50PrUT0f1ZSVyScya8+a+rQKMb/SVB9dcSCXX211FxO+SiqrEpWcN2M6zpJFSTQp4KyFOv2g6yc
pfZJ1pRnmwXp1+0GdbpAbNUTlcj16HbMBYyB3n+3923NbRxZmvvMCP+HMtw2ABp33iTw4tCI8tpr
2dZa7F6POBqyABQJWGAVGgXQIm1t+D/02775ZSJmFX7ym/0m/hP/kj3fOZlZmXUBQFutnugVHKbI
QlZeTp48tzyX8DxiU6fgLKyT1o577Zq6bu56nZrGya63UXNUv03Llp6reVV4nGMNDcIJBzDWNSsw
yrCDOqiqfpLEfHYl1DPXayX7MVqf486RBKGZELl9ZdFKXDkqBqUyzhWGuCTpJXS2JS1I0KwtEc0W
jVjdU8fFeCGkT4ylVzqYpG5TKgpq1nY52oz45ZyImrSSfmlJghzZzWihlErHNK1FFTvUwPpanvG3
Q4VQuOpUGXvQV26oKknbigVRC/WbLI4O94nciiZcJb8DE1WK9VpSi62iW7jKgda8lnSIBrtZ7tu7
pt1IioRj/lIEALjPKrmOfhVDfqp/WFDh2iADJdLfCj5uauLShXii5V2L8BYaKSvt+8V4IRmlYjpI
OBEa+UXqjfTlT65EkQMXZ8BlwCoQQXQfDrqkLBEC4lyVGK6l8b41t6Yzq2qaQGZsPn/I3sMvy3j8
bjo9wkq2oFnNOrjpzvWR5ZePj4diK7ac1asyuaHlxKq/tQMbbXPNPzpZ3j/hZ1H+xxNYfWcnJ380
B+Ti/I/02dpA/sft7Y3t9vYm8r/utKn52/yPb+BTkP9Rcns1dE4vZAJ9e/r+GT/p8//Vg3uHnz9o
XAxe4xiLz3+7jWTPOP872532Np63N3Y2t96e/zfxKcrKWmGX7fZGdW3tkfYVCGAVmcJthvWQm58v
IjYjQs1Np0pVZncTIZb4KRy2f/vhPw63at6Tr6uNtQfs7oCUnKST3PyITImsuZw6mRCby3InntbE
ymOSNrHL+doVK82SFdZHPNEF8oQ0vPX1xyq3bDeVW7axvr62Vvc+D8KbX7rU7tPwEvoS8sj+9sMv
BkhqeevrXkUiF0nh34DXnYfkrRjfClraZUMSXyp+CSuAzJ0WX/ceByTZnJFw0/ch0/oqpQkH/e16
vWh283NIs/hKtZnSgKy5wXo1pRVYi6LeDpPUhZLslMB+8wsL96kdqkiSW9qEeqfdbtGOVBveI8iK
wRk2mB2n1Ktqnj5pjgjGp7X9dX7zn2pXh+i5NwoQOGaJ46H36qW+LUPDV79iqnqpU3S5vo5EMl1a
USbvorJ9zLAtN/8JALx6qZ3P9gY3P/kHr34F6HEDcOV1PDyKBchVgQ8i1gaRzotEwuT6evYCj7ow
qWW7cOUjHTWC+2U6xytpSM1hdX0d3+UldKVvaIh5iHgHmOuCm59SmWBNUlmVgzaVczZJNYtUBOw9
B5U+L/8wDSQHiS9n9H5hpT4yeQWxb0IvE6CxE96rXw3YOwrspsWrX7E21zeGmji5aGntko325kfC
NwBPEtLe/GwhC0yZ+q50zWP7Ju2gmGElOy0SZSIgMG2QxZ5jTiHtX/gNeyaFMMT6BGlC9Ol01IOe
vr5ekMiWDq63LJktPJsifSboF5kKssfOGZocg+09tFJzWhBQxl9aJKIYQxoN50tUW86DoZ2LhHay
iqoSWDDMFD5KhK25uKmaTdnApvTGEXADGJ92YmKc57X5Y0QTThnvvYo5JskxgNE6wIs6bbKBWeXi
5kcJslIBm7SMK8kliIzTdjRpLVmbiv1ClmON1Ekr/TQJQuXU2mzSFMdawrAGSIhAzwJeyhlLgOKG
pVYE38SSilTCKh45N/oUHkkE8jGfLztsVMN4EzDGXjKAVRRXRZnJONZJQ/kiAiXr3iqCyiQvTkxu
wEnLhgt2mc0tVW3wfB7rlzCHvCtINwas4T0YE9W6SpnxtHmXRk6bCAPVf8O7N0ZTf6wvCBWLx/Ea
G8LGSyKaCqZj5zy++QlBuo21tffe8z4NqfXYn66ttXH9Nxn5U3EenE6QzOw0JV+eygVLjDv86ehi
NBVGn2p1YhKDd05adzpbJ7Rz16PJaRVWAaYKyQg00YubnweccXnAjr3TSwLuVGKI4xlxKuEvp/5g
EIXxycSfDU/REWJZsHycdt0De0vCbxZufDgkp81oMmuG9E49mE6ayHbc3jilQ9tpeF8FbHCkFUt8
G5NHwSVmQpwAOuCUlUqt9jGxR1ezIXLRr23QDkpsXE1yWhJgiM6R9o12kD7uTcZJ6nfIH/dISIVX
B6Cs98m3Gq2vN9Y2G96/zMFlqYNc4Q6skwgI5N4AeDCGyPTqpT3Yq1+rXsDij2wv+t0itOF0bxmp
yJJqHClJjdaADDnlLMZ68thBlu4g34Tz4JIvrhl7grBPRKJGNMeB7pXaRrVV3mQ+jnmJCUh4JMLJ
/wnxRELJfTW0oeHKjdbhrKd7yvPmYP1UHYiA0JM2w7vjVXJSVVe7a2vfe4ckVnr0T0CE9+dwIFKL
9/3a9/V6nf+nNn8m2vi993h+wTt1mkpUdWrwr6gKALrzHkKeiOx+dCqHU72e8c1PnF4IzR9Ilv/v
vU9UtkCsW6fDR1zafYspm5T/PAR9CSJEqw+uOTxQZf2X8anvTyS4nxaWV5MgPZvKKYp63PXq3sOt
u96j9qZ3v31alTXpogXfe6cPT2lXfwqJK/32w980f2J/O2TWTwbiJBNPvq55p1zc4FRWK+7LXtNI
IN97j5S/w5V5JjNSkhnNK0mgcloFU7FIqA5vA2ZyWMHs5keVeBHj3Qe/+d774uYXnYLRrfmgEIiT
vSZpqiqvXnI61jDEyfp+be3jUX9I75PceZpTcoXIJCstdArmoKL5cUaY+ilclUb9ZjztN7+h9+X7
xjfx6VpFU/VUs36ctKPfSXU6vRwF39LDIJw3nrMypZ74cRzMYn5mWOgWWCiQFpJYseMkiIx9C9Xz
rbvMWsIgq/pmHSK/8tMGdWAAiqSgJE4oG1dMMjkxF60IJR3G8wtqnWGfJLIPYuuunSMVVc69KmYJ
R3fwi1BtZEiqx2x0GVk6HA396qUcPpKdvY/ngdyZEeH7RrGeVy+FS5J+A0rMQqpXYW0GoA/YUR+i
uVzLjll8SES+bcDyTPdrKPr6us17B/p95vR6xc565apZLodrSujUGgikwpqgMbKGsS5kiUZMsD+W
Cgi6OcCnMe7ZZMTKbTLpHRI5RWuo8vRFXD+nfywQGG3KkkwSUVG2YVflUGYxnfZ9CsHx5hcm86Lw
7/IWWCSJ4MzODWd0fITeqFNX+azd8tobd7w5dFml/SqIslo5ADl49ZJpIrE3/TAmZqm1bHb41IeG
1YlMTRriWXSMWG4aE6Zc+H0ipBKkAd4Eq4E2PuByBBEVCjBXjjQmqgQRFq3D7OIRfTOAgqc2MJLT
RCjsX2KyuKpTJgECCp2kKVta1NywJkz3MhrTLCXjHpIIM1fqIRVKhZRMlfA5SR6c7OsdPtjKZQGT
pIOp4kgKZN/KQtE3W6UDlJaFIoxOIvbNj/GaV6wS1pQdgHd8fZ23jqao9pYJxKuXln8N2JeazBdQ
aMFJ8eqrl+rSGaeYZGbRKPl8K3QVPNFRHnpB0dT0rHIYNP7pjOBpxqL4xGsdY8X6b9vbG53tdqvD
9t+tt/X/3sinYP8hJ7y2MW6//5tbGztv9/9NfBbsP+TE1zLGyvu/tb2zIfUfNzY33u7/m/gs2X9L
T/j9Yyy+/+tsqvs/qf+4tY37/y3s/9v7v7//p7mefwHYFbuElDSD3VZXNFt2E6fcTJOLuEZ0kkIy
b735zlrOY5WqpV5/dlHvnXe99852zrbPOrvypE8yMZ6dnakHo/AZ/d0e0H899ehiPgvQaLu37W9v
qYfIGEzPBsGgP9hUz3r+lB4Fd4OdoLVrDRuhy05w198yw87RctC647da6hHUXXrWu0ujDOy3r9t4
+2xnsKnneN3BFM+2znrmyQZe3dra7vj6ySY92fE3ez09wPUW2tCQbT2L62160gp2+ne29ZMdbrPh
b/f1kzv0ZKu33WsH+snzBBYyzZ7ff3bOvnUoczCtKFiTKsYKmPWQoAsFjWT3ejy6JgC2tybPdzn9
cn0YjM6HM3rU2NQdm0et1vu7XkQayNk4+raL3CcRNXmRu+GwdnjfwRe7/u1oMBvS6+2tFoa58Kfn
I1KsWtIBaTYD8VDpbE6ee+1t+rHNDfM7HrapW2vunW2nU7Wub9Wcd7CzBR113I7ad+2ONmgKNMU2
z2TVLhuMyz3qF960Y/+q652NA3RAP+vfTv1J18PPXdIvR+dhnV1eu6QX4V5n1zvH9xiRobDrfUME
bHR2VefMLyENHdORDOq9YPZtEIR6rnXSG2fRRdfbLAYaT2w2zk6Mh7yDF3NntLg3SbRBnZotxA5y
bz0OmqPV0AMiGqNBgn1As6puUSftcTSnEXnBuSgM4lBdNJV4DoinkZzpRdVGN9rNO4tBdD6liVow
wt+7/LNOcKFns6AuRpoYKRgngT+rAInrZ6NZDWoufKnbO7SDNa99Nq1W9Z52lmwNLZHGXbT8WwNU
MNfsTHvToFUKbdoLDhsmByuRg9K9cdR/tps9g4u7INwNF2yTfRA3Fvd2bU9mFDLZUnNCkVxFbjb4
OCBjUp1RO0HqhOC42OriopqoMCWHANxZTAA4lfKqSLTNp/1s6iBK7lFMdpIpk5m02cZCxFg81e7Y
j2f1/nA0ZhR0O124UGK0U6zU8IfiM9zjCKkUmBn0CTsZjgaDhKoJLaHxUwRr2XRGOZjqMrDiHrjw
83LazTuVHCcHcxtbFu5kkHzJ0HlkTHh18Yvj4KqAqqvZpWefOWjLCOe2xQgXz2NUfDC1DMD4bfaj
k3P4NiwSNZV2DFNtntWnud5ePKG4j4sXmpHGsPpzJbIUvDRj9yRzBPq4q53EAS4v5bdkFYxHOfte
0PGwlicpzwY25wSUdyxwLD/WNmkbB2czmt6QaEadhQT4vsl+F81pRVrcycg/28XkbzZoTPPXOmyQ
DuBMmfe2sKMptnAWzQRKK8tfF7rxmX8xGhMWzkd1+jJimNQQwwxPvBh38upharWL9pE5dTBeifvs
bDrcdwNCbQ6yb6UJSKeIaRVPSe4vC6SH6Fk1xcoWrI0dq4rEkPl09Z64xlRBR8IKbk8hL5CB4jt9
BO+2bEJy53aMZzOf8RTsaprwXFDzcZCmUUskIJ797+VNuHAcjWNWp4yas7hpPL+gtmANvKsE6kk0
EkzKHiaHCC1k+Xwx81qEOL47XFVK2twUKUkphkZPKhCVeBo0uZFP/3I9xVG/C/o+H/tTPIiXzsyW
b4xKuAw6/GbvVnRu4MUXPrOphTDV5Cy+immp9fkI92dhXI9paQtPotyHuUcRp3czSCRIfaiDjd7m
lm8QexYt0VyESKvy5rP0gTejLNMsNABs5NnMcJ1NIOoCqtFcT+Vvtz3/alYud3PH2Rv58A5N7jSL
TFfKMsRmJceWEwMrjEFqATlUUyqgiBP/FqTV5JTPQjsLH2qcUh0HfjwMBukWC+RSBqLBTmPdyhKR
DBcrFBGAltMZyFlKYJkSJuz+Mf6tBhZs2Om6Hgy1tFNCzSO9Z2L5GsCv9sJ2FfAqR3+pFmGGcN9p
ZMtxMDF4nSXCMl7C+bqtoYi/pXla2qK3sYTz8FgTNtNYkNrOnjBWa10b4B8mpXrsnDPeuZNvWbu9
ZMCjwGtqmZliIztkzqIbra3Xsm6e0S2sHkvMd9xnWuXu3FLlFq5crHOzlWi5smfNZblMUyyXLkOc
UfAaQYfebqtgC4ebKhE7y+IC/2wrCJa9LXJ1LoPcDjrL3tbMI+f9No1/9/dy50GwOegvVAeYNK5o
DlliWEVfxXqTYz4W3Evh7c4SNM8gw+2pCE/x91hg8CLh8+1ww34xb9Al54MNxgcZxUBkNr0XzAYd
xzfbm21e4MwmjmYcgQYf1wCp1iVrcNZTDnyxFw2uWFm/hOKPa5+T0L+kbbH3O0TZqHcl4ph64em5
LyLRRhTS+6GPHCjf2UTkcrgIFrPL7F0TxrNNplBsOswtWymNexmrVr2nb502VnwtdcfkXlbxjJZT
W9VXMTNvr7iIZSx5c8kpTndjeG5GsLhlH+CSuXaj3MkzW7j9FhYy0c08irNip9poaE9niWFSvzlM
beISOU6v4uJ3L15sV/aQTFYtq5VCpOx13kr9uxYa1Zdr611tnsIs7EV2nGnhNN+iP60DZ+56bUVB
BfIEYTBgM4pEpgQx8ztFN0nxEjrIocycAnEsCcb9ECVyiExqGsmOFVN2SC7SHhTVcmzK1l6wfv4c
8+U1G7PwKheJ9q27c2nv2MBl7Xe7KtwXWtEdL+LEefIEi8ZZoZVA+VXr5oDjEAIRYl/j0diksJe6
4NceZ3Htz9TSU8P44moMH+tQ6gq5UWr09+iaYyAHCP6jRbPwtQCI+iYrXsAD6rCQ69OinynT3bIj
pFblIpCy+DtQXtpFwU2A3cK5FIDFielprmX/dmZiM0A3nA3lvq+CAoTLZuw0T9m25NphhTGXWrmW
9pFjfM9a3Te3M+RrM8XvF1/VpAbEplvdi8qaSBXUfb4B3z5cKogBp0tq3SOYGG74rFRAqR+NnaNE
VOR8Ooq9ypXPHlk1XbUPZquLER3Fsb/QJKGhrhQIcYDPUV76QS/YSQxPd/w7d+9srLKdTsfJxji9
Kw+qjFlL4NJuOYBBVJ6qXyKRNCSKxpAVeYQgBTl6NZjStkCxqfjX87EXxaRjRbcBSjD7aw5ISBne
ChI72nsbgy3/zkITZk63BQDRfa16GQPlAN0VdLPCm5ZekQZ/O0lgmQRQqbDLCpINhEmaYCkeMgEq
hsWI5zOnTUYchSRrjWaKSg2CfjT1IeFrupy5lshfkHTbHYKBacjm0iyn4XdeNJ+Jb2DH3J8ad0L1
XT06O4uDGZ9jHv4f7a/5uj8L/H+/eU3u36v6f++0WtvbO60d+H+3tztv/b/fxGfx/ifhpH9kjMX+
3zutTqet/b83N3ew/zud9tv8b2/kg4QGjUFwRrSuUk4hQ0P9i0oB85BtLx5XGxxNgyq8tVHT0EMF
s/6svEt8o1nkS67yO2nb0Gp+5EnqJhRFps6t5FP5AdGNgnxKXz34+KsHj+9/6V2gicr81IDxi2RM
714Pukt/dk9WKJUWaahK+dug13C/LVd35SViVUG6KZ5xA2liRt2HO0yrpd588hgJMcuHbWTDPezw
zw3+uck/t/Dzydflp6r9/S8fIrntIbHjshGJr9tVanbYcZ51+NmG82yDn206zzb52ZbzbKuq09we
bjtfbHPjHefZDj+74zy7g2dPvnaePa+WXwheiJgL9TTUSQIUahy2sY5Go8HxlnyLEtVMOS1E+z/5
uo0faFPjGGhTBa3yVad+2EbVM1g5pyjwaBCVx3pCY1SuqzqyAOBEVoNWjStqNf/9q8q/DT6s1iuN
9eqfmo3gedCn1sqjfXTmVS6gzOCNiT+Ng09R7Oq4/bRGqhypI6jAcnHcecpyAd6QPg+5zwXdqYSm
3jo0wlbL+zC3d6fPJ19TpwvnmO20Lf9Usp1733/vWUPkvNsRdH1h7Z1Ie0qUHavydARR/QWfcB2c
ziHOc95itUlodtiuikip71F1ciXpCxnMo9QuxqPwK3zJm6hnem2yazelUlyTU2zzgrDFDx4f4cSw
7kT4+IlKPc3SJP1tpb9A2TQO5ihbMeZ4KPcp9PyR3I1UUqHJQHZ9y67elvziL/j4m/kHldia+EkD
hGlCD739/X2PhHUmvANsiDwK56QBf0Sr8breYwJ1eE4dKOeFppbKgxCLl6RHSvxWBdZ1EjBXHhdz
fYiEQ7APsW1fyGbVmqr/5XxWQcA+EV9zYoBg70aN0cBaBRqkkae8R5tPWxvvlyBil5Aj4TyY7ZdO
emM/fFbyhkSW90tNIpPvjQb7qHuNXlFt8YOLiNS5facI0AdIP8HVdPZRAvaDPsrX3ikd4D0Mj/f2
mv5BWZDUrCFEPSUz0c99uBRyIunnSFb9EPmcAwXWMvGaB48V1pgOrmcOppX3+G42Wdl1ifb5ahzs
lyyFC7OqEJk+LkDMp9hflyxytU9ZT4AReT0Yi5bkTGh4URliQsBr0AJrTZWhHGSuO0LrsFd9No6i
aeXC4xIeXFl06PE0yy3+58J7H99UG/F4RNOtdwyOpbOOqaRdOptETtauCqeH6EqiAZ19T2coG4lp
gmPChtGVtTKTSnqCkpVEEVykm2Bx704aw4m9H+Us4g07B+k57zXp4d7E2jf4pJUOHshSooKVdPMS
kNU8k4AMkOOZeh8m+anL+ZnIvIrU6uZuOG/6huQ4UNm5JDOBKthQbXhHbLzAnB4d3vPmsS9XcIi/
o7/mSLVU8/z45qd0ThMusTO1E7A19poTYJY1x73B6NKCBjzoBPlSxbWOJw29LScX/nNmH9YTZIkD
dfL22FR3UJEn6EidqnTrpG5YuQG5piaYXyVk5x5A58qoGlwuzlBXzVTsPqZTwZhRk2K0JmVdUUu0
OeEkduYVk9auLKuU2gG8uoocS/1Mzs9vP/zN089V0QBeiVpBZuAQ7QbxCfAX78+bQy5/ELnp87Iz
1i+qBlyawM2wl33HQD8+mQ8KYO7FenzJ1EGLFmLrwvdp48KfVBJ5/5lDDl084psE8dErHez1GKOe
HbeeCjnrHewJReOn7acWkdtrUkdM6qqNb6JRWCmXFQ2U50zVhZlrTWI/JaeTJDRDJRFFM+iM3Zc8
So/8MCDOfYbqSWpdAbKV0fH+zjoSJBOE54G43plSyOWTKHyk/qrZjYlKPuO2JoUpt6Z/zyEwZJrq
S/cD7WSrOj+Kzs/HQc4LYppSrYgT6yYvarpKIXKxdy1FrGovZzYcxY2TeE4YghIr46sKnhDFmJ7P
kR421hKjaZxUJWdIpb+WnK6q+Phuei5c17lwMtg2lAtAHULqK931n4Jxwx8M7gONKuWMla5sT1Uh
3vLlNWbDIKwUTIinjPoFGBryQ6W8h0shl0fE817p4D52lGTD3374D5DRPc7IdeDMyfSmtr+S+yUq
PXCZlmD2KYyXl/7YnV66DwKvURntHl9UM+Af4N4QBX4K1tsfB/7UjMrA4+lkkGAVjEmGTQ6HPXJw
mcXEBLmCy4aIglL6bhU0S2aXgm8yEyULk/qL06NTQrLZX8vAbiZorwJrwsXoHGJMkiVJ8ieLKLzL
axpBZeGMqsi9xKoNGPKVGXcQwQEmNBl3Qy1lx5LHMG5492fTcfP+xaD5uX81j70IeZzhTYoZQanQ
Yjm352xhSqIX79aqgTbRgQWQhphE4O3TaJ8FVxCX6K8LIjzJX3SszmbJn735DBOBotFOyLoRqfTZ
ZZ3z+L0PnpKkzsqsUjsx2HxKS54dyZbS//dmxHqoX2I2EPHLrFyWnfPC4txFwXjUJ5IpU5+HwZlP
jNU5TVjCLJo8mkYT/5yvBioZHB5ov6BK6sRDfSB6OiL85u9j/Hvy7YhO97fpmj5E009YD6EX3HKk
OQ1Hg26Oyp5qyAn0ut7xsTAirwxFBtWkUpNkSHa5DBsga4+Xc/IV4m90dSKvQLJ8C2ZLNjBW+XMw
3BhVOKEcEnmqQ6MQjuZxNJqNg0KyoqUAzZI1iPIIhTC6BdhLK3kwNscX93mjGfJ64kw1RaTmw6wz
KENc5vxoU6XPItfr6HwudbEUW45cRCYuLCTIRVt6nf74grZ7120Pi84gg9cDf+bXrzMozXqiQ8SO
r1Hr5l30EE2CBM8twAhF+x2c02GE00m/8h0pgTPgd74pVIwYPhzCv5toom3T5hcvMjxzms80E2I+
1b+nGB5PW0IpVaEg4rPy4Cia5LLOCRKGTivTXN5pv40e+ffFLPFE8gxEDmynGeAyQkwb+iI5BrVy
GE+RpDsbk4SrchkkjxU4RJeqGPBwt8dPqylRepKBrxktmnAT5pH7JaVniJFA9BMm2mYAVlNkNsFA
aSBorAwKwex4wkaHSWKQqP+pqQrRsZwtAx6UHaimZHEZgAR7YRtq2b1Z6NH/dSn7hfgxWywuHZha
BaQB8IsHiVSf2jNBguIdwzHDLQRp7Fh+WdkNy0VwlNMhvarE9i6GvVjlqOGbQ0aTQ9nH1HdsXJxz
rbgx/xzyzz7/nNDPF6kXnqSlmyePG8QNHvj9oYUdTE+eCA1Z2H3Nm8ujkMdKTgM+hzk9Rxl4MUt+
chw1rp/KqPjttuPSKibzeFihd6sOT9frBjmVrmveM/o9apDgIzupiigSGg+BvhXrK1WPlCBvPTRV
A/FKnzF+Uk6RjutG+OGHu/TPHDUpo8Ycv4/ldy5WSH8fP3tKbbLAyEwNYKGehqar1PqOrFGOUqMc
pUdxdoghw5aOfUaE0Zjk9DQeKIQGOjTC1Bbzy1K4MnnLr3k968Xk9sOvenXrzx4LaBXf2/N6BMt6
m0DZru5mpzjpz4DoWOdHttWx3Wp567zkJr6sevBC1CdavzxETVhWsWzbKeZdckgOgzdrVSA9bG/Y
PrhfXGGmDDKXEFwldBZSO+osM6xSgBTbAOVxDBCpKWYURVBaGl9lQIZ9Rf+eJKUlrJ2NdB0EuQzB
a4eEKOH5bMhvQf5qcC7x2CgrkopUGVQCWiYXxbMteviwiaUGGcm+8ozsEjIN78+6KMlU0m1XrFTj
VTbNSrAb39vE3quXh8EFXPwHza+4nGgwkNTGdnpiCQjQ+fV/JL3KH2tBlCus8LIJR9kQmdYE9Ooz
RMkYB1hDZ+jsTQ6+EL82UwyBpqAx4ebnsLFISVfqhkP+l+DeAssozgM27H0SrcIKHQCxqhE80BxP
5srSpwvAZO10Rw3Z9KZn4wFhauLrl/dSX7Wwq6n4Ulwx23iiGsfWjdZ/QQOfsw3mLmBq7Me0ClU3
ClqKri2iD1JV3bPrXkibOEIxUrtcsNrgYedAfdXVcb0q//CV+TtQybPl4iAfBiKFEhjYnZ/+GQb+
gP6Z4tcDENe9Jv1Cf+iXSRhC/n+uklrwHccb48Ii99skGXFOg/dznmHfi4ZLUKzgSwu7Clqk59PE
4psaEIjVcbZWGFWOpBNmzn4iLlyHT1PHWO0jA3rAyIZbulDh0wxDD6yJymm8VqdxQYNxUQOF6NwJ
Mc+kZe+goDtumcMmr5lNXis2KeTh/YI+SHxZMOFroRyF3/YXr6UiLa4bk9RSsIXlIlHFQN46DoRe
Jd6II4Vn+eA9Wgb/o2L4mx4I+EuaJVS5oIHNawuaHC0E7VEhaBmu8vWRgauGKf3g80D/CrkwhM8h
WvcuUerDkLU84pVqkkeixsFVSdHivVHOBbUdMUgNm6OEGHgVXRmkqkn3Cv0g0Yt05BCNld+H04Xq
wGJTDu/IocKl10JdakAa+mOlI0uNh6atbkBaAbdQDfpuZ0jv16qpxiAzTELmw6rVbT6Fc1eM9ZXS
5C4HMggNMLvfS1G3RDy5NuIJDr8IogAEHx537y16ozgGMutbdMYRRMxXE7lltOrHVNToirSxrOsK
CGmZFp80IDgUr2RhlERa8AJ4ku/vLsT13Bf7xS8myK0w0fq5jFTmn/LPVQCAaAXPU0cd2PmITQQ1
5SG37x0/5domMf96a/WeHRRhONPeU6yi55gAHpF2LmoL2wGsPzEfODR0Sa2VWgwye/wtv9W86y7N
+cWuTFrbAuT9rEHA6rtxfdzHAGkzIqaERTdGpIA8//Ks0q+SmtqqSsBALCP03a6dTeBWf0/F2HjD
Jb6Kdg0S9liNjHti4mESSJEi5ZYF9xDa5VbbqpkuMFw892c0YuXRsf9U7QAWoJ71kmdYhbmd4Nay
f8bxj96yG/QyDYoWrd32WBFU92iok8aVovLilhLmEqP0hwpvckqISMKdano0xP5cmXifARtLSI1F
WKE7kCpQsjg4qJJsFUoTKv236h5BtSp19vx4pH51J+GcRtm07Il8lnsiYcp+dPyMugzFB3U4lH+D
QP5VdUdSg+DzZe+boD9rPAuu4sqEznLOmP3MmPiEGWuXPmgTPoV5Zq/hEGa0F14wjjlqmWeVe/jy
+pv9FX0EAffhNn2RpkGThtgU9gkiH3zA8IAPZKYVApX2TWtqCYjltJR56Ckk+yaTn1TNqqQhd4em
svW5rUI6LTSvvX2PAxuBF9LueKI37OkCimTpoMWHh3mxmoNlGVLMU5AseV4tUlJzTGtupx9l9Xuk
7xAhQzVd+cYi5RjJ8dhJvooSrvPGyVWGoU7s9mgsW8/CKPnO0kyUJ+SCuwmRHropy5y4+d3jHGsq
IDIcheewICwJsUxqmAHusjG59isbrQoMWTkmQ56YFkOsPBxI61A6+FeZ1yIKZqIZUc2VgWfNY9mm
rbxxdHRe9845u+fp7XPh+sIFMR+y1wXbh9q247WJBXV02AFWweO4sHu+GHb26p8ft55mACBn+flx
W6xsgV54Ta28WgwayNHLoJOWMvVzw6JNgHASXi9Fuvhqosm2oV3tN36VFFqDmwDqM7Nz+NSfRWE1
qWEqQf8MOGdISQNALSa+mwaAR1AHTkzScOWfe58RPRW3hStdAzc7bh7xvM/5iaRDFATDn4kynKUA
96W6MsMC+RmMd1CmRndT7GUSbcT5HcaS2oGmK6BpeBktpXzPnfXNzwhZTSpCcqViy0oNSKu+/uL3
b37CXXoCISJULMVIsU02csvqUMLNjnXhQBcYLkXg0cEWAxNrkfX85dm+PmvBazIR5ExxhR6RxanQ
ZlD8vooylzddLhBJkcKup1nx75mfirbO9F9Mza3Y9JS5fOnNWJ4p2mog4TmltHEaNUu1SVcJIvwn
E0HoTC4RdCMgVDuJjBAb1zDPsu9Yi6Vq5kpW4t8rRM9FaIbLSYE9ZTZVvt2QH+ExkQBq6rC6oxWz
DFgbR+yxm2UUWqjMjMZP88bLT/eg6lYmMmJJOXmIlwfMr4YXTVh9y1qoi9m4NtkEgPEqbF37+7t9
NeLJeDQjzlUnxqUCSdqGneGh9iPhl3liafbH2JfvC5GFLvY/YkXg+vg6rSLhI9FKrMMoDBjoYfN8
D/Unucl37vGzDZNeAQkdMJUVqQhv6B8JcoKCBRi7+xE1ovkstRk0bjQLnIcPHh8dcxd8t0aS0RgZ
JsV5T5h4VZvL1az59aZ+pG3wQtUSE3VWCik4QVmz/NgeYZ6yei81j61kFH+oVKQFRnG+ZrYt4vbI
HObph8/YhiVBfy0d6NeueSousGN75NzSmIyI3MOs60ZkG5oa16yjXqfdN/B5uMTSg9kf+7Lxdfmr
J3851h1/oWmnt8SuoxdTdO+G75RrIyzcoYcgR7jnGaftj9y/0QeceWAlpgFx2bSKoVt01z0dMiHu
lvqgKMO3eMHp2YC6wsPS9nzbU4EWKYu5p10otKcIfRk6ZywxljfTlvLEtm0bw2tFpvBakSGcDqCe
3CoAWXzTLOXdDTt3eDsdizw+jz8fsbxt/tT113NueqXGe9LSYuUYXkyZ5u+b/yMV1pumxPxKXF9O
wSrGbI2KcmsTWTcxiuTR0JG+jOkXuZnZQi2jjSOopmdmbY26dl6Jxh9kabYR8IQrJ5w2KmDbaoiL
ksNjNMdw7kJNTxZvL+gnSCzzuT2MRwvv06OGimY0DCTv4gafch6wkPSv4AJHbqCcixiWSpVcwpcw
5lJqCZez1pR16NNR1VgtTacAkmcOHNIsDZ8iVpnL2uinULVVr4/EkSkd4pA4RdmOzy/EBQb3S1Bl
tHUe4bgItFc6rwocxNZzyLpidd5Xo9mFlKRHCouJrtSOYAzt54WS7dy/jj/kFleifovHSJjY8hHK
gKLlDR2qns6svkJtePTETv5hfnH4uV0bnscpWYH7JZpbSQq8l0x9991srvbaonruQVhNZ8DlgVYs
6e6biu5catwdW5d4Ly7w3pCgx6O/nHz24F/hRJly7j+ZXYq4ZCgmJHZ9/o38oJ5ot0hbUD9uPXUj
zPkGKdODkSKs/hP3yn87bJ7XJHBXSRd3795V+YRVdAgdsv54Pgh0VI6OwTwxgZsvajq4k5hzNIsQ
r9OQZjU3VNNEX84u671ZqGMpL02QZHXFyMQZVzuRgLhLAq8EA5HcTSjwmCbinwcI/vh0FlxUZA+q
QkPaUHgJ8Wf9oVcJptOq041EUNqqxZ8qZZCDMtIOIBBGBTvyEso179131cu/K9Yx40i/LB4wmc00
uIgu3dn88aDAo8vFcakMI73i3fRu5O1B7OxBzXTzEXYC3LvFiRtSG9JcFzOkHGNfbvm6ckj5aOLi
db15i33K2aXlkYlHxAB8ZQZkaryj8jcWmhh37aywNZCdyPLJvWIzq9CcWAcHgsv4qfhAfZ/lakIM
/SzwVWqhB3amFEdIsrOgOGVIyun4BvH2XiTDWl+QFJOxT6VEWtdC5XLbimCBXP24Yq2xQzlisCW+
FnXmir9aoO1rwVqPZbWB0L2K6JwSsg/ar/5v0q8tPXPuiLQI7XZNOJ3z+PNRnm/ovDk0IElbMpcI
5oxEK3uZ9Pw4KBC5tXQOjxGkY83RLmHM4x6yEj0/NiI9EFUL1U4ulTzhnb1f2HWmzLY3W0aHGCwZ
faBDPtO1D5QimdPREHG5WKD8ghUaUbLMz5R8jF+h9pGsm56QiEN3usrjDjRKNhp+E0nRoZRrxK7+
XW6vKqYGEZJdIWtIdrLxJU+VWp7oAYDePdpwscFZQyspWTr/SNRh5YCg5Wr+s5ro2G7SjiKbq0ZD
FuPHsRLk/7gKhS9ogavoP7naiUs5VlGQNEFZQSnLGU7MefBWeFeRmWQfMga/VD6UxSu5rY71RzUs
nMXVgJvVHPW5UK/m2Mz1itKetaIgx0qGvY1ymlVsi0ZNt4ZiuIJemDfZHPqQogrL55HtFRmDlgIA
KvAw3Sx/uPJiM63O8KV6KTDW8mu2xPMv4wiEilUucHtORNafc3Z2yDkjlnNI9RMDHtSe2TQJ2jZC
je7AFmpoqZdBTUWHIxlTMJ24vCiJXcmxIPLriQXRjdfmL58uNyeq0HQ5p9ZzmYw814p+YZircgBa
HJ+8QFhbFJIa/FXCmlmTz8Q0C//Z5PoFvniTBzGJxbiIT5RXySZFvCiA4y4xbE5viRgwKKofak+9
FFtKKuNd0vYi8itwp5aNlhVhs2US8rUsSdPY6Vt2fj2EnqrH9rpWc4ZVkZq5FqG0jFLNBHOm+lJs
aVkMKSbLvnQ0ONc55R5ZCip0FUtsnKvGXNpvitVEJ4iDD7qJn6jB9J8ax58qf8altxjSNCdAdGko
vRsIKsfvMnUzKhU4Sk4I+8rxoVaXjzKxl2y6R7bHJIgUgZi57TKkMqgght5cGjxNx5eWtTdfOR1l
WqRi5KYTcDm4uK6YSNCxyjhnxX8m5uQVQvLFVlI6eEzy3lSlBmEFMx2Xn8eUM8Gxie1n79/4NQ6w
vc08nCJT6TloEKaNpHyjO7tcxQ1s5ajc/BjcWo7B9PfF5eKzUmzug7E3ZSss52TRhliPq3REhDnL
UwJWG/nS2JR1AKHLOHBfRJydUUR7+0sbQsYDMhaz5CSYErBsag8OPtYKRC2h/dWu5HgMdUJDSZ54
1XDE2YU+f38gLNgqzAlb6uDmJ/8PhAUTs2w3vI9tw3XXy7NYe1cpk3WK8uEFRcxJBwDxPuC/UhQS
Pe3T1kPEPFHWd+T3CCqpZ6D6Fen1I0lqG3HqBGom+Qj1Szo7IYH+tx/+RkcrO+LR81nuoGW/z5sM
eS0Q5Cw7w7KOKpIA7+3NLzI06MR86pdz7jTyXZhQZKuU9mLWJU/zvyDmaIL+GAtEZULon/YwyY0p
Sk/BlBQzfi/Yg0xEswJTJqb59t2HFXWn4Q6ib1VY5HJj324x0qLoKHW5ZgczrdbpZBSk4zRzA91V
+DKYqFkrMFBnpv1QEl9izVnOSA2tpJuDIHaYnvnWMkBY4+B7pPW6FMGjlfgq6fsXiZDHK+z5qd47
aogRRrfWV/p7eTM8akhZTg7wFBE1GSdA3oMpvV1L+hZZTzVwHADcEDKX9ilpbInLc/454rplBtPc
njRv0y7utuEpndBaFPWLmx9jvdGAsPR3orTQjtpR+rPa5SXmch89Cdep0JYqHf+nHCOOsGhXfa4V
WKfEqTrrR53Dk7k8AKRkvsvUrnbaPzxUeVFjy9TmRWBsQYiqb7yoKjx4GYJjqcIEuaCACVv2Ju8w
gNjD6dp0iYTPHn3q/fbDL97HGFwoAbOuokQJL9Jos0AuWjGpBT7HqYNkp+JNHaUKI4rKlsxOyCQ1
CAeI4hVwptBpwD7MiO5hCqJskv/bpipNL2lpqIuTGjc/Gy8vlDsxNqUWEuu6+Z/1CuTpR4mLUEVU
L/0VLos+Hj0PBnB3zM+1OxfKTq0XzWip8mVZchnFTb6QvBON66UzQSYYXVgwyyQI+S+W/SMtenXq
Gw3vYf6FukoIjfuJXSfM+MrE8Kg7f1feESq9iq67Wg6qvGRJoPu3GYANBDkdqYXcpisxZuRNKpp+
hsvpheGkfjqWtKcfUI9Wh5iwOC2iW0fM4ym732WEQMRwpJPXCJWX3cnEt63kC6/Mn24XHynlVd+Q
qq+ry4LFYpXOKME3HTpGLFQiK1JInLfKx3b4O7NkAC7Fj43noTIPKZqxYmQfiwxJryvKC0mkH7+b
Zc5Z+rQoZCzjz5zrX56w+ZSPeZT1Mdd8ne1wApBl4WRFVEVDSTikne5LW5grcgKJkv4lmJrkVvrG
P8Ed3p1UfKcKjF1qkBD8+kKlLbWxiZmDwpJMkOGCcK88hPtERVrzZYscxUVnCWBxmq0ubpZsg1sx
eqne/yiC2cGky3DnVnjidTO4MFQVYhQyiCyTAaYlSmcRRZ5Xi+xYqwtv+amwaOiMHYPYJZJEwU7t
J/55ObfsQ0ndGk1PmNalLxB0OxR82PfaqW8mwxwrO1dZwTIQ6egd4NWqFNalHvAMzjlFnpKEkX9O
h+Hp2a9GAQ0QaXIFWGyNlz2TKLZxSbK2jhFW1otswjq1dSvBo3D8lH4dTU26Fj5PiCP19rx2C8eq
lVjMnitJa2iHuK2WFkVdGPDmNGVziq4el6dAcRPLoE/r3OVR3kIP2bzGhXvEBle2maoM0ESktfVN
yrTYykgFkW83P/Xn1Or+/6h2vVcvta/Nq19JQHz1ssDThr6F3TKICQm5LkhOuCcD6tXLz0chtd7P
eryqUJyaLpUDSZVzICovL50FpML6rNybdRA9S9p2tWi8h/nOH6KRqrs4JbCQJkb7s0SvxH6twmt+
hwcy6t6pHOsn0+CcOOn0ChUeMgUFy8bjEy/qekXyZFd19w+uh/j/2yedPJzT1r+muq/6s2L91+3t
7dZmZ7P131rtje1O62391zfxyd9/IsXBLG48vxi/jjEW13+l77a2Zf83ttvbvP9b21s7b+u/vonP
3ke0yQiDiIl675fajVaJ7Z2oXr9fms/O6ndKHx2s7aFO7AET/r0ZaS5jfxZ4o8F+STDlBEIEyeQl
L/QvSBTJLQPrSduSLvt9gvdRNzXVx4FhPXvPJz7J3sHzyXS/1CgRL4tHM57nKIxHg8Bqys3Ho/AZ
inrtl1gkiodBMCtxHZD9EkqMN/txbEoRLqh8TM1M6WO80kyNE/eno8nM7vgb/9KXpyWPeljcvVNY
2e58r8kLVnBuakAT+JsC/9e///nnH4Evr+v0Lz3/7XaG/m91drbfnv838fkd538akMA3kNMvQl8K
iUqelPQsWaV3+mO4Fthn+2wUjAeKXuAnPEScujL6pmSvyU0LXp3556WD1AScN/aaMuGDNfnz3Xod
7nAbuqQt61EQ1D8NEXukKi2O6asB+zHYcjUucpOat3cRcF1Xo+DIjOjEMlzwRwYqKRlfpp9ac7qR
lKoBPUNNIu6Wfz2ZRtEs3VhgXbgrqdZxQIsJ+zSHu+30d9AHJ7Eelv9S487jYAqS9fejSG8/b/KT
pv8nJ6gzeHLSmFy9tjGWyX+t7U5K/tvcekv/38znPa++XveE3nc9pvd4snY2jS68hje6QO4bry+l
NcfEJt6e+H+qT/b8X/jh6CyIXyMNWHL+6dzv4PzvtFo7m5s7O5D/Nrc33p7/N/EpOP/vrCl7dhli
CgKuc1U6HYBdtqrcPtLR7iQkDUZTOBCzzTYqquUD12Ql8U2Mrlh5Uh8MLi7qh+1G43Cr5j35umoG
GwSiatHrNGCpVDJB59pv2uk/6TSR5hocqY7w/kTq8w68L+Hzql47cJfa8B6EcRD6UlcP4l8yiBeM
AzjCvbNWYXNrcMarpjbKM/NJHbn7nPSDfGlzZTvd6nnWbJ+tJsyrch8dB17T9nuocTDx3B9I0sF+
QY5ElDmxi/f8+eidNVOPiDM4qCjVmqfiqK60JfzxIvdlLtDcbrS7plwqJzsoadf4vcHIPyiZgvC4
UI8lviTH01os3AzoavedtelqySnSiSmylnmdqkLPtsNSv55jqZauZY/O2JTPpnpMeybTpgb2hlbY
7w6RTXMkqMJiuKgMh2rT7DpS7D3lZFflDc91rtITJLWklC5nnwBxjPLzhGAjZIRVUKc/COHhMz6K
aKvoJQVGMxSdG6dKukAzqYDuwjFplSo7jnwXSMGhC1qJuxx1rq895HGS9VxDteHxSbu1uqVhstll
bCk9EgecklcpDJqtpX35rKhZlYRUwu+vJHMIf0X0o2I83qu7VpjUlX3rBC/h/hxzDp3EH7hBDFRX
u8lBk4nog83H7srDrVCfy5yO0R8nHsEYOi5CL3mr64Sr5LvmW2sLtYO/ZHsFxspMaTk6T6i1YOqF
hgmuMbrkRo+9MECF3Uv6zdoNnTkWxZEDIXu0Zd8E9hI9k9qlwXPf7iaNc6DB1WcRI3BlJzG1Jtdl
FFKebFwqmadr6+EHzu0WTgPRHoBVizPPJiNW8qsypR2TvP72OWmMi3a1tiwlDZ2FpfloavTwczcj
DfZRpZrJSTNTNQzHvGElq5H13ema4mvAyCtf58XPPyUKS4qOStbr1XPqZgmNe2ctn8gpRGR+/8mD
+5/ceywrNGEjVtYg8eGtyZUmtS8pH7uSLOtu1/uqTfD6qmMnyKCZBsrHeFcxdslQLPmIlfxwuF0/
vAO5oc1pc538xCjffE6nj9vTQYcPt7wWqAoROKtjfJ8t3CHbn5NneW6cMW6VZ5mWqlnmsoSgpWzy
eOAYETXOL0KTP5+OYkVo1dwrgC1YhQrFnSFq6J21J2KRF8wAOoWI8HCJUS1Zptr90LczD8smoVQD
MR/CAL1G6SURRcxkustTrBbVakA/DJp31jRs9pNsrDUDAP96PvaiuD+fRg3vYXDFc2Dxc8zckbAa
/FumKLNSy2h3tV+BpI22mxDHAZCSqam4o7FJ6F9NQmgn83EMHOMy9AoFAlX6Q5V+V0N2OCSXa2Db
jdOl6xeWre8uKFu/y6XoP9RFtnNmsNHNlg8fjPpBTpVvknmYftPxHkncr+TyrjLPeixJxgOOBFP4
pvNZs488kcZSSUvwyt4MdaG90Wg1MJNGywj4/nxGZBjffnHv6BPzuO/PgvNItIz/5U+DYTSPA/Mt
8s+ShI4vH/73Rw/rG5a+AP4Z0zfH5W+DHhy9mM6ZX07UGk96yCdkfKa58jfeSpwhyun7Ubtee9m9
PNFfme4Qz4xz1RtjlkfTeWAWPJnQ9H2l0XzMFePfWXvx1hvi7eft5+3n7eft5+3n7efv8Pl/51Oq
GwBAAQA=
