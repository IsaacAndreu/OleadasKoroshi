# -*- coding: utf-8 -*-
# TUCTUC Lecturas PDA como app: a qué usuarios se les ofrece instalar la app (clon de koroshi_pda_app).
# Parámetro tuctuc_pda_app.usuarios: ids de usuario separados por comas ('*' = todos). Al instalar está VACÍO (a nadie):
# se pone a mano el id del usuario con el que se prueba y, después, el de las PDA de Oriola.
import re

from odoo import models

PARAM_USUARIOS = 'tuctuc_pda_app.usuarios'


class ResUsers(models.Model):
    _inherit = 'res.users'

    def tuctuc_pda_app_activa(self):
        """True si a este usuario se le pone el manifiesto de la app (y el service worker en Android)."""
        if not self or len(self) != 1 or self._is_public():
            return False
        valor = self.env['ir.config_parameter'].sudo().get_param(PARAM_USUARIOS, '') or ''
        lista = [x.strip() for x in re.split(r'[,;\s]+', valor) if x.strip()]
        return '*' in lista or str(self.id) in lista
