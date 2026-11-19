# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Zonas',
    'summary': 'Partir los pedidos de tienda por zonas de picking buscando el maximo de cajas cerradas',
    'description': """
Sustituira a la accion de servidor 1883 "KOROSHI Partir OUT zonas v12 REAL" (v12f), que lanza el cron 202.
Objetivo: el maximo % de cajas cerradas (cajas que salen llenas a la tienda sin juntar restos de varias zonas).

El calculo (carpeta motor/) es Python puro, sin Odoo, y tiene tests (carpeta tests/, se lanzan sin Odoo:
python -m unittest discover -s tests -t .).

Fase 1 - Medir (no toca el reparto de la 1883):
- Inventario > KOROSHI Zonas > Ejecuciones: una por prefijo de agrupaciones (Z-ddmm- o Z-ddmm-R2-), con las
  cajas previstas (CAJAS n de la nota), las estimadas con lo cogido y las reales (matriculas).
- Caja cerrada real: matricula no compartida con otra OUT y que llega al 80 % de 80 L con lo que lleva
  dentro. Una caja compartida (koroshi_caja_existente) nunca es cerrada; cuenta una vez, para su OUT duena
  (parametro koroshi_zonas.regla_dueno: primera_linea, como el Monitor, o mas_uds).
- Cada hora registra las OUT de las agrupaciones Z- de hoy (para leer el CAJAS n antes de que se pise la
  nota) y cada noche mide los ultimos 7 dias. Menu "Medir desde el 22/10" para el historico.
- La ficha diaria de koroshi_kpi muestra el % real de cajas cerradas de las zonas.

Fase 2 - La v12f dentro del modulo (motor/v12f.py, copia literal de la accion 1883):
- Un solo codigo con el modo como campo: DIAGNOSTICO (no escribe), SIMULAR (parte dentro de un savepoint
  y lo deshace) y REAL (todo o nada: si falla una comprobacion se deshace). prueba_ids y
  prueba_agrupacion fuerzan DIAGNOSTICO, como en la accion.
- Menus "Diagnostico de hoy" y "Simular hoy"; en la lista de albaranes, Accion > "KOROSHI Zonas:
  diagnostico de las OUT seleccionadas" (como la 1881 con prueba_ids).
- Cada ejecucion guarda contexto, parametros, informe y los datos de entrada (JSON) para reproducirla.
- El informe se publica en el canal "KOROSHI Partir OUT zonas" (el de la 1881), si existe.
- El cron 202 y las acciones 1880-1883 NO se tocan todavia (fase 3).

Solo escribe fuera de sus tablas al partir en SIMULAR (deshecho) y REAL: lo mismo que la accion 1883
(partir movimientos, crear agrupaciones, nota). Nunca cancela una OUT ni fuerza disponibilidad.

Fase 3 - Configuracion y sustitucion:
- Inventario > KOROSHI Zonas > Configuracion: personas, horario, minimos, litros por caja (un solo valor),
  tiendas de 48 h, canal y destinatarios del correo. Valores iniciales = los de la v12f.
- Litros por tipo de prenda: una sola tabla, la de koroshi_kpi, con los valores de la v12f (decision del 11/11).
- Cron "partir OUT" a las 03:50 UTC. Modo sombra (por defecto): calcula sin partir y a las 04:30 compara con lo
  que ha partido el cron 202. Modo real: parte (si el cron 202 sigue activo, no hace nada y avisa).
- Etiquetas de zona (antes la 1843) con las cajas del reparto, y correo del dia (antes la 1868, desactivado).
- "Diagnostico sin guardar" de las OUT seleccionadas: calcula, lo ensena y no deja nada.
- Las acciones 1880-1883, 1843 y 1868 no se tocan.

v1.5.0 (19/11/2026): acabar a la hora y preparar el paso a real (bin/versiones/zonas-diagnostico-y-mejoras_2026-11-19.md).
  Ensayo: en modo sombra, el calculo que se compara con el cron 202 es un SIMULAR (parte dentro de un savepoint, pasa
  las comprobaciones y lo deshace), no un DIAGNOSTICO: el camino que parte no se habia ejecutado nunca con OUT de
  verdad. La comparacion de las 04:30 dice si el ensayo ha ido bien. Al SIMULAR, las OUT nuevas se llaman
  '<OUT>-SIM-<zona>' y no gastan numeros de la secuencia EFFEC/OUT/ (no vuelve atras al deshacer: dejaria huecos).
  Aviso: el informe y el correo del dia dicen a que hora se acaba con las personas de la configuracion y, si es
  despues de la hora de fin, cuantas personas harian falta por zona. Solo texto: el reparto no cambia.
  Previsto contra real: cada noche, con las lecturas de la PDA (koroshi_preparacion, si esta), primera lectura,
  95 % y ultima por zona, personas que han leido y desvio de la zona mas larga contra lo previsto.
  Campos nuevos solo en koroshi.zonas.ejecucion (tabla propia).
v1.4.0 (14/11/2026): auditoria 13/11, fase 6. Primer modulo con koroshi_base: COMPANY_ID, la hora del almacen,
  hoy y el rango de dias en UTC salen de koroshi_base.comun (antes, copiados aqui). Mismo comportamiento.
  Nueva dependencia: koroshi_base (instalarlo antes).
v1.3.0 (14/11/2026): auditoria 13/11, fase 5. Tres cosas que la 1883 no hacia, cada una con su ajuste:
  OUT de dias anteriores: tambien se reparten las OUT abiertas de hasta 7 dias antes (dias_atras; antes, las
  que no se partian el dia que entraban ya no se partian nunca); las que estan en la cola de un operario no se
  tocan. Si no cabe todo (sin 'Todo en una ronda'), entran primero las de dias anteriores y las tiendas de 48 h
  (orden_urgencia; antes, por numero de tienda y las de numero alto siempre se quedaban fuera). Con 'Todo en una
  ronda', el informe y el correo avisan si se acaba despues de la hora de fin. En modo sombra se calcula como la
  1883 (para comparar con el cron 202) y, ademas, un diagnostico con lo nuevo.
v1.2.0 (11/11/2026): fase 3, configuracion, cron en sombra, etiquetas y correo dentro del modulo.
v1.1.2 (11/11/2026): las agrupaciones que almacen crea a mano para imprimir lo del transportista ('Z-2210-SALIO
  22-10', 'Z-2710- SALE 28-10'...) ya no cuentan como zonas: cada OUT suya va al dia y la zona de su nota. Al
  actualizar se borran las filas con esas zonas y se vuelve a registrar (despues: Medir desde el 22/10).
v1.1.1 (11/11/2026): el nombre de la ejecucion y el dia, la compania, la diferencia y la causa de cada OUT
  se escriben al crear y al escribir (antes eran calculados guardados y el primer cron, justo al instalar, los
  dejo vacios). Al actualizar se rellenan los que estaban vacios.
v1.1 (11/11/2026): fase 2, la v12f dentro del modulo, igual que la 1883 en los tests sin Odoo.
v1.0 (11/11/2026): fase 1, medir las cajas reales.
""",
    'version': '13.0.1.5.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['mail', 'stock', 'stock_picking_batch', 'koroshi_kpi', 'koroshi_base'],
    'data': [
        'security/ir.model.access.csv',
        'data/parametros.xml',
        'data/cron.xml',
        'data/rellenar.xml',
        'data/config.xml',
        'views/ejecucion_views.xml',
        'views/config_views.xml',
        'views/kpi_dia_views.xml',
    ],
    'installable': True,
    'application': False,
}
