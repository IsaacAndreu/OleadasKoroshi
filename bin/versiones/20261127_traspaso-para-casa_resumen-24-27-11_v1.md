# Traspaso para seguir desde casa: qué se ha hecho del 24 al 27/11/2026 (v1, 27/11 tarde)

Resumen de la sesión «Soporte» y de las sesiones que ha coordinado. El estado de cada módulo está en
[TABLERO.md](../../TABLERO.md); las reglas, en [CLAUDE.md](../../CLAUDE.md). Este documento dice qué ha pasado, qué
está a medias y por dónde seguir.

## 1. Instalado en producción (nath.tuctuc.com), todo con el sí de Isaac

| Fecha | Módulo y versión | Qué hace |
|---|---|---|
| 24/11 15:38-15:42 | Tanda A y B del plan de instalación (base 1.2.1, faltantes 1.10.0, contenedores 1.15.0…; retener_tiendas 1.3.0) | Correcciones de la revisión general; retener pedidos de tienda duplicados o cancelados en S4T |
| 25/11 | koroshi_juntar_cajas 1.1.0, koroshi_impresion 1.0.0 | Juntar CJ desde la PDA y «Revisar caja»; pantalla Transportista e impresión en Expediciones |
| 26/11 ~14:11 | contenedores 1.16.0, operarios 2.25.0, preparacion 3.38.0 (y otros, un solo desplegar.sh) | Retirar cajas a 0; soltar un pedido desde la PDA; partir una OUT grande |
| 26/11 ~15:45 | koroshi_zonas 1.9.0 | Zonas en real |
| 27/11 ~09:32 | koroshi_monitor 1.47.0 + koroshi_preparacion 3.38.1 | Correo GLS sin el tope de 5 etiquetas; aviso «OUT ocupada (otra PDA o la oficina)» en vez de «Otra PDA está guardando» |
| 27/11 ~12:00 | koroshi_monitor 1.48.0 (sesión Monitor) | Correo GLS de tiendas solo con «Cajas preparadas» (lo pidió Erika) |
| 27/11 ~12:02 | koroshi_transportista 1.8.0 | Botón «Recuperar etiqueta GLS» cuando GLS contesta -70 |

**Falta probar en la PDA:** el botón «Recuperar etiqueta GLS» con K85 (OUT/28318, CJ665014668) y K10 (OUT/28327,
28355 y 28356). Sus etiquetas ya se recuperaron a mano (expediciones GLS 1386256033 y 1386233314), pero las OUT aún no
tienen el número de seguimiento hasta que se pulse «Recuperar» desde la PDA.

## 2. Hecho y SIN instalar (esperan el sí de Isaac)

- **koroshi_agrupaciones_web 1.2.0**: como mucho 180 pedidos por corte y un solo corte a las 06:00 (lo pidió KOROSHI el
  27/11). Datos: un día normal entran unos 100–110 pedidos web (entre 85 y 125); de 1 a 4 al día llegan reservados
  pero sin la prenda en el hueco.
- **Diseño v2 de agrupaciones web** (`bin/versiones/20261127_diseno-web-faltante-cancelar-entero_v2.md`): si en un
  pedido web se marca faltante, se cancela el pedido entero y las prendas ya cogidas van a una ubicación nueva
  EFFEC/REUBICAR. Espera visto bueno.
- **koroshi_contenedores 1.17 (Compactar fase 1)**: en curso en otra sesión; se sube en este commit tal cual está
  (sin etiqueta ni ZIP). No instalar hasta que esa sesión la cierre.
- Otros «hecho sin instalar» de días anteriores: ver la tabla del TABLERO (informe 1.3.0, s4t_pedidos 1.2.0,
  devoluciones 1.3.0, prenda_suelo 1.1.0, recuentos 1.2.0…).

## 3. Incidencias del 27/11 y cómo quedaron

- **«Otra PDA está guardando» (K74/K75)**: no era otra PDA. Era «Comprobar disponibilidad» masiva desde la oficina
  (Almacen 2), que bloqueó 6 OUT durante 7 minutos. Se cambió el mensaje (preparacion 3.38.1).
- **Correo GLS «Etiquetas GLS» y «Cajas preparadas»**: el tope de 5 etiquetas se ha quitado (monitor 1.47.0). Después,
  la 1.48.0 deja solo «Cajas preparadas».
- **Etiqueta GLS con error -70 (K85 y K10)**: GLS ya tenía la expedición creada. Se recuperó el PDF y se hizo el botón
  (transportista 1.8.0).
- **CJ665014661 dentro de CJ665014527**: juntadas (1 calcetín).
- **Pedidos triplicados del 24/11 (K7 4724 y K1 4722)**: S4T los rechazaba con «KO: None». Con la llamada hecha a
  mano desde el servidor se vio el mensaje real: *«La orden de servicio … no existe o no tiene líneas pendientes»*, es
  decir, el sistema de KOROSHI los tenía cerrados. KOROSHI los reabrió y **a las 16:29 se subieron solos (READY,
  71 y 51 líneas)**. La acción 1960 todavía tiene esos dos pedidos en la lista: **no lanzarla** (saldrían «already
  READY»); antes de volver a usarla, cambiar la lista.
  - Lección: el módulo de Effective solo guarda el campo «detail»; si S4T contesta con «message», en Odoo sale
    «KO: None». Para saber el motivo, repetir la llamada mostrando la respuesta entera (sin imprimir la clave).
- **Correo de S4T**: piden que se envíe «como siempre» y **con Efrén en copia**.

## 4. Faltantes: pendientes a mano

Patrón: un mismo operario marca faltante en huecos que sí tienen la prenda. Las uds pasan a EFFEC/FALTANTE, S4T las sigue
viendo como disponibles, Odoo no las puede reservar y el corte web cancela el pedido (caso 59610, cancelado dos veces).

- **2525ML05-000039-10 (5 uds)**: Isaac las encontró en L52 P19 C1. **Devueltas al stock el 27/11** (faltante de la
  OUT/25316-2 «Encontrado»). Para hacerlo se validó solo esa línea de la ronda INT/67387; las otras 125 líneas pasaron
  a la **INT/67411**, que sigue abierta. La OUT/28509 de Zalando espera 2 uds de esa referencia: no tocarla.
- **Por mirar en el almacén**: 2521SU08-000003-XL (L31 P29 C1, 1 ud), 2621PT29-000302-32 (3), 2621ML07-000015-M (2),
  2622SU02-000014-M (2). Ofrecido: sacar la lista de todos los faltantes pendientes de ese operario.
- **Escrito para el operario**: el borrador está en el chat de Soporte, no en el repo (el repo es público). Antes de
  entregarlo, completarlo con la lista de sus faltantes y pasarlo por la gestoría.
- **K48 al 57 %**: 141 uds canceladas, 127 de ellas en SKU con faltante; faltante global 1,49 %.

## 5. Compactación en odoo.tuctuc.com (análisis, nada instalado)

Documentos: `bin/versiones/20261127_compactacion-en-tuctuc-analisis_v1.md`, `_v2.md` y **`_v3.md` (la buena)**.

- tuctuc tiene en Oriola-Amposta una nave **N1 hecha como NAU-2**: huecos «L01 P18 C1» (189 lineales) y cajas con
  etiqueta dentro (TT_, MI_, UB_, KO_). Unas 62.000 cajas con stock.
- La misma nave está **repetida en tres empresas** (WH-OR compañía 1, MODAI compañía 23, UBRAN compañía 21): cada hueco
  existe 2-3 veces con el mismo código de barras. Allí la compañía 8 es E-LEARNING (no se puede dejar la 8 fija).
- Sin valoración en tiempo real (no hay asientos de stock). Ya tiene hr, stock_barcode y queue_job.
- Unas 20.000 cajas cuelgan de la nave sin hueco. La NAVE2 usa otro formato de hueco (`N2|S|pasillo|lado|X|Y`), muchos
  sin código de barras.
- Plan: «perfil de almacén» en koroshi_contenedores; 3-4 semanas; empezar cuando la 1.17 esté probada en NAU-2.
- **Preguntas para Isaac**: ¿Oriola N1 con las tres empresas juntas? ¿Qué son las cajas sin hueco? ¿También la NAVE2?
  (y el resto del apartado de preguntas de la v3).

## 6. Otros temas abiertos

- **About You**: no hay procedimiento escrito; Isaac no lo ha pasado aún. Se trata como Zalando (no cancelar ni
  enviar a mano).
- **Inversa de verano**: propuesta para «la guía» en `bin/versiones/propuesta-inversa-verano-guia_2026-11-27_1358.md`.
- **K46 4634 / CJ665013084**: Isaac iba a mirar si la caja está físicamente.
- **Correos**: 5.379 correos en cola y fallos a una dirección que no existe («Has sido asignado»); sin tocar.
- **Migración GCP → OVH**: decidida el 26/11 (KOROSHI primero, PG 11, corte en fin de semana); ver
  `bin/versiones/estudio-migracion-servidores_2026-11-26.md`.

## 7. Qué NO se ha subido a GitHub y por qué

- `App.config`, `PedidosMultiples/ConnectionSQL.cs`, `PedidosMultiples/InitialForm.cs`: tienen credenciales
  (CLAUDE.md: no añadir ni mover). Los cambios siguen solo en el PC del almacén.
- `Properties/AssemblyInfo.cs`: alguien cambió la versión del programa de escritorio de 0.8.0.9 a 0.8.1.0, y esa
  versión no se toca sin Isaac. Sigue solo en local.
- `bin/*.tar.gz` (paquetes de tuctuc del 24-25/11) y `redistribucion/compactacion-zona0_*.xlsx` (salidas del programa,
  2,9 MB): binarios o resultados generados; se quedan en el disco.

## 8. Cómo seguir desde casa

1. `git pull` en `main`.
2. Leer `TABLERO.md` y este documento.
3. Ojo: `TRASPASO_AUDITORIA.md` está en `.gitignore` (no viaja). Y el repo de GitHub sale **público**, aunque el
   `.gitignore` dice «repo privado»; hay credenciales antiguas en la historia (pendiente de rotar).
4. Nada se instala ni se reinicia en el servidor sin el sí de Isaac; un módulo, una sesión.
