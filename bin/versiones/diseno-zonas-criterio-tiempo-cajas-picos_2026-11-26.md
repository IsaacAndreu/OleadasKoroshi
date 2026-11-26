# koroshi_zonas: elegir las zonas por tiempo, cajas cerradas y sin picos (diseño, 26/11/2026)

Estado: **diseño, sin código**. Espera el visto bueno de Isaac. Instalada en el servidor: 1.9.0 (26/11, 15:45), con
«Elegir cada día cuántas zonas» encendido (3, 4, 5) y el ritmo en 52 / 21 s.

Lo que pide Isaac (26/11):

> «Vull que este modul de zones sigue independent totalment (sempre sent conscient que si hi han uds al muelle tenim
> un apart que te que se muelle pero als lineals pot fer les zones que vagin millor per temps i per caixes tancades).
> No vull picos ni caixes que no estiguen tancades.»

- Muelle (MU1, MU2): siempre aparte, como ahora.
- Lineales: el módulo decide cuántas zonas y dónde se cortan, mirando **la hora de fin y las cajas cerradas**.
- **Sin picos**: que no haya una zona que acabe mucho más tarde que las demás.
- **Sin cajas abiertas** por culpa del reparto.

---

## 1. Primero: el ritmo real sale absurdo (0 s / 67,6 s) — por qué

Configuración de hoy: «0,0 s por lectura + 67,6 s por lineal (error medio 646,7 %)», propuesto 0 / 121 s.
**No se debe pulsar «Usar el ritmo real»** hasta arreglarlo.

Datos medidos (`ritmo_zonas` de las ejecuciones medidas; segundos por lectura = segundos-persona ÷ lecturas):

| Día | Zona | Lecturas | Lineales por OUT | s-persona | s por lectura |
|---|---|---|---|---|---|
| 13/11 (ej. 17) | D1 | 962 | 344 | 1.951 | **2,0** |
| 13/11 | D2, D3 | 1.154, 949 | | **0** | — |
| 16/11 (ej. 21) | D1 | 2.603 | 1.097 | 941 | **0,4** |
| 16/11 | D2, D3 | 1.972, 2.104 | | **0** | — |
| 17/11 | D1–D3 | 627–903 | | 32–43 mil | 47–57 |
| 19/11 | D1–D3 | 604–835 | | 34–42 mil | 50–57 |
| 23/11 | D1–D3 | 1.876–2.407 | | 80–102 mil | 36–43 |
| 25/11 | D1–D3 | 601–874 | | 29–42 mil | 47–49 |

(24/11 está «parcial» y no entra.)

**Causa:** el 13/11 y el 16/11 la PDA casi no apuntó lecturas: 1 y 3 personas medidas, y D2 y D3 a cero. Coincide con el
16/11, cuando Lecturas no guardaba. D1 de esos dos días entra en el ajuste con miles de lecturas hechas «en» 2.000 s y
0,4 s. Esas dos filas tiran el ajuste a «las lecturas no cuestan nada».

No es culpa de que sean días «histórico»: el 17/11 y el 19/11 también lo son y sus datos son buenos (47–57 s por lectura).

Sin esos dos días (12 zonas-día):

| | s por lectura | s por lineal | error |
|---|---|---|---|
| ajuste | 16,8 | 52,1 | **4,9 %** |
| propuesto (escalado a la hora de fin de ahora) | **23** | **73** | |
| ritmo de ahora (52 / 21) | | | 35,0 % |

Contando también el 24/11 parcial sale lo mismo (23 / 72, error 4,3 %). La propuesta anterior era 31 / 53, con
9 zonas-día; con más días el peso del «andar» (lineales) sube.

**Arreglo propuesto (código, 1.10.0):** una zona-día solo entra en el ajuste si está **medida de verdad**:
1. Al medir, guardar en `ritmo_zonas` también las lecturas de la PDA de la zona (`lecturas_pda`). Es un campo Text
   de la tabla propia del módulo; no toca tablas compartidas.
2. Entra si `lecturas_pda ≥ 70 %` de las lecturas del reparto, y si **todas** las zonas de lineal de ese día tienen
   segundos-persona. Si una está a cero, ese día falla entero.
3. Seguro extra: fuera también la que dé menos de 10 s o más de 150 s por lectura.
4. El texto de la configuración dice cuántas zonas-día se han descartado y por qué.

Con eso, hoy saldría 23 / 73.

---

## 2. Qué pasa hoy con 3, 4, 5 y 6 zonas (datos del 26/11)

Reparto real del 26/11 en DIAGNÓSTICO, 11 personas, cajas de 80 % (script
`criterio2611.py` en el scratchpad de la sesión, sobre `koroshi_zonas_2611_datos.json`).

- «Abiertas» = trozos de OUT cuya última caja no llega al 80 %.
- «Inevitables» = la tienda entera no llena su última caja (38 hoy). Esa caja abierta existe se reparta como se reparta.
- **«Por partir»** = abiertas que salen porque el reparto ha partido una OUT entre zonas. **Esta es la parte que el
  módulo sí puede evitar.**
- **Pico** = minutos entre la primera y la última zona de lineal que acaban.

| Ritmo | Lineal | Acaba | Por partir | Uds fuera de zona | Pico | Personas |
|---|---|---|---|---|---|---|
| 52/21 | 3 | 14:15 | 12 | 520 | 82 min | 2 · 4 · 5 |
| 52/21 | **4** (elige la 1.9.0) | 13:51 | 17 | 735 | 89 min | 2 · 3 · 3 · 3 |
| 52/21 | 5 | 14:36 | 14 | 987 | 168 min | |
| 23/73 | **3** | **12:44** | 18 | **459** | **16 min** | 4 · 4 · 3 |
| 23/73 | 4 | 13:15 | 16 | 551 | 61 min | 3 · 3 · 3 · 2 |
| 23/73 | 5 | 13:58 | 19 | 979 | 148 min | |
| 23/73 | 6 | 13:56 | 15 | 1.051 | 159 min | |

Lo que se ve:
1. **Los picos salen de redondear las personas.** El motor corta las fronteras para igualar el trabajo y después reparte
   11 personas enteras. Con 4 o 5 zonas, a una le tocan 2 personas para lo que serían 2,6, y acaba una hora o dos más
   tarde. Cuantas más zonas, más pico.
2. **Las cajas abiertas por partir apenas cambian** con el número de zonas (12–19). Lo que sí crece mucho son las
   **uds cogidas fuera de su zona** (de 459 a 1.051): son las que se mueven de la frontera para cerrar cajas. Es
   andar de más.
3. Con el ritmo bueno (23/73), 3 zonas gana en todo: acaba antes, menos pico y menos uds fuera.

---

## 3. Propuesta

### A. Quitar los picos en el motor: fronteras según las personas (lo que más ayuda)

Hoy: frontera por trabajo → personas enteras → pico.
Propuesto: **personas enteras primero, frontera después.**
1. Para N zonas, repartir las personas de lineal en enteros: 11 en 3 = 4 · 4 · 3.
2. Cortar las fronteras para que **trabajo ÷ personas** sea igual en cada zona: la zona de 3 personas recibe 3/11 del
   trabajo, no 1/3.
3. El ajuste de cajas cerradas mueve después las líneas de la frontera, como ahora.

Así todas las zonas acaban a la vez, salvo lo que muevan las cajas. No hace falta «que una zona ayude a otra al acabar»,
que en el almacén cuesta organizarlo.

### B. Elegir el número de zonas con los tres criterios

Para cada número de zonas a probar (3, 4, 5…) se calcula el reparto, como ahora, y se mira:

| Criterio | Qué es | Regla |
|---|---|---|
| Cajas | abiertas **por partir** (no las inevitables) | no más de **mínimo + 5** de las opciones |
| Pico | min entre la primera y la última zona de lineal | no más de **30 min** |
| Hora | la zona que acaba más tarde | la más temprana de las que quedan |
| Desempate | | si una con menos zonas acaba menos de 10 min más tarde, esa |

- Si ninguna pasa los filtros, se coge la de menos pico y se avisa en el informe y el correo («AVISO: ninguna opción
  sin picos»).
- Los umbrales (5 cajas, 30 min y 10 min) van en la configuración, para que un jefe los pueda cambiar.
- La línea del informe y el correo lo enseña todo:

  `ZONAS DEL DIA: 3 de lineal. 3: acaba 12:44, pico 16 min, 18 cajas abiertas por partir, 459 uds fuera <- ELEGIDA;
  4: acaba 13:15, pico 61 min (más de 30); 5: …`

Con los datos de hoy y el ritmo 23/73 elegiría 3 (acaba a las 12:44, pico de 16 min). Con 52/21 ninguna pasa los
30 min de pico sin la parte A. **Por eso A va antes que B.**

### C. Sobre «ninguna caja sin cerrar»

Cero no es posible: 38 tiendas hoy piden menos de lo que llena su última caja, y esa caja sale abierta se reparta como
se reparta. Lo que el módulo puede hacer es **no abrir ninguna más** al partir OUT entre zonas. Hoy son 12–19 por día.
Para bajarlas, más adelante: cuando la última caja de una OUT partida quedaría abierta, dejar toda esa OUT en la zona
principal, aunque se ande un poco más. Hoy ya se hace con las líneas de la frontera, pero no con OUT enteras.
Se mide aparte, sin tocar ahora.

---

## 4. Orden y versiones (propuesta)

| Versión | Qué | Riesgo |
|---|---|---|
| 1.10.0 | ritmo: solo zonas-día medidas de verdad (sección 1) | ninguno en la PDA: solo cambia la propuesta de ritmo |
| 1.10.0 | fronteras según las personas (A) | cambia dónde se corta; se prueba en DIAGNÓSTICO con 10 días reales antes |
| 1.10.0 | elegir con cajas, pico y hora (B), umbrales en la configuración | solo cambia cuántas zonas se eligen |
| después | «Usar el ritmo real» (23/73), lo pulsa un jefe | |
| 1.11.0 | modo del día (tradicional / agrupaciones T), lo que antes era la 1.10.0 | |

**Mientras tanto (mañana, 27/11):** la 1.9.0 elegirá con 52/21. Hoy habría elegido 4 zonas (13:51, pico 89 min).
Si Isaac prefiere evitar ese pico, se puede apagar «Elegir cada día cuántas zonas» y dejar las zonas de la
configuración. Es un cambio de configuración, no de código.

## 5. Qué no se ha probado

- Las cifras son del motor en DIAGNÓSTICO con los datos del 26/11. No se han probado A ni B: son diseño.
- El filtro del ritmo está comprobado a mano con los `ritmo_zonas` del servidor (leídos por RPC, solo lectura).
