# Compactación en Odoo por fases: diseño v6 (26/11/2026)

**Estado: DISEÑO v6 para Isaac. No hay código de la 1.17.0.** La v1 a la v5 se conservan tal cual.

La v6 recoge **cómo se hará de verdad**, por fases (Isaac dijo «de acuerdo, procede» el 26/11), y detalla la
**fase 1 (1.17.0)**. Todo lo que la v5 decía de la KO mixta y de «pasar prendas» pasa a la fase 2 y no se programa
ahora.

## 0. Las fases

| Fase | Qué | Versión | Estado |
|---|---|---|---|
| **0** | Retirar cajas a 0 (ronda por lineal y hueco, «Tiene prendas», «Revisar» negativos) | koroshi_contenedores 1.16.0 | **Instalada el 26/11.** Falta probarla en la PDA (L67 P16) y usarla una semana |
| **1** | Juntar cada modelo-color **moviendo cajas enteras** y decir qué caja va abajo o arriba | 1.17.0 | **Este diseño** |
| **2** | Fusionar cajas medio vacías del mismo modelo-color (pasar prendas, solo lo libre). Aquí entra la KO mixta, donde se gane espacio | 1.18.0 | Después de medir lo ganado con las fases 0 y 1 |
| **3** | Recolocar la nave: zona 0 cerca del muelle, palés girados (lado de 80 al pasillo), lineales por fases | — | Análisis en el programa de Windows, con medidas reales |

**Principios (no cambian en ninguna fase):**

1. Primero lo que más libera con menos riesgo: cajas a 0, después cajas enteras y por último prenda a prenda.
2. **Desde Contenedores nunca se toca la reserva de una OUT.** Mover una KO entera lleva sus prendas y sus reservas, y
   Lecturas lo ve (R7).
3. **Ninguna ubicación nueva en Odoo.** C1–C4 son columnas, que ya existen. La altura (abajo o arriba) es un dato de la
   KO, apuntado en una tabla propia del módulo.
4. Cada fase se mide antes de pasar a la siguiente. La copia diaria de las 19:00 da los números.

## 1. Datos fijos (Isaac, 26/11)

- **Hueco de Odoo = una columna** (L67 P16 C1). Una columna es medio palé: **8 cajas, 4 de alto × 2 de fondo**. Un
  palé son 2 columnas.
- **Caja = una KO.** La recepción sigue con una KO por caja (decisión 11).
- **Zona 0** = temporadas I27 y V27, de L44 a L136.
- **Abajo** = alturas 1–2, lo cómodo. **Arriba** = alturas 3–4.

**Con esto, la fase 1 no necesita litros.** Se cuentan cajas: una columna admite 8 KO. Los litros del MASTER solo hacen
falta en la fase 2, para saber si dos cajas medio vacías caben en una.

## 2. Fase 1 (1.17.0): reglas del plan

Odoo calcula el plan **por lineal, cuando se pide** («Calcular L67»), en vivo y con funciones sin Odoo en `logica.py`
probadas contra el programa:

1. **Qué se vacía:** las columnas de la zona 0 del lineal con **menos de 4 cajas** (menos de la mitad). No se vacía una
   columna que tenga algo de la zona Z.
2. **Adónde:** a otras columnas de la zona 0 del mismo lineal o de hasta 2 lineales más allá:
   - **sin pasar de 8 cajas** (parámetro `koroshi_contenedores.cajas_columna = 8`; ver decisión 15);
   - **nunca dos colores del mismo modelo** en una columna;
   - las cajas del mismo modelo-color de una columna van **juntas** al mismo destino. Mejor si ese destino ya tiene ese
     modelo-color;
   - los modelos-color de **más salida**, al destino más cercano al muelle (el lineal con el número más bajo); los de
     poca salida y los restos de talla, al más lejano.
3. **Una columna solo cuenta como vaciada si caben todas sus cajas.** Si no, no se toca.
4. **Orden:** primero las columnas que se vacían moviendo menos cajas.
5. **Abajo o arriba**, para cada caja que se mueve:
   - se ordenan las tallas del modelo-color por sus líneas de salida de 28 días;
   - las más pedidas, hasta más o menos la mitad de las uds del modelo-color, son «abajo»; el resto, «arriba»;
   - una caja va **abajo** si su talla principal es de las de abajo. Es la regla `tallas_por_altura` del programa.
6. **Rotación (líneas de 28 días):** se calcula en el momento solo para los artículos del lineal (`read_group` sobre
   las líneas de OUT hechas). No hace falta cron.
7. **No se mueven:**
   - las KO con dos modelos-color (unas 40 en toda la zona 0): salen en el plan como «revisar»;
   - las KO con prendas leídas para una OUT sin validar: se espera.

   Una KO con reservas sí se mueve, porque sus reservas viajan con ella.

**Antes de calcular un lineal**, si le quedan cajas a 0, sale el aviso «Retíralas primero» con el botón a la ronda de la
fase 0. Avisa, no bloquea.

## 3. Fase 1: lo que hace el operario en la PDA

Botón nuevo **«Compactar»** en Contenedores. Sale un resumen por lineal: pasos hechos / total y columnas libres /
previstas. Se toca un lineal o se lee; si no tiene plan, se pulsa «Calcular».

```
┌──────────────────────────────┐
│ L67 · columna 3 de 12        │
│ Vaciar L67 P22 C1 (2 cajas)  │
│                              │
│  KO_150726_118  12 uds       │
│   2622JA00-000003 NEGRO      │
│   → L68 P05 C2 · ABAJO       │
│  KO_150726_119   8 uds       │
│   → L68 P05 C2 · ARRIBA      │
│                              │
│ 1) Lee las cajas             │
│ 2) Lee la columna de destino │
│ [No está] [No cabe] [Saltar] │
└──────────────────────────────┘
```

1. Lee las cajas del paso. Si lee una que no es del paso: «Esa no está en el plan de esta columna».
2. Lee la columna de destino:
   - si es la del plan, la KO se mueve con la ruta de siempre (`/mover`) y la PDA dice **«ABAJO»** o **«ARRIBA»** en
     grande;
   - si es otra («No cabe»), se avisa si en ese destino hay el mismo modelo en otro color o si pasaría de 8 cajas, y
     hay que confirmar.
3. Con todas las cajas de la columna hechas: «✓ L67 P22 C1 LIBRE» y el paso siguiente.
4. Botones:
   - «No está»: la caja no está en la columna. Queda para revisar y no se cambia nada en Odoo;
   - «No cabe»: se lee otra columna o se salta;
   - «Saltar»: el paso va al final.

**Se comprueba en vivo** en cada movimiento:

- la caja sigue en la columna de origen;
- la caja está activa y no tiene prendas leídas sin validar;
- el destino es una columna, no otra KO, ni la zona Z.

## 4. Fase 1: datos (todo en tablas propias)

- **`koroshi.compactacion.paso`**:
  - lineal, orden y columna de origen;
  - KO, destino y destino real;
  - modelo-color, uds y banda (abajo o arriba);
  - estado: pendiente, hecho, cambiado, saltado, no está o revisar;
  - motivo, operario, fecha y la línea del registro.
- **`koroshi.contenedor.banda`**: KO → abajo o arriba, quién y cuándo. Se escribe al mover. Contenedores lo enseña en
  la ficha de la KO y en el hueco.
- **`koroshi.contenedor.movimiento`**: campo nuevo `paso_id`.
- **Parámetros:**
  - `cajas_columna = 8` (ver decisión 15);
  - `cajas_vaciar = 4`: se vacía con menos de 4;
  - `lineales_distancia = 2`;
  - `temporadas_zona0 = I27,V27`.

**Nada en `stock.picking`, `stock.picking.type`, `stock.move.line` ni `stock.location`** (regla 7). No se crea ninguna
ubicación.

## 5. Riesgos

| Riesgo | Qué se hace |
|---|---|
| Mover una KO mientras un preparador va a por ella | Si tiene prendas leídas, no se mueve. Si solo tiene reservas, se mueve y Lecturas recarga (R7, ya instalado) en 30 s o al leer. Mejor compactar cada lineal sin oleada abierta en él |
| El plan se queda viejo durante el día | Se calcula en el momento, por lineal. «Calcular» otra vez sustituye los pasos pendientes. Cada paso se comprueba al hacerlo |
| Dos lineales vecinos llenan la misma columna | Al calcular L68 cuentan como ocupados los destinos de los pasos pendientes de L67 |
| Lentitud | Un lineal y sus vecinos: unos cientos de cajas. Medirlo antes de instalar |
| El preparador no ve «abajo / arriba» en Lecturas | En la fase 1 lo ve quien compacta. Enseñarlo en Lecturas es `koroshi_preparacion`: otro módulo y otra sesión, después |

## 6. Decisiones

| # | Qué | Estado |
|---|---|---|
| 13 | Cómo sabe Odoo la altura | **Opción A** (tabla propia de bandas), según la recomendación del 26/11. Isaac dijo «de acuerdo, procede» |
| 14 | Fondo de una columna | **Decidido:** 8 cajas por columna (medio palé) |
| 15 | Tope de una columna de destino | **Pendiente:** ¿8 cajas (llena) o 7 (deja un hueco para maniobrar)? Va en un parámetro: se puede cambiar sin versión |
| 16 | «Cerca del muelle» | **Propuesta:** el lineal con el número más bajo (el muelle está antes de L01). Dentro de un lineal no se ordena por P hasta la fase 3 |

## 7. Qué hay que probar (fase 1)

- **Sin Odoo (`logica.py`):**
  - columnas a vaciar (< 4);
  - destinos sin pasar de 8 ni mezclar colores;
  - el mismo modelo-color junto;
  - orden por beneficio;
  - bandas abajo / arriba;
  - **equivalencia con el programa** en el mismo ejemplo.
- **En el navegador:**
  - «Calcular» en un lineal pequeño;
  - mover dos KO de prueba con su banda;
  - «No cabe» a una columna con otro color del mismo modelo (aviso).
- **Medir:** «Calcular» en el lineal más grande de la zona 0.
- **En la PDA:** un lineal entero (L67, después de retirar sus cajas a 0) con preparación al lado. Comprobar que
  Lecturas ve la columna nueva.

## 8. Números

La sesión del mapa los rehace con estas reglas: 8 cajas por columna, cajas enteras, sin litros y después de retirar
las cajas a 0. Sale cuántas columnas se liberan y cuántas cajas hay que mover, por lineal, con la copia de hoy
(`copias/20261126_1454_odoo.sqlite`). Los de la v2 (1.216 huecos, 2.524 cajas) eran con 770 L y ya no valen.
