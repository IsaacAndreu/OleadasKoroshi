# COPIA del codigo en produccion el 06/11/2026 11:20 (accion automatica 20, server action 1873,
# creada 30/10/2026 07:28 UTC). Disparador: on_create_or_write, sin campos disparadores, sin dominio.
# Para volver atras: pegar este codigo y quitar el campo disparador "name".

# KOROSHI - BLOQUEAR MATRICULAS CJ DUPLICADAS
# Impide crear o renombrar un paquete con una matricula CJ ya utilizada.
# Si el usuario intenta editar una caja cerrada y Odoo intenta crear otra CJ,
# la operacion se revierte y la caja original no se toca.

for paquete in records:
    nombre = (paquete.name or '').strip()
    normalizado = nombre.upper()
    if not nombre or not normalizado.startswith('CJ') or len(normalizado) <= 2:
        continue

    candidatos = env['stock.quant.package'].search([
        ('id', '!=', paquete.id),
        ('name', 'ilike', nombre),
    ])
    repetidos = candidatos.filtered(
        lambda p: (p.name or '').strip().upper() == normalizado
    )
    if repetidos:
        log('KOROSHI BLOQUEO CJ DUPLICADA: %s ya existe en paquete(s) %s' % (
            nombre, ', '.join(repetidos.mapped('display_name')[:3])
        ))
        raise Warning(
            'No se ha podido guardar el paquete.\n\n'
            'La matricula %s ya existe en otro paquete. '
            'No se ha creado ni modificado ninguna caja.\n\n'
            'Para anadir la prenda, usa la accion "Anadir unidades a caja existente".'
            % nombre
        )
