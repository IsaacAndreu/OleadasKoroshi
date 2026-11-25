# Pregunta a S4T: ¿podemos ENVIAR correcciones de traspasos? (20/11/2026)

Borrador. No enviado: lo revisa Isaac. Pedido por Isaac: «Miram si en la api de correciones natros podem enviar
correcions o sols podem recibir?».

---

**Para:** Andrés Moya (S4T)
**CC:** Sonia, Betty
**Asunto:** Correcciones de traspasos: ¿podemos enviaros las nuestras?

Hola Andrés,

Una duda sobre las correcciones de traspasos (`GET /transfers/corrections`).

Según la documentación de la API que tenemos (openapi del 12/11), solo podemos **recibir** las correcciones: no vemos
ningún endpoint para **enviarlas**. Lo único cercano que mandamos es `POST /stock/register` (movimientos de stock) y
tenemos sin usar `POST /box/validate`.

**Lo que necesitamos**
Cuando al recibir o preparar un traspaso encontramos una diferencia nuestra (más o menos unidades que las del
traspaso), hoy no tenemos cómo comunicárosla por la API. Querríamos saber:

1. ¿Existe ya un endpoint para **enviar** una corrección de traspaso (por ejemplo, un `POST /transfers/corrections`)?
   Si existe, ¿cuál es, con qué campos y con qué signo (+/−) y significado?
2. Si no existe, ¿lo tenéis previsto o lo podéis añadir? Nos valdría con: número de traspaso, artículo, color y talla,
   unidades según el traspaso, unidades reales, y motivo.
3. Mientras tanto, ¿cuál es la vía que queréis que usemos para estas diferencias: `POST /stock/register`,
   `POST /box/validate` o un correo?

Un último punto, para no equivocarnos al leerlas: ¿nos podéis confirmar qué significa el signo de las correcciones
que recibimos y qué efecto debe tener cada una en el stock de 00006665 (y si es solo informativa para nosotros)?

Gracias,

Isaac

---

## Para Isaac (no va en el correo)

- **No he podido comprobar el openapi de hoy:** `http://82.223.131.45:3232/openapi.json` responde «Not authenticated».
  La clave de la API está solo en `s4t.config` del servidor y no la he copiado ni usado; la respuesta se basa en el
  resumen del 12/11 (`20261112_S4T_API_endpoints_resumen.md`). Si quieres que se compruebe con la clave, dilo y se
  hace aparte (lectura).
- `koroshi_s4t_traspasos` 1.3.0 (sin instalar) solo descarga las correcciones y las registra; no mueve stock ni envía
  nada.
- Se pregunta el signo y el efecto en stock porque seguimos sin tener esa definición (el PDF API_TRANSFERS no la da).
