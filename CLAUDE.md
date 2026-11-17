# CLAUDE.md — Almacén KOROSHI (Odoo 13 EE)

Módulos Odoo 13 Enterprise del almacén KOROSHI (Effective Logistics, compañía 8, NAU-2), en producción en
nath.tuctuc.com. Los operarios preparan pedidos con PDA todo el día: cualquier fallo se nota en el almacén al
momento. El mapa de módulos y el despliegue están en [README.md](README.md).

**Trabajo en curso**: corrección por fases de la auditoría del 13/11/2026. Estado y fases que quedan en
[TRASPASO_AUDITORIA.md](TRASPASO_AUDITORIA.md): leerlo antes de seguir.

## Reglas (no negociables)

1. **Todo en castellano**: código, comentarios, textos de pantalla, README, commits y mensajes.
2. **Nunca sobrescribir una versión.** Cada cambio:
   - sube la versión del `__manifest__.py`,
   - añade su línea al historial del manifest (`vX.Y.Z (dd/mm/aaaa): qué cambia y por qué`),
   - se commitea y se empaqueta con `python bin/empaquetar.py <modulo>`: etiqueta `<modulo>/vX.Y.Z` (anotada, **nunca
     se mueve ni se borra**) y ZIP `bin/AAAAMMDD_<modulo>_vX.Y.Z.zip` sacado de la etiqueta con `git archive`. Nunca
     con `Compress-Archive` (rompe las rutas en Linux). Los ZIP, APK y fotos no van en git (`.gitignore`).
   - `empaquetar.py` pasa antes `bin/comprobar.py` (reglas 2, 7 y 9 como comprobaciones). Si para, se arregla el
     código; no se esquiva. Cada trampa nueva que aparezca se añade allí, no solo aquí.
   - Se instala con `bin/desplegar.sh check|install <modulo> <version> ...`: ya no se escribe un script por versión
     (desde el 14/11/2026, fase 6).
3. **El servidor puede ir por delante del repo**: antes de sacar una versión, preguntar la `installed_version`
   real del módulo.
4. **No se instala, ni se sube, ni se reinicia nada en el servidor.** Se dejan el ZIP y el script listos y se
   avisa; la instalación la hace el responsable.
5. **No tocar datos de producción.** Si hacen falta datos reales para decidir, pedirlos.
6. **Un módulo, una sesión.** Un módulo solo se trabaja en una sesión a la vez. Si un cambio toca dos módulos,
   decirlo antes de empezar.
7. **Campos nuevos en tablas compartidas** (`stock.picking`, `stock.picking.type`, `stock.move.line`):
   prohibido sin preguntar. Ya tumbaron la PDA una vez (`no_overscan` en `stock.picking.type`, 03/11).
8. **Lo común va en `koroshi_base`** (`from odoo.addons.koroshi_base import comun`): compañía, hora del almacén,
   rangos de días en UTC y matrícula CJ. No copiar constantes nuevas en cada módulo. Los módulos que aún no lo usan
   se pasan uno a uno, cada uno con su versión.
9. **Trampas de Odoo 13**:
   - `aria-hidden="true"` oculta el elemento (regla global `display:none`): usar `role="presentation"`.
   - La acción cliente `display_notification` no existe.
   - Los `<function>` con `noupdate` solo corren al **instalar**, no al actualizar.
   - El `report_name` de un informe QWeb debe llevar punto (`modulo.plantilla`).
10. **Antes de cambiar algo**, leer el código y confirmar que el fallo existe tal como se describe. Si no se
   puede confirmar, decirlo en vez de arreglarlo a ciegas.
11. **Cada fase/entrega acaba con**: qué se ha cambiado (`archivo:línea`), cómo se ha probado, qué no se ha
    podido probar y qué hay que probar en una PDA real. Después, parar y esperar el visto bueno.

## Secretos

`App.config`, `bin/Release/PedidosMultiples.exe.Config` y varios `.cs` de `PedidosMultiples/` tienen
credenciales versionadas (pendientes de rotar). **No copiarlas, no moverlas y no añadir otras.** En los módulos
Odoo las claves se leen de la configuración del servidor (p. ej. `s4t.config`), nunca del código.

## Pruebas reales

En OUT reales solo pruebas reversibles: leer y deshacer, sin cerrar cajas ni validar.
