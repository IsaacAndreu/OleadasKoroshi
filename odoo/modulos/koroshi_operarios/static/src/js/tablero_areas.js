odoo.define('koroshi_operarios.TableroAreas', function (require) {
'use strict';
/* KOROSHI Operarios v2.23.0 - Tablero del responsable por áreas (formato D, Isaac 20/11).
 * Diseño: bin/versiones/diseno-tablero-responsable_2026-11-20_v8.md. Sustituye a tablero_formatos.js (2.21).
 *
 * Columnas = áreas y «Sin área». En Picking, una fila por zona o agrupación (en el orden en que se dan; «1.ª, 2.ª…»
 * en las que no tiene nadie). Se arrastra a una persona (de cualquier columna) a una fila de Picking: esa zona va
 * la primera de su cola (tablero_mover, el servidor comprueba el grupo). Las demás áreas solo se miran. Los datos
 * llegan en una llamada (tablero_datos); cada minuto se actualiza solo, si la pestaña se ve y no se arrastra nada.
 */
var AbstractAction = require('web.AbstractAction');
var core = require('web.core');

var MODELO = 'koroshi.operario.asignacion';
var REFRESCO_MS = 60000;

function esc(t) { return _.escape(t === undefined || t === null ? '' : String(t)); }

var TableroAreas = AbstractAction.extend({
    events: {
        'click .o_kta_actualizar': '_onActualizar',
        'dragstart [data-persona]': '_onDragStart',
        'dragend [data-persona]': '_onDragEnd',
        'dragover [data-pieza]': '_onDragOver',
        'dragleave [data-pieza]': '_onDragLeave',
        'drop [data-pieza]': '_onDrop',
    },

    init: function () {
        this._super.apply(this, arguments);
        this.datos = null;
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

    _mover: function (piezaId, empId) {
        var self = this;
        this.ocupado = true;
        return this._rpc({model: MODELO, method: 'tablero_mover', args: [piezaId, empId], kwargs: {primero: true}})
            .then(function () {
                self.ocupado = false;
                return self._recargar(true);
            }, function () {
                self.ocupado = false;
                return self._recargar(true);
            });
    },

    // ------------------------------------------------------------------ pintar
    _pintar: function () {
        var $donde = this.$('.o_content').length ? this.$('.o_content') : this.$el;
        var d = this.datos || {areas: [], personas: [], filas: []};
        var porArea = {};
        _.each(d.personas, function (p) { (porArea[p.area || ''] = porArea[p.area || ''] || []).push(p); });
        var h = '<div class="o_kta">' +
            '<div class="o_kta_barra"><b>Tablero</b><span class="o_kta_hueco"></span>' +
            '<span class="o_kta_mut">Actualizado ' + esc(d.hora || '') + '</span>' +
            '<button type="button" class="btn btn-sm btn-primary o_kta_actualizar">Actualizar</button></div>' +
            '<div class="o_kta_expl">Arrastra a una persona a una zona de Picking: la hará después de lo que tiene ' +
            'entre manos. Las demás áreas solo se miran.</div><div class="o_kta_cols">';
        h += this._picking(d, porArea.picking || []);
        var self = this;
        _.each(d.areas, function (a) {
            if (a.codigo === 'picking') { return; }
            h += self._columna(a.nombre, porArea[a.codigo] || [], '');
        });
        h += this._columna('Sin área', porArea[''] || [], 'o_kta_sin',
                           'Han trabajado hoy y ahora no están en ningún área');
        $donde.html(h + '</div></div>');
    },

    _persona: function (p, conDetalle) {
        var cls = p.estado === 'parado' ? 'o_kta_par' : (p.estado === 'trabaja' ? 'o_kta_ok' : 'o_kta_nada');
        var titulo = p.nombre + (p.uds ? ' · ' + p.uds + ' uds hoy' : '') +
                     (p.cola && p.cola.length ? ' · en cola: ' + p.cola.join(', ') : '');
        var h = '<div class="o_kta_p ' + cls + '" draggable="true" data-persona="' + p.id + '" title="' +
                esc(titulo) + '"><span class="o_kta_av" role="presentation">' + esc(p.ini) + '</span>' +
                '<span class="o_kta_pn"><b>' + esc(p.nombre) + '</b>';
        if (conDetalle !== false && (p.detalle || p.desde)) {
            h += '<span class="o_kta_mut">' + esc(p.detalle) + (p.desde ? ' · desde ' + esc(p.desde) : '') +
                 '</span>';
        }
        return h + '</span></div>';
    },

    _columna: function (titulo, personas, cls, ayuda) {
        var self = this;
        var h = '<div class="o_kta_col ' + (cls || '') + '"><div class="o_kta_hd"><b>' + esc(titulo) + '</b>' +
                '<span class="o_kta_n">' + personas.length + '</span></div>';
        if (ayuda) { h += '<div class="o_kta_mut">' + esc(ayuda) + '</div>'; }
        _.each(personas, function (p) { h += self._persona(p); });
        if (!personas.length) { h += '<div class="o_kta_vacio">nadie</div>'; }
        return h + '</div>';
    },

    _picking: function (d, personas) {
        var self = this;
        var enFila = {};
        var sueltos = [];
        var ids = _.pluck(d.filas, 'batch_id');
        _.each(personas, function (p) {
            if (p.lote && ids.indexOf(p.lote) >= 0) {
                (enFila[p.lote] = enFila[p.lote] || []).push(p);
            } else {
                sueltos.push(p);
            }
        });
        var h = '<div class="o_kta_col o_kta_picking"><div class="o_kta_hd"><b>Picking</b>' +
                '<span class="o_kta_n">' + personas.length + '</span></div>';
        _.each(d.filas, function (f) {
            var gente = enFila[f.batch_id] || [];
            h += '<div class="o_kta_fila' + (f.pieza_id ? ' o_kta_libre' : '') + '"' +
                 (f.pieza_id ? ' data-pieza="' + f.pieza_id + '"' : '') + '><div class="o_kta_fcab">' +
                 (f.orden ? '<span class="o_kta_orden" title="Orden en que se da">' + f.orden + '.ª</span>' : '') +
                 '<b>' + esc(f.nombre) + '</b>' +
                 (f.entera ? '<span class="o_kta_tag" title="Entera, para una sola persona">entera</span>' : '') +
                 '<span class="o_kta_mut o_kta_der">' + esc(f.texto) + '</span></div>' +
                 '<div class="o_kta_prog" role="presentation"><i style="width:' + (f.pct || 0) + '%"></i></div>' +
                 '<div class="o_kta_gente">';
            _.each(gente, function (p) { h += self._persona(p, false); });
            if (!gente.length) {
                h += '<span class="o_kta_mut">' + (f.pieza_id ? 'nadie · arrastra aquí' : 'nadie') + '</span>';
            }
            h += '</div></div>';
        });
        if (!d.filas.length) {
            h += '<div class="o_kta_vacio">No hay zonas ni agrupaciones con trabajo libre.</div>';
        }
        if (sueltos.length) {
            h += '<div class="o_kta_fila"><div class="o_kta_fcab"><b>Otros pedidos</b></div><div class="o_kta_gente">';
            _.each(sueltos, function (p) { h += self._persona(p); });
            h += '</div></div>';
        }
        return h + '</div>';
    },

    // ------------------------------------------------------------------ eventos
    _onActualizar: function () { this._recargar(true); },

    _onDragStart: function (ev) {
        var $t = $(ev.currentTarget);
        this.arrastrando = parseInt($t.attr('data-persona'), 10) || 0;
        var dt = ev.originalEvent && ev.originalEvent.dataTransfer;
        if (dt) {
            dt.effectAllowed = 'move';
            try { dt.setData('text/plain', String(this.arrastrando)); } catch (e) { /* navegadores viejos */ }
        }
        $t.addClass('o_kta_arrastrado');
    },
    _onDragEnd: function (ev) {
        $(ev.currentTarget).removeClass('o_kta_arrastrado');
        this.$('.o_kta_encima').removeClass('o_kta_encima');
        var self = this;
        setTimeout(function () { self.arrastrando = null; }, 0);
    },
    _onDragOver: function (ev) {
        if (!this.arrastrando) { return; }
        ev.preventDefault();
        var $d = $(ev.currentTarget);
        this.$('.o_kta_encima').not($d).removeClass('o_kta_encima');
        $d.addClass('o_kta_encima');
    },
    _onDragLeave: function (ev) {
        if (!$.contains(ev.currentTarget, ev.originalEvent.relatedTarget)) {
            $(ev.currentTarget).removeClass('o_kta_encima');
        }
    },
    _onDrop: function (ev) {
        var emp = this.arrastrando;
        if (!emp) { return; }
        ev.preventDefault();
        this.arrastrando = null;
        this.$('.o_kta_encima').removeClass('o_kta_encima');
        return this._mover(parseInt($(ev.currentTarget).attr('data-pieza'), 10), emp);
    },
});

core.action_registry.add('koroshi_tablero_areas', TableroAreas);
return TableroAreas;
});
