odoo.define('koroshi_monitor.monitor', function (require) {
'use strict';
// KOROSHI Monitor zonas: misma pantalla que estado-OUT-agrupaciones-Z-*.html, con datos en
// directo de /koroshi_monitor/datos. Se refresca sola cada REFRESCO ms. Solo lee.

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');

var REFRESCO = 60000;
var ZS = ['D1', 'D2', 'D3', 'D4', 'D5', 'ZX'];
var COL = {D1: 'var(--km-z1)', D2: 'var(--km-z2)', D3: 'var(--km-z3)', D4: 'var(--km-z4)', D5: 'var(--km-z5)',
    D6: 'var(--km-z6)', D7: 'var(--km-z7)', D8: 'var(--km-z8)', ZX: 'var(--km-zx)'};
// v1.9: orden de las zonas: D1, D2... por numero, despues ZX, ZX1, ZX2..., y las rondas (R2-D1...) detras
function ordenZona(z) {
    var r = 0, m = /^R(\d+)-(.*)$/.exec(z);
    if (m) { r = parseInt(m[1], 10); z = m[2]; }
    m = /^D(\d+)$/.exec(z);
    if (m) { return r * 10000 + parseInt(m[1], 10); }
    m = /^ZX(\d*)$/.exec(z);
    if (m) { return r * 10000 + 1000 + (parseInt(m[1], 10) || 0); }
    return r * 10000 + 2000;
}
// v1.9: en la matriz la ronda va en la misma columna que su zona (R2-D1 en D1): las tiendas de cada ronda son otras
function sinRonda(z) { return z.replace(/^R\d+-/, ''); }
var EST = {hecha: 'Hecha', curso: 'Cogiéndose', pend: 'Sin empezar', parcial: 'Parada (sin cerrar caja)', sinstock: 'Sin stock'};

function e(s) { return _.escape(s === undefined || s === null ? '' : String(s)); }
// v1.11: enlace a la OUT en Odoo (se abre en otra pestana para no perder el monitor)
function aOut(o, html) {
    if (!o.id) { return html; }
    return '<a class="km-a" target="_blank" href="/web#id=' + o.id + '&model=stock.picking&view_type=form&cids=8">' + html + '</a>';
}
function n(x) { return Math.round(x).toLocaleString('es-ES'); }
function zt(z) { return '<span class="km-z" style="background:' + (COL[z.replace(/^R\d+-/, '')] || 'var(--km-zx)') + '">' + e(z) + '</span>'; }
function hm(h) { var m = Math.round((h || 0) * 60); return Math.floor(m / 60) + ' h ' + ('0' + (m % 60)).slice(-2); }
function horaMin(h) {
    if (!h) { return -1; }
    var m = /^(\d{1,2}):(\d{2})$/.exec(String(h));
    return m ? parseInt(m[1], 10) * 60 + parseInt(m[2], 10) : -1;
}
var OUT_COLORS = ['#2563eb', '#0f766e', '#c2410c', '#7c3aed', '#be123c', '#15803d', '#b45309', '#0369a1', '#9333ea', '#4d7c0f', '#c026d3', '#475569'];
function outColor(o) {
    var s = String((o && (o.id || o.out)) || '');
    var h = 0;
    for (var i = 0; i < s.length; i++) { h = ((h << 5) - h) + s.charCodeAt(i); h |= 0; }
    return OUT_COLORS[Math.abs(h) % OUT_COLORS.length];
}
function transporteTexto(o) {
    if (!o) { return ''; }
    var t = o.transportista || '';
    var et = o.etiqueta || '';
    return t + (t && et ? ' · ' : '') + et;
}
// v1.18: operarios del modulo koroshi_operarios. v1.30: nombre + codigo ('Ana Garcia · OP3'); antes solo el codigo.
// En negrita el que la tiene abierta ahora; los demas (la empezaron o la dejaron) en gris.
function opsTxt(o) {
    var ahora = o.ops_ahora || [], todos = o.ops || [], parados = o.ops_parados || [];
    if (!todos.length) { return '<span class="km-muted">–</span>'; }
    return todos.map(function (c) {
        // v1.21: en rojo el que la tiene abierta pero lleva rato sin leer
        if (parados.indexOf(c) >= 0) { return '<b class="km-op km-op-parado" title="Abierta, sin leer">' + e(c) + '</b>'; }
        return ahora.indexOf(c) >= 0 ? '<b class="km-op">' + e(c) + '</b>' : '<span class="km-op km-op-old">' + e(c) + '</span>';
    }).join(' ');
}
// v1.21: alarma de bloqueo. Operarios con un pedido abierto en Lecturas que llevan mas de r.sin_leer_min minutos sin
// leer nada (se han parado o se han ido sin «Dejar aqui»). Quien lea ese pedido se lo queda sin preguntar.
function avisoParados(r, tv) {
    var ps = (r.operarios || []).filter(function (o) { return o.parado; });
    if (!ps.length) { return ''; }
    ps.sort(function (a, b) { return b.sin_leer - a.sin_leer; });
    return '<div class="km-card km-aviso km-alarma"><b>' + (ps.length === 1 ? '1 pedido abierto sin leer' : ps.length + ' pedidos abiertos sin leer') +
        ' desde hace más de ' + (r.sin_leer_min || 15) + ' min:</b> ' +
        ps.map(function (o) { return '<b class="km-op km-op-parado">' + e(o.op) + '</b> ' + e(o.ahora) + ' (' + o.sin_leer + ' min)'; }).join(' · ') +
        (tv ? '' : '. ¿Se ha parado o se ha ido sin «Dejar aquí»? Si otro operario lee ese pedido, se lo queda sin preguntar.') + '</div>';
}
function tablaOperarios(ops, tv) {
    if (!ops || !ops.length) { return ''; }
    var h = '<h2>Operarios (' + ops.length + ')</h2><div class="km-card km-scroll"><table class="km-ops"><thead><tr><th>Operario</th><th>Ahora</th><th>Desde</th>' +
        (tv ? '' : '<th class="r">Pedidos</th><th class="r">Acabados</th><th class="r">Dejados</th>') +
        '<th class="r">Uds</th><th class="r">Min</th><th class="r">u/h</th></tr></thead><tbody>';
    ops.forEach(function (o) {
        // v1.25: o.alarma = la PDA le está pitando (alarma de parado): la fila entera en rojo
        h += '<tr' + (o.ahora ? ' class="km-op-activo' + (o.alarma ? ' km-op-alarma-fila' : (o.parado ? ' km-op-parado-fila' : '')) + '"' : '') + '><td><b class="km-op' + (o.parado || o.alarma ? ' km-op-parado' : '') + '">' + e(o.op) + '</b></td><td class="m">' +
            (o.ahora ? e(o.ahora) + (o.alarma ? ' <span class="km-alarma-txt">🔔 ALARMA · ' + o.sin_leer + ' min sin leer</span>' :
                                     (o.parado ? ' <span class="km-parado-txt">' + o.sin_leer + ' min sin leer</span>' : '')) :
             o.pausa ? '<span class="km-pausa">⏸ Pausa</span> ' + e(o.pausa_ref || '') :   // v1.24
             '<span class="km-muted">–</span>') +
            '</td><td>' + e(o.ahora ? o.desde : (o.pausa || o.desde)) + '</td>' +
            (tv ? '' : '<td class="r">' + o.tareas + '</td><td class="r">' + o.acabadas + '</td><td class="r">' + (o.dejadas || '') + '</td>') +
            '<td class="r">' + n(o.uds) + '</td><td class="r">' + n(o.min) + '</td><td class="r"><b>' + (o.uh || '') + '</b></td></tr>';
    });
    return h + '</tbody></table></div>' + (tv ? '' : '<p class="km-nota">Nombre y código de la tarjeta de cada operario (KOROSHI Operarios). Uds = uds leídas entre que lee la OUT y la valida o la deja; en curso, hasta ahora.</p>');
}
// Personas y horas estimadas por las cajas cerradas (v1.3): sale para cualquier dia, no solo hoy
function personas(p, quien) {
    if (!p || !p.hp) { return ''; }
    var inactividad = p.inactividad_min || 5;
    // v1.20.1: en zonas, una persona por OUT desde que empieza cada caja hasta que la cierra
    var nota = p.zonas ?
        'Estimado por las cajas cerradas: cada ' + quien + ' es una persona. Cuenta desde que empieza una caja hasta que la cierra ' +
        '(la primera, ' + String(p.primera_caja_min || 0).replace('.', ',') + ' min antes: lo típico entre cajas ese día). ' +
        'Si entre dos cajas pasan más de ' + (p.hueco_max_min || 20) + ' min, ese hueco no cuenta (pico o faltante).' :
        'Estimado por las cajas cerradas: cada ' + quien + ' cuenta como una persona mientras tenga actividad en los últimos ' +
        inactividad + ' min. Si pasa más tiempo sin lectura deja de contar (puede ser un pico o un faltante).';
    return '<h2>Personas y horas</h2><p class="km-nota">' + nota +
        ' Todas las PDA usan el mismo usuario: por persona, ver la tabla Operarios.</p>' +
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
        'change .km-filtro': '_onFiltro',
        'input .km-buscar': '_onFiltro',
        'click .km-refrescar': '_cargar',
        'click .km-envios': '_abrirEnvios',
        'click .km-produccion': '_abrirProduccion',   // v1.31.0
        'click .km-mapa': '_abrirMapa',
        'click .km-limpiar-filtros': '_limpiarFiltros',
        'dblclick th.km-sort': '_onSort',
        'click details > summary': '_onToggle',
        'click a.km-a': '_onOut',
    },

    init: function () {
        this._super.apply(this, arguments);
        this.prefijo = false;
        this.abiertas = {};
        this.orden = {key: '', dir: 1};
        this.filtro = {estado: 'todos', transporte: 'todos', texto: ''};
    },

    start: function () {
        var self = this;
        this.$el.addClass('o_koroshi_monitor');
        return this._super.apply(this, arguments).then(function () {
            self.$el.html('<main><p class="km-sub">Cargando…</p></main>');
            self._cargar();
            // v1.27: con la pestaña oculta (otra pestaña, pantalla bloqueada) no se pide nada; al volver, al momento
            self.timer = setInterval(function () { if (!document.hidden) { self._cargar(); } }, REFRESCO);
            self._alVolver = function () {
                if (!document.hidden && Date.now() - (self._ultimaCarga || 0) > REFRESCO) { self._cargar(); }
            };
            document.addEventListener('visibilitychange', self._alVolver);
        });
    },

    destroy: function () {
        clearInterval(this.timer);
        if (this._alVolver) { document.removeEventListener('visibilitychange', this._alVolver); }
        this._super.apply(this, arguments);
    },

    _onPrefijo: function (ev) {
        this.prefijo = ev.target.value;
        this.abiertas = {};
        this.orden = {key: '', dir: 1};
        this.filtro = {estado: 'todos', transporte: 'todos', texto: ''};
        this._cargar();
    },

    _onFiltro: function (ev) {
        var el = ev.currentTarget;
        if (el.classList.contains('km-buscar')) {
            this.filtro.texto = el.value || '';
        } else if (el.classList.contains('km-filtro-estado')) {
            this.filtro.estado = el.value || 'todos';
        } else if (el.classList.contains('km-filtro-transporte')) {
            this.filtro.transporte = el.value || 'todos';
        }
        this._cargar();
    },

    _limpiarFiltros: function () {
        this.filtro = {estado: 'todos', transporte: 'todos', texto: ''};
        this.orden = {key: '', dir: 1};
        this._cargar();
    },

    _onSort: function (ev) {
        ev.preventDefault();
        var key = ev.currentTarget.getAttribute('data-sort-key') || '';
        if (!key) { return; }
        if (this.orden.key === key) { this.orden.dir *= -1; }
        else { this.orden = {key: key, dir: 1}; }
        this._cargar();
    },

    _ordenarOut: function (lista) {
        var self = this;
        var key = this.orden.key;
        if (!key) { return lista; }
        var out = lista.slice();
        function val(o) {
            if (key === 'tienda') { return (o.tienda || '').toLocaleLowerCase(); }
            if (key === 'transportista') { return (o.transportista || '').toLocaleLowerCase(); }
            if (key === 'etiqueta') { return (o.etiqueta || '').toLocaleLowerCase(); }
            if (key === 'estado') { return ({curso: 0, parcial: 1, pend: 2, hecha: 3, sinstock: 4}[o.est] === undefined ? 99 : ({curso: 0, parcial: 1, pend: 2, hecha: 3, sinstock: 4}[o.est])); }
            if (key === 'cajas' || key === 'leido' || key === 'u' || key === 'min' || key === 'uh' || key === 'huecos') { return Number(o[key] || 0); }
            if (key === 'ini' || key === 'fin') { return horaMin(o[key]); }
            if (key === 'op') { return ((o.ops_ahora || [])[0] || (o.ops || [])[0] || '~').toLocaleLowerCase(); }
            return String(o[key] || '').toLocaleLowerCase();
        }
        out.sort(function (a, b) {
            var av = val(a), bv = val(b), c = av < bv ? -1 : (av > bv ? 1 : 0);
            if (!c) { c = knum(a.tienda) - knum(b.tienda) || String(a.out || '').localeCompare(String(b.out || '')); }
            return c * self.orden.dir;
        });
        return out;
    },

    _filtrarOut: function (lista) {
        var f = this.filtro || {estado: 'todos', transporte: 'todos', texto: ''};
        var q = String(f.texto || '').trim().toLocaleLowerCase();
        return lista.filter(function (o) {
            var transport = !!(o.transportista || o.etiqueta);
            if (f.estado !== 'todos' && o.est !== f.estado) { return false; }
            if (f.transporte === 'transportista' && !o.transportista) { return false; }
            if (f.transporte === 'etiqueta' && !o.etiqueta) { return false; }
            if (f.transporte === 'sin' && transport) { return false; }
            if (q && [o.tienda, o.out, o.pedido, o.transportista, o.etiqueta, (o.ops || []).join(' ')].join(' ').toLocaleLowerCase().indexOf(q) < 0) { return false; }
            return true;
        });
    },

    // El mapa operativo reutiliza el mismo endpoint y detecta las zonas KOR
    // creadas hoy. Se abre dentro de Odoo para no duplicar el plano dentro de
    // esta pantalla ni cargarlo cuando no hay zonas reales.
    _abrirMapa: function (ev) {
        ev.preventDefault();
        this.do_action({
            type: 'ir.actions.client',
            tag: 'koroshi_warehouse_map',
            context: {koroshi_mode: 'ops'},
            target: 'current',
        });
    },

    // v1.19.2: acceso visible dentro del Monitor picking, no solo desde el menu superior de Inventario.
    _abrirEnvios: function (ev) {
        ev.preventDefault();
        this.do_action({
            type: 'ir.actions.client',
            name: 'Consulta de envíos',
            tag: 'koroshi_consulta_envios',
            target: 'current',
        });
    },

    // v1.31.0: Producción por hora (uds y u/h de cada operario hora a hora)
    _abrirProduccion: function (ev) {
        ev.preventDefault();
        this.do_action({
            type: 'ir.actions.client',
            name: 'Producción por hora',
            tag: 'koroshi_produccion',
            target: 'current',
        });
    },

    // v1.12: clic en una OUT: se abre dentro de Odoo (con migas para volver al monitor); funciona tambien en la PDA y
    // donde no se abren pestanas nuevas. Ctrl/Cmd/Mayus o boton central: pestana nueva (el enlace normal)
    _onOut: function (ev) {
        if (ev.ctrlKey || ev.metaKey || ev.shiftKey || ev.button === 1) { return; }
        var m = /[#&]id=(\d+)/.exec(ev.currentTarget.getAttribute('href') || '');
        if (!m) { return; }
        ev.preventDefault();
        ev.stopPropagation();
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: 'stock.picking',
            res_id: parseInt(m[1], 10),
            views: [[false, 'form']],
            target: 'current',
        });
    },

    // v1.13: nombre en las migas de pan (para volver al monitor despues de abrir una OUT)
    getTitle: function () {
        return 'Monitor picking';
    },

    _onToggle: function (ev) {
        // El clic en el titulo abre/cierra: se guarda como quedara para el siguiente refresco
        var det = ev.currentTarget.parentNode;
        var z = det.getAttribute('data-z');
        if (z) { this.abiertas[z] = !det.open; }
    },

    _cargar: function () {
        var self = this;
        this._ultimaCarga = Date.now();     // v1.27
        return this._rpc({route: '/koroshi_monitor/datos', params: {prefijo: this.prefijo}}).then(function (r) {
            self.prefijo = r.prefijo;
            var scroll = self.el.scrollTop;
            self._pintar(r);
            self.el.scrollTop = scroll;
        });
    },

    _selector: function (r) {
        var et = r.etiquetas || {};
        var ctl = '<div class="km-ctl"><select class="km-prefijo">' + (r.prefijos || []).map(function (p) {
            return '<option value="' + e(p) + '"' + (p === r.prefijo ? ' selected' : '') + '>' + e(et[p] || p.replace(/-$/, '')) + '</option>';
        }).join('') + '</select>';
        if (r.modo === 'tiendas') {
            var f = this.filtro || {estado: 'todos', transporte: 'todos', texto: ''};
            ctl += '<select class="km-filtro km-filtro-estado" title="Filtrar por estado">' +
                '<option value="todos"' + (f.estado === 'todos' ? ' selected' : '') + '>Todos los estados</option>' +
                '<option value="curso"' + (f.estado === 'curso' ? ' selected' : '') + '>En curso</option>' +
                '<option value="pend"' + (f.estado === 'pend' ? ' selected' : '') + '>Sin empezar</option>' +
                '<option value="hecha"' + (f.estado === 'hecha' ? ' selected' : '') + '>Hechas</option>' +
                '<option value="parcial"' + (f.estado === 'parcial' ? ' selected' : '') + '>Parciales</option>' +
                '</select><select class="km-filtro km-filtro-transporte" title="Filtrar por transporte">' +
                '<option value="todos"' + (f.transporte === 'todos' ? ' selected' : '') + '>Todo transporte</option>' +
                '<option value="transportista"' + (f.transporte === 'transportista' ? ' selected' : '') + '>Con transportista</option>' +
                '<option value="etiqueta"' + (f.transporte === 'etiqueta' ? ' selected' : '') + '>Con etiqueta</option>' +
                '<option value="sin"' + (f.transporte === 'sin' ? ' selected' : '') + '>Sin asignar</option>' +
                '</select><input class="km-buscar" type="search" placeholder="Buscar tienda, OUT o etiqueta…" value="' + e(f.texto || '') + '">' +
                '<button class="btn btn-secondary km-limpiar-filtros" title="Limpiar filtros y orden">Limpiar</button>';
        }
        return ctl + '<button class="btn btn-secondary km-refrescar">Refrescar</button>' +
            '<button class="btn btn-info km-produccion">Producción por hora</button>' +   // v1.31.0
            '<button class="btn btn-success km-envios">Consulta envíos / Excel</button>' +
            '<button class="btn btn-primary km-mapa">Abrir mapa operativo</button></div>';
    },

    _pintar: function (r) {
        if (r.modo === 'tiendas') {
            return this._pintarTiendas(r);
        }
        var self = this;
        var D = r.D || [];
        var T = {u: 0, l: 0, h: 0, c: 0, p: 0};
        var Z = {};
        ZS.forEach(function (z) { Z[z] = {u: 0, l: 0, h: 0, c: 0, p: 0, uh: 0, n: 0, b: 0}; });
        D.forEach(function (o) {
            if (!Z[o.z]) { Z[o.z] = {u: 0, l: 0, h: 0, c: 0, p: 0, uh: 0, n: 0, b: 0}; ZS.push(o.z); }
            var z = Z[o.z], k = o.est === 'hecha' ? 'h' : (o.est === 'curso' || o.est === 'parcial') ? 'c' : 'p';
            z.n++; z.u += o.u; z.l += o.leido; z[k]++; z.b += o.cajas || 0;
            if (o.est === 'hecha') { z.uh += o.u; }
            T.u += o.u; T.l += o.leido; T[k]++;
        });
        var zonas = ZS.filter(function (z) { return Z[z].n; });
        zonas.sort(function (a, b) { return ordenZona(a) - ordenZona(b) || (a < b ? -1 : 1); });
        var pctT = T.u ? Math.round(100 * T.l / T.u) : 0;

        var h = '<main class="km-zonas">';
        h += '<div class="km-cab"><h1>Cómo van las agrupaciones '+ e((r.prefijo || '').replace(/-$/, '')) + '</h1>';
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
        h += avisoParados(r, false);
        h += personas(r.personas, 'OUT');
        h += tablaOperarios(r.operarios, false);

        // Totales
        h += '<h2>Totales: lo que llevan y lo que les falta</h2><div class="km-card km-scroll"><table><thead><tr><th>Zona</th><th class="r">Uds total</th><th class="r">Uds cogidas</th><th class="r">Uds que faltan</th><th class="r">%</th><th class="r">OUT total</th><th class="r">OUT hechas</th><th class="r">OUT cogiéndose</th><th class="r">OUT que faltan</th><th>Operario</th></tr></thead><tbody>';
        // v1.18: operarios de cada zona (la tarea es de la agrupacion entera)
        var opsZona = function (zn) {
            var o = {ops: [], ops_ahora: []};
            D.forEach(function (d) {
                if (d.z !== zn) { return; }
                (d.ops || []).forEach(function (c) { if (o.ops.indexOf(c) < 0) { o.ops.push(c); } });
                (d.ops_ahora || []).forEach(function (c) { if (o.ops_ahora.indexOf(c) < 0) { o.ops_ahora.push(c); } });
            });
            return o;
        };
        zonas.forEach(function (zn) {
            var z = Z[zn];
            h += '<tr><td>' + zt(zn) + '</td><td class="r">' + n(z.u) + '</td><td class="r">' + n(z.l) + '</td><td class="r"><b>' + n(z.u - z.l) + '</b></td><td class="r">' + (z.u ? Math.round(100 * z.l / z.u) : 0) + ' %</td><td class="r">' + z.n + '</td><td class="r">' + z.h + '</td><td class="r">' + z.c + '</td><td class="r"><b>' + (z.c + z.p) + '</b></td><td>' + opsTxt(opsZona(zn)) + '</td></tr>';
        });
        h += '<tr class="km-tot"><td>Total</td><td class="r">' + n(T.u) + '</td><td class="r">' + n(T.l) + '</td><td class="r">' + n(T.u - T.l) + '</td><td class="r">' + pctT + ' %</td><td class="r">' + D.length + '</td><td class="r">' + T.h + '</td><td class="r">' + T.c + '</td><td class="r">' + (T.c + T.p) + '</td><td></td></tr></tbody></table></div>';

        // Avance por zona
        h += '<h2>Avance por zona</h2><div class="km-ley"><span><i style="background:var(--km-ok)"></i>OUT hecha (validada)</span><span><i style="background:var(--km-cur)"></i>cogiéndose</span><span><i style="background:var(--km-pend)"></i>sin empezar</span></div><div class="km-card">';
        zonas.forEach(function (zn) {
            var z = Z[zn], pct = z.u ? Math.round(100 * z.l / z.u) : 0, ph = z.u ? 100 * z.uh / z.u : 0, pc = z.u ? Math.max(0, 100 * (z.l - z.uh) / z.u) : 0;
            h += '<div class="km-zona">' + zt(zn) + '<div><div class="km-fila"><span><b>' + n(z.l) + ' de ' + n(z.u) + ' u</b> (' + pct + ' %)</span><span>' + z.h + ' hechas · ' + z.c + ' cogiéndose · ' + z.p + ' sin empezar (de ' + z.n + ' OUT)</span></div>' +
                '<div class="km-barra"><i style="width:' + ph + '%;background:var(--km-ok)"></i><i style="width:' + pc + '%;background:var(--km-cur)"></i></div></div></div>';
        });
        h += '</div>';

        // Matriz tienda x zona
        var P = {}, orden = [], cols = [];
        D.forEach(function (o) {
            var c = sinRonda(o.z);
            if (!P[o.pedido]) { P[o.pedido] = {caja: o.caja, tienda: o.tienda, z: {}}; orden.push(o.pedido); }
            P[o.pedido].z[c] = o;
            if (cols.indexOf(c) < 0) { cols.push(c); }
        });
        cols.sort(function (a, b) { return ordenZona(a) - ordenZona(b) || (a < b ? -1 : 1); });
        // v1.9: por numero de tienda (con dos rondas las cajas empiezan otra vez en 01)
        orden.sort(function (a, b) { return knum(P[a].tienda) - knum(P[b].tienda) || (parseInt(P[a].caja, 10) || 0) - (parseInt(P[b].caja, 10) || 0); });
        // v1.9: tiendas listas para juntar = todas sus OUT hechas (validadas, o con todo lo que hay cogido)
        // v1.10: y etiquetadas = ademas todas sus OUT tienen la etiqueta del transportista (numero de seguimiento)
        var listas = [], casi = [], etiquetadas = [];
        orden.forEach(function (k) {
            var p = P[k], n = 0, hh = 0, ee = 0, faltan = [];
            Object.keys(p.z).forEach(function (c) {
                n++;
                if (p.z[c].est === 'hecha') { hh++; } else { faltan.push(c); }
                if (p.z[c].etq) { ee++; }
            });
            p.lista = n && hh === n;
            p.etq = p.lista && ee === n;
            if (p.etq) { etiquetadas.push(p); } else if (p.lista) { listas.push(p); } else if (n - hh <= 2) { casi.push([p, faltan]); }
        });
        h += '<h2>Tiendas listas para juntar (' + listas.length + ' de ' + orden.length + ')</h2><div class="km-card">';
        h += listas.length ? '<div class="km-chips">' + listas.map(function (p) {
            return '<span class="km-chip km-chip-ok" title="' + e(p.tienda) + '"><b>' + e(kno(p.tienda)) + '</b></span>';
        }).join('') + '</div>' : '<p class="km-nota">Ahora no hay ninguna tienda con todas sus OUT hechas pendiente de juntar.</p>';
        if (etiquetadas.length) {
            h += '<p class="km-nota" style="margin-top:10px">Ya con etiqueta del transportista (terminadas): ' + etiquetadas.map(function (p) {
                return '<span class="km-chip km-chip-etq" title="' + e(p.tienda) + '"><b>' + e(kno(p.tienda)) + '</b></span>';
            }).join(' ') + '</p>';
        }
        if (casi.length) {
            h += '<p class="km-nota" style="margin-top:10px">Les falta 1 o 2 zonas: ' + casi.map(function (x) {
                return '<b>' + e(kno(x[0].tienda)) + '</b> (' + x[1].map(e).join(', ') + ')';
            }).join(' · ') + '</p>';
        }
        h += '</div>';
        // v1.9: casillas compactas (solo leido/total; la OUT y el estado al pasar el raton) para que con 8 zonas
        // o mas quepa sin arrastrar; la tienda solo con su K (nombre y pedido al pasar el raton)
        h += '<h2>Cada tienda en cada zona</h2><p class="km-nota">Cada casilla es una OUT: unidades leídas / total y, debajo, sus <b>bultos</b> (cajas cerradas), con el color de su estado. En rojo: OUT hecha cuyos bultos en Odoo (los que van a XPO) no coinciden con las cajas cerradas. ' +
            'Al pasar el ratón: número de OUT, agrupación y estado. Vacío = la tienda no tiene nada en esa zona. Las rondas (R2...) van en la columna de su zona.</p>' +
            '<div class="km-ley"><span><i style="background:var(--km-ok)"></i>OUT hecha</span><span><i style="background:var(--km-cur)"></i>cogiéndose</span>' +
            '<span><i style="background:var(--km-bar)"></i>sin empezar</span><span><i style="background:#b9b6ad"></i>tienda con todo hecho: a juntar</span>' +
            '<span><i style="background:#3d5a80"></i>tienda con etiqueta del transportista: terminada</span></div>';
        h += '<div class="km-card km-scroll"><table class="km-matriz"><thead><tr><th>Caja</th><th>Tienda</th>' + cols.map(function (z) { return '<th>' + zt(z) + '</th>'; }).join('') + '<th class="r">Leído</th><th class="r">Bultos</th></tr></thead><tbody>';
        orden.forEach(function (k) {
            var p = P[k], u = 0, l = 0, b = 0;
            h += '<tr' + (p.etq ? ' class="km-r-etq" title="Tienda con la etiqueta del transportista: terminada"' :
                (p.lista ? ' class="km-r-lista" title="Tienda con todas sus OUT hechas: lista para juntar"' : '')) + '><td><b>' + e(p.caja) + '</b></td><td title="' + e(p.tienda) + ' · ' + e(k) + '"><b>' + e(kno(p.tienda)) + '</b> <small>' + e(p.tienda.split(' - ').slice(1).join(' - ')) + '</small></td>';
            cols.forEach(function (z) {
                var o = p.z[z];
                if (!o) { h += '<td></td>'; return; }
                u += o.u; l += o.leido; b += o.cajas || 0;
                // v1.14: bultos de la OUT = cajas cerradas; en rojo si esta hecha y Odoo tiene otros bultos (los de XPO)
                var mal = o.est === 'hecha' && o.bultos !== (o.cajas || 0);
                h += '<td>' + aOut(o, '<span class="km-cel km-' + o.est + (mal ? ' km-bx-mal' : '') + '" title="' + e(o.out) + ' · ' + e(o.lote) + ' · ' + EST[o.est] +
                    ' · ' + (o.cajas || 0) + ' cajas cerradas · ' + o.bultos + ' bultos en Odoo' + ((o.ops || []).length ? ' · ' + o.ops.join(', ') : '') + ' (clic: abrir la OUT)">' + n(o.leido) + '/' + n(o.u) +
                    '<small class="km-bx">' + (o.cajas || 0) + ' b' + (mal ? ' ≠ ' + o.bultos : '') + '</small></span>') + '</td>';
            });
            h += '<td class="r">' + n(l) + '/' + n(u) + '</td><td class="r"><b>' + b + '</b></td></tr>';
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
            h += '<div class="km-card"><details data-z="' + e(zn) + '"' + (abierta ? ' open' : '') + '><summary>' + zt(zn) + ' ' + e(r.prefijo + zn) + ' · ' + n(z.l) + '/' + n(z.u) + ' u · ' + z.b + ' bultos · ' + z.h + ' hechas, ' + z.c + ' cogiéndose, ' + z.p + ' sin empezar</summary>';
            h += '<div class="km-scroll"><table><thead><tr><th>Estado</th><th>Caja</th><th>OUT</th><th>Tienda</th><th>Pedido</th><th>Lineales</th><th class="r">Huecos</th><th>Leído</th><th class="r">Bultos</th><th>Empieza</th><th>Última / validada</th><th>Operario</th></tr></thead><tbody>';
            L.forEach(function (o) {
                var pct = o.u ? 100 * o.leido / o.u : 0, c = o.est === 'hecha' ? 'var(--km-ok)' : 'var(--km-cur)';
                h += '<tr><td><span class="km-cel km-' + o.est + '">' + EST[o.est] + '</span></td><td><b>' + e(o.caja) + '</b></td><td class="m">' + aOut(o, e(o.out)) + '</td><td>' + e(o.tienda) + '</td><td class="m">' + e(o.pedido) + '</td><td>' + e(o.lin) + '</td><td class="r">' + o.huecos + '</td>' +
                    '<td><span class="km-mini"><i style="width:' + pct + '%;background:' + c + '"></i></span>' + n(o.leido) + '/' + n(o.u) + '</td><td class="r">' + (o.cajas || 0) + (o.est === 'hecha' && o.bultos !== (o.cajas || 0) ? ' <span class="km-bx-txt">(Odoo ' + o.bultos + ')</span>' : '') +
                    '</td><td>' + (o.est === 'hecha' ? '' : e(o.ini)) + '</td><td>' + e(o.fin) + '</td><td>' + opsTxt(o) + '</td></tr>';
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
        var self = this;
        lista = this._ordenarOut(lista);
        var COLE = {hecha: 'var(--km-ok)', parcial: 'var(--km-par)'};
        var th = function (key, label, cls) {
            var active = self.orden.key === key;
            return '<th class="km-sort' + (active ? ' km-sort-active' : '') + (cls ? ' ' + cls : '') + '" data-sort-key="' + key + '" title="Doble clic para ordenar">' + label + (active ? (self.orden.dir > 0 ? ' ▲' : ' ▼') : '') + '</th>';
        };
        var h = '<div class="km-scroll"><table class="km-out"><thead><tr>' + th('estado', 'Estado') + th('tienda', 'Tienda') +
            (tv ? '' : th('pedido', 'Pedido')) + th('out', 'OUT') + th('op', 'Operario') +
            (tv ? '' : th('transportista', 'Transportista / etiqueta')) + th('leido', 'Leído') +
            (tv ? '<th class="r">Última caja</th>' : th('cajas', 'Cajas', 'r') + th('huecos', 'Huecos', 'r') + '<th>Lineales</th>' + th('ini', '1ª validación') + th('fin', 'Última validación') + th('hace', 'Hace', 'r') + th('min', 'Min', 'r') + th('uh', 'u/h', 'r')) +
            '</tr></thead><tbody>';
        lista.forEach(function (o) {
            var base = o.est === 'hecha' ? o.leido : o.disp;
            var p = base ? 100 * o.leido / base : 0, c = COLE[o.est] || 'var(--km-cur)';
            // Una OUT hecha con transportista o etiqueta queda azul para
            // distinguirla visualmente de una OUT hecha pendiente de expedir.
            var conTransporte = o.est === 'hecha' && !!(o.transportista || o.etiqueta);
            var cls = 'km-r-' + o.est + (o.parada ? ' km-parada' : '') + (conTransporte ? ' km-r-transport' : '');
            var hace = o.hace === '' ? '' : 'hace ' + o.hace + ' min';
            var transporte = o.transportista ? e(o.transportista) : '<span class="km-muted">Sin asignar</span>';
            var etiqueta = o.etiqueta ? '<br><span class="km-etiqueta">' + e(o.etiqueta) + '</span>' : '';
            // v1.8: hecha sin validar = ya cogido todo lo que hay; lo que falta (sin stock) debajo
            var sv = o.sin_validar ? '<br><small>sin validar' + (o.falta ? ' · faltan ' + n(o.falta) : '') + '</small>' : '';
            h += '<tr class="' + cls + '"><td><span class="km-cel km-' + o.est + '">' + EST[o.est] + '</span>' + sv + '</td><td>' + e(o.tienda) + '</td>' +
                (tv ? '' : '<td class="m">' + e(o.pedido) + '</td>') + '<td class="m">' + aOut(o, e(o.out)) +
                (o.lote && !tv ? '<br><small>' + e(o.lote) + '</small>' : '') + '</td>' +
                '<td>' + opsTxt(o) + '</td>' +
                (tv ? '' : '<td class="km-transport">' + transporte + etiqueta + '</td>') +
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
        var Dvisible = this._filtrarOut(D);
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
        if (!tv && Dvisible.length !== D.length) {
            h += '<p class="km-filtro-activo">Mostrando <b>' + Dvisible.length + '</b> de ' + D.length + ' OUT. Puedes combinar este filtro con la ordenación por doble clic en cualquier encabezado.</p>';
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

        h += avisoParados(r, tv);
        if (paradas.length) {
            h += '<div class="km-card km-aviso"><b>' + paradas.length + ' OUT hechas sin validar (sin cerrar caja hace más de ' + (eq.parada_min || 20) + ' min):</b> ' +
                paradas.map(function (o) { return e(o.out) + ' ' + e(o.tienda) + ' (' + o.hace + ' min, faltan ' + n(o.falta) + ')'; }).join(' · ') +
                '. Se dan por hechas: les faltan prendas (sin stock o no encontradas). Validarlas en Odoo.' +
                (tv ? '' : ' Detalle en KOROSHI KPI › Faltas por día.') + '</div>';
        }

        if (!tv) {
            h += '<div class="km-grid">' + [
                // v1.20.2: operarios de Lecturas + OUT sin operario, sin contar a nadie dos veces
                [eq.activas || 0, 'personas cogiendo ahora' + (eq.activas_op !== undefined ?
                    ': ' + (eq.activas_op || 0) + ' con Lecturas' + (eq.activas_otras ? ' (' + eq.activas_otras + ' en INT u otro trabajo)' : '') +
                    ' + ' + (eq.activas_sin_op || 0) + ' OUT sin operario (caja cerrada en los últimos ' + (eq.parada_min || 20) + ' min)' :
                    ' (caja cerrada en los últimos ' + (eq.parada_min || 20) + ' min)') +
                    ((eq.activas_tiendas || eq.activas) && eq.uh ? ' · ~' + n(eq.uh / (eq.activas_tiendas || eq.activas)) + ' u/h por persona' : '')],
                [n(eq.cajas || 0), 'cajas cerradas' + (eq.cajas ? ' · ' + (T.l / eq.cajas).toFixed(1).replace('.', ',') + ' u por caja' : '')],
                [D.filter(function (o) { return o.sin_validar; }).length, 'hechas sin validar (con faltas de stock)'],
            ].map(function (k) { return '<div class="km-card km-kpi"><b>' + k[0] + '</b><span>' + k[1] + '</span></div>'; }).join('') + '</div>';
        }

        // 2-3. Lo que se esta cogiendo a la vista; sin empezar y hechas plegadas
        var marcha = Dvisible.filter(function (o) { return o.est === 'curso' || o.est === 'parcial'; });
        var pend = Dvisible.filter(function (o) { return o.est === 'pend'; });
        var hechas = Dvisible.filter(function (o) { return o.est === 'hecha'; });
        var porK = function (a, b) { return knum(a.tienda) - knum(b.tienda); };
        pend.sort(porK);
        hechas.sort(porK);

        h += tablaOperarios(r.operarios, tv);
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
            var phOut = r.por_hora_out || [];
            var visibles = {};
            Dvisible.forEach(function (o) { visibles[o.id] = true; });
            var max = 1;
            phOut.forEach(function (x) {
                var total = 0;
                x[1].forEach(function (o) { if (visibles[o.id]) { total += o.u; } });
                if (total > max) { max = total; }
            });
            h += '<h2>Unidades leídas por hora</h2><div class="km-card">';
            if (!ph.length) {
                h += '<p class="km-nota">Todavía no hay lecturas.</p>';
            }
            phOut.forEach(function (x) {
                var totalVisible = 0;
                var segmentos = x[1].filter(function (o) { return visibles[o.id]; });
                segmentos.forEach(function (o) { totalVisible += o.u; });
                if (!segmentos.length) { return; }
                var barra = segmentos.map(function (o) {
                    return '<i title="' + e(o.out + ' · ' + o.tienda + ': ' + n(o.u) + ' u') + '" style="width:' + (100 * o.u / max) + '%;background:' + outColor(o) + '"></i>';
                }).join('');
                h += '<div class="km-hora"><span>' + (x[0] < 10 ? '0' : '') + x[0] + 'h</span><span class="km-barra km-hora-stack">' + barra + '</span><b>' + n(totalVisible) + '</b></div>';
            });
            var leyOut = {};
            Dvisible.forEach(function (o) { leyOut[o.id] = o; });
            var leyKeys = Object.keys(leyOut).sort(function (a, b) { return knum(leyOut[a].tienda) - knum(leyOut[b].tienda) || String(leyOut[a].out).localeCompare(String(leyOut[b].out)); });
            if (leyKeys.length) {
                h += '<div class="km-out-ley">' + leyKeys.map(function (id) {
                    var o = leyOut[id];
                    return '<span><i style="background:' + outColor(o) + '"></i>' + e(kno(o.tienda) || o.out) + '</span>';
                }).join('') + '</div>';
            }
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
