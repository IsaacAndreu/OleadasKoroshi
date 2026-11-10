# Opción B: preparación en Lecturas. Plan v3: lo construido y lo que sigue (10/11/2026)

Sustituye como guía de trabajo a los planes v1 y v2 (`20261110_PLAN_preparacion_en_lecturas_v1.md` y `_v2.md`), que siguen
valiendo como estudio.

## Decisiones del usuario (10/11/2026)

- **Todo dentro de Lecturas**: leer, caja y **validar**, sin entrar ni salir de la app de código de barras.
- **Solo OUT sueltas** en la primera versión. Los lotes **Z-** siguen en la app de siempre.
- Un EAN que no es de la OUT, o de una línea completa, se **bloquea con aviso rojo** y no cuenta.
- **Caja**: botón «Caja», sale «Escanea la caja», se lee la **CJ** y se cierra. Luego se sigue con la siguiente.
- Se activa **por empleado (tarjeta)**: todas las PDA usan el mismo usuario. Lo prueban primero **Isaac e Isaac2**
  y después el jefe de almacén.
- Al completar una línea salta sola a la siguiente. Flechas **◀ ▶** para ver la línea de antes o la siguiente.
  **Foto** del producto, como en la app.
- En la PDA **no sale nada de productividad**.
- Fuera de alcance por ahora: instalar la v2.3 sola, sacar Departament IT del grupo 141 y el EAN 1/1 de Faltante.

## Lo que se ha comprobado en el servidor (solo lectura)

- La app actual (stock_barcode + stock_barcode_optimization de Brain Station) hace en el servidor solo tres cosas:
  guardar `qty_done`, llamar a `put_in_pack(package_name=CJ)` y llamar a `button_validate`. Los bultos, XPO, S4T y
  koroshi_caja_existente van en el servidor. Por eso la pantalla propia puede validar desde la primera versión.
- La foto es `/web/image/product.product/<id>/image_256`, la misma imagen del producto que enseña la app.
- Datos del diagnóstico (acción 1908, solo lectura):
  - el 96 % de las líneas son de 1 ud;
  - p90 de 84 líneas por OUT;
  - 29 de las 41 OUT asignadas estaban en un lote Z-;
  - no hay lotes, propietarios ni embalajes con barcode.

## Construido

| Versión | Qué |
|---|---|
| koroshi_operarios **v2.3.1** | Pantalla nueva de Lecturas (v2.3) sin contador del día, sin minutos y sin «productividad» en la PDA |
| koroshi_preparacion **v3.0.0** | Módulo nuevo: leer (+1 con bloqueo y sin pasarse), deshacer, Caja con CJ (`put_in_pack`), validar (validación de koroshi_faltantes), Faltante y vuelta, sin conexión con reintento sin contar dos veces, tabla de lecturas |
| koroshi_preparacion **v3.0.1** | Foto del producto, flechas ◀ ▶, tocar una línea para verla, salto automático a la siguiente |
| koroshi_preparacion **v3.0.2** | El punto del lector dice siempre «Lector preparado», porque no hace falta tocar el campo; se pone gris solo sin conexión |

Entregables en `bin/`:
- `20261110_koroshi_preparacion_v3.0.2.zip`
- `20261110_koroshi_operarios_v2.3.1.zip`
- `instalar_koroshi_preparacion_v3.0.2_2026-11-10.sh`

En `bin/versiones/`:
- la guía de prueba `20261110_PRUEBA_preparacion_v3.0.2.md`;
- la maqueta `20261110_MOCKUP_preparacion_en_lecturas_v3.0.2.html`.

Vuelta atrás: `koroshi_preparacion.activa` = `0`, y Lecturas abre la app de siempre sin reiniciar.

## Siguiente (v3.1), después de la prueba en la PDA

1. Lo que salga de la prueba con Isaac/Isaac2 y el jefe de almacén.
2. **Lotes Z-** recorriendo OUT a OUT (v3.4a del plan v2, unos 3-4 días). Antes hay que leer cómo guarda
   `barcode_batch_process` su estado de lectura (X14 del plan v2). Hasta entonces, no se escribe en OUT de un Z-.
3. Opcional: cerrar la caja leyendo directamente la CJ sin pulsar el botón (0 choques CJ/EAN en el diagnóstico).
4. Opcional: cantidad de golpe para líneas de muchas uds.
5. Comparar los bultos (`number_of_packages`), la etiqueta y XPO de OUT validadas en la pantalla nueva con OUT
   validadas en la app.
