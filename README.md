# SINIA-UY — Sistema de Monitoreo de Incendios Forestales

**UTEC | Ingeniería de Datos e Inteligencia Artificial | Proyecto de Ingeniería de Datos | 2026**

Sistema de monitoreo ambiental que integra fuentes de datos satelitales y meteorológicas para detectar, analizar y predecir riesgo de incendios forestales en Uruguay, Brasil y Argentina.

---

## Arquitectura

```
APIs externas
  ├── NASA FIRMS (focos de calor)
  ├── Open-Meteo (meteorología histórica + forecast)
  └── CAMS via Open-Meteo (calidad del aire PM10/PM2.5)
        │
        ▼
   ETL Python (extract → transform → load)
        │
        ├──→ PostgreSQL (Data Warehouse analítico)
        │       ├── focos_calor
        │       ├── meteo_diario (+ índice de riesgo)
        │       ├── calidad_aire_diario
        │       └── etl_ejecuciones (auditoría CDC)
        │
        └──→ MongoDB (base operacional flexible)
                ├── focos_snapshots (documentos por día)
                ├── alertas (eventos de riesgo)
                └── ejecuciones_etl (trazabilidad)
                        │
                        ▼
              Dashboard Streamlit
```

---

## Levantamiento rápido (Docker)

### 1. Clonar y configurar

```bash
git clone <repo>
cd SONIA-UY

# Copiar y editar variables de entorno
cp docker/.env.example config/.env
# Editar config/.env con tu FIRMS_MAP_KEY y contraseñas deseadas
```

### 2. Levantar la infraestructura

```bash
cd docker
docker compose up -d postgres mongo
# Esperar que pasen los healthchecks (~20 segundos)
docker compose ps
```

### 3. Cargar datos iniciales

```bash
# Instalar dependencias Python
pip install -r requirements.txt

# Extraer y transformar datos (genera los parquets)
python etl/extract/extract_firms.py
python etl/extract/extract_meteo.py
python etl/extract/extract_cams.py

# Cargar en PostgreSQL
python etl/load/load_postgres.py

# Cargar en MongoDB
python etl/load/load_mongo.py
```

### 4. Levantar el dashboard

```bash
# Opción A: local
streamlit run dashboard/app.py

# Opción B: Docker
docker compose up -d streamlit
# Acceder en http://localhost:8501
```

### 5. Automatización (scheduler)

```bash
# Mantiene datos actualizados automáticamente
python etl/scheduler.py
```

---

## Levantar todo con Docker Compose

```bash
cd docker
docker compose up -d
```

Servicios:
| Servicio    | Puerto | Descripción                   |
|-------------|--------|-------------------------------|
| PostgreSQL  | 5432   | Base de datos relacional      |
| MongoDB     | 27017  | Base de datos documental      |
| Streamlit   | 8501   | Dashboard analítico           |

---

## Tests de calidad de datos

```bash
# Ejecutar todos los tests (requiere parquets en data/processed/)
python tests/test_calidad_datos.py

# O con pytest (más detallado)
pytest tests/test_calidad_datos.py -v

# Ver resultados
cat tests/resultados_tests.json
```

Categorías de tests:
- **Completitud**: campos críticos sin nulos
- **Unicidad**: sin duplicados por clave natural
- **Consistencia**: coordenadas, rangos, relaciones
- **Validez**: dominios permitidos (nivel_riesgo, confianza, etc.)
- **Idempotencia**: doble carga = mismo resultado
- **CDC**: detección de nuevos registros y modificaciones

---

## Entrega EC3

La evidencia de la etapa 3 esta consolidada en
[`docs/ENTREGA_EC3_IMPLEMENTACION.md`](docs/ENTREGA_EC3_IMPLEMENTACION.md):
modelo SQL, modelo NoSQL, ETL, CDC, testing, seguridad, dashboard, despliegue
hibrido, Docker y rendimiento preliminar.

---

## Backup y recuperación

```bash
# Crear backup (PostgreSQL + MongoDB + config)
bash backups/backup.sh

# Restaurar desde backup
bash backups/restore.sh backups/2026-03-12_220000
```

---

## Estructura del proyecto

```
SONIA-UY/
├── config/
│   ├── .env                  # Variables de entorno (NO commitear)
│   └── settings.py           # Configuración central
├── etl/
│   ├── extract/              # Extractores por fuente
│   ├── transform/            # Transformaciones y cálculo de índice de riesgo
│   ├── load/
│   │   ├── load_postgres.py  # Carga idempotente hacia PostgreSQL
│   │   └── load_mongo.py     # Carga hacia MongoDB
│   ├── utils/
│   │   └── logger.py         # Logger estructurado JSON
│   └── scheduler.py          # Scheduler de actualización automática
├── sql/
│   ├── ddl/
│   │   ├── 01_roles.sql      # Roles y permisos
│   │   ├── 02_schema.sql     # DDL completo
│   │   ├── 03_indices.sql    # Índices analíticos
│   │   └── 04_vistas.sql     # Vistas de seguridad y analítica
│   ├── dml/
│   │   └── 01_seed_puntos.sql
│   └── queries/
│       └── 01_analiticas.sql # 10 consultas analíticas
├── nosql/
│   ├── schemas/              # JSON Schema de colecciones
│   ├── queries/              # Consultas MongoDB representativas
│   └── init/                 # Script de inicialización
├── dashboard/
│   └── app.py                # Dashboard Streamlit
├── tests/
│   └── test_calidad_datos.py # Tests de calidad, idempotencia y CDC
├── backups/
│   ├── backup.sh             # Script de backup
│   └── restore.sh            # Script de restauración
├── docker/
│   ├── docker-compose.yml
│   ├── Dockerfile.streamlit
│   └── .env.example
├── data/
│   ├── raw/                  # Datos crudos descargados
│   └── processed/            # Datos transformados (Parquet)
├── logs/                     # Logs estructurados JSON
└── requirements.txt
```

---

## Fuentes de datos

| Fuente | Tipo | Acceso | Granularidad |
|--------|------|--------|--------------|
| NASA FIRMS VIIRS NRT | API REST | Clave gratuita | Por foco, ~3h latencia |
| NASA FIRMS VIIRS SP | API REST | Clave gratuita | Histórico, diario |
| Open-Meteo Forecast | API REST | Sin clave | Diario, 7 días |
| Open-Meteo Archive | API REST | Sin clave | Histórico diario |
| CAMS via Open-Meteo | API REST | Sin clave | Horario → diario |

---

## Índice de riesgo de incendio

Suma ponderada de 4 componentes (valores [0,1]):

```
Índice = Temperatura×0.25 + Humedad×0.30 + Viento×0.20 + Sequía×0.25
```

| Rango | Nivel |
|-------|-------|
| 0.00–0.25 | Bajo |
| 0.25–0.50 | Moderado |
| 0.50–0.75 | Alto |
| 0.75–1.00 | Muy Alto |

---

## Justificación técnica de decisiones

**¿Por qué PostgreSQL como Data Warehouse?**
Los datos de incendios, meteorología y calidad del aire tienen esquema estable, requieren
consultas analíticas con agregaciones temporales y JOINs frecuentes. PostgreSQL es ideal
como motor OLAP liviano para estos volúmenes (~100K registros/año).

**¿Por qué MongoDB?**
Los logs ETL, alertas y snapshots diarios tienen estructura variable o semi-estructurada.
Los snapshots de focos benefician del modelo de documento embebido: una sola consulta
devuelve todos los focos de un día sin JOINs. El caso de uso justifica complementariedad,
no redundancia.

**¿Por qué no sharding real?**
El volumen de datos actual (~365 registros/año por tabla principal) no justifica sharding.
Se documenta la estrategia de sharding hipotética: `fecha` como shard key en `focos_calor`
(alta cardinalidad, consultas por rango temporal) si el volumen escala a millones de registros.
