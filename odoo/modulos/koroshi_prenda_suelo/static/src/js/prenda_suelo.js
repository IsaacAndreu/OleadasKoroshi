odoo.define('koroshi_prenda_suelo.Pantalla', function (require) {
'use strict';
/* KOROSHI Prenda en el suelo v1.0.0 - pantalla de la PDA.
 * Se lee la prenda encontrada en el suelo (y, si se quiere, el hueco que se tiene delante: así se sabe quién está más
 * cerca). La PDA da una sola orden (A faltante, B a un compañero, C/D a su hueco, E a la mesa de los jefes) y abajo,
 * en pequeño, las otras opciones. «Hecho» / «No sirve» quedan apuntados en Odoo (Prendas del suelo).
 * La tarjeta es la misma que en Lecturas, Contenedores, Faltante y Referencia (localStorage koroshi_operarios_pda_<uid>).
 * v1.1.0 (23/11, O4): la tarjeta y el lector salen de koroshi_base.comun. El campo también lee cuando el lector para
 *   150 ms (las PDA no mandan Intro), como Contenedores; con «⌨ Escribir» espera al Intro.
 * Todo dentro de .o_koroshi_prenda_suelo. Sin aria-hidden (Odoo 13 lo oculta). */
var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var comun = require('koroshi_base.comun');   // v1.1.0

var REPETIDA_MS = 700;       // la misma lectura llega por el bus y por el campo: se descarta la copia
var PERSONA_MS = 3600000;    // tarjeta sin actividad: parámetro koroshi_operarios.minutos_tarjeta (60 por defecto)
var POSICION_MS = 600000;    // el hueco leído vale 10 min como «estoy aquí»

function _e(t) { return _.escape(t == null ? '' : String(t)); }
function _n(x) { return (Math.round((x || 0) * 100) / 100).toString().replace('.', ','); }

var PrendaSuelo = AbstractAction.extend({
    contentTemplate: 'koroshi_prenda_suelo.Pantalla',
    events: {
        'keydown .o_kps_codigo': '_onKeydown',
        'input .o_kps_codigo': '_onEscribe',     // v1.1.0
        'click .o_kps_teclado': '_onTeclado',
        'click .o_kps_vaciar': '_onVaciar',
        'click .o_kps_hecho': '_onHecho',
        'click .o_kps_nosirve': '_onNoSirve',
        'click .o_kps_encontrada': '_onEncontrada',
        'click .o_kps_quitar_pos': '_onQuitarPosicion',
    },

    init: function () {
        this._super.apply(this, arguments);
        this.ocupado = false;
        this.teclado = false;
        this.ultima = {codigo: '', t: 0, fuente: ''};
        this.persona = null;       // {id, nombre}
        this.posicion = null;      // {id, nombre, t}
        this.res = null;           // la última respuesta de /leer (tipo resultado)
        this.codigoPrenda = '';    // para volver a buscar al leer el hueco después de la prenda
        this.sinFaltantes = false;
        this.actividadEn = Date.now();
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
        comun.cancelarLector(this);   // v1.1.0
        this._super.apply(this, arguments);
    },

    // ------------------------------------------------------------------ tarjeta (compartida con las otras pantallas)
    // v1.1.0: de koroshi_base.comun.tarjeta
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
        if (this.posicion && Date.now() - this.posicion.t > POSICION_MS) {
            this.posicion = null;
            this._pintar();
        }
    },

    // ------------------------------------------------------------------ lectura
    _foco: function () {
        var $c = this.$('.o_kps_codigo');
        if ($c.length && document.activeElement !== $c[0]) { $c.focus(); }
    },

    _onKeydown: function (ev) {
        if (comun.esFinDeLectura(ev)) {     // v1.1.0: Intro o tabulador
            ev.preventDefault();
            comun.cancelarLector(this);
            var codigo = (ev.currentTarget.value || '').trim();
            ev.currentTarget.value = '';
            if (this.teclado) { this._ponerTeclado(false); }
            this._leer(codigo, 'campo');
        }
    },

    // v1.1.0: sin «⌨ Escribir» lo que entra es el lector: se lee cuando para (las PDA no mandan Intro)
    _onEscribe: function (ev) {
        var self = this;
        if (this.teclado) { return comun.cancelarLector(this); }
        comun.leerAlParar(this, ev.currentTarget, function (codigo) { self._leer(codigo, 'campo'); });
    },

    _onBarcodeScanned: function (codigo) { this._leer(codigo, 'bus'); },

    _ponerTeclado: function (si) {
        this.teclado = si;
        var $c = this.$('.o_kps_codigo');
        $c.attr('inputmode', si ? null : 'none');
        this.$('.o_kps_teclado').toggleClass('o_kps_teclado_on', si).text(si ? '⌨ Ocultar' : '⌨ Escribir');
        $c.blur();
        $c.focus();
    },

    _onTeclado: function () { this._ponerTeclado(!this.teclado); },

    _aviso: function (tipo, msg) {
        this.$('.o_kps_aviso').removeClass('o_kps_ok o_kps_mal o_kps_info').addClass(
            msg ? 'o_kps_' + (tipo || 'info') : '').text(msg || '');
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
            return {ok: false, sinConexion: true};
        });
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
        return this._consultar(codigo, false);
    },

    _consultar: function (codigo, sinFaltantes, msgTras) {
        var self = this;
        this._aviso('info', 'Buscando ' + codigo + '…');
        return this._llamar('/koroshi/prenda_suelo/leer', {
            codigo: codigo,
            employee_id: this.persona ? this.persona.id : false,
            ubicacion_id: this.posicion ? this.posicion.id : false,
            sin_faltantes: sinFaltantes,
        }).then(function (r) {
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
            if (r.tipo === 'ubicacion') {
                self.posicion = {id: r.ubicacion.id, nombre: r.ubicacion.nombre, t: Date.now()};
                if (self.codigoPrenda && self.res && self.res.registro_id) {
                    // hueco leído después de la prenda: se vuelve a buscar desde aquí
                    self._aviso('ok', 'Estás en ' + r.ubicacion.nombre + '. Busco otra vez desde aquí…');
                    return self._consultar(self.codigoPrenda, self.sinFaltantes);
                }
                self._aviso('ok', 'Estás en ' + r.ubicacion.nombre + '. Ahora lee la prenda.');
                return self._pintar();
            }
            self.res = r;
            self.codigoPrenda = codigo;
            self.sinFaltantes = sinFaltantes;
            self._aviso(msgTras ? 'ok' : '', msgTras || '');
            self._pintar();
            window.scrollTo(0, 0);
        });
    },

    // ------------------------------------------------------------------ botones
    _onVaciar: function () {
        this.res = null;
        this.codigoPrenda = '';
        this.sinFaltantes = false;
        this._aviso('', '');
        this._pintar();
        this._foco();
    },

    _onQuitarPosicion: function () {
        this.posicion = null;
        this._pintar();
        this._foco();
    },

    _contestar: function (resultado) {
        var self = this;
        if (this.ocupado || !this.res) { return; }
        return this._llamar('/koroshi/prenda_suelo/contestar', {
            registro_id: this.res.registro_id, resultado: resultado,
            employee_id: this.persona ? this.persona.id : false,
        }).then(function (r) {
            if (r.sinConexion) { return; }
            if (!r.ok) { self._pitido(false); return self._aviso('mal', r.msg || 'Error'); }
            self._pitido(true);
            self.res = null;
            self.codigoPrenda = '';
            self.sinFaltantes = false;
            self._pintar();
            self._aviso('ok', resultado === 'hecho' ? 'Gracias. Apuntado.' :
                'Apuntado como «No sirve». Si no sabes dónde dejarla, a la mesa de los jefes.');
            self._foco();
        });
    },

    _onHecho: function () { return this._contestar('hecho'); },
    _onNoSirve: function () { return this._contestar('no_sirve'); },

    _onEncontrada: function () {
        var self = this;
        if (this.ocupado || !this.res) { return; }
        return this._llamar('/koroshi/prenda_suelo/encontrada', {
            registro_id: this.res.registro_id,
            employee_id: this.persona ? this.persona.id : false,
        }).then(function (r) {
            if (r.sinConexion) { return; }
            if (!r.ok) { self._pitido(false); return self._aviso('mal', r.msg || 'Error'); }
            self._pitido(true);
            self._aviso('ok', 'Faltante encontrado. Mirando a dónde va ahora…');
            return self._consultar(self.codigoPrenda, true,
                'Faltante encontrado: Odoo ya la tiene en ' + r.hueco + '. Ahora haz lo que pone abajo.');
        });
    },

    // ------------------------------------------------------------------ pintar
    _pintar: function () {
        var cab = [];
        cab.push(this.persona ? '<b>' + _e(this.persona.nombre) + '</b>' :
            '<span class="o_kps_gris">Sin tarjeta (opcional: pásala)</span>');
        if (this.posicion) {
            cab.push('Estás en <b>' + _e(this.posicion.nombre) + '</b> <button type="button" ' +
                'class="o_kps_quitar_pos">✕</button>');
        } else {
            cab.push('<span class="o_kps_gris">Lee el hueco que tienes delante para saber quién está más cerca</span>');
        }
        this.$('.o_kps_quien').html(cab.join(' · '));
        this.$('.o_kps_cuerpo').html(this.res ? this._htmlResultado(this.res) : this._htmlInicio());
        this.$('.o_kps_vaciar').toggle(!!this.res);
    },

    _htmlInicio: function () {
        return '<div class="o_kps_card o_kps_ayuda"><h3>¿Has encontrado una prenda en el suelo?</h3>' +
            '<ol><li><b>Lee la prenda</b> (su código de barras).</li>' +
            '<li>Si quieres, lee el <b>hueco que tienes delante</b>: así te digo quién está más cerca.</li>' +
            '<li>Haz lo que diga la PDA y pulsa <b>Hecho</b>.</li></ol>' +
            '<div class="o_kps_nota">Nunca la metas en una caja sin leerla: descuadra la caja.</div></div>';
    },

    _htmlResultado: function (r) {
        var p = r.producto;
        var h = '<div class="o_kps_prenda">' + _e(p.nombre) + (p.ean ? ' <small>' + _e(p.ean) + '</small>' : '') +
            '</div>';
        if (r.desde) {
            h += '<div class="o_kps_nota o_kps_desde">Distancias desde ' + _e(r.desde) +
                (r.desde_fuente ? ' (' + _e(r.desde_fuente) + ')' : '') + '</div>';
        }
        h += this._htmlOrden(r);
        h += this._htmlOtras(r);
        if (r.caso !== 'A' || !r.faltantes[0].puede) {   // con «Encontrada», se contesta después
            h += '<div class="o_kps_botones_res"><button type="button" class="o_kps_hecho">✔ Hecho</button>' +
                '<button type="button" class="o_kps_nosirve">No sirve</button></div>';
        }
        return h;
    },

    _htmlOrden: function (r) {
        var t, d = [];
        if (r.caso === 'A') {
            var f = r.faltantes[0];
            t = 'ES UN FALTANTE';
            d.push('De ' + _e(f.out) + (f.fecha ? ' (' + _e(f.fecha) + ')' : '') + '. Su hueco: <b>' + _e(f.hueco) +
                '</b>.');
            if (f.puede) {
                d.push('<button type="button" class="o_kps_encontrada">Encontrada → a ' + _e(f.hueco) + '</button>');
                d.push('<span class="o_kps_nota">Odoo la devuelve de FALTANTE a su hueco y después te digo a quién ' +
                    'dársela.</span>');
            } else {
                d.push('<b>' + _e(f.motivo) + '</b>');
            }
        } else if (r.caso === 'B') {
            var q = r.personas[0];
            t = 'DÁSELA A ' + _e(q.nombre).toUpperCase();
            d.push(this._htmlPersona(q, true));
            d.push('<span class="o_kps_nota">Que la lea en Lecturas, como una más de su pedido.</span>');
        } else if (r.caso === 'C') {
            var s = r.sin_empezar[0];
            t = 'A SU HUECO ' + _e(s.hueco);
            d.push('La pide ' + _e(s.out) + ' (' + _n(s.uds) + ' ud' + (s.uds === 1 ? '' : 's') + '), que ' +
                (s.en_curso_sin_leer ? 'está empezada pero nadie lee en ella desde hace rato' :
                    'aún no prepara nadie') + '. Déjala en su hueco: allí la cogerán.' +
                (s.metros_txt ? ' <span class="o_kps_metros">' + _e(s.metros_txt) + '</span>' : ''));
        } else if (r.caso === 'D') {
            var u = r.huecos[0];
            t = 'VUELVE A ' + _e(u.hueco);
            d.push('No la pide nadie. Odoo tiene ' + _n(u.uds) + ' ud' + (u.uds === 1 ? '' : 's') + ' ahí.' +
                (u.metros_txt ? ' <span class="o_kps_metros">' + _e(u.metros_txt) + '</span>' : ''));
        } else {
            t = 'A ' + _e(r.sitio).toUpperCase();
            d.push('Odoo no la tiene en ningún hueco de lineal ni de muelle.');
        }
        return '<div class="o_kps_card o_kps_orden o_kps_caso_' + r.caso + '"><div class="o_kps_titulo_orden">' + t +
            '</div><div class="o_kps_detalle">' + d.join('<br/>') + '</div></div>';
    },

    _htmlPersona: function (q, grande) {
        var partes = [];
        partes.push('Pedido <b>' + _e(q.out) + '</b>' + (q.agrupacion ? ' (' + _e(q.agrupacion) + ')' : '') +
            ', la pide en <b>' + _e(q.hueco_linea) + '</b>.');
        var donde = [];
        if (q.esta_en) { donde.push('está en <b>' + _e(q.esta_en) + '</b>' + (q.minutos_txt ? ' (' + _e(q.minutos_txt) + ')' : '')); }
        if (q.va_a && q.va_a !== q.esta_en) { donde.push('va a <b>' + _e(q.va_a) + '</b>'); }
        if (!donde.length) { donde.push('aún no ha leído nada en este pedido'); }
        var frase = donde.join(', ');
        frase = grande ? 'Ahora ' + frase : frase.charAt(0).toUpperCase() + frase.slice(1);
        partes.push(frase + '.' +
            (q.metros_txt ? ' <span class="o_kps_metros">' + _e(q.metros_txt) + '</span>' : ''));
        return partes.join('<br/>');
    },

    _htmlOtras: function (r) {
        var self = this;
        var filas = [];
        var personas = r.caso === 'B' ? r.personas.slice(1) : (r.caso === 'A' ? r.personas : []);
        personas.forEach(function (q) {
            filas.push('<li><b>' + _e(q.nombre) + '</b>: ' + self._htmlPersona(q, false) + '</li>');
        });
        var sin = r.caso === 'C' ? r.sin_empezar.slice(1) : (r.caso === 'A' || r.caso === 'B' ? r.sin_empezar : []);
        sin.forEach(function (s) {
            filas.push('<li>Hueco <b>' + _e(s.hueco) + '</b>: la pide ' + _e(s.out) + ' (sin empezar)' +
                (s.metros_txt ? ', ' + _e(s.metros_txt) : '') + '</li>');
        });
        var huecos = r.caso === 'D' ? r.huecos.slice(1) : r.huecos;
        huecos.forEach(function (u) {
            filas.push('<li>Hueco <b>' + _e(u.hueco) + '</b>: Odoo tiene ' + _n(u.uds) +
                (u.metros_txt ? ', ' + _e(u.metros_txt) : '') + '</li>');
        });
        if (!filas.length) { return ''; }
        return '<div class="o_kps_card o_kps_otras"><div class="o_kps_sub">Si no puedes:</div><ul>' +
            filas.join('') + '</ul></div>';
    },
});

core.action_registry.add('koroshi_prenda_suelo', PrendaSuelo);
return PrendaSuelo;
});
