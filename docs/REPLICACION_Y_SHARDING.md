# Replicacion y sharding

Revision actualizada: **2026-05-22**.

La consigna pide replicacion en ambos motores y sharding o simulacion de alto volumen. En este proyecto se adopta una postura explicita:

- el entorno local operativo usa un nodo PostgreSQL y un nodo MongoDB por simplicidad academica;
- la arquitectura documenta como se replicaria cada motor;
- el sharding se valida con una simulacion reproducible basada en datos FIRMS reales.

## Replicacion definida

### PostgreSQL

Modelo propuesto:

- 1 primario de escritura para ETL.
- 1 o 2 replicas de solo lectura para dashboard y consultas pesadas.
- Replicacion fisica por WAL streaming.
- Promocion de replica ante caida del primario.

Justificacion:

- `focos_calor`, `meteo_diario` y `calidad_aire_diario` son datos historicos y reprocesables desde fuentes externas.
- La replicacion asincrona admite una perdida potencial pequena porque el ETL puede reejecutarse de forma idempotente.
- Las lecturas analiticas pueden moverse a una replica para no competir con cargas.

Evidencia:

- Modelo relacional en `sql/ddl/02_schema.sql`.
- Indices en `sql/ddl/03_indices.sql`.
- Roles en `sql/ddl/01_roles.sql`.
- Docker local en `docker/docker-compose.yml`.

Blueprint operativo:

```text
postgres_primary  -> puerto 5432
postgres_replica1 -> puerto 5433, hot_standby=on
```

### MongoDB

Modelo propuesto:

- Replica set de 3 miembros.
- 1 primario para escrituras ETL.
- 2 secundarios o 1 secundario + 1 arbitro segun recursos.
- Eleccion automatica ante caida del primario.

Justificacion:

- MongoDB guarda alertas, snapshots y trazabilidad ETL.
- La disponibilidad de escritura protege la auditoria operacional.
- El replica set es el patron nativo de alta disponibilidad de MongoDB.

Evidencia:

- JSON Schema en `nosql/schemas/`.
- Inicializacion en `nosql/init/01_setup_mongo.js`.
- Consultas en `nosql/queries/01_consultas.js`.
- Carga documental en `etl/load/load_mongo.py`.

## Sharding simulado

Ejecucion:

```bash
python scripts/simular_sharding.py
```

Reportes:

- `reports/sharding_simulado_ultimo.json`
- `reports/sharding_simulado_20260520_093426.json`

### SQL / Data Warehouse

Tabla candidata: `focos_calor`.

Shard key propuesta: `fecha_adq`.

Estrategia: particionamiento por rango trimestral.

Resultado medido sobre `1.946.361` focos:

| Metrica | Valor |
|---|---:|
| Shards logicos | `9` |
| Registros totales | `1.946.361` |
| Minimo por shard | `5.385` |
| Maximo por shard | `1.152.194` |
| Promedio por shard | `216.262,33` |
| Desbalance max/promedio | `5,328` |

Top shards:

| Shard | Registros |
|---|---:|
| `2024Q3` | `1.152.194` |
| `2024Q4` | `439.390` |
| `2024Q1` | `157.402` |
| `2024Q2` | `124.712` |
| `2026Q1` | `24.104` |

Interpretacion:

La distribucion no es uniforme porque los focos de calor son estacionales y regionalmente concentrados. La clave `fecha_adq` sigue siendo defendible porque las consultas principales filtran o agregan por tiempo y pueden beneficiarse de pruning temporal.

### MongoDB

Coleccion candidata: `focos_snapshots`.

Shard key propuesta: `{ fecha: 1, pais: "hashed" }`.

Estrategia: rango temporal mensual combinado con hash conceptual de pais.

Resultado medido:

| Metrica | Valor |
|---|---:|
| Shards logicos | `51` |
| Registros totales | `1.946.361` |
| Minimo por shard | `96` |
| Maximo por shard | `579.505` |
| Promedio por shard | `38.163,94` |
| Desbalance max/promedio | `15,185` |

Interpretacion:

El desbalance alto muestra que una clave solo temporal concentraria escrituras y lecturas en meses de fuego intenso. Combinar fecha con pais hasheado mejora la distribucion conceptual sin perder consultas por ventana temporal.

## Decision final

No se activa sharding real porque agregaria complejidad mayor al beneficio para el volumen academico actual. La decision arquitectonica esta tomada y respaldada por simulacion: si el sistema escala, se particiona `focos_calor` por `fecha_adq` y se shardea `focos_snapshots` por `{ fecha: 1, pais: "hashed" }`.
