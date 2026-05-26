# MongoDB

PostgreSQL conserva el Data Warehouse y las consultas analiticas. MongoDB se
limita a documentos variables: metadata de ejecucion, rechazos con payload
original y snapshots FIRMS resumidos. Estos documentos admiten distintos
detalles por fuente sin modificar el esquema estrella.

`mongo_schema.json` contiene los validadores JSON Schema y
`mongo_queries.js` consultas representativas. No se almacenan credenciales ni
se propone sharding para el servidor institucional.
