# Agente de impresión (portátil de Expediciones)

Escucha la cola de Odoo (`koroshi_impresion`) e imprime en la Zebra del portátil lo que se pida desde la PDA.
Diseño: `bin/versiones/diseno-imprimir-desde-pda_2026-11-25_v4.md`. Versión 1.0.0 (25/11/2026).

**Antes**: `koroshi_impresion` 1.0.0 instalado en Odoo (crea la impresora `EXP1`).

## Instalar en el portátil (una vez, ~15 min)

1. **Python 3** (python.org, Windows installer 64-bit). En la primera pantalla marcar **«Add python.exe to PATH»**.
   No hace falta instalar nada con pip.
2. **Carpeta** `C:\KoroshiImpresion` con:
   - `agente_impresion.py`, `config.ejemplo.ini` e `instalar_tarea.ps1` (de esta carpeta del repo);
   - **SumatraPDF portable** (sumatrapdfreader.org → Download → «portable version» 64-bit), renombrado a
     `C:\KoroshiImpresion\SumatraPDF.exe`.
3. **Config**: copiar `config.ejemplo.ini` como `config.ini` y poner el **login de Almacén Nath** en `usuario`.
   Para el nombre de la Zebra, en PowerShell:
   ```powershell
   cd C:\KoroshiImpresion; python agente_impresion.py --impresoras
   ```
   y copiar el nombre exacto (p. ej. `ZDesigner ZD420-203dpi ZPL`) en `nombre_windows`.
4. **Contraseña** de Almacén Nath en el Administrador de credenciales de Windows (la pide sin enseñarla; no se
   guarda en ningún fichero). Cambiar `LOGIN` por el mismo login del paso 3:
   ```powershell
   cmdkey /generic:koroshi-impresion-odoo /user:LOGIN /pass
   ```
   Si un día se cambia la contraseña de Almacén Nath, repetir este paso (y reiniciar la tarea).
5. **Comprobar** (entra en Odoo y mira la impresora; no imprime nada):
   ```powershell
   python agente_impresion.py --comprobar
   ```
6. **Probar el papel 4x6** con una etiqueta ya hecha (bajar de una OUT un `LabelXPO_...pdf` o `gls_label_...pdf`):
   ```powershell
   python agente_impresion.py --probar C:\ruta\LabelXPO_xxx.pdf
   ```
   Si sale pequeña, cortada o girada: en Windows, Preferencias de impresión de la Zebra → papel 4x6 (101,6 x 152,4 mm).
7. **Arranque automático** (PowerShell **como administrador**):
   ```powershell
   cd C:\KoroshiImpresion; powershell -ExecutionPolicy Bypass -File .\instalar_tarea.ps1
   ```
   Crea la tarea «KOROSHI agente de impresion» (al iniciar sesión, se relanza si se cae) y la arranca.
8. En Odoo, Inventario > Configuración > Impresión > Impresoras: `EXP1` tiene que salir **Conectada**.

## Día a día

- El portátil tiene que estar encendido y con la sesión abierta. Si está apagado, los trabajos esperan en la cola y
  salen al encenderlo; la PDA avisa de que no está conectado.
- Log: `C:\KoroshiImpresion\log\agente.log` (se guardan 14 días).
- Errores (sin papel, impresora apagada): en Odoo, Cola de impresión → filtro «Con error» → «Reintentar».
- Si se queda colgado: Programador de tareas → «KOROSHI agente de impresion» → Finalizar y Ejecutar.
