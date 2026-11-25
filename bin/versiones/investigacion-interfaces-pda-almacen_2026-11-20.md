# Investigación: cómo se diseñan las pantallas de PDA en almacén

Fecha: 20/11/2026. Para: pantallas PDA de KOROSHI (Odoo 13, Zebra con lector integrado, operarios con guantes y prisa).
Solo investigación: no se ha tocado código ni servidor.

**Aviso sobre las fuentes.** Hay mucha documentación de fabricantes (Zebra, Microsoft, Infor, Odoo, SAP) y poca
investigación seria con medidas. No he encontrado una guía de diseño pública de Honeywell ni documentación de pantallas
de Manhattan: de esos dos solo hay folletos comerciales. Donde una idea sale de una sola fuente o de un caso aislado,
lo digo.

---

## 1. Buenas prácticas para terminales de mano

### Tamaño de botones y texto
- Google (Android/Material) pide como mínimo **48 × 48 dp** por botón, que en la mano son unos **9 mm**, con **8 dp** de
  separación. La zona que se puede pulsar puede ser mayor que el dibujo del botón.
  <https://support.google.com/accessibility/android/answer/7101858> ·
  <https://material.io/design/layout/applying-density.html>
- Con guantes ese mínimo se queda corto. Zebra, en su biblioteca de componentes para almacén, hizo el botón principal
  («Confirmar») **el doble de grande** que el resto, pensando en guantes, lluvia y sol.
  <https://medium.com/zebra-design/creating-the-zebra-technologies-component-library-a3c70b231d40>
  (no se pudo abrir el artículo entero; el dato sale del extracto del buscador).
- Las Zebra recientes tienen un **modo guante** en la pantalla táctil (Ajustes > Pantalla > Modo panel táctil:
  «Guante y dedo»). Es un ajuste del aparato, no de la aplicación.
  <https://docs.zebra.com/us/en/mobile-computers/handheld/em45-series/em45-ug/c-em45-settings/display/t-em45-setting-touch-panel-mode.html>
- La app de almacén de Microsoft (Dynamics 365) deja a cada operario subir el **texto hasta el 400 %** y los **botones
  hasta el 200 %**, y elegir en qué esquina va el botón principal (diestros/zurdos). Es el ejemplo más completo que
  he encontrado de una app de almacén pensada para guantes.
  <https://learn.microsoft.com/en-us/dynamics365/supply-chain/warehousing/warehouse-app-user-settings>

### Contraste
- La regla general de accesibilidad (WCAG) pide texto con contraste mínimo 4,5 a 1 con el fondo; en almacén (pantalla
  sucia, reflejos, poca luz en pasillos) conviene ir bastante por encima.
  <https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html>
- Microsoft ofrece un tema de **alto contraste** y temas de color por operario: así se ve de lejos quién tiene la
  sesión abierta cuando varias personas comparten aparato.
  <https://learn.microsoft.com/en-us/dynamics365/supply-chain/warehousing/warehouse-app-accessibility>

### Un paso por pantalla y pocas opciones
- Zebra (consejos para apps de almacén sobre SAP): enseñar **solo lo que el operario necesita**, menos pantallas, menos
  toques, y que un operario nuevo pueda trabajar el primer día.
  <https://www.zebra.com/ap/en/blog/posts/2024/sap-mobile-advisor-why-you-must-put-workers-mobile-experiences-first-when-modernizing-warehouse.html>
- RF-SMART: el sistema debe ir guiando paso a paso para que el operario no tenga que recordar procedimientos ni
  navegar menús. <https://www.rfsmart.com/netsuite/wms/ease-of-use>
- Ivanti (pantallas RF de SAP EWM): las pantallas pensadas para PC obligan a ampliar y desplazar en la PDA, y eso
  frena y provoca errores; su arreglo fue quitar opciones y sacar el teclado justo cuando hace falta.
  <https://www.ivanti.com/blog/optimizing-sap-ewm-with-ux-on-the-edge>
- Caso de rediseño de pantalla RF: el mejor diseño es el que obliga a **mirar menos la pantalla**: el dato clave
  (ubicación, cantidad) en grande. Es un caso único, tomarlo como orientación.
  <https://medium.com/@Isaacfade/revitalizing-warehouse-operations-a-strategic-redesign-of-the-rf-scanner-interface-427cf2f10fc9>

### Confirmación por sonido y vibración
- No fiarse solo del sonido: hay ruido y gente con cascos. Scandit recomienda **tres señales a la vez**: color, sonido
  y vibración. <https://www.scandit.com/blog/scanning-at-scale-ux-insights/>
- El sonido de **acierto y el de error deben ser distintos**. En un foro de usuarios de IFS se quejaban justo de que el
  pitido era el mismo para lectura buena y mala.
  <https://community.ifs.com/warehouse-data-collection-wadaco-252/wadaco-different-beep-for-bad-scan-6731>
- Microsoft separa tres sonidos (acierto, «vuelve a leer», error) y deja regular volumen y vibración por operario.
  <https://learn.microsoft.com/en-us/dynamics365/supply-chain/warehousing/warehouse-app-user-settings>
- CartonCloud añadió sonido y vibración de error además del mensaje en pantalla.
  <https://www.cartoncloud.com/blog/error-notification-vibration-and-sound-for-android>
- Caso Nordstrom: añadir vibración al acierto se notó más que el aviso solo visual.
  <https://medium.com/@sabrinaweschler/designing-a-scanning-experience-for-nordstrom-onefill-part-1-4a1e2f20c2d7>
- Tesis (Utrecht) sobre sonido en WMS: el sonido suele quedarse en un pitido y está poco pensado.
  <https://studenttheses.uu.nl/handle/20.500.12932/46062>

### Leer en vez de teclear
- Todas las fuentes coinciden: el código se lee con el lector, el teclado es el último recurso. Microsoft incluso
  permite **apagar el lector mientras la app está ocupada** para que una lectura no se pierda ni se cuele en otro
  campo. <https://learn.microsoft.com/en-us/dynamics365/supply-chain/warehousing/warehouse-app-user-settings>
- Infor configura cada dato como «solo mostrar» o «hay que leerlo para confirmar» (por ejemplo, la ubicación de
  origen). Así se obliga a leer donde importa y se ahorra donde no.
  <https://docs.infor.com/wms/2022.x/en-us/useradminlib/scepickug/bfy1612893563711.html>

### Errores grandes y claros
- Microsoft muestra los errores con una ilustración grande y su sonido propio; Mecalux rediseñó sus mensajes de
  terminal con iconos. <https://www.mecalux.com/software/updates/new-ux-messaging-rf-terminals>
- Idea común: el error debe decir **qué ha pasado y qué hacer ahora** («Esta prenda no es de este pedido. Déjala
  aparte y lee la siguiente»), y no desaparecer solo antes de que el operario lo haya visto.

---

## 2. Cómo lo hacen los WMS conocidos

| Sistema | Menú de inicio | Entrada del operario | Ubicar | Vuelta al menú |
|---|---|---|---|---|
| **SAP EWM (RF)** | Menú por tareas que se define en el «gestor de menús RF»; cada usuario ve su menú según su perfil. | El usuario entra y elige su «recurso» (aparato/puesto); hay entrada automática por usuario y almacén. | Tareas guiadas: el sistema dice de dónde a dónde y el operario confirma leyendo. | Tecla o botón de volver; el sistema ofrece la siguiente tarea. |
| **Infor WMS** | Menú principal → «Picking», etc.; se puede indicar la **zona** para recibir solo tareas de esa zona. | Usuario RF. | Lee ubicación y matrícula; cada dato es «mostrar» o «confirmar leyendo». | **Esc vuelve siempre al menú principal**; Enter guarda y pasa a la siguiente pantalla. Se puede saltar la pantalla «siguiente tarea» para ir más rápido. |
| **Odoo Barcode (v15-17)** | Pantalla de lectura con botón **Operaciones** (tarjetas: Recepciones, Entregas…). | Usuario Odoo; las fichas (badge) de empleado existen en Asistencias y Fabricación. | Se lee el albarán o se elige; se lee producto, se ajusta cantidad y ubicación, y **Validar**. | Tras validar se vuelve a la lista. |
| **Mecalux Easy WMS** | Rediseño reciente: menú desplegable más sencillo, filtros en listas largas, iconos en los mensajes. | — (no documentado en abierto) | — | — |
| **Manhattan Active** | Solo folletos: app táctil «moderna» con tareas y juego/objetivos para el operario. Sin detalle de pantallas. | — | — | — |
| **Microsoft Dynamics 365** (no pedido, pero el mejor documentado) | Menú principal con tareas; ajustes por operario. | Usuario + tema de color por persona. | Pasos guiados uno a uno. | Botón grande, posición elegible. |

Fuentes:
- SAP EWM: <https://learning.sap.com/courses/processes-in-sap-s-4hana-ewm/outlining-the-radio-frequency-rf-framework> ·
  <https://help.sap.com/saphelp_ewm70/helpdata/en/4d/4fa477c9c20c7ae10000000a42189c/content.htm> ·
  <https://userapps.support.sap.com/sap/support/knowledge/en/3672406>
- Infor: <https://docs.infor.com/wms/2026.x/en-us/useradminlib/sceintroug/ezy1612893909424.html> ·
  <https://docs.infor.com/wms/2022.x/en-us/useradminlib/scepickug/bfy1612893563711.html>
- Odoo: <https://www.odoo.com/documentation/17.0/applications/inventory_and_mrp/barcode/operations/receipts_deliveries.html> ·
  <https://www.odoo.com/documentation/17.0/applications/hr/attendances/kiosks.html>
- Mecalux: <https://www.mecalux.com/software/updates/trf-new-visuals>
- Manhattan: <https://www.supplychainbrain.com/articles/23654-manhattan-associates-enhances-apps-for-distribution-warehouse-management>

**Lo que se repite en todos:**
1. **Menú por tareas**, corto, y a menudo filtrado por zona o por perfil del operario.
2. **El sistema guía**: dice qué toca y el operario confirma leyendo, no buscando en listas.
3. **Una tecla/botón fijo para volver al menú** (en Infor, Esc siempre lleva al menú principal).
4. **Al acabar una tarea, la siguiente** sin pasar por el menú, si el operario sigue en la misma área.

**Login con tarjeta:** en Odoo, la ficha del empleado tiene un campo «ID de credencial» (badge) que usa el quiosco de
Asistencias: se lee la tarjeta y entra; opcionalmente pide PIN. Fabricación (Shop Floor) también deja cambiar de
operario leyendo la ficha. En Odoo 13 esto existe en Asistencias, no en Inventario.

**Ubicar «lee artículo → lee ubicación»:** en Odoo estándar la ubicación de destino se elige en la línea o se lee
después del producto; en foros se pide justo este flujo y no hay respuesta oficial clara
(<https://www.odoo.com/forum/help-1/scan-product-then-scan-location-for-internal-transfer-2-step-receipts-internal-transfer-putaway-strategy-132690>).
Los WMS grandes lo hacen como tarea guiada: lee el artículo, el sistema **propone** ubicación, el operario va y **lee la
ubicación para confirmar**.

---

## 3. Patrones concretos

### 3.1 Leer la tarjeta del operario con el lector (DataWedge)
- **Modo teclado (keystroke):** el lector «teclea» el código en el campo que tenga el foco, y puede mandar **Enter**
  al final (por defecto Enter va como pulsación de tecla). Es lo que sirve para Odoo en el navegador.
  <https://techdocs.zebra.com/datawedge/latest/guide/output/keystroke/>
- **Modo intent:** el lector entrega el código a una **app Android** por programa, sin campo con foco. Un navegador
  web no lo recibe, así que **para Odoo 13 en Chrome no sirve** (salvo con una app propia o Enterprise Browser).
  <https://techdocs.zebra.com/datawedge/latest/guide/output/intent/>
- Odoo avisa de que en Zebra hay que marcar **«Send Characters as Events»** o Odoo no reconoce las lecturas.
  <https://www.odoo.com/documentation/17.0/applications/inventory_and_mrp/barcode/setup/device_troubleshooting.html>
- Si las lecturas llegan cortadas o desordenadas: subir el **retardo entre caracteres** de 100 en 100 ms (hasta 1000)
  o el retardo antes del Enter. Cuesta algo de velocidad.
- Consecuencias para el diseño (deducción mía, no de una fuente):
  - La pantalla debe **dejar siempre el foco en el campo de lectura** al cargar, después de cada lectura y después de
    cerrar un aviso; si el foco se pierde, la lectura «se escribe» en otro sitio o se pierde.
  - Mejor aún: **escuchar las teclas en toda la página** (como hace Odoo Barcode) y no depender de un campo concreto;
    el Enter marca el final del código.
  - Distinguir el tipo de código por su forma (prefijo de la tarjeta de operario, CJ para caja, ubicación, EAN de
    prenda) para que una lectura «equivocada» dé un error claro en vez de buscar en el sitio que no es.
  - La tarjeta del operario no debe ser una contraseña: es para decir **quién** es, no para entrar a Odoo.

### 3.2 Inicio por áreas con tiempo por tarea
- Infor y SAP filtran tareas por **zona** o perfil; Microsoft muestra al entrar un resumen de «tu trabajo de hoy».
  <https://learn.microsoft.com/en-us/dynamics365/supply-chain/warehousing/warehouse-app-user-settings>
- Patrón práctico: **cuadrícula de botones grandes** (2 columnas), uno por área, con un número grande de «pendiente»
  y, si hace falta, el tiempo o la hora de corte. El tiempo por tarea se registra **solo**, al entrar y salir del área,
  sin pedir nada al operario (si se le pide, no lo hará con prisa).
- Manhattan habla de objetivos y «juego» para motivar; con cuidado: en un almacén pequeño puede crear presión sin
  mejorar la calidad.

### 3.3 Botón «prenda encontrada, ¿a dónde va?»
- No he encontrado un nombre estándar, pero todos los WMS tienen un «consultar artículo»: lees el código y te dice
  dónde está o dónde debe ir. En SAP e Infor es una transacción de consulta en el menú.
- Patrón recomendado: **un botón fijo, visible desde cualquier pantalla**, que abre una pantalla de una sola lectura:
  «Lee la prenda» → respuesta en grande: **«VA A: pedido X / caja CJ… / ubicación Y»** o «Devolución: déjala en Z».
  Si no tiene destino, que lo diga claro y deje marcarla como «encontrada sin destino» para que la vea un jefe.

---

## 4. Recomendaciones para nuestras pantallas (por prioridad)

**Imprescindibles (afectan a errores y velocidad todos los días)**

1. **Foco siempre en la lectura.** En las cuatro pantallas, tras cargar, tras cada lectura y tras cerrar cualquier
   aviso, el foco vuelve al campo de lectura (o se escucha la lectura en toda la página). Revisar DataWedge en todas
   las PDA: salida teclado, Enter al final, «Send Characters as Events» marcado, mismo perfil en todas.
2. **Tres señales para cada lectura:** verde + sonido corto + vibración corta si va bien; rojo + sonido distinto y más
   largo + vibración larga si va mal. El mismo código de colores y sonidos en todas las pantallas.
3. **Errores que no se escapan:** mensaje a pantalla casi completa, frase corta de qué pasa y qué hacer, y que **solo
   se cierre leyendo otra vez o con un botón grande** (no a los 3 segundos). Nunca un aviso pequeño en una esquina.
4. **Botones grandes de verdad:** como mínimo unos 12-15 mm de alto con guantes (el mínimo de Google, 9 mm, es para
   dedo desnudo), separados entre sí, y el botón principal el doble de grande. Activar el modo guante de la pantalla
   en las Zebra que lo tengan.
5. **Un dato protagonista por pantalla**, en letra muy grande: en Lecturas, la ubicación y la cantidad que faltan; en
   Ubicar, la ubicación de destino; en Contenedores, la caja/contenedor activo.

**Inicio PDA (7 áreas)**

6. **Cuadrícula de 7 botones grandes** (2 columnas), con nombre corto, icono y un número grande de pendientes. Si una
   área no tiene trabajo, se ve apagada pero no desaparece (que el sitio de cada botón no cambie).
7. **Entrada con tarjeta:** leer la tarjeta del operario identifica quién trabaja (no sustituye a la contraseña de
   Odoo). Mostrar el nombre del operario arriba, siempre visible, con un color por persona si comparten PDA.
8. **Tiempo por área automático:** se cuenta al entrar y salir del área; nada que rellenar.

**Lecturas (picking)**

9. **Flujo fijo y guiado:** la pantalla dice qué toca («Ve a ubicación X, lee 3 de esta prenda») y el operario solo lee.
   Al acabar el pedido, pasar al siguiente sin volver al menú.
10. **Contador grande «faltan N»** y lectura de más o de otra prenda = error rojo que bloquea hasta confirmarlo.

**Contenedores**

11. **Primero leer el contenedor/caja, luego las prendas**, y tener siempre a la vista en qué contenedor se está
    metiendo. Cambiar de contenedor = leer el otro (no elegir de una lista).

**Ubicar devoluciones (lee artículo → lee ubicación)**

12. **Dos pasos, dos pantallas:** 1) «Lee la prenda» → aparece en grande la ubicación propuesta; 2) «Lee la
    ubicación» → si coincide, verde y vuelta al paso 1; si no, rojo con «Esta no es: va a X». Permitir otra ubicación
    solo con confirmación explícita.

**Generales**

13. **Botón fijo «¿Dónde va esta prenda?»** accesible desde todas las pantallas (ver 3.3).
14. **Botón fijo de volver al menú** en el mismo sitio en todas las pantallas, y que no se pierda trabajo al usarlo.
15. **Pocas opciones:** quitar de la PDA todo lo que no use el operario (menús de Odoo, listas, filtros). Lo raro va al
    PC del jefe.

Antes de aplicar nada: probar cada cambio en una PDA real con guantes, en el pasillo con más ruido y menos luz.
