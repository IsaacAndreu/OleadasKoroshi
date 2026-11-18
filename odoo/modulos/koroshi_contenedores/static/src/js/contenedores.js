odoo.define('koroshi_contenedores.Pantalla', function (require) {
'use strict';
/* KOROSHI Contenedores v1.5.0 - mover contenedores KO_/TT_, compactar huecos y ver inventario por lineal.
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
var REPETIDA_MS = 700;
var PERSONA_MS = 180000;
var EN_ESPERA_MAX = 5;          // v1.4: lecturas guardadas mientras se espera a Odoo

function _e(t) { return _.escape(t == null ? '' : String(t)); }
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
        'click .o_kc_anadir': '_onAnadir',
        'click .o_kc_quitar_ultima': '_onQuitarUltima',
        'click .o_kc_guardar_anadir': '_onGuardarAnadir',
        'click .o_kc_cancelar_anadir': '_onCancelarAnadir',
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
        this.lecturasAnadir = [];       // v1.5: orden de lectura (para «Quitar la última»)
    },

    start: function () {
        var self = this;
        core.bus.on('barcode_scanned', this, this._onBarcodeScanned);
        return this._super.apply(this, arguments).then(function () {
            self.timer = setInterval(self._vigilar.bind(self), 10000);
            self._pintar();
            self._foco();
        });
    },

    destroy: function () {
        core.bus.off('barcode_scanned', this, this._onBarcodeScanned);
        clearInterval(this.timer);
        this._super.apply(this, arguments);
    },

    _vigilar: function () {
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
        if (conPersona) { this.persona = null; }
        this._pintar();
    },

    _foco: function () {
        var $c = this.$('.o_kc_codigo');
        if ($c.length && document.activeElement !== $c[0]) { $c.focus(); }
    },

    _onKeydown: function (ev) {
        if (ev.which === 13) {
            ev.preventDefault();
            var codigo = (ev.currentTarget.value || '').trim();
            ev.currentTarget.value = '';
            this._leer(codigo);
        }
    },

    _onBarcodeScanned: function (codigo) { this._leer(codigo); },

    _aviso: function (tipo, msg) {
        this.$('.o_kc_aviso').removeClass('o_kc_ok o_kc_mal o_kc_info').addClass(
            msg ? 'o_kc_' + (tipo || 'info') : '').text(msg || '');
    },

    // v1.4: al acabar una petición, la siguiente lectura que esperaba (si no ha empezado otra petición)
    _fin: function () {
        var self = this;
        this.ocupado = false;
        this.actividadEn = Date.now();
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

    _leer: function (codigo, deCola) {
        var self = this;
        codigo = (codigo || '').trim();
        if (!codigo) { return; }
        var t = Date.now();
        if (!deCola) {
            if (codigo === this.ultima.codigo && t - this.ultima.t < REPETIDA_MS) { return; }
            this.ultima = {codigo: codigo, t: t};
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
                self._pintar();
                self._aviso('ok', '✓ Movido. ' + m.msg);
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

    _hacerCero: function () {
        var self = this;
        if (this.ocupado || !this.detalle || !this.persona) { return; }
        this.ocupado = true;
        return this._rpc({route: '/koroshi/contenedores/cero', params: {
            contenedor_id: this.detalle.id, employee_id: this.persona.id, confirmado: true}}).then(function (m) {
            self._fin();
            self.confirmando = false;
            if (!m || !m.ok) {
                self._pitido(false);
                self._aviso('mal', (m && m.msg) || 'No se ha podido poner a cero.');
                self._pintar();
                return;
            }
            self.detalle = m.contenedor;
            self._aviso('ok', '✓ ' + m.msg + '. Ya se puede archivar.');
            self._pintar();
        }, self._sinConexion.bind(self));
    },

    // Añadir prendas: cada lectura es una prenda (1 ud) hasta «Guardar» o «Cancelar»
    _onAnadir: function () {
        if (!this.detalle || !this.persona) { return; }
        this.anadiendo = [];
        this.lecturasAnadir = [];
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
            self.lecturasAnadir.push(p.id);
            self._pitido(true);
            self._aviso('ok', '+1 ' + p.nombre);
            self._pintar();
        }, self._sinConexion.bind(self));
    },

    _onQuitarUltima: function () {
        if (!this.anadiendo || !this.lecturasAnadir.length) { return; }
        var id = this.lecturasAnadir.pop();
        var fila = _.findWhere(this.anadiendo, {id: id});
        if (fila) {
            fila.uds -= 1;
            if (fila.uds <= 0) { this.anadiendo = _.without(this.anadiendo, fila); }
            this._aviso('info', '−1 ' + fila.nombre);
        }
        this._pintar();
        this._foco();
    },

    _onCancelarAnadir: function () {
        this.anadiendo = null;
        this.lecturasAnadir = [];
        this._aviso('', 'No se ha añadido nada.');
        this._pintar();
        this._foco();
    },

    _onGuardarAnadir: function () {
        var self = this;
        if (this.ocupado || !this.detalle || !this.persona || !this.anadiendo || !this.anadiendo.length) { return; }
        this.ocupado = true;
        return this._rpc({route: '/koroshi/contenedores/anadir', params: {
            contenedor_id: this.detalle.id, employee_id: this.persona.id,
            lineas: this.anadiendo.map(function (f) { return {producto_id: f.id, uds: f.uds}; })}}).then(function (m) {
            self._fin();
            if (!m || !m.ok) {
                self._pitido(false);
                self._aviso('mal', (m && m.msg) || 'No se ha podido añadir.');
                return;
            }
            self.anadiendo = null;
            self.lecturasAnadir = [];
            self.detalle = m.contenedor;
            self._aviso('ok', '✓ ' + m.msg);
            self._pintar();
            self._foco();
        }, self._sinConexion.bind(self));
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
        var self = this;
        var id = parseInt($(ev.currentTarget).data('id'), 10);
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
        var html = '<button type="button" class="o_kc_volver_hueco">← Volver al hueco</button>' +
            '<div class="o_kc_card"><h3>' + _e(c.nombre) + '</h3><div class="o_kc_hueco">En: ' + _e(c.hueco) + '</div>';
        if (c.n_lineas) {
            html += '<div>' + c.n_lineas + ' ref. · ' + _n(c.uds) + ' uds' +
                (c.reservadas ? ' · <b>' + _n(c.reservadas) + ' reservadas</b>' : '') + '</div><table>' +
                c.lineas.map(function (l) {
                    return '<tr><td>' + _e(l.producto) + '</td><td class="o_kc_n">' + _n(l.uds) +
                        (l.reservadas ? ' (res. ' + _n(l.reservadas) + ')' : '') + '</td></tr>';
                }).join('') + (c.mas ? '<tr><td colspan="2">… y ' + c.mas + ' referencias más</td></tr>' : '') +
                '</table>';
        } else {
            html += '<div class="o_kc_vacio">Sin prendas en el sistema</div>';
        }
        if (this.anadiendo) {
            var total = _.reduce(this.anadiendo, function (s, f) { return s + f.uds; }, 0);
            html += '<div class="o_kc_anadir_caja"><b>Añadir a ' + _e(c.nombre) + ': lee cada prenda</b>';
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
                _n(c.uds) + ' uds saldrán del stock (ajuste de inventario, queda apuntado quién lo hace).</div>' +
                '<button type="button" class="o_kc_confirmar_si">Sí, vacío: poner a cero</button>' +
                '<button type="button" class="o_kc_confirmar_no">No</button></div>';
        } else {
            html += '<div class="o_kc_acciones">' +
                (c.n_lineas ? '<button type="button" class="o_kc_cero">Poner a cero</button>' : '') +
                '<button type="button" class="o_kc_anadir">Añadir prendas</button></div>';
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
        } else if (this.detalle) {
            paso = 'Contenedor: ponerlo a cero o añadir prendas';
        } else if (this.hueco) {
            paso = 'Compactar: marca y archiva los vacíos; mueve los que tienen prendas';
        } else if (this.lineal) {
            paso = 'Inventario del lineal: toca un hueco para abrirlo';
        } else {
            paso = '1. Escanea el contenedor (KO_…) para mover, una ubicación para limpiarla o escribe un lineal (L94)';
        }
        this.$('.o_kc_paso').text(paso);
        var html = this.conts.map(function (c) {
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
                '">Quitar</button><h3>' + _e(c.nombre) + '</h3><div class="o_kc_hueco">Ahora en: ' +
                _e(c.hueco) + '</div>' + cuerpo + '</div>';
        }).join('');
        this.$('.o_kc_lista').html(html);
        this.$('.o_kc_hueco_panel').html(this._pintarLineal() + this._pintarHueco() + this._pintarDetalle());
    },
});

core.action_registry.add('koroshi_contenedores_pantalla', Pantalla);
return Pantalla;
});
