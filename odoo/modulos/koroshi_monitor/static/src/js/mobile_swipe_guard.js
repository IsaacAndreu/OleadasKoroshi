odoo.define('koroshi_monitor.mobile_swipe_guard', function (require) {
'use strict';

// El include movil del nucleo define _enableSwipe. Exigirlo como dependencia garantiza
// que esta proteccion se aplica despues del codigo original, sea cual sea el orden de los assets.
require('web.KanbanRendererMobile');
var config = require('web.config');
var KanbanRenderer = require('web.KanbanRenderer');

if (!config.device.isMobile) {
    return;
}

KanbanRenderer.include({
    _enableSwipe: function () {
        if (!this.$el || typeof this.$el.swipe !== 'function') {
            // Las pestanas del Kanban siguen funcionando; solo se omite el gesto lateral.
            // No se lanza una excepcion que tape o bloquee Inventario en una PDA.
            if (window.console && window.console.warn) {
                window.console.warn('KOROSHI: TouchSwipe no disponible; gesto lateral desactivado.');
            }
            return;
        }
        return this._super.apply(this, arguments);
    },
});
});
