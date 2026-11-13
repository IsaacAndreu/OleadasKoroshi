# -*- coding: utf-8 -*-
# KOROSHI Informe: ver el correo en el navegador sin mandarlo (/koroshi/informe/ver?tipo=diario|semanal|mensual).
# Solo para el grupo «KOROSHI Operarios: ver productividad». El diario de hoy recalcula antes la ficha KPI y las faltas
# del dia (lo mismo que se hace al mandarlo); con recalcular=0 no.
import datetime

from odoo import http
from odoo.http import request

from ..models.informe import esc


class KoroshiInformeController(http.Controller):

    @http.route('/koroshi/informe/ver', type='http', auth='user')
    def ver(self, tipo='diario', dia=None, recalcular=None, **kw):
        if not request.env.user.has_group('koroshi_operarios.grupo_productividad'):
            return request.not_found()
        Informe = request.env['koroshi.informe']
        try:
            fecha = dia and datetime.datetime.strptime(dia, '%Y-%m-%d').date() or Informe._hoy()
        except ValueError:
            fecha = Informe._hoy()
        if tipo not in ('diario', 'semanal', 'mensual'):
            tipo = 'diario'
        if recalcular is None:
            recalc = tipo == 'diario' and fecha == Informe._hoy()
        else:
            recalc = recalcular == '1'
        asunto, cuerpo = Informe.componer(tipo, fecha, recalcular=recalc)
        pagina = ('<!doctype html><html lang="es"><head><meta charset="utf-8">'
                  '<meta name="viewport" content="width=device-width,initial-scale=1"><title>%s</title></head>'
                  '<body style="margin:0;background:#f4f4f4"><div style="max-width:760px;margin:0 auto;background:#fff;'
                  'padding:16px 20px"><p style="font-family:Arial,sans-serif;font-size:12px;color:#666;margin:0 0 10px">'
                  'Vista previa (no se ha mandado). Asunto: <b>%s</b></p>%s</div></body></html>') % (
                      esc(asunto), esc(asunto), cuerpo)
        return request.make_response(pagina, headers=[('Content-Type', 'text/html; charset=utf-8')])
