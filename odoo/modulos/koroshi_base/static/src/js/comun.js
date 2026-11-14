odoo.define('koroshi_base.comun', function (require) {
'use strict';
/* KOROSHI Base v1.0.0 (auditoria 13/11, fase 6): lo que se repetia en las pantallas KOROSHI.
 * Uso: var comun = require('koroshi_base.comun'); comun.esMatricula(codigo)
 * La misma regla que comun.py: CJ + 9 cifras, sin espacios y en mayusculas o minusculas. */
var RE_CJ = /^CJ\d{9}$/;

function esMatricula(codigo) {
    return RE_CJ.test(String(codigo || '').trim().toUpperCase());
}

return {
    COMPANY_ID: 8,
    RE_CJ: RE_CJ,
    esMatricula: esMatricula,
};
});
