# odoo.tuctuc.com — mejoras de rendimiento: antes y después

**Informe del 24/11/2026.** Lo que se ha cambiado hoy en odoo.tuctuc.com para que vaya más rápido, cuánto tardaba
cada cosa antes y cuánto tarda ahora.

**Cómo se ha trabajado.** Se ha corregido el propio código de Odoo y de los módulos que ya estaban instalados. No se
han añadido módulos nuevos por encima.

Cada cambio se ha probado antes en la base de datos real, en modo prueba: se calcula, se compara y se deshace. La
prueba no escribe nada. Solo se ha instalado cuando el resultado salía **idéntico** al de antes.

Todo queda guardado:
- una versión con nombre y fecha, sin sobrescribir la anterior;
- una copia de seguridad en el servidor para volver atrás;
- el detalle técnico en el repositorio (`odoo/nucleo_tuctuc/README.md` y `TABLERO.md`).

## 1. Ya instalado

| Pantalla o acción | Qué se ha cambiado | Antes | Ahora | Resultado | Instalado |
|---|---|---|---|---|---|
| **Contabilidad › Modelo 349 › «Calcular»** (PRIME, marzo 2026, 177.206 líneas) | Módulo del 349, versión 1.2.2: calcula por bloques e índices en sus tablas | Más de 1 h 40 min sin acabar; el informe se quedaba a 0 | **~5 min por pasada.** Contabilidad lo calculó en 10 min 46 s, con un reintento automático explicado abajo | Idéntico (informe 202, 3.058 líneas: 19,1 s → 6,6 s) | 24/11, 14:00 |
| **Contabilidad › Modelo 347 › «Calcular»** (UNITED 2026) | Módulo del 347, versión 2.1.3: filtro de impuestos partido en dos consultas | 184 s (3 min) | **3,5 s** | Idéntico | 24/11, 14:00 |
| **Contabilidad › Modelo 347** (PRIME 2024, 1,68 millones de apuntes) | Igual que la fila anterior | No acababa | **41 s** | Idéntico | 24/11, 14:00 |
| **Inventario › Previsto** de un producto | El cálculo de la pantalla reescrito con la misma lógica | Más de 10 min sin acabar (en otro Odoo igual: 220 s) | **0,18 s** (producto 1318281, 2.676 líneas) | Mismas columnas y datos | 24/11, 15:27 |
| **Trazabilidad / movimientos de un producto** | Índice en los movimientos detallados (19 millones de filas) | ~1 s por consulta: recorría la tabla entera | **Milisegundos** | Idéntico (el índice no cambia resultados) | 24/11, 15:27 |
| **Botón «Stock» del producto** e **Inventario › Stock** | Ya no se ejecuta una tarea de limpieza en cada clic; la sigue haciendo el planificador de cada noche | +11,7 s en cada clic, y escribía en la tabla de stock | **11,7 s menos por clic** | Mismo stock en pantalla | 24/11, 15:27 |
| **Cualquier búsqueda en listas** (módulo «búsqueda con comas») | Ya no pregunta a la base de datos en cada búsqueda si el módulo está instalado | 200 búsquedas = 200 consultas de más | **0 consultas de más** | Mismos resultados | 24/11, 15:27 |

**El reintento del 349.** Al calcular un 349 muy grande puede coincidir que otro proceso toque a la vez una ficha que
el cálculo usa. Odoo entonces vuelve a empezar solo (hasta 5 veces), y por eso puede tardar el doble. Si el informe
queda a 0, se vuelve a pulsar «Calcular». Isaac ha decidido dejarlo así de momento.

## 2. Hecho y probado; entra con el reinicio de hoy a las 17:00

| Pantalla o acción | Qué se ha cambiado | Antes | Ahora | Resultado |
|---|---|---|---|---|
| **Buscar productos por stock** («Stock = 10», «< 0», «= 0», «≠ 0»…) | Se suma el stock directamente en la base de datos, en vez de calcular uno a uno los 306.743 productos. Los kits se siguen calculando como siempre | **10 a 19 minutos** por búsqueda; la pantalla se quedaba «pensando» | **20 a 28 segundos** | **Idéntico** en las 10 búsquedas probadas, comparadas con el stock real de los 306.743 productos («= 10»: 72 productos; «< 0»: 61) |

La búsqueda «Stock > 0» ya era rápida y no cambia. Ya tenía un fallo de antes, que se mantiene: no muestra 24 kits
(LK9000-*) que sí tienen stock por sus componentes.

## 3. En curso hoy: tres índices

Un índice es como el índice de un libro: la base de datos va directa a las filas que necesita en vez de leer la
tabla entera. Se crean sin bloquear a nadie (Odoo sigue trabajando). Además se ha preparado el código para que
ninguna actualización futura los borre.

| Dónde se nota | Tabla | Antes | Mejora esperada |
|---|---|---|---|
| Abrir y validar albaranes con **paquetes** | Niveles de paquete (684.683 filas) | Hasta 86 s en leer los paquetes de un albarán | Milisegundos |
| **Consumo de embalaje por paquete** (módulo de consumo de cajas) | Movimientos de stock (20,6 millones de filas) | 6 a 21 s por paquete | Milisegundos |
| Movimientos creados desde **compras** | Movimientos de stock (20,6 millones) | Recorría la tabla entera (hoy no hay ninguno, pero Odoo lo pregunta) | Inmediato |

*Estado a las 16:30 (hora de aquí): el primero espera a que acaben dos exportaciones de stock en marcha. Cuando
estén, se comprobará que la base de datos los usa.*

## 4. Pendiente: siguientes candidatos encontrados hoy

| Proceso | Cuánto tarda hoy | Qué se ve | Mejora estimada |
|---|---|---|---|
| **Exportar stock a la tienda externa** (Code22men, cola de trabajos) | 12 min de media, hasta 37 min; 86 ejecuciones | Ocupa la base de datos todo ese rato y retrasa a otros (hoy ha retrasado estos índices) | Alta: probablemente minutos → segundos, con la misma suma directa del punto 2 |
| **Lector de códigos de barras** (cargar ubicaciones) | 18 s cada vez | Hay 759.880 ubicaciones (730.337 con código de barras); hay que saber por qué tantas | Alta, pero antes hay que entender esas ubicaciones |
| **Conciliación bancaria** | Hasta 128 s y 3.129 consultas al abrir | Pantalla lenta para contabilidad | Por estudiar |
| **Validar un movimiento de ubicación** | 117 s | — | Por estudiar |
| **Búsquedas en pedidos de venta** | Recorren la tabla entera | — | Por estudiar (índices) |

Orden propuesto: exportación de stock, después el lector de códigos de barras (antes, preguntar por las ubicaciones),
y después el resto.

## 5. Para volver atrás

Cada cambio tiene su copia de seguridad en el servidor (`/opt/tuctuc-erp/copias_modulos/`), con el día y la hora. Se
copia el archivo antiguo y se reinicia. Los índices se pueden quitar sin afectar a ningún dato.

**Aviso para informática.** Tres archivos del Odoo base de tuctuc están cambiados. Si alguien actualiza esa carpeta
con git (`git pull`), se pierden y hay que volver a copiarlos desde el repositorio.
