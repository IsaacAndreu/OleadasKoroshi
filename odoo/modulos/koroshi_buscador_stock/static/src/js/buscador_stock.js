odoo.define('koroshi_buscador_stock.Pantalla', function (require) {
'use strict';
/* KOROSHI Buscador de stock v1.1.0 - pantalla de la oficina, SOLO LECTURA.
 * v1.1: el modelo enseña dónde están todas sus tallas sin pulsar ninguna; un solo modelo encontrado se abre solo.
 * Una caja: lineal (L94), contenedor KO_/TT_ (o un trozo), código de hueco, EAN o referencia, o un trozo de la
 * referencia o la descripción (lista de modelos). Un modelo enseña sus tallas/colores con stock, reservado, libre y
 * entradas pendientes; una talla, dónde está, qué OUT la reservan y qué recepciones la traen. Un hueco o contenedor,
 * lo que tiene dentro. «← Atrás» vuelve a la pantalla anterior. Todo dentro de .o_koroshi_buscador_stock.
 * Sin aria-hidden (Odoo 13 lo oculta): role="presentation". */
var AbstractAction = require('web.AbstractAction');
var core = require('web.core');

function _e(t) { return _.escape(t == null ? '' : String(t)); }
function _n(x) { return (Math.round((x || 0) * 100) / 100).toString().replace('.', ','); }
function _ficha(modelo, id, texto) {
    if (!id) { return _e(texto); }
    return '<a href="/web#id=' + id + '&amp;model=' + modelo + '&amp;view_type=form" target="_blank" ' +
        'rel="noopener">' + _e(texto) + '</a>';
}
function _celdaN(x, clase) {
    return '<td class="o_kb_n' + (clase ? ' ' + clase : '') + '">' + _n(x) + '</td>';
}

var Pantalla = AbstractAction.extend({
    contentTemplate: 'koroshi_buscador_stock.Pantalla',
    events: {
        'keydown .o_kb_texto': '_onKeydown',
        'click .o_kb_buscar': '_onBuscar',
        'click .o_kb_atras': '_onAtras',
        'click .o_kb_ir_modelo': '_onIrModelo',
        'click .o_kb_ir_prenda': '_onIrPrenda',
        'click .o_kb_ir_ubicacion': '_onIrUbicacion',
    },

    init: function () {
        this._super.apply(this, arguments);
        this.historia = [];     // pantallas anteriores: {route, params}
        this.actual = null;
        this.ocupado = false;
    },

    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self._pintarAtras();
            setTimeout(function () { self.$('.o_kb_texto').focus(); }, 50);
        });
    },

    // ---------------------------------------------------------------- navegación
    _ir: function (route, params, sinHistoria) {
        var self = this;
        if (this.ocupado) { return Promise.resolve(); }
        this.ocupado = true;
        this._aviso('Buscando…', 'o_kb_info');
        return this._rpc({route: route, params: params}).then(function (r) {
            self.ocupado = false;
            if (!r || !r.ok) {
                self._aviso((r && r.msg) || 'Error al buscar.', 'o_kb_mal');
                return;
            }
            if (self.actual && !sinHistoria) { self.historia.push(self.actual); }
            self.actual = {route: route, params: params};
            self._aviso('', '');
            self._pintar(r);
        }, function () {
            self.ocupado = false;
            self._aviso('No se puede hablar con Odoo. Vuelve a probar.', 'o_kb_mal');
        });
    },

    _onKeydown: function (ev) {
        if (ev.key === 'Enter') { ev.preventDefault(); this._onBuscar(); }
    },
    _onBuscar: function () {
        var texto = (this.$('.o_kb_texto').val() || '').trim();
        if (!texto) { this._aviso('Escribe algo para buscar.', 'o_kb_mal'); return; }
        this._ir('/koroshi/buscador_stock/buscar', {texto: texto});
    },
    _onAtras: function () {
        if (!this.historia.length || this.ocupado) { return; }
        var anterior = this.historia.pop();
        var self = this;
        this._ir(anterior.route, anterior.params, true).then(function () { self._pintarAtras(); });
    },
    _onIrModelo: function (ev) {
        ev.preventDefault();
        this._ir('/koroshi/buscador_stock/modelo', {plantilla_id: $(ev.currentTarget).data('id')});
    },
    _onIrPrenda: function (ev) {
        ev.preventDefault();
        var $t = $(ev.currentTarget);
        this._ir('/koroshi/buscador_stock/modelo', {plantilla_id: $t.data('plantilla'), producto_id: $t.data('id')});
    },
    _onIrUbicacion: function (ev) {
        ev.preventDefault();
        this._ir('/koroshi/buscador_stock/ubicacion', {ubicacion_id: $(ev.currentTarget).data('id')});
    },

    // ---------------------------------------------------------------- pintar
    _aviso: function (texto, clase) {
        this.$('.o_kb_aviso').removeClass('o_kb_ok o_kb_mal o_kb_info').addClass(clase || '').text(texto || '');
    },
    _pintarAtras: function () {
        this.$('.o_kb_atras').prop('disabled', !this.historia.length);
    },
    _pintar: function (r) {
        var html = '';
        if (r.tipo === 'lista') { html = this._htmlLista(r); }
        else if (r.tipo === 'modelo') { html = this._htmlModelo(r.modelo, r.prenda); }
        else if (r.tipo === 'ubicacion') { html = this._htmlUbicacion(r.ubicacion); }
        else if (r.tipo === 'lineal') { html = this._htmlLineal(r.lineal); }
        this.$('.o_kb_resultado').html(html);
        this._pintarAtras();
        var el = this.$('.o_kb_resultado')[0];
        if (el && el.scrollIntoView) { el.scrollIntoView(); }
    },

    _htmlLista: function (r) {
        var h = '<div class="o_kb_card"><h3>Resultados de «' + _e(r.texto) + '»</h3>';
        if (r.modelos.length) {
            h += '<h4>Modelos</h4><table><thead><tr><th>Modelo</th><th>Referencia</th><th class="o_kb_n">Tallas</th>' +
                '<th class="o_kb_n">Stock</th><th class="o_kb_n">Reservado</th><th class="o_kb_n">Libre</th>' +
                '</tr></thead><tbody>';
            _.each(r.modelos, function (m) {
                h += '<tr><td><a href="#" class="o_kb_ir_modelo" data-id="' + m.id + '">' + _e(m.nombre) + '</a></td>' +
                    '<td>' + _e(m.referencia) + '</td>' + _celdaN(m.variantes) + _celdaN(m.uds) +
                    _celdaN(m.reservadas) + _celdaN(m.libres, 'o_kb_libre') + '</tr>';
            });
            h += '</tbody></table>';
            if (r.modelos_mas) { h += '<p class="o_kb_mas">Hay más modelos: escribe algo más concreto.</p>'; }
        }
        if (r.contenedores.length) {
            h += '<h4>Contenedores</h4><table><thead><tr><th>Contenedor</th><th>Hueco</th></tr></thead><tbody>';
            _.each(r.contenedores, function (c) {
                h += '<tr><td><a href="#" class="o_kb_ir_ubicacion" data-id="' + c.id + '">' + _e(c.nombre) +
                    '</a></td><td>' + _e(c.hueco) + '</td></tr>';
            });
            h += '</tbody></table>';
            if (r.contenedores_mas) { h += '<p class="o_kb_mas">Hay más contenedores: escribe algo más concreto.</p>'; }
        }
        return h + '</div>';
    },

    _htmlModelo: function (m, prenda) {
        var h = '<div class="o_kb_card"><h3>' + _ficha('product.template', m.id, m.nombre) + '</h3>' +
            '<table><thead><tr><th>Talla / color</th><th>Referencia</th><th>EAN</th><th class="o_kb_n">Stock</th>' +
            '<th class="o_kb_n">Reservado</th><th class="o_kb_n">Libre</th><th class="o_kb_n">Entradas pendientes</th>' +
            '</tr></thead><tbody>';
        _.each(m.filas, function (f) {
            var marcada = prenda && prenda.id === f.id ? ' class="o_kb_marcada"' : '';
            h += '<tr' + marcada + '><td><a href="#" class="o_kb_ir_prenda" data-id="' + f.id + '" data-plantilla="' +
                m.id + '">' + _e(f.variante) + '</a></td><td>' + _e(f.referencia) + '</td><td>' + _e(f.ean) +
                '</td>' + _celdaN(f.uds) + _celdaN(f.reservadas) + _celdaN(f.libres, 'o_kb_libre') +
                _celdaN(f.entradas) + '</tr>';
        });
        h += '</tbody><tfoot><tr><td colspan="3">Total</td>' + _celdaN(m.total.uds) + _celdaN(m.total.reservadas) +
            _celdaN(m.total.libres, 'o_kb_libre') + _celdaN(m.total.entradas) + '</tr></tfoot></table>';
        h += '<p class="o_kb_nota">Pulsa una talla o color para ver quién la reserva y qué entradas la traen.</p></div>';
        if (prenda) { return h + this._htmlPrenda(prenda); }
        // v1.1: ubicaciones de todo el modelo (todas las tallas), sin pulsar ninguna
        h += '<div class="o_kb_card"><h4>Dónde está (todas las tallas)</h4>';
        if (!m.donde.length) {
            h += '<p class="o_kb_vacio">No hay stock en ninguna ubicación interna.</p>';
        } else {
            h += '<table><thead><tr><th>Hueco</th><th>Contenedor</th><th>Talla / color</th><th class="o_kb_n">Uds</th>' +
                '<th class="o_kb_n">Reservadas</th><th class="o_kb_n">Libres</th></tr></thead><tbody>';
            _.each(m.donde, function (d) {
                h += '<tr><td><a href="#" class="o_kb_ir_ubicacion" data-id="' + d.hueco_id + '">' + _e(d.hueco) +
                    '</a></td><td>' + (d.contenedor ? '<a href="#" class="o_kb_ir_ubicacion" data-id="' +
                    d.ubicacion_id + '">' + _e(d.contenedor) + '</a>' : '') + '</td><td><a href="#" ' +
                    'class="o_kb_ir_prenda" data-id="' + d.producto_id + '" data-plantilla="' + m.id + '">' +
                    _e(d.variante) + '</a></td>' + _celdaN(d.uds) + _celdaN(d.reservadas) +
                    _celdaN(d.libres, 'o_kb_libre') + '</tr>';
            });
            h += '</tbody></table>';
            if (m.donde_mas) { h += '<p class="o_kb_mas">Se ven las primeras 200 ubicaciones.</p>'; }
        }
        return h + '</div>';
    },

    _htmlPrenda: function (p) {
        var h = '<div class="o_kb_card"><h3>' + _ficha('product.product', p.id, p.nombre) + '</h3>' +
            '<p class="o_kb_sub">EAN ' + _e(p.ean || '—') + ' · stock ' + _n(p.uds) + ' · reservado ' + _n(p.reservadas) +
            ' · libre ' + _n(p.uds - p.reservadas) + ' · entradas pendientes ' + _n(p.entradas_uds) + '</p>';
        // 1. Dónde está
        h += '<h4>Dónde está</h4>';
        if (!p.donde.length) {
            h += '<p class="o_kb_vacio">No hay stock en ninguna ubicación interna.</p>';
        } else {
            h += '<table><thead><tr><th>Hueco</th><th>Contenedor</th><th class="o_kb_n">Uds</th>' +
                '<th class="o_kb_n">Reservadas</th><th class="o_kb_n">Libres</th></tr></thead><tbody>';
            _.each(p.donde, function (d) {
                h += '<tr><td><a href="#" class="o_kb_ir_ubicacion" data-id="' + d.hueco_id + '">' + _e(d.hueco) +
                    '</a></td><td>' + (d.contenedor ? '<a href="#" class="o_kb_ir_ubicacion" data-id="' +
                    d.ubicacion_id + '">' + _e(d.contenedor) + '</a>' : '') + '</td>' + _celdaN(d.uds) +
                    _celdaN(d.reservadas) + _celdaN(d.libres, 'o_kb_libre') + '</tr>';
            });
            h += '</tbody></table>';
            if (p.donde_mas) { h += '<p class="o_kb_mas">Y ' + p.donde_mas + ' ubicaciones más.</p>'; }
        }
        // 2. Quién la reserva
        h += '<h4>Quién la reserva</h4>' + this._htmlReservas(p.reservas, false);
        // 3. Entradas pendientes
        h += '<h4>Entradas pendientes</h4>';
        if (!p.entradas.length) {
            h += '<p class="o_kb_vacio">No hay recepciones abiertas que la traigan.</p>';
        } else {
            h += '<table><thead><tr><th>Recepción</th><th>Origen</th><th>Fecha prevista</th><th>Estado</th>' +
                '<th class="o_kb_n">Uds</th></tr></thead><tbody>';
            _.each(p.entradas, function (e) {
                h += '<tr><td>' + _ficha('stock.picking', e.id, e.nombre) + '</td><td>' + _e(e.origen) + '</td><td>' +
                    _e(e.fecha) + '</td><td>' + _e(e.estado_txt) + '</td>' + _celdaN(e.uds) + '</tr>';
            });
            h += '</tbody></table>';
            if (p.entradas_mas) { h += '<p class="o_kb_mas">Hay más recepciones abiertas.</p>'; }
        }
        return h + '</div>';
    },

    _htmlReservas: function (r, conPrendas) {
        if (!r.filas.length) { return '<p class="o_kb_vacio">Nada reservado.</p>'; }
        var h = '<table><thead><tr><th>Albarán</th><th>Origen</th><th>Tipo</th><th>Estado</th>' +
            (conPrendas ? '<th>Prendas</th>' : '') + '<th>Sale de</th><th class="o_kb_n">Uds reservadas</th>' +
            '</tr></thead><tbody>';
        _.each(r.filas, function (f) {
            h += '<tr><td>' + _ficha('stock.picking', f.id, f.nombre) + '</td><td>' + _e(f.origen) + '</td><td>' +
                _e(f.tipo) + '</td><td>' + _e(f.estado_txt) + '</td>' + (conPrendas ? '<td>' + _e(f.prendas) +
                '</td>' : '') + '<td>' + _e(f.desde) + '</td>' + _celdaN(f.uds) + '</tr>';
        });
        h += '</tbody></table>';
        if (r.mas) { h += '<p class="o_kb_mas">Hay más albaranes con reserva (se ven los primeros 100).</p>'; }
        return h;
    },

    _htmlUbicacion: function (u) {
        var h = '<div class="o_kb_card"><h3>' + (u.es_contenedor ? 'Contenedor ' : 'Hueco ') +
            _ficha('stock.location', u.id, u.nombre) + (u.activo ? '' : ' <span class="o_kb_vacio">(archivado)</span>') +
            '</h3><p class="o_kb_sub">' + _e(u.completo) + ' · ' + _n(u.uds) + ' uds · ' + _n(u.reservadas) +
            ' reservadas · ' + _n(u.uds - u.reservadas) + ' libres</p>';
        if (u.es_contenedor && u.hueco_id) {
            h += '<p>Está en el hueco <a href="#" class="o_kb_ir_ubicacion" data-id="' + u.hueco_id + '">' +
                _e(u.hueco) + '</a></p>';
        }
        if (u.contenedores.length) {
            h += '<h4>Contenedores (' + u.contenedores.length + ')</h4><table><thead><tr><th>Contenedor</th>' +
                '<th class="o_kb_n">Uds</th><th class="o_kb_n">Reservadas</th></tr></thead><tbody>';
            _.each(u.contenedores, function (c) {
                h += '<tr><td><a href="#" class="o_kb_ir_ubicacion" data-id="' + c.id + '">' + _e(c.nombre) +
                    '</a></td>' + _celdaN(c.uds) + _celdaN(c.reservadas) + '</tr>';
            });
            h += '</tbody></table>';
        }
        h += '<h4>Prendas</h4>';
        if (!u.filas.length) {
            h += '<p class="o_kb_vacio">Sin stock.</p>';
        } else {
            h += '<table><thead><tr>' + (u.es_contenedor ? '' : '<th>Contenedor</th>') + '<th>Prenda</th>' +
                '<th>Referencia</th><th>EAN</th><th class="o_kb_n">Uds</th><th class="o_kb_n">Reservadas</th>' +
                '<th class="o_kb_n">Libres</th></tr></thead><tbody>';
            _.each(u.filas, function (f) {
                h += '<tr>' + (u.es_contenedor ? '' : '<td>' + _e(f.contenedor || '(en el hueco)') + '</td>') +
                    '<td><a href="#" class="o_kb_ir_prenda" data-id="' + f.producto_id + '" data-plantilla="' +
                    f.plantilla_id + '">' + _e(f.nombre) + '</a></td><td>' + _e(f.referencia) + '</td><td>' +
                    _e(f.ean) + '</td>' + _celdaN(f.uds) + _celdaN(f.reservadas) + _celdaN(f.libres, 'o_kb_libre') +
                    '</tr>';
            });
            h += '</tbody></table>';
            if (u.mas) { h += '<p class="o_kb_mas">Y ' + u.mas + ' filas más.</p>'; }
        }
        h += '<h4>Reservas desde aquí</h4>' + this._htmlReservas(u.reservas, true);
        return h + '</div>';
    },

    _htmlLineal: function (l) {
        var h = '<div class="o_kb_card"><h3>Lineal ' + _e(l.codigo) + '</h3><p class="o_kb_sub">' + l.huecos.length +
            ' huecos · ' + l.con_stock + ' con stock · ' + _n(l.uds) + ' uds</p>';
        if (!l.huecos.length) {
            return h + '<p class="o_kb_vacio">No hay huecos con ' + _e(l.codigo) + ' en el nombre.</p></div>';
        }
        h += '<table><thead><tr><th>Hueco</th><th class="o_kb_n">Contenedores</th><th class="o_kb_n">Con stock</th>' +
            '<th class="o_kb_n">Uds</th><th class="o_kb_n">Reservadas</th></tr></thead><tbody>';
        _.each(l.huecos, function (f) {
            h += '<tr' + (f.uds ? ' class="o_kb_con"' : '') + '><td><a href="#" class="o_kb_ir_ubicacion" data-id="' +
                f.id + '">' + _e(f.nombre) + '</a></td>' + _celdaN(f.n_cont) + _celdaN(f.n_cont_stock) +
                _celdaN(f.uds) + _celdaN(f.reservadas) + '</tr>';
        });
        h += '</tbody></table>';
        if (l.truncado) { h += '<p class="o_kb_mas">Se ven los primeros 400 huecos.</p>'; }
        return h + '</div>';
    },
});

core.action_registry.add('koroshi_buscador_stock_pantalla', Pantalla);
return Pantalla;
});
