# 13 â€” Deploy al servidor UTEC

> **AtenciÃ³n**: esta guÃ­a asume un servidor Linux (Ubuntu Server 22.04 LTS o similar) con acceso SSH. Si el servidor de UTEC es algo distinto (un servicio gestionado tipo VPS administrado, una VM con Windows Server, o un servicio PaaS), ajustÃ¡ la secciÃ³n 1 segÃºn corresponda. La lÃ³gica de fondo es la misma: instalar Postgres y Mongo, clonar el repo, configurar el `.env`, levantar el ETL y exponer el dashboard.

## Datos del servidor que necesitÃ¡s antes de empezar

Pedile al docente o al Ã¡rea de infraestructura:

| Dato | Ejemplo | CÃ³mo se usa |
|------|---------|-------------|
| IP o hostname | `servidor.utec.edu.uy` o `192.168.x.x` | Para SSH |
| Usuario SSH | `rquintana` | `ssh usuario@host` |
| Forma de autenticaciÃ³n | clave pÃºblica o contraseÃ±a | Para conectarte |
| Sistema operativo | Ubuntu 22.04 | Determina los comandos de instalaciÃ³n |
| Permisos sudo | sÃ­/no | Para instalar paquetes |
| Puertos abiertos | 5432? 27017? 8501? 22? 443? | Define si el dashboard se ve desde fuera |
| Â¿Docker disponible? | sÃ­/no | Define si usamos contenedores o instalaciÃ³n nativa |
| Â¿Hay dominio asignado? | `sinia.utec.edu.uy` | Para configurar nginx/reverse proxy |
| Espacio en disco | 20 GB+ recomendado | Postgres + Mongo + logs crecen |
| RAM | 4 GB+ recomendado | Postgres + Mongo + Streamlit + scheduler |

**Anotalos en un archivo local `servidor_utec.md` (NO commitearlo) o en tu gestor de contraseÃ±as.**

## Escenario A â€” Servidor con Docker disponible (recomendado)

Es el camino mÃ¡s limpio: replicÃ¡s casi exacto el setup local.

### A.1 Conectarse al servidor

```powershell
# Desde tu PC, en PowerShell
ssh tu_usuario@servidor.utec.edu.uy
```

Si te pide contraseÃ±a, ingresala. Si configuraste clave SSH, entra directo.

### A.2 Verificar Docker

```bash
docker --version
docker compose version
```

Si no estÃ¡n instalados, pedile al admin del servidor que los instale (en Ubuntu: `sudo apt install docker.io docker-compose-v2 && sudo usermod -aG docker $USER`). CerrÃ¡ y volvÃ© a abrir la sesiÃ³n SSH para que el grupo `docker` tome efecto.

### A.3 Clonar el repo

```bash
cd /opt                                           # o /home/tu_usuario/apps
sudo git clone https://github.com/<usuario>/sinia-uy.git
sudo chown -R $USER:$USER sinia-uy
cd sinia-uy
git checkout main                                 # asegurarte de estar en main
```

Si el repo es privado, configurÃ¡ una clave SSH del servidor en GitHub (Settings â†’ SSH Keys) y clonÃ¡ con `git@github.com:...`. O usÃ¡ un Personal Access Token de solo lectura.

### A.4 Configurar el `.env` del servidor

**No copies el `.env` de tu PC.** En el servidor las contraseÃ±as deben ser distintas y mÃ¡s fuertes:

```bash
cp docker/.env.example docker/.env
nano docker/.env
```

GenerÃ¡ contraseÃ±as largas con `openssl rand -base64 32` y pegalas en `docker/.env`:

```env
PG_SUPERUSER=postgres
PG_SUPERPASS=<contraseÃ±a_fuerte_postgres_super>
PG_DATABASE=sinia_uy
PG_USER=sinia_etl_user
PG_PASSWORD=<contraseÃ±a_fuerte_etl>
PG_PORT=5432

MONGO_ROOT_USER=mongo_admin
MONGO_ROOT_PASS=<contraseÃ±a_fuerte_mongo_root>
MONGO_DATABASE=sinia_uy
MONGO_USER=sinia_etl_user
MONGO_PASSWORD=<contraseÃ±a_fuerte_mongo_etl>
MONGO_PORT=27017

FIRMS_MAP_KEY=<tu_api_key_firms>
LOG_LEVEL=INFO
TIMEZONE=America/Montevideo
```

Y tambiÃ©n `config/.env` para el ETL Python:

```bash
cp docker/.env config/.env
nano config/.env
```

CambiÃ¡ los hosts a los nombres del contenedor (lo verÃ¡s en `docker-compose.yml`):

```env
PG_HOST=localhost           # el ETL python corre fuera de los containers
PG_PORT=5432
MONGO_HOST=localhost
MONGO_PORT=27017
# ... resto idÃ©ntico a docker/.env
```

### A.5 Levantar Postgres y Mongo

```bash
cd docker
docker compose up -d postgres mongo
docker compose ps
```

EsperÃ¡ los healthchecks. VerificÃ¡:

```bash
docker compose logs postgres | tail -50
docker compose logs mongo | tail -50
```

### A.6 Instalar Python y dependencias (para el ETL fuera del contenedor)

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip
cd /opt/sinia-uy
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### A.7 Primera carga de datos

```bash
source .venv/bin/activate

# Extraer
python etl/extract/extract_firms.py
python etl/extract/extract_meteo.py
python etl/extract/extract_cams.py
python etl/extract/extract_forecast.py

# Transformar
python etl/transform/transform_firms.py
python etl/transform/transform_meteo.py
python etl/transform/transform_cams.py

# Cargar
python etl/load/load_postgres.py
python etl/load/load_mongo.py

# Validar
python tests/test_calidad_datos.py
cat tests/resultados_tests.json | python -m json.tool | grep '"estado"'
```

Si los 17 tests dan PASS, el deploy estÃ¡ sano.

### A.8 Levantar el dashboard

```bash
docker compose up -d streamlit
docker compose ps
```

Si el puerto 8501 estÃ¡ abierto, accedÃ©s desde tu PC con `http://<ip-servidor>:8501`. Si **no** estÃ¡ abierto (lo normal en servidores universitarios), pasÃ¡ al paso A.9.

### A.9 Reverse proxy con nginx (acceso vÃ­a HTTPS)

Si UTEC te asignÃ³ un dominio (ej. `sinia.utec.edu.uy`), exponÃ© el dashboard vÃ­a nginx + Let's Encrypt:

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
sudo nano /etc/nginx/sites-available/sinia
```

PegÃ¡:

```nginx
server {
    listen 80;
    server_name sinia.utec.edu.uy;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 86400;
    }
}
```

Activar y certificar:

```bash
sudo ln -s /etc/nginx/sites-available/sinia /etc/nginx/sites-enabled/
sudo nginx -t                                 # validar config
sudo systemctl reload nginx
sudo certbot --nginx -d sinia.utec.edu.uy     # certificado HTTPS gratis
```

Si no hay dominio, usÃ¡ un tÃºnel SSH desde tu PC:

```powershell
ssh -L 8501:localhost:8501 tu_usuario@servidor.utec.edu.uy
```

Y abrÃ­ `http://localhost:8501` en tu navegador local.

### A.10 Scheduler como servicio systemd

Para que el ETL corra automÃ¡ticamente y sobreviva reinicios:

```bash
sudo nano /etc/systemd/system/sinia-scheduler.service
```

PegÃ¡:

```ini
[Unit]
Description=SINIA-UY ETL Scheduler
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=tu_usuario
WorkingDirectory=/opt/sinia-uy
Environment="PATH=/opt/sinia-uy/.venv/bin:/usr/bin"
ExecStart=/opt/sinia-uy/.venv/bin/python /opt/sinia-uy/etl/scheduler.py
Restart=on-failure
RestartSec=30
StandardOutput=append:/opt/sinia-uy/logs/scheduler.log
StandardError=append:/opt/sinia-uy/logs/scheduler.error.log

[Install]
WantedBy=multi-user.target
```

Activar:

```bash
sudo systemctl daemon-reload
sudo systemctl enable sinia-scheduler
sudo systemctl start sinia-scheduler
sudo systemctl status sinia-scheduler
```

Ver logs en vivo:

```bash
journalctl -u sinia-scheduler -f
```

### A.11 Backups automÃ¡ticos vÃ­a cron

```bash
crontab -e
```

AgregÃ¡:

```cron
# Backup diario 04:00 UTC (01:00 Uruguay)
0 4 * * * cd /opt/sinia-uy && bash backups/backup.sh >> /opt/sinia-uy/logs/backup.log 2>&1
```

VerificÃ¡ que `backups/backup.sh` tiene permisos:

```bash
chmod +x backups/backup.sh
chmod +x backups/restore.sh
```

### A.12 Firewall (UFW)

```bash
sudo ufw allow 22/tcp       # SSH
sudo ufw allow 80/tcp       # HTTP (para certbot)
sudo ufw allow 443/tcp      # HTTPS
# NO abrir 5432 ni 27017 al exterior â€” solo localhost
sudo ufw enable
sudo ufw status
```

## Escenario B â€” Servidor sin Docker (instalaciÃ³n nativa)

Si UTEC no permite Docker, instalÃ¡ Postgres y Mongo directamente.

### B.1 Instalar PostgreSQL 16

```bash
sudo apt install -y postgresql-16 postgresql-contrib
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

Setear contraseÃ±a del superuser:

```bash
sudo -u postgres psql
\password postgres            # ingresÃ¡ la contraseÃ±a
\q
```

Crear la BD y ejecutar los scripts del proyecto:

```bash
sudo -u postgres createdb sinia_uy
sudo -u postgres psql -d sinia_uy -f /opt/sinia-uy/sql/ddl/01_roles.sql
sudo -u postgres psql -d sinia_uy -f /opt/sinia-uy/sql/ddl/02_schema.sql
sudo -u postgres psql -d sinia_uy -f /opt/sinia-uy/sql/ddl/03_indices.sql
sudo -u postgres psql -d sinia_uy -f /opt/sinia-uy/sql/ddl/04_vistas.sql
sudo -u postgres psql -d sinia_uy -f /opt/sinia-uy/sql/dml/01_seed_puntos.sql
```

VerificÃ¡:

```bash
sudo -u postgres psql -d sinia_uy -c "SELECT COUNT(*) FROM puntos_monitoreo;"   # deberÃ­a decir 19
```

### B.2 Instalar MongoDB 7

```bash
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update
sudo apt install -y mongodb-org
sudo systemctl enable mongod
sudo systemctl start mongod
```

Habilitar autenticaciÃ³n: editar `/etc/mongod.conf`, agregar `security: { authorization: enabled }`, reiniciar:

```bash
sudo systemctl restart mongod
mongosh
```

Crear usuarios (ver `nosql/init/01_setup_mongo.js` y replicar el script en `mongosh`).

### B.3 Resto idÃ©ntico al Escenario A

Pasos A.3 (clonar repo), A.4 (.env), A.6 (Python), A.7 (cargar datos), A.10 (systemd para scheduler), A.11 (backups), A.12 (firewall) se aplican igual.

## Workflow de despliegue continuo

Una vez todo levantado, el ciclo es:

```
[Tu PC]                                [GitHub]                    [Servidor UTEC]
  â†“
  trabajÃ¡s en feature/...
  â†“
  git commit -m "..."
  git push origin dev   â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â†’   dev actualizado
  â†“
  PR dev â†’ main                            â†“
  git tag v1.x.x
  git push origin main  â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â†’   main actualizado  â”€â”€â”€â”€â†’   ssh + git pull
                                                                    docker compose restart
                                                                    o systemctl restart sinia-scheduler
```

### Script de deploy en el servidor

CreÃ¡ `scripts/deploy.sh` en el repo:

```bash
#!/bin/bash
# Script de actualizaciÃ³n en servidor UTEC.
# Uso: bash scripts/deploy.sh
set -e
cd /opt/sinia-uy

echo "==> Pull desde origin/main"
git fetch origin
git checkout main
git pull origin main

echo "==> Activando venv y actualizando dependencias"
source .venv/bin/activate
pip install -r requirements.txt --quiet

echo "==> Reiniciando contenedores"
cd docker
docker compose up -d --build

echo "==> Reiniciando scheduler"
sudo systemctl restart sinia-scheduler

echo "==> Validando tests de calidad"
cd ..
python tests/test_calidad_datos.py

echo "==> Deploy completo"
```

Permisos:

```bash
chmod +x scripts/deploy.sh
```

PrÃ³ximo deploy desde el servidor:

```bash
cd /opt/sinia-uy
bash scripts/deploy.sh
```

## Restaurar desde backup en el servidor

```bash
ls -lh backups/                       # listar backups disponibles
bash backups/restore.sh backups/2026-05-11_040000
```

## Monitoreo bÃ¡sico

```bash
# Estado general
docker compose ps
sudo systemctl status sinia-scheduler

# Logs del scheduler
tail -f logs/scheduler.log

# Ãšltima ejecuciÃ³n ETL
docker exec sinia_postgres psql -U postgres -d sinia_uy -c \
  "SELECT fuente, etapa, estado, finalizado_en FROM etl_ejecuciones ORDER BY finalizado_en DESC LIMIT 10;"

# Uso de disco
df -h /opt/sinia-uy
du -sh /opt/sinia-uy/data /opt/sinia-uy/logs /opt/sinia-uy/backups
```

## Checklist final de deploy

- [ ] ConexiÃ³n SSH al servidor funciona.
- [ ] Repo clonado en `/opt/sinia-uy` (o ubicaciÃ³n equivalente).
- [ ] `docker/.env` y `config/.env` con contraseÃ±as distintas a las locales.
- [ ] Postgres y Mongo levantados y `healthy`.
- [ ] Schemas creados (tablas y colecciones visibles).
- [ ] ETL corriÃ³ la primera vez sin errores.
- [ ] 20/20 tests PASS.
- [ ] Dashboard accesible (vÃ­a dominio + nginx, o tÃºnel SSH).
- [ ] Scheduler corre como servicio systemd.
- [ ] Backup automÃ¡tico configurado en cron.
- [ ] Firewall configurado (solo 22, 80, 443 abiertos al exterior).
- [ ] Script `scripts/deploy.sh` probado.

---

**PrÃ³ximo paso:** [14_PLAN_DOCUMENTACION_PARALELA.md](14_PLAN_DOCUMENTACION_PARALELA.md) â€” escribir la doc de desarrollo mientras hacÃ©s esto.
