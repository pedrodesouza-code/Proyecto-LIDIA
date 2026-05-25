// =============================================================================
// SINIA-UY — Limpieza de documentos de países fuera del alcance reducido
// =============================================================================
// Tras restringir el alcance a Uruguay + Brasil + Argentina, este script
// elimina de MongoDB los documentos cargados de Bolivia, Paraguay, Chile y
// Perú que quedaron de la versión previa.
//
// Ejecutar UNA SOLA VEZ después de cambiar el alcance.
// Idempotente: re-ejecutarlo no hace nada porque los datos ya no están.
//
// Uso:
//   mongosh "mongodb://localhost:27017/sinia_uy" --file 02_limpiar_paises_excluidos.js
//   o
//   use sinia_uy
//   load("nosql/queries/02_limpiar_paises_excluidos.js")
// =============================================================================

const PAISES_VALIDOS = ["URY", "BRA", "ARG"];

print("── Conteo previo ──────────────────────────────────────────────────");
print(`focos_snapshots (total):     ${db.focos_snapshots.countDocuments()}`);
print(`alertas (total):             ${db.alertas.countDocuments()}`);
print(`ejecuciones_etl (total):     ${db.ejecuciones_etl.countDocuments()}`);

// Conteo de documentos a borrar (focos_snapshots embebe focos con pais)
const previewSnapshots = db.focos_snapshots.countDocuments({
    "focos.pais": { $nin: PAISES_VALIDOS }
});
const previewAlertas = db.alertas.countDocuments({
    pais: { $exists: true, $nin: PAISES_VALIDOS }
});
print(`focos_snapshots a revisar:   ${previewSnapshots}`);
print(`alertas a borrar:            ${previewAlertas}`);

print("");
print("── Iniciando limpieza ─────────────────────────────────────────────");

// ── 1. alertas: eliminar las que están en países excluidos ───────────────
const resAlertas = db.alertas.deleteMany({
    pais: { $exists: true, $nin: PAISES_VALIDOS }
});
print(`alertas eliminadas:          ${resAlertas.deletedCount}`);

// ── 2. focos_snapshots: filtrar focos embebidos por país ─────────────────
// Estrategia: usar $pull para sacar los focos de países excluidos de cada
// documento, y borrar el documento si quedó sin focos.
const resPull = db.focos_snapshots.updateMany(
    {},
    { $pull: { focos: { pais: { $nin: PAISES_VALIDOS } } } }
);
print(`snapshots actualizados:      ${resPull.modifiedCount}`);

const resVacios = db.focos_snapshots.deleteMany({
    $or: [
        { focos: { $size: 0 } },
        { focos: { $exists: false } }
    ]
});
print(`snapshots vacíos eliminados: ${resVacios.deletedCount}`);

// ── 3. ejecuciones_etl: no se tocan (son trazas históricas válidas) ──────
print("ejecuciones_etl:             (preservadas, son trazas históricas)");

print("");
print("── Conteo posterior ───────────────────────────────────────────────");
print(`focos_snapshots:             ${db.focos_snapshots.countDocuments()}`);
print(`alertas:                     ${db.alertas.countDocuments()}`);
print(`ejecuciones_etl:             ${db.ejecuciones_etl.countDocuments()}`);

print("");
print("── Distribución por país ──────────────────────────────────────────");
const distribucion = db.focos_snapshots.aggregate([
    { $unwind: "$focos" },
    { $group: { _id: "$focos.pais", total: { $sum: 1 } } },
    { $sort: { total: -1 } }
]).toArray();
distribucion.forEach(d => print(`  ${d._id || "(sin país)"}: ${d.total} focos`));

print("");
print("Limpieza completa.");
