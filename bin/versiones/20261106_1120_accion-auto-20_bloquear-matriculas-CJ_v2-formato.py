# KOROSHI - BLOQUEAR MATRICULAS CJ DUPLICADAS O MAL LEIDAS          v2 06/11/2026
# Accion automatica 20 (base.automation), modelo stock.quant.package,
# disparador "Al crear y actualizar", campo disparador: name.
#
# v1 (30/10): impide crear o renombrar un paquete con una matricula CJ ya usada.
# v2 (06/11): ademas, toda caja con "CJ" en el nombre tiene que ser exactamente
#     CJ + 9 numeros (p.ej. CJ665007365). Bloquea las matriculas mal leidas:
#       - leida dos veces seguidas: CJ665007365CJ665007365 (S4T rechazo el
#         pedido S-6665003781 con "KO: None" del 04/11 al 06/11)
#       - tabulador o espacio delante: "\tCJ665005000"
#       - numero de mas o de menos: CJ6650075733, CJ66007998
#       - texto pegado: CJ665006045-K43-1510, NoCJ665003608
#     Medido el 06/11: 21.090 de 21.105 cajas CJ ya cumplen el formato.
#     Los paquetes que no llevan "CJ" (PACK..., EFFEC/OUT/...) no se tocan.
#     Con el campo disparador = name, solo salta al crear o al cambiar el nombre:
#     las 15 cajas antiguas mal leidas no bloquean nada mientras no se renombren.
#
# Reglas safe_eval: sin import, sin f-strings, log() antes de raise.

DIGITOS = '0123456789'

for paquete in records:
    nombre = paquete.name or ''
    normalizado = nombre.strip().upper()
    if 'CJ' not in nombre.upper():
        continue

    # --- v2: formato CJ + 9 numeros, sin espacios ni nada mas ---
    bien = (len(nombre) == 11 and nombre[:2] == 'CJ')
    if bien:
        for c in nombre[2:]:
            if c not in DIGITOS:
                bien = False
    if not bien:
        visible = nombre.replace('\t', '[TAB]').replace(' ', '[ESPACIO]')
        log('KOROSHI BLOQUEO CJ MAL LEIDA: "%s"' % visible)
        raise Warning(
            'Matricula mal leida: %s\n\n'
            'Tiene que ser CJ y 9 numeros (ejemplo: CJ665007365), sin nada mas.\n'
            'Puede que se haya leido dos veces. Borra el campo y vuelve a leer la etiqueta.\n\n'
            'No se ha creado ni modificado ninguna caja.' % visible
        )

    # --- v1: matricula repetida ---
    candidatos = env['stock.quant.package'].search([
        ('id', '!=', paquete.id),
        ('name', 'ilike', normalizado),
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
