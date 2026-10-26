odoo.define('koroshi_monitor.monitor', function (require) {
'use strict';
// KOROSHI Monitor zonas: misma pantalla que estado-OUT-agrupaciones-Z-*.html, con datos en
// directo de /koroshi_monitor/datos. Se refresca sola cada REFRESCO ms. Solo lee.

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');

var REFRESCO = 60000;
var ZS = ['D1', 'D2', 'D3', 'D4', 'D5', 'ZX'];
var COL = {D1: 'var(--km-z1)', D2: 'var(--km-z2)', D3: 'var(--km-z3)', D4: 'var(--km-z4)', D5: 'var(--km-z5)', ZX: 'var(--km-zx)'};
var EST = {hecha: 'Hecha', curso: 'Cogiéndose', pend: 'Sin empezar', parcial: 'Parada (sin cerrar caja)', sinstock: 'Sin stock'};

function e(s) { return _.escape(s === undefined || s === null ? '' : String(s)); }
function n(x) { return Math.round(x).toLocaleString('es-ES'); }
function zt(z) { return '<span class="km-z" style="background:' + (COL[z] || 'var(--km-zx)') + '">' + e(z) + '</span>'; }
function hm(h) { var m = Math.round((h || 0) * 60); return Math.floor(m / 60) + ' h ' + ('0' + (m % 60)).slice(-2); }
// Personas y horas estimadas por las cajas cerradas (v1.3): sale para cualquier dia, no solo hoy
function personas(p, quien) {
    if (!p || !p.hp) { return ''; }
    return '<h2>Personas y horas</h2><p class="km-nota">Estimado por las cajas cerradas: cada cuarto de hora, cuántas ' + quien +
        ' cierran caja a la vez (huecos de hasta 30 min cuentan como trabajo). Todas las PDA usan el mismo usuario, así que no se puede saber por persona.</p>' +
        '<div class="km-grid">' + [
            [p.personas_max + (p.personas_media ? ' <small>(media ' + String(p.personas_media).replace('.', ',') + ')</small>' : ''), 'personas (máximo a la vez)'],
            [hm(p.hp), 'horas-persona'],
            [hm(p.horas_reloj), 'horas de reloj' + (p.inicio ? ' (' + e(p.inicio) + ' – ' + e(p.ultima) + ')' : '')],
            [n(p.uds_hp) + ' u/h', 'por hora-persona'],
            [n(p.uds_persona), 'uds por persona'],
            [String(p.s_ud).replace('.', ',') + ' s', 'por prenda (picking)'],
        ].map(function (k) { return '<div class="km-card km-kpi"><b>' + k[0] + '</b><span>' + k[1] + '</span></div>'; }).join('') + '</div>';
}

var Monitor = AbstractAction.extend({
    hasControlPanel: false,
    events: {
        'change .km-prefijo': '_onPrefijo',
        'click .km-refrescar': '_cargar',
        'click details > summary': '_onToggle',
    },

    init: function () {
        this._super.apply(this, arguments);
        this.prefijo = false;
        this.abiertas = {};
    },

    start: function () {
        var self = this;
        this.$el.addClass('o_koroshi_monitor');
        return this._super.apply(this, arguments).then(function () {
            self.$el.html('<main><p class="km-sub">Cargando…</p></main>');
            self._cargar();
            self.timer = setInterval(function () { self._cargar(); }, REFRESCO);
        });
    },

    destroy: function () {
        clearInterval(this.timer);
        this._super.apply(this, arguments);
    },

    _onPrefijo: function (ev) {
        this.prefijo = ev.target.value;
        this.abiertas = {};
        this._cargar();
    },

    _onToggle: function (ev) {
        // El clic en el titulo abre/cierra: se guarda como quedara para el siguiente refresco
        var det = ev.currentTarget.parentNode;
        var z = det.getAttribute('data-z');
        if (z) { this.abiertas[z] = !det.open; }
    },

    _cargar: function () {
        var self = this;
        return this._rpc({route: '/koroshi_monitor/datos', params: {prefijo: this.prefijo}}).then(function (r) {
            self.prefijo = r.prefijo;
            var scroll = self.el.scrollTop;
            self._pintar(r);
            self.el.scrollTop = scroll;
        });
    },

    _selector: function (r) {
        var et = r.etiquetas || {};
        return '<div class="km-ctl"><select class="km-prefijo">' + (r.prefijos || []).map(function (p) {
            return '<option value="' + e(p) + '"' + (p === r.prefijo ? ' selected' : '') + '>' + e(et[p] || p.replace(/-$/, '')) + '</option>';
        }).join('') + '</select><button class="btn btn-secondary km-refrescar">Refrescar</button></div>';
    },

    _pintar: function (r) {
        if (r.modo === 'tiendas') {
            return this._pintarTiendas(r);
        }
        var self = this;
        var D = r.D || [];
        var T = {u: 0, l: 0, h: 0, c: 0, p: 0};
        var Z = {};
        ZS.forEach(function (z) { Z[z] = {u: 0, l: 0, h: 0, c: 0, p: 0, uh: 0, n: 0}; });
        D.forEach(function (o) {
            if (!Z[o.z]) { Z[o.z] = {u: 0, l: 0, h: 0, c: 0, p: 0, uh: 0, n: 0}; ZS.push(o.z); }
            var z = Z[o.z], k = o.est === 'hecha' ? 'h' : (o.est === 'curso' || o.est === 'parcial') ? 'c' : 'p';
            z.n++; z.u += o.u; z.l += o.leido; z[k]++;
            if (o.est === 'hecha') { z.uh += o.u; }
            T.u += o.u; T.l += o.leido; T[k]++;
        });
        var zonas = ZS.filter(function (z) { return Z[z].n; });
        var pctT = T.u ? Math.round(100 * T.l / T.u) : 0;

        var h = '<main>';
        h += '<div class="km-cab"><h1>Cómo van las agrupaciones ' + e((r.prefijo || '').replace(/-$/, '')) + '</h1>';
        h += this._selector(r) + '</div>';
        h += '<p class="km-sub">' + r.pedidos + ' pedidos de tienda partidos por zona (' + D.length + ' OUT). Datos de Odoo a las <b>' + e(r.hora) +
            '</b>, se refresca solo cada minuto. Unidades reales (movimientos), no las columnas «Demanded/Reserved» de la lista de Odoo, que están mal en las OUT partidas.</p>';
        if (!D.length) {
            this.$el.html(h + '<p>No hay OUT en esta agrupación.</p></main>');
            return;
        }

        h += '<div class="km-grid">' + [
            [pctT + ' %', n(T.l) + ' de ' + n(T.u) + ' u leídas'],
            [T.h + ' / ' + D.length, 'OUT hechas'],
            [T.c, 'OUT cogiéndose ahora'],
            [T.p, 'OUT sin empezar'],
        ].map(function (k) { return '<div class="km-card km-kpi"><b>' + k[0] + '</b><span>' + k[1] + '</span></div>'; }).join('') + '</div>';
        h += personas(r.personas, 'zonas (una persona por zona)');

        // Totales
        h += '<h2>Totales: lo que llevan y lo que les falta</h2><div class="km-card km-scroll"><table><thead><tr><th>Zona</th><th class="r">Uds total</th><th class="r">Uds cogidas</th><th class="r">Uds que faltan</th><th class="r">%</th><th class="r">OUT total</th><th class="r">OUT hechas</th><th class="r">OUT cogiéndose</th><th class="r">OUT que faltan</th></tr></thead><tbody>';
        zonas.forEach(function (zn) {
            var z = Z[zn];
            h += '<tr><td>' + zt(zn) + '</td><td class="r">' + n(z.u) + '</td><td class="r">' + n(z.l) + '</td><td class="r"><b>' + n(z.u - z.l) + '</b></td><td class="r">' + (z.u ? Math.round(100 * z.l / z.u) : 0) + ' %</td><td class="r">' + z.n + '</td><td class="r">' + z.h + '</td><td class="r">' + z.c + '</td><td class="r"><b>' + (z.c + z.p) + '</b></td></tr>';
        });
        h += '<tr class="km-tot"><td>Total</td><td class="r">' + n(T.u) + '</td><td class="r">' + n(T.l) + '</td><td class="r">' + n(T.u - T.l) + '</td><td class="r">' + pctT + ' %</td><td class="r">' + D.length + '</td><td class="r">' + T.h + '</td><td class="r">' + T.c + '</td><td class="r">' + (T.c + T.p) + '</td></tr></tbody></table></div>';

        // Avance por zona
        h += '<h2>Avance por zona</h2><div class="km-ley"><span><i style="background:var(--km-ok)"></i>OUT hecha (validada)</span><span><i style="background:var(--km-cur)"></i>cogiéndose</span><span><i style="background:var(--km-pend)"></i>sin empezar</span></div><div class="km-card">';
        zonas.forEach(function (zn) {
            var z = Z[zn], pct = z.u ? Math.round(100 * z.l / z.u) : 0, ph = z.u ? 100 * z.uh / z.u : 0, pc = z.u ? Math.max(0, 100 * (z.l - z.uh) / z.u) : 0;
            h += '<div class="km-zona">' + zt(zn) + '<div><div class="km-fila"><span><b>' + n(z.l) + ' de ' + n(z.u) + ' u</b> (' + pct + ' %)</span><span>' + z.h + ' hechas · ' + z.c + ' cogiéndose · ' + z.p + ' sin empezar (de ' + z.n + ' OUT)</span></div>' +
                '<div class="km-barra"><i style="width:' + ph + '%;background:var(--km-ok)"></i><i style="width:' + pc + '%;background:var(--km-cur)"></i></div></div></div>';
        });
        h += '</div>';

        // Matriz tienda x zona
        var P = {}, orden = [];
        D.forEach(function (o) {
            if (!P[o.pedido]) { P[o.pedido] = {caja: o.caja, tienda: o.tienda, z: {}}; orden.push(o.pedido); }
            P[o.pedido].z[o.z] = o;
        });
        orden.sort(function (a, b) { return (parseInt(P[a].caja, 10) || 0) - (parseInt(P[b].caja, 10) || 0); });
        h += '<h2>Cada tienda en cada zona</h2><p class="km-nota">Cada casilla es una OUT: número de OUT y unidades leídas / total. Vacío = la tienda no tiene nada en esa zona.</p>';
        h += '<div class="km-card km-scroll"><table><thead><tr><th>Caja</th><th>Tienda</th><th>Pedido</th>' + zonas.map(function (z) { return '<th>' + zt(z) + '</th>'; }).join('') + '<th class="r">Leído</th></tr></thead><tbody>';
        orden.forEach(function (k) {
            var p = P[k], u = 0, l = 0;
            h += '<tr><td><b>' + e(p.caja) + '</b></td><td>' + e(p.tienda) + '</td><td class="m">' + e(k) + '</td>';
            zonas.forEach(function (z) {
                var o = p.z[z];
                if (!o) { h += '<td></td>'; return; }
                u += o.u; l += o.leido;
                h += '<td><span class="km-cel km-' + o.est + '" title="' + EST[o.est] + '">' + e(o.out) + '<br>' + n(o.leido) + '/' + n(o.u) + '</span></td>';
            });
            h += '<td class="r">' + n(l) + '/' + n(u) + '</td></tr>';
        });
        h += '</tbody></table></div>';

        // Listas por zona
        h += '<h2>OUT por zona</h2>';
        var rank = {curso: 0, pend: 1, hecha: 2};
        zonas.forEach(function (zn) {
            var L = D.filter(function (o) { return o.z === zn; });
            L.sort(function (a, b) { return rank[a.est] - rank[b.est] || (parseInt(a.caja, 10) || 0) - (parseInt(b.caja, 10) || 0); });
            var z = Z[zn];
            var abierta = zn in self.abiertas ? self.abiertas[zn] : (z.c || z.p);
            h += '<div class="km-card"><details data-z="' + e(zn) + '"' + (abierta ? ' open' : '') + '><summary>' + zt(zn) + ' ' + e(r.prefijo + zn) + ' · ' + n(z.l) + '/' + n(z.u) + ' u · ' + z.h + ' hechas, ' + z.c + ' cogiéndose, ' + z.p + ' sin empezar</summary>';
            h += '<div class="km-scroll"><table><thead><tr><th>Estado</th><th>Caja</th><th>OUT</th><th>Tienda</th><th>Pedido</th><th>Lineales</th><th class="r">Huecos</th><th>Leído</th><th>Empieza</th><th>Última / validada</th></tr></thead><tbody>';
            L.forEach(function (o) {
                var pct = o.u ? 100 * o.leido / o.u : 0, c = o.est === 'hecha' ? 'var(--km-ok)' : 'var(--km-cur)';
                h += '<tr><td><span class="km-cel km-' + o.est + '">' + EST[o.est] + '</span></td><td><b>' + e(o.caja) + '</b></td><td class="m">' + e(o.out) + '</td><td>' + e(o.tienda) + '</td><td class="m">' + e(o.pedido) + '</td><td>' + e(o.lin) + '</td><td class="r">' + o.huecos + '</td>' +
                    '<td><span class="km-mini"><i style="width:' + pct + '%;background:' + c + '"></i></span>' + n(o.leido) + '/' + n(o.u) + '</td><td>' + (o.est === 'hecha' ? '' : e(o.ini)) + '</td><td>' + e(o.fin) + '</td></tr>';
            });
            h += '</tbody></table></div></details></div>';
        });
        h += '</main>';
        this.$el.html(h);
    },
});

// Modo tiendas (v1.1): una OUT por pedido, sin zonas. Ritmo del equipo, hora prevista de fin,
// uds por hora y cada OUT con lo que ha tardado.
// v1.7: franja grande arriba (% hecho, hora de fin, uds que quedan); filas con color segun el estado;
// "Sin empezar" y "Hechas" plegadas; modo pantalla (TV, pantalla vertical del almacen): sin el menu de
// Odoo, letra grande y solo lo que se esta cogiendo. El modo pantalla se queda guardado en ese navegador.
var TV_KEY = 'koroshi_monitor_tv';

function kno(tienda) { return (tienda || '').split(' - ')[0]; }
function knum(tienda) { return parseInt(kno(tienda).replace(/\D/g, ''), 10) || 999; }

Monitor.include({
    events: _.extend({}, Monitor.prototype.events, {
        'click .km-tv-btn': '_onTv',
    }),

    start: function () {
        try { this.tv = window.localStorage.getItem(TV_KEY) === '1'; } catch (err) { this.tv = false; }
        $('body').toggleClass('km-tv', !!this.tv);
        return this._super.apply(this, arguments);
    },

    destroy: function () {
        $('body').removeClass('km-tv');
        this._super.apply(this, arguments);
    },

    _onTv: function () {
        this.tv = !this.tv;
        try { window.localStorage.setItem(TV_KEY, this.tv ? '1' : '0'); } catch (err) { /* sin almacenamiento: solo esta vez */ }
        $('body').toggleClass('km-tv', this.tv);
        this._cargar();
    },

    // Tabla de OUT (v1.7: fila con el color de su estado; en pantalla, menos columnas y mas grandes)
    _tablaOut: function (lista) {
        var tv = this.tv;
        var COLE = {hecha: 'var(--km-ok)', parcial: 'var(--km-par)'};
        var h = '<div class="km-scroll"><table class="km-out"><thead><tr><th>Estado</th><th>Tienda</th>' +
            (tv ? '' : '<th>Pedido</th>') + '<th>OUT</th><th>Leído</th>' +
            (tv ? '<th class="r">Última caja</th>' : '<th class="r">Cajas</th><th class="r">Huecos</th><th>Lineales</th><th>1ª caja</th><th>Última caja / validada</th><th class="r">Hace</th><th class="r">Min</th><th class="r">u/h</th>') +
            '</tr></thead><tbody>';
        lista.forEach(function (o) {
            var base = o.est === 'hecha' ? o.leido : o.disp;
            var p = base ? 100 * o.leido / base : 0, c = COLE[o.est] || 'var(--km-cur)';
            var cls = 'km-r-' + o.est + (o.parada ? ' km-parada' : '');
            var hace = o.hace === '' ? '' : 'hace ' + o.hace + ' min';
            // v1.8: hecha sin validar = ya cogido todo lo que hay; lo que falta (sin stock) debajo
            var sv = o.sin_validar ? '<br><small>sin validar' + (o.falta ? ' · faltan ' + n(o.falta) : '') + '</small>' : '';
            h += '<tr class="' + cls + '"><td><span class="km-cel km-' + o.est + '">' + EST[o.est] + '</span>' + sv + '</td><td>' + e(o.tienda) + '</td>' +
                (tv ? '' : '<td class="m">' + e(o.pedido) + '</td>') + '<td class="m">' + e(o.out) +
                (o.lote && !tv ? '<br><small>' + e(o.lote) + '</small>' : '') + '</td>' +
                '<td><span class="km-mini"><i style="width:' + p + '%;background:' + c + '"></i></span>' + n(o.leido) + '/' + n(base) + '</td>' +
                (tv ? '<td class="r">' + hace + '</td>' :
                    '<td class="r">' + (o.cajas || '') + '</td><td class="r">' + o.huecos + '</td><td>' + e(o.lin) +
                    '</td><td>' + e(o.ini) + '</td><td>' + e(o.fin) + '</td><td class="r">' + (o.hace === '' ? '' : o.hace + ' min') +
                    '</td><td class="r">' + (o.min || '') + '</td><td class="r">' + (o.uh || '') + '</td>') +
                '</tr>';
        });
        return h + '</tbody></table></div>';
    },

    // Bloque plegable (se acuerda de si estaba abierto entre refrescos)
    _plegable: function (clave, titulo, cuerpo) {
        return '<details data-z="' + clave + '"' + (this.abiertas[clave] ? ' open' : '') + '><summary>' + titulo + '</summary>' + cuerpo + '</details>';
    },

    _pintarTiendas: function (r) {
        var tv = this.tv;
        var D = r.D || [];
        var eq = r.equipo || {};
        // v1.4: el avance es sobre lo que se puede coger (disp = reservado + cogido); lo que falta sin stock va aparte
        var T = {u: 0, l: 0, hecha: 0, curso: 0, parcial: 0, pend: 0, sinstock: 0, upend: 0};
        D.forEach(function (o) {
            T.u += (o.est === 'hecha' ? o.leido : o.disp); T.l += o.leido;
            T[o.est]++;
            if (o.est === 'pend') { T.upend += o.disp; }
        });
        var pct = T.u ? Math.round(100 * T.l / T.u) : 0;
        var quedan = Math.max(T.u - T.l, 0);
        var paradas = D.filter(function (o) { return o.parada; });
        var et = r.etiquetas || {};
        var h = '<main' + (tv ? ' class="km-tvmain"' : '') + '>';
        h += '<div class="km-cab"><h1>' + (tv ? 'Pedidos de tienda · ' : 'Cómo van los pedidos de tienda · ') +
            e((et[r.prefijo] || '').replace('Tiendas ', '')) + '</h1>' +
            (tv ? '<div class="km-ctl"><span class="km-nota">Datos de las ' + e(r.hora) + '</span><button class="btn btn-secondary km-tv-btn">Salir de pantalla</button></div>' :
                this._selector(r).replace(/<\/div>$/, '<button class="btn btn-secondary km-tv-btn">Modo pantalla</button></div>')) + '</div>';
        if (!tv) {
            h += '<p class="km-sub">' + r.pedidos + ' pedidos de tienda (' + D.length + ' OUT), una OUT por pedido. Datos de Odoo a las <b>' + e(r.hora) +
                '</b>, se refresca solo cada minuto. El ritmo es del equipo entero (todas las PDA usan el mismo usuario).' +
                (r.sin_stock ? ' No salen ' + r.sin_stock + ' pedidos pendientes en espera (lo que faltaba al validar, sin stock): no son trabajo de hoy.' : '') + '</p>';
        }
        if (!D.length) {
            this.$el.html(h + '<p>No hay OUT de tiendas ese día.</p></main>');
            return;
        }

        // 1. Franja grande: % hecho, hora de fin y uds que quedan
        var hecho = T.u && T.l >= T.u;
        var fin = eq.fin_previsto ? e(eq.fin_previsto) : (hecho ? 'Hecho' : (eq.ultima ? e(eq.ultima) : '–'));
        var finTxt = eq.fin_previsto ? 'acaba a este ritmo' : (hecho ? 'todo cogido' : 'última lectura');
        h += '<div class="km-card km-hero"><div class="km-hero-top"><div class="km-hero-pct">' + pct + '<small> %</small></div>' +
            '<div class="km-hero-dato"><b>' + fin + '</b><span>' + finTxt + '</span></div>' +
            '<div class="km-hero-dato"><b>' + n(quedan) + '</b><span>uds por coger</span></div></div>' +
            '<div class="km-hero-barra"><i style="width:' + pct + '%"></i></div>' +
            '<div class="km-hero-pie">' + n(T.l) + ' de ' + n(T.u) + ' u cogidas · <b>' + n(eq.uh || 0) + ' u/h</b>' +
            (eq.inicio ? ' desde las ' + e(eq.inicio) : '') + ' · <b>' + (eq.activas || 0) + '</b> cogiendo ahora · OUT: <b>' + T.hecha + '</b> hechas, <b>' +
            (T.curso + T.parcial) + '</b> en marcha, <b>' + T.pend + '</b> sin empezar</div></div>';

        if (paradas.length) {
            h += '<div class="km-card km-aviso"><b>' + paradas.length + ' OUT hechas sin validar (sin cerrar caja hace más de ' + (eq.parada_min || 20) + ' min):</b> ' +
                paradas.map(function (o) { return e(o.out) + ' ' + e(o.tienda) + ' (' + o.hace + ' min, faltan ' + n(o.falta) + ')'; }).join(' · ') +
                '. Se dan por hechas: les faltan prendas (sin stock o no encontradas). Validarlas en Odoo.' +
                (tv ? '' : ' Detalle en KOROSHI KPI › Faltas por día.') + '</div>';
        }

        if (!tv) {
            h += '<div class="km-grid">' + [
                [eq.activas || 0, 'personas cogiendo ahora (caja cerrada en los últimos ' + (eq.parada_min || 20) + ' min)' +
                    (eq.activas && eq.uh ? ' · ~' + n(eq.uh / eq.activas) + ' u/h por persona' : '')],
                [n(eq.cajas || 0), 'cajas cerradas' + (eq.cajas ? ' · ' + (T.l / eq.cajas).toFixed(1).replace('.', ',') + ' u por caja' : '')],
                [D.filter(function (o) { return o.sin_validar; }).length, 'hechas sin validar (con faltas de stock)'],
            ].map(function (k) { return '<div class="km-card km-kpi"><b>' + k[0] + '</b><span>' + k[1] + '</span></div>'; }).join('') + '</div>';
        }

        // 2-3. Lo que se esta cogiendo a la vista; sin empezar y hechas plegadas
        var marcha = D.filter(function (o) { return o.est === 'curso' || o.est === 'parcial'; });
        var pend = D.filter(function (o) { return o.est === 'pend'; });
        var hechas = D.filter(function (o) { return o.est === 'hecha'; });
        var porK = function (a, b) { return knum(a.tienda) - knum(b.tienda); };
        pend.sort(porK);
        hechas.sort(porK);

        h += '<h2>Cogiéndose ahora (' + marcha.length + ')</h2>';
        h += '<div class="km-card">' + (marcha.length ? this._tablaOut(marcha) : '<p class="km-nota">Ahora no se está cogiendo ninguna OUT.</p>') + '</div>';

        h += '<h2>Sin empezar (' + pend.length + ' OUT · ' + n(T.upend) + ' u)</h2><div class="km-card">';
        if (pend.length) {
            h += '<div class="km-chips">' + pend.map(function (o) {
                return '<span class="km-chip" title="' + e(o.tienda) + ' · ' + e(o.out) + '"><b>' + e(kno(o.tienda)) + '</b> ' + n(o.disp) + ' u</span>';
            }).join('') + '</div>';
            if (!tv) { h += this._plegable('pend', 'Ver la lista', this._tablaOut(pend)); }
        } else {
            h += '<p class="km-nota">No queda ninguna OUT por empezar.</p>';
        }
        h += '</div>';

        h += '<h2>Hechas (' + hechas.length + ')</h2>';
        if (hechas.length) {
            h += '<div class="km-card">' + (tv ? '<div class="km-chips">' + hechas.map(function (o) {
                return '<span class="km-chip km-chip-ok"><b>' + e(kno(o.tienda)) + '</b></span>';
            }).join('') + '</div>' : this._plegable('hecha', 'Ver las ' + hechas.length + ' OUT hechas', this._tablaOut(hechas))) + '</div>';
        }

        if (!tv) {
            h += personas(r.personas, 'OUT');
            // Uds leidas por hora
            var ph = r.por_hora || [];
            var max = 1;
            ph.forEach(function (x) { if (x[1] > max) { max = x[1]; } });
            h += '<h2>Unidades leídas por hora</h2><div class="km-card">';
            if (!ph.length) {
                h += '<p class="km-nota">Todavía no hay lecturas.</p>';
            }
            ph.forEach(function (x) {
                h += '<div class="km-hora"><span>' + (x[0] < 10 ? '0' : '') + x[0] + 'h</span><span class="km-barra"><i style="width:' + (100 * x[1] / max) +
                    '%;background:var(--km-cur)"></i></span><b>' + n(x[1]) + '</b></div>';
            });
            h += '</div>';
            h += '<p class="km-nota">Odoo solo guarda la hora de cada caja cerrada (matrícula CJ): «1ª caja» y «Última caja / validada» son esas horas. ' +
                '«Min» = lo que ha tardado la OUT, estimado a partir de sus cajas (hace falta 2 o más). ' +
                'Lo que falta (sin stock o no cogido) está en <b>KOROSHI KPI › Faltas por día</b>.</p>';
        }
        h += '</main>';
        this.$el.html(h);
    },
});

core.action_registry.add('koroshi_monitor', Monitor);
return Monitor;
});
