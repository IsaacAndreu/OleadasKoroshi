# Prueba: koroshi_preparacion v3.1.0 + operarios v2.3.1, preparar la OUT dentro de Lecturas (10/11/2026)

Subir a `/home/it_nath_group`:
- `20261110_koroshi_operarios_v2.3.1.zip`
- `20261110_koroshi_preparacion_v3.1.zip`
- `instalar_koroshi_preparacion_v3.1_2026-11-10.sh`

Pasos:
1. `bash instalar_koroshi_preparacion_v3.1_2026-11-10.sh check`, y después `sudo AUTO_CONFIRM=1 bash … install`, fuera de horas.
2. Aplicaciones > Actualizar lista.
   - *KOROSHI Operarios* > **Actualizar**.
   - *KOROSHI Preparación en Lecturas* > **Instalar** (o **Actualizar** si ya estaba una v3.0.x).
3. Ctrl+F5 en el PC y en las PDA.

La pantalla nueva solo la usan **Isaac (OP9990001)** e **Isaac2 (OP9980001)**. El resto de operarios sigue igual que hoy.

## 1. Abrir

- [ ] Lecturas > leer OP9990001. Su primera OUT **suelta** se abre en la pantalla nueva:
  - arriba: OUT, tienda e Isaac;
  - en grande: «Ve a» con la ubicación, la referencia y el producto.
- [ ] Si su primera OUT está en un lote **Z-**, se abre la app de siempre. Es lo esperado en la v3.0.
- [ ] Una tarjeta que no está en la lista (otro operario) abre la app de siempre.

## 1a. Aspecto (v3.1)

- [ ] El nombre del producto sale una vez y en grande, con la **talla** en un recuadro negro (L, 44, 10…).
- [ ] Producto sin foto: no sale el icono gris de Odoo. Con foto (la mayoría): sale la foto.
- [ ] Con 0 leídas no sale «Todo en caja». Después: «Sin caja: N» en amarillo o «✓ Todo en caja».
- [ ] Barra de progreso gruesa con «N de M uds» dentro. El nombre del operario no se parte.
- [ ] Aviso al leer, corto: «2511TR12-000002-XL · 1 de 1».

## 1b. Foto y flechas (v3.0.1)

- [ ] Sale la **foto** del producto, la misma que en la app. Si un producto no tiene foto, no queda ningún hueco.
- [ ] Al completar una línea (por ejemplo 3/3) salta sola a la siguiente.
- [ ] **◀** enseña la línea de antes («Ya cogida», en verde) y **▶** la siguiente. «Ir a la que toca ▸» vuelve.
- [ ] Tocar una línea en «Ver líneas» la pone en grande.
- [ ] No hace falta tocar el campo para leer: abajo pone siempre «Lector preparado» (gris solo sin conexión).
- [ ] En Lecturas no sale nada de productividad: ni «Hoy: N pedidos · N uds» ni los minutos del pedido.

## 2. Leer

- [ ] Leer el EAN que pide: pitido, aviso verde «REF 1 de 1» y la barra de progreso avanza.
- [ ] Leer un EAN de otra OUT: aviso **rojo** «no es de este pedido» y no cuenta.
- [ ] Leer otra vez una línea completa: aviso rojo «Ya tienes todas las uds…».
- [ ] Leer una etiqueta CJ sin pulsar Caja: «Es una caja: pulsa Caja antes de leerla».
- [ ] **Deshacer**: quita la última lectura (−1).
- [ ] Leer muy rápido varios productos seguidos: cuentan todos.

## 3. Caja

- [ ] Pulsar **Caja**: sale «Escanea la caja · N uds van a esta caja».
- [ ] Leer la CJ: aviso verde «Caja CJ… cerrada con N uds» y «Todo en caja».
- [ ] Repetirlo con una segunda caja en la misma OUT.
- [ ] En Odoo, la OUT tiene las líneas en sus cajas CJ, como si se hubiera hecho con la app.

## 4. Validar (solo con una OUT de prueba, o con OK)

- [ ] Con todo leído y en caja, **Validar** se pone en verde y grande.
- [ ] Validar: pantalla «✓ … validada», vuelta a Lecturas con «¡Hecho!» y se abre la siguiente.
- [ ] En Odoo, la OUT queda **Hecho**, con sus bultos, la etiqueta y XPO como siempre. Compararlo con una OUT hecha con la app.
- [ ] Con algo sin leer: «Quedan N líneas…». Hay que usar **Faltante**.

## 5. Faltante y volver

- [ ] Pulsar **Faltante**: se abre la pantalla de faltantes con esa OUT. «Volver a la OUT» vuelve a la pantalla nueva, **no** a la app.
- [ ] Validar desde Faltante: vuelta a Lecturas con «¡Hecho!».
- [ ] **←** sin validar: Lecturas con Continuar / Faltante / Saltar. Continuar vuelve a la pantalla nueva.

## 6. Mirar los registros

- *KOROSHI Operarios > Lecturas de preparación*: cada lectura con quién, OUT, código, resultado y errores en rojo.

## Vuelta atrás

- Rápida: *Parámetros del sistema* > `koroshi_preparacion.activa` = `0`. Lecturas vuelve a abrir la app de siempre, sin reiniciar.
- Completa: desinstalar *KOROSHI Preparación en Lecturas*.
- Para añadir operarios: `koroshi_preparacion.empleados`, con los códigos separados por comas. `*` activa a todos.
