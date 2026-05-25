# Anexo A — DDL del Data Warehouse (MySQL 8)

Este anexo documenta el modelo dimensional canónico diseñado para el Data Warehouse del proyecto SINIA-UY. El DDL completo se encuentra en el archivo [`sql/ddl/06_schema_mysql_dw.sql`](../sql/ddl/06_schema_mysql_dw.sql) del repositorio.

> **Aclaración de implementación.** El modelo se diseñó en MySQL 8 como ejercicio dimensional canónico siguiendo metodología Kimball. La implementación operativa del sistema, descrita en la sección 4.2.2 del documento principal, se realiza sobre PostgreSQL 16 en la base `grp03db` del servidor académico de UTEC, preservando el modelo lógico equivalente con traducción directa de tipos y constraints.

## A.1 Organización general

El esquema sigue una arquitectura de **modelo estrella** con cuatro dimensiones conformadas y cinco tablas de hechos separadas por granularidad temporal. La base se crea como `sinia_sa_dw` con `utf8mb4_unicode_ci` y todas las tablas usan motor **InnoDB** para soporte transaccional y de claves foráneas.

```
                ┌──────────────┐
                │  dim_tiempo  │
                └──────┬───────┘
                       │
   ┌───────────┐       │       ┌─────────────────┐
   │ dim_pais  │───────┼───────│ fact_*_diaria   │
   └───────────┘       │       │ fact_*_mensual  │
                       │       │ fact_*_anual    │
   ┌──────────────┐    │       └─────────────────┘
   │ dim_grilla   │────┤
   └──────────────┘    │
                       │
   ┌────────────────┐  │
   │ dim_cobertura  │──┘
   └────────────────┘
```

Las dimensiones conformadas garantizan integración entre hechos: una pregunta como "focos por mes y país" obtiene la misma respuesta consultando `fact_incendios_diario` o `fact_meteorologia_diaria` porque ambas referencian la misma `dim_tiempo` y la misma `dim_pais`.

## A.2 Dimensiones

| Dimensión | PK | Cardinalidad esperada | Rol |
|-----------|----|----------------------|-----|
| `dim_tiempo` | `tiempo_key` (yyyymmdd) | ~2920 (8 años × 365) | Llave temporal natural inteligente que permite agregar por año, semestre, trimestre, mes, día y semana sin self-joins |
| `dim_pais` | `pais_key` (autoincremental) | 3 (URY, BRA, ARG) | Codifica ISO3, ISO2 y nombre legible. Reemplaza al `CHAR(3)` denormalizado |
| `dim_grilla` | `grilla_key` (autoincremental) | ~6500 celdas | Grilla de 0.25° que armoniza espacialmente focos, meteo y calidad de aire. Cada celda tiene `pais_dominante_key` y `porcentaje_tierra` |
| `dim_cobertura` | `cobertura_key` | 17 clases IGBP | Decodifica el `lc_type1` de MODIS en grupo de combustible e índice de combustibilidad |

## A.3 Hechos

| Hecho | Grano | Clave única natural | Origen |
|-------|-------|--------------------|--------|
| `fact_incendios_diario` | día × celda × país | `(tiempo_key, grilla_key, pais_key)` | NASA FIRMS, agregación de focos puntuales |
| `fact_meteorologia_diaria` | día × celda × país | `(tiempo_key, grilla_key, pais_key)` | Open-Meteo / ERA5-Land |
| `fact_calidad_aire_diaria` | día × celda × país | `(tiempo_key, grilla_key, pais_key)` | CAMS via Open-Meteo |
| `fact_precipitacion_mensual` | mes × celda × país | `(tiempo_key, grilla_key, pais_key)` con `tiempo_key` truncado a primer día de mes | CHIRPS |
| `fact_cobertura_vegetal_anual` | año × celda × cobertura | `(tiempo_key, grilla_key, cobertura_key)` | MODIS MCD12Q1 |

Cada hecho incluye dos columnas de auditoría: `lote_hash` (hash SHA-256 del lote ETL, base para el CDC de la sección 4.3.2.1) y `cargado_en` (timestamp de inserción). Los hechos con corrección histórica admisible también tienen `actualizado_en` con `ON UPDATE CURRENT_TIMESTAMP` para registrar la última modificación.

## A.4 Reglas de integridad implementadas en el DDL

| Tipo | Aplicación en el DDL | Ejemplo |
|------|---------------------|---------|
| `NOT NULL` | Claves, fechas, identificadores de fuente | `tiempo_key INT NOT NULL` |
| `UNIQUE` | Combinaciones de grano analítico para idempotencia | `UNIQUE (tiempo_key, grilla_key, pais_key)` |
| `CHECK` | Rangos físicos (coordenadas, porcentajes, conteos no negativos, riesgo en [0,1]) | `CHECK (indice_riesgo BETWEEN 0 AND 1)` |
| `FK` | Hechos referencian dimensiones; bloqueo de borrado en cascada accidental | `FOREIGN KEY (tiempo_key) REFERENCES dim_tiempo(tiempo_key)` |
| `ENUM` | Dominios pequeños y estables (nivel_riesgo, nivel_pm10) | `ENUM('bajo','moderado','alto','muy_alto')` |
| `DEFAULT` | Campos de fuente y timestamps de carga | `cargado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP` |

Cada restricción se justifica en función del dominio: las coordenadas no pueden estar fuera del rango geográfico físico; un porcentaje siempre vive en [0, 100]; un nivel de riesgo solo puede tomar uno de cuatro valores predefinidos por la lógica del cálculo.

## A.5 Equivalencia con la implementación PostgreSQL

| MySQL 8 | PostgreSQL 16 |
|---------|---------------|
| `AUTO_INCREMENT` | `SERIAL` o `IDENTITY` |
| `ENUM(...)` | `VARCHAR + CHECK (col IN (...))` o tipo `CREATE TYPE ... AS ENUM` |
| `ENGINE=InnoDB` | (no aplica, el motor es único) |
| `ON UPDATE CURRENT_TIMESTAMP` | Trigger `BEFORE UPDATE` que setea `NOW()` |
| `DECIMAL(p,s)` | `NUMERIC(p,s)` (compatibilidad nominal) |
| `TINYINT` | `SMALLINT` |
| `BOOLEAN` | `BOOLEAN` (idéntico) |

El DDL PostgreSQL operativo se encuentra en [`sql/ddl/02_schema.sql`](../sql/ddl/02_schema.sql) e implementa exactamente las mismas reglas con los tipos equivalentes. La traducción se hizo conservando claves naturales, granos analíticos y todos los constraints de dominio.

## A.6 Índices analíticos

El DDL define índices secundarios sobre los hechos para acelerar consultas dimensionales típicas:

- Por `tiempo_key` descendente en todos los hechos (consulta de últimas N fechas).
- Por `pais_key` en los hechos para agregaciones por país.
- Por `grilla_key` para consultas espaciales.
- Por `nivel_riesgo` con índice parcial donde es no nulo (filtros de alertas).

Los índices completos están en [`sql/ddl/03_indices.sql`](../sql/ddl/03_indices.sql) (versión PostgreSQL).

## A.7 Trazabilidad y auditoría

El sistema audita cada corrida del pipeline ETL en la tabla `etl_ejecuciones` (PostgreSQL) y, en paralelo, en la colección `ejecuciones_etl` (MongoDB) descrita en el [Anexo B](ANEXO_B_JSON_SCHEMA_MONGODB.md). La columna `lote_hash` de cada hecho permite vincular un registro con la ejecución ETL que lo introdujo o modificó, soportando el CDC retrospectivo descrito en la sección 4.3.2.1.
