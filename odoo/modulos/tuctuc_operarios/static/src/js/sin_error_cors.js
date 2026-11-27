odoo.define('tuctuc_operarios.sin_error_cors', function () {
'use strict';
/* v2.11.1 (13/11/2026): en las PDA, al entrar en Odoo (y al salir de Código de barras) salía «Odoo Client Error ·
 * Error de CORS desconocido». No es de Odoo ni de los módulos: el navegador de la PDA avisa de un error de un script
 * que no es de Odoo, sin fichero ni línea («Script error.»), y Odoo lo enseña en una ventana. Odoo deja que otro lo
 * atienda con window.onOriginError: aquí se apunta en la consola y no sale la ventana. Los errores de verdad (con
 * fichero y línea) siguen saliendo igual. Odoo borra window.onOriginError cada vez que lo usa: se vuelve a poner. */
function callar() {
    try { console.warn('TUCTUC: error de script sin detalles (CORS) ignorado'); } catch (e) { /* nada */ }
    setTimeout(poner, 0);
}
function poner() {
    if (window.onOriginError !== callar) { window.onOriginError = callar; }
}
poner();
});
