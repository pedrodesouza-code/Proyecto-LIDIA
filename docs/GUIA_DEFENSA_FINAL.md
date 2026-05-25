# Guia de defensa final

Estado oficial: **2026-05-22**.

Usar esta guia junto con `docs/ESTADO_ACTUAL_PROYECTO_2026-05-22.md`.

## 1. Apertura

Mensaje breve:

> SINIA-UY integra datos satelitales, meteorologicos y atmosfericos para monitorear focos de calor, riesgo de incendios y calidad ambiental en Uruguay, Brasil, Argentina y Chile. El sistema usa Python para ETL, PostgreSQL como capa analitica, MongoDB para snapshots/trazabilidad, tests automaticos para calidad/idempotencia/CDC y Streamlit como dashboard.

## 2. Lo primero que hay que dejar claro

El proyecto tiene dos niveles de evidencia:

| Nivel | Que representa | Archivo |
|---|---|---|
| Estado actual local | 4 paises, 36 puntos, 20 tests | `docs/ESTADO_ACTUAL_PROYECTO_2026-05-22.md` |
| Evidencia UTEC historica | Sincronizacion institucional del 2026-05-15 con alcance anterior | `reports/utec_verificacion_ultimo.json` |

Si el tribunal pregunta por Chile en UTEC, responder:

> Chile esta incorporado en el estado actual del repositorio y en los reportes locales. La verificacion UTEC versionada corresponde a una sincronizacion anterior del 15/05; para afirmar Chile en UTEC se debe ejecutar una nueva verificacion remota.

## 3. Comandos de demo

Desde la raiz del proyecto:

```bash
pytest tests -q
```

Resultado esperado:

```text
20 passed
```

Medir rendimiento:

```bash
python scripts/medir_rendimiento.py
```

Comparar SQL vs NoSQL:

```bash
python scripts/comparar_sql_nosql_real.py
```

Validar Docker Compose:

```bash
docker compose -f docker/docker-compose.yml --env-file docker/.env.example config --quiet
```

Levantar dashboard:

```bash
streamlit run dashboard/app.py
```

Abrir:

```text
http://localhost:8501
```

## 4. Evidencia que conviene mostrar

| Tema | Archivo |
|---|---|
| Estado actual | `docs/ESTADO_ACTUAL_PROYECTO_2026-05-22.md` |
| Consigna vs cumplimiento | `docs/MATRIZ_CUMPLIMIENTO_CONSIGNA_2026.md` |
| Entrega EC3 | `docs/ENTREGA_EC3_IMPLEMENTACION.md` |
| Tests | `tests/resultados_tests.json` |
| Carga completa | `reports/carga_completa_ultimo.json` |
| SQL vs NoSQL | `reports/sql_vs_nosql_real_ultimo.json` |
| SLA y rendimiento | `docs/SLA_Y_RENDIMIENTO.md` |
| Replicacion y sharding | `docs/REPLICACION_Y_SHARDING.md` |
| Seguridad y backup | `docs/SEGURIDAD_BACKUP_GOBERNANZA.md` |
| Preguntas -> consultas -> dashboard | `docs/CORRESPONDENCIA_PREGUNTAS_CONSULTAS_DASHBOARD.md` |
| Despliegue hibrido | `docs/DESPLIEGUE_HIBRIDO.md` |

## 5. Puntos tecnicos para defender

### Por que SQL y NoSQL

PostgreSQL guarda hechos estructurados: focos, meteorologia, calidad del aire, precipitacion y cobertura vegetal. Sirve para integridad, restricciones, claves, indices y consultas analiticas.

MongoDB guarda documentos operacionales: snapshots, ejecuciones ETL, alertas y resumenes materializados. Sirve para trazabilidad y estructuras flexibles.

Respuesta corta:

> SQL y NoSQL no compiten en el proyecto: PostgreSQL resuelve consistencia analitica y MongoDB resuelve trazabilidad documental.

### CDC e idempotencia

CDC detecta registros nuevos y modificaciones. La idempotencia asegura que correr dos veces la misma carga no duplique datos.

Evidencia:

- `tests/test_calidad_datos.py`
- `tests/resultados_tests.json`
- claves naturales en `sql/ddl/02_schema.sql`
- upserts en `etl/load/`

### Calidad de datos

Los tests cubren:

- alcance de 4 paises y 36 puntos;
- Uruguay completo con 19 departamentos;
- completitud;
- unicidad;
- consistencia;
- validez;
- idempotencia;
- CDC.

### Rendimiento

El SLA interactivo de consultas analiticas es de hasta 3000 ms. Los reportes actuales muestran que las consultas materializadas en SQL y Mongo quedan por debajo de ese umbral.

### Sharding

No se activa sharding fisico porque el volumen academico entra en un nodo. Se simula una estrategia reproducible:

- SQL: particionamiento de `focos_calor` por `fecha_adq`.
- MongoDB: `focos_snapshots` con clave conceptual `{ fecha: 1, pais: "hashed" }`.

Respuesta corta:

> El proyecto no necesita sharding real hoy; deja disenada y medida una estrategia de escalamiento para cuando el volumen lo justifique.

### Docker

La configuracion Docker es valida. Si el engine no levanta por Windows/WSL, no invalida el repositorio: se demuestra con `docker compose config --quiet`.

## 6. Plan B de demo

Si PostgreSQL o MongoDB no responden:

1. Ejecutar `pytest tests -q`.
2. Mostrar `reports/carga_completa_ultimo.json`.
3. Mostrar `reports/sql_vs_nosql_real_ultimo.json`.
4. Mostrar `reports/rendimiento_ultimo.json`.
5. Levantar el dashboard con fallback a Parquet.

## 7. Cierre

Mensaje breve:

> El sistema cubre el ciclo de vida completo del dato: fuentes reales, extraccion, transformacion, carga, calidad, CDC, trazabilidad, analitica, visualizacion, rendimiento y documentacion. Las brechas restantes son de infraestructura productiva final, no de diseno ni de implementacion academica.
