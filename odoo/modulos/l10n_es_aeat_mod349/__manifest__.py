# Copyright 2004-2011 - Pexego Sistemas Informáticos. (http://pexego.es)
# Copyright 2013 - Top Consultant (http://www.topconsultant.es/)
# Copyright 2016 - Tecnativa - Angel Moya <odoo@tecnativa.com>
# Copyright 2017 - Tecnativa - Luis M. Ontalba <luis.martinez@tecnativa.com>
# Copyright 2017 Eficent Business & IT Consult. Services <contact@eficent.com>
# Copyright 2014-2020 Tecnativa - Pedro M. Baeza
# Copyright 2018 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Modelo 349 AEAT",
    "version": "13.0.1.2.2",
    # Copia propia de tuctuc a partir de la 13.0.1.2.0 de la OCA instalada en el servidor (commit be55499).
    # Si se vuelve a copiar encima la versión de la OCA, se pierde este arreglo.
    "description": """
Historial de tuctuc:

v1.2.2 (24/11/2026): índices en report_id, move_line_id, refund_line_id y refund_id de los detalles
y registros del 349. Sin ellos, abrir un 349, recalcularlo o buscar la factura de cada rectificativa
recorría entera la tabla de detalles (2 M filas, 108.183 lecturas completas desde el 02/09/2026).
Un índice no cambia ningún resultado.

v1.2.1 (24/11/2026): «Calcular» crea los detalles en bloques de 1.000 en vez de uno a uno, une cada
detalle a su cliente con un solo write por grupo y deja de crecer recordsets con += en bucle. Con
180.218 líneas intracomunitarias (PRIME COLLECTIONS, marzo 2026) el cálculo original tardaba horas.
Mismo resultado: mismas líneas, en el mismo orden, mismos importes y mismos registros por cliente.
""",
    "author": "Tecnativa, Eficent, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "Localisation/Accounting",
    "website": "https://github.com/OCA/l10n-spain",
    "depends": ["l10n_es_aeat", "l10n_es"],
    "data": [
        "data/aeat_349_map_data.xml",
        "data/aeat_export_mod349_partner_refund_data.xml",
        "data/aeat_export_mod349_partner_data.xml",
        "data/aeat_export_mod349_data.xml",
        "views/account_move_view.xml",
        "views/account_tax_view.xml",
        "views/aeat_349_map_view.xml",
        "views/mod349_view.xml",
        "report/common_templates.xml",
        "report/aeat_mod349.xml",
        "report/report_views.xml",
        "security/ir.model.access.csv",
        "security/mod_349_security.xml",
    ],
    "development_status": "Mature",
    "maintainers": ["pedrobaeza"],
    "installable": True,
}
