# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Envios a S4T',
    'summary': 'Envia a S4T (POST /shipments) el transportista, tracking, bultos, peso y volumen de cada pedido',
    'description': """
Por cada pedido S-6665 ya READY en S4T, con todas las OUT hechas y con etiqueta, manda a S4T un envio por
cada tracking distinto (XPO o GLS): bultos = cajas distintas, peso = 15 kg x bultos y volumen = 0,09 m3 x
bultos (criterio con el que factura XPO; igual que koroshi_xpo_bultos v1.1).
El ultimo envio del pedido va con is_final=true y S4T pasa la orden a SHIPPED.

SE INSTALA DESACTIVADO:
- el cron "KOROSHI - Envios a S4T" queda archivado (inactivo);
- el parametro koroshi_s4t_envios.modo vale 'diagnostico': solo calcula y guarda los envios, sin llamar a S4T.
Para enviar de verdad hay que poner el modo a 'real' Y activar el cron (o usar "Enviar ahora").

Usa la configuracion (host y X-Api-Key) del modulo api_s4t_batch_update_PROD. No anade campos a tablas
existentes: guarda todo en su propio modelo koroshi.s4t.envio.
v1.0 (12/11/2026). v1.1 (12/11/2026): peso y volumen por bulto (15 kg y 0,09 m3), como XPO.
""",
    'version': '13.0.1.1.0',
    'author': 'NATH',
    'category': 'Inventory',
    'license': 'LGPL-3',
    'depends': ['api_s4t_batch_update_PROD', 'delivery', 'sale_stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/datos.xml',
        'views/envio_views.xml',
    ],
    'installable': True,
    'application': False,
}
