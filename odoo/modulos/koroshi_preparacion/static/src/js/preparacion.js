odoo.define('koroshi_preparacion.Pantalla', function (require) {
'use strict';
/* KOROSHI Preparación en Lecturas v3.2.0 - pantalla para preparar una OUT suelta sin salir de Lecturas.
 * v3.29: ROBUSTEZ. Una caja cerrada sin conexión que Odoo no acepta PARA la cola (antes la caja siguiente se llevaba
 * sus uds): la PDA pide otra etiqueta, «Probar otra vez» o «Dejar lo leído fuera de caja». Mover, deshacer y validar
 * van con id y tiempo máximo y se reintentan solos (no se hacen dos veces); validar contesta «validada» si ya lo
 * estaba. Lo de la cola que Odoo rechaza o lleva más de 24 h en la PDA queda apuntado para el encargado. Al volver la
 * conexión, si la OUT ya está hecha se vuelve a Lecturas. El estado ligero ya no trae lo fijo (se mezcla con el que
 * hay).
 * v3.26: «⏸ Pausa (comer, café)» en el menú ☰ (dos toques): como la pausa de Lecturas, sin salir antes.
 * v3.24.1: se lee la CJ y luego se toca qué caja es (o al revés); ninguna marcada de entrada. Botones grandes.
 * v3.24: tipo de caja (Consumibles): al cerrar una caja el operario elige Grande / 60x40x40 / Mediana / Online…
 * (se recuerda por operario). Odoo pone ese «Tipo de paquete» a la caja y resta 1 en Consumibles. Zalando / About
 * You: «Caja» enseña los tipos y tocar uno cierra la caja.
 * v3.22: «Caja» también sin red: la caja se cierra en la PDA (lo leído pasa a ella) y va a la cola, en su sitio, con
 * las lecturas; Odoo la cierra al volver la conexión. Zalando / About You: «S<n>» para apuntar y luego su PACK.
 * v3.15: también una agrupación de zona (Z-) entera, en un solo recorrido: las líneas de todas sus OUT en el orden de
 * la ruta, cada una con su caja de tienda («CAJA 05 · K34 ...», banda amarilla). Leer una CJ cierra la caja de la
 * tienda de esa etiqueta (no hace falta pulsar «Caja»). Validar valida cada OUT. La PDA manda lote_id en vez de
 * picking_id; la memoria de la PDA guarda la cola con la clave 'L<id>'.
 * v3.7: leer una ubicación lleva a su línea; «Poner cantidad» (varias uds de golpe tras leer una con la pistola);
 * notas de la OUT arriba; los códigos de barras alternativos también cuentan al momento; «Imprimir» abre otra vez la
 * etiqueta de caja (OUT + matrícula), la del transportista o el albarán.
 * v3.6: no se queda colgada si Odoo va lento o se va la red. Cada lectura cuenta al momento en la PDA (pita y suma
 * +1) y se guarda en Odoo en segundo plano; si Odoo la rechaza, avisa y la quita. Las lecturas pendientes se guardan
 * en la memoria de la PDA (localStorage) y se mandan al volver, aunque se cierre la app. Cada petición tiene un tiempo
 * máximo (20 s): si Odoo no contesta, se vuelve a mandar con el mismo id (no cuenta dos veces). Caja y Validar sí
 * esperan a Odoo: sin conexión dicen «Esperando conexión…».
 * v3.5: más rápida en OUT grandes. Leer y Deshacer reciben el estado ligero (solo cantidades y totales) y se
 * parchea el que hay; la lista se pinta solo si está abierta; la foto de la línea siguiente se baja antes; las
 * alternativas de Faltante se buscan solas si el operario se queda unos segundos en la misma línea.
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
var COLORES = ['a', 'b', 'c', 'd', 'e', 'f'];   // v3.21: colores de la franja de la ubicación (menú ☰)
var COLOR_DEFECTO = 'f';
var CONFIRMAR_MS = 4000;       // v3.2: «Tampoco está aquí» se pulsa dos veces
var PRECARGA_ALT_MS = 3000;     // v3.5: parado en la misma línea 3 s -> se buscan ya las alternativas de Faltante
var ALT_VALIDO_MS = 120000;     // v3.5: alternativas guardadas: se enseñan al momento durante 2 min
var LENTO_MS = 5000;            // v3.6: Odoo tarda más de 5 s -> «Odoo va lento, se guarda igual»
var TIEMPO_MAX_MS = 20000;      // v3.6: sin respuesta en 20 s -> se vuelve a mandar (mismo id)
var OCUPADA_MS = 1500;          // v3.6: la OUT la está guardando otra petición -> se vuelve a probar
var CLAVE_COLA = 'koroshi_preparacion_cola';   // v3.6: lecturas pendientes en la memoria de la PDA
var COLA_HORAS = 24;            // v3.6: las pendientes de más de un día no se mandan (v3.29: se apuntan como caducadas)
var CLAVE_CADUCADAS = 'koroshi_preparacion_caducadas';   // v3.29: caducadas pendientes de apuntar en Odoo
var VALIDAR_MAX_MS = 90000;     // v3.29: validar una OUT grande puede tardar: más tiempo antes de reintentar
var REINTENTOS_MAX = 8;         // v3.29: mover / deshacer / validar: reintentos con el mismo id (lento u ocupada)
var MAX_ALTERNATIVAS = 3;
var ICONOS = {ok: '✓', info: 'ℹ', warn: '⚠', mal: '✖'};
// v3.22: ALARMA DE PARADO. Con la OUT abierta y X min sin leer ninguna prenda (parámetro
// koroshi_preparacion.minutos_alarma, por defecto 4; 0 = sin alarma), sirena a volumen máximo, vibración y la
// pantalla parpadeando en rojo. No se para hasta que cuenta una lectura (prenda, caja, Poner cantidad, Faltante
// resuelto) o se sale con ←. No hace caso del interruptor de sonido de Lecturas.
var ALARMA_MIN_DEFECTO = 4;
// v3.23: solo en horario de trabajo (koroshi_preparacion.horario_alarma), en minutos desde las 00:00 de la PDA
var ALARMA_HORARIO_DEFECTO = [[360, 600], [615, 780], [840, 1020]];   // 6-10, 10:15-13, 14-17
var ALARMA_MIRAR_MS = 2000;     // cada 2 s se mira si toca
var SIRENA_MS = 1000;           // un ciclo de sirena por segundo

var Pantalla = AbstractAction.extend({
    contentTemplate: 'koroshi_preparacion.Pantalla',
    events: {
        'keydown .o_kp_codigo': '_onKeydown',
        'focus .o_kp_codigo': '_estadoLector',
        'blur .o_kp_codigo': '_onBlur',
        'click .o_kp_lector': '_onTocar',
        'click .o_kp_volver': '_onVolver',
        'click .o_kp_caja': '_onCaja',
        'click .o_kp_tipo_caja': '_onTipoCaja',          // v3.24
        'click .o_kp_cancelar_caja': '_salirDeCaja',
        'click .o_kp_rech_reintentar': '_onRechazadaReintentar',   // v3.29: caja sin conexión rechazada
        'click .o_kp_rech_fuera': '_onRechazadaFuera',
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
        'click .o_kp_ver_lineas': '_onMenuLineas',   // v3.11: desde el menú ☰
        // v3.0.1: flechas, tocar una línea de la lista y volver a la que toca
        'click .o_kp_anterior': '_onAnterior',
        'click .o_kp_posterior': '_onPosterior',
        'click .o_kp_ir_pendiente': '_onIrPendiente',
        'click .o_kp_lineas li': '_onTocarLinea',
        // v3.7
        'click .o_kp_cantidad_btn': '_onCantidad',
        'click .o_kp_cant_todas': '_onCantidadTodas',
        'click .o_kp_cant_ok': '_onCantidadOk',
        'keydown .o_kp_cant_input': '_onKeydownCantidad',
        'click .o_kp_cant_cancelar': '_cerrarHoja',
        'click .o_kp_imprimir': '_onMenuImprimir',   // v3.11: desde el menú ☰
        'click .o_kp_menu_btn': '_onMenu',
        'click .o_kp_pack_seguir': '_onPackSeguir',      // v3.20
        'click .o_kp_l_editar': '_onEditarCaja',         // v3.21: ✎ en una línea ya en caja
        'click .o_kp_pausa_btn': '_onPausaBtn',          // v3.30: pausa arriba (⏸ / ▶)
        'click .o_kp_seguir': '_onSeguir',               // v3.30: volver de la pausa sin salir
        'click .o_kp_menu_color': '_onMenuColor',        // v3.21: color de la franja de la ubicación
        'click .o_kp_color_op': '_onElegirColor',
        'click .o_kp_color_cerrar': '_cerrarHoja',
        'click .o_kp_mv_menos': '_onMoverMenos',
        'click .o_kp_mv_mas': '_onMoverMas',
        'click .o_kp_mv_destino': '_onMoverDestino',
        'click .o_kp_mv_cancelar': '_cerrarHoja',
        'click .o_kp_cajas_resumen': '_onVerCajas',     // v3.20: tocar «N cajas» enseña la lista
        'click .o_kp_menu_cerrar': '_cerrarHoja',
        'click .o_kp_imp_item': '_onImprimirItem',
        'click .o_kp_imp_cerrar': '_cerrarHoja',
    },

    init: function (parent, action) {
        this._super.apply(this, arguments);
        var ctx = (action && action.context) || {};
        this.lote = ctx.preparacion_lote || null;            // v3.15: {id, name} de una agrupación Z-
        this.pickingName = this.lote ? this.lote.name : (ctx.preparacion_out || false);
        this.operario = ctx.preparacion_operario || null;   // {id, nombre}
        this.precargada = ctx.preparacion_estado || null;   // v3.14: el estado que ya tenía Lecturas
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
        this.altCache = {};            // v3.5: {move_line_id: {t, leidas, r}} alternativas de Faltante ya buscadas
        this.fotosBajadas = {};        // v3.5: fotos ya pedidas al navegador
        this.listaSucia = true;        // v3.5: la lista de líneas se pinta al abrirla
        this.alarmaMin = ALARMA_MIN_DEFECTO;   // v3.22
        this.alarmaHorario = ALARMA_HORARIO_DEFECTO;   // v3.23
        this.ultimaActividad = Date.now();
        this.alarmaOn = false;
    },

    willStart: function () {
        var self = this;
        var pre = this.precargada;
        if (pre && pre.out && pre.out.name === this.pickingName) {
            // v3.14: Lecturas ya la tenía cargada: se pinta al momento y se refresca justo después (start)
            this.estado = pre;
            this.refrescarAlEmpezar = true;
            return this._super.apply(this, arguments);
        }
        var carga = this._rpc({route: '/koroshi/preparacion/cargar', params: _.extend(
            this.lote ? {lote_id: this.lote.id} : {picking_name: this.pickingName},   // v3.15
            {employee_id: this.operario ? this.operario.id : false})})
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
        $('body').addClass('o_kp_pantalla_pda');   // v3.10: sin la barra de menús de Odoo (más sitio en la PDA)
        core.bus.on('barcode_scanned', this, this._onBarcodeScanned);
        window.addEventListener('online', this._enLinea);
        window.addEventListener('offline', this._fueraDeLinea);
        return this._super.apply(this, arguments).then(function () {
            // v3.0.1: producto sin foto -> no se ve el hueco
            self.$('.o_kp_foto').on('error', function () { $(this).hide(); }).on('load', function () { $(this).show(); });
            self.$('.o_kp_f_foto').on('error', function () { $(this).hide(); });   // v3.2
            self._ponerColor(self._colorGuardado());   // v3.21: el de la última vez en esta PDA, sin esperar
            self._cargarColor();
            self._pintar();
            if (self.errorCarga) { self._aviso(self.errorCarga, 'mal'); }
            self._recuperarCola();   // v3.6: lo que quedó sin guardar (app cerrada, PDA reiniciada)
            if (self.refrescarAlEmpezar) { self.refrescarAlEmpezar = false; self._recargar(); }   // v3.14
            // v3.3: preparar a dos -> se ve lo que lee el compañero (y si valida, se vuelve a Lecturas)
            self.timerDos = setInterval(function () {
                if (self.estado && self.estado.a_dos && self.modo === 'leer' && !self.enviando && !self.cola.length &&
                        !self.sinRed) {
                    self._recargar(null, true);   // v3.5: ligero
                }
            }, A_DOS_MS);
            self.ultimaActividad = Date.now();   // v3.22: cuenta desde que se abre la OUT
            self.timerAlarma = setInterval(self._mirarAlarma.bind(self), ALARMA_MIRAR_MS);
            self._foco();
        });
    },

    on_attach_callback: function () {
        // vuelve de la pantalla de Faltante: se recarga la OUT (si ya está validada, vuelta a Lecturas)
        this._super.apply(this, arguments);
        $('body').addClass('o_kp_pantalla_pda');   // v3.10
        if (this.yaMostrada) { this._recargar(); }
        this.yaMostrada = true;
        this.ultimaActividad = Date.now();   // v3.22: vuelve de Faltante: se cuenta otra vez desde ahora
        this._foco();
        this._ajustarUbicacion();
    },

    on_detach_callback: function () {
        $('body').removeClass('o_kp_pantalla_pda');   // v3.10: otras pantallas, con su barra
        this._alarma(false);   // v3.22: en otra pantalla no suena
        this._super.apply(this, arguments);
    },

    destroy: function () {
        $('body').removeClass('o_kp_pantalla_pda');   // v3.10
        core.bus.off('barcode_scanned', this, this._onBarcodeScanned);
        window.removeEventListener('online', this._enLinea);
        window.removeEventListener('offline', this._fueraDeLinea);
        clearTimeout(this.timerAviso);
        clearTimeout(this.timerReintento);
        clearTimeout(this.timerVolver);
        clearTimeout(this.timerConfirmar);
        clearInterval(this.timerDos);
        clearTimeout(this.timerAlt);
        clearTimeout(this.timerLento);
        clearTimeout(this.timerOtra);
        clearInterval(this.timerAlarma);   // v3.22: «←» (dejar la OUT aquí) para la alarma
        this._alarma(false);
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

    // v3.15: agrupación Z- entera (lote_id) o una OUT (picking_id)
    _esLote: function () {
        return !!this.lote || !!(this.estado && this.estado.out && this.estado.out.es_lote);
    },

    _obj: function (id, esLote) {
        if (esLote === undefined) { esLote = this._esLote(); }
        return esLote ? {lote_id: id} : {picking_id: id};
    },

    _claveMemoria: function () {
        var out = this._out();
        if (!out) { return null; }
        return (this._esLote() ? 'L' : '') + out.id;
    },

    // v3.15: «CAJA 05 · K34 TIENDA» de una línea de agrupación ('' en una OUT suelta)
    _destino: function (l) {
        if (!l || !this._esLote()) { return ''; }
        if (l.caja_tienda) { return 'CAJA ' + l.caja_tienda + ' · ' + (l.tienda || l.out_name || ''); }
        return (l.out_name || '') + (l.tienda ? ' · ' + l.tienda : '');
    },

    // v3.5: estado ligero -> se parchea el que hay. Devuelve false si no cuadra (líneas nuevas, partidas o en otro
    // orden): entonces hay que cargar la OUT entera.
    _aplicar: function (nuevo) {
        if (!nuevo) { return true; }
        if (!nuevo.ligero) {
            this.estado = nuevo;
            this._reaplicarPendientes();   // v3.6
            return true;
        }
        var viejo = this.estado;
        var din = nuevo.lineas || [];
        if (!viejo || !viejo.lineas || viejo.lineas.length !== din.length) { return false; }
        for (var i = 0; i < din.length; i++) {
            if (viejo.lineas[i].id !== din[i][0]) { return false; }
        }
        var lineas = viejo.lineas;
        din.forEach(function (d, j) {
            var l = lineas[j];
            l.pedidas = d[1];
            l.leidas = d[2];
            l.caja = d[3];
            l.completa = d[4];
        });
        // v3.29: el ligero solo trae lo que cambia; lo fijo (out, tipos de caja, alarma) se queda el que había
        var e = _.extend({}, viejo, nuevo);
        e.lineas = lineas;
        e.ligero = false;
        if (nuevo.out_estado && viejo.out) { e.out = _.extend({}, viejo.out, {estado: nuevo.out_estado}); }
        this.estado = e;
        this._reaplicarPendientes();   // v3.6
        return true;
    },

    // ------------------------------------------------------------ v3.6: lecturas que cuentan al momento
    // La línea de la OUT con ese código (EAN, EAN con/sin 0 delante o referencia) que aún no está completa ni en caja.
    _delProducto: function (codigo) {
        var e = this.estado;
        if (!e || !e.lineas || RE_CJ.test(codigo)) { return []; }
        var v = [codigo];
        if (/^\d{12}$/.test(codigo)) { v.push('0' + codigo); }
        if (/^0\d{12}$/.test(codigo)) { v.push(codigo.slice(1)); }
        return e.lineas.filter(function (l) {
            if ((l.ean && v.indexOf(l.ean) >= 0) || (l.ref && l.ref === codigo)) { return true; }
            return _.some(l.eans_alt || [], function (a) { return v.indexOf(a) >= 0; });   // v3.7
        });
    },

    // v3.7: si el código es la ubicación (caja KO_ o hueco) de alguna línea, se ve esa línea (la primera pendiente)
    _irAUbicacion: function (codigo) {
        var e = this.estado;
        if (!e || !e.lineas) { return false; }
        var c = codigo.toUpperCase();
        var deAhi = e.lineas.filter(function (l) {
            return _.some(l.ubicacion_codigos || [], function (u) { return String(u).toUpperCase() === c; }) ||
                (l.ubicacion && l.ubicacion.toUpperCase() === c);
        });
        if (!deAhi.length) { return false; }
        var l = _.find(deAhi, function (x) { return !x.completa && !x.caja; });
        if (l) {
            this.verId = l.id === e.siguiente_id ? null : l.id;
            this._aviso(deAhi[0].ubicacion + ': lee ' + (l.nombre || l.producto) +
                        (l.talla ? ' · Talla ' + l.talla : ''), 'info');
        } else {
            this.verId = deAhi[0].id;
            this._aviso('En ' + deAhi[0].ubicacion + ' ya está todo cogido.', 'info');
        }
        this._pitido(true);
        this._pintar();
        return true;
    },

    _lineaLocal: function (codigo) {
        var libres = _.filter(this._delProducto(codigo), function (l) { return !l.caja && l.leidas < l.pedidas; });
        if (this._esLote()) {
            // v3.15: el mismo artículo puede ir a varias tiendas: primero la línea que se ve (su caja es la que dice
            // la pantalla); si no, la primera de la ruta. Odoo recibe la misma línea (linea_id).
            var visto = this._idVisto();
            var esa = _.findWhere(libres, {id: visto});
            if (esa) { return esa; }
        }
        return libres[0] || null;
    },

    _recalcular: function (e) {
        var sig = _.find(e.lineas, function (x) { return !x.completa && !x.caja; });
        e.siguiente_id = sig ? sig.id : false;
        e.todo_leido = e.lineas.length > 0 && _.every(e.lineas, function (x) { return x.completa; });
    },

    _sumarLocal: function (e, l, n) {
        n = n || 1;
        l.leidas += n;
        l.completa = l.leidas >= l.pedidas;
        e.leidas += n;
        if (!e.out || e.out.con_caja !== false) {   // v3.14: las INT no van en caja
            e.sin_caja += n;
            e.mias_sin_caja = (e.mias_sin_caja || 0) + n;
            var o = l.out_id && _.findWhere(e.outs || [], {id: l.out_id});   // v3.15: por tienda
            if (o) { o.sin_caja += n; o.leidas += n; }
        }
        this._recalcular(e);
    },

    // lo que aún está en la cola (Odoo no lo tiene) se vuelve a sumar sobre lo que dice Odoo
    _reaplicarPendientes: function () {
        var self = this;
        var e = this.estado;
        if (!e || !e.lineas) { return; }
        this.cola.forEach(function (item) {
            if (item.tipo === 'caja') {   // v3.22: caja cerrada sin red: lo leído antes ya va en ella
                if (item.local) { self._cajaLocal(e, item); }
                return;
            }
            if (!item.optimista) { return; }
            var n = item.n || 1;
            var l = _.findWhere(e.lineas, {id: item.lineaId});
            if (item.tipo === 'cantidad') {   // v3.7: va a su línea o a ninguna
                if (l && !l.caja && l.leidas + n <= l.pedidas) { self._sumarLocal(e, l, n); }
                return;
            }
            if (!l || l.caja || l.leidas >= l.pedidas) {
                l = _.find(e.lineas, function (x) {
                    return x.producto_id === item.productoId && !x.caja && x.leidas < x.pedidas;
                });
            }
            if (l) { self._sumarLocal(e, l); }
        });
    },

    _pendientes: function () {
        return this.cola.filter(function (i) { return i.tipo === 'leer' || i.tipo === 'cantidad'; }).length;
    },

    // v3.22: cajas cerradas en la PDA que Odoo aún no tiene
    _cajasPendientes: function () {
        return this.cola.filter(function (i) { return i.tipo === 'caja'; }).length;
    },

    // v3.22: «N lecturas y M cajas» de lo que falta por guardar
    _textoPendientes: function () {
        var n = this._pendientes();
        var c = this._cajasPendientes();
        var t = [];
        if (n || !c) { t.push(n + (n === 1 ? ' lectura' : ' lecturas')); }
        if (c) { t.push(c + (c === 1 ? ' caja' : ' cajas')); }
        return t.join(' y ');
    },

    // v3.22: a qué OUT de la agrupación va una CJ, sin preguntar a Odoo (las mismas reglas que Odoo):
    // la de su etiqueta de zona, la que ya tiene esa caja, la de la línea que se ve o la única con algo fuera de caja.
    _outDeCaja: function (e, codigo, outId) {
        var outs = e.outs || [];
        var c = (codigo || '').toUpperCase();
        var o = _.find(outs, function (x) { return (x.cjs || []).indexOf(c) >= 0; });
        if (o) { return o; }
        var conCaja = _.find(e.lineas || [], function (l) { return l.caja === c && l.out_id; });
        if (conCaja) { return _.findWhere(outs, {id: conCaja.out_id}) || null; }
        var conAlgo = _.filter(outs, function (x) { return x.sin_caja > 0; });
        if (outId) {
            o = _.findWhere(conAlgo, {id: outId});
            if (o) { return o; }
        }
        return conAlgo.length === 1 ? conAlgo[0] : null;
    },

    // v3.22: cerrar la caja en la PDA (sin red): lo leído fuera de caja pasa a esa caja. Odoo la cierra al volver,
    // en el mismo orden (las lecturas de antes van a ella; las de después, fuera). Las líneas a medias siguen libres:
    // al volver la conexión Odoo las parte y la PDA carga lo que diga Odoo.
    _cajaLocal: function (e, item) {
        var nombre = item.codigo || item.provisional || '';
        var uds = 0;
        var outId = false;
        if (this._esLote()) {
            var o = this._outDeCaja(e, item.codigo, item.outId);
            if (!o || !o.sin_caja) { return 0; }
            outId = o.id;
            uds = o.sin_caja;
            o.sin_caja = 0;
        } else {
            uds = e.a_dos ? (e.mias_sin_caja || 0) : e.sin_caja;
        }
        if (!uds) { return 0; }
        e.sin_caja = Math.max(0, (e.sin_caja || 0) - uds);
        e.mias_sin_caja = Math.max(0, (e.mias_sin_caja || 0) - uds);
        (e.lineas || []).forEach(function (l) {
            if (l.completa && !l.caja && l.leidas > 0 && (!outId || l.out_id === outId)) { l.caja = nombre; }
        });
        var cajas = (e.cajas || []).slice();
        var ya = _.findWhere(cajas, {nombre: nombre});
        // v3.24.3: la caja cerrada sin red también enseña su tipo
        var tipo = item.tipoCaja && _.findWhere(e.tipos_caja || [], {id: item.tipoCaja});
        if (ya) { ya.uds += uds; } else {
            cajas.push({nombre: nombre, uds: uds, sin_red: true, tipo: tipo ? tipo.nombre : false});
        }
        e.cajas = cajas;
        this._recalcular(e);
        return uds;
    },

    // la cola de lecturas (y, v3.22, de cajas) en la memoria de la PDA, por OUT
    _leerMemoria: function () {
        try { return JSON.parse(window.localStorage.getItem(CLAVE_COLA) || '{}') || {}; } catch (e) { return {}; }
    },

    _escribirMemoria: function (todo) {
        try { window.localStorage.setItem(CLAVE_COLA, JSON.stringify(todo)); } catch (e) { /* sin memoria */ }
    },

    _guardarCola: function () {
        var clave = this._claveMemoria();   // v3.15: 'L<id>' en las agrupaciones
        if (!clave) { return; }
        var todo = this._leerMemoria();
        // v3.22: también las cajas, en su sitio de la cola (si no, lo leído después iría a la caja de antes)
        var lecturas = this.cola.filter(function (i) {
            return i.tipo === 'leer' || i.tipo === 'cantidad' || i.tipo === 'caja';
        }).map(function (i) {
            return {tipo: i.tipo, codigo: i.codigo, id: i.id, t: i.t, employee_id: i.employee_id,
                    lineaId: i.lineaId, n: i.n, outId: i.outId, provisional: i.provisional,
                    tipoCaja: i.tipoCaja, diferida: i.diferida, rechazo: i.rechazo};   // v3.29
        });
        if (lecturas.length) { todo[clave] = lecturas; } else { delete todo[clave]; }
        this._escribirMemoria(todo);
    },

    _recuperarCola: function () {
        var self = this;
        var out = this._out();
        var clave = this._claveMemoria();
        var todo = this._leerMemoria();
        var limite = Date.now() - COLA_HORAS * 3600000;
        // v3.29: lo de más de 24 h ya no se aplica, pero se apunta en Odoo (antes se tiraba sin decir nada)
        var caducadas = this._leerCaducadas();
        Object.keys(todo).forEach(function (k) {
            var viejas = (todo[k] || []).filter(function (i) { return (i.t || 0) < limite; });
            if (viejas.length) {
                caducadas[k] = (caducadas[k] || []).concat(viejas);
                todo[k] = (todo[k] || []).filter(function (i) { return (i.t || 0) >= limite; });
            }
        });
        this._escribirCaducadas(caducadas);
        this._escribirMemoria(todo);
        this._mandarCaducadas();
        if (out && todo[clave]) {
            todo[clave].forEach(function (i) {
                // v3.29: lo que vuelve de la memoria es diferido (el operario no lo vio guardarse)
                var item = {tipo: i.tipo || 'leer', codigo: i.codigo, id: i.id, t: i.t, employee_id: i.employee_id,
                            lineaId: i.lineaId, n: i.n, diferida: true, rechazo: i.rechazo};
                if (item.tipo === 'caja') {   // v3.22: la caja cerrada sin red (mismo id: Odoo no la cierra dos veces)
                    item.outId = i.outId;
                    item.provisional = i.provisional;
                    item.tipoCaja = i.tipoCaja;   // v3.24
                    item.local = true;
                    self._cajaLocal(self.estado, item);
                    self.cola.push(item);
                    return;
                }
                if (item.tipo === 'cantidad') {   // v3.7
                    var lc = _.findWhere(self.estado.lineas, {id: i.lineaId});
                    item.optimista = true;
                    if (lc && !lc.caja && lc.leidas + (i.n || 1) <= lc.pedidas) { self._sumarLocal(self.estado, lc, i.n); }
                    self.cola.push(item);
                    return;
                }
                var l = self._lineaLocal(i.codigo);
                if (l) {
                    item.optimista = true;
                    item.lineaId = l.id;
                    item.productoId = l.producto_id;
                    self._sumarLocal(self.estado, l);
                }
                self.cola.push(item);
            });
            var n = this.cola.length;
            if (n && this.cola[0].rechazo) {
                this._pintar();
                this._hojaRechazada();   // v3.29: una caja que Odoo no aceptó: antes de seguir, otra etiqueta
            } else if (n) {
                this._aviso('Guardando ' + this._textoPendientes() + ' que quedaron en la PDA…', 'info');
                this._pintar();
                this._enviar();
            } else {
                this._guardarCola();
            }
        }
        // las de otras OUT (se cerró la app antes de guardarlas): se mandan solas, en segundo plano
        Object.keys(todo).forEach(function (pid) {
            if (out && clave === pid) { return; }
            self._vaciarOtra(pid, todo[pid] || []);
        });
    },

    // clave: el id de la OUT o, v3.15, 'L<id>' de una agrupación
    _vaciarOtra: function (clave, items) {
        var self = this;
        var todo = this._leerMemoria();
        if (items.length) { todo[clave] = items; } else { delete todo[clave]; }
        this._escribirMemoria(todo);
        if (!items.length) { return; }
        var esLote = String(clave).charAt(0) === 'L';
        var id = parseInt(esLote ? String(clave).slice(1) : clave, 10);
        if (!id) { return; }
        var i = items[0];
        // v3.29: una caja que Odoo no aceptó para la cola de esa OUT: se decide al abrirla (otra etiqueta)
        if (i.rechazo) { return; }
        var parar = function (msg) {
            var resto = items.slice();
            resto[0] = _.extend({}, i, {rechazo: msg || 'Error de Odoo'});
            self._vaciarOtra(clave, resto);
        };
        return this._post(this._ruta(i), _.extend(this._params(i, id, esLote), {diferida: true}))
            .then(function (r) {
                if (r && r.que === 'ocupada') {
                    setTimeout(function () { self._vaciarOtra(clave, items); }, OCUPADA_MS);
                    return;
                }
                // v3.29: Odoo ya la ha apuntado si no la acepta. Una caja rechazada (con la OUT abierta) para la cola:
                // si siguiera, la caja siguiente se llevaría sus uds.
                if (i.tipo === 'caja' && !(r && r.ok) && !(r && r.que === 'out_cerrada')) { return parar(r && r.msg); }
                self._vaciarOtra(clave, items.slice(1));
            }, function (err) {
                // sin red / Odoo lento: se queda en la memoria para la próxima vez
                if (!(err && err.msg)) { return; }
                // v3.29: error de Odoo con esta petición (no queda nada apuntado): se apunta aparte
                if (i.tipo === 'caja') { return parar(err.msg); }
                self._apuntarRechazo(clave, i, err.msg);
                self._vaciarOtra(clave, items.slice(1));
            });
    },

    // v3.29: lo de la cola que Odoo no ha podido ni apuntar (error de Odoo) o que ha caducado: a «rechazadas»
    _apuntarRechazo: function (clave, item, motivo) {
        var esLote = String(clave).charAt(0) === 'L';
        var id = parseInt(esLote ? String(clave).slice(1) : clave, 10);
        if (!id) { return; }
        return this._post('/koroshi/preparacion/rechazadas', _.extend(this._obj(id, esLote), {
            lecturas: [this._paraRechazo(item)], motivo: motivo})).then(null, function () { /* sin red: nada */ });
    },

    _paraRechazo: function (i) {
        return {tipo: i.tipo, codigo: i.codigo || i.provisional || '', id: i.id, employee_id: i.employee_id, n: i.n};
    },

    _leerCaducadas: function () {
        try { return JSON.parse(window.localStorage.getItem(CLAVE_CADUCADAS) || '{}') || {}; } catch (e) { return {}; }
    },

    _escribirCaducadas: function (todo) {
        try { window.localStorage.setItem(CLAVE_CADUCADAS, JSON.stringify(todo)); } catch (e) { /* sin memoria */ }
    },

    // v3.29: las caducadas se apuntan en Odoo («Lecturas rechazadas de cola») y solo entonces se borran de la PDA
    _mandarCaducadas: function () {
        var self = this;
        var pend = this._leerCaducadas();
        Object.keys(pend).forEach(function (clave) {
            var items = pend[clave] || [];
            var esLote = String(clave).charAt(0) === 'L';
            var id = parseInt(esLote ? String(clave).slice(1) : clave, 10);
            if (!items.length || !id) {
                var p0 = self._leerCaducadas();
                delete p0[clave];
                return self._escribirCaducadas(p0);
            }
            self._post('/koroshi/preparacion/rechazadas', _.extend(self._obj(id, esLote), {
                lecturas: items.map(self._paraRechazo), motivo: ''})).then(function (r) {
                if (r && r.ok) {
                    var p = self._leerCaducadas();
                    delete p[clave];
                    self._escribirCaducadas(p);
                }
            }, function () { /* sin red: la próxima vez */ });
        });
    },

    // v3.7: ruta y parámetros de cada cosa de la cola
    _ruta: function (item) {
        if (item.tipo === 'caja') { return '/koroshi/preparacion/caja'; }
        if (item.tipo === 'cantidad') { return '/koroshi/preparacion/cantidad'; }
        return '/koroshi/preparacion/leer';
    },

    _params: function (item, pickingId, esLote) {
        if (esLote === undefined) { esLote = this._esLote(); }
        var p = _.extend(this._obj(pickingId, esLote), {codigo: item.codigo, id_lectura: item.id,
                 employee_id: item.employee_id || (this.operario ? this.operario.id : false)});
        if (item.tipo === 'cantidad') {
            p.linea_id = item.lineaId;
            p.cantidad = item.n;
        }
        if (esLote && item.tipo === 'leer' && item.lineaId) { p.linea_id = item.lineaId; }   // v3.15: la que se ve
        if (esLote && item.tipo === 'caja' && item.outId) { p.out_id = item.outId; }          // v3.15: CJ sin tienda
        if (item.tipo === 'caja' && item.tipoCaja) { p.tipo_caja = item.tipoCaja; }           // v3.24
        if (item.diferida) { p.diferida = true; }   // v3.29: si Odoo no la acepta, la ve el encargado
        return p;
    },

    // llamada JSON a Odoo con tiempo máximo. Si falla, rechaza con {lento} (no contesta o está reiniciando),
    // {sinRed}, {sesion} (sesión caducada) o {msg} (error de Odoo con esta petición).
    _post: function (ruta, params, maxMs) {
        var ctrl = window.AbortController ? new window.AbortController() : null;
        var timer = ctrl ? setTimeout(function () { ctrl.abort(); }, maxMs || TIEMPO_MAX_MS) : null;
        var opciones = {
            method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({jsonrpc: '2.0', method: 'call', params: params, id: Date.now()}),
        };
        if (ctrl) { opciones.signal = ctrl.signal; }
        return window.fetch(ruta, opciones).then(function (resp) {
            if (resp.status >= 500) { clearTimeout(timer); throw {lento: true}; }
            return resp.json().then(function (j) {
                clearTimeout(timer);
                return j;
            }, function () {
                clearTimeout(timer);
                throw {lento: true};
            });
        }, function (err) {
            clearTimeout(timer);
            throw (err && err.name === 'AbortError') ? {lento: true} : {sinRed: true};
        }).then(function (j) {
            if (j && j.error) {
                var d = j.error.data || {};
                if (j.error.code === 100 || /SessionExpired/.test(d.name || '')) { throw {sesion: true}; }
                throw {msg: d.message || j.error.message || 'Error de Odoo'};
            }
            return j ? j.result : null;
        });
    },

    // v3.29: una petición que no puede hacerse dos veces (mover, deshacer, validar): lleva id_lectura y, si Odoo no
    // contesta a tiempo o la OUT está ocupada, se vuelve a mandar IGUAL (mismo id) hasta REINTENTOS_MAX veces. Odoo
    // contesta lo mismo que la primera vez si ya la hizo. Sin red o sesión caducada: rechaza enseguida.
    _llamar: function (ruta, params, maxMs) {
        var self = this;
        var intento = 0;
        var esperar = function () { return new Promise(function (ok) { setTimeout(ok, OCUPADA_MS); }); };
        var vivo = function () { return !(self.isDestroyed && self.isDestroyed()); };
        var probar = function () {
            intento += 1;
            return self._post(ruta, params, maxMs).then(function (r) {
                if (r && r.que === 'ocupada' && intento < REINTENTOS_MAX && vivo()) { return esperar().then(probar); }
                return r;
            }, function (err) {
                if (err && err.lento && intento < REINTENTOS_MAX && vivo()) { return esperar().then(probar); }
                throw err;
            });
        };
        return probar();
    },

    // v3.29: el texto de un fallo de _post / _llamar
    _textoFallo: function (err) {
        if (err && err.sinRed) { return 'Sin conexión. Prueba otra vez cuando vuelva.'; }
        if (err && err.sesion) { return 'La sesión de Odoo ha caducado: vuelve a entrar.'; }
        if (err && err.lento) { return 'Odoo no contesta. Prueba otra vez en un momento.'; }
        return (err && err.msg) || 'Error de Odoo';
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
        if (this.enPausa) { return this._aviso('En pausa: pulsa ▶ Seguir para volver a leer.', 'warn'); }   // v3.30
        if (this.modo === 'menu' || this.modo === 'color' || this.modo === 'caja_auto') { this._cerrarHoja(); }   // v3.11, v3.21: lo cierra y cuenta
        if (this.modo === 'mover') {   // v3.21: con «Cambiar de caja» abierto, leer una CJ es la caja de destino
            if (RE_CJ.test(codigo.toUpperCase())) { return this._moverA(codigo.toUpperCase()); }
            this.$('.o_kp_mv_aviso').attr('class', 'o_kp_hoja_aviso o_kp_mv_aviso o_kp_mal')
                .text('✖ Eso no es una etiqueta de caja. Elige una caja o lee su etiqueta CJ.');
            return this._pitido(false);
        }
        if (this.modo === 'rechazada') {   // v3.29: la caja que Odoo no aceptó espera otra etiqueta
            if (RE_CJ.test(codigo.toUpperCase()) && this.cola[0] && this.cola[0].codigo) {
                return this._reintentarRechazada(codigo.toUpperCase());
            }
            this.$('.o_kp_hoja_caja .o_kp_hoja_aviso').attr('class', 'o_kp_hoja_aviso o_kp_mal')
                .text('✖ Eso no es una etiqueta de caja. Lee otra etiqueta CJ o elige abajo.');
            return this._pitido(false);
        }
        if (this.modo === 'pack') {   // v3.20: leer con el número de caja a la vista lo cierra y cuenta
            if (this.packVolver) { return; }
            this._cerrarHoja();
        }
        if (this.modo === 'pregunta' || this.modo === 'validando' || this.modo === 'cantidad' ||
                this.modo === 'imprimir') { return; }
        if (this.modo === 'faltante') {
            if (this.sinRed) {
                this._avisoFaltante('Sin conexión: espera a que vuelva para cambiar de ubicación.', 'mal');
                return this._pitido(false);
            }
            return this._reubicar(codigo);   // v3.2: la ubicación de donde se coge
        }
        var tipo = this.modo === 'caja' ? 'caja' : 'leer';
        // v3.15: en una agrupación, leer una CJ es cerrar la caja de esa tienda (su etiqueta dice de qué OUT es)
        if (tipo === 'leer' && this._esLote() && RE_CJ.test(codigo)) { tipo = 'caja'; }
        // v3.24.1: con tipos de caja, se lee la CJ y luego se dice qué caja es (no se cierra con un tipo supuesto)
        if (tipo === 'caja' && !this.tipoHoja && RE_CJ.test(codigo.toUpperCase()) &&
                ((this.estado && this.estado.tipos_caja) || []).length) {
            if (this.modo !== 'caja') { this._hojaCaja(false); }   // agrupación: CJ leída sin pulsar «Caja»
            return this._pedirTipo(codigo.toUpperCase());
        }
        var item = {tipo: tipo, codigo: codigo, id: this._nuevoId(), t: ahora,
                    employee_id: this.operario ? this.operario.id : false};
        if (this.sinRed) { item.diferida = true; }   // v3.29: leída sin conexión
        if (tipo === 'caja') { item.tipoCaja = this.tipoHoja || this._tipoCaja(); }   // v3.24
        if (tipo === 'caja' && this._esLote()) {
            // v3.15: si la CJ no es de ninguna tienda, va a la tienda de la línea que se ve
            var vista = this.estado && _.findWhere(this.estado.lineas, {id: this._idVisto()});
            item.outId = vista ? vista.out_id : false;
        }
        if (tipo === 'caja' && this.sinRed) {
            // v3.22: sin red la caja se cierra en la PDA y Odoo la cierra al volver (en su sitio de la cola)
            return this._cajaSinRed(item);
        }
        if (tipo === 'leer') {
            // v3.6: si el producto es de la OUT y le faltan uds, cuenta ya (pita y +1); Odoo lo guarda detrás
            var l = this._lineaLocal(codigo);
            if (l) {
                item.optimista = true;
                item.lineaId = l.id;
                item.productoId = l.producto_id;
                this._sumarLocal(this.estado, l);
                this.verId = l.completa ? null : l.id;
                var destino = this._destino(l);   // v3.15: a qué caja de tienda va
                // v3.15: con destino el aviso no se va solo (la pantalla ya enseña la línea siguiente)
                this._aviso((destino ? '→ ' + destino + ' · ' : '') + (l.nombre || l.producto) + ' · ' + l.leidas +
                            ' de ' + l.pedidas, 'ok', !!destino);
                this._sonar(l.completa ? 'linea' : 'ok');   // v3.13: otro sonido si la línea queda completa
                this._actividad();   // v3.22
                if (l.completa) { this._avisoAquiMismo(l); }
                if (this.estado.todo_leido) {
                    this._aviso('Todo leído. ' + (this.estado.sin_caja ? 'Cierra la caja y valida.' : 'Pulsa Validar.'),
                                'ok');
                }
            } else if (this._irAUbicacion(codigo)) {
                return;   // v3.7: era una ubicación de la OUT: se ve su línea
            } else if (this.sinRed) {
                var delProducto = this._delProducto(codigo);
                this._aviso(delProducto.length ? 'Ya tienes todas las uds de ' + (delProducto[0].nombre ||
                    delProducto[0].producto) + '. No cuenta.' : 'Sin conexión: no se puede comprobar ' + codigo +
                    '. No cuenta.', 'mal');
                return this._pitido(false);
            }
        }
        this.cola.push(item);
        this._guardarCola();
        if (item.optimista) { this._pintar(); }
        this._enviar();
    },

    _enviar: function () {
        var self = this;
        if (this.enviando || this.sinRed || !this.cola.length || !this._out()) { return; }
        var item = this.cola[0];
        if (item.rechazo) { return; }   // v3.29: parada hasta que el operario decida qué hace con esa caja
        this.enviando = true;
        clearTimeout(this.timerOtra);
        clearTimeout(this.timerLento);
        this.timerLento = setTimeout(function () {   // v3.6
            if (self.enviando) {
                self._aviso('Odoo va lento: lo leído se guarda igual (' + self._pendientes() + ' pendientes).', 'warn');
            }
        }, LENTO_MS);
        return this._post(this._ruta(item), this._params(item, this._out().id)).then(function (r) {
            clearTimeout(self.timerLento);
            self.enviando = false;
            if (self.isDestroyed && self.isDestroyed()) { return; }
            if (r && r.que === 'ocupada') {
                // v3.6: otra petición está guardando en esta OUT: se vuelve a probar (no se pierde)
                self.timerOtra = setTimeout(function () { self._enviar(); }, OCUPADA_MS);
                return;
            }
            self.sesionCaducada = false;
            if (item.tipo === 'caja' && item.local && !(r && r.ok) && !(r && r.que === 'out_cerrada')) {
                // v3.29: caja cerrada sin red que Odoo no acepta: se PARA la cola. Si siguiera, lo leído después y la
                // caja siguiente se llevarían las uds de esta. El operario lee otra etiqueta o decide.
                if (r && r.estado) { self._aplicar(r.estado); }
                return self._pararCola(item, (r && r.msg) || 'Error');
            }
            if (r && r.que === 'out_cerrada') { self.outCerrada = true; }   // v3.29: lo que queda, apuntado y fuera
            self.cola.shift();
            self._guardarCola();
            var cuadra = !(r && r.estado) || self._aplicar(r.estado);
            if (!cuadra) { self._recargar(); }   // v3.5: algo ha cambiado de forma (p. ej. la caja del compañero)
            if (item.tipo === 'caja') { self._trasCaja(r, item); } else { self._trasLeer(r, item); }
            self._pintar();
            self._enviar();
            if (!self.cola.length && self.outCerrada) {   // v3.29: la OUT ya estaba hecha: vuelta a Lecturas
                self.outCerrada = false;
                self._recargar();
            }
        }, function (err) {
            clearTimeout(self.timerLento);
            self.enviando = false;
            if (err && err.lento) {
                // v3.6: Odoo no contesta en 20 s (o se está reiniciando): se vuelve a mandar, mismo id
                self._aviso('Odoo no contesta: se vuelve a intentar (' + self._pendientes() + ' pendientes).', 'warn');
                self.timerOtra = setTimeout(function () { self._enviar(); }, OCUPADA_MS);
                return self._pintar();
            }
            if (err && err.sinRed) { return self._sinConexion(); }   // la lectura se queda y se reintenta
            if (err && err.sesion) {
                self.sesionCaducada = true;
                self._aviso('La sesión de Odoo ha caducado: vuelve a entrar. Lo leído está guardado en la PDA.', 'mal');
                return self._pitido(false);
            }
            if (item.tipo === 'caja' && item.local) {
                // v3.29: lo mismo que si la rechaza: se para la cola hasta que el operario decida
                return self._pararCola(item, (err && err.msg) || 'Error de Odoo');
            }
            // error de Odoo con esta lectura: se quita y se carga la OUT tal como está en Odoo
            // v3.29: y se apunta (con el error de Odoo la petición no ha dejado nada)
            self._apuntarRechazo(self._claveMemoria(), item, (err && err.msg) || 'Error de Odoo');
            self.cola.shift();
            self._guardarCola();
            self._aviso((item.optimista ? 'No se ha guardado ' + item.codigo + ': ' : '') +
                        (item.tipo === 'caja' && item.local ? 'La caja ' + (item.codigo || item.provisional) +
                         ' no se ha cerrado en Odoo (lo leído sigue fuera de caja): ' : '') +
                        ((err && err.msg) || 'Error de Odoo'), 'mal');
            self._pitido(false);
            self._recargar();
            self._enviar();
        });
    },

    _trasLeer: function (r, item) {
        if (item && item.optimista) {
            // v3.6: ya pitó y se vio al leer; solo se avisa si Odoo no la ha aceptado (y ya no cuenta)
            if (!(r && r.ok)) {
                this._aviso('No se ha guardado ' + item.codigo + ': ' + ((r && r.msg) || 'Error'), 'mal');
                this._pitido(false);
            }
            return;
        }
        if (r && r.ok) {
            // v3.0.1: si la línea leída aún no está completa se queda a la vista; si ya lo está, salta sola a la siguiente
            var l = this.estado && _.findWhere(this.estado.lineas, {id: r.linea_id});
            this.verId = l && !l.completa ? l.id : null;
            this._aviso(r.msg, 'ok', !!r.destino);   // v3.15: con la caja de tienda, no se va solo
            this._sonar(l && l.completa ? 'linea' : 'ok');   // v3.13
            this._actividad();   // v3.22
            if (l && l.completa) { this._avisoAquiMismo(l); }
            if (this.estado && this.estado.todo_leido) {
                this._aviso('Todo leído. ' + (this.estado.sin_caja ? 'Cierra la caja y valida.' : 'Pulsa Validar.'), 'ok');
            }
            return;
        }
        if (r && r.que === 'talla_hermana' && r.linea_id && this.estado) {
            // v3.13: se ve la línea de la talla que toca
            this.verId = r.linea_id === this.estado.siguiente_id ? null : r.linea_id;
        }
        this._aviso((r && r.msg) || 'Error', 'mal');
        this._pitido(false);
    },

    /** v3.13: la línea se ha completado y la siguiente está en la misma parada: que no se mueva. */
    _avisoAquiMismo: function (hecha) {
        var e = this.estado;
        if (!e || !hecha || !hecha.parada || e.todo_leido) { return; }
        var sig = _.findWhere(e.lineas, {id: e.siguiente_id});
        if (!sig || sig.parada !== hecha.parada) { return; }
        var mas = this._aquiMismo(sig);
        this._aviso('AQUÍ MISMO: ahora ' + (sig.nombre || sig.producto) + (sig.talla ? ' · ' + sig.talla : '') +
                    (mas ? ' (y ' + mas + ' más)' : ''), 'ok');
    },

    /** v3.13: cuántas líneas más (sin la que se ve) quedan por coger en la misma parada. */
    _aquiMismo: function (l) {
        var e = this.estado;
        if (!e || !l || !l.parada) { return 0; }
        return _.filter(e.lineas, function (x) {
            return x.id !== l.id && x.parada === l.parada && !x.completa && !x.caja;
        }).length;
    },

    // ------------------------------------------------------------ caja
    _onCaja: function () {
        if (!this._out() || this.modo === 'rechazada') { return; }
        if (this.modo === 'pack') { this._cerrarHoja(); }
        if (!this.estado.sin_caja) {
            this._aviso('No hay nada leído fuera de caja.', 'info');
            return this._foco();
        }
        if (!this._esLote() && this.estado.out && this.estado.out.pack_auto) {
            // v3.24: con tipos de caja, primero se elige (tocar uno la cierra); sin tipos, como antes
            if ((this.estado.tipos_caja || []).length) { return this._hojaCaja(true); }
            return this._cerrarAuto();
        }
        return this._hojaCaja(false);
    },

    // v3.19: Zalando / About You: sin etiqueta CJ. Odoo crea el paquete (PACK...) y se sigue leyendo
    _cerrarAuto: function () {
        var auto = {tipo: 'caja', codigo: '', id: this._nuevoId(), t: Date.now(),
                    employee_id: this.operario ? this.operario.id : false, tipoCaja: this._tipoCaja()};
        if (this.modo === 'caja_auto') { this._cerrarHoja(); }
        if (this.sinRed) { return this._cajaSinRed(auto); }   // v3.22
        this._aviso('Cerrando caja…', 'info');
        this.cola.push(auto);
        this._guardarCola();
        this._enviar();
        return this._foco();
    },

    // ------------------------------------------------------------ v3.24: tipo de caja
    _claveTipoCaja: function () {
        return 'koroshi_preparacion_tipo_caja_' + (this.operario ? this.operario.id : 'pda');
    },

    /** El tipo elegido (id de Consumibles), si sigue en la lista; si no, el primero. false si no hay tipos. */
    _tipoCaja: function () {
        var tipos = (this.estado && this.estado.tipos_caja) || [];
        if (!tipos.length) { return false; }
        var id = this.tipoCajaId;
        if (!id) {
            try { id = parseInt(window.localStorage.getItem(this._claveTipoCaja()) || '0', 10); } catch (e) { id = 0; }
        }
        return _.findWhere(tipos, {id: id}) ? id : tipos[0].id;
    },

    _pintarTipos: function (auto) {
        var tipos = (this.estado && this.estado.tipos_caja) || [];
        var actual = this.tipoHoja;   // v3.24.1: sin ninguno marcado hasta que lo toquen
        var $c = this.$('.o_kp_tipos_caja').empty().toggle(!!tipos.length);
        tipos.forEach(function (t) {
            $('<button type="button" class="o_kp_tipo_caja"/>').attr('data-id', t.id)
                .toggleClass('o_kp_tipo_elegido', !auto && !!actual && t.id === actual)
                .append($('<b/>').text(t.nombre))
                .append(t.medidas ? $('<small/>').text(t.medidas) : null)
                .appendTo($c);
        });
        this.$('.o_kp_tipos_titulo').toggle(!!tipos.length)
            .text(auto ? '¿Qué caja cierras? Toca el tipo:' : 'Lee la CJ y toca qué caja es:');
    },

    // v3.24.1: CJ leída sin tipo: la hoja la enseña y espera a que toquen qué caja es
    _pedirTipo: function (codigo) {
        this.cjPendiente = codigo;
        this.$('.o_kp_hoja_caja .o_kp_hoja_titulo').text(codigo);
        if (!this._esLote() && this.estado) {
            this.$('.o_kp_hoja_texto').text(this.estado.sin_caja + (this.estado.sin_caja === 1 ? ' ud va' : ' uds van') +
                                            ' a esta caja.');
        }
        this.$('.o_kp_tipos_titulo').text('¿Qué caja es? Toca el tipo:');
        this.$('.o_kp_hoja_caja .o_kp_hoja_aviso').attr('class', 'o_kp_hoja_aviso o_kp_ok')
            .text('✓ Etiqueta leída. Ahora toca el tipo de caja.');
        this._pitido(true);
        return this._foco();
    },

    _onTipoCaja: function (ev) {
        var id = parseInt($(ev.currentTarget).data('id'), 10);
        if (!id) { return; }
        this.tipoCajaId = id;
        try { window.localStorage.setItem(this._claveTipoCaja(), String(id)); } catch (e) { /* sin memoria */ }
        if (this.modo === 'caja_auto') { return this._cerrarAuto(); }   // Zalando / About You: tocar = cerrar
        this.tipoHoja = id;   // v3.24.1
        this.$('.o_kp_tipo_caja').each(function () {
            $(this).toggleClass('o_kp_tipo_elegido', parseInt($(this).data('id'), 10) === id);
        });
        if (this.cjPendiente) {   // v3.24.1: ya se había leído la CJ: se cierra la caja con este tipo
            var cj = this.cjPendiente;
            this.cjPendiente = null;
            this.ultima = {codigo: '', t: 0};
            return this._leer(cj);
        }
        this.$('.o_kp_hoja_caja .o_kp_hoja_aviso').attr('class', 'o_kp_hoja_aviso').text('Ahora lee la etiqueta CJ.');
        this._foco();
    },

    // la hoja de cerrar caja: CJ (leer la etiqueta) o, auto = Zalando / About You, solo el tipo
    _hojaCaja: function (auto) {
        this.modo = auto ? 'caja_auto' : 'caja';
        this.tipoHoja = null;      // v3.24.1: cada caja, su tipo (tocado a propósito)
        this.cjPendiente = null;
        this._pintarTipos(auto);
        this.$('.o_kp_hoja_caja .o_kp_hoja_titulo').text(auto ? 'Cerrar caja' : 'Escanea la caja');
        if (auto) {
            this.$('.o_kp_hoja_tiendas').empty().hide();
            this.$('.o_kp_hoja_texto').text(this.estado.sin_caja + (this.estado.sin_caja === 1 ? ' ud va' : ' uds van') +
                                            ' a esta caja. Odoo le pone el número (PACK).');
            this.$('.o_kp_hoja_caja .o_kp_hoja_aviso').attr('class', 'o_kp_hoja_aviso').text('');
            this.$('.o_kp_hoja_pregunta, .o_kp_hoja_faltante').hide();
            this.$('.o_kp_hoja_caja').show();
            this.$('.o_kp_hoja').show();
            return this._foco();
        }
        var $t = this.$('.o_kp_hoja_tiendas').empty().hide();
        if (this._esLote()) {
            // v3.15: cada tienda tiene su caja: la etiqueta CJ dice de qué tienda es
            this.$('.o_kp_hoja_texto').text('Lee la etiqueta CJ de la caja de la tienda. Fuera de caja:');
            _.filter(this.estado.outs || [], function (o) { return o.sin_caja > 0; }).forEach(function (o) {
                $('<li/>').text(o.destino + ': ' + o.sin_caja + (o.sin_caja === 1 ? ' ud' : ' uds')).appendTo($t);
            });
            $t.toggle(!!$t.children().length);
        } else {
            this.$('.o_kp_hoja_texto').text(this.estado.sin_caja + (this.estado.sin_caja === 1 ? ' ud va' : ' uds van') +
                                            ' a esta caja. Lee la etiqueta CJ de la caja.');
        }
        this.$('.o_kp_hoja_caja .o_kp_hoja_aviso').attr('class', 'o_kp_hoja_aviso').text('');
        this.$('.o_kp_hoja_pregunta, .o_kp_hoja_faltante').hide();
        this.$('.o_kp_hoja_caja').show();
        this.$('.o_kp_hoja').show();
        this._foco();
    },

    // v3.22: cerrar la caja sin red. Se comprueba en la PDA lo mismo que Odoo (etiqueta CJ, que haya algo fuera de
    // caja, de qué tienda es) y lo leído pasa ya a esa caja. Zalando / About You: sin número aún -> «S<n>» para
    // apuntar en la caja; al volver la conexión sale su PACK.
    _cajaSinRed: function (item) {
        var e = this.estado;
        var self = this;
        var error = function (msg) {
            if (self.modo === 'caja') {
                self.$('.o_kp_hoja_caja .o_kp_hoja_aviso').attr('class', 'o_kp_hoja_aviso o_kp_mal').text('✖ ' + msg);
            } else {
                self._aviso(msg, 'mal');
            }
            self._pitido(false);
            return self._foco();
        };
        item.codigo = (item.codigo || '').toUpperCase();
        if (item.codigo && !RE_CJ.test(item.codigo)) {
            return error(item.codigo + ' no es una etiqueta de caja (CJ + 9 cifras). Lee la etiqueta de la caja.');
        }
        if (this._esLote()) {
            var o = this._outDeCaja(e, item.codigo, item.outId);
            if (!o) {
                return error('La caja ' + item.codigo + ' no tiene tienda. Lee la etiqueta de la caja de la tienda ' +
                             '(la de «CAJA nn»).');
            }
            if (!o.sin_caja) { return error(o.destino + ': no hay nada leído fuera de caja para esta tienda.'); }
        } else if (!(e.a_dos ? e.mias_sin_caja : e.sin_caja)) {
            return error('No hay nada leído fuera de caja: lee algún artículo antes de cerrar la caja.');
        }
        if (!item.codigo) { item.provisional = 'S' + ((e.cajas || []).length + 1); }
        item.local = true;
        item.diferida = true;   // v3.29: cerrada sin conexión
        var uds = this._cajaLocal(e, item);
        this._actividad();   // v3.22: cerrar caja también para la alarma de parado
        this.cola.push(item);
        this._guardarCola();
        if (this.modo === 'caja') { this._cerrarHoja(); }
        this._sonar('caja');
        this._pintar();
        var udsTxt = uds + (uds === 1 ? ' ud' : ' uds');
        if (item.provisional) {
            this._verPack('Caja cerrada SIN CONEXIÓN · apunta en la caja', item.provisional, uds, false);
            this.$('.o_kp_pack_nota').text('Su número PACK sale cuando vuelva la conexión.');
            return;
        }
        this._aviso('Caja ' + item.codigo + ' cerrada en la PDA con ' + udsTxt + '. Se guarda en Odoo cuando vuelva ' +
                    'la conexión. Puedes seguir leyendo.', 'ok', true);
        return this._foco();
    },

    // v3.29: caja cerrada sin red que Odoo no acepta. Se queda la primera de la cola (con el motivo) y no se manda
    // nada más hasta que el operario lea otra etiqueta, pruebe otra vez o deje lo leído fuera de caja.
    _pararCola: function (item, msg) {
        item.rechazo = msg;
        this._guardarCola();
        this._pitido(false);
        this._pintar();
        this._hojaRechazada();
    },

    _hojaRechazada: function () {
        var item = this.cola[0];
        if (!item || !item.rechazo) { return; }
        this.modo = 'rechazada';
        var nombre = item.codigo || item.provisional || '';
        var resto = this.cola.length - 1;
        this.$('.o_kp_hoja_pregunta, .o_kp_hoja_faltante, .o_kp_hoja_cantidad, .o_kp_hoja_imprimir, .o_kp_hoja_menu, ' +
               '.o_kp_hoja_pack, .o_kp_hoja_mover, .o_kp_hoja_color').hide();
        this.$('.o_kp_hoja_tiendas').empty().hide();
        this.$('.o_kp_tipos_titulo, .o_kp_tipos_caja, .o_kp_cancelar_caja').hide();
        this.$('.o_kp_hoja_caja .o_kp_hoja_titulo').text('La caja ' + nombre + ' no se ha cerrado en Odoo');
        this.$('.o_kp_hoja_texto').text(item.rechazo + ' ' + (resto ? 'Lo leído después (' + resto +
            (resto === 1 ? ' cosa' : ' cosas') + ') espera en la PDA. ' : '') +
            (item.codigo ? 'Lee OTRA etiqueta CJ para esta caja, o elige abajo.' : 'Elige abajo.'));
        this.$('.o_kp_hoja_caja .o_kp_hoja_aviso').attr('class', 'o_kp_hoja_aviso o_kp_mal')
            .text('✖ La cola está parada: no se guarda nada más hasta decidirlo.');
        this.$('.o_kp_rechazada_botones').show();
        this.$('.o_kp_hoja_caja').show();
        this.$('.o_kp_hoja').show();
        this._foco();
    },

    // otra etiqueta (codigo) o la misma: va con un id NUEVO (el de antes ya está apuntado como rechazado)
    _reintentarRechazada: function (codigo) {
        var item = this.cola[0];
        if (!item || !item.rechazo) { return this._cerrarHoja(); }
        var viejo = item.codigo || item.provisional || '';
        if (codigo) { item.codigo = codigo; }
        item.id = this._nuevoId();
        delete item.rechazo;
        var nuevo = item.codigo || item.provisional || '';
        if (this.estado && nuevo !== viejo) {   // la caja de la PDA se llama ya como la etiqueta nueva
            (this.estado.lineas || []).forEach(function (l) { if (l.caja === viejo) { l.caja = nuevo; } });
            (this.estado.cajas || []).forEach(function (c) { if (c.nombre === viejo) { c.nombre = nuevo; } });
        }
        this._guardarCola();
        this._cerrarHoja();
        this._aviso('Cerrando la caja ' + nuevo + ' en Odoo…', 'info');
        this._enviar();
    },

    _onRechazadaReintentar: function () {
        if (this.modo !== 'rechazada') { return; }
        this._reintentarRechazada(false);
    },

    _onRechazadaFuera: function () {
        var item = this.cola[0];
        if (this.modo !== 'rechazada' || !item || !item.rechazo) { return; }
        this.cola.shift();
        this._guardarCola();
        this._cerrarHoja();
        this._aviso('Lo de la caja ' + (item.codigo || item.provisional || '') + ' sigue fuera de caja: entra en la ' +
                    'próxima caja que cierres.', 'warn', true);
        this._recargar();   // lo que tiene Odoo, con lo que queda en la cola sumado
        this._enviar();
    },

    _trasCaja: function (r, item) {
        if (item && item.local) {
            // v3.22: una caja cerrada sin red llega a Odoo: no se toca lo que el operario tenga abierto ahora
            if (r && r.ok) {
                if (item.provisional && r.caja) {
                    this.mapaSC = this.mapaSC || {};
                    this.mapaSC[r.caja] = item.provisional;
                    if (this.estado && this.estado.cajas) {   // la «S<n>» de la PDA ya es su PACK
                        this.estado.cajas = _.reject(this.estado.cajas, function (c) {
                            return c.nombre === item.provisional;
                        });
                    }
                    if (this.modo === 'leer' || this.modo === 'pack') {
                        this._sonar('caja');
                        this._verPack('La caja ' + item.provisional + ' ya tiene número · apúntalo', r.caja, r.uds,
                                      false);
                        this.$('.o_kp_pack_nota').text('Táchale «' + item.provisional + '» y apunta este número.');
                        return;
                    }
                    return this._aviso('La caja ' + item.provisional + ' es la ' + r.caja + ': apúntalo en la caja.',
                                       'ok', true);
                }
                return this._aviso('Guardada en Odoo: ' + ((r && r.msg) || ('caja ' + item.codigo)), 'ok');
            }
            this._aviso('La caja ' + (item.codigo || item.provisional) + ' no se ha cerrado en Odoo (lo leído sigue ' +
                        'fuera de caja): ' + ((r && r.msg) || 'Error') + ' Ciérrala otra vez.', 'mal', true);
            return this._pitido(false);
        }
        if (r && r.ok) {
            this._cerrarHoja();
            this._aviso(r.msg, 'ok', true);
            this._sonar('caja');   // v3.13
            this._actividad();   // v3.22
            var out = this._out();
            if (out && out.pack_auto && r.caja) {   // v3.20: Zalando / About You: el número en grande
                this._verPack('Caja cerrada', r.caja, r.uds, false);
            }
            return;
        }
        var msg = (r && r.msg) || 'Error';
        if (this.modo !== 'caja') {
            // v3.15: CJ leída sin pulsar «Caja» (agrupación): el aviso en la pantalla
            this._aviso(msg, 'mal');
            return this._pitido(false);
        }
        // sigue esperando la etiqueta
        this.$('.o_kp_hoja_caja .o_kp_hoja_aviso').attr('class', 'o_kp_hoja_aviso o_kp_mal').text('✖ ' + msg);
        this._pitido(false);
        if (this.estado && !this.estado.sin_caja) { this._cerrarHoja(); this._aviso(msg, 'mal'); }
    },

    // v3.20: hoja con el número del paquete (PACK...) en grande y la lista de cajas de la OUT. volver = tras validar
    // (al pulsar el botón se vuelve a Lecturas).
    _verPack: function (titulo, nombre, uds, volver) {
        var e = this.estado || {};
        var cajas = (e.cajas || []).slice();
        if (nombre && !_.findWhere(cajas, {nombre: nombre})) { cajas.push({nombre: nombre, uds: uds || 0}); }
        this.modo = 'pack';
        this.packVolver = !!volver;
        this.$('.o_kp_hoja_caja, .o_kp_hoja_pregunta, .o_kp_hoja_faltante, .o_kp_hoja_cantidad, .o_kp_hoja_imprimir, ' +
               '.o_kp_hoja_menu, .o_kp_hoja_mover').hide();
        this.$('.o_kp_pack_titulo').text(titulo || '');
        this.$('.o_kp_pack_numero').text(nombre || '').toggle(!!nombre);
        this.$('.o_kp_pack_uds').text(nombre ? (uds || 0) + (uds === 1 ? ' ud' : ' uds') : '').toggle(!!nombre);
        this.$('.o_kp_pack_nota').toggle(!!nombre);
        this.$('.o_kp_pack_lista_titulo').text(cajas.length ? 'Cajas de ' + ((this._out() || {}).name || 'esta OUT') +
                                               ' (' + cajas.length + ')' : 'Aún no hay cajas cerradas.');
        var $l = this.$('.o_kp_pack_lista').empty();
        var mapa = this.mapaSC || {};
        this.$('.o_kp_pack_nota').text('Apunta este número en la caja.');   // v3.22: la de siempre (sin red cambia)
        cajas.forEach(function (c) {
            $('<li/>').toggleClass('o_kp_pack_nueva', c.nombre === nombre)
                .append($('<b/>').text(c.nombre))
                .append($('<span/>').text((c.tipo ? ' · ' + c.tipo : '') +   // v3.24
                                          ' · ' + c.uds + (c.uds === 1 ? ' ud' : ' uds') +
                                          (mapa[c.nombre] ? ' · era ' + mapa[c.nombre] : '') +   // v3.22
                                          (c.sin_red ? ' · sin guardar aún' : '')))
                .appendTo($l);
        });
        this.$('.o_kp_pack_seguir').text(volver ? 'Hecho' : 'Seguir leyendo');
        this.$('.o_kp_hoja_pack').show();
        this.$('.o_kp_hoja').show();
    },

    // ------------------------------------------------------------ v3.21: color de la ubicación (por operario)
    _claveColor: function () {
        return 'koroshi_preparacion_color_' + (this.operario ? this.operario.id : 'pda');
    },

    _colorGuardado: function () {
        try { return window.localStorage.getItem(this._claveColor()) || COLOR_DEFECTO; } catch (e) { return COLOR_DEFECTO; }
    },

    _ponerColor: function (color) {
        if (COLORES.indexOf(color) < 0) { color = COLOR_DEFECTO; }
        this.color = color;
        var $r = this.$('.o_koroshi_preparacion').addBack('.o_koroshi_preparacion');
        COLORES.forEach(function (c) { $r.removeClass('o_kp_color_' + c); });
        $r.addClass('o_kp_color_' + color);
        try { window.localStorage.setItem(this._claveColor(), color); } catch (e) { /* sin memoria */ }
        this.$('.o_kp_color_op').each(function () {
            $(this).toggleClass('o_kp_color_elegido', $(this).data('color') === color);
        });
    },

    _cargarColor: function () {
        var self = this;
        if (!this.operario) { return; }
        this._rpc({route: '/koroshi/preparacion/color', params: {employee_id: this.operario.id}}).then(function (r) {
            if (r && r.ok && r.color && r.color !== self.color) {
                self._ponerColor(r.color);
                self._pintar();
            }
        }).guardedCatch(function (e) { if (e && e.event && e.event.preventDefault) { e.event.preventDefault(); } });
    },

    _onMenuColor: function () {
        this.modo = 'color';
        this.$('.o_kp_hoja_menu').hide();
        this._ponerColor(this.color || COLOR_DEFECTO);
        this.$('.o_kp_hoja_color').show();
        this.$('.o_kp_hoja').show();
    },

    _onElegirColor: function (ev) {
        var color = String($(ev.currentTarget).data('color') || '');
        this._ponerColor(color);
        this._cerrarHoja();
        this._aviso('Color de la ubicación: ' + color.toUpperCase() + '.', 'ok');
        if (this.operario) {
            this._rpc({route: '/koroshi/preparacion/color', params: {employee_id: this.operario.id, color: color}})
                .guardedCatch(function (e) { if (e && e.event && e.event.preventDefault) { e.event.preventDefault(); } });
        }
    },

    // ------------------------------------------------------------ v3.21: cambiar de caja
    _onEditarCaja: function (ev) {
        ev.stopPropagation();
        var id = parseInt($(ev.currentTarget).data('id'), 10);
        var l = this.estado && _.findWhere(this.estado.lineas, {id: id});
        if (!l || !l.caja || this.modo !== 'leer') { return; }
        if (this.sinRed) { return this._aviso('Sin conexión: espera a que vuelva para cambiar de caja.', 'mal'); }
        if (this.cola.length) { return this._aviso('Espera un momento: se está guardando lo leído.', 'warn'); }
        this.mover = {linea: l, n: 1};
        this.modo = 'mover';
        this.$('.o_kp_hoja_caja, .o_kp_hoja_pregunta, .o_kp_hoja_faltante, .o_kp_hoja_cantidad, .o_kp_hoja_imprimir, ' +
               '.o_kp_hoja_menu, .o_kp_hoja_pack').hide();
        this.$('.o_kp_mv_producto').text((l.nombre || l.producto) + (l.talla ? ' · Talla ' + l.talla : ''));
        this.$('.o_kp_mv_ahora').text('Ahora en la caja ' + l.caja + ' (' + l.leidas + (l.leidas === 1 ? ' ud)' : ' uds)'));
        this.$('.o_kp_mv_cant_fila').toggle(l.leidas > 1);
        this.$('.o_kp_mv_cant').text('1');
        var $d = this.$('.o_kp_mv_destinos').empty();
        // v3.28: sacar de la caja: vuelve a «por poner» y entra en la caja siguiente (antes «+ Caja nueva»)
        $('<button type="button" class="o_kp_boton o_kp_mv_destino o_kp_mv_fuera"/>').attr('data-destino', 'FUERA')
            .text('↩ Sacar de la caja (va a la siguiente)').appendTo($d);
        _.each((this.estado.cajas || []), function (c) {
            if (c.nombre === l.caja) { return; }
            $('<button type="button" class="o_kp_boton o_kp_blanco o_kp_mv_destino"/>').attr('data-destino', c.nombre)
                .text(c.nombre + ' (' + c.uds + (c.uds === 1 ? ' ud)' : ' uds)')).appendTo($d);
        });
        var auto = this._out() && this._out().pack_auto;
        this.$('.o_kp_mv_cj').toggle(!auto);
        this.$('.o_kp_mv_aviso').attr('class', 'o_kp_hoja_aviso o_kp_mv_aviso').text('');
        this.$('.o_kp_hoja_mover').show();
        this.$('.o_kp_hoja').show();
        this._foco();
    },

    _onMoverMenos: function () {
        if (!this.mover) { return; }
        this.mover.n = Math.max(1, this.mover.n - 1);
        this.$('.o_kp_mv_cant').text(this.mover.n);
    },

    _onMoverMas: function () {
        if (!this.mover) { return; }
        this.mover.n = Math.min(this.mover.linea.leidas, this.mover.n + 1);
        this.$('.o_kp_mv_cant').text(this.mover.n);
    },

    _onMoverDestino: function (ev) {
        this._moverA(String($(ev.currentTarget).data('destino') || ''));
    },

    _moverA: function (destino) {
        var self = this;
        var out = this._out();
        if (!this.mover || !out || !destino || this.moviendo) { return; }
        this.moviendo = true;
        this.$('.o_kp_mv_aviso').attr('class', 'o_kp_hoja_aviso o_kp_mv_aviso').text('Cambiando de caja…');
        // v3.29: un id por movimiento (mismo destino y uds): si se vuelve a tocar tras un fallo, no se mueve dos veces
        var clave = destino + '|' + this.mover.n;
        this.mover.ids = this.mover.ids || {};
        this.mover.ids[clave] = this.mover.ids[clave] || this._nuevoId();
        return this._llamar('/koroshi/preparacion/mover_caja', _.extend(this._obj(out.id), {
            linea_id: this.mover.linea.id, cantidad: this.mover.n, destino: destino,
            employee_id: this.operario ? this.operario.id : false, id_lectura: this.mover.ids[clave],
        })).then(function (r) {
            self.moviendo = false;
            if (r && r.estado) { self._aplicar(r.estado); }
            if (r && r.ok) {
                self.mover = null;
                self._cerrarHoja();
                if (self.$('.o_kp_lineas').is(':visible')) { self._pintarLineas(true); }
                self._aviso(r.msg, 'ok', true);
                self._sonar('caja');
                self._actividad();   // v3.22
                return;
            }
            self.$('.o_kp_mv_aviso').attr('class', 'o_kp_hoja_aviso o_kp_mv_aviso o_kp_mal')
                .text('✖ ' + ((r && r.msg) || 'No se ha podido cambiar de caja.'));
            self._pitido(false);
        }, function (err) {
            self.moviendo = false;
            self.$('.o_kp_mv_aviso').attr('class', 'o_kp_hoja_aviso o_kp_mv_aviso o_kp_mal')
                .text('✖ ' + self._textoFallo(err));
            self._pitido(false);
            if (err && err.sinRed) { self._sinConexion(); }
        });
    },

    _onVerCajas: function () {
        if (!this._out() || this.modo !== 'leer') { return; }
        this._verPack('Cajas cerradas', '', 0, false);
    },

    _onPackSeguir: function () {
        if (this.packVolver) {
            this.packVolver = false;
            return this.trigger_up('history_back');
        }
        this._cerrarHoja();
    },

    _salirDeCaja: function () {
        this._cerrarHoja();
        this._aviso('Caja sin cerrar. Puedes seguir leyendo.', 'info');
    },

    _onFondoHoja: function () {
        if (this.modo === 'rechazada') { return; }   // v3.29: hay que decidir
        if (this.modo === 'pack') { return this._onPackSeguir(); }   // v3.20
        if (this.modo === 'mover' || this.modo === 'color') { return this._cerrarHoja(); }      // v3.21
        if (this.modo === 'caja' || this.modo === 'caja_auto') { this._salirDeCaja(); }   // v3.24
        else if (this.modo === 'pregunta') { this._cerrarHoja(); }
        else if (this.modo === 'faltante') { this._cerrarFaltante(); }
        else if (this.modo === 'cantidad' || this.modo === 'imprimir' || this.modo === 'menu') { this._cerrarHoja(); }
    },

    _cerrarHoja: function () {
        if (this.modo === 'rechazada') {   // v3.29: la hoja de caja vuelve a ser la de siempre
            this.$('.o_kp_rechazada_botones').hide();
            this.$('.o_kp_cancelar_caja').show();
        }
        this.modo = 'leer';
        this.tipoHoja = null;      // v3.24.1
        this.cjPendiente = null;
        this.$('.o_kp_hoja').hide();
        this.$('.o_kp_hoja_cantidad, .o_kp_hoja_imprimir, .o_kp_hoja_menu, .o_kp_hoja_pack, .o_kp_hoja_mover, ' +
               '.o_kp_hoja_color').hide();   // v3.7, v3.11, v3.20, v3.21
        this.mover = null;
        this._pintar();
        this._foco();
    },

    // ------------------------------------------------------------ validar
    _onValidar: function () {
        if (!this._out() || this.sinRed || this.modo !== 'leer' || this.cola.length || this.enviando) { return; }
        // v3.27: Zalando / About You: segundo toque en «Validar incompleto» (en los 8 s siguientes)
        var incompleto = this.incompletoOut === this._out().id;
        this._desarmarIncompleto();
        return this._validar(false, incompleto);
    },

    // v3.27: Odoo ha dicho que faltan uds en una OUT de Zalando / About You: el botón pasa a «Validar incompleto»
    _armarIncompleto: function (outId) {
        var self = this;
        this.incompletoOut = outId;
        clearTimeout(this.timerIncompleto);
        this.timerIncompleto = setTimeout(function () { self._desarmarIncompleto(); self._pintar(); }, 8000);
    },
    _desarmarIncompleto: function () {
        clearTimeout(this.timerIncompleto);
        this.incompletoOut = null;
    },

    _onPendienteSi: function () { return this._validar('si'); },
    _onPendienteNo: function () { return this._validar('no'); },

    _validar: function (pedidoPendiente, incompleto) {
        var self = this;
        var out = this._out();
        this.$('.o_kp_hoja').hide();
        this.modo = 'validando';
        this._capa('Validando ' + out.name + '…', false);
        // v3.29: con id y tiempo máximo; si Odoo no contesta se vuelve a mandar igual (no se valida dos veces y, si ya
        // está validada, contesta «validada»)
        return this._llamar('/koroshi/preparacion/validar', _.extend(this._obj(out.id), {
            employee_id: this.operario ? this.operario.id : false,
            pedido_pendiente: pedidoPendiente || false,
            tipo_caja: this._tipoCaja() || false,   // v3.24: la última caja de Zalando / About You
            incompleto: incompleto || false,   // v3.27
            id_lectura: this._nuevoId(),
        }), VALIDAR_MAX_MS).then(function (r) {
            if (r && r.estado) { self._aplicar(r.estado); }
            var titulo = '✓ ' + out.name + (r && r.incompleta ? ' validada INCOMPLETA' : ' validada');   // v3.27
            if (r && r.ok && r.que === 'validada' && r.caja_auto) {
                // v3.20: Zalando / About You: la última caja se ha cerrado sola: su número y la lista, hasta «Hecho»
                self._ocultarCapa();
                self._pitido(true);
                self._verPack(titulo + ' · última caja', r.caja_auto, r.caja_uds, true);
                return;
            }
            if (r && r.ok && r.que === 'validada') {
                self._capa(self._esLote() ? '✓ ' + r.msg : (r.incompleta ? '✓ ' + r.msg : titulo), true);   // v3.15, v3.27
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
            if (r && r.que === 'quedan' && r.incompleto) { self._armarIncompleto(out.id); }   // v3.27
            self._pintar();
            self._aviso((r && r.msg) || 'No se ha podido validar.', r && r.que === 'quedan' ? 'warn' : 'mal');
            self._pitido(false);
        }, function (err) {
            self._ocultarCapa();
            self.modo = 'leer';
            if (err && err.sinRed) { return self._sinConexion(); }   // al volver, si ya está validada, a Lecturas
            self._aviso(err && err.lento ? 'Odoo no contesta al validar. Pulsa Validar otra vez: si ya está validada, ' +
                        'lo dirá.' : self._textoFallo(err), 'mal');
            self._pitido(false);
        });
    },

    // ------------------------------------------------------------ deshacer / faltante / volver
    _onDeshacer: function () {
        var self = this;
        if (!this._out() || this.modo !== 'leer') { return; }
        // v3.6: la última lectura aún no ha llegado a Odoo -> se quita en la PDA, sin esperar
        var ultimo = this.cola[this.cola.length - 1];
        var enVuelo = this.enviando && this.cola.length === 1;
        if (ultimo && (ultimo.tipo === 'leer' || ultimo.tipo === 'cantidad') && !enVuelo) {
            this.cola.pop();
            this._guardarCola();
            var l = null;
            if (ultimo.optimista) {
                var e = this.estado;
                var n = ultimo.n || 1;
                l = _.findWhere(e.lineas, {id: ultimo.lineaId});
                if (!l || l.caja || l.leidas < n) {
                    l = _.find(e.lineas, function (x) {
                        return x.producto_id === ultimo.productoId && !x.caja && x.leidas > 0;
                    });
                }
                if (l) { this._sumarLocal(e, l, -n); }
            }
            this.verId = l ? l.id : this.verId;
            this._pintar();
            this._aviso('Deshecha: ' + (l ? (l.nombre || l.producto) : ultimo.codigo) + ' (−' + (ultimo.n || 1) + ')',
                        'info');
            this._pitido(true);
            return this._foco();
        }
        if (this.sinRed) { this._aviso('Sin conexión: espera a que vuelva para deshacer.', 'warn'); return; }
        if (this.cola.length || this.enviando) { this._aviso('Un momento: guardando lo leído…', 'info'); return; }
        this.enviando = true;
        // v3.29: con id y reintentos: si Odoo tarda, se vuelve a mandar igual y no se deshace otra lectura
        return this._llamar('/koroshi/preparacion/deshacer', _.extend(this._obj(this._out().id), {
            employee_id: this.operario ? this.operario.id : false, id_lectura: this._nuevoId(),
        })).then(function (r) {
            self.enviando = false;
            if (r && r.que === 'ocupada') { return self._aviso('Odoo está guardando: pulsa otra vez.', 'warn'); }
            if (r && r.estado && !self._aplicar(r.estado)) { self._recargar(); }   // v3.5: ligero
            if (r && r.ok && r.linea_id) { self.verId = r.linea_id; }   // v3.0.1: se ve la línea deshecha
            self._pintar();
            self._aviso((r && r.msg) || 'Error', r && r.ok ? 'info' : 'mal');
            self._pitido(!!(r && r.ok));
            self._foco();
        }, function (err) {
            self.enviando = false;
            if (err && err.sinRed) { return self._sinConexion(); }
            self._aviso(self._textoFallo(err) + (err && err.lento ? ' Mira la línea antes de deshacer otra vez.' : ''),
                        'mal');
            self._recargar();   // lo que hay de verdad en Odoo
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
        if (this.modo === 'rechazada') { this.$('.o_kp_rechazada_botones').hide(); this.$('.o_kp_cancelar_caja').show(); }
        if (this.modo === 'faltante') { return this._cerrarFaltante(); }
        // v3.6: con red, se espera a que lo leído llegue a Odoo (sin red o sin sesión, se queda en la PDA y se manda
        // al volver a abrir la preparación)
        var parada = this.cola.length && this.cola[0].rechazo;   // v3.29: se decide al volver a abrirla
        if (this.cola.length && !this.sinRed && !this.sesionCaducada && !parada) {
            return this._aviso('Espera: guardando ' + this._textoPendientes() + '…', 'warn');   // v3.22
        }
        this.trigger_up('history_back');
    },

    _recargar: function (despues, ligero) {
        var self = this;
        if (!this._out()) { return; }
        return this._rpc({route: '/koroshi/preparacion/cargar', params: _.extend(this._obj(this._out().id), {
            employee_id: this.operario ? this.operario.id : false, ligero: !!ligero})}, {shadow: true})
            .then(function (r) {
                if (!r || !r.ok) { return; }
                if (!self._aplicar(r.estado)) { return self._recargar(despues); }   // v3.5: no cuadra -> entera
                if (self._outTerminada()) { return; }   // validada desde Faltante: vuelta a Lecturas
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
        if (!this._out() || this.sinRed || this.modo !== 'leer') { return; }
        if (this.cola.length || this.enviando) { return this._aviso('Un momento: guardando lo leído…', 'info'); }   // v3.6
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
        // v3.5: si ya se habían buscado (el operario estaba parado en esta línea), se ven al momento; igualmente se
        // vuelven a pedir por si ha cambiado el stock libre
        var guardada = this.altCache[l.id];
        var fresca = !!guardada && guardada.leidas === l.leidas && Date.now() - guardada.t < ALT_VALIDO_MS;
        if (fresca) { this._mostrarAlternativas(guardada.r, l.id); }
        return this._rpc({route: '/koroshi/faltantes/buscar', params: {move_line_id: l.id}}, {shadow: fresca})
            .then(function (r) {
                if (r && r.ok) { self.altCache[l.id] = {t: Date.now(), leidas: l.leidas, r: r}; }
                self._mostrarAlternativas(r, l.id);
            }).guardedCatch(function (err) {
                if (err && err.event && err.event.preventDefault) { err.event.preventDefault(); }
                if (self.modo !== 'faltante' || fresca) { return; }
                self.$('.o_kp_f_cargando').hide();
                if (self._esSinConexion(err)) { self._cerrarFaltante(); return self._sinConexion(); }
                self._avisoFaltante(self._mensajeError(err), 'mal');
            });
    },

    // v3.5: pinta las alternativas de Faltante (de la búsqueda o de las ya guardadas)
    _mostrarAlternativas: function (r, lineaId) {
        var f = this.faltante;
        if (this.modo !== 'faltante' || !f || f.linea.id !== lineaId || f.ocupado) { return; }
        this.$('.o_kp_f_cargando').hide();
        if (!r || !r.ok || !r.linea) { return this._avisoFaltante((r && r.msg) || 'No se ha podido buscar.', 'mal'); }
        var lin = r.linea;
        if (lin.motivo) { return this._avisoFaltante(lin.motivo, 'mal'); }
        f.listo = true;
        this.$('.o_kp_f_no_esta').text('No está en ' + lin.ubicacion + ' · ' + lin.pendiente +
                                       (lin.pendiente === 1 ? ' ud' : ' uds'));
        var alt = (lin.alternativas || []).slice(0, MAX_ALTERNATIVAS);
        var $ol = this.$('.o_kp_f_alternativas').empty();
        // v3.30: la más cercana tiene pocas (menos de 3 o no llega para lo que falta): la segunda también en grande
        var dos = alt.length > 1 && alt[0].libre < Math.max(lin.pendiente || 1, 3);
        alt.forEach(function (a, i) {
            var $li = $('<li/>').toggleClass('o_kp_f_segunda', dos && i === 1);
            // v3.12: hueco y KO en la misma línea y del mismo tamaño, como en la tarjeta
            var partes = (a.nombre || '').split(' · ');
            var $u = $('<span class="o_kp_f_alt_ubi"/>').appendTo($li);
            $('<span class="o_kp_hueco"/>').text(partes[0] || '').appendTo($u);
            if (partes.length > 1) { $('<span class="o_kp_ko"/>').text(partes.slice(1).join(' · ')).appendTo($u); }
            $('<span class="o_kp_f_alt_libre"/>').text((i === 0 ? 'La más cercana · ' :
                (dos && i === 1 ? 'Si no, aquí · ' : '')) + a.libre +
                (a.libre === 1 ? ' ud' : ' uds')).appendTo($li);
            $ol.append($li);
        });
        this.$('.o_kp_f_prueba').toggle(!!alt.length);
        this.$('.o_kp_f_sin_alt').toggle(!alt.length);
        this._ajustarFaltante();   // v3.12
        this.$('.o_kp_f_nada').show();
        if (!this.confirmarNada) { this._sinConfirmar(); }
        this._foco();
    },

    // v3.5: el operario lleva unos segundos en la misma línea sin leer -> puede que no la encuentre: se buscan ya
    // las alternativas, para que «Faltante» las enseñe al momento
    _precargarAlternativas: function (l) {
        var self = this;
        clearTimeout(this.timerAlt);
        if (!l || l.completa || l.caja) { return; }
        var guardada = this.altCache[l.id];
        if (guardada && guardada.leidas === l.leidas && Date.now() - guardada.t < ALT_VALIDO_MS) { return; }
        this.timerAlt = setTimeout(function () {
            if (self.modo !== 'leer' || self.sinRed || self.enviando || self.cola.length || self._idVisto() !== l.id) {
                return;
            }
            self._rpc({route: '/koroshi/faltantes/buscar', params: {move_line_id: l.id}}, {shadow: true})
                .then(function (r) {
                    if (r && r.ok) { self.altCache[l.id] = {t: Date.now(), leidas: l.leidas, r: r}; }
                }).guardedCatch(function (err) {
                    if (err && err.event && err.event.preventDefault) { err.event.preventDefault(); }
                });
        }, PRECARGA_ALT_MS);
    },

    // v3.5: baja ya la foto de la próxima línea pendiente (al llegar a ella sale sin hueco en blanco)
    _precargarFoto: function (e, sig) {
        var pos = e.lineas.indexOf(sig);
        for (var i = pos + 1; i < e.lineas.length; i++) {
            var l = e.lineas[i];
            if (l.completa || l.caja) { continue; }
            if (l.producto_id && l.tiene_foto !== false && !this.fotosBajadas[l.producto_id]) {
                this.fotosBajadas[l.producto_id] = true;
                (new Image()).src = '/web/image/product.product/' + l.producto_id + '/image_512';   // v3.9.2
            }
            return;
        }
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
            self._actividad();   // v3.22
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
            self._actividad();   // v3.22
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

    // ------------------------------------------------------------ v3.7: cantidad a mano
    _onCantidad: function () {
        var l = this.estado && _.findWhere(this.estado.lineas, {id: this._idVisto()});
        if (!l || this.modo !== 'leer' || l.caja) { return; }
        if (l.leidas < 1) {   // v3.9.3: primero una con la pistola (así se comprueba que es el artículo bueno)
            this._aviso('Lee primero una ud de ' + (l.nombre || l.producto) + ' con la pistola. Después pon el resto.',
                        'warn');
            this._pitido(false);
            return this._foco();
        }
        var falta = l.pedidas - l.leidas;
        if (falta < 1) { return; }
        this.modo = 'cantidad';
        this.cantLinea = l.id;
        this.$('.o_kp_cant_texto').text((l.nombre || l.producto) + (l.talla ? ' · Talla ' + l.talla : '') + ' en ' +
                                        l.ubicacion + '. Llevas ' + l.leidas + ' de ' + l.pedidas + '; faltan ' + falta + '.');
        this.$('.o_kp_cant_input').attr('max', falta).val('');
        this.$('.o_kp_cant_todas').text('Todas las que faltan (' + falta + ')').data('n', falta);
        this.$('.o_kp_cant_aviso').attr('class', 'o_kp_hoja_aviso o_kp_cant_aviso').text('');
        this.$('.o_kp_hoja_caja, .o_kp_hoja_pregunta, .o_kp_hoja_faltante, .o_kp_hoja_imprimir').hide();
        this.$('.o_kp_hoja_cantidad').show();
        this.$('.o_kp_hoja').show();
        this.$('.o_kp_cant_input').focus();
    },

    _onKeydownCantidad: function (ev) {
        ev.stopPropagation();
        if (ev.key === 'Enter' || ev.keyCode === 13) {
            ev.preventDefault();
            this._onCantidadOk();
        }
    },

    _onCantidadTodas: function () {
        this._ponerCantidad(parseInt(this.$('.o_kp_cant_todas').data('n'), 10));
    },

    _onCantidadOk: function () {
        this._ponerCantidad(parseInt(this.$('.o_kp_cant_input').val(), 10));
    },

    _ponerCantidad: function (n) {
        var e = this.estado;
        var l = e && _.findWhere(e.lineas, {id: this.cantLinea});
        if (!l) { return this._cerrarHoja(); }
        var falta = l.pedidas - l.leidas;
        if (!n || n < 1 || n > falta) {
            this.$('.o_kp_cant_aviso').attr('class', 'o_kp_hoja_aviso o_kp_cant_aviso o_kp_mal')
                .text('✖ Pon un número de 1 a ' + falta + '.');
            return this._pitido(false);
        }
        // va por la misma cola que las lecturas: cuenta al momento y Odoo lo guarda detrás (mismo id si reintenta)
        var item = {tipo: 'cantidad', codigo: 'A MANO +' + n, id: this._nuevoId(), t: Date.now(), n: n, lineaId: l.id,
                    productoId: l.producto_id, optimista: true, employee_id: this.operario ? this.operario.id : false};
        this._sumarLocal(e, l, n);
        this.verId = l.completa ? null : l.id;
        this.cola.push(item);
        this._guardarCola();
        this._cerrarHoja();
        this._aviso((l.nombre || l.producto) + ' · ' + l.leidas + ' de ' + l.pedidas + ' (+' + n + ' a mano)', 'ok');
        this._pitido(true);
        this._actividad();   // v3.22
        if (e.todo_leido) {
            this._aviso('Todo leído. ' + (e.sin_caja ? 'Cierra la caja y valida.' : 'Pulsa Validar.'), 'ok');
        }
        this._enviar();
    },

    // ------------------------------------------------------------ v3.7: imprimir
    _onImprimir: function () {
        var self = this;
        if (!this._out() || this.modo !== 'leer') { return; }
        this.modo = 'imprimir';
        this.$('.o_kp_imp_lista').empty().text('Buscando…');
        this.$('.o_kp_imp_aviso').attr('class', 'o_kp_hoja_aviso o_kp_imp_aviso').text('');
        this.$('.o_kp_hoja_caja, .o_kp_hoja_pregunta, .o_kp_hoja_faltante, .o_kp_hoja_cantidad').hide();
        this.$('.o_kp_hoja_imprimir').show();
        this.$('.o_kp_hoja').show();
        if (this.sinRed) {
            this.$('.o_kp_imp_lista').empty();
            return this.$('.o_kp_imp_aviso').addClass('o_kp_mal').text('✖ Sin conexión: espera a que vuelva.');
        }
        return this._post('/koroshi/preparacion/impresos', this._obj(this._out().id)).then(function (r) {
            if (self.modo !== 'imprimir') { return; }
            var $l = self.$('.o_kp_imp_lista').empty();
            var lista = (r && r.ok && r.impresos) || [];
            if (!lista.length) { $l.text('No hay nada que imprimir de esta OUT.'); }
            lista.forEach(function (d) {
                var $b = $('<button type="button" class="o_kp_imp_item"/>').attr('data-url', d.url).text(d.nombre);
                if (d.detalle) { $('<span class="o_kp_imp_detalle"/>').text(d.detalle).appendTo($b); }
                $l.append($b);
            });
        }, function () {
            if (self.modo !== 'imprimir') { return; }
            self.$('.o_kp_imp_lista').empty();
            self.$('.o_kp_imp_aviso').addClass('o_kp_mal').text('✖ Odoo no contesta. Prueba otra vez.');
        });
    },

    _onImprimirItem: function (ev) {
        var url = $(ev.currentTarget).attr('data-url');
        if (url) { window.open(url, '_blank'); }
    },

    // ------------------------------------------------------------ v3.11: menú ☰ (ver líneas, imprimir)
    _onMenu: function () {
        if (!this._out() || this.modo !== 'leer') { return; }
        this.modo = 'menu';
        this._pintarBotonLineas();
        this.$('.o_kp_hoja_caja, .o_kp_hoja_pregunta, .o_kp_hoja_faltante, .o_kp_hoja_cantidad, .o_kp_hoja_imprimir').hide();
        this.$('.o_kp_hoja_menu').show();
        this.$('.o_kp_hoja').show();
    },

    // v3.30: pausa (comer, café) con el botón de arriba, al lado del ☰. Primer toque: «¿Pausa?» (4 s); segundo: lo
    // leído se guarda y Odoo para el tiempo (motivo «Pausa» de Operarios: la OUT sigue suya y la primera). La pantalla
    // se queda tapada con «EN PAUSA» y ▶ Seguir: vuelve a empezar el tiempo con la misma OUT, sin leer la tarjeta.
    // A dos (ayudante) no hay OUT suya que guardar: como antes, se para su tiempo y vuelve a Lecturas.
    _onPausaBtn: function () {
        var self = this;
        var $b = this.$('.o_kp_pausa_btn');
        if (this.enPausa) { return this._onSeguir(); }
        if (!this.operario) { return this._aviso('Sin tarjeta no hay pausa: pulsa ← para salir.', 'warn'); }
        if (this.sinRed) { return this._aviso('Sin conexión: espera a que vuelva para la pausa.', 'mal'); }
        if (this.modo !== 'leer' && this.modo !== 'menu') { return; }
        if (!$b.hasClass('o_kp_confirmar_pausa')) {
            $b.addClass('o_kp_confirmar_pausa').text('¿Pausa?');
            clearTimeout(this.timerPausa);
            this.timerPausa = setTimeout(function () { $b.removeClass('o_kp_confirmar_pausa').text('⏸'); }, 4000);
            return;
        }
        clearTimeout(this.timerPausa);
        $b.removeClass('o_kp_confirmar_pausa').text('⏸');
        if (this.cola.length || this.enviando) {
            return this._aviso('Espera: guardando ' + this._textoPendientes() + '… y vuelve a pulsar ⏸.', 'warn');
        }
        var emp = this.operario.id;
        var nombre = this.operario.nombre;
        this._cerrarHoja();
        this._aviso('Pausa…', 'info');
        var ayudante = false;
        return this._rpc({route: '/koroshi/operarios/motivos', params: {}}).then(function (r) {
            var m = r && r.ok && _.findWhere(r.motivos || [], {destino: 'pausa'});
            if (!m) { throw {msg: 'No se ha podido cargar la pausa.'}; }
            return self._rpc({route: '/koroshi/operarios/saltar', params: {employee_id: emp, motivo_id: m.id, nota: ''}});
        }).then(function (r) {
            if (r && r.ok) { return r.msg; }
            // a dos (ayudante): no tiene la OUT asignada; solo se cierra su tiempo
            ayudante = true;
            return self._rpc({route: '/koroshi/operarios/dejar', params: {employee_id: emp}}).then(function (d) {
                if (!d || !d.ok) { throw {msg: (r && r.msg) || (d && d.msg) || 'Error'}; }
                return 'Tu tiempo queda parado';
            });
        }).then(function (msg) {
            if (ayudante) {
                window.koroshiPausaHecha = {nombre: nombre, msg: msg};   // Lecturas (abajo) quita el operario y lo dice
                return self.trigger_up('history_back');
            }
            self._ponerPausa(nombre);
        }).guardedCatch(function (e) {
            if (e && e.event && e.event.preventDefault) { e.event.preventDefault(); }
            self._aviso('No se ha podido hacer la pausa' + (e && e.msg ? ': ' + e.msg : '') + '. Vuelve a probar.', 'mal');
        });
    },

    _ponerPausa: function (nombre) {
        var d = new Date();
        var hora = ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2);
        this.enPausa = {desde: hora};
        this._alarma(false);
        this.modo = 'pausa';
        this._aviso('', '');
        this.$('.o_kp_pausa_texto').text((nombre || '') + ' · desde las ' + hora);
        this.$('.o_kp_pausa_capa').show();
        this.$('.o_kp_pausa_btn').text('▶').addClass('o_kp_en_pausa').attr('aria-label', 'Seguir');
        this.$('.o_kp_codigo').blur();
    },

    _quitarPausa: function () {
        this.enPausa = null;
        this.modo = 'leer';
        this.$('.o_kp_pausa_capa').hide();
        this.$('.o_kp_pausa_btn').text('⏸').removeClass('o_kp_en_pausa').attr('aria-label', 'Pausa (comer, café)');
    },

    // ▶ Seguir: Odoo vuelve a empezar el tiempo con la primera de su cola (la de la pausa). Si por lo que sea es otra
    // (se la han quitado desde la oficina), se vuelve a Lecturas, que la abre.
    _onSeguir: function () {
        var self = this;
        if (!this.enPausa || this.siguiendo) { return; }
        if (this.sinRed) { return this.$('.o_kp_pausa_texto').text('Sin conexión: espera a que vuelva y pulsa ▶.'); }
        var out = this._out();
        var mia = this._esLote() ? (this.lote && this.lote.name) : (out && out.name);
        this.siguiendo = true;
        this.$('.o_kp_seguir').prop('disabled', true).text('▶ …');
        return this._rpc({route: '/koroshi/operarios/siguiente', params: {employee_id: this.operario.id}}).then(function (r) {
            self.siguiendo = false;
            self.$('.o_kp_seguir').prop('disabled', false).text('▶ Seguir');
            var a = r && r.ok && r.asignacion;
            if (!r || !r.ok) {
                return self.$('.o_kp_pausa_texto').text((r && r.msg) || 'No se ha podido seguir. Vuelve a probar.');
            }
            if (a && (a.ref === mia || a.picking_name === mia)) {
                self._quitarPausa();
                self._actividad();   // la alarma de parado empieza de cero
                self._recargar();
                self._aviso('▶ Seguimos con ' + mia + '.', 'ok');
                return self._foco();
            }
            // otra OUT (o ninguna): a Lecturas, que enseña la que toca
            self._quitarPausa();
            self.trigger_up('history_back');
        }).guardedCatch(function (e) {
            self.siguiendo = false;
            self.$('.o_kp_seguir').prop('disabled', false).text('▶ Seguir');
            if (e && e.event && e.event.preventDefault) { e.event.preventDefault(); }
            self.$('.o_kp_pausa_texto').text(self._esSinConexion(e) ? 'Sin conexión: espera a que vuelva y pulsa ▶.' :
                                             'No se ha podido seguir: ' + self._mensajeError(e));
        });
    },

    _onMenuLineas: function () {
        this._cerrarHoja();
        this._onVerLineas();
        var $l = this.$('.o_kp_lineas');
        if ($l.is(':visible') && $l[0].scrollIntoView) { $l[0].scrollIntoView({block: 'start'}); }
    },

    _onMenuImprimir: function () {
        this._cerrarHoja();
        this._onImprimir();
    },

    _onVerLineas: function () {
        var $l = this.$('.o_kp_lineas');
        var abrir = !$l.is(':visible');
        $l.toggle(abrir);
        if (abrir && this.listaSucia) { this._pintarLineas(true); }   // v3.5: se pinta al abrirla
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
            if (this.estado) { this._pintar(); }   // v3.6.1: Caja / Validar dicen ya «Esperando conexión…»
        }
        clearTimeout(this.timerReintento);
        this.timerReintento = setTimeout(function () { self._probarConexion(); }, REINTENTO_MS);
    },

    _probarConexion: function () {
        var self = this;
        if (!this.sinRed || !this._out()) { return; }
        // v3.29: con tiempo máximo (_post) y mirando si mientras tanto la OUT se ha validado
        return this._post('/koroshi/preparacion/cargar', _.extend(this._obj(this._out().id), {
            employee_id: this.operario ? this.operario.id : false}))
            .then(function (r) {
                if (!r || !r.ok) { return self._sinConexion(); }
                clearTimeout(self.timerReintento);
                self.sinRed = false;
                self.$('.o_kp_offline').hide();
                self._estadoLector();
                self.$el.removeClass('o_kp_sin_red');
                self._aplicar(r.estado);   // v3.6: con lo pendiente sumado
                if (self._outTerminada()) { return; }   // v3.29
                self._pintar();
                self._aviso('Conexión recuperada.' + (self.cola.length ? ' Guardando lo leído…' : ' Ya puedes leer.'), 'ok');
                self._pitido(true);
                self._enviar();   // la lectura que se quedó a medias (mismo id: no cuenta dos veces)
            }, function (err) {
                if (err && err.sesion) {
                    self.sesionCaducada = true;
                    self._aviso('La sesión de Odoo ha caducado: vuelve a entrar. Lo leído está guardado en la PDA.', 'mal');
                }
                self._sinConexion();
            });
    },

    // v3.29: la OUT (o la agrupación) ya está validada o cancelada: «✓ … validada» y vuelta a Lecturas. Lo que
    // quedaba en la cola se manda igual (Odoo lo apunta como rechazado de cola) desde la memoria, en segundo plano.
    _outTerminada: function () {
        var self = this;
        var out = this.estado && this.estado.out;
        if (!out || (out.estado !== 'done' && out.estado !== 'cancel')) { return false; }
        clearTimeout(this.timerReintento);
        if (this.cola.length) {
            var clave = this._claveMemoria();
            var items = (this._leerMemoria()[clave] || []).map(function (i) { return _.omit(i, 'rechazo'); });
            this.cola = [];
            this._vaciarOtra(clave, items);
        }
        this._capa('✓ ' + out.name + (out.estado === 'done' ? ' validada' : ' cancelada'), true);
        this.timerVolver = setTimeout(function () { self.trigger_up('history_back'); }, VOLVER_MS);
        return true;
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
        this.$('.o_kp_nota').text(out.nota || '').toggle(!!out.nota);   // v3.7 (v3.9: el «NOTA» lo pone el CSS)
        // v3.3: preparar a dos -> quién va con quién y por dónde empieza cada uno
        var quien = this.operario ? this.operario.nombre : 'Sin tarjeta';
        if (e.a_dos) {
            quien += e.rol === 'ayudante' ? ' · 2ª mitad' : ' · 1ª mitad';   // v3.4: la OUT partida por la mitad
            if (e.companeros && e.companeros.length) { quien += ' · con ' + e.companeros.join(', '); }
        }
        this.$('.o_kp_operario').text(quien);
        this.$('.o_kp_pausa_btn').toggle(!!this.operario);   // v3.30
        this.$el.toggleClass('o_kp_a_dos', !!e.a_dos).toggleClass('o_kp_ayudante', e.rol === 'ayudante');
        this._avisosEquipo(e);
        // progreso
        var pct = e.pedidas ? Math.round(100 * Math.min(e.leidas, e.pedidas) / e.pedidas) : 0;
        this.$('.o_kp_barra_lleno').css('width', pct + '%');
        var pendientes = this._pendientes();   // v3.6
        this.$('.o_kp_progreso_texto').text(e.leidas + ' de ' + e.pedidas + ' uds' +
            (pendientes ? ' · ' + pendientes + (pendientes === 1 ? ' guardándose' : ' guardándose') : ''));
        // v3.1: con 0 leídas no se dice nada de cajas («Todo en caja» confundía)
        var txtCaja = e.sin_caja ? 'Sin caja: ' + e.sin_caja + (e.sin_caja === 1 ? ' ud' : ' uds')
            : (e.leidas ? '✓ Todo en caja' : '');
        if (e.a_dos && e.sin_caja) {
            // v3.3: cada uno cierra su caja solo con lo que ha leído él
            txtCaja = 'Tuyas sin caja: ' + e.mias_sin_caja + (e.otros_sin_caja ? ' · compañero: ' + e.otros_sin_caja : '');
        }
        if (out.con_caja === false) { txtCaja = ''; }   // v3.14: INT, sin caja
        this.$('.o_kp_sin_caja').text(txtCaja).toggleClass('o_kp_hay', !!e.sin_caja).toggle(!!txtCaja);
        this.$('.o_kp_cajas_resumen').text(e.cajas.length ? e.cajas.length + (e.cajas.length === 1 ? ' caja' : ' cajas') : '');
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
            var destino = this._destino(sig);   // v3.15: agrupación -> a qué caja de tienda va
            this.$('.o_kp_destino').text(destino ? '→ ' + destino : '').toggle(!!destino);
            // v3.9.2: hueco (lineal, palet, columna) y caja KO en la misma línea y del mismo tamaño
            var ubi = this._partesUbicacion(sig);
            var $u = this.$('.o_kp_ubicacion').empty();
            if (ubi.hueco && this.color === 'e') {
                // v3.21: E = cada parte del hueco (L24, P19, C2, MU-02...) en su casilla
                var $cas = $('<span class="o_kp_casillas"/>').appendTo($u);
                ubi.hueco.split(/\s+/).forEach(function (t) {
                    var mm = /^([A-Za-z]+)-?(\d+)$/.exec(t);
                    var $c = $('<span class="o_kp_casilla"/>').appendTo($cas);
                    $('<small/>').text(mm ? mm[1].toUpperCase() : '').appendTo($c);
                    $('<span/>').text(mm ? mm[2] : t).appendTo($c);
                });
            } else if (ubi.hueco) {
                $('<span class="o_kp_hueco"/>').text(ubi.hueco).appendTo($u);
            }
            $('<span class="o_kp_ko"/>').text(sig.ubicacion).appendTo($u);
            this.$('.o_kp_ubi_detalle').text(ubi.detalle);
            var aqui = esLaQueToca && !sig.completa ? this._aquiMismo(sig) : 0;   // v3.13
            if (aqui) {
                $('<span class="o_kp_aqui"/>').text('AQUÍ MISMO: ' + aqui + ' más').appendTo(this.$('.o_kp_ubi_detalle'));
            }
            // v3.1: nombre una sola vez y en grande, talla destacada, referencia solo si es distinta
            this.$('.o_kp_producto_ref').text(sig.nombre || sig.producto);
            this.$('.o_kp_talla').text(sig.talla || '');
            this.$('.o_kp_talla_fila').toggle(!!sig.talla);
            this.$('.o_kp_producto').text(sig.ref ? 'Ref. ' + sig.ref : '').toggle(!!sig.ref);
            // v3.9: número grande «1 de 5» y una barrita por ud (hasta 20)
            var $c = this.$('.o_kp_cuantas').empty();
            $('<span class="o_kp_n"/>').text(sig.leidas).appendTo($c);
            $('<span class="o_kp_de"/>').text('de ' + sig.pedidas + (sig.completa ? ' ✓' : '')).appendTo($c);
            if (sig.caja) {
                var $cc = $('<span class="o_kp_cuantas_caja"/>').text('En la caja ' + sig.caja).appendTo($c);
                // v3.28.1: ✎ aquí mismo (sacar de la caja / otra caja), sin entrar en la lista
                $('<button type="button" class="o_kp_l_editar o_kp_editar_tarjeta" aria-label="Cambiar de caja"/>')
                    .attr('data-id', sig.id).text('✎').toggle(this.modo === 'leer').appendTo($cc);
            }
            var $s = this.$('.o_kp_segmentos').empty();
            if (sig.pedidas > 1 && sig.pedidas <= 20) {
                for (var k = 0; k < sig.pedidas; k++) {
                    $('<span/>').toggleClass('o_kp_seg_ok', k < sig.leidas).appendTo($s);
                }
            }
            // v3.7: «Poner cantidad» si faltan 2 o más; v3.9.3: se ve siempre (antes, solo tras leer una), pero si aún
            // no se ha leído ninguna con la pistola avisa en vez de abrir
            this.$('.o_kp_cantidad_btn').toggle(this.modo === 'leer' && !sig.caja && sig.pedidas - sig.leidas >= 2)
                .toggleClass('o_kp_cant_bloqueado', sig.leidas < 1);
            // v3.1: sin foto no se pinta nada (ni el icono gris de Odoo): el texto ocupa todo el ancho
            var conFoto = sig.tiene_foto !== false && !!sig.producto_id;
            // v3.9.2: 512 px (con 256 se veía borrosa a 150 px en pantallas de PDA de alta densidad)
            var src = conFoto ? '/web/image/product.product/' + sig.producto_id + '/image_512' : '';
            var $f = this.$('.o_kp_foto');
            if ($f.attr('src') !== src) {
                $f.hide();
                if (src) { $f.attr('src', src); } else { $f.removeAttr('src'); }
            }
            if (!conFoto) { $f.hide(); }
            this.$('.o_kp_siguiente').toggleClass('o_kp_vista_hecha', !!sig.completa)
                .toggleClass('o_kp_vista_otra', !esLaQueToca).show();
            this._ajustarUbicacion();   // v3.9.2: ya visible, se puede medir
            this.$('.o_kp_ir_pendiente').text(e.todo_leido ? 'Volver al resumen ▸' : 'Ir a la que toca ▸')
                .toggle(!esLaQueToca);
            this.$('.o_kp_completa').hide();
            if (sig.producto_id) { this.fotosBajadas[sig.producto_id] = true; }
            this._precargarFoto(e, sig);           // v3.5
            if (this.modo === 'leer' && this.altVista !== sig.id + ':' + sig.leidas) {
                this.altVista = sig.id + ':' + sig.leidas;
                this._precargarAlternativas(sig);  // v3.5
            }
        } else {
            this.$('.o_kp_siguiente').hide();
            this.$('.o_kp_completa_texto').text(e.todo_leido
                ? (e.a_dos && e.sin_caja && !e.mias_sin_caja ? 'Falta que tu compañero cierre su caja.'
                    : (e.sin_caja ? 'Pulsa «Caja» y lee la etiqueta. Después, Validar.' : 'Pulsa «Validar».'))
                : 'Lo que queda ya está en caja o se marca con «Faltante».');
            this.$('.o_kp_completa').show();
        }
        // botones
        // v3.6: sin red se sigue leyendo (y deshaciendo lo no guardado); v3.22: y cerrando cajas. Validar espera a Odoo
        var libre = this.modo === 'leer';
        var conRed = !this.sinRed;
        var guardando = this.cola.length > 0 || this.enviando;
        var mias = e.a_dos ? e.mias_sin_caja : e.sin_caja;   // v3.3: a dos, solo lo suyo
        this.$('.o_kp_caja').toggle(out.con_caja !== false)   // v3.14: en las INT no hay botón Caja
            .prop('disabled', !libre || !mias)   // v3.22: también sin red (Odoo la cierra al volver)
            .text(conRed ? 'Caja' : 'Caja (sin red)')
            .toggleClass('o_kp_destacado', !!mias && e.todo_leido);
        var armado = this.incompletoOut === out.id;   // v3.27: Zalando / About You, validar incompleto
        this.$('.o_kp_validar').prop('disabled', !libre || !conRed || guardando || !!e.sin_caja || !e.leidas)
            .text(!conRed ? 'Esperando conexión…' : (guardando ? 'Guardando lecturas…' :
                  (armado ? '⚠ Validar incompleto' : '✓ Validar')))
            .toggleClass('o_kp_incompleto', armado)
            .toggleClass('o_kp_destacado', conRed && !guardando && !e.sin_caja && e.todo_leido);
        this.$('.o_kp_deshacer').prop('disabled', !libre || !e.leidas || (!conRed && !this.cola.length));
        this.$('.o_kp_faltante').prop('disabled', !libre || !conRed || e.todo_leido || !e.siguiente_id);
        this._pintarLineas();
    },

    // v3.9: lo que va encima del código de la ubicación, como en la etiqueta del rack: nave y hueco
    // («EFFEC/Stock/NAVE2/08981 - L107 P37 C1/KO_260926_001» -> «NAVE2 · 08981 - L107 P37 C1»)
    _detalleUbicacion: function (l) {
        return this._partesUbicacion(l).detalle;
    },

    // v3.9.2: «EFFEC/Stock/NAVE2/08981 - L107 P37 C1/KO_260926_001» ->
    //   hueco «L107 P37 C1» (va grande al lado del KO) y detalle «NAVE2 · 08981» (va pequeño encima)
    _partesUbicacion: function (l) {
        var partes = String(l.ubicacion_completa || '').split('/').filter(function (x) {
            return x && x !== 'EFFEC' && x !== 'Stock';
        });
        partes.pop();                                   // la propia ubicación (el KO): ya se pinta
        var padre = partes.length ? partes[partes.length - 1] : '';
        var hueco = '';
        var m = /^(\d+)\s*-\s*(.+)$/.exec(padre);
        if (m) {
            hueco = m[2];
            partes[partes.length - 1] = m[1];
        } else if (padre && !/^NAVE/i.test(padre)) {
            hueco = padre;
            partes.pop();
        }
        return {hueco: hueco, detalle: partes.join(' · ')};
    },

    // v3.9.2: la ubicación siempre en una línea: baja la letra hasta que quepa (PDA de 360 a 480 px de ancho)
    /** v3.12: las ubicaciones de «Prueba en» en una línea: baja la letra hasta que caben. */
    _ajustarFaltante: function () {
        this.$('.o_kp_f_alt_ubi').each(function (i) {
            if (!this.offsetWidth) { return; }
            var fs = i === 0 ? 30 : 20;
            this.style.fontSize = fs + 'px';
            while (this.scrollWidth > this.clientWidth && fs > 14) {
                fs -= 1;
                this.style.fontSize = fs + 'px';
            }
        });
    },

    _ajustarUbicacion: function () {
        var el = this.$('.o_kp_ubicacion')[0];
        if (!el || !el.offsetWidth) { return; }
        if (this.color === 'e') { el.style.fontSize = ''; return; }   // v3.21: las casillas ya caben
        var fs = this.color === 'f' ? 44 : 30;                         // v3.21: F = el hueco muy grande
        el.style.fontSize = fs + 'px';
        while (el.scrollWidth > el.clientWidth && fs > 15) {
            fs -= 1;
            el.style.fontSize = fs + 'px';
        }
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

    _pintarLineas: function (forzar) {
        var e = this.estado;
        var $l = this.$('.o_kp_lineas');
        // v3.5: cerrada no se pinta (con 100+ líneas cada lectura repintaba todo); se pinta al abrirla
        this.listaSucia = !forzar && !$l.is(':visible');
        if (!this.listaSucia) { this._llenarLineas($l.empty(), e); }
        var $c = this.$('.o_kp_cajas').empty();
        if (e.cajas.length) {
            $c.text('Cajas cerradas: ' + e.cajas.map(function (c) { return c.nombre + ' (' + c.uds + ')'; }).join(', '));
        }
        this._pintarBotonLineas();
    },

    _llenarLineas: function ($l, e) {
        var self = this;
        e.lineas.forEach(function (l) {
            var $li = $('<li/>').attr('data-id', l.id).toggleClass('o_kp_hecha', l.completa)
                .toggleClass('o_kp_ahora', l.id === e.siguiente_id);
            $('<span class="o_kp_l_marca" role="presentation"/>').text(l.completa ? '✓' : '').appendTo($li);
            if (l.producto_id && l.tiene_foto !== false) {
                // v3.0.1: miniatura (solo se descarga al abrir la lista)
                $('<img class="o_kp_l_foto" alt="" loading="lazy"/>')
                    .attr('src', '/web/image/product.product/' + l.producto_id + '/image_128')
                    .on('error', function () { $(this).css('visibility', 'hidden'); }).appendTo($li);
            }
            var $t = $('<span class="o_kp_l_texto"/>').appendTo($li);
            $('<span class="o_kp_l_ubi"/>').text(l.ubicacion).appendTo($t);
            $('<span class="o_kp_l_prod"/>').text((l.nombre || l.producto) + (l.talla ? ' · Talla ' + l.talla : '')).appendTo($t);
            var destino = self._destino(l);   // v3.15
            if (destino) { $('<span class="o_kp_l_destino"/>').text('→ ' + destino).appendTo($t); }
            if (l.caja) { $('<span class="o_kp_l_caja"/>').text('Caja ' + l.caja).appendTo($t); }
            $('<span class="o_kp_l_cant"/>').text(l.leidas + '/' + l.pedidas).appendTo($li);
            if (l.caja && l.leidas > 0 && !self._esLote()) {
                // v3.21: cambiar de caja lo que ya está en una caja cerrada
                $('<button type="button" class="o_kp_l_editar" aria-label="Cambiar de caja"/>').text('✎')
                    .attr('data-id', l.id).appendTo($li);
            }
            $l.append($li);
        });
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

    _aviso: function (texto, clase, fijo) {
        var self = this;
        clearTimeout(this.timerAviso);
        var $a = this.$('.o_kp_aviso').empty();
        var tipo = clase || 'info';
        $a.attr('class', 'o_kp_aviso' + (texto ? ' o_kp_' + tipo : ''));
        if (!texto) { return; }
        $('<span class="o_kp_aviso_icono" role="presentation"/>').text(ICONOS[tipo] || ICONOS.info).appendTo($a);
        $('<span/>').text(texto).appendTo($a);
        if (tipo === 'ok' && !fijo) {   // v3.15: fijo = se queda hasta el siguiente aviso
            this.timerAviso = setTimeout(function () { self._aviso('', ''); }, AVISO_OK_MS);
        }
    },

    _foco: function () {
        if (this.modo === 'cantidad') { return; }   // v3.7: no quitar el foco al número
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
        this.$('.o_kp_lector_texto').text(listo ? 'Lector preparado' : 'Sin conexión · lo leído se guarda en la PDA');
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
        this._sonar(bien ? 'ok' : 'error');
    },

    // v3.13: un sonido distinto para cada caso (se distingue sin mirar la pantalla):
    //   ok     = pip corto (una ud bien leída)
    //   linea  = dos notas que suben (línea completa: ve a la siguiente)
    //   caja   = tres notas que suben (caja cerrada)
    //   error  = zumbido grave largo (no cuenta)
    _sonar: function (tipo) {
        var SONIDOS = {
            ok: {vibrar: 60, notas: [[880, 0, 0.09]]},
            linea: {vibrar: [60, 50, 60], notas: [[880, 0, 0.09], [1320, 0.11, 0.14]]},
            caja: {vibrar: [60, 40, 60, 40, 60], notas: [[660, 0, 0.1], [880, 0.12, 0.1], [1320, 0.24, 0.2]]},
            error: {vibrar: [120, 80, 120], tipo: 'square', notas: [[220, 0, 0.4]]},
        };
        var s = SONIDOS[tipo] || SONIDOS.ok;
        this._vibrar(s.vibrar);
        if (!this.sonido) { return; }
        try {
            var Ctx = window.AudioContext || window.webkitAudioContext;
            if (!Ctx) { return; }
            if (!this.audio) { this.audio = new Ctx(); }
            var ctx = this.audio;
            if (ctx.state === 'suspended' && ctx.resume) { ctx.resume(); }
            s.notas.forEach(function (n) {
                var o = ctx.createOscillator();
                var g = ctx.createGain();
                o.type = s.tipo || 'sine';
                o.frequency.value = n[0];
                g.gain.value = 0.2;
                o.connect(g);
                g.connect(ctx.destination);
                o.start(ctx.currentTime + n[1]);
                o.stop(ctx.currentTime + n[1] + n[2]);
            });
        } catch (e) { /* sin sonido */ }
    },

    // ------------------------------------------------------------ v3.22: alarma de parado
    // Algo ha contado (prenda, caja, cantidad, faltante): vuelve a contar desde ahora y se para la alarma.
    _actividad: function () {
        this.ultimaActividad = Date.now();
        if (this.alarmaOn) { this._alarma(false); }
    },

    _mirarAlarma: function () {
        var e = this.estado;
        if (e && typeof e.alarma_min === 'number') { this.alarmaMin = e.alarma_min; }
        if (e && e.alarma_horario) { this.alarmaHorario = e.alarma_horario; }   // v3.23
        var enHorario = this._enHorario();
        var out = this._out();
        var abierta = !!out && out.estado !== 'done' && out.estado !== 'cancel';
        var toca = this.alarmaMin > 0 && abierta && this._visible() && this.modo !== 'validando' && !this.packVolver &&
            enHorario && !this.enPausa;   // v3.30: en pausa no suena
        if (!toca) {
            this._alarma(false);
            // v3.23: fuera de horario (pausa, comida) tampoco cuenta: a las 10:15 o a las 14:00 empieza de cero
            if (!this._visible() || this.modo === 'validando' || !enHorario || this.enPausa) {
                this.ultimaActividad = Date.now();
            }
            return;
        }
        var parado = Date.now() - this.ultimaActividad;
        if (parado >= this.alarmaMin * 60000) {
            this._alarma(true, Math.floor(parado / 60000));
        }
    },

    // v3.23: ¿la hora de la PDA está dentro de algún tramo del horario?
    _enHorario: function () {
        var tramos = this.alarmaHorario;
        if (!tramos || !tramos.length) { return true; }
        var d = new Date();
        var m = d.getHours() * 60 + d.getMinutes();
        return tramos.some(function (t) { return m >= t[0] && m < t[1]; });
    },

    _alarma: function (on, minutos) {
        if (on) {
            this.$('.o_kp_alarma_min').text(minutos || this.alarmaMin);
            if (this.alarmaOn) { return; }
            this.alarmaOn = true;
            this.$('.o_koroshi_preparacion').addClass('o_kp_alarma');
            this.$('.o_kp_alarma_aviso').show();
            this._sirena();
            this.timerSirena = setInterval(this._sirena.bind(this), SIRENA_MS);
            return;
        }
        if (!this.alarmaOn) { return; }
        this.alarmaOn = false;
        clearInterval(this.timerSirena);
        this.$('.o_koroshi_preparacion').removeClass('o_kp_alarma');
        this.$('.o_kp_alarma_aviso').hide();
        try { if (navigator.vibrate) { navigator.vibrate(0); } } catch (e) { /* nada */ }
    },

    // Un ciclo de sirena (~0,9 s): dos tonos agudos de onda cuadrada que se alternan, al máximo del navegador
    // (gain 1). Es lo más fuerte que puede sacar una página web; el volumen del sistema lo pone el Android.
    _sirena: function () {
        try { if (navigator.vibrate) { navigator.vibrate([450, 100, 350]); } } catch (e) { /* nada */ }
        try {
            var Ctx = window.AudioContext || window.webkitAudioContext;
            if (!Ctx) { return; }
            if (!this.audio) { this.audio = new Ctx(); }
            var ctx = this.audio;
            if (ctx.state === 'suspended' && ctx.resume) { ctx.resume(); }
            var t0 = ctx.currentTime + 0.02;
            var g = ctx.createGain();
            g.gain.value = 1;
            g.connect(ctx.destination);
            for (var i = 0; i < 6; i++) {
                var o = ctx.createOscillator();
                o.type = 'square';
                o.frequency.value = i % 2 ? 2300 : 3100;
                o.connect(g);
                o.start(t0 + i * 0.15);
                o.stop(t0 + i * 0.15 + 0.14);
            }
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

// v3.14: lo que Lecturas tiene precargado para abrir al momento (la pantalla y la OUT que toca)
var PRECARGA_MS = 90000;
var accionPreparar = null;

Operarios.include({
    /** v3.26: vuelve de la preparación tras la pausa: la PDA queda libre (como la pausa de Lecturas). */
    on_attach_callback: function () {
        var p = window.koroshiPausaHecha;
        if (p) {
            window.koroshiPausaHecha = null;
            this._olvidarOperario();
        }
        var res = this._super.apply(this, arguments);
        if (p) { this._aviso('⏸ Pausa, ' + p.nombre + '. ' + p.msg + '.', 'info'); }
        return res;
    },

    /** v3.14: con la OUT que toca a la vista, se carga ya en segundo plano (pantalla y OUT): Continuar abre al momento. */
    _precargar: function (obj) {
        var self = this;
        if (!obj || obj.tipo !== 'out' || !this.operario || this.sinRed) { return; }
        var ref = obj.picking_name || obj.ref;
        var emp = this.operario.id;
        var p = this.precarga;
        if (p && p.ref === ref && p.emp === emp && (p.cargando || Date.now() - p.t < PRECARGA_MS / 2)) { return; }
        var nueva = {ref: ref, emp: emp, t: Date.now(), cargando: true};
        this.precarga = nueva;
        var accion = accionPreparar ? Promise.resolve(accionPreparar) :
            this._rpc({route: '/web/action/load', params: {action_id: 'koroshi_preparacion.action_koroshi_preparacion_pantalla'}},
                      {shadow: true}).then(function (a) { accionPreparar = a; return a; });
        return accion.then(function () {
            return self._rpc({route: '/koroshi/preparacion/modo', params: {employee_id: emp, picking_name: ref}}, {shadow: true});
        }).then(function (r) {
            if (!r || !r.propia) { nueva.propia = false; return; }
            nueva.propia = true;
            return self._rpc({route: '/koroshi/preparacion/cargar', params: {picking_name: ref, employee_id: emp}},
                             {shadow: true}).then(function (c) { if (c && c.ok) { nueva.estado = c.estado; } });
        }).then(function () {
            nueva.cargando = false;
            nueva.t = Date.now();
        }, function () {
            if (self.precarga === nueva) { self.precarga = null; }
        });
    },

    _pintarActual: function () {
        var res = this._super.apply(this, arguments);
        if (this.actual && !this.ocupado) { this._precargar(this.actual); }   // v3.14
        return res;
    },

    _mostrarHecho: function (ref, siguiente) {
        var res = this._super.apply(this, arguments);
        if (siguiente) { this._precargar(siguiente); }   // v3.14: la siguiente, mientras cuenta 3 s
        return res;
    },

    _abrir: function (obj) {
        var self = this;
        var deSiempre = this._super.bind(this);
        if (obj && obj.tipo === 'agrupacion' && obj.batch_id && this.operario && !this.sinRed) {
            return this._abrirLote(obj, deSiempre);   // v3.15: agrupación Z- entera en la pantalla nueva
        }
        if (!obj || obj.tipo !== 'out' || !this.operario || this.sinRed) {
            return deSiempre(obj);
        }
        var ref = obj.picking_name || obj.ref;
        var p = this.precarga;
        if (p && p.ref === ref && p.emp === this.operario.id && !p.cargando && Date.now() - p.t < PRECARGA_MS) {
            // v3.14: ya precargada: sin preguntar ni esperar a Odoo
            this.precarga = null;
            if (!p.propia) { return deSiempre(obj); }
            this.ocupado = true;
            this._mostrarAbriendo(ref, this.operario.nombre);
            return this.do_action(accionPreparar ? _.extend({}, accionPreparar) :
                                  'koroshi_preparacion.action_koroshi_preparacion_pantalla', {
                additional_context: {
                    preparacion_out: ref,
                    preparacion_operario: {id: this.operario.id, nombre: this.operario.nombre},
                    preparacion_estado: p.estado || false,
                },
            }).then(function () { self.ocupado = false; }).guardedCatch(function () {
                self.ocupado = false;
                return deSiempre(obj);
            });
        }
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

    /** v3.15: agrupación Z- (tarea o asignación de tipo 'agrupacion'): si el operario está activado y la agrupación
     * se puede preparar aquí (parámetro koroshi_preparacion.agrupaciones), la pantalla nueva con la agrupación entera;
     * si no, la app de código de barras como siempre. */
    _abrirLote: function (obj, deSiempre) {
        var self = this;
        var ref = obj.ref || '';
        this.ocupado = true;
        return this._rpc({route: '/koroshi/preparacion/modo',
                          params: {employee_id: this.operario.id, lote_id: obj.batch_id}}, {shadow: true})
            .then(function (r) {
                if (!r || !r.propia) {
                    self.ocupado = false;
                    return deSiempre(obj);
                }
                self._mostrarAbriendo(ref, self.operario.nombre);
                return self.do_action('koroshi_preparacion.action_koroshi_preparacion_pantalla', {
                    additional_context: {
                        preparacion_lote: {id: obj.batch_id, name: ref},
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
        if (this.desdePreparacion && this.out && !this.ocupado && this.paso !== 'validada') {
            // v3.15: antes que la agrupación: si venía de la pantalla nueva (OUT o agrupación Z-), vuelve a ella
            return this.trigger_up('history_back');
        }
        if (!this.out || this.ocupado || this.paso === 'validada') {
            return deSiempre();
        }
        var emp = this._empleadoId ? this._empleadoId() : false;
        if (!emp) { return deSiempre(); }
        // v3.15: la agrupación Z- de esta OUT (o la agrupación leída) también vuelve a la pantalla nueva
        var loteId = this.out.lote_id || this.out.batch_id || false;
        var loteName = this.out.batch_name || this.out.name;
        var pregunta = loteId ? {employee_id: emp, lote_id: loteId} : {employee_id: emp, picking_name: this.out.name};
        return this._rpc({route: '/koroshi/preparacion/modo', params: pregunta}, {shadow: true})
            .then(function (r) {
                if (!r || !r.propia) { return deSiempre(); }
                var ctx = {
                    preparacion_operario: self.operario ? {id: self.operario.id, nombre: self.operario.nombre} : false,
                };
                if (loteId) {
                    ctx.preparacion_lote = {id: loteId, name: loteName};
                } else {
                    ctx.preparacion_out = self.out.name;
                }
                return self.do_action('koroshi_preparacion.action_koroshi_preparacion_pantalla', {
                    additional_context: ctx,
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
