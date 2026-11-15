# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI KPI v1.8.0 (15/11/2026, auditoria 13/11 fase 7): previsión de cajas por volumen.
# Python puro (sin Odoo), con tests en tests/test_prevision.py.
#
# Cajas previstas = volumen ÷ m³ por caja × factor.
#   - m³ por caja: 0,084 (mediana de las cajas llenas medida el 06/11; la caja 60x40x33 es 0,079).
#   - factor: corrige la última caja de cada OUT (no va llena) y lo que no cuadra. Se calibra solo con los días
#     anteriores de la ficha (cajas reales ÷ (volumen ÷ m³ por caja)): del 20/10 al 13/11, mediana 1,07.
# =============================================================================

M3_CAJA = 0.084
FACTOR_DEFECTO = 1.07
DIAS_MINIMO = 5             # con menos días calibrados se usa FACTOR_DEFECTO
CAJAS_MINIMO_DIA = 50       # los días muy pequeños no calibran (pesa demasiado la última caja de cada OUT)


def mediana(valores):
    v = sorted(valores)
    n = len(v)
    if not n:
        return None
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2.0


def factor_calibrado(dias, m3_caja=M3_CAJA, minimo_dias=DIAS_MINIMO, minimo_cajas=CAJAS_MINIMO_DIA):
    """dias: [(volumen_m3, cajas_reales)]. Devuelve (factor, días usados). Sin días suficientes, FACTOR_DEFECTO."""
    ratios = []
    for vol, cajas in dias:
        if vol and vol > 0 and cajas and cajas >= minimo_cajas:
            ratios.append(float(cajas) / (vol / m3_caja))
    if len(ratios) < minimo_dias:
        return FACTOR_DEFECTO, len(ratios)
    return round(mediana(ratios), 3), len(ratios)


def cajas_previstas(volumen, factor, m3_caja=M3_CAJA):
    """Cajas para este volumen (m³). 0 si no hay volumen."""
    if not volumen or volumen <= 0 or m3_caja <= 0:
        return 0
    return int(round(volumen / m3_caja * factor))


def desvio(reales, previstas):
    """% que se ha desviado lo real de lo previsto (+ = han salido más cajas). None si no hay previsión."""
    if not previstas:
        return None
    return round((float(reales) - previstas) / previstas * 100.0, 1)
