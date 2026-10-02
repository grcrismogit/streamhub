# Guía de despliegue en AWS — StreamHub

Orden recomendado: **Security Groups → RDS → S3 → IAM Role → EC2 (API) → S3 Frontend (SPA)**.
Región usada en los ejemplos: `us-east-1` (N. Virginia). Usa la misma región para todo.

> **Convención de nombres.** Los nombres de bucket son únicos a nivel mundial: agrega un sufijo propio, p. ej. `streamhub-frontend-cris2026`. En esta guía se escribe `XXXX`.

> **¿Usas AWS Academy (Learner Lab)?** No puedes crear roles IAM. En el paso 4 usa el perfil existente **`LabInstanceProfile`** (rol `LabRole`), que ya tiene acceso a S3. Además, la IP pública cambia cada vez que se reinicia el laboratorio: usa una **Elastic IP**.

---

## 0. Antes de empezar

1. Sube el proyecto a GitHub/GitLab (repositorio **público**, o configura una *deploy key* para clonarlo desde EC2):
   ```bash
   git init -b main
   git add .
   git status              # revisa que NO aparezca ningún archivo .env, node_modules ni dist
   git commit -m "StreamHub: SPA React + FastAPI + AWS"
   git remote add origin https://github.com/<usuario>/<repo>.git
   git push -u origin main
   ```
2. (Opcional) Instala y configura AWS CLI en tu PC: `aws configure`.

---

## 1. Security Groups (EC2 → Network & Security → Security Groups)

Crea dos grupos en la **VPC por defecto**:

| Nombre | Regla de entrada | Origen | Para qué |
|---|---|---|---|
| `sg-streamhub-api` | HTTP · TCP 80 | `0.0.0.0/0` | Que la SPA y cualquier usuario llamen a la API |
| `sg-streamhub-api` | SSH · TCP 22 | **My IP** | Administrar la instancia (solo desde tu IP) |
| `sg-streamhub-db` | PostgreSQL · TCP 5432 | **`sg-streamhub-api`** (el SG, no una IP) | Solo la API puede hablar con la BD |

Las reglas de salida se dejan por defecto. 📸 *Evidencia: captura de ambos SG con sus reglas.*

---

## 2. Base de datos — Amazon RDS (PostgreSQL)

RDS → **Create database**:

| Opción | Valor |
|---|---|
| Creation method | Standard create |
| Engine | **PostgreSQL** 16.x |
| Templates | **Free tier** (cuentas con plan gratuito) o **Sandbox** (cuentas de pago) |
| DB instance identifier | `streamhub-db` |
| Master username | `streamhub_admin` |
| Credentials management | Self managed → contraseña **fuerte** de solo letras y números (evita `/ @ " '` y espacios) |
| Instance class | `db.t3.micro` / `db.t4g.micro` |
| Storage | gp3, 20 GiB, *sin* autoscaling |
| Connectivity | Don't connect to an EC2 compute resource · VPC por defecto |
| **Public access** | **No** |
| VPC security group | Choose existing → **`sg-streamhub-db`** (quita `default`) |
| Additional configuration → **Initial database name** | **`streamhub`** ⚠️ si lo olvidas, la BD no existe |
| Backup | 1 día de retención · Encryption: activado |

Espera a que el estado sea **Available** (~10 min) y copia el **Endpoint** (`streamhub-db.xxxxx.us-east-1.rds.amazonaws.com`).
📸 *Evidencia: pantalla "Connectivity & security" con endpoint, puerto 5432, "Publicly accessible: No" y el SG.*

---

## 3. Buckets S3

### Opción A — Script (AWS CLI)
```bash
SUFFIX=cris2026 REGION=us-east-1 bash infra/aws/create_buckets.sh
```

### Opción B — Consola

**Bucket 1 · `streamhub-frontend-XXXX` (público, solo la SPA compilada)**
1. Create bucket → desmarca **Block all public access** → confirma la advertencia.
2. Properties → **Static website hosting** → Enable → Index document: `index.html` · Error document: **`index.html`** (necesario para que rutas como `/watch/5` funcionen al recargar).
3. Permissions → **Bucket policy** → pega `infra/aws/s3-frontend-bucket-policy.json` cambiando `XXXX`.
4. Copia el **Bucket website endpoint**: `http://streamhub-frontend-XXXX.s3-website-us-east-1.amazonaws.com`

**Bucket 2 · `streamhub-videos-XXXX` y Bucket 3 · `streamhub-thumbnails-XXXX` (privados)**
1. Create bucket → **deja activado** *Block all public access*.
2. Default encryption: SSE-S3 (viene activado).
3. (Recomendado) Management → Lifecycle rule → *Delete incomplete multipart uploads* después de 1 día.

> Los videos/miniaturas **no** se hacen públicos: la API entrega URLs prefirmadas que expiran en 1 hora.

📸 *Evidencia: lista de los 3 buckets; propiedades de hosting del frontend; "Block public access: On" en videos y miniaturas.*

---

## 4. IAM Role para EC2 (sin access keys)

> En **Learner Lab** salta este paso y usa `LabInstanceProfile`.

1. IAM → Policies → **Create policy** → JSON → pega `infra/aws/iam-ec2-s3-policy.json` (cambia `XXXX`) → nombre `StreamHubS3MediaAccess`.
2. IAM → Roles → **Create role** → Trusted entity: *AWS service* → **EC2** → adjunta `StreamHubS3MediaAccess` → nombre `StreamHubEC2Role`.

Solo permite `PutObject`, `GetObject` y `DeleteObject` sobre los 2 buckets de medios (**mínimo privilegio**). 📸 *Evidencia: el rol con su política.*

---

## 5. API FastAPI en EC2

### 5.1 Lanzar la instancia
EC2 → **Launch instance**:

| Opción | Valor |
|---|---|
| Name | `streamhub-api` |
| AMI | **Amazon Linux 2023** |
| Instance type | `t3.micro` (o `t2.micro`) |
| Key pair | crea/elige uno (`.pem`) |
| Network settings → Security group | **`sg-streamhub-api`** |
| Storage | 16 GiB gp3 |
| Advanced details → **IAM instance profile** | **`StreamHubEC2Role`** (o `LabInstanceProfile`) |

Luego: EC2 → **Elastic IPs** → Allocate → *Associate* con `streamhub-api`. Esa IP es la URL de tu API.

### 5.2 Instalar la API
```bash
ssh -i streamhub-key.pem ec2-user@<IP-ELASTICA>

# Comprobar que la instancia usa el IAM Role (no hay keys configuradas):
aws sts get-caller-identity            # debe mostrar ...assumed-role/StreamHubEC2Role/...

sudo dnf install -y git
git clone https://github.com/<usuario>/<repo>.git /tmp/streamhub
sudo REPO_URL=https://github.com/<usuario>/<repo>.git bash /tmp/streamhub/backend/deploy/setup_ec2.sh
```

La primera ejecución crea `/etc/streamhub/api.env` (con un `JWT_SECRET_KEY` aleatorio ya generado) y se detiene. Complétalo:

```bash
sudo nano /etc/streamhub/api.env
```
```ini
ENVIRONMENT=production
CORS_ORIGINS=http://streamhub-frontend-XXXX.s3-website-us-east-1.amazonaws.com
DB_HOST=streamhub-db.xxxxx.us-east-1.rds.amazonaws.com
DB_PORT=5432
DB_NAME=streamhub
DB_USER=streamhub_admin
DB_PASSWORD=<tu-contraseña-de-RDS>
DB_SSLMODE=require
AWS_REGION=us-east-1
S3_VIDEOS_BUCKET=streamhub-videos-XXXX
S3_THUMBNAILS_BUCKET=streamhub-thumbnails-XXXX
```
> ⚠️ `CORS_ORIGINS` debe coincidir **exactamente** con la URL del sitio (con `http://`, sin `/` final).

Vuelve a ejecutar el script; ahora aplica las migraciones (crea las tablas en RDS), configura systemd + Nginx y hace un *health check*:
```bash
sudo REPO_URL=https://github.com/<usuario>/<repo>.git bash /tmp/streamhub/backend/deploy/setup_ec2.sh
```

Abre **`http://<IP-ELASTICA>/docs`** 🎉

### 5.3 Verificaciones útiles (y buenas capturas de evidencia)
```bash
# Diagnóstico completo: IAM Role, RDS y los 2 buckets (subir/leer/borrar)
cd /opt/streamhub/backend && sudo -u streamhub .venv/bin/python -m app.diagnostics

systemctl status streamhub-api --no-pager       # servicio activo
curl -s http://127.0.0.1/health                 # {"status":"ok","database":"ok"}
sudo journalctl -u streamhub-api -f             # logs en vivo

# Tablas creadas en RDS:
set -a; sudo cat /etc/streamhub/api.env > /tmp/e; source /tmp/e; rm /tmp/e; set +a
PGPASSWORD=$DB_PASSWORD psql "host=$DB_HOST dbname=$DB_NAME user=$DB_USER sslmode=require" -c '\dt'
PGPASSWORD=$DB_PASSWORD psql "host=$DB_HOST dbname=$DB_NAME user=$DB_USER sslmode=require" \
  -c 'SELECT id, title, views, user_id FROM videos;'
```

### 5.4 Actualizar tras un `git push`
```bash
sudo REPO_URL=https://github.com/<usuario>/<repo>.git bash /opt/streamhub/backend/deploy/setup_ec2.sh
```

---

## 6. SPA en S3 (Bucket Frontend)

La URL de la API se **incrusta al compilar**, así que defínela antes del build.

### Opción A — Script (Linux/macOS/Git Bash)
```bash
cd frontend
BUCKET=streamhub-frontend-XXXX VITE_API_URL=http://<IP-ELASTICA> bash scripts/deploy-s3.sh
```

### Opción B — Manual (Windows / consola web)
```powershell
cd frontend
"VITE_API_URL=http://<IP-ELASTICA>" | Out-File -Encoding utf8 .env.production.local
npm install
npm run build
```
En la consola de S3 → `streamhub-frontend-XXXX` → **Upload** → arrastra **el contenido** de `dist/` (el archivo `index.html` y la carpeta `assets/`), **no** la carpeta `dist` en sí. No subas `src/`, `node_modules/` ni `package.json`.

Abre el **Bucket website endpoint**. 📸 *Evidencia: objetos del bucket (solo `index.html`, `favicon.svg`, `assets/`).*

---

## 7. Prueba funcional (checklist)

1. Registro → redirige al inicio con sesión iniciada.
2. Perfil → publicar 3 videos (MP4 + miniatura). Ver barra de progreso.
3. Principal → aparecen con miniatura, título, autor, vistas y fecha.
4. Reproductor → el video se reproduce y se puede adelantar; aumentan las vistas; comentar; recomendados a la derecha.
5. Perfil → editar título/miniatura, eliminar un video (se borra también de S3: compruébalo en la consola).
6. Recargar la página en `/watch/1` → sigue funcionando (Error document = `index.html`).

---

## 8. Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| En el navegador: *blocked by CORS policy* | `CORS_ORIGINS` no coincide | Copia la URL exacta del sitio, sin `/` final → `sudo systemctl restart streamhub-api` |
| `502 Bad Gateway` | La API no arrancó | `sudo journalctl -u streamhub-api -n 50` (normalmente una variable mal escrita en `api.env`) |
| `/health` → 503 o timeout de BD | SG de RDS mal configurado / `DB_NAME` inexistente | Regla 5432 con origen `sg-streamhub-api`; crear la BD `streamhub` |
| `502` al subir / `AccessDenied` en logs | Instancia sin IAM Role o política con nombres de bucket incorrectos | EC2 → Actions → Security → *Modify IAM role* |
| `413 Request Entity Too Large` | Video > 100 MB | Comprimir el video; el límite está en Nginx y en la API |
| 403/404 al recargar una ruta de la SPA | Falta *Error document* | Static website hosting → Error document: `index.html` |
| La SPA llama a `localhost:8000` | Se compiló sin `VITE_API_URL` | Recompilar con la variable y volver a subir `dist/` |
| *Mixed content* | Sitio en HTTPS y API en HTTP | Usa ambos en HTTP (S3 website) o ambos en HTTPS (CloudFront + ALB/ACM) |
| El video no carga tras ~1 hora con la pestaña abierta | La URL prefirmada expiró | Recargar la página (se generan URLs nuevas) |

---

## 9. Costos y limpieza

Con capa gratuita el costo es casi nulo, pero **al terminar la evaluación** elimina: instancia EC2, **Elastic IP** (cobra si queda sin asociar), instancia RDS (sin snapshot final si no la necesitas), y vacía/borra los 3 buckets.
