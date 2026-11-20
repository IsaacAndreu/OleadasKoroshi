odoo.define('koroshi_actividades.InicioPda', function (require) {
'use strict';
/* KOROSHI Actividades v1.6.0 - «Inicio (PDA)»: entrada única por áreas (acción de cliente).
 * Diseño: bin/versiones/diseno-pda-entrada-unica_2026-11-20_v2.md (Isaac, 20/11).
 *
 * - Pasa tu tarjeta (lector o escribir el código + Intro). La tarjeta es la misma que en Lecturas, Contenedores y
 *   Faltante: memoria de la PDA, clave koroshi_operarios_pda_<usuario>, {id, nombre, t}. Si ya está puesta y es
 *   reciente (koroshi_operarios.minutos_tarjeta, 60 min), entra sin pasarla.
 * - Un botón por área: Recepciones, Picking, Compactación, Devoluciones, Inversa, Expediciones y Extra (las que
 *   tienen alguna actividad). Un área con una sola actividad entra directamente; con varias, sale la lista.
 *   Entrar = empieza el tiempo de esa actividad (el anterior se cierra solo) y abre su pantalla si la tiene.
 * - Pausa (el tiempo se para), Salir (para el tiempo y olvida la tarjeta) y «Gestión» solo para los jefes.
 * - «¿Sigues?»: si el servidor lo pregunta (desde las 13:00, 30 min sin señal), aviso rojo y pitido cada minuto;
 *   pasar la tarjeta es «Sigo».
 *
 * Además (InicioPdaGlobal, abajo), en todas las pantallas del navegador que ha pasado por el Inicio:
 * - botón «◀ Áreas» abajo a la izquierda para volver (no dentro de un pedido abierto ni con una ventana encima);
 * - señal de vida: si la tarjeta se ha usado en otra pantalla (Lecturas, Contenedores...) en los últimos minutos, el
 *   tramo abierto cuenta como «Sigo» y el «¿Sigues?» no lo cierra.
 * Sin librerías externas. Todo dentro de .o_koroshi_inicio. Nada de aria-hidden (Odoo 13 lo oculta).
 */
var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var session = require('web.session');

var REPETIDA_MS = 700;          // la misma lectura dos veces seguidas (bus + campo) cuenta una
var REFRESCO_MS = 60000;        // estado del servidor (tiempo, «¿Sigues?»)
var PITIDO_SIGUES_MS = 60000;
var CLAVE_FIJO = 'koroshi_actividades_fijo';    // persona de la pantalla de Actividades (inversa)
var CLAVE_INICIO = 'koroshi_inicio_pda';        // sessionStorage: este navegador usa el Inicio (botón «◀ Áreas»)
var PERSONA_MS = 60 * 60000;    // se cambia con /koroshi/operarios/minutos_tarjeta

function _e(t) { return _.escape(t == null ? '' : String(t)); }

function _fecha(utc) {
    return utc ? new Date(utc.replace(' ', 'T') + 'Z') : null;
}

function _hora(utc) {
    var d = _fecha(utc);
    return d ? d.toLocaleTimeString('es-ES', {hour: '2-digit', minute: '2-digit'}) : '';
}

function _hm(minutos) {
    minutos = Math.max(0, Math.round(minutos || 0));
    var h = Math.floor(minutos / 60), m = minutos % 60;
    return h ? h + ' h ' + (m < 10 ? '0' : '') + m + ' min' : m + ' min';
}

function _iniciales(nombre) {
    var p = (nombre || '').split(/\s+/).filter(Boolean);
    if (!p.length) { return '?'; }
    return (p.length === 1 ? p[0].slice(0, 2) : p[0][0] + p[1][0]).toUpperCase();
}

function claveTarjeta() {
    return 'koroshi_operarios_pda_' + (session.uid || '');
}

function leerTarjeta() {
    try {
        var v = window.localStorage.getItem(claveTarjeta());
        return v ? JSON.parse(v) : null;
    } catch (e) { return null; }
}

var InicioPda = AbstractAction.extend({
    contentTemplate: 'koroshi_actividades.InicioPda',
    events: {
        'keydown .o_ki_codigo': '_onKeydown',
        'click .o_ki_area': '_onArea',
        'click .o_ki_act': '_onActividad',
        'click .o_ki_cerrar_panel': '_onCerrarPanel',
        'click .o_ki_pausa': '_onPausa',
        'click .o_ki_salir': '_onSalir',
        'click .o_ki_enlace': '_onEnlace',
        'click .o_ki_lector': '_foco',
        'click .o_ki_aviso': '_onAviso',
        'pointerdown': '_marcar',
    },

    init: function () {
        this._super.apply(this, arguments);
        this.persona = null;        // {id, nombre}
        this.datos = null;          // respuesta del servidor: persona, areas, gestion
        this.leidoEn = 0;           // Date.now() de la última respuesta (para que corra el tiempo)
        this.desfase = 0;
        this.panel = null;          // código del área con la lista abierta
        this.ocupado = false;
        this.ultima = {codigo: '', t: 0};
        this.salirEn = 0;           // primer toque en Salir (el segundo confirma)
        this.pitadoEn = 0;
    },

    start: function () {
        var self = this;
        core.bus.on('barcode_scanned', this, this._onBarcode);
        try { window.sessionStorage.setItem(CLAVE_INICIO, '1'); } catch (e) { /* nada */ }
        return this._super.apply(this, arguments).then(function () {
            self._tomarTarjeta();
            self._leerMinutos();
            self._pintar();
            self._refrescar();
            self.timer = setInterval(self._vigilar.bind(self), 15000);
            self.timerRefresco = setInterval(self._refrescar.bind(self), REFRESCO_MS);
            self._foco();
        });
    },

    on_attach_callback: function () {
        this._super.apply(this, arguments);
        // v1.8.2: también si la persona ya estaba (volver con «◀ Áreas», recargar): sin datos se quedaba en «Cargando…»
        if (this._tomarTarjeta() || (this.persona && !this.datos)) { this._refrescar(); }
        this._foco();
    },

    destroy: function () {
        core.bus.off('barcode_scanned', this, this._onBarcode);
        clearInterval(this.timer);
        clearInterval(this.timerRefresco);
        clearTimeout(this.timerAviso);
        if (this.audio) { try { this.audio.close(); } catch (e) { /* nada */ } }
        this._super.apply(this, arguments);
    },

    // ------------------------------------------------------------ tarjeta compartida
    _tomarTarjeta: function () {
        var g = leerTarjeta();
        if (!g || !g.id) { return false; }
        if (g.t && Date.now() - g.t > PERSONA_MS) { return false; }
        if (this.persona && this.persona.id === g.id) { return false; }
        this.persona = {id: g.id, nombre: g.nombre};
        this.datos = null;
        return true;
    },
    _guardarTarjeta: function () {
        if (!this.persona) { return; }
        try {
            window.localStorage.setItem(claveTarjeta(), JSON.stringify(
                {id: this.persona.id, nombre: this.persona.nombre, t: Date.now()}));
        } catch (e) { /* sin memoria: solo en esta pantalla */ }
    },
    _olvidarTarjeta: function () {
        var g = leerTarjeta();
        try {
            if (!g || !this.persona || g.id === this.persona.id) {
                window.localStorage.removeItem(claveTarjeta());
            }
            window.localStorage.removeItem(CLAVE_FIJO);
        } catch (e) { /* nada */ }
        this.persona = null;
        this.datos = null;
        this.panel = null;
    },
    _marcar: function () {
        // tocar la pantalla con alguien dentro = actividad (la tarjeta no caduca)
        var g = leerTarjeta();
        if (this.persona && g && g.id === this.persona.id && (!g.t || Date.now() - g.t > 30000)) {
            this._guardarTarjeta();
        }
    },
    _leerMinutos: function () {
        var self = this;
        return this._rpc({route: '/koroshi/operarios/minutos_tarjeta', params: {}}, {shadow: true})
            .then(function (r) {
                if (r && r.ok && r.minutos > 0) { PERSONA_MS = r.minutos * 60000; }
            }).guardedCatch(function (e) {
                if (e && e.event && e.event.preventDefault) { e.event.preventDefault(); }
            });
    },
    _vigilar: function () {
        var g = leerTarjeta();
        if (this.persona && (!g || g.id !== this.persona.id)) {
            // otra pantalla ha cambiado de operario (o ha salido)
            this.persona = null;
            this.datos = null;
            this._tomarTarjeta();
            this._refrescar();
        } else if (this.persona && g && g.t && Date.now() - g.t > PERSONA_MS) {
            this._olvidarTarjeta();
            this._aviso('Sesión cerrada por inactividad. Pasa tu tarjeta.', 'info');
        } else if (this.persona && !this.datos) {
            this._refrescar();    // v1.8.2: red por si la primera carga no llegó
        }
        this._pintarAhora();
        this._avisarSigues();
    },

    // ------------------------------------------------------------ servidor
    _llamar: function (ruta, params) {
        var self = this;
        return this._rpc({route: ruta, params: params || {}}, {shadow: true}).then(function (r) {
            self.$('.o_ki_offline').removeClass('o_ki_si');
            return r;
        }, function (e) {
            if (e && e.event && e.event.preventDefault) { e.event.preventDefault(); }
            self.$('.o_ki_offline').addClass('o_ki_si');
            return {ok: false, msg: 'Sin conexión con Odoo. Prueba otra vez.'};
        });
    },
    _datos: function (r) {
        if (!r || !r.ok) { return false; }
        this.datos = r;
        this.leidoEn = Date.now();
        var ahora = _fecha(r.ahora);
        this.desfase = ahora ? ahora.getTime() - Date.now() : 0;
        if (r.persona) {
            this.persona = {id: r.persona.employee_id, nombre: r.persona.nombre};
        }
        return true;
    },
    _refrescar: function () {
        var self = this;
        // v1.8.2: sin datos se pide aunque la pantalla aún no esté puesta en la página. Al volver con la tarjeta ya
        // guardada, start() llega aquí antes de que Odoo enganche la pantalla y antes no se pedía nunca: «Cargando…».
        if (!this.persona || this.ocupado || !this.el || (this.datos && !$.contains(document, this.el))) {
            this._pintar();
            return Promise.resolve();
        }
        return this._llamar('/koroshi/actividades/inicio/estado', {employee_id: this.persona.id}).then(function (r) {
            if (r && r.ok) {
                self._datos(r);
            } else if (r && r.msg && r.msg.indexOf('tarjeta') >= 0) {
                self._olvidarTarjeta();
            }
            self._pintar();
        });
    },

    // ------------------------------------------------------------ lecturas
    _onBarcode: function (barcode) {
        if (!this.el || !$.contains(document, this.el)) { return; }   // no se ve: no es para nosotros
        this._leer(barcode);
    },
    _onKeydown: function (ev) {
        if (ev.key === 'Enter' || ev.keyCode === 13) {
            ev.preventDefault();
            var v = $(ev.currentTarget).val();
            $(ev.currentTarget).val('');
            this._leer(v);
        }
    },
    _leer: function (codigo) {
        var self = this;
        codigo = (codigo || '').trim();
        if (!codigo || this.ocupado) { return; }
        var ahora = Date.now();
        if (codigo === this.ultima.codigo && ahora - this.ultima.t < REPETIDA_MS) { return; }
        this.ultima = {codigo: codigo, t: ahora};
        this.ocupado = true;
        this._llamar('/koroshi/actividades/inicio/tarjeta', {codigo: codigo}).then(function (r) {
            self.ocupado = false;
            if (!self._datos(r)) {
                self._aviso((r && r.msg) || 'No se ha podido leer.', 'mal');
                return;
            }
            self._guardarTarjeta();
            self.panel = null;
            var p = r.persona;
            self._aviso(p.en_pda ? 'Hola, ' + p.nombre + '. Sigues en ' + p.area_nombre + '.'
                                 : 'Hola, ' + p.nombre + '. Elige dónde vas a trabajar.', 'ok');
            self._pintar();
        });
    },

    // ------------------------------------------------------------ botones
    _area: function (codigo) {
        return _.findWhere((this.datos && this.datos.areas) || [], {codigo: codigo});
    },
    _onArea: function (ev) {
        var area = this._area($(ev.currentTarget).data('area'));
        if (!area || this.ocupado) { return; }
        if (area.actividades.length === 1) {
            this._entrar(area.actividades[0].id);
        } else {
            this.panel = this.panel === area.codigo ? null : area.codigo;
            this._pintar();
        }
    },
    _onActividad: function (ev) {
        this._entrar($(ev.currentTarget).data('id'));
    },
    _onCerrarPanel: function () {
        this.panel = null;
        this._pintar();
    },
    _entrar: function (actividadId) {
        var self = this;
        if (!this.persona || this.ocupado) { return; }
        this.ocupado = true;
        this._llamar('/koroshi/actividades/inicio/entrar',
                     {employee_id: this.persona.id, actividad_id: actividadId}).then(function (r) {
            self.ocupado = false;
            if (!self._datos(r)) {
                self._aviso((r && r.msg) || 'No se ha podido entrar.', 'mal');
                return;
            }
            self._guardarTarjeta();
            self.panel = null;
            if (r.inversa) {
                // la pantalla de Actividades abre a esta persona sin volver a pasar la tarjeta
                try {
                    window.localStorage.setItem(CLAVE_FIJO, JSON.stringify(
                        {id: self.persona.id, nombre: self.persona.nombre}));
                } catch (e) { /* nada */ }
            }
            if (r.abre) {
                return self.do_action(r.abre, {clear_breadcrumbs: true});
            }
            self._aviso(r.msg + '. El tiempo cuenta desde ahora.', 'ok');
            self._pintar();
        });
    },
    _onPausa: function () {
        var self = this;
        if (!this.persona || this.ocupado) { return; }
        this.ocupado = true;
        this._llamar('/koroshi/actividades/inicio/pausa', {employee_id: this.persona.id}).then(function (r) {
            self.ocupado = false;
            if (r && r.ok) {
                self._datos(r);
                self._aviso(r.msg, 'info');
            } else {
                self._aviso((r && r.msg) || 'No se ha podido.', 'warn');
            }
            self._pintar();
        });
    },
    _onSalir: function () {
        var self = this;
        if (!this.persona) { return; }
        if (Date.now() - this.salirEn > 4000) {
            this.salirEn = Date.now();
            this.$('.o_ki_salir').text('¿Salir? Toca otra vez');
            setTimeout(function () { self.$('.o_ki_salir').text('Salir'); }, 4000);
            return;
        }
        this.salirEn = 0;
        var id = this.persona.id, nombre = this.persona.nombre;
        this._llamar('/koroshi/actividades/inicio/salir', {employee_id: id});
        this._olvidarTarjeta();
        this._aviso('Hasta luego, ' + nombre + '. La PDA queda libre.', 'ok');
        this._pintar();
    },
    _onEnlace: function (ev) {
        var self = this;
        if (!this.persona || this.ocupado) { return; }
        this._llamar('/koroshi/actividades/inicio/gestion',
                     {employee_id: this.persona.id, enlace_id: $(ev.currentTarget).data('id')}).then(function (r) {
            if (r && r.ok && r.abre) {
                return self.do_action(r.abre, {clear_breadcrumbs: true});
            }
            self._aviso((r && r.msg) || 'No se ha podido abrir.', 'mal');
        });
    },

    // ------------------------------------------------------------ pintar
    _onAviso: function () {
        this._aviso('');    // v1.8.2: el aviso va por encima de la cabecera; tocarlo lo quita
    },
    _aviso: function (texto, tipo) {
        var $a = this.$('.o_ki_aviso');
        clearTimeout(this.timerAviso);
        if (!texto) { $a.empty().removeClass('o_ki_si'); return; }
        $a.attr('class', 'o_ki_aviso o_ki_si o_ki_' + (tipo || 'info')).text(texto);
        if (tipo === 'ok' || tipo === 'info') {
            this.timerAviso = setTimeout(function () { $a.empty().removeClass('o_ki_si'); }, 6000);
        }
    },
    _foco: function () {
        var $c = this.$('.o_ki_codigo');
        if ($c.length && !this.persona) { $c.focus(); }
    },
    _minutosDesde: function (utc) {
        var d = _fecha(utc);
        return d ? (Date.now() + this.desfase - d.getTime()) / 60000 : 0;
    },
    _pintarAhora: function () {
        var p = this.datos && this.datos.persona;
        var $a = this.$('.o_ki_ahora');
        if (!p) { $a.empty(); return; }
        var html;
        if (p.situacion === 'trabajando') {
            html = '<span class="o_ki_ahora_txt">Ahora: <b>' + _e(p.area_nombre || p.actividad) + '</b>' +
                   (p.area_nombre && p.actividad !== p.area_nombre ? ' · ' + _e(p.actividad) : '') + '</span>' +
                   '<span class="o_ki_ahora_t">' + _hm(this._minutosDesde(p.desde)) + '</span>';
        } else if (p.situacion === 'pausa') {
            html = '<span class="o_ki_ahora_txt">En pausa desde las ' + _e(_hora(p.desde)) +
                   '. Toca un área para seguir.</span>';
        } else {
            html = '<span class="o_ki_ahora_txt">Elige dónde vas a trabajar.</span>';
        }
        $a.html(html);
        this.$('.o_ki_sigues').toggleClass('o_ki_si', !!(p.situacion === 'trabajando' && p.sigues));
    },
    _avisarSigues: function () {
        var p = this.datos && this.datos.persona;
        if (p && p.situacion === 'trabajando' && p.sigues && this.el && $.contains(document, this.el) &&
                Date.now() - this.pitadoEn >= PITIDO_SIGUES_MS) {
            this.pitadoEn = Date.now();
            this._pitar();
        }
    },
    _pitar: function () {
        try {
            var Ctx = window.AudioContext || window.webkitAudioContext;
            if (!Ctx) { return; }
            var ctx = this.audio || (this.audio = new Ctx());
            if (ctx.state === 'suspended' && ctx.resume) { ctx.resume(); }
            var t = ctx.currentTime;
            _.each([0, 0.3, 0.6], function (d) {
                var o = ctx.createOscillator(), g = ctx.createGain();
                o.type = 'square';
                o.frequency.value = 1800;
                g.gain.value = 0.3;
                o.connect(g);
                g.connect(ctx.destination);
                o.start(t + d);
                o.stop(t + d + 0.18);
            });
        } catch (e) { /* sin sonido: queda el aviso rojo */ }
    },
    _pintar: function () {
        var con = !!this.persona;
        this.$('.o_ki_lector').toggleClass('o_ki_oculto', con);
        this.$('.o_ki_menu').toggleClass('o_ki_oculto', !con);
        this.$('.o_ki_salir').toggleClass('o_ki_oculto', !con);
        this.$('.o_ki_avatar').text(con ? _iniciales(this.persona.nombre) : 'K');
        this.$('.o_ki_nombre').text(con ? this.persona.nombre : 'KOROSHI');
        if (!con) {
            this.$('.o_ki_areas, .o_ki_panel, .o_ki_gestion, .o_ki_ahora').empty();
            this.$('.o_ki_sigues').removeClass('o_ki_si');
            this._foco();
            return;
        }
        var d = this.datos;
        if (!d) {
            this.$('.o_ki_areas').html('<div class="o_ki_cargando">Cargando…</div>');
            return;
        }
        var actual = d.persona.situacion === 'trabajando' ? d.persona.area : null;
        var self = this;
        var areas = _.map(d.areas, function (a) {
            var cls = 'o_ki_area' + (a.codigo === actual ? ' o_ki_actual' : '') +
                      (a.codigo === self.panel ? ' o_ki_abierta' : '') + (a.codigo === 'extra' ? ' o_ki_extra' : '');
            var sub = a.codigo === 'extra' ? _.pluck(a.actividades, 'nombre').join(', ') :
                (a.actividades.length === 1 ? a.actividades[0].nota : a.actividades.length + ' tareas');
            return '<button type="button" class="' + cls + '" data-area="' + _e(a.codigo) + '" style="border-color:' +
                   _e(a.color) + '"><span class="o_ki_area_nombre">' + _e(a.nombre) +
                   (a.codigo === actual ? ' <span class="o_ki_punto" role="presentation">●</span>' : '') +
                   '</span><span class="o_ki_area_sub">' + _e(sub || '') + '</span></button>';
        });
        this.$('.o_ki_areas').html(areas.join(''));
        var panel = this.panel && this._area(this.panel);
        if (panel) {
            var actId = d.persona.situacion === 'trabajando' ? d.persona.actividad_id : null;
            var filas = _.map(panel.actividades, function (x) {
                return '<button type="button" class="o_ki_act' + (x.id === actId ? ' o_ki_actual' : '') +
                       '" data-id="' + x.id + '" style="border-left-color:' + _e(x.color) + '">' +
                       '<span class="o_ki_act_nombre">' + _e(x.nombre) + (x.abre ? ' ›' : '') + '</span>' +
                       (x.nota ? '<span class="o_ki_act_nota">' + _e(x.nota) + '</span>' : '') + '</button>';
            });
            this.$('.o_ki_panel').html('<div class="o_ki_panel_cab"><b>' + _e(panel.nombre) + '</b>' +
                '<button type="button" class="o_ki_cerrar_panel">Cerrar</button></div>' + filas.join(''));
        } else {
            this.$('.o_ki_panel').empty();
        }
        this.$('.o_ki_pausa').toggleClass('o_ki_oculto', d.persona.situacion !== 'trabajando');
        if (d.gestion && d.gestion.length) {
            this.$('.o_ki_gestion').html('<div class="o_ki_gestion_tit">Gestión</div>' + _.map(d.gestion, function (g) {
                return '<button type="button" class="o_ki_enlace" data-id="' + g.id + '">' + _e(g.nombre) +
                       '</button>';
            }).join(''));
        } else {
            this.$('.o_ki_gestion').empty();
        }
        this._pintarAhora();
    },
});

core.action_registry.add('koroshi_actividades_inicio_pda', InicioPda);
return InicioPda;
});


odoo.define('koroshi_actividades.InicioPdaGlobal', function (require) {
'use strict';
/* KOROSHI Actividades v1.6.0 - en todas las pantallas, solo si este navegador ha abierto el Inicio (PDA):
 * - botón «◀ Áreas» para volver al Inicio (no dentro de un pedido de Preparación o de la app de código de barras, ni
 *   en el propio Inicio, ni con una ventana abierta). Va por debajo de las capas de Lecturas (z-index 1030).
 * - señal de vida cada 2 min: si la tarjeta compartida se ha usado en los últimos 5 min, /inicio/senal (el tramo
 *   abierto cuenta como «Sigo»; sin tramo no hace nada).
 */
var rpc = require('web.rpc');
var session = require('web.session');

var CLAVE_INICIO = 'koroshi_inicio_pda';
var ACCION_INICIO = 'koroshi_actividades.action_koroshi_inicio_pda';
var SENAL_MS = 120000;
var SENAL_RECIENTE_MS = 300000;
var OCULTAR_EN = '.o_koroshi_inicio, .o_koroshi_preparacion, .o_barcode_client_action, .modal.show, ' +
                 '.o_ko_capa:visible, .o_ko_hoja:visible';

function usaInicio() {
    try { return window.sessionStorage.getItem(CLAVE_INICIO) === '1'; } catch (e) { return false; }
}

function tarjeta() {
    try {
        var v = window.localStorage.getItem('koroshi_operarios_pda_' + (session.uid || ''));
        return v ? JSON.parse(v) : null;
    } catch (e) { return null; }
}

var $boton = null;
function boton() {
    if (!$boton) {
        $boton = $('<button type="button" class="o_ki_volver">◀ Áreas</button>').appendTo(document.body);
        $boton.on('click', function () {
            // por la URL (como /koroshi_pda/inicio): Odoo carga la acción y se conserva la empresa (cids)
            var cids = /(?:^|[#&])cids=([^&]*)/.exec(window.location.hash || '');
            $boton.hide();
            window.location.hash = 'action=' + ACCION_INICIO + (cids ? '&cids=' + cids[1] : '');
        });
    }
    return $boton;
}

function vigilarBoton() {
    if (!usaInicio()) {
        if ($boton) { $boton.hide(); }
        return;
    }
    var ocultar = !$('.o_action_manager').length || $(OCULTAR_EN).length > 0;
    boton().toggle(!ocultar);
}

var senalEnviada = 0;
function senal() {
    if (!usaInicio()) { return; }
    var g = tarjeta();
    if (!g || !g.id || !g.t || Date.now() - g.t > SENAL_RECIENTE_MS || g.t <= senalEnviada) { return; }
    // en el propio Inicio no hace falta (pasar la tarjeta ya es «Sigo»)
    if ($('.o_koroshi_inicio').length) { return; }
    senalEnviada = g.t;
    rpc.query({route: '/koroshi/actividades/inicio/senal', params: {employee_id: g.id}}, {shadow: true})
        .guardedCatch(function (e) {
            if (e && e.event && e.event.preventDefault) { e.event.preventDefault(); }
        });
}

setInterval(vigilarBoton, 1500);
setInterval(senal, SENAL_MS);
});
