# -*- coding: utf-8 -*-
from . import models
from .models.stock_picking import actualizar_delegacion


def rellenar_delegaciones(cr, registry):
    """Al instalar: rellena la delegacion de todos los albaranes que ya hay, con SQL."""
    actualizar_delegacion(cr)
