# 16. Deploy del dashboard a Streamlit Community Cloud

Esta guia documenta como publicar el dashboard del proyecto SINIA-UY en
Streamlit Community Cloud (gratis), de modo que tenga una URL publica
accesible desde cualquier navegador â€” util para la defensa y para mostrar
el sistema sin depender de tu maquina local ni de la red interna de UTEC.

## 1. Por que Streamlit Cloud y no la BD UTEC directamente

La base de datos asignada por UTEC esta en `10.200.245.40`, una IP de
red privada (rango RFC1918 `10.0.0.0/8`). Solo es accesible desde dentro
de la red institucional. Streamlit Cloud corre en AWS y no tiene ruta a
esa red, por lo que **el dashboard hosteado no puede conectarse
directamente a Postgres/Mongo UTEC**.

Solucion adoptada: el dashboard ya tiene fallback a archivos Parquet
(`dashboard/db.py`). Versionamos los parquets en el repositorio y
Streamlit Cloud levanta el dashboard leyendo de esos archivos. La
demostracion contra la BD UTEC se hace localmente.

## 2. Que se versiona en el repo

`.gitignore` excluye `data/raw/` y subcarpetas de staging/backups dentro
de `data/processed/`, pero **incluye** los siguientes parquets, leidos
por el dashboard:

| Archivo | Tamano aprox. | Para que sirve |
|---|---|---|
| `data/processed/firms_procesado.parquet` | ~41 MB | Historico de focos de calor (2018-2026) |
| `data/processed/firms_nrt_procesado.parquet` | ~175 KB | Focos NRT (ultimas 24h) |
| `data/processed/meteo_procesado_todos.parquet` | ~437 KB | Meteo + indice de riesgo |
| `data/processed/cams_procesado_todos.parquet` | ~200 KB | Calidad del aire historica |
| `data/processed/cams_nrt_procesado.parquet` | ~36 KB | Calidad del aire NRT |
| `data/processed/forecast_riesgo.parquet` | ~20 KB | Pronostico 7 dias |
| `data/processed/chirps_sa.parquet` | ~24 KB | Precipitacion mensual |
| `data/processed/modis_lc.parquet` | ~8 KB | Cobertura vegetal |

Total: ~42 MB. Dentro del limite de GitHub (warning a partir de 50 MB
por archivo, hard limit 100 MB).

## 3. Paso a paso del deploy

### 3.1. Verificar que el repo este listo

Desde tu maquina, en la raiz del proyecto:

```bash
git status                              # No deberia haber cambios pendientes
git log --oneline -5                    # Confirmar ultimos commits
git ls-files data/processed/            # Confirmar que los parquets estan trackeados
```

Si los parquets no aparecen, los agregas:

```bash
git add data/processed/*.parquet
git commit -m "Versionar parquets para deploy a Streamlit Cloud"
git push origin main                     # o la rama que uses
```

### 3.2. Cuenta de Streamlit Cloud

1. Entrar a https://streamlit.io/cloud
2. Iniciar sesion con la cuenta de GitHub de Rafael (`RafaelQuintanilla`).
3. Autorizar a Streamlit a acceder al repositorio `Proyecto-LIDIA`.

### 3.3. Crear la app

1. Click "New app".
2. Configurar:
   - **Repository**: `RafaelQuintanilla/Proyecto-LIDIA`
   - **Branch**: `main` (o la que tenga los cambios)
   - **Main file path**: `dashboard/app.py`
   - **Python version**: 3.11 (recomendado para coincidir con el proyecto)
   - **App URL**: elegir un slug, ej. `sinia-uy` -> URL final `https://sinia-uy.streamlit.app`
3. Click "Deploy".
4. El primer build tarda 3-5 minutos. Streamlit instala las dependencias
   de `requirements.txt`, copia los parquets versionados y levanta la app.

### 3.4. Variables de entorno (opcional)

Si en algun momento quisieras que Streamlit Cloud se conecte a una BD
cloud (Supabase, Neon, MongoDB Atlas), las credenciales se configuran
en la app -> Settings -> Secrets, formato TOML:

```toml
PG_HOST = "host.de.la.bd.cloud"
PG_PORT = 5432
PG_DATABASE = "sinia_uy"
PG_USER = "..."
PG_PASSWORD = "..."
```

Por ahora dejamos esta seccion vacia: el dashboard caera al fallback
parquet automaticamente (timeout de 3 segundos en `_pg_disponible()`).

## 4. Verificacion post-deploy

Una vez levantado, verificar manualmente en `https://sinia-uy.streamlit.app`:

- Pagina principal carga con KPIs llenos (focos, riesgo, alertas).
- Panel de mapa muestra puntos.
- Filtros por pais (ARG/BRA/URY/CHL) funcionan.
- Panel NRT muestra focos de las ultimas 24h (los del ultimo
  `firms_nrt_procesado.parquet` commiteado).
- Pestana "Riesgo por pais" tiene barras llenas (replica de
  `v_riesgo_por_pais`).
- Pestana "Dias criticos" tiene tabla (replica de `v_dias_criticos`).
- Sidebar dice "Fuente: parquet" (no postgresql) â€” confirmando el
  fallback funciona.

## 5. Actualizar los datos

Para refrescar los datos del dashboard cloud:

1. Correr el ETL local (que actualiza `data/processed/*.parquet`).
2. `git add data/processed/*.parquet`
3. `git commit -m "Refrescar parquets â€” YYYY-MM-DD"`
4. `git push`
5. Streamlit Cloud detecta el push y redeploya automaticamente en 1-2 min.

Cadencia recomendada antes de la defensa: refrescar cada dia o cuando
haya datos NRT relevantes (como los 303 focos del 2026-05-15).

## 6. Cumplimiento de consigna hibrida

Con este deploy, la arquitectura cumple **explicitamente** la consigna
de despliegue hibrido:

| Componente | Ubicacion | Tipo |
|---|---|---|
| PostgreSQL Data Warehouse | Servidor UTEC (`10.200.245.40`) | On-premise / institucional |
| MongoDB operacional | Servidor UTEC (`10.200.245.40`) | On-premise / institucional |
| Dashboard Streamlit | Streamlit Community Cloud (AWS) | Cloud publico |
| Repositorio | GitHub | Cloud publico |
| ETL Python | Local + on-premise UTEC | Hibrido |

Ver `docs/DESPLIEGUE_HIBRIDO.md` para la justificacion academica
completa.
