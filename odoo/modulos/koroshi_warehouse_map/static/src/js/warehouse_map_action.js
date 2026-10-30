odoo.define('koroshi_warehouse_map.action', function (require) {
    'use strict';

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');

    var WarehouseMapAction = AbstractAction.extend({
        className: 'o_koroshi_warehouse_map_action',

        start: function () {
            this.$el.empty();
            this.$iframe = $('<iframe>', {
                class: 'o_koroshi_warehouse_map_frame',
                title: 'Mapa KOROSHI NAU-2',
                src: '/koroshi_warehouse_map/static/src/html/warehouse_planner_20261029_v1.html?v=20261029_1730_v35',
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
