odoo.define('koroshi_transportista.Pantalla', function (require) {
'use strict';
/* KOROSHI Transportista v1.8.0 - pantalla de la PDA (área Expediciones). v1.1.0: CJ por sus últimas cifras.
 * v1.8.0: GLS -70 (ya existe) -> botón «Recuperar etiqueta GLS».
 * v1.7.0: lista fija abajo con las expediciones de hoy (K##) y «Reimprimir», sin leer ninguna caja.
 * v1.5.0: aviso de transportista (bultos e historial); GLS/XPO ya no se marca solo.
 * v1.3.0: «Dejar fuera» una OUT de otro día.
 * v1.2.0: marca SUMI en las OUT de suministros.
 * v1.1.1: el campo va en un formulario (Intro/«Ir» de Android) con botón «✓ Leer»; foco al campo tras cada lectura.
 * 1. Tarjeta (la compartida: koroshi_base.comun.tarjeta). GLS / XPO se puede elegir antes o al final.
 * 2. Se leen las CJ de la tienda. La primera fija la tienda. Una CJ que no va se rechaza con el porqué y hay que
 *    pulsar «Apartada» (la pantalla no sigue hasta entonces).
 * 3. «Leídas N de M». Solo con todo cuadrado se enciende «Imprimir etiquetas» -> confirmar -> GLS/XPO de verdad y el
 *    PDF a la impresora del portátil de Expediciones.
 * El campo lee cuando el lector para 150 ms (las PDA no mandan Intro); con «⌨ Escribir» espera al Intro.
 * Todo dentro de .o_koroshi_transportista. Sin aria-hidden (Odoo 13 lo oculta). */
var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var comun = require('koroshi_base.comun');

var REPETIDA_MS = 700;
var PERSONA_MS = 3600000;

function _e(t) { return _.escape(t == null ? '' : String(t)); }
function _token() { return Date.now() + '-' + Math.random().toString(36).slice(2, 10); }
var NOMBRE = {gls: 'GLS', xpo: 'XPO'};

var Transportista = AbstractAction.extend({
    contentTemplate: 'koroshi_transportista.Pantalla',
    events: {
        'keydown .o_ktr_codigo': '_onKeydown',
        'submit .o_ktr_form': '_onEnviar',
        'input .o_ktr_codigo': '_onEscribe',
        'click .o_ktr_teclado': '_onTeclado',
        'click .o_ktr_tr': '_onTransportista',
        'click .o_ktr_imprimir': '_onImprimir',
        'click .o_ktr_confirmar': '_onConfirmar',
        'click .o_ktr_cancelar': '_onCancelar',
        'click .o_ktr_apartada': '_onApartada',
        'click .o_ktr_otra': '_onOtra',
        'click .o_ktr_reimprimir': '_onReimprimir',
        'click .o_ktr_fuera': '_onFuera',
        'click .o_ktr_meter': '_onMeter',
        'click .o_ktr_recargar': '_cargarExpediciones',
        'click .o_ktr_recuperar': '_onRecuperar',
    },

    init: function () {
        this._super.apply(this, arguments);
        this.ocupado = false;
        this.teclado = false;
        this.ultima = {codigo: '', t: 0, fuente: ''};
        this.persona = null;
        this.actividadEn = Date.now();
        this.transportista = '';     // 'gls' | 'xpo' | '' (se pregunta al final)
        this.expediciones = null;    // v1.7.0: las de hoy (todas las tiendas), para reimprimir
        this._vaciar();
    },

    _vaciar: function () {
        this.estado = null;          // respuesta de /leer
        this.leidas = [];            // CJ que cuentan
        this.rechazadas = [];        // [{cj, motivo}] hasta pulsar «Apartada»
        this.fuera = [];             // v1.3.0: ids de OUT de otros días dejadas fuera de esta etiqueta
        this.confirmando = false;
        this.hecho = null;
        this.glsExiste = '';         // v1.8.0: texto del -70 de GLS (enseña «Recuperar etiqueta GLS»)
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
            self._cargarExpediciones();
        });
    },

    on_attach_callback: function () {
        this._super.apply(this, arguments);
        if (this._tomarGuardada()) { this._pintar(); }
        this._foco();
        this._cargarExpediciones();
    },

    // v1.7.0: lista de las expediciones de hoy (solo lee; no usa _llamar para no bloquear la pantalla)
    _cargarExpediciones: function () {
        var self = this;
        return this._rpc({route: '/koroshi/transportista/expediciones', params: {}}, {shadow: true}).then(function (r) {
            if (r && r.ok) {
                self.expediciones = r.expediciones || [];
                self.$('.o_ktr_expediciones').html(self._htmlExpediciones());
            }
        }, function () {});
    },

    destroy: function () {
        core.bus.off('barcode_scanned', this, this._onBarcodeScanned);
        clearInterval(this.timer);
        comun.cancelarLector(this);
        this._super.apply(this, arguments);
    },

    // ------------------------------------------------------------------ tarjeta (compartida)
    _guardada: function () { return comun.tarjeta.leer(); },
    _guardarPersona: function () {
        if (this.persona) { this.guardadaEn = comun.tarjeta.guardar(this.persona); }
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

    // ------------------------------------------------------------------ lector
    _foco: function () {
        var $c = this.$('.o_ktr_codigo');
        if ($c.length && document.activeElement !== $c[0]) { $c.focus(); }
    },
    _onKeydown: function (ev) {
        if (comun.esFinDeLectura(ev)) {
            ev.preventDefault();
            comun.cancelarLector(this);
            var codigo = (ev.currentTarget.value || '').trim();
            ev.currentTarget.value = '';
            if (this.teclado) { this._ponerTeclado(false); }
            this._leer(codigo, 'campo');
        }
    },
    // v1.1.1: Intro/«Ir» del teclado de pantalla (Android no siempre manda la tecla 13) o el botón «✓ Leer»
    _onEnviar: function (ev) {
        ev.preventDefault();
        comun.cancelarLector(this);
        var campo = this.$('.o_ktr_codigo')[0];
        var codigo = ((campo && campo.value) || '').trim();
        if (campo) { campo.value = ''; }
        if (this.teclado) { this._ponerTeclado(false); }
        if (!codigo) {
            this._pitido(false);
            return this._aviso('mal', 'Escribe la caja (o sus 4 últimas cifras) y pulsa «✓ Leer».');
        }
        this._leer(codigo, 'campo');
    },
    _onEscribe: function (ev) {
        var self = this;
        if (this.teclado) { return comun.cancelarLector(this); }
        comun.leerAlParar(this, ev.currentTarget, function (codigo) { self._leer(codigo, 'campo'); });
    },
    _onBarcodeScanned: function (codigo) { this._leer(codigo, 'bus'); },
    _ponerTeclado: function (si) {
        this.teclado = si;
        var $c = this.$('.o_ktr_codigo');
        $c.attr('inputmode', si ? null : 'none');
        this.$('.o_ktr_teclado').toggleClass('o_ktr_teclado_on', si).text(si ? '⌨ Ocultar' : '⌨ Escribir');
        this.$('.o_ktr_form').toggleClass('o_ktr_escribiendo', si);
        $c.blur();
        $c.focus();
    },
    _onTeclado: function () { this._ponerTeclado(!this.teclado); },

    _aviso: function (tipo, msg) {
        this.$('.o_ktr_aviso').removeClass('o_ktr_ok o_ktr_mal o_ktr_info').addClass(
            msg ? 'o_ktr_' + (tipo || 'info') : '').text(msg || '');
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
        if (this.hecho) { this._vaciar(); }
        this.confirmando = false;
        var cj = codigo.toUpperCase();
        if (comun.esMatricula(cj) && this.leidas.indexOf(cj) >= 0) {
            this._pitido(false);
            return this._aviso('mal', cj + ' ya está leída.');
        }
        this._aviso('info', 'Leyendo ' + codigo + '…');
        return this._llamar('/koroshi/transportista/leer', {
            codigo: codigo, leidas: this.leidas, partner_id: this.estado ? this.estado.partner_id : false,
            fuera: this.fuera,
        }).then(function (r) {
            if (r.sinConexion) { return; }
            if (!r.ok) {
                self._pitido(false);
                self._foco();
                return self._aviso('mal', r.msg || 'Error');
            }
            if (r.tipo === 'persona') {
                self._pitido(true);
                self.persona = r.persona;
                self._guardarPersona();
                self._aviso('ok', 'Hola, ' + r.persona.nombre + '.');
                self._pintar();
                return self._foco();
            }
            self.estado = r;
            self.leidas = r.leidas || [];
            var mala = _.findWhere(r.sobran || [], {cj: r.cj});
            if (mala) {
                if (!_.findWhere(self.rechazadas, {cj: mala.cj})) { self.rechazadas.push(mala); }
                self._pitido(false);
                self._aviso('mal', mala.cj + ' NO va en esta expedición: ' + mala.motivo + '. Apártala.');
            } else {
                self._pitido(true);
                self._aviso(r.cuadra ? 'ok' : 'info', r.cuadra ?
                    'Están todas: ' + r.n_leidas + ' de ' + r.n_esperadas + '. Ya puedes imprimir.' :
                    r.cj + (r.escrita ? ' (escrita ' + r.escrita + ')' : '') + ' leída. Leídas ' + r.n_leidas + ' de ' +
                    r.n_esperadas + '.');
            }
            self._pintar();
            self._foco();     // v1.1.1: que la siguiente lectura caiga en el campo
        });
    },

    // ------------------------------------------------------------------ botones
    _onTransportista: function (ev) {
        var tr = $(ev.currentTarget).data('tr');
        this.transportista = this.transportista === tr && !this.confirmando ? '' : tr;
        if (this.confirmando && !this.transportista) { this.transportista = tr; }
        this._pintar();
    },
    _puedeImprimir: function () {
        return this.estado && this.estado.cuadra && !this.rechazadas.length && !this.hecho;
    },
    _onImprimir: function () {
        if (!this._puedeImprimir() || this.ocupado) { return; }
        if (!this.persona) {
            this._pitido(false);
            return this._aviso('mal', 'Pasa antes tu tarjeta de operario.');
        }
        // v1.5.0: ya no se marca solo (K68 25/11 salió por XPO sin querer): se elige siempre GLS o XPO
        this.confirmando = true;
        this._aviso('info', this.transportista ? 'Comprueba y confirma.' : 'Elige GLS o XPO.');
        this._pintar();
        window.scrollTo(0, 0);
    },
    _onCancelar: function () {
        this.confirmando = false;
        this._aviso('', '');
        this._pintar();
        this._foco();
    },
    _onConfirmar: function () {
        var self = this;
        if (!this._puedeImprimir() || this.ocupado || !this.transportista) { return; }
        this.$('.o_ktr_confirmar').prop('disabled', true).text('Registrando en ' + NOMBRE[this.transportista] + '…');
        return this._etiquetar(false);
    },
    // v1.8.0: GLS dijo -70 (ya existe): se busca en GLS y se baja la etiqueta, sin mandar otra expedición
    _onRecuperar: function () {
        if (!this._puedeImprimir() || this.ocupado || !this.persona) { return; }
        this.transportista = 'gls';
        this.$('.o_ktr_recuperar').prop('disabled', true).text('Buscando en GLS…');
        return this._etiquetar(true);
    },
    _etiquetar: function (recuperar) {
        var self = this;
        return this._llamar('/koroshi/transportista/etiquetar', {
            leidas: this.leidas, partner_id: this.estado.partner_id, transportista: this.transportista,
            employee_id: this.persona.id, token: this.token, fuera: this.fuera, recuperar: !!recuperar,
        }).then(function (r) {
            if (r.sinConexion) { return; }
            self.confirmando = false;
            if (!r.ok) {
                self._pitido(false);
                self._aviso('mal', r.msg || 'Error');
                self.glsExiste = r.gls_existe ? (r.msg || 'GLS: ya existe (-70).') : '';
                if (r.hecho) { self.hecho = {ok: false, texto: r.msg}; }
                return self._pintar();
            }
            self._pitido(true);
            self.glsExiste = '';
            self.hecho = r;
            self._cargarExpediciones();
            self._aviso(r.aviso_envio || r.aviso_impresion ? 'info' : 'ok', r.impresos ?
                'Hecho: ' + r.transportista + ' ' + r.tracking + '. Imprimiendo en ' + (r.impresora || 'Expediciones') + '.' :
                'Hecho: ' + r.transportista + ' ' + r.tracking + '.');
            self._pintar();
            self._foco();
        });
    },
    _onApartada: function (ev) {
        var cj = $(ev.currentTarget).data('cj');
        this.rechazadas = _.reject(this.rechazadas, function (x) { return x.cj === cj; });
        this._aviso('', '');
        this._pintar();
        this._foco();
    },
    // v1.3.0: dejar fuera / volver a meter una OUT de otro día (su caja no está o no tiene que salir hoy)
    _onFuera: function (ev) {
        var id = parseInt($(ev.currentTarget).data('id'), 10);
        if (this.ocupado || !id || this.fuera.indexOf(id) >= 0) { return; }
        this.fuera.push(id);
        this._refrescar('OUT dejada fuera: no va en esta etiqueta y se queda sin etiqueta.');
    },
    _onMeter: function (ev) {
        var id = parseInt($(ev.currentTarget).data('id'), 10);
        if (this.ocupado) { return; }
        this.fuera = _.without(this.fuera, id);
        this._refrescar('OUT otra vez dentro: hay que leer sus cajas.');
    },
    _refrescar: function (texto) {
        var self = this;
        if (!this.estado) { return; }
        this.confirmando = false;
        return this._llamar('/koroshi/transportista/leer', {
            codigo: '', leidas: this.leidas, partner_id: this.estado.partner_id, fuera: this.fuera,
        }).then(function (r) {
            if (r.sinConexion) { return; }
            if (!r.ok) {
                self._pitido(false);
                return self._aviso('mal', r.msg || 'Error');
            }
            self.estado = r;
            self.leidas = r.leidas || [];
            (r.sobran || []).forEach(function (m) {
                if (!_.findWhere(self.rechazadas, {cj: m.cj})) { self.rechazadas.push(m); }
            });
            self._aviso(r.cuadra ? 'ok' : 'info', texto + ' Leídas ' + r.n_leidas + ' de ' + r.n_esperadas + '.');
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
    _onReimprimir: function (ev) {
        var self = this;
        var tracking = String($(ev.currentTarget).data('tracking'));
        // v1.7.0: la lista de abajo lleva la tienda en el botón: se reimprime sin leer ninguna caja
        var partner = parseInt($(ev.currentTarget).data('partner'), 10) || (this.estado && this.estado.partner_id);
        if (this.ocupado || !partner) { return; }
        if (!this.persona) {
            this._pitido(false);
            return this._aviso('mal', 'Pasa antes tu tarjeta de operario.');
        }
        return this._llamar('/koroshi/transportista/reimprimir', {
            partner_id: partner, tracking: tracking, employee_id: this.persona.id,
        }).then(function (r) {
            if (r.sinConexion) { return; }
            self._pitido(!!r.ok);
            self._aviso(r.ok ? (r.aviso_impresion ? 'info' : 'ok') : 'mal', r.ok ?
                'Reimprimiendo ' + r.tracking + (r.aviso_impresion ? '. ' + r.aviso_impresion : '.') : r.msg);
        });
    },

    // ------------------------------------------------------------------ pintar
    _pintar: function () {
        this.$('.o_ktr_quien').html(this.persona ? '<b>' + _e(this.persona.nombre) + '</b>' :
            '<span class="o_ktr_rojo">Sin tarjeta: pásala antes de imprimir</span>');
        var self = this;
        this.$('.o_ktr_tr').each(function () {
            $(this).toggleClass('o_ktr_tr_on', $(this).data('tr') === self.transportista);
        });
        var h;
        if (this.hecho) {
            h = this._htmlHecho(this.hecho);
        } else if (!this.estado) {
            h = this._htmlInicio();
        } else {
            h = this._htmlGlsExiste() + (this.confirmando ? this._htmlConfirmar() : '') + this._htmlRechazadas() +
                this._htmlEstado() +
                this._htmlBotones() + this._htmlCajas() + this._htmlEtiquetadas();
        }
        this.$('.o_ktr_cuerpo').html(h);
        this.$('.o_ktr_expediciones').html(this._htmlExpediciones());
    },

    _htmlGlsExiste: function () {
        if (!this.glsExiste || this.hecho) { return ''; }
        return '<div class="o_ktr_card o_ktr_card_mal"><div class="o_ktr_rojo">⚠ ' + _e(this.glsExiste) + '</div>' +
            '<div class="o_ktr_nota">No se manda otra expedición: se busca la que ya está en GLS, se baja su etiqueta ' +
            'y se imprime.</div><div class="o_ktr_botones"><button type="button" class="o_ktr_recuperar">' +
            'Recuperar etiqueta GLS</button></div></div>';
    },

    _htmlExpediciones: function () {
        var l = this.expediciones;
        if (l === null) { return ''; }
        var h = '<div class="o_ktr_card"><div class="o_ktr_nota"><b>Expediciones de hoy</b> (' + l.length + ')' +
            ' <button type="button" class="o_ktr_recargar">↻</button></div>';
        if (!l.length) { return h + '<div class="o_ktr_gris">Todavía ninguna.</div></div>'; }
        l.forEach(function (e) {
            h += '<div class="o_ktr_rech o_ktr_exp"><b class="o_ktr_k">' + _e(e.codigo || e.tienda) + '</b> ' +
                _e(e.hora) + ' · ' + _e(e.transportista) + ' ' + _e(e.tracking) + ' · ' + e.bultos + ' bulto' +
                (e.bultos === 1 ? '' : 's') + ' <button type="button" class="o_ktr_reimprimir" data-tracking="' +
                _e(e.tracking) + '" data-partner="' + _e(e.partner_id) + '">Reimprimir</button></div>';
        });
        return h + '</div>';
    },

    _htmlInicio: function () {
        return '<div class="o_ktr_card o_ktr_ayuda"><h3>Etiqueta del transportista</h3><ol>' +
            '<li>Pasa tu <b>tarjeta</b>. Si ya lo sabes, elige arriba <b>GLS</b> o <b>XPO</b>.</li>' +
            '<li>Lee <b>todas las cajas (CJ)</b> de la tienda que tienes delante. Si una etiqueta no se lee, pulsa ' +
            '<b>⌨ Escribir</b> y escribe sus <b>4 últimas cifras</b>.</li>' +
            '<li>Cuando salga «Leídas N de N», pulsa <b>Imprimir etiquetas</b>.</li></ol>' +
            '<div class="o_ktr_nota">Si una caja no va, la pantalla dice por qué. Hasta que no cuadren todas, no se ' +
            'puede imprimir.</div></div>';
    },

    _htmlEstado: function () {
        var r = this.estado;
        var imp = r.impresora || {};
        var h = '<div class="o_ktr_card"><div class="o_ktr_tienda">' + _e(r.tienda) + '</div>' +
            '<div class="o_ktr_cuenta ' + (r.cuadra && !this.rechazadas.length ? 'o_ktr_verde_t' : '') + '">Leídas ' +
            r.n_leidas + ' de ' + r.n_esperadas + ' bultos</div>';
        if (r.faltan && r.faltan.length && r.n_leidas) {
            h += '<div class="o_ktr_nota">Faltan: ' + _e(r.faltan.join(', ')) + '</div>';
        }
        if (!r.n_esperadas) {
            h += '<div class="o_ktr_rojo">Esta tienda no tiene OUT validadas pendientes de etiqueta.</div>';
        }
        (r.avisos || []).forEach(function (a) { h += '<div class="o_ktr_naranja">⚠ ' + _e(a) + '</div>'; });
        if (imp.nombre && !imp.conectada) {
            h += '<div class="o_ktr_naranja">⚠ ' + _e(imp.nombre) + ' no está conectada: las etiquetas saldrán ' +
                'cuando se encienda el portátil.</div>';
        }
        return h + '</div>';
    },

    _htmlRechazadas: function () {
        if (!this.rechazadas.length) { return ''; }
        var h = '<div class="o_ktr_card o_ktr_card_mal"><div class="o_ktr_rojo">Estas cajas NO van en esta ' +
            'expedición. Apártalas:</div>';
        this.rechazadas.forEach(function (x) {
            h += '<div class="o_ktr_rech"><b>' + _e(x.cj) + '</b>: ' + _e(x.motivo) +
                ' <button type="button" class="o_ktr_apartada" data-cj="' + _e(x.cj) + '">Apartada</button></div>';
        });
        return h + '</div>';
    },

    _htmlCajas: function () {
        var r = this.estado;
        if (!r.cajas || !r.cajas.length) { return ''; }
        var filas = r.cajas.map(function (c) {
            return '<li class="' + (c.leida ? 'o_ktr_si' : 'o_ktr_no') + '">' + (c.leida ? '✔ ' : '✖ ') + _e(c.cj) +
                ' <span class="o_ktr_gris">' + _e(c.outs.join(', ')) + '</span></li>';
        });
        var outs = (r.outs || []).map(function (o) {
            return '<li>' + (o.sumi ? '<span class="o_ktr_sumi">SUMI</span> ' : '') + _e(o.nombre) + ' · ' +
                _e(o.origen) + ' · ' + o.bultos + ' caja' + (o.bultos === 1 ? '' : 's') +
                (o.de_otro_dia ? ' · <span class="o_ktr_naranja">del ' + _e(o.dia) + '</span>' +
                    ' <button type="button" class="o_ktr_fuera" data-id="' + o.id + '">Dejar fuera</button>' : '') +
                '</li>';
        });
        var fuera = (r.fuera || []).map(function (o) {
            return '<li>' + _e(o.nombre) + ' · ' + _e(o.origen) + ' · ' + _e(o.cajas) +
                ' <button type="button" class="o_ktr_meter" data-id="' + o.id + '">Volver a meter</button></li>';
        });
        return '<div class="o_ktr_card"><div class="o_ktr_nota">Cajas que espera Odoo:</div><ul class="o_ktr_lista">' +
            filas.join('') + '</ul><div class="o_ktr_nota">OUT que van:</div><ul class="o_ktr_lista">' +
            outs.join('') + '</ul>' + (fuera.length ? '<div class="o_ktr_nota o_ktr_naranja">Dejadas fuera (se quedan ' +
            'sin etiqueta):</div><ul class="o_ktr_lista">' + fuera.join('') + '</ul>' : '') + '</div>';
    },

    _htmlEtiquetadas: function () {
        var r = this.estado;
        if (!r.etiquetadas || !r.etiquetadas.length) { return ''; }
        var h = '<div class="o_ktr_card"><div class="o_ktr_nota">Ya etiquetadas (últimos días):</div>';
        r.etiquetadas.forEach(function (e) {
            h += '<div class="o_ktr_rech">' + _e(e.transportista) + ' <b>' + _e(e.tracking) + '</b> · ' + _e(e.fecha) +
                ' · ' + e.outs.length + ' OUT <button type="button" class="o_ktr_reimprimir" data-tracking="' +
                _e(e.tracking) + '">Reimprimir</button></div>';
        });
        return h + '</div>';
    },

    _htmlConfirmar: function () {
        var r = this.estado;
        if (!this.transportista) {
            return '<div class="o_ktr_card o_ktr_card_conf"><h3>¿GLS o XPO?</h3>' +
                (r.habitual ? '<div class="o_ktr_nota">Lo habitual en esta tienda para ' + r.n_esperadas +
                    ' bultos: <b>' + NOMBRE[r.habitual] + '</b>.</div>' : '') + '<div class="o_ktr_botones">' +
                '<button type="button" class="o_ktr_tr o_ktr_tr_grande" data-tr="gls">GLS</button>' +
                '<button type="button" class="o_ktr_tr o_ktr_tr_grande" data-tr="xpo">XPO</button></div>' +
                '<div class="o_ktr_botones"><button type="button" class="o_ktr_cancelar">Cancelar</button></div></div>';
        }
        var nSumi = _.filter(r.outs || [], function (o) { return o.sumi; }).length;
        var nFuera = (r.fuera || []).length;
        // v1.5.0: aviso en rojo si se sale de lo habitual (bultos o historial). No prohíbe: confirma «igualmente».
        var avisosTr = (r.aviso_tr && r.aviso_tr[this.transportista]) || [];
        var aviso = avisosTr.length ? '<div class="o_ktr_aviso_tr">⚠ ' + avisosTr.map(_e).join('<br/>⚠ ') +
            '<br/>¿Seguro que va por ' + NOMBRE[this.transportista] + '?</div>' : '';
        return '<div class="o_ktr_card o_ktr_card_conf"><h3>' + NOMBRE[this.transportista] + ' · ' + _e(r.tienda) +
            '</h3><div class="o_ktr_cuenta">' + r.n_esperadas + ' bultos · ' + (r.outs || []).length + ' OUT</div>' +
            (nSumi ? '<div class="o_ktr_nota">Incluye ' + nSumi + ' OUT de <span class="o_ktr_sumi">SUMI</span> ' +
                '(suministros de la tienda).</div>' : '') +
            (nFuera ? '<div class="o_ktr_naranja">Se quedan FUERA: ' + _e(_.pluck(r.fuera, 'nombre').join(', ')) +
                '</div>' : '') +
            aviso + '<div class="o_ktr_nota">Se registra la expedición en ' + NOMBRE[this.transportista] +
            ' (no se puede deshacer) y la etiqueta sale en la impresora del portátil.</div>' +
            '<div class="o_ktr_botones"><button type="button" class="o_ktr_confirmar">' +
            (avisosTr.length ? 'Sí, con ' + NOMBRE[this.transportista] + ' igualmente' : 'Sí, imprimir') + '</button>' +
            '<button type="button" class="o_ktr_cancelar">Cancelar</button></div></div>';
    },

    _htmlBotones: function () {
        if (this.confirmando) { return ''; }
        var puede = this._puedeImprimir();
        return '<div class="o_ktr_botones"><button type="button" class="o_ktr_imprimir"' +
            (puede ? '' : ' disabled="disabled"') + '>Imprimir etiquetas</button>' +
            '<button type="button" class="o_ktr_otra">Otra tienda</button></div>';
    },

    _htmlHecho: function (r) {
        if (!r.ok) {
            return '<div class="o_ktr_card o_ktr_card_mal"><h3>⚠ Revisar</h3><div class="o_ktr_rojo">' + _e(r.texto) +
                '</div><div class="o_ktr_botones"><button type="button" class="o_ktr_otra">Otra tienda</button></div></div>';
        }
        return '<div class="o_ktr_card"><h3>✔ ' + _e(r.transportista) + ' ' + _e(r.tracking) + '</h3>' +
            '<div class="o_ktr_tienda">' + _e(r.tienda) + '</div><div class="o_ktr_cuenta">' + r.bultos + ' bultos</div>' +
            (r.aviso_envio ? '<div class="o_ktr_rojo">⚠ ' + _e(r.texto) + '</div>' : '') +
            (r.impresos ? '<div class="o_ktr_verde_t">Imprimiendo en ' + _e(r.impresora || 'Expediciones') + '</div>' : '') +
            (r.aviso_impresion ? '<div class="o_ktr_naranja">⚠ ' + _e(r.aviso_impresion) + '</div>' : '') +
            '<div class="o_ktr_nota">Lee una caja de otra tienda para seguir.</div>' +
            '<div class="o_ktr_botones"><button type="button" class="o_ktr_otra">Otra tienda</button></div></div>';
    },
});

core.action_registry.add('koroshi_transportista', Transportista);
return Transportista;
});
