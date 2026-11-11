odoo.define('koroshi_monitor.mobile_swipe_guard', function (require) {
'use strict';

// El include mobil del nucli defineix _enableSwipe. Exigir-lo com a dependencia garanteix
// que aquest guard s'aplica despres del codi original, independentment de l'ordre d'assets.
require('web.KanbanRendererMobile');
var config = require('web.config');
var KanbanRenderer = require('web.KanbanRenderer');

if (!config.device.isMobile) {
    return;
}

KanbanRenderer.include({
    _enableSwipe: function () {
        if (!this.$el || typeof this.$el.swipe !== 'function') {
            // Les pestanyes del Kanban continuen funcionant; nomes s'omet el gest lateral.
            // No llancem una excepcio que tapi o bloquegi Inventari en una PDA.
            if (window.console && window.console.warn) {
                window.console.warn('KOROSHI: TouchSwipe no disponible; gest lateral desactivat.');
            }
            return;
        }
        return this._super.apply(this, arguments);
    },
});
});
