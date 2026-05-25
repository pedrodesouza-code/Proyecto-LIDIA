// =============================================================================
// SINIA-UY — Inicialización MongoDB
// =============================================================================
// Este script crea el usuario de la aplicación y la base de datos.
// Se ejecuta automáticamente en el primer arranque del contenedor MongoDB.
// =============================================================================

db = db.getSiblingDB("sinia_uy");

const appUser = process.env.MONGO_USER || "sinia_etl_user";
const appPassword = process.env.MONGO_PASSWORD || "sinia_etl_2026";
const dashUser = process.env.MONGO_DASH_USER || "sinia_dash_user";
const dashPassword = process.env.MONGO_DASH_PASSWORD || "sinia_dash_2026";

// Crear usuario con permisos de lectura+escritura sobre sinia_uy
db.createUser({
    user: appUser,
    pwd:  appPassword,
    roles: [
        { role: "readWrite", db: "sinia_uy" }
    ]
});

// Crear usuario de solo lectura para el dashboard
db.createUser({
    user: dashUser,
    pwd:  dashPassword,
    roles: [
        { role: "read", db: "sinia_uy" }
    ]
});

// Crear las colecciones con las validaciones básicas
// (el setup completo con JSON Schema lo hace load_mongo.py)
db.createCollection("ejecuciones_etl");
db.createCollection("alertas");
db.createCollection("focos_snapshots");

print("MongoDB sinia_uy inicializado correctamente.");
