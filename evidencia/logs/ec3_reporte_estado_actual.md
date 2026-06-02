# Auditoría EC3 - Estado Actual

Generado: 2026-06-02T19:52:40.672781+00:00

## Diagnóstico General

Estado general: **NO LISTO**.

Hay puntos pendientes o parcialmente evidenciados que conviene cerrar antes de la entrega. El reporte no inventa resultados: marca como parcial o no verificado lo que no pudo comprobar con archivos, logs o conexión.

## Resumen

- COMPLETO: 8
- FALTA: 2
- PARCIAL: 3

## Tabla De Cumplimiento

| Criterio | Estado | Evidencia encontrada | Riesgo | Urgencia | Acción recomendada | ¿Se puede terminar hoy? |
| --- | --- | --- | --- | --- | --- | --- |
| D1 SQL relacional | COMPLETO | DDL=True; schemas=3/3; missing_tables=ninguna; constraints=[{'constraint_type': 'CHECK', 'n': 181}, {'constraint_type': 'FOREIGN KEY', 'n': 15}, {'constraint_type': 'PRIMARY KEY', 'n': 18}, {'constraint_type': 'UNIQUE', 'n': 14}]; not_null=111; indexes=49; views=8; errores_logs=0 | Errores en DDL/logs o tablas faltantes afectan reproducibilidad. | BAJA | Corregir logs con errores reales y asegurar DDL ejecutable. | SI |
| D1 carga real y validación post-carga | FALTA | conteos=[{'objeto': 'fact_incendio', 'filas': 0}, {'objeto': 'dim_clima', 'filas': 0}, {'objeto': 'dim_precipitacion', 'filas': 0}, {'objeto': 'dim_cobertura_vegetal', 'filas': 0}, {'objeto': 'dim_calidad_aire', 'filas': 0}]; invalidos=[{'check_name': 'ubicacion_pais_fuera_alcance', 'n': 0}, {'check_name': 'ubicacion_latitud_invalida', 'n': 0}, {'check_name': 'ubicacion_longitud_invalida', 'n': 0}, {'check_name': 'frp_negativo', 'n': 0}, {'check_name': 'humedad_invalida', 'n': 0}, {'check_name': 'direccion_viento_invalida', 'n': 0}, {'check_name': 'pm_invalido', 'n': 0}]; rechazos=0; ingesta_metadata=0 | Si faltan metadata o controles cuantitativos, defensa queda débil. | MEDIA | Actualizar evidencia final si cambian cargas. | SI |
| D2 NoSQL documental | COMPLETO | colecciones={'ingesta_metadata': 4, 'rechazos_etl': 0, 'raw_payloads': 20, 'pipeline_logs': 4, 'snapshots_firms': 3}; ingestas=[{'_id': {'fuente': 'FIRMS', 'estado': 'ok'}, 'n': 4}]; rechazos=[]; logs=[{'_id': {}, 'n': 4}] | Colecciones vacías reducen evidencia NoSQL. | BAJA | Mantener MongoDB como metadata/logs/rechazos/snapshots; no reemplazar DW. | SI |
| D3 ETL Python modular | COMPLETO | extractores=True; config_externa=True; secretos=0; logs_d3=0; ultima_exit_ok=False | Secretos o falta de evidencia de ejecución afectan entrega. | MEDIA | Ejecutar D3 evidencia con PYTHONPATH correcto y guardar logs. | SI |
| D3 idempotencia | PARCIAL | natural/record_hash=13 columnas; duplicados=[{'stg_firms': 0}, {'stg_meteo': 0}, {'stg_chirps': 0}, {'stg_modis': 0}, {'stg_calidad_aire': 0}]; logs_idempotencia=1; dos_corridas=False | Sin dos corridas consecutivas, idempotencia queda parcialmente demostrada. | MEDIA | Generar corrida 1 y 2 smoke con conteo antes/después. | SI |
| D3 integración y trazabilidad | COMPLETO | fuentes_db=[{'fuente': 'FIRMS', 'n': 3}]; fuentes_invalidas=[]; rechazos=[]; forecast_refs=[] | Referencias FORECAST o fuentes inválidas contradicen alcance. | BAJA | Eliminar/aislar referencias FORECAST activas y documentar rechazos. | SI |
| D4 Change Data Capture | PARCIAL | logs_d4=0; log_ok=False; cdc_sql=[{'fuente': 'FIRMS', 'tipo_evento': 'alta', 'n': 838}, {'fuente': 'FIRMS', 'tipo_evento': 'sin_cambio', 'n': 18}]; cdc_mongo=[] | D4 solo es completo con evidencia SQL y MongoDB. | MEDIA | Reejecutar script D4 si falta MongoDB CDC o resumen exit_code 0. | SI |
| D5 Testing y validación | FALTA | compileall_ok=False; pytest_ok=False; passed=18 passed; logs=1 | Si pytest falla o no hay evidencia cuantitativa, D5 queda parcial. | ALTA | Corregir tests o guardar evidencia D5 final. | SI |
| D5 consultas y dashboard coherente | COMPLETO | dashboard_pg_dw=True; vistas=[{'view': 'v_incendios_pais_periodo', 'rows': 0}, {'view': 'v_incendios_region', 'rows': 0}, {'view': 'v_incendios_clima', 'rows': 0}, {'view': 'v_incendios_precipitacion', 'rows': 0}, {'view': 'v_incendios_cobertura', 'rows': 0}, {'view': 'v_calidad_aire_alta_actividad', 'rows': 0}, {'view': 'v_calidad_pipeline', 'rows': 3}]; logs_dashboard=1 | Dashboard roto o leyendo archivos debilita validación funcional. | BAJA | Abrir Streamlit y guardar captura/evidencia. | SI |
| D6 Seguridad y gobernanza | COMPLETO | roles=True; gitignore=True; secretos=0; backup_docs=True; governance_docs=True | Falta backup/gobernanza puede bajar nivel aunque el pipeline funcione. | BAJA | Agregar procedimiento backup/restore y nota ética si falta. | SI |
| D7 Streamlit | COMPLETO | metricas=8; temporal_refs=34; comparaciones_refs=48; filtros=True; matriz_docs=1 | Puede faltar matriz pregunta EC1 → vista → visualización. | BAJA | Documentar matriz pregunta analítica/vista/fuente/visualización. | SI |
| D8 Docker/despliegue | COMPLETO | compose=True; dockerfiles=1; deploy_docs=True; conectividad=True; sharding_docs=True; logs=8 | Sin documentación de despliegue puede quedar débil la reproducibilidad fuera de Jupyter. | BAJA | Documentar qué corre local/UTEC, variables, puertos y límites; no prometer Docker real si no fue probado. | SI |
| D9 rendimiento | PARCIAL | logs=1; tiempos_consultas=True; tiempos_pipeline=False; indices=False; completa_vs_smoke=False | Sin tiempos cuantitativos, el rendimiento queda como afirmación cualitativa. | MEDIA | Guardar tabla de tiempos de vistas/pipeline y explicar impacto de índices y smoke vs carga completa. | SI |

## Urgencias Ordenadas

- **ALTA - D5 Testing y validación**: Corregir tests o guardar evidencia D5 final.
- **MEDIA - D1 carga real y validación post-carga**: Actualizar evidencia final si cambian cargas.
- **MEDIA - D3 idempotencia**: Generar corrida 1 y 2 smoke con conteo antes/después.
- **MEDIA - D4 Change Data Capture**: Reejecutar script D4 si falta MongoDB CDC o resumen exit_code 0.
- **MEDIA - D9 rendimiento**: Guardar tabla de tiempos de vistas/pipeline y explicar impacto de índices y smoke vs carga completa.

## Plan Para Terminar Hoy

### Tareas De 30 Minutos

- D5 Testing y validación: Corregir tests o guardar evidencia D5 final.

### Tareas De 1 Hora

- D1 carga real y validación post-carga: Actualizar evidencia final si cambian cargas.
- D3 idempotencia: Generar corrida 1 y 2 smoke con conteo antes/después.
- D4 Change Data Capture: Reejecutar script D4 si falta MongoDB CDC o resumen exit_code 0.
- D9 rendimiento: Guardar tabla de tiempos de vistas/pipeline y explicar impacto de índices y smoke vs carga completa.

### Tareas Que No Conviene Intentar Hoy

- Recolectar series históricas faltantes que dependan de APIs externas lentas o cupos diarios.
- Prometer cobertura completa donde las fuentes reales tienen huecos documentados.
- Rehacer el modelo de datos si las validaciones actuales ya pasan.

## No Conviene Prometer Sin Evidencia

- No prometer que CAMS cubre 2018-2021 con PM2.5/PM10 útil: la evidencia cargada empieza en 2022-08-04.
- No prometer MODIS Argentina/Brasil 2022-2024 si no se cargó fuente real para esos años.
- No decir que los descartes masivos son errores ETL: muchos son filtrados por alcance geográfico/temporal.
- No decir que FIRMS confirma incendios: FIRMS detecta focos de calor satelitales.
- No afirmar cobertura completa de CHIRPS para Uruguay si la tabla no tiene URY.

## Evidencias Fuertes

- D1 SQL relacional: DDL=True; schemas=3/3; missing_tables=ninguna; constraints=[{'constraint_type': 'CHECK', 'n': 181}, {'constraint_type': 'FOREIGN KEY', 'n': 15}, {'constraint_type': 'PRIMARY KEY', 'n': 18}, {'constraint_type': 'UNIQUE', 'n': 14}]; not_null=111; indexes=49; views=8; errores_logs=0
- D2 NoSQL documental: colecciones={'ingesta_metadata': 4, 'rechazos_etl': 0, 'raw_payloads': 20, 'pipeline_logs': 4, 'snapshots_firms': 3}; ingestas=[{'_id': {'fuente': 'FIRMS', 'estado': 'ok'}, 'n': 4}]; rechazos=[]; logs=[{'_id': {}, 'n': 4}]
- D3 ETL Python modular: extractores=True; config_externa=True; secretos=0; logs_d3=0; ultima_exit_ok=False
- D3 integración y trazabilidad: fuentes_db=[{'fuente': 'FIRMS', 'n': 3}]; fuentes_invalidas=[]; rechazos=[]; forecast_refs=[]
- D5 consultas y dashboard coherente: dashboard_pg_dw=True; vistas=[{'view': 'v_incendios_pais_periodo', 'rows': 0}, {'view': 'v_incendios_region', 'rows': 0}, {'view': 'v_incendios_clima', 'rows': 0}, {'view': 'v_incendios_precipitacion', 'rows': 0}, {'view': 'v_incendios_cobertura', 'rows': 0}, {'view': 'v_calidad_aire_alta_actividad', 'rows': 0}, {'view': 'v_calidad_pipeline', 'rows': 3}]; logs_dashboard=1
- D6 Seguridad y gobernanza: roles=True; gitignore=True; secretos=0; backup_docs=True; governance_docs=True
- D7 Streamlit: metricas=8; temporal_refs=34; comparaciones_refs=48; filtros=True; matriz_docs=1
- D8 Docker/despliegue: compose=True; dockerfiles=1; deploy_docs=True; conectividad=True; sharding_docs=True; logs=8
