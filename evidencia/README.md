# Evidencia EC3

Esta carpeta conserva solo evidencia liviana y reproducible. No contiene
datasets ni resultados afirmados sin ejecucion.

## Evidencia Local

Los tests unitarios validan reglas de calidad, idempotencia y CDC sin requerir
datos pesados. El resultado de la ejecucion realizada para preparar el aporte
se registra en `logs/validacion_local.txt`.

## Evidencia Pendiente En UTEC

Tras configurar las conexiones y datos institucionales:

1. Ejecutar los DDL y guardar el registro de salida.
2. Ejecutar dos veces el ETL y exportar los conteos de `audit.etl_runs` y
   `audit.cdc_eventos`.
3. Capturar las vistas del dashboard alimentadas por PostgreSQL.
4. Registrar tiempo de carga, filas validas y rechazos por fuente.

No debe agregarse a Git evidencia que contenga passwords, tokens o datos raw.
