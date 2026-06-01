# Evidencias D2 - Implementacion Del Modelo NoSQL

Este directorio conserva la evidencia liviana para el criterio D2 de la rubrica
EC3 del Proyecto LIDIA. MongoDB se valida como capa documental complementaria:
metadata de ingesta, logs, rechazos, raw payloads controlados y snapshots. El
Data Warehouse principal sigue siendo PostgreSQL.

## Archivos generados

- `d2_mongodb_conexion_<timestamp>.log`: prueba de conexion con `mongosh`,
  base usada por el proyecto, resultado de `ping` y fecha de ejecucion.
- `d2_validacion_mongodb_<timestamp>.log`: salida de
  `nosql/d2_validacion_mongodb.js`. Incluye colecciones esperadas, conteos,
  muestras sanitizadas, agrupaciones y validaciones de campos.
- `d2_resumen_ultima_ejecucion.log`: rutas de los logs de la ultima corrida y
  recordatorio del rol complementario de MongoDB.

## Que valida cada salida

- **Conexion**: confirma que `mongosh` puede conectarse usando `MONGO_URI` y
  muestra la base activa.
- **Colecciones**: verifica existencia de `ingesta_metadata`, `rechazos_etl`,
  `raw_payloads`, `pipeline_logs` y `snapshots_firms`.
- **Conteos**: muestra cuantos documentos hay por coleccion. Si una coleccion
  existe pero tiene `0` documentos, se marca como limitacion sin crear datos
  ficticios.
- **Documentos reales**: muestra hasta tres documentos por coleccion, ocultando
  campos con nombres sensibles como passwords, tokens, secrets o API keys.
- **Consultas representativas**: agrupa ingestas por fuente/estado, rechazos
  por fuente/motivo, logs por etapa/severidad y snapshots FIRMS por periodo y
  pais.
- **Campos minimos**: revisa que los documentos existentes tengan los campos
  requeridos por el contrato documental.
- **Timestamps**: confirma presencia de `registrado_en` o `fecha`, segun
  corresponda.

## Ejecucion

Desde la raiz del proyecto:

```bash
export MONGO_URI='mongodb://<oculto>
bash scripts/d2_generar_evidencia_nosql.sh
```

Si el entorno Jupyter no permite ejecutar `.sh`, usar la version Python:

```bash
export MONGO_URI='mongodb://<oculto>
python scripts/d2_generar_evidencia_nosql.py
```

El script `.sh` usa `mongosh`, captura `stdout` y `stderr` con `2>&1`, y guarda
la salida con `tee` dentro de `evidencia/logs`. La version Python usa `pymongo`
y genera los mismos archivos de evidencia sin insertar documentos.

## Interpretacion

MongoDB cumple D2 si las colecciones documentales existen, las consultas
representativas devuelven evidencia real cuando hay documentos y las
limitaciones quedan explicitas cuando alguna coleccion esta vacia. MongoDB no
debe usarse para reemplazar `dw.fact_incendio` ni las dimensiones del modelo
relacional.
