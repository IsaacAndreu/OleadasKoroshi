# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Operarios - utilidades del antiguo informe diario por email.
#
# v2.12 (14/11/2026, auditoria 13/11 fase 2): el correo diario de las 17:00 de este modulo se ha quitado (cron,
# accion y menu «Enviar informe de hoy ahora»): llegaban dos correos con cifras distintas. El correo que queda es el
# de koroshi_informe, con la misma cifra (koroshi.operario.tarea.resumen_operario_dia).
# Aqui solo quedan codigo_corto() y hm(), que importa koroshi_informe. Los parametros koroshi_operarios.informe_*
# se quedan en la base (no molestan).
# =============================================================================
from odoo import models

from .tarea import codigo_corto, RE_OP  # noqa: F401  (koroshi_informe los importa de aqui)


def hm(minutos):
    m = int(round(minutos or 0))
    return '%d:%02d' % (m // 60, m % 60)


class KoroshiOperarioInforme(models.AbstractModel):
    _name = 'koroshi.operario.informe'
    _description = 'KOROSHI Operarios: informe diario (v2.12: sin correo, lo manda koroshi_informe)'
