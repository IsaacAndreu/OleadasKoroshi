odoo.define('koroshi_actividades.TableroPda', function (require) {
'use strict';
/* KOROSHI Actividades v1.5.0 - en Lecturas (PDA, koroshi_operarios): tarjeta de actividad del tablero.
 *
 * Cuando a un operario le toca una actividad (p. ej. «Manipulación devoluciones»), la PDA no abre nada: enseña
 * «Tu responsable te pide» con la actividad y «Ve al portátil de Actividades». Sin botones: la tarjeta se acaba
 * cuando pulsa «Fin» en el portátil. Mientras, cada 30 s se pide la siguiente (si la pantalla se ve y no está
 * ocupada): en cuanto el Fin la acaba, la PDA pasa sola a lo siguiente, como al volver de una OUT validada.
 */
var Operarios = require('koroshi_operarios.Pantalla');

var VIGILAR_MS = 30000;

Operarios.include({
    _abrir: function (obj) {
        if (obj && obj.tipo === 'actividad') {
            this.ocupado = false;
            this._ocultarCapa();
            this._pintarActual();
            if (this.kaAvisada !== obj.id) {
                this.kaAvisada = obj.id;
                this._aviso('Ve al portátil de Actividades: ' + (obj.ref || '') +
                            '. Pasa tu tarjeta y empieza. Al acabar, pulsa Fin allí.', 'info');
            }
            this._kaVigilar();
            return Promise.resolve();
        }
        return this._super.apply(this, arguments);
    },

    _pintarActual: function () {
        var res = this._super.apply(this, arguments);
        if (this.actual && this.actual.tipo === 'actividad') {
            this.$('.o_ko_actual_sub').text('Tu responsable te pide');
            this.$('.o_ko_continuar, .o_ko_botonera, .o_ko_pausa, .o_ko_nota_hecha').hide();
        }
        return res;
    },

    _kaVigilar: function () {
        var self = this;
        clearInterval(this.kaTimer);
        this.kaTimer = setInterval(function () {
            if (!self.actual || self.actual.tipo !== 'actividad' || !self.operario) {
                clearInterval(self.kaTimer);
                self.kaTimer = null;
                return;
            }
            if (self.ocupado || self.capa || self.sinRed || !self.el || !$.contains(document, self.el) ||
                    self.$('.o_ko_hoja').is(':visible')) {
                return;
            }
            self._siguiente('si_nueva');
        }, VIGILAR_MS);
    },

    destroy: function () {
        clearInterval(this.kaTimer);
        return this._super.apply(this, arguments);
    },
});
return Operarios;
});
