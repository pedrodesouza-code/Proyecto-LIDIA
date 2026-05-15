# Replicacion y sharding

Fecha de cierre tecnico: 2026-05-15.

La consigna pide replicacion en ambos motores y sharding o simulacion de alto volumen.
En este proyecto se adopta una postura explicita:

- el entorno local operativo usa un nodo PostgreSQL y un nodo MongoDB por simplicidad
  academica y porque el volumen cabe en un unico nodo;
- la arquitectura final documenta como se replica cada motor;
- el sharding se valida con una simulacion reproducible basada en los datos FIRMS reales.

## Replicacion definida

### PostgreSQL

Modelo propuesto:

- 1 primario de escritura para ETL.
- 1 o 2 replicas de solo lectura para dashboard y consultas pesadas.
- Replicacion fisica por WAL streaming.
- Promocion de replica ante caida del primario.

Justificacion:

- `focos_calor`, `meteo_diario` y `calidad_aire_diario` son datos historicos y
  reprocesables desde fuentes externas.
- La replicacion asincrona admite una perdida potencial de segundos, porque el ETL
  puede reejecutarse de forma idempotente.
- Las lecturas analiticas pueden moverse a una replica para no competir con cargas.

Evidencia actual:

- Modelo relacional operativo en `sql/ddl/02_schema.sql`.
- Indices en `sql/ddl/03_indices.sql`.
- Roles en `sql/ddl/01_roles.sql`.
- Docker local en `docker/docker-compose.yml`.

Blueprint operativo para replica real:

```text
postgres_primary  -> puerto 5432
postgres_replica1 -> puerto 5433, hot_standby=on
```

La configuracion real requiere montar `postgresql.conf`, `pg_hba.conf`, usuario
`replicator`, slot o `primary_conninfo`, y un `pg_basebackup` inicial.

### MongoDB

Modelo propuesto:

- Replica set de 3 miembros.
- 1 primario para escrituras de ETL.
- 2 secundarios o 1 secundario + 1 arbitro segun recursos.
- Eleccion automatica ante caida del primario.

Justificacion:

- MongoDB guarda alertas, snapshots y trazabilidad ETL.
- La disponibilidad de escritura es importante para no perder auditoria operativa.
- El replica set es el patron nativo de alta disponibilidad de MongoDB.

Evidencia actual:

- JSON Schema en `nosql/schemas/`.
- Inicializacion en `nosql/init/01_setup_mongo.js`.
- Consultas representativas en `nosql/queries/01_consultas.js`.
- Carga documental en `etl/load/load_mongo.py`.

Blueprint operativo para replica real:

```text
mongo1 -> rs0 primary
mongo2 -> rs0 secondary
mongo3 -> rs0 secondary/arbiter
```

## Sharding simulado

Ejecucion:

```bash
python scripts/simular_sharding.py
```

Reportes:

- `reports/sharding_simulado_ultimo.json`
- `reports/sharding_simulado_20260515_101451.json`

### SQL / Data Warehouse

Tabla candidata: `focos_calor`.

Shard key propuesta: `fecha_adq`.

Estrategia: particionamiento por rango trimestral.

Resultado medido sobre 1.836.537 focos:

| Metrica | Valor |
|---|---:|
| Shards logicos | 4 |
| Registros totales | 1.836.537 |
| Minimo por shard | 117.770 |
| Maximo por shard | 1.144.932 |
| Promedio por shard | 459.134,25 |
| Desbalance max/promedio | 2,494 |

Shards mas grandes:

| Shard | Registros |
|---|---:|
| 2024Q3 | 1.144.932 |
| 2024Q4 | 429.663 |
| 2024Q1 | 144.172 |
| 2024Q2 | 117.770 |

Interpretacion:

La distribucion no es perfectamente uniforme porque los incendios son estacionales.
Eso no invalida la shard key: las consultas principales del proyecto son temporales,
por lo que `fecha_adq` permite pruning de particiones. Una consulta Q1 2024 toca solo
el shard `2024Q1`.

### MongoDB

Coleccion candidata: `focos_snapshots`.

Shard key propuesta: `{ fecha: 1, pais: "hashed" }`.

Estrategia: rango temporal mensual combinado con hash conceptual de pais.

Resultado medido:

| Metrica | Valor |
|---|---:|
| Shards logicos | 36 |
| Registros totales | 1.836.537 |
| Minimo por shard | 96 |
| Maximo por shard | 579.505 |
| Promedio por shard | 51.014,92 |
| Desbalance max/promedio | 11,36 |

Interpretacion:

El desbalance alto muestra un punto importante para la defensa: la actividad de fuego
esta muy concentrada en meses secos y en Brasil. Por eso una clave solo creciente por
fecha seria riesgosa. Agregar `pais` con hash ayuda a distribuir escrituras recientes
sin perder la capacidad de consultar por ventanas temporales.

## Decision final

No se activa sharding real en local porque agregaria complejidad mayor al beneficio para
un volumen academico que ya responde bajo SLA. La decision arquitectonica esta tomada
y validada: si el sistema escala, se particiona `focos_calor` por `fecha_adq` y se shardea
`focos_snapshots` por `{ fecha: 1, pais: "hashed" }`.
