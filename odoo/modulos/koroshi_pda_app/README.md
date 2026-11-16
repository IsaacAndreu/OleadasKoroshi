# KOROSHI Lecturas PDA como app (v1.1.0, 16/11/2026)

> v1.1.0 (16/11/2026, auditoría 13/11, fase 6): la empresa sale de `koroshi_base.comun` (instalar koroshi_base
> antes). Misma app y mismas rutas.

Instala **Lecturas (PDA)** como una app en las PDA: un icono «Lecturas KOROSHI» en la pantalla de inicio que abre
directamente Lecturas, sin barra de direcciones ni pestañas de Chrome.

## En cada PDA (una vez)

0. El usuario tiene que estar en el parámetro **koroshi_pda_app.usuarios** (Ajustes → Técnico → Parámetros del
   sistema; ids separados por comas, `*` = todos). Al instalar el módulo vale `2` (**Departament IT**): se prueba con
   ese usuario antes de ponerlo en el de las PDA (Almacén Nath). Al resto de usuarios no les cambia nada.
1. Abrir Chrome en `https://nath.tuctuc.com` y entrar con ese usuario.
2. Menú **⋮** → **Instalar aplicación** (en algunas versiones, **Añadir a pantalla de inicio** → Instalar).
3. Sale el icono **Lecturas** en la pantalla de inicio. A partir de ahora se abre desde ahí.

Si Chrome solo ofrece «Crear acceso directo» y al abrirlo sale la barra de direcciones, cerrar Chrome del todo,
volver a abrir `nath.tuctuc.com`, esperar unos segundos y probar otra vez (la primera visita registra el service worker).

## Qué hace

| Ruta | Para qué |
|---|---|
| `/koroshi_pda/inicio` | Donde abre la app. Con sesión → Lecturas (`/web#cids=8&action=koroshi_operarios_pantalla`). Sin sesión → login de Odoo y, al entrar, Lecturas. |
| `/koroshi_pda/manifest.webmanifest` | Nombre, icono, colores, `display: standalone` (sin barra), `scope: /`. |
| `/koroshi_pda/sw.js` | Service worker vacío: no guarda nada en caché. Solo para que Chrome deje instalarla. Se registra solo en Android. |

Solo a los usuarios del parámetro, en las páginas de Odoo va el enlace al manifiesto (plantilla heredada de
`web.layout`). En un PC, Chrome puede enseñar a esos usuarios el icono de instalar en la barra de direcciones; no hace
falta usarlo.

No escribe nada en la base de datos (solo crea el parámetro al instalar).

## Acción inicial

Para que al entrar en Odoo (o si la sesión caduca y hay que volver a entrar) salga directamente Lecturas:
Ajustes → Usuarios → el usuario → Preferencias → **Acción inicial** = **Operarios** (la de Lecturas PDA).
Departament IT ya la tiene. En Almacén Nath, cuando se decida pasarlo a las PDA (11/11: aún no).
