# Pregunta a S4T: contenido esperado de las matrículas de tienda (inversa KOROSHI)

**Asunto:** Contenido esperado por matrícula de caja (devoluciones de tienda KOROSHI)

Hola,

En Effective (NAU-2) vamos a empezar a trabajar la inversa de KOROSHI: las cajas que devuelven las tiendas, con
matrícula CJ + 9 cifras (por ejemplo CJ080000717). Ya leemos cada matrícula y os la enviamos con
`POST /box-number/register`. Ahora necesitamos saber **qué lleva cada caja antes de abrirla**, para repartirla por
familias.

Hoy solo lo vemos de forma indirecta: `POST /matriculas/verify` nos devuelve la `cantidadEsperada` por SKU, pero
antes tenemos que enviaros lo que hemos contado. Nosotros necesitamos el dato antes de contar.

Os pedimos:

1. **Un endpoint de consulta del contenido esperado por matrícula**, sin enviar recuento. Por ejemplo
   `GET /matriculas/{matricula}`, que devuelva:
   - matrícula, tienda de origen y fecha de envío;
   - líneas: SKU (por ejemplo `2521JA10-000061-S`), EAN si lo tenéis y cantidad.
2. Si es posible, también **un listado de las matrículas pendientes de recibir**, para ver el volumen antes de que
   llegue el camión. Por ejemplo `GET /matriculas?estado=pendiente&desde=AAAA-MM-DD`, con su contenido o con el
   total de uds.
3. ¿Qué devuelve la API si la matrícula aún no tiene contenido cargado? ¿Un 404?
4. Sobre `POST /matriculas/verify`: nuestras llamadas devuelven el error *Field required: body.almacen*. ¿Qué valor
   tenemos que enviar en `almacen` para KOROSHI?
5. ¿Ese endpoint de verificación tiene que usarse sí o sí cuando contamos una caja, o es opcional?

Con el punto 1 nos basta para empezar. Las pruebas en el almacén empiezan el lunes 16/11. Hasta tener el dato,
contaremos las cajas sin el contenido.

Gracias,
Isaac Andreu – Effective Logistics
