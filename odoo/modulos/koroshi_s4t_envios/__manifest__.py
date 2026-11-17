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
v1.2.0 (14/11/2026): auditoria 13/11, fase 3. Una OUT pendiente ya no para el pedido (se mandan las hechas; is_final
cuando no queda ninguna). Errores reintentables (408, 409, 429, 5xx, red) separados de los definitivos ('rechazado',
con aviso en el pedido y por correo a koroshi_s4t_envios.avisar). Respuesta 200 con lista protegida. El cron ya no se
llena de atascados y va por turnos. Bultos con koroshi_xpo_bultos (depende de el). Sigue en modo diagnostico.
v1.3.0 (17/11/2026): camion XPO y correccion de bultos (spec intent/carga-camion-bultos/spec_2026-11-17.md). Con
koroshi_monitor 1.29 (cierre del camion y manifiesto), los trackings XPO van sin is_final hasta que su OUT esta en un
cierre: el pedido pasa a SHIPPED cuando el camion ha salido. Si los bultos de un envio ya mandado cambian antes del
cierre, queda en «Bultos cambiados» y se corrige con el boton «Reenviar» (nunca solo); despues, solo una nota en el
pedido. GLS como antes. Sin koroshi_monitor 1.29, como la v1.2. Campos nuevos solo en koroshi.s4t.envio. Sigue en
modo diagnostico.
""",
    'version': '13.0.1.3.0',
    'author': 'NATH',
    'category': 'Inventory',
    'license': 'LGPL-3',
    'depends': ['api_s4t_batch_update_PROD', 'delivery', 'sale_stock', 'koroshi_xpo_bultos'],
    'data': [
        'security/ir.model.access.csv',
        'data/datos.xml',
        'views/envio_views.xml',
    ],
    'installable': True,
    'application': False,
}
