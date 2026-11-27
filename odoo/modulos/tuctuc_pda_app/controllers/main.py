# -*- coding: utf-8 -*-
# =============================================================================
# TUCTUC Lecturas PDA como app. Clon de koroshi_pda_app 1.2.0 para odoo.tuctuc.com (nave de Oriola - Amposta).
#
# Tres rutas, solo para que Chrome deje instalar Lecturas como una app (icono en la pantalla de inicio, sin barra de
# direcciones):
#   /tuctuc_pda/manifest.webmanifest  el manifiesto de la app (nombre, icono, pantalla completa, inicio)
#   /tuctuc_pda/sw.js                 service worker mínimo: no guarda nada en caché, todo va a Odoo como siempre
#   /tuctuc_pda/inicio                donde abre la app: con sesión -> Lecturas; sin sesión -> login y, al entrar,
#                                     vuelta aquí -> Lecturas
# Diferencia con koroshi_pda_app: no hay compañía fija (allí cids=8). Lecturas se abre con TODAS las compañías de la
# PDA que tenga el usuario (las de tuctuc.almacen: PRIME, MODA INTIMA, UNITED), para que la app de código de barras
# vea los albaranes de las tres. Sin el Inicio por áreas (koroshi_actividades no se clona).
# No escribe nada en la base de datos.
# =============================================================================
import json

import werkzeug.urls
import werkzeug.utils

from odoo import http
from odoo.http import request

ACCION = 'tuctuc_operarios_pantalla'
INICIO = '/tuctuc_pda/inicio'
COLOR = '#14243b'                                       # el fondo de la pantalla «Lee tu tarjeta»

SW = u"""// TUCTUC Lecturas PDA: service worker mínimo, solo para que Chrome deje instalar la app.
// No guarda nada en caché: todas las peticiones van a Odoo como siempre.
self.addEventListener('install', function () { self.skipWaiting(); });
self.addEventListener('activate', function (e) { e.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', function () { /* nada: la red de siempre */ });
"""


def cids_de(usuario):
    """Compañías con las que se abre Lecturas: las de la PDA (tuctuc.almacen, en su orden) que tiene el usuario y,
    si no tiene ninguna, su compañía actual. Lista de ids."""
    pda = usuario.env['tuctuc.almacen'].companias()
    ids = [c.id for c in pda if c in usuario.company_ids]
    return ids or [usuario.company_id.id]


class TuctucPdaApp(http.Controller):

    def _destino(self):
        usuario = request.env['res.users'].sudo().browse(request.session.uid)
        return '/web#cids=%s&action=%s' % (','.join(str(i) for i in cids_de(usuario)), ACCION)

    @http.route('/tuctuc_pda/manifest.webmanifest', type='http', auth='none', methods=['GET'], sitemap=False)
    def manifest(self, **kw):
        icono = '/tuctuc_pda_app/static/img/icon-%s.png'
        datos = {
            'id': INICIO,
            'name': 'Lecturas Oriola',
            'short_name': 'Lecturas',
            'description': 'Lecturas (PDA) de la nave de Oriola - Amposta: tarjeta, pedidos y preparación.',
            'start_url': INICIO,
            'scope': '/',
            'display': 'standalone',
            'orientation': 'portrait',
            'background_color': COLOR,
            'theme_color': COLOR,
            'lang': 'es',
            'icons': [
                {'src': icono % 192, 'sizes': '192x192', 'type': 'image/png', 'purpose': 'any maskable'},
                {'src': icono % 512, 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any maskable'},
            ],
        }
        return request.make_response(json.dumps(datos, ensure_ascii=False), headers=[
            ('Content-Type', 'application/manifest+json; charset=utf-8'),
            ('Cache-Control', 'public, max-age=3600'),
        ])

    @http.route('/tuctuc_pda/sw.js', type='http', auth='none', methods=['GET'], sitemap=False)
    def service_worker(self, **kw):
        return request.make_response(SW, headers=[
            ('Content-Type', 'application/javascript; charset=utf-8'),
            ('Service-Worker-Allowed', '/'),       # registrado con scope '/': la app es todo Odoo
            ('Cache-Control', 'no-cache'),
        ])

    @http.route(INICIO, type='http', auth='none', methods=['GET'], sitemap=False)
    def inicio(self, **kw):
        if request.session.uid:
            return werkzeug.utils.redirect(self._destino(), 303)
        return werkzeug.utils.redirect('/web/login?' + werkzeug.urls.url_encode({'redirect': INICIO}), 303)
