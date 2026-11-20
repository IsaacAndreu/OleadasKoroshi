odoo.define('koroshi_monitor.produccion', function (require) {
'use strict';
// v1.31.0 (17/11/2026): «Producción por hora». Por operario: uds y u/h de cada hora del dia, sus pedidos, y el total
// del equipo hora a hora. Datos de /koroshi_monitor/produccion (solo lee). Hoy: se refresca cada 2 min.
// v1.32.0 (17/11/2026, revision con el responsable): u/h REAL (hora entera de presencia) como cifra principal y u/h
// picking (mientras lee) al lado; minutos efectivos y perdidos en cada casilla; verde/rojo contra el ritmo estandar
// (100 u/h real); selector Todo / Tiendas / Web / Marketplace / Otros; franja del dia con total, hecho, pendiente,
// horas que quedan y hora de fin.

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');

var REFRESCO_MS = 120000;
var TIPOS = [['todo', 'Todo'], ['tiendas', 'Tiendas'], ['web', 'Web'], ['marketplace', 'Marketplace'], ['otros', 'Otros']];

function e(valor) {
    return _.escape(valor === undefined || valor === null ? '' : String(valor));
}

function n(valor) {
    return Math.round(Number(valor || 0)).toLocaleString('es-ES');
}

function coma(valor) {
    return String(valor === undefined || valor === null ? '' : valor).replace('.', ',');
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

function hm(min) {
    min = Math.round(min || 0);
    return Math.floor(min / 60) + ' h ' + ('0' + (min % 60)).slice(-2);
}

function claseColor(c) {
    return c === 'ok' ? ' kp-ok' : (c === 'bajo' ? ' kp-bajo' : '');
}

var Produccion = AbstractAction.extend({
    hasControlPanel: false,

    events: {
        'click .kp-monitor': '_onMonitor',
        'change .kp-dia': '_onDia',
        'click .kp-tipo': '_onTipo',
        'click .kp-refrescar': '_onRefrescar',
        'click .kp-excel': '_onExcel',
        'click .kp-op': '_onOperario',
        'click a.kp-out': '_onOut',
    },

    init: function (parent, action) {
        this._super.apply(this, arguments);
        this.dia = (action && action.context && action.context.koroshi_dia) || null;
        this.tipo = 'todo';
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
        var params = {dia: this.dia};
        if (this.tipo !== 'todo') { params.tipo = this.tipo; }
        return this._rpc({route: '/koroshi_monitor/produccion', params: params}).then(function (r) {
            self.r = r;
            self.dia = r.dia;
            self._pintar(r);
        });
    },

    _onDia: function (ev) {
        this.dia = $(ev.currentTarget).val();
        this._cargar();
    },

    _onTipo: function (ev) {
        ev.preventDefault();
        this.tipo = $(ev.currentTarget).data('tipo');
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

    _cabecera: function (c, r) {
        if (!c || !c.total) { return ''; }
        return '<div class="kp-hero"><div class="kp-hero-pct">' + c.pct + '<small> %</small></div>' +
            '<div><b>' + n(c.total) + '</b><span>uds del día (pedidos de tienda' + (c.anteriores ? ', con ' + c.anteriores + ' OUT abiertas de días anteriores' : '') + ')</span></div>' +
            '<div><b>' + n(c.hecho) + '</b><span>hechas</span></div>' +
            '<div><b>' + n(c.pendiente) + '</b><span>pendientes</span></div>' +
            '<div><b>' + (c.horas_quedan !== null && c.horas_quedan !== undefined ? coma(c.horas_quedan) + ' h' : '–') + '</b><span>quedan a ' + n(c.uh_equipo) + ' u/h del equipo</span></div>' +
            '<div><b>' + (c.fin_previsto ? e(c.fin_previsto) : (c.pendiente ? '–' : 'Hecho')) + '</b><span>' + (r.es_hoy ? 'hora de fin a este ritmo' : 'fin') + '</span></div></div>';
    },

    _pintar: function (r) {
        var self = this;
        var h = '<main>';
        h += '<div class="kp-cab"><div><h1>Producción por hora</h1><p>Lo que ha hecho cada operario cada hora. ' +
            (r.es_hoy ? 'Hoy, datos de las ' + e(r.hora) + ' (se actualiza cada 2 min).' : '') + '</p></div>' +
            '<button class="btn btn-secondary kp-monitor">← Monitor picking</button></div>';
        var tipos = r.tipos || {};
        h += '<div class="kp-ctl"><label>Día <select class="kp-dia">' + (r.dias || []).map(function (d) {
            return '<option value="' + e(d) + '"' + (d === r.dia ? ' selected' : '') + '>' + e(fechaTxt(d)) + (d === r.hoy ? ' (hoy)' : '') + '</option>';
        }).join('') + '</select></label>' +
            '<div class="kp-tipos">' + TIPOS.filter(function (t) { return t[0] === 'todo' || tipos[t[0]] || t[0] === self.tipo; }).map(function (t) {
                return '<button class="kp-tipo' + (t[0] === self.tipo ? ' kp-activo' : '') + '" data-tipo="' + t[0] + '">' + t[1] +
                    (t[0] !== 'todo' && tipos[t[0]] ? ' <small>' + tipos[t[0]] + '</small>' : '') + '</button>';
            }).join('') + '</div>' +
            '<button class="btn btn-secondary kp-refrescar">Refrescar</button>' +
            '<span class="kp-sep"></span><label>Excel de <input type="date" class="kp-excel-desde" value="' + e(r.dia) + '"/></label>' +
            '<label>a <input type="date" class="kp-excel-hasta" value="' + e(r.dia) + '"/></label>' +
            '<button class="btn btn-success kp-excel">Descargar Excel</button></div>';
        if (r.sin_modulo) {
            this.$el.html(h + '<p class="kp-nota">Hace falta KOROSHI Operarios 2.12 o más para ver la producción por operario.</p></main>');
            return;
        }
        h += this._cabecera(r.cabecera, r);
        var ops = r.operarios || [], horas = r.horas || [], eq = r.equipo || {celdas: {}};
        if (!ops.length) {
            this.$el.html(h + '<p class="kp-nota">' + (this.tipo === 'todo' ? 'Este día no hay pedidos con operario (KOROSHI Operarios).' :
                'Este día no hay pedidos de este tipo con operario.') + '</p></main>');
            return;
        }
        h += '<div class="kp-kpis">' + [
            [n(eq.uds), 'uds del día'],
            ['<span class="' + claseColor(eq.color) + '">' + n(eq.uh_real) + '</span>', 'u/h real por persona (hora entera)'],
            [n(eq.uh), 'u/h picking (mientras lee)'],
            [hm(eq.presencia), 'de presencia · ' + hm(eq.efectivo) + ' leyendo'],
            [hm(eq.perdido), 'perdidas (cerrar cajas, huecos, desayuno)'],
            [eq.operarios + (eq.max_a_la_vez ? ' <small>(' + eq.max_a_la_vez + ' a la vez)</small>' : ''), 'operarios'],
        ].map(function (k) { return '<div class="kp-kpi"><b>' + k[0] + '</b><span>' + k[1] + '</span></div>'; }).join('') + '</div>';

        function celda(c, equipo) {
            if (!c || (!c.uds && !c.min && !c.pres)) { return '<td class="kp-vacia">·</td>'; }
            var tit = c.uds + ' uds · ' + c.pres + ' min de presencia, ' + c.min + ' leyendo, ' + c.perdido + ' perdidos' +
                (c.uh !== null && c.uh !== undefined ? ' · ' + c.uh + ' u/h mientras lee' : '') + (equipo ? ' · ' + c.personas + ' operarios' : '');
            return '<td class="kp-celda' + claseColor(c.color) + '" title="' + e(tit) + '">' +
                '<span class="kp-uds">' + n(c.uds) + ' uds</span>' +
                '<b>' + (c.uh_real !== null && c.uh_real !== undefined ? n(c.uh_real) + ' u/h' : '–') + '</b>' +
                '<small>' + c.min + ' min leyendo' + (c.perdido ? ' · <span class="kp-perd">' + c.perdido + ' perd.</span>' : '') + '</small>' +
                (c.uh !== null && c.uh !== undefined ? '<small class="kp-pick">picking ' + n(c.uh) + ' u/h</small>' : '') +
                (equipo ? '<small>' + c.personas + ' op.</small>' : '') + '</td>';
        }

        h += '<div class="kp-card kp-scroll"><table class="kp-tabla"><thead><tr><th class="kp-col-op">Operario</th>' +
            horas.map(function (x) { return '<th class="c">' + horaTxt(x) + '</th>'; }).join('') +
            '<th class="r">Uds</th><th class="r">Presencia</th><th class="r">Perdido</th><th class="r">u/h real</th><th class="r">u/h picking</th></tr></thead><tbody>';
        ops.forEach(function (o) {
            var abierto = !!self.abiertos[o.op];
            h += '<tr class="kp-op' + (abierto ? ' kp-abierto' : '') + '" data-op="' + e(o.op) + '" title="Clic: ver sus pedidos">' +
                '<td class="kp-col-op"><span class="kp-flecha">' + (abierto ? '▾' : '▸') + '</span> ' + e(o.op) +
                (o.estimado ? ' <span class="kp-est" title="Algún pedido sin lecturas en la PDA (app de siempre): sus uds se reparten por el tiempo">~</span>' : '') +
                '<small>' + o.n_pedidos + ' pedidos</small></td>' +
                horas.map(function (x) { return celda(o.celdas[String(x)], false); }).join('') +
                '<td class="r"><b>' + n(o.uds) + '</b></td><td class="r">' + hm(o.presencia) + '</td><td class="r kp-perd">' + hm(o.perdido) +
                '</td><td class="r kp-total' + claseColor(o.color) + '"><b>' + n(o.uh_real) + '</b></td><td class="r">' + n(o.uh) + '</td></tr>';
            if (abierto) {
                h += '<tr class="kp-pedidos"><td colspan="' + (horas.length + 6) + '"><table><thead><tr><th>Pedido</th><th>Tipo</th><th>Estado</th><th>Empieza</th><th>Acaba</th>' +
                    '<th class="r">Uds</th><th class="r">Min (inicio a fin)</th><th class="r">Min leyendo</th><th class="r">u/h picking</th></tr></thead><tbody>' +
                    o.pedidos.map(function (p) {
                        return '<tr><td>' + (p.out_id ? '<a class="kp-out" data-id="' + p.out_id + '" href="/web#id=' + p.out_id + '&model=stock.picking&view_type=form">' + e(p.ref) + '</a>' : e(p.ref)) +
                            (p.estimado ? ' <span class="kp-est">~</span>' : '') + '</td><td>' + e(p.tipo) + '</td><td>' + e(p.estado) + '</td><td>' + e(p.ini) + '</td><td>' + e(p.fin) +
                            '</td><td class="r">' + n(p.uds) + '</td><td class="r">' + n(p.min_total) + '</td><td class="r">' + n(p.min) + '</td><td class="r">' + (p.uh ? n(p.uh) : '') + '</td></tr>';
                    }).join('') + '</tbody></table></td></tr>';
            }
        });
        h += '</tbody><tfoot><tr class="kp-equipo"><td class="kp-col-op">EQUIPO<small>uds de la hora · u/h real por persona</small></td>' +
            horas.map(function (x) { return celda(eq.celdas[String(x)], true); }).join('') +
            '<td class="r"><b>' + n(eq.uds) + '</b></td><td class="r">' + hm(eq.presencia) + '</td><td class="r kp-perd">' + hm(eq.perdido) +
            '</td><td class="r kp-total' + claseColor(eq.color) + '"><b>' + n(eq.uh_real) + '</b></td><td class="r">' + n(eq.uh) + '</td></tr></tfoot></table></div>';

        h += '<p class="kp-nota"><b>Cómo se cuenta.</b> <b>u/h real</b> (la grande) = uds entre el tiempo de presencia: el tiempo leyendo más los huecos de menos de 15 min entre pedidos ' +
            '(cerrar cajas, precintar, palé). Los ratos de 15 min o más sin hacer nada (una sesión olvidada abierta, el desayuno) no cuentan. ' +
            'Descansos por turno (según la hora de entrada): en el de 6 a 14 se descuentan 15 min (primero lo que ya no contaba; si falta, de los huecos cortos más largos); en el partido, de 13 a 14 solo cuenta lo leído. En <span class="kp-ok-txt">verde</span> desde ' + (r.ritmo || 100) + ' u/h real, en <span class="kp-bajo-txt">rojo</span> por debajo. ' +
            '<b>u/h picking</b> = solo los minutos leyendo (sin los ratos de 15 min o más sin leer). <b>Perdido</b> = presencia − minutos leyendo (los huecos cortos). ' +
            'Con menos de ' + (r.min_uh_hora || 5) + ' min en una hora no sale la u/h. Uds de cada hora = las uds de cada pedido repartidas según la hora de cada lectura en la PDA; ' +
            '<span class="kp-est">~</span> = pedido hecho con la app de siempre (sin lecturas): sus uds se reparten por el tiempo. ' +
            'Con un tipo elegido (Tiendas, Web…), la presencia es solo el tiempo dentro de esos pedidos. Solo sale lo que se hace con tarjeta en Lecturas. ' +
            'La franja de arriba es de los pedidos de tienda (como el Monitor), hoy con las OUT abiertas de días anteriores.</p></main>';
        this.$el.html(h);
    },
});

core.action_registry.add('koroshi_produccion', Produccion);
return Produccion;
});
