# Copyright 2004-2011 Pexego Sistemas Informáticos. (http://pexego.es)
# Copyright 2012 NaN·Tic  (http://www.nan-tic.com)
# Copyright 2013 Acysos (http://www.acysos.com)
# Copyright 2013 Joaquín Pedrosa Gutierrez (http://gutierrezweb.es)
# Copyright 2016 Tecnativa - Antonio Espinosa
# Copyright 2016 Tecnativa - Angel Moya <odoo@tecnativa.com>
# Copyright 2018 PESOL - Angel Moya <info@pesol.es>
# Copyright 2014-2022 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "AEAT modelo 347",
    "version": "13.0.2.1.3",
    # Copia propia de tuctuc a partir de la 13.0.2.1.2 de la OCA instalada en el servidor (commit 6272a35).
    # Si se vuelve a copiar encima la versión de la OCA, se pierde este arreglo.
    "description": """
Historial de tuctuc:

v2.1.3 (24/11/2026): «Calcular» del 347 de 2024 de PRIME COLLECTIONS (1,68 M apuntes) no acababa. Tres causas:
1) por cada cliente sacaba todos los clientes (726.000) y asientos (838.000) para quitar los «No incluir en
el 347»: ahora se quitan los 48 asientos marcados y los clientes se filtran solo entre los que salen;
2) el filtro «tax_ids en T O tax_line_id en T» recorría todos los apuntes del año (14 min una sola consulta):
ahora son dos consultas que no se solapan (0,3 s y 4,2 s medidas con EXPLAIN ANALYZE);
3) una consulta por cliente: ahora dos por clave, agrupadas por cliente y asiento. Mismo resultado.
""",
    "author": "Tecnativa,PESOL,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-spain",
    "category": "Accounting",
    "license": "AGPL-3",
    "depends": [
        "account_tax_balance",
        "base_vat",
        "l10n_es",
        "l10n_es_aeat",
        "portal",
    ],
    "data": [
        "data/aeat_export_mod347_partner_data.xml",
        "data/aeat_export_mod347_real_state_data.xml",
        "data/aeat_export_mod347_data.xml",
        "data/tax_code_map_mod347_data.xml",
        "security/ir.model.access.csv",
        "security/mod_347_security.xml",
        "views/account_move_view.xml",
        "views/res_partner_view.xml",
        "views/mod347_view.xml",
        "views/report_347_partner.xml",
        "views/mod347_templates.xml",
        "data/mail_template_data.xml",
    ],
    "installable": True,
    "images": ["images/l10n_es_aeat_mod347.png"],
}
