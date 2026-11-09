# Proposta: eina de FALTANTS a la PDA (koroshi_faltantes) — v1, 09/11/2026

Només és una proposta. Per preparar-la només s'ha llegit Odoo; no s'ha escrit ni instal·lat res.

## 1. Què passa avui (dades d'Odoo)

- **Com està guardat l'estoc:** cada unitat reservada d'una OUT té una línia amb la seva ubicació final, que és una caixa `KO_ddmmyy_nnn` dins d'un forat.
  - Exemple: `EFFEC/Stock/NAVE2/27898 - L46 P15 C3/KO_140726_005`.
  - No hi ha lots ni paquets, i el 91 % de les línies són d'una sola unitat (5.031 de 5.536 reservades ara).
- **Què fan quan una peça no hi és:** des de la PDA (usuari «Almacén Nath") **posen a 0 la quantitat d'aquella ubicació**.
  - Odoo ho apunta com a «Cantidad de producto actualizada»: l'estoc surt cap a pèrdues d'inventari i no queda cap registre de qui, de quina OUT ni de per què.
  - Del 27/10 fins avui: **111 vegades, 159 unitats, 92 articles**, unes 5–27 unitats al dia, sempre entre les 06:50 i les 09:00.
- **Hi havia estoc en un altre lloc?** De les 111, **49 (el 44 %) tenen ara mateix estoc lliure en una altra ubicació**: la mediana és de 4 ubicacions, i un 10 % en té 16 o més. És a dir, gairebé la meitat dels faltants es podrien haver servit d'un altre lloc.
- **Què és «Faltas por dia» del KPI:** des del 02/11 són 421 línies i 455 unitats, però **el 94 % no té cap estoc a la nau**. Per tant, això és sobretot **«no hi ha estoc»**, no «no el trobo». Són dues coses diferents, i aquesta eina és per a la segona.
- **Ubicació FALTANT:** no n'hi ha cap ara mateix.

## 2. Com es pot canviar una línia d'ubicació sense trencar res

- **És el que ja fa Odoo:** quan a una línia reservada (sense cap unitat llegida) se li canvia la ubicació d'origen, el mateix Odoo:
  1. treu la reserva de la ubicació vella;
  2. reserva a la nova, però **només si hi ha estoc lliure** (no la pren a una altra OUT);
  3. si a la nova no n'hi ha prou, en reserva el que pot i l'OUT queda «parcialment disponible».

  És la mateixa lògica que fa servir l'app de codi de barres quan l'operari canvia d'ubicació.
- **Mai «Forzar disponibilidad»**, i no es toquen `stock.quant` a mà.
- **Primer la línia, després la peça:** la peça que no hi és s'ha de treure de la ubicació **després** de moure la reserva. Si no, Odoo es queixa que hi ha més reservat que estoc, que és el que pot passar ara quan es posa a 0 una ubicació amb reserva.
- **La ubicació FALTANT** ha d'estar **fora d'`EFFEC/Stock`**, per exemple `EFFEC/FALTANT`, de tipus intern. Així **cap OUT no hi reserva mai**, però l'estoc no es perd: queda allà fins que algú el revisa.

## 3. Flux a la PDA

Una pantalla dins d'Odoo, «Faltante», amb la mateixa filosofia que `koroshi_operarios`. S'hi entra amb un botó a la pantalla d'operaris o des del menú.

1. L'operari està fent una OUT a l'app de codi de barres i una peça no hi és. Torna enrere amb la fletxa: l'app desa el que ha llegit i surt la pantalla d'operaris.
2. Prem **«Faltante»** i llegeix **l'OUT** (o la pantalla ja la sap, perquè ell la té oberta) i **l'EAN de la peça**.
3. Surt en gran:
   - **On estava reservada:** `L46 P15 C3 · KO_140726_005 · 1 u`.
   - **On n'hi ha més, amb estoc lliure**, ordenat pel lineal més proper al seu, com a màxim 5:
     `L44 P17 C3 (2 u)`, `L52 P09 C1 (1 u)`...
4. Va a una d'aquestes ubicacions i **llegeix la ubicació** (la caixa KO o el forat). En aquell moment, tot de cop:
   - la línia de l'OUT passa a la ubicació nova, amb la reserva bona;
   - la unitat que no hi era passa de la ubicació vella a **FALTANT**;
   - queda apuntat a la llista de faltants: qui, OUT, article, d'on, cap a on, hora.
   - **Si alguna cosa falla, no es fa res.**
5. Si **no n'hi ha enlloc**, prem **«No hi és enlloc»**:
   - la unitat va a FALTANT;
   - la línia queda sense reserva;
   - l'OUT es valida sense aquella peça, igual que ara.
6. Prem **«Tornar a l'OUT»**: torna a obrir l'OUT a l'app de codi de barres, ja amb la ubicació nova.

**Revisió diària** (a l'oficina): llista dels faltants del dia amb dos botons per a cada línia.
- **Trobat:** torna la unitat de FALTANT a la ubicació que es triï.
- **No trobat:** treu-la de FALTANT cap a pèrdues d'inventari. És el que ara fan a la PDA posant a 0, però amb un registre.

Es pot exportar a Excel des de la mateixa llista.

## 4. Què es pot fer i què no

| Es pot | No es pot (sense tocar l'app de codi de barres) |
|---|---|
| Buscar on més hi ha estoc lliure i canviar la reserva amb la lògica d'Odoo | Fer-ho des de dins de la pantalla de l'OUT: cal sortir-ne amb la fletxa i tornar-hi a entrar (amb un botó, i en tornar ja surt actualitzada) |
| Una taula pròpia de faltants (qui, què, d'on, cap a on, estat de la revisió) | Saber si una altra PDA té oberta la mateixa OUT en aquell moment |
| La ubicació FALTANT fora d'Stock, perquè no es reservi | Canviar només una part d'una línia de 2–4 unitats a la v1: la v1 mou la línia sencera (el 91 % de les línies són d'1 unitat) |
| Revisió diària amb Trobat / No trobat | |

## 5. Riscos

- **Dues PDA a la mateixa OUT:** si dues PDA tenen oberta la mateixa OUT, la que no ha fet el canvi té la línia vella a la memòria. La v1 només canvia línies **sense cap unitat llegida**, i el flux obliga a sortir de l'OUT abans de fer-ho. Amb les zones de la v12, cada OUT de zona la fa una sola persona.
- **Moviments d'estoc reals:** l'eina **escriu a l'estoc**: canvia la reserva i fa moviments interns cap a i des de FALTANT. Per això cal provar-la primer amb una OUT de prova i amb el teu OK, fora d'hores, com sempre.
- **Mal ús:** si algú llegeix una ubicació que no és on ha agafat la peça, l'estoc queda malament, igual que ara. La llista de faltants ho fa visible.
- **Hàbits:** cal que deixin de posar a 0 des de la PDA. Es pot vigilar amb un informe dels «Cantidad de producto actualizada» del dia.
- **Mai:** cap camp nou a `stock.picking`, `stock.move(.line)`, `stock.picking.batch` ni `stock.picking.type` (el 03/11 un camp va tombar la PDA). No es toca l'app de codi de barres ni s'utilitza «Forzar disponibilidad».

## 6. Estructura del mòdul (`odoo/modulos/koroshi_faltantes`)

```
models/faltante.py         koroshi.faltante (taula propia) + logica: alternativas, reubicar, a FALTANT, revisar
data/ubicacion.xml         ubicacion EFFEC/FALTANT (interna, fuera de EFFEC/Stock), noupdate
controllers/main.py        /koroshi/faltantes/buscar, /reubicar, /sin_alternativa (json)
static/src/js|xml|css      accion de cliente "Faltante" para la PDA
views/faltante_views.xml   lista, revision (Encontrado / No encontrado), filtros por dia y operario
security/ir.model.access.csv
```

Dependències: `stock`, `stock_barcode` i, si es vol el botó a la pantalla d'operaris, `koroshi_operarios`.
