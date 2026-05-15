# Revision y sincronizacion UTEC - 2026-05-15

## Objetivo

Verificar las bases de datos del servidor UTEC y dejarlas alineadas con el
alcance final real del sistema SINIA-UY: Uruguay, Brasil y Argentina.

## Estado inicial encontrado

Antes del cierre final, PostgreSQL UTEC estaba accesible pero contenia datos del
alcance regional anterior y MongoDB tenia snapshots sin el campo `pais` embebido.

- PostgreSQL tenia `3.836.386` focos, incluyendo `BOL`, `CHL`, `PER`, `PRY` y `OTR`.
- MongoDB tenia `352` snapshots, pero los documentos no servian para resumenes por pais.
- Las vistas materializadas finales no estaban creadas.

## Acciones ejecutadas

Se realizo una sincronizacion controlada contra UTEC, preservando colecciones
ajenas como `eventos` y sin guardar credenciales en el repositorio.

Acciones PostgreSQL UTEC:

- Aplicacion de DDL, indices, vistas y seed de puntos.
- Limpieza de alcance a `URY`, `BRA`, `ARG`.
- Creacion de `mv_focos_por_pais` y `mv_focos_por_pais_mes`.

Acciones MongoDB UTEC:

- Actualizacion de validadores e indices.
- Eliminacion de snapshots sin `pais`.
- Carga de `347` snapshots historicos y `5` snapshots NRT con `pais` embebido.
- Creacion de resumenes materializados `focos_resumen_pais` y `focos_resumen_mes`.

## Verificacion final UTEC

PostgreSQL UTEC:

| Control | Resultado |
|---|---:|
| `focos_calor` total | `1841820` |
| `focos_calor` rango total | `2024-01-01` a `2026-05-15` |
| focos ultimos 7 dias | `5283` |
| paises presentes | `ARG`, `BRA`, `URY` |
| `puntos_monitoreo` | `11` |
| `meteo_diario` | `11564` |
| `calidad_aire_diario` | `3997` |
| `precipitacion_mensual` | `702` |
| `cobertura_vegetal` | `63` |
| `mv_focos_por_pais` | `3` |
| `mv_focos_por_pais_mes` | `39` |

MongoDB UTEC:

| Control | Resultado |
|---|---:|
| colecciones | `alertas`, `ejecuciones_etl`, `eventos`, `focos_resumen_mes`, `focos_resumen_pais`, `focos_snapshots` |
| `focos_snapshots` | `352` |
| `snapshots_con_pais` | `352` |
| `snapshots_sin_pais` | `0` |
| `focos_resumen_pais` | `3` |
| `focos_resumen_mes` | `39` |
| `ejecuciones_etl` | `3` |
| `alertas` | `0` |
| `eventos` | `2` |
| ultimo snapshot | `2026-05-15` |
| focos en ultimo snapshot | `303` |
| ultima ejecucion Mongo | `firms_nrt/load`, estado `ok` |

## Actualizacion de permisos MongoDB

Luego de solicitar el permiso al encargado del servidor, se verifico que el
usuario `grp03` ya puede ejecutar `collMod` sobre `grp03db`.

Resultado de la verificacion:

| Coleccion | Validador JSON Schema | Indices verificados |
|---|---|---|
| `ejecuciones_etl` | aplicado | `_id_`, `idx_estado`, `idx_fuente_inicio` |
| `alertas` | aplicado | `_id_`, `idx_activas`, `idx_fecha_gen`, `idx_tipo_nivel` |
| `focos_snapshots` | aplicado | `_id_`, `idx_fecha_unico` |

Conteos al momento de la verificacion final:

| Coleccion | Documentos |
|---|---:|
| `ejecuciones_etl` | `3` |
| `alertas` | `0` |
| `focos_snapshots` | `352` |

## Observaciones

- Las bases del servidor UTEC quedaron actualizadas con alcance real al `2026-05-15`.
- MongoDB UTEC ya permite actualizar validadores JSON Schema con `collMod`.
- MongoDB fue recargado con historico y NRT reales para que los resumenes por pais sean correctos.
- La evidencia reproducible quedo en `reports/utec_verificacion_ultimo.json` y `reports/utec_sync_ultimo.json`.

## Conclusion

El sistema local esta operativo y las bases UTEC quedaron sincronizadas con datos
reales, alcance correcto y agregados SQL/NoSQL listos para dashboard y consultas.
