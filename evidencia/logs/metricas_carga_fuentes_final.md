# Métricas finales de carga por fuente

Generado: 2026-06-01T21:18:40.578849+00:00

## staging_por_fuente

| fuente | filas | desde | hasta |
| --- | --- | --- | --- |
| CAMS | 927024 | 2022-08-04 | 2025-12-31 |
| CHIRPS | 702 | 2018-01-01 | 2024-06-01 |
| FIRMS | 2585805 | 2018-01-01 | 2025-01-01 |
| INUMET | 224369 | 2020-01-01 | 2025-12-31 |
| METEO | 2173968 | 2018-01-01 | 2025-12-31 |
| MODIS | 133 | 2018-01-01 | 2024-01-01 |

## dw_objetos

| objeto | filas |
| --- | --- |
| dw.dim_calidad_aire | 38626 |
| dw.dim_clima | 2398337 |
| dw.dim_cobertura_vegetal | 133 |
| dw.dim_fecha | 2929 |
| dw.dim_precipitacion | 702 |
| dw.fact_incendio | 2585805 |

## asociaciones_fact_incendio

| total | con_clima | con_precipitacion | con_cobertura | con_calidad_aire |
| --- | --- | --- | --- | --- |
| 2585805 | 83682 | 47576 | 7108 | 20599 |

## cams_por_pais

| pais_codigo | filas | ubicaciones | desde | hasta |
| --- | --- | --- | --- | --- |
| ARG | 179424 | 6 | 2022-08-04 | 2025-12-31 |
| BRA | 179424 | 6 | 2022-08-04 | 2025-12-31 |
| URY | 568176 | 19 | 2022-08-04 | 2025-12-31 |

## cams_cobertura_punto_anio

| punto_anio_con_datos_pm | punto_anio_sin_pm | total_punto_anio | min_horas_con_pm | max_horas_con_pm |
| --- | --- | --- | --- | --- |
| 124 | 124 | 248 | 3600 | 8784 |

## vistas_dashboard

| vista | filas |
| --- | --- |
| dw.v_calidad_aire_alta_actividad | 5187 |
| dw.v_calidad_pipeline | 143 |
| dw.v_incendios_clima | 6409 |
| dw.v_incendios_cobertura | 6 |
| dw.v_incendios_precipitacion | 254 |

## audit_asociacion_ultima

| variable | total_hechos | asociados | sin_asociar | umbral_km | distancia_maxima_km | ejecutado_en |
| --- | --- | --- | --- | --- | --- | --- |
| calidad_aire | 2585805 | 20599 | 2565206 | 100.00 | 99.999 | 2026-06-01 21:16:51.424588+00 |
| clima | 2585805 | 83682 | 2502123 | 150.00 | 143.897 | 2026-06-01 20:39:37.475998+00 |
| precipitacion | 2585805 | 47576 | 2538229 | 100.00 | 99.998 | 2026-06-01 20:39:37.475998+00 |
| cobertura | 2585805 | 7108 | 2578697 | 100.00 | 99.908 | 2026-06-01 20:39:37.475998+00 |
| precipitacion | 2585805 | 47576 | 2538229 | 100.00 | 99.998 | 2026-05-27 19:01:02.48423+00 |
| cobertura | 2585805 | 7108 | 2578697 | 100.00 | 99.908 | 2026-05-27 19:01:02.48423+00 |

## MongoDB

```json
{
  "estado": "ok",
  "database": "grp03db",
  "colecciones": {
    "alertas": 0,
    "cdc_control": 1,
    "cdc_eventos": 4,
    "data_quality_results": 36,
    "devops_probe": 0,
    "ejecuciones_etl": 3,
    "etl_runs": 6,
    "eventos": 2,
    "focos_resumen_mes": 39,
    "focos_resumen_pais": 3,
    "focos_snapshots": 352,
    "ingesta_metadata": 7,
    "pipeline_logs": 919,
    "raw_payloads": 6,
    "raw_snapshots": 4,
    "rechazos_etl": 3,
    "snapshots_firms": 3
  }
}
```
