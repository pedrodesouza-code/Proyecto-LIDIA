\pset pager off
\echo 'D4 - Validacion Change Data Capture Proyecto LIDIA'
\echo '1. Conteos de eventos CDC por fuente y tipo'
SELECT fuente,
       tipo_evento,
       COUNT(*)::bigint AS eventos,
       MIN(registrado_en) AS primer_evento,
       MAX(registrado_en) AS ultimo_evento
FROM audit.cdc_eventos
WHERE fuente IN ('FIRMS','METEO','CAMS','CHIRPS','MODIS','INUMET')
GROUP BY fuente, tipo_evento
ORDER BY fuente, tipo_evento;

\echo '2. Ultimas corridas CDC/control D4'
SELECT r.run_id::text,
       r.fuente,
       r.etapa,
       r.estado,
       r.filas_leidas,
       r.filas_insertadas,
       r.filas_actualizadas,
       r.filas_rechazadas,
       r.iniciado_en,
       r.finalizado_en,
       r.detalle
FROM audit.etl_runs r
WHERE r.detalle->>'criterio' = 'D4 CDC controlado'
   OR EXISTS (
       SELECT 1
       FROM audit.cdc_eventos e
       WHERE e.run_id = r.run_id
         AND e.detalle ? 'fase'
   )
ORDER BY r.iniciado_en DESC
LIMIT 20;

\echo '3. Registros nuevos detectados'
SELECT e.run_id::text,
       e.fuente,
       e.record_hash,
       e.detalle->>'natural_key' AS natural_key,
       e.detalle,
       e.registrado_en
FROM audit.cdc_eventos e
WHERE e.tipo_evento = 'alta'
ORDER BY e.registrado_en DESC
LIMIT 20;

\echo '4. Registros modificados detectados con hash anterior'
SELECT e.run_id::text,
       e.fuente,
       e.record_hash AS record_hash_nuevo,
       e.detalle->>'hash_anterior' AS record_hash_anterior,
       e.detalle->>'natural_key' AS natural_key,
       e.detalle,
       e.registrado_en
FROM audit.cdc_eventos e
WHERE e.tipo_evento = 'modificacion'
ORDER BY e.registrado_en DESC
LIMIT 20;

\echo '5. Registros sin cambio detectados'
SELECT e.run_id::text,
       e.fuente,
       e.record_hash,
       e.detalle->>'natural_key' AS natural_key,
       e.detalle,
       e.registrado_en
FROM audit.cdc_eventos e
WHERE e.tipo_evento = 'sin_cambio'
ORDER BY e.registrado_en DESC
LIMIT 20;

\echo '6. Registros rechazados CDC si existen'
SELECT e.fuente,
       e.detalle->>'motivo' AS motivo,
       COUNT(*)::bigint AS rechazos,
       MAX(e.registrado_en) AS ultimo_rechazo
FROM audit.cdc_eventos e
WHERE e.tipo_evento = 'rechazo'
GROUP BY e.fuente, e.detalle->>'motivo'
ORDER BY rechazos DESC, fuente
LIMIT 50;

\echo '7. Ausencia de duplicados por natural_key en staging/DW principal'
SELECT 'staging.stg_firms' AS tabla,
       COUNT(*)::bigint AS natural_keys_duplicadas
FROM (
    SELECT natural_key
    FROM staging.stg_firms
    GROUP BY natural_key
    HAVING COUNT(*) > 1
) d
UNION ALL
SELECT 'dw.fact_incendio' AS tabla,
       COUNT(*)::bigint AS natural_keys_duplicadas
FROM (
    SELECT natural_key
    FROM dw.fact_incendio
    GROUP BY natural_key
    HAVING COUNT(*) > 1
) d;

\echo '8. Comparacion record_hash antes/despues en modificaciones'
SELECT e.run_id::text,
       e.fuente,
       e.detalle->>'natural_key' AS natural_key,
       e.detalle->>'hash_anterior' AS record_hash_anterior,
       e.record_hash AS record_hash_nuevo,
       (e.detalle->>'hash_anterior') IS DISTINCT FROM e.record_hash AS hash_cambio,
       e.registrado_en
FROM audit.cdc_eventos e
WHERE e.tipo_evento = 'modificacion'
ORDER BY e.registrado_en DESC
LIMIT 20;

\echo '9. Impacto en PostgreSQL: auditoria, staging y fact_incendio'
SELECT 'audit.etl_runs D4' AS objeto,
       COUNT(*)::bigint AS filas
FROM audit.etl_runs
WHERE detalle->>'criterio' = 'D4 CDC controlado'
UNION ALL
SELECT 'audit.cdc_eventos D4',
       COUNT(*)::bigint
FROM audit.cdc_eventos
WHERE detalle ? 'fase'
UNION ALL
SELECT 'staging.stg_firms',
       COUNT(*)::bigint
FROM staging.stg_firms
UNION ALL
SELECT 'dw.fact_incendio',
       COUNT(*)::bigint
FROM dw.fact_incendio;

\echo '10. Trazabilidad por fuente, run_id y timestamp'
SELECT e.run_id::text,
       e.fuente,
       r.estado AS estado_run,
       e.tipo_evento,
       e.detalle->>'natural_key' AS natural_key,
       e.registrado_en
FROM audit.cdc_eventos e
JOIN audit.etl_runs r ON r.run_id = e.run_id
WHERE e.fuente IN ('FIRMS','METEO','CAMS','CHIRPS','MODIS','INUMET')
ORDER BY e.registrado_en DESC
LIMIT 50;
