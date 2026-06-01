// D2 - Validacion MongoDB Proyecto LIDIA EC3.
// Uso: mongosh "$MONGO_URI" nosql/d2_validacion_mongodb.js
// Este script es de solo lectura: no inserta, actualiza ni elimina documentos.

const expectedCollections = [
  "ingesta_metadata",
  "rechazos_etl",
  "raw_payloads",
  "pipeline_logs",
  "snapshots_firms",
];

const sensitivePatterns = [
  /password/i,
  /passwd/i,
  /token/i,
  /secret/i,
  /api[_-]?key/i,
  /authorization/i,
  /credential/i,
];

function printSection(title) {
  print(`\n## ${title}`);
}

function safeValue(key, value, depth = 0) {
  if (sensitivePatterns.some((pattern) => pattern.test(String(key)))) {
    return "[REDACTED]";
  }
  if (value instanceof Date) {
    return value.toISOString();
  }
  if (value === null || value === undefined) {
    return value;
  }
  if (Array.isArray(value)) {
    return depth >= 3 ? `[Array(${value.length})]` : value.slice(0, 10).map((item) => safeValue(key, item, depth + 1));
  }
  if (typeof value === "object") {
    if (depth >= 3) {
      return "[Object]";
    }
    const output = {};
    Object.keys(value).slice(0, 30).forEach((childKey) => {
      output[childKey] = safeValue(childKey, value[childKey], depth + 1);
    });
    return output;
  }
  return value;
}

function sanitizeDocument(doc) {
  return safeValue("document", doc);
}

function existsField(collectionName, fieldName) {
  const query = {};
  query[fieldName] = {$exists: true, $ne: null};
  return db.getCollection(collectionName).countDocuments(query);
}

function missingRequiredCount(collectionName, requiredFields) {
  if (!requiredFields.length) {
    return 0;
  }
  const missingClauses = requiredFields.map((fieldName) => {
    const clause = {};
    clause[fieldName] = {$exists: false};
    return clause;
  });
  return db.getCollection(collectionName).countDocuments({$or: missingClauses});
}

function printJson(value) {
  print(JSON.stringify(value, null, 2));
}

printSection("Conexion");
printJson({
  host_info: db.runCommand({hostInfo: 1}).ok === 1 ? "OK" : "REVISAR",
  database: db.getName(),
  timestamp: new Date().toISOString(),
  rol_mongodb: "Complementario documental; PostgreSQL sigue siendo el Data Warehouse principal",
});

printSection("Colecciones Esperadas");
const existingCollections = db.getCollectionNames().sort();
const collectionStatus = expectedCollections.map((name) => ({
  collection: name,
  exists: existingCollections.includes(name),
}));
printJson(collectionStatus);

printSection("Conteos Por Coleccion");
const counts = expectedCollections.map((name) => ({
  collection: name,
  count: existingCollections.includes(name) ? db.getCollection(name).countDocuments({}) : null,
  limitation: existingCollections.includes(name)
    ? (db.getCollection(name).countDocuments({}) === 0 ? "Coleccion existente sin documentos; no se inventan datos" : "")
    : "Coleccion no existe",
}));
printJson(counts);

printSection("Muestra De Documentos Sanitizada");
expectedCollections.forEach((name) => {
  print(`\n### ${name}`);
  if (!existingCollections.includes(name)) {
    printJson({collection: name, exists: false, sample: []});
    return;
  }
  const sample = db.getCollection(name).find({}).limit(3).toArray().map(sanitizeDocument);
  printJson({collection: name, sample_count: sample.length, sample});
});

printSection("Agrupacion Ingestas Por Fuente Y Estado");
if (existingCollections.includes("ingesta_metadata")) {
  printJson(db.ingesta_metadata.aggregate([
    {$group: {_id: {fuente: "$fuente", estado: "$estado"}, documentos: {$sum: 1}}},
    {$sort: {"_id.fuente": 1, "_id.estado": 1}},
  ]).toArray());
} else {
  printJson({limitation: "ingesta_metadata no existe"});
}

printSection("Agrupacion Rechazos Por Fuente Y Motivo");
if (existingCollections.includes("rechazos_etl")) {
  printJson(db.rechazos_etl.aggregate([
    {$group: {_id: {fuente: "$fuente", motivo: "$motivo"}, documentos: {$sum: 1}}},
    {$sort: {documentos: -1, "_id.fuente": 1}},
  ]).toArray());
} else {
  printJson({limitation: "rechazos_etl no existe"});
}

printSection("Agrupacion Logs Por Etapa Y Severidad");
if (existingCollections.includes("pipeline_logs")) {
  printJson(db.pipeline_logs.aggregate([
    {
      $group: {
        _id: {
          etapa: {$ifNull: ["$etapa", "sin_etapa"]},
          severidad: {$ifNull: ["$severidad", "$estado"]},
        },
        documentos: {$sum: 1},
      },
    },
    {$sort: {"_id.etapa": 1, "_id.severidad": 1}},
  ]).toArray());
} else {
  printJson({limitation: "pipeline_logs no existe"});
}

printSection("Snapshots FIRMS Por Periodo Y Pais");
if (existingCollections.includes("snapshots_firms")) {
  printJson(db.snapshots_firms.aggregate([
    {
      $group: {
        _id: {
          pais_codigo: "$pais_codigo",
          anio: {$year: "$fecha"},
        },
        snapshots: {$sum: 1},
        total_focos: {$sum: "$total_focos"},
        primera_fecha: {$min: "$fecha"},
        ultima_fecha: {$max: "$fecha"},
      },
    },
    {$sort: {"_id.anio": 1, "_id.pais_codigo": 1}},
  ]).toArray());
} else {
  printJson({limitation: "snapshots_firms no existe"});
}

printSection("Validacion De Campos Minimos");
const requiredByCollection = {
  ingesta_metadata: ["run_id", "fuente", "estado", "metricas", "registrado_en"],
  rechazos_etl: ["run_id", "fuente", "motivo", "registro", "registrado_en"],
  raw_payloads: ["run_id", "fuente", "payload", "registrado_en"],
  pipeline_logs: ["run_id", "fuente", "estado", "mensaje", "registrado_en"],
  snapshots_firms: ["fecha", "pais_codigo", "total_focos", "resumen"],
};
printJson(expectedCollections.map((name) => ({
  collection: name,
  exists: existingCollections.includes(name),
  required_fields: requiredByCollection[name],
  documents_missing_required_fields: existingCollections.includes(name)
    ? missingRequiredCount(name, requiredByCollection[name])
    : null,
})));

printSection("Validacion De Timestamps O Fecha De Ejecucion");
printJson([
  {
    collection: "ingesta_metadata",
    documents_with_timestamp: existingCollections.includes("ingesta_metadata") ? existsField("ingesta_metadata", "registrado_en") : null,
  },
  {
    collection: "rechazos_etl",
    documents_with_timestamp: existingCollections.includes("rechazos_etl") ? existsField("rechazos_etl", "registrado_en") : null,
  },
  {
    collection: "raw_payloads",
    documents_with_timestamp: existingCollections.includes("raw_payloads") ? existsField("raw_payloads", "registrado_en") : null,
  },
  {
    collection: "pipeline_logs",
    documents_with_timestamp: existingCollections.includes("pipeline_logs") ? existsField("pipeline_logs", "registrado_en") : null,
  },
  {
    collection: "snapshots_firms",
    documents_with_fecha: existingCollections.includes("snapshots_firms") ? existsField("snapshots_firms", "fecha") : null,
  },
]);

printSection("Limitaciones Detectadas");
const limitations = counts
  .filter((item) => item.limitation)
  .map((item) => ({collection: item.collection, limitation: item.limitation}));
printJson(limitations.length ? limitations : [{estado: "Sin limitaciones de existencia/conteo detectadas"}]);

printSection("Fin D2");
