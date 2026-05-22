# Guion de demo oral para tercera entrega

Este guion sirve para defender el proyecto en vivo sin perderse. La idea es
mostrar comportamiento real: datos, ETL, bases, CDC, pruebas, dashboard y
rendimiento.

## 1. Apertura de 1 minuto

Frase inicial:

> El proyecto SINIA-UY integra datos satelitales, meteorologicos y ambientales
> para monitorear riesgo de incendios en Uruguay, Brasil, Argentina y Chile. La solucion
> implementa un pipeline ETL en Python, persistencia relacional en PostgreSQL,
> persistencia documental en MongoDB y un dashboard Streamlit para analisis.

Puntos clave:

- problema real;
- fuentes reales;
- ETL modular;
- SQL para integridad;
- MongoDB para documentos, snapshots y trazabilidad;
- dashboard para consumo analitico;
- tests y reportes para evidencia.

## 2. Mostrar estructura del proyecto

Abrir:

```text
docs/desarrollo/00_INDICE.md
```

Decir:

> Este indice es el punto de navegacion. Separamos defensa ETL, modelo ER,
> dashboard, pruebas de tribunal, CDC, rendimiento y MongoDB para poder explicar
> cada parte sin mezclar conceptos.

## 3. Defender el ETL

Mostrar carpetas:

```text
etl/extract/
etl/transform/
etl/load/
etl/scheduler.py
config/settings.py
etl/utils/logger.py
```

Frase:

> Extract obtiene datos de fuentes externas o archivos. Transform normaliza,
> tipa, limpia y calcula variables derivadas. Load persiste en PostgreSQL y
> MongoDB usando cargas idempotentes. El scheduler orquesta y el logger registra
> trazabilidad.

Si preguntan por que se hizo asi:

> Porque separar responsabilidades permite depurar mejor. Si falla una API, miro
> extract; si falla un tipo de dato, miro transform; si falla una insercion, miro
> load.

## 4. Defender PostgreSQL

Mostrar:

```text
sql/ddl/01_roles.sql
sql/ddl/02_schema.sql
sql/ddl/03_indices.sql
sql/ddl/04_vistas.sql
```

Frase:

> PostgreSQL guarda la verdad analitica. Tiene tablas con grano claro, claves
> primarias, claves foraneas, restricciones, indices y vistas.

Preguntas tipicas:

- `puntos_monitoreo` es dimension porque describe lugares.
- `focos_calor` es hecho porque cada fila es una deteccion satelital.
- las claves unicas permiten idempotencia;
- las claves foraneas protegen integridad referencial;
- los indices aceleran filtros por fecha, pais y punto.

## 5. Defender MongoDB

Mostrar:

```text
nosql/schemas/
nosql/queries/01_consultas.js
reports/utec_verificacion_ultimo.json
docs/desarrollo/09_EVIDENCIA_RENDIMIENTO_Y_MONGO.md
```

Frase:

> MongoDB se usa como complemento documental. Guarda snapshots diarios,
> ejecuciones ETL, alertas y resumenes materializados. No reemplaza PostgreSQL:
> cumple una funcion operacional distinta.

Si preguntan por Mongo local:

> Docker fallo por WSL con codigo `Wsl/0x80070422`, pero resolvimos la demo
> usando MongoDB nativo de Windows. Mongo local esta activo en `localhost:27017`
> con snapshots, resumenes materializados y ejecuciones ETL.

## 6. Demo CDC

Ejecutar:

```bash
python scripts/evidenciar_cdc_ec3.py
```

Mostrar:

```text
reports/cdc_ec3_ultimo.json
```

Explicar:

> La prueba inserta un registro temporal, repite la carga para demostrar que no
> duplica, modifica valores para demostrar CDC y termina con rollback para dejar
> la base limpia.

Valores que hay que decir:

```text
insert_inicial_rowcount = 1
repeticion_idempotente_rowcount = 0
modificacion_cdc_rowcount = 1
despues_rollback = 0
```

Interpretacion:

- `1`: inserto;
- `0`: no duplico;
- `1`: actualizo cambio;
- `0`: rollback dejo limpio.

## 7. Demo tests

Ejecutar:

```bash
python -m pytest tests/test_calidad_datos.py -q
```

Frase:

> Los tests validan calidad, reglas de negocio, idempotencia y CDC. Sirven como
> evidencia automatica de que el pipeline no depende solo de revision manual.

Resultado esperado:

```text
20 passed
```

## 8. Demo rendimiento

Mostrar:

```text
reports/rendimiento_ultimo.json
reports/sql_vs_nosql_real_ultimo.json
```

Frase:

> El rendimiento se mide con reportes reproducibles. Se miden lecturas,
> consultas analiticas, incremental e idempotencia contra un SLA de consulta de
> 3000 ms.

Datos fuertes:

```text
consultas_medidas = 12
sla_consulta_ms = 3000
postgres_estado = ok
postgres_metricas = 4
```

## 9. Demo dashboard

Ejecutar:

```bash
python -m streamlit run dashboard/app.py --server.port 8502
```

Abrir:

```text
http://localhost:8502
```

Mostrar:

- Resumen General.
- Focos de Calor.
- Indice de Riesgo.
- Comparativo por Pais.
- Fuentes y Datos Crudos.

Frase:

> El dashboard consulta datos persistidos y muestra KPIs, agregaciones
> temporales, comparaciones por pais y vistas de datos crudos. Para mapas usa
> muestra visual acotada, pero los KPIs usan conteos reales.

Evidencia:

```text
reports/dashboard_evidencia_ultimo.png
docs/desarrollo/08_EVIDENCIA_DASHBOARD_EC3.md
```

## 10. Cierre de 1 minuto

Frase final:

> La implementacion cumple la tercera entrega porque no se queda en diseno:
> extrae, transforma, carga, valida, mide rendimiento, demuestra CDC y expone el
> resultado en un dashboard. PostgreSQL asegura integridad; MongoDB aporta
> documentos y trazabilidad; Python automatiza el flujo; y los reportes dejan
> evidencia reproducible.

## 11. Preguntas dificiles y respuestas cortas

Pregunta: Por que SQL y NoSQL?

Respuesta:

> SQL para datos estructurados, integridad y consultas analiticas. NoSQL para
> snapshots, logs, alertas y documentos flexibles.

Pregunta: Que pasa si cargo dos veces?

Respuesta:

> No duplica porque usamos claves naturales y upsert. La evidencia CDC muestra
> `repeticion_idempotente_rowcount = 0`.

Pregunta: Que pasa si modifican un dato?

Respuesta:

> El upsert detecta diferencia y actualiza. La evidencia muestra
> `modificacion_cdc_rowcount = 1`.

Pregunta: Que pasa si entra dato invalido?

Respuesta:

> Lo frenan las transformaciones, los tests o las constraints de base segun el
> caso. No dependemos de una sola capa.

Pregunta: Por que Docker dio error?

Respuesta:

> Porque Windows/WSL devolvio `Wsl/0x80070422`. No fue error del modelo NoSQL.
> Para la demo local usamos `mongod.exe` nativo y Mongo quedo funcionando.

Pregunta: Por que el mapa no muestra todos los millones de puntos?

Respuesta:

> Porque no aporta claridad visual y afecta rendimiento. Los KPIs calculan el
> total real; el mapa usa una muestra priorizada para visualizacion.

## 12. Orden recomendado de ejecucion

1. Abrir `docs/desarrollo/00_INDICE.md`.
2. Mostrar arquitectura ETL.
3. Mostrar DDL SQL.
4. Mostrar evidencia Mongo UTEC.
5. Ejecutar CDC.
6. Ejecutar tests.
7. Mostrar rendimiento.
8. Abrir dashboard.
9. Cerrar con fortalezas y limitaciones.
