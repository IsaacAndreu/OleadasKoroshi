#!/usr/bin/env bash
# =============================================================================
# ACTUALIZAR el modulo KOROSHI Monitor (koroshi_monitor), ya instalado, a la version 1.9 que va dentro de este
# script (R1 y R2 separadas, zonas sin arrastrar, tiendas hechas en gris). Con comprobaciones antes de tocar nada.
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
echo "KOROSHI - actualizar Monitor v1.9 ($( [ "$INSTALAR" = "1" ] && echo 'MODO ACTUALIZAR' || echo 'MODO SOLO COMPROBAR: no se cambia nada'))"

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
H4sIAAAAAAAAA+xc63LbRpb271TlHTrWeADYJERSlpyhQ89qJGWj+CKXL1M1ZrQsiIBEWCBA4yJL
nMnWPs2+wv7fR9kn2e+c7gYaF8raTDK1VbuslIVL9+nTp8/9HOQySZNsEc6WSRzmSbp97zf4DfB7
srt7b7A3GD7ZHfHfwWDIz9Xv3nB39GQw2Hs82hncGwxHjzFc7P4WyDR/RZZ7qRD38mKO//4RK/6v
+l02zn+exHmaRFGQZr8aL9z9/Hdx7ns4/93Bzv+f/z/kd9v5L70wdlc3f/cadMB7jx9vOP/He3s7
Txrnv7ezu3NPDH6F/X3x93/8/LdE/2FfzBM/jC/GosjP+9/Sk6+/2hKTX/NHAJ+fvDl5+8OxeCl5
TayT2MtEX/henmRi5aWeiDz8jXMvwoWdJVEioiDoiTgRc295Fnoi9nzPcQGNAG43uVdCsj9mSdwT
RVZ4aYiZSSyyIAuT2HHFId4vEx//ZsFFEQtrlQbn4cfEGhNAAWysD/3RaDjoW8L2LtJi5c0xM8iE
HzDCDqgUe+I8JFSxiZP373gFetcDlh89GpmHQezjHm97ErAon60CP/QT4OcD1WVyFS7xgvDmXcbz
IPKAn9MTiyKY03aKs3BeYhFmeQgC4b2GG4Vx4EV4Z79YhnH/xdK7Fol4+b5/fe3IVaIg9L2sJwLw
up8IexHMF56YiCsvwgvCaV6kWYInXnSR8PCkBL8C1nhDhJdvAHSVhsuAjiuA0ODvjSiiPFxWD7bF
IkmZEnINwt4tKfzu+OjV4f7b8Wgw2uuD1KMdEPtq6A57TFsiKZFWEyoLJXkz0D4Cx9B7QH59dOgK
BUojO08D4Jlh/3pvGXYdgGy0SRwTOGoZZstEPMLfuCCyfyoCAXJADfhEnTltlJa4EVkh0jBfVrQI
IvkAy0ci+FSEK6BHKFVUZsx58zfEzXwFHrvCuTE9zkNNCCGw5dGYeSYT8yBNGV2M0SiABbw5bguI
RAKG5UEJgVXktplUHk0ElXCV0Roa/Ov9N/uH+7OXx68cILOCSmeBmycXxImJ8Bg5hhHEigWIRszE
Ch+JwSqZJ46J9uOxYqYMEuSl89CLcIQEGXBzyBcRWhL2pofToCNkiKmEzlCXcrcVmrw6iAUxyfRi
PDO5CNIxX2Z5Mr8EQMhKELOxIqLR/iy85rdABNsJMmzYc55qOBCcFdg4BTekV3TOj4RE96k49yII
FF4qnFchsMIBS/4DaCyGfQg74kPUUn8jvDQP50WkSPOS+Ark9SJ6JvmKeGPlXYQx8yERrI+pfVOx
9D/0H7qLfBkRLc7CePsKB8Vv3N9AC4dLoJ+Tyg3AQUH5IMVlebO6ydd0e54mS4HDTIR6cR4GkQ9F
ssjzlfHapXtRQsLGs5zmH5y8fL3/6i+z40MQ91tR/rbE0fffHx28O/7zkXhx8s/Hb98dH7ztibfu
C2z51ez1m6Pvj388eYtJw11jUk0dE3UzqL2YeDcg4mWrKLjwzqKAYBwe79P8HVH7bZEiYKa7/461
cXb/dkDvjl+fzKBojg9PAM0yVY719VcG507EaGAsU5OpJvMzd5Lm0RpoomXYJhNQwBpA/hKoGSWz
wpvn4ZXnEE3fHM1eHL862n/BzOxi2CqMAju1xAv7J/+RIyyHB7183xzwLzZsAg1RI+Q+mqN+OnuO
MdDS7sPfWbzi11/NwcaZeC6NrbLeNp25e1C6i86YRrKkBedilq/tLIjO6ammShrANMTMXC7xHlQ6
FpTc4gbxlVtANN18LSBf1lGRJqtg+6Xnp6Ev8ShhL5KbWZRAzjYtobnbLS/i5LPNCxf53HG9rFyf
ILiErePwaLu+lPIOMh4HAxpfmctFSR7Q6eHx1GLd467C+SVcKffMy+cL69TNCj+xHTcLoCQX9tS2
Ym8ZWD1hTaLwki8+9B9YzimUZOoH6cQKfeLAOd5EcAzyyc5g4FQrkhlhhpmeVg/PQTBCRYSxRMlA
kS243AQruBy0AAZuCiYPc9vqY6GhMx2cQh/ipj4xPC/nxklO4OX6DfgVYq63InfBVrOcFjiImS2H
OuLZRFSy3gHyDLb8snW2cnaDH1JPHZCfm+eDBQlvP29AV6AsyzxK8BMoJDWce6gZh0xMcJ3P6Ab6
e7lqcSwv2kLTeuCPHwxGviUewG4QcHeRFBgsr1nygzqvKW3QuZOtUleAOXyyK2IJ6+TFyXwRSJi/
3V4q9MVDsTcAp5ibqO2B3GJDWOApQh6ynmajnkR/8gqiR84NsODr+lZ5zDa/Ffb7dwdw+zgU4AgB
Gpr8d+VNZ09Nf0u5pdsNZ7Ry1sxVpJ6NJWiy0y0/jFQbTwahsW5A3oIhdbRVUPmvP9clcUVywttu
cB1YkZzuFZQRZJWUXEPc2DhMWo/BxdbB/o/7wiLIBKVDWNRceusq0ZZznOnwdDoeQRPlabiynSZO
S4gZYwXq5nGQzkKfNUQXgutu7LSO8BAorKTmAxS+tat7Ayr0IbztPPsc5otSV3Rsas2I1QBMSYOU
U07rc/hIpis39E/pYNoArbU1FutexwvSjHjXiW7XeKK3JX33rtdJkTM0qWuDVQR/17bY69mGb7BN
it9yOmZukXf9ZCys5092YYQPthHmvNj/ywm09EjYf9p/c3D04uTVvmMJGN0rdhO8MYcG8JEr5fC8
AycpMUDLLo2/tkuSDRw+sk0v3Ys0KVb2wHGIKvKhZrUe8Vl/eNpFCulFMzWSNIQrvJmoBUYN3AGg
caBZ3pHvXt5Ibx23087lZjJqtogouY1Y1ZpFcjCulkX5vGsqEUeqJmt2ZlyzZrh1pvTteZO4ynmW
j9n8hPwKvmtM/VmrzvLgEVapGAQnuioCX55rKmwigSNDFDOEwe2NpwKZMnKscgpPGyGNuVwrupGE
dei+vvoYwbTw9AQy8AQ8EDAyMspOK7hYu+ER4UnQdIRmFKaTN6TcJcgb8VAYW8piQIQpA2JbTE16
982E/pX5EfKX2qdwl9+0seIqTfxins+KZDn7lN/QI0newJ95Vx70yVkIDr/pYtc7/axPFLwDgmQH
Y0kgcOrUTceSFDxRsKELz9mYk25b1jZwCr+tqQKnkCI4cxNBQxu7a4xVIfHSu7YxuHvfpyStLHgY
Ut+LfuW0MGB5ZSToqv56iw0256wglTqC7lVxPmwGMWtfcbVDPgNYN0qM+F8PKUVhWw1u7FDlrrpI
gdn2XbdENo4gPaN3gyGrSWxTS/2p+AZ2UYp7m00wUKmsU+0eTw2E6BgZYOMZzDYryj+SSGDSHRlQ
HWbXduksery7U8fUPHwWHULr0otfJrm/VDzVrymlnwzxIdczD5NYvfqchqRcWUn8XWuy4MNxnK28
+aV3ETTlc0v8oDKac5kJlb7lpEx0zkN4jmSCKW3I7phN2UhKVwjlsXtwwcDtnjj40XHFC6+cG3nm
QnwgrIZDCOSYU1FpcpF68GkvCkpTUooNR0YOqDo9uYLKjF4k0SqAZlc58ywUURFckFo3l8FBc8Jd
Lmd/LOJcZSgyYPc2lInAcZnFlEvwaNeIsfxsppxPSo/ZZCOny2jaRU4KM1nPRRyqSswhXBuGnzoG
/QkFvVDL5f5E8Az2Zal2FayNLGywrt4FBeJTi85Nc9Vp0zEtEZmuPk0txpPc1E+NadUk6DsOURuI
U1CBJ5YKWip3Q0Yv1f0SSCuHp7Fvk46bTUb0JZtBnj/nMWwaawqY0kzNp1o3kSMvHcBtq6Ey2QuT
iS3Anu6c6uhfPuDofxecTZ6GHAL3sWVItDMHzen7Nt801sHmsUqZFNM+a9dQQiCMuzU0fMRSO4dx
bmOg8neHjtOAQ0h3QFkWEpGX729DQiGyLDogaFzgpcoNL4sKiRZtpIssTT0OqNSRp61d11+TFetY
fLMY3oKpdIwVshtlvoMEn8Vk03LMcqWQuRfQJ7eAFiwGU9MOnHZujhJBhLInjfxn8Z2+vWV/NHgi
Pt8K8EwDfKZvbwF4dgtAGbxx1EzYyVsJeSJzJV0xMv0osRPGRbART+iaaaloyv3Xn26A3Zh6GzV4
qNJeJU1qD29bo5zYucQCj2WuVqfJPjtie1vsDdpjtcKdLlgzqzvmpIV0gKj6d4vM0G8LcVNIKXwy
62wnpTUMVC2S6n58JWyqWepM/UrVtZ2nNDKJAi6vYuj7p2SHY64Xkp1ur8gp3AmLdtLNxhIjlcY1
UijWh74lg/dIpZbs1pA/9Z+fvFGjrPeWlpuGZegQVT4cZYNKHWn/ktziZ/jyvAWnnWNkW9UrD6tH
y9Yz8ap8qdOjVNCVFVdTKu7fv09uWtbX52HUPQPK+nu6RNvO+I2p0JrmHEezvfYaDwwHk0uyqhRt
J6o6rXhFFVCZZ66C9VNdxyconNPcGVA2t0xAcqUnT70z72NiOFZcTtTVRA7iZeqT7nQnxfPXxy62
XMMrlQWCpo/k54r45DLUzrQhlJeY7OduniSpH8ZeZDviofjDHkTGxmMzC4xblccmSRzuNrKZEhUY
wxwH6EG87cueTKE4bDAkKxgeHgWjkE4jmeBdh0vyIoxnoHuQhtjQhP2j+iYvaXNZAn/Ct9X6TZ3J
8gM/RL2eXjZ5HmjApMbY5MAdNfZUIsRhFt/0RNz2M0okw4w1I2HKkjeE2r1ELFYO+G4idjq0okQC
1LXjXg1dPRG+scIQf+wayL4YNjAyaFYrqETJxybJyQ7VNT6hfZsS12DsuhbvN+A44Kjci2YZZCH2
M3DVttjZG9QWV7qgkbi1FpT8gx8EvbNABDuipJ6W6hlOAW/VWTQmVoOoVkJAGFcO43d5YxoqkOF3
VAzjHEATFMl/NuMxJTJqxqiZErQKRBOMNADTKuRRyimqR2Qbb5zuhWiuwrvc1yYg8u0GQNms8AFB
Da5t9qGiPEDo1qD2tn9uFXaU6j2vV2tk2lI1gYAPqnxkqw+ESy2cDNGPde6xTO04ZCZlHwdgyTK6
uZps6+BUEHckERCdNmrkJ50Glt9SBwmhl3G/TzeS1PVzByy1FeemDvHD0cEP++ZqXhHTPPxR2VRM
93RLEnWuiBPqqiCAM5VCdcpcrVwak4I4C6j4zwGSoej4vdRBKt3Xr7JuvUb+ylgCc773IjMJAGmv
5bEmG/JYGEClH+4bM+o/QSQBqHzfd5N6fkxHKPS8G2DZstOGqSdDWJvwnk2MRfvmmkwZlaW72xba
JHqXmo50BzrdgLnVo7aPVpSoRhKDmpVnjmDNspo6lailailPugiFNAxqCFhRMQLfdUXH1osHXIcG
f1EMnNAxAwwH3/Sur97bEr7TwoQC0gYqy4KcDGVq9ZjO1SmWpuYC8Z//QRVMDsLV2hY74kUm2w9s
67/+7d8t9aQ/LDMGuHVA92E5yRAFnJyfS6dZh7eYxYQuD7tM16oBDEYFY4avAVYkY2huYEvlvHS7
o2e03ukEoB15Ro+jKpvA3cUu5ouEu4ngBrdpqk2rjgrN62cbQlOFI1kCW4/t67EdBpbCo7ar3TSv
VBMFjDXpDl0HLYOQXlnqxCO+okeyvIkndEEPytoinqnrZg64KgRijLqmqYV8UvBNWbyjgzcTQGTz
wTj0RlUQ+82Eb1k0rMQVk8ALFjcrcqov5CoehZHcNKJJR2VFBm6+Y95q2fYlj6OTUKQxsVX5EK46
KmrMJMW4nqjOrAlSlTcNFS4rBlSqJVb+pmJlbNy0GYbW02Waqj5qFB5avkEFwxqbELvs/z9xpxec
hzywre6Wa6sn8ptVMLGo8xo3XpEvJhZFfVpayYngocqJUCV81Qny8OHlZ9OrQMzIfWllBGmr+HLi
h/O8FlqqF1gzipLPgT+jVjYvvkFEm02mVQdiI5l8U+YTqm4yYwC3Cba7rEKKLxDhXQS2bDFsRhc0
T8fIZZvzg4y1Ky3ar3rT6B8/wPnYvneTTUJERWGWYJWlRyFSBVe2yWt0y4406kUzkszqMQVvhPsj
Oa2mdigS0b0alDWvt3ZpCI0drWeSWNSnlvVpI7inZpJz2oBtPfAfLJvJ36rhTM7W/dvMrvIRRaTA
E5rfOPU8xLnmnV01vgpbu/LctXY/++GU9OO1w9OueZrOUo+5G8YtW9+cpsUqMZhyB4mlmkTFg0yd
4Xlt59u09R7hMGGW4twKH7RjqQR5fRfrkhRN16BceE0Lr91UtusQkvWR7Mr+gV1Z1djOvunIg3sf
q1zTkN3HKKKC0Zuh6msF+8BkJWkdHNgiDdwlNb1Qi+iH/k/+Xx//3P8dhHgt1cv0uqKkPEXMuTZz
S2sy729AzY5A9raNsVfwZmh4Pp6qkzSzS9S+WTNkmSqdSJalLgt1SRpfL0l6X1/3jC89qm4061C3
hkiDRFOagZRQ0V/dOjCmpOepGa0CWUu5afnXWTfVsiZZg0lp1VpA+CyyqQQpnXE5qtnPSXXWzrbT
robTWkOT2XmqpRSn8KCzF+muP9uqdC4vgH8qxdsSMs3BH/q+v1z2wcaKZ5mBZZt/pEuamXya4elF
wWFdJmw1882o77ouJxXlFzdg9KygWukq9Jprlp8V3YhguQqDtQc3Ik85RUcSohK8YjC8s4Dc0rmm
j0iWxBE850EKRxkSeYagdTVmpWvCffOT/4h6cTc0zDXa3prloC3xWmc5bzhVmY039jWqfkbp2VYt
9SVVHf7ciibKPqTmSlQ2TrmmzZ5tvXDc0x1B0grRFx70XU3gNI0KXDE2D+ccI9QzefRbyr50g+42
CD/62VF/+gb92wWvjhPJ05sN1Ye137IhZOJuIEE99rWXqgo3cpz6g3Zt0EBiTf0iALRh1XLltV82
CNKSE712Rx6vSb6qed1lDyZcB3ar993GAnIvuIDXli/4Ck6HU+uE34xm1TivEc3XYXwunbeNKMqT
lag+2uj2dG0xuJ4Hq1z82YuK4ChNk3TTwX2Ri7qqCrN1STnZrdzZp8ywexJ0A8XDhmPIC0FMz8lC
Mkj3ilBHCNaBuF9b3T7vqri4qwQWEpHDLS/Pul5S9nbKIY80H2V+ZSzfs+rdHatWvqzKlWWi/GRq
zCkr2bTC2a1KR3Qfw+bq46F2hf0mCV3KHNiXwc1EqUR/TJhzONkYyybxkOuChx1vtOE+VXl97j/x
qwiz8h4PW2pTAZCakyEoH1vXmphdejAqS3t6TV0PpSdUVhXDPFjipL8Ee0rBJ2horMJ+BK9gpsm/
AMWokrah6JctIBz3A1a94bTf+ImXRmP9uPNTzHozfAtCLYC6g2deek138M/zdU3jGW4TKwGoqFt0
INBRSpCulBaky5YavKuykyrn7srtf+K01Y/vC+5Vrzlal3QpIkc07Ad6EonXRUIrtidt6LNtj/Mi
ar5wsxl/ryQXMZ1L/GN8NNdKn/yNBv2eHJ1auxQePqOpoKfT8e47/EOKuAlNAir7q1tgam86gNQa
cLtsRX6LrZCpCzYTdSPRNBA6fTiRIA1pr8aorGI5RIuyER1nKhJn0bo1eyE/F8zqhdN4Zmh7I9Gp
bYL6ZNEosOhe25axcHRVpCxSGKbhbqbwC2ZwS7wl9zWjTzPPArMFkbsvzS+Ux/zVcKz9z80Z2yt4
/HF/2FyI5z0t6zlUKsVClNr9V2GrqX0NkIqusdgWdszumSsOsPZQ4hOX+Lr1NaRVVrlBql6MZFF1
ysnErqhZv1LJXlm4Kx8+NMEBF+MOSLmDu3asGas0umjwpljwi3JMVUD0q2oINQJwGVEPk1XEFjD6
3JvBNb8eIkPNn77y20Z1qqJd5dHIMoumX5k5l8LRVUinD81VylxmF/p64pcT5l07oGIL3fTEhpHG
fnjxZ8YH7p0eG7dOVfM2OLtaph9NRIuFZXFTf9dPLZVBeudv7m3ubyk4u1Z2CjiykKtEHMahJTVq
Mf72yJd9T1wGlVXSVlFTl0F12dXe9DF/4nBCwCiFus2192UWgArPDn26Haqvpe+rIvT9Tvnr5CHb
PDD+rClXvNTpu5dQuguJaoyZXT9tVRSNgTLLr7nK17Vc36hfdH6MUNuN/t8vdOP7i5bYGIBsDD60
EdH/e466IeFKffXZUodFMb7Cr74qYsWuvkpqLqdiFNU2JTu0bsZ1m6QaDujjONlqdTshq2CpTcma
8WyLIP26w6DOEIi9euISuR6djrmAMdCLLxJOdUqepeykceJi2FPl5LEY9TRPjsVOrxb6PTZy6Z2R
l83rTDU1wBM1whhlVOKo0hz0SavqJ9VXjmP5cWNnV0r7V0Z9tXaN6iOz8hO4icpoVa0adslSreaJ
UrlU/0MF/f8X0o4EsDZcNNM14nBPiUvZZdCUGCOurHGSqqbYimrGcdWiGdl3M/vv9r6tuY0jS3Of
EbH/oYxuDwAaKFxIghR4UWhEee1t2dZK7F6v1BqyABQJWLhNFUCJtLXh/9Bv++aXiZhV+Mlv9pv4
T/xL9nznZFZlZVUBoKTW9kywHKbIqrznyXPLcxExaS350uAE2ZeZwUIJlQnVtGZVTFcC47O8468D
BVC46lQxatBWpnMmcduKBFEJ9ZtMjg73idyKxlQlu4HIjxLzNbgWU0Q3YJVdi3kutgsGm1EemLum
zUTymGP+KAwAzGMVX0e/iiLfah8aVJguSEcx97eGDZsauDQhlmZZ1yK8hRGXZdt2MVxIDKWQDhJO
hAZ+4Xqn+vInk6PIWJdEh6sWK4cF0W0kwMXSRMgSZ4rEMB0ND4yx1ROjqtgIMqXzeS99D1eW/riu
HRBgLV3QvGocXLtxfWS58rNnA9EVG8boFRncwDBS1V9Nx0VTXfN3j/+2LP7fCXSg85OT940BuDz+
Hz3bm4j/125vtpvtLcT/3GlS8dv4fx/hyYn/J7GdXB3TCZEg//6wePt8/Mc+/48f3Dv66oE77n/A
Ppaf/2Zzq83xX9s77VazjffNzZ2t7dvz/zGevKicZTZQbm5WCoVH+ubch44ggBEJc+XXv4ynrFSD
0GeHylRK6MgfKr61P2r+/uO/HW1XnaffVtzCA778R0hG4tCvf0KkPObjTxOR8OqrYuedVkXnEQXt
YQPrwiWLkBIV1IP3zBhRMVxnY+OJii3asWKLuhsbhULN+cqfXP/aoXJfTi4gPSCO6O8//hotkpre
xoZTFj89En83YYPmIHgn+jdcdPZYrcJXbN9AJpax0+RrzhOf6PwZkfqeBw7PUwE82MVtz+lO59e/
TGgUj1WZgDpkOQa6nIBmYEyKWjuKQ9dJsEta9utfmdW1dqgsQU5pE2qtZrNBO1JxnUfgnPwzbDCb
EamqapweyVFwPae5/evi+t/Vrg7Qcnfow03KYE4nzts3+u4IBd/+hqHqqQZocmMDET87NKNU3D2l
CZhjW67/HQvw9o02xdrvX//sHb79DUsPffil03LwKpRFrsj6wD+rP9VxcYi12thIX2dRE1Fo0Q4M
20him8IY0Y7xSfJCfVDZ2MC3rICe9IW6WExg3Q/llX/9sxUJNAoqqmKQWjFH41CjcLxnWzIIuFnx
Z6kjOUh8VaH3CzP1EMnJD73I0TBeNDZJe/tbtOwttexRibe/YW5JSxEqkohFSnOXaKTXPxG8YfEk
IOn1LwawQLGnbw4LDmv7aAdFKSnRSREoEe5vtnoSe44xTWj/Jt+xnc4EakmPVpoAPQiGXUitGxs5
gUzp4DqrgpnCzmeqzwT9IkNB9NAFryZ7HDsPjdCMxgooVShNEj57E+oN50sEPY76oE1tBHeywKbC
NfCaKXgUf9LoGqMSbcomNqU7mgI2APG2SQ/DPM/NG8F3LmC4d8rRMYmPAVS4PirqsLnRmpXH1z+J
S5FyT6RpXEosOUQcNn0nq/HclKcTotxqoI5L6bexyyWHVmYFn5iZEoS5QCGyesbiWaZJsihJJ8yy
wJvoFRFKVnnfZvpawj6HlnzE58t0ktRrvIU1xl7yAiufpbJSGrFnj17l8RSYrHMjf6EoeG2sgAJM
GhpNkMt0JKWKy+N5oithDFkXckmPJ9d5MCKsdWkptbSyk3q2FWa+at917o1Q1Bvp6zJF4nG8RhFi
4ykRTgXRMWPeXv8Ml1S3UPjDH5wvJ1R65AWFQhOXYbOhF4gpXTDzqZlTi788leuGEDfawXA8DITQ
W6VOosDQrZPGbmv7hHbuajg7rUBGZqwQ90ADHV//0ueIu302cw0uaHED8ZgN50SphL6cev3+dBKe
zLz54BQNwXMD08dp1y2w7SCsSGHUhkNyWp/O5vUJ1an5wayOaLfNzVM6tC3Xeeyz+o1mLN5cjB4F
lpgIcQBgn0MWKrHaw8AeXc4HiEVe2KQdFE+wqsQ0pIUhPEfSN8qB+7g3G8Whv8F/3CMmFTYOWGW9
T55RaGPDLWy5zj8vQGWpgUzmDqSTEAj4Xh9wMALL9PaN2dnb3yqOz+yPbC/a3Saw6QbDIM0VGVxN
gktSvbngIQOOYqsHjx1k7g78zWThX/A1LkOPP+kRkqgSzkms7qXaRrVVzmwxCnmK8ZJwTwST/wPs
iThOe6rrCIcro9IEZT3dV3Yohxun6kD4BJ60Gc6uU84IVVzpFAo/OEfEVjr0j0+I95dJX7gW54fC
D7Vajf+nMn8m3PiD82Qx5p06tcIynUbwlxcFHs05D8FPTM12dOCCUz2f0fXPHEwHxR9IlPcfnC9U
mHfMW4dDhxfWfYMoRyHfuQv6CCREs/ev2BlORX2X/qntL8SVnSaWFZPeHk35FEkd7jg15+H2HedR
c8u53zytyJx00PofnNOHp7SrP0+IKv3+4980fWLrM0RWjzvikApPv606pxzc/lRmK8a8Tj3iQH5w
Hqnb/8vonYxIcWY0rjhcyGkFRMVAodqZC5DJRvbz658ciZiP/u6D3vzgfH3961gEDivmvwIgDvYZ
B2Uqv33D4TgnE5ysHwqFz4e9AdUnvvM0I+UGoUkWWugULIBFs71uMPRTGO4Me/Uw6NW/o/ry3f0u
PC2UNVa3ivXCuBz9TqLT6cXQf0kv/cnCfcXClHrjhaE/D/ldREK3QUIBtODE8s0IgWTMO5muZ9zs
VWMCWdH3zGD5ldUysAMvoHAKiuOEsHHJKJPDUNGMENJ/tBhT6RT5JJa9Hxo3z+yXpyLMVTBKmH2D
XkzURk5I9JgPL6aGDEddv30jh494Z+fzhS83SIT4vlOk5+0boZIk3wATM5PqlFmawdL7bLYO1lwu
KUfMPsQsXxtreabbjTD6xoZJe/u6PlN6PePEfOXiVa5Kq4rp1BIIuMKqgDFiZLEsZLBGjLA/lwj4
ujiWT0Pci9mQhdt40DvEcorUUOHhC7t+Tv8YSxBJUwZnErOKsg17KoYus+m07wEYx+tfGc2LwL/H
W2CgJFpnvuo/o+Mj+EaduvKfmg2nubnrLCDLKulXrSiLlX2gg7dvGCcSedMvQyKWWspm80d9aFic
SOUkIZpFx4j5phFBytjrESIVlwXQJmgNtPIBVwXwL1ALc5ngxkSUIMSiZZg9vKIvfQh4agOncpoI
hL0LDBYXV0olQItCJylgTYsaG+aE4V5MRzRKiS+HILJMlboI/FEmIVMF/I2Dx8b7ussHW13gY5B0
MJVXRQ7vW17K+qazNADTMlOE3onFvv4pLDj5ImFV6QF4xzc2eOtoiGpvGUG8fWNYm4B8qcF8DYEW
lBRV375RV7A4xcQzi0TJ51uBq8CJ9nnQE5oGUcvKY9/9T6cEtwmLohMftI8183+125utdrPRYv3v
duM2/9fHeHL2H3zCB+vj5vu/tb25c7v/H+NZsv/gEz9IH2vv/3Z7Z3MT+7+9ubV5u/8f41mx/4ac
8O59LL//a7W2d1pR/s/mzibu/7e3Wrf3fx/jqW9kXwB2RC8hKa2gt9UZrVbdxCmjy/gizp2eWEDm
bNT/ayHjtQpMUqu9GNe65x3nD2c7Z+2z1p686RFPjHdnZ+rFcPKC/m726b+uejVezH0UanfbXntb
vUR8XHrX9/u9/pZ61/UCeuXf8Xf8xp7R7RRNtvw73nbU7QIl+41dr9FQryDu0rvuHeqlb9a+aqL2
2U5/S4/xqoUhnm2fdaM3m6i6vd1uefrNFr3Z8ba6Xd3B1TbKUJdNPYqrNr1p+Du93bZ+s8NlNr12
T7/ZpTfb3Xa36es3r+K1kGF2vd6Lc7Y0Q1D/oKzWmkQxFsCMl7S6ENCId6+FwytawOb27NUeBxuu
Dfzh+WBOr9wt3XD0qtH4dM+ZkgRyNpq+7CASyJSKvM7ccGg7nO9hmVx7OezPB1S9ud1AN2MvOB+S
YNWQBkiy6YuFSmtr9spptulHmwtmNzxoUrPG2FvtRKNqXi/VmHewszkNtZINNe+YDW3SEGiITR7J
uk26DMtdahe2pSPvsuOcjXw0QD9rLwNv1nHwc4/ky+H5pMYGoB2Si3Cvs+ec4zt65FXYc74jBDY8
u6xxHJQJdR3SkfRrXX/+0vcneqw1khvn03HH2cpfNB7YfJQeGHe5i4qZI1remoSdoEajLcQOcmtd
diGj2dALQhrDfgx9ALOKLlEj6XG4oB55wpkgDORQWTaUcIEVt4Gc8UXFBDfazd3lS3Qe0ECNNcLf
e/yzRutC7+Z+TZQ0IQIOznxvXgYQ186G8yrEXFgWN3doB6tO8yyoVPSetlZsDU2R+l02/RsvqEBu
tDPNrQisLLBpLjlsGBy0RAmQ7o6mvRd76TO4vAmC3cmSbTIP4uby1q7MwQwnjLbUmJAkVaGbTT4O
iB9UY9COgTpGOEloTcKiGqgQpQQC2F2OADhw8LpA1ObTfhYkACXzKMY7yZgpGnS0jbmAsXyonZEX
zmu9wXDEIJhsdOlEidAGmGlEH/LPcJf9haxl5qWPyclg2O/HWE1wCfVvIaxVwxlmQGqSgOW3wIl/
V+Nu3qn4OCUg1902YCcF5Cu6zkJjQqvzK478yxysrkZnjz510FYhzrZBCJePY5h/MDUPwPAd7Ucr
4/BtGigqkHK8plo9q09zrbl8QGEPFy80Ig1htVeKZcmpNGfzpOgI9HBXOwt9XF7Kb/EsGI4y9j2n
4UE1i1Oe903KiVXeMZZj9bE2UdvIP5vT8AaEM2rMJMD2TfY7b0xr4uJWiv9p56O/ed8Nsuc6cEkG
SAyZ9za3oQBbOJ/OZZXW5r/GuvCZNx6OCAoXwxp9nPKaVOHRC0u8EHfy6qU122X7yJTaH61FfXa2
EtR3E0xtBrBv2wiklUe08ock95c53MP0RcUiZUvmxoZVeWzIIli/Jc6olNOQkIKbY8gx4jF8r4/g
nYaJSHZvRni2sglPzq7aiGdMxUe+jaNWcEA8+nelTbhwHI5CFqciMWd50XAxprIgDbyrtNSz6VAg
KX2YEkhoKcnni5kPwsTx3eG6XNLWlnBJSjCM5KQcVomHQYMbevTvZDH2g2GvA/y+GHkBXoQrR2by
N5FIuGp1uGb3Rniu74Rjj8nU0jXV6Cy8DGmqtcUQ92eTsBbS1JaeRLkPSx5FnN4tP+Yg9aH2N7tb
214E2PPpCslFkLRKbz23D3zUyyrJQi+ACTxbKaqzBUBdgjXqG1a0ctPyr2pELo/uOLtDD9ah8Z1m
nupKaYZYrZTQ5YSAikghtQQdqiHlYMSZdwPUGkVQT692en2osCU69r1w4PftEkv4Ul7ECDoj7VYa
iaSoWC6LALAM5kBnFsMSECTsvR/9Vh0LNOx0khYMVdsooeqQ3DMzbA1gVzs2TQWc8vFfKnmQIdQ3
mJp8HFQMTmsFs4xKOF83VRTxVxqnIS06mysoD/c1YzWNsVLt9AljsTapA3xvVKr7zjjjrd1szdrN
OQPuBVZTq9QUm+kuMybtNrY/yLx5RDfQeqxQ33GbtsjduqHILVQ5X+ZmLdFqYc8Yy2qeJp8vXQU4
Q/8DLh1au6mALRQuUCx2msT53tm276+qLXx1JoFs+61VtTXxyKjfpP7vvCt17vtb/d5ScYBR45rq
kBWKVbSVLzcl1McCexbc7qwA8xQw3ByL8BDfRQODigTPN4MNs2JWpyvOByuMD1OCgfBsei+YDCYM
30xrtkWOMZsYmrEHGmxcfQQelxi6aUs50MXutH/JwvoFBH9c+5xMvAvaFnO/J0iS9Il4HFMrPLxk
RYSdmE6o/sRDRJDvTSRyMVi2FvOL9F0T+jNVphBsWkwtG5bEvYpUq9btW6fNNatZd0zJyyoe0Wps
q9rKJ+bNNSexiiRvrTjFdjMRzU0xFjdsA1QyU2+UOXgmCzffwlwiupWFcdZsVCsNzeGsUEzqmgNr
E1fwcXoW43eevOiuzC4ZrRpaKwVI6eu8tdpPamhUW0ld73rjFGJhTrKVGBZO8w3a0zJw6q7XFBSU
I48/8fusRhHPFD9keqfwJgleggfZlZkDAo4k3LY3QUIYQpMaR7JhRcAGyXnSg8JaCZ2ysRcsn7/C
eHnOkVp4nYtE89Y9cWmf0IHL3O90lLsvpKJdZ8ph5OQNJo2zQjOB8KvmzQ7HEzBE8H0Nh6MooLtk
wb5yOKZpb7586vr+KbTGu91YAdGqEwsDrlLcqlo5unizREItD50P88w30K0nG1ul31nZRnx0DejY
aidOBAjJlkXZVp0Qo/mrZOMimsXUkxrPVlSbQKSM9QFFksEcTrMwN2fmGcLrcJQAGTot58EwdMqX
HlseVXUuNqhnxkMCuRFictZXLbHik8XOO4NH7/ldfyfWr+x6u3d2N2nsN2o33oRE48pOyFLe/INY
ki+x//vuA5l/rmv/adj/bTep+K3950d4lu9/7E72Pn0st/9sb262UvafrWbj1v7zYzxwaHb7/hlJ
2uWSBQyu+hdxsxcTlr0czr01DPwKrDWR4ctBPp/evLRHaL6eZ0uq4rto2XA9O9I4dAtSgFLjRvCZ
bIdINyeeyuMHnz9+8OT+N84YRVTkFxfCL1Fa514XvEtvfk9mKHnHqKty6aXfdZNfS5U9qdSbBr5d
FO+4gBSJej3AdXijoWo+fYLwcKWjJmJDHrX45yb/3OKf2/j59NvSc1X+/jcPEerxqNlxShFjcNWs
ULGjVuJdi99tJt5t8rutxLstfredeLdd0UEfj9qJD20uvJN4t8PvdhPvdvHu6beJd68qpdcCF0L+
wZ5OtJOwAo2jJubhui77W7EWdVqNksvA2/fpt038QJkq+0BGOYHKj1u1oyZyAEHLESDdWQSo3NdT
6qN8VdGWxVhOeDU3qpxfpv4vj8t/7X9WqZXdjcof667/yu9RaWXROjxzymOqyjVmXhD6XyL1y7Pm
8yoxzMSUIR/B+FnrObM4qCFtHnGbS5pT4f2cDfDdDSTSzmo90ebTb6nRpWNMN9qUf8rpxp0ffnCM
LjLqtgRcXxt7J+odxfeMVLImWlH9gU+4dk5lF8cFb7HaJBQ7albEUVXfo+jgKtIW4vlOrV0k6eIx
PvIm6pFeRbFm65I3qc4BZ3lC2OIHT45xYpinJHj8QgViZRUr/W24vyOJEBtzlwwfU7wUfSq9fyS6
0bLlmghg17dsqrZE233Nxz8av18OjYGfuEBMM3rpHBwcOMQeMuLtY0Pk1WRBcsBdmo3TcZ7QUk/O
qQGZWdTmBCk0oja/8mA3w7FDXyE+6UOE8PRV3RIh1AdPSlYDV/PEcpb2+QKiRzsTHhRxbos0mcuR
f1A0+FgkZi0TLnqWs/rPMYnk2ecEb8VD1PTRI/21X0dfh6XkgAbj8gADwuYB4I05lQcCrRxqnuZh
zpqE1WlQHjsctZ2TyQ0cHmapwf+MnU/xpeKGoyENt9ZSt8D1VLYsFZlGu0xnhKYpsw90R7xpdYgp
HYZnKHIJOz4MppfGzKLooTNkKUO+e42LcHQ/mWFyn8zcwczcj5J9NEv7g9ahPeb9Or3cnxn7BsOL
4uEDmco0ZyadrCg7VSeKsoOV45E6n8UhSUvZ4XacsqRn5WY4VO6mOPKqEDTifqtidFdc55hlPozp
0dE9ZxF6omeGkwn9tUA8karjhdc/2477nFUhMKMMufv1GSDLGON+f3hhrAbMRAT4rHwqz2aumT2e
caSbTBWPI+jss1R+WJY3aEidKrt0nCqm5IJ4VwXyKwTs3AIOc6lkZq1Ph2GqpJK0PqNTwZBRVdnn
dcSlvJJxhvqoShS7qSSzlHDRPLuyHEv9Ts7P7z/+zdHvVZxonomaQarjCcpxsnupv6gPOOK1FSMq
PWJdURXgaNTJMFLpOtHqI7N9zpo7oe5f3NFp0hKpL7m+z92xNyvHTO2LBDpMwhGry8QQpXi432WI
eiEZqwmddQ/3BaPx2+ZzA8nt16khRnUV97vpcFKWfNcl/Z7pq1AszS4fWMwokfs5gscrnEFn7L4E
C3nkTXwiT2dImKHm5SMkDx1vI71ziQjf5NwX+5Io+2XpZDp5pP6qmoUJS77gslGcPi5N/56DKqaK
6pulQ21Jpho/np6fj3xd4XVVZ51CNOGOIUpUzLHOB8PQPQkXtP0ImT+6LOMNoYPgfIEAh6HmeaLC
cZZZXgb7s0QlVMlk9+yxcJ7O3MFgTxD+GXmlqC276T/6I9fr9+8DRsqllIaoZA5VQdXq6bnzAbJI
Zw+Ih4x41Oga4lG5tA8FaZIAhItu8fA+tou4m99//DfgyH2OKXOYGFPUmtrbcuZHRO7msPv+/EvY
zF14o+Tw7DZoeSOhx2zxdSW1/H1ovpGwIWe+vZHvBVGvvHg8nBQQrAMxcbcx5Js9+xdpSIyBy79w
CVbO/bmkMloHzOLRWeubGIkckyUDIUblwcjBWVOxr+bDOUJfIdBjXQgyp1/RQQZBbDmESKACkCEc
mk6bquXiaRLK6QzLHIk7Jow5P5apUnX64+tp35wvykPooTouFbo3J4Tc5azgJH17tasEjIG/YS4z
sUqSBfgTtDCdwajkdWphZMne4WgmTlow65W/55zlhJNyk5ZjlWAz9f1MQ4W5+a9fpw5lkH0qY2gJ
9O/WieJhi7eBiixPB1leHE9nmWdzhphaQTnIPJxmbbTIvy8/cyc6A7S5tkFqcRkgAjdOxk0sagKy
8+jkfET0Ubn7xa/VcggnVo6Wh5t99rxiEeJZan2j3qYzLsKH8KCouBQRMYS7YQEq6oCZHBmN31f8
CworccSfP5uxyDKLxZnaH+sqcwlTaemQCXW8qhYllw6ILVjM59NIhurOJw79X5M8ETCxNolq8TAK
50v8A1c8jHkCa88ECPJ3DMcMijri9zH9KMd03jrK6ZBWVezXJIS9Xueo4csRg8mR7KP1jeXvBScX
GfHPAf/s8c8Z/XxtVXhqo8+nT9yzafDA6w0M6GB88lRwyNLmq85CXk24r/g04DnKaHmaWi+Wz54+
m7pXz6VX/HbTfmkWs0U4KFPdWN9izhvoVJquOi/o96lLhFF2UmXdITAeAHzLxieVwIpW3ngZpZlB
lR5D/KxkoY4rd/LZZ3v0zwJJjKbuAr+P5HfObkN/P3vxnMqkFyM1NCwLtTSImrLmd2z0cmz1cmz3
ktghXhmWkw4YEDh9tg0HCqABDu7E2mKuLJmO4lok5XaNirGCkIScmvFnlxVkZc/Zd7q0lrUmLWWz
spce4qw3B6BjnndNnUWz0XA2eMp1fKw4uKg3U6+i8gBJxJiHMzUvGHcxgXJ4edMyCTF6+4Pm4f38
IOwloLkY4bJ6plTJxXbUWKpbxWEpsgHMkxBfrCGmOFFgWupfBQmEdKZ/j+O2EdTOhzpUsOgLUe2I
AGVyPh9wrW/+fFxxOdxmGBldSLQuJY75NE3OomLqA/CwgFYFj2TeCkzNKOuu82cdtzuQiJRlIxpn
nAxdqTZD5+2bI38MK7h+/THnn/L7Ev3PjOAnNnM6BO1PE2fsjURTKvfdMm2CUVZjWGzTJ3r2KaQU
SR8sAvDq7M8Ov5Yr8ShesJGz+fqXibtMCpCzkET/K2BviV4F5wEb9imxVpMyHQCRyWk9UBxvFkpP
oGOkp6X8Y1c2ve6YcECQGpsJZFXqqRJmwHFPsvGkC89U4dBQ+v4DqgcS2xBpEoNI+0SzUKkVEDBT
h9/WB6mirqJ0KyRNHCN7lZlfTm3woHWoPnW064sK0XcZ/e2r+JKidsxeA+FCaRnY4o3+Gfhen/4J
8OshkOt+nX6hP3RlYoYQIpfTauV8Y5ccqDszv8bx+jIKfJrxDvue110MYjkfDejKKWGPp47J1/VC
wJw1sbVCqDI4nUnq7MfswtXkuXWM1T7yQvcZ2KDjnyh4mqPrvjFQOY1X6jQuKTDKK6AAnRsh4hmX
7B7mNMclM8jkFZPJK0UmBT18mtMGsS9LBnwlmCP3a2/5XMpS4sqdWVPBFpbyWJVo5Y3jQOBV5I04
VnCWvbzHq9b/OH/9oxZo8VcUi7FyTgGT1uYUOV66tMe5S8vrKp+Po3XVa0o/+DzQv4IuIsSXQFr3
LhANO0JrWcjLKpKFokb+ZVHh4v1hxvWWaVRPBevDGBk4ZR08u6JR9xrtwBdaGkogjbXr415SNWCQ
qQTtyMDCxQ+CXaoAGvpjrSNLhQdRWV2ApAIuoQr0ko0hAk6jqgoDzTAKWQwqRrPZGC45Y8yvaKO7
jJWBVWG0+10Lu8XsyVXEnuDwCyOKheDDk9x7A98oioHgswaeSTAi0aeZ3FEYIdbLqneF2pjXTTII
Nk+Lx14ItlYvGhAlRpo8AR7kp3tLYT2zYi+/YgzcChKNn6tQZfYp/0oZVIpU8Mo66oDOR6wiqCoj
kgPn2XMO/x3yrzcW79mGB4ozbWDAInqGCuARSecitrAewPgT48F1aIfEWglXLKPH3/Jb1bnq0Jhf
78mgtS5A6qcVAkbb7tWzHjqw1YgYEibtDkkAefXNWblXITG1URHb4VB66CWbTmwCl/p7CsaRwUhs
zmOG6WajrmlkwRPfT/sSx19MQPhymXa50TSSbMoaLh/7C+qx/OiZ91ztACag3nXjd5hFZBbDpWX/
ItsYqmUW6KYK5E1aW7awIBiKFh6pRDiZQpbJc0xcQkTHVpbRiSjb4pNeSZ4G1YE6Bl44tI+BrFb6
KLzIPArQIT969oLamoh91GAg/6pY2FbjeL7pfuf35u4L/zIsz+jwZPTVS/WFZ5JSL2nInjHYZ+mZ
BgPorV47/ihkTxoeVSa0pyAez8wVyfyApvdP/8STg7FNxuFSJdGnLLF0MqtEvaPUhACEGtk/cFp8
9Gj9pdyzmV6y50sOoSF25cMLkx81BkMZouiFbG/8vpInl2Vok5KN3k2LtHDqFLqqiq6tpLcsidhL
J/ZiLOIGaxRr76MDyXZCkTLnxWQafzOYcWU6tEQdLwSzYymjxC4GxicXSJilPAgmw8k55OYVPgmZ
Ghre8BwdTYY2jAegKazhhQmnvuLhQy1aO03CAC1tGIm14H6Si/8q80xFG2Cu4atnjeepZRS4QrJx
btjXS1h1lNWKrTOOFpnZGNVOckle5xN5/T7CkJFrR+wAJGkEWDNcZ9F8T6dNuYxTQSAvBzLIcc6i
wJtPJ5U4y5K4JfHCJboURyUqMfOSjkrcg9p50QjC2HDh/InOtmRIuNRZutL9Zh3k++xBLQ0iZQH+
jGWRNDTel/xvvBbwIFMp8zrpLIJ1UVeIPTR7oI3E+YyGK0vjOikmsXQvOerrXyadKNUJ9JPIpWYo
CbHSqq2/eL3rn3GVGa8QnRhOBCHpgFjHKLNDkgnTGpdNcaE3EqNQbQ7aj6xBU6cpR72dpU8yCogZ
atHWMCE3j9bLKNTKf/JRAuOTPEpJI0hVTowjRVAdZKnnEiofyQ6zlqrnXQnyQggx7o1zhKJ5oMy7
hMjh4jNeKuWcFKHe41UuWCpnSkyJiubtKdQaEZKZMVuU1vzkY3ktCvmY9jpYX1vhJdtyw9loOCeU
VCOMpMw7mxGewkt9P8uVeWA2XmOAyL5jTONXbAnOBDiUK5sTwsOywpRZFbUpfd2tVrLbXAqe+IYs
cT+WLmi0atNYOuH0DzMFzDphWZNbMHWni7m1/tTVdO4nXj54cvyMm3juRIa7k7IaE5es61dac6UE
1YzlTfFg0QxSaqyR2fbC0hKtFCfXUiI9VPzVEiWSma6WsbbZM3sOeJMXLPOJHXlD2443q44yNW+Z
N9g3VL7AyeMofdU5NQUz94r51iv7uhPPwxWSEUb/zJPdrclfXfkrIQ15S0Wh7go5SE8mT0+Nb8oU
CBqhiQO7eZizRFZUd5N/ow1cfkOrQh1CObuOYkgY331toCjmSfo0KEWRWI3o0QBpwiIpgeuUWaOl
YXL0laO+WaWPk8RBipVLdVuzFOuCTOVRNU91VM1THNHR04NbZ0GW38xIxsCIcibIKB2LLJKKPx8x
gxT9qVP6ZdyMSNrAuKRBNdG9iP7R39f/R5L21aOshWsRWDkF6yh/NCiKlnNqaC4VsqOup1p52csz
yzDVaAw2CfWYPTJja9Q1zVqI/DCNmE2smyDH0xxyrLoYFw9tchC1oT8YpHpJdaXAymxhNFx67TR1
lcuALpKp38STSewQPiJHzymK2oS+kvk+xWawrjLS3a4ga8ac0nYv2j8Hs6XhVLLX4SyxDjYlw5NH
ITMpGv0UZLaullXu+7Msl8V2wLQPfC03xVDDQveklVjweYHLVjpzejVOnO46j61s6Srnn5Ujvcrt
mxmkV6ZFd7X7mR2jb40sg2iJbWEn2WkGF2aWQe6naLiAFWlsRUkVWIwyBe6lo/5Vl2UG9CcVO5YS
d7RmckAvyg3ISeuSfetkgfmpAl3xLDj+y8mfHvwv2BrZOZbnF8IlRYgSDLg+/xHboN5o6yGT737W
eJ5042JFa6qFiHkw2o+tkP56VD+vineMYiru3LmjIlMprwg6ZL3Rou9rLwjt6HASeUe8rmoPCqLJ
UxKXL2e+K8WqSX+IyMVhflHrzifaYeEiclaorOkhMOe4uWKYfkHL+3JIG/WSeGoCgSc0EO/ch430
l3N/XJY9qAgOaUKkJMCf9wZO2Q+CSqIZ8WQwJYU/lktAByX49sFeXDkd8BRKVeeTT1Tld/I5uLFd
fjyawB9PL5KjeX/j/OOL5f4hvEZ6xnv2bmTtQZjYg2rUzF3sBIh2g70jrQ2pb4i6SI6xJ8ZgKjkt
H03cT2zUb7BPGbu0wkMA9jpEADylrmFsvKMipOSqgvbM+EJVoJ2pYbp2yeowwTmhUmOdgMp43ywS
oK514EkBiFc/vfjKSf2B6XOb4I1Mf9pEQNuSbQYsRpHLWFfjAzExKQ2QxckmdUBJalsWKBB1cZKb
jTQ9Ce7X4FrzGktyvZqP7Wl+WvdllAGvvQ7HbPHWh823/zdu12Sa2UHT5pyTTRNMZ7z+aphlQrWo
D6IlSdlWLufHGYjWvoztepyNPIvb0kw5LlYRLTBDqIS6jFtIM/L8OuLkAaial044LGfx7HxJzDfM
Jdakmaw52GDxDYfoGEXRVPJjRkMDWnaeoPyCGUasZInfKf4Yv0LaI17XHpCwQ7sdZZhi5r49MMJX
WzeIe46ZiFt82VXu7b4P19z0YMMLHiqVPNEdALy7tOGiUjO6VlyyNH5XpGB1baj5av6zEovWSc/Y
PK2mBkNm40ehYuTfX3LCB5rgOvJPpnSSxBzrCEgaoeTLYhm9iIYO95WfKOwSL39Kh2f5Gi+fwE1F
q/cVrHAE11vTtMCoj4Oq2skXFm27MxGHQ8W63kQmTcuzeb3apSEPriEOZg02Ay1YyGD1ONKtwht/
5QJA8h3YxbK7Ky1XyirOU1sL5qhmuZrJ6PzzaAr8xJIWiHwZ1tu9hQ+3RrA3Q2ZvSOITdR2knXkQ
uzRGvIxuwORlaKoXflX5TiLQgR/MkiQotuzO0Bdy9VhfmPRm5I/PVysPleOmnFPjvQxG3mv5PtcJ
TNkKLPfeW8KjLXPY8v9VnP5YgE95/AnZ2eIAmJ7YWvohccOcST6SWSVSA5EgH2ZtRKc5PhI8JCCf
fqbtWCxqFKdWuKDthV+Enxxa2pdMeMxGFNGlYTCYkVa+YQZogWOWem3Oaz1TMeXHlKkIslmTSsrV
yWpLUaNVHlYYLBu+UOecKIdbZOYn16ok1miu65Fk1hRliQ6+AgvNyLq4CkW/1Y8nYVHWuLOQohnu
UysdTZNuUnL8LqzrTQnhmriiXN97ymjyUcoziRX1CBcUu1jBTSmzXApV+mV4mEZXBM9t76uSNvwp
2T5YeZJFprNtkoKLZUHkJzVS0VwM76hYebyGw6qoSIqHT4jNYylTy5W212oWUU65jsUqn/2/cjV2
P7vJOBJRyu0x6CW0daN8Lzu/WMdKZ22ftWwPtWqGnvTdvNbwrOW59mDkBKx89UND/+pwhqMpQc7q
cDsVN5sbC5j1F7yMA/f1lCMfCUdvfjRXCIiKYw2Eoo2c+QEtlontQcFHWm6oxri/0pH4SRMdLEgC
E126CXY21+joPZ3mjMwuUKH2r3/23sNpjohl03U+N/XVHSdLUe1cWppqC/OhgkLmJAMAeR/yXxaG
REsHtPVgMU+U0h3e737ZegesX5ZW70pUtCk7FlMxifWjK+nIP7T0v//4Nzpa6R6PX80zOy15Pd5k
8Gu+AGcp0S2LpsIJ8N5e/ypdA08sAq+UcZWRbRuEKO1F2+BR58zJ/kDEMXKJYSgQkQmOMdpOJNPi
3h5CFJM+sl7BHqT8/dQypTz+bt78pKyuMpKd6MsUZrmSniE36GmZ74C6UzNN/ddrdDb0bS+mTDdQ
5dwHIhrNFRCoo759JkGlMOc0ZaSCRkCrvh8miF701dA7GP3gO/JJXAjj0YgtjvS1i/iPogob5ql6
x67oXnRpfYG/nzXCY1fyurD7k7CocT8+vIIDql2N2xZeTxVIXPcnHSySuE9xYyssUrPPEQe+jyAt
2ZKmbdpW3dQ32RERRVAfX/8U6o3GCkt7J0oKbakdpT8rHZ5iJvXRg0ha65lcZcKkKUN3IyQ6KT5X
c5RSYvOaNnPNoMkcXxZcMl9hans5bb47UTHHQkPD5kxB2PwJ0gbwpCowsOQVVOHNwRfkEGFDzeQc
+WB7fNTQMXb/9OhL5/cff3U+R+eCCZh05bkRv7bBZglftKbLN55n1kEyw9xZR6nMgKIiEbKNKHEN
QgGm4Rowk2srYB5mopWCQZQq8n+bWKXuxCUj7JIIO5cd6Y4nyo1EOqUGgtYlYyvqGcjbu7FBUFlE
L/0Jd0SfD1/5fRgtZsexWwhmp9LLRrRS+DIUuAzikTd91onGrdKZABOULsyYpdzn/8F8423Wq1Xb
dJ2H2ffoKtgiriX2Ek54lxrB6av+JL8jWHodWXe9CC1ZoUSA92/SASsIMhpSE7lJU6LMyBrUNPgT
7qSXOlt5tqdVV7+gFo0GMWAxUUSzCTZP/CwS31JMIEzs7dAOguVld1KuMGsZmSv1Z7KJu0p41Rej
6nMlx6/kHg9FgpVysI8Y3rSLCZFQMXy3gDhrlk9M51AmyVg4ix5HdoZKPaRwxppOQMwyxK2uyS/E
TkFcN02c0/hpmVtQykQ500o8JvOWpfg0bSmu6Trr4Rzlx5vyGWKksQqr6FUSCmkGw9Ea5rKcQMKk
f/GDKPSLvuiPYYd3x3IFU15sKxUSAl9fq6B+JjQxcVBQknKpWOKNkwVwXyg/RL5skaO47CxhWRLF
1mc3i6bCLR+8VOvvC2Cm39kq2LkRnDidFCwMVIhxBQzCy6QW02Cl04Ai7yt5eqz1mbfsQDHUdUqP
QeQSIVSgp/Zis7yMy/WBBDacBieM6+wLBF0OwZQPnKbteznI0LJzBHNMA45oziGqViTHE7WAd7DJ
yTOQJIj8s+0lpUe/HgaMFpEGlwPFRn+rfQmV9iLtLKi2bq31yO3fkq+nQRTMgM8T3PycfafZwLFq
xBqzV4rTGpiRC9YLGqAuDHhz6rI5eVePqwMEJMMuoE3j3GVh3lzD2KzCuXvEClfWmar4qISktfZN
QqCbwkgZLmXXP/cWVOr+f690nLdvtInN29+IQXz7JsfAhr5Cb+mHBIQcczvDG48X6u2br4YTKn2Q
NnRV7o5VHYYenCpHCFPGXdpHvszyrNybteDcSNJ2Ja+/h9k2HyKRqrs4xbCQJEb7s0KuxH6tQ2ve
wfAYiVNcldwz8M+JkgaXCLCcykhTigw9UVHnApA3e6q5/88Jdf6DPXZk3Iuh//JD5f3Sz5r5v9rt
dmOrtdX4L43mZrvVuM3/9TGe7P0nTOrPQ/fVePQh+lie/4u+bbdl/zfbzTbv/3Z7e+c2/9fHePbv
0ibDeSEk5HtQbLqNIqsrkdXxoLiYn9V2i3cPC/vIE3bIeHt/ToLHyJv7zrB/UBRIOQEPQCx10Zl4
Y+IkMtOAOVK26AwnAz8Yzk9QH3mzrDYOI8qx/2rmEevsv5oFB0W3SKQoHM55nMNJOOz7RlEuPhpO
XiDfxUGROZpw4PtzkjMvZzSkuf9qXu+F1P0g8M8OiqmY4EbmOyoWpb5DlbrVT9gLhrO52fB33oUn
b4sOtbC8+URiPbPx/TpPWK1zXS80LX9d1v/D73/2+Ye7yoc6/SvPf7OZwv/brZ327fn/GM87nP/A
J36tL6dfeDYLiIpwVsIpHAaKqwvd3giWAebZPhv6o77CF/gJAw/BFipli77o2K9z0Zyqc++8eGgN
IFFjvy4DPizIn5/UarBm29QpzSTTN/HZX07gMaSSEI3oU5/NEEy2GPewcc6zO/COrqlecGSGdGJ5
XfBHalUsFl2Gb83ZLiR5GIDPiHV3uVn+9SSYTud2YVnr3F2xSoc+TWbSozHcadrfIM7NQt0t/6X6
XYR+AJT198NIt8/HfGz8f3KCLD0nJ+7s8oP1sYr/a7RbFv+3tX2L/z/O8wentlFzBN93HMb3eFM4
C6Zjx3WGYxL/55z1Hl5YRCZuT/x/qid9/sfeZHjmhx8QB6w4/9tbm1tR/ufWJvN/W5u38t9HefLO
//fMEZTApMBJOlOgK1WlkJH97ZF2UEee3zhdM6emysxSAbNixe7NIkGx/LTW74/HnNv3aBvJfyu6
r74vYhZyMXecYrGovcS1xXOi9bjJmJFzC4Wv4I0fs3vOofMNbFVVpcPkLF3nwST0J55kiwLfF3fh
+CMfBmyFMmtJ/TOeMBVRBpVPa4iIlgjqxnctl6atrB5k1TS1qhf0LXLoO3XTWqHKnr8Lry+R3Ho5
gec4U7KRkOLPx4UoxQZHW1AepVVHOT9davX1k2U2x4UCgkJ0nLk37iJJKIclKGpr9v3+0DssRvlR
cQceiktIhnG0KKV5jSudQrBeFAk7gkRal65jSshQW8zm6wEWq3ZeVzTFqndWrWPMcxkzFTB3ssx2
cvBEookUMBHOkMAO1TS0luQ9tbME80Zn2kLJ6EgIKdp5XYsZ6WWdsl5v+oNgHAbewyltEVVSCxh1
VC0ksoVWnWQm0OQKxqWs9JsISYEoGTo1i5i2VQv6hiIvUa7r8OG6sWgl67HVYRgpPhJLmaJTznVq
rdpGd4ZXqwrmKO7xlxLZgz8VC+XIMr2yZ7gzXZq3Q2dGBlszLgdu+nzV0l58tGQc+iTjoF06uLzp
ca6+EZrjsCDoQrsvyHS3Owmfkmz7eWNeE22FLxEzAaYyTJqLjrVoTJZaKSBQAXUtgZhDZ+Kfe/Ph
Bf1mbIMOvrnnnC18QXG0V9/55vScKOqKi5G3O3HZjIVAYTbjvzTDQBpDkzzgytgMRloIGVkwRe3D
xP0TjgChGqyo5lhezIYsx1d4QDtR7OWbx4qJbKgr1VWhYqqFlWFikKP+q2SgGGyhigCTEf2lEhGW
qIYRQ4Znt9uJMgcBEC8F4wPdZ54NBR95ByRtlOokkr4ITitk4zQFgUzRv3hw/4t7T2R+kVOHEcpH
LGyrcuFI5YvKAq7Ik7rTcR43abEet8ygFTROXxkA7ynaLdFdJZarYhCO2rWjXTAGTQ45mojtSqjQ
O6czx+XpdMPAWqr5Krh54dLIZZ8IOS87nxGidhEZStwoRK1b0KRxVcDNYjoENMCL0BhH/KChnwfD
UCFWNfQyFhaEQXnJzuHQUyg8kXC6PjvVqO86ciubGxeIb1L8lNL8gXdrbroNl7bFbWhmy1vM6bDg
29f3jr/Qb3ve3D+fCr/3P73AH0wXoa8/IhQnsUv49vC/PXpY24wZN6C3kD48K730uzCWYWCMfjlR
fOBJF6FYSs91PW/uoVKkoSrZV1SqB+ObVl+rL7opuIMCxLojjO84WPh6nrMZjdtTTOXnnFS58PpW
0r19bp/b5/a5fW6f2+f2uX1un9vn9rl9bp/b5/a5fW6f2+f2uX1un9vn9rl9/sM9/w8H+8QhAEAB
AA==
