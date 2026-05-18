# Evidencia CDC para EC3

La consigna de EC3 pide demostrar carga inicial, carga incremental, insercion de
nuevos registros, modificacion de existentes, impacto cuantitativo y trazabilidad.

Para practicar y generar evidencia reproducible se agrega:

```text
scripts/evidenciar_cdc_ec3.py
```

## Que demuestra

En PostgreSQL:

1. Inserta un registro temporal en `meteo_diario`.
2. Repite el mismo upsert para demostrar idempotencia.
3. Modifica el indice y nivel de riesgo para demostrar CDC.
4. Lee el valor modificado dentro de la transaccion.
5. Ejecuta `ROLLBACK` para dejar la base como estaba.

En MongoDB:

1. Inserta una ejecucion ETL temporal en `ejecuciones_etl`.
2. Verifica que el documento exista.
3. Lo elimina para no ensuciar la coleccion.
4. Deja `mongo.estado = ok` cuando MongoDB local esta escuchando en
   `localhost:27017`.

## Como ejecutarlo

```bash
python scripts/evidenciar_cdc_ec3.py
```

## Salida esperada

El script genera:

```text
reports/cdc_ec3_ultimo.json
reports/cdc_ec3_YYYYMMDD_HHMMSS.json
```

## Como defenderlo

Frase corta:

> La prueba usa la misma logica de `ON CONFLICT` que el loader. Primero inserta,
> despues reejecuta sin duplicar, luego modifica y actualiza. Todo ocurre dentro
> de una transaccion con rollback, por eso se puede demostrar ante el tribunal
> sin alterar la base real.

## Evidencia que hay que mostrar

En el JSON revisar:

- `insert_inicial_rowcount`
- `repeticion_idempotente_rowcount`
- `modificacion_cdc_rowcount`
- `conteos.antes`
- `conteos.durante_transaccion`
- `conteos.despues_rollback`

Lectura:

- si `insert_inicial_rowcount = 1`, se inserto un nuevo registro;
- si `repeticion_idempotente_rowcount = 0`, no se duplico;
- si `modificacion_cdc_rowcount = 1`, se detecto y aplico cambio;
- si `despues_rollback` vuelve al valor inicial, la prueba fue segura;
- si `mongo.estado = ok`, tambien se demostro insercion y limpieza documental.
