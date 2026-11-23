# Crear e imprimir lineales y contenedores (23/11/2026) — diseño v1

Lo pide Isaac (nota de voz 23/11): crear un lineal o un contenedor y sacar su etiqueta debe ser un solo botón, sin
exportar ni hacer nada dos veces. Lo usan Recepciones y Compactación. Fuera de alcance: etiquetas de pedidos y zonas
(Monitor de picking) y etiquetas de colores y precio.

## Cómo está hoy (leído en producción el 23/11, solo lectura)

**Contenedores** (`stock.location`, 75.849 KO_ y 2.184 TT_):
- Nombre `KO_ddmmaa_NNN`; el código de barras es el mismo nombre. El NNN vuelve a 001 cada día (KO_171126_001).
- Se crean en tandas (17/11: 100; 30/10: 700; 26/10: 295…), todos en el mismo segundo, con el usuario Almacén Nath.
- Nacen sueltos en `EFFEC/Stock/NAVE2` (hay 4.059 ahí) y la PDA (Contenedores) los mueve después a su hueco.
- TT_ es lo mismo con otro prefijo (última tanda 25/08/2026).

**Huecos de un lineal** (`stock.location`, 30.700 con nombre `NNNNN - Lxx Pyy Cz`):
- Nombre `21048 - L142 P00 C1`; código de barras `L142 P00 C1` (sin el número). Cuelgan de `EFFEC/Stock/NAVE2`.
- Se crearon por importación con Departament IT (24-25/08/2026: 11.828 de golpe).
- **2.510 huecos no tienen código de barras** (los de L180 del 25/08 y 510 del 21/05).
- El número de delante (21048) no es único: se repite en UBRAN y WH (copias viejas). Su significado está por confirmar.
- Los de muelle (`MU-04 P18 C1`, sin número) se crearon uno a uno a mano el 27/10 con Almacén Nath; código = nombre.

**Impresión**: en Odoo solo existe el informe estándar «Location Barcode» (A4, sin formato de etiqueta). Hay formato de
papel KOROSHI 4x6 (102 x 152) para la Zebra de las etiquetas de pedido.

## Propuesta

Módulo nuevo **koroshi_ubicaciones** («Crear e imprimir»). No toca koroshi_contenedores ni añade campos a tablas
compartidas: solo crea `stock.location` como se hace ahora, con un asistente (tabla propia transitoria) y un informe QWeb
propio (`koroshi_ubicaciones.etiqueta_ubicacion`).

Menú Inventario › KOROSHI › **Crear e imprimir** (jefes, Recepciones y Compactación). Tres botones:

1. **Contenedores**: cuántos (por defecto 100) y prefijo (KO_ o TT_). Crea `KO_<hoy>_<siguiente…>` en NAVE2 con
   código = nombre y abre el PDF con sus etiquetas. Nunca repite un nombre (busca el último NNN del día, también
   archivados).
2. **Lineal**: código (L181 o MU-05), de P a P, y alturas (C1 a C4). Enseña antes la lista que va a crear y para si
   alguno ya existe. Crea los huecos en NAVE2 con código de barras `L181 P00 C1` y abre el PDF.
3. **Volver a imprimir**: un lineal entero, un trozo (L94 P10-P20) o unos contenedores (KO_171126_001 a 050).

Etiqueta: código de barras Code128 grande con el texto debajo; para el hueco, el lineal en grande (L181) y P/C.

Aparte (no en esta versión): poner código de barras a los 2.510 huecos que no lo tienen, si Isaac quiere.

## Preguntas a Isaac

1. ¿Con qué impresora y tamaño de etiqueta imprimís hoy los huecos y los contenedores (Zebra 4x6, otra más pequeña,
   A4 de pegatinas)? ¿Qué exportáis y con qué programa?
2. El número de delante del hueco (21048): ¿qué es (orden de recorrido, correlativo) y hay que ponerlo en los lineales
   nuevos? Si no hace falta, los nuevos se llamarían como MU: `L181 P00 C1`.
3. ¿Desde el PC de Recepciones basta, o también desde la PDA?
