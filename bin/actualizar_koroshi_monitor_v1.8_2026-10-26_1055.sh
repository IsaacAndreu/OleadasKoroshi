#!/usr/bin/env bash
# =============================================================================
# ACTUALIZAR el modulo KOROSHI Monitor (koroshi_monitor), ya instalado, a la version 1.8 que va dentro de este
# script (las OUT con faltas salen como Hechas, sin validar). Con comprobaciones antes de tocar nada.
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
echo "KOROSHI - actualizar Monitor v1.8 ($( [ "$INSTALAR" = "1" ] && echo 'MODO ACTUALIZAR' || echo 'MODO SOLO COMPROBAR: no se cambia nada'))"

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
H4sIAAAAAAAAA+19XXPcRpLgPDNi/kOZGm0DdDf6g19y88OnEem1xpKls+i5XXF4FNgNsmF2A20A
TYm0tTH/Yd/ubV424s7hp3m4iJk36Z/ML7n8qCoUCkB3U9ZoJ/bUM6a6gaqsrKysrMysrKzLOInT
UXg6iaMwi5P2r/4Onw58tjc3f9XZ6nS3N3v0b6fTpefy86vuZm9ra6uz2etu/arT7W1sbf9KbP49
kLE/szTzEyF+lc0G8P8P0eI/1OfSGv9BHGVJPB4HSfreeGHZ8d/egtHH593Nznrv4/h/iM+88Z/4
YeRNr39xGzjAWxsbNeO/sbm5ua7Hf2O7A+O/tb7Z+ZXovIf+Lfz8fz7+d0RrrSUG8TCMLvpilp23
7uGTX6/cEXvv84MAv3ryzZNnXz4Uj5nXxE0c+aloiaGfxamY+okvxj78G2X+GL44aTyOxTgImiKK
xcCfnIW+iPyh73oADQG2be5lSM53aRw1xSyd+UkINeNIpEEaxpHriQN4P4mH8DcNLmaRaEyT4Dz8
Lm70EaAAbBrPW71et9NqCMe/SGZTfwA1g1QMA0LYBSpFvjgPEVXoxJNvj6gFfNcELL/zsWQWBtEQ
fsPbJgMW+tk0GIbDGPAbAqqT+CqcwAvEm3oZDYKxD/i5TTGaBQPszuwsHGgswjQLgUDwXsEdh1Hg
j+Gd82gSRq1HE/+ViMXjb1uvXrncyjgIh37aFAHw+jAWzigYjHyxJ678MbxAnAazJI3hiT++iKl4
rMFPAWt4g4TnNwB0moSTAIcrgEkD/16L2TgLJ/mDthjFCVGC20DsPU3ho4eHXx/cf9bvdXpbLSB1
bx2IfdX1uk2iLZIUSasIlYZM3hRoPwaOwfcA+enhgSckKIXsIAkAzxT6r/qWQq8DIBt2EoYJOGoS
ppNYfAr/RjMk+/ezQAA5QAwMkToD7Cg2cS3SmUjCbJLTIhjzA2h+LILvZ+EU0EOUcioT5tT5a+Rm
+gY8dgXjRvQ4DxUhhIAu9/rEM6kYBElC6EIZhQKwgD+AnzOYEjEwLBWKEawkt0Ok8rEiUAm+pdiG
Av/0/jf3D+6fPn74tQvITEGk04QbxBfIibHwCTmCEUSSBZBGxMQSH8ZgGg9i10R7oy+ZKYUZ5CeD
0B/DECJkgJvB/EJCM2GvmzAaOIQEMWHoBHXCvc3RpNaBWDBNUtUY1YwvgqRPX9MsHlwCQJgrQUSL
FRIN+9eA1/QWEIHuBCl02Hd3FByYOFNg4wS4IbnCcf5UMLo74twfw4SClxLnaQhYwQAz/wFoaAz6
IZwxDaKa9dfCT7JwMBtL0jxGvgLy+mN8xnyFvDH1L8KI+BAJ1oKqLVOwtJ631rxRNhkjLc7CqH0F
A0VvvL+DFA4ngH6GIjcADgr0gwS+6h/T6+wGf54n8UTAYMZCvjgPg/EQBMkoy6bGaw9/Cw0JOp5m
WP/Bk8dP73/9r6cPD4C494T+3BGHX3xx+ODo4e8PxaMn//zw2dHDB8+a4pn3CLr89enTbw6/ePi7
J8+gUnfTqFQQx0jdFMRehLwbIPHS6Ti48M/GAcI4eHgf66+LwucOCgJiutUjksbp6nxARw+fPjkF
QfPw4AlAa5gip/HrFYNz90SvYzRTmFM28xN3ouRREmhPzWEHl4AZrAYw/2IQM3LOCn+QhVe+izT9
5vD00cOvD+8/Imb2oNg0HAdO0hCPnD8MP3VFw6VCj7+1C/xPB9YELCJLcD/sUn84+wrKgJT21n7T
oBZ/vTIANk7FV7zYytXbwTH3Hmh10e1jSZppwbk4zW6cNBif41NFlSSApSEi5vKQ90CkQ4PMLV4Q
XXkzmJpediNgfjUOZ0k8DdqP/WESDhkPDXsUX5+OY5hndU0o7vb0lyh+6VDDs2zgen6q20cIHmLr
ulTaKTYltYOUysECGl2ZzY3jLMDRg8fHDZI93jQcXIIq5Z352WDUOPHS2TB2XC8NQEiOnGOnEfmT
oNEUjb1xeElfnrfuNtwTEJLJMEj2GuEQOXAAb8agGGR7652Om7eIywgxzPFJ/vAcCIaoiDBilAwU
aQXnTpCAy4AWgIGXAJOHmdNoQUNd97hzAvIQfhQrhue6bhRnCJ7bt+DniHn+FNUFR9ZyS+Bgmjlc
1BX7eyKf6xUgz2AtvyyNLde2+CHx5QANM3N8oEHEe5hZ0CWoRsMcSuAnoBBLOO9AMQ4uMcGr7BR/
gPyeTEscS42W0GzcHfbvdnrDhrgL6wYC90bxDArzd5r5QZHXpDSo7MkdLSuAOYa4rogJrE5+FA9G
AcP8+/UlR1+sia0OcIrZiUIfUC02JgtoijAf0qZioyajv/c1TD1UbgAL+l7sKpVp01vhfHv0ANQ+
MgXIQgAJjfq71KbTHVPfkmpp21JGc2XNbIXlbMSgcZ0u6WEo2qgyEBraDVBbMGYddhWo/MPr4kyc
4jyhbltcB6yISvcUhBHMVRRy1nSjxWGv9Bi4uPHg/u/uiwZCRigVk0XWxbeenNpcxz3unhz3eyCJ
siScOq6N0wSmGWEF1M2iIDkNhyQhqhC8qcZOyQgfDIUpSz6AQj+d/LcBFeQhaNtZ+jLMRlpWVHTq
hhArADhGCaKrnBTr0JAcT71weIIDUwbYuGn0xU2z4gVKRnhXiW5VeaR3g3X3qtfxLCNoLGuD6Rj0
XadBWk8bdIM2Cv6GW1HzDmrX233R+Gp7ExbhB20wcx7d/9cnIKV7wvnt/W8eHD568vV9tyFg0b0i
NcHvk2kAOnIuHL6qwIlnDKDl6MVfrUvMBi4NWd1L7yKJZ1On47pIFX6oWK2JfNbqnlSRgrVookac
hKAK1xN1BqU6XgegkaGpf6Hurn+wtg4/jyubO2WruYFEyRywVRunYy4M3yYz/byqKhKHRVPj9Mz4
TpJhbk3W7amT8C2jWkOoTU9Qr6BfVtXXSnTqgQezStogMKLTWTDkcU2EgyRw2UQxTRj4ee1LQ0Zb
jrlPYccyaczmStYNE9bF38XW+2BMC19VwAUegQcCFhm2spMcLrRtaUTwJLAVoVM001EbkuoSzDfk
oTBqyBUDpjB6QJwGURPffbKHf9k/gvpSeRSW+RxbLU6TeDgbZKezeHL6fXaNj5i8wfDUv/JBnpyF
wOHXVey61KfxPRrvAIHZwWgSEDhxi0vHBAU8UtCShee0mKNsmxQ6cAJ6my0Cj2EWgTK3J7Co1Tur
rDSJJ/4rBwpX9/sEZytNPChS7It65ZYwoPlKSOC34us7tGCTzwpmpbKgm7mdD2sGMmtLcrWLOgOw
7jg27H9VRE+Ftixs9VD6rqpIAbWdZbuEaxxC2sd3nS6JSeimmvUn4hNYF3m6l9kECkqRdaLU42MD
IRxGAmg9g2WbBOXnOCWg0pIMKAezqrs4Fk3q3YlrSh4ai4pJ6+GLd5u57zo95ceepd8b0wdVzyyM
I/nqZRKicCUh8YvapIkPiuPp1B9c+heBPT/viC+lR3PAnlDWLfe0o3MQguaISzC6DUkdc9Abie4K
ITV2H1Qw4HZfPPid64lHvq479s2GaEBIDIcwIfvkikrii8QHnfZihm5KdLHBkKECKkePW5Ce0Yt4
PA1AskufeRqK8Sy4QLFuNgMDTQ53bs75bhZl0kORAnbPQnYE9rUXk5ug0p5hYw3TU6l8onvMwTXy
eDI+riInmpkk58ZkqjLmMLlqip+4Bv0RBdVQSeX+HuEZ7Euz2pOwalnYYF3VCzTEjxs4boqrTmzF
VCNyPP3+uEF4opr6vVUtrwTyjkxUC3E0KuBJQxotubrB1kv+ewJIS4XH6rdJx/olY7xozUDNn/wY
DpY1J5iUTPZTJZtQkWcFsN2wRCZpYezYAtjH6yfK+ucHZP1vAmejpsFFQH0sLSRKmQPJORw69MNq
BzoPrWinmNJZq4oiAmFULaFBR9TSOYwyBwpKfbfruhYcRLoCymTGiDz+dh4SEpHJrAKCwgW0VO7w
ZJYjUaINq8i81MMAaRl5Uup18TWuYhWN10/DOZiyYiyRrZ3zFSR4KfbqmiOW05PMuwB5Mge0oGlw
bK4DJ5WdQ0cQouzzIv9S7Kqfc/qHhffEy7kAzxTAffVzDsCzOQDZeCOrGbHjnwx5j30lVTYyftCx
E0azoBZPkDXHWtDo/hef1sC2qs6jBhWV0kvTpPBwXhu6YmUTI3jMvlrlJnvpinZbbHXKZZXAPR6R
ZJa/iJNGrADh7t+cOYOfO2A3hejCx2Wd1kleDQO5F4n7fvRNOLhnqTz1U7mv7e5gyXgc0PYqFP12
B9fhiPYLcZ0ut0gu3D2a2nE1GzNG0o1ruFAaz1sNNt7H0rXklIr8tvXVk29kqca3DTVvrJWhYqrS
4Mg1SMtI5118iy9Bl6cuuGUfI61VTT1YTWy26ImX25fKPYoburzjas6K1dVVVNPSlhoPY98zQK+/
r7Zoyx6/Pm60JhnZ0bRe+9YDQ8GkLVm5Fe3Ecnda8orcQCWeuQpudtQ+PkIhn+Z6B7252gFJOz1Z
4p/538WGYkXbiWo3kYx4dn3iLxVJ8dXThx50uYBXwhsEto40zCTxUWUojKk1KS+h8jDzsjhOhmHk
jx1XrInPtmDKOPDY9ALDT+nHxpnY3bS8mYwKLIYZDKAP09u5bLILxaUFg1nB0PDQGIXZaTgT/Ffh
BLUI4xnQPUhC6NAe6UfFTl5i59IY9ImhI9u3ZSbNH9BD5OvjS5vnAQ1YUiPoZMfrWX3SCJGZRT+a
IirrGRrJMCXJiJjSzOuC2L0EW0wX2N0T6xVSkZEA6jpRs4Cuqgi6scQQ/nEKIFuia2Fk0KywoTKO
v7NJjutQUeIj2vOEuALjFKV4y4LjAkdl/vg0hbkQDVPgqrZY3+oUGpeywHLcNkbo/AM9COTOCCzY
Hjr11Kw+hVGAt3IsrIp5IdwrQSCEK5nxm9QxBRWQoXe4GUY+ABsUzv/0lMpoZGSNnu0SbMzAmiCk
ATC2gholV5ExIm1441Y3hHUl3rpfdUD4bQ2g9HQ2BAiycKGza5LyAEKFBpW7/bq0sSNF73lxt4bd
ljIIBPgg90eW4kBoq4WcIeqx8j1q146LyyTHcQAs3kY3W+OwDnIFUUQSAlFuI8s/6VpY3sMIEkQv
pXifaiQx6mcJLNUqTkEd4svDB1/eN1vzZxHWg3+kNxWq+yokCSNXxBOMqkCAp9KF6mpfLTcNlYIo
DXDznwwkQ9DRe5ZB0t3Xyr1uTct/ZTQBdb7wx6YTAGZ7wY+1V+PHggK49UNxY8b+TzBmANLft7tX
9I8pCwWfVwPUITtlmKoyTFYb3v6e0WjLbJMoI710y3WhTKKjxFSkK9CpBkyhHoV+lKxEWRIZ1Nx5
JgvW3FaTozIuiVr0k45CwQuDLAKsKBmBflVZx41Hd2kfGvgLbeAYhxnAkPGN71ryvcPw3RImaJBa
qExmqGTIpVaVqWwdbWkMLhBv/i/uYJIRLttukCI+Szn8wGn87Y//0ZBPWl3tMYCfLtC9qysZUwFG
bpix0qzMW6hFhNaDrd21sgCBkcaYoWsAK+JiaHbgjvR5qXBH3wi9Uw5AZ+wbMY5y2wTUXejFYBRT
NBGowWWaqqVVWYXm9/0a01TiiCuBo8q2VNmKBRbNo7KqbS+vuCcKMG5Qdqh9UG2ENPVWJzyib/iI
tzfhCX7BB3pvEZ7J77YPON8IhDLyO1ad8ZMZ/dCbdzjwpgMI13xgHHwjdxBbtsNXbxrm0xUqAS80
KFiRXH0h7eKhGUlBI4p0uK1IwM13xFultX1C5XAkJGlMbKU/hHYdJTVOmWK0nyjHzAYptzcNEc47
BrhVi6z8Sc7K0HFzzTCkntqmyfdHjY2Hkm6Qw2j0TYhV6/9/o0gvUB6ywGlUh1w3miK7ngZ7DYy8
hh/+LBvtNdDqU7MVlQgqKpUIuYUvI0HW1i5fmloF2IwUl6YtSEfal3vDcJAVTEv5Atocj+OXwfAU
Q9n86Bos2nTvOI9AtJzJ19qfkEeTGQUoTLAcZRWifQEW3kXgcIihbV1gPWUj6zDnuylJV2y0lcem
4Z9hAOPjDP3rdC8EqyhMY2hl4qOJlMPlMHmFro5Iw1g0w8ksH6Pxhrh/ytUKYgctERWrgV7zYmiX
gmD16OaUiYVxamkLOwK/MZjkHDvgNO4O705s528ecMa1Vfw2sSs/QosU8ATJb4x6FsK4ZpVRNUNp
tlb5uQvhfs7aMcrHVy5Ve0XVlJe6T9Ewng59c+0VS2NwTBEkDRkkKu6mcgzPCz1vY9ebiMMesRT5
Vmig3YZ0kBd7caNJYasGuuEbbPjGSzhcB5E0bF+5jWA7XzC6sSDnU7mzwCOKQQjyKwpE1RSKRfW9
aRyEyIO1GgcqcoLlNVax7QwhjaOi8CRMUQxirFYOsuCRUtNDOaVkRBdTjojUKERIAAdDz44ZJOuq
XMoOd8RtyMqozKp4zEK8jxmYqZgYVJe7laE6y36cRi6SqAH4k8ulEg/eEU+Vx+qa3E5pvzZGTcam
sZaSh0cL53lrOJxMWi4dncGKHFNit4RbgAntT5KWUtwEbKroDpYoGK2PZyQC1xYQsKzSVD8nfa/o
lcHPhGOMJ0hpjEN+3nL+MPyh99qV/7RyapddKZMK70iWXNd4km+GJXmA4uoahrtJetNE7qj0XLf4
oLzPYyBxg3v/AKimVd3yzVAHe2GTe6rtCp+MTb48ENmj1Si8CZxSHLMDDXBf4AuswNmIvsEC4hai
muvRzIOgFaLZTRid80JciyKPLKP6ae0SVtXF4NUgmGbi9/54FhwmSZzUDdxCLqryEJ/eaMpx5Gll
zCnBbjJoC8UDa5GnhkD+nKOgJpDeFaIO6nQF4sNC6855lffcm8YgxkELnPPyrOoleuKOSX1lWadt
5T6/J5/GZl+GZaW53yMV+vhLn9wPHIBAnopcRtx2J+lAqTVDm4QeWoHOZXC9N/YnZ0MQR33EnEwD
qyzJ7wPa4zmoeKNWmRPpo6VYgmFuLeSaQFGdMwCw5CQIUl9S+wbELk2RzibO8Svcwdb6gd4hCrNg
AiO9CPYxGhJAQ6MVWvSoBdPluQCKseNVhqJeloCQDQewisGDLesjHhtB0v3KY3XFwOYShIIyvISW
pZf4JXSt7KYg8Yw1noQAiKg5MhDQkUIQv0kpiF9LYnBZYcciZ3nhdhsNozh8C3SBpl1abc+hdQWW
zTBQlXB6XcTYYrlSTcxkuZw/xo10Lz2lsyfciKkJwR/jAFTJFP4RC/1TA8M0zdAXeLiPVYGebsW7
XfiDgtiGxoB0rGwJTOFNBZBCMGXVWpHNWSvYDKVlorhI2AuEcgXtMUhjtudlpIdIF1FT2bB0UmlV
0dSaa4ny0a+0uAkWnRrS3nBaqTVBHj8znOUqbrK0WLjKw60dzsbSsNxSuGAZvCOeofqa4jG7s8AM
J6NIOvO0aZ9OgEZK/6z3vl35UKzVtRuiejvaN4/bXtAQuun+TTiyaksBxA20SLSFE5F65okH0HaX
8Yk0vl6xDV6VpZ8HPdE93iA7JsdQVYCDeiUdd7wJox+umeAAF+MXIOV1lo0+MlqxIiLgzWxEL3SZ
fDNomHu2cVOXtoRUMd4RKgHDo7sEzj4Jggs1HWOkt9ZOQ067XKNhl7min/aC8uSo2hTFQ8PS/cmm
cEtVXOz8rOoBOs7xR1PUlDT6Q43vG4eVKzU2CoPJ69Uou2pOf7onSizMG1XqjDaGxwXJ0uenHYpV
mJGnRO/6urwpJ6c4LA6lWSMbo3MkQ45hoS0t3vEqbVCpLS21hebUHcyOXWivsK3l2W3fJxGGh/83
XDyGG8qTr6tyQ3G1cv5V8pBjDhgdUckkL1Xq7hpK9aaQLGN6Sk9Ku0NGQfbYKq4aqn25oeGLrgws
L/RGHaWvxvedmqg1QGqND7WIqFQLxYWEdl3zIygVK4pxojo/IUKCXZ4wsZuTNooMgeFom+t+cU2S
m8d40InDZuYTMjeWypQsLJ7lKYifajOo0gQirR65hNvD0TEbMAr60UVMfjnmWXSlGSMuuk25NdgX
vabiyb5YbxZMvw3DL1ppeTnUzrGiBvBEgTDGlhhylF4OWihV1ZP8xFqfD6pVRhiUP9rqK2y95weG
9HGmPenRyrfdHc1SpY1wLVzyw/EqV4xSJABrQ0UzVSMy9+R00TvG9owx7MoCJ0nPuCOpZgxXwZrh
GIpTNpOWsi8NTZDOpRJbSKOy4EdVqooZFm685mf0diQZCretZL4RhFV50A60bbkEQQn5jTsHk/uU
d7jyVaUagD4Th/01tBbTRDd4lY6JUl/scHoKidszR01t+dcpx/SSFQAMdZR6HXxlr7MFHz2ouA3N
DeXa3xLxSBJxBsFRQxXyhIdQa1l2nA7xBefDSWEi4YxQzM9ab6wy1FRqFBV0KTS4iFg1KoiCUWAX
yxPBJK40iTEMMN0zcGsXsHJtAVny+fwifw9V5vaorn24eylfUNY0Jq4NXE1Zqnx8PGJfsRFY7DJy
IyPgUL01D6GZ7pr/7FRflZ95+d9O0W+anZ7+0hxw8/O/wUfmf9ta3+pubWD+t+0uFP+Y/+0DfGry
v3FuH0/l9MFMgP+Y/Pvx88s+9vz/5vD+weNDbzJ8j23Mn//d7saWnf9zfXtj8+P8/xCfuqyMDgWo
dtfdlZWnKiFjgH6FJBjwiYjB2z9PYnLEoaFop0qUjmt9HibVe9IH3b/98T8ONpvi+b+43sphSidj
wxQ0uOnbP2GmNNL9XxQyobUX5U570WQ/iU7aQgG2K9dkdnJWSB9PT0wwK4In1taeydySfSu3pLe2
trLSEo+D6O1f+lDuYXSFFgfmkfzbH/+iiSS7t7YmHD6nBSbzOsYgCUzeiO0bRzR2yBVD23JP0I5m
3KHzLfEsAN3gHNSDgY9aoS8TONARpx1xFmdv/xwBFt/IMgk0SLYP+n8S6IHRKYB2kKcu42SHQPa3
fyH12Bohh5NcwiC0et1uB0bE9cRT1LaCcxxgim+WVSWePtheePQY+vb97O3/lqM6QshnYYDHZAyF
NhJvflL7TVjwzV8RVdXVBEGurWHGxz70qJR3TXoPMhyWt/8bCfDmJxWKszt8+7O//+avSHr0oV+L
nsBHKRPZZfrg+ZxhrPKigDq2tlbeAgMQOrVkHwObwMqLMRjNzvEINkZ75K6t4buqhI7wBpqYRRjd
jQ6v4O3PViZInVRS5qC0ck7mqSbx4DXFEqFRXJV/FBriiUTbG2q8sKc+ZvIJUl8fNMuJRiFJb/6q
yd6TZNcl3vwV+1aMLoEihVyU0HfORvn2T8BvSDxOSPn2zwazoDNQ7TauCPIQwgiyI5OzU2KiPDz+
ZLs0ccwRpwjGL/oOiQY/ZpHwgdLA6EkSnqGlu7ZWk8gSJq5YlMwyQOKrOQFfGBXMHjkjatKJU/HI
SM1nUEC6T6GTeGYrgtZwfrFxSKf+VXgOy04y8uRxfaKZ5Ec+T6i3Plw9KOs4KGfjGHkDOd4OAyKe
p775Yzw7lRDfC0dPk3waoNs3wIoqbaqmmTN5+yc+UiKPp0E3rjmXGGacNc/ONfO+yZMumOVUMXVe
Sj3Nj9xRal1yCnKYIXCYhyKEqWcQzwpnYqIUD+E5zG/si8RUovL0ZeVZO4zpAZKPaX6Zh+QUjTeQ
xjiWRGB5ZsWRjiY62aGoPIlRkvVvdV5EJy/NnVbIk4YXFJfLciYd1yN8nqlKiEPVJl7xxIsnDscg
ta4tR5hykELLtpMtkPA9cX+MRf2x2mKTSzxOr7EWbNQlkKm46Jg5T9/+jEcSvZWVO3fEwwhKj/1k
ZaWLG2jT0E/4rGwyDQDMC0u/fMFbFCnugifhJEx4obdKnerEwL3Tzr3e5imM3E04feGiXU1SIW8B
EJ28/fOQMq6ixEYvIhA34ROTaQYrFa8vL/zhMI7S06mfjV4gIIzcx+7jbFcQpgl0AcMkMRAOJ8mL
djzN2hHUaQXJtI3ZTrvrL2DS9jzxTUAuO+gxn+Yh8ci8RIsQJYANKGWdNKt9ROzpdTbCXNQr6zCC
fBKoyTntgDAg58D6xnKofdyfjvPUz6h/3AclFeMikMpqnHyj0Nqat7Lhid/OcJUFAJXKHS6dIEBQ
7w2QD8aoMr35yWzszV9dEZD6w8OLcDeBbc6SMClrRYZWU9CSZGse6pAJZTFVyOMIknaH+k00C65o
65e4J4gGICSaIHMK1L2WwyiHSkxn45S6mJOEWgKe/O+onvDBWV82rWX4MCirqy92ZezK/toLOSEC
YE8YDHFPOBWpat3+ysqP4gDUSgH/BCB4/xwNWWsRP6782Gq16D8o8y3Ixh/Fs9mERuqFlZbnhea/
uizgCE48Qn0iNuGog+svVH/Gb3+mZCpY/JCzfP8ovpRpvrHfKh02nsJ5YCzKOuU3NQEvUQhB74Mb
Ogwls35z+wD7Sz7KDB2rykluY+O86G13Op+Jlni0+Zl42t0QD7ovXO6TSlr+o3jx6AWM6s8RrEp/
++O/q/WJItYws3beEB2pf/4vTfGCkpu/4N5OpiEgK9paA/lRPJURA9f6GWMkNTPAK08X8cLFRcUQ
oeowD3Im6DIoQv4kOGM6tvcA15sfxddv/zJhg8PK+S4ZiJI95kl5nDc/UTrGKMKZ9ePKyhfhYAT1
Qe98UXHlAohJMlpgFsxQilafukDUX2CwTzhop8mg/R3U5/fed+mLFUdJdavYIM3LwXcwnV5chcFL
eBhEM+8VGVPyiZ+mQZbSM72EbuISikyLmlh96CEKGXMf58w3dgOb+QLpqr1pVPllpDNKByIgawpS
40Rj45pEJqUhgh5hSvfxbAKlS8snqOzD1NitpnNZMsOYi1iCtkDrRSQHMgLTIwuvYsOGg6bf/MST
D3Rn8cUs4F0nEHzfyaXnzU+8SoJ9g5KYlFThkDWDpAeZAPoIqua8sTkm9SFX+baQlucKrpboa2vm
2jtU9WmlVz0u9Jc3a3l7tSmVTmWBoFbYZDbGHElkCxmqEQnsLzgDuiqO5FMcdzkNybjNkd4GlZOt
BpfQZ3X9Av4xSKCtKUMzyVVFHoYdmUOV1HQY9wQVx7d/ITHPBv8ODYEhkoDOFB5wDtOH5Y2cdc5X
3Y7ort8TM7RlpfUrKUpm5RDFwZufSCbC8qYeprBYKiubQibVpCFzonQnBaxZMI1IbxoDp0z8AQhS
zkyPaxN6DZTzAbcXskQT5rqgjbEpAYJF2TA7+AjeDNHAkwMY82wCFvavEFnc7JIuASAKzKSEPC0S
N+wTonsVjwFLzi+GSURpVTrDxA8OGJky4WuePDQf13s0seWmPyIJExOpy9OmSvd15qq+5Sz9KGlJ
KcLWQcV++6d0RdSbhE3pB6ARX1ujoQMU5diSgHjzkxGhgsuXROZrNGhxJcWqb36S27Y4i0FnZouS
5rdkV+YTdU5CdShONGR5Ytv7L+cEtxcWuU681zaWvv9rvbfV7fTI/4v3/3y8/+nv/6kZf9QT3lsb
tx//jc31j/e/fZDPnPFHPfG9tLH0+G9uba+v4/hvrm+sfxz/D/FZMP6GnfDubczf/+t1tje25f2P
vQ34D/f/Nze3Pu7/fYhPe616A7DPfgm+0gj9tupGo0U7cTJQM9+I8+JTi8nEWvvXKxWPZWKKVuty
0jq76Is759vnW+e9HX4yAJ0Yn52fywdhdAm/u0P435l8NJllARbaOtvytzblQ8yPCs+GwXAw3JDP
zvwEHgWfBdtBZ8doNkaQveAzf1M3O8OSw849v9ORj9DchWdnn0ErQ7P2TRdrn28PNxSONz1E8Xzz
/Ew/WceqwN89Xz3ZgCfb/sbZmWrgZhPLQJNdhcXNq7xX3OCZP7i8oDgzTM+eOJJqYFSRKWU8BDqh
qQVaeCsNb4AU3c3pqx1KG9saBeHFKINH3oYCrB91Ond3RAy2xPk4ftnHnA4xFHldOXTotxA/YFxy
62U4zEZQvbvZwWYmfnIRgonUYQBgoww51qS3MX0lulvwZ4sKVgMedQGsgXtvqwBU9uulxHkbx6gG
UK8IqPuZCWgdUAAUu4TJsiA94sozgIuRpWP/ui/OxwECgL+tl4k/7Qv8uwOWYngRtSj8sw8WDu7Q
7IgLfI8tEhV2xHcgisLz6xZltIig6RQmV9A6C7KXQRApXFtgAWbxpC826olGiGXjMmLU5D2sWInR
fGhpgDlvAKgeQhxBgnZGB8igN/AApn84zLkP2cxVJVpgB4YzaJE6XMnCOM3deaikM6S4zeQ0812T
3WA0780n0UUCiBo0wt879LcFdIFnWdBid0uKqeOmgZ85yMSt8zBrosGKccXdbRjBpuieJ66rxrS3
YGigi9DuvO7fmqDMuXpkuhuarSy26c6ZbIgc+nsKLH02Blt+pzwH54MA3o3mDJM5EdfnQ7sxkQkj
ElsSJ7zuUoqbdZoOmAmmRaydM3UucIrcWuRFiSgvLwUBcG++AKAUsMsy0RbN9vOkwCiVUzEfSZJM
Gmk9jLWMMR/V/thPs9ZgFI6JBYtA53YUlswEe6rXh/o5fEanhSwyE+nz5WQUDoe5VGNZAu1bAmsR
OmEFpxYXsHoIdIXrYtlNI5VPpwLnepsG75SYfEHTVWKM1+r6iuPgukaqS+xs7EsTbZHg3DIWwvl4
hPUTU+kAxN96PHoVk2/dEFEJlyOaKkerms2t7nyE0gFuoQBGisNar6TKUlMpo0AjPQUGuOs6TQPc
huRveS+IjyrGvQbwqFml82ZDc+VEKm8b5Fg8rU3RNg7OM0BvBDKjRUoCRrHxeNfhtKQs7pX0n616
8ZcNvaS6ryMPtPkCyjS2tYASHMIszphKS+tfE1X43J+EY+DCWdiClzHRpInneTGmLsXddfnQ6u28
caSVOhgvtfpsbxRW33VUaiuYfdMWIL26RaseJd6JrNEe4kvXWsrm9I1CpOrUkFmyPCS6G6cGEC8F
t5eQE8zG8IOagp91TEFy73YLz0b1wlMzqrbgmUDxcWDLqAUaEGH/rmsTbh2G45TMKW3mzC+aziZQ
FpcGGlUg9TQOmZPKk6kghOYu+bTF8l6UONoFXFZL2thgLUkahtpOqlGVCA1ALvTh32g2CZJw0Ef5
Phv7CT5IF2Jm6jfaJFxEHap5dis5NxTpxKdlai5NlThLr1PoamsW4k5YlLZS6Nrcmcg7W8WpiLN3
I8g1SDWpg/WzjU1fM3YWL7BcWEjLi4oze8LrVhZZFooAJvNslFadDWTUOVKjvWblnTZj+JpGDmq9
W3kW+hjnme9O1jmhpI+HHEQFr0yKXKFdS3PEoUSpRiJO/VuIVp0Lu0ztMn2gsGU6Dv10FAztEnP0
UiKi5k7tpyoLkdIqVqsiIFsmGYozS2FJgBN2ftn6LRtmbtjuF2MRmnZ4QVOA3TM1ogYwQnZibvoL
5+j3bh1n8OqbxKYehy4G0VugLGMlnF+3dRTRW8DTsBbF+oKVh9qakpvGoNRWeYaRWVv0Af5iUara
rpjjvXvVnrXbawbUCsY/LXJTrJebrOi019l8L/0mjG7h9VjgviOYtsndu6XJzatyvc1NXqLFxp6B
y2Kdpl4vXcQ4YfAeSYfQbmtg8wqXSBW7vMQF/vlmECyqzXp15QK5FfQW1VaLR0X9LrT/2buuzsNg
YziYaw6QaFzSHbLAsYqw6u2mgvuYec/i2+0FbF5ihttLEULxXTwwWBH4+Xa8YVasanTB/CCH8X7J
MGCdTY0FLYOFEDYzLm1WE5bGIWN0lgyjVQNMIR1E1TFvuC6excNrMtav0PDHbZ/TyL+CYTHHO8Lr
bj7hs8MAhdArVsSkE3EE9SMf84H8YAqRq9E8WmRX5b0mbM90maJh06PVsmNZ3IuWagnd3nVaX7Ka
tcdU3KwijBZLWwmrfjHvLtmJRUvyxoJZbIPRa25JsbglDFwlK/1GlcjTsnD7IaxdRDeqJM6SQJXT
0ERngWNS1RxZg7hAj1O9mLxz59l3ZTZJYtXwWklGKm/nLQW/6KGRsIq+3uXw5MXC7GSvgBbO5lvA
UzZwaa/XNBTkkZwgCobkRuEzJkFK652Um2B4sRykQ8mUDnDMybb9CK/2ADGpZCSFSCQUWgxScs4G
ecGlbAwFmeevEF3qsvYKI9oLthHNPffClr3hAa8PW50T//Pdewr/Wjr+C8//b2xj/o/N7lbvY/zX
h/jMH//8OMkvaWN+/Nfm5vq2Pf7bvV73Y/zXh/jggUZvGJyDfu40LGbw5L+Ya3cWkcYm6O6VMAlc
jNbCG14EXlQxyBo7IF3bdbFkMr+D0iiXiyPLUzfgFXAA3Eg+UX0gyqvJp/DN4RffHD578ERMsIjM
/OChygwauLh/Bl0AhfQ+95DvnYGmnMbL4Mwrvm24O1xpECeBXRSfUQEuolvdw020TkfWfP4MU0o1
DrqYT+6gR3/X6e8G/d3Ev8//pXEiyz948gjTwx10+6KhDYabrgvFDnqFZz16tl54tk7PNgrPNujZ
ZuHZJj57/i+FZ6/cxmuJxOGzI0SCLGMo86XMh0e2Lvw2ThTiXQ4UH9cwju3gQzZs4flTNlId67QH
IqDcnbI2Jz18TRTVHBg4KTCfyqx16uFYT+Gh2NvbE2CMES8PxY8/Cn4UzUDx/Vw0GqIvngGvRhcA
gM0tDTPCTOYa5mMfNzAphdsrTBP3CDOpBbJuA3j08FnDAnCTOTcGhMYueYIGoBmke6tIy1XozPU4
2Fs1rEa868yB4cU7XwDdIuXxarTG6j6WCRA2/NptI9T9RrHp0cQZYdM4THjThoG9M0K4HZdy+wLG
Zv9AQ4gTZyIoTS7dzzYShFCjQ/9MxF1843rpOBwETqsnHe/t0vUkCy/WpfSu626fjyKp/BwqhwFe
5BvJdAmj+NromU7XNlX3BqsQ0fBcOJ9MsXOfTL3R1KQ8U8fIvdbYHfX2bZx32/Bwd2qMEO51re4f
clfi+iuCyykKmkKnKEDK8SW7n+Y54BrVuQqEc4t7gV1PHMVISsTp6cF9MUt9Nu3pluBZOsPD2E3h
p29/tk89UhrrxEzR4O22p8hZBo67w/DKoAbuzDHzWQnsj6eeefUqcor5BPNI4GQTu2Rw7jv8BAHJ
+WOXznPzNzyUfE3mfBeYnSDgtG00zCtfyzks3NINZ8cwK4gzmvLqVpWuoq5kfr2rrqITXzS4l5yf
k3rn8LRUz3j+/O2P/y7Uc5mYk3oie1BqOMJydFMs15+1R5Ri1EqwUcZYVZQFKP1nMQdHuY6mPl4L
W0Nzkar2+SwfdJrTHBXpe+JN/KmTawSXBcFX5COyUXjvb3V/94w46pKvewRxdra/yxKNnnZPDCG3
2wZAJOpc77s4jBy+LLKhnlMgMq9NStfYs1ZyL3iVYbZeKTNgjj3gk9ZP/SiAhegcM5TLfgWYzwCm
t3E3YgOWuOgi4C09fTdW4zSOnspfTbMwSMlLKquTHFFp+PcC179SUeXM21eb9xL4UXxxMQ5UhddN
dc0HpmLsG3qYa+KajcLUO01nMPyYo3h87eATEAfJxQyzQ6XujlU4v6KNyGC/5pRO8ia2HRsXusWr
FhkcE8y3iRd5ACwb9G+CMV7//QB5xGmUTNuGiarkqsXd87IRXsFYjRChjAlAsWnULZ3GLtrjxQUg
nZ2t7j/A4QI95m9//A+Ukbt0IH+/gJOGJsfWqXyJqVIpz3GQPcQwhSt/XETPhgHk1RqjCfG1WyL/
EJ0NmCG7pr+DceAnulUiHqFTYoJlOCZvNud8s+XgqsyJOXMFVx7wykWQ8d0Ry7BZjp1F3wImPE3m
IAKKyuFY4FyTiUOyMMO8IZglq80LMuW7VxmacLGl89eJzN6CuWTCixlnrpaTOi5yOcxh7iPowSAx
syPuKlSHH1/HQ7O/WB5vvYE6HhS6n4FAPqMrNcF08Vs3BR5D/Yb0yQKV+G7ATxBCPMV9vNclwjDJ
3mFqFmZaMh04P9CFnyCTam/8RCrhNvUPU8UV5uC/fl2alEn1rMy5JVHfrRlFaHOAp0zlCxOZHxzF
08q5OcWEJImTVE5OszZCpO/z59wpn36IC7RNSsQlhki8/CZLUFELnF23TmZjWB/lCYv8sSQHa2KO
Jg+BPT5xrYV4WqKvbi2eUhGahHurUkthE4O1GzKVdAOk5DA2wVDqL1hYmiNBdjwlk2WqFYl26zdt
mSqeVmlukBbqnKrWSs4NgFowy7JYW0tnWSTgvxYn5saoNnNRXd3XuRBBf6CK+7lOYI0ZM0H9iOE0
Qy/HMKbu6xso6+jIs4OhysR5RQ57vcxUwzcHxCYHPI7WO7K0Z5TNfUx/R/R3QH+n8Pe1VeG5LT6f
P/PO4+TQH4wM7iB58pxlyFzwTTHjRxG1lc8G/BxUQI5L9CL77Plx7N2ccKv47bbtQi+ms3TkQF13
xySt6jeKUwbdFJfwPfb44u/8mgNg4xGyr2O8kjeGAOWNhzqvP1YZEMdPG5bouPGiTz/dgX9meGtE
7M3w+5i/03UC8Pv48gTKlIlRQg3JApBGGpTVvyOjlSOrlSO7lcIIEWXklcHICOEYFAGbDyRDIzt4
0U4ZwHSQIRsiFp+bHoVupyPWCKE2vnQFbl2YN9Fh5RHeqcIalklD6mvZQACta3fU3X9Qn06WhU4u
/shZ0nBrZQ9AK7Ur9R0pxFEOFIwJC8eSXogoQPsy3xHaSup7noIGeCgLVdZDOhZEZuIBDFt0kY2o
1pNvj8CUP/BlaknadeLEI9I4CqCblETetM7xQ+ZSEzUW08EZmwljPfGtSkGacHItx0gslt8FK1MI
peLNTwfBBMMAhu1v6PqNYMiJjMxkRBw0oLLp/SkSYJZziABniuFu+yk7FSwl5hPV+5KI0LYAKeRE
nd3p/tcxJZbRqQ+NKyvf/jny5unkzNJFYbyA+eZ4OZD/ccDugqITOcDwbCEDPbA4PplJq12ley3b
3EceD3pbmHwAnIrdIzFQWWkgS5i5U32+jKBceCoLp4az9R/QWC8Mg/brJdoX1JR3OQsHc3+pTKJq
IrnSq66ggG5/hJd3mNfryAEe9fblq76K/ZXZhq7170CmymInYDUNWCcEMtCWP/wzCvwh/JPg1/3n
gNRuG77AD1UZVBPM9ke3itS8o5hkdD5Wvs1TD1UUuFvxDMe9rrmcxWpeGtxVU8LGp42dbytCYDxP
YWhp/Kr0jqg09/PF+yY6saaxHEci9JCYDX3rkeSnDJseGojybLyRs3FOgXFdAcnoBES0RF7ybL8G
HJWsWBZvaFm8kcsii4e7NTBAmZiD8A1Ljtq3g/l9cbjEjTe1uoJD2KhTHDTljekA7LVKA3Ek+aya
vEeL6H9UT38NAYi/oFgulWsKmGttTZGjuaQ9qiUt0ZVfH2m6KprCH5oP8C+LCy34CkLr/hUm9tRi
rUp4WUWqRNQ4uF6Vsng3rNhWMqMKoWA7zIWBcFQeUFeJ7iXg4GEwBlQQGkvXx/1ACcBYpgprR4UU
Xn0v0qWJTIP3ii8zZaHwSJdVBUBHpxKywKAIDFMAwGMujGKGRMhs5BpgqyVcscfYv1Vb3FVQBo80
6NE/s6Rbrp7caPUEJz8rokgImjzFsTfkjVwxMI+eIWcKioh+NeUdAyNbrCNbl6KNdN2igmDrtPix
CUHheqsGR3FsE3WAkLy7M5fXKysO6ivmzC050fi7SFRWz3LgiyS8UVbBK2uqI3c+JYO9KTDKK6IL
ht/Nwn4Kxi/bIWRmGz+xAdxt7IPVyKkUGR38zd+a4qYPSICdTVgoU5vrl+1tA7Z3o8z5uI4+DJJu
J8w7AU2eGdqnA4ZDGjyMMufpsX8isezCsslb1q1CgbNSgZ3KEQFp+YAi4Jn4mDwSf+aitLzl+4Az
8achXXGSqssL+jozLNpAlPq8dMFDm9UvT/zeH7z9GT2YY910xLevB5xCmYwZxqNkJ9XYxcvooZiM
WGlv++yR0j+f0mjRT5qVJECLxkAxZEEVzHS4AT4pK/UFRZHT4y6lIDJTlJn7slKCo2P26fElCPAZ
3mncFOj7rRGlUlnUJvSUmKWkxum3PESVmsZEhVxc5q9LjqC6tajUEdUZZI0pzJsbW9vVUxlnuO7O
cF+2q4xaezbiJ/cPFbxD5YIGVCsqBUOE4R/sMDuo0B+MGyVj6SQ+fHZ0TG9OzGiU2ItnGZPnLJFL
kGyenrbVI6UUyjWggpSvbSteI1vSEMcm7JmlgC2U1EvpZ4/Q55HO1c/MS21Iopgt41AnfnRJ0pdD
ozoqHKrbFDJ6qvf63fUaDAU7KPv0YmMig2wmR+ON7dfDz6MFQhmxP/Z5xFv864x/gdDNBbI/V1yf
LZDVqjN1JiC+k3teqGxFdMci7tvo7cLPi78RBnp5UWGBBtHuWUbnYi1zV+3E8z6c2h2ROhhvjyhs
cFsEt97MLZFduX9vKW9CefOU0xJeyjdSh8r1trattOVqlqmXNeu0smadTgZTTyG3DEHmLzZ8r4Be
XwprD0yLJdYh/KkS/1c4HfhygbyksbRg85zoX/9++784tX9b322w1CrEs2AZFUuxIhsQsWEUSGEH
TcfKLhjU7T+YGiqxTUHztDEzhkYtasvI7P2ysDalbmFxjKsXx9ICaEj54voZL7V+alWyEsI4nOvR
iT0ZG6eX4CrTAT+V6xoeTakxIdgGKpgC+HzAZGQzQJtFC5Y1o0/lDR4Vcoq9BXTcajqcF+hgr2T4
qVshK1c0+MvCbFkDprRJY7nlzY3w1+yERQsHd0zVEXoM7uy6fVG+X62ZX6/miW+sO9XkzQDWTWpN
gm/eM7Xw8jSPqlSc/1/iLgKEREEfUfVlBDPzLgJqZ9WIal4F3Fb5QoFVfZ/ATjmjQHPe/QFB5Nrn
NKmhJa8Q8PUNApTavti2ulKg/kIBj0Pojn5/+tXhv+K2nX0TU3bVKIZfX0axo+Z/bstJo0duzKXT
cZg5DVAKGu5x56QYr3wZzSZlCFp5MODnG3x/OGhfNDkMVCoVn332mTz1KsP/YJINxrNhoML9VETf
qQ4DBINblZ0mMVhu19PA42LNYuCfjuXLrlpnWaQi8650VJ67ZChcRjl5OALrCsj7MoSBeunR1dzP
ABH/IsBgoIdZMHF4DFyWIV20u4Dxs8FIOEGSuAUwHLJnGgW/cRooDhoYro6BUTK6jrrQaIpPPpGV
3ym47tYBaDk2STCJr4rY/PIotKOr+YGQRCPV4x17NKrGIC2MQVOD+RxHAhftDgX8WwPS5vsj5TT2
eZ9VXmFDUxOjvNfatxinilFaEAqHW2GwAPjKS+FIQRjSVTERH3Qc8xnHdKZEmXl2sYliJzZ2ha8F
XhfKMieVF6Of4irjP5kVWJ22iEshUET9MvHlUZZD8xhJQTcyj4gUkuU07HgXji+Yp7oaL0CJWV2g
yRoKa0nPcJgLiAlsr4pyhxS0X0NrrQNW1HqVHjtQ+rRqyyiDuvYyGrOlW+933/yfHK6pNNNJBFtz
LoIGnq54/Dis2p2ctUeaJKWwhfn6ODHRUvo4Dv2ZT3eWVWlbSilHFydmIqgwKtGnRBDKijw91po8
MqrSpQsnc6p0djoONk5p9cQUHqZqjmowH3dC01Fn6JD2YwUgukMQO8hfsIdalWzQM6kf41e09kDX
tRFideheX+75mDfk7BmpsazbfHaEeV0XH8+SN3QNAzyDUkY2vSJUoeSpauBzdgrJ4x9G01JLZuCf
sxUsL9pRejX9dHPTungEpM71p9iQ1PhxKhX5X2454Qvo4DL2T6V1UpQcyxhISqDU22IVrQALx1kg
/umfYMW7ssivrS0oUUHRBR24rWn1Sw0rnILL0bRsMKrpIKv2641Fe0uXzeFUqq63sUnL9mxdq3Zp
tAeXMAerkK0QC5YwWIxHGSoeO1tIALR8R3ax6uYa852yUvNUG/E1rlmqZio6v+W7kfUt4U5auJWc
L2ukiwblheR4B0Ueu691GQXA1GWgq1dBUx4SwBN9QTItLkF50FSFv5Cq5/7CYtg+vTxZ7DyUJxR4
nhrPGRl+ruz72mhnGZc8P0x9jo42LzI5+J6j2/lSdDu0nZedDUqu4XMYQ5CCNkz3zWmblY8k0gWA
wsF1mk5RY/Ah2qefysXJtVajPG3jFQwvhhwGRdTKQdOsY3b0IeWOoWBqr3zHPHOMEcjysdmv5TZk
ZcBupSPIVk3cUkyvBUuuRotCiRFZiiSGxikJL0Ek5cc0Oqqie28R3GvWZGeJOmWMwQ86cKeJjn6r
HZ/P/y6xZ8FFKyKRF56oKEYc8/SjVcIMY6L0MKuFkwxLRyYbIJ+Wgn7JUY8n4PPwZboQtapcSVQG
Dh6l0FsEJ3Zgc0NOZtGww5vrLIvKUyXFFZx3vXUI8thP9VaFDDzOncdLnMxgF8nqfuk+Svt4RtWi
XIrKzl0+u3+gahTZfRs8ChnQbBwUCW3fKG3BZlelSf1LwsGrg7+bFX7SdwsIx89SQeGHY5GQ8zVI
Df+roOzJMXDO4nPlrletjSWk+rNcxgn3tbzGVzB98pcmhaouC17yquA+JwqI1Kl4PoF/7RXU2WJw
xWtrkN89Ht3IGosuVLwn9xfEo8Ni2fXEF6a/ui+qHNUYd1LwVFuSDytIYQ42AArvffplSUiEtAdD
jyrmqXS64zGvwLGeodR3GOrnnOgjphM0UIwPtatK6og7kP5vf/x3mFrlFo9eZZWNNvwBDTLqawEz
Z6PQLJmmrAnQ2OprvEFOzBK/UbGVUR0+gxngVu0YOpWPt/oFLI462pS4gE0mjDnlbzXBbDYKOt+d
DsvFMSiF0ksylYLpbw8+cuRWRrGRwp3LxaDLW7Q0LyxP7qmZUXTLAZ2GgR0gXHnCQsbN4yKq+4oc
qNKbyOwJ2OfyyggFjcwNwyAtLHr6reF3MNrB95ir8ooVj46mrd524aMZWIWCxmS9I499L6q02sDf
rcLwyOOcsRRZzCpq3k6AB24SqN3MYbOuJwsUtvuLsYtF2Se1sToBOHceUVI9zWlFSGptU9Gjpr/J
TvLDhjpe/KwGGinM8E6lFdqTIwo/3T51sXL1UUgUQ9pMrdLcwxYVvhteoovmc7PGKfUpJvIwYuGq
FTridMpCNZQXSDNN+vmhk/yi7NzDVr4pG0MKiYKUW1BePr3QzSQO5K3zUGPBFe9e3Qmd1zbbzNGL
ljxNhZ9jayKZ+VysqeQQo8iUO3TSDLQGXgHidAmeqY0VMCczrJUsQaQr8t9MqdIWeUktXQr5VapT
ulBHCYj2KXUwO0sxiZDqAT/9PA8Ictj0Uq9wj+iL8FUAhlldwpYZS3YoPQ+jhcaX4cAlFtcH1apm
NO4qnTMzodOFFLPSybR/sGNnturVa6174lH1PrrMKoTbEjuF+PZrJeDUVn9R32EpvYytu9xR5KpT
uSj3b9MAOQgqAMmO3AYUOzOqkIqTr3BPui6kkPb7fS13W/zgTD0AiAZARJhDFBFsQc0jlIvvSkog
hn/bpyZZyvPoGCuWW4renBMjSLOzCOJzabyqjVH5mtSIiijz+4QKZ+Wic7Q5v0VhdCGNQo4Nt5i4
qpfPzHMXtCQj4az1WMcZSveQlBlu3bnH1ZJNbEBdUl/ALPJSfca65cW5LJ/qcuYhrEI0sr18y/6Z
y/xqHueGgSS6fK5PqXWd/HBCHpGRefXsyKsFUkVRiVdI85y58jA7PANBkv4+SPSparXRn/MOjU7x
0MVrsMKBVxY7JJi/vpbZa0xuosVBcknp1MHrElvNZTgOc2Jek1Nx3lxCshSKLa9urpoOt3r2ktB/
KYOJPDP/Qt65FZ+IfokXRjJrpmQG1mVKxDRU6TKj8HO3zo+1vPJWfQYbmi75MWC5xNPJ6Kf287C8
is31EWfwiZNTknX2BoIqh1kD90TXejMdVXjZKSknduMVLvz7WNXljNcAAZ9hTE5dgCRw5Lf2gR2F
/XISUBMRkKvhYqO98pzEjI1XoGuj2EcvkvRelDMlyKFbih617Vv2dZzoc4I0n16hRrUruh2cVp3c
Y/ZKaloj81Dgcufx5IYBDU6bB6du63Hx2bviiUaEacy7KslbGxhbVbh2jMjhSj5TmQgMhLTyvnGu
T9MYgUU+S97+PJhBqQe/c/vizU8qxObNX0FBfPNTTYANvEW/ZZACE1JySa/aqG28+elxGEHpvXKg
K6IGE7Sp8q2ipkrJN2Rwl0pW6pA9y/tmPTAt0dp269p7VB3zwRap3IuTCgtYYjA+C+xKHK9l1pp3
CDzG9MqevDgkCS5gJU2uMZNgKW91Qwd6YkWV9Jaf7Ehw/8lpt/9hPnZyt6swePm+8v6rz7L5/7e2
Ohu9Dcz/vr7V63zM//8hPtXjDzIyyFLv1WT8PtqYn/8f3m1u8fivb3W3aPw3tza3P+b//xCf3c9h
kPFYQgpidW+163VWyRGJV6/src6y89a91c/3V3bxnoB9ksi76sJWEQ73VplTTnF1B2V5VUT+BHSE
ymsABJddFWE0CpIwO8X6mDffgrGv14TdV1MflOLg1TTZW/VWYZFJw4zwDKM0HAZGUSo+DqNLTNm8
t0q6SjoKggwsyOspoISXtLYHKTQ/SoLzvdVSWkvj5gsopq++wCptq510kITTzAT8nX/l89NVARDm
gy9crGEC321ThyWd24rQQP420//9j3/1/MeDKO9r9i+c/91uSf5v9ra3Ps7/D/F5h/mfBKCJDXn2
szZmMdEqHkPCWRgmUl9LvcEY9/zNuX0eBuOhlBf4F0M3WFrIrONqC2O3TUVrqmb+xeq+hUChxm6b
Ed5f4Z+ftFoYp7bel/fc8f1goEE/jPAskMyjP4ZXQwowMBVe3GHFCDSu+Rmee27JVnDK4L2tRBf8
UaKKpXwz+laf7UKcShjlGSjlHoGlr6dJHGd2YaZ17ahYpdMAOhMNAIfPuvY7NNSmqWqWfsl2Z2mQ
oMj6+0mkj58P+bHl/+kpJpo/PfWm1++tjUX6X2erZ+l/G5sf5f+H+dwRrbWWYHnfFyTv8cnKeRJP
hCf4Dk+6Kw/PV8Ey8XHG/5f6lOf/xI/C8yB9jzJgwfzf2Ibv6v63rQ7pfxsbH+9/+yCfuvn/A2kE
DVRS8PhzpUHXaHIh4wKTp+roOWhIxnVtdLtCZW5nDBiW6t5UG4rO89ZwOJm0Drqed7CJ95K5qq1h
wGYW3sXWF6urq+r8t4plLkDPQeaKnLey8hjP2efqntgXTzAKVVbaL/bSE4dRGkQ+X3iAel/ehAjG
AYamrTjk/wzOqcNQRIZKPm95nke5EfRGBO2iXJtRsArJphlE1V5R+8NpINpmHEKTzvTO/CGnJhvU
pDvDfLdmFudvj1Z0XmrKoyDPijaFPNZ0rRzTz+ZFE6+sYLqHvsj8yRnec0UJB1ZVnPruMPT3V/UV
X7i7nfJhj4qwZ3Y3E43d/kqyXH4IOzdE2UuuskUwqj1S8xWCq037ajIERU51cpojzhnjDAXMkXT4
Wtk0xI6sYEcorTAdlQbUenx1l32lHQ10ZZQTYwdGyKp9NdlqxQ1pwlH0hh/A4xi6HcYwRFBJElA3
1FwpXHjVFMXLrIoUzEtZN0hhsgnMf6HymXPQWnNF7T3U3fXmCZpctzatmB4bfeKR1accA7MqnNrj
qk07nM44r4r8nc7kwfdrztlBr1ZXHB1z7u4YB5WuzX2fc+MSNjPjBu7hBRLSTj61GA81k3GiXQvc
lhnQdTNjBEcJP8xL1bm7m/3CaZHqyHijX5GKr3cILWRTRhP6Io/vm50FKCuYggCajmaYyjAVUXDh
Z+EVfDOGge7DpJsFzmcBizgYq+8Cs3tC51PxEPOtfl62ghBYmAL0ia4VqPWJdWQYGYZfRYisaWrv
F3aWcAqAqEGKKo3lchqSHe8SQtt9FZ1/+ywwOjrabS5KAtNcWZgApgkPHxdTwOAQytwuFXldXL2w
6BpGdhjq3b2+TrePjHjNEh/FfeXckPxRN0HK4aaikCmdZdpKtUyTHEgr+peHD768/4z7p49rGEl6
OHa2yVuJUH5VxratAvura1jpTMcApZuvU2VStOsKLO5y0ZfuKVQwuutexwOCeB2lEfizDEYU3319
/+hL9XTgZ8FFzErJ//CTYBTP8G5Sfok3WsKaju8e/fPTR631XLvAOZjCi2O80RVjNfgOUvXlVCor
p2eYCaRxour5mY+VtBulYe+jyBaMd8rHKt8oUHgaEXngbIz4HSWzQPVzOgW8fan5fEGX163Mudn7
4+fj5+Pn4+fj5+On/vP/ANTYudcAGAEA
