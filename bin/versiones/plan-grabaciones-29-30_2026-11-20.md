# Plan de lo pedido en las grabaciones 29 y 30 — 20/11/2026

Fuentes: `C:\Users\tuctuc\Videos\Nueva grabación 29_1402.txt` y `Nueva grabación 30_8821.txt` (almacén, 20/11).
Quién lo pide: Isaac con el responsable del almacén, Cruz (manipulaciones) y Betty (facturación).
Regla general dicha en las dos: **quitar todos los Excel** del almacén. Lo primero: los de devoluciones y faltantes.

| # | Qué piden | Chat | Estado |
|---|---|---|---|
| 1 | Devoluciones: «Ubicar devoluciones» sin Excel. El operario elige qué ha hecho y lee prenda → contenedor. Informe por día, semana y mes para facturar | **Nuevo**: Devoluciones | Por diseñar. Prioritario («es ràpid i li traiem de damunt») |
| 2 | Devoluciones: el proceso entero (llega el paquete → qué lleva → manipular → ubicar) | **Nuevo**: Devoluciones (el mismo) | Diseño por fases, después del 1 |
| 3 | Una sola entrada en la PDA por áreas, con el tiempo de cada área, y «Gestión» solo para jefes | **Nuevo**: PDA, entrada única por áreas | Diseño. La tarjeta compartida ya está (operarios 2.22.1, 20/11) |
| 4 | Cierre automático de la sesión por turno (no a las 17:00 para todos) y descansos | Cerrar sesión a los 15 min | Mensaje enviado |
| 5 | Picking: dar trabajo por zonas o agrupaciones, no por pedidos. Botón para elegir cada día zonas o normal, con estimación. Coger la siguiente por unidades y prioridad de tienda | Zonas + Tablero | Mensajes enviados |
| 6 | Tablero: lo que se ve del tablero | Tablero | Mensaje enviado (con el 5) |
| 7 | KOROSHI quiere saber cuándo **empezamos** cada pedido, no solo cuándo acabamos. Idea: una pestaña para que ellos vean el monitor, cajas y prendas | Integración APIs traspasos y envíos | Mensaje enviado |
| 8 | Stock de cajas de cartón: Betty da unas 3.000 de 60x40x40 y se descuentan al elegir la caja | Este chat (Soporte 20/11) | Ya existe en koroshi_consumibles (resta al cerrar caja en la PDA). Falta dar la entrada de las 3.000 cajas: necesita el sí de Isaac |
| 9 | Stock: ajustes manuales «Cantidad de producto actualizada» | Este chat | Ya analizado el 20/11 (Excel de stock). Pendiente: bloquear ajustes a mano de Almacén Nath |

## 1 y 2. Devoluciones (lo que se dijo)

**Ubicar devoluciones (primero).**
- Hay tres opciones de manipulación para el operario, en palabras normales (no M1/M2/M3):
  - **Quitar precio**;
  - **Quitar precio y embolsar**;
  - **Reetiquetar y embolsar**.
- Se facturan por separado (Cruz y Betty). M1/M2/M3 solo para el informe.
- Hoy cada tipo va a un cajón y se ubica con un Excel. Lo nuevo: el operario entra en «Ubicar devoluciones», elige la opción y lee prenda, prenda… y el contenedor. Queda guardado quién, cuándo y qué.
- Informe: cuántas de cada opción por día, semana o mes, para facturar.
- Desalarmar: se juntan las chapas y se piden alarmas. No hace falta en la PDA de momento.

**El proceso entero (por fases).**
1. **Llega el paquete.** Se lee la matrícula (tiendas), el código de Zalando o el del transportista (GLS…) y queda «ha llegado hoy». Se tiene que poder buscar: «lo de GLS del día 28 lo tienes aquí».
2. **Qué lleva.** Se lee lo que hay dentro contra lo que dice el cliente. Tres casos: está bien / está mal (tara) / no ha llegado. Si no nos pasan qué lleva, lo leemos nosotros y se lo mandamos.
3. **Al leer, se marca** si hay que manipular y cuál de las tres opciones (o tara). Lo que está bien va directo a su puesto.
4. **Manipular por días.** Cada zona del palé es un día (p. ej. «box 20/11 V2C», o por matrícula para tiendas). Se puede pedir «hazme el de ayer», ya se sabe cuántas prendas hay y se puede calcular el tiempo. Prioridad si alguien lo pide.
5. **Ubicar** (lo del punto 1).

Hoy hay gente consultando la API a mano en un taburete mientras manipula. Esto lo quita.

## 3. Entrada única en la PDA por áreas

- Hoy se tiene que salir de una app y entrar en otra, y se desconecta enseguida. La tarjeta ya es la misma en todas desde el 20/11, con 60 min.
- Una entrada, y dentro una pestaña por área. Al entrar en un área empieza a contar su tiempo:
  - **Recepciones** (y descargar camión);
  - **Picking** (Lecturas);
  - **Compactación** (Contenedores);
  - **Devoluciones**;
  - **Inversa**;
  - **Expediciones** (cargar camión, montar cajas).
- Tareas sin lecturas, como cartón, limpieza o descarga: un botón empieza y para el tiempo, como Actividades. «Extra» con varias opciones.
- **Gestión** (monitor, tablero, integración S4T, cajas escaneadas): solo para quien toca. Los del almacén no tienen que ver contabilidad ni informes de dinero.

## 4. Cierre de sesión

- Ahora cierra a las 17:00. Con el turno de 6 a 14 se tuvo que cambiar a mano.
- Que vaya por turno.
- Regla de la empresa:
  - con 8 h seguidas, 15 min de descanso que se descuentan solos;
  - con horario partido, 1 h de comida.
- Las expediciones de algún camión pueden llegar a las 19:00.

## 5 y 6. Picking por zonas o agrupaciones

- Al operario se le da trabajo por **zona o agrupación**, no pedido a pedido. Con 200 o 2.000 pedidos no se pueden poner uno a uno.
- **Botón para elegir cada día**: tradicional o zonas, con una estimación del tiempo de cada una.
- Cuando acaba, coge la siguiente libre según las **unidades** (la de 50 acaba antes que la de 120) y la **prioridad de las tiendas** (el número S4T más bajo primero).

## 7. KOROSHI

- Piden que el aviso salga cuando **empezamos** cada pedido, no solo al acabar.
- Idea: una pestaña para KOROSHI con monitor, bultos, cajas y prendas. Es tema de Andrés: preguntarle antes.
