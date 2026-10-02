# Matriz de cumplimiento — requisito por requisito

✅ = implementado y probado en local (pruebas automáticas + navegador). ☁️ = se completa al desplegar en AWS (ver `DEPLOY_AWS.md`).

## 1. SPA en React (solo 4 páginas)

| Requisito | Estado | Dónde |
|---|:---:|---|
| React + Vite | ✅ | `frontend/` (React 19, Vite, TypeScript) |
| Exactamente 4 páginas | ✅ | `src/App.tsx`: `/login`, `/`, `/watch/:id`, `/profile` (cualquier otra ruta redirige a `/`) |
| **P1** Crear cuenta e iniciar sesión (nombre, correo, contraseña) | ✅ | `pages/AuthPage.tsx` → `POST /users`, `POST /login` |
| **P2** Videos dinámicos con miniatura, título, usuario, vistas y fecha | ✅ | `pages/HomePage.tsx` + `components/VideoCard.tsx` → `GET /videos` |
| **P2** Datos obtenidos desde FastAPI | ✅ | `src/api/` (todas las llamadas usan `VITE_API_URL`) |
| **P3** Video, título, descripción, usuario, vistas | ✅ | `pages/PlayerPage.tsx` → `GET /videos/{id}`, `POST /videos/{id}/view` |
| **P3** Comentarios | ✅ | `GET/POST /videos/{id}/comments` |
| **P3** Recomendados cargados desde la API | ✅ | `GET /videos/{id}/recommended` |
| **P4** Info básica, cantidad de videos, lista de videos | ✅ | `pages/ProfilePage.tsx` → `GET /users/me`, `GET /videos?user_id=` |
| **P4** Publicar / consultar / actualizar / eliminar | ✅ | `VideoUploadForm`, lista "Mis videos", `EditVideoForm` (`PUT`), modal de borrado (`DELETE`) |

## 2. Amazon S3 (3 buckets)

| Requisito | Estado | Dónde |
|---|:---:|---|
| Bucket Frontend solo con el contenido de `dist/` | ✅ ☁️ | `frontend/scripts/deploy-s3.sh` sube `dist/` (no `src/`, `node_modules/`, `package.json`) |
| Bucket Videos: solo MP4, ≤ 100 MB | ✅ | Validación por extensión + *magic bytes* + tamaño en `services/storage.py`; Nginx limita a 110 MB |
| Bucket Miniaturas: JPG, JPEG, PNG | ✅ | Ídem; además validación en el navegador (`lib/validation.ts`) |

## 3. API FastAPI en EC2

| Endpoint | Estado |
|---|:---:|
| `POST /users` · `POST /login` · `GET /users/{id}` | ✅ |
| `POST /videos` · `GET /videos` · `GET /videos/{id}` · `PUT /videos/{id}` · `DELETE /videos/{id}` | ✅ |
| `POST /videos/{id}/comments` · `GET /videos/{id}/comments` | ✅ |
| Documentación en `/docs` | ✅ |
| Desplegada en EC2 | ☁️ `backend/deploy/setup_ec2.sh` (systemd + Nginx) |

Extras: `GET /users/me`, `GET /videos/{id}/recommended`, `POST /videos/{id}/view`, `GET /health`.

## 4. Base de datos en RDS

| Entidad / campo pedido | Estado | Columna |
|---|:---:|---|
| Usuario: id, name, email, password_hash | ✅ | `users` (+ `created_at`) |
| Video: id, title, description, video_url, thumbnail_url, views, user_id | ✅ | `videos` (+ `video_key`, `thumbnail_key`, `created_at`, `updated_at`) |
| Comentario: id, content, user_id, video_id, created_at | ✅ | `comments` |
| RDS solo datos estructurados; archivos en S3 | ✅ | RDS guarda URLs/keys; los binarios van a S3 |
| PostgreSQL en RDS | ☁️ | Migración `alembic/versions/0001_initial.py` |

## 5. Despliegue y configuración

| Requisito | Estado | Cómo |
|---|:---:|---|
| `dist/` → S3 Frontend | ☁️ | Static website hosting + bucket policy de solo lectura |
| FastAPI → EC2 | ☁️ | `setup_ec2.sh` |
| Videos/Miniaturas → S3 | ✅ ☁️ | Buckets privados + URLs prefirmadas |
| **Variables de entorno** | ✅ | `app/core/config.py` lee `/etc/streamhub/api.env`; frontend usa `VITE_API_URL` |
| **IAM Roles** | ✅ ☁️ | boto3 usa el Instance Profile; `infra/aws/iam-ec2-s3-policy.json` (mínimo privilegio) |
| **Security Groups** | ☁️ | `sg-streamhub-api` (80, 22 desde tu IP) y `sg-streamhub-db` (5432 solo desde `sg-streamhub-api`) |
| Sin credenciales en el código | ✅ | `grep -rn "aws_secret\|password=" backend/app` no encuentra valores; `.env` en `.gitignore`; `python -m app.diagnostics` avisa si no se usa un IAM Role |

## 6. Entrega

Ver `docs/EVIDENCIAS.md` (24 capturas) y `docs/GUION_VIDEO.md`.
