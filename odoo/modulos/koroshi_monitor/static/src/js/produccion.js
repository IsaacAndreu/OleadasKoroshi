odoo.define('koroshi_monitor.produccion', function (require) {
'use strict';
// v1.31.0 (17/11/2026): «Producción por hora». Por operario: uds y u/h de cada hora del dia, sus pedidos, y el total
// del equipo hora a hora. Datos de /koroshi_monitor/produccion (solo lee). Hoy: se refresca cada 2 min.

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');

var REFRESCO_MS = 120000;

function e(valor) {
    return _.escape(valor === undefined || valor === null ? '' : String(valor));
}

function n(valor) {
    return Math.round(Number(valor || 0)).toLocaleString('es-ES');
}

function fechaTxt(iso) {
    var p = (iso || '').split('-');
    var dias = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
    var d = new Date(Number(p[0]), Number(p[1]) - 1, Number(p[2]));
    return dias[d.getDay()] + ' ' + p[2] + '/' + p[1];
}

function horaTxt(h) {
    return ('0' + h).slice(-2) + '-' + ('0' + ((h + 1) % 24)).slice(-2);
}

var Produccion = AbstractAction.extend({
    hasControlPanel: false,

    events: {
        'click .kp-monitor': '_onMonitor',
        'change .kp-dia': '_onDia',
        'click .kp-refrescar': '_onRefrescar',
        'click .kp-excel': '_onExcel',
        'click .kp-op': '_onOperario',
        'click a.kp-out': '_onOut',
    },

    init: function (parent, action) {
        this._super.apply(this, arguments);
        this.dia = (action && action.context && action.context.koroshi_dia) || null;
        this.abiertos = {};
        this.r = null;
    },

    start: function () {
        var self = this;
        this.$el.addClass('o_koroshi_produccion');
        return this._super.apply(this, arguments).then(function () {
            self._cargar();
            self._timer = setInterval(function () {
                if (self.r && self.r.es_hoy && !document.hidden) { self._cargar(); }
            }, REFRESCO_MS);
        });
    },

    destroy: function () {
        clearInterval(this._timer);
        this._super.apply(this, arguments);
    },

    getTitle: function () {
        return 'Producción por hora';
    },

    _cargar: function () {
        var self = this;
        return this._rpc({route: '/koroshi_monitor/produccion', params: {dia: this.dia}}).then(function (r) {
            self.r = r;
            self.dia = r.dia;
            self._pintar(r);
        });
    },

    _onDia: function (ev) {
        this.dia = $(ev.currentTarget).val();
        this._cargar();
    },

    _onRefrescar: function (ev) {
        ev.preventDefault();
        this._cargar();
    },

    _onExcel: function (ev) {
        ev.preventDefault();
        var desde = this.$('.kp-excel-desde').val() || this.dia;
        var hasta = this.$('.kp-excel-hasta').val() || desde;
        window.location = '/koroshi_monitor/produccion.xlsx?desde=' + encodeURIComponent(desde) + '&hasta=' + encodeURIComponent(hasta);
    },

    _onOperario: function (ev) {
        var op = $(ev.currentTarget).data('op');
        this.abiertos[op] = !this.abiertos[op];
        this._pintar(this.r);
    },

    _onMonitor: function (ev) {
        ev.preventDefault();
        this.do_action({type: 'ir.actions.client', name: 'Monitor picking', tag: 'koroshi_monitor', target: 'current'});
    },

    _onOut: function (ev) {
        if (ev.ctrlKey || ev.metaKey) { return; }
        ev.preventDefault();
        this.do_action({type: 'ir.actions.act_window', res_model: 'stock.picking', res_id: $(ev.currentTarget).data('id'),
                        views: [[false, 'form']], target: 'current'});
    },

    _pintar: function (r) {
        var self = this;
        var h = '<main>';
        h += '<div class="kp-cab"><div><h1>Producción por hora</h1><p>Lo que ha hecho cada operario cada hora: uds y u/h. ' +
            (r.es_hoy ? 'Hoy, datos de las ' + e(r.hora) + ' (se actualiza cada 2 min).' : '') + '</p></div>' +
            '<button class="btn btn-secondary kp-monitor">← Monitor picking</button></div>';
        h += '<div class="kp-ctl"><label>Día <select class="kp-dia">' + (r.dias || []).map(function (d) {
            return '<option value="' + e(d) + '"' + (d === r.dia ? ' selected' : '') + '>' + e(fechaTxt(d)) + (d === r.hoy ? ' (hoy)' : '') + '</option>';
        }).join('') + '</select></label><button class="btn btn-secondary kp-refrescar">Refrescar</button>' +
            '<span class="kp-sep"></span><label>Excel de <input type="date" class="kp-excel-desde" value="' + e(r.dia) + '"/></label>' +
            '<label>a <input type="date" class="kp-excel-hasta" value="' + e(r.dia) + '"/></label>' +
            '<button class="btn btn-success kp-excel">Descargar Excel</button></div>';
        if (r.sin_modulo) {
            this.$el.html(h + '<p class="kp-nota">Hace falta KOROSHI Operarios 2.12 o más para ver la producción por operario.</p></main>');
            return;
        }
        var ops = r.operarios || [], horas = r.horas || [], eq = r.equipo || {celdas: {}};
        if (!ops.length) {
            this.$el.html(h + '<p class="kp-nota">Este día no hay pedidos con operario (KOROSHI Operarios).</p></main>');
            return;
        }
        h += '<div class="kp-kpis">' + [
            [n(eq.uds), 'uds del día'],
            [String(eq.horas_ef || 0).replace('.', ','), 'horas efectivas'],
            [n(eq.uh), 'u/h por persona'],
            [eq.operarios, 'operarios'],
        ].map(function (k) { return '<div class="kp-kpi"><b>' + k[0] + '</b><span>' + k[1] + '</span></div>'; }).join('') + '</div>';

        // máximo de uds en una celda: el fondo de cada casilla va de blanco a azul según sus uds
        var max = 1;
        ops.forEach(function (o) { horas.forEach(function (x) { var c = o.celdas[String(x)]; if (c && c.uds > max) { max = c.uds; } }); });
        function celda(c) {
            if (!c || (!c.uds && !c.min)) { return '<td class="kp-vacia">·</td>'; }
            var a = Math.min(c.uds / max, 1);
            return '<td style="background:rgba(49,91,133,' + (0.08 + 0.5 * a).toFixed(2) + ')" title="' + c.min + ' min efectivos">' +
                '<b>' + n(c.uds) + '</b><small>' + (c.uh !== null && c.uh !== undefined ? n(c.uh) + ' u/h' : c.min + ' min') + '</small></td>';
        }

        h += '<div class="kp-card kp-scroll"><table class="kp-tabla"><thead><tr><th class="kp-col-op">Operario</th>' +
            horas.map(function (x) { return '<th class="c">' + horaTxt(x) + '</th>'; }).join('') +
            '<th class="r">Uds</th><th class="r">Horas</th><th class="r">u/h</th></tr></thead><tbody>';
        ops.forEach(function (o) {
            var abierto = !!self.abiertos[o.op];
            h += '<tr class="kp-op' + (abierto ? ' kp-abierto' : '') + '" data-op="' + e(o.op) + '" title="Clic: ver sus pedidos">' +
                '<td class="kp-col-op"><span class="kp-flecha">' + (abierto ? '▾' : '▸') + '</span> ' + e(o.op) +
                (o.estimado ? ' <span class="kp-est" title="Algún pedido sin lecturas en la PDA (app de siempre): sus uds se reparten por el tiempo">~</span>' : '') +
                '<small>' + o.n_pedidos + ' pedidos</small></td>' +
                horas.map(function (x) { return celda(o.celdas[String(x)]); }).join('') +
                '<td class="r"><b>' + n(o.uds) + '</b></td><td class="r">' + String(o.horas_ef).replace('.', ',') + '</td><td class="r"><b>' + n(o.uh) + '</b></td></tr>';
            if (abierto) {
                h += '<tr class="kp-pedidos"><td colspan="' + (horas.length + 4) + '"><table><thead><tr><th>Pedido</th><th>Estado</th><th>Empieza</th><th>Acaba</th>' +
                    '<th class="r">Uds</th><th class="r">Min efectivos</th><th class="r">u/h</th></tr></thead><tbody>' +
                    o.pedidos.map(function (p) {
                        return '<tr><td>' + (p.out_id ? '<a class="kp-out" data-id="' + p.out_id + '" href="/web#id=' + p.out_id + '&model=stock.picking&view_type=form">' + e(p.ref) + '</a>' : e(p.ref)) +
                            (p.estimado ? ' <span class="kp-est">~</span>' : '') + '</td><td>' + e(p.estado) + '</td><td>' + e(p.ini) + '</td><td>' + e(p.fin) +
                            '</td><td class="r">' + n(p.uds) + '</td><td class="r">' + n(p.min) + '</td><td class="r">' + (p.uh ? n(p.uh) : '') + '</td></tr>';
                    }).join('') + '</tbody></table></td></tr>';
            }
        });
        h += '</tbody><tfoot><tr class="kp-equipo"><td class="kp-col-op">EQUIPO<small>uds de la hora · u/h por persona</small></td>' +
            horas.map(function (x) {
                var c = eq.celdas[String(x)];
                if (!c) { return '<td class="kp-vacia">·</td>'; }
                return '<td title="' + c.personas + ' operarios, ' + String(c.personas_ef).replace('.', ',') + ' personas a jornada completa"><b>' + n(c.uds) + '</b><small>' +
                    (c.uh !== null && c.uh !== undefined ? n(c.uh) + ' u/h' : '') + ' · ' + c.personas + ' op.</small></td>';
            }).join('') +
            '<td class="r"><b>' + n(eq.uds) + '</b></td><td class="r">' + String(eq.horas_ef).replace('.', ',') + '</td><td class="r"><b>' + n(eq.uh) + '</b></td></tr></tfoot></table></div>';

        h += '<p class="kp-nota"><b>Cómo se cuenta.</b> Uds de cada hora = las uds de cada pedido repartidas según la hora de cada lectura en la PDA. ' +
            'u/h de cada hora = esas uds entre los minutos efectivos de esa hora (sin los ratos de 15 min o más sin leer). Con menos de ' + (r.min_uh_hora || 5) +
            ' min en una hora sale solo el tiempo. Totales de Uds, Horas y u/h: la misma cifra que la tabla Operarios del Monitor y Productividad. ' +
            '<span class="kp-est">~</span> = pedido hecho con la app de siempre (sin lecturas en la PDA): sus uds se reparten por el tiempo. ' +
            'Fila EQUIPO: uds que ha sacado todo el equipo en esa hora, la u/h por persona y cuántos operarios han trabajado.</p></main>';
        this.$el.html(h);
    },
});

core.action_registry.add('koroshi_produccion', Produccion);
return Produccion;
});
