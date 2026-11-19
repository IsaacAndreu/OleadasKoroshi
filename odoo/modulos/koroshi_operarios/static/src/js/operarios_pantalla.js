odoo.define('koroshi_operarios.Pantalla', function (require) {
'use strict';
/* KOROSHI Operarios v2.3.0 - pantalla de la PDA dentro de Odoo (accion de cliente).
 *
 * v2.2: al entrar con el operario guardado (iniciar sesion, menu, recargar) la OUT se abre directamente; las 3
 * opciones solo salen al volver con la flecha atras sin validar. Grupo "KOROSHI Operarios: tarjeta obligatoria":
 * sin tarjeta no se abre nada (lo comprueba tambien el servidor en /koroshi/operarios/leer).
 * v2.2.2: en ese grupo, sin tarjeta la pantalla queda bloqueada: sin barra de Odoo y sin menu de codigo de barras.
 *
 * v2.3.0 (solo cambia el aspecto y la forma de usarla; la logica de colas es la misma):
 * - Tarjeta obligatoria sin operario: pantalla completa "Lee tu tarjeta". El campo sigue con foco pero no se ve;
 *   punto verde = lector preparado, gris + "Toca la pantalla" si pierde el foco. Una OUT sin tarjeta: aviso rojo.
 * - Cabecera "quien soy": iniciales con color sacado del nombre, nombre grande, contador del dia y Salir.
 * - Botones grandes: Continuar verde; Faltante (koroshi_faltantes) naranja y Saltar gris en una fila.
 * - Avisos ok / info / warn / mal con icono y boton de accion (Reintentar); los verdes se van a los 4 s.
 * - Salir y cambiar de operario con confirmacion en hoja inferior. Saltar: motivos como tarjetas en hoja inferior.
 * - "Abriendo X para Y" (no lee nada mientras abre) y "¡Hecho!" al volver con la OUT validada (siguiente en 3 s).
 * - Sin conexion: banda roja, no lee, reintenta cada 5 s. Sonido + vibracion con interruptor por PDA.
 * - Salida por inactividad: parametro koroshi_operarios.minutos_inactividad (0 = no).
 * - Menu (☰): en tarjeta obligatoria, pulsacion larga de 2 s.
 *
 * v2.15: recarga sola. /estado trae version_pantallas (huella de los modulos koroshi_* de la BD). La primera que
 *   llega es la de esta carga; si cambia (se ha actualizado un modulo), la PDA se recarga sola en un momento seguro:
 *   en Lecturas, sin hoja ni capa, sin nada escrito, con red y sin lecturas de koroshi_preparacion pendientes en la
 *   memoria. Si la PDA esta dentro de una OUT, espera a volver a Lecturas. Al recargar, el operario guardado abre
 *   su OUT como siempre.
 *
 * v2.20: tablero del responsable. La cola puede traer tarjetas de zona («lote»: la PDA recibe sus OUT una a una,
 *   no hace falta nada aquí) y notas («nota»: lo que pide el responsable). Una nota no abre nada: sale en «Estás
 *   haciendo» con el texto y el botón «Hecho, siguiente» (/koroshi/operarios/nota_hecha); Continuar, Saltar,
 *   Faltante y Pausa no salen con una nota.
 *
 * Se conserva lo que usa koroshi_faltantes: this.actual, this.operario, events como objeto, .o_ko_dejar.
 */
var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var session = require('web.session');

var REPETIDA_MS = 700;       // la misma lectura dos veces seguidas (bus + campo) cuenta una
var AVISO_OK_MS = 4000;      // los avisos verdes se van solos
var REINTENTO_MS = 5000;     // sin conexion: reintento
var CUENTA_HECHO = 3;        // segundos antes de abrir la siguiente
var MENU_LARGO_MS = 2000;    // pulsacion larga del menu en tarjeta obligatoria
var CLAVE_SONIDO = 'koroshi_operarios_sonido';
// v2.15: memoria de koroshi_preparacion (lecturas y caducadas pendientes de mandar): con algo dentro no se recarga
var CLAVES_PENDIENTES = ['koroshi_preparacion_cola', 'koroshi_preparacion_caducadas'];
var PLACEHOLDER = 'Escribir tarjeta o pedido y Enter';
var ICONOS = {ok: '✓', info: 'ℹ', warn: '⚠', mal: '✖'};
var DESTINOS = {oficina: 'Queda en expediciones', final: 'Va al final de tu cola', suya: 'Sigue siendo tuyo: fin de turno',
                libre: 'Lo hace otro: no te vuelve a salir (si ya lo dejó otro, a expediciones)', pausa: 'Sigue siendo tuyo: pausa'};   // v2.10

var Pantalla = AbstractAction.extend({
    contentTemplate: 'koroshi_operarios.Pantalla',
    // objeto plano: koroshi_faltantes hace _.extend({}, Operarios.prototype.events, {...})
    events: {
        'keydown .o_ko_codigo': '_onKeydown',
        'focus .o_ko_codigo': '_onFocoLector',
        'blur .o_ko_codigo': '_onFocoLector',
        'click .o_ko_bloqueo': '_onTocarBloqueo',
        'click .o_ko_lector': '_onTocarBloqueo',
        'click .o_ko_continuar': '_onContinuar',
        'click .o_ko_nota_hecha': '_onNotaHecha',        // v2.20
        'click .o_ko_saltar': '_onSaltar',
        'click .o_ko_pausa': '_onPausa',                 // v2.10
        'click .o_ko_motivo': '_onMotivo',
        'click .o_ko_confirmar_salto': '_onConfirmarSalto',
        'click .o_ko_cancelar_salto': '_onCancelarSalto',
        'keydown .o_ko_nota': '_onNotaKeydown',
        'input .o_ko_nota': '_onNotaInput',
        'click .o_ko_hoja_fondo': '_cerrarHoja',
        'click .o_ko_confirmar_si': '_onConfirmarSi',
        'click .o_ko_confirmar_no': '_cerrarHoja',
        'click .o_ko_salir': '_onSalir',
        'click .o_ko_menu': '_onMenu',
        'pointerdown .o_ko_menu': '_onMenuAbajo',
        'pointerup .o_ko_menu': '_onMenuArriba',
        'pointerleave .o_ko_menu': '_onMenuArriba',
        'pointercancel .o_ko_menu': '_onMenuArriba',
        'contextmenu .o_ko_menu': '_onMenuContextual',
        'click .o_ko_parar': '_onParar',
        'click .o_ko_sonido': '_onSonido',
        'click .o_ko_aviso_accion': '_onAvisoAccion',
        'pointerdown': '_marcarActividad',
        'keydown': '_marcarActividad',
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
        this.obligatoria = false;  // v2.2.2: usuario en el grupo "tarjeta obligatoria"
        // v2.3
        this.capa = null;          // 'abriendo' | 'hecho' | null
        this.sinRed = false;
        this.motivoElegido = null;
        this.confirmarAccion = null;
        this.minutosInactividad = 0;
        this.ultimaActividad = Date.now();
        this.versionBase = null;   // v2.15: version_pantallas de esta carga
        this.recargaPendiente = false;
        this.refHecho = null;      // ref de la OUT que estaba haciendo al irse a la app (para "¡Hecho!")
        this.sonido = this._leerSonido();
        this._enLinea = this._onEnLinea.bind(this);
        this._fueraDeLinea = this._onFueraDeLinea.bind(this);
    },

    willStart: function () {
        var self = this;
        var grupo = session.user_has_group('koroshi_operarios.grupo_tarjeta_obligatoria').then(function (v) {
            self.obligatoria = !!v;
        });
        return Promise.all([this._super.apply(this, arguments), grupo]);
    },

    start: function () {
        var self = this;
        core.bus.on('barcode_scanned', this, this._onBarcodeScanned);
        window.addEventListener('online', this._enLinea);
        window.addEventListener('offline', this._fueraDeLinea);
        return this._super.apply(this, arguments).then(function () {
            $('body').addClass('o_ko_en_lecturas');   // v2.6: en PDA (pantalla estrecha) sin la barra de Odoo
            self._pintarSonido();
            self._pintarOperario();
            self._pintarAbiertas();
            self.timerAbiertas = setInterval(self._pintarAbiertas.bind(self), 60000);
            self.timerInactividad = setInterval(self._comprobarInactividad.bind(self), 30000);
            self._cargarMotivos();
            var guardado = self._guardado();
            if (guardado) {
                // la PDA ya tenia operario: v2.2 abre directamente la OUT que esta haciendo o la siguiente.
                return self._rpc({route: '/koroshi/operarios/operario', params: {employee_id: guardado.id}})
                    .then(function (r) {
                        if (r && r.ok) {
                            self._ponerOperario(r.employee_id, r.operario);
                            // se abre en on_attach_callback (abrir otra accion desde start lia las migas de pan)
                            self.abrirAlEntrar = true;
                            return;
                        }
                        self._olvidarOperario();
                    }).guardedCatch(function () {
                        // sin red al entrar: se queda con el guardado y se reintenta
                        self.operario = {id: guardado.id, nombre: guardado.nombre};
                        self._sinConexion();
                    });
            }
        });
    },

    on_attach_callback: function () {
        // vuelve de la app de codigo de barras (validada o flecha atras) o de la pantalla de Faltante
        this._super.apply(this, arguments);
        $('body').addClass('o_ko_en_lecturas');   // v2.6
        this.ocupado = false;
        this._ocultarCapa();
        if (this._recargarSiToca()) { return; }   // v2.15: vuelve de una OUT y hay version nueva
        this._marcarActividad();
        this._pintarAbiertas();
        if (this.operario) {
            var modo = this.abrirAlEntrar ? 'abrir' : 'si_nueva';
            this.abrirAlEntrar = false;
            // v2.3: si vuelve con la OUT validada se ensena "¡Hecho!" con la siguiente
            this.refHecho = modo === 'si_nueva' && this.actual ? this.actual.ref : null;
            this._siguiente(modo);
        }
        this._pintarOperario();
        this._foco();
    },

    on_detach_callback: function () {
        $('body').removeClass('o_ko_en_lecturas');   // v2.6
        this._bloquear(false);
        this._pararCuenta();
        this._super.apply(this, arguments);
    },

    destroy: function () {
        $('body').removeClass('o_ko_en_lecturas');   // v2.6
        this._bloquear(false);
        core.bus.off('barcode_scanned', this, this._onBarcodeScanned);
        window.removeEventListener('online', this._enLinea);
        window.removeEventListener('offline', this._fueraDeLinea);
        clearInterval(this.timerAbiertas);
        clearInterval(this.timerInactividad);
        clearTimeout(this.timerReintento);
        clearTimeout(this.timerAviso);
        clearTimeout(this.timerMenu);
        this._pararCuenta();
        if (this.audio) { try { this.audio.close(); } catch (e) { /* nada */ } }
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
        this._marcarActividad();
        this._pintarOperario();
        this._pintarAbiertas();
    },
    _olvidarOperario: function () {
        this.operario = null;
        this.actual = null;
        this.tarea = null;
        this.cola = [];
        this.refHecho = null;
        try { window.localStorage.removeItem(this._clave()); } catch (e) { /* nada */ }
        this._cerrarHoja();
        this._ocultarCapa();
        this.$('.o_ko_dia').text('');
        this._pintarOperario();
        this._pintarActual();
        this._foco();
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
            if (c) { this._leer(c); }
        }
    },

    _leer: function (codigo, ayudar) {
        var self = this;
        codigo = (codigo || '').trim();
        var ahora = Date.now();
        if (!codigo || (codigo === this.ultima.codigo && ahora - this.ultima.t < REPETIDA_MS)) {
            return;
        }
        this.ultima = {codigo: codigo, t: ahora};
        this._marcarActividad();
        if (this.sinRed) {
            this._aviso('Sin conexión: no se ha leído ' + codigo + '. Espera a que vuelva.', 'mal');
            this._pitido(false);
            return;
        }
        // v2.3: mientras abre, con "¡Hecho!" o con una hoja abierta no se lee nada
        if (this.ocupado || this.capa || this.$('.o_ko_hoja').is(':visible')) {
            return;
        }
        this.ocupado = true;
        return this._rpc({
            route: '/koroshi/operarios/leer',
            params: {codigo: codigo, employee_id: this.operario ? this.operario.id : false, ayudar: !!ayudar},
        }).then(function (r) {
            if (r && r.ok && r.que === 'ayudar') {
                // v2.5: la OUT ya la hace otro -> se pregunta antes de entrar de ayudante
                self.ocupado = false;
                self._pitido(true);
                // v2.8: «¿Unirte a X?» en vez de «¿Ayudar a X?»
                return self._confirmar('¿Unirte a ' + r.titular + '?', r.msg + ' Tú harías la segunda mitad.',
                    'Sí, unirme', 'No', function () {
                        self.ultima = {codigo: '', t: 0};
                        self._leer(r.codigo, true);
                    });
            }
            if (r && r.ok && r.que === 'tarjeta') {
                self.ocupado = false;
                if (self.operario && self.operario.id !== r.employee_id) {
                    // v2.3: tarjeta de otro con uno dentro -> se pregunta
                    self._pitido(true);
                    return self._preguntarCambio(r);
                }
                self._ponerOperario(r.employee_id, r.operario);
                self._pitido(true);
                return self._siguiente('abrir');
            }
            if (r && !r.ok && !self.operario && !r.obligatoria) {
                // sin tarjeta -> se abre igual, sin contar tiempo (no para el grupo "tarjeta obligatoria")
                return self._abrirSinTarjeta(codigo);
            }
            if (r && r.obligatoria) {
                self.ocupado = false;
                self._aviso('Esto es un pedido. Primero tu tarjeta.', 'mal');
                self._pitido(false);
                return;
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
            if (r.ayudante && r.msg) { self._aviso(r.msg, 'info'); }   // v2.4: preparar a dos
            return self._abrir(r.tarea || r.asignacion);
        }).guardedCatch(function (e) {
            self.ocupado = false;
            self._falloRpc(e, function () { self.ultima = {codigo: '', t: 0}; self._leer(codigo); });
        });
    },

    _preguntarCambio: function (r) {
        var self = this;
        var actual = this.operario.nombre;
        var texto = actual + ' está dentro' + (this.actual ? ' con ' + this.actual.ref + ' (sigue siendo suyo).' : '.');
        this._confirmar('¿Cambiar a ' + r.operario + '?', texto, 'Sí, soy ' + r.operario, 'No, sigue ' + actual,
            function () {
                self.actual = null;
                self.tarea = null;
                self.cola = [];
                self._ponerOperario(r.employee_id, r.operario);
                self._aviso('Hola, ' + r.operario + '.', 'ok');
                return self._siguiente('abrir');
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
            .guardedCatch(function (e) {
                self.ocupado = false;
                self._falloRpc(e, function () { self._siguiente(abrir); });
            });
    },

    _trasSiguiente: function (r, abrir, previo) {
        this.ocupado = false;
        var hecho = this.refHecho;
        this.refHecho = null;
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
        if (r.msg_ayudante) { this._aviso(r.msg_ayudante, 'info'); }   // v2.5: ayudante puesto desde el reparto
        var nueva = abrir === 'abrir' || (abrir === 'si_nueva' && r.nueva);
        if (abrir === 'si_nueva' && hecho && (r.nueva || !r.asignacion) && (!r.asignacion || r.asignacion.ref !== hecho)) {
            // v2.3: vuelve con la OUT validada -> "¡Hecho!" y la siguiente en cuenta atras
            this._pitido(true);
            this._pintarAbiertas();
            return this._mostrarHecho(hecho, r.asignacion ? (r.tarea || r.asignacion) : null, r.msg);
        }
        if (!r.asignacion) {
            this._aviso((previo ? previo + ' · ' : '') + (r.msg || 'No tienes más pedidos'), 'info');
            return;
        }
        if (nueva) {
            if (previo) { this._aviso(previo, 'info'); }
            return this._abrir(r.tarea || r.asignacion);
        }
        this._aviso(previo || '', previo ? 'info' : '');
    },

    // v2.20: nota del tablero hecha -> se acaba y se le da lo siguiente (como al volver de una OUT validada)
    _onNotaHecha: function () {
        var self = this;
        if (!this.actual || this.actual.tipo !== 'nota' || !this.operario || this.ocupado || this.sinRed) { return; }
        this.ocupado = true;
        return this._rpc({route: '/koroshi/operarios/nota_hecha',
                          params: {employee_id: this.operario.id, asignacion_id: this.actual.id}})
            .then(function (r) {
                self._pitido(!!(r && r.ok));
                return self._trasSiguiente(r, 'abrir');
            })
            .guardedCatch(function (e) {
                self.ocupado = false;
                self._falloRpc(e, function () { self._onNotaHecha(); });
            });
    },

    _onContinuar: function () {
        if (!this.actual || this.ocupado || this.sinRed) { return; }
        return this._abrir(this.tarea || this.actual);
    },

    _abrir: function (obj) {
        // abre la OUT o la agrupacion en la app de codigo de barras, como si se leyera alli
        var self = this;
        if (obj && obj.tipo === 'nota') {
            // v2.20: una nota del tablero no se abre: se lee en la pantalla y se pulsa «Hecho, siguiente»
            this.ocupado = false;
            this._ocultarCapa();
            this._pintarActual();
            this._aviso('Tu responsable te pide: ' + (obj.texto || obj.ref || ''), 'info');
            return Promise.resolve();
        }
        var ref = obj.ref || obj.picking_name;
        var fallo = function (msg) {
            self.ocupado = false;
            self._ocultarCapa();
            self._aviso('No se ha podido abrir ' + ref + ': ' + msg + '. Pulsa Continuar o ábrela desde el menú de código de barras.', 'mal',
                        {texto: 'Reintentar', fn: function () { self._abrir(obj); }});
            self._pitido(false);
        };
        var prom;
        this.ocupado = true;
        this._mostrarAbriendo(ref, this.operario ? this.operario.nombre : '');
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
        return prom.then(function () { self.ocupado = false; }).guardedCatch(function (e) {
            if (self._esSinConexion(e)) {
                self.ocupado = false;
                self._ocultarCapa();
                return self._sinConexion();
            }
            fallo('error de Odoo');
        });
    },

    _abrirSinTarjeta: function (codigo) {
        // OUT (o agrupacion) leida sin tarjeta: se abre como en el menu de codigo de barras y NO se crea tarea.
        var self = this;
        var fallo = function (msg) {
            self.ocupado = false;
            self._ocultarCapa();
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
        // v2.3.1: los operarios no ven nada de productividad
        this._aviso('Sin tarjeta: abriendo ' + codigo + '. Lee tu tarjeta la próxima vez.', 'warn');
        this._mostrarAbriendo(codigo, '');
        var prom = this._rpc({model: 'stock.picking', method: 'search_read',
                              args: [[['name', '=', codigo]], ['name', 'batch_id']], kwargs: {limit: 1}})
            .then(function (pk) {
                if (pk.length) {   // v2.9: una OUT es solo esa OUT, aunque sea de una zona (Z-)
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
            .guardedCatch(function (e) {
                if (self._esSinConexion(e)) {
                    self.ocupado = false;
                    self._ocultarCapa();
                    return self._sinConexion();
                }
                fallo('No se ha podido abrir ' + codigo);
            });
    },

    // ------------------------------------------------------------ capa: abriendo / hecho
    _mostrarAbriendo: function (ref, para) {
        this._pararCuenta();
        this.capa = 'abriendo';
        this.$('.o_ko_abriendo_ref').text(ref || '');
        this.$('.o_ko_abriendo_para').text(para ? 'para ' + para : 'sin tarjeta');
        this.$('.o_ko_hecho').hide();
        this.$('.o_ko_abriendo').show();
        this.$('.o_ko_capa').removeClass('o_ko_capa_hecho').show();
    },

    _mostrarHecho: function (ref, siguiente, msg) {
        var self = this;
        this._pararCuenta();
        this.capa = 'hecho';
        this.siguienteHecho = siguiente;
        this.$('.o_ko_hecho_ref').text(ref + ' validado');
        this.$('.o_ko_abriendo').hide();
        if (siguiente) {
            this.$('.o_ko_hecho_sig_ref').text(siguiente.ref || siguiente.picking_name || '');
            this.$('.o_ko_hecho_sig_tienda').text(siguiente.tipo === 'nota' ? 'Tarea de tu responsable' :   // v2.20
                (siguiente.tienda || (siguiente.zona ? 'Zona ' + siguiente.zona : '')));
            this.$('.o_ko_hecho_siguiente').show();
            this.$('.o_ko_hecho_fin').hide();
            this.$('.o_ko_parar_texto').text('Parar aquí');
            var n = CUENTA_HECHO;
            this.$('.o_ko_cuenta_n').text(n);
            this.timerCuenta = setInterval(function () {
                n -= 1;
                self.$('.o_ko_cuenta_n').text(Math.max(n, 0));
                if (n <= 0) {
                    self._pararCuenta();
                    var obj = self.siguienteHecho;
                    self.siguienteHecho = null;
                    self._abrir(obj);
                }
            }, 1000);
        } else {
            this.$('.o_ko_hecho_siguiente').hide();
            this.$('.o_ko_hecho_fin').text(msg || 'No tienes más pedidos. Pide a tu responsable.').show();
            this.$('.o_ko_parar_texto').text('Vale');
        }
        this.$('.o_ko_hecho').show();
        this.$('.o_ko_capa').addClass('o_ko_capa_hecho').show();
    },

    _pararCuenta: function () {
        clearInterval(this.timerCuenta);
        this.timerCuenta = null;
    },

    _ocultarCapa: function () {
        this._pararCuenta();
        this.capa = null;
        this.$('.o_ko_capa').hide().removeClass('o_ko_capa_hecho');
    },

    _onParar: function () {
        var habia = !!this.siguienteHecho;
        this.siguienteHecho = null;
        this._ocultarCapa();
        if (habia) { this._aviso('Parado. Pulsa Continuar cuando quieras.', 'info'); }
        this._foco();
    },

    // ------------------------------------------------------------ saltar (hoja inferior)
    _cargarMotivos: function () {
        var self = this;
        return this._rpc({route: '/koroshi/operarios/motivos', params: {}}).then(function (r) {
            self.motivos = (r && r.ok && r.motivos) || [];
        }).guardedCatch(function () { /* se reintenta al abrir la hoja */ });
    },

    _onSaltar: function () {
        if (!this.actual || this.ocupado || this.sinRed) { return; }
        if (!this.motivos.length) { this._cargarMotivos(); }
        var $m = this.$('.o_ko_salto_motivos').empty();
        this.motivoElegido = null;
        this.motivos.forEach(function (m) {
            if (m.destino === 'pausa' || m.sin_caja) { return; }   // v2.10: la pausa tiene su botón; v2.17: «Sin caja», en la preparación
            var $b = $('<button type="button" class="o_ko_motivo"/>').attr('data-id', m.id);
            $('<span class="o_ko_marca" role="presentation"/>').appendTo($b);
            $('<span class="o_ko_motivo_txt"/>').text(m.nombre)
                .append($('<span class="o_ko_motivo_destino"/>').text(DESTINOS[m.destino] || ''))
                .appendTo($b);
            $b.appendTo($m);
        });
        if (!this.motivos.length) {
            $('<div class="o_ko_capa_sub"/>').text('No se han podido cargar los motivos. Cierra y vuelve a probar.').appendTo($m);
        }
        this.$('.o_ko_salto_titulo').text('¿Por qué saltas ' + this.actual.ref + '?');
        this.$('.o_ko_nota').val('');
        this.$('.o_ko_nota_caja').hide();
        this.$('.o_ko_confirmar').hide();
        this.$('.o_ko_salto').show();
        this._pintarBotonSalto();
        this._abrirHoja();
    },

    // v2.10: pausa (comer, café). Como «Fin de turno»: el tiempo se para, la PDA queda libre y al leer la tarjeta
    // la misma OUT sale la primera.
    _onPausa: function () {
        var self = this;
        if (!this.actual || this.ocupado || this.sinRed) { return; }
        var buscar = this.motivos.length ? Promise.resolve() : this._cargarMotivos();
        return buscar.then(function () {
            var m = _.findWhere(self.motivos, {destino: 'pausa'});
            if (!m) { return self._aviso('No se ha podido cargar la pausa. Vuelve a probar.', 'mal'); }
            self._confirmar('¿Pausa?', self.actual.ref + ' sigue siendo tuyo. Al volver, lee tu tarjeta y sale el primero.',
                            '⏸ Sí, pausa', 'No, volver', function () { return self._saltar(m, ''); });
        });
    },

    _onMotivo: function (ev) {
        var id = parseInt($(ev.currentTarget).data('id'), 10);
        var m = _.findWhere(this.motivos, {id: id});
        if (!m || this.ocupado) { return; }
        this.motivoElegido = m;
        this.$('.o_ko_motivo').removeClass('o_ko_elegido').attr('aria-pressed', 'false');
        $(ev.currentTarget).addClass('o_ko_elegido').attr('aria-pressed', 'true');
        this.$('.o_ko_nota_caja').toggle(!!m.pide_nota);
        if (m.pide_nota) { this.$('.o_ko_nota').focus(); }
        this._pintarBotonSalto();
    },

    _onNotaInput: function () { this._pintarBotonSalto(); },

    _onNotaKeydown: function (ev) {
        ev.stopPropagation();   // el Enter de la nota no es una lectura
        if (ev.key === 'Enter' || ev.keyCode === 13) {
            ev.preventDefault();
            this._onConfirmarSalto();
        }
    },

    _salteValido: function () {
        var m = this.motivoElegido;
        return !!m && (!m.pide_nota || !!(this.$('.o_ko_nota').val() || '').trim());
    },

    _pintarBotonSalto: function () {
        this.$('.o_ko_confirmar_salto').prop('disabled', !this._salteValido() || this.ocupado);
    },

    _onConfirmarSalto: function () {
        if (!this._salteValido() || this.ocupado) { return; }
        var m = this.motivoElegido;
        return this._saltar(m, m.pide_nota ? (this.$('.o_ko_nota').val() || '').trim() : '');
    },

    _onCancelarSalto: function () {
        this._cerrarHoja();
    },

    _saltar: function (motivo, nota) {
        var self = this;
        this.ocupado = true;
        this._pintarBotonSalto();
        return this._rpc({route: '/koroshi/operarios/saltar',
                          params: {employee_id: this.operario.id, motivo_id: motivo.id, nota: nota || ''}})
            .then(function (r) {
                self.ocupado = false;
                self.motivoElegido = null;
                self._cerrarHoja();
                if (!r || !r.ok) {
                    self._pintarActual();
                    self._aviso((r && r.msg) || 'Error', 'mal');
                    self._pitido(false);
                    return;
                }
                self._pitido(true);
                if (r.destino === 'suya' || r.destino === 'pausa') {
                    // fin de turno (v2.10: o pausa): la PDA queda libre para el siguiente
                    var nombre = self.operario.nombre;
                    self._olvidarOperario();
                    self._aviso(r.destino === 'pausa' ? '⏸ Pausa, ' + nombre + '. ' + r.msg + '.' :
                                r.msg + '. Hasta mañana, ' + nombre + '.', 'info');
                    return;
                }
                return self._trasSiguiente(r, 'abrir', r.msg_salto);
            }).guardedCatch(function (e) {
                self.ocupado = false;
                self._pintarBotonSalto();
                self._falloRpc(e);
            });
    },

    // ------------------------------------------------------------ hoja inferior / confirmar
    _abrirHoja: function () {
        this.$('.o_ko_hoja').show();
        var $p = this.$('.o_ko_hoja_panel');
        setTimeout(function () { $p.find('button:not(:disabled)').first().focus(); }, 0);
    },

    _cerrarHoja: function () {
        this.motivoElegido = null;
        this.confirmarAccion = null;
        this.$('.o_ko_hoja').hide();
        this.$('.o_ko_salto').hide();
        this.$('.o_ko_confirmar').hide();
        this._foco();
    },

    _confirmar: function (titulo, texto, si, no, accion, aviso) {
        this.confirmarAccion = accion;
        this.$('.o_ko_salto').hide();
        this.$('.o_ko_confirmar_titulo').text(titulo);
        var $t = this.$('.o_ko_confirmar_texto').empty();
        if (aviso) { $('<div class="o_ko_warn_txt"/>').text('⚠ ' + aviso).appendTo($t); }
        if (texto) { $('<div/>').text(texto).appendTo($t); }
        this.$('.o_ko_confirmar_si').text(si);
        this.$('.o_ko_confirmar_no').text(no);
        this.$('.o_ko_confirmar').show();
        this._abrirHoja();
    },

    _onConfirmarSi: function () {
        var accion = this.confirmarAccion;
        this._cerrarHoja();
        if (accion) { accion(); }
    },

    // ------------------------------------------------------------ salir / menu
    _onSalir: function () {
        if (!this.operario) { return; }
        var self = this;
        var nombre = this.operario.nombre;
        var aviso = this.actual ? 'Dejas ' + this.actual.ref + ' a medias: sigue siendo tuyo y será el primero al volver.' : '';
        this._confirmar('¿Salir, ' + nombre + '?', 'La PDA queda libre para otro operario.', 'Sí, salir', 'No, seguir',
                        function () {
                            self._salirYa();
                            // v2.7: a la pantalla de inicio de Odoo (todas las apps); se vuelve con «Lecturas (PDA)»
                            self.trigger_up('show_home_menu');
                        }, aviso);
    },

    _salirYa: function (porque) {
        var nombre = this.operario ? this.operario.nombre : '';
        var pendiente = this.actual ? this.actual.ref : '';
        this._olvidarOperario();
        if (!nombre) { return; }
        var texto = porque === 'inactividad' ? 'Salida automática por inactividad: ' + nombre + '.' : 'Adiós, ' + nombre + '.';
        this._aviso(texto + (pendiente ? ' ' + pendiente + ' sigue siendo tuyo.' : ''), 'info');
    },

    _onMenu: function (ev) {
        if (this.obligatoria) {
            // v2.3: en tarjeta obligatoria solo con pulsacion larga (_onMenuAbajo)
            if (ev) { ev.preventDefault(); }
            if (!this.menuLargo) { this._aviso('Mantén pulsado ☰ 2 segundos para ir al menú.', 'info'); }
            this.menuLargo = false;
            return;
        }
        this._irMenu();
    },

    _irMenu: function () {
        if (this.obligatoria && !this.operario) {
            return this._aviso('Lee primero tu tarjeta.', 'mal');
        }
        this.do_action('stock_barcode.stock_barcode_action_main_menu');
    },

    _onMenuAbajo: function () {
        if (!this.obligatoria) { return; }
        var self = this;
        clearTimeout(this.timerMenu);
        this.menuLargo = false;
        this.$('.o_ko_menu').addClass('o_ko_cargando');
        this.timerMenu = setTimeout(function () {
            self.menuLargo = true;
            self.$('.o_ko_menu').removeClass('o_ko_cargando');
            self._vibrar(60);
            self._irMenu();
        }, MENU_LARGO_MS);
    },

    _onMenuArriba: function () {
        clearTimeout(this.timerMenu);
        this.$('.o_ko_menu').removeClass('o_ko_cargando');
    },

    _onMenuContextual: function (ev) { ev.preventDefault(); },

    // ------------------------------------------------------------ inactividad
    _marcarActividad: function () {
        this.ultimaActividad = Date.now();
    },

    _comprobarInactividad: function () {
        if (!this.minutosInactividad || !this.operario || this.capa) { return; }
        if (!this.el || !$.contains(document, this.el)) { return; }   // en la app de codigo de barras: no
        if (Date.now() - this.ultimaActividad >= this.minutosInactividad * 60000) {
            this._salirYa('inactividad');
        }
    },

    // ------------------------------------------------------------ sin conexion
    _esSinConexion: function (e) {
        if (!navigator.onLine) { return true; }
        var err = e && (e.message || e);
        if (!err) { return false; }
        if (err.code === -32098) { return true; }
        var tipo = err.data && err.data.type;
        return !!(tipo && String(tipo).indexOf('xhr') === 0);
    },

    _falloRpc: function (e, reintentar) {
        if (e && e.event && e.event.preventDefault) { e.event.preventDefault(); }   // sin dialogo de Odoo
        if (this._esSinConexion(e)) { return this._sinConexion(); }
        this._ocultarCapa();
        var err = e && (e.message || e);
        var msg = (err && err.data && err.data.message) || (err && err.message) || 'Error de Odoo';
        this._aviso(msg, 'mal', reintentar ? {texto: 'Reintentar', fn: reintentar} : null);
        this._pitido(false);
    },

    _sinConexion: function () {
        var self = this;
        if (!this.sinRed) {
            this.sinRed = true;
            this.$el.addClass('o_ko_sin_red');
            this.$('.o_ko_offline').show();
            this._pitido(false);
        }
        clearTimeout(this.timerReintento);
        this.timerReintento = setTimeout(function () { self._probarConexion(); }, REINTENTO_MS);
    },

    _probarConexion: function () {
        var self = this;
        if (!this.sinRed) { return; }
        return this._rpc({route: '/koroshi/operarios/estado', params: {}}, {shadow: true})
            .then(function (r) {
                if (r && r.ok) { return self._conexionVuelta(); }
                self._sinConexion();
            }).guardedCatch(function (e) {
                if (e && e.event && e.event.preventDefault) { e.event.preventDefault(); }
                self._sinConexion();
            });
    },

    _conexionVuelta: function () {
        clearTimeout(this.timerReintento);
        this.sinRed = false;
        this.$el.removeClass('o_ko_sin_red');
        this.$('.o_ko_offline').hide();
        this.ocupado = false;
        this._aviso('Conexión recuperada. Ya puedes leer.', 'ok');
        this._pitido(true);
        this._pintarAbiertas();
        if (!this.motivos.length) { this._cargarMotivos(); }
        if (this.operario) { this._siguiente('no'); }
    },

    _onEnLinea: function () {
        if (this.sinRed) { this._probarConexion(); }
    },

    _onFueraDeLinea: function () {
        this._sinConexion();
    },

    // ------------------------------------------------------------ pintar
    _foco: function () {
        var $i = this.$('.o_ko_codigo');
        if (!$i.length) { return; }
        // en bloqueo el campo es invisible y no saca teclado (inputmode=none): siempre con foco
        if (this._enBloqueo() || !('ontouchstart' in window)) {
            $i.focus();
        }
        this._estadoLector();
    },

    _enBloqueo: function () {
        return this.obligatoria && !this.operario;
    },

    _onFocoLector: function (ev) {
        var self = this;
        if (ev.type === 'focusout' || ev.type === 'blur') {
            // en bloqueo se recupera el foco (salvo que se este escribiendo la nota de una hoja)
            setTimeout(function () {
                if (self._enBloqueo() && self.el && $.contains(document, self.el) && !self.$('.o_ko_hoja').is(':visible')) {
                    self.$('.o_ko_codigo').focus();
                }
                self._estadoLector();
            }, 50);
            return;
        }
        this._estadoLector();
    },

    _onTocarBloqueo: function () {
        this.$('.o_ko_codigo').focus();
        this._estadoLector();
    },

    _estadoLector: function () {
        var listo = !!this.el && document.activeElement === this.$('.o_ko_codigo')[0];
        this.$('.o_ko_lector').toggleClass('o_ko_listo', listo);
        this.$('.o_ko_lector_texto').text(listo ? 'Lector preparado' : 'Toca la pantalla');
    },

    _aviso: function (texto, clase, accion) {
        var self = this;
        clearTimeout(this.timerAviso);
        var $a = this.$('.o_ko_aviso').empty();
        var tipo = clase || 'info';
        this.avisoAccion = null;
        $a.attr('class', 'o_ko_aviso' + (texto ? ' o_ko_' + tipo : ''));
        var $b = this.$('.o_ko_bloqueo_aviso');
        if (!texto) {
            $b.attr('class', 'o_ko_bloqueo_aviso').text('');
            return;
        }
        $('<span class="o_ko_aviso_icono" role="presentation"/>').text(ICONOS[tipo] || ICONOS.info).appendTo($a);
        $('<span class="o_ko_aviso_texto"/>').text(texto).appendTo($a);
        if (accion) {
            this.avisoAccion = accion.fn;
            $('<button type="button" class="o_ko_aviso_accion"/>').text(accion.texto).appendTo($a);
        }
        // en la pantalla bloqueada solo se ven los rojos y los verdes
        if (this._enBloqueo() && (tipo === 'mal' || tipo === 'ok')) {
            $b.attr('class', 'o_ko_bloqueo_aviso o_ko_' + tipo).text((ICONOS[tipo] || '') + ' ' + texto);
        } else {
            $b.attr('class', 'o_ko_bloqueo_aviso').text('');
        }
        if (tipo === 'ok') {
            this.timerAviso = setTimeout(function () { self._aviso('', ''); }, AVISO_OK_MS);
        }
    },

    _onAvisoAccion: function () {
        var fn = this.avisoAccion;
        this._aviso('', '');
        if (fn) { fn(); }
    },

    // ------------------------------------------------------------ sonido y vibracion
    _leerSonido: function () {
        try { return window.localStorage.getItem(CLAVE_SONIDO) !== '0'; } catch (e) { return true; }
    },

    _onSonido: function () {
        this.sonido = !this.sonido;
        try { window.localStorage.setItem(CLAVE_SONIDO, this.sonido ? '1' : '0'); } catch (e) { /* nada */ }
        this._pintarSonido();
        if (this.sonido) { this._pitido(true); }
        this._aviso(this.sonido ? 'Sonido y vibración activados' : 'Sonido y vibración desactivados', 'ok');
    },

    _pintarSonido: function () {
        this.$('.o_ko_sonido').toggleClass('o_ko_mudo', !this.sonido).text(this.sonido ? '🔊' : '🔇')
            .attr('aria-pressed', this.sonido ? 'true' : 'false');
    },

    _vibrar: function (patron) {
        // sin un toque/tecla previo Chrome bloquea vibrate y saca un error en consola: solo si ya hubo interaccion
        try {
            var activo = !navigator.userActivation || navigator.userActivation.hasBeenActive;
            if (this.sonido && activo && navigator.vibrate) { navigator.vibrate(patron); }
        } catch (e) { /* nada */ }
    },

    _pitido: function (bien) {
        this._vibrar(bien ? 80 : [120, 80, 120]);
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
            o.stop(ctx.currentTime + (bien ? 0.12 : 0.4));
        } catch (e) { /* sin sonido */ }
    },

    // v2.2.2: grupo "tarjeta obligatoria" sin operario -> sin barra de Odoo ni menu de codigo de barras
    _bloquear: function (si) {
        $('body').toggleClass('o_ko_bloqueado', !!si);
    },

    _iniciales: function (nombre) {
        var partes = (nombre || '').trim().split(/\s+/).filter(Boolean);
        if (!partes.length) { return '?'; }
        var ini = partes[0].charAt(0) + (partes.length > 1 ? partes[partes.length - 1].charAt(0) : (partes[0].charAt(1) || ''));
        return ini.toUpperCase();
    },

    _colorNombre: function (nombre) {
        var h = 0;
        for (var i = 0; i < (nombre || '').length; i++) { h = (h * 31 + nombre.charCodeAt(i)) % 360; }
        return 'hsl(' + h + ', 55%, 32%)';   // oscuro: texto blanco con buen contraste
    },

    _pintarOperario: function () {
        var $q = this.$('.o_ko_quien');
        var bloqueado = this._enBloqueo();
        this._bloquear(bloqueado && this.el && $.contains(document, this.el));
        this.$el.toggleClass('o_ko_modo_bloqueo', bloqueado);
        this.$('.o_ko_bloqueo').toggle(bloqueado);
        this.$('.o_ko_codigo').attr('inputmode', bloqueado ? 'none' : null)
            .attr('placeholder', PLACEHOLDER);
        this.$('.o_ko_menu').toggle(!bloqueado);
        var $av = this.$('.o_ko_avatar');
        if (!this.operario) {
            $q.attr('class', 'o_ko_quien o_ko_vacio')
                .text(this.obligatoria ? 'Lee tu tarjeta' : 'Lee tu tarjeta (o directamente la OUT)');
            $av.text('?').css('background-color', '');
            this.$('.o_ko_salir').hide();
        } else {
            $q.attr('class', 'o_ko_quien').text(this.operario.nombre);
            $av.text(this._iniciales(this.operario.nombre)).css('background-color', this._colorNombre(this.operario.nombre));
            this.$('.o_ko_salir').show();
        }
        if (bloqueado) { this._foco(); } else { this._estadoLector(); }
    },

    _dato: function (texto, clase) {
        return $('<span class="o_ko_dato"/>').addClass(clase || '').text(texto);
    },

    _pintarActual: function () {
        var self = this;
        var $a = this.$('.o_ko_actual');
        var $c = this.$('.o_ko_cola').empty();
        if (!this.operario) {
            $a.hide();
            this.$('.o_ko_cola_titulo').hide();
            return;
        }
        if (this.actual) {
            var x = this.actual;
            var t = this.tarea || {};
            this.$('.o_ko_actual_ref').text(x.ref);
            this.$('.o_ko_actual_tienda').text(x.tienda || (x.tipo === 'agrupacion' ? 'Agrupación' : ''));
            // v2.20: nota del tablero: el texto, «Hecho, siguiente» y nada más
            var esNota = x.tipo === 'nota';
            this.$('.o_ko_actual_sub').text(esNota ? 'Tu responsable te pide' : 'Estás haciendo');
            this.$('.o_ko_continuar, .o_ko_botonera, .o_ko_pausa').toggle(!esNota);
            this.$('.o_ko_nota_hecha').toggle(esNota);
            var $d = this.$('.o_ko_datos').empty();
            var zona = x.zona || t.zona;
            if (zona) { $d.append(this._dato('Zona ' + zona, 'o_ko_zona')); }
            if (x.lineas) { $d.append(this._dato(x.lineas + (x.lineas === 1 ? ' línea' : ' líneas'))); }
            if (x.uds) { $d.append(this._dato(x.uds + ' uds')); }
            // v2.3.1: sin minutos (los operarios no ven nada de productividad)
            if (x.uds) {
                var hechas = Math.min(x.hechas || 0, x.uds);
                var pct = Math.round(100 * hechas / x.uds);
                this.$('.o_ko_barra_lleno').css('width', pct + '%');
                this.$('.o_ko_progreso_texto').text(hechas + ' de ' + x.uds + ' uds leídas (' + pct + ' %)');
                this.$('.o_ko_progreso').show();
            } else {
                this.$('.o_ko_progreso').hide();
            }
            $a.show();
        } else {
            $a.hide();
        }
        var resto = this.cola.filter(function (y) { return !self.actual || y.id !== self.actual.id; });
        this.$('.o_ko_cola_titulo').toggle(!!resto.length);
        resto.forEach(function (y) {
            var $txt = $('<span class="o_ko_cola_txt"/>')
                .append($('<span class="o_ko_cola_ref"/>').text(y.ref))
                .append($('<span class="o_ko_cola_tienda"/>').text(y.tienda || ({agrupacion: 'Agrupación',
                    lote: 'Zona: sus OUT una a una', nota: 'Tarea de tu responsable'}[y.tipo] || '')));   // v2.20
            var $extra = $('<span class="o_ko_cola_extra"/>');
            if (y.zona) { $extra.append(self._dato(y.zona, 'o_ko_zona')); }
            if (y.uds) { $extra.append(self._dato(y.uds + ' uds')); }
            $('<li/>').append($txt).append($extra).appendTo($c);
        });
    },

    // v2.15: recarga sola cuando se ha actualizado un modulo koroshi_*
    _mirarVersion: function (version) {
        if (!version) { return; }   // servidor sin la v2.15
        if (!this.versionBase) { this.versionBase = version; return; }
        if (version !== this.versionBase) {
            this.recargaPendiente = true;
            this._recargarSiToca();
        }
    },

    _hayPendientes: function () {
        try {
            return CLAVES_PENDIENTES.some(function (k) {
                var v = JSON.parse(window.localStorage.getItem(k) || '{}') || {};
                return Object.keys(v).length > 0;
            });
        } catch (e) {
            return true;   // si no se puede leer la memoria, mejor no recargar
        }
    },

    _recargarSiToca: function () {
        if (!this.recargaPendiente) { return false; }
        var enLecturas = $('body').hasClass('o_ko_en_lecturas') && this.el && $.contains(document, this.el);
        var escrito = (this.$('.o_ko_codigo').val() || '').trim();
        if (!enLecturas || this.ocupado || this.capa || this.sinRed || navigator.onLine === false ||
                this.$('.o_ko_hoja').is(':visible') || escrito || this._hayPendientes()) {
            return false;
        }
        this.recargaPendiente = false;
        window.location.reload();
        return true;
    },

    _pintarAbiertas: function () {
        var self = this;
        return this._rpc({route: '/koroshi/operarios/estado',
                          params: {employee_id: this.operario ? this.operario.id : false}}, {shadow: true})
            .then(function (r) {
                if (!r || !r.ok) { return; }
                self.$('.o_ko_reloj').text(r.ahora);
                self.minutosInactividad = r.minutos_inactividad || 0;
                self._mirarVersion(r.version_pantallas);   // v2.15
                var n = r.n_operarios !== undefined ? r.n_operarios : r.abiertas.length;
                self.$('.o_ko_n_operarios').text('(' + n + ')');
                // v2.3.1: sin contador del día (pedidos / uds): los operarios no ven nada de productividad
                self.$('.o_ko_dia').text('');
                var $c = self.$('.o_ko_abiertas').empty();
                if (!r.abiertas.length) { $c.text('Nadie'); return; }
                r.abiertas.forEach(function (t) {
                    var $f = $('<div class="o_ko_fila"/>');
                    var $a = $('<span/>').append($('<b/>').text(t.operario))
                        .append(document.createTextNode(' · ' + t.ref + (t.tienda ? ' · ' + t.tienda : '')));
                    $f.append($a).append($('<span/>').text(t.inicio));
                    $c.append($f);
                });
            }).guardedCatch(function (e) {
                if (e && e.event && e.event.preventDefault) { e.event.preventDefault(); }
                if (self._esSinConexion(e)) { self._sinConexion(); }
            });
    },
});

core.action_registry.add('koroshi_operarios_pantalla', Pantalla);
return Pantalla;
});
