# KOROSHI Consumibles

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
