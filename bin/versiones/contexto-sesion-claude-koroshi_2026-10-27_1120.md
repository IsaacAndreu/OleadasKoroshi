# Contexto para seguir con KOROSHI (sesión 26-27/10/2026)

Pásale esto a otro Claude para que siga donde lo dejamos. No lleva contraseñas.

## 1. Quién y dónde

- **Usuario:** Isaac (IT de NATH). Explicaciones en **catalán** (o castellano si escribe en castellano). Código y comentarios en **castellano**.
- **Repo:** `C:\dev\OleadasKoroshi` (GitHub `IsaacAndreu/OleadasKoroshi`, privado, rama `main`).
  - Último push: `9f7222f`.
  - Lo hecho después del push no está commiteado (ver punto 7).
- **Odoo principal:** nath.tuctuc.com (BD `NATH_PRODUCTION`, Odoo 13 EE).
  - Empresa KOROSHI = Effective Logistics, `company_id = 8`.
  - Servicio `nath-erp`, addons en `/opt/nath-erp/nath/enterprise-addons`.
- **Odoo de Oriola:** odoo.tuctuc.com (BD `TUCTUC_PRODUCTION`).
- **Cómo trabajo con Odoo:** JSON-RPC desde la pestaña del navegador (`/web/dataset/call_kw`) con contexto `allowed_company_ids: [8]`.
  - Acción de pruebas: **ir.actions.server 1837** (modelo stock.picking). Ahora está vacía: `raise Warning('Accion de pruebas vacia')`.

## 2. Reglas de trabajo (obligatorias)

- **Odoo 13 safe_eval:**
  - Sin f-strings, sin import, sin comprensiones de listas y sin lambdas que capturen variables (dan error `LOAD_DEREF`).
  - `log(...)` siempre ANTES de `raise Warning(...)`.
- **Toda acción que escriba:** primero versión **DIAGNÓSTICO** en la 1837; a REAL solo cuando Isaac lo diga.
  - **Al pasar de REAL a DIAGNOSTICO, cambiar la línea `^MODO = ` con regex anclada y comprobarla antes de ejecutar.**
  - El 27/10 un `replace` tocó un comentario y una "prueba" corrió en REAL. Creó la 2ª ronda Z-2710-R2 sin permiso; Isaac la aceptó.
- **Versiones:**
  - Nunca sobrescribir.
  - Cada versión nueva va a `bin/` con fecha y hora en el nombre (`..._2026-10-27_HHMM_vX-descripcion...`).
  - Las páginas y documentos van a `bin/versiones/`.
- **Prohibido:**
  - Mostrar o escribir contraseñas (poner ***).
  - Pulsar **"Forzar disponibilidad"**.
  - Borrar datos.
  - Tocar el AutoUpdater ni la versión del programa de escritorio (0.8.0.9).
  - Ejecutar el programa compilado (escribe en BD de producción).
- **Push:** solo cuando Isaac lo pida. Commits con `git -c user.name="Isaac Andreu" -c user.email="isaacandreu76@gmail.com"` y la línea `Co-Authored-By: Claude ...`.
- **Fuera del repo:** antes de instalar algo o tocar archivos fuera del repo, preguntar.
- **Alcance:** solo KOROSHI. No tocar crons ni acciones de otros.
- **Instalar módulos:**
  1. Isaac ejecuta en el servidor el `.sh` de `bin/` (primero sin `INSTALAR=1`, solo comprueba; después `sudo INSTALAR=1 bash ...`). Reinicia Odoo: las PDA ~1 min sin conexión, mejor a la hora de comer.
  2. Después yo pulso Actualizar (`button_immediate_upgrade` del módulo) y compruebo.
  3. Hay que recargar la página (F5) para ver el JS nuevo.

## 3. Picking por zonas: acción "Partir OUT zonas"

- **Qué hace:** parte cada OUT de tienda ("PED. TIENDAS") en una OUT por zona.
  - Crea agrupaciones `Z-ddmm-D1..`, `ZX` (fuera de lineal) y, si ya hay de ese día, `Z-ddmm-R2-...`.
  - La nota de cada OUT: `Z-ddmm-D3 | CAJA 05 | K34 ... | PEDIDO S-...`.
  - Cada unidad tiene su sububicación `KO_/TT_`; el "hueco" es la ubicación padre. El lineal sale del nombre (`L94`).
  - Modo prueba sin escribir: contexto `prueba_agrupacion='Z-2710-'`.
- **Versiones** (repo `odoo/`, copias con fecha en `bin/`):
  - **v8** `KOROSHI_partir_OUT_zonas_v8.py`: 8 zonas, una sola tanda, orden por **número de tienda** (K1, K2...; antes por prioridad 48h).
  - **v9** `KOROSHI_partir_OUT_zonas_v9.py`, en Odoo **acción 1866**, en DIAGNÓSTICO:
    - La ZX se reparte en trozos (ZX1, ZX2...) entre las personas que acaban antes. Antes la hacía una sola persona y el 27/10 dejó fuera 22 pedidos.
    - Recalcula los contadores de las OUT al partir.
    - **v9c**: nunca coge un pedido de **menos de 15 uds reservadas** (`MIN_UDS_PEDIDO = 15`).
  - **v10** `KOROSHI_partir_OUT_zonas_v10.py`, solo en el repo, en DIAGNÓSTICO. Es la recomendada:
    - Pedidos pequeños enteros (`ENTERA_MENOS_DE`, agrupaciones T1, T2...).
    - Menos zonas (`ZONAS`).
    - Ningún trozo de tienda < 15 uds (`MIN_UDS_OUT`, se junta con la zona de al lado).
    - `FACTOR_ENTERO = 1.25`.
    - **AUTO**: prueba ZONAS 2-8 × ENTERA [0, 25, 35, 50, 75, todo] y elige la que mete más pedidos antes de HORA_FIN y hace menos cajas.
    - **v10b**: también `MIN_UDS_PEDIDO = 15`.
    - Con el 27/10 (1.700 uds, 8 personas) elige **tradicional**: 46-50 cajas de 34 uds en vez de 390 de 4,9.
    - **Pendiente:** el ritmo del modelo (52 s/lectura, 21 s/lineal, calibrado 22/10) es optimista. El 27/10 fue a 70 s/ud por los "picos". Calibrar con días reales.
- **Crons de las 03:00:**
  - Cron 200 (partir en REAL) y cron 201 (correo con mapa y líneas a isaac.andreu@nath.es) eran de **un solo uso** (27/10) y ya están inactivos.
  - **Para mañana no hay nada programado.**
  - Propuesta pendiente de que Isaac diga sí: programar la v10b a las 03:00 en DIAGNÓSTICO, revisarla a las 7:30 y pasarla a REAL si cuadra.
- **Conclusiones con datos:**
  - Uds por caja vs velocidad: 22/10 11,6 uds/OUT → 48 s/ud; 27/10 R1 4,0 → 70 s/ud; R2 2,6 → 115 s/ud. **Los "picos" (cajas pequeñas) frenan mucho.**
  - Con cajas normales, todos los métodos van a ~48 s/ud. El tiempo se va en la ubicación (~38 s: PDA, buscar), no andando.
  - Siguiente mejora posible: menos pasos de PDA por prenda.

## 4. Monitor picking (módulo `odoo/modulos/koroshi_monitor`)

- **Menú:** Inventario › Monitor picking (acción cliente 1846, menú 1199). Ruta de datos `/koroshi_monitor/datos`.
- **Instalada: v1.12.**
  - R1 y R2 en pantallas separadas: "Z-2710 R1" y "Z-2710-R2".
  - Todo el ancho, sin arrastrar; zonas en orden.
  - Matriz tienda × zona con casillas compactas "leído/total".
  - Colores de la casilla: verde = OUT hecha (validada o con todo lo disponible cogido); naranja = cogiéndose; gris claro = sin empezar.
  - Colores de la fila: **gris** = la tienda tiene todas las OUT hechas (a juntar); **azul oscuro** = todas sus OUT con `carrier_tracking_ref` (etiqueta XPO), terminada.
  - Leyenda, lista "Tiendas listas para juntar".
  - **Clic en una casilla abre la OUT dentro de Odoo** (Ctrl+clic: pestaña nueva).
- **Preparada, NO instalada: v1.13.** La miga de pan dice "Monitor picking" (ahora sale sin nombre). Script: `bin/actualizar_koroshi_monitor_v1.13_2026-10-27_1113_nombre-en-migas.sh`.
- **Probar cambios del JS sin instalar:** página de prueba con stubs de `odoo.define` y datos inventados.
  - Plantilla en el scratchpad `monitor_test/index.html`.
  - Se sirve con `python -m http.server` vía `.claude/launch.json` en la carpeta temporal `.prova_monitor`. Borrarla después.

## 5. Otras cosas de estos dos días

- **Etiqueta de zona** (informe 1842, vista QWeb **6035**, `odoo/KOROSHI_report_etiqueta_zona.xml`):
  - **v16**: la matrícula ya no salta de hoja.
  - **v17** (activa): OUT grande, código 22 mm al 95 %, texto 20 pt; matrícula 50 mm con zonas / 62 mm sin zonas.
  - Comprobado con 21 etiquetas: 1 hoja cada una.
  - Para probar: `rep.render_qweb_pdf([id])` y contar `/Type /Page`. Con muestras de ~20; 250 de golpe tarda demasiado.
- **Juntar cajas:** pestaña en el pedido, vista **6036**, acción 1844. Se quitó la ventana de confirmación: un solo clic. Copia: `bin/KOROSHI_vista_pedido_juntar_cajas_2026-10-27_1042_v2-sin-confirmacion.xml`.
- **Contadores de las OUT** (`count_demand / count_reserve / count_done`, módulo stock_picking_date):
  - Son campos guardados que no se recalculan. Las OUT partidas heredaban los del pedido entero (~600 uds por agrupación).
  - Corregidos el 27/10 con `odoo/KOROSHI_recalcular_contadores_OUT.py`; la v9 ya los recalcula al partir.
- **"Indefinido"** en Transferencias agrupado por batch = OUT sin agrupación (web W-... o pedidos que no entran). No es un error.
- **Regla INT "solo lo pedido":** base.automation 19, solo avisa (`BLOQUEAR = False`).
- **Comprobar bultos:** acción 1858.
- **Monitor de Oriola:** instalado en odoo.tuctuc.com.
- **Módulo `koroshi_delegacion`:** hecho, **no instalado**.
- **Sync S4T:** cron 186. Los backorders cancelados bloquean la sincronización (hay que borrarlos; lo hace Isaac a mano).
- **27/10:** 50 pedidos (1.707 uds). R1 = 28 (K1-K58) y R2 = 22 (K59-K86), ningún pedido en las dos rondas.
- **Faltas:** la K22 tenía 20 sin coger (16 sin stock). La OUT 21571 ya la arregló Isaac.

## 6. Ideas habladas y aparcadas

- Pantalla PDA para quitar prendas de una caja: caso puntual, aparcado.
- Lectura de cajas al palet o un "check" para no olvidar cajas de zona: a Isaac no le convence. El problema es físico; con menos cajas por tienda (v10) debería bajar.
- Plano de zonas diario dentro del módulo, sin API, gratis: propuesto, no hecho.
- App de Lluís (10 pedidos a una persona, B-10): acción `KOROSHI_crear_agrupaciones_OUT.py` en DIAGNÓSTICO, no pasar a REAL.

## 7. Pendiente ahora mismo

1. **Sin commitear desde el push `9f7222f`:**
   - v9c y v10b (mínimo 15 uds por pedido);
   - etiqueta v17;
   - monitor v1.10 a v1.13;
   - vista de juntar v2;
   - scripts `.sh` v1.10 a v1.13;
   - este documento.
2. Decidir si mañana se programa la v10b (DIAGNÓSTICO a las 03:00, revisión a las 7:30).
3. Instalar el monitor v1.13 cuando se pueda reiniciar.
4. Calibrar el ritmo de la v10 con días reales.
