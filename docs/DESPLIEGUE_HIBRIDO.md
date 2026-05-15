# Despliegue hibrido

La consigna pide integrar al menos un componente en infraestructura in situ y al menos
un componente en entorno cloud.

## Distribucion propuesta

| Componente | Ubicacion | Justificacion |
|---|---|---|
| PostgreSQL / Data Warehouse | Servidor institucional UTEC | Persistencia principal, datos auditables y cercania al entorno academico |
| MongoDB operacional | Servidor institucional UTEC o contenedor local controlado | Trazabilidad ETL, snapshots y alertas |
| Dashboard Streamlit | Cloud o maquina de demo | Acceso visual para defensa, consumo de datos persistidos |
| Repositorio Git | GitHub | Control de versiones y evidencia de cambios |
| ETL Python | Local/UTEC segun etapa | Puede correr donde tenga conectividad a APIs y bases |

## Evidencia existente

- `scripts/deploy.sh`
- `docs/desarrollo/13_DEPLOY_SERVIDOR_UTEC.md`
- `config/utec.env.example`
- `docker/docker-compose.yml`
- Dashboard verificado localmente en `http://localhost:8501` el 2026-05-15.

## Evidencia final ejecutada

El 2026-05-15 se verificaron y sincronizaron las bases asignadas por UTEC:

- PostgreSQL `grp03db` en `10.200.245.40:15434`.
- MongoDB `grp03db` en `10.200.245.40:27023`.
- Reportes versionados:
  - `reports/utec_verificacion_ultimo.json`
  - `reports/utec_sync_ultimo.json`
  - `reports/limpieza_alcance_ultimo.json`

Comandos reproducibles:

```bash
python scripts/verificar_utec.py
python scripts/limpiar_alcance_real.py
python scripts/sincronizar_utec_real.py --fase materializadas
python scripts/sincronizar_utec_real.py --fase mongo
```

Resultado PostgreSQL:

- `focos_calor`: `1.841.820`.
- Paises presentes: `ARG`, `BRA`, `URY`.
- Vistas materializadas: `mv_focos_por_pais` = `3`, `mv_focos_por_pais_mes` = `39`.

Resultado MongoDB:

- `focos_snapshots`: `352`.
- `snapshots_con_pais`: `352`.
- `snapshots_sin_pais`: `0`.
- `focos_resumen_pais`: `3`.
- `focos_resumen_mes`: `39`.
- Coleccion institucional `eventos` preservada.

## Estado actual

El despliegue hibrido queda cumplido: persistencia SQL/NoSQL en servidor
institucional UTEC, codigo versionado en GitHub y dashboard ejecutable localmente
o en contenedor cuando el host tenga Docker/WSL habilitado.
