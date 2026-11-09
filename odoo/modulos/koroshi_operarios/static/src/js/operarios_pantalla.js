odoo.define('koroshi_operarios.Pantalla', function (require) {
'use strict';
/* KOROSHI Operarios v2.0 - pantalla de la PDA dentro de Odoo (accion de cliente).
 *
 * - Tarjeta UNA vez: la PDA se queda con ese operario (guardado en el navegador) hasta que pulsa "Salir".
 * - Al leer la tarjeta se abre sola la primera OUT de su cola (/koroshi/operarios/siguiente).
 * - Al volver de la app de codigo de barras (validar o flecha atras):
 *     validada -> se abre sola la siguiente;  flecha atras -> se queda aqui con Continuar / Saltar / Faltante.
 * - Saltar: motivo -> oficina, final de su cola o fin de turno (sigue suya y la primera; la PDA se libera).
 * - Se puede seguir leyendo una OUT a mano (se le asigna si esta libre). Sin tarjeta, la OUT se abre igual pero
 *   no cuenta en productividad.
 * - Abre las OUT igual que el menu de codigo de barras (scan_from_main_menu) y las agrupaciones Z- con
 *   start_batch_processing. No cambia la app de codigo de barras.
 */
var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var session = require('web.session');

var REPETIDA_MS = 700;       // la misma lectura dos veces seguidas (bus + campo) cuenta una
var PREFIJOS_ZONA = ['Z-'];  // agrupaciones que se abren enteras (igual que models/tarea.py)

var Pantalla = AbstractAction.extend({
    contentTemplate: 'koroshi_operarios.Pantalla',
    events: {
        'keydown .o_ko_codigo': '_onKeydown',
        'click .o_ko_continuar': '_onContinuar',
        'click .o_ko_saltar': '_onSaltar',
        'click .o_ko_motivo': '_onMotivo',
        'click .o_ko_cancelar_salto': '_onCancelarSalto',
        'click .o_ko_salir': '_onSalir',
        'click .o_ko_menu': '_onMenu',
    },

    init: function () {
        this._super.apply(this, arguments);
        this.operario = null;      // {id, nombre}
        this.actual = null;        // asignacion que esta haciendo
        this.tarea = null;
        this.cola = [];
        this.motivos = [];
        this.ocupado = false;
        this.ultima = {codigo: '', t: 0};
    },

    start: function () {
        var self = this;
        core.bus.on('barcode_scanned', this, this._onBarcodeScanned);
        return this._super.apply(this, arguments).then(function () {
            self._pintarOperario();
            self._pintarAbiertas();
            self.timerAbiertas = setInterval(self._pintarAbiertas.bind(self), 60000);
            self._cargarMotivos();
            var guardado = self._guardado();
            if (guardado) {
                // la PDA ya tenia operario: se muestra lo suyo, sin abrir nada solo
                return self._rpc({route: '/koroshi/operarios/operario', params: {employee_id: guardado.id}})
                    .then(function (r) {
                        if (r && r.ok) {
                            self._ponerOperario(r.employee_id, r.operario);
                            return self._siguiente('no');
                        }
                        self._olvidarOperario();
                    });
            }
        });
    },

    on_attach_callback: function () {
        // vuelve de la app de codigo de barras (validada o flecha atras) o de la pantalla de Faltante
        this._super.apply(this, arguments);
        this.ocupado = false;
        this._pintarAbiertas();
        if (this.operario) {
            this._siguiente('si_nueva');
        }
        this._foco();
    },

    destroy: function () {
        core.bus.off('barcode_scanned', this, this._onBarcodeScanned);
        clearInterval(this.timerAbiertas);
        this._super.apply(this, arguments);
    },

    // ------------------------------------------------------------ operario guardado en la PDA
    _clave: function () {
        return 'koroshi_operarios_pda_' + (session.uid || '');
    },
    _guardado: function () {
        try {
            var v = window.localStorage.getItem(this._clave());
            return v ? JSON.parse(v) : null;
        } catch (e) { return null; }
    },
    _ponerOperario: function (id, nombre) {
        this.operario = {id: id, nombre: nombre};
        try { window.localStorage.setItem(this._clave(), JSON.stringify(this.operario)); } catch (e) { /* nada */ }
        this._pintarOperario();
    },
    _olvidarOperario: function () {
        this.operario = null;
        this.actual = null;
        this.tarea = null;
        this.cola = [];
        try { window.localStorage.removeItem(this._clave()); } catch (e) { /* nada */ }
        this._pintarOperario();
        this._pintarActual();
    },

    // ------------------------------------------------------------ lecturas
    _onBarcodeScanned: function (barcode) {
        if (!this.el || !$.contains(document, this.el)) {
            return;     // la pantalla no se ve (estan en la app de codigo de barras): no es para nosotros
        }
        this._leer(barcode);
    },

    _onKeydown: function (ev) {
        if (ev.key === 'Enter' || ev.keyCode === 13) {
            ev.preventDefault();
            var $i = this.$('.o_ko_codigo');
            var c = ($i.val() || '').trim();
            $i.val('');
            if (c) {
                if (this.$('.o_ko_salto').is(':visible')) { return this._saltarConNota(c); }
                this._leer(c);
            }
        }
    },

    _leer: function (codigo) {
        var self = this;
        codigo = (codigo || '').trim();
        var ahora = Date.now();
        if (!codigo || (codigo === this.ultima.codigo && ahora - this.ultima.t < REPETIDA_MS) || this.ocupado) {
            return;
        }
        this.ultima = {codigo: codigo, t: ahora};
        this.ocupado = true;
        return this._rpc({
            route: '/koroshi/operarios/leer',
            params: {codigo: codigo, employee_id: this.operario ? this.operario.id : false},
        }).then(function (r) {
            if (r && r.ok && r.que === 'tarjeta') {
                self.ocupado = false;
                self._ponerOperario(r.employee_id, r.operario);
                self._pitido(true);
                return self._siguiente('abrir');
            }
            if (r && !r.ok && !self.operario) {
                // sin tarjeta -> se abre igual, sin contar tiempo
                return self._abrirSinTarjeta(codigo);
            }
            if (!r || !r.ok) {
                self.ocupado = false;
                self._aviso((r && r.msg) || 'Error', 'mal');
                self._pitido(false);
                return;
            }
            // OUT leida a mano: pasa a ser la que hace
            self.actual = r.asignacion;
            self.tarea = r.tarea;
            self.cola = r.cola || [];
            self._pintarActual();
            self._pitido(true);
            self._aviso('Empezado ' + (r.asignacion ? r.asignacion.ref : codigo) + ' · abriendo...', 'ok');
            return self._abrir(r.tarea || r.asignacion);
        }).guardedCatch(function () {
            self.ocupado = false;
            self._aviso('Sin conexion con Odoo', 'mal');
            self._pitido(false);
        });
    },

    // ------------------------------------------------------------ cola
    _siguiente: function (abrir) {
        // abrir: 'abrir' (siempre), 'si_nueva' (solo si ha cambiado: la anterior esta validada), 'no'
        var self = this;
        if (!this.operario) { return Promise.resolve(); }
        this.ocupado = true;
        return this._rpc({route: '/koroshi/operarios/siguiente', params: {employee_id: this.operario.id}})
            .then(function (r) { return self._trasSiguiente(r, abrir); })
            .guardedCatch(function () {
                self.ocupado = false;
                self._aviso('Sin conexion con Odoo', 'mal');
            });
    },

    _trasSiguiente: function (r, abrir, previo) {
        this.ocupado = false;
        if (!r || !r.ok) {
            this._aviso((r && r.msg) || 'Error', 'mal');
            this._pitido(false);
            if (r && r.msg === 'Lee primero tu tarjeta') { this._olvidarOperario(); }
            return;
        }
        this.actual = r.asignacion;
        this.tarea = r.tarea;
        this.cola = r.cola || [];
        this._pintarActual();
        if (!r.asignacion) {
            this._aviso((previo ? previo + ' · ' : '') + (r.msg || 'No tienes más pedidos'), 'info');
            return;
        }
        if (abrir === 'abrir' || (abrir === 'si_nueva' && r.nueva)) {
            this._aviso((previo ? previo + ' · ' : '') + 'Abriendo ' + r.asignacion.ref + '...', 'ok');
            return this._abrir(r.tarea || r.asignacion);
        }
        this._aviso(previo || '', previo ? 'info' : '');
    },

    _onContinuar: function () {
        if (!this.actual || this.ocupado) { return; }
        this._aviso('Abriendo ' + this.actual.ref + '...', 'ok');
        return this._abrir(this.tarea || this.actual);
    },

    _abrir: function (obj) {
        // abre la OUT o la agrupacion en la app de codigo de barras, como si se leyera alli
        var self = this;
        var ref = obj.ref || obj.picking_name;
        var fallo = function (msg) {
            self.ocupado = false;
            self._aviso('No se ha podido abrir ' + ref + ': ' + msg + '. Pulsa Continuar o abrela desde el menú de código de barras.', 'mal');
        };
        var prom;
        this.ocupado = true;
        if (obj.tipo === 'agrupacion' && obj.batch_id) {
            prom = this._rpc({model: 'stock.picking.batch', method: 'start_batch_processing', args: [[obj.batch_id]]})
                .then(function (accion) {
                    if (!accion) { return fallo('la agrupación no devuelve pantalla'); }
                    return self.do_action(accion);
                });
        } else {
            prom = this._rpc({route: '/stock_barcode/scan_from_main_menu', params: {barcode: obj.picking_name || ref}})
                .then(function (res) {
                    if (res && res.action) { return self.do_action(res.action); }
                    return fallo((res && res.warning) || 'sin respuesta');
                });
        }
        return prom.then(function () { self.ocupado = false; }).guardedCatch(function () { fallo('error de Odoo'); });
    },

    _abrirSinTarjeta: function (codigo) {
        // OUT (o agrupacion) leida sin tarjeta: se abre como en el menu de codigo de barras y NO se crea tarea.
        var self = this;
        var fallo = function (msg) {
            self.ocupado = false;
            self._aviso(msg, 'mal');
            self._pitido(false);
        };
        var abrirLote = function (batchId) {
            return self._rpc({model: 'stock.picking.batch', method: 'start_batch_processing', args: [[batchId]]})
                .then(function (accion) {
                    if (!accion) { return fallo('La agrupación no devuelve pantalla'); }
                    return self.do_action(accion);
                });
        };
        var esZona = function (nombre) {
            return PREFIJOS_ZONA.some(function (p) { return (nombre || '').indexOf(p) === 0; });
        };
        this._aviso('Sin tarjeta: abriendo ' + codigo + ' (no cuenta en productividad)...', 'info');
        var prom = this._rpc({model: 'stock.picking', method: 'search_read',
                              args: [[['name', '=', codigo]], ['name', 'batch_id']], kwargs: {limit: 1}})
            .then(function (pk) {
                if (pk.length && pk[0].batch_id && esZona(pk[0].batch_id[1])) {
                    return abrirLote(pk[0].batch_id[0]);
                }
                if (pk.length) {
                    return self._rpc({route: '/stock_barcode/scan_from_main_menu', params: {barcode: pk[0].name}});
                }
                return self._rpc({model: 'stock.picking.batch', method: 'search_read',
                                  args: [[['name', '=', codigo]], ['name']], kwargs: {limit: 1}})
                    .then(function (lotes) {
                        if (lotes.length) { return abrirLote(lotes[0].id); }
                        return self._rpc({route: '/stock_barcode/scan_from_main_menu', params: {barcode: codigo}});
                    });
            })
            .then(function (res) {
                if (res && res.action) { return self.do_action(res.action); }
                if (res && res.warning) { return fallo(res.warning); }
            });
        return prom.then(function () { self.ocupado = false; })
            .guardedCatch(function () { fallo('No se ha podido abrir ' + codigo); });
    },

    // ------------------------------------------------------------ saltar
    _cargarMotivos: function () {
        var self = this;
        return this._rpc({route: '/koroshi/operarios/motivos', params: {}}).then(function (r) {
            self.motivos = (r && r.ok && r.motivos) || [];
        });
    },

    _onSaltar: function () {
        if (!this.actual || this.ocupado) { return; }
        var $m = this.$('.o_ko_salto_motivos').empty();
        this.motivoNota = null;
        this.motivos.forEach(function (m) {
            $('<button type="button" class="o_ko_motivo"/>').attr('data-id', m.id).text(m.nombre).appendTo($m);
        });
        this.$('.o_ko_salto_titulo').text('¿Por qué saltas ' + this.actual.ref + '?');
        this.$('.o_ko_salto').show();
        this.$('.o_ko_actual').hide();
    },

    _onCancelarSalto: function () {
        this.motivoNota = null;
        this.$('.o_ko_salto').hide();
        this._pintarActual();
        this.$('.o_ko_codigo').attr('placeholder', 'Escribir tarjeta o pedido y Enter');
    },

    _onMotivo: function (ev) {
        var id = parseInt($(ev.currentTarget).data('id'), 10);
        var m = _.findWhere(this.motivos, {id: id});
        if (!m || this.ocupado) { return; }
        if (m.pide_nota) {
            this.motivoNota = m;
            this.$('.o_ko_codigo').attr('placeholder', 'Escribe el motivo y Enter').focus();
            this._aviso('Escribe el motivo abajo y pulsa Enter', 'info');
            return;
        }
        return this._saltar(m, '');
    },

    _saltarConNota: function (texto) {
        if (!this.motivoNota) {
            this._aviso('Elige primero un motivo', 'mal');
            return;
        }
        return this._saltar(this.motivoNota, texto);
    },

    _saltar: function (motivo, nota) {
        var self = this;
        this.ocupado = true;
        return this._rpc({route: '/koroshi/operarios/saltar',
                          params: {employee_id: this.operario.id, motivo_id: motivo.id, nota: nota || ''}})
            .then(function (r) {
                self.ocupado = false;
                self.motivoNota = null;
                self.$('.o_ko_salto').hide();
                self.$('.o_ko_codigo').attr('placeholder', 'Escribir tarjeta o pedido y Enter');
                if (!r || !r.ok) {
                    self._pintarActual();
                    self._aviso((r && r.msg) || 'Error', 'mal');
                    self._pitido(false);
                    return;
                }
                self._pitido(true);
                if (r.destino === 'suya') {
                    // fin de turno: la PDA queda libre para el siguiente
                    var nombre = self.operario.nombre;
                    self._olvidarOperario();
                    self._aviso(r.msg + '. Hasta mañana, ' + nombre + '.', 'info');
                    return;
                }
                return self._trasSiguiente(r, 'abrir', r.msg_salto);
            }).guardedCatch(function () {
                self.ocupado = false;
                self._aviso('Sin conexion con Odoo', 'mal');
            });
    },

    _onSalir: function () {
        var nombre = this.operario ? this.operario.nombre : '';
        var pendiente = this.actual ? this.actual.ref : '';
        this._olvidarOperario();
        this._aviso(nombre ? ('Adiós, ' + nombre + (pendiente ? '. ' + pendiente + ' sigue siendo tuyo.' : '')) : '',
                    'info');
    },

    _onMenu: function () {
        this.do_action('stock_barcode.stock_barcode_action_main_menu');
    },

    // ------------------------------------------------------------ pintar
    _foco: function () {
        if (this.$('.o_ko_codigo').length && !('ontouchstart' in window)) {
            this.$('.o_ko_codigo').focus();
        }
    },

    _aviso: function (texto, clase) {
        var $a = this.$('.o_ko_aviso');
        $a.text(texto || '');
        $a.attr('class', 'o_ko_aviso o_ko_caja' + (texto ? ' o_ko_' + (clase || 'info') : ''));
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

    _pintarOperario: function () {
        var $q = this.$('.o_ko_quien');
        if (!this.operario) {
            $q.attr('class', 'o_ko_quien o_ko_caja o_ko_vacio').text('Lee tu tarjeta (o directamente la OUT)');
            this.$('.o_ko_salir').hide();
            return;
        }
        $q.attr('class', 'o_ko_quien o_ko_caja').text(this.operario.nombre);
        this.$('.o_ko_salir').show();
    },

    _pintarActual: function () {
        var $a = this.$('.o_ko_actual');
        var $c = this.$('.o_ko_cola').empty();
        if (!this.operario) {
            $a.hide();
            this.$('.o_ko_cola_titulo').hide();
            return;
        }
        if (this.actual) {
            this.$('.o_ko_actual_ref').text(this.actual.ref + (this.actual.tienda ? ' · ' + this.actual.tienda : ''));
            $a.show();
        } else {
            $a.hide();
        }
        var resto = this.cola.filter(function (x) { return !this.actual || x.id !== this.actual.id; }, this);
        this.$('.o_ko_cola_titulo').toggle(!!resto.length);
        resto.forEach(function (x) {
            $('<div class="o_ko_fila"/>').append($('<span/>').text(x.ref))
                .append($('<span/>').text(x.tienda || (x.tipo === 'agrupacion' ? 'Agrupación' : '')))
                .appendTo($c);
        });
    },

    _pintarAbiertas: function () {
        var self = this;
        return this._rpc({route: '/koroshi/operarios/estado', params: {}}).then(function (r) {
            if (!r || !r.ok) { return; }
            self.$('.o_ko_reloj').text(r.ahora);
            var $c = self.$('.o_ko_abiertas').empty();
            if (!r.abiertas.length) { $c.text('Nadie'); return; }
            r.abiertas.forEach(function (t) {
                var $f = $('<div class="o_ko_fila"/>');
                var $a = $('<span/>').append($('<b/>').text(t.operario))
                    .append(document.createTextNode(' · ' + t.ref + (t.tienda ? ' · ' + t.tienda : '')));
                $f.append($a).append($('<span/>').text(t.inicio));
                $c.append($f);
            });
        });
    },
});

core.action_registry.add('koroshi_operarios_pantalla', Pantalla);
return Pantalla;
});
