# Respuesta a KOROSHI (web@koroshi.tv) — pedidos online — 20/11/2026

Borrador para Isaac. **No enviado.** Datos leídos en Odoo el 20/11 hacia las 09:00 (hora local), sin tocar nada.
Lo que va entre [corchetes] lo tiene que decidir o completar Isaac antes de enviar.

---

**Asunto:** RE: Pedidos online pendientes

Hola Sandra, hola Sonia:

Os confirmo pedido a pedido cómo está todo en el almacén esta mañana.

**1. Los 6 pedidos que no nos habían entrado (58547, 58548-02, 58549, 58551, 58552 y 58553)**

Los metimos nosotros a mano ayer por la tarde (19/11). Están así:

- **58549, 58551, 58552 y 58553**: completos, con todo el stock reservado. Están en la agrupación de hoy
  (WEB_201126_01) y se preparan hoy.
- **58547**: falta **2622BL02-000003-XXL** (no hay stock). Las otras dos prendas (2522BL03-000003-XXL y
  2622ML20-000003-XXL) sí están.
- **58548-02**: faltan **2522ML14-000017-XL** y **2522ML31-000003-XL**. Las otras tres (1922ML00-000003-XL,
  2425ML01-000070-6 y 2525ML05-000039-6) sí están.

Como con el resto de pedidos web incompletos, 58547 y 58548-02 se cancelan hoy en el almacén y os llegará el
aviso automático. Si queréis servir lo que sí hay, cancelad los originales en el TPV y mandadlos de nuevo solo
con esas prendas.

**2. Los 6 pedidos anulados por falta de stock**

Confirmado: en nuestro sistema están cancelados los seis (58623, 58645, 58667-02, 58687, 58697 y 58844), con las
prendas que indicáis. No salen del almacén.

Sobre el TPV: [si lo hace KOROSHI:] la anulación en el TPV la tenéis que hacer vosotros, nosotros no tenemos
acceso. [si lo hace alguien de Nath: «Lo anulamos también en el TPV hoy.»]

**3. El pedido 58577**

Completo no lo podemos servir: de **2521XC04-000003-42** no tenemos stock bueno (la única unidad que queda es de
taras). Las otras dos prendas, **1922VS06-000015-XS** y **2422XC02-000003-39**, sí las tenemos.

Si queréis mandar solo esas dos, cancelad el 58577 en el TPV y enviadnos un pedido nuevo con ellas; lo
prepararemos en cuanto nos entre.

**4. Los pedidos 5930007689 (13/11), 58833 (16/11) y 59246-02 (18/11)**

Están preparados y cerrados en el almacén desde esos días. [si los confirma KOROSHI:] Por favor, confirmadlos en el
TPV para que salgan las etiquetas; en cuanto las tengamos se envían. [si los confirma Nath: «Los confirmamos hoy
en el TPV y salen con las etiquetas de hoy.»]

[Si alguno ya ha salido, cambiar este punto: preguntar antes en expedición.]

Quedo a vuestra disposición para lo que necesitéis.

Un saludo,
Isaac

---

## Notas para Isaac (no van en el correo)

Lo que se ha mirado en Odoo (solo lectura):

| Pedido | OUT | Estado en Odoo |
|---|---|---|
| W-0000058547 | OUT/26658 | Preparada a medias (`assigned`), sin agrupación. Falta 2622BL02-000003-XXL (0 de 1) |
| W-0000058548-02 | OUT/26659 | Igual: faltan 2522ML14-000017-XL y 2522ML31-000003-XL |
| W-0000058549, 58551, 58552, 58553 | OUT/26660-26663 | Reservadas del todo, en **WEB_201126_01** (en curso) |
| 58623, 58645, 58667-02, 58687, 58697, 58844 | OUT/25063, 25255, 25309, 25337, 25345, 25457 | Las seis **canceladas** (13/11 y 16/11) |
| W-0000058577 | OUT/25029 | Cancelada el 13/11. Pedido de venta sigue en `sale` |
| W-5930007689 | OUT/25303 | **Hecha** 13/11 13:44, lote WEB_131126_02 |
| W-0000058833 | OUT/25449 | **Hecha** 16/11 13:48, lote WEB_161126_01 |
| W-0000059246-02 | OUT/26266 | **Hecha** 18/11 11:12, lote WEB_181126_01, transportista «RECOGE CLIENTE» |

1. **El corte de las 06:00 de hoy no se ha hecho.** `ultimo_corte` = «2026-11-20 06:00», pero no hay registro de
   corte del 20/11 (el último es el de las 11:00 del 19/11). El código marca `ultimo_corte` antes de hacer el corte
   y, si el corte falla, lo deshace sin dejar rastro (`koroshi_agrupaciones_web/models/corte.py:275-285`).
   WEB_201126_01 (64 OUT) la creó **a mano** «Almacén Nath» a las 06:06 hora local, probablemente a la vez que el
   cron. Por eso 58547 y 58548-02 siguen vivas: **en el corte de las 11:00 se cancelarán** (cancelar = 1, son
   incompletas y del 19/11) y saldrá el correo a Betty, salvo que antes se lea algo de ellas.
   → Isaac (20/11): que se cancelen en el corte de las 11:00. No hay que hacer nada en Odoo; después de las 11:00
   comprobar que OUT/26658 y OUT/26659 están canceladas y que el correo a Betty ha salido antes de enviar esto.
2. **58577:** stock libre hoy: 1922VS06-000015-XS = 1 (L41 P20 C2); 2422XC02-000003-39 = 6;
   2521XC04-000003-42 = 1, pero en `TARKO/Stock/NAVE2/KO_TARAS_490` (taras). Isaac (20/11): la de taras no se
   sirve, así que el 58577 no se sirve completo. El correo les pide que lo cancelen y manden uno nuevo con las dos
   prendas que hay. En Odoo no se ha hecho nada (OUT/25029 sigue cancelada; el pedido de venta sigue en `sale`).
3. **Los 3 validados:** en Odoo no hay nada que los distinga del resto. Todos los pedidos web de noviembre (1.829)
   tienen `x_s4t_status` = PENDING y `x_s4t_synced` = falso, y ninguna OUT web tiene `sent_to_s4t_api`: la web
   no pasa por «Envíos a S4T» y Odoo no manda nada a KOROSHI. Las etiquetas salen cuando el pedido está confirmado
   en el **TPV de KOROSHI**. Lo que no sé: **quién confirma en el TPV** (¿expedición/Betty desde Nath o KOROSHI?) y
   si estos tres paquetes siguen en el almacén o ya han salido. Pregunta a expedición antes de enviar.
4. Los 6 recuperados llevan IDs S4T provisionales (-900024 a -900029): si S4T los manda más tarde con su ID real,
   pueden entrar duplicados. Vigilarlo.
