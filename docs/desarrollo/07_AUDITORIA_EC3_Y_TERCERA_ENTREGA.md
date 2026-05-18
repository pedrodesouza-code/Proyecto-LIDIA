# Auditoria EC3 y preparacion de tercera entrega

Este documento sirve para revisar el proyecto contra los requisitos de la
consigna y preparar la defensa de la tercera entrega. No reemplaza el informe
formal: es una guia practica para saber que esta cubierto, que evidencia mostrar
y que puntos conviene reforzar antes del tribunal.

## 1. Lectura ejecutiva

El proyecto tiene una base fuerte para EC3: hay ETL modular en Python, modelo
relacional PostgreSQL, modelo documental MongoDB, dashboard Streamlit, tests,
reportes de evidencia, Docker, seguridad documentada, backup y mediciones de
rendimiento.

El mayor riesgo no es que falte codigo central, sino que algunas evidencias
deben mostrarse de forma mas directa ante una banca exigente. Para la tercera
entrega conviene reforzar especialmente:

- CDC con prueba reproducible y salida cuantitativa.
- Dashboard con evidencia visual y relacion pregunta-consulta-visualizacion.
- Despliegue hibrido con pruebas de conectividad y capturas.
- Seguridad sin credenciales expuestas en el relato de defensa.
- Rendimiento actualizado cerca de la fecha de entrega.

## 2. Estado general por requisito EC3

| Requisito del documento | Estado actual | Evidencia principal | Riesgo ante tribunal | Accion recomendada |
|---|---:|---|---|---|
| Sistema funcional con datos reales | Alto | `reports/utec_verificacion_ultimo.json` | Que pidan ejecutar y no solo leer informe | Tener comandos de demo listos |
| Modelo SQL con DDL, integridad, constraints e indices | Alto | `sql/ddl/01_roles.sql` a `sql/ddl/04_vistas.sql` | Preguntas tabla por tabla | Usar guia ER y laboratorio SQL |
| Carga real mediante ETL | Alto | `etl/extract/`, `etl/transform/`, `etl/load/` | Preguntas sobre cada fuente | Explicar flujo fuente -> transformacion -> carga |
| Validacion post-carga | Alto | `tests/test_calidad_datos.py`, `tests/resultados_tests.json` | Que modifiquen datos y esperen reaccion | Practicar pruebas con `BEGIN` y `ROLLBACK` |
| Modelo NoSQL coherente y con datos reales | Medio/alto | `nosql/schemas/`, `reports/utec_verificacion_ultimo.json` | Mongo local puede no estar activo | Mostrar evidencia UTEC o levantar Mongo antes |
| Consultas NoSQL representativas | Alto | `nosql/queries/01_consultas.js` | Preguntas sobre por que Mongo | Defender snapshots, logs y resumenes |
| ETL modular con errores, logging y config | Alto | `config/settings.py`, `etl/utils/logger.py` | Que pidan donde se manejan errores | Mostrar config, logs y try/except por etapa |
| CDC funcional | Medio/alto | `scripts/evidenciar_cdc_ec3.py`, `reports/cdc_ec3_ultimo.json` | Mongo local no conectado en ultima prueba | Reejecutar con Mongo activo si se quiere evidencia completa |
| Testing e idempotencia | Alto | 17 tests automaticos | Que pidan prueba en vivo | Ejecutar pytest y explicar cada familia de test |
| Seguridad, roles y privilegio minimo | Medio/alto | `sql/ddl/01_roles.sql`, `sql/ddl/04_vistas.sql` | Passwords demo hardcodeados pueden ser criticados | Aclarar entorno demo o mover credenciales a variables |
| Backup y recuperacion | Alto | `scripts/backup_restore_real.py`, `reports/backup_restore_ultimo.json` | Preguntas sobre restauracion real | Mostrar manifest y procedimiento |
| Dashboard con KPIs y visualizaciones | Alto | `dashboard/app.py`, `docs/desarrollo/18_DEFENSA_DASHBOARD_SECCIONES.md` | Falta captura formal reciente | Capturar pantallas y relacionarlas con preguntas |
| Docker | Medio/alto | `docker/docker-compose.yml`, `docker/Dockerfile.streamlit` | Docker engine puede fallar en Windows | Mostrar `docker compose config --quiet` |
| Despliegue hibrido | Medio | `docs/DESPLIEGUE_HIBRIDO.md`, `config/utec.env.example` | Falta URL/captura cloud si no esta publicado | Completar evidencia de componente cloud |
| Rendimiento preliminar | Alto | `reports/rendimiento_ultimo.json`, `reports/sql_vs_nosql_real_ultimo.json` | Reportes pueden quedar viejos | Regenerar reportes antes de entregar |

## 3. Auditoria del modelo SQL

### Que esta bien

El proyecto tiene DDL separado por responsabilidades:

- `01_roles.sql`: seguridad y permisos.
- `02_schema.sql`: tablas, claves primarias, claves foraneas y restricciones.
- `03_indices.sql`: indices de consulta.
- `04_vistas.sql`: vistas para consulta controlada.
- `07_optimizacion_materializada.sql`: vistas materializadas para rendimiento.

Esto es defendible porque muestra diseno fisico real, no solo un diagrama.

### Como defenderlo

Frase recomendada:

> En PostgreSQL guardamos la verdad analitica normalizada. Cada tabla tiene un
> grano definido, constraints para evitar datos invalidos, claves unicas para
> sostener idempotencia y claves foraneas para preservar integridad referencial.

### Que puede preguntar el tribunal

- Por que `puntos_monitoreo` es dimension.
- Por que `focos_calor` es tabla de hechos.
- Que diferencia hay entre clave primaria y clave unica.
- Que pasa si intento cargar una medicion para un punto inexistente.
- Que pasa si cargo dos veces el mismo dato.
- Por que se agregaron indices por fecha, pais o punto.

### Accion pendiente

Practicar el laboratorio `docs/desarrollo/17_LAB_DEFENSA_PRUEBAS_TRIBUNAL.md`.
Esa guia permite modificar datos dentro de transacciones y volver atras con
`ROLLBACK`.

## 4. Auditoria del modelo NoSQL

### Que esta bien

MongoDB se usa para documentos donde tiene sentido operacional:

- snapshots diarios de focos;
- logs de ejecucion ETL;
- alertas;
- resumenes materializados por pais y por mes.

La evidencia UTEC muestra:

- `352` snapshots;
- `3` resumenes por pais;
- `39` resumenes por pais/mes;
- `0` snapshots sin pais.

### Como defenderlo

Frase recomendada:

> MongoDB no reemplaza a PostgreSQL. Lo usamos como complemento documental:
> PostgreSQL mantiene datos relacionales y MongoDB guarda snapshots y trazas
> operativas que se leen como documentos completos.

### Riesgo actual

La ultima prueba local de CDC intento conectar a MongoDB en `localhost:27017`,
pero el servicio no estaba activo. Eso no invalida la evidencia PostgreSQL ni la
evidencia UTEC, pero si el profesor pide demo local de Mongo hay que levantar el
servicio antes.

### Accion pendiente

Antes de defender, decidir una de estas dos opciones:

- levantar MongoDB local y reejecutar `python scripts/evidenciar_cdc_ec3.py`;
- usar la evidencia UTEC en `reports/utec_verificacion_ultimo.json` como prueba
  de MongoDB real.

## 5. Auditoria del ETL

### Que esta bien

El ETL esta separado por capas:

- `etl/extract/`: descarga u obtiene datos.
- `etl/transform/`: limpia, tipa, normaliza y enriquece.
- `etl/load/`: carga PostgreSQL y MongoDB.
- `etl/scheduler.py`: orquesta ejecuciones.
- `etl/utils/logger.py`: genera logs estructurados.
- `config/settings.py`: centraliza configuracion externa.

### Como defenderlo

Frase recomendada:

> La arquitectura ETL evita mezclar responsabilidades. Si falla una fuente, se
> puede revisar su extractor; si falla una regla de calidad, se revisa la
> transformacion; si falla la persistencia, se revisa el loader.

### Puntos que conviene dominar

- Que fuente alimenta cada tabla.
- Que columnas se tipan como fecha, numerico, texto o booleano.
- Donde se deduplican registros.
- Donde se calcula el indice de riesgo.
- Donde se aplica upsert.
- Donde se registra la ejecucion ETL.

## 6. Auditoria CDC

### Evidencia nueva

Se agrego:

```text
scripts/evidenciar_cdc_ec3.py
reports/cdc_ec3_ultimo.json
docs/desarrollo/06_EVIDENCIA_CDC_EC3.md
```

La prueba PostgreSQL demuestra:

| Operacion | Resultado observado | Interpretacion |
|---|---:|---|
| Insercion inicial | `insert_inicial_rowcount = 1` | El registro nuevo entra |
| Repeticion idempotente | `repeticion_idempotente_rowcount = 0` | No duplica |
| Modificacion CDC | `modificacion_cdc_rowcount = 1` | Detecta cambio y actualiza |
| Conteo final | `despues_rollback = 0` | La base queda limpia |

### Como defenderlo

Frase recomendada:

> CDC significa que el pipeline no necesita recargar todo para reflejar cambios.
> Identifica una clave natural, compara el dato entrante con el existente y solo
> inserta o actualiza cuando corresponde.

### Accion pendiente

Reejecutar la prueba el dia de la defensa para generar un JSON con fecha
reciente.

## 7. Auditoria del dashboard

### Que esta bien

El dashboard Streamlit existe en:

```text
dashboard/app.py
dashboard/db.py
```

Y la defensa por secciones esta en:

```text
docs/desarrollo/18_DEFENSA_DASHBOARD_SECCIONES.md
```

### Riesgo actual

La consigna pide KPIs, agregaciones temporales, comparaciones y coherencia entre
preguntas, consultas y visualizaciones. El codigo existe, pero ante tribunal
conviene mostrar evidencia visual reciente: capturas o demo en vivo.

### Accion pendiente

Preparar una corrida local:

```bash
python -m streamlit run dashboard/app.py --server.port 8502
```

Luego revisar:

- KPIs principales.
- Evolucion temporal.
- Comparacion por pais.
- Comparacion por fuente o nivel de riesgo.
- Tabla o detalle exploratorio.
- Filtros.
- Mensajes cuando no hay datos.

## 8. Auditoria de seguridad

### Que esta bien

El proyecto incluye:

- roles SQL;
- vistas;
- configuracion externa;
- variables de entorno;
- documentacion de seguridad;
- backup y restore.

### Riesgo actual

`sql/ddl/01_roles.sql` contiene passwords de demostracion. En defensa hay que
evitar decir que esas son credenciales productivas.

### Como defenderlo

Frase recomendada:

> Las credenciales reales se manejan por variables de entorno. Los valores
> visibles en scripts son de laboratorio o demostracion, no secretos productivos.

### Accion recomendada

Mejorar el archivo de roles para que use placeholders o documentar claramente
que son claves demo.

## 9. Auditoria de rendimiento

### Que esta bien

Hay scripts y reportes:

- `scripts/medir_rendimiento.py`
- `scripts/comparar_sql_nosql_real.py`
- `reports/rendimiento_ultimo.json`
- `reports/sql_vs_nosql_real_ultimo.json`
- `docs/SLA_Y_RENDIMIENTO.md`

### Riesgo actual

Si el tribunal pregunta por rendimiento, un reporte de varios dias antes sirve,
pero es mas fuerte mostrar uno regenerado cerca de la entrega.

### Accion pendiente

Antes de entregar:

```bash
python scripts/medir_rendimiento.py
python scripts/comparar_sql_nosql_real.py
```

Si MongoDB no esta activo, explicar que la comparacion contra motores reales
depende de conectividad a PostgreSQL/MongoDB.

## 10. Que falta para cerrar la tercera entrega

Prioridad alta:

1. Reejecutar tests y dejar `tests/resultados_tests.json` actualizado.
2. Reejecutar `scripts/evidenciar_cdc_ec3.py` con PostgreSQL y, si es posible,
   MongoDB activo.
3. Abrir dashboard y generar evidencia visual.
4. Regenerar reportes de rendimiento.
5. Revisar el tema de passwords demo en `sql/ddl/01_roles.sql`.

Prioridad media:

1. Confirmar si hay URL cloud de Streamlit o evidencia equivalente.
2. Confirmar que Docker Compose valida en el entorno de entrega.
3. Confirmar que el informe formal cite los reportes mas recientes.
4. Ensayar preguntas de tribunal con datos modificados en transacciones.

Prioridad baja:

1. Ordenar capturas en una carpeta de evidencia.
2. Preparar una version corta de defensa de 5 minutos.
3. Preparar una version extendida de defensa de 15 a 20 minutos.

## 11. Comandos recomendados para el dia de defensa

Validar tests:

```bash
python -m pytest tests/test_calidad_datos.py -q
```

Generar evidencia CDC:

```bash
python scripts/evidenciar_cdc_ec3.py
```

Validar Docker Compose:

```bash
docker compose -f docker/docker-compose.yml --env-file docker/.env.example config --quiet
```

Abrir dashboard:

```bash
python -m streamlit run dashboard/app.py --server.port 8502
```

Ver estado Git:

```bash
git status --short
```

## 12. Conclusion de auditoria

El proyecto esta bien encaminado para la tercera entrega. La implementacion
principal esta realizada y hay evidencia tecnica. Lo que falta es convertir esa
evidencia en demostracion defendible: pruebas recientes, capturas, comandos
preparados y explicacion clara de que pasa cuando se insertan, repiten, modifican
o consultan datos.

La defensa debe enfocarse en demostrar comportamiento, no solo estructura:

- si se carga dos veces, no duplica;
- si cambia un dato, se actualiza;
- si entra un dato invalido, la base o los tests lo detectan;
- si se consulta el dashboard, responde desde datos persistidos;
- si se necesita auditar, hay logs y reportes.
