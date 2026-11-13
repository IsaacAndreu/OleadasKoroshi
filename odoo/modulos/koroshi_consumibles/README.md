# KOROSHI Consumibles (v1.3.0, 13/11/2026)

## v1.3.0: aviso por correo (13/11/2026)

- Campo **«Avisar por correo a»** en cada consumible (correos separados por comas). Llega un correo cuando el stock baja
  al **mínimo de aviso** y otro cuando se **agota**. Vale también para las cajas que resta la PDA al cerrar una caja.
- Sin correos puestos, no se avisa (como antes). Hay que poner el mínimo y los correos en cada caja.

## v1.2.1

- Campo «Se elige en Lecturas»: solo esas cajas salen en la PDA. La Online queda sin marcar, porque lo online se
  prepara por INT (al SORTER) y sus OUT no llevan caja. La 1.2.0 no se instaló.

## v1.2.0: cajas para la PDA

- En el artículo, «Es una caja (se elige en la PDA)», el nombre corto para el botón, el orden y las medidas en mm.
- Cada caja tiene su «Tipo de paquete» de Odoo (`product.packaging`), que se crea y se actualiza solo con el nombre
  y las medidas en cm. Es el tipo que se pone a la caja (`stock.quant.package.packaging_id`) al cerrarla.
- Al instalar se dejan las cajas de KOROSHI: Grande 590x390x400 (la que ya estaba), 600x400x400, Mediana (sin
  medidas: las pone Betty) y Online 280x280x120.
- En Lecturas (koroshi_preparacion 3.24) el operario elige el tipo al cerrar la caja y se resta 1 con un consumo que
  lleva la OUT, la caja y el operario. Si no hay stock, el consumo de la PDA se apunta igual y el artículo queda
  «Agotado», para que Betty corrija el total; el cierre de la caja nunca se para por esto.

Módulo sencillo para controlar cajas y materiales que todavía no están dados
de alta como productos del inventario de Odoo.

## Uso

1. Abrir **Inventario → Consumibles KOROSHI → Totales iniciales**.
2. Crear cada artículo y poner el total que conoce Betty en **Total conocido por Betty**.
3. Usar **Registrar consumo** para apuntar lo gastado cada día.
4. Consultar el stock actual y el historial de movimientos.

El cálculo es:

```text
stock actual = total inicial + entradas - consumos + correcciones
```

El módulo no modifica productos, existencias, albaranes ni reservas de Odoo.
Cada movimiento conserva fecha, usuario, cantidad y observaciones. Las
correcciones pueden ser positivas o negativas y los consumos no permiten
registrar más unidades de las disponibles.
Los movimientos no se pueden borrar; para corregir un apunte se registra una
corrección positiva o negativa.
