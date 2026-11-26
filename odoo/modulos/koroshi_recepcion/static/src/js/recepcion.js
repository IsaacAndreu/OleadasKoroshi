odoo.define('koroshi_recepcion.Pantalla', function (require) {
'use strict';
/* KOROSHI Recepción de contenedores v1.7.0 (26/11/2026) - PDA o tablet.
 * 1.7.0 (Isaac): el modelo se autocompleta al escribir (primero los de las IN y del PL; si queda uno, se pone solo).
 *    Vuelve el KO_ por caja: «🏷 Etiquetas KO» crea N y las manda a la Zebra; se lee el KO de la caja, el modelo y
 *    las uds (con nº y PL, propone las del PL) y se guarda. El nº a mano y «+1 caja» quedan como modo rápido.
 * 1.6.1: el buscador de IN encuentra por contenedor (carrier_tracking_ref; «4099960» o un trozo valen) y dice si no
 *    está en ninguna IN abierta; sin referencia del proveedor ni BL en el buscador ni en pantalla.
 * 1.6.0: datos de la IN: los contenedores (carrier_tracking_ref) rellenan la matrícula; el packing list en Excel
 *    dice qué lleva cada caja («caja 7 de 2711JA12: 40 L»), avisa si el nº no está o ya se contó, y qué nº faltan.
 * 1.5.0: las etiquetas van a la Zebra de Expediciones por la cola de koroshi_impresion (EXP1): última tanda, todos los
 *    palés de la recepción (aunque ya existan) o solo el palé tocado.
 * 1.4.1: «+1 caja» (Isaac: «el escribim 1 vegada i dsp es anar sumant»): con el modelo activo puesto una vez, cada
 *    toque cuenta una caja de ese modelo en el palé activo, sin nº ni uds; «−1» deshace la última. 2 s entre toques.
 * 1.4.0: total de cajas del packing de S4T (o el escrito a mano) y contador «leídas / total · faltan N» siempre
 *    visible en la ficha y al leer.
 * 1.3.0: buscador de IN al crear o cambiar las IN (nombre, pedido, referencia del proveedor o modelo). En «Leer cajas»
 *    todo se escribe con el teclado: Intro acepta el campo y pasa al siguiente (caja → pedido → modelo → uds →
 *    Guardar); en el modelo, Intro busca y si hay uno solo lo coge. El lector sigue igual.
 * 1.2.0 (opción A de Isaac): por caja solo se apunta nº de caja + modelo (REFERENCE de la etiqueta: buscador de modelos
 *    o leer el EAN de una prenda) + uds totales de la caja + palé (+ pedido, opcional). No toca stock: «Cerrar» deja
 *    la IN pendiente hasta leer las prendas al ubicar. Comparación por modelo.
 * 1.1.0: sin contenedor de control KO_. La caja es su nº escrito a mano (rotulador) y, si se quiere, el nº de pedido
 *    de su etiqueta (ORDER NUMBER): si no es de ninguna IN del contenedor, avisa. Recepcionar solo crea palés.
 * 0. Pasar la tarjeta (la misma de Lecturas, Contenedores y Faltante: memoria de la PDA).
 * 1. Lista de contenedores abiertos o «Nuevo contenedor»: matrícula, muelle y las IN que trae.
 * 2. Ficha: «Recepcionar»: cuántos palés usa quien recepciona (crea los PAL-NN A/B que falten; las cajas, opcional)
 *    y el PDF de etiquetas de los palés para la Zebra del PC de Recepciones.
 * 3. Leer, a ciegas: palé y cara (botón o etiqueta), caja (nº a mano y pedido de la etiqueta), prenda (código o
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
        'input .o_kr_buscar': '_onBuscarInput',
        'keydown .o_kr_ncaja, .o_kr_pedido': '_onCampoCaja',
        'keydown .o_kr_cant': '_onCantKey',
        'input .o_kr_cant': '_onCantInput',
        'keydown .o_kr_buscar_in': '_onBuscarInKey',
        'keydown .o_kr_ncaja1': '_onCaja1Key',
        'change .o_kr_in input[type=checkbox]': '_onMarcaIn',
        'change .o_kr_ncaja, .o_kr_pedido': '_onCambiaCaja',
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
        this.caja = '';             // 1.1.0: nº de caja escrito a mano (texto)
        this.ko = null;             // 1.7.0: KO_ pegado en la caja {id, nombre}
        this.pedido = '';           // nº de pedido de la etiqueta (opcional)
        this.modelo = '';           // 1.2.0: modelo de la caja (2711JA22)
        this.resModelos = null;     // buscador de modelos
        this.borrador = {};         // 1.3.0: matrícula, muelle y referencia mientras se buscan IN
        this.textoIn = '';          // 1.3.0: lo buscado en el buscador de IN
        this.masUnoHasta = 0;       // 1.4.1: «+1» bloqueado hasta (doble toque, 2 s)
        this.insVistas = {};        // 1.3.0: id -> IN (para enseñar las marcadas que no salen en la búsqueda)
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
            if (r.tipo === 'producto') { return self._ponerModelo(r.producto.base); }
            self._pintar();
            if (r.tipo === 'caja') { self._siguienteCampo(); }
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
        // 1.7.0: el KO_ es la matrícula de la caja; el nº escrito a mano queda opcional
        this.ko = {id: caja.id, nombre: caja.nombre};
        this.cantidad = '';
        this._aviso(caja.ya ? 'mal' : 'ok', caja.nombre + (caja.ya ? ': OJO, ya tiene ' + caja.ya + '.' : '') +
            (this.modelo ? ' Modelo ' + this.modelo + ': escribe las uds (o «Otro modelo»).' : ' Ahora el modelo.'));
    },
    // nº de caja y pedido (1.1.0): se escriben a mano. Si el lector escribe ahí un código (prenda), se lee como código.
    _pareceCodigo: function (v) { return /^\d{8,}$/.test(v) || /^(PAL|KO_|TT_)/i.test(v); },
    _onCambiaCaja: function () {
        var c = (this.$('.o_kr_ncaja').val() || '').trim();
        var p = (this.$('.o_kr_pedido').val() || '').trim();
        if (!this._pareceCodigo(c)) { this.caja = c; }
        this.pedido = p;
        this._proponerPl();
    },
    _onCampoCaja: function (ev) {
        if (ev.which !== 13 && ev.which !== 9) { return; }
        ev.preventDefault();
        var $i = $(ev.currentTarget);
        var v = ($i.val() || '').trim();
        if ($i.hasClass('o_kr_ncaja') && this._pareceCodigo(v)) {
            $i.val(this.caja || '');
            return this._leer(v, 'campo');
        }
        if ($i.hasClass('o_kr_pedido') && /^\d{12,14}$/.test(v)) {    // un EAN leído en el pedido: es una prenda
            $i.val(this.pedido || '');
            return this._leer(v, 'campo');
        }
        this._onCambiaCaja();
        if ($i.hasClass('o_kr_ncaja')) {
            this.$('.o_kr_pedido').focus();
        } else {
            this._aviso('ok', 'Caja ' + (this.caja || '?') + (this.modelo ? ': escribe las uds.' : ': ahora el modelo.'));
            this._siguienteCampo();
        }
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
            self.borrador = {};
            self.textoIn = '';
            _.each(r.ins, function (i) { self.insVistas[i.id] = i; });
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
            self.textoIn = '';
            _.each(r.ins, function (i) { self.insVistas[i.id] = i; });
            _.each(self.rec.ins, function (i) { self.elegidas[i.id] = true; self.insVistas[i.id] = i; });
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
            picking_ids: ids, employee_id: this.persona.id,
        }).then(function (r) {
            if (!r) { return; }
            self.rec = r.recepcion;
            self.ultimas = [];
            self.vista = 'ficha';
            self._aviso('ok', 'Contenedor ' + r.recepcion.matricula + ' creado (' + r.recepcion.name + ').');
            self._pintar();
        });
    },
    _a_buscar_in_todas: function () { this.$('.o_kr_buscar_in').val(''); this._a_buscar_in(); },
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
            self._aviso('ok', r.tanda ? 'Creado: ' + r.tanda + '. Imprímelas con «🖨 Etiquetas» (van a la Zebra de Expediciones).'
                : 'No había nada nuevo que crear.');
            self._pintar();
        });
    },
    // 1.5.0: a la Zebra de Expediciones por la cola de koroshi_impresion (antes abría el PDF)
    _imprimirEn: function (que, paletId) {
        var self = this;
        if (!this._necesitaPersona()) { return; }
        return this._llamar('/koroshi/recepcion/imprimir', {
            recepcion_id: this.rec.id, que: que, palet_id: paletId || false, employee_id: this.persona.id,
        }).then(function (r) {
            if (!r) { return; }
            self.rec = r.recepcion;
            self._pitido(!!r.conectada);
            self._aviso(r.conectada ? 'ok' : 'mal', 'Enviado a imprimir: ' + r.msg);
        });
    },
    _a_imprimir: function () { this._imprimirEn('ultima'); },
    _a_imprimir_palets: function () {
        if (!window.confirm('¿Imprimir las etiquetas de todos los palés de esta recepción (' + (this.rec.palets || 0) +
                ' palés, caras A y B)?')) { return; }
        this._imprimirEn('palets');
    },
    _a_imprimir_palet: function () {
        if (!this.palet) { this._pitido(false); return this._aviso('mal', 'Toca primero el palé que quieres imprimir.'); }
        this._imprimirEn('palet', this.palet.id);
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
    _a_buscar: function () {
        var self = this;
        var texto = this.$('.o_kr_buscar').val();
        clearTimeout(this.autoTimer);       // 1.7.0: Intro o «Buscar» manda; el autocompletar pendiente, no
        this.autoTexto = null;
        return this._llamar('/koroshi/recepcion/buscar', {recepcion_id: this.rec.id, texto: texto, modelos: true})
            .then(function (r) {
                if (!r) { return; }
                self.resModelos = r.modelos;
                self.resultadosMas = r.mas;
                self.textoBuscado = texto;
                if (!r.modelos.length) { self._aviso('mal', 'No encuentro modelos con «' + texto + '».'); }
                if (r.modelos.length === 1) { return self._ponerModelo(r.modelos[0].modelo); }
                self._pintar();
            });
    },
    _ponerModelo: function (modelo) {
        clearTimeout(this.autoTimer);
        this.autoTexto = null;
        this.modelo = String(modelo || '');
        this.resModelos = null;
        this.textoBuscado = '';
        this.cantidad = '';
        this._aviso('ok', 'Modelo ' + this.modelo + ': escribe las uds de la caja.');
        this._pintar();
        this._siguienteCampo();
        this._proponerPl();
    },
    // 1.3.0: el primer campo que falta (caja, modelo, uds), con el foco puesto para escribir.
    // 1.7.0: con KO leído, el nº a mano no hace falta
    _siguienteCampo: function () {
        var $c = (!this.caja && !this.ko) ? this.$('.o_kr_ncaja')
            : (!this.modelo ? this.$('.o_kr_buscar') : this.$('.o_kr_cant'));
        if ($c.length) { $c.focus(); $c.select(); }
    },
    // 1.7.0: con nº de caja y modelo, propone las uds del packing list (Excel de la IN), si las uds están vacías
    _proponerPl: function () {
        var self = this;
        if (!this.rec || !this.modelo || !this.caja || this.cantidad) { return; }
        var modelo = this.modelo, caja = this.caja;
        this._llamar('/koroshi/recepcion/pl_caja', {recepcion_id: this.rec.id, modelo: modelo, caja: caja}, true)
            .then(function (r) {
                if (!r || !r.uds || self.modelo !== modelo || self.caja !== caja || self.cantidad) { return; }
                self.cantidad = String(r.uds);
                self.$('.o_kr_cant').val(self.cantidad).focus().select();
                self._aviso('ok', 'Según el PL, ' + r.texto + '. Revisa las uds y «Guardar».');
            });
    },
    // 1.7.0: autocompletar el modelo al escribir (sin Intro): a los 3 caracteres, 300 ms después de la última tecla
    _onBuscarInput: function (ev) {
        var self = this;
        var v = (ev.currentTarget.value || '').trim();
        clearTimeout(this.autoTimer);
        if (v.length < 3 || /^\d{8,}$/.test(v)) {      // un EAN se lee con su Intro
            this.resModelos = null;
            this.$('.o_kr_sugerencias').html('');
            return;
        }
        this.autoTimer = setTimeout(function () { self._autocompletar(v); }, 300);
    },
    _autocompletar: function (texto) {
        var self = this;
        this.autoTexto = texto;
        return this._llamar('/koroshi/recepcion/buscar', {recepcion_id: this.rec.id, texto: texto, modelos: true}, true)
            .then(function (r) {
                // solo la respuesta de lo último escrito (las anteriores llegan tarde y se ignoran)
                if (!r || self.autoTexto !== texto || self.modelo) { return; }
                var actual = (self.$('.o_kr_buscar').val() || '').trim();
                if (actual !== texto) { return; }
                self.resModelos = r.modelos;
                self.resultadosMas = r.mas;
                self.textoBuscado = texto;
                if (r.modelos.length === 1 && !r.mas) { return self._ponerModelo(r.modelos[0].modelo); }
                self.$('.o_kr_sugerencias').html(self._htmlSugerencias());
            });
    },
    _htmlSugerencias: function () {
        if (!this.resModelos) { return ''; }
        if (!this.resModelos.length) {
            return '<p class="o_kr_gris">Ningún modelo con «' + _e(this.textoBuscado) + '».</p>';
        }
        var h = '<div class="o_kr_resultados">';
        _.each(this.resModelos, function (m) {
            var propio = m.en_in || m.en_pl;
            h += '<button type="button" data-accion="elegir_modelo" data-valor="' + _e(m.modelo) + '"' +
                (propio ? ' class="o_kr_de_in"' : '') + '><b>' + _e(m.modelo) + '</b> ' + _e(m.nombre) +
                (propio ? (m.en_in ? '' : ' <span class="o_kr_gris">(del PL)</span>')
                    : ' <span class="o_kr_gris">(no está en las IN)</span>') + '</button>';
        });
        if (this.resultadosMas) { h += '<p class="o_kr_gris">Hay más: escribe un trozo más largo.</p>'; }
        return h + '</div>';
    },
    // 1.7.0: «🏷 Etiquetas KO»: crea N KO_ de esta recepción y los manda a la Zebra de Expediciones
    _a_crear_ko: function () {
        var self = this;
        if (!this._necesitaPersona()) { return; }
        var n = parseInt(window.prompt('¿Cuántas etiquetas KO (una por caja)? De 1 a 500 de una vez.', '50'), 10);
        if (!n) { return; }
        if (!window.confirm('Se crean ' + n + ' KO nuevos y se mandan a la Zebra de Expediciones. ¿Seguro?')) { return; }
        return this._llamar('/koroshi/recepcion/crear_ko', {recepcion_id: this.rec.id, cantidad: n,
            employee_id: this.persona.id}).then(function (r) {
            if (!r) { return; }
            self.rec = r.recepcion;
            self._pitido(!!r.conectada);
            self._aviso(r.conectada ? 'ok' : 'mal', r.msg);
            self._pintar();
        });
    },
    _a_quitar_ko: function () { this.ko = null; this._pintar(); this._siguienteCampo(); },
    _onCantInput: function (ev) {
        // un código leído aquí se reconoce al llegar el Intro (_onCantKey); sin Intro, Odoo rechaza la cantidad
        this.cantidad = (ev.currentTarget.value || '').replace(/[^0-9]/g, '');
    },
    _onCantKey: function (ev) {
        if (ev.which !== 13) { return; }
        ev.preventDefault();
        var v = (ev.currentTarget.value || '').trim();
        if (/^\d{8,}$/.test(v)) { ev.currentTarget.value = this.cantidad || ''; return this._leer(v, 'campo'); }
        this.cantidad = v.replace(/[^0-9]/g, '');
        this._a_guardar();
    },
    _a_elegir_modelo: function (m) { this._ponerModelo(m); },
    _a_otro_modelo: function () { this.modelo = ''; this.resModelos = null; this._pintar(); this.$('.o_kr_buscar').focus(); },
    // 1.4.1: «+1 caja» / «−1»
    _a_mas_uno: function () {
        var self = this;
        if (!this._necesitaPersona()) { return; }
        if (Date.now() < this.masUnoHasta) { return; }          // doble toque: 2 s entre «+1»
        this.masUnoHasta = Date.now() + 2000;
        if (!this.modelo) { this._pitido(false); return this._aviso('mal', 'Primero pon el modelo (escríbelo y Intro, o lee una prenda).'); }
        var nCaja = (this.$('.o_kr_ncaja1').val() || '').trim();     // 1.6.0: nº de caja, opcional
        return this._llamar('/koroshi/recepcion/mas_uno', {
            recepcion_id: this.rec.id, palet_id: this.palet ? this.palet.id : false, modelo: this.modelo,
            employee_id: this.persona.id, token: _token(), caja: nCaja,
        }).then(function (r) {
            if (!r) { return; }
            self.rec = r.recepcion;
            self.ultimas = r.ultimas;
            var txt = '+1 ' + (r.pl ? r.pl : (r.caja ? 'caja ' + r.caja + ' de ' : 'caja de ') + (r.modelo || 'sin modelo')) +
                ' · ' + ((self.rec.por_modelo || {})[r.modelo] || 0) + ' de este modelo; ' + self.rec.cajas_leidas + ' / ' +
                (self.rec.total || '?') + ' en total.' + (self.palet ? '' : ' (sin palé)');
            self._pintar();
            self.$('.o_kr_ncaja1').focus();
            if (r.avisos && r.avisos.length) {
                self._pitido(false);
                self._aviso('mal', 'Contada, pero OJO: ' + r.avisos.join('; ') + '. ' + txt);
            } else {
                self._pitido(true);
                self._aviso('ok', txt);
            }
        });
    },
    _a_menos_uno: function () {
        var self = this;
        if (!this._necesitaPersona()) { return; }
        if (!window.confirm('¿Quitar el último «+1»?')) { return; }
        return this._llamar('/koroshi/recepcion/menos_uno', {recepcion_id: this.rec.id, employee_id: this.persona.id})
            .then(function (r) {
                if (!r) { return; }
                self.rec = r.recepcion;
                self.ultimas = r.ultimas;
                self._aviso('ok', 'Quitado un «+1» de ' + (r.modelo || 'sin modelo') + '.');
                self._pintar();
            });
    },
    _htmlMasUno: function () {
        var r = this.rec;
        var n = this.modelo ? ((r.por_modelo || {})[this.modelo] || 0) : 0;
        var faltan = this.modelo ? (r.faltan || {})[this.modelo] : '';
        return '<div class="o_kr_caja ' + (this.modelo ? 'o_kr_hecho' : 'o_kr_falta') + '"><div class="o_kr_etq">' +
            'Contar cajas (modelo activo)</div>' +
            '<div class="o_kr_grande">' + (this.modelo ? _e(this.modelo) + ': ' + n + ' cajas' : 'Pon el modelo abajo (3)') +
            '</div>' + (faltan ? '<div>Faltan (nº): ' + _e(faltan) + '</div>' : '') +
            '<div class="o_kr_fila"><input type="text" class="o_kr_campo o_kr_ncaja1" autocomplete="off" ' +
            'placeholder="nº de caja (si quieres) e Intro" style="max-width:220px"/>' +
            '<button type="button" class="o_kr_primario o_kr_mas_uno" ' +
            'style="font-size:28px;min-width:180px;min-height:70px" data-accion="mas_uno">+1 caja</button>' +
            '<button type="button" data-accion="menos_uno">−1</button></div></div>';
    },
    // 1.6.0: Intro en el nº de caja del «+1» = «+1 caja» (un EAN leído ahí es una prenda: su modelo)
    _onCaja1Key: function (ev) {
        if (ev.which !== 13) { return; }
        ev.preventDefault();
        var v = (ev.currentTarget.value || '').trim();
        if (/^\d{8,}$/.test(v)) { ev.currentTarget.value = ''; return this._leer(v, 'campo'); }
        this.masUnoHasta = 0;
        this._a_mas_uno();
    },
    // 1.6.0: al marcar IN, la matrícula sale de sus contenedores (carrier_tracking_ref) si no se ha escrito otra
    _onMarcaIn: function () {
        var self = this;
        if (this.vista !== 'nueva') { return; }
        this._elegidasIds();
        var $m = this.$('.o_kr_matricula');
        var actual = ($m.val() || '').trim();
        if (actual && actual !== this.matriculaAuto) { return; }
        var conts = [];
        _.each(_.keys(this.elegidas), function (k) {
            var i = self.elegidas[k] && self.insVistas[k];
            _.each(((i && i.contenedores) || '').split(' + '), function (c) {
                if (c && conts.indexOf(c) < 0) { conts.push(c); }
            });
        });
        this.matriculaAuto = conts.join(' + ');
        $m.val(this.matriculaAuto);
    },
    _a_cargar_pl: function () {
        var self = this;
        if (!this._necesitaPersona()) { return; }
        return this._llamar('/koroshi/recepcion/cargar_pl', {recepcion_id: this.rec.id, employee_id: this.persona.id})
            .then(function (r) {
                if (!r) { return; }
                self.rec = r.recepcion;
                self._aviso(r.recepcion.pl_cajas ? 'ok' : 'mal', 'Packing list: ' + r.msg);
                self._pintar();
            });
    },
    _a_cerrar: function () {
        var self = this;
        if (!this._necesitaPersona()) { return; }
        if (!window.confirm('¿Terminar de apuntar cajas? No toca el stock: la IN queda pendiente hasta leer las ' +
                'prendas al ubicar.')) { return; }
        return this._llamar('/koroshi/recepcion/cerrar', {recepcion_id: this.rec.id, employee_id: this.persona.id})
            .then(function (r) {
                if (!r) { return; }
                self.rec = r.recepcion;
                self.vista = 'ficha';
                self._aviso('ok', 'Cerrado: ' + r.recepcion.cajas_leidas + ' cajas, ' + _n(r.recepcion.uds_leidas) +
                    ' uds. La IN sigue pendiente.');
                self._pintar();
            });
    },
    _onBuscarKey: function (ev) {
        if (ev.which !== 13) { return; }
        ev.preventDefault();
        var v = (ev.currentTarget.value || '').trim();
        if (/^\d{8,}$/.test(v)) { ev.currentTarget.value = ''; return this._leer(v, 'campo'); }   // EAN: su modelo
        this._a_buscar();
    },
    // 1.3.0: buscador de IN (crear contenedor o cambiar sus IN)
    _onBuscarInKey: function (ev) {
        if (ev.which === 13) { ev.preventDefault(); this._a_buscar_in(); }
    },
    _guardarBorrador: function () {
        if (this.vista !== 'nueva') { return; }
        this.borrador = {matricula: this.$('.o_kr_matricula').val(), muelle: this.$('.o_kr_muelle').val()};
    },
    _a_buscar_in: function () {
        var self = this;
        this._elegidasIds();             // guarda lo marcado antes de cambiar la lista
        this._guardarBorrador();
        var texto = (this.$('.o_kr_buscar_in').val() || '').trim();
        return this._llamar('/koroshi/recepcion/ins', {
            recepcion_id: this.vista === 'editar_ins' && this.rec ? this.rec.id : false, texto: texto,
        }).then(function (r) {
            if (!r) { return; }
            self.ins = r.ins;
            self.textoIn = texto;
            _.each(r.ins, function (i) { self.insVistas[i.id] = i; });
            if (!r.ins.length) {
                self._aviso('mal', /\d{4,}/.test(texto) && /[A-Za-z]{3,}|^\d{6,}$/.test(texto.replace(/\s/g, ''))
                    ? 'El contenedor «' + texto + '» no está en ninguna IN abierta (ni como nº de IN, pedido o modelo).'
                    : 'Ninguna IN abierta con «' + texto + '».');
            }
            self._pintar();
            self.$('.o_kr_buscar_in').focus();
        });
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
        this.$('.o_kr_cant').val(this.cantidad);
    },
    _a_guardar: function () {
        var self = this;
        if (!this._necesitaPersona()) { return; }
        if (this.$('.o_kr_ncaja').length) { this._onCambiaCaja(); }
        if (this.$('.o_kr_cant').length) { this.cantidad = (this.$('.o_kr_cant').val() || '').replace(/[^0-9]/g, ''); }
        // 1.7.0: con KO, el palé y el nº a mano son opcionales
        if (!this.palet && !this.ko) { this._pitido(false); return this._aviso('mal', 'Falta el palé: tócalo arriba (o lee el KO de la caja).'); }
        if (!this.caja && !this.ko) { this._pitido(false); return this._aviso('mal', 'Lee el KO de la caja o escribe su nº (el escrito a mano).'); }
        if (!this.modelo) { this._pitido(false); return this._aviso('mal', 'Falta el modelo: búscalo o lee una prenda.'); }
        if (!parseInt(this.cantidad, 10)) { this._pitido(false); return this._aviso('mal', 'Escribe las uds de la caja.'); }
        return this._llamar('/koroshi/recepcion/guardar', {
            recepcion_id: this.rec.id, caja: this.caja, pedido: this.pedido, palet_id: this.palet ? this.palet.id : false,
            modelo: this.modelo, producto_id: false, contenedor_id: this.ko ? this.ko.id : false,
            cantidad: parseInt(this.cantidad, 10), employee_id: this.persona.id, token: this.token,
        }).then(function (r) {
            if (!r) { return; }
            self.token = _token();          // la siguiente lectura es otra
            self.rec = r.recepcion;
            self.ultimas = r.ultimas;
            // 1.2.0: una línea por caja; el modelo, el pedido y el palé se quedan para la siguiente caja
            self.caja = '';
            self.ko = null;                 // 1.7.0: la siguiente caja lleva otro KO
            self.cantidad = '';
            self._pintar();
            self.$('.o_kr_ncaja').focus();
            var pl = r.pl ? ' Según el PL: ' + r.pl + '.' : '';
            if (r.avisos && r.avisos.length) {
                self._pitido(false);
                self._aviso('mal', 'Guardado, pero OJO: ' + r.avisos.join('; ') + '. (' + r.msg + ')' + pl);
            } else {
                self._pitido(true);
                self._aviso('ok', 'Guardado: ' + r.msg + pl);
            }
        });
    },
    _a_otra_caja: function () {
        this.caja = '';
        this.ko = null;
        this.pedido = '';
        this.prod = null;
        this.cantidad = '';
        this._pintar();
        this.$('.o_kr_ncaja').focus();
    },
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

    // 1.4.0: «37 / 1046 cajas · faltan 1009»
    _contador: function (r) {
        var total = r.total || 0;
        var h = '<span class="o_kr_grande">' + r.cajas_leidas + ' / ' + (total || '?') + ' cajas</span>';
        if (total) {
            var faltan = total - r.cajas_leidas;
            h += ' <span class="o_kr_grande ' + (faltan > 0 ? 'o_kr_falta' : 'o_kr_hecho') + '">' +
                (faltan > 0 ? 'faltan ' + faltan : (faltan === 0 ? 'completo' : 'sobran ' + (-faltan))) + '</span>';
        }
        if (r.packing_avisos) { h += '<div class="o_kr_gris">' + _e(r.packing_avisos) + '</div>'; }
        return h;
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
            var b = this.borrador || {};
            h += '<label>Contenedores (salen de la IN al marcarla; corrígelos si no son)</label>' +
                '<input type="text" class="o_kr_campo o_kr_matricula" placeholder="MSKU1234567" value="' +
                _e(b.matricula) + '"/>' +
                '<label>Muelle</label><input type="text" class="o_kr_campo o_kr_muelle" placeholder="1" value="' +
                _e(b.muelle) + '"/>';
        }
        h += '<label>¿Qué IN trae? (pedidos de KOROSHI abiertos, por fecha prevista)</label>' +
            '<div class="o_kr_fila"><input type="text" class="o_kr_campo o_kr_buscar_in" autocomplete="off" ' +
            'placeholder="Buscar: contenedor (MIEU4099960), IN (396), pedido (2172) o modelo" value="' + _e(this.textoIn) + '"/>' +
            '<button type="button" data-accion="buscar_in">Buscar</button>' +
            (this.textoIn ? '<button type="button" data-accion="buscar_in_todas">Ver todas</button>' : '') + '</div>';
        var fuera = _.filter(_.keys(this.elegidas), function (k) {
            return self.elegidas[k] && !_.findWhere(self.ins, {id: parseInt(k, 10)});
        });
        if (fuera.length) {
            h += '<p>Marcadas que no salen en esta búsqueda: <b>' + _e(_.map(fuera, function (k) {
                var i = self.insVistas[k];
                return i ? (i.origen || i.name) : ('#' + k);
            }).join(', ')) + '</b></p>';
        }
        if (!this.ins.length) { h += '<p class="o_kr_gris">No hay IN abiertas' + (this.textoIn ? ' con «' +
            _e(this.textoIn) + '»' : '') + '.</p>'; }
        _.each(this.ins, function (i) {
            h += '<div class="o_kr_in"><input type="checkbox" value="' + i.id + '"' +
                (self.elegidas[i.id] ? ' checked="checked"' : '') + '/><div><b>' + _e(i.origen || i.name) + '</b> ' +
                _e(i.name) + (i.backorder ? ' (pendiente de otra)' : '') + ' · ' + _e(i.fecha) + ' · ' + _n(i.uds) +
                ' uds' +
                (i.contenedores ? '<br/>Contenedores: <b>' + _e(i.contenedores) + '</b>' : '') +
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
            '</div>' +
            '<div class="o_kr_gris">Packing list (Excel de la IN): ' + _e(r.pl_info || 'sin cargar') + '</div>';
        h += '<table><tr><th>IN</th><th>Pedido</th><th>Contenedores</th><th>Fecha prevista</th><th>Estado</th>' +
            '<th class="o_kr_n">Uds</th></tr>';
        _.each(r.ins, function (i) {
            h += '<tr><td>' + _e(i.name) + '</td><td>' + _e(i.origen) + '</td><td>' + _e(i.contenedores) + '</td><td>' +
                _e(i.fecha) + '</td><td>' + _e(i.estado) + '</td><td class="o_kr_n">' + _n(i.uds) + '</td></tr>';
        });
        if (!r.ins.length) { h += '<tr><td colspan="6" class="o_kr_gris">Sin IN: añádelas antes de validar.</td></tr>'; }
        h += '</table>';
        h += '<div class="o_kr_fila"><div class="o_kr_caja"><div class="o_kr_etq">Cajas</div><div class="o_kr_grande">' +
            r.cajas_leidas + ' / ' + (r.total || '?') + '</div>' + (r.total ? '<div>faltan ' +
            Math.max(r.total - r.cajas_leidas, 0) + '</div>' : '') + '<div class="o_kr_gris">' +
            (r.cajas ? 'escritas a mano (packing: ' + (r.cajas_packing || '?') + ')' : 'según el packing de S4T') +
            '</div>' + (r.packing_avisos ? '<div class="o_kr_gris">' + _e(r.packing_avisos) + '</div>' : '') +
            '</div><div class="o_kr_caja"><div class="o_kr_etq">Palés</div>' +
            '<div class="o_kr_grande">' + (r.palets || 0) + '</div></div><div class="o_kr_caja"><div class="o_kr_etq">' +
            'Uds leídas / pasadas a stock</div><div class="o_kr_grande">' + _n(r.uds_leidas) + ' / ' +
            _n(r.uds_validadas) + '</div></div></div>';
        h += '<div class="o_kr_fila">';
        if (r.state === 'pendiente') {
            h += '<button type="button" class="o_kr_primario" data-accion="recepcionar">Recepcionar</button>';
        }
        if (r.state === 'leyendo') {
            h += '<button type="button" class="o_kr_primario" data-accion="leer">Leer cajas</button>' +
                '<button type="button" data-accion="recepcionar">+ Palés / cajas</button>';
        }
        if (r.state === 'pendiente' || r.state === 'leyendo') {
            h += '<button type="button" data-accion="crear_ko">🏷 Etiquetas KO (cajas)</button>';
        }
        if (r.tanda_id) { h += '<button type="button" data-accion="imprimir">🖨 Etiquetas (última tanda)</button>'; }
        h += '<button type="button" data-accion="cargar_pl">↻ Packing list (Excel de la IN)</button>';
        if (r.palets) { h += '<button type="button" data-accion="imprimir_palets">🖨 Etiquetas de los palés</button>'; }
        if (r.state === 'pendiente' || r.state === 'leyendo') {
            h += '<button type="button" data-accion="editar_ins">Cambiar IN</button>';
        }
        if (r.state === 'leyendo') {
            h += '<button type="button" data-accion="cerrar">Terminar (cerrar)</button>';
        }
        if (r.responsable) {
            h += '<button type="button" data-accion="exportar">Exportar (Excel)</button>' +
                '<button type="button" data-accion="comparar">Comparar con las IN</button>';
            if (r.state === 'validada' || r.state === 'cerrada') {
                h += '<button type="button" class="o_kr_primario" data-accion="reabrir">Reabrir (llegan cajas)</button>';
            }
        }
        h += '</div>';
        return h + this._htmlUltimas();
    },

    _htmlRecepcionar: function () {
        var r = this.rec;
        return '<div class="o_kr_grande">' + _e(r.matricula) + ': recepcionar</div>' +
            '<p>Se crean los palés que falten, con sus etiquetas (🖨 a la Zebra de Expediciones). Las cajas NO ' +
            'llevan etiqueta nuestra: al leer se escribe el nº que llevan a mano.</p>' +
            '<label>¿Cuántas cajas hay? (opcional: para ver qué números faltan)</label>' +
            '<input type="number" min="0" class="o_kr_campo o_kr_cajas" value="' + (r.cajas || '') + '" placeholder="' +
            (r.cajas_packing ? 'vacío = ' + r.cajas_packing + ' del packing' : '') + '"/>' +
            '<label>¿Cuántos palés vas a usar? (cada palé tiene cara A y cara B)</label>' +
            '<input type="number" min="1" max="99" class="o_kr_campo o_kr_npalets" value="' + (r.palets || '') + '"/>' +
            '<label>Muelle</label><input type="text" class="o_kr_campo o_kr_muelle" value="' + _e(r.muelle) + '"/>' +
            '<div class="o_kr_fila"><button type="button" class="o_kr_primario" data-accion="hacer_recepcionar">' +
            'Crear palés y empezar</button><button type="button" data-accion="ficha">Cancelar</button></div>';
    },

    _htmlLeer: function () {
        var self = this;
        var r = this.rec;
        var h = '<div class="o_kr_fila"><button type="button" data-accion="ficha">← ' + _e(r.matricula) + '</button>' +
            this._contador(r) + '</div>';
        h += this._htmlMasUno();
        h += '<div class="o_kr_etq">1. Palé y cara</div><div class="o_kr_palets">';
        _.each(r.palets_lista, function (p) {
            var activo = self.palet && self.palet.id === p.id;
            h += '<button type="button" data-accion="palet" data-valor="' + p.id + '"' +
                (activo ? ' class="o_kr_activo"' : '') + '>' + _e(p.nombre.replace('PAL-', '')) + '</button>';
        });
        if (!r.palets_lista.length) { h += '<span class="o_kr_gris">Sin palés: «+ Palés / cajas» en la ficha.</span>'; }
        if (this.palet) {
            h += '<button type="button" data-accion="imprimir_palet">🖨 Etiqueta de ' + _e(this.palet.nombre) + '</button>';
        }
        h += '</div>';
        h += '<div class="o_kr_fila">' +
            '<div class="o_kr_caja' + ((this.caja || this.ko) ? ' o_kr_hecho' : ' o_kr_falta') + '"><div class="o_kr_etq">' +
            '2. Caja: lee su etiqueta KO</div>' +
            '<div class="o_kr_grande">' + (this.ko ? _e(this.ko.nombre) : 'Lee el KO') + '</div>' +
            (this.ko ? '<button type="button" data-accion="quitar_ko">Quitar KO</button>' : '') +
            '<label>Nº de caja (el escrito a mano; opcional con KO)</label>' +
            '<input type="text" class="o_kr_campo o_kr_ncaja" autocomplete="off" placeholder="108" value="' +
            _e(this.caja) + '"/>' +
            '<label>Nº de pedido de la etiqueta (ORDER NUMBER, si quieres)</label>' +
            '<input type="text" class="o_kr_campo o_kr_pedido" autocomplete="off" placeholder="0000001936" value="' +
            _e(this.pedido) + '"/>' +
            ((this.caja || this.ko) ? '<button type="button" data-accion="otra_caja">Otra caja</button>' : '') + '</div>' +
            '<div class="o_kr_caja' + (this.palet ? ' o_kr_hecho' : ' o_kr_falta') + '"><div class="o_kr_etq">Palé</div>' +
            '<div class="o_kr_grande">' + (this.palet ? _e(this.palet.nombre) : (this.ko ? 'sin palé (vale con KO)'
                : 'Toca un palé')) + '</div></div></div>';
        h += '<div class="o_kr_caja' + (this.modelo ? ' o_kr_hecho' : ' o_kr_falta') + '"><div class="o_kr_etq">' +
            '3. Modelo (REFERENCE de la etiqueta)</div>';
        if (this.modelo) {
            h += '<div class="o_kr_grande">' + _e(this.modelo) + '</div>' +
                '<button type="button" data-accion="otro_modelo">Otro modelo</button>';
        } else {
            h += '<div>Lee el código de barras de una prenda o escribe el modelo (salen solos):</div>' +
                '<div class="o_kr_fila"><input type="text" class="o_kr_campo o_kr_buscar" autocomplete="off" ' +
                'placeholder="2711JA1…" value="' + _e(this.textoBuscado || '') + '"/>' +
                '<button type="button" data-accion="buscar">Buscar</button></div>' +
                '<div class="o_kr_sugerencias">' + this._htmlSugerencias() + '</div>';
        }
        h += '</div>';
        h += '<div class="o_kr_fila"><div><div class="o_kr_etq">4. Uds de la caja (total)</div>' +
            '<input type="text" inputmode="numeric" autocomplete="off" class="o_kr_campo o_kr_cant o_kr_cantidad" ' +
            'placeholder="0" value="' + _e(this.cantidad) + '"/></div><div class="o_kr_teclado">';
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
            '<th>Palé</th><th>Caja</th><th>Pedido</th><th>Modelo / prenda</th><th class="o_kr_n">Uds</th><th>Quién</th>' +
            '<th></th></tr>';
        _.each(this.ultimas, function (l) {
            h += '<tr><td>' + _e(l.hora) + '</td><td>' + _e(l.palet) + '</td><td>' + _e(l.caja) + '</td><td' +
                (l.ajeno ? ' class="o_kr_falta" title="No es de ninguna IN de este contenedor"' : '') + '>' +
                _e(l.pedido) + (l.ajeno ? ' ⚠' : '') + '</td><td>' +
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
        h += '<div class="o_kr_fila"><div class="o_kr_caja"><div class="o_kr_etq">Uds de las IN</div><div class="o_kr_grande">' +
            _n(c.total.teorico) + '</div></div><div class="o_kr_caja ' + (c.total.leido === c.total.teorico ? 'o_kr_hecho'
            : 'o_kr_falta') + '"><div class="o_kr_etq">Uds llegadas (cajas)</div><div class="o_kr_grande">' +
            _n(c.total.leido) + '</div></div></div>';
        var cj = c.cajas || {leidas: 0, esperadas: 0, huecos: [], n_huecos: 0, ajenas: []};
        h += '<div class="o_kr_fila"><div class="o_kr_caja"><div class="o_kr_etq">Cajas leídas</div>' +
            '<div class="o_kr_grande">' + cj.leidas + (cj.esperadas ? ' / ' + cj.esperadas : '') + '</div></div>' +
            '<div class="o_kr_caja ' + (cj.n_huecos ? 'o_kr_falta' : 'o_kr_hecho') + '"><div class="o_kr_etq">' +
            'Huecos en la numeración</div><div class="o_kr_grande">' + cj.n_huecos + '</div>' +
            (cj.n_huecos ? '<div>' + _e(cj.huecos.join(', ')) + (cj.huecos.length < cj.n_huecos ? '…' : '') +
            '</div>' : '') + '</div>' +
            '<div class="o_kr_caja ' + (cj.ajenas.length ? 'o_kr_falta' : 'o_kr_hecho') + '"><div class="o_kr_etq">' +
            'Cajas de otro pedido</div><div class="o_kr_grande">' + cj.ajenas.length + '</div>' +
            (cj.ajenas.length ? '<div>' + _e(_.map(cj.ajenas, function (a) {
                return 'caja ' + a.caja + ' (pedido ' + a.pedido + ')';
            }).join(', ')) + '</div>' : '') + '</div></div>';
        h += '<table><tr><th>Modelo</th><th class="o_kr_n">Cajas / PL</th><th>Nº que faltan</th>' +
            '<th class="o_kr_n">Uds IN</th><th class="o_kr_n">Llegadas</th><th class="o_kr_n">Diferencia</th>' +
            '<th>Dónde (palé / caja: uds)</th></tr>';
        var algo = false;
        _.each(c.modelos, function (m) {
            if (self.soloProblemas && !m.problema) { return; }
            algo = true;
            h += '<tr class="o_kr_' + m.estado + '"><td>' + _e(m.modelo) + '</td><td class="o_kr_n">' + m.cajas +
                ' / ' + (m.cajas_pl || m.cajas_packing || '?') + '</td><td>' + _e(m.faltan) +
                '</td><td class="o_kr_n">' + _n(m.teorico) + '</td><td class="o_kr_n">' + _n(m.leido) +
                '</td><td class="o_kr_n">' + _n(m.diferencia) + (m.estado === 'no_venia' ? ' (no venía)' : '') +
                '</td><td>' + _e(m.donde) + '</td></tr>';
        });
        if (!algo) { h += '<tr><td colspan="7">Todo cuadra.</td></tr>'; }
        h += '</table>';
        if (this.rec.state === 'leyendo') {
            h += '<div class="o_kr_fila"><button type="button" class="o_kr_primario" data-accion="cerrar">' +
                'Terminar (cerrar; la IN queda pendiente)</button></div>';
        }
        return h;
    },
});

core.action_registry.add('koroshi_recepcion_pantalla', Pantalla);
return Pantalla;
});
