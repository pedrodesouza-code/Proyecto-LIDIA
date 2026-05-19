-- =============================================================================
-- SINIA-UY — DDL Principal — Modelo Relacional Regional
-- =============================================================================
-- Diseño orientado a Data Warehouse analítico.
-- Alcance: 4 países — Uruguay, Brasil, Argentina y Chile.
-- Período: 2018–2025.
--
-- Tablas:
--   1. puntos_monitoreo      → dimensión geográfica (36 puntos en 4 países)
--   2. focos_calor           → hechos de detección satelital FIRMS
--   3. meteo_diario          → hechos meteorológicos + índice de riesgo
--   4. calidad_aire_diario   → hechos calidad del aire CAMS
--   5. etl_ejecuciones       → auditoría CDC
--   6. paises_referencia     → dimensión país (código, nombre, región)
--   7. precipitacion_mensual → precipitación CHIRPS mensual por punto
--   8. cobertura_vegetal     → clasificación MODIS MCD12Q1 anual por punto
--
-- Ejecutar después de 01_roles.sql
-- =============================================================================

-- Extensión para UUID si se necesita en el futuro
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- TABLA 1: puntos_monitoreo
-- Dimensión. 36 puntos geográficos de monitoreo en 4 países.
-- Uruguay queda cubierto en sus 19 departamentos.
-- =============================================================================
CREATE TABLE IF NOT EXISTS puntos_monitoreo (
    id           SERIAL       PRIMARY KEY,
    nombre       VARCHAR(50)  NOT NULL UNIQUE,
    pais         CHAR(3)      NOT NULL,                -- ISO 3166-1 alpha-3: BRA, ARG, URY, CHL
    region       VARCHAR(80),                          -- Descripción de la zona (ej: "Chiquitanía boliviana")
    latitud      NUMERIC(9,6) NOT NULL
                     CHECK (latitud  BETWEEN -90.0 AND 90.0),
    longitud     NUMERIC(9,6) NOT NULL
                     CHECK (longitud BETWEEN -180.0 AND 180.0),
    activo       BOOLEAN      NOT NULL DEFAULT TRUE,
    creado_en    TIMESTAMP    NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  puntos_monitoreo IS '36 puntos geográficos de monitoreo ambiental: Uruguay completo, Brasil/Argentina estratégicos y Chile volcánico-transfronterizo';
COMMENT ON COLUMN puntos_monitoreo.nombre IS 'Nombre del punto (ciudad)';
COMMENT ON COLUMN puntos_monitoreo.pais IS 'Código ISO 3166-1 alpha-3 del país';
COMMENT ON COLUMN puntos_monitoreo.latitud IS 'Latitud decimal WGS84, rango regional del sistema';
COMMENT ON COLUMN puntos_monitoreo.longitud IS 'Longitud decimal WGS84, rango regional del sistema';

-- =============================================================================
-- TABLA 2: focos_calor
-- Hechos. Un registro por foco de calor detectado por satélite (NASA FIRMS).
-- Clave natural: (latitud, longitud, fecha_adq, hora_adq_hhmm, satelite)
-- =============================================================================
CREATE TABLE IF NOT EXISTS focos_calor (
    id                  BIGSERIAL    PRIMARY KEY,
    fecha_adq           DATE         NOT NULL,
    hora_adq_hhmm       INTEGER      CHECK (hora_adq_hhmm BETWEEN 0 AND 2359),
    latitud             NUMERIC(8,5) NOT NULL
                            CHECK (latitud  BETWEEN -90.0 AND 90.0),
    longitud            NUMERIC(8,5) NOT NULL
                            CHECK (longitud BETWEEN -180.0 AND 180.0),
    pais                CHAR(3),                        -- ISO 3166-1 alpha-3, asignado en transform
    potencia_radiativa  NUMERIC(10,3) CHECK (potencia_radiativa >= 0),
    confianza_raw       VARCHAR(5),
    confianza_num       SMALLINT     CHECK (confianza_num BETWEEN 1 AND 3),
    satelite            VARCHAR(20),
    instrumento         VARCHAR(20),
    dia_noche           CHAR(1)      CHECK (dia_noche IN ('D', 'N')),
    es_diurno           BOOLEAN,
    brillo_ti4          NUMERIC(8,3),
    brillo_ti5          NUMERIC(8,3),
    fuente              VARCHAR(20)  NOT NULL DEFAULT 'FIRMS',
    insertado_en        TIMESTAMP    NOT NULL DEFAULT NOW(),
    -- Clave natural para idempotencia (no duplicados por re-carga)
    UNIQUE (latitud, longitud, fecha_adq, hora_adq_hhmm, satelite)
);

COMMENT ON TABLE  focos_calor IS 'Focos de calor detectados por satélite NASA FIRMS VIIRS/MODIS en Uruguay, Brasil, Argentina y Chile';
COMMENT ON COLUMN focos_calor.pais IS 'Código ISO 3166-1 alpha-3 asignado por bbox en la transformación';
COMMENT ON COLUMN focos_calor.potencia_radiativa IS 'Fire Radiative Power en megawatts (MW)';
COMMENT ON COLUMN focos_calor.confianza_num IS '1=baja, 2=nominal, 3=alta (mapeo de l/n/h)';
COMMENT ON COLUMN focos_calor.dia_noche IS 'D=diurno, N=nocturno';

-- =============================================================================
-- TABLA 3: meteo_diario
-- Hechos. Datos meteorológicos diarios + índice de riesgo de incendio.
-- Clave natural: (fecha, id_punto, tipo_dato)
-- tipo_dato: 'historico' = datos pasados, 'forecast' = pronóstico
-- =============================================================================
CREATE TABLE IF NOT EXISTS meteo_diario (
    id                              SERIAL       PRIMARY KEY,
    fecha                           DATE         NOT NULL,
    id_punto                        INTEGER      NOT NULL
                                        REFERENCES puntos_monitoreo(id) ON DELETE RESTRICT,
    -- Variables meteorológicas crudas
    temperature_2m_max              NUMERIC(5,2),
    temperature_2m_min              NUMERIC(5,2),
    temperature_2m_mean             NUMERIC(5,2),
    relative_humidity_2m_max        NUMERIC(5,2) CHECK (relative_humidity_2m_max BETWEEN 0 AND 100),
    relative_humidity_2m_min        NUMERIC(5,2) CHECK (relative_humidity_2m_min BETWEEN 0 AND 100),
    wind_speed_10m_max              NUMERIC(6,2) CHECK (wind_speed_10m_max >= 0),
    wind_gusts_10m_max              NUMERIC(6,2) CHECK (wind_gusts_10m_max >= 0),
    precipitation_sum               NUMERIC(7,2) CHECK (precipitation_sum >= 0),
    et0_fao_evapotranspiration      NUMERIC(6,3) CHECK (et0_fao_evapotranspiration >= 0),
    precipitation_probability_max   NUMERIC(5,2) CHECK (precipitation_probability_max BETWEEN 0 AND 100),
    -- Componentes del índice de riesgo [0,1]
    riesgo_temp                     NUMERIC(6,4) CHECK (riesgo_temp    BETWEEN 0 AND 1),
    riesgo_humedad                  NUMERIC(6,4) CHECK (riesgo_humedad BETWEEN 0 AND 1),
    riesgo_viento                   NUMERIC(6,4) CHECK (riesgo_viento  BETWEEN 0 AND 1),
    riesgo_sequia                   NUMERIC(6,4) CHECK (riesgo_sequia  BETWEEN 0 AND 1),
    -- Índice final
    indice_riesgo                   NUMERIC(6,4) CHECK (indice_riesgo  BETWEEN 0 AND 1),
    nivel_riesgo                    VARCHAR(10)  CHECK (nivel_riesgo IN ('bajo','moderado','alto','muy_alto')),
    -- Metadatos
    fuente                          VARCHAR(30)  NOT NULL DEFAULT 'open-meteo',
    tipo_dato                       VARCHAR(15)  NOT NULL DEFAULT 'historico'
                                        CHECK (tipo_dato IN ('historico','forecast')),
    insertado_en                    TIMESTAMP    NOT NULL DEFAULT NOW(),
    actualizado_en                  TIMESTAMP    NOT NULL DEFAULT NOW(),
    -- Unicidad para CDC: solo un registro por (fecha, punto, tipo)
    UNIQUE (fecha, id_punto, tipo_dato)
);

COMMENT ON TABLE  meteo_diario IS 'Datos meteorológicos diarios con índice de riesgo de incendio calculado';
COMMENT ON COLUMN meteo_diario.indice_riesgo IS 'Índice ponderado [0,1]: temp×0.25 + humedad×0.30 + viento×0.20 + sequía×0.25';
COMMENT ON COLUMN meteo_diario.tipo_dato IS 'historico=Open-Meteo Archive, forecast=pronóstico 7 días';

-- Trigger para actualizar 'actualizado_en' automáticamente en UPDATE
CREATE OR REPLACE FUNCTION fn_actualizar_timestamp()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.actualizado_en = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_meteo_actualizado ON meteo_diario;
CREATE TRIGGER trg_meteo_actualizado
    BEFORE UPDATE ON meteo_diario
    FOR EACH ROW EXECUTE FUNCTION fn_actualizar_timestamp();

-- =============================================================================
-- TABLA 4: calidad_aire_diario
-- Hechos. Datos diarios de calidad del aire (CAMS via Open-Meteo Air Quality).
-- Clave natural: (fecha, id_punto)
-- =============================================================================
CREATE TABLE IF NOT EXISTS calidad_aire_diario (
    id                          SERIAL      PRIMARY KEY,
    fecha                       DATE        NOT NULL,
    id_punto                    INTEGER     NOT NULL
                                    REFERENCES puntos_monitoreo(id) ON DELETE RESTRICT,
    -- Indicadores de material particulado
    pm10_media                  NUMERIC(8,3) CHECK (pm10_media  >= 0),
    pm10_max                    NUMERIC(8,3) CHECK (pm10_max    >= 0),
    pm10_p95                    NUMERIC(8,3) CHECK (pm10_p95    >= 0),
    pm2_5_media                 NUMERIC(8,3) CHECK (pm2_5_media >= 0),
    pm2_5_max                   NUMERIC(8,3) CHECK (pm2_5_max   >= 0),
    aerosol_optical_depth_media NUMERIC(8,5),
    -- Índice europeo de calidad del aire
    european_aqi_media          NUMERIC(6,2),
    european_aqi_max            NUMERIC(6,2),
    -- Calidad del dato
    horas_validas               SMALLINT     CHECK (horas_validas BETWEEN 0 AND 24),
    -- Alertas
    supera_oms_pm10             BOOLEAN,
    nivel_pm10                  VARCHAR(10)  CHECK (nivel_pm10 IN ('normal','elevado','alerta')),
    -- Metadatos
    fuente                      VARCHAR(30)  NOT NULL DEFAULT 'cams-openmeteo',
    insertado_en                TIMESTAMP    NOT NULL DEFAULT NOW(),
    actualizado_en              TIMESTAMP    NOT NULL DEFAULT NOW(),
    UNIQUE (fecha, id_punto)
);

COMMENT ON TABLE  calidad_aire_diario IS 'Calidad del aire diaria CAMS (PM10, PM2.5, AQI) por punto de monitoreo';
COMMENT ON COLUMN calidad_aire_diario.pm10_media IS 'Media diaria PM10 µg/m³. Límite OMS: 45 µg/m³';
COMMENT ON COLUMN calidad_aire_diario.supera_oms_pm10 IS 'TRUE si pm10_media > 45 µg/m³ (límite OMS 2021)';

DROP TRIGGER IF EXISTS trg_cams_actualizado ON calidad_aire_diario;
CREATE TRIGGER trg_cams_actualizado
    BEFORE UPDATE ON calidad_aire_diario
    FOR EACH ROW EXECUTE FUNCTION fn_actualizar_timestamp();

-- =============================================================================
-- TABLA 5: etl_ejecuciones
-- Auditoría CDC. Registro de cada ejecución del pipeline ETL.
-- Permite trazabilidad completa y verificación de idempotencia.
-- =============================================================================
CREATE TABLE IF NOT EXISTS etl_ejecuciones (
    id                      SERIAL       PRIMARY KEY,
    fuente                  VARCHAR(50)  NOT NULL,
    etapa                   VARCHAR(20)  NOT NULL
                                CHECK (etapa IN ('extract','transform','load','testing')),
    tipo_carga              VARCHAR(15)  NOT NULL
                                CHECK (tipo_carga IN ('inicial','incremental','test')),
    fecha_datos_desde       DATE,
    fecha_datos_hasta       DATE,
    registros_procesados    INTEGER      CHECK (registros_procesados >= 0),
    registros_insertados    INTEGER      CHECK (registros_insertados >= 0),
    registros_actualizados  INTEGER      CHECK (registros_actualizados >= 0),
    registros_sin_cambio    INTEGER      CHECK (registros_sin_cambio  >= 0),
    estado                  VARCHAR(10)  NOT NULL
                                CHECK (estado IN ('ok','error','parcial')),
    mensaje                 TEXT,
    iniciado_en             TIMESTAMP    NOT NULL DEFAULT NOW(),
    finalizado_en           TIMESTAMP,
    duracion_segundos       NUMERIC(10,3)
                                CHECK (duracion_segundos >= 0)
);

COMMENT ON TABLE  etl_ejecuciones IS 'Auditoría de ejecuciones ETL para trazabilidad CDC e idempotencia';
COMMENT ON COLUMN etl_ejecuciones.tipo_carga IS 'inicial=primera carga completa, incremental=delta desde última ejecución';
COMMENT ON COLUMN etl_ejecuciones.registros_sin_cambio IS 'Registros detectados pero sin cambios (ya existían idénticos)';

-- =============================================================================
-- TABLA 6: paises_referencia
-- Dimensión estática. Metadata de los 4 países en alcance del sistema.
-- =============================================================================
CREATE TABLE IF NOT EXISTS paises_referencia (
    codigo_iso3  CHAR(3)      PRIMARY KEY,              -- ISO 3166-1 alpha-3 (BRA, ARG, URY, CHL)
    codigo_iso2  CHAR(2)      NOT NULL UNIQUE,           -- ISO 3166-1 alpha-2 (BR, BO, etc.)
    nombre       VARCHAR(80)  NOT NULL,
    region       VARCHAR(50)  DEFAULT 'Sudamérica',
    activo       BOOLEAN      NOT NULL DEFAULT TRUE
);

COMMENT ON TABLE paises_referencia IS 'Países en alcance del sistema SINIA-UY: Uruguay + Brasil/Argentina + Chile como fuente volcánica transfronteriza, período 2018-2025';

INSERT INTO paises_referencia (codigo_iso3, codigo_iso2, nombre) VALUES
    ('URY', 'UY', 'Uruguay'),
    ('BRA', 'BR', 'Brasil'),
    ('ARG', 'AR', 'Argentina'),
    ('CHL', 'CL', 'Chile')
ON CONFLICT (codigo_iso3) DO NOTHING;

-- =============================================================================
-- TABLA 7: precipitacion_mensual
-- Hechos. Precipitación mensual CHIRPS por punto de monitoreo.
-- Clave natural: (anio, mes, id_punto)
-- =============================================================================
CREATE TABLE IF NOT EXISTS precipitacion_mensual (
    id              SERIAL       PRIMARY KEY,
    anio            SMALLINT     NOT NULL CHECK (anio BETWEEN 1981 AND 2100),
    mes             SMALLINT     NOT NULL CHECK (mes  BETWEEN 1 AND 12),
    id_punto        INTEGER      NOT NULL
                        REFERENCES puntos_monitoreo(id) ON DELETE RESTRICT,
    precipitacion_mm NUMERIC(8,2) CHECK (precipitacion_mm >= 0),
    fuente          VARCHAR(30)  NOT NULL DEFAULT 'CHIRPS_ClimateSERV',
    insertado_en    TIMESTAMP    NOT NULL DEFAULT NOW(),
    UNIQUE (anio, mes, id_punto)
);

COMMENT ON TABLE  precipitacion_mensual IS 'Precipitación total mensual en mm por punto — fuente CHIRPS (UCSB/NASA)';
COMMENT ON COLUMN precipitacion_mensual.precipitacion_mm IS 'Precipitación total mensual en milímetros';

-- =============================================================================
-- TABLA 8: cobertura_vegetal
-- Hechos. Clasificación MODIS MCD12Q1 anual por punto de monitoreo.
-- Clave natural: (anio, id_punto)
-- =============================================================================
CREATE TABLE IF NOT EXISTS cobertura_vegetal (
    id               SERIAL      PRIMARY KEY,
    anio             SMALLINT    NOT NULL CHECK (anio BETWEEN 2001 AND 2100),
    id_punto         INTEGER     NOT NULL
                         REFERENCES puntos_monitoreo(id) ON DELETE RESTRICT,
    lc_type1         SMALLINT    CHECK (lc_type1 BETWEEN 1 AND 255),  -- Clasificación IGBP
    lc_descripcion   VARCHAR(60),                                       -- Etiqueta legible IGBP
    fuente           VARCHAR(30) NOT NULL DEFAULT 'MODIS_MCD12Q1_AppEEARS',
    insertado_en     TIMESTAMP   NOT NULL DEFAULT NOW(),
    UNIQUE (anio, id_punto)
);

COMMENT ON TABLE  cobertura_vegetal IS 'Tipo de cobertura/uso del suelo anual MODIS MCD12Q1 v6.1 por punto';
COMMENT ON COLUMN cobertura_vegetal.lc_type1 IS 'Clasificación IGBP: 1=bosque siempreverde, 10=pastizal, 12=cultivo, etc.';
COMMENT ON COLUMN cobertura_vegetal.lc_descripcion IS 'Descripción legible del tipo IGBP en español';
