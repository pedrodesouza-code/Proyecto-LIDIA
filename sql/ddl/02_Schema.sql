-- Proyecto LIDIA - modelo estrella EC3, periodo analitico 2018-2025.
-- Alcance geografico: Uruguay (URY), Argentina (ARG) y Brasil (BRA).
-- Fuentes admitidas: INUMET, FIRMS, CHIRPS, FORECAST, METEO y MODIS.

CREATE TABLE IF NOT EXISTS staging.ingesta_metadata (
    ingesta_id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL,
    fuente VARCHAR(20) NOT NULL CHECK (fuente IN ('INUMET','FIRMS','CHIRPS','FORECAST','METEO','MODIS')),
    ultima_fecha_procesada DATE,
    filas_leidas INTEGER NOT NULL DEFAULT 0 CHECK (filas_leidas >= 0),
    filas_insertadas INTEGER NOT NULL DEFAULT 0 CHECK (filas_insertadas >= 0),
    filas_actualizadas INTEGER NOT NULL DEFAULT 0 CHECK (filas_actualizadas >= 0),
    filas_rechazadas INTEGER NOT NULL DEFAULT 0 CHECK (filas_rechazadas >= 0),
    estado VARCHAR(15) NOT NULL CHECK (estado IN ('iniciado','ok','parcial','error')),
    iniciado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finalizado_en TIMESTAMPTZ,
    UNIQUE (run_id, fuente)
);

CREATE TABLE IF NOT EXISTS staging.rechazos_etl (
    rechazo_id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL,
    fuente VARCHAR(20) NOT NULL,
    motivo TEXT NOT NULL,
    registro JSONB NOT NULL,
    rechazado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS staging.stg_firms (
    record_hash CHAR(64) PRIMARY KEY,
    natural_key VARCHAR(240) NOT NULL UNIQUE,
    fecha_adq DATE NOT NULL,
    hora_adq_hhmm INTEGER CHECK (hora_adq_hhmm BETWEEN 0 AND 2359),
    latitud NUMERIC(9,6) NOT NULL CHECK (latitud BETWEEN -90 AND 90),
    longitud NUMERIC(9,6) NOT NULL CHECK (longitud BETWEEN -180 AND 180),
    pais_codigo CHAR(3) NOT NULL CHECK (pais_codigo IN ('URY','ARG','BRA')),
    frp_mw NUMERIC(12,3) CHECK (frp_mw >= 0),
    brillo_termico NUMERIC(10,3),
    confianza NUMERIC(5,2) CHECK (confianza BETWEEN 0 AND 100),
    satelite VARCHAR(30),
    instrumento VARCHAR(30),
    dia_noche CHAR(1) CHECK (dia_noche IN ('D','N')),
    raw_payload JSONB,
    cargado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS staging.stg_meteo (
    record_hash CHAR(64) PRIMARY KEY,
    natural_key VARCHAR(240) NOT NULL UNIQUE,
    fuente VARCHAR(20) NOT NULL CHECK (fuente IN ('METEO','FORECAST','INUMET')),
    fecha DATE NOT NULL,
    fecha_hora_utc TIMESTAMPTZ NOT NULL,
    pais_codigo CHAR(3) NOT NULL CHECK (pais_codigo IN ('URY','ARG','BRA')),
    ubicacion VARCHAR(100) NOT NULL,
    departamento VARCHAR(100),
    latitud NUMERIC(9,6),
    longitud NUMERIC(9,6),
    temperatura_c NUMERIC(6,2),
    humedad_pct NUMERIC(6,2) CHECK (humedad_pct BETWEEN 0 AND 100),
    viento_kmh NUMERIC(7,2) CHECK (viento_kmh >= 0),
    direccion_viento_grados NUMERIC(6,2) CHECK (direccion_viento_grados BETWEEN 0 AND 360),
    presion_superficie_hpa NUMERIC(8,2) CHECK (presion_superficie_hpa > 0),
    precipitacion_mm NUMERIC(10,3) CHECK (precipitacion_mm >= 0),
    raw_payload JSONB,
    cargado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS staging.stg_chirps (
    record_hash CHAR(64) PRIMARY KEY,
    natural_key VARCHAR(240) NOT NULL UNIQUE,
    fecha DATE NOT NULL,
    pais_codigo CHAR(3) NOT NULL CHECK (pais_codigo IN ('URY','ARG','BRA')),
    ubicacion VARCHAR(100) NOT NULL,
    precipitacion_mm NUMERIC(10,3) NOT NULL CHECK (precipitacion_mm >= 0),
    raw_payload JSONB,
    cargado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS staging.stg_modis (
    record_hash CHAR(64) PRIMARY KEY,
    natural_key VARCHAR(240) NOT NULL UNIQUE,
    anio SMALLINT NOT NULL CHECK (anio BETWEEN 2018 AND 2025),
    pais_codigo CHAR(3) NOT NULL CHECK (pais_codigo IN ('URY','ARG','BRA')),
    ubicacion VARCHAR(100) NOT NULL,
    codigo_cobertura INTEGER,
    descripcion_cobertura VARCHAR(120),
    raw_payload JSONB,
    cargado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dw.dim_fecha (
    fecha_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fecha DATE NOT NULL UNIQUE,
    anio SMALLINT NOT NULL,
    mes SMALLINT NOT NULL CHECK (mes BETWEEN 1 AND 12),
    trimestre SMALLINT NOT NULL CHECK (trimestre BETWEEN 1 AND 4)
);

CREATE TABLE IF NOT EXISTS dw.dim_ubicacion (
    ubicacion_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pais_codigo CHAR(3) NOT NULL CHECK (pais_codigo IN ('URY','ARG','BRA')),
    pais_nombre VARCHAR(30) NOT NULL,
    region VARCHAR(100),
    ubicacion VARCHAR(100),
    latitud NUMERIC(9,6) NOT NULL CHECK (latitud BETWEEN -90 AND 90),
    longitud NUMERIC(9,6) NOT NULL CHECK (longitud BETWEEN -180 AND 180),
    UNIQUE (pais_codigo, latitud, longitud)
);

CREATE TABLE IF NOT EXISTS dw.dim_estacion_meteorologica (
    estacion_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo_estacion VARCHAR(60) NOT NULL UNIQUE,
    nombre VARCHAR(120) NOT NULL,
    departamento VARCHAR(100),
    pais_codigo CHAR(3) NOT NULL DEFAULT 'URY' CHECK (pais_codigo = 'URY'),
    latitud NUMERIC(9,6) NOT NULL CHECK (latitud BETWEEN -35.2 AND -30.0),
    longitud NUMERIC(9,6) NOT NULL CHECK (longitud BETWEEN -58.7 AND -53.0),
    fuente VARCHAR(20) NOT NULL DEFAULT 'INUMET' CHECK (fuente = 'INUMET')
);

CREATE TABLE IF NOT EXISTS dw.dim_clima (
    clima_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fecha_id INTEGER NOT NULL REFERENCES dw.dim_fecha(fecha_id),
    ubicacion_id BIGINT NOT NULL REFERENCES dw.dim_ubicacion(ubicacion_id),
    estacion_id BIGINT REFERENCES dw.dim_estacion_meteorologica(estacion_id),
    fuente VARCHAR(20) NOT NULL CHECK (fuente IN ('METEO','FORECAST','INUMET')),
    fecha_hora_utc TIMESTAMPTZ NOT NULL,
    temperatura_c NUMERIC(6,2),
    humedad_pct NUMERIC(6,2) CHECK (humedad_pct BETWEEN 0 AND 100),
    viento_kmh NUMERIC(7,2) CHECK (viento_kmh >= 0),
    direccion_viento_grados NUMERIC(6,2) CHECK (direccion_viento_grados BETWEEN 0 AND 360),
    presion_superficie_hpa NUMERIC(8,2) CHECK (presion_superficie_hpa > 0),
    UNIQUE (fecha_hora_utc, ubicacion_id, fuente)
);

CREATE TABLE IF NOT EXISTS dw.dim_precipitacion (
    precipitacion_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fecha_id INTEGER NOT NULL REFERENCES dw.dim_fecha(fecha_id),
    ubicacion_id BIGINT NOT NULL REFERENCES dw.dim_ubicacion(ubicacion_id),
    precipitacion_mm NUMERIC(10,3) CHECK (precipitacion_mm >= 0),
    fuente VARCHAR(20) NOT NULL DEFAULT 'CHIRPS' CHECK (fuente = 'CHIRPS'),
    UNIQUE (fecha_id, ubicacion_id, fuente)
);

CREATE TABLE IF NOT EXISTS dw.dim_cobertura_vegetal (
    cobertura_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    anio SMALLINT NOT NULL CHECK (anio BETWEEN 2018 AND 2025),
    ubicacion_id BIGINT NOT NULL REFERENCES dw.dim_ubicacion(ubicacion_id),
    codigo_cobertura INTEGER,
    descripcion_cobertura VARCHAR(120),
    fuente VARCHAR(20) NOT NULL DEFAULT 'MODIS' CHECK (fuente = 'MODIS'),
    UNIQUE (anio, ubicacion_id)
);

CREATE TABLE IF NOT EXISTS dw.dim_calidad_aire (
    calidad_aire_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fecha_id INTEGER REFERENCES dw.dim_fecha(fecha_id),
    ubicacion_id BIGINT REFERENCES dw.dim_ubicacion(ubicacion_id),
    pm25 NUMERIC(9,3) CHECK (pm25 >= 0),
    pm10 NUMERIC(9,3) CHECK (pm10 >= 0),
    fuente VARCHAR(20),
    observacion TEXT,
    UNIQUE (fecha_id, ubicacion_id)
);
COMMENT ON TABLE dw.dim_calidad_aire IS 'Dimension opcional; queda sin carga hasta validar una fuente aprobada en EC3.';

CREATE TABLE IF NOT EXISTS dw.fact_incendio (
    incendio_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    natural_key VARCHAR(240) NOT NULL UNIQUE,
    record_hash CHAR(64) NOT NULL,
    fecha_id INTEGER NOT NULL REFERENCES dw.dim_fecha(fecha_id),
    ubicacion_id BIGINT NOT NULL REFERENCES dw.dim_ubicacion(ubicacion_id),
    clima_id BIGINT REFERENCES dw.dim_clima(clima_id),
    precipitacion_id BIGINT REFERENCES dw.dim_precipitacion(precipitacion_id),
    cobertura_id BIGINT REFERENCES dw.dim_cobertura_vegetal(cobertura_id),
    calidad_aire_id BIGINT REFERENCES dw.dim_calidad_aire(calidad_aire_id),
    frp_mw NUMERIC(12,3) CHECK (frp_mw >= 0),
    brillo_termico NUMERIC(10,3),
    confianza NUMERIC(5,2) CHECK (confianza BETWEEN 0 AND 100),
    satelite VARCHAR(30),
    instrumento VARCHAR(30),
    dia_noche CHAR(1) CHECK (dia_noche IN ('D','N')),
    cargado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON COLUMN dw.fact_incendio.brillo_termico IS 'Brightness FIRMS: brillo termico satelital, no temperatura del aire.';

CREATE TABLE IF NOT EXISTS audit.etl_runs (
    run_id UUID PRIMARY KEY,
    fuente VARCHAR(20) NOT NULL CHECK (fuente IN ('INUMET','FIRMS','CHIRPS','FORECAST','METEO','MODIS')),
    etapa VARCHAR(20) NOT NULL CHECK (etapa IN ('extract','transform','load','pipeline','test')),
    estado VARCHAR(15) NOT NULL CHECK (estado IN ('iniciado','ok','parcial','error')),
    ultima_fecha_procesada DATE,
    filas_leidas INTEGER NOT NULL DEFAULT 0 CHECK (filas_leidas >= 0),
    filas_insertadas INTEGER NOT NULL DEFAULT 0 CHECK (filas_insertadas >= 0),
    filas_actualizadas INTEGER NOT NULL DEFAULT 0 CHECK (filas_actualizadas >= 0),
    filas_rechazadas INTEGER NOT NULL DEFAULT 0 CHECK (filas_rechazadas >= 0),
    duracion_segundos NUMERIC(12,3) CHECK (duracion_segundos >= 0),
    iniciado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finalizado_en TIMESTAMPTZ,
    detalle JSONB
);

CREATE TABLE IF NOT EXISTS audit.cdc_eventos (
    evento_id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES audit.etl_runs(run_id),
    fuente VARCHAR(20) NOT NULL,
    record_hash CHAR(64) NOT NULL,
    tipo_evento VARCHAR(15) NOT NULL CHECK (tipo_evento IN ('alta','modificacion','sin_cambio','rechazo')),
    registrado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    detalle JSONB
);
