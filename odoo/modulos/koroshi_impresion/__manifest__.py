# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Impresión',
    'summary': 'Cola de impresión para las impresoras USB de los PC del almacén: la PDA apunta el PDF y el agente del '
               'PC lo imprime.',
    'description': """
Impresión en los PC del almacén (KOROSHI, Effective Logistics).
Diseño: bin/versiones/diseno-imprimir-desde-pda_2026-11-25_v4.md (visto bueno de Isaac el 25/11/2026).

Las impresoras (Zebra 4x6) van por cable a un PC, sin red propia: Odoo no puede imprimir en ellas. Este módulo es la
cola: una pantalla (la primera será «Transportista» en Expediciones, módulo koroshi_transportista) apunta un trabajo
para una impresora, y el agente de ese PC (bin/agente_impresion) pregunta cada pocos segundos, lo imprime en su
impresora y dice si ha ido bien.

- koroshi.impresora: las impresoras (código que usa el agente, p. ej. EXP1; último contacto = «conectada»).
- koroshi.impresion.trabajo: la cola. Un trabajo es un PDF: un adjunto ya hecho (etiqueta de GLS/XPO; el mismo PDF
  adjunto a varias OUT se imprime una sola vez) o un informe QWeb de unos registros. Estados pendiente, imprimiendo,
  impreso, error. Por orden de llegada.
- Métodos: encolar (pantallas); agente_siguientes, agente_pdf y agente_hecho (agente). Un trabajo «imprimiendo» más
  de 5 min vuelve a la cola; a los 3 intentos queda en error (botón «Reintentar»). Los impresos se borran a los 30 días.
- Menú: Inventario > Configuración > Impresión (PC del almacén).
No añade campos a tablas de Odoo.

v1.0.0 (25/11/2026): primera versión. Lógica en logica.py con tests sin Odoo. Crea la impresora EXP1 «Zebra
Expediciones» (portátil de Expediciones) y el cron de limpieza.
""",
    'version': '13.0.1.0.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'stock', 'koroshi_base'],
    'data': [
        'security/ir.model.access.csv',
        'views/impresion_views.xml',
        'data/datos.xml',
    ],
    'installable': True,
    'application': False,
}
