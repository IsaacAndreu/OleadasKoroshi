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
        'submit .ke-extra-form': '_onAnadir',
        'click .ke-extra-quitar': '_onQuitar',
        'click .ke-cierre-ver': '_onCierreVer',          // v1.29.0
        'click .ke-cierre-enviar': '_onCierreEnviar',    // v1.29.0
    },

    init: function () {
        this._super.apply(this, arguments);
        this.resultados = [];
        this.apartado = 'tiendas';
        this.transportistas = {tiendas: 'xpo', web: 'gls'};
        this.desde = this._hoy();
        this.hasta = this.desde;
        this.extras = [];
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
            self._cargarExtras();
        });
    },

    getTitle: function () {
        return 'Consulta de envíos';
    },

    _cabecera: function (texto) {
        var tiendas = this.apartado === 'tiendas';
        var transportista = this.transportistas[this.apartado];
        var opciones = tiendas ?
            '<option value="xpo"' + (transportista === 'xpo' ? ' selected' : '') + '>XPO SAS</option><option value="gls"' + (transportista === 'gls' ? ' selected' : '') + '>GLS</option>' +
            '<option value="todos"' + (transportista === 'todos' ? ' selected' : '') + '>Todos (con y sin transportista)</option>' :
            '<option value="gls"' + (transportista === 'gls' ? ' selected' : '') + '>GLS</option><option value="seur"' + (transportista === 'seur' ? ' selected' : '') + '>SEUR</option>';
        return '<main><div class="ke-cab"><div><h1>Consulta de envíos</h1>' +
            '<p>Pedido, bultos y número de expedición, en pantalla o en Excel.</p></div>' +
            '<button type="button" class="btn btn-secondary ke-monitor">← Volver al Monitor picking</button></div>' +
            '<nav class="ke-tabs"><button type="button" class="ke-tab' + (tiendas ? ' active' : '') + '" data-apartado="tiendas">Tiendas</button>' +
            '<button type="button" class="ke-tab' + (!tiendas ? ' active' : '') + '" data-apartado="web">Web</button></nav>' +
            '<section class="ke-export"><div><h2>Descargar Excel de ' + (tiendas ? 'tiendas' : 'pedidos web') + '</h2>' +
            '<p>' + (tiendas ? 'XPO SAS o GLS: pedidos con la etiqueta del transportista creada en esas fechas. Todos: pedidos validados en esas fechas, con y sin transportista.' : 'Elige GLS o SEUR.') + ' Puedes descargar un día o un rango de fechas.</p></div>' +
            '<div class="ke-export-camps"><label>Transportista<select class="ke-export-control ke-export-transport">' + opciones + '</select></label>' +
            '<label>Desde<input class="ke-export-control ke-export-desde" type="date" value="' + e(this.desde) + '"></label>' +
            '<label>Hasta<input class="ke-export-control ke-export-hasta" type="date" value="' + e(this.hasta) + '"></label>' +
            '<button class="btn btn-success ke-excel" type="button">Descargar Excel</button></div></section>' +
            (tiendas ? this._htmlCierre() : '') +
            '<section class="ke-extra"><form class="ke-extra-form"><div><h2>Añadir un pedido u OUT al Excel de un día</h2>' +
            '<p>Si al Excel le falta algo (por ejemplo, de un día anterior), escríbelo aquí y saldrá junto al resto de ese día.</p></div>' +
            '<div class="ke-export-camps"><label>Pedido u OUT<input class="ke-extra-texto" type="text" autocomplete="off" placeholder="' +
            (tiendas ? 'S-6665004126 u OUT/24601' : 'W-… u OUT/…') + '"></label>' +
            '<label>Día<input class="ke-extra-dia" type="date" value="' + e(this.desde) + '"></label>' +
            '<button class="btn btn-primary ke-extra-anadir" type="submit">Añadir</button></div></form>' +
            '<div class="ke-extra-lista">' + this._htmlExtras() + '</div></section>' +
            '<form class="ke-form"><label for="ke-buscar">¿Qué quieres buscar?</label>' +
            '<div class="ke-search"><input id="ke-buscar" class="ke-buscar" type="search" autocomplete="off" ' +
            'placeholder="Pedido, OUT, tienda o nº de expedición" value="' + e(texto || '') + '">' +
            '<button class="btn btn-primary" type="submit">Buscar</button></div></form>';
    },

    // v1.29.0: cerrar el camión XPO del día y mandar el manifiesto por correo (solo si se pulsa).
    _htmlCierre: function () {
        return '<section class="ke-cierre"><div class="ke-cierre-cab"><div><h2>Cerrar camión XPO y enviar manifiesto</h2>' +
            '<p>Al acabar de cargar: manda a XPO el Excel XPO del día, con copia a Koroshi y a oficina. Primero revisa el resumen.</p></div>' +
            '<div class="ke-export-camps"><label>Día<input class="ke-cierre-dia" type="date" value="' + e(this.desde) + '"></label>' +
            '<button class="btn btn-secondary ke-cierre-ver" type="button">Ver resumen</button></div></div>' +
            '<div class="ke-cierre-resumen"></div></section>';
    },

    _htmlResumenCierre: function (r) {
        var h = '<div class="ke-cierre-datos"><div><span>Tiendas</span><b>' + numero(r.tiendas) + '</b></div>' +
            '<div><span>Pedidos</span><b>' + numero(r.pedidos) + '</b></div>' +
            '<div><span>Bultos</span><b>' + numero(r.bultos) + '</b></div>' +
            '<div><span>Cajas preparadas</span><b>' + numero(r.cajas) + '</b></div></div>';
        if ((r.diferencias || []).length) {
            h += '<div class="ke-cierre-dif"><b>Diferencias sin resolver (' + r.diferencias.length + '):</b><ul>' +
                r.diferencias.map(function (d) { return '<li>' + e(d) + '</li>'; }).join('') +
                '</ul><small>Salen también en el correo. Si se pueden arreglar antes, mejor.</small></div>';
        } else if (r.outs) {
            h += '<div class="ke-cierre-ok">Los bultos cuadran con las cajas en todas las tiendas.</div>';
        }
        h += '<p class="ke-cierre-para"><b>Para:</b> ' + e((r.para || []).join(', ') || '— (falta el parámetro koroshi_monitor.manifiesto_para)') +
            '<br/><b>CC:</b> ' + e((r.cc || []).join(', ') || '—') + '</p>';
        if (r.cierre) {
            h += '<div class="ke-cierre-hecho">Camión ya cerrado: enviado ' + e(r.cierre.cuando) + ' por ' + e(r.cierre.usuario) +
                (r.cierre.envios > 1 ? ' (' + r.cierre.envios + ' veces)' : '') + ', ' + numero(r.cierre.bultos) + ' bultos.</div>' +
                '<button class="btn btn-outline-danger ke-cierre-enviar" type="button" data-reenviar="1">Reenviar manifiesto corregido</button>';
        } else if (!r.outs) {
            h += '<div class="ke-cierre-dif">Ese día no hay ninguna OUT de tienda con etiqueta XPO.</div>';
        } else {
            h += '<button class="btn btn-danger ke-cierre-enviar" type="button">Cerrar camión y enviar manifiesto</button>';
        }
        return h;
    },

    _onCierreVer: function (ev) {
        if (ev) { ev.preventDefault(); }
        var self = this;
        var dia = this.$('.ke-cierre-dia').val() || this._hoy();
        this.$('.ke-cierre-resumen').html('<p class="ke-muted">Calculando…</p>');
        return this._rpc({route: '/koroshi_monitor/cierre/resumen', params: {dia: dia}}).then(function (r) {
            self.cierre = r;
            self.$('.ke-cierre-resumen').html(self._htmlResumenCierre(r));
        }).guardedCatch(function () {
            self.$('.ke-cierre-resumen').html('<div class="ke-cierre-dif">No se ha podido consultar Odoo.</div>');
        });
    },

    _onCierreEnviar: function (ev) {
        ev.preventDefault();
        var self = this;
        var r = this.cierre;
        if (!r) { return; }
        var reenviar = ev.currentTarget.getAttribute('data-reenviar') === '1';
        var pregunta = (reenviar ? '¿Mandar OTRA VEZ el manifiesto del ' : '¿Cerrar el camión y mandar el manifiesto del ') + r.dia_texto +
            ' a ' + (r.para || []).join(', ') + '?\n\n' + r.tiendas + ' tiendas, ' + r.pedidos + ' pedidos, ' + r.bultos + ' bultos.' +
            ((r.diferencias || []).length ? '\nCon ' + r.diferencias.length + ' diferencias sin resolver.' : '');
        if (!window.confirm(pregunta)) { return; }
        this.$('.ke-cierre-enviar').prop('disabled', true);
        return this._rpc({route: '/koroshi_monitor/cierre/enviar', params: {dia: r.dia, reenviar: reenviar}}).then(function (res) {
            if (res.error) {
                self.do_warn('No se ha enviado', res.error);
                self.$('.ke-cierre-enviar').prop('disabled', false);
                return;
            }
            self.do_notify('Manifiesto enviado', res.mensaje);
            return self._onCierreVer();
        }).guardedCatch(function () {
            self.$('.ke-cierre-enviar').prop('disabled', false);
        });
    },

    _htmlExtras: function () {
        var extras = this.extras || [];
        var rango = this.desde === this.hasta ? 'el ' + this._fechaCorta(this.desde) :
            'del ' + this._fechaCorta(this.desde) + ' al ' + this._fechaCorta(this.hasta);
        if (!extras.length) {
            return '<p class="ke-extra-vacio">No hay nada añadido a mano ' + e(rango) + '.</p>';
        }
        var h = '<p class="ke-extra-titulo">Añadido a mano ' + e(rango) + ' (' + extras.length + ')</p>' +
            '<div class="ke-tabla"><table><thead><tr><th>Día</th><th>Pedido</th><th>OUT</th><th>Excel</th>' +
            '<th>Estado</th><th>Nº expedición</th><th>Añadido por</th><th></th></tr></thead><tbody>';
        extras.forEach(function (x) {
            h += '<tr><td>' + e(x.dia) + '</td><td>' + e(x.pedido || '—') + '</td>' +
                '<td><a class="ke-out" data-id="' + x.out_id + '" href="/web#id=' + x.out_id + '&model=stock.picking&view_type=form&cids=8">' + e(x.out) + '</a></td>' +
                '<td>' + e(x.transportista) + '</td><td>' + e(x.estado) + '</td><td class="ke-mono">' + e(x.expedicion || '—') + '</td>' +
                '<td>' + e(x.usuario) + '<small> ' + e(x.cuando) + '</small></td>' +
                '<td><button type="button" class="btn btn-sm btn-outline-danger ke-extra-quitar" data-id="' + x.id + '">Quitar</button></td></tr>';
        });
        return h + '</tbody></table></div>';
    },

    _fechaCorta: function (iso) {
        var partes = String(iso || '').split('-');
        return partes.length === 3 ? partes[2] + '/' + partes[1] + '/' + partes[0] : iso;
    },

    _pintarExtras: function () {
        this.$('.ke-extra-lista').html(this._htmlExtras());
    },

    _cargarExtras: function () {
        var self = this;
        return this._rpc({route: '/koroshi_monitor/envios_extra/lista', params: {
            apartado: this.apartado, desde: this.desde, hasta: this.hasta,
        }}).then(function (respuesta) {
            self.extras = respuesta.extras || [];
            self._pintarExtras();
        });
    },

    _onAnadir: function (ev) {
        ev.preventDefault();
        var self = this;
        var texto = String(this.$('.ke-extra-texto').val() || '').trim();
        var dia = this.$('.ke-extra-dia').val();
        if (texto.length < 3) {
            this.do_warn('Falta información', 'Escribe el pedido o la OUT.');
            return;
        }
        if (!dia) {
            this.do_warn('Falta información', 'Elige el día.');
            return;
        }
        // La lista de abajo enseña el día al que se añade.
        this.desde = dia;
        this.hasta = dia;
        this.$('.ke-export-desde').val(dia);
        this.$('.ke-export-hasta').val(dia);
        this.$('.ke-extra-anadir').prop('disabled', true);
        return this._rpc({route: '/koroshi_monitor/envios_extra/anadir', params: {
            apartado: this.apartado, transportista: this.transportistas[this.apartado],
            texto: texto, dia: dia, desde: dia, hasta: dia,
        }}).then(function (respuesta) {
            self.$('.ke-extra-anadir').prop('disabled', false);
            if (respuesta.error) {
                self.do_warn('No se ha añadido', respuesta.error);
                return;
            }
            self.extras = respuesta.extras || [];
            self._pintarExtras();
            self.$('.ke-extra-texto').val('').focus();
            if ((respuesta.nuevas || []).length) {
                self.do_notify('Añadido al ' + self._fechaCorta(dia), 'OUT: ' + respuesta.nuevas.join(', '));
            }
            if ((respuesta.repetidas || []).length) {
                self.do_warn('Ya estaba añadido', 'OUT: ' + respuesta.repetidas.join(', '));
            }
        }).guardedCatch(function () {
            self.$('.ke-extra-anadir').prop('disabled', false);
        });
    },

    _onQuitar: function (ev) {
        ev.preventDefault();
        var self = this;
        var id = parseInt(ev.currentTarget.getAttribute('data-id'), 10);
        var fila = _.findWhere(this.extras || [], {id: id});
        if (!fila || !window.confirm('¿Quitar ' + fila.out + ' del Excel del ' + fila.dia + '? (la OUT no se toca)')) {
            return;
        }
        return this._rpc({route: '/koroshi_monitor/envios_extra/quitar', params: {
            extra_id: id, apartado: this.apartado, desde: this.desde, hasta: this.hasta,
        }}).then(function (respuesta) {
            self.extras = respuesta.extras || [];
            self._pintarExtras();
        });
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
        this.extras = [];
        this._pintarInicio();
        this.$('.ke-buscar').focus();
        this._cargarExtras();
    },

    _onExportControl: function (ev) {
        var el = ev.currentTarget;
        if (el.classList.contains('ke-export-transport')) {
            this.transportistas[this.apartado] = el.value;
        } else if (el.classList.contains('ke-export-desde')) {
            this.desde = el.value || this._hoy();
            if (!this.hasta || this.hasta < this.desde) {
                this.hasta = this.desde;
                this.$('.ke-export-hasta').val(this.hasta);
            }
            this.$('.ke-extra-dia').val(this.desde);
            this._cargarExtras();
        } else if (el.classList.contains('ke-export-hasta')) {
            this.hasta = el.value || this.desde;
            this._cargarExtras();
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
