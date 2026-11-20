odoo.define('koroshi_recuentos.Referencia', function (require) {
'use strict';
/* KOROSHI Recuentos v1.1.0 - pantalla «Referencia» de la PDA.
 * v1.0 (fase 1, solo lectura): se lee o se escribe una referencia (2621XC04), una variante o una prenda (EAN):
 *   tabla color x talla con lo que dice Odoo y los sitios en orden de recorrido (en naranja, donde se quitó a mano).
 * v1.1 (fase 2, el recuento): «Contar esta referencia» (con la tarjeta de operario, la misma que en Lecturas,
 *   Contenedores y Faltante). Caja a caja: leer la caja o el hueco, leer CADA prenda («Quitar la última» si sobra)
 *   y «Caja hecha». A ciegas: la PDA no enseña lo que dice Odoo hasta terminar; si no cuadra, pide leer la caja otra
 *   vez. Cada lectura queda apuntada en Odoo. «Terminar» enseña el resultado. NO toca el stock (eso es la fase 3).
 *   Lo que se lee mientras se espera a Odoo va a una cola y se lee después, en orden (no se pierde ninguna prenda).
 * Todo dentro de .o_koroshi_recuentos. Sin aria-hidden (Odoo 13 lo oculta). */
var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var session = require('web.session');

var REPETIDA_MS = 700;       // la misma lectura llega por el bus y por el campo: se descarta la copia
var EN_ESPERA_MAX = 40;      // lecturas guardadas mientras se espera a Odoo (al contar se lee deprisa)
var PERSONA_MS = 3600000;    // tarjeta sin actividad: parámetro koroshi_operarios.minutos_tarjeta (60 por defecto)

function _e(t) { return _.escape(t == null ? '' : String(t)); }
function _n(x) { return (Math.round((x || 0) * 100) / 100).toString().replace('.', ','); }

var ESTADO_CAJA = {
    pendiente: 'sin contar', contando: 'contando', cuadra: 'cuadra ✓', confirmada: 'diferencia',
    para_jefe: 'para el jefe', no_existe: 'no existe',
};

var Referencia = AbstractAction.extend({
    contentTemplate: 'koroshi_recuentos.Referencia',
    events: {
        'keydown .o_kr_codigo': '_onKeydown',
        'click .o_kr_teclado': '_onTeclado',
        'click .o_kr_atras': '_onAtras',
        'click .o_kr_vaciar': '_onVaciar',
        'click .o_kr_modelo': '_onModelo',
        'click .o_kr_sitio': '_onSitio',
        // v1.1: recuento
        'click .o_kr_contar': '_onContar',
        'click .o_kr_rcaja': '_onAbrirCaja',
        'click .o_kr_quitar': '_onQuitar',
        'click .o_kr_hecha': '_onHecha',
        'click .o_kr_noexiste': '_onNoExiste',
        'click .o_kr_terminar': '_onTerminar',
        'click .o_kr_si': '_onSi',
        'click .o_kr_no': '_onNo',
    },

    init: function () {
        this._super.apply(this, arguments);
        this.pila = [];          // pantallas anteriores (para «Atrás»): {tipo, datos}
        this.actual = null;      // {tipo: 'modelos'|'referencia'|'caja'|'recuento'|'terminado', datos}
        this.ocupado = false;
        this.teclado = false;
        this.ultima = {codigo: '', t: 0, fuente: ''};
        this.enEspera = [];      // v1.1: lecturas que esperan a Odoo
        this.persona = null;     // v1.1: {id, nombre}
        this.actividadEn = Date.now();
        this.confirmar = null;   // v1.1: {texto, si: función}
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
    },

    destroy: function () {
        core.bus.off('barcode_scanned', this, this._onBarcodeScanned);
        clearInterval(this.timer);
        this._super.apply(this, arguments);
    },

    // ------------------------------------------------------------------ tarjeta (compartida con las otras pantallas)
    _clave: function () { return 'koroshi_operarios_pda_' + (session.uid || ''); },
    _guardada: function () {
        try {
            var v = window.localStorage.getItem(this._clave());
            return v ? JSON.parse(v) : null;
        } catch (e) { return null; }
    },
    _guardarPersona: function () {
        if (!this.persona) { return; }
        this.guardadaEn = Date.now();
        try {
            window.localStorage.setItem(this._clave(), JSON.stringify(
                {id: this.persona.id, nombre: this.persona.nombre, t: this.guardadaEn}));
        } catch (e) { /* sin memoria: solo en esta pantalla */ }
    },
    _tomarGuardada: function () {
        var g = this._guardada();
        if (!g || !g.id || (this.persona && this.persona.id === g.id)) { return false; }
        if (g.t && Date.now() - g.t > PERSONA_MS) { return false; }
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
        return this._rpc({route: '/koroshi/operarios/minutos_tarjeta', params: {}}, {shadow: true})
            .then(function (r) {
                if (r && r.ok && r.minutos > 0) {
                    PERSONA_MS = r.minutos * 60000;
                    if (!self.persona && self._tomarGuardada()) { self._pintar(); }
                }
            }).guardedCatch(function (e) {
                if (e && e.event && e.event.preventDefault) { e.event.preventDefault(); }
            });
    },
    _vigilar: function () {
        var g = this._guardada();
        if (this.persona && g && g.id === this.persona.id && g.t && g.t > this.actividadEn) {
            this.actividadEn = g.t;
        }
        if (this.persona && Date.now() - this.actividadEn > PERSONA_MS) {
            this.persona = null;
            this._aviso('info', 'Tarjeta caducada por inactividad. Pasa tu tarjeta para seguir.');
            this._pintar();
        }
    },
    _ponerPersona: function (p) {
        this.persona = p;
        this._guardarPersona();
        this._actividad();
        this._pitido(true);
        this._aviso('ok', 'Hola, ' + p.nombre + '.');
        this._pintar();
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

    _contando: function () {
        return this.actual && this.actual.tipo === 'recuento' && this.actual.datos.recuento.estado === 'contando';
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
            // v1.1: al contar se lee deprisa: la lectura espera su turno (o pita si ya hay demasiadas)
            if (this.enEspera.length >= EN_ESPERA_MAX) {
                this._pitido(false);
                return this._aviso('mal', 'Espera a que acabe: ' + codigo + ' NO se ha leído. Vuelve a leerlo.');
            }
            this.enEspera.push(codigo);
            return;
        }
        this._actividad();
        if (this._contando()) { return this._leerRecuento(codigo); }
        return this._buscar(codigo, true);
    },

    // Al acabar una petición, la siguiente lectura que esperaba
    _fin: function () {
        var self = this;
        this.ocupado = false;
        if (this.enEspera.length) {
            setTimeout(function () {
                if (!self.ocupado && self.enEspera.length) {
                    var c = self.enEspera.shift();
                    if (self._contando()) { self._leerRecuento(c); } else { self._buscar(c, true); }
                }
            }, 0);
        }
    },

    _llamar: function (ruta, params) {
        var self = this;
        this.ocupado = true;
        return this._rpc({route: ruta, params: params}).then(function (r) {
            self._fin();
            return r;
        }, function () {
            self.enEspera = [];
            self.ocupado = false;
            self._pitido(false);
            self._aviso('mal', 'Sin conexión con Odoo. Lo último NO se ha apuntado: vuelve a leerlo.');
            return {ok: false, sinConexion: true};
        });
    },

    _buscar: function (texto, nueva) {
        var self = this;
        this._aviso('info', 'Buscando ' + texto + '…');
        return this._llamar('/koroshi/recuentos/referencia', {texto: texto}).then(function (r) {
            if (r.sinConexion) { return; }
            if (r.error) {
                self._pitido(false);
                return self._aviso('mal', r.error);
            }
            if (r.tipo === 'persona') { return self._ponerPersona(r.persona); }
            self._pitido(true);
            self._aviso('', '');
            self._ir({tipo: r.tipo, datos: r}, nueva);
        });
    },

    // ------------------------------------------------------------------ navegación
    _ir: function (pantalla, nueva) {
        if (nueva) { this.pila = []; } else if (this.actual) { this.pila.push(this.actual); }
        this.actual = pantalla;
        this.confirmar = null;
        this._pintar();
        this._foco();
        window.scrollTo(0, 0);
    },

    _onAtras: function () {
        this.actual = this.pila.length ? this.pila.pop() : null;
        this.confirmar = null;
        this._aviso('', '');
        this._pintar();
        this._foco();
    },

    _onVaciar: function () {
        this.pila = [];
        this.actual = null;
        this.confirmar = null;
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
        return this._llamar('/koroshi/recuentos/caja', {ubicacion_id: id, modelo: modelo}).then(function (r) {
            if (r.sinConexion) { return; }
            if (r.error) { self._pitido(false); return self._aviso('mal', r.error); }
            self._aviso('', '');
            self._ir({tipo: 'caja', datos: r}, false);
        });
    },

    // ------------------------------------------------------------------ v1.1: recuento
    _sinPersona: function () {
        if (this.persona) { return false; }
        this._pitido(false);
        this._aviso('mal', 'Pasa antes tu tarjeta de operario.');
        return true;
    },

    // Respuesta de una ruta del recuento: pinta el recuento, pita y avisa
    _respuesta: function (r) {
        if (r.sinConexion) { return; }
        if (r.tipo === 'persona') { return this._ponerPersona(r.persona); }
        if (!r.ok) {
            if (r.preguntar) { return this._preguntar(r.msg, this._terminar.bind(this, true)); }
            this._pitido(false);
            return this._aviso('mal', r.msg || 'No se ha podido.');
        }
        var bien = r.bien !== false;
        if (r.tipo !== 'recuento' || r.msg) { this._pitido(bien); }
        this._aviso(r.msg ? (bien ? 'ok' : 'mal') : '', r.msg || '');
        if (r.tipo === 'terminado') {
            return this._ir({tipo: 'terminado', datos: r}, false);
        }
        if (this.actual && this.actual.tipo === 'recuento') {
            this.actual = {tipo: 'recuento', datos: r};
            this.confirmar = null;
            this._pintar();
        } else {
            this._ir({tipo: 'recuento', datos: r}, false);
        }
    },

    _rec: function () { return this.actual && this.actual.datos && this.actual.datos.recuento; },

    _onContar: function () {
        if (this.ocupado || this._sinPersona()) { return; }
        var d = this.actual && this.actual.datos;
        if (!d || !d.modelo) { return; }
        this._llamar('/koroshi/recuentos/empezar', {modelo: d.modelo, employee_id: this.persona.id})
            .then(this._respuesta.bind(this));
    },

    _leerRecuento: function (codigo) {
        if (this._sinPersona()) { this.enEspera = []; return; }
        this._llamar('/koroshi/recuentos/leer', {recuento_id: this._rec().id, codigo: codigo,
                                                  employee_id: this.persona.id})
            .then(this._respuesta.bind(this));
    },

    _onAbrirCaja: function (ev) {
        var id = $(ev.currentTarget).data('id');
        if (this.ocupado || !id || this._sinPersona()) { return; }
        this._llamar('/koroshi/recuentos/abrir_caja', {recuento_id: this._rec().id, caja_id: id,
                                                        employee_id: this.persona.id})
            .then(this._respuesta.bind(this));
    },

    _onQuitar: function () {
        if (this.ocupado || this._sinPersona()) { return; }
        this._llamar('/koroshi/recuentos/quitar', {recuento_id: this._rec().id, employee_id: this.persona.id})
            .then(this._respuesta.bind(this));
    },

    _cajaHecha: function () {
        this._llamar('/koroshi/recuentos/caja_hecha', {recuento_id: this._rec().id, employee_id: this.persona.id})
            .then(this._respuesta.bind(this));
    },

    _onHecha: function () {
        if (this.ocupado || this._sinPersona()) { return; }
        var d = this.actual.datos;
        if (!d.leidas) {
            return this._preguntar('No has leído ninguna prenda. ¿Está vacía de verdad (nada de ' +
                d.recuento.referencia + ')?', this._cajaHecha.bind(this));
        }
        this._cajaHecha();
    },

    _onNoExiste: function (ev) {
        var self = this;
        ev.stopPropagation();   // el botón está dentro de la caja, que al tocarla se abre
        var id = $(ev.currentTarget).data('id');
        if (this.ocupado || !id || this._sinPersona()) { return; }
        this._preguntar('¿Seguro que este sitio no existe en el almacén?', function () {
            self._llamar('/koroshi/recuentos/no_existe', {recuento_id: self._rec().id, caja_id: id,
                                                          employee_id: self.persona.id})
                .then(self._respuesta.bind(self));
        });
    },

    _terminar: function (forzar) {
        this._llamar('/koroshi/recuentos/terminar', {recuento_id: this._rec().id, employee_id: this.persona.id,
                                                      forzar: !!forzar})
            .then(this._respuesta.bind(this));
    },

    _onTerminar: function () {
        if (this.ocupado || this._sinPersona()) { return; }
        this._terminar(false);
    },

    _preguntar: function (texto, si) {
        this.confirmar = {texto: texto, si: si};
        this._pitido(false);
        this._pintar();
    },
    _onSi: function () {
        var c = this.confirmar;
        this.confirmar = null;
        if (c && c.si && !this.ocupado) { c.si(); } else { this._pintar(); }
    },
    _onNo: function () { this.confirmar = null; this._pintar(); },

    // ------------------------------------------------------------------ pintar
    _pintar: function () {
        var a = this.actual;
        var html = '<div class="o_kr_persona">' + (this.persona
            ? 'Operario: <b>' + _e(this.persona.nombre) + '</b>'
            : 'Sin tarjeta (para contar, pasa tu tarjeta)') + '</div>';
        if (this.confirmar) {
            html += '<div class="o_kr_card o_kr_confirmar"><div>' + _e(this.confirmar.texto) + '</div>' +
                '<button type="button" class="o_kr_si">Sí</button><button type="button" class="o_kr_no">No</button></div>';
        }
        if (!a) {
            html += '<div class="o_kr_paso">Lee una prenda o escribe la referencia (⌨ Escribir): 2621XC04</div>' +
                '<div class="o_kr_nota">Enseña lo que dice Odoo de todas las tallas y colores, y dónde. Desde ahí se ' +
                'puede contar la referencia.</div>';
        } else if (a.tipo === 'modelos') {
            html += this._pintarModelos(a.datos);
        } else if (a.tipo === 'caja') {
            html += this._pintarCaja(a.datos);
        } else if (a.tipo === 'recuento') {
            html += this._pintarRecuento(a.datos);
        } else if (a.tipo === 'terminado') {
            html += this._pintarTerminado(a.datos);
        } else {
            html += this._pintarReferencia(a.datos);
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
        if (!c.existe) { return '<td class="o_kr_n o_kr_no_hay">·</td>'; }
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
        var contar = d.recuento_abierto
            ? 'Seguir el recuento ' + _e(d.recuento_abierto.name)
            : 'Contar esta referencia';
        var html = '<div class="o_kr_card"><h3>' + _e(d.modelo) + '</h3>' +
            '<div class="o_kr_sub">' + d.n_variantes + ' variantes · Odoo dice ' + _n(d.total) + ' uds' +
            (d.reservadas ? ' · ' + _n(d.reservadas) + ' reservadas' : '') + ' · ' + _e(d.hora) +
            (d.leida ? '<br/>Leída: ' + _e(d.leida) : '') + '</div>' +
            '<div class="o_kr_tabla"><table class="o_kr_rejilla">' + cab + filas + '</table></div>' +
            '<div class="o_kr_nota">Color en filas, talla en columnas. Entre paréntesis, lo reservado para pedidos. ' +
            'En rojo, lo negativo.</div>' +
            '<button type="button" class="o_kr_contar">' + contar + '</button></div>';
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

    _nombreCaja: function (c) {
        return _e(c.hueco) + (c.contenedor ? ' · ' + _e(c.contenedor) : '');
    },

    _pintarRecuento: function (d) {
        var self = this;
        var r = d.recuento;
        var html = '<div class="o_kr_card"><h3>' + _e(r.name) + ' · ' + _e(r.referencia) + '</h3>' +
            '<div class="o_kr_sub">Recuento a ciegas: cuenta lo que hay de verdad. Cada lectura queda apuntada.</div></div>';
        if (d.activa) {
            var a = d.activa;
            var filas = d.cuenta.map(function (f) {
                return '<tr><td>' + _e(f.color) + ' · <b>' + _e(f.talla) + '</b></td><td class="o_kr_n">' +
                    _n(f.uds) + '</td></tr>';
            }).join('');
            html += '<div class="o_kr_card o_kr_activa"><div class="o_kr_sub">Contando (' + a.vuelta + '.ª lectura)</div>' +
                '<div class="o_kr_hueco">' + this._nombreCaja(a) + '</div>' +
                '<div class="o_kr_leidas">' + d.leidas + ' prendas leídas</div>' +
                (filas ? '<table>' + filas + '</table>' : '<div class="o_kr_nota">Lee cada prenda de ' +
                    _e(r.referencia) + ' que haya en la caja.</div>') +
                (d.ultima ? '<div class="o_kr_nota">Última: ' + _e(d.ultima) + '</div>' : '') +
                '<div class="o_kr_acciones">' +
                '<button type="button" class="o_kr_hecha">Caja hecha</button>' +
                '<button type="button" class="o_kr_quitar"' + (d.leidas ? '' : ' disabled') + '>Quitar la última</button>' +
                (d.leidas ? '' : '<button type="button" class="o_kr_noexiste" data-id="' + a.id + '">No existe</button>') +
                '</div></div>';
        } else {
            var siguiente = _.find(d.cajas, function (c) { return c.estado === 'pendiente'; });
            html += '<div class="o_kr_paso">' + (siguiente
                ? 'Lee la caja (o el hueco): ' + this._nombreCaja(siguiente)
                : 'Todas las cajas están contadas. Pulsa «Terminar».') + '</div>' +
                '<div class="o_kr_nota">Si ves la referencia en otro sitio, lee ese sitio: se añade a la lista.</div>';
        }
        var hechas = _.filter(d.cajas, function (c) { return c.estado !== 'pendiente' && c.estado !== 'contando'; });
        html += '<div class="o_kr_paso">Cajas: ' + hechas.length + ' de ' + d.cajas.length + ' hechas</div>';
        html += d.cajas.map(function (c) {
            var abrir = !d.activa && c.estado === 'pendiente';
            return '<div class="o_kr_card o_kr_fila_caja o_kr_e_' + c.estado + (abrir ? ' o_kr_rcaja' : '') +
                '" data-id="' + c.id + '"><span class="o_kr_hueco_p">' + self._nombreCaja(c) + '</span>' +
                (c.fuera_de_lista ? ' <span class="o_kr_marca">añadida</span>' : '') +
                (c.con_ajuste ? ' <span class="o_kr_marca o_kr_m_naranja">ajuste a mano</span>' : '') +
                '<span class="o_kr_estado">' + _e(ESTADO_CAJA[c.estado] || c.estado) +
                (c.vuelta > 1 && c.estado !== 'pendiente' ? ' (' + c.vuelta + ' lecturas)' : '') + '</span>' +
                (abrir ? '<button type="button" class="o_kr_noexiste" data-id="' + c.id + '">No existe</button>' : '') +
                '</div>';
        }).join('');
        if (!d.activa) {
            html += '<div class="o_kr_acciones o_kr_fuera"><button type="button" class="o_kr_terminar">Terminar el recuento</button></div>';
        }
        return html;
    },

    _pintarTerminado: function (d) {
        var s = d.resumen;
        var filas = s.filas.map(function (f) {
            var cls = f.diferencia < 0 ? ' o_kr_neg' : (f.diferencia > 0 ? ' o_kr_pos' : '');
            return '<tr><td>' + _e(f.color) + ' · <b>' + _e(f.talla) + '</b></td><td class="o_kr_n">' + _n(f.odoo) +
                '</td><td class="o_kr_n">' + _n(f.leido) + '</td><td class="o_kr_n' + cls + '">' +
                (f.diferencia > 0 ? '+' : '') + _n(f.diferencia) + '</td></tr>';
        }).join('');
        return '<div class="o_kr_card"><h3>' + _e(d.recuento.name) + ' · ' + _e(d.recuento.referencia) + '</h3>' +
            '<div class="o_kr_resultado">' + _e(s.estado) + '</div>' +
            (filas ? '<table><tr><th></th><th>Odoo</th><th>Leído</th><th>Dif.</th></tr>' + filas + '</table>'
                : '<div class="o_kr_nota">No se ha cerrado ninguna caja.</div>') +
            (s.sin_contar ? '<div class="o_kr_nota">' + s.sin_contar + ' cajas sin contar.</div>' : '') +
            (s.para_jefe ? '<div class="o_kr_nota">' + s.para_jefe + ' cajas para el jefe (tres lecturas distintas).</div>' : '') +
            (s.no_existe ? '<div class="o_kr_nota">' + s.no_existe + ' sitios que no existen.</div>' : '') +
            '<div class="o_kr_nota">Queda apuntado en Odoo (Recuentos hechos). Todavía no se cambia el stock.</div></div>';
    },
});

core.action_registry.add('koroshi_recuentos_referencia', Referencia);
return Referencia;
});
