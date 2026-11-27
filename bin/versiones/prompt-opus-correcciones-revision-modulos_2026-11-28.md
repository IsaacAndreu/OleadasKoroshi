# Prompt para Opus 5.5: correcciones de la revisión de módulos (28/11/2026)

Copiar todo lo que hay debajo de la línea en una sesión nueva con **Opus 5.5, esfuerzo high**, en la carpeta
`C:\dev\OleadasKoroshi`.

---

Vas a corregir, por entregas, lo que encontró la revisión de todos los módulos del 28/11/2026 en los módulos Odoo 13 EE
del almacén KOROSHI (compañía 8, nath.tuctuc.com). Los operarios preparan pedidos con PDA todo el día: un fallo se
nota en el almacén al momento. Prefiero un arreglo pequeño y seguro a uno completo y arriesgado.

## Antes de empezar

1. Lee `CLAUDE.md` (reglas no negociables), `TABLERO.md` y `bin/versiones/revision-modulos-fable_2026-11-28.md`. Los
   códigos Z1, E1, P1, F1, M1, H1, T1… de este prompt son los de ese informe: allí está cada hallazgo con su
   `archivo:línea`, su gravedad y el arreglo propuesto.
2. El informe sale de **leer** el código; nada se reprodujo en Odoo. Solo los marcados con ✔ se comprobaron dos veces.
   Regla 10: antes de cada cambio abre el código y confirma que el fallo existe tal como se describe. Si no lo puedes
   confirmar, o el código ha cambiado desde `e71282a`, dilo y no lo arregles a ciegas.
3. Muchos módulos están cogidos por otros chats (columna «Módulo cogido» del TABLERO). **Antes de cada entrega, mira si
   su módulo está cogido**: si lo está, pide a Isaac que lo suelte o deja el hallazgo apuntado para ese chat. Cuando
   empieces, apúntate en «En curso» con el módulo de la entrega.
4. Pregunta a Isaac la `installed_version` real de cada módulo antes de sacar su versión (regla 3): el servidor puede
   ir por delante del repo.
5. Trabaja desde `main` al día, no desde `feat/tuctuc-pda`, salvo la entrega 12.

## Cómo se trabaja

- **Una entrega cada vez, en el orden de abajo**, y dentro de ella un módulo cada vez. Si la entrega toca dos módulos,
  dilo al empezarla (regla 6). Cada módulo lleva su propia versión.
- Al acabar cada módulo: versión subida en el manifest, línea de historial, commit con rutas (como los commits
  anteriores del repo), `python bin/empaquetar.py <modulo>` y la línea del TABLERO en el mismo commit. Antes de
  empaquetar, pasa el subagente `revisor-version`.
- Después, el cierre de la regla 11: qué se ha cambiado (`archivo:línea`), cómo se ha probado, qué no se ha podido
  probar y qué hay que probar en una PDA real. **Para y espera el visto bueno de Isaac** antes de la siguiente.
- No se instala, ni se sube, ni se reinicia nada en el servidor. No se tocan datos de producción. Si necesitas datos
  reales, escribe la consulta de solo lectura y espera a que Isaac la pase.
- Ningún campo nuevo en `stock.picking`, `stock.picking.type` ni `stock.move.line` (regla 7). Los índices sobre esas
  tablas tampoco van en el módulo: se proponen aparte, para crearlos a mano con `CONCURRENTLY` y el sí de Isaac.
- Todo en castellano. Lo común, a `koroshi_base` (regla 8), pero **no subas la versión de `koroshi_base` dentro de
  otra entrega**: un `-u` de base arrastra ~23 módulos. Lo que haya que llevar a base se junta en la entrega 10.
- Añade una prueba sin Odoo por cada arreglo de lógica (en `tests/` del módulo; créala si no existe). Para lo que
  llama a S4T, GLS o XPO, con `requests` simulado.
- No cambies comportamiento que nadie ha pedido. Donde el arreglo cambie lo que ve el operario o lo que se cancela, se
  avisa o se envía, **pregunta antes** (están marcados con «decide Isaac»).
- Las pruebas en OUT reales, solo reversibles: leer y deshacer, sin cerrar cajas ni validar.

## Entrega 0. Datos que faltan (solo lectura, sin código)

Prepara para Isaac, en un solo bloque que pueda pegar en la consola del servidor, las consultas del apartado 9 del
informe: `installed_version` de todos los módulos; `\d stock_move_line`, `\d stock_quant_package` y `\d zebra_label`;
versión de Python del servicio; OUT canceladas por «KOROSHI Retener» desde el 24/11 con el nº de líneas de su pedido;
y las líneas «KOROSHI Preparación validar» del log de la última semana. Con las respuestas, corrige las gravedades
marcadas «probable» antes de seguir. La consola no tiene usuario `postgres` local y el `python3` del sistema es 3.5:
ver `odoo/modulos/koroshi_rendiment/README.md`.

## Entrega 1. koroshi_retener_tiendas: no cancelar lo que aún no se ha reservado (Z1, Z7, Z10)

Lo más urgente: está instalado y cancelando. **Decide Isaac** si mientras tanto se pone
`koroshi_retener_tiendas.cancelar_pocas` = 0 en el servidor.
- Z1: un pedido con movimientos por reservar sin intento de reserva (job de `koroshi_s4t_pedidos` sin acabar, o
  pedido recién entrado) no se cancela ni cuenta como «pocas uds»: solo se avisa, con el motivo.
- Z10: apuntar la revisión después de hacerla y avisar si se salta por llegar tarde.
- Z7: que «real» no se pueda poner (o que el correo lo diga) mientras zonas no llame a `pickings_retenidos()`.
- Prueba: `_pocas` con un pedido grande sin reservar; revisión que falla a medias.

## Entrega 2. S4T: caídas y páginas perdidas (Z2, Z8, Z11b, Z6)

`koroshi_s4t_envios` y después `koroshi_s4t_traspasos`. No llames a S4T para probar.
- Z2: 5xx y 429 se tratan como la red. **Decide Isaac** qué hacer con los envíos que ya estén atascados por esto
  (consulta de solo lectura para contarlos).
- Z8: caída y vuelta por «ha habido fallo y ninguna respuesta»; contadores también en real.
- Z11b: no leer todo el histórico en cada pasada.
- Z6: conciliar N días por parámetro y no apuntar la conciliación si falló algún GET; `try` en el `create` de reserva.
- Pruebas con `requests` simulado: 503, 429, lista, cuerpo no JSON, timeout.

## Entrega 3. Permisos dentro de los métodos (E1, E9, P11, M4, M15 bandeja)

Un módulo cada vez: `koroshi_impresion`, `koroshi_transportista`, `koroshi_juntar_cajas`, `koroshi_devoluciones`,
`koroshi_recepcion`, `koroshi_warehouse_map`, `koroshi_preparacion` (solo P11) y `koroshi_menu` (bandeja).
- La comprobación de grupo y de tarjeta va **dentro** del método que hace el trabajo, no solo en el controlador.
- Impresión: lista blanca de informes en `encolar` y grupo propio para `agente_*`. Ojo: el agente del portátil de
  Expediciones entra con el usuario de la PDA; no lo dejes fuera (di qué grupo hay que darle).
- Comprueba que las PDA siguen entrando: lista para cada módulo qué usuario y qué grupo lo usan hoy.

## Entrega 4. koroshi_contenedores 1.17 antes de instalarla (F1, F2, F4, F11, F7)

Está «en curso», sin etiqueta, y la escribe otro chat: **no la toques sin que Isaac te la pase**. Si te la pasa:
F1 (los cuatro puntos del §3.2), F2 (FALTANTE como destino de `/mover`), F4 («Poner a cero» con lecturas sin
validar), F11 (bloqueo por caja) y F7 (resumen de «Retirar cajas a 0» filtrado en SQL).

## Entrega 5. koroshi_transportista y koroshi_impresion: no duplicar ni perder etiquetas (E2, E4, E5, E6, E12, E7, E8, E14)

No llames a GLS ni a XPO para probar.
- E2: marca de «intento XPO en curso» por OUT con commit propio. Sin campo nuevo en `stock.picking`: tabla propia.
- E4 y E6: no enviar ni recuperar si las cajas no cuadran; mandar a la oficina.
- E5: adjuntos por id mayor que el máximo previo, no por hora. E12: quitar el dominio con punto y no rehacer
  `estado()` entero en cada lectura.
- E7 (agente, `bin/agente_impresion`), E8 (caducar y no duplicar la cola) y E14 (PDF al encolar). El agente lleva su
  propia versión y hay que reinstalarlo en el portátil: dilo en el cierre.

## Entrega 6. koroshi_preparacion y koroshi_operarios (P1 a P15)

Esfuerzo high: toca validación y cajas. Operarios antes que preparación si cambian los dos.
- P4: `FOR NO KEY UPDATE NOWAIT`. Es una línea, pero cambia quién espera a quién: explica en el cierre qué casos
  siguen dando «ocupada».
- P1: **decide Isaac** antes de programar (hacer `commit` por OUT cambia el todo o nada de la agrupación). Propón el
  diseño con sus casos de fallo y espera.
- P3, P5, P6, P12, P13: a dos, caja automática, cambio de hueco y refresco viejo.
- P2, P7, P8, P9, P10: lentitud. P14: medianoche local (cópialo de `tuctuc_operarios/models/reparto.py:49-51`).
- P15: crea `koroshi_operarios/tests/` con cola, pausa, a dos y cierre por inactividad.

## Entrega 7. koroshi_zonas y koroshi_agrupaciones_web (Z3, Z4, Z9, Z12, Z13, Z14, Z5, Z11a)

No instalar zonas el mismo día antes de las 04:50 sin avisar.
- Z3 y Z4 juntos: hora límite, `en_cola` para todas y un solo reintento desde el vigilante.
- Z13: `noupdate` en los crons (también en `koroshi_s4t_pedidos`) y validar `rendimiento` e `iter_equilibrio`. Di qué
  pasa con los crons ya creados en el servidor al añadir `noupdate` (no se reescriben: comprobarlo).
- Z5: **decide Isaac** si las web completas que esperan más de 3 días se siguen agrupando.

## Entrega 8. koroshi_monitor, koroshi_menu, koroshi_kpi, koroshi_informe, koroshi_warehouse_map (M1 a M15)

- M1 y M2 juntos: una caché que sirva a los 16 workers y un solo recorrido de tareas por petición. Mide antes y
  después con el nº de consultas por llamada (el log de Odoo lo da).
- M5 y M6 (pantalla), M7 y M8 (bultos: **decide Isaac** cuál es la cifra buena del camión), M3, M9 a M15.

## Entrega 9. Recepción, devoluciones, recuentos, prenda en el suelo y faltantes (E3, E10, E11, E13, E15, E16, E17, E18, F3, F5, F6, F8, F9, F10, F12 a F15)

Empieza por E3 (tanda duplicada de devoluciones) y F3 (reubicar repetido): mueven stock.

## Entrega 10. koroshi_base, koroshi_caja_existente y lo común (H1 a H6, M12, y las copias de E18, P15, F15)

- H1 primero y solo: una consulta agrupada en `_koroshi_corregir_bultos`. Con los índices de la entrega 0, propone
  aparte el índice si hace falta.
- H2: los `<function>` a `migrations/` o con guarda. H3: `'installable': False` en `koroshi_delegacion`.
- Una sola versión de `koroshi_base` con todo lo común (función del tipo de pedido de M12, prefijos, expresiones de
  lineal, modelo/color/talla de F15). Pasar los módulos a usarla uno a uno, cada uno con su versión.

## Entrega 11. Herramientas de `bin/` (H7 a H12)

Sin módulos. H7 (E11: sintaxis del Python del servidor), H11 (marca «en curso» y validar antes de `git tag`), H8 y
H10 (que `desplegar.sh` pare en horario o con campos nuevos, salvo variable explícita), H9 y H12.

## Entrega 12. Módulos `tuctuc_*` (T1 a T6)

Son de otra empresa y otro servidor (odoo.tuctuc.com), en la rama `feat/tuctuc-pda`, sin instalar. **Pregunta a Isaac
si los lleva este chat o el suyo.** Si son tuyos: T1 y T2 antes de cualquier instalación, T3 (crons apagados y con
`noupdate`) y T4 (acabar de adaptar `tuctuc_preparacion` y commitearlo).

## Lo que no hay que hacer

- No arregles nada del apartado 10 del informe («miré y está bien»).
- No cambies `stock_picking_date`, `product_multi_barcode` ni ningún módulo que no sea `koroshi_*`/`tuctuc_*`: si el
  fallo está allí, se arregla desde un módulo propio o se apunta.
- No juntes entregas para ir más rápido.
