// Validacion D4 CDC para MongoDB. Ejecutar con:
// mongosh "$MONGO_URI" nosql/d4_validacion_cdc_mongo.js

function printSection(title) {
  print("\n## " + title);
}

function redact(doc) {
  if (!doc) {
    return doc;
  }
  const clone = JSON.parse(JSON.stringify(doc));
  for (const key of ["password", "token", "secret", "api_key", "apikey"]) {
    if (clone[key]) {
      clone[key] = "[REDACTADO]";
    }
  }
  return clone;
}

const expectedCollections = ["cdc_eventos", "ingesta_metadata", "pipeline_logs", "snapshots_firms"];

printSection("Conexion MongoDB");
printjson({
  database: db.getName(),
  role: "MongoDB complementa PostgreSQL con metadata, logs, snapshots y evidencia CDC"
});

printSection("Colecciones Esperadas");
const existing = db.getCollectionNames();
printjson(expectedCollections.map((name) => ({
  collection: name,
  exists: existing.indexOf(name) >= 0,
  count: existing.indexOf(name) >= 0 ? db.getCollection(name).countDocuments({}) : 0
})));

printSection("Conteos CDC Por Tipo De Evento");
if (existing.indexOf("cdc_eventos") >= 0) {
  printjson(db.cdc_eventos.aggregate([
    {$group: {_id: {fuente: "$fuente", tipo_evento: "$tipo_evento"}, eventos: {$sum: 1}, ultimo: {$max: "$registrado_en"}}},
    {$sort: {"_id.fuente": 1, "_id.tipo_evento": 1}}
  ]).toArray());
} else {
  printjson({limitacion: "cdc_eventos no existe"});
}

printSection("Ultimos Documentos CDC");
if (existing.indexOf("cdc_eventos") >= 0) {
  printjson(db.cdc_eventos.find(
    {},
    {_id: 0, run_id: 1, fuente: 1, tipo_evento: 1, natural_key: 1, record_hash: 1, hash_anterior: 1, estado: 1, registrado_en: 1}
  ).sort({registrado_en: -1}).limit(10).toArray().map(redact));
}

printSection("Metadata D4");
if (existing.indexOf("ingesta_metadata") >= 0) {
  printjson(db.ingesta_metadata.find(
    {"metricas.criterio": /D4 CDC/},
    {_id: 0, run_id: 1, fuente: 1, estado: 1, metricas: 1, registrado_en: 1}
  ).sort({registrado_en: -1}).limit(10).toArray().map(redact));
}

printSection("Logs D4");
if (existing.indexOf("pipeline_logs") >= 0) {
  printjson(db.pipeline_logs.find(
    {mensaje: /D4 CDC/},
    {_id: 0, run_id: 1, fuente: 1, estado: 1, mensaje: 1, registrado_en: 1}
  ).sort({registrado_en: -1}).limit(10).toArray().map(redact));
}

printSection("Snapshots FIRMS D4");
if (existing.indexOf("snapshots_firms") >= 0) {
  printjson(db.snapshots_firms.find(
    {"resumen.criterio": "D4 CDC"},
    {_id: 0, fecha: 1, pais_codigo: 1, total_focos: 1, resumen: 1}
  ).sort({fecha: -1}).limit(10).toArray().map(redact));
}

printSection("Validacion Campos Minimos CDC");
if (existing.indexOf("cdc_eventos") >= 0) {
  printjson({
    total_cdc: db.cdc_eventos.countDocuments({}),
    con_run_id: db.cdc_eventos.countDocuments({run_id: {$exists: true, $ne: null}}),
    con_fuente: db.cdc_eventos.countDocuments({fuente: {$exists: true, $ne: null}}),
    con_tipo_evento: db.cdc_eventos.countDocuments({tipo_evento: {$exists: true, $ne: null}}),
    con_timestamp: db.cdc_eventos.countDocuments({registrado_en: {$exists: true, $ne: null}}),
    eventos_requeridos: {
      alta: db.cdc_eventos.countDocuments({tipo_evento: "alta"}),
      modificacion: db.cdc_eventos.countDocuments({tipo_evento: "modificacion"}),
      sin_cambio: db.cdc_eventos.countDocuments({tipo_evento: "sin_cambio"})
    }
  });
}
