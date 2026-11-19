odoo.define('koroshi_operarios.Tablero', function (require) {
'use strict';
/* KOROSHI Operarios v2.20.0 - Tablero del responsable (vista kanban js_class="koroshi_tablero").
 *
 * Solo añade al kanban de siempre:
 * - la columna sin operario se llama «Por repartir» y va la primera (CSS order);
 * - botón «Actualizar»: recalcula las piezas por repartir (tablero_refrescar) y recarga;
 * - cada minuto lo mismo, si la pestaña se ve y no se está arrastrando nada;
 * - después de soltar una tarjeta, recarga (al dar una zona o una nota, la pieza vuelve a «Por repartir»).
 * Arrastrar lo hace el kanban de Odoo: el servidor decide qué se puede mover (models/tablero.py).
 */
var KanbanColumn = require('web.KanbanColumn');
var KanbanController = require('web.KanbanController');
var KanbanRenderer = require('web.KanbanRenderer');
var KanbanView = require('web.KanbanView');
var viewRegistry = require('web.view_registry');

var REFRESCO_MS = 60000;
var TRAS_SOLTAR_MS = 1500;

var Columna = KanbanColumn.extend({
    init: function (parent, data) {
        this._super.apply(this, arguments);
        this.esPiezas = !data.res_id;
        if (this.esPiezas) { this.title = 'Por repartir'; }
    },
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            if (self.esPiezas) { self.$el.addClass('o_kt_piezas'); }
        });
    },
});

var Renderer = KanbanRenderer.extend({
    config: _.extend({}, KanbanRenderer.prototype.config, {KanbanColumn: Columna}),
});

var Controller = KanbanController.extend({
    renderButtons: function ($node) {
        this._super.apply(this, arguments);
        var self = this;
        var $b = $('<button type="button" class="btn btn-primary o_kt_actualizar"/>').text('Actualizar');
        $b.on('click', function () { self._ktActualizar(); });
        if (this.$buttons) {
            this.$buttons.append($b);
        } else if ($node) {
            this.$buttons = $('<div/>').append($b);
            this.$buttons.appendTo($node);
        }
    },
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.ktTimer = setInterval(function () {
                if (document.hidden || $('.ui-sortable-helper').length || self.ktOcupado) { return; }
                self._ktActualizar();
            }, REFRESCO_MS);
        });
    },
    destroy: function () {
        clearInterval(this.ktTimer);
        clearTimeout(this.ktTrasSoltar);
        this._super.apply(this, arguments);
    },
    _ktActualizar: function () {
        var self = this;
        if (this.ktOcupado) { return Promise.resolve(); }
        this.ktOcupado = true;
        return this._rpc({model: 'koroshi.operario.asignacion', method: 'tablero_refrescar', args: []})
            .then(function () { return self.reload(); })
            .then(function () { self.ktOcupado = false; }, function () { self.ktOcupado = false; });
    },
    _onAddRecordToColumn: function () {
        var self = this;
        var res = this._super.apply(this, arguments);
        clearTimeout(this.ktTrasSoltar);
        this.ktTrasSoltar = setTimeout(function () { self._ktActualizar(); }, TRAS_SOLTAR_MS);
        return res;
    },
});

var Tablero = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Controller: Controller,
        Renderer: Renderer,
    }),
});

viewRegistry.add('koroshi_tablero', Tablero);
return Tablero;
});
