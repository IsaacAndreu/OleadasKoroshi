odoo.define('koroshi_devoluciones.Pantalla', function (require) {
'use strict';
/* KOROSHI Devoluciones v1.0.0 (20/11/2026) - «Ubicar devoluciones» en la PDA, sin Excel.
 * 1. Tarjeta: la misma que Lecturas, Contenedores y Faltante (memoria de la PDA, clave koroshi_operarios_pda_<usuario>,
 *    {id, nombre, t}); dura koroshi_operarios.minutos_tarjeta sin actividad (60 por defecto).
 * 2. El operario toca qué ha hecho (Quitar precio / Quitar precio y embolsar / Reetiquetar y embolsar). La opción se
 *    queda puesta hasta que la cambie.
 * 3. Lee prenda, prenda… (cada lectura = 1 ud; «Quitar la última»; «Cantidad» = N uds a la última).
 * 4. Lee el contenedor KO_/TT_ o el hueco: se guarda la tanda y empieza otra con la misma opción.
 * Lo que se lee mientras se espera a Odoo va a una cola corta (como Contenedores 1.4). Una tanda lleva un id: si se
 * corta la wifi al guardar y se vuelve a leer el contenedor, no se guarda dos veces.
 * v1.1.0 (20/11/2026) «Llegadas» (fase 2, etapa 1): pestaña arriba «Ubicar» / «Llegadas». En Llegadas se toca el
 *   canal (Tiendas, Web, Zalando…; se queda puesto) y se lee lo que trae cada paquete: matrícula CJ (tienda, sale
 *   sola), código de Zalando o del transportista (GLS…). Cada lectura queda «ha llegado hoy»; si ya estaba, lo dice
 *   y no lo repite. Se ve cuántos han llegado hoy por canal y los últimos.
 * Todo dentro de .o_koroshi_devoluciones. Sin aria-hidden (Odoo 13 lo oculta). */
var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var session = require('web.session');
var REPETIDA_MS = 700;
var PERSONA_MS = 3600000;       // se cambia por koroshi_operarios.minutos_tarjeta al entrar
var EN_ESPERA_MAX = 5;

function _e(t) { return _.escape(t == null ? '' : String(t)); }
function _idTanda() {
    return 'D' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

var Pantalla = AbstractAction.extend({
    contentTemplate: 'koroshi_devoluciones.Pantalla',
    events: {
        'keydown .o_kd_codigo': '_onKeydown',
        'click .o_kd_opcion': '_onOpcion',
        'click .o_kd_cambiar_opcion': '_onCambiarOpcion',
        'click .o_kd_confirmar_si': '_onConfirmarSi',
        'click .o_kd_confirmar_no': '_onConfirmarNo',
        'click .o_kd_quitar_ultima': '_onQuitarUltima',
        'click .o_kd_borrar': '_onBorrar',
        'click .o_kd_cantidad_ok': '_onCantidad',
        'keydown .o_kd_cantidad': '_onCantidadKey',
        'click .o_kd_teclado': '_onTeclado',
        'click .o_kd_salir': '_onSalir',
        'click .o_kd_vista': '_onVista',              // v1.1
        'click .o_kd_canal': '_onCanal',              // v1.1
        'click .o_kd_cambiar_canal': '_onCambiarCanal',   // v1.1
    },

    init: function () {
        this._super.apply(this, arguments);
        this.persona = null;
        this.opciones = [];
        this.modo = 'mover';
        this.opcion = null;          // {id, nombre, color}
        this.prendas = [];           // [{id, nombre, uds}] por artículo, en orden de primera lectura
        this.lecturas = [];          // [{id, uds}] en orden de lectura (para «Quitar la última»)
        this.tanda = null;           // id de la tanda (se crea con la primera prenda)
        this.confirmando = null;     // acción pendiente de «¿Seguro?»: {texto, si: function}
        this.ultimoGuardado = '';
        this.ocupado = false;
        this.ultima = {codigo: '', t: 0};
        this.actividadEn = Date.now();
        this.enEspera = [];
        this.teclado = false;
        this.vista = 'ubicar';       // v1.1: 'ubicar' o 'llegadas'
        this.canales = [];           // v1.1: [{id, nombre}]
        this.canal = null;           // v1.1: {id, nombre} elegido en Llegadas
        this.hoy = null;             // v1.1: {total, por_canal, ultimos}
    },

    start: function () {
        var self = this;
        core.bus.on('barcode_scanned', this, this._onBarcodeScanned);
        return this._super.apply(this, arguments).then(function () {
            self.timer = setInterval(self._vigilar.bind(self), 10000);
            self._tomarGuardada();
            self._leerMinutosTarjeta();
            self._cargarOpciones();
            self._cargarLlegadas();   // v1.1
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
        this._super.apply(this, arguments);
    },

    // ------------------------------------------------------------ tarjeta compartida (como Contenedores 1.9.1)
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
    _tomarGuardada: function () {
        var g = this._guardada();
        if (!g || !g.id || (this.persona && this.persona.id === g.id)) { return false; }
        if (g.t && Date.now() - g.t > PERSONA_MS) { return false; }
        if (this.prendas.length) { return false; }     // a mitad de una tanda no se cambia de persona
        this.persona = {id: g.id, nombre: g.nombre};
        this.actividadEn = g.t || Date.now();
        return true;
    },
    _actividadCompartida: function () {
        if (!this.persona || (this.guardadaEn && this.actividadEn - this.guardadaEn < 30000)) { return; }
        var g = this._guardada();
        if (!g || g.id === this.persona.id) { this._guardarPersona(); }
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
        // con prendas leídas sin guardar no se cierra (se perderían)
        if (this.persona && Date.now() - this.actividadEn > PERSONA_MS && !this.prendas.length) {
            this.persona = null;
            this.opcion = null;
            this._pintar();
            this._aviso('info', 'Sesión cerrada por inactividad. Pasa tu tarjeta.');
        }
    },

    // ------------------------------------------------------------ opciones
    _cargarOpciones: function () {
        var self = this;
        return this._rpc({route: '/koroshi/devoluciones/inicio', params: {}}).then(function (r) {
            if (!r || !r.ok) { return self._aviso('mal', (r && r.msg) || 'No se han podido cargar las opciones.'); }
            self.opciones = r.opciones || [];
            self.modo = r.modo;
            self._pintar();
        }, self._sinConexion.bind(self));
    },

    _onOpcion: function (ev) {
        var id = parseInt($(ev.currentTarget).data('id'), 10);
        this.opcion = _.findWhere(this.opciones, {id: id}) || null;
        this.actividadEn = Date.now();
        this._aviso('', '');
        this._pintar();
        this._foco();
    },

    _onCambiarOpcion: function () {
        var self = this;
        if (!this.prendas.length) {
            this.opcion = null;
            this._pintar();
            return;
        }
        this._confirmar('Hay ' + this._total() + ' uds leídas sin guardar. Si cambias de opción, se borran. ¿Seguro?',
            function () { self._vaciar(); self.opcion = null; });
    },

    _confirmar: function (texto, si) {
        this.confirmando = {texto: texto, si: si};
        this._pintar();
    },
    _onConfirmarSi: function () {
        var c = this.confirmando;
        this.confirmando = null;
        this._aviso('', '');
        if (c) { c.si(); }
        this._pintar();
        this._foco();
    },
    _onConfirmarNo: function () {
        this.confirmando = null;
        this._pintar();
        this._foco();
    },

    _onSalir: function () {
        var self = this;
        var salir = function () {
            self._vaciar();
            self.persona = null;
            self.opcion = null;
            try { window.localStorage.removeItem(self._clave()); } catch (e) { /* nada */ }
            self._aviso('info', 'Has salido. Pasa tu tarjeta.');
        };
        if (this.prendas.length) {
            return this._confirmar('Hay ' + this._total() + ' uds leídas sin guardar. Si sales, se borran. ¿Seguro?',
                                   salir);
        }
        salir();
        this._pintar();
    },

    // ------------------------------------------------------------ lecturas
    _foco: function () {
        var $c = this.$('.o_kd_codigo');
        if ($c.length && document.activeElement !== $c[0]) { $c.focus(); }
    },
    _onKeydown: function (ev) {
        if (ev.which === 13) {
            ev.preventDefault();
            var codigo = (ev.currentTarget.value || '').trim();
            ev.currentTarget.value = '';
            if (this.teclado) { this._ponerTeclado(false); }
            this._leer(codigo, false, 'campo');
        }
    },
    _onBarcodeScanned: function (codigo) { this._leer(codigo, false, 'bus'); },

    _ponerTeclado: function (si) {
        this.teclado = si;
        var $c = this.$('.o_kd_codigo');
        $c.attr('inputmode', si ? null : 'none');
        this.$('.o_kd_teclado').text(si ? '⌨ Ocultar' : '⌨ Escribir');
        $c.blur();
        $c.focus();
    },
    _onTeclado: function () { this._ponerTeclado(!this.teclado); },

    _aviso: function (tipo, msg) {
        this.$('.o_kd_aviso').removeClass('o_kd_ok o_kd_mal o_kd_info').addClass(
            msg ? 'o_kd_' + (tipo || 'info') : '').text(msg || '');
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

    _fin: function () {
        var self = this;
        this.ocupado = false;
        this.actividadEn = Date.now();
        this._actividadCompartida();
        if (this.enEspera.length) {
            setTimeout(function () {
                if (!self.ocupado && self.enEspera.length) { self._leer(self.enEspera.shift(), true); }
            }, 0);
        }
    },
    _sinConexion: function () {
        this._fin();
        this._pitido(false);
        this._aviso('mal', 'Sin conexión con Odoo. Vuelve a leer lo último.');
    },

    _leer: function (codigo, deCola, fuente) {
        var self = this;
        codigo = (codigo || '').trim();
        if (!codigo) { return; }
        var t = Date.now();
        if (!deCola) {
            // una lectura llega dos veces (bus y campo): se descarta la copia de la OTRA vía. Dos lecturas de la
            // misma vía son dos prendas.
            if (codigo === this.ultima.codigo && t - this.ultima.t < REPETIDA_MS &&
                    (!fuente || !this.ultima.fuente || fuente !== this.ultima.fuente)) { return; }
            this.ultima = {codigo: codigo, t: t, fuente: fuente};
        }
        if (this.ocupado) {
            if (this.enEspera.length >= EN_ESPERA_MAX) {
                this._pitido(false);
                return this._aviso('mal', 'Espera a que acabe: ' + codigo + ' NO se ha leído. Vuelve a leerlo.');
            }
            this.enEspera.push(codigo);
            return;
        }
        if (this.confirmando) {
            this._pitido(false);
            return this._aviso('mal', 'Contesta antes la pregunta: ' + codigo + ' NO se ha leído.');
        }
        if (this.vista === 'llegadas') { return this._leerLlegada(codigo); }   // v1.1
        this.ocupado = true;
        return this._rpc({route: '/koroshi/devoluciones/leer', params: {codigo: codigo}}).then(function (r) {
            self._fin();
            if (!r || !r.ok) {
                self._pitido(false);
                return self._aviso('mal', (r && r.msg) || 'No se ha podido leer.');
            }
            if (r.tipo === 'persona') { return self._leidaPersona(r.persona); }
            if (!self.persona) {
                self._pitido(false);
                return self._aviso('mal', 'Primero pasa tu tarjeta de operario.');
            }
            if (!self.opcion) {
                self._pitido(false);
                return self._aviso('mal', 'Primero toca qué has hecho (una de las opciones). No se ha contado.');
            }
            if (r.tipo === 'prenda') { return self._leidaPrenda(r.prenda); }
            if (r.tipo === 'destino') { return self._guardar(r.destino); }
        }, self._sinConexion.bind(self));
    },

    _leidaPersona: function (p) {
        if (this.prendas.length && (!this.persona || this.persona.id !== p.id)) {
            this._pitido(false);
            return this._aviso('mal', 'Hay prendas sin guardar de ' + (this.persona ? this.persona.nombre : '') +
                               ': lee antes el contenedor o bórralas.');
        }
        this.persona = p;
        this._guardarPersona();
        this._pitido(true);
        this._aviso('ok', 'Hola, ' + p.nombre + '.');
        this._pintar();
    },

    _leidaPrenda: function (p) {
        this.tanda = _idTanda();   // contenido nuevo = tanda nueva (solo un reintento idéntico reusa el id)
        var fila = _.findWhere(this.prendas, {id: p.id});
        if (fila) { fila.uds += 1; } else { this.prendas.push({id: p.id, nombre: p.nombre, uds: 1}); }
        this.lecturas.push({id: p.id, uds: 1});
        this._pitido(true);
        this._aviso('ok', '+1 ' + p.nombre);
        this._pintar();
    },

    _guardar: function (destino) {
        var self = this;
        if (!this.prendas.length) {
            this._pitido(false);
            return this._aviso('mal', destino.nombre + ': lee antes las prendas y después el contenedor.');
        }
        this.ocupado = true;
        this._aviso('info', 'Guardando en ' + destino.nombre + '…');
        return this._rpc({route: '/koroshi/devoluciones/guardar', params: {
            tanda: this.tanda, employee_id: this.persona.id, manipulacion_id: this.opcion.id,
            destino_id: destino.id,
            lineas: _.map(this.prendas, function (f) { return {producto_id: f.id, uds: f.uds}; }),
        }}).then(function (r) {
            self._fin();
            if (!r || !r.ok) {
                self._pitido(false);
                return self._aviso('mal', ((r && r.msg) || 'No se ha podido guardar.') + ' Las prendas siguen leídas.');
            }
            self._vaciar();
            self.ultimoGuardado = r.msg;
            self._pitido(true);
            self._pintar();
            self._aviso('ok', r.msg);
        }, function () {
            // sin respuesta: puede haberse guardado o no. Se deja todo igual (mismo id de tanda): al volver a leer el
            // contenedor, si ya estaba guardada no se repite.
            self._sinConexion();
            self._aviso('mal', 'Sin conexión al guardar. Vuelve a leer el contenedor (no se guarda dos veces).');
        });
    },

    // ------------------------------------------------------------ v1.1: Llegadas
    _cargarLlegadas: function () {
        var self = this;
        return this._rpc({route: '/koroshi/devoluciones/llegadas_hoy', params: {}}, {shadow: true}).then(function (r) {
            if (!r || !r.ok) { return; }
            self.canales = r.canales || [];
            self.hoy = r;
            self._pintar();
        }, function () { /* sin conexión: se verá al leer */ });
    },

    _onVista: function (ev) {
        var self = this;
        var vista = $(ev.currentTarget).data('vista');
        if (vista === this.vista) { return; }
        var cambiar = function () {
            self._vaciar();
            self.vista = vista;
            self._aviso('', '');
            if (vista === 'llegadas') { self._cargarLlegadas(); }
        };
        if (this.prendas.length) {
            return this._confirmar('Hay ' + this._total() + ' uds leídas sin guardar. Si cambias a ' +
                (vista === 'llegadas' ? 'Llegadas' : 'Ubicar') + ', se borran. ¿Seguro?', cambiar);
        }
        cambiar();
        this._pintar();
        this._foco();
    },

    _onCanal: function (ev) {
        this.canal = _.findWhere(this.canales, {id: $(ev.currentTarget).data('id')}) || null;
        this.actividadEn = Date.now();
        this._aviso('', '');
        this._pintar();
        this._foco();
    },
    _onCambiarCanal: function () {
        this.canal = null;
        this._pintar();
        this._foco();
    },

    _leerLlegada: function (codigo) {
        var self = this;
        this.ocupado = true;
        return this._rpc({route: '/koroshi/devoluciones/llegada', params: {
            codigo: codigo, canal: this.canal ? this.canal.id : '', employee_id: this.persona ? this.persona.id : false,
        }}).then(function (r) {
            self._fin();
            if (!r || !r.ok) {
                self._pitido(false);
                return self._aviso('mal', (r && r.msg) || 'No se ha podido leer.');
            }
            if (r.tipo === 'persona') { return self._leidaPersona(r.persona); }
            self.hoy = r;
            self._pitido(r.nuevo);
            self._pintar();
            self._aviso(r.nuevo ? 'ok' : 'info', r.msg);
        }, self._sinConexion.bind(self));
    },

    _pintarLlegadas: function () {
        var html = '';
        if (!this.canal) {
            this.$('.o_kd_paso').text('¿De dónde viene? Toca el canal.');
            html += '<div class="o_kd_opciones">';
            _.each(this.canales, function (c) {
                html += '<button type="button" class="o_kd_opcion o_kd_canal" data-id="' + _e(c.id) + '">' +
                    _e(c.nombre) + '</button>';
            });
            if (!this.canales.length) { html += '<div>Cargando canales… (si no salen, Ctrl+F5)</div>'; }
            html += '</div>';
        } else {
            this.$('.o_kd_paso').text('Lee la matrícula, el código de Zalando o el del transportista de cada paquete.');
            html += '<div class="o_kd_elegida o_kd_elegida_canal">' + _e(this.canal.nombre) +
                '<button type="button" class="o_kd_cambiar_canal">Cambiar</button></div>';
        }
        var h = this.hoy;
        if (h && h.total) {
            html += '<div class="o_kd_card"><div class="o_kd_total">Hoy han llegado ' + h.total + '</div><div>' +
                _.map(h.por_canal, function (c) { return _e(c.nombre) + ': <b>' + c.n + '</b>'; }).join(' · ') +
                '</div><table>';
            _.each(h.ultimos, function (p) {
                html += '<tr><td>' + _e(p.codigo) + (p.tienda ? ' <small>(' + _e(p.tienda) + ')</small>' : '') +
                    '</td><td>' + _e(p.canal) + '</td><td class="o_kd_n">' + _e(p.hora.slice(-5)) + '</td></tr>';
            });
            html += '</table></div>';
        }
        return html;
    },

    _vaciar: function () {
        this.prendas = [];
        this.lecturas = [];
        this.tanda = null;
    },
    _total: function () {
        return _.reduce(this.prendas, function (s, f) { return s + f.uds; }, 0);
    },
    // cambiar las lecturas tras un fallo al guardar = tanda nueva (el contenido ya no es el mismo)
    _cambiaContenido: function () {
        if (this.prendas.length) { this.tanda = _idTanda(); }
    },

    _onQuitarUltima: function () {
        if (!this.lecturas.length) { return; }
        var lec = this.lecturas.pop();
        var fila = _.findWhere(this.prendas, {id: lec.id});
        if (fila) {
            fila.uds -= lec.uds;
            if (fila.uds <= 0) { this.prendas = _.without(this.prendas, fila); }
            this._aviso('info', '−' + lec.uds + ' ' + fila.nombre);
        }
        if (!this.prendas.length) { this.tanda = null; } else { this._cambiaContenido(); }
        this._pintar();
        this._foco();
    },
    _onBorrar: function () {
        var self = this;
        if (!this.prendas.length) { return; }
        this._confirmar('¿Borrar las ' + this._total() + ' uds leídas sin guardar?', function () {
            self._vaciar();
            self._aviso('info', 'Lecturas borradas.');
        });
    },
    _onCantidadKey: function (ev) {
        if (ev.which === 13) { ev.preventDefault(); this._onCantidad(); }
    },
    _onCantidad: function () {
        var $q = this.$('.o_kd_cantidad');
        var n = parseInt($q.val(), 10);
        if (!this.lecturas.length) {
            return this._aviso('mal', 'Lee antes una prenda; la cantidad es para la última leída.');
        }
        if (!(n >= 1 && n <= 500)) { return this._aviso('mal', 'Escribe una cantidad entre 1 y 500.'); }
        var lec = _.last(this.lecturas);
        var fila = _.findWhere(this.prendas, {id: lec.id});
        fila.uds += n - lec.uds;
        lec.uds = n;
        this._cambiaContenido();
        this._aviso('ok', 'La última lectura pasa a ' + n + ' uds: ' + fila.uds + ' uds de ' + fila.nombre);
        this._pintar();
        this._foco();
    },

    // ------------------------------------------------------------ pintar
    _pintar: function () {
        var html = '';
        this.$('.o_kd_persona').html(this.persona ?
            'Operario: <b>' + _e(this.persona.nombre) + '</b> <button type="button" class="o_kd_salir">Salir</button>' :
            '<b>Pasa tu tarjeta de operario.</b>');
        if (this.confirmando) {
            html += '<div class="o_kd_confirmar"><div>' + _e(this.confirmando.texto) + '</div>' +
                '<button type="button" class="o_kd_confirmar_si">Sí</button>' +
                '<button type="button" class="o_kd_confirmar_no">No</button></div>';
        }
        if (this.persona) {   // v1.1: pestañas
            html += '<div class="o_kd_vistas">' +
                '<button type="button" class="o_kd_vista' + (this.vista === 'ubicar' ? ' o_kd_vista_on' : '') +
                '" data-vista="ubicar">Ubicar</button>' +
                '<button type="button" class="o_kd_vista' + (this.vista === 'llegadas' ? ' o_kd_vista_on' : '') +
                '" data-vista="llegadas">Llegadas</button></div>';
        }
        if (!this.persona) {
            this.$('.o_kd_paso').text('');
        } else if (this.vista === 'llegadas') {
            html += this._pintarLlegadas();
        } else if (!this.opcion) {
            this.$('.o_kd_paso').text('¿Qué has hecho? Toca una opción.');
            html += '<div class="o_kd_opciones">';
            _.each(this.opciones, function (o) {
                html += '<button type="button" class="o_kd_opcion" data-id="' + o.id + '" style="background:' +
                    _e(o.color) + '">' + _e(o.nombre) + '</button>';
            });
            if (!this.opciones.length) { html += '<div>No hay opciones de manipulación. Avisa al responsable.</div>'; }
            html += '</div>';
            if (this.ultimoGuardado) { html += '<div class="o_kd_ultimo">Último: ' + _e(this.ultimoGuardado) + '</div>'; }
        } else {
            this.$('.o_kd_paso').text(this.prendas.length ?
                'Sigue leyendo prendas, o lee el contenedor o la ubicación para guardar.' :
                'Lee las prendas y después el contenedor o la ubicación.');
            html += '<div class="o_kd_elegida" style="background:' + _e(this.opcion.color) + '">' +
                _e(this.opcion.nombre) +
                '<button type="button" class="o_kd_cambiar_opcion">Cambiar</button></div>';
            if (this.prendas.length) {
                html += '<div class="o_kd_card"><div class="o_kd_total">' + this._total() + ' uds leídas</div><table>';
                _.each(this.prendas.slice().reverse(), function (f) {
                    html += '<tr><td>' + _e(f.nombre) + '</td><td class="o_kd_n">' + f.uds + '</td></tr>';
                });
                html += '</table><div class="o_kd_acciones">' +
                    '<button type="button" class="o_kd_quitar_ultima">Quitar la última</button>' +
                    '<input type="number" min="1" max="500" class="o_kd_cantidad" placeholder="Uds"/>' +
                    '<button type="button" class="o_kd_cantidad_ok">Cantidad</button>' +
                    '<button type="button" class="o_kd_borrar">Borrar todo</button></div></div>';
            }
            if (this.modo === 'apuntar') {
                html += '<div class="o_kd_modo">Solo se apunta: el stock no se mueve.</div>';
            }
        }
        this.$('.o_kd_cuerpo').html(html);
    },
});

core.action_registry.add('koroshi_devoluciones_pantalla', Pantalla);
return Pantalla;
});
