# Diseño: «Revisar caja» en la PDA (área Expediciones) — 25/11/2026, v2

Solo diseño. No hay código. Espera el visto bueno de Isaac.

Sustituye a la propuesta de `diseno-revisar-box-partir_2026-11-19.md` (v1, en Lecturas y solo con la OUT sin
validar). Isaac y el jefe de almacén han contestado el 25/11 a sus preguntas P1 y P2:

- **P1 (cuándo se dan cuenta):** en expediciones, con las OUT **ya validadas**, al montar el palet.
- **P2 (quién y dónde):** expediciones, desde la PDA, en el área Expediciones, junto a «Juntar cajas».

## El caso de hoy (K1 MAQUINISTA, S-6665004772)

- La zona D2 llenó dos cajas físicas, pero en Odoo las 23 uds quedaron en la CJ665013811.
- La segunda caja lleva pegada, muy probablemente, la CJ665013810, que no existe en Odoo: no se leyó en Lecturas.
- En la serie de D2 de hoy también falta la CJ665013804, entre K45 y K22.
- Resultado: 7 cajas físicas en el palet y 6 en Odoo. XPO y S4T recibirían 6 bultos.

## Qué pide el almacén

1. Leer la matrícula de una caja y **ver todo lo que hay dentro** según Odoo (sirve también de doble check: «¿esta
   caja tiene lo que dice Odoo?»).
2. Si dos cajas físicas comparten una CJ en Odoo: abrir la caja que **no tiene su CJ bien en Odoo**, leer **todas
   sus prendas**, leer **la CJ que lleva pegada** y pasar las prendas leídas a esa CJ. Lo no leído se queda en la
   CJ original.
3. Lo mismo sirve si se han mezclado prendas de dos pedidos (las prendas de otro pedido salen en rojo: ver abajo).

## Propuesta

### Dónde

En `koroshi_juntar_cajas` 1.1.0, con una segunda actividad en el área Expediciones: **«Revisar caja»**. Es la
pantalla gemela de «Juntar cajas»: mismo módulo, misma tarjeta, mismo registro para deshacer. No toca
`koroshi_preparacion` (Lecturas).

### Flujo en la PDA

1. Tarjeta del operario.
2. **Leer la CJ** que tiene las prendas en Odoo (en el ejemplo, CJ665013811). Sale la lista:
   `K1 MAQUINISTA · S-6665004772 · CJ665013811 · 23 uds` y cada artículo con sus uds (`3 · Pantalón X · 40`).
3. **Leer las prendas** de la caja que se va a separar. Cada lectura:
   - verde: está en esa CJ → «1 de 3» en su fila;
   - rojo: no está en esa CJ, o ya se han leído todas → no cuenta, pita;
   - «Deshacer la última».
4. Al acabar, dos botones:
   - **«Todo bien»**: no cambia nada. Solo apunta la revisión (doble check).
   - **«Pasar lo leído a otra CJ»** → leer la **CJ pegada** en esa caja (CJ665013810). Vale una CJ que no existe en
     Odoo (se crea) o una CJ vacía. Una CJ con prendas de **otro** pedido: error.
5. Resultado: «CJ665013811: 13 uds · CJ665013810: 10 uds · Bultos del pedido 6 → 7». Si el pedido ya tiene etiqueta
   del transportista, aviso en rojo: hay que hacer la etiqueta del bulto nuevo.

### Qué cambia en Odoo

- Sin campos nuevos en tablas compartidas. Se usan la CJ (`stock.quant.package`) y `result_package_id` de las
  líneas, como en «Juntar cajas».
- **Línea entera leída** (todas sus uds): solo se cambia su `result_package_id` a la CJ nueva. Es lo mismo que hace
  «Juntar cajas» y la acción 1844 v5: probado en 56 pedidos desde el 19/11.
- **Línea leída en parte** (por ejemplo, 2 de 3 uds del mismo artículo): se parte en dos líneas hechas. La original
  se queda con 1 ud en la CJ original y una línea nueva lleva las 2 uds a la CJ nueva. Odoo lo hace en tres pasos:
  devuelve 2 uds al hueco, las vuelve a sacar y las mete en la CJ nueva. **Esto no está probado en este Odoo**: es
  el riesgo de la versión (ver «Antes de instalar»).
- Cuánto pasa (leído en Odoo el 25/11): de las 4.813 líneas en CJ desde el 24/11, 812 (17 %) llevan más de 1 ud.
  En la CJ665013811 de la K1 las 23 líneas son de 1 ud: ese caso se arregla solo con líneas enteras.
- Bultos de las OUT del pedido: se recalculan con la misma regla que «Juntar cajas». Comprobación: suben exactamente
  en 1; si no, no se cambia nada.
- Nota en la OUT y en el pedido. Línea en el registro (quién, CJ origen, CJ nueva, uds, ids) para deshacer en la
  oficina.
- Todo o nada.

### Cuándo no deja (igual que «Juntar cajas»)

- Pedido **SHIPPED** en S4T, o alguna OUT en un **camión cerrado**: no deja.
- Pedido de **Zalando**: no deja.
- Pedido **READY** en S4T: S4T ya tiene las prendas con la CJ vieja. Propuesta: deja, pero avisa en rojo y deja una
  nota para volver a mandarlo con la acción 1960. Es la misma pregunta pendiente para «Juntar cajas».
- CJ con prendas de otro pedido o tienda como CJ nueva: no deja.

## Preguntas para Isaac

- **R1.** ¿Va bien en `koroshi_juntar_cajas` (Expediciones) y con el nombre «Revisar caja»?
- **R2.** Pedido READY en S4T: ¿avisar y dejar (propuesta) o bloquear? Vale para las dos pantallas.
- **R3.** ¿Se puede leer como CJ nueva una matrícula que no existe en Odoo (se crea)? Propuesta: sí, es el caso de
  hoy (la CJ665013810 pegada pero nunca leída).

## Antes de instalar

1. Tests sin Odoo de la lógica: qué líneas se mueven enteras, cuáles se parten, y que las uds y los bultos cuadran.
2. **Prueba de partir una línea hecha**, fuera de horas, con el sí de Isaac, en un pedido que no salga hoy (o en el
   K1 con la CJ665013810, si Isaac lo decide). Se comprueba que el stock del hueco no cambia y que las uds de la OUT
   siguen igual.
3. Si partir la línea no queda limpio, la 1.1.0 solo mueve líneas enteras. Para separar 2 de 3 uds del mismo
   artículo habría que avisar a la oficina.
4. Probar en una PDA: lector, prenda que no es de esa caja (rojo), CJ nueva que no existe, y doble toque.
