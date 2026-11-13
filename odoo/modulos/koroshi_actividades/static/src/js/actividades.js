odoo.define('koroshi_actividades.Pantalla', function (require) {
'use strict';
/* KOROSHI Actividades v1.0.0 - pantalla del portátil de manipulaciones (acción de cliente).
 *
 * - Izquierda: «Pasa tu tarjeta» (lector o escribir el código + Enter). Con la persona: sus botones de actividad
 *   (tocar = empezar o cambiar), Pausar / Seguir / Fin. Se cierra sola a los 20 s sin tocar nada.
 * - Derecha: quién está trabajando ahora (por actividad), en pausa y terminado hoy, con su tiempo.
 * - Varias personas a la vez: cada una pasa su tarjeta cuando quiere; la lista es de todas.
 * Sin librerías externas. Todo dentro de .o_koroshi_actividades para no tocar el resto de Odoo.
 */
var AbstractAction = require('web.AbstractAction');
var core = require('web.core');

var REPETIDA_MS = 700;          // la misma lectura dos veces seguidas (bus + campo) cuenta una
var CERRAR_PERSONA_MS = 20000;  // panel de la persona sin tocar nada -> se cierra
var CERRAR_TRAS_ACCION_MS = 3500;
var REFRESCO_MS = 30000;
var ICONOS = {ok: '✓', info: 'ℹ', warn: '⚠', mal: '✖'};

function _e(t) { return _.escape(t == null ? '' : String(t)); }

function _fecha(utc) {
    // 'YYYY-MM-DD HH:MM:SS' en UTC (Odoo) -> Date
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

var Pantalla = AbstractAction.extend({
    contentTemplate: 'koroshi_actividades.Pantalla',
    events: {
        'keydown .o_ka_codigo': '_onKeydown',
        'click .o_ka_actividad': '_onActividad',
        'click .o_ka_pausar': '_onPausar',
        'click .o_ka_seguir': '_onSeguir',
        'click .o_ka_fin': '_onFin',
        'click .o_ka_listo': '_cerrarPersona',
        'click .o_ka_fila_clic': '_onFila',
        'click .o_ka_confirmar_si': '_onConfirmarSi',
        'click .o_ka_confirmar_no': '_onConfirmarNo',
        'click': '_onClicFondo',
        'pointerdown': '_marcarActividad',
        'keydown': '_marcarActividad',
    },

    init: function () {
        this._super.apply(this, arguments);
        this.actividades = [];
        this.personas = [];
        this.persona = null;        // estado de la persona abierta (de /tarjeta)
        this.leidaEn = 0;           // Date.now() cuando se pidió la persona (para que corra su tiempo)
        this.listaEn = 0;           // Date.now() cuando se pidió la lista
        this.desfase = 0;           // hora del servidor - hora del portátil (ms)
        this.sinTarjeta = false;
        this.ocupado = false;
        this.ultima = {codigo: '', t: 0};
        this.ultimaActividad = Date.now();
        this.confirmar = null;
    },

    start: function () {
        var self = this;
        core.bus.on('barcode_scanned', this, this._onBarcodeScanned);
        return this._super.apply(this, arguments).then(function () {
            self._refrescar();
            self.timerLista = setInterval(self._refrescar.bind(self), REFRESCO_MS);
            self.timerReloj = setInterval(self._tic.bind(self), 1000);
            self._foco();
        });
    },

    destroy: function () {
        core.bus.off('barcode_scanned', this, this._onBarcodeScanned);
        clearInterval(this.timerLista);
        clearInterval(this.timerReloj);
        clearTimeout(this.timerCerrar);
        this._super.apply(this, arguments);
    },

    // ------------------------------------------------------------------ lectura
    _foco: function () {
        var $c = this.$('.o_ka_codigo');
        if ($c.length && document.activeElement !== $c[0]) {
            $c.focus();
        }
    },

    _onClicFondo: function (ev) {
        // volver a poner el foco en el campo al tocar cualquier sitio que no sea un botón
        if (!$(ev.target).closest('button, a, input').length) {
            this._foco();
        }
    },

    _onKeydown: function (ev) {
        if (ev.which === 13) {
            ev.preventDefault();
            var codigo = (ev.currentTarget.value || '').trim();
            ev.currentTarget.value = '';
            this._leer(codigo);
        }
    },

    _onBarcodeScanned: function (codigo) {
        this._leer(codigo);
    },

    _leer: function (codigo) {
        var self = this;
        codigo = (codigo || '').trim();
        if (!codigo) {
            return;
        }
        var t = Date.now();
        if (codigo === this.ultima.codigo && t - this.ultima.t < REPETIDA_MS) {
            return;
        }
        this.ultima = {codigo: codigo, t: t};
        this.$('.o_ka_codigo').val('');
        return this._llamar('/koroshi/actividades/tarjeta', {codigo: codigo}).then(function (r) {
            if (r) {
                self._abrirPersona(r.persona);
            }
        });
    },

    _onFila: function (ev) {
        var self = this;
        var id = parseInt($(ev.currentTarget).data('id'), 10);
        if (!this.sinTarjeta || !id) {
            return;
        }
        return this._llamar('/koroshi/actividades/persona', {employee_id: id}).then(function (r) {
            if (r) {
                self._abrirPersona(r.persona);
            }
        });
    },

    // ------------------------------------------------------------------ servidor
    _llamar: function (ruta, params) {
        var self = this;
        if (this.ocupado) {
            return Promise.resolve(null);
        }
        this.ocupado = true;
        return this._rpc({route: ruta, params: params}).then(function (r) {
            self.ocupado = false;
            if (!r || !r.ok) {
                self._aviso('mal', (r && r.msg) || 'No se ha podido hacer.');
                return null;
            }
            return r;
        }, function () {
            self.ocupado = false;
            self._aviso('mal', 'Sin conexión con Odoo. Vuelve a probar en unos segundos.');
            return null;
        });
    },

    _refrescar: function () {
        var self = this;
        return this._rpc({route: '/koroshi/actividades/estado', params: {}}).then(function (r) {
            if (!r || !r.ok) {
                return;
            }
            self.actividades = r.actividades;
            self.personas = r.personas;
            self.sinTarjeta = !!r.sin_tarjeta;
            self.listaEn = Date.now();
            var srv = _fecha(r.ahora);
            if (srv) {
                self.desfase = srv.getTime() - Date.now();
            }
            self.$('.o_ka_horario').text('Pausa sola a las ' + (r.hora_pausa || '–') + ' · cierre a las ' +
                (r.hora_cierre || '–'));
            self.$el.toggleClass('o_ka_sin_conexion', false);
            self._pintarLista();
            if (self.persona) {
                self._pintarPersona();
            }
        }, function () {
            self.$el.toggleClass('o_ka_sin_conexion', true);
        });
    },

    // ------------------------------------------------------------------ persona
    _abrirPersona: function (p) {
        this.persona = p;
        this.leidaEn = Date.now();
        this.confirmar = null;
        clearTimeout(this.timerAviso);
        this.$('.o_ka_aviso').attr('class', 'o_ka_aviso').empty();   // el aviso de la persona anterior fuera
        this._marcarActividad();
        this._pintarPersona();
        this._programarCierre(CERRAR_PERSONA_MS);
    },

    _cerrarPersona: function () {
        this.persona = null;
        this.confirmar = null;
        clearTimeout(this.timerCerrar);
        this._pintarPersona();
        this._foco();
    },

    _programarCierre: function (ms) {
        var self = this;
        clearTimeout(this.timerCerrar);
        this.timerCerrar = setTimeout(function () {
            if (Date.now() - self.ultimaActividad >= ms - 50) {
                self._cerrarPersona();
            } else {
                self._programarCierre(ms);
            }
        }, ms);
    },

    _marcarActividad: function () {
        this.ultimaActividad = Date.now();
    },

    _accion: function (ruta, params, despues) {
        var self = this;
        if (!this.persona) {
            return;
        }
        return this._llamar(ruta, _.extend({employee_id: this.persona.employee_id}, params || {})).then(function (r) {
            if (!r) {
                return;
            }
            self.persona = r.persona;
            self.leidaEn = Date.now();
            self._aviso('ok', r.msg);
            self._pintarPersona();
            self._refrescar();
            self._marcarActividad();
            self._programarCierre(despues || CERRAR_TRAS_ACCION_MS);
        });
    },

    _onActividad: function (ev) {
        var id = parseInt($(ev.currentTarget).data('id'), 10);
        if (this.persona && this.persona.situacion === 'trabajando' && this.persona.actividad_id === id) {
            this._aviso('info', 'Ya estás en ' + this.persona.actividad + '.');
            return;
        }
        return this._accion('/koroshi/actividades/empezar', {actividad_id: id});
    },

    _onPausar: function () {
        return this._accion('/koroshi/actividades/pausar');
    },

    _onSeguir: function () {
        return this._accion('/koroshi/actividades/seguir');
    },

    _onFin: function () {
        // «Fin» pide confirmación: es el final de la jornada
        this.confirmar = 'fin';
        this._pintarPersona();
    },

    _onConfirmarSi: function () {
        this.confirmar = null;
        return this._accion('/koroshi/actividades/fin');
    },

    _onConfirmarNo: function () {
        this.confirmar = null;
        this._pintarPersona();
    },

    // ------------------------------------------------------------------ pintar
    _minutosPersona: function (p, desde) {
        return (p.minutos_hoy || 0) + (p.situacion === 'trabajando' ? (Date.now() - desde) / 60000 : 0);
    },

    _textoSituacion: function (p) {
        if (p.situacion === 'trabajando') {
            return '<span class="o_ka_estado o_ka_trabajando">Trabajando</span> en <b>' + _e(p.actividad) +
                '</b> desde las ' + _hora(p.desde);
        }
        if (p.situacion === 'pausa') {
            return '<span class="o_ka_estado o_ka_pausa">En pausa</span> desde las ' + _hora(p.desde) +
                (p.pausa_auto ? ' <span class="o_ka_auto">(pausa automática de la comida)</span>' : '') +
                ' · estaba en <b>' + _e(p.actividad) + '</b>';
        }
        if (p.situacion === 'terminado') {
            return '<span class="o_ka_estado o_ka_terminado">Terminado</span> a las ' + _hora(p.desde) +
                (p.fin_auto ? ' <span class="o_ka_auto">(cerrado solo)</span>' : '');
        }
        return 'Aún no has empezado hoy. Toca lo que vas a hacer.';
    },

    _pintarPersona: function () {
        var p = this.persona;
        this.$('.o_ka_lector').toggleClass('o_ka_oculto', !!p);
        var $p = this.$('.o_ka_persona').toggleClass('o_ka_oculto', !p);
        if (!p) {
            $p.empty();
            return;
        }
        var html = '<div class="o_ka_persona_cab"><div><div class="o_ka_nombre">' + _e(p.nombre) + '</div>' +
            '<div class="o_ka_situacion">' + this._textoSituacion(p) + '</div>' +
            '<div class="o_ka_hoy">Hoy: <b class="o_ka_minutos_persona">' +
            _hm(this._minutosPersona(p, this.leidaEn)) + '</b>' +
            (p.entrada ? ' · entrada ' + _hora(p.entrada) : '') + '</div></div>' +
            '<button type="button" class="o_ka_listo">Listo</button></div>';
        if (this.confirmar === 'fin') {
            html += '<div class="o_ka_confirmar"><p>¿Acabas la jornada, ' + _e(p.nombre.split(' ')[0]) + '?</p>' +
                '<div class="o_ka_fila_botones">' +
                '<button type="button" class="o_ka_boton o_ka_rojo o_ka_confirmar_si">Sí, fin</button>' +
                '<button type="button" class="o_ka_boton o_ka_gris o_ka_confirmar_no">No</button></div></div>';
            $p.html(html);
            return;
        }
        html += '<div class="o_ka_titulo_bloque">' + (p.situacion === 'trabajando' ? 'Cambiar a…' : '¿Qué vas a hacer?') +
            '</div><div class="o_ka_actividades">';
        _.each(this.actividades, function (a) {
            var actual = p.situacion === 'trabajando' && p.actividad_id === a.id;
            html += '<button type="button" class="o_ka_actividad' + (actual ? ' o_ka_actual' : '') + '" data-id="' +
                a.id + '" style="--ka-color:' + _e(a.color) + '"><span class="o_ka_act_nombre">' + _e(a.nombre) +
                '</span>' + (a.nota ? '<span class="o_ka_act_nota">' + _e(a.nota) + '</span>' : '') +
                (actual ? '<span class="o_ka_act_nota">● ahora</span>' : '') + '</button>';
        });
        html += '</div><div class="o_ka_fila_botones">';
        if (p.situacion === 'trabajando') {
            html += '<button type="button" class="o_ka_boton o_ka_ambar o_ka_pausar">⏸ Pausar</button>';
        }
        if (p.situacion === 'pausa') {
            html += '<button type="button" class="o_ka_boton o_ka_verde o_ka_seguir">▶ Seguir con ' + _e(p.actividad) +
                '</button>';
        }
        if (p.situacion === 'trabajando' || p.situacion === 'pausa') {
            html += '<button type="button" class="o_ka_boton o_ka_rojo o_ka_fin">■ Fin</button>';
        }
        html += '</div>';
        $p.html(html);
    },

    _pintarLista: function () {
        var self = this;
        var grupos = {trabajando: [], pausa: [], terminado: []};
        _.each(this.personas, function (p) {
            if (grupos[p.situacion]) {
                grupos[p.situacion].push(p);
            }
        });
        var clic = this.sinTarjeta ? ' o_ka_fila_clic' : '';
        var fila = function (p, extra) {
            return '<div class="o_ka_fila' + clic + '" data-id="' + p.employee_id + '">' +
                '<span class="o_ka_fila_nombre">' + _e(p.nombre) + '</span>' +
                '<span class="o_ka_fila_extra">' + extra + '</span>' +
                '<span class="o_ka_fila_min" data-min="' + (p.minutos_hoy || 0) + '" data-corre="' +
                (p.situacion === 'trabajando' ? 1 : 0) + '">' + _hm(p.minutos_hoy) + '</span></div>';
        };
        var html = '';
        // trabajando: por actividad, en el orden de los botones
        var porAct = _.groupBy(grupos.trabajando, 'actividad_id');
        var hay = false;
        _.each(this.actividades, function (a) {
            var gente = porAct[a.id];
            if (!gente) {
                return;
            }
            hay = true;
            html += '<div class="o_ka_grupo" style="--ka-color:' + _e(a.color) + '"><div class="o_ka_grupo_cab">' +
                _e(a.nombre) + ' <span>' + gente.length + '</span></div>';
            _.each(gente, function (p) {
                html += fila(p, 'desde ' + _hora(p.desde));
            });
            html += '</div>';
        });
        // actividades archivadas que aún tienen a alguien
        _.each(porAct, function (gente, id) {
            if (!_.findWhere(self.actividades, {id: parseInt(id, 10)})) {
                hay = true;
                html += '<div class="o_ka_grupo"><div class="o_ka_grupo_cab">' + _e(gente[0].actividad) + '</div>';
                _.each(gente, function (p) { html += fila(p, 'desde ' + _hora(p.desde)); });
                html += '</div>';
            }
        });
        if (!hay) {
            html += '<p class="o_ka_vacio">Nadie trabajando ahora.</p>';
        }
        if (grupos.pausa.length) {
            html += '<div class="o_ka_grupo o_ka_grupo_pausa"><div class="o_ka_grupo_cab">En pausa <span>' +
                grupos.pausa.length + '</span></div>';
            _.each(grupos.pausa, function (p) {
                html += fila(p, (p.pausa_auto ? 'pausa automática' : 'desde ' + _hora(p.desde)) + ' · ' + _e(p.actividad));
            });
            html += '</div>';
        }
        if (grupos.terminado.length) {
            html += '<div class="o_ka_grupo o_ka_grupo_fin"><div class="o_ka_grupo_cab">Terminado hoy <span>' +
                grupos.terminado.length + '</span></div>';
            _.each(grupos.terminado, function (p) {
                html += fila(p, 'a las ' + _hora(p.desde) + (p.fin_auto ? ' (cerrado solo)' : ''));
            });
            html += '</div>';
        }
        this.$('.o_ka_lista').html(html);
    },

    _tic: function () {
        var self = this;
        var ahora = new Date(Date.now() + this.desfase);
        this.$('.o_ka_reloj').text(ahora.toLocaleTimeString('es-ES', {hour: '2-digit', minute: '2-digit'}));
        var extra = (Date.now() - this.listaEn) / 60000;
        this.$('.o_ka_fila_min').each(function () {
            var $m = $(this);
            var min = parseFloat($m.data('min')) + ($m.data('corre') ? extra : 0);
            $m.text(_hm(min));
        });
        if (this.persona) {
            this.$('.o_ka_minutos_persona').text(_hm(this._minutosPersona(this.persona, this.leidaEn)));
        }
        if (!this.persona) {
            self._foco();
        }
    },

    _aviso: function (tipo, texto) {
        var $a = this.$('.o_ka_aviso');
        clearTimeout(this.timerAviso);
        $a.attr('class', 'o_ka_aviso o_ka_aviso_' + tipo)
            .html('<span class="o_ka_icono" role="presentation">' + (ICONOS[tipo] || '') + '</span> ' + _e(texto));
        if (tipo === 'ok' || tipo === 'info') {
            this.timerAviso = setTimeout(function () { $a.attr('class', 'o_ka_aviso').empty(); }, 5000);
        }
    },
});

core.action_registry.add('koroshi_actividades_pantalla', Pantalla);
return Pantalla;
});
