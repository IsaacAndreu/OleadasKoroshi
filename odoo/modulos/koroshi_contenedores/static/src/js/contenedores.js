odoo.define('koroshi_contenedores.Pantalla', function (require) {
'use strict';
/* KOROSHI Contenedores v1.8.0 - mover contenedores KO_/TT_, compactar huecos y ver inventario por lineal.
 * v1.14 (23/11, R23): «Es otro» al lado de «Cambiar»: lo que Odoo llama A en el contenedor es otra prenda (error de
 *   talla). Se lee una prenda de verdad (B), se ponen las uds y «Guardar»: sale A y entra B en una sola operación.
 *   Si no es el mismo modelo o hay reservas de A que no quedarían, avisa y hay que pulsar «Guardar» otra vez.
 * v1.12 (23/11): «Cambiar» por debajo de lo reservado: lo que no está pasa a Faltantes (confirmar 2 veces).
 * v1.11 (23/11): «Poner a cero» con prendas reservadas: pasan a Faltantes (como al marcar un faltante).
 * v1.10 (23/11): «Archivar» en la ficha del contenedor abierto (si no tiene prendas en el sistema).
 * v1.9.3 (23/11): sin «⌨ Escribir», el campo lee al parar el lector (150 ms), sin esperar Intro.
 * v1.9.2 (23/11): el campo lee con Intro o con tabulador al final.
 * v1.9 (20/11): la tarjeta es la misma que en Lecturas y Faltante (memoria de la PDA, clave
 *   koroshi_operarios_pda_<usuario>, {id, nombre, t}). Al entrar se coge la que haya si tiene menos de 15 min sin
 *   actividad; pasar la tarjeta aquí la deja puesta en las otras. La inactividad de 15 min la quita solo aquí.
 * v1.8 (almacén 19/11): la búsqueda por trozo y las sugerencias encuentran todo lo que tiene código: contenedores,
 *   huecos, lineales y artículos (EAN, referencia o nombre). Tocar un resultado lo abre: el contenedor va a la lista,
 *   el hueco se abre, el lineal da su inventario y el artículo dice dónde está.
 * v1.7 (almacén 19/11): en el contenedor abierto, «Cambiar» al lado de cada artículo pone las uds reales (ajuste de
 *   la diferencia, nunca por debajo de lo reservado). Buscar por un trozo del nombre (etiqueta rota): al pulsar
 *   Intro, uno = ese contenedor, varios = lista para elegir; con «⌨ Escribir», sugerencias desde 4 caracteres (v1.8: 3).
 *   Los contenedores de la lista de mover tienen «Abrir» (cantidades, poner a cero, añadir).
 * v1.6 (pruebas del almacén 18/11): botón «← Atrás» (un paso atrás: contenedor → hueco → lineal/artículo → inicio;
 *   tras «Mover marcados» vuelve al hueco); el campo no saca el teclado de la PDA (inputmode=none, como Operarios) y
 *   «⌨ Escribir» lo saca para teclear L94; leer una prenda dice dónde hay stock de ella; la persona se mantiene 15 min;
 *   «Se han movido N contenedores»; al añadir prendas, dos lecturas seguidas del mismo EAN cuentan dos (antes la
 *   segunda en menos de 0,7 s se perdía sin aviso) y «Cantidad» cambia las uds de la última lectura.
 * v1.13: «Añadir prendas» manda un id de tanda: si se corta la wifi y se vuelve a pulsar «Guardar» con lo mismo, no se
 *   añade dos veces (cambiar lo leído = tanda nueva). «Cambiar» manda las uds que enseñaba al abrir: si Odoo ha
 *   cambiado mientras se contaba, no se cambia nada.
 * v1.5: en la lista del hueco cada contenedor tiene casilla: «Marcar vacíos», «Archivar marcados» (no archiva si
 *   alguno tiene prendas) y «Mover marcados» (el siguiente hueco escaneado es el destino). Tocar el nombre abre el
 *   contenedor: «Poner a cero» (no si hay reservas) y «Añadir prendas» (cada lectura = 1 ud, «Guardar»). Son ajustes
 *   de inventario y quedan apuntados con quién y cuándo.
 * v1.4: lo que se lee mientras la pantalla espera a Odoo ya no se pierde: va a una cola corta (EN_ESPERA_MAX) y se
 *   lee después, en orden. Si la cola está llena, pita y lo dice. Una lectura de la cola que falla también pita.
 * 0. Pasar la tarjeta de operario (se mantiene 3 min sin actividad; así queda apuntado quién lo hace).
 * Mover: escanear 1 o más contenedores (se ven prendas y reservas) y después la ubicación de destino.
 * Limpiar: escanear un hueco sin contenedores en cola: se ven sus contenedores; se archivan los que están a cero
 *   tras confirmar que el hueco está físicamente vacío.
 * Inventario: escribir o escanear un lineal (L94): lista de huecos con contenedores y stock; tocar uno lo abre.
 * Todo dentro de .o_koroshi_contenedores. */
var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var session = require('web.session');
var REPETIDA_MS = 700;
var RAFAGA_MS = 150;     // v1.9.3: sin teclado, el campo lee cuando el lector para 150 ms (Odoo usa 55 ms)
var PERSONA_MS = 3600000;        // v1.6: 15 min (antes 3) sin actividad; v1.9.1: parametro
                                // koroshi_operarios.minutos_tarjeta (60 por defecto), se lee al entrar
var EN_ESPERA_MAX = 5;          // v1.4: lecturas guardadas mientras se espera a Odoo

function _e(t) { return _.escape(t == null ? '' : String(t)); }
// v1.13: id de una tanda de «Añadir prendas» (como Devoluciones): un reintento idéntico reusa el mismo id
function _idTanda() {
    return 'C' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}
function _n(x) { return (Math.round((x || 0) * 100) / 100).toString().replace('.', ','); }

var Pantalla = AbstractAction.extend({
    contentTemplate: 'koroshi_contenedores.Pantalla',
    events: {
        'keydown .o_kc_codigo': '_onKeydown',
        'click .o_kc_quitar': '_onQuitar',
        'click .o_kc_vaciar': '_onVaciar',
        'click .o_kc_cambiar': '_onCambiar',
        'click .o_kc_archivar': '_onArchivar',
        'click .o_kc_confirmar_si': '_onConfirmarSi',
        'click .o_kc_confirmar_no': '_onConfirmarNo',
        'click .o_kc_fila_hueco': '_onFilaHueco',
        'click .o_kc_solo_stock': '_onSoloStock',
        'click .o_kc_volver': '_onVolver',
        // v1.5: compactar un hueco
        'change .o_kc_marca': '_onMarca',
        'click .o_kc_marcar_vacios': '_onMarcarVacios',
        'click .o_kc_desmarcar': '_onDesmarcar',
        'click .o_kc_mover_marcados': '_onMoverMarcados',
        'click .o_kc_ver': '_onVer',
        'click .o_kc_volver_hueco': '_onVolverHueco',
        'click .o_kc_cero': '_onCero',
        'click .o_kc_archivar_uno': '_onArchivarUno',     // v1.10
        'click .o_kc_anadir': '_onAnadir',
        'click .o_kc_quitar_ultima': '_onQuitarUltima',
        'click .o_kc_guardar_anadir': '_onGuardarAnadir',
        'click .o_kc_cancelar_anadir': '_onCancelarAnadir',
        // v1.6
        'click .o_kc_atras': '_onAtras',
        'click .o_kc_teclado': '_onTeclado',
        'click .o_kc_cantidad_ok': '_onCantidad',
        'keydown .o_kc_cantidad': '_onCantidadKey',
        // v1.7
        'click .o_kc_editar': '_onEditar',
        'click .o_kc_editar_ok': '_onEditarOk',
        'click .o_kc_editar_no': '_onEditarNo',
        'keydown .o_kc_editar_uds': '_onEditarKey',
        'input .o_kc_codigo': '_onEscribe',
        'click .o_kc_sugerencia': '_onSugerencia',
        'click .o_kc_abrir': '_onVer',
        // v1.14: «Es otro»
        'click .o_kc_otro': '_onOtro',
        'click .o_kc_otro_ok': '_onOtroOk',
        'click .o_kc_otro_no': '_onOtroNo',
        'keydown .o_kc_otro_uds': '_onOtroKey',
    },

    init: function () {
        this._super.apply(this, arguments);
        this.persona = null;
        this.conts = [];
        this.hueco = null;
        this.lineal = null;
        this.soloStock = false;
        this.confirmando = false;
        this.ocupado = false;
        this.ultima = {codigo: '', t: 0};
        this.actividadEn = Date.now();
        this.enEspera = [];             // v1.4
        this.marcados = {};             // v1.5: id -> true (casillas de la lista del hueco)
        this.detalle = null;            // v1.5: contenedor abierto desde la lista del hueco
        this.anadiendo = null;          // v1.5: prendas leídas para añadir al contenedor abierto [{id, nombre, uds}]
        this.lecturasAnadir = [];       // v1.5: orden de lectura (para «Quitar la última»); v1.6: [{id, uds}]
        this.tandaAnadir = null;        // v1.13: id de la tanda; null = lo leído ha cambiado (se crea al guardar)
        this.articulo = null;           // v1.6: dónde hay stock de la prenda leída
        this.origenHueco = null;        // v1.6: hueco del que salen los «Mover marcados» (para «Atrás»)
        this.teclado = false;           // v1.6: campo con teclado de la PDA (para escribir L94)
        this.editando = null;           // v1.7: artículo del contenedor abierto al que se cambia la cantidad
        this.otro = null;               // v1.14: «Es otro» {id, nombre, uds, reservadas, b, n, confirmado, tanda}
        this.candidatos = null;         // v1.7: contenedores que contienen el trozo escrito
        this.buscarTimer = null;        // v1.7: sugerencias mientras se escribe
        this.rafagaTimer = null;        // v1.9.3: lectura del campo al parar el lector
    },

    start: function () {
        var self = this;
        core.bus.on('barcode_scanned', this, this._onBarcodeScanned);
        return this._super.apply(this, arguments).then(function () {
            self.timer = setInterval(self._vigilar.bind(self), 10000);
            self._tomarGuardada();   // v1.9
            self._leerMinutosTarjeta();   // v1.9.1
            self._pintar();
            self._foco();
        });
    },

    // v1.9: al volver a esta pantalla (migas de pan), coge la tarjeta pasada en otra si es distinta
    on_attach_callback: function () {
        this._super.apply(this, arguments);
        if (this._tomarGuardada()) { this._pintar(); }
    },

    destroy: function () {
        core.bus.off('barcode_scanned', this, this._onBarcodeScanned);
        clearInterval(this.timer);
        clearTimeout(this.buscarTimer);
        clearTimeout(this.rafagaTimer);     // v1.9.3
        this._super.apply(this, arguments);
    },

    // ------------------------------------------------------------ v1.9: tarjeta compartida con Lecturas y Faltante
    _clave: function () {
        return 'koroshi_operarios_pda_' + (session.uid || '');
    },
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
    // Coge la tarjeta guardada si es reciente (sin hora = de Lecturas antigua: vale) y no está a mitad de añadir
    // prendas. Devuelve true si ha cambiado la persona.
    _tomarGuardada: function () {
        var g = this._guardada();
        if (!g || !g.id || (this.persona && this.persona.id === g.id)) { return false; }
        if (g.t && Date.now() - g.t > PERSONA_MS) { return false; }
        if (this.anadiendo && this.anadiendo.length) { return false; }
        this.persona = {id: g.id, nombre: g.nombre};
        this.actividadEn = g.t || Date.now();
        return true;
    },
    // Actividad: pone al día la hora de la tarjeta compartida como mucho cada 30 s (si sigue siendo la misma)
    _actividadCompartida: function () {
        if (!this.persona || (this.guardadaEn && this.actividadEn - this.guardadaEn < 30000)) { return; }
        var g = this._guardada();
        if (!g || g.id === this.persona.id) { this._guardarPersona(); }
    },

    // v1.9.1: cuánto dura la tarjeta sin actividad (si falla, se queda con el valor de antes)
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
        // v1.9: la actividad en Lecturas o Faltante con la misma tarjeta también cuenta
        var g = this._guardada();
        if (this.persona && g && g.id === this.persona.id && g.t && g.t > this.actividadEn) {
            this.actividadEn = g.t;
        }
        // v1.5: con prendas leídas sin guardar no se cierra (se perderían)
        if (this.persona && Date.now() - this.actividadEn > PERSONA_MS &&
                !(this.anadiendo && this.anadiendo.length)) {
            this._reiniciar(true);
            this._aviso('', 'Sesión cerrada por inactividad. Pasa tu tarjeta.');
        }
    },

    _reiniciar: function (conPersona) {
        this.conts = [];
        this.hueco = null;
        this.lineal = null;
        this.confirmando = false;
        this.marcados = {};
        this.detalle = null;
        this.anadiendo = null;
        this.lecturasAnadir = [];
        this.articulo = null;
        this.origenHueco = null;
        this.editando = null;
        this.otro = null;               // v1.14
        this.candidatos = null;
        if (conPersona) { this.persona = null; }
        this._pintar();
    },

    _foco: function () {
        var $c = this.$('.o_kc_codigo');
        if ($c.length && document.activeElement !== $c[0]) { $c.focus(); }
    },

    _onKeydown: function (ev) {
        // v1.9.2: Intro o tabulador al final (según cómo esté configurado el lector). Con el campo marcado, Odoo no
        // manda la lectura al bus: si el lector acaba en tabulador, el código se quedaba escrito sin hacer nada.
        if (ev.which === 13 || ev.which === 9) {
            ev.preventDefault();
            clearTimeout(this.rafagaTimer);     // v1.9.3: ya se lee ahora
            var codigo = (ev.currentTarget.value || '').trim();
            ev.currentTarget.value = '';
            this._sugerencias(null);            // v1.7
            if (this.teclado) { this._ponerTeclado(false); }   // v1.6: tras escribir, vuelve sin teclado
            this._leer(codigo, false, 'campo');
        }
    },

    _onBarcodeScanned: function (codigo) { this._leer(codigo, false, 'bus'); },

    // v1.6: sin teclado en pantalla salvo que se pida (el escáner escribe igual en el campo)
    _ponerTeclado: function (si) {
        this.teclado = si;
        var $c = this.$('.o_kc_codigo');
        $c.attr('inputmode', si ? null : 'none');
        this.$('.o_kc_teclado').toggleClass('o_kc_teclado_on', si).text(si ? '⌨ Ocultar' : '⌨ Escribir');
        $c.blur();
        $c.focus();
    },

    _onTeclado: function () { this._ponerTeclado(!this.teclado); },

    _aviso: function (tipo, msg) {
        this.$('.o_kc_aviso').removeClass('o_kc_ok o_kc_mal o_kc_info').addClass(
            msg ? 'o_kc_' + (tipo || 'info') : '').text(msg || '');
    },

    // v1.4: al acabar una petición, la siguiente lectura que esperaba (si no ha empezado otra petición)
    _fin: function () {
        var self = this;
        this.ocupado = false;
        this.actividadEn = Date.now();
        this._actividadCompartida();   // v1.9
        if (this.enEspera.length) {
            setTimeout(function () {
                if (!self.ocupado && self.enEspera.length) { self._leer(self.enEspera.shift(), true); }
            }, 0);
        }
    },

    // v1.4: pitido corto (bien) o doble y grave (mal), sin ficheros de sonido
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

    _sinConexion: function () { this._fin(); this._aviso('mal', 'Sin conexión con Odoo. Vuelve a probar.'); },

    _leer: function (codigo, deCola, fuente) {
        var self = this;
        codigo = (codigo || '').trim();
        if (!codigo) { return; }
        var t = Date.now();
        if (!deCola) {
            // v1.6: una lectura llega dos veces (bus y campo): se descarta la copia de la OTRA vía. Dos lecturas de
            // la misma vía son dos prendas (antes la segunda del mismo EAN en < 0,7 s se perdía al añadir prendas).
            if (codigo === this.ultima.codigo && t - this.ultima.t < REPETIDA_MS &&
                    (!fuente || !this.ultima.fuente || fuente !== this.ultima.fuente)) { return; }
            this.ultima = {codigo: codigo, t: t, fuente: fuente};
        }
        if (this.ocupado) {
            // v1.4: antes se perdía sin avisar. Ahora espera su turno (o pita si ya hay demasiadas)
            if (this.enEspera.length >= EN_ESPERA_MAX) {
                this._pitido(false);
                return this._aviso('mal', 'Espera a que acabe: ' + codigo + ' NO se ha leído. Vuelve a leerlo.');
            }
            this.enEspera.push(codigo);
            return this._aviso('info', codigo + ' leído: va en cuanto acabe lo anterior.');
        }
        if (this.anadiendo) { return this._leerPrenda(codigo); }   // v1.5: modo «Añadir prendas»
        if (this.otro) { return this._leerOtro(codigo); }          // v1.14: «Es otro»: la prenda de verdad
        this.ocupado = true;
        return this._rpc({route: '/koroshi/contenedores/leer', params: {codigo: codigo}}).then(function (r) {
            self._fin();
            if (!r || !r.ok) {
                self._aviso('mal', (r && r.msg) || 'No se ha podido leer.');
                if (deCola) { self._pitido(false); }   // v1.4: el operario ya no lo mira
                return;
            }
            if (r.tipo === 'persona') {
                self.persona = r.persona;
                self._guardarPersona();   // v1.9: queda puesta también en Lecturas y Faltante
                self._aviso('ok', 'Hola, ' + r.persona.nombre + '.');
                self._pintar();
                return;
            }
            if (!self.persona) {
                self._aviso('mal', 'Primero pasa tu tarjeta de operario.');
                return;
            }
            self.confirmando = false;
            self.detalle = null;
            self.editando = null;
            self.candidatos = null;
            if (r.tipo === 'candidatos') {  // v1.7: varios contenedores con ese trozo: elegir uno
                self.candidatos = r;
                self.hueco = null;
                self.lineal = null;
                self.articulo = null;
                self._aviso('info', r.items.length + (r.mas ? '+' : '') + ' resultados con «' + r.texto +
                    '». Toca el tuyo.');
                self._pintar();
                return;
            }
            if (r.tipo === 'articulo') {    // v1.6: dónde hay stock de la prenda (no toca la cola de mover)
                self.articulo = r.articulo;
                self.hueco = null;
                self.lineal = null;
                self._aviso('', '');
                self._pintar();
                return;
            }
            self.articulo = null;
            if (r.tipo === 'lineal') {
                self.conts = [];
                self.hueco = null;
                self.lineal = r.lineal;
                self._aviso(r.lineal.truncado ? 'info' : '', r.lineal.truncado
                    ? 'Lineal muy grande: se muestran solo los primeros huecos.' : '');
                self._pintar();
                return;
            }
            if (r.tipo === 'contenedor') {
                self.hueco = null;
                self.lineal = null;
                var c = r.contenedor;
                if (!_.findWhere(self.conts, {id: c.id})) { self.conts.push(c); }
                self._aviso('', '');
                self._pintar();
                return;
            }
            if (!self.conts.length) {
                self.hueco = r.ubicacion;
                self.marcados = {};
                self.lineal = null;
                self._aviso('', '');
                self._pintar();
                return;
            }
            self.ocupado = true;
            return self._rpc({route: '/koroshi/contenedores/mover', params: {
                contenedor_ids: _.pluck(self.conts, 'id'), destino_id: r.ubicacion.id,
                employee_id: self.persona.id}}).then(function (m) {
                self._fin();
                if (!m || !m.ok) {
                    self._aviso('mal', (m && m.msg) || 'No se ha podido mover.');
                    return;
                }
                self.conts = [];
                self.origenHueco = null;
                self._pintar();
                self._aviso('ok', '✓ ' + m.msg);
            }, self._sinConexion.bind(self));
        }, self._sinConexion.bind(self));
    },

    // ------------------------------------------------------------------ v1.5: compactar un hueco
    // Archivar marcados (con confirmación). El servidor no archiva ninguno si alguno tiene prendas.
    _idsMarcados: function () {
        var self = this;
        if (!this.hueco) { return []; }
        return _.pluck(_.filter(this.hueco.contenedores, function (c) { return self.marcados[c.id]; }), 'id');
    },

    _onMarca: function (ev) {
        var id = parseInt($(ev.currentTarget).data('id'), 10);
        if (ev.currentTarget.checked) { this.marcados[id] = true; } else { delete this.marcados[id]; }
        this.confirmando = false;
        this._pintar();
    },

    _onMarcarVacios: function () {
        var self = this;
        if (!this.hueco) { return; }
        _.each(this.hueco.contenedores, function (c) { if (c.vacio) { self.marcados[c.id] = true; } });
        this.confirmando = false;
        this._pintar();
        this._foco();
    },

    _onDesmarcar: function () {
        this.marcados = {};
        this.confirmando = false;
        this._pintar();
        this._foco();
    },

    _onArchivar: function () {
        if (this.ocupado || !this.hueco || !this.persona || !this._idsMarcados().length) { return; }
        this.confirmando = 'archivar';
        this._pintar();
    },

    _onConfirmarNo: function () {
        this.confirmando = false;
        this._pintar();
        this._foco();
    },

    _onConfirmarSi: function () {
        if (this.confirmando === 'cero') { return this._hacerCero(); }
        if (this.confirmando === 'archivar_uno') { return this._hacerArchivarUno(); }   // v1.10
        var self = this;
        var ids = this._idsMarcados();
        if (this.ocupado || !this.hueco || !this.persona || this.confirmando !== 'archivar' || !ids.length) { return; }
        this.ocupado = true;
        return this._rpc({route: '/koroshi/contenedores/archivar', params: {
            contenedor_ids: ids, ubicacion_id: this.hueco.id, employee_id: this.persona.id,
            confirmado: true}}).then(function (m) {
            self._fin();
            self.confirmando = false;
            if (!m || !m.ok) {
                self._pitido(false);
                self._aviso('mal', (m && m.msg) || 'No se ha podido archivar.');
                self._pintar();
                return;
            }
            self.marcados = {};
            self.hueco = m.ubicacion;
            self._aviso('ok', '✓ ' + m.msg);
            self._pintar();
        }, self._sinConexion.bind(self));
    },

    // Mover marcados: pasan a la cola de mover y el siguiente hueco escaneado es el destino
    _onMoverMarcados: function () {
        var self = this;
        var ids = this._idsMarcados();
        if (this.ocupado || !this.persona || !ids.length) { return; }
        this.ocupado = true;
        return this._rpc({route: '/koroshi/contenedores/detalle', params: {contenedor_ids: ids}}).then(function (r) {
            self._fin();
            if (!r || !r.ok) {
                self._aviso('mal', (r && r.msg) || 'No se han podido coger.');
                return;
            }
            self.conts = r.contenedores;
            self.origenHueco = self.hueco;   // v1.6: «Atrás» vuelve aquí
            self.hueco = null;
            self.lineal = null;
            self.marcados = {};
            self.confirmando = false;
            self._aviso('info', 'Ahora escanea la ubicación de destino.');
            self._pintar();
            self._foco();
        }, self._sinConexion.bind(self));
    },

    // Abrir un contenedor de la lista: ver sus prendas, ponerlo a cero o añadir prendas
    _onVer: function (ev) {
        var self = this;
        var id = parseInt($(ev.currentTarget).data('id'), 10);
        if (this.ocupado || !id) { return; }
        this.ocupado = true;
        return this._rpc({route: '/koroshi/contenedores/detalle', params: {contenedor_ids: [id]}}).then(function (r) {
            self._fin();
            if (!r || !r.ok) {
                self._aviso('mal', (r && r.msg) || 'No se ha podido abrir.');
                return;
            }
            self.detalle = r.contenedores[0];
            self.confirmando = false;
            self._aviso('', '');
            self._pintar();
        }, self._sinConexion.bind(self));
    },

    _onVolverHueco: function () {
        var self = this;
        if (this.anadiendo && this.anadiendo.length) {
            return this._aviso('mal', 'Tienes prendas leídas sin guardar: «Guardar» o «Cancelar» antes.');
        }
        this.detalle = null;
        this.anadiendo = null;
        this.confirmando = false;
        this._aviso('', '');
        if (!this.hueco) { this._pintar(); return; }
        this.ocupado = true;
        return this._rpc({route: '/koroshi/contenedores/hueco', params: {ubicacion_id: this.hueco.id}}).then(function (r) {
            self._fin();
            if (r && r.ok) { self.hueco = r.ubicacion; }
            self.marcados = _.pick(self.marcados, _.pluck(self.hueco.contenedores, 'id'));
            self._pintar();
            self._foco();
        }, self._sinConexion.bind(self));
    },

    _onCero: function () {
        if (this.ocupado || !this.detalle || !this.persona) { return; }
        this.confirmando = 'cero';
        this._pintar();
    },

    // v1.10: archivar el contenedor abierto (vacío en el sistema), con confirmación
    _onArchivarUno: function () {
        if (this.ocupado || !this.detalle || !this.persona || this.detalle.n_lineas) { return; }
        this.confirmando = 'archivar_uno';
        this._pintar();
    },

    _hacerArchivarUno: function () {
        var self = this;
        if (this.ocupado || !this.detalle || !this.persona) { return; }
        var id = this.detalle.id;
        this.ocupado = true;
        return this._rpc({route: '/koroshi/contenedores/archivar_uno', params: {
            contenedor_id: id, employee_id: this.persona.id, confirmado: true}}).then(function (m) {
            self._fin();
            self.confirmando = false;
            if (!m || !m.ok) {
                self._pitido(false);
                self._aviso('mal', (m && m.msg) || 'No se ha podido archivar.');
                self._pintar();
                return;
            }
            // fuera de la lista de mover y de las casillas; vuelve al hueco (o al inicio) como «Volver»
            self.conts = _.reject(self.conts, function (x) { return x.id === id; });
            delete self.marcados[id];
            self._onVolverHueco();
            self._aviso('ok', '✓ ' + m.msg);
        }, self._sinConexion.bind(self));
    },

    _hacerCero: function () {
        var self = this;
        if (this.ocupado || !this.detalle || !this.persona) { return; }
        this.ocupado = true;
        return this._rpc({route: '/koroshi/contenedores/cero', params: {
            contenedor_id: this.detalle.id, employee_id: this.persona.id, confirmado: true,
            pasar_faltantes: !!this.detalle.reservadas}}).then(function (m) {   // v1.11: lo ha confirmado
            self._fin();
            self.confirmando = false;
            if (!m || !m.ok) {
                self._pitido(false);
                self._aviso('mal', (m && m.msg) || 'No se ha podido poner a cero.');
                self._pintar();
                return;
            }
            self.detalle = m.contenedor;
            self._refrescarCont(m.contenedor);
            self._aviso('ok', '✓ ' + m.msg + '. Ya se puede archivar.');
            self._pintar();
        }, self._sinConexion.bind(self));
    },

    // Añadir prendas: cada lectura es una prenda (1 ud) hasta «Guardar» o «Cancelar»
    _onAnadir: function () {
        if (!this.detalle || !this.persona) { return; }
        this.anadiendo = [];
        this.lecturasAnadir = [];
        this.tandaAnadir = null;
        this.confirmando = false;
        this._aviso('info', 'Lee las prendas que hay en ' + this.detalle.nombre + ' (una lectura = 1 ud).');
        this._pintar();
        this._foco();
    },

    _leerPrenda: function (codigo) {
        var self = this;
        this.ocupado = true;
        return this._rpc({route: '/koroshi/contenedores/producto', params: {codigo: codigo}}).then(function (r) {
            self._fin();
            if (!self.anadiendo) { return; }
            if (!r || !r.ok) {
                self._pitido(false);
                self._aviso('mal', (r && r.msg) || 'No se ha podido leer.');
                return;
            }
            var p = r.producto;
            var fila = _.findWhere(self.anadiendo, {id: p.id});
            if (fila) { fila.uds += 1; } else { self.anadiendo.push({id: p.id, nombre: p.nombre, uds: 1}); }
            self.lecturasAnadir.push({id: p.id, uds: 1});
            self.tandaAnadir = null;    // v1.13: contenido nuevo = tanda nueva
            self._pitido(true);
            self._aviso('ok', '+1 ' + p.nombre);
            self._pintar();
        }, self._sinConexion.bind(self));
    },

    _onQuitarUltima: function () {
        if (!this.anadiendo || !this.lecturasAnadir.length) { return; }
        var lec = this.lecturasAnadir.pop();
        this.tandaAnadir = null;
        var fila = _.findWhere(this.anadiendo, {id: lec.id});
        if (fila) {
            fila.uds -= lec.uds;
            if (fila.uds <= 0) { this.anadiendo = _.without(this.anadiendo, fila); }
            this._aviso('info', '−' + lec.uds + ' ' + fila.nombre);
        }
        this._pintar();
        this._foco();
    },

    // v1.6: «Cantidad»: la última lectura pasa a ser N uds (leer una prenda y escribir 12)
    _onCantidad: function () {
        var $q = this.$('.o_kc_cantidad');
        var n = parseInt($q.val(), 10);
        if (!this.anadiendo || !this.lecturasAnadir.length) {
            return this._aviso('mal', 'Lee antes una prenda; la cantidad es para la última leída.');
        }
        if (!(n >= 1 && n <= 500)) {
            return this._aviso('mal', 'Escribe una cantidad entre 1 y 500.');
        }
        var lec = _.last(this.lecturasAnadir);
        var fila = _.findWhere(this.anadiendo, {id: lec.id});
        fila.uds += n - lec.uds;
        lec.uds = n;
        this.tandaAnadir = null;
        this.actividadEn = Date.now();
        this._aviso('ok', n + ' uds de ' + fila.nombre);
        this._pintar();
        this._foco();
    },

    _onCantidadKey: function (ev) {
        if (ev.which !== 13) { return; }
        ev.preventDefault();
        ev.stopPropagation();
        var v = (ev.currentTarget.value || '').trim();
        if (v.length > 4) {             // es una lectura del escáner (EAN), no una cantidad: va como prenda
            ev.currentTarget.value = '';
            this._foco();
            return this._leer(v, false, 'campo');
        }
        this._onCantidad();
    },

    // v1.6: «← Atrás»: deshace un paso de la pantalla (nunca deshace lo guardado en Odoo)
    _onAtras: function () {
        if (this.ocupado) { return; }
        this.actividadEn = Date.now();
        if (this.anadiendo) {
            if (this.anadiendo.length) {
                return this._aviso('mal', 'Tienes prendas leídas sin guardar: «Guardar» o «Cancelar» antes.');
            }
            return this._onCancelarAnadir();
        }
        if (this.confirmando) { return this._onConfirmarNo(); }
        if (this.otro) { return this._onOtroNo(); }             // v1.14
        if (this.editando) { return this._onEditarNo(); }       // v1.7
        if (this.detalle) { return this._onVolverHueco(); }
        if (this.conts.length) {
            if (this.origenHueco) {        // venía de «Mover marcados»: vuelve al hueco
                this.hueco = this.origenHueco;
                this.conts = [];
                this.origenHueco = null;
                this._aviso('', '');
                return this._onVolverHueco();
            }
            var c = this.conts.pop();
            this._aviso('info', 'Quitado ' + c.nombre + ' de la lista.');
            this._pintar();
            return this._foco();
        }
        if (this.hueco) {
            if (this.lineal) { return this._onVolver(); }
            this.hueco = null;             // si se abrió desde un artículo, vuelve a él
            this.marcados = {};
            this._aviso('', '');
            this._pintar();
            return this._foco();
        }
        if (this.lineal || this.articulo) {   // v1.8: si venía de la lista de resultados, vuelve a ella
            this.lineal = null;
            this.articulo = null;
            this._aviso('', '');
            this._pintar();
            return this._foco();
        }
        if (this.candidatos) {                // v1.7; v1.8: lo último, debajo de lo que se abrió desde la lista
            this.candidatos = null;
            this._aviso('', '');
            this._pintar();
            return this._foco();
        }
        this._aviso('info', 'Ya estás al principio.');
        this._foco();
    },

    _onCancelarAnadir: function () {
        this.anadiendo = null;
        this.lecturasAnadir = [];
        this.tandaAnadir = null;
        this._aviso('', 'No se ha añadido nada.');
        this._pintar();
        this._foco();
    },

    _onGuardarAnadir: function () {
        var self = this;
        if (this.ocupado || !this.detalle || !this.persona || !this.anadiendo || !this.anadiendo.length) { return; }
        this.ocupado = true;
        if (!this.tandaAnadir) { this.tandaAnadir = _idTanda(); }
        return this._rpc({route: '/koroshi/contenedores/anadir', params: {
            contenedor_id: this.detalle.id, employee_id: this.persona.id, tanda: this.tandaAnadir,
            lineas: this.anadiendo.map(function (f) { return {producto_id: f.id, uds: f.uds}; })}}).then(function (m) {
            self._fin();
            if (!m || !m.ok) {
                self._pitido(false);
                self._aviso('mal', (m && m.msg) || 'No se ha podido añadir.');
                return;
            }
            self.anadiendo = null;
            self.lecturasAnadir = [];
            self.tandaAnadir = null;
            self.detalle = m.contenedor;
            self._refrescarCont(m.contenedor);
            self._aviso('ok', '✓ ' + m.msg);
            self._pintar();
            self._foco();
        }, function () {
            // v1.13: sin respuesta: puede haberse guardado o no. Se deja todo igual (misma tanda): al volver a pulsar
            // «Guardar», si ya estaba guardado no se añade otra vez.
            self._sinConexion();
            self._aviso('mal', 'Sin conexión al guardar. Vuelve a pulsar «Guardar» (no se añade dos veces).');
        });
    },

    // ------------------------------------------------------------------ v1.7: cambiar la cantidad
    _refrescarCont: function (c) {
        this.conts = this.conts.map(function (x) { return x.id === c.id ? c : x; });
    },

    _onEditar: function (ev) {
        var id = parseInt($(ev.currentTarget).data('producto'), 10);
        if (this.ocupado || !this.detalle || !this.persona || this.anadiendo || this.otro || !id) { return; }
        var lineas = _.filter(this.detalle.lineas, function (l) { return l.producto_id === id; });
        if (!lineas.length) { return; }
        this.editando = {
            id: id, nombre: lineas[0].producto,
            uds: _.reduce(lineas, function (s, l) { return s + l.uds; }, 0),
            reservadas: _.reduce(lineas, function (s, l) { return s + l.reservadas; }, 0),
        };
        this.confirmando = false;
        this.actividadEn = Date.now();
        this._aviso('info', 'Escribe las uds que hay de verdad y «Guardar».');
        this._pintar();
        var $q = this.$('.o_kc_editar_uds');
        $q.focus();
        $q.select();
    },

    _onEditarNo: function () {
        this.editando = null;
        this._aviso('', '');
        this._pintar();
        this._foco();
    },

    _onEditarKey: function (ev) {
        if (ev.which !== 13) { return; }
        ev.preventDefault();
        ev.stopPropagation();
        if ((ev.currentTarget.value || '').trim().length > 5) {   // una lectura del escáner, no una cantidad
            ev.currentTarget.value = '';
            return this._aviso('mal', 'Escribe la cantidad con el teclado (no leas aquí).');
        }
        this._onEditarOk();
    },

    _onEditarOk: function () {
        var self = this;
        var e = this.editando;
        if (this.ocupado || !e || !this.detalle || !this.persona) { return; }
        var v = (this.$('.o_kc_editar_uds').val() || '').trim();
        var n = parseInt(v, 10);
        if (!/^\d+$/.test(v) || !(n >= 0)) {
            return this._aviso('mal', 'Escribe un número de uds (0 o más).');
        }
        if (n < e.reservadas && e.confirmar !== n) {
            // v1.12: se puede, pero las reservadas que no están pasan a Faltantes: se confirma con otro «Guardar»
            e.confirmar = n;
            e.nuevas = n;
            this._pintar();
            return;
        }
        if (n === e.uds) {
            return this._aviso('info', 'Ya tiene ' + n + ' uds: no se cambia nada.');
        }
        this.ocupado = true;
        return this._rpc({route: '/koroshi/contenedores/cantidad', params: {
            contenedor_id: this.detalle.id, employee_id: this.persona.id, producto_id: e.id,
            uds: n, pasar_faltantes: n < e.reservadas, antes: e.uds}}).then(function (m) {
            self._fin();
            if (!m || !m.ok) {
                self._pitido(false);
                self._aviso('mal', (m && m.msg) || 'No se ha podido cambiar.');
                return;
            }
            self.editando = null;
            self.detalle = m.contenedor;
            self._refrescarCont(m.contenedor);
            self._pitido(true);
            self._aviso('ok', '✓ ' + m.msg);
            self._pintar();
            self._foco();
        }, self._sinConexion.bind(self));
    },

    // ------------------------------------------------------------------ v1.14 (R23): «Es otro» (error de talla)
    _onOtro: function (ev) {
        var id = parseInt($(ev.currentTarget).data('producto'), 10);
        if (this.ocupado || !this.detalle || !this.persona || this.anadiendo || this.editando || !id) { return; }
        var lineas = _.filter(this.detalle.lineas, function (l) { return l.producto_id === id; });
        if (!lineas.length) { return; }
        this.otro = {
            id: id, nombre: lineas[0].producto,
            uds: _.reduce(lineas, function (s, l) { return s + l.uds; }, 0),
            reservadas: _.reduce(lineas, function (s, l) { return s + l.reservadas; }, 0),
            b: null, n: undefined, confirmado: null, tanda: null, tandaClave: null,
        };
        this.confirmando = false;
        this.actividadEn = Date.now();
        this._aviso('info', 'Lee una prenda de las que hay DE VERDAD en el contenedor.');
        this._pintar();
        this._foco();
    },

    _onOtroNo: function () {
        this.otro = null;
        this._aviso('', 'No se ha cambiado nada.');
        this._pintar();
        this._foco();
    },

    _leerOtro: function (codigo) {
        var self = this;
        var o = this.otro;
        this.ocupado = true;
        return this._rpc({route: '/koroshi/contenedores/producto', params: {codigo: codigo, modelo_de: o.id}})
            .then(function (r) {
                self._fin();
                if (self.otro !== o) { return; }
                if (!r || !r.ok) {
                    self._pitido(false);
                    self._aviso('mal', (r && r.msg) || 'No se ha podido leer.');
                    return;
                }
                if (r.producto.id === o.id) {
                    self._pitido(false);
                    self._aviso('mal', 'Es el mismo artículo que dice Odoo. Si faltan o sobran uds, usa «Cambiar».');
                    return;
                }
                o.b = r.producto;
                o.confirmado = null;
                self._pitido(true);
                self._aviso(r.producto.mismo_modelo ? 'ok' : 'mal', r.producto.mismo_modelo
                    ? 'Ahora pon cuántas uds son ' + r.producto.nombre + ' y «Guardar».'
                    : 'Ojo: NO es el mismo modelo. Revisa la prenda antes de guardar.');
                self._pintar();
                var $q = self.$('.o_kc_otro_uds');
                $q.focus();
                $q.select();
            }, self._sinConexion.bind(self));
    },

    _onOtroKey: function (ev) {
        if (ev.which !== 13) { return; }
        ev.preventDefault();
        ev.stopPropagation();
        var v = (ev.currentTarget.value || '').trim();
        if (v.length > 5) {             // una lectura del escáner: es otra prenda, no una cantidad
            ev.currentTarget.value = '';
            return this._leer(v, false, 'campo');
        }
        this._onOtroOk();
    },

    _onOtroOk: function () {
        var self = this;
        var o = this.otro;
        if (this.ocupado || !o || !o.b || !this.detalle || !this.persona) { return; }
        var $q = this.$('.o_kc_otro_uds');
        var v = ($q.val() || '').trim();
        if (v.length > 5) {             // el lector ha escrito en la casilla (la PDA no manda Intro)
            $q.val('');
            return this._leer(v, false, 'campo');
        }
        var n = parseInt(v, 10);
        if (!/^\d+$/.test(v) || !(n >= 1)) {
            return this._aviso('mal', 'Escribe cuántas uds son ' + o.b.nombre + ' (1 o más).');
        }
        if (n > o.uds) {
            return this._aviso('mal', 'Solo hay ' + _n(o.uds) + ' uds de ' + o.nombre + ' en el contenedor.');
        }
        var aFaltantes = Math.max(0, o.reservadas - (o.uds - n));
        var clave = o.b.id + '|' + n;
        if ((aFaltantes > 0 || !o.b.mismo_modelo) && o.confirmado !== clave) {
            // como «Cambiar» (v1.12): lo que tiene consecuencias se confirma con otro «Guardar»
            o.confirmado = clave;
            o.n = n;
            o.aFaltantes = aFaltantes;
            this._aviso('info', 'Lee el aviso en rojo y pulsa «Guardar» otra vez.');
            this._pintar();
            return;
        }
        if (!o.tanda || o.tandaClave !== clave) {   // misma operación = misma tanda (un reintento no se repite)
            o.tanda = _idTanda();
            o.tandaClave = clave;
        }
        this.ocupado = true;
        return this._rpc({route: '/koroshi/contenedores/cambiar_articulo', params: {
            contenedor_id: this.detalle.id, employee_id: this.persona.id, producto_id: o.id,
            producto_real_id: o.b.id, uds: n, antes: o.uds, tanda: o.tanda,
            pasar_faltantes: aFaltantes > 0, otro_modelo: !o.b.mismo_modelo}}).then(function (m) {
            self._fin();
            if (!m || !m.ok) {
                self._pitido(false);
                self._aviso('mal', (m && m.msg) || 'No se ha podido cambiar.');
                return;
            }
            self.otro = null;
            self.detalle = m.contenedor;
            self._refrescarCont(m.contenedor);
            self._pitido(true);
            self._aviso('ok', '✓ ' + m.msg);
            self._pintar();
            self._foco();
        }, function () {
            // sin respuesta: puede haberse guardado o no. Misma tanda: al volver a pulsar no se hace dos veces
            self._sinConexion();
            self._aviso('mal', 'Sin conexión al guardar. Vuelve a pulsar «Guardar» (no se hace dos veces).');
        });
    },

    // ------------------------------------------------------------------ v1.7: buscar por un trozo del nombre
    // Con «⌨ Escribir»: desde 4 caracteres salen los contenedores que lo contienen (no con el escáner)
    _onEscribe: function (ev) {
        var self = this;
        clearTimeout(this.buscarTimer);
        clearTimeout(this.rafagaTimer);
        var v = (ev.currentTarget.value || '').trim();
        // v1.9.3: sin «⌨ Escribir» no hay teclado: lo que entra en el campo es el lector. Las PDA no mandan Intro ni
        // tabulador al final (Odoo en el móvil lee al pasar 55 ms sin teclas, pero solo si no hay campo marcado), así
        // que con el campo marcado la lectura se quedaba escrita. Ahora se lee al parar la ráfaga, como hace Odoo.
        if (!this.teclado) {
            var campo = ev.currentTarget;
            this.rafagaTimer = setTimeout(function () {
                var codigo = (campo.value || '').trim();
                if (!codigo) { return; }          // ya se leyó con Intro o tabulador
                campo.value = '';
                self._leer(codigo, false, 'campo');
            }, RAFAGA_MS);
            return this._sugerencias(null);
        }
        if (!this.teclado || v.length < 3) { return this._sugerencias(null); }   // v1.8: desde 3 (L94)
        this.buscarTimer = setTimeout(function () {
            self._rpc({route: '/koroshi/contenedores/buscar', params: {texto: v}}).then(function (r) {
                if ((self.$('.o_kc_codigo').val() || '').trim() !== v) { return; }   // ya ha escrito más
                self._sugerencias(r && r.ok ? r : null);
            }, function () { self._sugerencias(null); });
        }, 350);
    },

    // v1.8: resultados de cualquier tipo (contenedor, hueco, lineal, artículo)
    _htmlItems: function (items, mas) {
        var TIPOS = {contenedor: 'Contenedor', hueco: 'Ubicación', lineal: 'Lineal', articulo: 'Artículo'};
        return items.map(function (it) {
            return '<button type="button" class="o_kc_sugerencia" data-tipo="' + it.tipo + '" data-id="' + it.id +
                '" data-codigo="' + _e(it.codigo || it.nombre) + '"><span class="o_kc_tipo o_kc_tipo_' + it.tipo +
                '">' + TIPOS[it.tipo] + '</span>' + _e(it.nombre) + '<br/><small>' + _e(it.detalle) + '</small></button>';
        }).join('') + (mas ? '<div class="o_kc_vacio">Hay más: escribe más.</div>' : '');
    },

    _sugerencias: function (r) {
        var $s = this.$('.o_kc_sugerencias');
        if (!r || !r.items || !r.items.length) { return $s.html(''); }
        $s.html(this._htmlItems(r.items, r.mas));
    },

    _onSugerencia: function (ev) {
        var $b = $(ev.currentTarget);
        var tipo = String($b.data('tipo') || 'contenedor');
        var id = parseInt($b.data('id'), 10);
        var codigo = String($b.data('codigo') || '');
        clearTimeout(this.buscarTimer);
        this.$('.o_kc_codigo').val('');
        this._sugerencias(null);
        if (this.teclado) { this._ponerTeclado(false); }
        if (tipo === 'hueco') { return this._abrirHueco(id); }
        if (tipo === 'articulo') { return this._abrirArticulo(id); }
        this._leer(codigo, false, 'toque');   // contenedor (a la lista de mover) o lineal
    },

    _abrirArticulo: function (id) {
        var self = this;
        if (this.ocupado || !id) { return; }
        this.ocupado = true;
        return this._rpc({route: '/koroshi/contenedores/donde', params: {producto_id: id}}).then(function (r) {
            self._fin();
            if (!r || !r.ok) {
                self._aviso('mal', (r && r.msg) || 'No se ha podido abrir.');
                return;
            }
            self.articulo = r.articulo;
            self.hueco = null;
            self.lineal = null;
            self.detalle = null;
            self._aviso('', '');
            self._pintar();
        }, self._sinConexion.bind(self));
    },

    _pintarCandidatos: function () {
        var r = this.candidatos;
        if (!r || this.hueco || this.lineal || this.detalle || this.articulo) { return ''; }
        return '<div class="o_kc_card"><h3>Resultados con «' + _e(r.texto) + '»</h3>' +
            this._htmlItems(r.items, r.mas) + '</div>';
    },

    // ------------------------------------------------------------------ inventario por lineal
    _refrescarLineal: function () {
        var self = this;
        if (!this.lineal) { this._pintar(); return; }
        return this._rpc({route: '/koroshi/contenedores/leer', params: {codigo: this.lineal.codigo}}).then(function (r) {
            if (r && r.ok && r.tipo === 'lineal') { self.lineal = r.lineal; }
            self._pintar();
        }, function () { self._pintar(); });
    },

    _onFilaHueco: function (ev) {
        return this._abrirHueco(parseInt($(ev.currentTarget).data('id'), 10));
    },

    _abrirHueco: function (id) {   // v1.8: también desde la búsqueda
        var self = this;
        if (this.ocupado || !id) { return; }
        this.ocupado = true;
        return this._rpc({route: '/koroshi/contenedores/hueco', params: {ubicacion_id: id}}).then(function (r) {
            self._fin();
            if (!r || !r.ok) {
                self._aviso('mal', (r && r.msg) || 'No se ha podido abrir.');
                return;
            }
            self.hueco = r.ubicacion;
            self.marcados = {};
            self.detalle = null;
            self.confirmando = false;
            self._aviso('', '');
            self._pintar();
        }, self._sinConexion.bind(self));
    },

    _onSoloStock: function () {
        this.soloStock = !this.soloStock;
        this._pintar();
        this._foco();
    },

    _onVolver: function () {
        this.hueco = null;
        this.detalle = null;
        this.marcados = {};
        this.confirmando = false;
        this._aviso('', '');
        this._refrescarLineal();
        this._foco();
    },

    _onQuitar: function (ev) {
        var id = parseInt($(ev.currentTarget).data('id'), 10);
        this.conts = _.reject(this.conts, function (c) { return c.id === id; });
        this._pintar();
        this._foco();
    },

    _onVaciar: function () {
        this._reiniciar(false);
        this._aviso('', '');
        this._foco();
    },

    _onCambiar: function () {
        this._reiniciar(true);
        this._aviso('', '');
        this._foco();
    },

    // ------------------------------------------------------------------ pintar
    // v1.6: dónde hay stock de la prenda leída; tocar un hueco lo abre
    _pintarArticulo: function () {
        var a = this.articulo;
        if (!a || this.hueco || this.lineal || this.detalle) { return ''; }
        var html = '<div class="o_kc_card"><h3>' + _e(a.nombre) + '</h3><div>' + _n(a.uds) + ' uds en ' +
            (a.filas.length + a.mas) + ' sitio(s)' + (a.reservadas ? ' · ' + _n(a.reservadas) + ' reservadas' : '') +
            '. Toca un hueco para abrirlo.</div>';
        if (!a.filas.length) {
            return html + '<div class="o_kc_vacio">No hay stock de este artículo en ninguna ubicación.</div></div>';
        }
        html += '<table>' + a.filas.map(function (f) {
            return '<tr class="o_kc_fila_hueco o_kc_con" data-id="' + f.hueco_id + '"><td>' + _e(f.hueco) +
                (f.contenedor ? '<br/><small>' + _e(f.contenedor) + '</small>' : '') + '</td><td class="o_kc_n">' +
                _n(f.uds) + ' uds' + (f.reservadas ? ' (res. ' + _n(f.reservadas) + ')' : '') + '</td></tr>';
        }).join('') + (a.mas ? '<tr><td colspan="2">… y ' + a.mas + ' sitios más</td></tr>' : '') + '</table>';
        return html + '</div>';
    },

    _pintarLineal: function () {
        var l = this.lineal;
        if (!l || this.hueco) { return ''; }
        var filas = this.soloStock ? _.filter(l.huecos, function (h) { return h.uds || h.directo_uds; }) : l.huecos;
        var html = '<div class="o_kc_card"><h3>Lineal ' + _e(l.codigo) + '</h3><div>' + l.huecos.length +
            ' huecos · ' + l.con_stock + ' con stock · ' + _n(l.uds) + ' uds</div>' +
            '<button type="button" class="o_kc_solo_stock">' + (this.soloStock ? 'Ver todos los huecos' : 'Ver solo con stock') +
            '</button>';
        if (!filas.length) {
            html += '<div class="o_kc_vacio">' + (this.soloStock ? 'Ningún hueco con stock.' : 'Sin huecos.') + '</div>';
        } else {
            html += '<table>' + filas.map(function (h) {
                var hay = h.uds || h.directo_uds;
                return '<tr class="o_kc_fila_hueco ' + (hay ? 'o_kc_con' : 'o_kc_sin') + '" data-id="' + h.id + '"><td>' +
                    _e(h.nombre) + '</td><td class="o_kc_n">' + h.n_cont + ' cont.' +
                    (hay ? ' · ' + h.n_cont_stock + ' con stock · ' + _n(h.uds + h.directo_uds) + ' uds' : ' · vacío') +
                    (h.directo_uds ? ' (' + _n(h.directo_uds) + ' sueltas)' : '') + '</td></tr>';
            }).join('') + '</table>';
        }
        return html + '</div>';
    },

    // v1.5: lista del hueco con casillas; «Marcar vacíos», «Archivar marcados», «Mover marcados»
    _pintarHueco: function () {
        var self = this;
        var h = this.hueco;
        if (!h || this.detalle) { return ''; }
        var html = '';
        if (this.lineal) {
            html += '<button type="button" class="o_kc_volver">← Volver al lineal ' + _e(this.lineal.codigo) + '</button>';
        }
        html += '<div class="o_kc_card"><h3>' + _e(h.nombre) + '</h3>';
        if (h.directo_n) {
            html += '<div class="o_kc_vacio">Hay ' + _n(h.directo_uds) + ' uds en el propio hueco (fuera de contenedores).</div>';
        }
        if (!h.contenedores.length) {
            return html + '<div>Sin contenedores KO_/TT_: ya está limpia.</div></div>';
        }
        var nVacios = _.where(h.contenedores, {vacio: true}).length;
        html += '<div>' + h.contenedores.length + ' contenedores · ' + nVacios + ' a cero · ' +
            (h.contenedores.length - nVacios) + ' con prendas. Toca el nombre para ver, poner a cero o añadir.</div>' +
            '<div class="o_kc_acciones"><button type="button" class="o_kc_marcar_vacios">Marcar vacíos</button>' +
            '<button type="button" class="o_kc_desmarcar">Desmarcar</button></div>';
        html += '<table class="o_kc_tabla_hueco">' + h.contenedores.map(function (c) {
            var marcado = !!self.marcados[c.id];
            return '<tr class="' + (c.vacio ? 'o_kc_sin' : 'o_kc_con') + (marcado ? ' o_kc_marcado' : '') + '">' +
                '<td class="o_kc_td_marca"><input type="checkbox" class="o_kc_marca" data-id="' + c.id + '"' +
                (marcado ? ' checked="checked"' : '') + '/></td>' +
                '<td><button type="button" class="o_kc_ver" data-id="' + c.id + '">' + _e(c.nombre) + '</button></td>' +
                '<td class="o_kc_n">' + (c.vacio ? 'VACÍO' : c.n_lineas + ' ref. · ' + _n(c.uds) + ' uds' +
                    (c.reservadas ? ' (res. ' + _n(c.reservadas) + ')' : '')) + '</td></tr>';
        }).join('') + '</table>';
        var ids = this._idsMarcados();
        if (this.confirmando === 'archivar') {
            html += '<div class="o_kc_confirmar"><div><b>¿Confirmas que estos ' + ids.length +
                ' contenedores están FÍSICAMENTE vacíos?</b></div>' +
                '<button type="button" class="o_kc_confirmar_si">Sí, vacíos: archivar ' + ids.length + '</button>' +
                '<button type="button" class="o_kc_confirmar_no">No</button></div>';
        } else {
            html += '<div class="o_kc_acciones">' +
                '<button type="button" class="o_kc_archivar"' + (ids.length ? '' : ' disabled="disabled"') +
                '>Archivar marcados (' + ids.length + ')</button>' +
                '<button type="button" class="o_kc_mover_marcados"' + (ids.length ? '' : ' disabled="disabled"') +
                '>Mover marcados (' + ids.length + ')</button></div>';
        }
        return html + '</div>';
    },

    // v1.5: un contenedor abierto desde la lista: prendas, «Poner a cero» y «Añadir prendas»
    _pintarDetalle: function () {
        var c = this.detalle;
        if (!c) { return ''; }
        var e = this.editando;
        var o = this.otro;              // v1.14
        var puedeEditar = !this.anadiendo && !this.confirmando && !e && !o;
        var html = '<button type="button" class="o_kc_volver_hueco">' + (this.hueco ? '← Volver al hueco' : '← Volver') +
            '</button>' +
            '<div class="o_kc_card"><h3>' + _e(c.nombre) + '</h3><div class="o_kc_hueco">En: ' + _e(c.hueco) + '</div>';
        if (c.n_lineas) {
            html += '<div>' + c.n_lineas + ' ref. · ' + _n(c.uds) + ' uds' +
                (c.reservadas ? ' · <b>' + _n(c.reservadas) + ' reservadas</b>' : '') + '</div><table>' +
                c.lineas.map(function (l) {
                    return '<tr><td>' + _e(l.producto) + '</td><td class="o_kc_n">' + _n(l.uds) +
                        (l.reservadas ? ' (res. ' + _n(l.reservadas) + ')' : '') +
                        (puedeEditar ? '<button type="button" class="o_kc_editar" data-producto="' + l.producto_id +
                            '">Cambiar</button><button type="button" class="o_kc_otro" data-producto="' +
                            l.producto_id + '">Es otro</button>' : '') + '</td></tr>';
                }).join('') + (c.mas ? '<tr><td colspan="2">… y ' + c.mas + ' referencias más</td></tr>' : '') +
                '</table>';
        } else {
            html += '<div class="o_kc_vacio">Sin prendas en el sistema</div>';
        }
        if (o) {                        // v1.14: «Es otro»
            html += '<div class="o_kc_editar_caja o_kc_otro_caja"><div>Odoo dice: <b>' + _e(o.nombre) + '</b> · ' +
                _n(o.uds) + ' uds' + (o.reservadas ? ' · ' + _n(o.reservadas) + ' reservadas para un pedido' : '') +
                '</div>';
            if (!o.b) {
                html += '<div class="o_kc_otro_lee">Lee una prenda de las que hay DE VERDAD.</div>';
            } else {
                html += '<div>De verdad es: <b>' + _e(o.b.nombre) + '</b></div>' +
                    (o.b.mismo_modelo ? '' : '<div class="o_kc_aviso_reserva"><b>NO es el mismo modelo</b> (no es ' +
                        'solo otra talla). Si de verdad es así, pulsa «Guardar» otra vez.</div>') +
                    '¿Cuántas uds son ' + _e(o.b.nombre) + '? <input type="number" class="o_kc_otro_uds" ' +
                    'inputmode="numeric" min="1" step="1" value="' +
                    (o.n !== undefined ? o.n : Math.round(o.uds)) + '"/>' +
                    (o.confirmado && o.aFaltantes > 0 ? '<div class="o_kc_aviso_reserva"><b>' + _n(o.aFaltantes) +
                        ' uds de ' + _e(o.nombre) + ' reservadas no quedarían: pasan a Faltantes</b> (la OUT las ' +
                        'coge de otro hueco con stock o, si no hay, sale sin ellas). Pulsa «Guardar» otra vez.</div>'
                        : '');
            }
            html += '<div><button type="button" class="o_kc_otro_ok"' + (o.b ? '' : ' disabled="disabled"') +
                '>Guardar</button><button type="button" class="o_kc_otro_no">Cancelar</button></div></div>';
            return html + '</div>';
        }
        if (e) {                        // v1.7: uds reales de un artículo
            html += '<div class="o_kc_editar_caja"><b>' + _e(e.nombre) + '</b><div>Ahora: ' + _n(e.uds) + ' uds' +
                (e.reservadas ? ' · ' + _n(e.reservadas) + ' reservadas para un pedido' : '') +
                '</div>Hay de verdad: <input type="number" class="o_kc_editar_uds" inputmode="numeric" min="0" ' +
                'step="1" value="' + (e.nuevas !== undefined ? e.nuevas : Math.round(e.uds)) + '"/>' +
                (e.confirmar !== undefined ? '<div class="o_kc_aviso_reserva"><b>' +
                    _n(e.reservadas - e.confirmar) + ' uds reservadas no están: pasan a Faltantes</b> (la OUT las ' +
                    'coge de otro hueco con stock o, si no hay, sale sin ellas). Pulsa «Guardar» otra vez.</div>' : '') +
                '<div><button type="button" class="o_kc_editar_ok">Guardar</button>' +
                '<button type="button" class="o_kc_editar_no">Cancelar</button></div></div>';
            return html + '</div>';
        }
        if (this.anadiendo) {
            var total = _.reduce(this.anadiendo, function (s, f) { return s + f.uds; }, 0);
            html += '<div class="o_kc_anadir_caja"><b>Añadir a ' + _e(c.nombre) + ': lee cada prenda</b>' +
                '<div class="o_kc_cantidad_fila">Cantidad de la última: <input type="number" class="o_kc_cantidad" ' +
                'inputmode="numeric" min="1" max="500" step="1"/><button type="button" class="o_kc_cantidad_ok">' +
                'Poner</button></div>';
            html += this.anadiendo.length ? '<table>' + this.anadiendo.map(function (f) {
                return '<tr><td>' + _e(f.nombre) + '</td><td class="o_kc_n">+' + f.uds + '</td></tr>';
            }).join('') + '</table>' : '<div>Aún nada leído.</div>';
            html += '<div class="o_kc_acciones">' +
                '<button type="button" class="o_kc_guardar_anadir"' + (total ? '' : ' disabled="disabled"') +
                '>Guardar (' + total + ' uds)</button>' +
                '<button type="button" class="o_kc_quitar_ultima"' + (total ? '' : ' disabled="disabled"') +
                '>Quitar la última</button>' +
                '<button type="button" class="o_kc_cancelar_anadir">Cancelar</button></div></div>';
        } else if (this.confirmando === 'cero') {
            html += '<div class="o_kc_confirmar"><div><b>¿' + _e(c.nombre) + ' está FÍSICAMENTE vacío?</b> Las ' +
                _n(c.uds) + ' uds saldrán del stock (ajuste de inventario, queda apuntado quién lo hace).' +
                (c.reservadas ? ' <b>' + _n(c.reservadas) + ' están reservadas para un pedido: pasan a Faltantes</b> ' +
                    '(la OUT las coge de otro hueco con stock o, si no hay, sale sin ellas).' : '') + '</div>' +
                '<button type="button" class="o_kc_confirmar_si">Sí, vacío: poner a cero</button>' +
                '<button type="button" class="o_kc_confirmar_no">No</button></div>';
        } else if (this.confirmando === 'archivar_uno') {     // v1.10
            html += '<div class="o_kc_confirmar"><div><b>¿' + _e(c.nombre) + ' está FÍSICAMENTE vacío?</b> Se ' +
                'archiva y deja de salir en Odoo (queda apuntado quién lo hace).</div>' +
                '<button type="button" class="o_kc_confirmar_si">Sí, vacío: archivar</button>' +
                '<button type="button" class="o_kc_confirmar_no">No</button></div>';
        } else {
            html += '<div class="o_kc_acciones">' +
                (c.n_lineas ? '<button type="button" class="o_kc_cero">Poner a cero</button>'
                    : '<button type="button" class="o_kc_archivar_uno">Archivar</button>') +   // v1.10
                '<button type="button" class="o_kc_anadir">Añadir prendas</button></div>';
            if (c.n_lineas) {
                html += '<div class="o_kc_vacio">Para archivarlo, antes «Poner a cero».</div>';
            }
        }
        return html + '</div>';
    },

    _pintar: function () {
        this.$('.o_kc_persona').html(this.persona
            ? 'Persona: <b>' + _e(this.persona.nombre) + '</b> <button type="button" class="o_kc_cambiar">Cambiar</button>'
            : '');
        var paso;
        if (!this.persona) {
            paso = '0. Pasa tu tarjeta de operario';
        } else if (this.conts.length) {
            paso = 'Ahora escanea la ubicación de destino (o más contenedores).';
        } else if (this.anadiendo) {
            paso = 'Añadir prendas: lee cada prenda y después «Guardar»';
        } else if (this.otro) {         // v1.14
            paso = this.otro.b ? 'Es otro: pon cuántas uds son y «Guardar»'
                : 'Es otro: lee una prenda de las que hay de verdad';
        } else if (this.detalle) {
            paso = 'Contenedor: «Cambiar» la cantidad de un artículo, «Es otro» si es otra talla, ponerlo a cero ' +
                'o añadir prendas';
        } else if (this.candidatos) {
            paso = 'Toca lo que buscas';
        } else if (this.hueco) {
            paso = 'Compactar: marca y archiva los vacíos; mueve los que tienen prendas';
        } else if (this.lineal) {
            paso = 'Inventario del lineal: toca un hueco para abrirlo';
        } else if (this.articulo) {
            paso = 'Dónde está este artículo: toca un hueco para abrirlo';
        } else {
            paso = '1. Escanea un contenedor (KO_…) para mover, una ubicación para limpiarla o una prenda para ver ' +
                'dónde está. Con «⌨ Escribir» busca cualquier cosa por un trozo: contenedor, ubicación, lineal o ' +
                'artículo';
        }
        this.$('.o_kc_paso').text(paso);
        var html = this.detalle ? '' : this.conts.map(function (c) {   // v1.7: con uno abierto, solo ese
            var filas = c.lineas.map(function (l) {
                return '<tr><td>' + _e(l.producto) + '</td><td class="o_kc_n">' + _n(l.uds) +
                    (l.reservadas ? ' (res. ' + _n(l.reservadas) + ')' : '') + '</td></tr>';
            }).join('');
            if (c.mas) { filas += '<tr><td colspan="2">… y ' + c.mas + ' referencias más</td></tr>'; }
            var cuerpo = c.n_lineas
                ? '<div>' + c.n_lineas + ' ref. · ' + _n(c.uds) + ' uds' +
                    (c.reservadas ? ' · ' + _n(c.reservadas) + ' reservadas (se conservan)' : '') +
                    '</div><table>' + filas + '</table>'
                : '<div class="o_kc_vacio">Sin prendas en el sistema</div>';
            return '<div class="o_kc_card"><button type="button" class="o_kc_quitar" data-id="' + c.id +
                '">Quitar</button><button type="button" class="o_kc_abrir" data-id="' + c.id + '">Abrir</button><h3>' + _e(c.nombre) + '</h3><div class="o_kc_hueco">Ahora en: ' +
                _e(c.hueco) + '</div>' + cuerpo + '</div>';
        }).join('');
        this.$('.o_kc_lista').html(html);
        this.$('.o_kc_hueco_panel').html(this._pintarCandidatos() + this._pintarArticulo() + this._pintarLineal() +
            this._pintarHueco() + this._pintarDetalle());
    },
});

core.action_registry.add('koroshi_contenedores_pantalla', Pantalla);
return Pantalla;
});
