# Instalar la PDA de Oriola en odoo.tuctuc.com (28/11/2026)

Seis módulos NUEVOS (en tuctuc no hay ningún `tuctuc_*`: comprobado el 28/11, solo lectura). Etiquetas en git y ZIP
sacados de la etiqueta con `bin/empaquetar.py`:

| Módulo | Versión | ZIP |
|---|---|---|
| tuctuc_base | 1.0.1 | `bin/20261128_tuctuc_base_v1.0.1.zip` |
| tuctuc_operarios | 1.0.1 | `bin/20261128_tuctuc_operarios_v1.0.1.zip` |
| tuctuc_faltantes | 1.0.2 | `bin/20261128_tuctuc_faltantes_v1.0.2.zip` |
| tuctuc_preparacion | 1.0.0 | `bin/20261128_tuctuc_preparacion_v1.0.0.zip` |
| tuctuc_contenedores | 1.0.0 | `bin/20261128_tuctuc_contenedores_v1.0.0.zip` |
| tuctuc_pda_app | 1.0.0 | `bin/20261128_tuctuc_pda_app_v1.0.0.zip` |

Lo hace el responsable (CLAUDE.md, regla 4): aquí no se sube, ni se instala, ni se reinicia nada.

## 1. Copiar al servidor de tuctuc

`desplegar.sh` trae por defecto las rutas de NATH: en tuctuc hay que darle las suyas. La ruta de addons propios de
tuctuc es la de `stock_barcode_optimization` (`/opt/tuctuc-erp/nath/custom_addons`); **comprobarla antes** con
`grep addons_path /opt/tuctuc-erp/tuctuc-erp.conf`.

```bash
export ADDONS_DIR=/opt/tuctuc-erp/nath/custom_addons
export ODOO_SERVICE=tuctuc-erp
export BACKUP_DIR=/opt/tuctuc-erp/copias_modulos
export ZIP_DIR=<carpeta donde se dejan los 6 ZIP>
bash desplegar.sh check tuctuc_base 1.0.1 tuctuc_operarios 1.0.1 tuctuc_faltantes 1.0.2 \
    tuctuc_preparacion 1.0.0 tuctuc_contenedores 1.0.0 tuctuc_pda_app 1.0.0
sudo -E AUTO_CONFIRM=1 bash desplegar.sh install tuctuc_base 1.0.1 tuctuc_operarios 1.0.1 tuctuc_faltantes 1.0.2 \
    tuctuc_preparacion 1.0.0 tuctuc_contenedores 1.0.0 tuctuc_pda_app 1.0.0
```

El `install` reinicia `tuctuc-erp` (~1 min): fuera de horas de tienda (el TPV de tuctuc va contra el mismo Odoo).
Después del reinicio, **reencolar los trabajos de queue_job que se queden en «started»** (pasó el 24/11).

## 2. Instalar en Odoo (Aplicaciones > Actualizar lista), en este orden

1. **TUCTUC Base**. Comprobar en Inventario > Configuración > **TUCTUC PDA: almacenes** que salen WH-OR (PRIME),
   MODAI (id 109, MODA INTIMA), UBRAN y MIECI (id 110, MODA INTIMA), NO los MODAI/MIECI de PRIME (251, 252), con
   SORTER en WH-OR y MODAI y zona N1 (MIECI, vacía).
2. **TUCTUC Operarios (Lecturas PDA)**.
3. **TUCTUC Faltantes (PDA)**. Comprobar que se han creado WH-OR/FALTANTE, MODAI/FALTANTE, UBRAN/FALTANTE y
   MIECI/FALTANTE (fuera de Stock) y que están en la tabla de almacenes.
4. **TUCTUC Preparación**.
5. **TUCTUC Contenedores**.
6. **TUCTUC Lecturas PDA como app**.

## 3. Configurar (a mano, después de instalar)

- **Operarios**: TUCTUC Operarios > Crear operarios, una línea por persona con el código de su tarjeta de NATH delante
  (`OP0007 Nombre Apellido`). La lista sale de NATH (Lecturas > Operarios); sin compañía.
- **Usuario de las PDA de Oriola**: con las compañías PRIME, MODA INTIMA y UNITED; Inventario / Usuario; Preferencias >
  Acción inicial = «Operarios».
- **App en la PDA**: parámetro `tuctuc_pda_app.usuarios` = id del usuario de prueba (después, el de las PDA).
- **Tarjeta obligatoria**: grupo «TUCTUC Operarios: tarjeta obligatoria» al usuario de las PDA cuando esté probado.
- Revisar parámetros (Ajustes > Técnico > Parámetros del sistema): `tuctuc_base.tipos_oleada`
  (WEB, WEB B&B, PED. INICIAL), `tuctuc_faltantes.correo_destinatarios`, `tuctuc_preparacion.embalajes` (vacío = los más
  usados), `tuctuc_contenedores.*` (muelle y cajas por columna, valores de NATH: confirmar en la nave).

## 4. Probar en una PDA de Oriola (solo pruebas reversibles en OUT reales)

1. Entrar por el icono «Lecturas Oriola»: tienen que estar las tres compañías marcadas.
2. Pasar una tarjeta OP creada con el mismo código que en NATH.
3. «Siguiente»: una OUT directa (B2B, REPETICIÓN, tiendas…), nunca una WEB / PED. INICIAL ni una que salga del SORTER.
4. Preparar: leer prendas, Caja eligiendo el embalaje (sale un BOX de Odoo con el embalaje), deshacer. **No validar**
   una OUT real salvo que el responsable lo diga.
5. Una INT de la estantería al SORTER: leer sin caja.
6. Faltante: reubicar una línea y deshacer en la oficina («Encontrado»).
7. Compactar: «Calcular» un lineal de WH-OR (solo mirar el plan) y leer un hueco con cajas de dos compañías.
8. % de faltante: «Recalcular» y apuntar cuánto tarda (stock_move de tuctuc es muy grande).
