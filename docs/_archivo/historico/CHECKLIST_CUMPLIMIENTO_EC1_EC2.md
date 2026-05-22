# Checklist de cumplimiento EC1 y EC2

Este checklist resume cómo el documento principal y los anexos cubren los requisitos más explícitos de EC1 y EC2.

## EC1

| Requisito | Cobertura en el material |
|---|---|
| Problema claro y delimitado | Sección 1.1 |
| Objetivo general y 3-6 objetivos específicos | Sección 1.2 |
| Mínimo 3 fuentes reales y heterogéneas | Secciones 1.3, 3.3 y 4.1 |
| Exploración preliminar real de datos | Sección 4.1.1 |
| Análisis inicial de calidad | Sección 4.1.2 y Tablas 9-10 |
| Viabilidad técnica SQL + NoSQL | Secciones 1, 2 y 4.3 |
| Riesgos y limitaciones | Secciones 1.4 y 4.3.5 |
| 10 preguntas analíticas | Sección 3.6 |
| Arquitectura preliminar / flujo | Figura 1 y Figura 5 |

## EC2

| Requisito | Cobertura en el material |
|---|---|
| Marco conceptual técnico | Sección 2 |
| Cuadro de artículos revisados | Cuadro 1 |
| Análisis detallado de fuentes | Sección 4.1 y Tablas 4-8 |
| Campos por fuente | Tabla 14 |
| Mapeo fuente-destino | Tabla 15 |
| Conflictos de integración y resolución | Tabla 16 |
| Modelo relacional como Data Warehouse | Sección 4.2.1, Figura 4 y Anexo A |
| Modelo NoSQL justificado | Tabla 12 y Sección 4.3.3 |
| Arquitectura detallada | Sección 4.3.1 y Figura 5 |
| Diseño detallado del ETL | Sección 4.3.2 |
| CDC | Sección 4.3.2.1 |
| Idempotencia | Sección 4.3.2.2 |
| Reglas de integridad SQL y NoSQL | Sección 4.3.3, Tabla 13 y Anexos A-B |
| KPIs alineados con preguntas | Tabla 17 |
| Trade-offs técnicos documentados | Sección 4.3.5 y Tabla 18 |

## Anexos relevantes

| Anexo | Archivo |
|---|---|
| Anexo A | `docs/ANEXO_A_DDL_MYSQL.md` y `sql/ddl/06_schema_mysql_dw.sql` |
| Anexo B | `docs/ANEXO_B_JSON_SCHEMA_MONGODB.md` |
| Anexo C | `docs/figures/` |
| Anexo D | `etl/` |
| Anexo E | `etl/load/` y `tests/test_calidad_datos.py` |
| Anexo F | `sql/queries/01_analiticas.sql` y `nosql/queries/01_consultas.js` |
| Anexo G | `dashboard/` |

