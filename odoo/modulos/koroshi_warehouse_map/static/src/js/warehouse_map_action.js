odoo.define('koroshi_warehouse_map.action', function (require) {
    'use strict';

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');

    var WarehouseMapAction = AbstractAction.extend({
        className: 'o_koroshi_warehouse_map_action',

        start: function () {
            this.$el.empty();
            // v.45: la ruta /planner pone ?v=<version del manifest> (antes estaba escrita a mano aqui)
            var mode = this.context && this.context.koroshi_mode === 'ops' ? '?mode=ops' : '';
            this.$iframe = $('<iframe>', {
                class: 'o_koroshi_warehouse_map_frame',
                title: 'Mapa KOROSHI NAU-2',
                src: '/koroshi_warehouse_map/planner' + mode,
                frameborder: '0',
                allow: 'fullscreen',
            });
            this.$el.append(this.$iframe);
            return this._super.apply(this, arguments);
        },
    });

    core.action_registry.add('koroshi_warehouse_map', WarehouseMapAction);
    return WarehouseMapAction;
});
