# -*- coding: utf-8 -*-
# custom_addons/multi_search_with_comma/models/multi_search.py:13-59 sustituye BaseModel._where_calc (TODAS las
# busquedas de TODOS los modelos) y en cada llamada lanza:
#     SELECT id FROM ir_module_module WHERE name='multi_search_with_comma' and state='installed' limit 1
# (linea 30). Visto en pg_stat_activity el 23/11/2026. Es una consulta mas por cada search(), tambien dentro de los
# bucles que hacen miles de busquedas.
#
# Aqui se vuelve a poner la MISMA funcion, letra por letra, con un unico cambio: saber si el modulo esta instalado
# mirando el registro ya cargado (registry._init_modules) en vez de preguntarlo a la base de datos. Este modulo
# depende de multi_search_with_comma, asi que se importa despues y su asignacion es la que queda.
# No se corrige nada mas (ni el '|' de mas ni 'active' en vez de _active_name) para no cambiar resultados.
from odoo.osv import expression
from odoo.osv.query import Query
from odoo.models import BaseModel, api

MODULO = 'multi_search_with_comma'


@api.model
def _where_calc(self, domain, active_test=True):
    if 'active' in self._fields and active_test and self._context.get('active_test', True):
        if not any(item[0] == 'active' for item in domain):
            domain = [('active', '=', 1)] + domain
    # Antes: self.env.cr.execute("SELECT id FROM ir_module_module WHERE name='multi_search_with_comma' ...")
    is_multi_search_installed = MODULO in self.env.registry._init_modules
    if domain:
        modified_domain = []
        for domain_tuple in domain:

            if not is_multi_search_installed:
                modified_domain.append(domain_tuple)
                continue
            if type(domain_tuple) in (list, tuple):
                if str(domain_tuple[1]) == 'ilike':
                    multi_name = domain_tuple[2].split(',')
                    len_name = len(multi_name)
                    if len_name > 1:
                        for length in multi_name:
                            modified_domain.append('|')
                        for f_name in multi_name:
                            modified_domain.append([domain_tuple[0], domain_tuple[1], f_name.strip()])
            modified_domain.append(domain_tuple)
        e = expression.expression(modified_domain, self)
        tables = e.get_tables()
        where_clause, where_params = e.to_sql()
        where_clause = [where_clause] if where_clause else []
    else:
        where_clause, where_params, tables = [], [], ['"%s"' % self._table]

    return Query(tables, where_clause, where_params)


BaseModel._where_calc = _where_calc
