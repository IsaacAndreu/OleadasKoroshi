# Pendientes de informática KOROSHI (Andrés / Efrén) — reunión del 18/11/2026

Para: Andrés, Efrén
CC: Sonia, Erika
Asunto: Resumen de la reunión del 18/11: lo que quedó pendiente por vuestra parte

---

Hola Andrés, Efrén:

Os pasamos lo que quedó pendiente por vuestra parte en la reunión de ayer, para tenerlo todo en un sitio. Si algo no
lo hemos entendido bien, decídnoslo.

## 1. Reasignaciones de pedidos (OMS → SGA) · urgente
- Cuando la web reasigna un pedido en el OMS, el pedido nuevo (sufijo -01, -02…) no nos llega por la API, o llega con
  las líneas sin cambiar (el ejemplo de Sonia: tres líneas donde deberían quedar dos).
- Visteis que la reasignación no pasa del OMS al SGA.
- **Plazo que se dijo:** un par de días.

## 2. Devoluciones
- **Web (B2C):** ya hacemos las devoluciones en la página buena del OMS, con el mismo usuario. Betty os confirma con una
  captura que el proceso entero queda registrado. Necesitamos que nos aparezcan las de los 2 palés que ya teníamos
  hechos (en la API solo salían 4).
- **Privalia / BP:** su devolución va por otro proceso y aún no está en el OMS. Queda pendiente unificarla.

## 3. Relación de bultos para XPO desde la API (Efrén)
- Informe con **5 columnas**: nº de expedición, nombre de tienda, total de bultos, volumen (m³) y peso (kg).
- Un botón que lo envíe directamente a la lista de XPO, con Erika e Isaac en copia.
- **Mientras no esté:** lo enviamos nosotros desde nuestro «Cerrar camión», con el asunto
  «PREVISIÓN XPO AMPOSTA dd/mm/aaaa» y un Excel con esas mismas columnas.

## 4. Quitar el estado «listo» (Efrén)
- Ya no hay envíos parciales. El único estado que importa es el cuadre: **expedido** frente a **validado sin expedir**
  (es lo que Erika necesita para la previsión de transporte).

## 5. Faltantes: KPI de faltante relativo (Efrén)
- En el panel de servido / no servido, una columna con el **faltante relativo por SKU**: faltante ÷ recepcionado, en %
  y con **dos decimales**.
- Ordenable, para revisar primero lo que pase del 10 %. La tolerancia la fija KOROSHI.
- **Cruce con el snapshot de stock de los viernes:** vuestro stock frente al nuestro, con la diferencia por SKU.

## 6. Correcciones de tiendas · nos interesa mucho
- Cuando una tienda detecta un error nuestro, lo corrige en vuestro sistema, pero la corrección no nos llega y nuestro
  stock se queda mal.
- Dijisteis que sería la siguiente pantalla. **Os pedimos que, además de la pantalla, nos llegue por la API**
  (endpoint o fichero diario): tienda, pedido o expedición, SKU, cantidad corregida, motivo y fecha. Así podemos
  regularizarlo de nuestro lado y revisar la causa (caja mal hecha, ubicación, lectura).

## 7. Volumen y peso por SKU en el packing list (Andrés)
- Dos campos más en el packing list de la API: **volumen y peso por SKU y talla**, sacados del packing list de origen.
  Llega unos 45 días antes que la mercancía.
- Ojo: el packing list del proveedor da el mismo volumen por unidad de la S a la XXXL, así que no sirve tal cual. Se
  quedó en pedir a los proveedores, como norma, el peso y el volumen de cada bulto.

## 8. Lo que queda para más adelante (sin fecha)
- Diseño del B2C web: Shopify + SendCloud, el TPV en remoto y que todo se haga desde una sola página del OMS.

---

Un saludo,
Isaac Andreu
Effective Logistics (NAU-2)
