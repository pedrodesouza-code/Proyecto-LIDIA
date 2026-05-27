// Consultas documentales EC3: metadata, rechazos y snapshots; el DW vive en PostgreSQL.
db.ingesta_metadata.find(
  {fuente: "FIRMS"},
  {run_id: 1, estado: 1, metricas: 1, registrado_en: 1}
).sort({registrado_en: -1}).limit(10);

db.rechazos_etl.aggregate([
  {$group: {_id: {fuente: "$fuente", motivo: "$motivo"}, filas: {$sum: 1}}},
  {$sort: {filas: -1}}
]);

db.raw_payloads.find(
  {fuente: {$in: ["INUMET", "FIRMS", "CHIRPS", "FORECAST", "METEO", "MODIS"]}},
  {fuente: 1, registrado_en: 1, payload: 1}
).sort({registrado_en: -1}).limit(10);

db.pipeline_logs.find(
  {estado: {$in: ["parcial", "error"]}},
  {run_id: 1, fuente: 1, estado: 1, mensaje: 1, registrado_en: 1}
).sort({registrado_en: -1}).limit(20);

db.snapshots_firms.find(
  {pais_codigo: {$in: ["URY", "ARG", "BRA"]}},
  {fecha: 1, pais_codigo: 1, total_focos: 1, resumen: 1}
).sort({fecha: -1}).limit(30);
