# Resumen de la sesión 12-13/11/2026: preparación en la PDA, monitor, ajustes y diagnósticos

Sesión principal de mejoras de almacén KOROSHI (NAU-2, Odoo 13 EE, nath.tuctuc.com, compañía 8).
Aquí se recoge qué se hizo, en qué estado quedó y qué se aprendió. Las versiones están en `bin/`; las páginas, en
`bin/versiones/`.

## 1. Estado al cerrar (13/11, 08:35)

| Módulo | En el servidor | Preparado en `bin/` (sin instalar) |
|---|---|---|
| koroshi_preparacion | 3.21.0 | **3.23.0** (alarma con horario + caja sin internet + negrita 3.21.1) |
| koroshi_menu | 1.1.0 | **1.3.0** (minutos y horario de la alarma en Ajustes KOROSHI) |
| koroshi_informe | no instalado | **1.0.0** (correo de productividad; sin probar dentro de Odoo) |
| koroshi_monitor | 1.23.2 | — |
| koroshi_operarios | 2.8.0 | — |
| koroshi_kpi | 1.5.0 | — |
| koroshi_xpo_bultos | 1.1.0 | — |
| koroshi_s4t_envios | 1.1.0 | — |

Para copiar a `/home/it_nath_group`:

- `bin/20261112_koroshi_preparacion_v3.23.0.zip`
- `bin/20261112_koroshi_menu_v1.3.0.zip`
- `bin/instalar_koroshi_preparacion_v3.23.0_menu_v1.3.0_2026-11-12.sh`
- Opcional: `bin/20261112_koroshi_informe_v1.0.0.zip` y `bin/instalar_koroshi_informe_v1.0.0_2026-11-12.sh`

**No instalar** (versiones incompletas que se quedan en `bin/` porque no se sobrescribe nada):

- `20261112_koroshi_preparacion_v3.22.0.zip`: no lleva la caja sin internet.
- `20261112_koroshi_menu_v1.2.0.zip`: no lleva el horario.
- `instalar_koroshi_preparacion_v3.22.0_menu_v1.2.0_2026-11-12.sh`

## 2. Qué se hizo

### Preparación en Lecturas (PDA)

- **3.18:** mensaje claro al leer otro código de la bolsa: «Lee el de KOROSHI, el que empieza por 8445962».
- **3.19 / 3.20 (Zalando y About You):**
  - «Caja» crea el paquete de Odoo (PACK…) sin leer etiqueta.
  - El número sale en grande y hay lista de cajas («N cajas»).
  - Al validar, lo que queda fuera de caja va solo a la última caja.
- **3.21:**
  - Lápiz ✎ en la lista de líneas para pasar unidades de una caja a otra o a una caja nueva.
  - Color de la franja de la ubicación elegible por operario (menú ☰); por defecto F, amarilla y grande.
- **3.21.1:** amarillos C y F con la letra más negra y el código KO en negrita.
- **3.23.0 (incluye la 3.22.0, que no se instaló):**
  - **Alarma de parado:**
    - Con la OUT abierta y 4 minutos sin leer, la PDA pita sin parar, vibra y parpadea en rojo hasta que lee una prenda.
    - Solo suena de 06:00 a 10:00, de 10:15 a 13:00 y de 14:00 a 17:00.
    - Parámetros `koroshi_preparacion.minutos_alarma` y `koroshi_preparacion.horario_alarma`.
  - **Caja sin internet:**
    - «Caja» y leer la CJ funcionan sin conexión. La caja se cierra en la PDA, va a la cola en su sitio entre las lecturas y queda en la memoria de la PDA.
    - Al volver la conexión, Odoo la cierra en el mismo orden y con el mismo id, sin duplicarla.
    - Zalando / About You: sin red sale «S1», «S2»… para apuntar en la caja; al volver sale su PACK («era S1»).
    - Validar sigue necesitando conexión.
  - **Arreglo:** al pulsar «Caja» se borraba la clase de los avisos de Faltante, Mover, Cantidad e Imprimir, y podían dejar de verse.

### Operarios 2.8.0

- Solo pregunta «¿Unirte a X?» (antes «Ayudar a X») si alguien está leyendo esa OUT ahora mismo.
- Si nadie lee la OUT desde hace 15 minutos, quien la lee se la queda sin preguntar. La tarea del otro se cierra como
  «relevo».
- Para saber si alguien trabaja se mira la última lectura de Lecturas **y** la última línea hecha en la app de código
  de barras.

### Monitor

- **1.21:** alarma roja de bloqueo para la OUT sin lecturas desde hace más de X minutos, con quién la tenía.
- **1.22 / 1.23.x** (sesión del Excel): Excel de tiendas agrupado por tienda, Done Quantity y cajas por pedido. El Excel
  de XPO solo cuenta las OUT con etiqueta XPO propia.

### KPI 1.5 y Menú 1.1

- **Comparativa de semanas.**
- **Faltas repetidas (revisar):** el mismo artículo y ubicación con faltas en varios días.
- **Ajustes KOROSHI:** una sola pantalla con los parámetros (Configuración › KOROSHI).

### Otros

- **Manual de la PDA para operarios:** https://claude.ai/artifact/6WY9e1nSQ5Dt6SRkfKYWN2 (copia en
  `bin/versiones/20261112_manual_operarios/`).
- **Demostración de colores de la ubicación:** https://claude.ai/artifact/FBMLCdS5zu6Y9qXoChNZtd.
- **Informes QWeb:** los 155 tienen punto en `report_name`. Sin plantilla solo «Aged Partner Balance» y
  «PRO-FORMA Invoice 2 copy(1)», que no son de KOROSHI.
- **scrcpy 5.0.1 (lleva su adb) instalado con winget en el PC:**
  - La TC22 (26225524701194) se ve por USB, pero falta aceptar «Permitir depuración USB» en la PDA.
  - El primer error «Dispositivo USB desconocido» era el cable o el puerto.

### Sesiones abiertas desde aquí (audio de la reunión del 12/11)

- **Inversa KOROSHI:**
  - Teórico por familias, palets y layout: `bin/versiones/teorico-inversa-KOROSHI_2026-11-12_1658_v2-cola-compartida.html`.
  - Diseño de la lectura de matrículas por operario: `bin/versiones/diseno-lectura-matriculas-inversa_2026-11-12_1705.md`.
  - Falta confirmar con Betty de dónde sale el contenido de las matrículas.
- **Correo de productividad:** `koroshi_informe` 1.0.0 (diario, semanal y mensual). Ejemplo en
  `bin/versiones/correo_productividad_ejemplo_2026-11-12_1700.html`. No envía nada sin correos en Ajustes.
- **Alarma sonora:** juntada en la 3.23.0.
- **Pendiente:** «Productividad sin pausas» (descontar 10:00-10:15 y 13-14 en operarios y KPI). Ahora no se descuenta en
  ningún sitio.

## 3. Diagnósticos

### «No va Odoo» (12/11, 12:36)

- Corte de un minuto por el reinicio al instalar el Monitor 1.23.0.
- Si una PDA se queda mal: cerrar la app de Odoo y abrirla otra vez. Si no basta, Ajustes › Aplicaciones › Odoo ›
  Almacenamiento y caché › **Borrar caché** (nunca «Borrar almacenamiento»).

### «Error de CORS desconocido» en la PDA

- Sale **al salir de Código de barras**, que recarga Odoo entero. Siempre ha salido.
- No es un error de los módulos KOROSHI ni se pierde nada: pulsar ACEPTAR y seguir.

### Pedido de K72 S-6665004044 sin validar (13/11)

- El pedido entró bien de S4T el 10/11 (01:18) y Odoo creó su OUT **EFFEC/OUT/24130**.
- **La borraron el 10/11 a las 12:05 con el usuario «Almacén Nath».**
- Pruebas:
  - Falta exactamente la OUT/24130 (id 385642) y faltan 24 ids de movimientos entre el pedido anterior (K31) y el
    siguiente.
  - El pedido y sus 23 líneas se modificaron por última vez a las 12:05:43 con Almacén Nath.
  - En el mismo minuto se mandaban a XPO la OUT/23953 y la **OUT/23932, otra OUT de K72** (del 9/11). Lo más probable es
    que vieran dos OUT de K72 y borraran la del 10/11 como si estuviera repetida.
- Arreglo (13/11, con el OK de Isaac): se pusieron las 23 líneas a 0 y otra vez a 1. Odoo creó **EFFEC/OUT/25275**, con
  19 de 23 uds reservadas y 4 sin stock.
- Quedan sin mirar tres pedidos de tiendas del 03/11 confirmados y sin OUT: S-6665003822 (K56), S-6665003821 (K81) y
  S-6665003812 (K33). Preguntar a Betty antes de crearles la OUT.

## 4. Qué hemos aprendido

### Odoo

- **Un pedido confirmado sin OUT casi nunca es error de la importación.**
  - Hay que mirar si falta el número de la OUT en la secuencia y los ids de `stock.move` entre el pedido anterior y el
    siguiente.
  - También quién modificó el pedido y cuándo: borrar la OUT reescribe las líneas del pedido.
  - Odoo no guarda quién borra: no hay módulo de auditoría y todos usan «Almacén Nath».
- **Volver a crear la OUT de un pedido confirmado:**
  - Escribir la misma cantidad en la línea no hace nada: `sale_stock` solo lanza la regla si la cantidad **sube**.
  - Hay que poner la cantidad a 0 y luego a la de antes. Así crea los movimientos que faltan, con el mismo grupo de
    abastecimiento.
- **Actualizar módulos que dependen entre sí:** en la misma llamada (`button_immediate_upgrade` con todos los ids). Si
  no, la cascada puede actualizar uno que necesita otro aún viejo y todo vuelve atrás («External ID not found»).
- **Mover unidades entre cajas sin perder la reserva:**
  - `copy` con 0 pedidas y las hechas.
  - Restar las mismas en la línea original.
  - Pasar las pedidas a la copia.
  - Es lo mismo que hace `put_in_pack`.

### PDA y pantalla

- **Probar el JS nuevo sin instalar:**
  - Servirlo desde el PC (servidor local con CORS) y redefinirlo con otro nombre de módulo.
  - Añadir las plantillas con `qweb.add_template` y abrir la acción `koroshi_preparacion_pantalla` sin operario.
  - Antes, bloquear en el navegador `fetch` y `XMLHttpRequest` a todo lo que no sea lectura (`/cargar`), para que nada
    llegue a Odoo.
  - Al acabar, borrar la cola de la memoria (`koroshi_preparacion_cola`) y recargar.
- Un selector genérico como `this.$('.o_kp_hoja_aviso')` toca **todas** las hojas. Siempre hay que limitarlo a la hoja
  que toca.
- Lo que se deja en la cola de la PDA tiene que guardar también las cajas, en su orden; si no, lo leído después de una
  caja acabaría dentro de la caja anterior.

### Trabajo con varias sesiones

- **Dos sesiones no deben editar el mismo módulo a la vez:**
  - El aviso de «para» llega cuando la otra acaba su turno, no antes.
  - Por eso salió una 3.22.0 a medias, que no se puede sobrescribir.
  - Si pasa, la versión final la saca la sesión que sigue editando, y la otra comprueba el ZIP contra el repo antes de
    instalar.
- Antes de decir qué ZIP copiar, mirar el `installed_version` del servidor. La sesión de Odoo del navegador caduca: si
  sale «Session Expired», Isaac tiene que entrar.

## 5. Siguientes pasos

1. Copiar la 3.23.0 y el menú 1.3.0, actualizar y probar la alarma y la caja sin red en una PDA.
2. Decir al almacén que **no borre OUT**: si una parece repetida, que avise.
3. Revisar los tres pedidos del 03/11 sin OUT (K56, K81, K33).
4. Inversa: confirmar con Betty el origen del teórico antes del lunes.
5. `koroshi_informe`: instalar, poner los correos en Ajustes y revisar el primer envío.
6. Productividad sin pausas (tarea propuesta).
