odoo.define('koroshi_recepcion.Pantalla', function (require) {
'use strict';
/* KOROSHI Recepción de contenedores v1.0.0 (23/11/2026) - PDA o tablet.
 * 0. Pasar la tarjeta (la misma de Lecturas, Contenedores y Faltante: memoria de la PDA).
 * 1. Lista de contenedores abiertos o «Nuevo contenedor»: matrícula, muelle y las IN que trae.
 * 2. Ficha: «Recepcionar»: cuántas cajas y cuántos palés ve quien recepciona (crea un KO_ por caja y los PAL-NN A/B
 *    que falten) y el PDF de etiquetas para la Zebra del PC de Recepciones.
 * 3. Leer, a ciegas: palé y cara (botón o etiqueta), caja (etiqueta KO_ o «Siguiente caja»), prenda (código o
 *    buscador: últimos 4 números del EAN o un trozo del modelo) y cantidad. «Guardar». Abajo, las últimas con «Anular».
 * 4. Responsable (su tarjeta en «Responsables de recepción»): «Comparar» con las IN, «Validar lo leído hasta ahora»
 *    o «Validar». Exportar (Excel).
 * Doble toque de la PDA: los botones se bloquean hasta que responde Odoo y cada lectura lleva un token (si llega dos
 * veces, se guarda una). Sin aria-hidden (Odoo 13 lo oculta): role="presentation". */
var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var session = require('web.session');

var RAFAGA_MS = 150;          // sin teclado, el campo lee cuando el lector para 150 ms (como Contenedores 1.9.3)
var REPETIDA_MS = 700;        // la misma lectura por el bus y por el campo: una sola
var PERSONA_MS = 3600000;     // koroshi_operarios.minutos_tarjeta (60 por defecto), se lee al entrar

function _e(t) { return _.escape(t == null ? '' : String(t)); }
function _n(x) { return (Math.round((x || 0) * 100) / 100).toString().replace('.', ','); }
function _token() { return Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10); }

var Pantalla = AbstractAction.extend({
    contentTemplate: 'koroshi_recepcion.Pantalla',
    events: {
        'keydown .o_kr_codigo': '_onKeydown',
        'input .o_kr_codigo': '_onEscribe',
        'click [data-accion]': '_onAccion',
        'click .o_kr_tecla': '_onTecla',
        'keydown .o_kr_buscar': '_onBuscarKey',
    },

    init: function (parent, action) {
        this._super.apply(this, arguments);
        this.inicial = action && action.params && action.params.recepcion_id;
        this.persona = null;
        this.vista = 'lista';
        this.rec = null;            // ficha de la recepción abierta
        this.lista = [];
        this.ins = [];
        this.elegidas = {};
        this.palet = null;          // {id, nombre}
        this.caja = null;           // {id, nombre}
        this.prod = null;           // {id, nombre, modelo, talla}
        this.cantidad = '';
        this.token = _token();
        this.ultimas = [];
        this.resultados = null;     // buscador de prendas
        this.comparacion = null;
        this.abiertos = {};         // modelos desplegados en la comparación
        this.soloProblemas = true;
        this.ocupado = false;
        this.ultima = {codigo: '', t: 0};
        this.actividadEn = Date.now();
    },

    start: function () {
        var self = this;
        core.bus.on('barcode_scanned', this, this._onBarcodeScanned);
        return this._super.apply(this, arguments).then(function () {
            self.timer = setInterval(self._vigilar.bind(self), 10000);
            self._tomarGuardada();
            self._leerMinutosTarjeta();
            if (self.inicial) {
                self._abrir(self.inicial);
            } else {
                self._irLista();
            }
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
        clearTimeout(this.rafagaTimer);
        this._super.apply(this, arguments);
    },

    // ------------------------------------------------------------ tarjeta compartida (como Contenedores 1.9)
    _clave: function () { return 'koroshi_operarios_pda_' + (session.uid || ''); },
    _guardada: function () {
        try {
            var v = window.localStorage.getItem(this._clave());
            return v ? JSON.parse(v) : null;
        } catch (e) { return null; }
    },
    _guardarPersona: function () {
        if (!this.persona) { return; }
        try {
            window.localStorage.setItem(this._clave(), JSON.stringify(
                {id: this.persona.id, nombre: this.persona.nombre, t: Date.now()}));
        } catch (e) { /* sin memoria: solo en esta pantalla */ }
    },
    _tomarGuardada: function () {
        var g = this._guardada();
        if (!g || !g.id || (this.persona && this.persona.id === g.id)) { return false; }
        if (g.t && Date.now() - g.t > PERSONA_MS) { return false; }
        this.persona = {id: g.id, nombre: g.nombre, responsable: false};
        this.actividadEn = g.t || Date.now();
        this._refrescarResponsable();
        return true;
    },
    _refrescarResponsable: function () {
        var self = this;
        if (!this.persona) { return; }
        this._rpc({route: '/koroshi/recepcion/inicio', params: {employee_id: this.persona.id}}, {shadow: true})
            .then(function (r) {
                if (r && r.ok && self.persona) { self.persona.responsable = r.responsable; self._pintar(); }
            });
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
            this._aviso('info', 'Sesión cerrada por inactividad. Pasa tu tarjeta.');
            this._pintar();
        }
        // No se repinta sola: borraría lo que se está escribiendo en el buscador. «↻» pone al día la ficha.
    },

    // ------------------------------------------------------------ lector
    _foco: function () {
        var $c = this.$('.o_kr_codigo');
        var activo = document.activeElement;
        if (activo && $(activo).is('input.o_kr_campo, input.o_kr_buscar')) { return; }
        if ($c.length && activo !== $c[0]) { $c.focus(); }
    },
    _onKeydown: function (ev) {
        if (ev.which === 13 || ev.which === 9) {
            ev.preventDefault();
            clearTimeout(this.rafagaTimer);
            var codigo = (ev.currentTarget.value || '').trim();
            ev.currentTarget.value = '';
            this._leer(codigo, 'campo');
        }
    },
    _onEscribe: function (ev) {
        var self = this;
        clearTimeout(this.rafagaTimer);
        this.rafagaTimer = setTimeout(function () {
            var v = (ev.currentTarget.value || '').trim();
            if (v) { ev.currentTarget.value = ''; self._leer(v, 'campo'); }
        }, RAFAGA_MS);
    },
    _onBarcodeScanned: function (codigo) { this._leer(codigo, 'bus'); },

    _leer: function (codigo, fuente) {
        var self = this;
        codigo = (codigo || '').trim();
        if (!codigo) { return; }
        var t = Date.now();
        if (codigo === this.ultima.codigo && t - this.ultima.t < REPETIDA_MS && fuente !== this.ultima.fuente) {
            return;
        }
        this.ultima = {codigo: codigo, t: t, fuente: fuente};
        if (this.ocupado) { this._pitido(false); return this._aviso('mal', 'Espera: ' + codigo + ' NO se ha leído.'); }
        return this._llamar('/koroshi/recepcion/leer', {
            recepcion_id: this.vista === 'leer' && this.rec ? this.rec.id : false, codigo: codigo,
        }).then(function (r) {
            if (!r) { return; }
            if (r.tipo === 'persona') {
                self.persona = r.persona;
                self._guardarPersona();
                self._pitido(true);
                self._aviso('ok', 'Hola, ' + r.persona.nombre + (r.persona.responsable ? ' (responsable)' : ''));
                if (self.rec) { return self._refrescarFicha(); }
                return self._pintar();
            }
            if (!self.persona) { self._pitido(false); return self._aviso('mal', 'Primero pasa tu tarjeta de operario.'); }
            if (self.vista !== 'leer') {
                self._pitido(false);
                return self._aviso('mal', 'Para leer cajas y prendas, entra en un contenedor y pulsa «Leer».');
            }
            self._pitido(true);
            if (r.tipo === 'palet') { self.palet = r.palet; self._aviso('ok', 'Palé ' + r.palet.nombre); }
            if (r.tipo === 'caja') { self._ponerCaja(r.caja); }
            if (r.tipo === 'producto') { self._ponerProd(r.producto); }
            self._pintar();
        });
    },

    // ------------------------------------------------------------ llamadas
    _llamar: function (route, params, sinBloqueo) {
        var self = this;
        if (!sinBloqueo) {
            if (this.ocupado) { return Promise.resolve(null); }
            this.ocupado = true;
            this.$('button').prop('disabled', true);
        }
        return this._rpc({route: route, params: params}).then(function (r) {
            if (!sinBloqueo) { self.ocupado = false; self.$('button').prop('disabled', false); }
            self.actividadEn = Date.now();
            if (self.persona) { self._guardarPersona(); }
            if (!r || !r.ok) {
                self._pitido(false);
                self._aviso('mal', (r && r.msg) || 'No se ha podido hacer.');
                return null;
            }
            return r;
        }).guardedCatch(function (e) {
            if (!sinBloqueo) { self.ocupado = false; self.$('button').prop('disabled', false); }
            if (e && e.event && e.event.preventDefault) { e.event.preventDefault(); }
            self._aviso('mal', 'Sin conexión con Odoo. Vuelve a probar (lo que no ha dicho «guardado» no está).');
        });
    },

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

    // ------------------------------------------------------------ navegación
    _irLista: function () {
        var self = this;
        this.vista = 'lista';
        this.rec = null;
        return this._llamar('/koroshi/recepcion/inicio', {employee_id: this.persona && this.persona.id}).then(function (r) {
            if (r) {
                self.lista = r.recepciones;
                if (self.persona) { self.persona.responsable = r.responsable; }
            }
            self._pintar();
        });
    },
    _abrir: function (id) {
        var self = this;
        return this._llamar('/koroshi/recepcion/ficha', {recepcion_id: id, employee_id: this.persona && this.persona.id})
            .then(function (r) {
                if (!r) { return; }
                self.rec = r.recepcion;
                self.ultimas = r.ultimas;
                self.vista = 'ficha';
                self._pintar();
            });
    },
    _refrescarFicha: function (callado) {
        var self = this;
        if (!this.rec) { return Promise.resolve(); }
        return this._llamar('/koroshi/recepcion/ficha', {recepcion_id: this.rec.id,
            employee_id: this.persona && this.persona.id}, callado).then(function (r) {
            if (!r) { return; }
            self.rec = r.recepcion;
            self.ultimas = r.ultimas;
            if (self.persona) { self.persona.responsable = r.recepcion.responsable; }
            self._pintar();
        });
    },
    _ponerCaja: function (caja) {
        this.caja = caja;
        this._aviso('ok', 'Caja ' + caja.nombre + ': ahora la prenda.');
    },
    _ponerProd: function (p) {
        this.prod = p;
        this.resultados = null;
        this.cantidad = '';
        this._aviso('ok', p.nombre + ': escribe la cantidad.');
    },

    // ------------------------------------------------------------ botones (data-accion)
    _onAccion: function (ev) {
        ev.preventDefault();
        var $b = $(ev.currentTarget);
        var accion = $b.data('accion');
        var valor = $b.data('valor');
        if (this.ocupado && accion !== 'teclado') { return; }
        var f = this['_a_' + accion];
        if (f) { f.call(this, valor, $b); }
        this._foco();
    },
    _necesitaPersona: function () {
        if (!this.persona) { this._pitido(false); this._aviso('mal', 'Primero pasa tu tarjeta de operario.'); }
        return !!this.persona;
    },
    _a_lista: function () { this._irLista(); },
    _a_abrir: function (id) { this._abrir(id); },
    _a_cambiar_persona: function () { this.persona = null; this._aviso('info', 'Pasa tu tarjeta.'); this._pintar(); },

    _a_nueva: function () {
        var self = this;
        if (!this._necesitaPersona()) { return; }
        return this._llamar('/koroshi/recepcion/ins', {}).then(function (r) {
            if (!r) { return; }
            self.ins = r.ins;
            self.elegidas = {};
            self.vista = 'nueva';
            self._pintar();
        });
    },
    _a_editar_ins: function () {
        var self = this;
        return this._llamar('/koroshi/recepcion/ins', {recepcion_id: this.rec.id}).then(function (r) {
            if (!r) { return; }
            self.ins = r.ins;
            self.elegidas = {};
            _.each(self.rec.ins, function (i) { self.elegidas[i.id] = true; });
            // las IN ya enlazadas pueden no estar abiertas: se enseñan igual
            _.each(self.rec.ins, function (i) {
                if (!_.findWhere(self.ins, {id: i.id})) { self.ins.unshift(_.extend({en_otra: ''}, i)); }
            });
            self.vista = 'editar_ins';
            self._pintar();
        });
    },
    _elegidasIds: function () {
        var self = this;
        this.$('.o_kr_in input[type=checkbox]').each(function () {
            self.elegidas[parseInt(this.value, 10)] = this.checked;
        });
        return _.map(_.filter(_.keys(this.elegidas), function (k) { return self.elegidas[k]; }),
            function (k) { return parseInt(k, 10); });
    },
    _a_crear: function () {
        var self = this;
        if (!this._necesitaPersona()) { return; }
        var ids = this._elegidasIds();
        return this._llamar('/koroshi/recepcion/crear', {
            matricula: this.$('.o_kr_matricula').val(), muelle: this.$('.o_kr_muelle').val(),
            referencia: this.$('.o_kr_referencia').val(), picking_ids: ids, employee_id: this.persona.id,
        }).then(function (r) {
            if (!r) { return; }
            self.rec = r.recepcion;
            self.ultimas = [];
            self.vista = 'ficha';
            self._aviso('ok', 'Contenedor ' + r.recepcion.matricula + ' creado (' + r.recepcion.name + ').');
            self._pintar();
        });
    },
    _a_guardar_ins: function () {
        var self = this;
        if (!this._necesitaPersona()) { return; }
        return this._llamar('/koroshi/recepcion/enlazar', {
            recepcion_id: this.rec.id, picking_ids: this._elegidasIds(), employee_id: this.persona.id,
        }).then(function (r) {
            if (!r) { return; }
            self.rec = r.recepcion;
            self.vista = 'ficha';
            self._aviso('ok', 'IN guardadas.');
            self._pintar();
        });
    },
    _a_ficha: function () { this.vista = 'ficha'; this._refrescarFicha(); },
    _a_recepcionar: function () { if (this._necesitaPersona()) { this.vista = 'recepcionar'; this._pintar(); } },
    _a_hacer_recepcionar: function () {
        var self = this;
        if (!this._necesitaPersona()) { return; }
        return this._llamar('/koroshi/recepcion/recepcionar', {
            recepcion_id: this.rec.id, cajas: parseInt(this.$('.o_kr_cajas').val(), 10) || 0,
            palets: parseInt(this.$('.o_kr_npalets').val(), 10) || 0, muelle: this.$('.o_kr_muelle').val(),
            employee_id: this.persona.id,
        }).then(function (r) {
            if (!r) { return; }
            self.rec = r.recepcion;
            self.vista = 'ficha';
            self._aviso('ok', r.tanda ? 'Creado: ' + r.tanda + '. Imprime las etiquetas en el PC de Recepciones.'
                : 'No había nada nuevo que crear.');
            self._pintar();
        });
    },
    _a_imprimir: function () {
        if (!this.rec || !this.rec.tanda_id) { return this._aviso('mal', 'No hay etiquetas que imprimir.'); }
        window.open('/report/pdf/koroshi_recepcion.etiqueta_tanda/' + this.rec.tanda_id, '_blank');
    },
    _a_leer: function () {
        if (!this._necesitaPersona()) { return; }
        this.vista = 'leer';
        this.prod = null;
        this.cantidad = '';
        this.resultados = null;
        this._pintar();
    },
    _a_palet: function (id) {
        var p = _.findWhere(this.rec.palets_lista, {id: id});
        this.palet = p || null;
        this._pintar();
    },
    _a_siguiente: function () {
        var self = this;
        return this._llamar('/koroshi/recepcion/siguiente', {recepcion_id: this.rec.id}).then(function (r) {
            if (!r) { return; }
            self._ponerCaja(r.caja);
            self._pintar();
        });
    },
    _a_buscar: function () {
        var self = this;
        var texto = this.$('.o_kr_buscar').val();
        return this._llamar('/koroshi/recepcion/buscar', {recepcion_id: this.rec.id, texto: texto}).then(function (r) {
            if (!r) { return; }
            self.resultados = r.productos;
            self.resultadosMas = r.mas;
            self.textoBuscado = texto;
            if (!r.productos.length) { self._aviso('mal', 'No encuentro prendas con «' + texto + '».'); }
            self._pintar();
        });
    },
    _onBuscarKey: function (ev) {
        if (ev.which === 13) { ev.preventDefault(); this._a_buscar(); }
    },
    _a_elegir: function (id) {
        var p = _.findWhere(this.resultados || [], {id: id});
        if (p) { this._ponerProd(p); this._pintar(); }
    },
    _onTecla: function (ev) {
        ev.preventDefault();
        var t = String($(ev.currentTarget).data('tecla'));
        if (t === 'borrar') { this.cantidad = this.cantidad.slice(0, -1); } else if (this.cantidad.length < 4) {
            this.cantidad = (this.cantidad === '0' ? '' : this.cantidad) + t;
        }
        this.$('.o_kr_cantidad').text(this.cantidad || '0');
    },
    _a_guardar: function () {
        var self = this;
        if (!this._necesitaPersona()) { return; }
        if (!this.palet) { this._pitido(false); return this._aviso('mal', 'Falta el palé: tócalo arriba.'); }
        if (!this.caja) { this._pitido(false); return this._aviso('mal', 'Falta la caja: lee su etiqueta KO_ o «Siguiente caja».'); }
        if (!this.prod) { this._pitido(false); return this._aviso('mal', 'Falta la prenda: léela o búscala.'); }
        if (!parseInt(this.cantidad, 10)) { this._pitido(false); return this._aviso('mal', 'Escribe la cantidad.'); }
        return this._llamar('/koroshi/recepcion/guardar', {
            recepcion_id: this.rec.id, caja_id: this.caja.id, palet_id: this.palet.id, producto_id: this.prod.id,
            cantidad: parseInt(this.cantidad, 10), employee_id: this.persona.id, token: this.token,
        }).then(function (r) {
            if (!r) { return; }
            self.token = _token();          // la siguiente lectura es otra
            self.rec = r.recepcion;
            self.ultimas = r.ultimas;
            self.prod = null;               // la caja y el palé se quedan: una caja puede tener varias tallas
            self.cantidad = '';
            self._pitido(true);
            self._aviso('ok', 'Guardado: ' + r.msg);
            self._pintar();
        });
    },
    _a_otra_caja: function () { this.caja = null; this.prod = null; this.cantidad = ''; this._pintar(); },
    _a_anular: function (id) {
        var self = this;
        if (!this._necesitaPersona()) { return; }
        if (!window.confirm('¿Anular esta lectura?')) { return; }
        return this._llamar('/koroshi/recepcion/anular', {lectura_id: id, employee_id: this.persona.id})
            .then(function (r) {
                if (!r) { return; }
                self.rec = r.recepcion;
                self.ultimas = r.ultimas;
                self._aviso('ok', 'Lectura anulada.');
                self._pintar();
            });
    },
    _a_comparar: function () {
        var self = this;
        if (!this._necesitaPersona()) { return; }
        return this._llamar('/koroshi/recepcion/comparar', {recepcion_id: this.rec.id, employee_id: this.persona.id})
            .then(function (r) {
                if (!r) { return; }
                self.comparacion = r;
                self.vista = 'comparar';
                self._pintar();
            });
    },
    _a_modelo: function (m) { this.abiertos[m] = !this.abiertos[m]; this._pintar(); },
    _a_problemas: function () { this.soloProblemas = !this.soloProblemas; this._pintar(); },
    _a_exportar: function () {
        if (!this._necesitaPersona()) { return; }
        window.open('/koroshi/recepcion/exportar?recepcion_id=' + this.rec.id + '&employee_id=' + this.persona.id,
            '_blank');
    },
    _a_reabrir: function () {
        var self = this;
        if (!this._necesitaPersona()) { return; }
        if (!window.confirm('¿Reabrir este contenedor para recibir las cajas que faltaban?')) { return; }
        return this._llamar('/koroshi/recepcion/reabrir', {recepcion_id: this.rec.id, employee_id: this.persona.id})
            .then(function (r) {
                if (!r) { return; }
                self.rec = r.recepcion;
                self._aviso('ok', 'Reabierto: ya se puede leer.');
                self._pintar();
            });
    },
    _a_validar: function (parcial) {
        var self = this;
        if (!this._necesitaPersona()) { return; }
        parcial = parcial === 1 || parcial === '1';
        var txt = parcial
            ? '¿Pasar a stock lo leído hasta ahora? La lectura sigue después.'
            : '¿Validar el contenedor? Lo leído pasa a stock y lo que no ha llegado queda pendiente en su IN.';
        if (!window.confirm(txt)) { return; }
        return this._llamar('/koroshi/recepcion/validar', {
            recepcion_id: this.rec.id, employee_id: this.persona.id, parcial: parcial,
        }).then(function (r) {
            if (!r) { return; }
            var res = r.resultado;
            var msg = 'Validado: ' + _n(res.uds) + ' uds a stock. IN validadas: ' + (res.pickings.join(', ') || '-') +
                '. Pendientes: ' + ((res.pendientes || []).join(', ') || '-') + '.';
            if (res.sin_in && res.sin_in.length) {
                msg += ' ATENCIÓN: no pasan a stock ' + res.sin_in.length + ' lecturas: ' + res.sin_in.join('; ') +
                    '. Anúlalas si son un error o enlaza su IN.';
            }
            self.rec = r.recepcion;
            self._aviso(res.sin_in && res.sin_in.length ? 'mal' : 'ok', msg);
            if (parcial) { return self._a_comparar(); }
            self.vista = 'ficha';
            self._pintar();
        });
    },

    // ------------------------------------------------------------ pintar
    _pintar: function () {
        var p = this.persona;
        this.$('.o_kr_persona').html(p
            ? 'Persona: <b>' + _e(p.nombre) + '</b>' + (p.responsable ? ' (responsable)' : '') +
              ' <button type="button" data-accion="cambiar_persona">Cambiar</button>'
            : '<span class="o_kr_grande">Pasa tu tarjeta de operario</span>');
        var html = '';
        if (this.vista === 'lista') { html = this._htmlLista(); }
        if (this.vista === 'nueva' || this.vista === 'editar_ins') { html = this._htmlNueva(); }
        if (this.vista === 'ficha') { html = this._htmlFicha(); }
        if (this.vista === 'recepcionar') { html = this._htmlRecepcionar(); }
        if (this.vista === 'leer') { html = this._htmlLeer(); }
        if (this.vista === 'comparar') { html = this._htmlComparar(); }
        this.$('.o_kr_cuerpo').html(html);
        if (this.ocupado) { this.$('button').prop('disabled', true); }
        this._foco();
    },

    _htmlLista: function () {
        var h = '<div class="o_kr_fila"><button type="button" class="o_kr_primario" data-accion="nueva">' +
            '+ Nuevo contenedor</button><button type="button" data-accion="lista">↻ Actualizar</button></div>';
        if (!this.lista.length) {
            return h + '<p class="o_kr_gris">No hay contenedores abiertos.</p>';
        }
        h += '<div class="o_kr_tarjetas">';
        _.each(this.lista, function (r) {
            h += '<div class="o_kr_tarjeta' + (r.state === 'leyendo' ? ' o_kr_leyendo' : '') + '" data-accion="abrir" ' +
                'data-valor="' + r.id + '"><b>' + _e(r.matricula) + '</b><br/>' + _e(r.name) +
                (r.muelle ? ' · Muelle ' + _e(r.muelle) : '') + '<br/>' + _e(r.llegada) + '<br/>' +
                (r.state === 'leyendo' ? 'Leyendo: ' + r.cajas_leidas + ' de ' + r.cajas + ' cajas'
                    : r.state === 'validada' ? 'Validado, con IN pendientes (cajas por llegar)' : 'Sin empezar') +
                '<br/><span class="o_kr_gris">Pedidos: ' + _e(r.ins || '-') + '</span></div>';
        });
        return h + '</div>';
    },

    _htmlNueva: function () {
        var self = this;
        var nueva = this.vista === 'nueva';
        var h = '';
        if (nueva) {
            h += '<label>Matrícula del contenedor (puerta o lateral)</label>' +
                '<input type="text" class="o_kr_campo o_kr_matricula" placeholder="MSKU1234567"/>' +
                '<label>Muelle</label><input type="text" class="o_kr_campo o_kr_muelle" placeholder="1"/>' +
                '<label>Referencia del proveedor o BL (si la sabes)</label>' +
                '<input type="text" class="o_kr_campo o_kr_referencia"/>';
        }
        h += '<label>¿Qué IN trae? (pedidos de KOROSHI abiertos, por fecha prevista)</label>';
        if (!this.ins.length) { h += '<p class="o_kr_gris">No hay IN abiertas.</p>'; }
        _.each(this.ins, function (i) {
            h += '<div class="o_kr_in"><input type="checkbox" value="' + i.id + '"' +
                (self.elegidas[i.id] ? ' checked="checked"' : '') + '/><div><b>' + _e(i.origen || i.name) + '</b> ' +
                _e(i.name) + (i.backorder ? ' (pendiente de otra)' : '') + ' · ' + _e(i.fecha) + ' · ' + _n(i.uds) +
                ' uds' + (i.ref ? ' · Ref. ' + _e(i.ref) : '') +
                (i.en_otra ? '<br/><span class="o_kr_gris">Ya está en ' + _e(i.en_otra) + '</span>' : '') +
                '</div></div>';
        });
        h += '<div class="o_kr_fila">' + (nueva
            ? '<button type="button" class="o_kr_primario" data-accion="crear">Crear contenedor</button>' +
              '<button type="button" data-accion="lista">Cancelar</button>'
            : '<button type="button" class="o_kr_primario" data-accion="guardar_ins">Guardar IN</button>' +
              '<button type="button" data-accion="ficha">Cancelar</button>') + '</div>';
        return h;
    },

    _htmlFicha: function () {
        var r = this.rec;
        var h = '<div class="o_kr_fila"><button type="button" data-accion="lista">← Contenedores</button>' +
            '<button type="button" data-accion="ficha">↻</button></div>';
        h += '<div class="o_kr_grande">' + _e(r.matricula) + '</div><div>' + _e(r.name) +
            (r.muelle ? ' · Muelle ' + _e(r.muelle) : '') + ' · Llegada ' + _e(r.llegada) +
            (r.referencia ? ' · Ref. ' + _e(r.referencia) : '') + '</div>';
        h += '<table><tr><th>IN</th><th>Pedido</th><th>Ref. proveedor</th><th>Fecha prevista</th><th>Estado</th>' +
            '<th class="o_kr_n">Uds</th></tr>';
        _.each(r.ins, function (i) {
            h += '<tr><td>' + _e(i.name) + '</td><td>' + _e(i.origen) + '</td><td>' + _e(i.ref) + '</td><td>' +
                _e(i.fecha) + '</td><td>' + _e(i.estado) + '</td><td class="o_kr_n">' + _n(i.uds) + '</td></tr>';
        });
        if (!r.ins.length) { h += '<tr><td colspan="6" class="o_kr_gris">Sin IN: añádelas antes de validar.</td></tr>'; }
        h += '</table>';
        h += '<div class="o_kr_fila"><div class="o_kr_caja"><div class="o_kr_etq">Cajas</div><div class="o_kr_grande">' +
            r.cajas_leidas + ' / ' + (r.cajas || 0) + '</div></div><div class="o_kr_caja"><div class="o_kr_etq">Palés</div>' +
            '<div class="o_kr_grande">' + (r.palets || 0) + '</div></div><div class="o_kr_caja"><div class="o_kr_etq">' +
            'Uds leídas / pasadas a stock</div><div class="o_kr_grande">' + _n(r.uds_leidas) + ' / ' +
            _n(r.uds_validadas) + '</div></div></div>';
        h += '<div class="o_kr_fila">';
        if (r.state === 'pendiente') {
            h += '<button type="button" class="o_kr_primario" data-accion="recepcionar">Recepcionar</button>';
        }
        if (r.state === 'leyendo') {
            h += '<button type="button" class="o_kr_primario" data-accion="leer">Leer cajas</button>' +
                '<button type="button" data-accion="recepcionar">+ Cajas / + Palés</button>';
        }
        if (r.tanda_id) { h += '<button type="button" data-accion="imprimir">🖨 Etiquetas (última tanda)</button>'; }
        if (r.state === 'pendiente' || r.state === 'leyendo') {
            h += '<button type="button" data-accion="editar_ins">Cambiar IN</button>';
        }
        if (r.responsable) {
            h += '<button type="button" data-accion="exportar">Exportar (Excel)</button>';
            if (r.state === 'leyendo') { h += '<button type="button" data-accion="comparar">Comparar y validar</button>'; }
            if (r.state === 'validada') {
                h += '<button type="button" data-accion="comparar">Comparar</button>' +
                    '<button type="button" class="o_kr_primario" data-accion="reabrir">Reabrir (llegan cajas)</button>';
            }
        }
        h += '</div>';
        return h + this._htmlUltimas();
    },

    _htmlRecepcionar: function () {
        var r = this.rec;
        return '<div class="o_kr_grande">' + _e(r.matricula) + ': recepcionar</div>' +
            '<p>Escribe lo que ves. Se crea un contenedor de control (KO_) por caja y los palés que falten, con sus ' +
            'etiquetas para la Zebra del PC de Recepciones.' + (r.contenedores ? ' Ya hay ' + r.contenedores +
            ' cajas creadas: solo se crean las que falten hasta el número nuevo.' : '') + '</p>' +
            '<label>¿Cuántas cajas?</label><input type="number" min="1" class="o_kr_campo o_kr_cajas" value="' +
            (r.cajas || '') + '"/>' +
            '<label>¿Cuántos palés vas a usar? (cada palé tiene cara A y cara B)</label>' +
            '<input type="number" min="1" max="99" class="o_kr_campo o_kr_npalets" value="' + (r.palets || '') + '"/>' +
            '<label>Muelle</label><input type="text" class="o_kr_campo o_kr_muelle" value="' + _e(r.muelle) + '"/>' +
            '<div class="o_kr_fila"><button type="button" class="o_kr_primario" data-accion="hacer_recepcionar">' +
            'Crear cajas y palés</button><button type="button" data-accion="ficha">Cancelar</button></div>';
    },

    _htmlLeer: function () {
        var self = this;
        var r = this.rec;
        var h = '<div class="o_kr_fila"><button type="button" data-accion="ficha">← ' + _e(r.matricula) + '</button>' +
            '<span class="o_kr_grande">' + r.cajas_leidas + ' / ' + (r.cajas || 0) + ' cajas</span></div>';
        h += '<div class="o_kr_etq">1. Palé y cara</div><div class="o_kr_palets">';
        _.each(r.palets_lista, function (p) {
            var activo = self.palet && self.palet.id === p.id;
            h += '<button type="button" data-accion="palet" data-valor="' + p.id + '"' +
                (activo ? ' class="o_kr_activo"' : '') + '>' + _e(p.nombre.replace('PAL-', '')) + '</button>';
        });
        if (!r.palets_lista.length) { h += '<span class="o_kr_gris">Sin palés: «+ Cajas / + Palés» en la ficha.</span>'; }
        h += '</div>';
        h += '<div class="o_kr_fila">' +
            '<div class="o_kr_caja' + (this.caja ? ' o_kr_hecho' : ' o_kr_falta') + '"><div class="o_kr_etq">2. Caja</div>' +
            '<div class="o_kr_grande">' + (this.caja ? _e(this.caja.nombre) : 'Lee la etiqueta KO_') + '</div>' +
            '<button type="button" data-accion="siguiente">Siguiente caja</button>' +
            (this.caja ? '<button type="button" data-accion="otra_caja">Otra caja</button>' : '') + '</div>' +
            '<div class="o_kr_caja' + (this.palet ? ' o_kr_hecho' : ' o_kr_falta') + '"><div class="o_kr_etq">Palé</div>' +
            '<div class="o_kr_grande">' + (this.palet ? _e(this.palet.nombre) : 'Toca un palé') + '</div></div></div>';
        h += '<div class="o_kr_caja' + (this.prod ? ' o_kr_hecho' : ' o_kr_falta') + '"><div class="o_kr_etq">3. Prenda</div>';
        if (this.prod) {
            h += '<div class="o_kr_grande">' + _e(this.prod.modelo) + ' · ' + _e(this.prod.talla) + '</div><div>' +
                _e(this.prod.nombre) + '</div>';
        } else {
            h += '<div>Lee el código de barras o búscala:</div><div class="o_kr_fila">' +
                '<input type="text" class="o_kr_campo o_kr_buscar" placeholder="últimos 4 números del EAN o un trozo ' +
                'del modelo" value="' + _e(this.textoBuscado || '') + '"/>' +
                '<button type="button" data-accion="buscar">Buscar</button></div>';
            if (this.resultados && this.resultados.length) {
                h += '<div class="o_kr_resultados">';
                _.each(this.resultados, function (p) {
                    h += '<button type="button" data-accion="elegir" data-valor="' + p.id + '"' +
                        (p.en_in ? ' class="o_kr_de_in"' : '') + '><b>' + _e(p.modelo) + ' · ' + _e(p.talla) +
                        '</b> ' + _e(p.nombre) + (p.ean ? ' <span class="o_kr_gris">…' + _e(p.ean.slice(-4)) + '</span>'
                        : '') + (p.en_in ? '' : ' <span class="o_kr_gris">(no está en las IN)</span>') + '</button>';
                });
                if (this.resultadosMas) { h += '<p class="o_kr_gris">Hay más: escribe un trozo más largo.</p>'; }
                h += '</div>';
            }
        }
        h += '</div>';
        h += '<div class="o_kr_fila"><div><div class="o_kr_etq">4. Cantidad</div><div class="o_kr_cantidad">' +
            _e(this.cantidad || '0') + '</div></div><div class="o_kr_teclado">';
        _.each(['1', '2', '3', '4', '5', '6', '7', '8', '9', 'borrar', '0'], function (t) {
            h += '<button type="button" class="o_kr_tecla" data-tecla="' + t + '">' + (t === 'borrar' ? '⌫' : t) +
                '</button>';
        });
        h += '<button type="button" class="o_kr_primario" data-accion="guardar">Guardar</button></div></div>';
        h += this._htmlUltimas();
        return h;
    },

    _htmlUltimas: function () {
        if (!this.ultimas || !this.ultimas.length) { return ''; }
        var h = '<div class="o_kr_etq" style="margin-top:10px">Últimas lecturas</div><table><tr><th>Hora</th>' +
            '<th>Palé</th><th>Caja</th><th>Prenda</th><th class="o_kr_n">Uds</th><th>Quién</th><th></th></tr>';
        _.each(this.ultimas, function (l) {
            h += '<tr><td>' + _e(l.hora) + '</td><td>' + _e(l.palet) + '</td><td>' + _e(l.caja) + '</td><td>' +
                _e(l.producto) + '</td><td class="o_kr_n">' + _n(l.uds) + '</td><td>' + _e(l.quien) + '</td><td>' +
                (l.validada ? '<span class="o_kr_gris">en stock</span>'
                    : '<button type="button" data-accion="anular" data-valor="' + l.id + '">Anular</button>') +
                '</td></tr>';
        });
        return h + '</table>';
    },

    _htmlComparar: function () {
        var self = this;
        var c = this.comparacion;
        var h = '<div class="o_kr_fila"><button type="button" data-accion="ficha">← ' + _e(this.rec.matricula) +
            '</button><button type="button" data-accion="comparar">↻ Comparar otra vez</button>' +
            '<button type="button" data-accion="problemas">' + (this.soloProblemas ? 'Ver todos los modelos'
            : 'Ver solo los que no cuadran') + '</button><button type="button" data-accion="exportar">Exportar (Excel)' +
            '</button></div>';
        h += '<div class="o_kr_fila"><div class="o_kr_caja"><div class="o_kr_etq">Teórico (IN)</div><div class="o_kr_grande">' +
            _n(c.total.teorico) + '</div></div><div class="o_kr_caja ' + (c.total.leido === c.total.teorico ? 'o_kr_hecho'
            : 'o_kr_falta') + '"><div class="o_kr_etq">Leído</div><div class="o_kr_grande">' + _n(c.total.leido) +
            '</div></div><div class="o_kr_caja"><div class="o_kr_etq">Leído sin pasar a stock</div><div class="o_kr_grande">' +
            _n(c.sin_validar) + '</div></div></div>';
        h += '<table><tr><th>Modelo / talla</th><th class="o_kr_n">Teórico</th><th class="o_kr_n">Leído</th>' +
            '<th class="o_kr_n">Diferencia</th><th>Dónde (palé / caja: uds)</th></tr>';
        var algo = false;
        _.each(c.modelos, function (m) {
            if (self.soloProblemas && !m.problema) { return; }
            algo = true;
            h += '<tr class="o_kr_modelo" data-accion="modelo" data-valor="' + _e(m.modelo) + '"><td>' +
                (self.abiertos[m.modelo] ? '▾ ' : '▸ ') + _e(m.modelo) + '</td><td class="o_kr_n">' + _n(m.teorico) +
                '</td><td class="o_kr_n">' + _n(m.leido) + '</td><td class="o_kr_n">' + _n(m.diferencia) +
                '</td><td></td></tr>';
            if (self.abiertos[m.modelo]) {
                _.each(m.filas, function (f) {
                    h += '<tr class="o_kr_' + f.estado + '"><td>' + _e(f.talla || f.producto) + '</td><td class="o_kr_n">' +
                        _n(f.teorico) + '</td><td class="o_kr_n">' + _n(f.leido) + '</td><td class="o_kr_n">' +
                        _n(f.diferencia) + (f.estado === 'no_venia' ? ' (no venía)' : '') + '</td><td>' + _e(f.donde) +
                        '</td></tr>';
                });
            }
        });
        if (!algo) { h += '<tr><td colspan="5">Todo cuadra.</td></tr>'; }
        h += '</table>';
        if (this.rec.state === 'leyendo') {
            h += '<div class="o_kr_fila"><button type="button" data-accion="validar" data-valor="1">' +
                'Validar lo leído hasta ahora</button><button type="button" class="o_kr_primario" ' +
                'data-accion="validar" data-valor="0">Validar el contenedor</button></div>';
        }
        return h;
    },
});

core.action_registry.add('koroshi_recepcion_pantalla', Pantalla);
return Pantalla;
});
