# 12 — Workflow con Git

Objetivo: dejar el proyecto versionado, hospedado en GitHub (o GitLab) y con un flujo de trabajo claro **local → commit → push → pull en servidor**.

## 1. Inicializar el repo (una sola vez)

Abrí PowerShell en la raíz del proyecto:

```powershell
cd "C:\Users\rqf18\OneDrive\Documentos\api\Custom Office Templates\EjercicioSQL\Escritorio\PROYECTO INGIENERIA DE DATOS\SONIA-UY"
git init
```

**Antes de hacer el primer commit, verificá qué se va a subir:**

```powershell
git status
```

El `.gitignore` actual ya excluye correctamente:
- `__pycache__/`, `.venv/`, `venv/`
- `.env` y todo `.env.*` (excepto `.env.example`)
- `data/raw/`, `data/processed/`, `backups/`
- `logs/`, `*.log`
- `.vscode/`, `.idea/` y configuraciones locales de herramientas

**Verificación crítica antes de commitear**:

```powershell
git status | findstr ".env"
```

Si aparece `docker/.env` o `config/.env` en la salida, **PARÁ** — ese archivo tiene contraseñas. Verificá el `.gitignore`. Solo `.env.example` debería poder commitearse.

## 2. Configurar tu identidad (una sola vez por máquina)

```powershell
git config --global user.name "Rafael <tu apellido>"
git config --global user.email "rqf180293@gmail.com"
```

(O usá tu mail institucional de UTEC si lo preferís para este proyecto académico.)

## 3. Primer commit

```powershell
git add .
git status                # revisar lo que vas a commitear
git commit -m "Commit inicial: SINIA-UY v1.0 — ETL + Postgres + Mongo + Dashboard + Tests"
```

## 4. Crear el repo remoto en GitHub

1. Andá a https://github.com/new
2. Repository name: `sinia-uy` (o el nombre que prefieras)
3. Description: "Sistema de monitoreo de incendios forestales — UTEC Ingeniería de Datos 2026"
4. **Private** (recomendado para proyecto académico con API keys históricas)
5. **NO** marques "Initialize with README" ni `.gitignore` ni licencia — ya tenés todo eso local.
6. Create repository.

GitHub te da dos comandos. Usá el segundo bloque ("…or push an existing repository"):

```powershell
git remote add origin https://github.com/<tu-usuario>/sinia-uy.git
git branch -M main
git push -u origin main
```

La primera vez te va a pedir autenticación. Las opciones:
- **GitHub Desktop** instalado y logueado → automático.
- **Token personal**: GitHub → Settings → Developer Settings → Personal Access Tokens → Generate. Lo pegás como contraseña.
- **SSH** (mi recomendación a mediano plazo): genera una clave con `ssh-keygen -t ed25519 -C "rqf180293@gmail.com"`, agregá la pública a GitHub → Settings → SSH Keys, y cambiá la URL del remote a `git@github.com:<usuario>/sinia-uy.git`.

## 5. Estructura de ramas recomendada

Para un proyecto académico con 1–3 personas, alcanza con:

```
main          ← rama estable, lo que está en el servidor UTEC
  └── dev     ← rama de integración diaria
       └── feature/<descripcion>   ← cada cambio nuevo
       └── fix/<descripcion>        ← cada bug que arregles
```

Crear `dev` la primera vez:

```powershell
git checkout -b dev
git push -u origin dev
```

## 6. Flujo de trabajo diario

### 6.1 Empezar a trabajar en algo nuevo

```powershell
git checkout dev
git pull origin dev                   # traer cambios recientes (de tu otra PC o compañero)
git checkout -b feature/optimizar-extract-firms
# ... editás archivos ...
```

### 6.2 Mientras trabajás

```powershell
git status                            # ¿qué cambié?
git diff                              # ver los cambios línea por línea
git add etl/extract/extract_firms.py  # agregar archivos específicos
# o
git add .                             # agregar todo lo modificado
git commit -m "Optimizar timeout en extract_firms cuando la API tarda"
```

**Convención de mensajes de commit** (te ahorra dolor de cabeza en 2 meses):

```
<tipo>: <descripción corta en presente>

Tipos:
  feat:     nueva funcionalidad
  fix:      arreglo de bug
  docs:     cambios en documentación
  refactor: cambio de código sin alterar comportamiento
  test:     agregar o corregir tests
  chore:    tareas operativas (deps, config, build)
  data:     cambios en seeds o datos versionados

Ejemplos:
  feat: agregar export CSV al dashboard
  fix: corregir bbox de Uruguay en transform_firms
  docs: documentar deploy a servidor UTEC
  test: agregar test de unicidad en calidad_aire_diario
```

### 6.3 Subir tus cambios

```powershell
git push origin feature/optimizar-extract-firms
```

### 6.4 Integrar a `dev`

En GitHub: abrí un **Pull Request** de `feature/optimizar-extract-firms` → `dev`. Aunque trabajes solo, el PR sirve para revisar el diff completo antes de mergear.

O por terminal (si trabajás solo y querés simpleza):

```powershell
git checkout dev
git merge feature/optimizar-extract-firms
git push origin dev
git branch -d feature/optimizar-extract-firms      # borrar rama local
git push origin --delete feature/optimizar-extract-firms   # borrar rama remota
```

### 6.5 Pasar `dev` a `main` (release / deploy a servidor)

Cuando `dev` está testeado y funciona end-to-end, lo pasás a `main`. **`main` es lo que corre en el servidor UTEC.**

```powershell
git checkout main
git merge dev
git tag -a v1.1.0 -m "Release v1.1.0 — dashboard con export CSV"
git push origin main --tags
```

Después en el servidor UTEC hacés `git pull origin main` (ver doc 13).

## 7. Cosas que NUNCA hagas

| Acción | Por qué no |
|--------|------------|
| Commitear `.env` o `config/.env` con contraseñas | Quedan en historial para siempre. Aunque borres el archivo, `git log` lo guarda. |
| `git push --force` en `main` | Reescribe historia y rompe a tus colaboradores. Solo permitido en ramas tuyas que nadie usa. |
| Commitear `data/raw/` o `data/processed/` | Son archivos generados, grandes y vuelven el repo lento. Ya están en `.gitignore`. |
| Commitear `__pycache__/` o `.venv/` | Lo mismo. |
| Mergear `feature/*` directo a `main` | Pasá por `dev` primero. `main` debe estar siempre listo para deploy. |

## 8. ¿Y si commiteás un secreto por accidente?

Pasa. Pasos:

1. **Asumí que el secreto está comprometido.** Rotalo en el servicio de origen (regenerá la `FIRMS_MAP_KEY`, cambiá las contraseñas de Postgres y Mongo).
2. **Borralo del último commit si todavía no pushaste:**
   ```powershell
   git reset HEAD~1
   # editá el archivo, sacá el secreto
   git add .
   git commit -m "..."
   ```
3. **Si ya pushaste:** además del cambio anterior, hay que reescribir historia con `git filter-repo` y forzar push. Hay tutoriales específicos, pero lo más rápido es que el secreto ya esté revocado y dejarlo correr.

## 9. Archivos importantes para el repo

Antes del primer commit, completá estos archivos en la raíz:

### README.md
Ya existe y está completo. Considerá agregar al inicio:

```markdown
[![Tests](https://img.shields.io/badge/tests-17%2F17%20passing-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.11+-blue)]()
[![License](https://img.shields.io/badge/license-Academic-orange)]()
```

(Los badges no son obligatorios pero quedan bien para presentar.)

### LICENSE (opcional)
Si es académico y no querés que terceros lo usen comercialmente, agregá un archivo `LICENSE` con texto tipo:

```
Copyright (c) 2026 Rafael Quintana / UTEC Ingeniería de Datos
Uso académico únicamente. No se permite uso comercial sin autorización.
```

### CHANGELOG.md
Te recomiendo armar uno desde el primer release:

```markdown
# Changelog

## [v1.0.0] — 2026-05-11
### Agregado
- Pipeline ETL completo (FIRMS, Open-Meteo, CAMS, CHIRPS, MODIS)
- Schema Postgres con 8 tablas + roles + vistas
- Schema MongoDB con 3 colecciones + validators
- Dashboard Streamlit con mapa y alertas
- 17 tests de calidad (idempotencia + CDC)
- Backups con pg_dump y mongodump
- Docker Compose para Postgres + Mongo + Streamlit

## [Unreleased]
- (pendiente)
```

## 10. Trabajar en paralelo desde dos máquinas

Si vas a alternar entre tu PC personal y la de UTEC:

```powershell
# En la PC nueva, clonar el repo
git clone https://github.com/<tu-usuario>/sinia-uy.git
cd sinia-uy

# Copiar tu .env (NO está en git — pasalo por USB o mensajería segura)
copy <ruta_a_tu_env> docker\.env
copy <ruta_a_tu_env_config> config\.env

# Setup como en doc 11
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cd docker
docker compose up -d postgres mongo
```

Después de cada sesión:

```powershell
git pull origin dev    # antes de empezar a trabajar
# ... trabajás ...
git add . && git commit -m "..." && git push origin dev
```

## 11. Checklist de "primer push exitoso"

- [ ] `git init` ejecutado.
- [ ] `git config` con nombre y email.
- [ ] `git status` no muestra ningún `.env` ni `data/raw/` ni `__pycache__/`.
- [ ] Primer commit hecho.
- [ ] Repo creado en GitHub (privado).
- [ ] Remote agregado con `git remote add origin`.
- [ ] Push de `main` exitoso.
- [ ] Rama `dev` creada y pusheada.
- [ ] Verificaste en GitHub que el repo NO tiene `.env` ni `data/`.

---

**Próximo paso:** [13_DEPLOY_SERVIDOR_UTEC.md](13_DEPLOY_SERVIDOR_UTEC.md) — subir todo al servidor.
