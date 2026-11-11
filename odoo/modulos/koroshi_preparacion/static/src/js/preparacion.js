odoo.define('koroshi_preparacion.Pantalla', function (require) {
'use strict';
/* KOROSHI Preparación en Lecturas v3.2.0 - pantalla para preparar una OUT suelta sin salir de Lecturas.
 * v3.2: «Faltante» trabaja con la línea que se ve: dice dónde probar (la ubicación con stock más cercana) y se lee
 * la ubicación de donde se coge, o «Tampoco está aquí». Sin lista ni pantalla aparte (rutas de koroshi_faltantes).
 * v3.0.1: foto del producto (la misma imagen que enseña la app de código de barras) y flechas ◀ ▶ para ver la línea
 * de antes o la siguiente; tocar una línea de la lista la pone en grande. Al completar una línea salta sola a la
 * siguiente pendiente.
 *
 * La abre Lecturas (koroshi_operarios) en lugar de la app de código de barras cuando el operario está activado
 * (parámetro koroshi_preparacion.empleados) y la OUT no es de una agrupación de zona Z-.
 *   leer EAN -> +1 ud en su línea | «Caja» -> «Escanea la caja» -> CJ -> put_in_pack | «Validar» -> button_validate
 * Al validar vuelve a Lecturas, que enseña «¡Hecho!» y abre la siguiente. «←» vuelve a Lecturas sin validar
 * (Continuar / Faltante / Saltar, como al volver de la app).
 * Las lecturas van en cola: si se leen varias seguidas no se pierde ninguna, y cada una lleva un id para que un
 * reintento no cuente dos veces.
 */
var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var session = require('web.session');

var REPETIDA_MS = 400;          // la misma lectura por el bus y por el campo: cuenta una
var REINTENTO_MS = 5000;        // sin conexión: reintento
var A_DOS_MS = 10000;          // v3.3: preparar a dos -> se refresca lo del compañero cada 10 s
var AVISO_OK_MS = 3000;
var VOLVER_MS = 900;            // tras validar, vuelta a Lecturas
var CLAVE_SONIDO = 'koroshi_operarios_sonido';   // el mismo interruptor que Lecturas
var CLAVE_PDA = 'koroshi_preparacion_pda';
var RE_CJ = /^CJ\d{9}$/i;
var CONFIRMAR_MS = 4000;       // v3.2: «Tampoco está aquí» se pulsa dos veces
var MAX_ALTERNATIVAS = 3;
var ICONOS = {ok: '✓', info: 'ℹ', warn: '⚠', mal: '✖'};

var Pantalla = AbstractAction.extend({
    contentTemplate: 'koroshi_preparacion.Pantalla',
    events: {
        'keydown .o_kp_codigo': '_onKeydown',
        'focus .o_kp_codigo': '_estadoLector',
        'blur .o_kp_codigo': '_onBlur',
        'click .o_kp_lector': '_onTocar',
        'click .o_kp_volver': '_onVolver',
        'click .o_kp_caja': '_onCaja',
        'click .o_kp_cancelar_caja': '_salirDeCaja',
        'click .o_kp_hoja_fondo': '_onFondoHoja',
        'click .o_kp_validar': '_onValidar',
        'click .o_kp_pendiente_si': '_onPendienteSi',
        'click .o_kp_pendiente_no': '_onPendienteNo',
        'click .o_kp_pendiente_cancelar': '_cerrarHoja',
        'click .o_kp_faltante': '_onFaltante',
        // v3.2: Faltante de la línea que se ve
        'click .o_kp_f_nada': '_onFaltaNada',
        'click .o_kp_f_cancelar': '_onCancelarFaltante',
        'click .o_kp_f_lista': '_onFaltanteLista',
        'keydown .o_kp_f_codigo': '_onKeydownFaltante',
        'click .o_kp_deshacer': '_onDeshacer',
        'click .o_kp_ver_lineas': '_onVerLineas',
        // v3.0.1: flechas, tocar una línea de la lista y volver a la que toca
        'click .o_kp_anterior': '_onAnterior',
        'click .o_kp_posterior': '_onPosterior',
        'click .o_kp_ir_pendiente': '_onIrPendiente',
        'click .o_kp_lineas li': '_onTocarLinea',
    },

    init: function (parent, action) {
        this._super.apply(this, arguments);
        var ctx = (action && action.context) || {};
        this.pickingName = ctx.preparacion_out || false;
        this.operario = ctx.preparacion_operario || null;   // {id, nombre}
        this.estado = null;
        this.verId = null;             // v3.0.1: línea que se ve en grande (null = la que toca)
        this.modo = 'leer';            // 'leer' | 'caja' (esperando la etiqueta) | 'faltante' | 'pregunta' | 'validando'
        this.faltante = null;          // v3.2: {linea, listo, ocupado}
        this.cola = [];                // lecturas pendientes de mandar
        this.enviando = false;
        this.sinRed = false;
        this.ultima = {codigo: '', t: 0};
        this.contador = 0;
        this.sonido = this._leerSonido();
        this.pda = this._idPda();
        this._enLinea = this._onEnLinea.bind(this);
        this._fueraDeLinea = this._sinConexion.bind(this);
    },

    willStart: function () {
        var self = this;
        var carga = this._rpc({route: '/koroshi/preparacion/cargar', params: {picking_name: this.pickingName,
            employee_id: this.operario ? this.operario.id : false}})
            .then(function (r) {
                if (r && r.ok) { self.estado = r.estado; } else { self.errorCarga = (r && r.msg) || 'Error'; }
            }).guardedCatch(function (e) {
                if (e && e.event && e.event.preventDefault) { e.event.preventDefault(); }
                self.errorCarga = 'No se ha podido cargar ' + (self.pickingName || 'la OUT') + '.';
            });
        return Promise.all([this._super.apply(this, arguments), carga]);
    },

    start: function () {
        var self = this;
        core.bus.on('barcode_scanned', this, this._onBarcodeScanned);
        window.addEventListener('online', this._enLinea);
        window.addEventListener('offline', this._fueraDeLinea);
        return this._super.apply(this, arguments).then(function () {
            // v3.0.1: producto sin foto -> no se ve el hueco
            self.$('.o_kp_foto').on('error', function () { $(this).hide(); }).on('load', function () { $(this).show(); });
            self.$('.o_kp_f_foto').on('error', function () { $(this).hide(); });   // v3.2
            self._pintar();
            if (self.errorCarga) { self._aviso(self.errorCarga, 'mal'); }
            // v3.3: preparar a dos -> se ve lo que lee el compañero (y si valida, se vuelve a Lecturas)
            self.timerDos = setInterval(function () {
                if (self.estado && self.estado.a_dos && self.modo === 'leer' && !self.enviando && !self.cola.length &&
                        !self.sinRed) {
                    self._recargar();
                }
            }, A_DOS_MS);
            self._foco();
        });
    },

    on_attach_callback: function () {
        // vuelve de la pantalla de Faltante: se recarga la OUT (si ya está validada, vuelta a Lecturas)
        this._super.apply(this, arguments);
        if (this.yaMostrada) { this._recargar(); }
        this.yaMostrada = true;
        this._foco();
    },

    destroy: function () {
        core.bus.off('barcode_scanned', this, this._onBarcodeScanned);
        window.removeEventListener('online', this._enLinea);
        window.removeEventListener('offline', this._fueraDeLinea);
        clearTimeout(this.timerAviso);
        clearTimeout(this.timerReintento);
        clearTimeout(this.timerVolver);
        clearTimeout(this.timerConfirmar);
        clearInterval(this.timerDos);
        if (this.audio) { try { this.audio.close(); } catch (e) { /* nada */ } }
        this._super.apply(this, arguments);
    },

    // ------------------------------------------------------------ utilidades
    _idPda: function () {
        try {
            var v = window.localStorage.getItem(CLAVE_PDA);
            if (!v) {
                v = 'PDA' + Math.floor(Math.random() * 1e9).toString(36);
                window.localStorage.setItem(CLAVE_PDA, v);
            }
            return v;
        } catch (e) { return 'PDA'; }
    },

    _nuevoId: function () {
        this.contador += 1;
        return this.pda + '-' + Date.now().toString(36) + '-' + this.contador;
    },

    _visible: function () {
        return !!this.el && $.contains(document, this.el);
    },

    _out: function () {
        return this.estado && this.estado.out;
    },

    // ------------------------------------------------------------ lecturas
    _onBarcodeScanned: function (barcode) {
        if (!this._visible()) { return; }
        this._leer(barcode);
    },

    _onKeydown: function (ev) {
        if (ev.key === 'Enter' || ev.keyCode === 13) {
            ev.preventDefault();
            var $i = this.$('.o_kp_codigo');
            var c = ($i.val() || '').trim();
            $i.val('');
            if (c) { this._leer(c); }
        }
    },

    _leer: function (codigo) {
        codigo = (codigo || '').trim();
        var ahora = Date.now();
        if (!codigo || (codigo === this.ultima.codigo && ahora - this.ultima.t < REPETIDA_MS)) { return; }
        this.ultima = {codigo: codigo, t: ahora};
        if (!this._out()) { return this._aviso(this.errorCarga || 'No hay OUT cargada.', 'mal'); }
        if (this.sinRed) {
            this._aviso('Sin conexión: no se ha leído ' + codigo + '. Espera a que vuelva.', 'mal');
            return this._pitido(false);
        }
        if (this.modo === 'pregunta' || this.modo === 'validando') { return; }
        if (this.modo === 'faltante') { return this._reubicar(codigo); }   // v3.2: la ubicación de donde se coge
        var tipo = this.modo === 'caja' ? 'caja' : 'leer';
        this.cola.push({tipo: tipo, codigo: codigo, id: this._nuevoId()});
        this._enviar();
    },

    _enviar: function () {
        var self = this;
        if (this.enviando || this.sinRed || !this.cola.length) { return; }
        var item = this.cola[0];
        this.enviando = true;
        var ruta = item.tipo === 'caja' ? '/koroshi/preparacion/caja' : '/koroshi/preparacion/leer';
        return this._rpc({route: ruta, params: {
            picking_id: this._out().id, codigo: item.codigo, id_lectura: item.id,
            employee_id: this.operario ? this.operario.id : false,
        }}, {shadow: true}).then(function (r) {
            self.cola.shift();
            self.enviando = false;
            if (r && r.estado) { self.estado = r.estado; }
            if (item.tipo === 'caja') { self._trasCaja(r); } else { self._trasLeer(r); }
            self._pintar();
            self._enviar();
        }).guardedCatch(function (e) {
            self.enviando = false;
            if (e && e.event && e.event.preventDefault) { e.event.preventDefault(); }
            if (self._esSinConexion(e)) { return self._sinConexion(); }   // la lectura se queda y se reintenta
            self.cola.shift();
            self._aviso(self._mensajeError(e), 'mal');
            self._pitido(false);
            self._enviar();
        });
    },

    _trasLeer: function (r) {
        if (r && r.ok) {
            // v3.0.1: si la línea leída aún no está completa se queda a la vista; si ya lo está, salta sola a la siguiente
            var l = this.estado && _.findWhere(this.estado.lineas, {id: r.linea_id});
            this.verId = l && !l.completa ? l.id : null;
            this._aviso(r.msg, 'ok');
            this._pitido(true);
            if (this.estado && this.estado.todo_leido) {
                this._aviso('Todo leído. ' + (this.estado.sin_caja ? 'Cierra la caja y valida.' : 'Pulsa Validar.'), 'ok');
            }
            return;
        }
        this._aviso((r && r.msg) || 'Error', 'mal');
        this._pitido(false);
    },

    // ------------------------------------------------------------ caja
    _onCaja: function () {
        if (!this._out() || this.sinRed) { return; }
        if (!this.estado.sin_caja) {
            this._aviso('No hay nada leído fuera de caja.', 'info');
            return this._foco();
        }
        this.modo = 'caja';
        this.$('.o_kp_hoja_texto').text(this.estado.sin_caja + (this.estado.sin_caja === 1 ? ' ud va' : ' uds van') +
                                        ' a esta caja. Lee la etiqueta CJ de la caja.');
        this.$('.o_kp_hoja_aviso').attr('class', 'o_kp_hoja_aviso').text('');
        this.$('.o_kp_hoja_pregunta, .o_kp_hoja_faltante').hide();
        this.$('.o_kp_hoja_caja').show();
        this.$('.o_kp_hoja').show();
        this._foco();
    },

    _trasCaja: function (r) {
        if (r && r.ok) {
            this._cerrarHoja();
            this._aviso(r.msg, 'ok');
            this._pitido(true);
            return;
        }
        // sigue esperando la etiqueta
        var msg = (r && r.msg) || 'Error';
        this.$('.o_kp_hoja_aviso').attr('class', 'o_kp_hoja_aviso o_kp_mal').text('✖ ' + msg);
        this._pitido(false);
        if (this.estado && !this.estado.sin_caja) { this._cerrarHoja(); this._aviso(msg, 'mal'); }
    },

    _salirDeCaja: function () {
        this._cerrarHoja();
        this._aviso('Caja sin cerrar. Puedes seguir leyendo.', 'info');
    },

    _onFondoHoja: function () {
        if (this.modo === 'caja') { this._salirDeCaja(); } else if (this.modo === 'pregunta') { this._cerrarHoja(); }
        else if (this.modo === 'faltante') { this._cerrarFaltante(); }
    },

    _cerrarHoja: function () {
        this.modo = 'leer';
        this.$('.o_kp_hoja').hide();
        this._pintar();
        this._foco();
    },

    // ------------------------------------------------------------ validar
    _onValidar: function () {
        if (!this._out() || this.sinRed || this.modo !== 'leer' || this.cola.length || this.enviando) { return; }
        return this._validar(false);
    },

    _onPendienteSi: function () { return this._validar('si'); },
    _onPendienteNo: function () { return this._validar('no'); },

    _validar: function (pedidoPendiente) {
        var self = this;
        var out = this._out();
        this.$('.o_kp_hoja').hide();
        this.modo = 'validando';
        this._capa('Validando ' + out.name + '…', false);
        return this._rpc({route: '/koroshi/preparacion/validar', params: {
            picking_id: out.id, employee_id: this.operario ? this.operario.id : false,
            pedido_pendiente: pedidoPendiente || false,
        }}).then(function (r) {
            if (r && r.estado) { self.estado = r.estado; }
            if (r && r.ok && r.que === 'validada') {
                self._capa('✓ ' + out.name + ' validada', true);
                self._pitido(true);
                self.timerVolver = setTimeout(function () { self.trigger_up('history_back'); }, VOLVER_MS);
                return;
            }
            self._ocultarCapa();
            if (r && r.que === 'preguntar') {
                self.modo = 'pregunta';
                self.$('.o_kp_hoja_caja, .o_kp_hoja_faltante').hide();
                self.$('.o_kp_hoja_pregunta').show();
                self.$('.o_kp_hoja').show();
                return;
            }
            self.modo = 'leer';
            self._pintar();
            self._aviso((r && r.msg) || 'No se ha podido validar.', r && r.que === 'quedan' ? 'warn' : 'mal');
            self._pitido(false);
        }).guardedCatch(function (e) {
            self._ocultarCapa();
            self.modo = 'leer';
            if (e && e.event && e.event.preventDefault) { e.event.preventDefault(); }
            if (self._esSinConexion(e)) { return self._sinConexion(); }
            self._aviso(self._mensajeError(e), 'mal');
            self._pitido(false);
        });
    },

    // ------------------------------------------------------------ deshacer / faltante / volver
    _onDeshacer: function () {
        var self = this;
        if (!this._out() || this.sinRed || this.modo !== 'leer' || this.cola.length || this.enviando) { return; }
        this.enviando = true;
        return this._rpc({route: '/koroshi/preparacion/deshacer', params: {
            picking_id: this._out().id, employee_id: this.operario ? this.operario.id : false,
        }}).then(function (r) {
            self.enviando = false;
            if (r && r.estado) { self.estado = r.estado; }
            if (r && r.ok && r.linea_id) { self.verId = r.linea_id; }   // v3.0.1: se ve la línea deshecha
            self._pintar();
            self._aviso((r && r.msg) || 'Error', r && r.ok ? 'info' : 'mal');
            self._pitido(!!(r && r.ok));
            self._foco();
        }).guardedCatch(function (e) {
            self.enviando = false;
            if (e && e.event && e.event.preventDefault) { e.event.preventDefault(); }
            if (self._esSinConexion(e)) { return self._sinConexion(); }
            self._aviso(self._mensajeError(e), 'mal');
        });
    },

    _onFaltanteLista: function () {
        // la pantalla de Faltante de siempre (para marcar varias a la vez)
        var out = this._out();
        if (!out || this.sinRed || (this.modo !== 'leer' && this.modo !== 'faltante')) { return; }
        if (this.modo === 'faltante') {
            if (this.faltante && this.faltante.ocupado) { return; }
            this._cerrarFaltante(true);
        }
        return this.do_action('koroshi_faltantes.action_koroshi_faltantes_pantalla', {
            additional_context: {
                desde_operarios: true,       // al validar o salir, koroshi_faltantes vuelve atrás (a esta pantalla)
                desde_preparacion: true,     // «Volver a la OUT» también vuelve aquí (ver include de abajo)
                faltante_out: out.name,
                faltante_operario: this.operario ? {id: this.operario.id, nombre: this.operario.nombre} : false,
            },
        });
    },

    _onVolver: function () {
        if (this.modo === 'validando') { return; }
        if (this.modo === 'faltante') { return this._cerrarFaltante(); }
        this.trigger_up('history_back');
    },

    _recargar: function (despues) {
        var self = this;
        if (!this._out()) { return; }
        return this._rpc({route: '/koroshi/preparacion/cargar', params: {picking_id: this._out().id,
            employee_id: this.operario ? this.operario.id : false}}, {shadow: true})
            .then(function (r) {
                if (!r || !r.ok) { return; }
                self.estado = r.estado;
                if (self.estado.out.estado === 'done' || self.estado.out.estado === 'cancel') {
                    // validada desde Faltante: vuelta a Lecturas («¡Hecho!» y la siguiente)
                    self._capa('✓ ' + self.estado.out.name + (self.estado.out.estado === 'done' ? ' validada' : ' cancelada'), true);
                    self.timerVolver = setTimeout(function () { self.trigger_up('history_back'); }, VOLVER_MS);
                    return;
                }
                if (despues) { despues(); }
                self._pintar();
            }).guardedCatch(function (e) {
                if (e && e.event && e.event.preventDefault) { e.event.preventDefault(); }
                if (self._esSinConexion(e)) { self._sinConexion(); }
            });
    },

    // ------------------------------------------------------------ v3.2: Faltante de la línea que se ve
    _onFaltante: function () {
        var self = this;
        var e = this.estado;
        if (!this._out() || this.sinRed || this.modo !== 'leer' || this.cola.length || this.enviando) { return; }
        var id = this._idVisto();
        var l = id && _.findWhere(e.lineas, {id: id});
        if (!l) { this._aviso('No queda ninguna línea por coger.', 'info'); return this._foco(); }
        if (l.completa || l.caja) {
            this._aviso('Esta línea ya está cogida. Con ◀ ▶ busca la que no encuentras.', 'info');
            return this._foco();
        }
        this.modo = 'faltante';
        this.faltante = {linea: l, listo: false, ocupado: false};
        this._sinConfirmar();
        var falta = Math.max(l.pedidas - l.leidas, 0);
        var $f = this.$('.o_kp_f_foto');
        if (l.producto_id && l.tiene_foto !== false) {
            $f.attr('src', '/web/image/product.product/' + l.producto_id + '/image_128').show();
        } else { $f.removeAttr('src').hide(); }
        this.$('.o_kp_f_producto').text((l.nombre || l.producto) + (l.talla ? ' · Talla ' + l.talla : ''));
        this.$('.o_kp_f_no_esta').text('No está en ' + l.ubicacion + ' · ' + falta + (falta === 1 ? ' ud' : ' uds'));
        this.$('.o_kp_f_cargando').show();
        this.$('.o_kp_f_prueba, .o_kp_f_sin_alt, .o_kp_f_nada').hide();
        this.$('.o_kp_f_alternativas').empty();
        this.$('.o_kp_f_codigo').val('');
        this._avisoFaltante('', '');
        this.$('.o_kp_hoja_caja, .o_kp_hoja_pregunta').hide();
        this.$('.o_kp_hoja_faltante').show();
        this.$('.o_kp_hoja').show();
        this._pintar();
        return this._rpc({route: '/koroshi/faltantes/buscar', params: {move_line_id: l.id}}).then(function (r) {
            if (self.modo !== 'faltante') { return; }
            self.$('.o_kp_f_cargando').hide();
            if (!r || !r.ok || !r.linea) { return self._avisoFaltante((r && r.msg) || 'No se ha podido buscar.', 'mal'); }
            var lin = r.linea;
            if (lin.motivo) { return self._avisoFaltante(lin.motivo, 'mal'); }
            self.faltante.listo = true;
            self.$('.o_kp_f_no_esta').text('No está en ' + lin.ubicacion + ' · ' + lin.pendiente +
                                           (lin.pendiente === 1 ? ' ud' : ' uds'));
            var alt = (lin.alternativas || []).slice(0, MAX_ALTERNATIVAS);
            var $ol = self.$('.o_kp_f_alternativas').empty();
            alt.forEach(function (a, i) {
                var $li = $('<li/>');
                $('<span class="o_kp_f_alt_ubi"/>').text(a.nombre).appendTo($li);
                $('<span class="o_kp_f_alt_libre"/>').text((i === 0 ? 'La más cercana · ' : '') + a.libre +
                    (a.libre === 1 ? ' ud' : ' uds')).appendTo($li);
                $ol.append($li);
            });
            self.$('.o_kp_f_prueba').toggle(!!alt.length);
            self.$('.o_kp_f_sin_alt').toggle(!alt.length);
            self.$('.o_kp_f_nada').show();
            self._sinConfirmar();
            self._foco();
        }).guardedCatch(function (err) {
            if (err && err.event && err.event.preventDefault) { err.event.preventDefault(); }
            if (self.modo !== 'faltante') { return; }
            self.$('.o_kp_f_cargando').hide();
            if (self._esSinConexion(err)) { self._cerrarFaltante(); return self._sinConexion(); }
            self._avisoFaltante(self._mensajeError(err), 'mal');
        });
    },

    _onKeydownFaltante: function (ev) {
        if (ev.key === 'Enter' || ev.keyCode === 13) {
            ev.preventDefault();
            ev.stopPropagation();
            var $i = this.$('.o_kp_f_codigo');
            var c = ($i.val() || '').trim();
            $i.val('');
            if (c) { this._leer(c); }
        }
    },

    _reubicar: function (codigo) {
        var self = this;
        var f = this.faltante;
        if (!f || !f.listo || f.ocupado) { return; }
        if (RE_CJ.test(codigo)) {
            this._avisoFaltante('Eso es una caja. Lee la ubicación de donde coges la pieza.', 'mal');
            return this._pitido(false);
        }
        f.ocupado = true;
        this._sinConfirmar();
        this._avisoFaltante('Cambiando a ' + codigo + '…', 'info');
        return this._rpc({route: '/koroshi/faltantes/reubicar', params: {
            move_line_id: f.linea.id, codigo: codigo, employee_id: this.operario ? this.operario.id : false,
        }}).then(function (r) {
            f.ocupado = false;
            if (r && r.ok && r.que === 'tarjeta') {
                self._avisoFaltante('Es una tarjeta. Lee la ubicación de donde coges la pieza.', 'mal');
                return self._pitido(false);
            }
            if (!r || !r.ok) {
                self._avisoFaltante((r && r.msg) || 'No se ha podido cambiar.', 'mal');
                return self._pitido(false);
            }
            var nueva = r.ubicacion_nueva;
            var productoId = f.linea.producto_id;
            self._cerrarFaltante(true);
            self._pitido(true);
            return self._recargar(function () {
                // se ve la línea en su ubicación nueva: ahora se lee el EAN como siempre
                var l = _.find(self.estado.lineas, function (x) {
                    return x.producto_id === productoId && x.ubicacion === nueva && !x.completa && !x.caja;
                });
                self.verId = l && l.id !== self.estado.siguiente_id ? l.id : null;
                self._aviso('Cambiada a ' + nueva + '. Ahora lee el producto.', 'info');
            });
        }).guardedCatch(function (err) {
            f.ocupado = false;
            if (err && err.event && err.event.preventDefault) { err.event.preventDefault(); }
            if (self._esSinConexion(err)) { self._cerrarFaltante(); return self._sinConexion(); }
            self._avisoFaltante(self._mensajeError(err), 'mal');
            self._pitido(false);
        });
    },

    _onFaltaNada: function () {
        var self = this;
        var f = this.faltante;
        if (!f || !f.listo || f.ocupado) { return; }
        if (!this.confirmarNada) {
            this.confirmarNada = true;
            this.$('.o_kp_f_nada').addClass('o_kp_confirmar').text('Pulsa otra vez: va a faltantes');
            clearTimeout(this.timerConfirmar);
            this.timerConfirmar = setTimeout(function () { self._sinConfirmar(); }, CONFIRMAR_MS);
            return;
        }
        this._sinConfirmar();
        f.ocupado = true;
        this._avisoFaltante('Mandando a faltantes…', 'info');
        return this._rpc({route: '/koroshi/faltantes/sin_alternativa', params: {
            move_line_id: f.linea.id, employee_id: this.operario ? this.operario.id : false,
        }}).then(function (r) {
            f.ocupado = false;
            if (!r || !r.ok) {
                self._avisoFaltante((r && r.msg) || 'No se ha podido mandar a faltantes.', 'mal');
                return self._pitido(false);
            }
            self._cerrarFaltante(true);
            self._pitido(true);
            return self._recargar(function () {
                self.verId = null;
                var e = self.estado;
                var txt = 'Va a faltantes: la OUT sale sin esa pieza.';
                if (e.todo_leido && e.leidas) { txt += e.sin_caja ? ' Cierra la caja y valida.' : ' Pulsa Validar.'; }
                self._aviso(txt, 'info');
            });
        }).guardedCatch(function (err) {
            f.ocupado = false;
            if (err && err.event && err.event.preventDefault) { err.event.preventDefault(); }
            if (self._esSinConexion(err)) { self._cerrarFaltante(); return self._sinConexion(); }
            self._avisoFaltante(self._mensajeError(err), 'mal');
            self._pitido(false);
        });
    },

    _sinConfirmar: function () {
        clearTimeout(this.timerConfirmar);
        this.confirmarNada = false;
        var hay = this.$('.o_kp_f_alternativas li').length;
        this.$('.o_kp_f_nada').removeClass('o_kp_confirmar').text(hay ? 'Tampoco está aquí' : 'Mandar a faltantes');
    },

    _avisoFaltante: function (texto, clase) {
        var tipo = clase || 'info';
        this.$('.o_kp_f_aviso').attr('class', 'o_kp_hoja_aviso o_kp_f_aviso' + (texto ? ' o_kp_mal o_kp_' + tipo : ''))
            .text(texto ? (ICONOS[tipo] || ICONOS.info) + ' ' + texto : '');
    },

    _onCancelarFaltante: function () {
        this._cerrarFaltante();
    },

    _cerrarFaltante: function (callado) {
        if (this.faltante && this.faltante.ocupado) { return; }
        clearTimeout(this.timerConfirmar);
        this.confirmarNada = false;
        this.faltante = null;
        this.$('.o_kp_hoja_faltante').hide();
        this._cerrarHoja();
        if (!callado) { this._aviso('', ''); }
    },


    // ------------------------------------------------------------ v3.0.1: flechas
    _idVisto: function () {
        var e = this.estado;
        if (!e) { return null; }
        if (this.verId && _.findWhere(e.lineas, {id: this.verId})) { return this.verId; }
        this.verId = null;
        return e.siguiente_id || null;
    },

    _mover: function (paso) {
        var e = this.estado;
        if (!e || !e.lineas.length || this.modo !== 'leer') { return; }
        var ids = _.pluck(e.lineas, 'id');
        var actual = this._idVisto();
        var i = actual ? ids.indexOf(actual) : (paso > 0 ? -1 : ids.length);
        var j = Math.max(0, Math.min(ids.length - 1, i + paso));
        this.verId = ids[j] === e.siguiente_id ? null : ids[j];
        this._pintar();
        this._foco();
    },

    _onAnterior: function () { this._mover(-1); },
    _onPosterior: function () { this._mover(1); },

    _onIrPendiente: function () {
        this.verId = null;
        this._pintar();
        this._foco();
    },

    _onTocarLinea: function (ev) {
        var id = parseInt($(ev.currentTarget).data('id'), 10);
        if (!id || this.modo !== 'leer') { return; }
        this.verId = id === (this.estado && this.estado.siguiente_id) ? null : id;
        this._pintar();
        var el = this.$('.o_kp_siguiente')[0];
        if (el && el.scrollIntoView) { el.scrollIntoView({block: 'start'}); }
        this._foco();
    },

    _onVerLineas: function () {
        var $l = this.$('.o_kp_lineas');
        var abrir = !$l.is(':visible');
        $l.toggle(abrir);
        this.$('.o_kp_ver_lineas').attr('aria-expanded', abrir ? 'true' : 'false');
        this._pintarBotonLineas();
    },

    // ------------------------------------------------------------ sin conexión
    _esSinConexion: function (e) {
        if (!navigator.onLine) { return true; }
        var err = e && (e.message || e);
        if (!err) { return false; }
        if (err.code === -32098) { return true; }
        var tipo = err.data && err.data.type;
        return !!(tipo && String(tipo).indexOf('xhr') === 0);
    },

    _mensajeError: function (e) {
        var err = e && (e.message || e);
        return (err && err.data && err.data.message) || (err && err.message) || 'Error de Odoo';
    },

    _sinConexion: function () {
        var self = this;
        if (!this.sinRed) {
            this.sinRed = true;
            this.$('.o_kp_offline').show();
            this._estadoLector();
            this.$el.addClass('o_kp_sin_red');
            this._pitido(false);
        }
        clearTimeout(this.timerReintento);
        this.timerReintento = setTimeout(function () { self._probarConexion(); }, REINTENTO_MS);
    },

    _probarConexion: function () {
        var self = this;
        if (!this.sinRed || !this._out()) { return; }
        return this._rpc({route: '/koroshi/preparacion/cargar', params: {picking_id: this._out().id,
            employee_id: this.operario ? this.operario.id : false}}, {shadow: true})
            .then(function (r) {
                if (!r || !r.ok) { return self._sinConexion(); }
                clearTimeout(self.timerReintento);
                self.sinRed = false;
                self.$('.o_kp_offline').hide();
                self._estadoLector();
                self.$el.removeClass('o_kp_sin_red');
                self.estado = r.estado;
                self._pintar();
                self._aviso('Conexión recuperada.' + (self.cola.length ? ' Guardando lo leído…' : ' Ya puedes leer.'), 'ok');
                self._pitido(true);
                self._enviar();   // la lectura que se quedó a medias (mismo id: no cuenta dos veces)
            }).guardedCatch(function (e) {
                if (e && e.event && e.event.preventDefault) { e.event.preventDefault(); }
                self._sinConexion();
            });
    },

    _onEnLinea: function () {
        if (this.sinRed) { this._probarConexion(); }
    },

    // ------------------------------------------------------------ pintar
    _pintar: function () {
        var e = this.estado;
        if (!e) {
            this.$('.o_kp_ref').text(this.pickingName || '');
            this.$('.o_kp_siguiente, .o_kp_progreso').hide();
            this.$('.o_kp_caja, .o_kp_validar, .o_kp_deshacer, .o_kp_faltante').prop('disabled', true);
            return;
        }
        var out = e.out;
        this.$('.o_kp_ref').text(out.name);
        this.$('.o_kp_tienda').text(out.tienda || out.origen || '');
        // v3.3: preparar a dos -> quién va con quién y por dónde empieza cada uno
        var quien = this.operario ? this.operario.nombre : 'Sin tarjeta';
        if (e.a_dos) {
            quien += e.rol === 'ayudante' ? ' · 2ª mitad' : ' · 1ª mitad';   // v3.4: la OUT partida por la mitad
            if (e.companeros && e.companeros.length) { quien += ' · con ' + e.companeros.join(', '); }
        }
        this.$('.o_kp_operario').text(quien);
        this.$el.toggleClass('o_kp_a_dos', !!e.a_dos).toggleClass('o_kp_ayudante', e.rol === 'ayudante');
        this._avisosEquipo(e);
        // progreso
        var pct = e.pedidas ? Math.round(100 * Math.min(e.leidas, e.pedidas) / e.pedidas) : 0;
        this.$('.o_kp_barra_lleno').css('width', pct + '%');
        this.$('.o_kp_progreso_texto').text(e.leidas + ' de ' + e.pedidas + ' uds');
        // v3.1: con 0 leídas no se dice nada de cajas («Todo en caja» confundía)
        var txtCaja = e.sin_caja ? 'Sin caja: ' + e.sin_caja + (e.sin_caja === 1 ? ' ud' : ' uds')
            : (e.leidas ? '✓ Todo en caja' : '');
        if (e.a_dos && e.sin_caja) {
            // v3.3: cada uno cierra su caja solo con lo que ha leído él
            txtCaja = 'Tuyas sin caja: ' + e.mias_sin_caja + (e.otros_sin_caja ? ' · compañero: ' + e.otros_sin_caja : '');
        }
        this.$('.o_kp_sin_caja').text(txtCaja).toggleClass('o_kp_hay', !!e.sin_caja).toggle(!!txtCaja);
        this.$('.o_kp_cajas_resumen').text(e.cajas.length ? '📦 ' + e.cajas.length + (e.cajas.length === 1 ? ' caja' : ' cajas') : '');
        this.$('.o_kp_progreso').show();
        // la línea en grande: la que toca o la elegida con las flechas (v3.0.1)
        var idVisto = this._idVisto();
        var sig = idVisto && _.findWhere(e.lineas, {id: idVisto});
        if (sig && (!e.todo_leido || this.verId)) {
            var pos = e.lineas.indexOf(sig);
            var esLaQueToca = sig.id === e.siguiente_id;
            this.$('.o_kp_etiqueta').text(esLaQueToca ? 'Ve a' : (sig.completa ? 'Ya cogida' : 'Pendiente'));
            this.$('.o_kp_posicion').text('Línea ' + (pos + 1) + ' de ' + e.lineas.length);
            this.$('.o_kp_anterior').prop('disabled', pos <= 0);
            this.$('.o_kp_posterior').prop('disabled', pos >= e.lineas.length - 1);
            this.$('.o_kp_ubicacion').text(sig.ubicacion);
            // v3.1: nombre una sola vez y en grande, talla destacada, referencia solo si es distinta
            this.$('.o_kp_producto_ref').text(sig.nombre || sig.producto);
            this.$('.o_kp_talla').text(sig.talla || '');
            this.$('.o_kp_talla_fila').toggle(!!sig.talla);
            this.$('.o_kp_producto').text(sig.ref ? 'Ref. ' + sig.ref : '').toggle(!!sig.ref);
            this.$('.o_kp_cuantas').text((sig.completa ? '✓ ' : '') + 'Cogidas ' + sig.leidas + ' de ' + sig.pedidas +
                                         (sig.caja ? ' · 📦 ' + sig.caja : ''));
            // v3.1: sin foto no se pinta nada (ni el icono gris de Odoo): el texto ocupa todo el ancho
            var conFoto = sig.tiene_foto !== false && !!sig.producto_id;
            var src = conFoto ? '/web/image/product.product/' + sig.producto_id + '/image_256' : '';
            var $f = this.$('.o_kp_foto');
            if ($f.attr('src') !== src) {
                $f.hide();
                if (src) { $f.attr('src', src); } else { $f.removeAttr('src'); }
            }
            if (!conFoto) { $f.hide(); }
            this.$('.o_kp_siguiente').toggleClass('o_kp_vista_hecha', !!sig.completa)
                .toggleClass('o_kp_vista_otra', !esLaQueToca).show();
            this.$('.o_kp_ir_pendiente').text(e.todo_leido ? 'Volver al resumen ▸' : 'Ir a la que toca ▸')
                .toggle(!esLaQueToca);
            this.$('.o_kp_completa').hide();
        } else {
            this.$('.o_kp_siguiente').hide();
            this.$('.o_kp_completa_texto').text(e.todo_leido
                ? (e.a_dos && e.sin_caja && !e.mias_sin_caja ? 'Falta que tu compañero cierre su caja.'
                    : (e.sin_caja ? 'Pulsa «Caja» y lee la etiqueta. Después, Validar.' : 'Pulsa «Validar».'))
                : 'Lo que queda ya está en caja o se marca con «Faltante».');
            this.$('.o_kp_completa').show();
        }
        // botones
        var libre = this.modo === 'leer' && !this.sinRed;
        var mias = e.a_dos ? e.mias_sin_caja : e.sin_caja;   // v3.3: a dos, solo lo suyo
        this.$('.o_kp_caja').prop('disabled', !libre || !mias)
            .toggleClass('o_kp_destacado', !!mias && e.todo_leido);
        this.$('.o_kp_validar').prop('disabled', !libre || !!e.sin_caja || !e.leidas)
            .toggleClass('o_kp_destacado', !e.sin_caja && e.todo_leido);
        this.$('.o_kp_deshacer').prop('disabled', !libre || !e.leidas);
        this.$('.o_kp_faltante').prop('disabled', !libre || e.todo_leido || !e.siguiente_id);
        this._pintarLineas();
    },

    // v3.4: avisos de trabajar a dos: «X se ha unido» (al titular, una vez) y los faltantes del compañero
    _avisosEquipo: function (e) {
        var self = this;
        this.faltantesVistos = this.faltantesVistos || {};
        var nuevos = [];
        (e.faltantes_companero || []).forEach(function (f) {
            if (!self.faltantesVistos[f.id]) {
                self.faltantesVistos[f.id] = true;
                if (self.faltantesListos) { nuevos.push(f.texto); }
            }
        });
        this.faltantesListos = true;   // los de antes de abrir la pantalla no se avisan
        if (e.aviso_equipo) { nuevos.unshift(e.aviso_equipo); e.aviso_equipo = ''; }
        if (nuevos.length) {
            this._aviso(nuevos.join(' · '), 'warn');
            this._pitido(true);
        }
    },

    _pintarLineas: function () {
        var e = this.estado;
        var $l = this.$('.o_kp_lineas').empty();
        e.lineas.forEach(function (l) {
            var $li = $('<li/>').attr('data-id', l.id).toggleClass('o_kp_hecha', l.completa)
                .toggleClass('o_kp_ahora', l.id === e.siguiente_id);
            $('<span class="o_kp_l_marca" aria-hidden="true"/>').text(l.completa ? '✓' : '').appendTo($li);
            if (l.producto_id && l.tiene_foto !== false) {
                // v3.0.1: miniatura (solo se descarga al abrir la lista)
                $('<img class="o_kp_l_foto" alt="" loading="lazy"/>')
                    .attr('src', '/web/image/product.product/' + l.producto_id + '/image_128')
                    .on('error', function () { $(this).css('visibility', 'hidden'); }).appendTo($li);
            }
            var $t = $('<span class="o_kp_l_texto"/>').appendTo($li);
            $('<span class="o_kp_l_ubi"/>').text(l.ubicacion).appendTo($t);
            $('<span class="o_kp_l_prod"/>').text((l.nombre || l.producto) + (l.talla ? ' · Talla ' + l.talla : '')).appendTo($t);
            if (l.caja) { $('<span class="o_kp_l_caja"/>').text('📦 ' + l.caja).appendTo($t); }
            $('<span class="o_kp_l_cant"/>').text(l.leidas + '/' + l.pedidas).appendTo($li);
            $l.append($li);
        });
        var $c = this.$('.o_kp_cajas').empty();
        if (e.cajas.length) {
            $c.text('Cajas cerradas: ' + e.cajas.map(function (c) { return c.nombre + ' (' + c.uds + ')'; }).join(', '));
        }
        this._pintarBotonLineas();
    },

    _pintarBotonLineas: function () {
        var n = this.estado ? this.estado.lineas.length : 0;
        var abierto = this.$('.o_kp_lineas').is(':visible');
        this.$('.o_kp_ver_lineas').text((abierto ? '▾ Ocultar líneas' : '▸ Ver líneas') + ' (' + n + ')');
    },

    _capa: function (texto, hecho) {
        this.$('.o_kp_capa_texto').text(texto);
        this.$('.o_kp_capa').toggleClass('o_kp_capa_hecho', !!hecho).show();
    },

    _ocultarCapa: function () {
        this.$('.o_kp_capa').hide().removeClass('o_kp_capa_hecho');
    },

    _aviso: function (texto, clase) {
        var self = this;
        clearTimeout(this.timerAviso);
        var $a = this.$('.o_kp_aviso').empty();
        var tipo = clase || 'info';
        $a.attr('class', 'o_kp_aviso' + (texto ? ' o_kp_' + tipo : ''));
        if (!texto) { return; }
        $('<span class="o_kp_aviso_icono" aria-hidden="true"/>').text(ICONOS[tipo] || ICONOS.info).appendTo($a);
        $('<span/>').text(texto).appendTo($a);
        if (tipo === 'ok') {
            this.timerAviso = setTimeout(function () { self._aviso('', ''); }, AVISO_OK_MS);
        }
    },

    _foco: function () {
        var $i = this.$(this.modo === 'faltante' ? '.o_kp_f_codigo' : '.o_kp_codigo');
        if ($i.length && !('ontouchstart' in window)) { $i.focus(); }
        this._estadoLector();
    },

    _onTocar: function () {
        this.$('.o_kp_codigo').focus();
        this._estadoLector();
    },

    _onBlur: function () {
        var self = this;
        setTimeout(function () { self._estadoLector(); }, 50);
    },

    _estadoLector: function () {
        // v3.0.2: el lector va por el bus de Odoo (como la app de código de barras): no hace falta tocar el campo.
        // El punto solo se pone gris sin conexión.
        var listo = !!this.el && !this.sinRed;
        this.$('.o_kp_lector').toggleClass('o_kp_listo', listo);
        this.$('.o_kp_lector_texto').text(listo ? 'Lector preparado' : 'Sin conexión');
    },

    // ------------------------------------------------------------ sonido y vibración (mismo interruptor que Lecturas)
    _leerSonido: function () {
        try { return window.localStorage.getItem(CLAVE_SONIDO) !== '0'; } catch (e) { return true; }
    },

    _vibrar: function (patron) {
        try {
            var activo = !navigator.userActivation || navigator.userActivation.hasBeenActive;
            if (this.sonido && activo && navigator.vibrate) { navigator.vibrate(patron); }
        } catch (e) { /* nada */ }
    },

    _pitido: function (bien) {
        this._vibrar(bien ? 60 : [120, 80, 120]);
        if (!this.sonido) { return; }
        try {
            var Ctx = window.AudioContext || window.webkitAudioContext;
            if (!Ctx) { return; }
            if (!this.audio) { this.audio = new Ctx(); }
            var ctx = this.audio;
            if (ctx.state === 'suspended' && ctx.resume) { ctx.resume(); }
            var o = ctx.createOscillator();
            var g = ctx.createGain();
            o.type = bien ? 'sine' : 'square';
            o.frequency.value = bien ? 880 : 220;
            g.gain.value = 0.2;
            o.connect(g);
            g.connect(ctx.destination);
            o.start();
            o.stop(ctx.currentTime + (bien ? 0.1 : 0.4));
        } catch (e) { /* sin sonido */ }
    },
});

core.action_registry.add('koroshi_preparacion_pantalla', Pantalla);
return Pantalla;
});


odoo.define('koroshi_preparacion.Lecturas', function (require) {
'use strict';
/* En Lecturas (koroshi_operarios): si el operario está activado y la OUT es suelta, se abre la pantalla de
 * preparación en lugar de la app de código de barras. En cualquier otro caso, lo de siempre. */
var Operarios = require('koroshi_operarios.Pantalla');

Operarios.include({
    _abrir: function (obj) {
        var self = this;
        var deSiempre = this._super.bind(this);
        if (!obj || obj.tipo !== 'out' || !this.operario || this.sinRed) {
            return deSiempre(obj);
        }
        var ref = obj.picking_name || obj.ref;
        this.ocupado = true;
        return this._rpc({route: '/koroshi/preparacion/modo',
                          params: {employee_id: this.operario.id, picking_name: ref}}, {shadow: true})
            .then(function (r) {
                if (!r || !r.propia) {
                    self.ocupado = false;
                    return deSiempre(obj);
                }
                self._mostrarAbriendo(ref, self.operario.nombre);
                return self.do_action('koroshi_preparacion.action_koroshi_preparacion_pantalla', {
                    additional_context: {
                        preparacion_out: ref,
                        preparacion_operario: {id: self.operario.id, nombre: self.operario.nombre},
                    },
                }).then(function () { self.ocupado = false; });
            }).guardedCatch(function (e) {
                self.ocupado = false;
                if (e && e.event && e.event.preventDefault) { e.event.preventDefault(); }
                if (self._esSinConexion(e)) { self._ocultarCapa(); return self._sinConexion(); }
                return deSiempre(obj);   // si falla la pregunta, la app de siempre
            });
    },
});
return Operarios;
});


odoo.define('koroshi_preparacion.Faltantes', function (require) {
'use strict';
/* En la pantalla de Faltante (koroshi_faltantes): «Volver a la OUT» vuelve a la pantalla de preparación en lugar
 * de abrir la app de código de barras (si venía de ella, o si el operario está activado y la OUT es suelta). */
var Faltantes = require('koroshi_faltantes.Pantalla');

Faltantes.include({
    init: function (parent, action) {
        this._super.apply(this, arguments);
        var ctx = (action && action.context) || {};
        this.desdePreparacion = !!ctx.desde_preparacion;
    },

    _onVolver: function () {
        var self = this;
        var deSiempre = this._super.bind(this);
        if (!this.out || this.ocupado || this.paso === 'validada' || this.out.batch_id || this.out.lote_id) {
            return deSiempre();
        }
        if (this.desdePreparacion) {
            return this.trigger_up('history_back');
        }
        var emp = this._empleadoId ? this._empleadoId() : false;
        if (!emp) { return deSiempre(); }
        return this._rpc({route: '/koroshi/preparacion/modo', params: {employee_id: emp, picking_name: this.out.name}},
                         {shadow: true})
            .then(function (r) {
                if (!r || !r.propia) { return deSiempre(); }
                return self.do_action('koroshi_preparacion.action_koroshi_preparacion_pantalla', {
                    additional_context: {
                        preparacion_out: self.out.name,
                        preparacion_operario: self.operario ? {id: self.operario.id, nombre: self.operario.nombre} : false,
                    },
                    replace_last_action: true,
                });
            }).guardedCatch(function (e) {
                if (e && e.event && e.event.preventDefault) { e.event.preventDefault(); }
                return deSiempre();
            });
    },
});
return Faltantes;
});
