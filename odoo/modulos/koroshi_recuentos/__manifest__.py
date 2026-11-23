# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Recuentos (comprobar el inventario por referencia)',
    'summary': 'PDA: una referencia con todas sus tallas y colores, dónde está y cuánto dice Odoo, y su recuento '
               'leído a ciegas con registro de cada lectura (inventario dinámico).',
    'description': """
Comprobar el inventario por referencia en la PDA (KOROSHI, Effective Logistics).
Diseño: bin/versiones/diseno-comprobar-inventario_2026-11-20_v3.md (aprobado por Isaac el 20/11/2026).

Fase 1 (1.0), solo lectura: pantalla «Referencia» (app «Referencia» e Inventario > KOROSHI Operarios > Recuentos).

- Se lee una prenda (EAN) o se escribe la referencia (2621XC04) o una variante. Un trozo (2621XC) da la lista.
- Tabla color x talla con lo que dice Odoo (reservado entre paréntesis, negativo en rojo).
- Los sitios (hueco y contenedor KO_/TT_) en orden de recorrido, con lo que dice Odoo de cada variante.
- En naranja, los sitios donde se quitó stock de la referencia a pérdidas en los últimos 90 días, aunque Odoo ya
  diga 0 («Odoo 0: mirar»): es donde puede estar lo que falta.
- Tocar un sitio enseña todo lo que Odoo dice que hay en él.

Fase 2 (1.1), el recuento leído, que solo apunta (NO toca el stock):

- «Contar esta referencia», con la tarjeta de operario (la misma que en Lecturas, Contenedores y Faltante).
- Caja a caja: leer la caja o el hueco, leer CADA prenda y «Caja hecha». No hay «Cantidad»: solo vale lo leído.
- A ciegas: la PDA no enseña lo que dice Odoo. Si no cuadra, pide leer la caja otra vez. Dos lecturas iguales =
  diferencia confirmada; tres distintas = para el jefe.
- Lo que dice Odoo se coge al cerrar cada caja, menos lo ya leído en OUT sin validar. Si se mueve stock de la caja
  mientras se cuenta, esa vuelta se descarta y se lee otra vez.
- Si se ve la referencia en otro sitio, se lee ese sitio y se añade («encontrada fuera de lista»).
- Registro de todo: cada lectura (koroshi.recuento.lectura), con quién, cuándo, caja y vuelta. Nada se borra ni se
  edita: «Quitar la última» deja la lectura anulada. En Odoo: Recuentos hechos y Lecturas de los recuentos, solo
  para mirar.
- «Terminar» enseña el resultado por talla y color: Odoo, leído y diferencia.

Fase 3 (sin hacer): aplicar sola la diferencia confirmada (traslado o ajuste REC/...), acta en Excel.

Tablas propias (koroshi.recuento, .caja, .linea, .lectura). No añade campos a tablas de Odoo.

v1.0.0 (20/11/2026): primera versión, fase 1: pantalla «Referencia» de solo lectura (lo pide Isaac el 20/11:
cuando KOROSHI dice «la prenda X no está», ver de una vez todas sus tallas, colores y sitios, y dónde se quitó a
mano).

v1.1.0 (20/11/2026): fase 2, el recuento leído a ciegas, con segunda y tercera lectura si no cuadra y registro de
cada lectura. Solo apunta: todavía no cambia el stock. Además, buscar la referencia es más rápido (por la plantilla
y sin pasar por las traducciones: de 1 s a 0,4 s en producción) y la descripción se reescribe sin sangrías
para que no dé el aviso «Unexpected indentation» al actualizar la lista de aplicaciones. Las variantes de la
referencia se guardan al empezar el recuento (no se buscan en cada lectura).
v1.2.0 (23/11/2026): revisión general del 23/11 (O4, O5, R16). Necesita koroshi_base 1.2.1 (instalarla antes). La
tarjeta compartida y el lector salen de koroshi_base (comun.js): el campo ahora también lee cuando el lector para
150 ms, como Contenedores (las PDA no mandan Intro y la lectura podía quedarse escrita); con «⌨ Escribir» espera al
Intro. En las rutas, el permiso, la tarjeta y la búsqueda de la prenda salen de koroshi_base.pda: la tarjeta tiene que
ser de un operario activo de la compañía; la búsqueda es la misma que antes. Sin campos nuevos.
""",
    'version': '13.0.1.2.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'stock', 'hr', 'barcodes', 'koroshi_base', 'koroshi_operarios'],
    'data': [
        'security/ir.model.access.csv',
        'data/secuencia.xml',
        'views/assets.xml',
        'views/views.xml',
        'views/recuento_views.xml',
        'views/menu.xml',
    ],
    'qweb': ['static/src/xml/referencia.xml'],
    'installable': True,
    'application': False,
}
