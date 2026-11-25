# Plan: preparar las SUMI con Lecturas en la PDA (v1, 25/11/2026)

**Por qué:** el 25/11 la SUMI de la K24 (OUT 27660) se metió en cajas a mano, con el usuario Almacén Nath y fuera de
Lecturas. La etiqueta CJ665013675 se pegó en una caja física pero nunca se leyó en Odoo: había 11 cajas físicas, y 10 en
Odoo y en la etiqueta XPO 121771366. Isaac quiere que las SUMI se hagan por Lecturas.

## Lo que hay hoy (leído en el código y en producción, sin cambiar nada)

- **Las OUT de SUMI son OUT normales:** tipo 45 «Órdenes de entrega», compañía 8 y origen `SUMINISTROS KOROSHI dd/mm Kxx`.
  No tienen agrupación. Desde el 01/11 hay 29, todas creadas por Departament IT desde el Excel de KOROSHI y todas hechas.
- **Lecturas ya acepta una OUT suelta por su nombre**, sin agrupación. `koroshi_preparacion/models/lectura.py:237-258`
  (`picking_propio`: compañía 8, salida y no hecha) y `controllers/main.py:55-60` (busca por nombre). No hay nada que
  excluya las SUMI.
- **Los artículos SUMI tienen EAN** (`8445962888xxx`, por ejemplo SUMI009 = 8445962888112), y Lecturas casa primero por
  EAN y después por referencia (`lectura.py:703-728`).
- **Caja en Lecturas:** se leen las prendas y la caja se cierra leyendo la CJ (`lectura.py:968-1037`, `put_in_pack` con
  ese nombre). No se puede validar con unidades sin caja (`lectura.py:1301-1311`). Cada CJ que existe en Odoo es una CJ
  leída, así que una etiqueta que no se lee no se convierte en caja: el fallo de la K24 se habría visto al cerrar.

## Recomendación

**Opción A (sin código, se puede probar ya): preparar las SUMI en Lecturas como una OUT suelta.**
1. En la PDA, en Lecturas, leer o escribir el nombre de la OUT de SUMI (por ejemplo `EFFEC/OUT/27660`).
2. Leer cada artículo por su EAN. Al acabar cada caja física, leer su CJ: así se cierra la caja.
3. Validar en Lecturas.
4. Después, Transportista, como siempre. Desde la 1.2.0 las OUT de SUMI salen marcadas como **SUMI**.

**Por comprobar antes de darlo por bueno (con una SUMI real y alguien delante; leer y deshacer no sirve, porque
validar no se deshace):**
- Que la pantalla de Lecturas (`static/src/js/preparacion.js`) no filtre la OUT antes de llegar al servidor.
- Que los EAN de las SUMI se lean bien en la PDA. Son de KOROSHI (prefijo 8445962), igual que la ropa.
- Que validar una OUT sin zona no pida nada de zonas: `_validar_out_de_zona` solo se usa con agrupación `Z-`.

**Opción B (solo si A no basta):** meter las SUMI del día en una agrupación «SUMI-ddmm» para que salgan en la lista de
tareas de Lecturas. Habría que cambiar `koroshi_preparacion`, que no es de esta sesión (regla 6), y sacar una versión
nueva. No hace falta para que funcione: solo ayuda a encontrarlas.

**Mientras tanto:** `koroshi_transportista` 1.4.0 avisa si la tienda tiene una CJ impresa con sus cajas que en Odoo está
vacía. En la K24 habría salido la CJ665013675.

## Qué hay que decidir

- Isaac: probar la opción A con la próxima SUMI y avisar a quien prepara los suministros de que se hacen por Lecturas.
