# Prueba fuera de horas: koroshi_operarios v2.3.0, pantalla nueva de Lecturas (10/11/2026)

Parte de la v2.2.2 de operarios y la v1.3.1 de faltantes, ya instaladas. **koroshi_faltantes no cambia.**

ZIP: `20261110_koroshi_operarios_v2.3.zip`.
Script: `actualizar_koroshi_operarios_v2.3_2026-11-10.sh` (primero `check`, después `install`).
Después: Aplicaciones > Actualizar lista > *KOROSHI Operarios* Actualizar > Ctrl+F5 en el PC y en las PDA.
Maqueta con todas las pantallas: `20261110_MOCKUP_interfaz_operarios_v2.3.html`.

Operarios de prueba: **Isaac (OP9990001)** e **Isaac2 (OP9980001)**. Usuario: **Departament IT**.
**No validar ninguna OUT real.** Solo se valida con una **OUT de prueba** (ver la sección 0) y con OK en el chat.

## 0. Antes de empezar

- [ ] *Ajustes > Técnico > Parámetros del sistema*: existe `koroshi_operarios.minutos_inactividad` = `0`.
- [ ] *Motivos para saltar*: siguen solo **No hay stock / en espera** y **Fin de turno**.
- [ ] El grupo **«KOROSHI Operarios: tarjeta obligatoria»** sigue con los mismos usuarios que antes de actualizar.
- [ ] Isaac e Isaac2 tienen alguna OUT en cola (*Reparto*). Si no hay, se puede mirar todo menos el «¡Hecho!».
- **OUT de prueba (solo con OK en el chat):** igual que en `20261110_PRUEBA_faltantes_v1.3.1_operarios_v2.2.1.md`.
  Una OUT de *Koroshi: Pedidos* a un cliente de prueba, 2–3 líneas con stock, *Comprobar disponibilidad*.
  **Nunca «Forzar disponibilidad».**

## 1. Sin tarjeta obligatoria (Departament IT fuera del grupo)

1. *Lecturas (PDA)* sin operario.
   - [ ] **No** sale la pantalla bloqueada. Cabecera con «?» y «Lee tu tarjeta (o directamente la OUT)».
   - [ ] Abajo: punto **verde** parpadeando y «Lector preparado». Tocar fuera del campo: se pone **gris** y sale «Toca
     la pantalla». Tocar: vuelve a verde.
   - [ ] Abajo a la izquierda **☰**: con un toque va al menú de código de barras, igual que hoy.
2. Leer una OUT sin tarjeta.
   - [ ] Pantalla **«Abriendo KO/OUT/…»** y se abre la OUT. Aviso naranja «Sin tarjeta: … no cuenta en productividad».
3. Volver, leer **OP9990001**.
   - [ ] «Abriendo … para Isaac» y se abre su OUT directamente (como en la v2.2).
4. **Flecha atrás** sin validar.
   - [ ] Cabecera con el **círculo «IS»**, «Isaac», «Hoy: N pedidos · N uds» y **Salir**.
   - [ ] Tarjeta «Estás haciendo»: referencia, tienda, **zona** (Z1…), líneas, uds, minutos y la barra de uds leídas.
   - [ ] **Continuar** verde y grande. Debajo, en la misma fila: **Faltante** naranja (a la izquierda) y **Saltar** gris.
   - [ ] «Después te tocan» con la cola **numerada** 1, 2, 3… y «Cogiendo ahora (N)» **plegado**; se abre al tocarlo.
5. **Continuar** → vuelve a la OUT. Atrás otra vez.

## 2. Saltar, Salir y cambiar de operario

1. **Saltar** → sale una hoja abajo con los motivos como tarjetas.
   - [ ] «Saltar pedido» desactivado hasta elegir motivo. Si el motivo pide nota, sigue desactivado hasta escribirla.
   - [ ] **No, volver** cierra la hoja sin hacer nada.
2. Elegir **No hay stock / en espera** → *Saltar pedido*.
   - [ ] Aviso y se abre la **siguiente** OUT de la cola. En *Reparto* la saltada queda como siempre (v2.2).
3. Atrás → **Salir**.
   - [ ] Hoja «¿Salir, Isaac?» con el aviso de que deja un pedido a medias (sigue siendo suyo). **No** → no pasa nada.
   - [ ] **Sí** → «Adiós, Isaac.», cabecera vacía.
4. Leer OP9990001, atrás, y leer **OP9980001** (Isaac2).
   - [ ] Hoja **«¿Cambiar a Isaac2?»**. *Sí* → abre la OUT de Isaac2. *No* → sigue Isaac.

## 3. Faltante (koroshi_faltantes sin cambios)

1. Con una OUT abierta y vuelta atrás → **Faltante** (naranja).
   - [ ] Se abre la pantalla de faltantes de la v1.3.1 con esa OUT y ese operario. Todo igual que antes.
2. En un **lote Z-** (leer OP de alguien con un Z- en cola o abrir el Z- desde Lecturas):
   - [ ] La tarjeta enseña la zona sin repetir la «Z» (p. ej. «Z2»). *Faltante* abre la lista del lote como antes.

## 4. ¡Hecho! (solo con la OUT de prueba, con OK)

1. Isaac con la OUT de prueba primera en la cola y otra detrás. Leerla y validarla en la app de código de barras.
   - [ ] Al volver sale **«¡Hecho!»** en verde, la siguiente (referencia y tienda) y «Se abre en 3 s».
   - [ ] A los 3 s se abre la siguiente. Repetir y tocar **Parar aquí**: se queda en Lecturas sin abrir nada.
2. Sin nada más en la cola: «¡Hecho!» sin siguiente.

## 5. Tarjeta obligatoria (Departament IT en el grupo, con OK)

1. Con OK: Departament IT en **«KOROSHI Operarios: tarjeta obligatoria»** (como en la prueba v2.2.1).
2. *Lecturas (PDA)* sin operario.
   - [ ] **Pantalla completa «Lee tu tarjeta»** con el punto verde. No se ve nada más (ni cola ni ☰).
   - [ ] Leer una OUT: aviso **rojo** «Esto es un pedido. Primero tu tarjeta.», vibra/pita y **no se abre nada**.
   - [ ] Tocar fuera: punto gris «Toca la pantalla»; tocar la pantalla: vuelve a verde.
3. Leer OP9990001 → se abre su OUT. Atrás.
   - [ ] **☰ con un toque:** aviso azul «Mantén pulsado ☰ 2 segundos…». **Mantener 2 s:** va al menú.
4. **Salir** → *Sí* → vuelve la pantalla bloqueada.
5. Con **Almacén Nath** (otra PDA o pestaña privada):
   - [ ] Ni bloqueo ni pulsación larga: una OUT sin tarjeta se abre como hoy (ver sección 1).

## 6. Sonido, vibración e inactividad

1. Botón **🔊** abajo a la derecha.
   - [ ] Al leer bien: pitido corto (y vibra en la PDA). Al leer mal: pitido grave.
   - [ ] Tocar 🔊 → se apaga (🔇). Recargar (F5): sigue apagado en esa PDA. Volver a encenderlo.
2. `koroshi_operarios.minutos_inactividad` = `1` (con OK; es solo un parámetro).
   - [ ] Isaac en Lecturas sin tocar nada 1–2 min: «Salida automática por inactividad: Isaac.»
   - [ ] Dentro de la app de código de barras (OUT abierta) **no** sale solo.
   - [ ] Volver a dejarlo en `0`.

## 7. Sin conexión

1. Con Isaac en Lecturas, quitar el wifi de la PDA (o modo avión).
   - [ ] Banda **roja** arriba «Sin conexión con Odoo…» en ≤ 5 s (o al leer algo).
   - [ ] Leer una OUT o tarjeta: aviso «Sin conexión: no se ha leído…», no se abre nada.
2. Volver a poner el wifi.
   - [ ] A los ≤ 5 s desaparece la banda y se puede leer otra vez.

## 8. Pantalla y accesibilidad

- [ ] En la PDA (pantalla pequeña) no hay que desplazar de lado; los botones se tocan bien con guantes.
- [ ] Con «Quitar animaciones» del sistema activado: no parpadea el punto ni gira la rueda.
- [ ] En el PC (pantalla ancha) se ve centrado y legible.

## 9. Dejarlo todo como estaba

- Departament IT: quitarlo del grupo y *Acción inicial* vacía, si se metió en la sección 5.
- `koroshi_operarios.minutos_inactividad` = `0`.
- OUT de prueba: si no se ha validado, *Anular reserva* y *Cancelar*. Si se ha validado, dejarla y apuntar su nombre
  aquí: ________.
- **Volver a la v2.2.2:** copiar `/opt/nath-erp/copias_modulos/koroshi_operarios_<fecha>` a
  `/opt/nath-erp/nath/enterprise-addons/koroshi_operarios`, reiniciar `nath-erp`, *Actualizar* KOROSHI Operarios y
  Ctrl+F5 en las PDA. El parámetro `minutos_inactividad` se puede quedar (la v2.2.2 no lo lee).
