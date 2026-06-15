# MongoDB

PostgreSQL conserva el Data Warehouse y las consultas analiticas. MongoDB se
limita a documentos variables: payloads crudos por fuente, metadata de
ejecucion, logs, rechazos con payload original, snapshots FIRMS resumidos y
metadata de calidad del aire CAMS/Open-Meteo Air Quality cuando exista carga
validada. Estos documentos admiten distintos
detalles por fuente sin modificar el esquema estrella.

`mongo_schema.json` contiene los validadores JSON Schema y
`mongo_queries.js` consultas representativas. No se almacenan credenciales ni
se propone sharding para el servidor institucional.

Colecciones documentales esperadas:

- `ingesta_metadata`: resumen de corridas por fuente, estado, conteos y ventana
  temporal.
- `rechazos_etl`: rechazos trazables con fuente, motivo y payload controlado.
- `raw_payloads`: muestras o documentos crudos controlados, no carga masiva de
  datasets históricos.
- `pipeline_logs`: logs operativos del pipeline, CDC y validaciones.
- `snapshots_firms`: snapshots agregados de FIRMS por pais/periodo.

MongoDB no almacena la tabla de hechos ni reemplaza las dimensiones del modelo
estrella. Las consultas analíticas principales se resuelven en PostgreSQL y el
dashboard consume vistas `dw`.

## Sharding Local

El sharding MongoDB documentado en `scripts/aplicar_sharding_mongo_compose.sh`
es una evidencia local academica para D8. Crea un `mongos` y shards locales para
demostrar conceptos de distribucion documental, pero no forma parte del
despliegue productivo ni se asume disponible en Jupyter/UTEC.
