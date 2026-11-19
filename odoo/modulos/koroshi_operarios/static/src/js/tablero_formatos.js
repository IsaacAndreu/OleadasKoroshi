odoo.define('koroshi_operarios.TableroFormatos', function (require) {
'use strict';
/* KOROSHI Operarios v2.21.0 - Tablero del responsable con cinco formatos para elegir (A-E).
 * Maqueta: bin/versiones/tablero-responsable-formatos_2026-11-19.html
 *
 * Misma cola y mismas reglas que el tablero 2.20.0: los datos llegan en una llamada (tablero_datos) y cada vez que
 * se suelta una tarjeta se llama a tablero_mover (el servidor comprueba el grupo y qué se puede mover). Se arrastra
 * con el arrastrar del navegador (HTML5). Clic en una tarjeta = su ficha (escribir la nota, Quitar, Ponerla la
 * primera). El formato elegido se recuerda en este PC (localStorage). Cada minuto se actualiza solo.
 */
var AbstractAction = require('web.AbstractAction');
var core = require('web.core');

var MODELO = 'koroshi.operario.asignacion';
var REFRESCO_MS = 60000;
var CLAVE_FORMATO = 'koroshi_tablero_formato';
var FORMATOS = [
    ['A', 'A · Columnas'], ['B', 'B · Zonas arriba'], ['C', 'C · Filas'],
    ['D', 'D · Por zonas'], ['E', 'E · Fichas'],
];
var ICONO = {lote: '▦', agrupacion: '▤', nota: '✎', actividad: '⏱', out: '▢'};

function esc(t) { return _.escape(t === undefined || t === null ? '' : String(t)); }

function leerFormato() {
    try { return window.localStorage.getItem(CLAVE_FORMATO) || 'A'; } catch (e) { return 'A'; }
}
function guardarFormato(f) {
    try { window.localStorage.setItem(CLAVE_FORMATO, f); } catch (e) { /* sin almacenamiento: da igual */ }
}

var TableroFormatos = AbstractAction.extend({
    events: {
        'click .o_ktf_formato': '_onFormato',
        'click .o_ktf_actualizar': '_onActualizar',
        'click .o_ktf_clasico': '_onClasico',
        'click .o_ktf_plegar': '_onPlegar',
        'click [data-carta]': '_onCarta',
        'dragstart [draggable=true]': '_onDragStart',
        'dragend [draggable=true]': '_onDragEnd',
        'dragover [data-destino]': '_onDragOver',
        'dragleave [data-destino]': '_onDragLeave',
        'drop [data-destino]': '_onDrop',
    },

    init: function () {
        this._super.apply(this, arguments);
        this.formato = leerFormato();
        this.datos = null;
        this.outsAbiertas = false;
        this.arrastrando = null;
        this.ocupado = false;
    },

    willStart: function () {
        var self = this;
        return Promise.all([this._super.apply(this, arguments), this._cargar(true)]).then(function () {
            return self;
        });
    },

    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self._pintar();
            self.timer = setInterval(function () {
                if (document.hidden || self.arrastrando || self.ocupado) { return; }
                self._recargar(true);
            }, REFRESCO_MS);
        });
    },

    destroy: function () {
        clearInterval(this.timer);
        this._super.apply(this, arguments);
    },

    // ------------------------------------------------------------------ datos
    _cargar: function (refrescar) {
        var self = this;
        return this._rpc({model: MODELO, method: 'tablero_datos', args: [], kwargs: {refrescar: !!refrescar}})
            .then(function (d) { self.datos = d; });
    },

    _recargar: function (refrescar) {
        var self = this;
        if (this.ocupado) { return Promise.resolve(); }
        this.ocupado = true;
        return this._cargar(refrescar).then(function () {
            self.ocupado = false;
            self._pintar();
        }, function () { self.ocupado = false; });
    },

    _mover: function (id, empId, primero) {
        var self = this;
        this.ocupado = true;
        return this._rpc({model: MODELO, method: 'tablero_mover', args: [id, empId || false],
                          kwargs: {primero: !!primero}})
            .then(function (res) {
                self.ocupado = false;
                // una nota recién dada: se abre su ficha para escribir lo que tiene que hacer
                if (res && res.tipo === 'nota' && empId) { self._abrirFicha(res.id); }
                return self._recargar(true);
            }, function () {
                self.ocupado = false;
                return self._recargar(true);
            });
    },

    _abrirFicha: function (id) {
        var self = this;
        return this.do_action({
            type: 'ir.actions.act_window', res_model: MODELO, res_id: id,
            views: [[this.datos.form_id, 'form']], target: 'new', name: 'Tarjeta del tablero',
        }, {on_close: function () { self._recargar(false); }});
    },

    // ------------------------------------------------------------------ pintar
    _pintar: function () {
        var $donde = this.$('.o_content').length ? this.$('.o_content') : this.$el;
        var d = this.datos || {operarios: [], piezas: {zonas: [], actividades: [], notas: [], outs: []}, zonas: []};
        var html = '<div class="o_ktf o_ktf_' + this.formato + '">' + this._barra(d);
        var f = this['_formato' + this.formato] || this._formatoA;
        html += f.call(this, d) + '</div>';
        $donde.html(html);
    },

    _barra: function (d) {
        var self = this;
        var h = '<div class="o_ktf_barra"><b>Tablero</b>';
        _.each(FORMATOS, function (f) {
            h += '<button type="button" class="btn btn-sm o_ktf_formato ' +
                 (self.formato === f[0] ? 'btn-primary' : 'btn-secondary') + '" data-f="' + f[0] + '">' +
                 esc(f[1]) + '</button>';
        });
        h += '<span class="o_ktf_hueco"></span><span class="o_ktf_mut">Actualizado ' + esc(d.hora || '') +
             '</span><button type="button" class="btn btn-sm btn-primary o_ktf_actualizar">Actualizar</button>' +
             '<button type="button" class="btn btn-sm btn-link o_ktf_clasico">Tablero clásico</button></div>';
        return h;
    },

    _av: function (op, pequeno) {
        var cls = op.estado === 'parado' ? 'o_ktf_p_par' : (op.estado === 'leyendo' ? 'o_ktf_p_ok' :
                  (op.estado === 'actividad' ? 'o_ktf_p_act' : 'o_ktf_p_sin'));
        return '<span class="o_ktf_av ' + cls + (pequeno ? ' o_ktf_av_p' : '') + '" title="' + esc(op.nombre) +
               '">' + esc(op.ini) + '</span>';
    },

    _estado: function (op) {
        return '<span class="o_ktf_mut o_ktf_est_' + op.estado + '">' + esc(op.estado_texto) +
               (op.uds ? ' · ' + op.uds + ' uds' : '') + '</span>';
    },

    _barraProg: function (pct, cls) {
        return '<div class="o_ktf_prog" role="presentation"><i class="' + (cls || '') + '" style="width:' +
               Math.max(0, Math.min(100, pct || 0)) + '%"></i></div>';
    },

    _carta: function (c, extra) {
        extra = extra || {};
        var mover = c.estado === 'pieza' || c.estado === 'cola';
        var cls = 'o_ktf_t o_ktf_tipo_' + c.tipo + ' o_ktf_' + c.estado + (extra.ahora ? ' o_ktf_ahora' : '');
        var nombre = c.tipo === 'nota' ? (c.texto || (c.estado === 'pieza' ? 'Nota (arrástrala y escribe)' : 'Nota'))
                                       : c.nombre;
        var h = '<div class="' + cls + '" data-carta="' + c.id + '"' + (mover ? ' draggable="true" data-id="' +
                c.id + '"' : '') + '>';
        h += '<div class="o_ktf_tcab"><span role="presentation">' + (ICONO[c.tipo] || '▢') + '</span><b>' +
             esc(nombre) + '</b></div>';
        if (extra.ahora) { h += '<div class="o_ktf_mut o_ktf_verde">Ahora</div>'; }
        if (c.estado === 'hecha') { h += '<div class="o_ktf_mut">Hecha</div>'; }
        if (c.sub) { h += '<div class="o_ktf_mut">' + esc(c.sub) + '</div>'; }
        if (c.zona && c.tipo === 'out') { h += '<div class="o_ktf_mut">' + esc(c.zona) + '</div>'; }
        if (c.prog && !extra.corta) { h += this._barraProg(c.pct, c.tipo === 'lote' ? 'o_ktf_azul' : '') +
                                           '<div class="o_ktf_mut">' + esc(c.prog) + '</div>'; }
        if (c.tambien && !extra.corta) { h += '<div class="o_ktf_mut o_ktf_azul_t">También: ' + esc(c.tambien) +
                                              '</div>'; }
        return h + '</div>';
    },

    _chip: function (c) {
        return '<span class="o_ktf_chip" draggable="true" data-id="' + c.id + '" data-carta="' + c.id + '">⏱ ' +
               esc(c.nombre) + '</span>';
    },

    _piezas: function (d, opts) {
        opts = opts || {};
        var self = this;
        var p = d.piezas;
        var h = '<div class="o_ktf_piezas" data-destino="1" data-emp="0"><div class="o_ktf_hd"><b>Por repartir</b>' +
                '<span class="o_ktf_mut">suelta aquí para quitar</span></div>';
        if (!opts.sinZonas && p.zonas.length) {
            h += '<div class="o_ktf_sec">Zonas y agrupaciones</div>';
            _.each(p.zonas, function (c) { h += self._carta(c); });
        }
        if (p.actividades.length) {
            h += '<div class="o_ktf_sec">Actividades</div><div>';
            _.each(p.actividades, function (c) { h += self._chip(c); });
            h += '</div>';
        }
        if (p.notas.length) {
            h += '<div class="o_ktf_sec">Notas</div>';
            _.each(p.notas, function (c) { h += self._carta(c); });
        }
        if (p.outs.length) {
            h += '<div class="o_ktf_sec"><a href="#" class="o_ktf_plegar">' + p.outs.length + ' OUT sueltas ' +
                 (this.outsAbiertas ? '▴' : '▾') + '</a></div>';
            if (this.outsAbiertas) {
                _.each(p.outs, function (c) { h += self._carta(c, {corta: true}); });
            }
        }
        return h + '</div>';
    },

    _cabOp: function (op) {
        return '<div class="o_ktf_hd">' + this._av(op) + '<div class="o_ktf_quien"><b>' + esc(op.nombre) +
               '</b><div>' + this._estado(op) + '</div></div></div>';
    },

    // ---- A: columnas
    _formatoA: function (d) {
        var self = this;
        var h = '<div class="o_ktf_expl">Una columna por persona. Arrastra de «Por repartir» a la columna; se hace de ' +
                'arriba abajo.</div><div class="o_ktf_cols">' + this._piezas(d);
        _.each(d.operarios, function (op) {
            h += '<div class="o_ktf_col" data-destino="1" data-emp="' + op.id + '">' + self._cabOp(op);
            if (op.ahora) { h += self._carta(op.ahora, {ahora: true}); }
            _.each(op.cola, function (c) { h += self._carta(c); });
            _.each(op.hechas, function (c) { h += self._carta(c, {corta: true}); });
            h += '<div class="o_ktf_soltar">Suelta aquí</div></div>';
        });
        return h + '</div>';
    },

    // ---- B: zonas arriba + rejilla
    _resumenZonas: function (d) {
        var self = this;
        var h = '<div class="o_ktf_zonas">';
        _.each(d.zonas, function (z) {
            h += '<div class="o_ktf_z"' + (z.pieza_id ? ' draggable="true" data-id="' + z.pieza_id + '"' : '') +
                 '><b>' + esc(z.nombre) + '</b>' + self._barraProg(z.pct, z.es_zona ? '' : 'o_ktf_azul') +
                 '<div class="o_ktf_mut">' + esc(z.prog) + '</div><div class="o_ktf_gente">';
            _.each(z.gente, function (g) {
                h += '<span class="o_ktf_av o_ktf_av_p o_ktf_p_ok" title="' + esc(g.nombre) + '">' + esc(g.ini) +
                     '</span>';
            });
            if (!z.gente.length) { h += '<span class="o_ktf_mut">nadie</span>'; }
            h += '</div></div>';
        });
        if (!d.zonas.length) { h += '<span class="o_ktf_mut">No hay zonas ni agrupaciones con OUT libres.</span>'; }
        return h + '</div>';
    },

    _formatoB: function (d) {
        var self = this;
        var h = '<div class="o_ktf_expl">Arriba, cómo va cada zona y quién está. Arrastra una zona a una persona ' +
                'para reforzar (va la primera de su cola).</div>' + this._resumenZonas(d) +
                '<div class="o_ktf_main">' + this._piezas(d, {sinZonas: true}) + '<div class="o_ktf_rejilla">';
        _.each(d.operarios, function (op) {
            h += '<div class="o_ktf_col" data-destino="1" data-emp="' + op.id + '" data-primero="1">' +
                 self._cabOp(op);
            if (op.ahora) { h += self._carta(op.ahora, {ahora: true, corta: true}); }
            _.each(op.cola, function (c) { h += self._carta(c, {corta: true}); });
            if (!op.ahora && !op.cola.length) { h += '<div class="o_ktf_soltar">Suelta aquí</div>'; }
            h += '</div>';
        });
        return h + '</div></div>';
    },

    // ---- C: filas
    _formatoC: function (d) {
        var self = this;
        var h = '<div class="o_ktf_expl">Una fila por persona; sus tareas en orden hacia la derecha.</div>' +
                '<div class="o_ktf_main"><div class="o_ktf_filas">';
        _.each(d.operarios, function (op) {
            h += '<div class="o_ktf_fila" data-destino="1" data-emp="' + op.id + '"><div class="o_ktf_fquien">' +
                 self._av(op) + '<div><b>' + esc(op.nombre) + '</b><div>' + self._estado(op) + '</div></div></div>' +
                 '<div class="o_ktf_ftareas">';
            var todas = (op.ahora ? [op.ahora] : []).concat(op.cola);
            _.each(todas, function (c, i) {
                if (i) { h += '<span class="o_ktf_flecha">→</span>'; }
                h += self._carta(c, {ahora: op.ahora && i === 0});
            });
            h += (todas.length ? '<span class="o_ktf_flecha">→</span>' : '') +
                 '<div class="o_ktf_soltar">Suelta aquí</div></div></div>';
        });
        return h + '</div>' + this._piezas(d) + '</div>';
    },

    // ---- D: por zonas (se arrastra a la gente)
    _dondeEsta: function (op) {
        var c = op.ahora || op.cola[0];
        if (!c) { return 'libre'; }
        if (c.tipo === 'actividad') { return 'act:' + c.nombre; }
        if (c.batch_id && (c.tipo === 'lote' || c.tipo === 'agrupacion' || c.zona)) { return 'z:' + c.batch_id; }
        return 'otras';
    },

    _persona: function (op) {
        var c = op.ahora || op.cola[0];
        return '<div class="o_ktf_persona" draggable="true" data-persona="' + op.id + '">' + this._av(op, true) +
               '<b>' + esc(op.nombre) + '</b><span class="o_ktf_mut">' +
               esc(op.estado === 'parado' ? op.estado_texto : (c ? (c.tipo === 'nota' ? (c.texto || 'Nota') : c.nombre)
                                                                  : '')) + '</span></div>';
    },

    _formatoD: function (d) {
        var self = this;
        var grupos = {};
        _.each(d.operarios, function (op) { (grupos[self._dondeEsta(op)] = grupos[self._dondeEsta(op)] || []).push(op); });
        var h = '<div class="o_ktf_expl">Cada columna es una zona o actividad. Arrastra a una persona a otra columna ' +
                'para mandarla allí (pasa a ser lo primero de su cola). Las OUT sueltas y las notas, en «Por repartir».' +
                '</div><div class="o_ktf_cols">';
        _.each(d.zonas, function (z) {
            h += '<div class="o_ktf_col o_ktf_dz"' + (z.pieza_id ? ' data-destino="1" data-pieza="' + z.pieza_id + '"' : '') +
                 '><div class="o_ktf_dh"><b>' + esc(z.nombre) + '</b>' + self._barraProg(z.pct, z.es_zona ? '' : 'o_ktf_azul') +
                 '<div class="o_ktf_mut">' + esc(z.prog) + (z.pieza_id ? '' : ' · sin OUT libres') + '</div></div>';
            _.each(grupos['z:' + z.batch_id] || [], function (op) { h += self._persona(op); });
            h += '</div>';
        });
        _.each(d.piezas.actividades, function (a) {
            h += '<div class="o_ktf_col o_ktf_dz o_ktf_dact" data-destino="1" data-pieza="' + a.id + '">' +
                 '<div class="o_ktf_dh"><b>⏱ ' + esc(a.nombre) + '</b><div class="o_ktf_mut">actividad (portátil)</div></div>';
            _.each(grupos['act:' + a.nombre] || [], function (op) { h += self._persona(op); });
            h += '</div>';
        });
        h += '<div class="o_ktf_col o_ktf_dz"><div class="o_ktf_dh"><b>Otras tareas</b><div class="o_ktf_mut">' +
             'OUT sueltas o notas</div></div>';
        _.each(grupos.otras || [], function (op) { h += self._persona(op); });
        h += '</div><div class="o_ktf_col o_ktf_dz o_ktf_dlibre"><div class="o_ktf_dh"><b>Sin tarea</b>' +
             '<div class="o_ktf_mut">pasan a la siguiente OUT libre</div></div>';
        _.each(grupos.libre || [], function (op) { h += self._persona(op); });
        h += '</div>' + this._piezas(d, {sinZonas: true});
        return h + '</div>';
    },

    // ---- E: fichas grandes
    _formatoE: function (d) {
        var self = this;
        var h = '<div class="o_ktf_expl">Una ficha por persona: lo de ahora en grande y lo siguiente debajo. ' +
                'Arrastra las piezas de arriba a la ficha.</div><div class="o_ktf_tira">' + this._piezas(d) + '</div>' +
                '<div class="o_ktf_fichas">';
        _.each(d.operarios, function (op) {
            var c = op.ahora || op.cola[0];
            var resto = op.ahora ? op.cola : op.cola.slice(1);
            h += '<div class="o_ktf_ficha' + (op.estado === 'parado' ? ' o_ktf_alerta' : '') +
                 '" data-destino="1" data-emp="' + op.id + '">' + self._cabOp(op);
            if (c) {
                h += '<div class="o_ktf_grande" data-carta="' + c.id + '">' +
                     esc(c.tipo === 'nota' ? (c.texto || 'Nota') : c.nombre) + '</div>';
                if (c.prog) { h += self._barraProg(c.pct) + '<div class="o_ktf_mut">' + esc(c.prog) + '</div>'; }
                if (!op.ahora) { h += '<div class="o_ktf_mut">Aún no la ha empezado</div>'; }
            } else {
                h += '<div class="o_ktf_grande o_ktf_mut">Sin tarea</div>';
            }
            h += '<div class="o_ktf_sig">Después: ';
            _.each(resto, function (r) {
                h += '<span data-carta="' + r.id + '" draggable="true" data-id="' + r.id + '">' +
                     esc(r.tipo === 'nota' ? (r.texto || 'Nota') : r.nombre) + '</span>';
            });
            if (!resto.length) { h += '<span class="o_ktf_vacio">(siguiente libre)</span>'; }
            h += '</div></div>';
        });
        return h + '</div>';
    },

    // ------------------------------------------------------------------ eventos
    _onFormato: function (ev) {
        this.formato = $(ev.currentTarget).data('f');
        guardarFormato(this.formato);
        this._pintar();
    },
    _onActualizar: function () { this._recargar(true); },
    _onClasico: function () {
        var self = this;
        return this._rpc({model: MODELO, method: 'tablero_clasico', args: []}).then(function (accion) {
            return self.do_action(accion);
        });
    },
    _onPlegar: function (ev) {
        ev.preventDefault();
        this.outsAbiertas = !this.outsAbiertas;
        this._pintar();
    },
    _onCarta: function (ev) {
        ev.stopPropagation();
        var id = parseInt($(ev.currentTarget).attr('data-carta'), 10);
        if (id) { this._abrirFicha(id); }
    },
    _onDragStart: function (ev) {
        var $t = $(ev.currentTarget);
        ev.stopPropagation();
        this.arrastrando = {id: parseInt($t.attr('data-id'), 10) || 0,
                            persona: parseInt($t.attr('data-persona'), 10) || 0};
        var dt = ev.originalEvent && ev.originalEvent.dataTransfer;
        if (dt) {
            dt.effectAllowed = 'move';
            try { dt.setData('text/plain', String(this.arrastrando.id || this.arrastrando.persona)); } catch (e) { /* IE */ }
        }
        $t.addClass('o_ktf_arrastrado');
    },
    _onDragEnd: function (ev) {
        $(ev.currentTarget).removeClass('o_ktf_arrastrado');
        this.$('.o_ktf_encima').removeClass('o_ktf_encima');
        var self = this;
        setTimeout(function () { self.arrastrando = null; }, 0);
    },
    _sirve: function ($d) {
        var a = this.arrastrando;
        if (!a) { return false; }
        if (a.persona) { return !!$d.attr('data-pieza'); }   // D: personas solo a columnas de zona o actividad
        return $d.attr('data-emp') !== undefined;
    },
    _onDragOver: function (ev) {
        var $d = $(ev.currentTarget);
        if (!this._sirve($d)) { return; }
        ev.preventDefault();
        ev.stopPropagation();
        this.$('.o_ktf_encima').not($d).removeClass('o_ktf_encima');
        $d.addClass('o_ktf_encima');
    },
    _onDragLeave: function (ev) {
        if (!$.contains(ev.currentTarget, ev.originalEvent.relatedTarget)) {
            $(ev.currentTarget).removeClass('o_ktf_encima');
        }
    },
    _onDrop: function (ev) {
        var $d = $(ev.currentTarget);
        var a = this.arrastrando;
        if (!this._sirve($d)) { return; }
        ev.preventDefault();
        ev.stopPropagation();
        this.arrastrando = null;
        this.$('.o_ktf_encima').removeClass('o_ktf_encima');
        if (a.persona) {
            return this._mover(parseInt($d.attr('data-pieza'), 10), a.persona, true);
        }
        return this._mover(a.id, parseInt($d.attr('data-emp'), 10) || false, $d.attr('data-primero') === '1');
    },
});

core.action_registry.add('koroshi_tablero_formatos', TableroFormatos);
return TableroFormatos;
});
