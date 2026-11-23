odoo.define('koroshi_faltantes.Pantalla', function (require) {
'use strict';
/* KOROSHI Faltantes v1.3 - pantalla "Faltante" de la PDA (accion de cliente koroshi_faltantes_pantalla).
 *
 * Los faltantes se marcan al FINAL de la OUT, sin leer el EAN:
 *   1. OUT (ya viene puesta desde Lecturas / Operarios, o se lee) -> lista de lo que queda por coger, en el orden de
 *      la app de codigo de barras (referencia grande, color / talla, ubicacion, uds).
 *   2. Se marcan una o varias lineas (las que no estan) -> Continuar. Tambien: leer la UBICACION donde esta (elige la
 *      linea pendiente de alli) o el EAN.
 *   3. Para cada linea, UNA ubicacion recomendada (la de stock libre mas cercana):
 *        - leer la ubicacion de donde se coge -> /koroshi/faltantes/reubicar
 *        - "Tampoco esta aqui" + confirmar -> /koroshi/faltantes/sin_alternativa (la pieza va a FALTANTE)
 *        - "Ver mas ubicaciones" ensena la lista de antes (hasta 5).
 *   4. Al acabar: si no queda nada por coger, se valida sola (/koroshi/faltantes/validar) o con el boton
 *      "Validar OUT". Si Odoo pregunta por el pedido pendiente: "Si, pedido pendiente" / "No, sin pedido pendiente".
 *      Si queda algo por coger (p. ej. lo reubicado): "Volver a la OUT".
 * La tarjeta del operario se puede leer en cualquier momento; si no, se usa el de la tarea abierta de la OUT.
 * Lecturas por el bus 'barcode_scanned' (solo si la pantalla se ve) o escribiendo y Enter.
 * Si se abrio desde la pantalla de Operarios, al volver de la OUT (o al validar) regresa a Operarios.
 * v1.8 (20/11): la tarjeta es la misma que en Lecturas y Contenedores (memoria de la PDA, clave
 *   koroshi_operarios_pda_<usuario>, {id, nombre, t}). Sin operario de Lecturas, al entrar se coge la guardada si
 *   tiene menos de 15 min sin actividad; leer una tarjeta aqui la deja puesta en las otras pantallas.
 * v1.10 (23/11, O4): la tarjeta y el lector salen de koroshi_base.comun. El campo ahora tambien lee cuando el lector
 *   para (las PDA no mandan Intro), pero solo lo que llega de golpe: lo escrito a mano («23649») espera al Enter.
 * No cambia la app de codigo de barras.
 */
var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var comun = require('koroshi_base.comun');   // v1.10

var REPETIDA_MS = 700;        // la misma lectura dos veces seguidas (bus + campo) cuenta una
var CONFIRMAR_MS = 5000;      // tiempo para la segunda pulsacion de "No esta en ninguna ubicacion"
var VOLVER_MS = 1800;         // tras validar, vuelve solo a Operarios
var TARJETA_MS = 3600000;     // v1.8: tarjeta guardada valida sin actividad; v1.8.1: parametro
                              // koroshi_operarios.minutos_tarjeta (60 por defecto), se lee al entrar

var Pantalla = AbstractAction.extend({
    contentTemplate: 'koroshi_faltantes.Pantalla',
    events: {
        'keydown .o_kf_codigo': '_onKeydown',
        'input .o_kf_codigo': '_onEscribe',     // v1.10
        'click .o_kf_pend': '_onMarcar',
        'click .o_kf_continuar': '_onContinuar',
        'click .o_kf_nada': '_onNada',
        'click .o_kf_vermas': '_onVerMas',
        'click .o_kf_saltar_linea': '_onSaltarLinea',
        'click .o_kf_validar': '_onValidar',
        'click .o_kf_si': '_onPedidoSi',
        'click .o_kf_no': '_onPedidoNo',
        'click .o_kf_volver': '_onVolver',
        'click .o_kf_otro': '_onOtro',
        'click .o_kf_nuevo': '_onNuevo',
        'click .o_kf_salir': '_onSalir',
    },

    init: function (parent, action) {
        this._super.apply(this, arguments);
        var ctx = (action && action.context) || {};
        this.desdeOperarios = !!ctx.desde_operarios;
        // desde Operarios llega la OUT (o la agrupacion Z-) que esta haciendo y el operario
        this.outInicial = ctx.faltante_out || false;
        this.operarioInicial = ctx.faltante_operario || null;
        this.ocupado = false;
        this.ultima = {codigo: '', t: 0};
        this.operario = null;      // {id, nombre, tarjeta: bool}
        this.abrioOut = false;
        this._limpiar();
    },

    start: function () {
        var self = this;
        core.bus.on('barcode_scanned', this, this._onBarcodeScanned);
        return this._super.apply(this, arguments).then(function () {
            if (self.operarioInicial && self.operarioInicial.id) {
                self.operario = {id: self.operarioInicial.id, nombre: self.operarioInicial.nombre, tarjeta: true};
            } else {
                self._tomarGuardada();   // v1.8
                self._leerMinutosTarjeta();   // v1.8.1
            }
            $('body').addClass('o_kf_en_faltante');   // v1.4: en PDA (pantalla estrecha) sin la barra de Odoo
            self._pintar();
            if (self.outInicial) {
                self._aviso('Cargando ' + self.outInicial + '...', 'info');
                return self._llamar({route: '/koroshi/faltantes/buscar',
                                     params: {codigo: self.outInicial, out_id: false,
                                              employee_id: self._empleadoId()}});
            }
        });
    },

    on_attach_callback: function () {
        this._super.apply(this, arguments);
        $('body').addClass('o_kf_en_faltante');   // v1.4
        this.ocupado = false;
        if (this.abrioOut) {
            // vuelve de la OUT (validada o con la flecha atras)
            this.abrioOut = false;
            if (this.desdeOperarios) {
                this.trigger_up('history_back');
                return;
            }
            this._limpiar();
            this.operario = null;
            this._tomarGuardada();   // v1.8: sigue con la tarjeta de la PDA
            this._aviso('', '');
        }
        this._pintar();
        this._foco();
    },

    on_detach_callback: function () {
        $('body').removeClass('o_kf_en_faltante');   // v1.4
        this._super.apply(this, arguments);
    },

    destroy: function () {
        $('body').removeClass('o_kf_en_faltante');   // v1.4
        core.bus.off('barcode_scanned', this, this._onBarcodeScanned);
        clearTimeout(this.timerConfirmar);
        clearTimeout(this.timerVolver);
        comun.cancelarLector(this);   // v1.10
        this._super.apply(this, arguments);
    },

    // ------------------------------------------------------------ v1.8: tarjeta compartida con Lecturas y Contenedores
    // v1.10: de koroshi_base.comun.tarjeta
    _tomarGuardada: function () {
        var g = comun.tarjeta.leer();
        if (!comun.tarjeta.vigente(g, TARJETA_MS)) { return false; }
        this.operario = {id: g.id, nombre: g.nombre, tarjeta: true};
        return true;
    },
    // v1.8.1: cuanto dura la tarjeta sin actividad (si falla, se queda con el valor de antes)
    _leerMinutosTarjeta: function () {
        var self = this;
        return comun.tarjeta.minutos(this).then(function (minutos) {
            if (minutos > 0) {
                TARJETA_MS = minutos * 60000;
                if (!self.operario && self._tomarGuardada()) { self._pintar(); }
            }
        });
    },
    _guardarTarjeta: function () {
        if (!this.operario || !this.operario.tarjeta) { return; }
        comun.tarjeta.guardar(this.operario);
    },

    // ------------------------------------------------------------ estado
    _limpiar: function () {
        this.paso = 'out';         // out | lista | ubic | fin | preguntar | validada
        this.out = null;
        this.pendientes = [];      // lo que queda por coger
        this.marcadas = [];        // ids marcados en la lista
        this.filtro = null;        // ids que deja ver una ubicacion o un EAN leidos
        this.cola = [];            // ids que faltan por resolver de los marcados
        this.linea = null;
        this.hechos = [];          // [{ref, tipo}]
        this.verMas = false;
        this.confirmarNada = false;
        this.fin = null;           // {se_puede_validar, quedan}
    },

    _outParams: function () {
        if (!this.out) { return {out_id: false}; }
        return this.out.lote_id ? {out_id: false, lote_id: this.out.lote_id} : {out_id: this.out.id};
    },

    // ------------------------------------------------------------ lecturas
    _onBarcodeScanned: function (barcode) {
        if (!this.el || !$.contains(document, this.el)) {
            return;     // la pantalla no se ve: no es para nosotros
        }
        this._leer(barcode);
    },

    // v1.10: el lector de la PDA no manda Enter: se lee cuando para (solo lo que llega de golpe, no lo escrito a mano)
    _onEscribe: function (ev) {
        var self = this;
        comun.leerAlParar(this, ev.currentTarget, function (codigo) { self._leer(codigo); }, {soloRafaga: true});
    },

    _onKeydown: function (ev) {
        if (ev.key === 'Enter' || ev.keyCode === 13) {
            comun.cancelarLector(this);   // v1.10
            ev.preventDefault();
            var $i = this.$('.o_kf_codigo');
            var c = ($i.val() || '').trim();
            $i.val('');
            if (c) { this._leer(c); }
        }
    },

    _leer: function (codigo) {
        codigo = (codigo || '').trim();
        var ahora = Date.now();
        if (!codigo || (codigo === this.ultima.codigo && ahora - this.ultima.t < REPETIDA_MS) || this.ocupado) {
            return;
        }
        this.ultima = {codigo: codigo, t: ahora};
        var peticion;
        if (this.paso === 'ubic' && this.linea && !this.linea.motivo) {
            peticion = {route: '/koroshi/faltantes/reubicar',
                        params: {move_line_id: this.linea.id, codigo: codigo, employee_id: this._empleadoId()}};
            this._aviso('Cambiando la reserva...', 'info');
        } else {
            peticion = {route: '/koroshi/faltantes/buscar',
                        params: _.extend({codigo: codigo, employee_id: this._empleadoId()}, this._outParams())};
        }
        return this._llamar(peticion);
    },

    _llamar: function (peticion) {
        var self = this;
        this.ocupado = true;
        return this._rpc(peticion).then(function (r) {
            self.ocupado = false;
            self._respuesta(r);
        }).guardedCatch(function () {
            self.ocupado = false;
            self._aviso('Sin conexion con Odoo o error de Odoo. No se ha cambiado nada en esta lectura.', 'mal');
            self._pitido(false);
        });
    },

    _respuesta: function (r) {
        if (!r || !r.ok) {
            if (r && r.que === 'no_validada') {
                this.paso = 'fin';
                this.fin = {se_puede_validar: false, quedan: 0, error: true};
            }
            this._aviso((r && r.msg) || 'Error', 'mal');
            this._pitido(false);
            this._pintar();
            return;
        }
        this._pitido(true);
        if (r.que === 'tarjeta') {
            this.operario = {id: r.operario.id, nombre: r.operario.nombre, tarjeta: true};
            this._guardarTarjeta();   // v1.8: queda puesta tambien en Lecturas y Contenedores
            this._aviso('Operario: ' + r.operario.nombre, 'info');
        } else if (r.que === 'out') {
            this._limpiar();
            this.out = r.out;
            if (r.operario && !(this.operario && this.operario.tarjeta)) {
                this.operario = {id: r.operario.id, nombre: r.operario.nombre, tarjeta: false};
            }
            this.pendientes = r.pendientes || [];
            this.paso = 'lista';
            if (!this.pendientes.length) {
                this._aviso('No queda nada por coger en ' + this.out.name + '.', 'ok');
                this.paso = 'fin';
                this.fin = {se_puede_validar: !this.out.batch_id, quedan: 0};
            } else if (this.pendientes.length === 1 && !this.pendientes[0].motivo) {
                this.marcadas = [this.pendientes[0].id];
                this._aviso('Solo queda esta. Pulsa Continuar si es la que no está.', 'info');
            } else {
                this._aviso('', '');
            }
        } else if (r.que === 'lista') {
            this.pendientes = r.pendientes || [];
        } else if (r.que === 'filtro') {
            // una ubicacion o un EAN leidos con varias lineas: solo se ven esas
            this.paso = 'lista';
            this.filtro = r.ids || [];
            this._aviso(r.msg || '', 'info');
        } else if (r.que === 'linea') {
            if (r.out && !(this.out && this.out.lote_id)) { this.out = r.out; }
            this.linea = r.linea;
            this.paso = 'ubic';
            this.verMas = false;
            this.confirmarNada = false;
            this._aviso(r.linea.motivo || '', r.linea.motivo ? 'mal' : '');
        } else if (r.que === 'hecho') {
            this.hechos.push({ref: (this.linea && this.linea.ref) || '', tipo: r.tipo,
                              ubicacion: r.ubicacion_nueva || ''});
            this.pendientes = r.pendientes || [];
            this._aviso(r.msg + (r.nota ? ' ' + r.nota : ''), 'ok');
            this.linea = null;
            return this._siguienteDeCola(r);
        } else if (r.que === 'quedan') {
            this.paso = 'fin';
            this.fin = {se_puede_validar: false, quedan: r.n};
            this._aviso(r.msg, 'mal');
        } else if (r.que === 'preguntar') {
            this.paso = 'preguntar';
            this._aviso('', '');
        } else if (r.que === 'validada') {
            this.paso = 'validada';
            this._aviso(r.msg, 'ok');
            this._volverSolo();
        }
        this._pintar();
    },

    _siguienteDeCola: function (r) {
        // quita la resuelta de la cola y pasa a la siguiente marcada que siga pendiente
        var vivos = _.pluck(this.pendientes, 'id');
        this.cola = _.filter(this.cola, function (id) { return _.contains(vivos, id); });
        this.marcadas = [];
        if (this.cola.length) {
            var id = this.cola.shift();
            this._pintar();
            return this._llamar({route: '/koroshi/faltantes/buscar', params: {move_line_id: id}});
        }
        this.paso = 'fin';
        this.fin = {se_puede_validar: !!(r && r.se_puede_validar), quedan: this.pendientes.length};
        this._pintar();
        if (r && r.validar_sola) {
            return this._validar(false);
        }
    },

    _empleadoId: function () {
        return this.operario ? this.operario.id : false;
    },

    // ------------------------------------------------------------ botones
    _onMarcar: function (ev) {
        var id = parseInt($(ev.currentTarget).data('id'), 10);
        var p = _.findWhere(this.pendientes, {id: id});
        if (!p || this.ocupado) { return; }
        if (p.motivo) {
            this._aviso(p.motivo, 'mal');
            return;
        }
        if (_.contains(this.marcadas, id)) {
            this.marcadas = _.without(this.marcadas, id);
        } else {
            this.marcadas.push(id);
        }
        this._pintar();
    },

    _onContinuar: function () {
        if (!this.marcadas.length || this.ocupado) { return; }
        var self = this;
        // en el orden de la lista
        this.cola = _.filter(_.pluck(this.pendientes, 'id'), function (id) { return _.contains(self.marcadas, id); });
        this.filtro = null;
        var id = this.cola.shift();
        return this._llamar({route: '/koroshi/faltantes/buscar', params: {move_line_id: id}});
    },

    _onNada: function () {
        var self = this;
        if (this.paso !== 'ubic' || !this.linea || this.linea.motivo || this.ocupado) { return; }
        if (!this.confirmarNada) {
            this.confirmarNada = true;
            this._pintar();
            clearTimeout(this.timerConfirmar);
            this.timerConfirmar = setTimeout(function () {
                self.confirmarNada = false;
                self._pintar();
            }, CONFIRMAR_MS);
            return;
        }
        clearTimeout(this.timerConfirmar);
        this.confirmarNada = false;
        this._aviso('Mandando a faltantes...', 'info');
        return this._llamar({route: '/koroshi/faltantes/sin_alternativa',
                             params: {move_line_id: this.linea.id, employee_id: this._empleadoId()}});
    },

    _onVerMas: function (ev) {
        ev.preventDefault();
        this.verMas = !this.verMas;
        this._pintar();
    },

    _onSaltarLinea: function () {
        // deja esta linea sin tocar y sigue con la siguiente marcada
        if (this.paso !== 'ubic' || this.ocupado) { return; }
        this.linea = null;
        this._aviso('', '');
        return this._siguienteDeCola({se_puede_validar: false});
    },

    _onValidar: function () {
        return this._validar(false);
    },

    _onPedidoSi: function () {
        return this._validar('si');
    },

    _onPedidoNo: function () {
        return this._validar('no');
    },

    _validar: function (pedidoPendiente) {
        if (!this.out || this.out.lote_id || this.ocupado) { return; }
        this._aviso('Validando ' + this.out.name + '...', 'info');
        return this._llamar({route: '/koroshi/faltantes/validar',
                             params: {out_id: this.out.id, pedido_pendiente: pedidoPendiente || false}});
    },

    _volverSolo: function () {
        // validada: desde Operarios se vuelve solo (Operarios abre la siguiente de la cola)
        var self = this;
        if (!this.desdeOperarios) { return; }
        clearTimeout(this.timerVolver);
        this.timerVolver = setTimeout(function () {
            if (self.paso === 'validada') { self.trigger_up('history_back'); }
        }, VOLVER_MS);
    },

    _onVolver: function () {
        var self = this;
        if (!this.out || this.ocupado) { return; }
        if (this.paso === 'validada') { return this._onSalir(); }
        var out = this.out;
        var fallo = function (msg) {
            self.ocupado = false;
            self.abrioOut = false;
            self._aviso('No se ha podido abrir ' + out.name + ': ' + msg + '. Abrela desde el menu de codigo de barras.', 'mal');
        };
        var prom;
        this.ocupado = true;
        this.abrioOut = true;
        if (out.batch_id) {
            prom = this._rpc({model: 'stock.picking.batch', method: 'start_batch_processing', args: [[out.batch_id]]})
                .then(function (accion) {
                    if (!accion) { return fallo('la agrupacion no devuelve pantalla'); }
                    return self.do_action(accion);
                });
        } else {
            prom = this._rpc({route: '/stock_barcode/scan_from_main_menu', params: {barcode: out.name}})
                .then(function (res) {
                    if (res && res.action) { return self.do_action(res.action); }
                    return fallo((res && res.warning) || 'sin respuesta');
                });
        }
        return prom.then(function () { self.ocupado = false; }).guardedCatch(function () { fallo('error de Odoo'); });
    },

    _onOtro: function () {
        // otro faltante en la misma OUT: vuelve a la lista (refrescada)
        if (!this.out) { return this._onNuevo(); }
        var out = this.out;
        var hechos = this.hechos;
        this._limpiar();
        this.out = out;
        this.hechos = hechos;
        this.paso = 'lista';
        this._aviso('', '');
        this._pintar();
        return this._llamar({route: '/koroshi/faltantes/pendientes', params: this._outParams()});
    },

    _onNuevo: function () {
        this._limpiar();
        this._aviso('', '');
        this._pintar();
        this._foco();
    },

    _onSalir: function () {
        if (this.desdeOperarios) {
            this.trigger_up('history_back');
        } else {
            this.do_action('stock_barcode.stock_barcode_action_main_menu');
        }
    },

    // ------------------------------------------------------------ pintar
    _aviso: function (texto, clase) {
        var $a = this.$('.o_kf_aviso');
        $a.text(texto || '');
        $a.attr('class', 'o_kf_aviso o_kf_caja' + (texto ? ' o_kf_' + clase : ''));
    },

    _pitido: function (bien) {
        try {
            var Ctx = window.AudioContext || window.webkitAudioContext;
            var ctx = new Ctx();
            var o = ctx.createOscillator();
            o.frequency.value = bien ? 880 : 220;
            o.connect(ctx.destination);
            o.start();
            setTimeout(function () { o.stop(); ctx.close(); }, bien ? 120 : 400);
        } catch (e) { /* sin sonido */ }
    },

    _foco: function () {
        var $i = this.$('.o_kf_codigo');
        if ($i.length && !('ontouchstart' in window)) { $i.focus(); }
    },

    _uds: function (n) {
        n = Math.round((n || 0) * 100) / 100;
        return n + ' ud';
    },

    _pintar: function () {
        if (!this.$el) { return; }
        var self = this;
        var textos = {
            out: 'Lee la OUT',
            lista: '¿Qué falta? Marca lo que no encuentras',
            ubic: 'Ve a la ubicación recomendada y lee la ubicación de donde la coges',
            fin: 'Faltantes hechos',
            preguntar: 'Faltan piezas: ¿pedido pendiente?',
            validada: 'OUT validada',
        };
        this.$('.o_kf_paso').text(textos[this.paso] || '');
        this.$('.o_kf_quien').text(this.operario ?
            this.operario.nombre + (this.operario.tarjeta ? '' : ' (tarea)') : 'Sin operario (puedes leer tu tarjeta)');

        // OUT
        var $out = this.$('.o_kf_out').empty();
        if (this.out) {
            $out.append($('<b/>').text(this.out.name));
            if (this.out.batch_name && this.out.batch_name !== this.out.name) {
                $out.append(document.createTextNode(' · ' + this.out.batch_name));
            }
            if (this.out.tienda) { $out.append($('<span class="o_kf_sub"/>').text(this.out.tienda)); }
        }
        $out.toggle(!!this.out);

        // lista de lo que queda por coger
        var $ps = this.$('.o_kf_pendientes').empty();
        if (this.paso === 'lista') {
            var visibles = this.filtro ? _.filter(this.pendientes, function (p) { return _.contains(self.filtro, p.id); })
                : this.pendientes;
            if (!visibles.length) {
                $ps.append($('<div class="o_kf_fila o_kf_nadie"/>').text('No queda nada por coger.'));
            }
            visibles.forEach(function (p) {
                var marcada = _.contains(self.marcadas, p.id);
                var $b = $('<button type="button" class="o_kf_pend"/>').attr('data-id', p.id)
                    .toggleClass('o_kf_marcada', marcada).toggleClass('o_kf_bloqueada', !!p.motivo);
                $b.append($('<span class="o_kf_check"/>').text(marcada ? '✔' : ''));
                var $t = $('<span class="o_kf_pend_txt"/>');
                if (p.ubicacion) { $t.append(self._ubi(p.ubicacion, 'o_kf_ubi o_kf_ubi_lista', 22)); }   // v1.4
                $t.append($('<span class="o_kf_ref"/>').text(self._nombre(p.producto || p.ref)));   // v1.4.1: no el EAN
                if (p.variante) { $t.append($('<span class="o_kf_sub"/>').text(p.variante)); }
                if (self.out && self.out.lote_id) {
                    $t.append($('<span class="o_kf_sub"/>').text(p.out + ' · ' + p.tienda));
                }
                if (p.motivo) { $t.append($('<span class="o_kf_sub o_kf_rojo"/>').text(p.motivo)); }
                $b.append($t);
                $b.append($('<span class="o_kf_cant"/>').text(self._uds(p.pendiente) +
                    (p.leidas ? ' (' + self._uds(p.leidas) + ' leídas)' : '')));
                $ps.append($b);
            });
            if (this.filtro) {
                $ps.append($('<div class="o_kf_sub"/>').text('Solo se ven las de la ubicación o artículo leído. ' +
                    'Pulsa «Otro faltante» para ver todas.'));
            }
        }
        $ps.toggle(this.paso === 'lista');
        this.$('.o_kf_continuar').toggle(this.paso === 'lista')
            .prop('disabled', !this.marcadas.length)
            .text(this.marcadas.length ? 'Continuar (' + this.marcadas.length + ')' : 'Marca lo que no encuentras');

        // la linea que se esta resolviendo
        var $lin = this.$('.o_kf_linea').empty();
        var l = this.linea;
        if (l && this.paso === 'ubic') {
            $lin.append($('<div class="o_kf_sub o_kf_etq"/>').text('No está en'));
            $lin.append($('<div class="o_kf_vieja"/>').append(this._ubi(l.ubicacion, 'o_kf_vieja_ubi', 20))
                .append($('<span class="o_kf_vieja_uds"/>').text(this._uds(l.pendiente))));
            $lin.append($('<div class="o_kf_ref"/>').text(this._nombre(l.ref || l.producto)));   // v1.4.1: una vez
            if (l.variante) { $lin.append($('<div class="o_kf_producto"/>').text(l.variante)); }
            if (this.cola.length) {
                $lin.append($('<div class="o_kf_sub"/>').text('Después: ' + this.cola.length + ' más'));
            }
        }
        $lin.toggle(!!(l && this.paso === 'ubic'));

        // recomendacion (una) y, si se pide, las demas
        var $alt = this.$('.o_kf_alternativas').empty();
        var alts = (l && l.alternativas) || [];
        if (l && this.paso === 'ubic' && !l.motivo) {
            if (!alts.length) {
                $alt.append($('<div class="o_kf_fila o_kf_nadie"/>').text('No hay stock libre en ninguna otra ubicación'));
            } else {
                $alt.append($('<div class="o_kf_titulo"/>').text('Prueba en'));
                $alt.append($('<div class="o_kf_reco"/>')
                    .append(this._ubi(alts[0].nombre, 'o_kf_reco_ubi', 32))
                    .append($('<span class="o_kf_reco_uds"/>').text(this._uds(alts[0].libre) + ' libres')));
                if (alts.length > 1) {
                    $alt.append($('<a href="#" class="o_kf_vermas"/>').text(this.verMas ? 'Ocultar las demás' :
                        'Ver más ubicaciones (' + (l.alternativas_total || alts.length) + ')'));
                }
                if (this.verMas) {
                    alts.slice(1).forEach(function (a) {
                        $alt.append($('<div class="o_kf_fila"/>').append(self._ubi(a.nombre, 'o_kf_fila_ubi', 20))
                            .append($('<span/>').text(self._uds(a.libre))));
                    });
                }
            }
        }

        // resumen al acabar
        var $res = this.$('.o_kf_resumen').empty();
        if (_.contains(['fin', 'preguntar', 'validada'], this.paso) && this.hechos.length) {
            var reub = _.where(this.hechos, {tipo: 'reubicado'}).length;
            var falt = _.where(this.hechos, {tipo: 'sin_alternativa'}).length;
            $res.append($('<div/>').text(this.hechos.length + ' faltantes: ' + reub + ' reubicados, ' + falt + ' a FALTANTE'));
            _.where(this.hechos, {tipo: 'reubicado'}).forEach(function (h) {
                $res.append($('<div class="o_kf_sub"/>').text(h.ref + ': cógela en ' + h.ubicacion));
            });
        }
        $res.toggle(!!$res.children().length);
        if (this.paso === 'fin' && this.fin && this.fin.quedan) {
            $res.append($('<div class="o_kf_rojo"/>').text('Quedan ' + this.fin.quedan + ' líneas por coger: vuelve a la OUT.'));
            $res.show();
        }

        // botones
        var hayAlts = !!alts.length;
        var textoNada = this.confirmarNada ? 'Pulsa otra vez: no está en ninguna ubicación' :
            (hayAlts ? 'Tampoco está aquí' : 'No está en ninguna ubicación');
        this.$('.o_kf_nada').toggle(this.paso === 'ubic' && !!l && !l.motivo).text(textoNada)
            .toggleClass('o_kf_confirmar', this.confirmarNada);
        this.$('.o_kf_saltar_linea').toggle(this.paso === 'ubic' && !!l);
        var puedeValidar = this.paso === 'fin' && this.fin && this.fin.se_puede_validar && !(this.out && this.out.batch_id);
        this.$('.o_kf_validar').toggle(!!puedeValidar);
        this.$('.o_kf_si, .o_kf_no').toggle(this.paso === 'preguntar');
        this.$('.o_kf_explica').toggle(this.paso === 'preguntar');
        this.$('.o_kf_volver').toggle(!!this.out).text(this.paso === 'validada' ? 'Siguiente' :
            (this.out && this.out.batch_id ? 'Volver a la agrupación' : 'Volver a la OUT'));
        this.$('.o_kf_otro').toggle(!!this.out && _.contains(['fin', 'ubic'], this.paso) && !(this.fin && this.fin.error));
        this.$('.o_kf_codigo').attr('placeholder', {
            out: 'Escribir OUT y Enter', lista: 'Leer ubicación o EAN (opcional)', ubic: 'Leer ubicación y Enter',
            fin: 'Escribir OUT y Enter', preguntar: '', validada: ''}[this.paso] || '');
        this._ajustarUbis();
    },

    // ------------------------------------------------------------ v1.4: ubicación como en Preparación
    /** v1.4.1: '[2412PT25-000039-36] 2412PT25-000039-36' -> '2412PT25-000039-36' (sin el código repetido). */
    _nombre: function (texto) {
        return (texto || '').replace(/^\[[^\]]*\]\s*/, '');
    },

    /** 'L44 P17 C2 · KO_110626_032' -> hueco y KO en la misma línea y del mismo tamaño. */
    _ubi: function (texto, clase, max) {
        var $u = $('<span/>').addClass(clase).addClass('o_kf_ajustar').attr('data-max', max || 24);
        var partes = (texto || '').split(' · ');
        $u.append($('<span class="o_kf_hueco"/>').text(partes[0] || ''));
        if (partes.length > 1) { $u.append($('<span class="o_kf_ko"/>').text(partes.slice(1).join(' · '))); }
        return $u;
    },

    /** Baja la letra hasta que la ubicación cabe en una línea (mínimo 14 px). */
    _ajustarUbis: function () {
        this.$('.o_kf_ajustar').each(function () {
            var t = parseInt(this.getAttribute('data-max'), 10) || 24;
            this.style.fontSize = t + 'px';
            while (this.clientWidth && this.scrollWidth > this.clientWidth && t > 14) {
                t -= 1;
                this.style.fontSize = t + 'px';
            }
        });
    },
});

core.action_registry.add('koroshi_faltantes_pantalla', Pantalla);
return Pantalla;
});

odoo.define('koroshi_faltantes.BotonOperarios', function (require) {
'use strict';
/* Boton "Faltante" en la pantalla de Operarios (koroshi_operarios). Al volver de la OUT, regresa alli. */
var Operarios = require('koroshi_operarios.Pantalla');

Operarios.include({
    events: _.extend({}, Operarios.prototype.events, {
        'click .o_kf_abrir_faltante': '_onFaltante',
    }),
    _onFaltante: function () {
        // se pasa la OUT (o la agrupacion Z-, v1.3) que esta haciendo y el operario
        var actual = this.actual || null;
        var codigo = false;
        if (actual && actual.tipo === 'out') {
            codigo = actual.picking_name;
        } else if (actual && actual.tipo === 'agrupacion') {
            codigo = actual.ref;
        }
        return this.do_action('koroshi_faltantes.action_koroshi_faltantes_pantalla', {
            additional_context: {
                desde_operarios: true,
                faltante_out: codigo,
                faltante_operario: this.operario ? {id: this.operario.id, nombre: this.operario.nombre} : false,
            },
        });
    },
});
return Operarios;
});
