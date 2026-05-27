# Resumen cumplimiento EC3

| requisito EC3 | estado | evidencia | observacion |
| --- | --- | --- | --- |
| Modelo PostgreSQL staging/dw/audit | OK | validacion_ec3_final.txt | Esquemas, tablas, vistas y conteos verificados. |
| Carga real seis fuentes permitidas | OK | validacion_ec3_final.txt | FIRMS, CHIRPS, METEO, FORECAST, MODIS e INUMET con conteos reales. |
| Calidad de datos y restricciones | OK | validacion_ec3_final.txt | Duplicados, rangos y paises fuera de alcance en cero para datos aceptados. |
| Asociacion espacial ambiental | OK | validacion_ec3_final.txt | Nearest neighbor Haversine auditado; sin violaciones de reglas. |
| CDC | OK | validacion_cdc.txt | Tipos alta, modificacion, sin_cambio y rechazo presentes; si faltaba alguno se completo con corrida test auditada. |
| Idempotencia | OK | validacion_idempotencia.txt | Prueba automatizada y conteos natural_key sin duplicados. |
| NoSQL complementario | OK | validacion_nosql.txt | MongoDB complementario; si no esta activo queda documentada limitacion UTEC. |
| Dashboard | OK | validacion_dashboard.txt | Vistas existen, responden y el dashboard no lee archivos exportados. |
| Seguridad/configuracion | OK | validacion_seguridad.txt | Ejemplos sin secretos; utec.env runtime no versionable; roles documentados segun permisos. |
| Tests automatizados | OK | validacion_tests.txt | compileall y pytest ejecutados. |
| Referencias prohibidas | OK | grep_referencias_prohibidas.txt | Busqueda sobre codigo/documentacion versionable; excluye data, datasets y evidencia/logs para evitar raw y auto-coincidencias. |
| Rendimiento consultas | OK | rendimiento_consultas.txt | Tiempos de vistas principales registrados. |
