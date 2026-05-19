-- =============================================================================
-- SINIA-UY — Limpieza de datos de países fuera del alcance reducido
-- =============================================================================
-- Tras definir el alcance del proyecto como Uruguay + Brasil + Argentina + Chile,
-- este script elimina de la BD los registros cargados de Bolivia, Paraguay,
-- Perú y otros países fuera del alcance final.
--
-- Ejecutar UNA SOLA VEZ después de cambiar el alcance.
-- Idempotente: re-ejecutarlo no hace nada porque los datos ya no están.
--
-- Modo seguro: cada paso muestra un COUNT antes y después.
-- Para ejecutar SIN borrar (solo previsualizar), cambiá BEGIN; ... COMMIT;
-- por BEGIN; ... ROLLBACK;
-- =============================================================================

\echo '── Conteo previo ──────────────────────────────────────────────────────'

SELECT 'paises_referencia (total)' AS tabla, COUNT(*) AS filas
FROM paises_referencia
UNION ALL
SELECT 'puntos_monitoreo (total)', COUNT(*) FROM puntos_monitoreo
UNION ALL
SELECT 'puntos a borrar (no URY/BRA/ARG/CHL)', COUNT(*)
FROM puntos_monitoreo WHERE pais NOT IN ('URY','BRA','ARG','CHL')
UNION ALL
SELECT 'focos_calor (total)', COUNT(*) FROM focos_calor
UNION ALL
SELECT 'focos a borrar (no URY/BRA/ARG/CHL o NULL)', COUNT(*)
FROM focos_calor WHERE pais NOT IN ('URY','BRA','ARG','CHL') OR pais IS NULL
UNION ALL
SELECT 'meteo_diario (total)', COUNT(*) FROM meteo_diario
UNION ALL
SELECT 'calidad_aire_diario (total)', COUNT(*) FROM calidad_aire_diario;

\echo ''
\echo '── Iniciando limpieza en transacción ─────────────────────────────────'

BEGIN;

-- ── 1. Hechos que dependen de id_punto ───────────────────────────────────
-- Borramos primero los hechos para no violar las FK contra puntos_monitoreo.

DELETE FROM cobertura_vegetal
WHERE id_punto IN (
    SELECT id FROM puntos_monitoreo WHERE pais NOT IN ('URY','BRA','ARG','CHL')
);

DELETE FROM precipitacion_mensual
WHERE id_punto IN (
    SELECT id FROM puntos_monitoreo WHERE pais NOT IN ('URY','BRA','ARG','CHL')
);

DELETE FROM calidad_aire_diario
WHERE id_punto IN (
    SELECT id FROM puntos_monitoreo WHERE pais NOT IN ('URY','BRA','ARG','CHL')
);

DELETE FROM meteo_diario
WHERE id_punto IN (
    SELECT id FROM puntos_monitoreo WHERE pais NOT IN ('URY','BRA','ARG','CHL')
);

-- ── 2. focos_calor (no tiene FK a puntos, se borra por columna pais) ────
-- Incluimos pais IS NULL por si quedaron focos fuera del bbox sin asignar.

DELETE FROM focos_calor
WHERE pais NOT IN ('URY','BRA','ARG','CHL') OR pais IS NULL;

-- ── 3. Dimensiones ───────────────────────────────────────────────────────

DELETE FROM puntos_monitoreo
WHERE pais NOT IN ('URY','BRA','ARG','CHL');

DELETE FROM paises_referencia
WHERE codigo_iso3 NOT IN ('URY','BRA','ARG','CHL');

-- Asegurar que los 4 países objetivo están presentes (idempotente).
INSERT INTO paises_referencia (codigo_iso3, codigo_iso2, nombre) VALUES
    ('URY', 'UY', 'Uruguay'),
    ('BRA', 'BR', 'Brasil'),
    ('ARG', 'AR', 'Argentina'),
    ('CHL', 'CL', 'Chile')
ON CONFLICT (codigo_iso3) DO NOTHING;

COMMIT;

\echo ''
\echo '── Conteo posterior ──────────────────────────────────────────────────'

SELECT 'paises_referencia' AS tabla, COUNT(*) AS filas FROM paises_referencia
UNION ALL
SELECT 'puntos_monitoreo', COUNT(*) FROM puntos_monitoreo
UNION ALL
SELECT 'focos_calor', COUNT(*) FROM focos_calor
UNION ALL
SELECT 'meteo_diario', COUNT(*) FROM meteo_diario
UNION ALL
SELECT 'calidad_aire_diario', COUNT(*) FROM calidad_aire_diario
UNION ALL
SELECT 'precipitacion_mensual', COUNT(*) FROM precipitacion_mensual
UNION ALL
SELECT 'cobertura_vegetal', COUNT(*) FROM cobertura_vegetal;

\echo ''
\echo '── Verificación: distribución por país ───────────────────────────────'

SELECT pais, COUNT(*) AS focos
FROM focos_calor
GROUP BY pais
ORDER BY focos DESC;

SELECT pais, COUNT(*) AS puntos
FROM puntos_monitoreo
GROUP BY pais
ORDER BY pais;
