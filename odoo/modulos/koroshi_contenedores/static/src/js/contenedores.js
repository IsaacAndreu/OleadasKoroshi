odoo.define('koroshi_contenedores.Pantalla', function (require) {
'use strict';
/* KOROSHI Contenedores v1.3.0 - mover contenedores KO_/TT_, limpiar huecos y ver inventario por lineal.
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
        if (this.persona && Date.now() - this.actividadEn > PERSONA_MS) {
            this._reiniciar(true);
            this._aviso('', 'Sesión cerrada por inactividad. Pasa tu tarjeta.');
        }
    },

    _reiniciar: function (conPersona) {
        this.conts = [];
        this.hueco = null;
        this.lineal = null;
        this.confirmando = false;
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

    _fin: function () { this.ocupado = false; this.actividadEn = Date.now(); },

    _sinConexion: function () { this._fin(); this._aviso('mal', 'Sin conexión con Odoo. Vuelve a probar.'); },

    _leer: function (codigo) {
        var self = this;
        codigo = (codigo || '').trim();
        if (!codigo || this.ocupado) { return; }
        var t = Date.now();
        if (codigo === this.ultima.codigo && t - this.ultima.t < REPETIDA_MS) { return; }
        this.ultima = {codigo: codigo, t: t};
        this.ocupado = true;
        return this._rpc({route: '/koroshi/contenedores/leer', params: {codigo: codigo}}).then(function (r) {
            self._fin();
            if (!r || !r.ok) {
                self._aviso('mal', (r && r.msg) || 'No se ha podido leer.');
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

    // ------------------------------------------------------------------ limpiar (con confirmación)
    _onArchivar: function () {
        if (this.ocupado || !this.hueco || !this.persona) { return; }
        this.confirmando = true;
        this._pintar();
    },

    _onConfirmarNo: function () {
        this.confirmando = false;
        this._pintar();
        this._foco();
    },

    _onConfirmarSi: function () {
        var self = this;
        if (this.ocupado || !this.hueco || !this.persona || !this.confirmando) { return; }
        this.ocupado = true;
        return this._rpc({route: '/koroshi/contenedores/limpiar', params: {
            ubicacion_id: this.hueco.id, employee_id: this.persona.id, confirmado: true}}).then(function (m) {
            self._fin();
            self.confirmando = false;
            if (!m || !m.ok) {
                self._aviso('mal', (m && m.msg) || 'No se ha podido limpiar.');
                self._pintar();
                return;
            }
            self.hueco = null;
            self._aviso(m.quedan ? 'info' : 'ok', (m.quedan ? '⚠ ' : '✓ ') + m.msg);
            self._refrescarLineal();
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

    _pintarHueco: function () {
        var h = this.hueco;
        if (!h) { return ''; }
        var vacios = _.where(h.contenedores, {vacio: true});
        var llenos = _.where(h.contenedores, {vacio: false});
        var html = '';
        if (this.lineal) {
            html += '<button type="button" class="o_kc_volver">← Volver al lineal ' + _e(this.lineal.codigo) + '</button>';
        }
        html += '<div class="o_kc_card"><h3>' + _e(h.nombre) + '</h3>';
        if (!h.contenedores.length) {
            html += '<div>Sin contenedores KO_/TT_: ya está limpia.</div>';
        }
        if (h.directo_n) {
            html += '<div class="o_kc_vacio">Hay ' + _n(h.directo_uds) + ' uds en el propio hueco (fuera de contenedores).</div>';
        }
        if (llenos.length) {
            html += '<div class="o_kc_vacio">Con stock (no se archivan: muévelos o regulariza):</div><table>' +
                llenos.map(function (c) {
                    return '<tr><td>' + _e(c.nombre) + '</td><td class="o_kc_n">' + c.n_lineas + ' ref. · ' +
                        _n(c.uds) + ' uds' + (c.reservadas ? ' (res. ' + _n(c.reservadas) + ')' : '') + '</td></tr>';
                }).join('') + '</table>';
        }
        if (vacios.length) {
            html += '<div>A cero (se pueden archivar):</div><table>' + vacios.map(function (c) {
                return '<tr><td>' + _e(c.nombre) + '</td><td class="o_kc_n">vacío</td></tr>';
            }).join('') + '</table>';
            if (this.confirmando) {
                html += '<div class="o_kc_confirmar"><div><b>¿Confirmas que esta ubicación está FÍSICAMENTE vacía?</b></div>' +
                    '<button type="button" class="o_kc_confirmar_si">Sí, está vacía: archivar ' + vacios.length + '</button>' +
                    '<button type="button" class="o_kc_confirmar_no">No</button></div>';
            } else {
                html += '<button type="button" class="o_kc_archivar">Archivar ' + vacios.length +
                    ' contenedor(es) vacío(s)</button>';
            }
        } else if (h.contenedores.length) {
            html += '<div>Ningún contenedor a cero: mueve antes lo que quede.</div>';
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
        } else if (this.hueco) {
            paso = 'Limpiar ubicación';
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
        this.$('.o_kc_hueco_panel').html(this._pintarLineal() + this._pintarHueco());
    },
});

core.action_registry.add('koroshi_contenedores_pantalla', Pantalla);
return Pantalla;
});
