# Seguridad, backup y gobernanza

## Seguridad implementada

El proyecto aplica separacion de responsabilidades en PostgreSQL:

| Rol | Proposito | Evidencia |
|---|---|---|
| `sinia_readonly` | Lectura para dashboard y consultas analiticas | `sql/ddl/01_roles.sql` |
| `sinia_etl` | Insercion y actualizacion desde pipeline ETL | `sql/ddl/01_roles.sql` |
| `sinia_admin` | Administracion y mantenimiento | `sql/ddl/01_roles.sql` |

Tambien usa vistas para exponer datos analiticos sin obligar al dashboard a consultar
tablas base directamente:

- `sql/ddl/04_vistas.sql`
- `dashboard/db.py`

La configuracion se externaliza por variables de entorno:

- `config/settings.py`
- `config/utec.env.example`
- `docker/.env.example`

## Riesgos residuales

| Riesgo | Estado | Mitigacion |
|---|---|---|
| Passwords de desarrollo visibles en ejemplos Docker/SQL | Riesgo bajo en entorno local, alto si se reutilizan en produccion | Cambiar valores en `config/.env` y servidor UTEC; no commitear `.env` real |
| Mongo local sin autenticacion fuerte si se ejecuta fuera de Docker | Riesgo medio | Usar credenciales de Docker o replica set con auth en entorno final |
| Dashboard con fallback a Parquet | Riesgo bajo | Es util para demo, pero en produccion debe priorizar PostgreSQL |
| Datos satelitales con falsos positivos/negativos | Riesgo analitico | Reportar limitaciones de FIRMS y usar confianza del sensor |

## Verificacion de no exposicion

Antes de entregar:

```bash
git status --short
rg -n "PASSWORD|PASS|SECRET|MAP_KEY|TOKEN|API_KEY" .
```

El objetivo no es eliminar ejemplos, sino confirmar que no haya secretos reales en:

- `config/.env`
- notebooks/exportaciones temporales
- logs con cadenas de conexion

## Backup

El repositorio contiene scripts de respaldo y restauracion:

- `backups/backup.sh`
- `backups/restore.sh`

Estrategia de backup:

| Componente | Metodo | Frecuencia recomendada |
|---|---|---|
| PostgreSQL | `pg_dump` | Diario durante etapa de defensa |
| MongoDB | `mongodump` | Diario durante etapa de defensa |
| Configuracion | copia de `.env.example` y hash de `.env` real sin exponerlo | En cada cambio |
| Datos procesados | copia de `data/processed/` | Antes de entrega |

Procedimiento operativo:

```bash
bash backups/backup.sh
bash backups/restore.sh backups/<fecha>
```

Pendiente recomendado:

- ejecutar un backup real en el entorno final;
- restaurarlo en una base temporal;
- guardar conteos antes/despues como evidencia.

## Gobernanza y etica del dato

El proyecto usa datos abiertos y no personales. Aun asi, hay consideraciones importantes:

- FIRMS detecta focos termicos, no necesariamente incendios confirmados en tierra.
- La cobertura satelital puede verse afectada por nubosidad, latencia y resolucion.
- Los indicadores de calidad de aire son aproximaciones por modelo/reanalisis, no siempre
  mediciones de estaciones oficiales.
- El sistema debe apoyar decisiones tecnicas, no reemplazar protocolos oficiales de
  emergencia.
- Uruguay se trata como pais nucleo del analisis; Brasil y Argentina se incorporan por
  influencia regional y transfronteriza.

## Conclusion de seguridad

La base de seguridad esta implementada para un prototipo academico: roles, privilegio
minimo, vistas, configuracion externa y scripts de backup. Para produccion real falta
rotacion de secretos, autenticacion Mongo robusta, TLS, auditoria de accesos y prueba
formal de restore.
