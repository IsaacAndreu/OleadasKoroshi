# KOROSHI Traspasos S4T (v1.3, 19/11/2026)

Descarga de S4T las devoluciones e-commerce (`/transfers/return-ecommerce`) y las correcciones
(`/transfers/corrections`). Cada devolución crea una recepción DEV de 6665 lista para validar; las correcciones solo
se registran. **Sin instalar**; al instalar, el cron queda archivado: primera descarga con «Ejecutar manualmente».

## v1.3 (19/11/2026, puesta en marcha)

- Parámetro `koroshi_s4t_traspasos.modo`. Al instalar queda en `guardar`: el cron descarga y guarda, pero **no crea
  DEV**. Con `real`, crea la DEV de cada devolución e-commerce.
- Botón «Sin DEV» (estado «Sin DEV (descartado)») para las que no deben crear recepción.
- «Recuperar por fecha» ya no procesa todos los nuevos: solo los que acaba de guardar y solo en modo real.

Puesta en marcha: instalar → «Ejecutar manualmente» el cron (guarda todo lo pendiente desde el 01/07) → revisar la
lista y marcar «Sin DEV» las que ya se recibieron → poner `modo` = `real` → activar el cron.

## v1.2 (16/11/2026, auditoría 13/11, fase 6)

- Empresa y hora del almacén salen de `koroshi_base.comun` (instalar koroshi_base antes). Mismo resultado.

## v1.1 (14/11/2026, auditoría 13/11, fase 3)

- Cada traspaso se guarda en su propio savepoint y **primero el JSON crudo**. Si uno trae algo raro, se queda guardado
  en «Error» con su JSON y el resto de la página sigue. Antes fallaba la página entera y, como S4T ya la había marcado
  como descargada, se perdía.
- **Conciliación diaria**: una vez al día, desde `koroshi_s4t_traspasos.hora_conciliacion` (06:00 si no está), se
  vuelven a pedir por fecha los de hoy y ayer y se guardan los que falten (`koroshi_s4t_traspasos.ultima_conciliacion`).
- Los que dan **error** al procesar se reintentan en cada pasada, hasta 5 veces (campo Intentos).
- «Recuperar por fecha» daba error al acabar (`display_notification` no existe en Odoo 13): ahora abre la lista.

## v1.0 (12/11/2026)

Primera versión.
