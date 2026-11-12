# Registro: diagnóstico de envíos a S4T v1 (12/11/2026)

Acción de servidor **1934**, «KOROSHI - Diagnostico envios S4T (shipments) v1 12/11 - NO ENVIA» (modelo `sale.order`).
Código: `bin/KOROSHI_envios_s4t_shipments_2026-11-12_v1_DIAGNOSTICO.py`. Se lanzó una vez por RPC con la empresa 8.
No ha enviado nada a S4T ni ha escrito nada en pedidos ni en OUT.

## Resultado

- Se han mirado 200 pedidos desde el 01/11, del S-6665003715 al S-6665003840. Ha llegado al límite de 200.
- **Ninguno está listo para enviar**: 194 tienen problemas, 3 tienen alguna OUT sin etiqueta y 3 no tienen OUT.
- El problema es **siempre el peso**: todos dan `peso 0`. Ningún pedido sale con 0 cajas.
- Dos pedidos (S-6665003757 y S-6665003805) tienen el tracking XPO 121771034 en una OUT **sin transportista**.
- Las expediciones XPO se repiten en varios pedidos de la misma tienda (p. ej. 121771038 en S-…3716 y S-…3765), como se esperaba.
- Un pedido puede tener dos trackings XPO: S-6665003840 tiene 121771082 en OUT/23105 y 121771062 en OUT/23105-O.

## Por qué el peso es 0

- Las OUT tienen `weight = 0` y `shipping_weight = 0`.
- **Ningún producto tiene peso**: 0 de 265.549 con `weight > 0`.
- Los productos sí tienen volumen: unos 0,0055 m3 por prenda.
- Transportistas: GLS (`gls_asm`, ids 42 y 43), XPO ES (`xpo_es`, id 173), MRW Portugal y RECOGE CLIENTE.

## Pendiente

Decidir de dónde sale `weight_kg`, que S4T exige mayor que 0. Opciones:
- un peso fijo por caja,
- un peso por prenda multiplicado por las unidades,
- el mismo peso que mandan los módulos de XPO y GLS al generar la etiqueta (habría que mirarlo en su código).
