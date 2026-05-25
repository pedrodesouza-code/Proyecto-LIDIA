-- =============================================================================
-- SINIA-SA - DDL MySQL 8.0 - Data Warehouse analitico
-- =============================================================================
-- Alcance espacial: America del Sur
-- Alcance temporal analitico: 2018-2025
--
-- Modelo dimensional propuesto para el informe:
--   Dimensiones conformadas:
--     - dim_tiempo
--     - dim_pais
--     - dim_grilla
--     - dim_cobertura
--   Tablas de hechos:
--     - fact_incendios_diario
--     - fact_meteorologia_diaria
--     - fact_calidad_aire_diaria
--     - fact_precipitacion_mensual
--     - fact_cobertura_vegetal_anual
--
-- Criterios de diseno:
--   - Grano explicito por tabla de hechos
--   - Integracion espacial mediante grilla comun de 0.25 grados
--   - Idempotencia mediante claves unicas compuestas por grano analitico
--   - Trazabilidad mediante lote_hash y timestamps de carga
-- =============================================================================

CREATE DATABASE IF NOT EXISTS sinia_sa_dw
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE sinia_sa_dw;

-- =============================================================================
-- DIMENSIONES
-- =============================================================================

CREATE TABLE IF NOT EXISTS dim_tiempo (
    tiempo_key       INT          NOT NULL PRIMARY KEY COMMENT 'Formato yyyymmdd',
    fecha            DATE         NOT NULL UNIQUE,
    anio             SMALLINT     NOT NULL,
    semestre         TINYINT      NOT NULL,
    trimestre        TINYINT      NOT NULL,
    mes              TINYINT      NOT NULL,
    nombre_mes       VARCHAR(15)  NOT NULL,
    dia              TINYINT      NOT NULL,
    dia_anio         SMALLINT     NOT NULL,
    semana_anio      TINYINT      NOT NULL,
    es_fin_semana    BOOLEAN      NOT NULL DEFAULT FALSE,
    nivel_temporal   ENUM('diario', 'mensual', 'anual') NOT NULL DEFAULT 'diario',
    CHECK (anio BETWEEN 2018 AND 2025),
    CHECK (semestre BETWEEN 1 AND 2),
    CHECK (trimestre BETWEEN 1 AND 4),
    CHECK (mes BETWEEN 1 AND 12),
    CHECK (dia BETWEEN 1 AND 31)
) ENGINE=InnoDB COMMENT='Dimension tiempo para hechos diarios, mensuales y anuales';


CREATE TABLE IF NOT EXISTS dim_pais (
    pais_key         SMALLINT     NOT NULL AUTO_INCREMENT PRIMARY KEY,
    codigo_iso3      CHAR(3)      NOT NULL UNIQUE,
    codigo_iso2      CHAR(2)      NOT NULL UNIQUE,
    nombre_pais      VARCHAR(60)  NOT NULL,
    subregion        VARCHAR(40)  NOT NULL DEFAULT 'America del Sur',
    activo           BOOLEAN      NOT NULL DEFAULT TRUE
) ENGINE=InnoDB COMMENT='Dimension pais para comparaciones regionales';


CREATE TABLE IF NOT EXISTS dim_grilla (
    grilla_key          INT           NOT NULL AUTO_INCREMENT PRIMARY KEY,
    celda_id            VARCHAR(32)   NOT NULL UNIQUE,
    resolucion_grados   DECIMAL(4,2)  NOT NULL DEFAULT 0.25,
    lat_centro          DECIMAL(8,4)  NOT NULL,
    lon_centro          DECIMAL(8,4)  NOT NULL,
    lat_min             DECIMAL(8,4)  NOT NULL,
    lat_max             DECIMAL(8,4)  NOT NULL,
    lon_min             DECIMAL(8,4)  NOT NULL,
    lon_max             DECIMAL(8,4)  NOT NULL,
    pais_dominante_key  SMALLINT      NULL,
    porcentaje_tierra   DECIMAL(5,2)  NULL,
    CONSTRAINT fk_dim_grilla_pais
        FOREIGN KEY (pais_dominante_key) REFERENCES dim_pais (pais_key),
    CHECK (lat_centro BETWEEN -90.0000 AND 90.0000),
    CHECK (lon_centro BETWEEN -180.0000 AND 180.0000),
    CHECK (lat_min <= lat_max),
    CHECK (lon_min <= lon_max)
) ENGINE=InnoDB COMMENT='Dimension espacial armonizada en grilla regular de 0.25 grados';


CREATE TABLE IF NOT EXISTS dim_cobertura (
    cobertura_key        SMALLINT      NOT NULL AUTO_INCREMENT PRIMARY KEY,
    codigo_igbp          SMALLINT      NOT NULL UNIQUE,
    descripcion          VARCHAR(80)   NOT NULL,
    grupo_combustible    VARCHAR(40)   NOT NULL,
    indice_combustible   DECIMAL(5,2)  NOT NULL,
    es_antrpica          BOOLEAN       NOT NULL DEFAULT FALSE
) ENGINE=InnoDB COMMENT='Dimension de clases MODIS IGBP';


-- =============================================================================
-- HECHOS
-- =============================================================================

CREATE TABLE IF NOT EXISTS fact_incendios_diario (
    incendio_diario_key      BIGINT         NOT NULL AUTO_INCREMENT PRIMARY KEY,
    tiempo_key               INT            NOT NULL,
    grilla_key               INT            NOT NULL,
    pais_key                 SMALLINT       NOT NULL,
    cantidad_focos           INT            NOT NULL DEFAULT 0,
    focos_confianza_alta     INT            NOT NULL DEFAULT 0,
    focos_diurnos            INT            NOT NULL DEFAULT 0,
    focos_nocturnos          INT            NOT NULL DEFAULT 0,
    frp_total_mw             DECIMAL(16,3)  NULL,
    frp_promedio_mw          DECIMAL(12,3)  NULL,
    frp_max_mw               DECIMAL(12,3)  NULL,
    densidad_focos_km2       DECIMAL(12,6)  NULL,
    fuente                   VARCHAR(30)    NOT NULL DEFAULT 'NASA_FIRMS',
    lote_hash                CHAR(64)       NOT NULL,
    cargado_en               TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_fact_incendios_diario
        UNIQUE (tiempo_key, grilla_key, pais_key),
    CONSTRAINT fk_incendios_tiempo
        FOREIGN KEY (tiempo_key) REFERENCES dim_tiempo (tiempo_key),
    CONSTRAINT fk_incendios_grilla
        FOREIGN KEY (grilla_key) REFERENCES dim_grilla (grilla_key),
    CONSTRAINT fk_incendios_pais
        FOREIGN KEY (pais_key) REFERENCES dim_pais (pais_key),
    CHECK (cantidad_focos >= 0),
    CHECK (focos_confianza_alta >= 0),
    CHECK (focos_diurnos >= 0),
    CHECK (focos_nocturnos >= 0)
) ENGINE=InnoDB COMMENT='Hecho diario agregado de focos de calor por celda y pais';


CREATE TABLE IF NOT EXISTS fact_meteorologia_diaria (
    meteorologia_diaria_key          BIGINT         NOT NULL AUTO_INCREMENT PRIMARY KEY,
    tiempo_key                       INT            NOT NULL,
    grilla_key                       INT            NOT NULL,
    pais_key                         SMALLINT       NOT NULL,
    temperatura_max_c                DECIMAL(6,2)  NULL,
    temperatura_min_c                DECIMAL(6,2)  NULL,
    temperatura_media_c              DECIMAL(6,2)  NULL,
    humedad_relativa_min_pct         DECIMAL(6,2)  NULL,
    humedad_relativa_media_pct       DECIMAL(6,2)  NULL,
    viento_max_kmh                   DECIMAL(6,2)  NULL,
    precipitacion_diaria_mm          DECIMAL(8,2)  NULL,
    presion_media_hpa                DECIMAL(8,2)  NULL,
    et0_mm                           DECIMAL(8,3)  NULL,
    riesgo_temp                      DECIMAL(6,4)  NULL,
    riesgo_humedad                   DECIMAL(6,4)  NULL,
    riesgo_viento                    DECIMAL(6,4)  NULL,
    riesgo_sequia                    DECIMAL(6,4)  NULL,
    indice_riesgo                    DECIMAL(6,4)  NULL,
    nivel_riesgo                     ENUM('bajo', 'moderado', 'alto', 'muy_alto') NULL,
    fuente                           VARCHAR(30)   NOT NULL DEFAULT 'OPEN_METEO_ERA5_LAND',
    lote_hash                        CHAR(64)      NOT NULL,
    cargado_en                       TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en                   TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_fact_meteorologia_diaria
        UNIQUE (tiempo_key, grilla_key, pais_key),
    CONSTRAINT fk_meteorologia_tiempo
        FOREIGN KEY (tiempo_key) REFERENCES dim_tiempo (tiempo_key),
    CONSTRAINT fk_meteorologia_grilla
        FOREIGN KEY (grilla_key) REFERENCES dim_grilla (grilla_key),
    CONSTRAINT fk_meteorologia_pais
        FOREIGN KEY (pais_key) REFERENCES dim_pais (pais_key),
    CHECK (indice_riesgo IS NULL OR indice_riesgo BETWEEN 0 AND 1)
) ENGINE=InnoDB COMMENT='Hecho diario meteorologico integrado por celda y pais';


CREATE TABLE IF NOT EXISTS fact_calidad_aire_diaria (
    calidad_aire_diaria_key          BIGINT         NOT NULL AUTO_INCREMENT PRIMARY KEY,
    tiempo_key                       INT            NOT NULL,
    grilla_key                       INT            NOT NULL,
    pais_key                         SMALLINT       NOT NULL,
    pm10_media_ug_m3                 DECIMAL(10,3) NULL,
    pm10_max_ug_m3                   DECIMAL(10,3) NULL,
    pm10_p95_ug_m3                   DECIMAL(10,3) NULL,
    pm2_5_media_ug_m3                DECIMAL(10,3) NULL,
    pm2_5_max_ug_m3                  DECIMAL(10,3) NULL,
    aerosol_optical_depth_media      DECIMAL(10,5) NULL,
    aqi_europeo_medio                DECIMAL(8,2)  NULL,
    aqi_europeo_max                  DECIMAL(8,2)  NULL,
    horas_validas                    TINYINT       NULL,
    supera_umbral_oms_pm10           BOOLEAN       NOT NULL DEFAULT FALSE,
    nivel_pm10                       ENUM('normal', 'elevado', 'alerta') NULL,
    fuente                           VARCHAR(30)   NOT NULL DEFAULT 'CAMS_OPEN_METEO',
    lote_hash                        CHAR(64)      NOT NULL,
    cargado_en                       TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en                   TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_fact_calidad_aire_diaria
        UNIQUE (tiempo_key, grilla_key, pais_key),
    CONSTRAINT fk_calidad_aire_tiempo
        FOREIGN KEY (tiempo_key) REFERENCES dim_tiempo (tiempo_key),
    CONSTRAINT fk_calidad_aire_grilla
        FOREIGN KEY (grilla_key) REFERENCES dim_grilla (grilla_key),
    CONSTRAINT fk_calidad_aire_pais
        FOREIGN KEY (pais_key) REFERENCES dim_pais (pais_key),
    CHECK (horas_validas IS NULL OR horas_validas BETWEEN 0 AND 24)
) ENGINE=InnoDB COMMENT='Hecho diario de calidad del aire agregado por celda y pais';


CREATE TABLE IF NOT EXISTS fact_precipitacion_mensual (
    precipitacion_mensual_key        BIGINT         NOT NULL AUTO_INCREMENT PRIMARY KEY,
    tiempo_key                       INT            NOT NULL COMMENT 'Primer dia del mes',
    grilla_key                       INT            NOT NULL,
    pais_key                         SMALLINT       NOT NULL,
    precipitacion_total_mm           DECIMAL(10,2)  NULL,
    anomalia_pct                     DECIMAL(8,2)   NULL,
    categoria_sequia                 ENUM('extrema', 'severa', 'moderada', 'normal', 'humeda') NULL,
    fuente                           VARCHAR(30)    NOT NULL DEFAULT 'CHIRPS',
    lote_hash                        CHAR(64)       NOT NULL,
    cargado_en                       TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_fact_precipitacion_mensual
        UNIQUE (tiempo_key, grilla_key, pais_key),
    CONSTRAINT fk_precipitacion_tiempo
        FOREIGN KEY (tiempo_key) REFERENCES dim_tiempo (tiempo_key),
    CONSTRAINT fk_precipitacion_grilla
        FOREIGN KEY (grilla_key) REFERENCES dim_grilla (grilla_key),
    CONSTRAINT fk_precipitacion_pais
        FOREIGN KEY (pais_key) REFERENCES dim_pais (pais_key)
) ENGINE=InnoDB COMMENT='Hecho mensual de precipitacion armonizado por celda y pais';


CREATE TABLE IF NOT EXISTS fact_cobertura_vegetal_anual (
    cobertura_vegetal_anual_key      BIGINT         NOT NULL AUTO_INCREMENT PRIMARY KEY,
    tiempo_key                       INT            NOT NULL COMMENT 'Primer dia del anio',
    grilla_key                       INT            NOT NULL,
    pais_key                         SMALLINT       NOT NULL,
    cobertura_key                    SMALLINT       NOT NULL,
    porcentaje_clase_dominante       DECIMAL(5,2)   NULL,
    cambio_interanual                BOOLEAN        NOT NULL DEFAULT FALSE,
    fuente                           VARCHAR(40)    NOT NULL DEFAULT 'MODIS_MCD12Q1_APPEEARS',
    lote_hash                        CHAR(64)       NOT NULL,
    cargado_en                       TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_fact_cobertura_vegetal_anual
        UNIQUE (tiempo_key, grilla_key, pais_key),
    CONSTRAINT fk_cobertura_tiempo
        FOREIGN KEY (tiempo_key) REFERENCES dim_tiempo (tiempo_key),
    CONSTRAINT fk_cobertura_grilla
        FOREIGN KEY (grilla_key) REFERENCES dim_grilla (grilla_key),
    CONSTRAINT fk_cobertura_pais
        FOREIGN KEY (pais_key) REFERENCES dim_pais (pais_key),
    CONSTRAINT fk_cobertura_dimension
        FOREIGN KEY (cobertura_key) REFERENCES dim_cobertura (cobertura_key)
) ENGINE=InnoDB COMMENT='Hecho anual de cobertura vegetal dominante por celda y pais';


-- =============================================================================
-- INDICES ANALITICOS
-- =============================================================================

CREATE INDEX idx_tiempo_anio_mes ON dim_tiempo (anio, mes, fecha);
CREATE INDEX idx_grilla_pais ON dim_grilla (pais_dominante_key, lat_centro, lon_centro);

CREATE INDEX idx_fact_incendios_pais_tiempo ON fact_incendios_diario (pais_key, tiempo_key);
CREATE INDEX idx_fact_incendios_grilla_tiempo ON fact_incendios_diario (grilla_key, tiempo_key);

CREATE INDEX idx_fact_meteo_pais_tiempo ON fact_meteorologia_diaria (pais_key, tiempo_key);
CREATE INDEX idx_fact_meteo_riesgo ON fact_meteorologia_diaria (nivel_riesgo, tiempo_key);

CREATE INDEX idx_fact_calidad_pais_tiempo ON fact_calidad_aire_diaria (pais_key, tiempo_key);
CREATE INDEX idx_fact_calidad_alerta ON fact_calidad_aire_diaria (supera_umbral_oms_pm10, tiempo_key);

CREATE INDEX idx_fact_precipitacion_pais_tiempo ON fact_precipitacion_mensual (pais_key, tiempo_key);
CREATE INDEX idx_fact_cobertura_pais_tiempo ON fact_cobertura_vegetal_anual (pais_key, tiempo_key);


-- =============================================================================
-- VISTAS ANALITICAS
-- =============================================================================

CREATE OR REPLACE VIEW vw_focos_por_pais_mes AS
SELECT
    p.nombre_pais,
    t.anio,
    t.mes,
    SUM(f.cantidad_focos) AS total_focos,
    ROUND(AVG(f.frp_promedio_mw), 3) AS frp_promedio_mw,
    MAX(f.frp_max_mw) AS frp_max_mw,
    SUM(f.focos_confianza_alta) AS focos_confianza_alta
FROM fact_incendios_diario f
JOIN dim_tiempo t ON t.tiempo_key = f.tiempo_key
JOIN dim_pais p ON p.pais_key = f.pais_key
GROUP BY p.nombre_pais, t.anio, t.mes;


CREATE OR REPLACE VIEW vw_riesgo_por_pais_mes AS
SELECT
    p.nombre_pais,
    t.anio,
    t.mes,
    ROUND(AVG(m.indice_riesgo), 4) AS riesgo_promedio,
    ROUND(MAX(m.indice_riesgo), 4) AS riesgo_maximo,
    SUM(CASE WHEN m.nivel_riesgo IN ('alto', 'muy_alto') THEN 1 ELSE 0 END) AS dias_criticos
FROM fact_meteorologia_diaria m
JOIN dim_tiempo t ON t.tiempo_key = m.tiempo_key
JOIN dim_pais p ON p.pais_key = m.pais_key
GROUP BY p.nombre_pais, t.anio, t.mes;


CREATE OR REPLACE VIEW vw_alertas_calidad_aire AS
SELECT
    p.nombre_pais,
    t.fecha,
    g.celda_id,
    c.pm10_media_ug_m3,
    c.pm2_5_media_ug_m3,
    c.aqi_europeo_medio,
    c.nivel_pm10
FROM fact_calidad_aire_diaria c
JOIN dim_tiempo t ON t.tiempo_key = c.tiempo_key
JOIN dim_pais p ON p.pais_key = c.pais_key
JOIN dim_grilla g ON g.grilla_key = c.grilla_key
WHERE c.supera_umbral_oms_pm10 = TRUE;


CREATE OR REPLACE VIEW vw_transicion_cobertura AS
SELECT
    p.nombre_pais,
    g.celda_id,
    t.anio,
    dc.descripcion AS clase_dominante,
    f.porcentaje_clase_dominante,
    f.cambio_interanual
FROM fact_cobertura_vegetal_anual f
JOIN dim_tiempo t ON t.tiempo_key = f.tiempo_key
JOIN dim_pais p ON p.pais_key = f.pais_key
JOIN dim_grilla g ON g.grilla_key = f.grilla_key
JOIN dim_cobertura dc ON dc.cobertura_key = f.cobertura_key;


-- =============================================================================
-- DATOS SEMILLA MINIMOS
-- =============================================================================

INSERT INTO dim_pais (codigo_iso3, codigo_iso2, nombre_pais) VALUES
    ('ARG', 'AR', 'Argentina'),
    ('BOL', 'BO', 'Bolivia'),
    ('BRA', 'BR', 'Brasil'),
    ('CHL', 'CL', 'Chile'),
    ('COL', 'CO', 'Colombia'),
    ('ECU', 'EC', 'Ecuador'),
    ('GUY', 'GY', 'Guyana'),
    ('PRY', 'PY', 'Paraguay'),
    ('PER', 'PE', 'Peru'),
    ('SUR', 'SR', 'Surinam'),
    ('URY', 'UY', 'Uruguay'),
    ('VEN', 'VE', 'Venezuela')
ON DUPLICATE KEY UPDATE nombre_pais = VALUES(nombre_pais);


INSERT INTO dim_cobertura (codigo_igbp, descripcion, grupo_combustible, indice_combustible, es_antrpica) VALUES
    (1, 'Bosque siempreverde de coniferas', 'bosque', 0.85, FALSE),
    (2, 'Bosque caducifolio de coniferas', 'bosque', 0.80, FALSE),
    (3, 'Bosque siempreverde de hoja ancha', 'bosque', 0.82, FALSE),
    (4, 'Bosque caducifolio de hoja ancha', 'bosque', 0.78, FALSE),
    (5, 'Bosque mixto', 'bosque', 0.80, FALSE),
    (6, 'Arbustal cerrado', 'arbustal', 0.72, FALSE),
    (7, 'Arbustal abierto', 'arbustal', 0.68, FALSE),
    (8, 'Sabana arbolada', 'sabana', 0.88, FALSE),
    (9, 'Sabana', 'sabana', 0.90, FALSE),
    (10, 'Pastizal', 'pastizal', 0.86, FALSE),
    (11, 'Humedal permanente', 'humedal', 0.20, FALSE),
    (12, 'Tierra de cultivo', 'agropecuario', 0.55, TRUE),
    (13, 'Zona urbana', 'urbano', 0.10, TRUE),
    (14, 'Mosaico cultivo vegetacion natural', 'mosaico', 0.48, TRUE),
    (16, 'Suelo desnudo o vegetacion escasa', 'suelo_desnudo', 0.18, FALSE),
    (17, 'Cuerpo de agua', 'agua', 0.00, FALSE),
    (255, 'Sin clasificar', 'sin_clasificar', 0.00, FALSE)
ON DUPLICATE KEY UPDATE descripcion = VALUES(descripcion);
