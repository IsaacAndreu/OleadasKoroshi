odoo.define('oriola_monitor.monitor', function (require) {
'use strict';
// Monitor picking Oriola: datos de /oriola_monitor/datos. Se refresca sola cada REFRESCO ms, pero solo
// si la pestana se esta viendo (este Odoo es lento: no pedir nada que nadie mira). Solo lee.

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');

var REFRESCO = 120000;

function e(s) { return _.escape(s === undefined || s === null ? '' : String(s)); }
function n(x) { return Math.round(x || 0).toLocaleString('es-ES'); }
function hm(h) { var m = Math.round((h || 0) * 60); return Math.floor(m / 60) + ' h ' + ('0' + (m % 60)).slice(-2); }
function fecha(d) { var p = d.split('-'); return p[2] + '/' + p[1]; }
var SEMANA = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb'];
function diaTxt(d, i) {
    if (i === 0) { return 'Hoy ' + fecha(d); }
    if (i === 1) { return 'Ayer ' + fecha(d); }
    var p = d.split('-');
    return SEMANA[new Date(+p[0], +p[1] - 1, +p[2]).getDay()] + ' ' + fecha(d);
}
function kpi(v, t) { return '<div class="om-card om-kpi"><b>' + v + '</b><span>' + t + '</span></div>'; }

var Monitor = AbstractAction.extend({
    hasControlPanel: false,
    events: {
        'change .om-dia': '_onDia',
        'click .om-refrescar': '_onRefrescar',
    },

    init: function () {
        this._super.apply(this, arguments);
        this.dia = false;
        this.cargando = false;
    },

    start: function () {
        var self = this;
        this.$el.addClass('o_oriola_monitor');
        return this._super.apply(this, arguments).then(function () {
            self.$el.html('<main><p class="om-sub">Cargando…</p></main>');
            self._cargar();
            self.timer = setInterval(function () {
                if (!document.hidden) { self._cargar(); }
            }, REFRESCO);
        });
    },

    destroy: function () {
        clearInterval(this.timer);
        this._super.apply(this, arguments);
    },

    _onDia: function (ev) {
        this.dia = ev.target.value;
        this._cargar();
    },

    _onRefrescar: function () {
        this._cargar(true);
    },

    _cargar: function (refrescar) {
        var self = this;
        if (this.cargando) { return; }      // nunca dos peticiones a la vez desde la misma pantalla
        this.cargando = true;
        return this._rpc({route: '/oriola_monitor/datos', params: {dia: this.dia, refrescar: !!refrescar}}).then(function (r) {
            self.cargando = false;
            var scroll = self.el.scrollTop;
            self._pintar(r);
            self.el.scrollTop = scroll;
        }, function () {
            self.cargando = false;
        });
    },

    _pintar: function (r) {
        if (r.error) {
            this.$el.html('<main><h1>Monitor picking</h1><div class="om-card om-error">' + e(r.error) + '</div></main>');
            return;
        }
        this.dia = r.dia;
        var R = r.resumen;
        var h = '<main><div class="om-cab"><h1>Monitor picking · Oriola</h1><div class="om-ctl"><select class="om-dia">' +
            r.dias.map(function (d, i) {
                return '<option value="' + d + '"' + (d === r.dia ? ' selected' : '') + '>' + diaTxt(d, i) + '</option>';
            }).join('') + '</select><button class="btn btn-secondary om-refrescar">Refrescar</button></div></div>' +
            '<p class="om-sub">' + e(r.tipo) + ' · datos de las ' + e(r.calculado) + ' (tardó ' + String(r.segundos).replace('.', ',') +
            ' s)' + (r.es_hoy ? ' · se actualiza cada 2 min si la pestaña está a la vista' : '') + '</p>';

        h += '<div class="om-grid">' +
            kpi(n(R.validadas), 'OUT validadas') +
            kpi(n(R.uds_validadas), 'uds servidas (OUT validadas)') +
            kpi(n(R.cajas), 'cajas cerradas') +
            kpi(n(R.uds_leidas) + (R.uds_auto ? ' <small>' + n(R.uds_auto) + ' automático</small>' : ''), 'uds leídas') +
            kpi(R.personas + (r.es_hoy ? ' <small>' + R.activas + ' ahora</small>' : ''), 'personas leyendo') +
            kpi(n(R.uds_hora_persona), 'uds por hora-persona (' + hm(R.horas_personas) + ')') +
            (r.es_hoy ? kpi(n(R.listas) + ' <small>' + n(R.uds_listas) + ' uds</small>', 'OUT listas para coger') +
                kpi(n(R.espera) + ' <small>' + n(R.uds_espera) + ' uds</small>', 'OUT en espera (sin stock)') : '') +
            '</div>';

        h += this._personas(r);
        h += this._porHora(r);
        h += this._canales(r);
        if (r.es_hoy) {
            h += this._lotes(r);
        }
        h += '<p class="om-nota" style="margin-top:24px">Uds leídas: líneas con cantidad hecha escritas ese día en las OUT de salida, por el usuario que las escribió. ' +
            'Horas activas: cuartos de hora con lecturas, más los huecos de hasta 30 min entre ellos. Solo lee: no cambia nada en Odoo.</p></main>';
        this.$el.html(h);
    },

    _personas: function (r) {
        var filas = function (L, auto) {
            var T = {uds: 0, lineas: 0, val: 0, uv: 0, cajas: 0, horas: 0};
            var b = L.map(function (p) {
                T.uds += p.uds; T.lineas += p.lineas; T.val += p.validadas; T.uv += p.uds_validadas; T.cajas += p.cajas; T.horas += p.horas;
                return '<tr' + (p.activo ? ' class="om-activo"' : '') + '><td>' + (r.es_hoy && !auto ? '<span class="om-punto' + (p.activo ? '' : ' off') + '"></span>' : '') +
                    e(p.nombre) + '</td><td class="r"><b>' + n(p.uds) + '</b></td><td class="r">' + n(p.lineas) + '</td><td class="r">' + n(p.out_leidas) +
                    '</td><td class="r">' + n(p.validadas) + '</td><td class="r">' + n(p.uds_validadas) + '</td><td class="r">' + n(p.cajas) +
                    '</td><td>' + e(p.primera) + '</td><td>' + e(p.ultima) + '</td><td class="r">' + (auto ? '' : hm(p.horas)) +
                    '</td><td class="r">' + (auto ? '' : n(p.uds_hora)) + '</td></tr>';
            }).join('');
            if (L.length > 1) {
                b += '<tr class="om-tot"><td>Total</td><td class="r">' + n(T.uds) + '</td><td class="r">' + n(T.lineas) + '</td><td></td><td class="r">' + n(T.val) +
                    '</td><td class="r">' + n(T.uv) + '</td><td class="r">' + n(T.cajas) + '</td><td></td><td></td><td class="r">' + (auto ? '' : hm(T.horas)) +
                    '</td><td class="r">' + (auto || !T.horas ? '' : n(T.uds / T.horas)) + '</td></tr>';
            }
            return b;
        };
        var cab = '<tr><th></th><th class="r">Uds leídas</th><th class="r">Líneas</th><th class="r">OUT tocadas</th><th class="r">OUT validadas</th>' +
            '<th class="r">Uds validadas</th><th class="r">Cajas</th><th>Primera</th><th>Última</th><th class="r">Horas activas</th><th class="r">Uds/hora</th></tr>';
        var h = '<h2>Por persona</h2>';
        if (!r.personas.length) {
            h += '<div class="om-card om-nota">Nadie ha leído nada ' + (r.es_hoy ? 'todavía hoy' : 'ese día') + '.</div>';
        } else {
            h += '<div class="om-card"><table>' + cab + filas(r.personas, false) + '</table>' +
                (r.es_hoy ? '<p class="om-nota" style="margin:8px 0 0"><span class="om-punto"></span>ha leído en los últimos 15 min</p>' : '') + '</div>';
        }
        if (r.automaticos.length) {
            h += '<h2>Almacén automático y sistema</h2><div class="om-card"><table>' + cab + filas(r.automaticos, true) + '</table></div>';
        }
        return h;
    },

    _porHora: function (r) {
        var H = r.por_hora;
        if (!H.length) { return ''; }
        var mx = Math.max.apply(null, H.map(function (x) { return x.personas + x.auto; })) || 1;
        return '<h2>Uds leídas por hora</h2><div class="om-card"><div class="om-ley"><span><i style="background:var(--om-per)"></i>Personas</span>' +
            '<span><i style="background:var(--om-auto)"></i>Automático y sistema</span></div>' +
            H.map(function (x) {
                return '<div class="om-hora"><span>' + ('0' + x.h).slice(-2) + ':00</span><div class="om-barra"><i style="width:' + (100 * x.personas / mx) +
                    '%;background:var(--om-per)"></i><i style="width:' + (100 * x.auto / mx) + '%;background:var(--om-auto)"></i></div><b>' +
                    n(x.personas + x.auto) + '</b></div>';
            }).join('') + '</div>';
    },

    _canales: function (r) {
        if (!r.canales.length) { return ''; }
        var hoy = r.es_hoy;
        return '<h2>' + (hoy ? 'Por canal: hecho hoy y pendiente ahora' : 'Por canal: hecho ese día') + '</h2><div class="om-card"><table><tr><th>Canal</th>' +
            '<th class="r">OUT validadas</th><th class="r">Uds</th>' +
            (hoy ? '<th class="r">Listas</th><th class="r">Uds</th><th class="r">En espera</th><th class="r">Uds</th><th>Más antigua</th>' : '') + '</tr>' +
            r.canales.map(function (c) {
                return '<tr><td>' + e(c.canal) + '</td><td class="r">' + n(c.hechas) + '</td><td class="r">' + n(c.uds_hechas) + '</td>' +
                    (hoy ? '<td class="r"><b>' + n(c.listas) + '</b></td><td class="r">' + n(c.uds_listas) + '</td><td class="r">' + n(c.espera) +
                        '</td><td class="r">' + n(c.uds_espera) + '</td><td>' + e(c.mas_antigua) + '</td>' : '') + '</tr>';
            }).join('') + '</table>' +
            (hoy ? '<p class="om-nota" style="margin:8px 0 0">Listas: con todo reservado. En espera: falta stock por reservar. Más antigua: fecha prevista de la OUT abierta más vieja.</p>' : '') +
            '</div>';
    },

    _lotes: function (r) {
        if (!r.lotes.length) { return ''; }
        return '<h2>Lotes con OUT sin hacer</h2><div class="om-card"><table><tr><th>Lote</th><th>Avance</th><th class="r">Hechas</th>' +
            '<th class="r">Listas</th><th class="r">En espera</th><th class="r">Total</th><th class="r">Uds pendientes</th></tr>' +
            r.lotes.map(function (l) {
                var t = l.hechas + l.listas + l.espera;
                var p = t ? 100 * l.hechas / t : 0;
                return '<tr><td>' + e(l.lote) + '</td><td><span class="om-mini"><i style="width:' + p + '%;background:var(--om-ok)"></i></span>' +
                    Math.round(p) + '%</td><td class="r">' + n(l.hechas) + '</td><td class="r">' + n(l.listas) + '</td><td class="r">' + n(l.espera) +
                    '</td><td class="r">' + n(t) + '</td><td class="r">' + n(l.uds) + '</td></tr>';
            }).join('') + '</table></div>';
    },
});

core.action_registry.add('oriola_monitor', Monitor);
return Monitor;
});
