---
name: "crear-intent-md"
description: "Entrevista guiada para generar un intent.md (Stage 1 Plan del AI-native SDLC). Usar SOLO cuando el usuario la invoque expresamente (/crear-intent-md)."
disable-model-invocation: true
---

# Crear intent.md (Plan · AI-native SDLC)

Objetivo: capturar una idea, petición, ticket o incidencia en un `intent.md`, una proto-especificación escrita en los términos del propio originador, legible por personas y accionable por agentes. Es el primer artefacto de la cadena intent.md → spec.md → plan.md → diff/tests → PR, y al aceptarse dispara la fase de requisitos y diseño.

Se activa **solo por invocación expresa**. No la uses por iniciativa propia.

## Principios

- El intent describe **qué se quiere, por qué y con qué restricciones**. NO describe cómo implementarlo (eso es spec.md y plan.md). Si el usuario baja a solución técnica, recógelo como restricción o pregunta abierta, o apártalo para la spec.
- Lenguaje del originador, sin jerga formal obligatoria. No reescribas su intención con tus palabras si cambia el matiz.
- Conciso: cada sección en 1–4 líneas. El documento completo debe caber en media pantalla.
- No inventes datos. Lo que no sepa el usuario va a **Preguntas abiertas**, no a otra sección.
- Cuantifica cuando se pueda ("un tercio del tiempo de llamada", "de 3 días a 1 hora").
- Es una skill genérica, válida para cualquier organización: no supongas empresa, producto, personas ni herramientas. Usa lo que haya en el contexto de quien la invoca (lo que diga o adjunte, su memoria, sus conectores) y pregunta lo que falte.

## Flujo

### 0. Presentación y arranque
Abre el primer mensaje con una presentación breve (3–4 líneas, con tus palabras, sin copiar texto del documento) que diga:
- Que esta skill sirve para redactar requerimientos siguiendo la metodología que propone Anthropic en *The AI-Native SDLC Playbook* (https://claude.com/blog/the-ai-native-sdlc-playbook).
- La idea en una frase: cada fase del desarrollo termina con un documento versionado que pasa a la siguiente (intent.md → spec.md → plan.md → código y tests → PR), y esa cadena sirve de registro de quién pidió qué y quién lo aprobó.
- Que aquí se prepara el primer eslabón, el `intent.md`: qué se quiere y por qué, con las palabras de quien lo pide; el cómo vendrá después en la spec.

Inmediatamente después, en el mismo mensaje, pregunta:
1. Origen: idea propia, ticket/petición de cliente, o incidencia/alerta de producción.
2. Autor (nombre y rol/área) — si ya lo sabes por el contexto, propónlo y que lo confirme.
3. "Cuéntame el problema con tus palabras: qué no se puede hacer hoy, a quién afecta y cómo sería 'mejor'." Invita a pegar texto, ticket, correo o log si lo tiene.

Si el usuario ya adjunta material (ticket, email, alerta), extrae de ahí todo lo posible y pregunta solo los huecos.

### 1. Entrevista de analista (por bloques, no todo de golpe)
Haz las preguntas que haría un analista, agrupadas en 2–4 rondas como máximo, 2–4 preguntas por ronda. Salta lo ya respondido. Usa AskUserQuestion cuando haya opciones cerradas; texto libre en el resto.

- **Problema**: ¿Desde cuándo pasa? ¿Con qué frecuencia? ¿Coste o impacto medible (tiempo, dinero, errores, llamadas)? ¿Qué se hace hoy como parche?
- **Resultado que buscamos**: ¿Qué verá o podrá hacer el usuario cuando esté resuelto? ¿Cómo sabremos que ha funcionado (criterio de éxito/métrica)? ¿Qué queda explícitamente **fuera de alcance**?
- **A quién y a qué afecta**: ¿Quién lo usa, quién lo sufre, quién lo mantiene? ¿Qué sistemas, módulos, APIs, integraciones o equipos se tocan?
- **Restricciones**: datos personales/RGPD, seguridad y autenticación, normativa aplicable, plazos, presupuesto, tecnología obligada o vetada, compatibilidad con lo existente.
- **Preguntas abiertas**: ¿Qué no sabemos aún? ¿Qué decisión depende de otra persona?

Si una respuesta es vaga ("que vaya más rápido", "mejorar la experiencia"), repregunta una vez pidiendo un ejemplo concreto o una cifra. Si sigue vago, déjalo y anótalo como pregunta abierta.

Para origen **incidencia**: pide la evidencia (métrica, umbral superado, fecha, logs) y colócala en Problema.

### 2. Borrador
Cuando la idea sea concreta, genera el borrador con esta plantilla exacta:

```markdown
# Intent: <título corto, orientado al resultado>
Autor: <Nombre> (<rol/área>). Estado: borrador. Fecha: <AAAA-MM-DD>. Origen: <idea | ticket #… | incidencia …>

## Problema
<Qué pasa hoy, a quién y con qué impacto, cuantificado si es posible.>

## Resultado que buscamos
<Qué se verá/podrá hacer cuando esté resuelto. Criterio de éxito.>
<Fuera de alcance: … (solo si se ha definido)>

## A quién y a qué afecta
<Personas/roles, equipos, sistemas, módulos, APIs.>

## Restricciones
<Restricciones de datos, seguridad, normativa, plazo, tecnología.>

## Preguntas abiertas
<Una pregunta por línea; quién debería responderla si se sabe.>
```

Reglas del borrador:
- Usa exactamente esos cinco encabezados, en ese orden y con esa redacción.
- Si una sección no tiene contenido, escribe "Ninguna identificada." — nunca la elimines.
- No añadas secciones extra salvo que el usuario lo pida.
- Muestra el borrador en el chat.

### 3. Revisión del originador
Pregunta explícitamente: "¿Hay algo que haya entendido mal o que quieras matizar?". Señala en una línea los puntos más débiles (p. ej. resultado sin métrica, restricción ambigua). Aplica correcciones hasta que diga que está bien. No pases a spec ni a solución técnica.

### 4. Entrega
- En este repositorio (KOROSHI), el fichero se guarda en **`intent/<slug-del-cambio>/intent_AAAA-MM-DD.md`**. Nunca se sobrescribe: cada corrección posterior a la entrega es un fichero nuevo con su fecha (y hora `_HHMM` si hay dos el mismo día). Créalo con Write y entrégalo con SendUserFile. El responsable (Isaac) lo revisa y lo acepta o lo cierra.
- Si hay un conector de GitHub/GitLab o una carpeta del ordenador conectada y el usuario lo pide, ofrece guardarlo/commitearlo allí; pide confirmación antes de cualquier commit o escritura externa.
- Si existe un ticket o herramienta de origen (gestor de incidencias, CRM, herramienta de proyectos, etc.), sugiere anotar su ID en `Origen` y el enlace al fichero en el ticket (vinculación mínima entre fuente de verdad y markdown).
- Siguiente paso natural (una línea): una vez aceptado, el intent se usa como entrada para generar `spec.md`.

## Qué evitar
- Interrogatorios de 15 preguntas en un mensaje.
- Rellenar huecos con suposiciones presentadas como hechos.
- Convertir el intent en una especificación funcional o técnica.
- Cambiar Estado a algo distinto de `borrador`: la aprobación es del product owner.