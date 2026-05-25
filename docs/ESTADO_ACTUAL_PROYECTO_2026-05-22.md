# Estado actual del proyecto - 2026-05-22

Este documento es la fuente de verdad operativa para defensa. Los documentos fechados el `2026-05-15` quedan como evidencia historica de una sincronizacion UTEC anterior y no reemplazan el estado actual del repositorio.

## Resumen ejecutivo

SINIA-UY / SONIA-UY es un sistema de ingenieria de datos para integrar datos ambientales reales, procesarlos con ETL Python, almacenarlos en PostgreSQL y MongoDB, validar calidad/idempotencia/CDC y exponer resultados en un dashboard Streamlit.

## Alcance vigente

| Pais | Puntos de monitoreo |
|---|---:|
| Uruguay | 19 |
| Brasil | 5 |
| Argentina | 4 |
| Chile | 8 |
| **Total** | **36** |

Codigos de pais en el sistema: `URY`, `BRA`, `ARG`, `CHL`.

Chile forma parte del alcance actual por su relevancia para eventos volcanicos y transporte atmosferico regional. Uruguay queda cubierto por sus 19 departamentos.

## Evidencia tecnica actual

| Control | Estado |
|---|---|
| Tests automatizados | `20 PASS / 0 FAIL` |
| Comando validado | `pytest tests -q` |
| Resultado de ultima corrida | `20 passed in 16.77s` |
| FIRMS procesado | `1.946.361` focos |
| Alcance en reportes actuales | `ARG`, `BRA`, `CHL`, `URY` |
| Cobertura de datasets | `36` puntos en meteo, CAMS y CHIRPS |
| Docker Compose | Configuracion valida con `docker compose config --quiet` |
| Python | Compilacion sin errores en `config`, `dashboard`, `etl`, `analytics`, `scripts` y `tests` |

## Reportes principales

- `reports/carga_completa_ultimo.json`
- `reports/sql_vs_nosql_real_ultimo.json`
- `reports/rendimiento_ultimo.json`
- `reports/backup_restore_ultimo.json`
- `reports/sharding_simulado_ultimo.json`
- `tests/resultados_tests.json`

## Lectura correcta de UTEC

`reports/utec_verificacion_ultimo.json` corresponde a una verificacion del `2026-05-15` con alcance anterior de `ARG/BRA/URY`. Es evidencia valida de despliegue institucional, pero no representa el alcance funcional actual del repositorio.

Para defensa:

- si se muestra UTEC, aclarar que es una evidencia historica de integracion institucional;
- si se muestra el estado actual del sistema, usar `reports/carga_completa_ultimo.json`, `reports/sql_vs_nosql_real_ultimo.json` y `tests/resultados_tests.json`;
- no afirmar que Chile ya esta sincronizado en UTEC salvo que se ejecute una nueva verificacion remota y el reporte lo confirme.

## Frase oficial para defensa

> El estado actual del proyecto integra cuatro paises y treinta y seis puntos de monitoreo. El pipeline procesa datos reales, carga estructuras SQL y NoSQL, valida calidad, idempotencia y CDC con veinte tests en verde, y expone evidencia reproducible mediante reportes y dashboard.
