-- =============================================================================
-- SINIA-UY — Seed: Puntos de Monitoreo (Uruguay + Brasil + Argentina + Chile)
-- =============================================================================
-- 36 puntos en 4 países:
--   - Uruguay completo: 19 departamentos representados por sus capitales.
--   - Brasil y Argentina: ciudades estrategicas por influencia regional.
--   - Chile: ciudades estrategicas + puntos volcanicos de impacto regional.
-- Período analítico: 2018-2025.
-- Idempotente: usa INSERT ... ON CONFLICT DO UPDATE para mantener el alcance vigente.
-- =============================================================================

INSERT INTO puntos_monitoreo (nombre, pais, region, latitud, longitud, activo)
VALUES
    -- ── Brasil (5 puntos — fuente principal de humo transfronterizo) ────────
    ('Cuiabá',       'BRA', 'Mato Grosso — corazón del Cerrado',           -15.60, -56.10, TRUE),
    ('Porto_Alegre', 'BRA', 'Rio Grande do Sul — frontera sur',            -30.03, -51.23, TRUE),
    ('Manaus',       'BRA', 'Amazonas — amazonia occidental',               -3.10, -60.02, TRUE),
    ('Campo_Grande', 'BRA', 'Mato Grosso do Sul — Pantanal',               -20.47, -54.62, TRUE),
    ('Brasília',     'BRA', 'Distrito Federal — Cerrado central',          -15.78, -47.93, TRUE),
    -- ── Argentina (4 puntos — norte y centro, frontera con Uruguay) ─────────
    ('Salta',        'ARG', 'NOA — yungas y chaco salteño',                -24.79, -65.41, TRUE),
    ('Posadas',      'ARG', 'Misiones — selva misionera limítrofe',        -27.37, -55.90, TRUE),
    ('Buenos_Aires', 'ARG', 'AMBA — frontera oeste con Uruguay',           -34.61, -58.37, TRUE),
    ('Mendoza',      'ARG', 'Cuyo — incendios de interfaz urbano-forestal',-32.89, -68.85, TRUE),
    -- ── Chile (8 puntos — volcanes, incendios y aerosoles transfronterizos) ──
    ('Santiago',              'CHL', 'Region Metropolitana — referencia nacional y calidad de aire',       -33.45, -70.66, TRUE),
    ('Temuco',                'CHL', 'La Araucania — zona forestal critica',                               -38.74, -72.59, TRUE),
    ('Valdivia',              'CHL', 'Los Rios — corredor volcanico del sur de Chile',                     -39.82, -73.24, TRUE),
    ('Osorno',                'CHL', 'Los Lagos — area afectada por Puyehue-Cordon Caulle',                -40.57, -73.13, TRUE),
    ('Puerto_Montt',          'CHL', 'Los Lagos — area de influencia del volcan Calbuco',                  -41.47, -72.94, TRUE),
    ('Coyhaique',             'CHL', 'Aysen — Patagonia y calidad de aire',                                -45.57, -72.07, TRUE),
    ('Puyehue_Cordon_Caulle', 'CHL', 'Complejo volcanico Puyehue-Cordon Caulle — erupcion 2011',           -40.59, -72.12, TRUE),
    ('Calbuco',               'CHL', 'Volcan Calbuco — erupcion 2015 con cenizas reportadas sobre Uruguay',-41.33, -72.61, TRUE),
    -- ── Uruguay (19 departamentos — cobertura nacional completa) ────────────
    ('Artigas',                'URY', 'Departamento Artigas — capital departamental',                  -30.40, -56.47, TRUE),
    ('Canelones',              'URY', 'Departamento Canelones — capital departamental',                -34.52, -56.28, TRUE),
    ('Melo',                   'URY', 'Departamento Cerro Largo — capital departamental',              -32.37, -54.18, TRUE),
    ('Colonia_del_Sacramento', 'URY', 'Departamento Colonia — capital departamental',                  -34.46, -57.84, TRUE),
    ('Durazno',                'URY', 'Departamento Durazno — capital departamental',                  -33.38, -56.52, TRUE),
    ('Trinidad',               'URY', 'Departamento Flores — capital departamental',                   -33.52, -56.90, TRUE),
    ('Florida',                'URY', 'Departamento Florida — capital departamental',                  -34.10, -56.21, TRUE),
    ('Minas',                  'URY', 'Departamento Lavalleja — capital departamental',                -34.38, -55.24, TRUE),
    ('Maldonado',              'URY', 'Departamento Maldonado — capital departamental',                -34.91, -54.96, TRUE),
    ('Montevideo',             'URY', 'Departamento Montevideo — capital nacional',                    -34.90, -56.19, TRUE),
    ('Paysandu',               'URY', 'Departamento Paysandu — capital departamental',                 -32.32, -58.08, TRUE),
    ('Fray_Bentos',            'URY', 'Departamento Rio Negro — capital departamental',                -33.13, -58.30, TRUE),
    ('Rivera',                 'URY', 'Departamento Rivera — sede UTEC y frontera con Brasil',         -30.91, -55.55, TRUE),
    ('Rocha',                  'URY', 'Departamento Rocha — capital departamental',                    -34.48, -54.33, TRUE),
    ('Salto',                  'URY', 'Departamento Salto — capital departamental',                    -31.38, -57.97, TRUE),
    ('San_Jose_de_Mayo',       'URY', 'Departamento San Jose — capital departamental',                 -34.34, -56.71, TRUE),
    ('Mercedes',               'URY', 'Departamento Soriano — capital departamental',                  -33.25, -58.03, TRUE),
    ('Tacuarembo',             'URY', 'Departamento Tacuarembo — capital departamental',               -31.73, -55.98, TRUE),
    ('Treinta_y_Tres',         'URY', 'Departamento Treinta y Tres — capital departamental',           -33.23, -54.38, TRUE)
ON CONFLICT (nombre) DO UPDATE SET
    pais = EXCLUDED.pais,
    region = EXCLUDED.region,
    latitud = EXCLUDED.latitud,
    longitud = EXCLUDED.longitud,
    activo = EXCLUDED.activo;

-- Verificación
SELECT id, nombre, pais, latitud, longitud
FROM puntos_monitoreo
ORDER BY pais, nombre;
