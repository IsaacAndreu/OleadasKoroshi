odoo.define('koroshi_recuentos.Referencia', function (require) {
'use strict';
/* KOROSHI Recuentos v1.0.0 - pantalla «Referencia» de la PDA (fase 1, SOLO LECTURA).
 * Se lee o se escribe una referencia (2621XC04), una variante (2621XC04-000014-42) o una prenda (EAN):
 *   - arriba, la tabla color x talla con lo que dice Odoo (en rojo lo negativo, entre paréntesis lo reservado);
 *   - debajo, los sitios (hueco y contenedor) en orden de recorrido, con lo que dice Odoo de cada variante;
 *     en naranja los sitios donde se quitó stock a mano en los últimos 90 días (aunque Odoo diga 0).
 * Tocar un sitio enseña todo lo que Odoo dice que hay en él. No cambia nada: no hay que pasar la tarjeta.
 * Todo dentro de .o_koroshi_recuentos. Sin aria-hidden (Odoo 13 lo oculta). */
var AbstractAction = require('web.AbstractAction');
var core = require('web.core');

var REPETIDA_MS = 700;       // la misma lectura llega por el bus y por el campo: se descarta la copia

function _e(t) { return _.escape(t == null ? '' : String(t)); }
function _n(x) { return (Math.round((x || 0) * 100) / 100).toString().replace('.', ','); }

var Referencia = AbstractAction.extend({
    contentTemplate: 'koroshi_recuentos.Referencia',
    events: {
        'keydown .o_kr_codigo': '_onKeydown',
        'click .o_kr_teclado': '_onTeclado',
        'click .o_kr_atras': '_onAtras',
        'click .o_kr_vaciar': '_onVaciar',
        'click .o_kr_modelo': '_onModelo',
        'click .o_kr_sitio': '_onSitio',
    },

    init: function () {
        this._super.apply(this, arguments);
        this.pila = [];          // pantallas anteriores (para «Atrás»): {tipo, datos}
        this.actual = null;      // {tipo: 'modelos'|'referencia'|'caja', datos}
        this.ocupado = false;
        this.teclado = false;
        this.ultima = {codigo: '', t: 0, fuente: ''};
    },

    start: function () {
        var self = this;
        core.bus.on('barcode_scanned', this, this._onBarcodeScanned);
        return this._super.apply(this, arguments).then(function () {
            self._pintar();
            self._foco();
        });
    },

    destroy: function () {
        core.bus.off('barcode_scanned', this, this._onBarcodeScanned);
        this._super.apply(this, arguments);
    },

    // ------------------------------------------------------------------ lectura
    _foco: function () {
        var $c = this.$('.o_kr_codigo');
        if ($c.length && document.activeElement !== $c[0]) { $c.focus(); }
    },

    _onKeydown: function (ev) {
        if (ev.which === 13) {
            ev.preventDefault();
            var codigo = (ev.currentTarget.value || '').trim();
            ev.currentTarget.value = '';
            if (this.teclado) { this._ponerTeclado(false); }
            this._leer(codigo, 'campo');
        }
    },

    _onBarcodeScanned: function (codigo) { this._leer(codigo, 'bus'); },

    _ponerTeclado: function (si) {
        this.teclado = si;
        var $c = this.$('.o_kr_codigo');
        $c.attr('inputmode', si ? null : 'none');
        this.$('.o_kr_teclado').toggleClass('o_kr_teclado_on', si).text(si ? '⌨ Ocultar' : '⌨ Escribir');
        $c.blur();
        $c.focus();
    },

    _onTeclado: function () { this._ponerTeclado(!this.teclado); },

    _aviso: function (tipo, msg) {
        this.$('.o_kr_aviso').removeClass('o_kr_ok o_kr_mal o_kr_info').addClass(
            msg ? 'o_kr_' + (tipo || 'info') : '').text(msg || '');
    },

    _pitido: function (bien) {
        try {
            var Ctx = window.AudioContext || window.webkitAudioContext;
            if (!Ctx) { return; }
            this.audio = this.audio || new Ctx();
            var a = this.audio;
            (bien ? [0] : [0, 0.18]).forEach(function (t0) {
                var o = a.createOscillator();
                var g = a.createGain();
                o.frequency.value = bien ? 1200 : 300;
                g.gain.value = 0.2;
                o.connect(g);
                g.connect(a.destination);
                o.start(a.currentTime + t0);
                o.stop(a.currentTime + t0 + 0.12);
            });
        } catch (e) { /* sin sonido */ }
    },

    _leer: function (codigo, fuente) {
        codigo = (codigo || '').trim();
        if (!codigo) { return; }
        var t = Date.now();
        if (codigo === this.ultima.codigo && t - this.ultima.t < REPETIDA_MS && fuente !== this.ultima.fuente) {
            return;
        }
        this.ultima = {codigo: codigo, t: t, fuente: fuente};
        if (this.ocupado) {
            this._pitido(false);
            return this._aviso('mal', 'Espera a que acabe: ' + codigo + ' NO se ha leído. Vuelve a leerlo.');
        }
        return this._buscar(codigo, true);
    },

    _buscar: function (texto, nueva) {
        var self = this;
        this.ocupado = true;
        this._aviso('info', 'Buscando ' + texto + '…');
        return this._rpc({route: '/koroshi/recuentos/referencia', params: {texto: texto}}).then(function (r) {
            self.ocupado = false;
            if (r.error) {
                self._pitido(false);
                return self._aviso('mal', r.error);
            }
            self._pitido(true);
            self._aviso('', '');
            self._ir({tipo: r.tipo, datos: r}, nueva);
        }, function () {
            self.ocupado = false;
            self._pitido(false);
            self._aviso('mal', 'Sin conexión con Odoo. Vuelve a probar.');
        });
    },

    // ------------------------------------------------------------------ navegación
    _ir: function (pantalla, nueva) {
        if (nueva) { this.pila = []; } else if (this.actual) { this.pila.push(this.actual); }
        this.actual = pantalla;
        this._pintar();
        this._foco();
        window.scrollTo(0, 0);
    },

    _onAtras: function () {
        this.actual = this.pila.length ? this.pila.pop() : null;
        this._aviso('', '');
        this._pintar();
        this._foco();
    },

    _onVaciar: function () {
        this.pila = [];
        this.actual = null;
        this._aviso('', '');
        this._pintar();
        this._foco();
    },

    _onModelo: function (ev) {
        var modelo = $(ev.currentTarget).data('modelo');
        if (!this.ocupado && modelo) { this._buscar(String(modelo), false); }
    },

    _onSitio: function (ev) {
        var self = this;
        var id = $(ev.currentTarget).data('id');
        if (this.ocupado || !id) { return; }
        var modelo = this.actual && this.actual.datos && this.actual.datos.modelo || '';
        this.ocupado = true;
        return this._rpc({route: '/koroshi/recuentos/caja', params: {ubicacion_id: id, modelo: modelo}}).then(function (r) {
            self.ocupado = false;
            if (r.error) { self._pitido(false); return self._aviso('mal', r.error); }
            self._aviso('', '');
            self._ir({tipo: 'caja', datos: r}, false);
        }, function () {
            self.ocupado = false;
            self._aviso('mal', 'Sin conexión con Odoo. Vuelve a probar.');
        });
    },

    // ------------------------------------------------------------------ pintar
    _pintar: function () {
        var a = this.actual;
        var html;
        if (!a) {
            html = '<div class="o_kr_paso">Lee una prenda o escribe la referencia (⌨ Escribir): 2621XC04</div>' +
                '<div class="o_kr_nota">Solo consulta: enseña lo que dice Odoo de todas las tallas y colores, y ' +
                'dónde. No cambia nada.</div>';
        } else if (a.tipo === 'modelos') {
            html = this._pintarModelos(a.datos);
        } else if (a.tipo === 'caja') {
            html = this._pintarCaja(a.datos);
        } else {
            html = this._pintarReferencia(a.datos);
        }
        this.$('.o_kr_cuerpo').html(html);
        this.$('.o_kr_atras').toggle(!!a);
    },

    _pintarModelos: function (d) {
        return '<div class="o_kr_paso">Hay varias referencias que empiezan por ' + _e(d.texto) + ':</div>' +
            '<div class="o_kr_modelos">' + d.modelos.map(function (m) {
                return '<button type="button" class="o_kr_modelo" data-modelo="' + _e(m) + '">' + _e(m) + '</button>';
            }).join('') + '</div>';
    },

    _celda: function (c) {
        if (!c.existe) { return '<td class="o_kr_n o_kr_no">·</td>'; }
        var cls = c.uds < 0 ? ' o_kr_neg' : (c.uds ? '' : ' o_kr_cero');
        return '<td class="o_kr_n' + cls + '">' + _n(c.uds) +
            (c.reservadas ? '<small> (' + _n(c.reservadas) + ')</small>' : '') + '</td>';
    },

    _pintarReferencia: function (d) {
        var self = this;
        var cab = '<tr><th></th>' + d.tallas.map(function (t) { return '<th>' + _e(t) + '</th>'; }).join('') + '</tr>';
        var filas = d.colores.map(function (c) {
            return '<tr><th>' + _e(c) + '</th>' + d.tallas.map(function (t) {
                return self._celda(d.celdas[c][t]);
            }).join('') + '</tr>';
        }).join('');
        var html = '<div class="o_kr_card"><h3>' + _e(d.modelo) + '</h3>' +
            '<div class="o_kr_sub">' + d.n_variantes + ' variantes · Odoo dice ' + _n(d.total) + ' uds' +
            (d.reservadas ? ' · ' + _n(d.reservadas) + ' reservadas' : '') + ' · ' + _e(d.hora) +
            (d.leida ? '<br/>Leída: ' + _e(d.leida) : '') + '</div>' +
            '<div class="o_kr_tabla"><table class="o_kr_rejilla">' + cab + filas + '</table></div>' +
            '<div class="o_kr_nota">Color en filas, talla en columnas. Entre paréntesis, lo reservado para pedidos. ' +
            'En rojo, lo negativo.</div></div>';
        if (d.ajustes_uds) {
            html += '<div class="o_kr_card o_kr_naranja">Se han quitado a mano ' + _n(d.ajustes_uds) +
                ' uds en los últimos ' + d.dias_ajustes + ' días (ajuste a pérdidas). Los sitios van en naranja.</div>';
        }
        if (!d.sitios.length) {
            return html + '<div class="o_kr_card o_kr_vacio">Odoo no tiene esta referencia en ningún sitio.</div>';
        }
        html += '<div class="o_kr_paso">' + d.sitios.length + ' sitios, en orden de recorrido:</div>';
        html += d.sitios.map(function (s) {
            var cls = 'o_kr_card o_kr_sitio' + (s.ajuste ? ' o_kr_naranja' : '') + (s.negativo ? ' o_kr_rojo' : '');
            var marcas = [];
            if (s.negativo) { marcas.push('<span class="o_kr_marca o_kr_m_rojo">negativo</span>'); }
            if (s.varios_colores) { marcas.push('<span class="o_kr_marca">varios colores</span>'); }
            if (s.solo_ajuste) { marcas.push('<span class="o_kr_marca o_kr_m_naranja">Odoo 0: mirar</span>'); }
            var lineas = s.filas.map(function (f) {
                return '<tr><td>' + _e(f.color) + ' · <b>' + _e(f.talla) + '</b></td><td class="o_kr_n' +
                    (f.uds < 0 ? ' o_kr_neg' : '') + '">' + _n(f.uds) +
                    (f.reservadas ? ' <small>(' + _n(f.reservadas) + ' res.)</small>' : '') + '</td></tr>';
            }).join('');
            var ajuste = s.ajuste ? '<div class="o_kr_ajuste">Quitadas a mano: ' + _n(s.ajuste.uds) + ' uds' +
                (s.ajuste.veces > 1 ? ' (' + s.ajuste.veces + ' veces)' : '') + '. Última: ' + _e(s.ajuste.fecha) +
                ', ' + _e(s.ajuste.que) + (s.ajuste.quien ? ' (' + _e(s.ajuste.quien) + ')' : '') + '</div>' : '';
            return '<div class="' + cls + '" data-id="' + s.id + '">' +
                '<div class="o_kr_sitio_cab"><span class="o_kr_hueco">' + _e(s.hueco) + '</span>' +
                (s.contenedor ? ' <span class="o_kr_cont">· ' + _e(s.contenedor) + '</span>' : '') +
                '<span class="o_kr_uds">' + _n(s.uds) + ' uds</span></div>' + marcas.join(' ') +
                (lineas ? '<table>' + lineas + '</table>' : '') + ajuste + '</div>';
        }).join('');
        return html;
    },

    _pintarCaja: function (d) {
        var lineas = d.filas.map(function (f) {
            return '<tr class="' + (f.de_la_referencia ? 'o_kr_suya' : '') + '"><td>' + _e(f.nombre) + '</td>' +
                '<td class="o_kr_n' + (f.uds < 0 ? ' o_kr_neg' : '') + '">' + _n(f.uds) +
                (f.reservadas ? ' <small>(' + _n(f.reservadas) + ' res.)</small>' : '') + '</td></tr>';
        }).join('');
        if (d.mas) { lineas += '<tr><td colspan="2">… y ' + d.mas + ' más</td></tr>'; }
        return '<div class="o_kr_card"><h3>' + _e(d.hueco) + (d.contenedor ? ' · ' + _e(d.contenedor) : '') + '</h3>' +
            '<div class="o_kr_sub">' + _e(d.hueco_largo) + '</div>' +
            '<div class="o_kr_sub">Odoo dice ' + _n(d.uds) + ' uds de ' + d.referencias + ' artículos. ' +
            'En negrita, los de la referencia buscada.</div>' +
            (lineas ? '<table>' + lineas + '</table>' : '<div class="o_kr_vacio">Odoo no tiene nada aquí.</div>') +
            '</div>';
    },
});

core.action_registry.add('koroshi_recuentos_referencia', Referencia);
return Referencia;
});
