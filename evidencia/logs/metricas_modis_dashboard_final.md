# Métricas MODIS y Dashboard

Generado: 2026-06-01T21:51:05.866365+00:00

## modis_staging_pais

| pais_codigo | filas | ubicaciones | desde | hasta |
| --- | --- | --- | --- | --- |
| ARG | 24 | 6 | 2018 | 2021 |
| BRA | 24 | 6 | 2018 | 2021 |
| URY | 133 | 19 | 2018 | 2024 |

## modis_dw_pais

| pais_codigo | filas | ubicaciones | desde | hasta |
| --- | --- | --- | --- | --- |
| ARG | 24 | 6 | 2018 | 2021 |
| BRA | 24 | 6 | 2018 | 2021 |
| URY | 133 | 19 | 2018 | 2024 |

## asociaciones_fact_incendio

| total | con_clima | con_precipitacion | con_cobertura | con_calidad_aire |
| --- | --- | --- | --- | --- |
| 2585805 | 83682 | 47576 | 56652 | 20599 |

## cobertura_por_pais

| pais_codigo | focos_con_cobertura |
| --- | --- |
| ARG | 39439 |
| BRA | 10105 |
| URY | 7108 |

## resumen_pipeline

| altas | modificaciones | descartes_auditoria | rechazos_detallados |
| --- | --- | --- | --- |
| 6304398 | 667 | 1089952 | 3704 |

## rechazos_detallados

| fuente | rechazos |
| --- | --- |
| CHIRPS | 702 |
| FIRMS | 3002 |

## vistas_dashboard

| vista | filas |
| --- | --- |
| dw.v_calidad_pipeline | 144 |
| dw.v_incendios_cobertura | 7 |
| dw.v_resumen_calidad_pipeline | 1 |

## Fuente y limitación

- MODIS_ARG_BRA: Zenodo record 8338928, MCD12Q1 v061 t1 COG, 2018-2021
- MODIS_URY: archivo local AppEEARS LC_Type1, 2018-2024
- limitacion: Argentina/Brasil 2022-2024 no disponibles en el record abierto usado; no se inventaron valores.
