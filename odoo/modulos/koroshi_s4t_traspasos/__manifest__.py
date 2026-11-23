# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Traspasos S4T (devoluciones y correcciones)',
    'summary': 'Descarga de S4T las devoluciones e-commerce y las correcciones de traspasos y las guarda en Odoo',
    'description': """
Lee de la API B2B de S4T (solo GET):
- /transfers/return-ecommerce: devoluciones de la tienda online a 6665 (DevoEcom).
- /transfers/corrections: correcciones de los traspasos de reposicion diaria de 6665 a las tiendas (+/-).

Cada traspaso se GUARDA primero en Odoo (con su JSON tal cual) y despues se procesa. Asi no se pierde nada aunque
S4T lo marque como descargado la primera vez que lo devuelve.
- Devolucion: crea una recepcion DEV de 6665 (Clientes -> DEVOLUCIO_KOROSHI) lista para validar (no la valida).
- Correccion: solo se registra (tienda, articulos, +/-). No mueve stock hasta saber con S4T que significa.

SE INSTALA CON EL CRON ARCHIVADO. Primera descarga: "Ejecutar manualmente" el cron y revisar.
Usa host y X-Api-Key de s4t.config (api_s4t_batch_update_PROD). No anade campos a tablas existentes.
v1.0 (12/11/2026).
v1.1.0 (14/11/2026): auditoria 13/11, fase 3. Cada traspaso en su savepoint, guardando antes el JSON crudo (uno
raro ya no hace perder la pagina). Conciliacion diaria de hoy y ayer por fecha (koroshi_s4t_traspasos.
hora_conciliacion, 06:00). Los que dan error se reintentan hasta 5 veces. «Recuperar por fecha» ya no usa
display_notification (no existe en Odoo 13). Sigue sin instalar y con el cron archivado.
v1.2.0 (16/11/2026): auditoria 13/11, fase 6 (pasar a koroshi_base). Empresa y hora del almacen salen de
koroshi_base.comun. Mismo resultado; sin campos ni vistas nuevas. Depende de koroshi_base.
v1.3.0 (19/11/2026): puesta en marcha para dar entrada a las devoluciones web. Parametro koroshi_s4t_traspasos.modo:
'guardar' al instalar (descarga y guarda todo lo pendiente desde el 01/07 sin crear DEV, para revisarlo) y 'real'
(DEV automatica de cada devolucion e-commerce). Boton 'Sin DEV' para las que no deben crear recepcion. 'Recuperar por
fecha' ya no procesa todos los nuevos: solo los que acaba de guardar y solo en modo real. Sin campos en tablas
compartidas (solo un estado nuevo en el modelo propio).
v1.4.0 (23/11/2026): revision general del 23/11 (R12). Al procesar se vuelve a buscar el articulo de las lineas que
no lo tenian (antes, crear el articulo en Odoo no arreglaba la correccion en error: el producto calculado no se
recalculaba) y los que agotaron los intentos por eso vuelven a probarse cuando el articulo ya esta. Una vez al dia
(desde la hora de conciliacion), correo a koroshi_s4t_traspasos.avisar con los traspasos en error (antes, tras 5
intentos, silencio). No cambia que se crea.
""",
    'version': '13.0.1.4.0',
    'author': 'NATH',
    'category': 'Inventory',
    'license': 'LGPL-3',
    'depends': ['api_s4t_batch_update_PROD', 'stock', 'koroshi_base'],
    'data': [
        'security/ir.model.access.csv',
        'data/datos.xml',
        'views/traspaso_views.xml',
        'wizard/recuperar_views.xml',
    ],
    'installable': True,
    'application': False,
}
