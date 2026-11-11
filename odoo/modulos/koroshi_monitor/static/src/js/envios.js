odoo.define('koroshi_monitor.envios', function (require) {
'use strict';

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');

function e(valor) {
    return _.escape(valor === undefined || valor === null ? '' : String(valor));
}

function numero(valor) {
    return Math.round(Number(valor || 0)).toLocaleString('es-ES');
}

var ConsultaEnvios = AbstractAction.extend({
    hasControlPanel: false,

    events: {
        'click .ke-monitor': '_onMonitor',
        'submit .ke-form': '_onBuscar',
        'click .ke-tab': '_onApartado',
        'click .ke-excel': '_onExcel',
        'change .ke-export-control': '_onExportControl',
        'click .ke-copiar': '_onCopiar',
        'click .ke-compartir': '_onCompartir',
        'click a.ke-out': '_onOut',
    },

    init: function () {
        this._super.apply(this, arguments);
        this.resultados = [];
        this.apartado = 'tiendas';
        this.transportistas = {tiendas: 'xpo', web: 'gls'};
        this.desde = this._hoy();
        this.hasta = this.desde;
    },

    _hoy: function () {
        var d = new Date();
        return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2);
    },

    start: function () {
        var self = this;
        this.$el.addClass('o_koroshi_envios');
        return this._super.apply(this, arguments).then(function () {
            self._pintarInicio();
            self.$('.ke-buscar').focus();
        });
    },

    getTitle: function () {
        return 'Consulta de envíos';
    },

    _cabecera: function (texto) {
        var tiendas = this.apartado === 'tiendas';
        var transportista = this.transportistas[this.apartado];
        var opciones = tiendas ?
            '<option value="xpo"' + (transportista === 'xpo' ? ' selected' : '') + '>XPO SAS</option><option value="gls"' + (transportista === 'gls' ? ' selected' : '') + '>GLS</option>' :
            '<option value="gls"' + (transportista === 'gls' ? ' selected' : '') + '>GLS</option><option value="seur"' + (transportista === 'seur' ? ' selected' : '') + '>SEUR</option>';
        return '<main><div class="ke-cab"><div><h1>Consulta de envíos</h1>' +
            '<p>Pedido, bultos y número de expedición, en pantalla o en Excel.</p></div>' +
            '<button type="button" class="btn btn-secondary ke-monitor">← Tornar al Monitor picking</button></div>' +
            '<nav class="ke-tabs"><button type="button" class="ke-tab' + (tiendas ? ' active' : '') + '" data-apartado="tiendas">Tendas</button>' +
            '<button type="button" class="ke-tab' + (!tiendas ? ' active' : '') + '" data-apartado="web">Web</button></nav>' +
            '<section class="ke-export"><div><h2>Descargar Excel de ' + (tiendas ? 'tendas' : 'pedidos web') + '</h2>' +
            '<p>' + (tiendas ? 'Tria XPO SAS o GLS.' : 'Tria GLS o SEUR.') + ' Pots descarregar un dia o un rang de dates.</p></div>' +
            '<div class="ke-export-camps"><label>Transportista<select class="ke-export-control ke-export-transport">' + opciones + '</select></label>' +
            '<label>Desde<input class="ke-export-control ke-export-desde" type="date" value="' + e(this.desde) + '"></label>' +
            '<label>Hasta<input class="ke-export-control ke-export-hasta" type="date" value="' + e(this.hasta) + '"></label>' +
            '<button class="btn btn-success ke-excel" type="button">Descargar Excel</button></div></section>' +
            '<form class="ke-form"><label for="ke-buscar">¿Qué quieres buscar?</label>' +
            '<div class="ke-search"><input id="ke-buscar" class="ke-buscar" type="search" autocomplete="off" ' +
            'placeholder="Pedido, OUT, tienda o nº de expedición" value="' + e(texto || '') + '">' +
            '<button class="btn btn-primary" type="submit">Buscar</button></div></form>';
    },

    _pintarInicio: function () {
        this.$el.html(this._cabecera('') +
            '<div class="ke-vacio"><b>Escribe cualquier dato que tengas.</b><span>Por ejemplo: el número de pedido, OUT/24181, K75 o el número de expedición.</span></div></main>');
    },

    _onMonitor: function (ev) {
        ev.preventDefault();
        this.do_action({
            type: 'ir.actions.client',
            name: 'Monitor picking',
            tag: 'koroshi_monitor',
            target: 'current',
        });
    },

    _onApartado: function (ev) {
        ev.preventDefault();
        this.apartado = ev.currentTarget.getAttribute('data-apartado') === 'web' ? 'web' : 'tiendas';
        this.resultados = [];
        this._pintarInicio();
        this.$('.ke-buscar').focus();
    },

    _onExportControl: function (ev) {
        var el = ev.currentTarget;
        if (el.classList.contains('ke-export-transport')) {
            this.transportistas[this.apartado] = el.value;
        } else if (el.classList.contains('ke-export-desde')) {
            this.desde = el.value || this._hoy();
        } else if (el.classList.contains('ke-export-hasta')) {
            this.hasta = el.value || this.desde;
        }
    },

    _onExcel: function (ev) {
        ev.preventDefault();
        this._onExportControl({currentTarget: this.$('.ke-export-transport')[0]});
        this.desde = this.$('.ke-export-desde').val() || this._hoy();
        this.hasta = this.$('.ke-export-hasta').val() || this.desde;
        if (this.desde > this.hasta) {
            this.do_warn('Fechas incorrectas', 'La fecha “Desde” no puede ser posterior a “Hasta”.');
            return;
        }
        window.location.href = '/koroshi_monitor/consulta_envios.xlsx?apartado=' + encodeURIComponent(this.apartado) +
            '&transportista=' + encodeURIComponent(this.transportistas[this.apartado]) +
            '&desde=' + encodeURIComponent(this.desde) + '&hasta=' + encodeURIComponent(this.hasta);
    },

    _onBuscar: function (ev) {
        ev.preventDefault();
        var texto = String(this.$('.ke-buscar').val() || '').trim();
        if (texto.length < 2) {
            this.do_warn('Falta información', 'Escribe al menos 2 caracteres.');
            return;
        }
        this._buscar(texto);
    },

    _buscar: function (texto) {
        var self = this;
        this.$el.html(this._cabecera(texto) + '<div class="ke-vacio"><b>Buscando…</b></div></main>');
        return this._rpc({route: '/koroshi_monitor/consulta_envios', params: {texto: texto, apartado: this.apartado}}).then(function (respuesta) {
            self.resultados = respuesta.resultados || [];
            self._pintar(respuesta);
        }).guardedCatch(function () {
            self.$el.html(self._cabecera(texto) +
                '<div class="ke-vacio ke-error"><b>No se ha podido consultar Odoo.</b><span>Prueba de nuevo en unos segundos.</span></div></main>');
        });
    },

    _resumen: function (pedido) {
        var lineas = [
            'Pedido: ' + (pedido.pedido || '—'),
            'Tienda: ' + (pedido.tienda || '—'),
            'Estado: ' + (pedido.estado || '—'),
            'Bultos Odoo: ' + numero(pedido.bultos),
            'Cajas preparadas: ' + numero(pedido.cajas),
        ];
        if (pedido.comprobable && !pedido.coincide) {
            lineas.push('ATENCIÓN: los bultos no coinciden');
        }
        lineas.push('Transportista: ' + (pedido.transportista || 'Sin asignar'));
        lineas.push(this._tituloExpedicion(pedido) + ': ' + ((pedido.expediciones || []).join(', ') || 'Sin expedición'));
        if (pedido.fecha) {
            lineas.push('Fecha: ' + pedido.fecha);
        }
        if ((pedido.outs || []).length > 1) {
            lineas.push('OUT: ' + pedido.outs.map(function (o) { return o.out; }).join(', '));
        }
        return lineas.join('\n');
    },

    _copiarTexto: function (texto) {
        var self = this;
        if (navigator.clipboard && navigator.clipboard.writeText) {
            return navigator.clipboard.writeText(texto).then(function () {
                self.do_notify('Resumen copiado', 'Ya puedes pegarlo en un correo, Teams o WhatsApp.');
            }).catch(function () {
                self._copiarAntiguo(texto);
            });
        }
        this._copiarAntiguo(texto);
    },

    _copiarAntiguo: function (texto) {
        var area = document.createElement('textarea');
        area.value = texto;
        area.setAttribute('readonly', 'readonly');
        area.style.position = 'fixed';
        area.style.opacity = '0';
        document.body.appendChild(area);
        area.select();
        document.execCommand('copy');
        document.body.removeChild(area);
        this.do_notify('Resumen copiado', 'Ya puedes pegarlo en un correo, Teams o WhatsApp.');
    },

    _pedidoBoton: function (ev) {
        var indice = parseInt(ev.currentTarget.getAttribute('data-indice'), 10);
        return this.resultados[indice];
    },

    _tituloExpedicion: function (pedido) {
        var transportista = String((pedido && pedido.transportista) || '').toUpperCase();
        if (transportista.indexOf('XPO') >= 0) { return 'Nº de expedición XPO'; }
        if (transportista.indexOf('GLS') >= 0) { return 'Nº de expedición GLS'; }
        return 'Nº de expedición / seguimiento';
    },

    _onCopiar: function (ev) {
        ev.preventDefault();
        var pedido = this._pedidoBoton(ev);
        if (pedido) {
            this._copiarTexto(this._resumen(pedido));
        }
    },

    _onCompartir: function (ev) {
        ev.preventDefault();
        var pedido = this._pedidoBoton(ev);
        if (!pedido) { return; }
        var texto = this._resumen(pedido);
        if (navigator.share) {
            var self = this;
            navigator.share({title: 'Pedido ' + pedido.pedido, text: texto}).catch(function (error) {
                if (!error || error.name !== 'AbortError') {
                    self._copiarTexto(texto);
                }
            });
        } else {
            this._copiarTexto(texto);
        }
    },

    _onOut: function (ev) {
        if (ev.ctrlKey || ev.metaKey || ev.shiftKey || ev.button === 1) { return; }
        ev.preventDefault();
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: 'stock.picking',
            res_id: parseInt(ev.currentTarget.getAttribute('data-id'), 10),
            views: [[false, 'form']],
            target: 'current',
        });
    },

    _pintar: function (respuesta) {
        var self = this;
        var pedidos = respuesta.resultados || [];
        var h = this._cabecera(respuesta.texto || '');
        if (!pedidos.length) {
            h += '<div class="ke-vacio"><b>No he encontrado ningún envío.</b><span>Revisa el número o prueba con la OUT, la tienda o la expedición XPO/GLS.</span></div></main>';
            this.$el.html(h);
            this.$('.ke-buscar').focus().select();
            return;
        }
        h += '<div class="ke-contador">' + pedidos.length + (pedidos.length === 1 ? ' pedido encontrado' : ' pedidos encontrados') +
            (respuesta.limitado ? ' · Hay más resultados: concreta un poco la búsqueda.' : '') + '</div>';
        pedidos.forEach(function (p, indice) {
            var clase = p.comprobable ? (p.coincide ? ' ke-ok' : ' ke-mal') : ' ke-pendiente';
            var comprobacion = p.comprobable ? (p.coincide ? 'Los bultos coinciden' : 'Los bultos NO coinciden') : 'Pendiente de comprobar';
            var expediciones = (p.expediciones || []).length ? p.expediciones.map(function (s) {
                return '<span class="ke-tracking">' + e(s) + '</span>';
            }).join(' ') : '<span class="ke-muted">Sin expedición</span>';
            h += '<section class="ke-pedido' + clase + '"><div class="ke-pedido-cab"><div><span class="ke-label">Pedido</span><h2>' + e(p.pedido) +
                '</h2><p>' + e(p.tienda) + '</p></div><div class="ke-acciones"><button class="btn btn-primary ke-copiar" data-indice="' + indice + '">Copiar resumen</button>' +
                '<button class="btn btn-secondary ke-compartir" data-indice="' + indice + '">Compartir</button></div></div>' +
                '<div class="ke-datos"><div><span>Estado</span><b>' + e(p.estado) + '</b><small>' + e(p.fecha) + '</small></div>' +
                '<div><span>Bultos Odoo</span><b>' + numero(p.bultos) + '</b></div><div><span>Cajas preparadas</span><b>' + numero(p.cajas) + '</b></div>' +
                '<div class="ke-cuadre"><span>Comprobación</span><b>' + e(comprobacion) + '</b></div></div>' +
                '<div class="ke-transporte"><div><span>Transportista</span><b>' + (p.transportista ? e(p.transportista) : '<span class="ke-muted">Sin asignar</span>') +
                '</b></div><div><span>' + e(self._tituloExpedicion(p)) + '</span><b>' + expediciones + '</b></div></div>';
            h += '<details><summary>Ver detalle de ' + p.outs.length + (p.outs.length === 1 ? ' OUT' : ' OUT') + '</summary><div class="ke-tabla"><table><thead><tr>' +
                '<th>OUT</th><th>Estado</th><th>Bultos Odoo</th><th>Cajas</th><th>Transportista</th><th>Nº expedición</th><th>Fecha</th></tr></thead><tbody>';
            (p.outs || []).forEach(function (o) {
                h += '<tr><td><a class="ke-out" data-id="' + o.id + '" href="/web#id=' + o.id + '&model=stock.picking&view_type=form&cids=8">' + e(o.out) + '</a></td>' +
                    '<td>' + e(o.estado) + '</td><td>' + numero(o.bultos) + '</td><td>' + numero(o.cajas) + '</td><td>' + e(o.transportista || '—') +
                    '</td><td class="ke-mono">' + e(o.expedicion || '—') + '</td><td>' + e(o.fecha || '—') + '</td></tr>';
            });
            h += '</tbody></table></div></details></section>';
        });
        h += '<p class="ke-nota">“Bultos Odoo” es lo declarado al transportista. “Cajas preparadas” son las matrículas CJ distintas que contienen unidades del pedido.</p></main>';
        this.$el.html(h);
        this.$('.ke-buscar').focus().select();
    },
});

core.action_registry.add('koroshi_consulta_envios', ConsultaEnvios);
return ConsultaEnvios;
});
