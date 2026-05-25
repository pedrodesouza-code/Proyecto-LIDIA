# Anexo B — JSON Schema de las colecciones MongoDB

Este anexo documenta los esquemas JSON que validan los documentos almacenados en MongoDB dentro del sistema SINIA-UY. Los archivos de validación están en [`nosql/schemas/`](../nosql/schemas/) y se aplican como `$jsonSchema` en la creación de cada colección.

## B.1 Por qué estas colecciones viven en MongoDB

La división SQL / NoSQL del sistema se justifica por las características de cada conjunto de datos:

| Colección | Característica que la hace NoSQL | Por qué no encaja bien en SQL |
|-----------|----------------------------------|-------------------------------|
| `focos_snapshots` | Documento auto-contenido por día con array embebido de focos y resumen agregado | En SQL requeriría un JOIN entre `focos_calor`, un agregado y un campo de contexto meteorológico; aquí es una sola lectura |
| `alertas` | Estructura semi-libre: los indicadores que dispararon la alerta varían según el tipo (`riesgo_meteorologico`, `focos_detectados`, `calidad_aire`, `combinada`) | En SQL forzaría columnas mayoritariamente nulas o una tabla auxiliar de pares clave-valor |
| `ejecuciones_etl` | Logs con campos opcionales, lista de errores variable, métricas anidadas | En SQL exigiría tablas anidadas o columnas JSON poco aprovechadas |

En los tres casos, MongoDB ofrece la ventaja real de flexibilidad de esquema combinada con validación estructural por `$jsonSchema`, manteniendo integridad sin renunciar a la heterogeneidad legítima del dato.

## B.2 Colección `focos_snapshots`

**Propósito.** Snapshot diario auto-contenido del estado de focos detectados por satélite. Permite responder "¿qué pasó el día X?" con una sola consulta, sin reagregar `focos_calor` desde Postgres.

**Schema.** Documento raíz con `fecha`, `generado_en`, `total_focos`, `resumen` (agregados precalculados), `focos` (array de objetos con coordenadas, FRP, confianza, satélite, día/noche) y opcionalmente `riesgo_del_dia` (contexto meteorológico desnormalizado para el mismo día).

**Campos requeridos.** `fecha`, `generado_en`, `total_focos`, `focos`. Cada foco del array exige al menos `latitud` y `longitud`.

**Ejemplo de documento.**

```json
{
  "fecha": "2024-09-15T00:00:00Z",
  "generado_en": "2024-09-16T03:00:14Z",
  "total_focos": 432,
  "resumen": {
    "frp_promedio": 22.4,
    "frp_maximo": 187.3,
    "focos_alta_confianza": 198,
    "focos_diurnos": 305,
    "focos_nocturnos": 127
  },
  "focos": [
    { "latitud": -30.91, "longitud": -55.55, "potencia_radiativa": 18.7,
      "confianza_raw": "h", "confianza_num": 3, "satelite": "Suomi NPP",
      "es_diurno": true, "hora_adq_hhmm": 1430 }
  ],
  "riesgo_del_dia": {
    "indice_promedio_todos_puntos": 0.62,
    "nivel_maximo": "alto",
    "puntos_en_alto_riesgo": 4
  }
}
```

**Consultas representativas.**

1. *Reproducir el estado de focos para un día concreto sin joins:*
   ```javascript
   db.focos_snapshots.findOne({ fecha: ISODate("2024-09-15") })
   ```
2. *Días con más de N focos en un rango:*
   ```javascript
   db.focos_snapshots.find(
     { fecha: { $gte: ISODate("2024-09-01"), $lt: ISODate("2024-10-01") },
       total_focos: { $gt: 200 } },
     { fecha: 1, total_focos: 1, "resumen.frp_maximo": 1 }
   )
   ```
3. *Días en los que coincidieron alta densidad de focos y riesgo meteorológico alto:*
   ```javascript
   db.focos_snapshots.find({
     total_focos: { $gt: 100 },
     "riesgo_del_dia.nivel_maximo": { $in: ["alto", "muy_alto"] }
   })
   ```

## B.3 Colección `alertas`

**Propósito.** Eventos de riesgo generados por el sistema cuando se cumplen ciertas condiciones (riesgo meteorológico alto, foco detectado con FRP elevado, PM10 por encima del límite OMS, o combinación). Cada alerta es un documento independiente con su propio ciclo de vida.

**Schema.** Campos requeridos: `tipo_alerta`, `fecha_generacion`, `fuente`, `nivel`, `puntos_afectados`. Dominios cerrados con `enum` para `tipo_alerta` (`riesgo_meteorologico`, `focos_detectados`, `calidad_aire`, `combinada`), `fuente` (`firms`, `open-meteo`, `cams`, `sistema`) y `nivel` (`moderado`, `alto`, `muy_alto`, `critico`). Los `puntos_afectados` son un array con al menos un elemento, cada uno con `nombre` y `valor_indicador` requeridos. Campo opcional `indicadores` con los valores numéricos que dispararon la alerta; `activa` booleano; `resuelta_en` fecha o null.

**Ejemplo de documento.**

```json
{
  "tipo_alerta": "combinada",
  "fecha_generacion": "2024-09-15T14:32:00Z",
  "fuente": "sistema",
  "nivel": "muy_alto",
  "puntos_afectados": [
    { "nombre": "Rivera", "latitud": -30.91, "longitud": -55.55,
      "valor_indicador": 0.81, "nivel_punto": "muy_alto" }
  ],
  "indicadores": {
    "indice_riesgo_max": 0.81, "focos_detectados": 27,
    "pm10_max": 63.4, "temperatura_max": 36.2, "humedad_min": 18
  },
  "mensaje": "Riesgo muy alto en Rivera: 27 focos activos y PM10 sobre límite OMS",
  "activa": true,
  "resuelta_en": null
}
```

**Consultas representativas.**

1. *Alertas activas hoy ordenadas por severidad:*
   ```javascript
   db.alertas.find({ activa: true }).sort({ nivel: -1, fecha_generacion: -1 })
   ```
2. *Histórico de alertas combinadas para un punto:*
   ```javascript
   db.alertas.find({
     tipo_alerta: "combinada",
     "puntos_afectados.nombre": "Rivera"
   })
   ```
3. *Conteo de alertas por mes y nivel:*
   ```javascript
   db.alertas.aggregate([
     { $group: {
         _id: {
           mes: { $dateToString: { format: "%Y-%m", date: "$fecha_generacion" } },
           nivel: "$nivel"
         },
         total: { $sum: 1 } } },
     { $sort: { "_id.mes": -1 } }
   ])
   ```

## B.4 Colección `ejecuciones_etl`

**Propósito.** Bitácora estructurada de cada corrida del pipeline ETL: cuándo arrancó, cuánto tardó, qué etapa, qué fuente, cuántos registros tocó, qué errores hubo. Soporta la auditoría CDC y la detección de incidentes operativos.

**Schema.** Campos requeridos: `fuente`, `etapa`, `tipo_carga`, `estado`, `iniciado_en`. Dominios cerrados con `enum`: `fuente` (`firms`, `firms_nrt`, `open-meteo`, `open-meteo-forecast`, `cams`), `etapa` (`extract`, `transform`, `load`, `testing`, `pipeline_completo`), `tipo_carga` (`inicial`, `incremental`, `test`, `reprocess`), `estado` (`ok`, `error`, `parcial`, `skip`). Campos opcionales: `finalizado_en`, `duracion_segundos`, `metricas` (registros procesados / insertados / actualizados / sin cambio / error), `rango_datos` (desde-hasta), `errores` (array de objetos con tipo y mensaje), `host`, `version_pipeline`.

**Ejemplo de documento.**

```json
{
  "fuente": "firms",
  "etapa": "pipeline_completo",
  "tipo_carga": "incremental",
  "estado": "ok",
  "iniciado_en": "2024-09-16T03:00:00Z",
  "finalizado_en": "2024-09-16T03:14:22Z",
  "duracion_segundos": 862.4,
  "metricas": {
    "registros_procesados": 4321,
    "registros_insertados": 4280,
    "registros_actualizados": 18,
    "registros_sin_cambio": 23,
    "registros_error": 0
  },
  "rango_datos": {
    "desde": "2024-09-15T00:00:00Z",
    "hasta": "2024-09-16T00:00:00Z"
  },
  "errores": [],
  "host": "sinia-server-utec",
  "version_pipeline": "1.2.0"
}
```

**Consultas representativas.**

1. *Última ejecución exitosa por fuente:*
   ```javascript
   db.ejecuciones_etl.aggregate([
     { $match: { estado: "ok" } },
     { $sort: { iniciado_en: -1 } },
     { $group: { _id: "$fuente", ultima: { $first: "$$ROOT" } } }
   ])
   ```
2. *Ejecuciones con errores en la última semana:*
   ```javascript
   db.ejecuciones_etl.find({
     estado: { $in: ["error", "parcial"] },
     iniciado_en: { $gte: new Date(Date.now() - 7*24*60*60*1000) }
   })
   ```
3. *Duración promedio por etapa y fuente:*
   ```javascript
   db.ejecuciones_etl.aggregate([
     { $match: { estado: "ok", duracion_segundos: { $ne: null } } },
     { $group: { _id: { fuente: "$fuente", etapa: "$etapa" },
                 promedio_seg: { $avg: "$duracion_segundos" } } }
   ])
   ```

## B.5 Validación en la capa de ingesta

Los JSON Schema anteriores se aplican a nivel de motor MongoDB en la creación de cada colección. Antes del insert, la capa ETL en Python (`etl/load/load_mongo.py`) hace una validación adicional con Pydantic sobre los mismos tipos y restricciones, de modo que los documentos que llegan al motor ya están estructuralmente correctos. La doble validación (Python pre-insert + MongoDB en insert) atrapa errores de estructura tanto en desarrollo como en producción, sin sacrificar la flexibilidad de campos opcionales.

## B.6 Justificación de elegir documental sobre relacional

Estas tres colecciones aprovechan tres ventajas estructurales del modelo documental que en SQL serían anti-patrones:

1. **Documento auto-contenido**: en `focos_snapshots`, todo lo necesario para "ver el día X" cabe en un documento; consultar es una sola lectura en lugar de una agregación con JOIN.
2. **Esquema flexible con dominio acotado**: en `alertas`, los `indicadores` varían según `tipo_alerta`, pero los `enum` y campos requeridos preservan la integridad del dominio.
3. **Anidamiento natural**: en `ejecuciones_etl`, la lista de `errores` y el bloque de `metricas` se modelan como objetos anidados sin necesidad de tablas auxiliares.

Esta complementariedad con el modelo relacional del Anexo A es la base del despliegue híbrido descrito en la sección 2 del documento principal.
