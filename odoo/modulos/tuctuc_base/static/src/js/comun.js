odoo.define('tuctuc_base.comun', function (require) {
'use strict';
/* TUCTUC Base v1.0.0: lo común de las pantallas de la PDA de Oriola - Amposta (clon de koroshi_base.comun 1.2.1).
 * Uso: var comun = require('tuctuc_base.comun');
 *   comun.esCaja(codigo)                                   -> caja de OUT (BOX + 7 cifras, la secuencia de Odoo)
 *   comun.tarjeta.leer() / guardar(persona) / vigente(g, ms) / minutos(widget)  -> la tarjeta compartida
 *   comun.esFinDeLectura(ev), comun.leerAlParar(widget, campo, leer, opciones), comun.cancelarLector(widget)
 * Sin compañía fija: la nave tiene tres compañías y la compañía sale de cada documento (en el servidor). */
var session = require('web.session');

var RE_CAJA = /^BOX\d{7}$/;    // misma regla que comun.PATRON_CAJA (parámetro tuctuc_base.patron_caja)
var RAFAGA_MS = 150;       // el lector ha parado si pasan 150 ms sin caracteres (Odoo en el movil usa 55 ms)
var MIN_RAFAGA = 4;        // con soloRafaga: caracteres minimos que llegan de golpe para ser una lectura
var MAX_MS_TECLA = 40;     // con soloRafaga: media maxima entre caracteres (una persona tarda 100 ms o mas)

function esCaja(codigo) {
    return RE_CAJA.test(String(codigo || '').trim().toUpperCase());
}

// ---------------------------------------------------------------- tarjeta de operario compartida
// Memoria de la PDA, clave tuctuc_operarios_pda_<usuario de Odoo>, valor {id, nombre, t}. La ponen Lecturas,
// Contenedores y Faltante: pasar la tarjeta en una vale para las demás.
var tarjeta = {
    clave: function () {
        return 'tuctuc_operarios_pda_' + (session.uid || '');
    },
    // {id, nombre, t} o null (sin memoria o vacia)
    leer: function () {
        try {
            var v = window.localStorage.getItem(tarjeta.clave());
            var g = v ? JSON.parse(v) : null;
            return g && g.id ? g : null;
        } catch (e) { return null; }
    },
    // guarda {id, nombre} con la hora de ahora; devuelve esa hora (0 si no hay persona)
    guardar: function (persona) {
        if (!persona || !persona.id) { return 0; }
        var t = Date.now();
        try {
            window.localStorage.setItem(tarjeta.clave(), JSON.stringify({id: persona.id, nombre: persona.nombre, t: t}));
        } catch (e) { /* sin memoria: solo en esta pantalla */ }
        return t;
    },
    // true si la guardada sirve: tiene id y no lleva mas de ms sin actividad (sin hora = de Lecturas antigua: vale)
    vigente: function (g, ms) {
        return !!(g && g.id && !(g.t && Date.now() - g.t > ms));
    },
    // minutos que dura la tarjeta sin actividad (parámetro tuctuc_operarios.minutos_tarjeta); 0 si no se sabe
    minutos: function (widget) {
        return widget._rpc({route: '/tuctuc/operarios/minutos_tarjeta', params: {}}, {shadow: true})
            .then(function (r) {
                return r && r.ok && r.minutos > 0 ? r.minutos : 0;
            }, function (e) {
                if (e && e.event && e.event.preventDefault) { e.event.preventDefault(); }
                return 0;
            });
    },
};

// ---------------------------------------------------------------- lector
// Intro o tabulador al final de una lectura (segun como este configurado el lector)
function esFinDeLectura(ev) {
    return ev.which === 13 || ev.which === 9 || ev.key === 'Enter';
}

// Para el evento «input» del campo de lectura. Las PDA no mandan Intro ni tabulador al final y, con el campo marcado,
// Odoo no pasa la lectura al bus: se quedaba escrita (koroshi_contenedores 1.9.3). Se lee cuando el lector para RAFAGA_MS.
// opciones.soloRafaga: en campos donde tambien se escribe a mano, solo se lee lo que ha llegado de golpe (MIN_RAFAGA
// caracteres o mas, MAX_MS_TECLA de media entre ellos); lo escrito a mano espera al Intro.
function leerAlParar(widget, campo, leer, opciones) {
    opciones = opciones || {};
    var ahora = Date.now();
    var r = widget._kbRafaga;
    if (!r) {
        r = widget._kbRafaga = {inicio: ahora, desde: widget._kbLargo || 0, eventos: 0, timer: null};
    }
    r.eventos += 1;
    r.ultimo = ahora;
    widget._kbLargo = (campo.value || '').length;
    clearTimeout(r.timer);
    r.timer = setTimeout(function () {
        if (widget._kbRafaga === r) { widget._kbRafaga = null; }
        var valor = campo.value || '';
        var codigo = valor.trim();
        if (!codigo) {                  // ya se leyo con Intro o tabulador
            widget._kbLargo = 0;
            return;
        }
        if (opciones.soloRafaga) {
            var nuevos = valor.length - r.desde;
            var media = r.eventos > 1 ? (r.ultimo - r.inicio) / (r.eventos - 1) : 0;
            if (nuevos < MIN_RAFAGA || media > MAX_MS_TECLA) { return; }   // escrito a mano: espera al Intro
        }
        campo.value = '';
        widget._kbLargo = 0;
        leer(codigo);
    }, opciones.ms || RAFAGA_MS);
}

// Al leer con Intro (o al vaciar el campo a mano): que no salte despues el lector al parar
function cancelarLector(widget) {
    if (widget._kbRafaga) { clearTimeout(widget._kbRafaga.timer); }
    widget._kbRafaga = null;
    widget._kbLargo = 0;
}

return {
    RE_CAJA: RE_CAJA,
    RAFAGA_MS: RAFAGA_MS,
    esCaja: esCaja,
    tarjeta: tarjeta,
    esFinDeLectura: esFinDeLectura,
    leerAlParar: leerAlParar,
    cancelarLector: cancelarLector,
};
});
