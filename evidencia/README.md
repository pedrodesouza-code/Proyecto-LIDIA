# Evidencia EC3

Esta carpeta conserva solo evidencia liviana y reproducible. No contiene
datasets ni resultados afirmados sin ejecucion.

## Evidencia Local

Los tests unitarios validan reglas de calidad, idempotencia y CDC sin requerir
datos pesados. El resultado de la ejecucion realizada para preparar el aporte
se registra en `logs/validacion_local.txt`.

## Evidencia De Carga Real

`logs/carga_real_integrada.txt` registra la carga controlada ejecutada en UTEC
con archivos reales para FIRMS, CHIRPS, MODIS e INUMET, y APIs reales para
METEO y FORECAST. La geometria territorial usada para asignar pais a puntos
es un insumo auxiliar de transformacion y no se incorpora como fuente
analitica.

`logs/carga_real_firms_chirps.txt` corresponde a una corrida preliminar
reemplazada por la carga integrada y no describe el estado actual de la base.

## Evidencia Pendiente En UTEC

Tras configurar las conexiones y datos institucionales:

1. Ejecutar los DDL y guardar el registro de salida.
2. Ejecutar dos veces el ETL y exportar los conteos de `audit.etl_runs` y
   `audit.cdc_eventos`.
3. Capturar las vistas del dashboard alimentadas por PostgreSQL.
4. Registrar tiempo de carga, filas validas y rechazos por fuente.

No debe agregarse a Git evidencia que contenga passwords, tokens o datos raw.
