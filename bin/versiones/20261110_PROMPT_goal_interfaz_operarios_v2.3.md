Implementar en koroshi_operarios v2.3.0 las 11 ideas de interfaz de la maqueta `C:\dev\OleadasKoroshi\bin\versiones\20261110_IDEAS_interfaz_operarios_v1.html` (léela entera primero: es la referencia visual y funcional; los 3 paquetes de su tabla final). Partir del código actual del repo `C:\dev\OleadasKoroshi\odoo\modulos\koroshi_operarios` (v13.0.2.2.2). Odoo 13 Enterprise, compañía 8, PDA Zebra con lector que escribe en un input + Enter.

QUÉ HACER
- Paquete 1: pantalla bloqueada a pantalla completa «Lee tu tarjeta» (solo en modo tarjeta obligatoria; input invisible pero con foco, punto verde que late = lector preparado, gris + «Toca la pantalla» si pierde el foco; si leen una OUT sin tarjeta: aviso rojo «Esto es un pedido. Primero tu tarjeta»), cabecera «quién soy» (iniciales en círculo con color calculado del nombre, nombre grande, Salir arriba a la derecha), botones grandes (Continuar verde a todo el ancho; Faltante naranja y Saltar gris debajo en una fila; mín. 52–58 px; icono + texto), avisos con 4 tipos (ok/info/warn/mal), icono, frases cortas, botón de acción dentro del aviso cuando haga falta (p. ej. Reintentar), verdes se van solos a los 4 s; Salir con confirmación (hoja inferior, avisa si deja un pedido a medias); leer la tarjeta de otro operario con uno dentro pregunta «¿Cambiar a X?»; Menú como icono ☰ discreto abajo y, en modo tarjeta obligatoria, solo con pulsación larga de 2 s.
- Paquete 2: Saltar en hoja inferior con los motivos activos como tarjetas grandes + «Saltar pedido» / «No, volver» (2 toques; el texto libre, si el motivo lo pide, dentro de la hoja); pantalla «Abriendo KO/OUT/… para <operario>» con spinner que ignora lecturas mientras abre; pantalla «¡Hecho!» al volver con la OUT validada con el siguiente pedido en cuenta atrás de 3 s y botón «Parar aquí»; sin conexión: banda roja fija, bloquea lecturas, reintenta cada 5 s, aviso verde al volver; sonido (Web Audio) y vibración (navigator.vibrate si existe) bien/mal, con interruptor por PDA en localStorage. Salida automática por inactividad: parámetro del sistema `koroshi_operarios.minutos_inactividad` creado con valor 0 = desactivado (noupdate).
- Paquete 3 (solo lectura en el controlador): en el pedido actual, tienda, zona, nº líneas, uds, minutos desde que empezó y progreso leído/total (de las cantidades hechas/reservadas de la OUT o del lote Z-); en la cola, lista numerada con tienda, zona y uds; «Cogiendo ahora» plegado con el nº de operarios; contador del día (pedidos y uds) igual que lo calcula Productividad.

REGLAS (obligatorias)
- Todo en castellano: textos, comentarios, README, docs.
- Mantener todo lo que hace hoy: abrir directo al leer la tarjeta, Continuar/Saltar/Faltante al volver atrás, los 2 motivos, el grupo «tarjeta obligatoria» (id 141), `_bloquear`, la clave localStorage `koroshi_operarios_pda_2`, los endpoints actuales (se pueden ampliar sus respuestas, no cambiar su contrato).
- koroshi_faltantes mete su botón con `t-extend` + `t-jquery=".o_ko_dejar" t-operation="after"` (`button.o_kf_abrir_faltante`) y extiende `koroshi_operarios.Pantalla` con `.include`. NO tocar koroshi_faltantes: conservar `.o_ko_dejar`, `this.actual`, `this.operario` y que el botón Faltante quede naranja y al lado de Saltar (resolverlo con CSS/orden en operarios).
- Almacén Nath y los usuarios fuera del grupo: mismo comportamiento que hoy (pueden leer una OUT sin tarjeta). Solo cambia el aspecto.
- Sin campos nuevos en stock.picking, stock.move, stock.move.line, stock.picking.batch ni stock.picking.type. No tocar stock_barcode. Nada de escribir stock.quant. Nunca «Forzar disponibilidad». No validar OUT reales.
- No escribir nada en Odoo (nath.tuctuc.com) sin mi OK en el chat; RPC de solo lectura sí, con contexto allowed_company_ids [8]. No enseñar contraseñas ni emails de clientes/usuarios.
- No sobrescribir ni borrar versiones: todo nuevo con fecha. Sin commits.
- Respetar prefers-reduced-motion; contraste alto; nada de librerías externas.

ENTREGABLES (en C:\dev\OleadasKoroshi\bin)
1. Código en `odoo/modulos/koroshi_operarios` con manifest `13.0.2.3.0`, historial de versión en el manifest y README actualizados.
2. `bin/<fecha>_koroshi_operarios_v2.3.zip` (carpeta `koroshi_operarios/` en la raíz, sin __pycache__).
3. `bin/actualizar_koroshi_operarios_v2.3_<fecha>.sh` con el mismo patrón que `bin/actualizar_koroshi_operarios_v2.2.1_faltantes_v1.3.1_2026-11-10.sh` (check / install, valida el ZIP, copia de seguridad, un solo reinicio, pasos de Actualizar).
4. `bin/versiones/<fecha>_PRUEBA_operarios_v2.3.md`: checklist de prueba fuera de horas (con y sin tarjeta obligatoria, Almacén Nath igual que hoy, Faltante desde Operarios, lote Z-, sin conexión, volver a la versión anterior).
5. Una maqueta HTML nueva con fecha en bin/versiones con capturas o reproducción de las pantallas finales.

CÓMO COMPROBARLO ANTES DE DARLO POR ACABADO
- Python compila (`python -m py_compile`), XML bien formado, JS sin errores de sintaxis (node --check sobre el JS si hace falta envolverlo).
- Probar la pantalla en el navegador integrado a tamaño PDA (375x812): página de prueba local que cargue el XML/CSS/JS con un mock de las rutas RPC, recorriendo: bloqueada → tarjeta → abriendo → volver → Continuar/Saltar (hoja)/Faltante → Hecho → sin conexión → Salir con confirmación → cambio de operario. Sin errores en consola. Captura de cada estado.
- Revisar con un diff que koroshi_faltantes y stock_barcode no han cambiado y que no hay campos nuevos en los modelos de stock.
- No instalar en el servidor: lo subo yo. Al acabar, resumen en catalán con qué se ha hecho, qué no y qué hay que probar.
