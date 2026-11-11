# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Lecturas PDA como app (v1.0.0, 11/11/2026).
#
# Tres rutas sin datos de Odoo, solo para que Chrome deje instalar Lecturas como una app (icono en la pantalla de
# inicio, sin barra de direcciones):
#   /koroshi_pda/manifest.webmanifest  el manifiesto de la app (nombre, icono, pantalla completa, inicio)
#   /koroshi_pda/sw.js                 service worker mínimo: no guarda nada en caché, todo va a Odoo como siempre
#   /koroshi_pda/inicio                donde abre la app: con sesión -> Lecturas; sin sesión -> login y, al entrar,
#                                      vuelta aquí -> Lecturas
# No lee ni escribe nada en la base de datos.
# =============================================================================
import json

import werkzeug.urls
import werkzeug.utils

from odoo import http
from odoo.http import request

COMPANY_ID = 8                                          # EFFECTIVE LOGISTICS, S.L.
LECTURAS = '/web#cids=%s&action=koroshi_operarios_pantalla' % COMPANY_ID
INICIO = '/koroshi_pda/inicio'
COLOR = '#14243b'                                       # el fondo de la pantalla «Lee tu tarjeta»

SW = u"""// KOROSHI Lecturas PDA: service worker mínimo, solo para que Chrome deje instalar la app.
// No guarda nada en caché: todas las peticiones van a Odoo como siempre.
self.addEventListener('install', function () { self.skipWaiting(); });
self.addEventListener('activate', function (e) { e.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', function () { /* nada: la red de siempre */ });
"""


class KoroshiPdaApp(http.Controller):

    @http.route('/koroshi_pda/manifest.webmanifest', type='http', auth='none', methods=['GET'], sitemap=False)
    def manifest(self, **kw):
        icono = '/koroshi_pda_app/static/img/icon-%s.png'
        datos = {
            'id': INICIO,
            'name': 'Lecturas KOROSHI',
            'short_name': 'Lecturas',
            'description': 'Lecturas (PDA) de KOROSHI: tarjeta, pedidos y preparación.',
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

    @http.route('/koroshi_pda/sw.js', type='http', auth='none', methods=['GET'], sitemap=False)
    def service_worker(self, **kw):
        return request.make_response(SW, headers=[
            ('Content-Type', 'application/javascript; charset=utf-8'),
            ('Service-Worker-Allowed', '/'),       # registrado con scope '/': la app es todo Odoo
            ('Cache-Control', 'no-cache'),
        ])

    @http.route(INICIO, type='http', auth='none', methods=['GET'], sitemap=False)
    def inicio(self, **kw):
        if request.session.uid:
            return werkzeug.utils.redirect(LECTURAS, 303)
        return werkzeug.utils.redirect('/web/login?' + werkzeug.urls.url_encode({'redirect': INICIO}), 303)
