# Traspàs del projecte: Oleades i matrícules Koroshi (EFFEC)

Document per continuar la feina des d'una altra sessió o compte. Escrit en català; el codi i els comentaris del repo són en castellà.

> **Repo privat obligatori.** El codi del programa conté credencials de producció (Postgres, SQL Server, SMTP, AutoUpdater i transportistes a `App.config`). No el feu públic ni el copieu a llocs públics.

---

## 1. Context

- **Empresa:** Effective Logistics. Odoo 13, base `NATH_PRODUCTION`, URL `https://nath.tuctuc.com`.
- **Client:** KOROSHI = empresa **EFFEC**, `company_id = 8`.
- **Programa "Pedidos Multiples"** (.NET Framework 4.8 WinForms): el programa de les **OLEADES** (put-to-store a la "U").
  - L'operari carrega una `stock.picking.batch` en estat `in_progress` amb OUT `assigned`.
  - Llegeix l'EAN de cada peça; el programa li diu a quin SEQ (posició/comanda) va; l'operari confirma el SEQ.
  - El programa fa directament a Postgres `UPDATE stock_move_line SET qty_done = @qty …`.
- **Objectiu:**
  1. Fer servir el programa per a les comandes de **botiga** de Koroshi.
  2. **Matrícules de caixa:** gravar a Odoo cada caixa com a paquet (`result_package_id`) amb el nom de la matrícula `CJ…`.
  3. **Crear oleades automàticament de nit**, perquè quan arriba el torn de les 6:00 tot estigui preparat.

## 2. Regles de treball (acordades amb l'Isaac)

- **No executar mai el programa**: escriu a les bases de dades de PRODUCCIÓ. Només compilar.
- **No tocar l'AutoUpdater** (`pedidos_multiples_odoo.xml`), ni l'URL d'actualització, ni la versió (0.8.0.9). Si es toquessin, s'actualitzarien tots els llocs de treball de totes les marques.
- **No mostrar credencials** als resums: posar `***`.
- **Codi i comentaris en castellà; explicacions en català.**
- **Canvis mínims.** No refactoritzar ni canviar el comportament de les altres empreses (NATH, ALAN, CODE, TCN, TTUC).
- **Aturar-se al final de cada fase**, fer un resum i esperar l'OK.
- **Accions de servidor d'Odoo** (`safe_eval` d'Odoo 13):
  - mai f-strings, sempre `%`;
  - sense `import`;
  - `log(...)` sempre **abans** de `raise Warning(...)`, perquè el raise fa rollback;
  - evitar comprensions de llistes i `reversed()`. Funcionen: `lambda`, `sorted(key=…)`, `+=` i `read_group`.
- **Abans d'escriure a Odoo:** primer una versió **DIAGNÒSTIC** que no escriu res i acaba amb `raise Warning`. Les proves es fan a l'acció de servidor id **1837**, sobre `stock.picking`.

## 3. Estructura del repo

```
PedidosMultiples.csproj        Projecte clàssic VS/MSBuild, net48, x64
App.config                     = PedidosMultiples.exe.config original (amb credencials)
PedidosMultiples/*.cs          Codi descompilat (C# 7.3); InitialForm.cs és el formulari principal
PedidosMultiples.Properties/   Resources.cs, Settings.cs
*.resx                         Recursos amb el nom complet (RootNamespace buit)
lib/                           DLL de l'original + nl/, x64/, x86/ pdfium.dll
recursos/                      MerchandizersMails.xlsx, eci_label.pdf, expediciones_label.pdf
odoo/                          Accions de servidor (Python per a safe_eval)
odoo/referencia/               Còpia dels mòduls del servidor: sorter_batch, koroshi_zebra
TRASPAS.md                     Aquest document
```

**Compilar:**
- Amb el MSBuild del Visual Studio: `msbuild PedidosMultiples.csproj /p:Configuration=Release`.
- Amb el .NET SDK (com s'ha fet al núvol): `dotnet msbuild PedidosMultiples.csproj -p:Configuration=Release -p:TargetFrameworkRootPath=<ruta a Microsoft.NETFramework.ReferenceAssemblies.net48>/build/`.
  - El `.csproj` activa `GenerateResourceUsePreserializedResources` **només** quan es compila amb `dotnet` (MSBuildRuntimeType=Core).
- **Estat:** compila amb 0 errors i 7 warnings, que ja hi eren a l'original. No s'ha executat mai.

## 4. Fases

| Fase | Estat |
|---|---|
| 1. Descompilar i compilar | ✅ Fet. ILSpy 9.1 amb el .pdb, C# 7.3 i les referències de net48 |
| 2. Anàlisi del codi | ✅ Fet (resum a la secció 5) |
| 3. Disseny | ✅ Pràcticament tancat. Queden les preguntes de la secció 9 |
| 4. Acció de servidor "empaquetar caixa" (`odoo/KOROSHI_empaquetar_caja*.py`) | ⏳ Pendent. Necessita el `grep` de `_put_in_pack` |
| 5. Implementació al programa | ⏳ Pendent |
| Oleades automàtiques (cron) | 🔄 En simulació (`odoo/KOROSHI_simular_oleadas_zonas.py`) |

## 5. Anàlisi del programa (resum, amb línies de `PedidosMultiples/InitialForm.cs`)

- **Empreses:** `companyIds` (`Form1_Load`, ~439): NATH=1, ALAN=23, CAREY=11, CODE=21, TCN=2, TTUC=1 (CAD=3, USA=4, COP=5), **EFFE=8**.
  - **EFFECTIVE ja existeix** al menú en aquesta versió (`eFFECTIVEToolStripMenuItem_Click`). Els llocs de treball tenen una versió més antiga.
  - `ConnectionSQL.cs`: TTUC, ALAN i CODE van a TUCTUC_PRODUCTION; **la resta (EFFE inclosa) a NATH_PRODUCTION**.
- **Càrrega:**
  - `queryGetOrdersByBatchName` (~122): batch `in_progress`, OUT `assigned` o `done`.
  - El nom de la batch ha de començar per `B-`, `BATCH/`, `ECI_`, `VP_` o `WEB_` (~883).
  - `queryInicial` (~98): una fila per `stock_move_line` (`sml_id`, QTY, `Leido = qty_done`).
- **SEQ:** número d'ordre de la comanda dins de la càrrega (`buildTable`, ~681).
- **Lectura:** EAN → es mostra el SEQ → l'operari confirma el SEQ → `Leido++` → `UpdateDoneQtyByOrderNumber` (~4262) amb `SET qty_done = Leido` (valor en memòria).
- **Caixa:**
  - Columna `Caja` per SEQ; `changeBox` (~2128) fa `Caja+1` i imprimeix l'etiqueta (`GenerateLabel`, ~3048).
  - Entrada: botó "Siguiente caja" + SEQ, o codi `CAMBIAR-CAJA`.
  - **No escriu res a Odoo.** Ho guarda en memòria i a `Logs\last_prep_EFFE.txt` i `Logs\packing_list_EFFE.txt`.
- **Final de comanda:** `CheckIfPeIsFinishedAndDoStuff` (~1328) comprova `GetDoneQtySum`, imprimeix l'etiqueta, envia correus i crida `FinishOrder`, que només marca les files.
  - Només per a NATH i ALAN (i TTUC) i en mode "Etiquetas", valida la OUT via XML-RPC (`OdooClient.cs`, `xml_put_in_pack`).
- **Riscos:**
  - **Dos llocs a la mateixa oleada:** `SET qty_done = <memòria>` perd lectures.
  - **Si Odoo parteix línies** (put-in-pack), l'`sml_id` en memòria queda antic i es comptaria dues vegades.
  - L'`UPDATE` no detecta quan actualitza 0 files.
  - Reintents infinits amb MessageBox.
  - Credencials al codi.
  - El programa reescriu el seu `.config` (`AddUpdateAppSettings`).

## 6. El que hem descobert a Odoo (accions INFO 1, 2 i 3)

- **Magatzems:** tots en `ship_only` (1 pas). Si es pica amb l'app de codis de barres sobre la OUT, es posa `qty_done` a la OUT, i el programa veuria les línies com a ja llegides.
- **Solució: el circuit SORTER de TucTuc** (mòdul `sorter_batch`, còpia a `odoo/referencia/`):
  - `stock.picking.create_transfer_for_batch(outs)` crea un **INT** de `EFFEC-STOCK` a la ubicació amb codi de barres **`SORTER`** (`EFFEC/SORTER`), amb l'origen = nom de la batch.
  - Treu la reserva de les OUT i n'**escriu `location_id = SORTER`**: queden "en espera".
  - Els pickers fan l'INT amb la PDA, el `qty_done` va a l'INT, i després "Comprobar disponibilidad" de les OUT les reserva des de SORTER.
  - Ja suporta la companyia 8. Existeixen `EFFEC/SORTER`, `EFFEC/Stock` (EFFEC-STOCK) i el tipus `EFFEC-INTERNAL`.
- **Matrícules:**
  - Mòdul `koroshi_zebra` (còpia a `odoo/referencia/`): seqüència `zebra.label.code` → `CJ` + 9 xifres (des de CJ665000001; ara mateix la següent és ~CJ665002787). Etiqueta de 110×150 mm amb Code128.
  - Els registres van a `zebra.label`. El paquet `stock.quant.package` amb aquell nom es crea en empaquetar.
  - Hi ha ~15.900 paquets `CJ` (~1.900 sense estoc).
  - De mitjana, **15 u per caixa** i 8-21 caixes per botiga.
- **Canal:** `sale.order.s_order_type_id.name`: **`PED. TIENDAS` → CJ**, `PED. MARKETPLACE` → PACK. Les comandes de botiga tenen origen `S-66…` i el destinatari "K<n> - …".
- **Regles automàtiques "en escriure" un albarà:**
  - **1789 S4T - Control matrícules** i **1812 S4T - Control cajas nombres**: en passar a `done` una OUT (que no sigui web `W-`), bloquegen si hi ha línies sense matrícula, prefix incorrecte o duplicats.
    - ⚠️ **Se salten la comprovació si la ubicació conté "SORTER".** Amb el circuit SORTER les botigues no es controlarien. **Proposta pendent d'OK:** saltar només si l'origen no comença per `S-66`.
  - **1705 Bloq:** si l'**usuari 68** modifica un INT o DEV no fet → `raise Warning("no")`. **Cal saber qui és l'usuari 68** (si és el de les PDA, no podria fer els INT).
- **Altres:**
  - 1786 "Dividir por capacidad" parteix les OUT de més de 300 u o 300 línies (`-1`, `-2`…).
  - Les comandes de botiga entren per API S4T (cron cada 15 min), sobretot entre la **1:00 i les 2:00**. Arriben **confirmades i reservades soles**.
  - Ara les botigues es fan amb agrupacions `TIENDA dd-mm` en **draft** i l'app de codis de barres (`barcode_batch_process`), amb l'usuari "Almacén Nath".
  - **Cap producte té volum ni pes** → s'equilibra per unitats.
- **Mapa de la nau** (`koroshi_mapa_16.html`):
  - 136 lineals (L01–L136), 36 posicions i 3-4 nivells (C1–C4).
  - Els lineals estan **aparellats esquena contra esquena**: un passadís dona servei a L(2k) i L(2k+1). Els talls de zona han d'acabar en lineal senar.
  - **Tota la temporada I27 és entre L41 i L136.**
  - Format d'ubicació a Odoo: `EFFEC/Stock/NAVE2/07828 - L94 P35 C1/KO_240826_1327`.

## 7. Disseny acordat

### 7.1 Oleades de nit (Odoo)

- **Volum:** ~50 botigues, ~10.000 u/dia, que pujaran a 15.000. **5 "U"** (llocs de lectura) alhora, a ~500 u/h (realista 425).
  - Calendari: torn de 6:00 a 13:00, pausa a les 10:00 (10 min), dinar de 13:00 a 14:00 i camió a les 14:00.
  - Amb 5 llocs n'hi ha prou per a ~13.000 u/dia; per a 15.000 u cal un 6è lloc o començar abans.
- **Cron 1 (2:30, reintent 4:00):**
  - agafa les OUT `PED. TIENDAS` de la nit, `assigned` i sense oleada;
  - les reparteix **per botiga** en N oleades `B-KOR-MMDD-NN` (una per "U"), equilibrades per unitats (la botiga més gran a l'oleada més buida);
  - crea **un INT per oleada × zona** cap a `EFFEC/SORTER/U<n>`;
  - **zones = trams de passadissos equilibrats cada nit**, un per PDA.
  - Opcional: una agrupació de picking per zona per a cada PDA.
- **Cron 2 (cada 15 min, de 3:00 a 9:00):** quan tots els INT d'una oleada estan fets, `action_assign` de les seves OUT, que s'han de reservar des de `SORTER/U<n>`.
- **Ubicacions noves proposades** (pendent d'OK): `EFFEC/SORTER/U1…U5`, virtuals. Fan que cada oleada reservi només el que s'ha picat per a ella.
- **Avís de procés:** amb el SORTER les OUT queden "en espera" fins que es valida l'INT. **No s'han d'esborrar** (la neteja de final de dia de la Betty).

### 7.2 Matrícules (programa + acció d'Odoo)

- **Preregistre per posició** abans de l'oleada (formulari nou `MatriculasForm`):
  - es llegeix el SEQ i les matrícules taronja de les caixes d'aquella posició, en ordre d'ús;
  - validacions: format `^CJ[A-Z0-9]+$`, que existeixi a `zebra.label`, que no estigui usada com a paquet amb contingut, i que no estigui repetida a la sessió;
  - es guarda en memòria i a `Logs\matriculas_EFFE.txt`.
- **CAMBIAR CAJA** (sense llegir la matrícula):
  - el programa pren la matrícula en curs del SEQ i crida Odoo **de manera síncrona** per JSON-RPC: `ir.actions.server.run` amb context `{active_model: 'stock.picking', active_id, active_ids, matricula}`;
  - **si dona error:** so, missatge, i la caixa queda oberta;
  - **si va bé:** `RecargarLineasPedido(pe)` (es tornen a llegir les línies, perquè Odoo les parteix) → `Caja+1` → següent matrícula → s'imprimeix la pegatina amb la matrícula.
- **Final de comanda:** tanca l'última caixa amb la matrícula de la cua; si la cua és buida, obliga a llegir-la.
- **Configuració nova a `App.config`:** `koroshi_modo_matricula`, `koroshi_prefijo_matricula`, `odoo_url`, `odoo_db`, `odoo_user`, `odoo_api_key`, `odoo_accion_empaquetar_id`, `odoo_timeout_seg`.
  - Només s'aplica si l'empresa és EFFE i no està activat el mode ECI ni el VP.
- **Classe nova `OdooRpc.cs`:** JSON-RPC amb Newtonsoft (`authenticate` + `execute_kw`).
- **Protecció per lloc** (opcional): camp `x_puesto` a la batch perquè dos llocs no carreguin la mateixa oleada. Pendent d'OK.
- **Acció d'Odoo `KOROSHI_empaquetar_caja.py`** (Fase 4):
  - comprova que el picking sigui de l'empresa 8, `outgoing` i `assigned`, i que la matrícula sigui `CJ` i no estigui usada en un altre albarà;
  - `lineas = qty_done > 0 sin result_package_id`;
  - `_put_in_pack(lineas)` i posa el nom de la matrícula al paquet (o reutilitza el paquet buit existent);
  - fa les mateixes comprovacions que les regles 1789 i 1812.

## 8. Fitxers `odoo/`

| Fitxer | Què fa | Escriu? |
|---|---|---|
| `KOROSHI_INFO_DIAGNOSTICO.py` | Info 1: magatzems, horaris, `qty_done` previ, ubicacions, volums, matrícules, batches, crons i mòduls | No |
| `KOROSHI_INFO_2_DIAGNOSTICO.py` | Info 2: mòduls propis, regles, com es preparen les OUT, unitats per caixa, camps | No |
| `KOROSHI_INFO_3_DIAGNOSTICO.py` | Info 3: codi de les regles i del sorter, `zebra.label`, `sorter.batch` | No |
| `KOROSHI_crear_oleadas_DIAGNOSTICO.py` | Primeres simulacions d'oleades (v3: rànquing de botigues) | No |
| `KOROSHI_crear_oleadas.py` | Crea batches `B-KOR` (`ESCRIBIR=False` per defecte). **Antic:** no fa servir el SORTER ni `PED. TIENDAS` | Només amb `ESCRIBIR=True` |
| `KOROSHI_simular_oleadas_zonas.py` | **Simulació actual:** oleades + zones per PDA + INT oleada × zona + requisits | No |
| `referencia/sorter_batch`, `referencia/koroshi_zebra` | Còpia dels mòduls del servidor (`/opt/nath-erp/nath/custom_addons/`) | — |

⚠️ L'acció planificada **"KOROSHI Crear Oleadas (Diagonistico)"** es va crear per error com a cron mensual (propera execució el 14/11). **S'ha de desactivar.**

## 9. Pendent (per ordre)

1. **Resultat de la simulació v2** d'oleades per zones (`KOROSHI_simular_oleadas_zonas.py`, amb `INCLUIR_YA_EN_OLEADA` i `INCLUIR_RESERVA_PARCIAL`).
2. **Qui és l'usuari 68** (`/web#id=68&model=res.users`).
3. **App de la PDA:** amb una agrupació de diversos INT (un per "U"), indica a quin albarà/carro va cada peça?
4. **OK per:** crear `EFFEC/SORTER/U1…U5`; corregir les regles 1789 i 1812 (excepció SORTER); camp `x_puesto` (opcional).
5. **`grep` de `_put_in_pack`** al servidor:
   ```bash
   find /opt/nath-erp -path "*addons/stock/models/stock_picking.py" 2>/dev/null
   grep -n "def _put_in_pack\|def action_put_in_pack\|def _pre_put_in_pack_hook" -A 30 <ruta>
   ```
6. **Pegatina pròpia:** quins codis de barres hi voleu (matrícula sí; comanda i origen?), i el logo del packing list d'EFFE (ara surt el de NATH).
7. **Fase 4:** `odoo/KOROSHI_empaquetar_caja.py` + `odoo/KOROSHI_empaquetar_caja_DIAGNOSTICO.py`.
8. **Cron real d'oleades** (crear batches + INT per zona cap a SORTER/U<n>) + cron 2 (reservar OUT), amb la versió diagnòstic primer.
9. **Fase 5:** commits A (EFFEC/logo), B (`App.config` + `OdooRpc.cs`), C (mode matrícula), D (protecció per lloc, opcional). Compilar sense errors; **no executar**.
10. **Més endavant:** dos lectors a la mateixa "U" (increment atòmic de `qty_done`); treure les credencials del codi.
