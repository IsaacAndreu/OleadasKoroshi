# Prueba fuera de horas: koroshi_faltantes v1.3 + koroshi_operarios v2.2 (09/11/2026)

ZIP: `20261109_koroshi_faltantes_v1.3.zip` y `20261109_koroshi_operarios_v2.2.zip`.
Script: `actualizar_koroshi_operarios_v2.2_faltantes_v1.3_2026-11-09.sh` (`check` y después `install`).
Después: Aplicaciones > Actualizar lista > *KOROSHI Operarios* Actualizar > *KOROSHI Faltantes* Actualizar > Ctrl+F5
en el PC y en las PDA.

Operarios de prueba: **Isaac (OP9990001)** e **Isaac2 (OP9980001)**. Usuario: **Departament IT**.
**No validar ninguna OUT real.** Los pasos que validan van con una **OUT de prueba** (ver 0).

## 0. Antes de empezar

- [ ] *Ajustes > Técnico > Parámetros del sistema*: existen `koroshi_faltantes.validar_sola` = `1` y
  `koroshi_faltantes.pedido_pendiente` = `preguntar`.
- [ ] *Ajustes > Usuarios y compañías > Grupos* (modo desarrollador): existe **«KOROSHI Operarios: tarjeta
  obligatoria»** y **no tiene usuarios**.
- [ ] Almacén Nath en la PDA: todo igual que hoy (leer una OUT a mano se abre como siempre).
- **OUT de prueba (solo con OK en el chat):** una OUT de *Koroshi: Pedidos* a un cliente de prueba (no tienda),
  2–3 líneas de artículos con stock en ubicaciones distintas, 2–4 uds por línea, *Comprobar disponibilidad*.
  **Nunca «Forzar disponibilidad».** Si no se quiere crear, los pasos 4 y 5 se dejan para el lunes con una OUT real
  que de verdad se vaya a enviar, con el responsable delante.

## 1. Faltantes: la lista (sin validar nada)

En una OUT real **preparada** (solo mirar, no tocar):

1. *Lecturas (PDA)* → abrir la OUT → **Faltante**.
   - [ ] Sale la **lista de lo que queda por coger**: referencia grande, color / talla, ubicación, uds. En el mismo
     orden que la app de código de barras (por ubicación).
   - [ ] Se pueden **marcar varias**; *Continuar* se activa con alguna marcada.
2. Marcar 1 línea → *Continuar*.
   - [ ] Sale **una sola** ubicación recomendada (la que tiene más stock libre) y el enlace **Ver más**.
   - [ ] **Ver más** enseña las demás; **Ocultar las demás** las esconde.
3. **Salir** (no reubicar en una OUT real).
4. Leer en la pantalla de Faltante el **código de una ubicación** de la lista.
   - [ ] Si en esa ubicación hay una línea pendiente, va directo a ella; si hay varias, filtra la lista.
5. En un **lote Z-** (*Faltante* desde una agrupación Z-):
   - [ ] Sale la lista del lote. **No** sale el botón *Validar OUT* (el lote se valida como siempre).

## 2. Faltantes: reubicar y «Tampoco está aquí» (OUT de prueba)

1. OUT de prueba → *Faltante* → marcar la línea A → *Continuar* → elegir la ubicación recomendada.
   - [ ] La línea A pasa a esa ubicación (en la OUT, *Operaciones detalladas*). Mensaje en verde.
2. Marcar la línea B → *Continuar* → **Tampoco está aquí**.
   - [ ] Pide confirmar (segundo toque). Al confirmar, la línea B **sale de la OUT** (se quita su reserva) y esas uds
     pasan de su ubicación a **FALTANT**. En *Faltantes* sale el registro «sin alternativa».
3. **Esta no: dejarla y seguir** con otra línea marcada.
   - [ ] Pasa a la siguiente sin tocar la que se ha dejado.

## 3. Línea a medias (OUT de prueba)

1. En la app de código de barras leer **1 de las 3 uds** de una línea. Guardar sin validar. Volver.
2. *Faltante* → esa línea sale con **2 pendientes**.
   - [ ] Reubicar: la línea leída se queda con la 1 ud en su sitio y las 2 se reservan en la ubicación nueva.
   - [ ] (Repetir en otra) *Tampoco está aquí*: la línea se queda en 1 ud leída y no se pierde lo leído.
3. Una línea **del todo leída** no sale en la lista.

## 4. Validar al acabar (OUT de prueba, solo con OK)

1. Leer en la app de código de barras todo lo que queda de la OUT de prueba, salvo lo marcado como faltante.
2. *Faltante* sobre la última línea pendiente → *Tampoco está aquí* → confirmar.
   - [ ] Al no quedar nada por coger, Odoo pregunta por lo que falta y la PDA enseña **Sí, pedido pendiente** /
     **No, sin pedido pendiente** con la explicación.
   - [ ] **No** → la OUT queda *Hecho* sin pedido pendiente. **Sí** (en otra OUT de prueba) → se crea el pedido pendiente.
   - [ ] Si se abrió desde Operarios: la tarea y la asignación quedan cerradas y vuelve sola a Lecturas.
3. Con `koroshi_faltantes.validar_sola` = `0`: no valida sola; sale el botón **Validar OUT**.
4. Error forzado (p. ej. OUT ya validada en otra pestaña): mensaje **en rojo** y botón **Volver a la OUT**.
5. Dejar `validar_sola` = `1` al acabar.

## 5. Validar desde cualquier página (sin código nuevo)

- [ ] Imprimir el código de barras **`O-BTN.validate`** (Code128) y leerlo dentro de una OUT de prueba en la
  **primera** página: valida igual que el botón *Validar* de la última página. Ver
  `20261109_INFORME_validar_OUT_codigo_barras.md`.

## 6. Operarios v2.2: abrir directo (todos los usuarios)

1. *Lecturas (PDA)* → leer **OP9990001** (Isaac, con una OUT en cola).
   - [ ] La OUT se abre **directamente**, sin las 3 opciones.
2. **Flecha atrás** sin validar.
   - [ ] Ahora sí: **Continuar / Saltar / Faltante**.
3. Ir al menú principal y volver a *Lecturas* (o recargar con F5).
   - [ ] Con Isaac guardado en la PDA, la OUT que está haciendo se abre **sola** al entrar.
4. Leer una OUT a mano (con Isaac): se abre directa.

## 7. Operarios v2.2: tarjeta obligatoria (solo Departament IT, con OK)

1. Con el OK del usuario: Departament IT en el grupo **«KOROSHI Operarios: tarjeta obligatoria»** y en el usuario
   *Preferencias > Acción inicial* = **Operarios**.
2. Cerrar sesión e iniciar con Departament IT.
   - [ ] Entra directamente en *Lecturas (PDA)*.
3. **Salir (otro operario)** y leer una OUT sin tarjeta.
   - [ ] «Lee primero tu tarjeta. Sin tarjeta no se puede abrir ningún pedido.» No se abre nada.
4. Leer OP9990001 → se abre su OUT.
5. Con **Almacén Nath** (otra PDA o pestaña privada):
   - [ ] Sin tarjeta, leer una OUT se abre como hoy (no está en el grupo).
6. Límite conocido: el botón **Menú** de Lecturas lleva al menú de código de barras y desde allí se puede abrir una OUT
   sin tarjeta. Lo comprobamos pero no se arregla (habría que tocar `stock_barcode`).

## 8. Dejarlo todo como estaba

- Departament IT: *Preferencias > Acción inicial* **vacía** y quitarlo del grupo (*Grupos* > «KOROSHI Operarios: tarjeta
  obligatoria» > pestaña *Usuarios* > quitar).
- OUT de prueba: si no se ha validado, *Anular reserva* y *Cancelar*. Si se ha validado, dejarla (no borrar datos) y
  apuntar su nombre aquí: ________.
- Parámetros: `validar_sola` = `1`, `pedido_pendiente` = `preguntar`.
- Volver a la versión anterior: copias en `/opt/nath-erp/copias_modulos/*_<fecha>`, copiarlas a los addons,
  reiniciar y *Actualizar* los dos módulos.
