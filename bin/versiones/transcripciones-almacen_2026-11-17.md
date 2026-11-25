# Transcripciones del almacén — 17/11/2026

Cuatro grabaciones (`C:\Users\tuctuc\Videos\`), limpiadas y ordenadas por tema. Se quitan muletillas,
repeticiones del transcriptor (la grabación 3 repite el mismo bloque cinco veces y la 2 acaba con «Su… Su…»)
y conversaciones ajenas. Los números son los que se dicen en voz alta mirando la pantalla.

---

## 1. «Carrer Danuvi» — pantalla Producción por hora (revisión con el responsable)

**Lo que se ve y gusta**
- Pestaña de producción por zonas y por operario, con unidades, u/h y minutos efectivos por hora;
  se va ampliando cada hora y se refresca sola cada minuto. Se puede cambiar el día (por defecto, hoy).
- Detalle por operario: empieza, acaba, unidades, u/h. «Esto es lo que quería y lo que necesito».
- Permite detectar a quién apretar: gente a 160, 125, 110 u/h y otra a 39 o 33 u/h.
- Se ve el tiempo que se pierde cerrando cajas (el cronómetro va de coger el pedido a validar; el hueco
  entre pedidos no cuenta).

**Dudas que salieron (comprobar)**
- No salen las tiendas («las de botigues») en la vista: hace falta verlo todo (Ctrl+F5 para que cargue).
- ¿Cuenta pedidos de ayer? Un operario «de 8 a 9 solo hizo 3 unidades». Debe contar solo lo del día
  de hoy. Explicación probable: hizo web u otra cosa fuera de la app, o empezó a las 9. «Hasta las 9 no
  le hacemos caso».
- Una fila confundía 91 unidades con minutos: el número grande son **unidades** de esa hora y los
  minutos efectivos van aparte (44 min). Pide que salgan los **minutos efectivos claramente** («que
  salga 41 minutos efectivos»), no solo las unidades.
- Ojo con Carolina: medias raras porque son chaquetas.
- La otra pantalla (la de la otra nave) no coge igual: «2.530 de 3.171, 80 %… esto no puede ser».
  Revisar que coja bien.

**Lo que pide**
1. **Colores** en la tabla (verde/rojo según ritmo).
2. **Diferenciar zonas vs webs vs Zalando/Volldur**: Zalando/Volldur no se reparten por zonas; las webs
   tampoco salen y también se quiere su productividad.
3. **Ponerlo en una pantalla visible** para que lo vea la gente del almacén.
4. **Barra de progreso por pedido**: al entrar un pedido arranca un contador. Ejemplo: 120 uds a
   ritmo estándar = 1 hora → barra de 1 hora. Mientras el operario va dentro del ritmo la barra va bien;
   cuando se queda atrás empieza a avisar y se pone **roja** progresivamente. «Que la gente vea:
   no llego».
5. **Cabecera del día**: total del día (lo pendiente a primera hora + lo que entra), hecho, pendiente,
   previsión de horas y **hora estimada de fin** al ritmo actual («así a primera hora sé a qué hora
   tendría que estar acabado»). Antes estaba en la otra pantalla y funcionaba.
6. **Informe a final de mes** con estos datos (tabla tipo informe, como el correo que ya le llega).
7. Después, extenderlo poco a poco a la otra nave (moda íntima, web, internas…).

---

## 2. «2026-11-17 12-08-39» — u/h real vs u/h efectiva

- Hoy la u/h que sale es **mientras está en picking** (minutos efectivos). Eso infla: si trabajan 9 min
  y cogen 15 uds, la media sale altísima. «No hace 125, hace 90».
- Cerrar la caja, precintar, ponerla en el palé… **forma parte del picking**. Andrés dirá: «yo pago la
  hora entera, no la efectiva».
- Quiere **las dos cifras**:
  - u/h mientras pica (la actual, «me parece correcta»);
  - **u/h real de la hora entera** = unidades leídas en esa hora (ej.: Diana Carolina de 9 a 10:
    42 uds → son 42 u/h, no 65).
- Y que el **tiempo efectivo y el tiempo perdido** salgan más visibles: si hay 39 min efectivos, ¿qué
  pasa en los otros 21? Es la siguiente métrica a trabajar.
- Huecos raros a la vista: una operaria «desaparece» de 10:00 a 10:14 (¿desayuno?) y otros 11 min
  hacia las 11:29. Bien que se vean.

---

## 3. «Carrer Danuvi 2» — PDA: login y ronda de faltantes

(La grabación repite cinco veces el mismo bloque; aquí una sola vez. Lo demás es charla de nave.)

- Tras las mejoras, si la PDA no detecta al operario: **tiene que salir siempre su nombre**; si no
  sale, volver a iniciar sesión.
- El faltante ya funciona y se envía.
- **Ronda de faltantes en la PDA**: se crea como una interna (INT) que manda a cada ubicación donde se
  suponía que estaba el artículo. El operario lee cada línea y marca:
  - **está** → vuelve a fijarse la ubicación;
  - **no está** → sigue en faltantes;
  - **la ubicación ya no existe** → opción nueva a añadir.
- Ya se reducen faltantes: si en una ubicación no está, la PDA busca otra ubicación nueva.
- El responsable quiere poder sacar un **documento** con lo encontrado y lo no encontrado, con el
  operario.
- Comentario: sobran campos en pantalla («finanzas, no sé cuántos… todo eso es basura»).
- Operativo (no software): reforzar zona 1 — Erika de la zona 2 a la 1.

---

## 4. «Nueva grabación 22» — devoluciones online y S4T

- Proceso actual de devoluciones: buscar el pedido → entrar → motivo → «Crear devolución». Hay varios
  tipos de devolución (lo pregunta Cruz).
- Al crear la devolución debería subirse a la API de S4T y **no se está subiendo**. Lo entendido:
  hacemos la devolución aquí → va a su sistema → nos lo devuelven para contar y ubicar. No llega.
- **Sonia** escribió (urgente, en mayúsculas): **dos palés de «Devos Online» llenos de género**
  esperando ubicar. Se preguntó hace tiempo cómo ubicarlo; Víctor pidió algo a su informático; sin
  respuesta.
- Hay un **Excel con fecha de lo gestionado** de devoluciones; lo lleva una compañera en su ordenador,
  sin Teams, y no se actualiza → compartirlo en el Teams/carpeta del almacén.
- Zalando: el Excel de lo entrado hay que pasarlo; se van leyendo los palés y se suben los datos.
- Esto no cuenta en productividad: solo cuentan pedidos de picking; devolver, ubicar y manipular no.
- Hace falta otra etiquetadora aquí.
- **Una sola cuenta en un solo ordenador**: se pidió hace semanas (correo y WhatsApp), sin respuesta;
  no se puede trabajar así, menos los lunes.
- **Acción**: contestar el correo poniendo en copia a Sonia, Andrés y Cruz: «llevamos X tiempo sin
  respuesta, ¿cómo procedemos?» (ubicación de los palés, API de devoluciones y la cuenta única).
