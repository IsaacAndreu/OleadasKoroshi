odoo.define('koroshi_juntar_cajas.Pantalla', function (require) {
'use strict';
/* KOROSHI Juntar cajas v1.0.0 - pantalla de la PDA (área Expediciones).
 * 1. Tarjeta (la misma que en Lecturas, Contenedores, Prenda en el suelo...: koroshi_base.comun.tarjeta).
 * 2. Leer la CJ pequeña (se pueden añadir más con «+ Otra caja pequeña»).
 * 3. Leer la CJ destino: /previa enseña pedido, tienda, «Bultos N -> N-1», errores y avisos (no cambia nada).
 * 4. «Juntar»: /juntar con un token (contra el doble toque). Todo o nada.
 * El campo lee cuando el lector para 150 ms (las PDA no mandan Intro); con «⌨ Escribir» espera al Intro.
 * Todo dentro de .o_koroshi_juntar_cajas. Sin aria-hidden (Odoo 13 lo oculta). */
var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var comun = require('koroshi_base.comun');

var REPETIDA_MS = 700;       // la misma lectura llega por el bus y por el campo: se descarta la copia
var PERSONA_MS = 3600000;    // tarjeta sin actividad: parámetro koroshi_operarios.minutos_tarjeta (60 por defecto)

function _e(t) { return _.escape(t == null ? '' : String(t)); }
function _uds(n) { return (n || 0) + ' ud' + (n === 1 ? '' : 's'); }
function _token() { return Date.now() + '-' + Math.random().toString(36).slice(2, 10); }

var JuntarCajas = AbstractAction.extend({
    contentTemplate: 'koroshi_juntar_cajas.Pantalla',
    events: {
        'keydown .o_kjc_codigo': '_onKeydown',
        'input .o_kjc_codigo': '_onEscribe',
        'click .o_kjc_teclado': '_onTeclado',
        'click .o_kjc_juntar': '_onJuntar',
        'click .o_kjc_otra': '_onOtra',
        'click .o_kjc_mas': '_onMas',
        'click .o_kjc_quitar': '_onQuitar',
    },

    init: function () {
        this._super.apply(this, arguments);
        this.ocupado = false;
        this.teclado = false;
        this.ultima = {codigo: '', t: 0, fuente: ''};
        this.persona = null;       // {id, nombre}
        this.actividadEn = Date.now();
        this._vaciar();
    },

    _vaciar: function () {
        this.paso = 'pequena';     // 'pequena' | 'destino'
        this.pequenas = [];        // info de /leer de cada CJ pequeña
        this.cajasPedido = [];     // las cajas del pedido de la primera CJ leída
        this.destino = '';         // CJ destino leída
        this.previa = null;        // respuesta de /previa
        this.hecho = null;         // respuesta de /juntar
        this.token = _token();
    },

    start: function () {
        var self = this;
        core.bus.on('barcode_scanned', this, this._onBarcodeScanned);
        return this._super.apply(this, arguments).then(function () {
            self._tomarGuardada();
            self._leerMinutosTarjeta();
            self.timer = setInterval(self._vigilar.bind(self), 10000);
            self._pintar();
            self._foco();
        });
    },

    on_attach_callback: function () {
        this._super.apply(this, arguments);
        if (this._tomarGuardada()) { this._pintar(); }
        this._foco();
    },

    destroy: function () {
        core.bus.off('barcode_scanned', this, this._onBarcodeScanned);
        clearInterval(this.timer);
        comun.cancelarLector(this);
        this._super.apply(this, arguments);
    },

    // ------------------------------------------------------------------ tarjeta (compartida con las otras pantallas)
    _guardada: function () { return comun.tarjeta.leer(); },
    _guardarPersona: function () {
        if (!this.persona) { return; }
        this.guardadaEn = comun.tarjeta.guardar(this.persona);
    },
    _tomarGuardada: function () {
        var g = this._guardada();
        if (!comun.tarjeta.vigente(g, PERSONA_MS) || (this.persona && this.persona.id === g.id)) { return false; }
        this.persona = {id: g.id, nombre: g.nombre};
        this.actividadEn = g.t || Date.now();
        return true;
    },
    _actividad: function () {
        this.actividadEn = Date.now();
        if (this.persona && (!this.guardadaEn || this.actividadEn - this.guardadaEn > 30000)) {
            var g = this._guardada();
            if (!g || g.id === this.persona.id) { this._guardarPersona(); }
        }
    },
    _leerMinutosTarjeta: function () {
        var self = this;
        return comun.tarjeta.minutos(this).then(function (minutos) {
            if (minutos > 0) {
                PERSONA_MS = minutos * 60000;
                if (!self.persona && self._tomarGuardada()) { self._pintar(); }
            }
        });
    },
    _vigilar: function () {
        var g = this._guardada();
        if (this.persona && g && g.id === this.persona.id && g.t && g.t > this.actividadEn) {
            this.actividadEn = g.t;
        }
        if (this.persona && Date.now() - this.actividadEn > PERSONA_MS) {
            this.persona = null;
            this._pintar();
        }
    },

    // ------------------------------------------------------------------ lectura
    _foco: function () {
        var $c = this.$('.o_kjc_codigo');
        if ($c.length && document.activeElement !== $c[0]) { $c.focus(); }
    },

    _onKeydown: function (ev) {
        if (comun.esFinDeLectura(ev)) {     // Intro o tabulador
            ev.preventDefault();
            comun.cancelarLector(this);
            var codigo = (ev.currentTarget.value || '').trim();
            ev.currentTarget.value = '';
            if (this.teclado) { this._ponerTeclado(false); }
            this._leer(codigo, 'campo');
        }
    },

    // sin «⌨ Escribir» lo que entra es el lector: se lee cuando para (las PDA no mandan Intro)
    _onEscribe: function (ev) {
        var self = this;
        if (this.teclado) { return comun.cancelarLector(this); }
        comun.leerAlParar(this, ev.currentTarget, function (codigo) { self._leer(codigo, 'campo'); });
    },

    _onBarcodeScanned: function (codigo) { this._leer(codigo, 'bus'); },

    _ponerTeclado: function (si) {
        this.teclado = si;
        var $c = this.$('.o_kjc_codigo');
        $c.attr('inputmode', si ? null : 'none');
        this.$('.o_kjc_teclado').toggleClass('o_kjc_teclado_on', si).text(si ? '⌨ Ocultar' : '⌨ Escribir');
        $c.blur();
        $c.focus();
    },

    _onTeclado: function () { this._ponerTeclado(!this.teclado); },

    _aviso: function (tipo, msg) {
        this.$('.o_kjc_aviso').removeClass('o_kjc_ok o_kjc_mal o_kjc_info').addClass(
            msg ? 'o_kjc_' + (tipo || 'info') : '').text(msg || '');
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

    _llamar: function (ruta, params) {
        var self = this;
        this.ocupado = true;
        return this._rpc({route: ruta, params: params}).then(function (r) {
            self.ocupado = false;
            return r || {ok: false, msg: 'Sin respuesta de Odoo.'};
        }, function () {
            self.ocupado = false;
            self._pitido(false);
            self._aviso('mal', 'Sin conexión con Odoo. Vuelve a leerlo.');
            self._pintar();
            return {ok: false, sinConexion: true};
        });
    },

    _leer: function (codigo, fuente) {
        var self = this;
        codigo = (codigo || '').trim();
        if (!codigo) { return; }
        var t = Date.now();
        if (codigo === this.ultima.codigo && t - this.ultima.t < REPETIDA_MS && fuente !== this.ultima.fuente) {
            return;
        }
        this.ultima = {codigo: codigo, t: t, fuente: fuente};
        if (this.ocupado) {
            this._pitido(false);
            return this._aviso('mal', 'Espera un momento: ' + codigo + ' NO se ha leído.');
        }
        this._actividad();
        if (this.hecho) {   // después de una junta, la siguiente lectura empieza otra
            this._vaciar();
        }
        if (this.paso === 'destino' && comun.esMatricula(codigo)) {
            return this._leerDestino(codigo.toUpperCase());
        }
        this._aviso('info', 'Leyendo ' + codigo + '…');
        return this._llamar('/koroshi/juntar_cajas/leer', {codigo: codigo}).then(function (r) {
            if (r.sinConexion) { return; }
            if (!r.ok) {
                self._pitido(false);
                return self._aviso('mal', r.msg || 'Error');
            }
            self._pitido(true);
            if (r.tipo === 'persona') {
                self.persona = r.persona;
                self._guardarPersona();
                self._aviso('ok', 'Hola, ' + r.persona.nombre + '.');
                return self._pintar();
            }
            // una CJ en el paso «pequeña»
            if (_.findWhere(self.pequenas, {cj: r.cj})) {
                self._pitido(false);
                return self._aviso('mal', r.cj + ' ya está leída.');
            }
            if (self.pequenas.length && r.pedido !== self.pequenas[0].pedido) {
                self._pitido(false);
                return self._aviso('mal', r.cj + ' es de ' + r.pedido + ' y las otras de ' + self.pequenas[0].pedido +
                    '. NO se ha añadido.');
            }
            self.pequenas.push(r);
            if (!self.cajasPedido.length) { self.cajasPedido = r.cajas_pedido || []; }
            self.paso = 'destino';
            self._aviso('ok', r.cj + ' leída. Ahora lee la caja DESTINO (donde la metes).');
            self._pintar();
        });
    },

    _leerDestino: function (cj) {
        var self = this;
        this.destino = cj;
        this.previa = null;
        this._aviso('info', 'Mirando ' + cj + '…');
        return this._llamar('/koroshi/juntar_cajas/previa', {
            pequenas: _.pluck(this.pequenas, 'cj'), destino: cj,
        }).then(function (r) {
            if (r.sinConexion) { return; }
            if (r.msg && !r.errores) {   // UserError de la ruta
                self._pitido(false);
                self.destino = '';
                self._pintar();
                return self._aviso('mal', r.msg);
            }
            self.previa = r;
            self.token = _token();
            self._pitido(r.ok);
            self._aviso(r.ok ? (r.avisos && r.avisos.length ? 'info' : 'ok') : 'mal',
                r.ok ? 'Revisa y pulsa «Juntar».' : 'No se puede juntar. No se ha cambiado nada.');
            self._pintar();
            window.scrollTo(0, 0);
        });
    },

    // ------------------------------------------------------------------ botones
    _onJuntar: function () {
        var self = this;
        if (this.ocupado || !this.previa || !this.previa.ok) { return; }
        if (!this.persona) {
            this._pitido(false);
            return this._aviso('mal', 'Pasa antes tu tarjeta de operario.');
        }
        this.$('.o_kjc_juntar').prop('disabled', true).text('Juntando…');
        return this._llamar('/koroshi/juntar_cajas/juntar', {
            pequenas: _.pluck(this.pequenas, 'cj'), destino: this.destino,
            employee_id: this.persona.id, token: this.token,
        }).then(function (r) {
            if (r.sinConexion) { return; }
            if (!r.ok) {
                self._pitido(false);
                self._aviso('mal', r.msg || 'Error');
                return self._pintar();
            }
            self._pitido(true);
            self.hecho = r;
            var quitar = (r.pequenas || []).join(', ');
            self._aviso('ok', 'Hecho: ' + r.bultos_antes + ' → ' + r.bultos_despues + ' bultos. Quita la etiqueta de ' +
                quitar + '.' + (r.etiqueta ? '\nOJO: hay que rehacer la etiqueta del transportista.' : ''));
            self._pintar();
            self._foco();
        });
    },

    _onOtra: function () {
        this._vaciar();
        this._aviso('', '');
        this._pintar();
        this._foco();
    },

    _onMas: function () {
        this.paso = 'pequena';
        this.destino = '';
        this.previa = null;
        this._aviso('info', 'Lee la otra caja pequeña.');
        this._pintar();
        this._foco();
    },

    _onQuitar: function (ev) {
        var cj = $(ev.currentTarget).data('cj');
        this.pequenas = _.reject(this.pequenas, function (p) { return p.cj === cj; });
        this.destino = '';
        this.previa = null;
        if (!this.pequenas.length) {
            this._vaciar();
        }
        this._aviso('', '');
        this._pintar();
        this._foco();
    },

    // ------------------------------------------------------------------ pintar
    _pintar: function () {
        this.$('.o_kjc_quien').html(this.persona ? '<b>' + _e(this.persona.nombre) + '</b>' :
            '<span class="o_kjc_rojo">Sin tarjeta: pásala antes de juntar</span>');
        var h;
        if (this.hecho) {
            h = this._htmlHecho(this.hecho);
        } else if (!this.pequenas.length) {
            h = this._htmlInicio();
        } else {
            h = this._htmlCajas() + (this.previa ? this._htmlPrevia(this.previa) : '') + this._htmlPedido();
        }
        this.$('.o_kjc_cuerpo').html(h + this._htmlBotones());
    },

    _htmlInicio: function () {
        return '<div class="o_kjc_card o_kjc_ayuda"><h3>Meter una caja pequeña dentro de otra</h3>' +
            '<ol><li>Pasa tu <b>tarjeta</b>.</li>' +
            '<li>Lee la <b>caja pequeña</b> (CJ).</li>' +
            '<li>Lee la <b>caja destino</b>, donde la metes. Tienen que ser del mismo pedido y la misma tienda.</li>' +
            '<li>Mete la ropa, pulsa <b>Juntar</b> y quita la etiqueta de la caja pequeña.</li></ol>' +
            '<div class="o_kjc_nota">Si leer la caja destino da un error, no se cambia nada.</div></div>';
    },

    _htmlCajas: function () {
        var p0 = this.pequenas[0];
        var h = '<div class="o_kjc_card"><div class="o_kjc_pedido">' + _e(p0.tienda) + ' · ' + _e(p0.pedido) +
            '</div>';
        this.pequenas.forEach(function (p) {
            h += '<div class="o_kjc_caja">Pequeña: <b>' + _e(p.cj) + '</b> (' + _uds(p.uds) + ', ' + _e(p.zonas) +
                (p.validada ? '' : ', <span class="o_kjc_rojo">OUT sin validar</span>') + ')' +
                '<button type="button" class="o_kjc_quitar" data-cj="' + _e(p.cj) + '">✕</button></div>';
        });
        if (this.paso === 'destino') {
            h += '<div class="o_kjc_flecha">↓</div>';
            h += this.destino ? '<div class="o_kjc_caja">Destino: <b>' + _e(this.destino) + '</b>' +
                (this.previa && this.previa.destino ? ' (' + _uds(this.previa.destino.uds) + ', ' +
                    _e(this.previa.destino.zonas) + ')' : '') + '</div>' :
                '<div class="o_kjc_paso">Lee la caja DESTINO</div>';
        } else {
            h += '<div class="o_kjc_paso">Lee la otra caja pequeña</div>';
        }
        return h + '</div>';
    },

    _htmlPrevia: function (r) {
        var h = '<div class="o_kjc_card">';
        if (r.ok) {
            h += '<div class="o_kjc_bultos">Bultos del pedido: ' + r.bultos_antes + ' → ' + r.bultos_despues + '</div>';
        }
        (r.errores || []).forEach(function (e) { h += '<div class="o_kjc_rojo">✖ ' + _e(e) + '</div>'; });
        (r.avisos || []).forEach(function (a) { h += '<div class="o_kjc_rojo">⚠ ' + _e(a) + '</div>'; });
        return h + '</div>';
    },

    _htmlPedido: function () {
        var self = this;
        if (this.cajasPedido.length < 2) { return ''; }
        var filas = this.cajasPedido.map(function (c) {
            var leida = _.findWhere(self.pequenas, {cj: c.cj}) || c.cj === self.destino;
            return '<li' + (c.pequena ? ' class="o_kjc_peq"' : '') + '>' + _e(c.cj) + ': ' + _uds(c.uds) +
                (c.zonas ? ' (' + _e(c.zonas) + ')' : '') + (c.pequena ? ' · pequeña' : '') +
                (leida ? ' ✔' : '') + '</li>';
        });
        return '<div class="o_kjc_card"><div class="o_kjc_nota">Cajas del pedido (' + this.cajasPedido.length +
            '):</div><ul class="o_kjc_lista">' + filas.join('') + '</ul></div>';
    },

    _htmlHecho: function (r) {
        return '<div class="o_kjc_card"><h3>✔ Juntadas</h3><div class="o_kjc_pedido">' + _e(r.tienda || '') +
            ' · ' + _e(r.pedido) + '</div><div class="o_kjc_caja">' + _e((r.pequenas || []).join(', ')) + ' → ' +
            _e(r.destino || '') + '</div><div class="o_kjc_bultos">Bultos: ' + r.bultos_antes + ' → ' +
            r.bultos_despues + '</div>' +
            (r.etiqueta ? '<div class="o_kjc_rojo">⚠ El pedido ya tenía etiqueta del transportista: avisa a la ' +
                'oficina para rehacerla.</div>' : '') +
            '<div class="o_kjc_nota">Quita la etiqueta de la caja pequeña. Lee otra caja para seguir.</div></div>';
    },

    _htmlBotones: function () {
        if (this.hecho || !this.pequenas.length) { return ''; }
        var puede = this.previa && this.previa.ok;
        var h = '<div class="o_kjc_botones">';
        if (puede) {
            h += '<button type="button" class="o_kjc_juntar"' + (this.ocupado ? ' disabled="disabled"' : '') +
                '>Juntar</button>';
        }
        if (this.paso === 'destino') {
            h += '<button type="button" class="o_kjc_mas">+ Otra caja pequeña</button>';
        }
        h += '<button type="button" class="o_kjc_otra">Otra</button></div>';
        return h;
    },
});

core.action_registry.add('koroshi_juntar_cajas', JuntarCajas);

/* v1.1.0: «Revisar caja» (área Expediciones). Misma tarjeta, lector y aspecto que «Juntar cajas».
 * 1. Leer la CJ: lo que hay dentro según Odoo, por artículo.
 * 2. Leer las prendas de la caja que se revisa: verde si están en esa CJ («1 de 3»), rojo si no (no cuentan).
 * 3. «Todo bien» (solo se apunta) o «Pasar lo leído a otra CJ» -> leer la CJ pegada en esa caja -> previa -> «Pasar».
 * Solo líneas enteras: nunca se toca el stock de los huecos (ver models/juntar.py, _mover_lineas). */
var RevisarCaja = JuntarCajas.extend({
    contentTemplate: 'koroshi_juntar_cajas.Revisar',
    events: {   // sin los botones de «Juntar» (Juntar, + Otra caja pequeña, ✕)
        'keydown .o_kjc_codigo': '_onKeydown',
        'input .o_kjc_codigo': '_onEscribe',
        'click .o_kjc_teclado': '_onTeclado',
        'click .o_kjc_otra': '_onOtra',
        'click .o_kjc_deshacer': '_onDeshacer',
        'click .o_kjc_bien': '_onBien',
        'click .o_kjc_a_otra': '_onAOtra',
        'click .o_kjc_pasar': '_onPasar',
        'click .o_kjc_volver': '_onVolver',
    },

    _vaciar: function () {
        this.paso = 'caja';        // 'caja' | 'prendas' | 'nueva'
        this.caja = null;          // respuesta de /revisar_caja/caja
        this.leidas = {};          // product_id -> uds leídas
        this.historial = [];       // product_id de cada lectura buena (para deshacer)
        this.nueva = '';
        this.previa = null;
        this.hecho = null;
        this.token = _token();
    },

    _totalLeidas: function () {
        return _.reduce(_.values(this.leidas), function (a, b) { return a + b; }, 0);
    },

    _leidasLista: function () {
        return _.map(this.leidas, function (n, pid) { return {product_id: parseInt(pid, 10), uds: n}; });
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
            return this._aviso('mal', 'Espera un momento: ' + codigo + ' NO se ha leído.');
        }
        this._actividad();
        if (this.hecho) { this._vaciar(); }
        var cj = comun.esMatricula(codigo);
        if (this.paso === 'caja' || (cj && this.paso === 'prendas' && !this._totalLeidas())) {
            return this._leerCaja(codigo);
        }
        if (cj) {   // con prendas leídas, una CJ es la CJ nueva
            return this._leerNueva(codigo.toUpperCase());
        }
        return this._leerPrenda(codigo);
    },

    _leerCaja: function (codigo) {
        var self = this;
        this._aviso('info', 'Leyendo ' + codigo + '…');
        return this._llamar('/koroshi/revisar_caja/caja', {codigo: codigo}).then(function (r) {
            if (r.sinConexion) { return; }
            if (!r.ok) { self._pitido(false); return self._aviso('mal', r.msg || 'Error'); }
            self._pitido(true);
            if (r.tipo === 'persona') {
                self.persona = r.persona;
                self._guardarPersona();
                self._aviso('ok', 'Hola, ' + r.persona.nombre + '.');
                return self._pintar();
            }
            self._vaciar();
            self.caja = r;
            self.paso = 'prendas';
            self._aviso(r.bloqueo ? 'mal' : 'ok', r.bloqueo ? 'Pedido ' + r.bloqueo + ': solo se puede mirar.' :
                r.cj + ': ' + _uds(r.uds) + '. Lee las prendas de la caja que revisas.');
            self._pintar();
        });
    },

    _leerPrenda: function (codigo) {
        var self = this;
        if (this.paso === 'nueva') {   // otra prenda: se vuelve a leer prendas
            this.paso = 'prendas';
            this.nueva = '';
            this.previa = null;
        }
        return this._llamar('/koroshi/revisar_caja/prenda', {cj: this.caja.cj, codigo: codigo}).then(function (r) {
            if (r.sinConexion) { return; }
            if (!r.ok) { self._pitido(false); return self._aviso('mal', r.msg || 'Error'); }
            if (r.tipo === 'persona') {
                self._pitido(true);
                self.persona = r.persona;
                self._guardarPersona();
                self._aviso('ok', 'Hola, ' + r.persona.nombre + '.');
                return self._pintar();
            }
            var p = _.findWhere(self.caja.productos, {product_id: r.product_id});
            var ya = self.leidas[r.product_id] || 0;
            if (!p || ya >= p.uds) {
                self._pitido(false);
                return self._aviso('mal', 'Ya has leído las ' + (p ? p.uds : 0) + ' de ' + r.nombre + ' que hay en ' +
                    self.caja.cj + '. Esta NO cuenta.');
            }
            self._pitido(true);
            self.leidas[r.product_id] = ya + 1;
            self.historial.push(r.product_id);
            self._aviso('ok', r.nombre + ': ' + (ya + 1) + ' de ' + p.uds + '.');
            self._pintar();
        });
    },

    _leerNueva: function (cj) {
        var self = this;
        this.paso = 'nueva';
        this.nueva = cj;
        this.previa = null;
        this._aviso('info', 'Mirando ' + cj + '…');
        return this._llamar('/koroshi/revisar_caja/previa', {
            cj: this.caja.cj, nueva: cj, leidas: this._leidasLista(),
        }).then(function (r) {
            if (r.sinConexion) { return; }
            if (r.msg && !r.errores) {
                self._pitido(false);
                self.nueva = '';
                self._pintar();
                return self._aviso('mal', r.msg);
            }
            self.previa = r;
            self.token = _token();
            self._pitido(r.ok);
            self._aviso(r.ok ? (r.avisos && r.avisos.length ? 'info' : 'ok') : 'mal',
                r.ok ? 'Revisa y pulsa «Pasar».' : 'No se puede pasar. No se ha cambiado nada.');
            self._pintar();
            window.scrollTo(0, 0);
        });
    },

    // ------------------------------------------------------------------ botones
    _onDeshacer: function () {
        var pid = this.historial.pop();
        if (!pid) { return; }
        this.leidas[pid] -= 1;
        if (!this.leidas[pid]) { delete this.leidas[pid]; }
        this.paso = 'prendas';
        this.nueva = '';
        this.previa = null;
        this._aviso('info', 'Quitada la última lectura.');
        this._pintar();
        this._foco();
    },

    _onAOtra: function () {
        this.paso = 'nueva';
        this._aviso('info', 'Lee la CJ pegada en la caja que has revisado.');
        this._pintar();
        this._foco();
    },

    _onVolver: function () {
        this.paso = 'prendas';
        this.nueva = '';
        this.previa = null;
        this._aviso('', '');
        this._pintar();
        this._foco();
    },

    _onBien: function () {
        var self = this;
        if (this.ocupado || !this.caja) { return; }
        if (!this.persona) { this._pitido(false); return this._aviso('mal', 'Pasa antes tu tarjeta de operario.'); }
        return this._llamar('/koroshi/revisar_caja/bien', {
            cj: this.caja.cj, leidas_uds: this._totalLeidas(), employee_id: this.persona.id,
        }).then(function (r) {
            if (r.sinConexion) { return; }
            if (!r.ok) { self._pitido(false); return self._aviso('mal', r.msg || 'Error'); }
            self._pitido(true);
            self._vaciar();
            self._aviso('ok', 'Apuntado: ' + r.cj + ' revisada (' + r.leidas + ' de ' + r.uds + ' uds leídas).');
            self._pintar();
            self._foco();
        });
    },

    _onPasar: function () {
        var self = this;
        if (this.ocupado || !this.previa || !this.previa.ok) { return; }
        if (!this.persona) { this._pitido(false); return this._aviso('mal', 'Pasa antes tu tarjeta de operario.'); }
        this.$('.o_kjc_pasar').prop('disabled', true).text('Pasando…');
        return this._llamar('/koroshi/revisar_caja/partir', {
            cj: this.caja.cj, nueva: this.nueva, leidas: this._leidasLista(),
            employee_id: this.persona.id, token: this.token,
        }).then(function (r) {
            if (r.sinConexion) { return; }
            if (!r.ok) { self._pitido(false); self._aviso('mal', r.msg || 'Error'); return self._pintar(); }
            self._pitido(true);
            self.hecho = r;
            self._aviso('ok', 'Hecho: ' + r.cj + ' ' + _uds(r.quedan) + ' · ' + r.nueva + ' ' + _uds(r.pasan) +
                '. Bultos ' + r.bultos_antes + ' → ' + r.bultos_despues + '.' +
                (r.etiqueta ? '\nOJO: hay que hacer la etiqueta del transportista del bulto nuevo.' : ''));
            self._pintar();
            self._foco();
        });
    },

    // ------------------------------------------------------------------ pintar
    _pintar: function () {
        this.$('.o_kjc_quien').html(this.persona ? '<b>' + _e(this.persona.nombre) + '</b>' :
            '<span class="o_kjc_rojo">Sin tarjeta: pásala antes de cambiar nada</span>');
        var h;
        if (this.hecho) {
            h = this._htmlHechoRevisar(this.hecho);
        } else if (!this.caja) {
            h = this._htmlAyudaRevisar();
        } else {
            h = this._htmlCaja() + (this.paso === 'nueva' ? this._htmlNueva() : '');
        }
        this.$('.o_kjc_cuerpo').html(h + this._htmlBotonesRevisar());
    },

    _htmlAyudaRevisar: function () {
        return '<div class="o_kjc_card o_kjc_ayuda"><h3>Revisar una caja</h3>' +
            '<ol><li>Pasa tu <b>tarjeta</b>.</li>' +
            '<li>Lee la <b>CJ</b> que tiene las prendas en Odoo: verás lo que hay dentro.</li>' +
            '<li>Lee las <b>prendas</b> de la caja que revisas. Verde: están en esa CJ. Rojo: no cuentan.</li>' +
            '<li><b>Todo bien</b>, o <b>Pasar lo leído a otra CJ</b> y lee la CJ pegada en esa caja.</li></ol>' +
            '<div class="o_kjc_nota">Las prendas pasan de caja sin tocar el stock de los huecos.</div></div>';
    },

    _htmlCaja: function () {
        var self = this;
        var c = this.caja;
        var filas = c.productos.map(function (p) {
            var n = self.leidas[p.product_id] || 0;
            return '<li' + (n ? ' class="o_kjc_peq"' : '') + '>' + _e(p.nombre) + ': ' +
                (n ? '<b>' + n + ' de ' + p.uds + '</b>' : _uds(p.uds)) + '</li>';
        });
        return '<div class="o_kjc_card"><div class="o_kjc_pedido">' + _e(c.tienda) + ' · ' + _e(c.pedido) +
            '</div><div class="o_kjc_caja"><b>' + _e(c.cj) + '</b>: ' + _uds(c.uds) + ' (' + _e(c.zonas) + ')' +
            '</div><div class="o_kjc_bultos">Leídas: ' + this._totalLeidas() + ' de ' + c.uds + '</div>' +
            '<ul class="o_kjc_lista">' + filas.join('') + '</ul></div>';
    },

    _htmlNueva: function () {
        var h = '<div class="o_kjc_card">';
        if (!this.nueva) {
            return h + '<div class="o_kjc_paso">Lee la CJ pegada en la caja revisada</div></div>';
        }
        h += '<div class="o_kjc_caja">' + _e(this.caja.cj) + ' → <b>' + _e(this.nueva) + '</b></div>';
        var r = this.previa;
        if (r && r.ok) {
            h += '<div class="o_kjc_caja">Pasan ' + _uds(r.pasan) + '; en ' + _e(this.caja.cj) + ' quedan ' +
                _uds(r.quedan) + '.' + (r.nueva_existe ? '' : ' (' + _e(this.nueva) + ' es nueva en Odoo)') +
                '</div><div class="o_kjc_bultos">Bultos del pedido: ' + r.bultos_antes + ' → ' + r.bultos_despues +
                '</div>';
        }
        ((r && r.errores) || []).forEach(function (e) { h += '<div class="o_kjc_rojo">✖ ' + _e(e) + '</div>'; });
        ((r && r.avisos) || []).forEach(function (a) { h += '<div class="o_kjc_rojo">⚠ ' + _e(a) + '</div>'; });
        return h + '</div>';
    },

    _htmlHechoRevisar: function (r) {
        return '<div class="o_kjc_card"><h3>✔ Pasadas</h3><div class="o_kjc_pedido">' + _e(r.tienda || '') + ' · ' +
            _e(r.pedido) + '</div><div class="o_kjc_caja">' + _e(r.cj) + ': ' + _uds(r.quedan) + ' · ' +
            _e(r.nueva) + ': ' + _uds(r.pasan) + '</div><div class="o_kjc_bultos">Bultos: ' + r.bultos_antes +
            ' → ' + r.bultos_despues + '</div>' +
            (r.etiqueta ? '<div class="o_kjc_rojo">⚠ El pedido ya tenía etiqueta del transportista: avisa a la ' +
                'oficina para hacer la del bulto nuevo.</div>' : '') +
            '<div class="o_kjc_nota">Lee otra caja para seguir.</div></div>';
    },

    _htmlBotonesRevisar: function () {
        if (this.hecho || !this.caja) { return ''; }
        var h = '<div class="o_kjc_botones">';
        var hay = this._totalLeidas() > 0;
        if (this.paso === 'nueva' && this.previa && this.previa.ok) {
            h += '<button type="button" class="o_kjc_verde o_kjc_pasar">Pasar</button>';
        }
        if (this.paso === 'nueva') {
            h += '<button type="button" class="o_kjc_volver">Seguir leyendo</button>';
        } else if (!this.caja.bloqueo) {
            if (hay) { h += '<button type="button" class="o_kjc_a_otra">Pasar lo leído a otra CJ</button>'; }
            h += '<button type="button" class="o_kjc_bien">Todo bien</button>';
        }
        if (hay) { h += '<button type="button" class="o_kjc_deshacer">Deshacer</button>'; }
        h += '<button type="button" class="o_kjc_otra">Otra caja</button></div>';
        return h;
    },
});

core.action_registry.add('koroshi_revisar_caja', RevisarCaja);
return JuntarCajas;
});
