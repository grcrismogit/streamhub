# Evidencias de la entrega — StreamHub

Completa cada fila y guarda las capturas en `docs/evidencias/` con el nombre sugerido.
Consejo: en cada captura de la consola de AWS deja visible la **región** y el **nombre del recurso**.

## Enlaces

| Entregable | Valor |
|---|---|
| Repositorio | `https://github.com/<usuario>/<repo>` |
| URL pública de la SPA | `http://streamhub-frontend-XXXX.s3-website-us-east-1.amazonaws.com` |
| URL pública de FastAPI | `http://<IP-ELASTICA>/docs` |
| Video explicativo | `https://...` |

## Infraestructura

| # | Evidencia | Qué debe verse | Archivo |
|---|---|---|---|
| 1 | **EC2** | Instancia *Running*, tipo, IP elástica, SG `sg-streamhub-api`, **IAM role** asociado | `01-ec2.png` |
| 2 | EC2 por SSH | `systemctl status streamhub-api` activo y `curl /health` → ok | `02-ec2-servicio.png` |
| 3 | IAM Role + conexión | `python -m app.diagnostics` con todo en ✔ (IAM Role, RDS, S3 videos, S3 miniaturas) | `03-diagnostico.png` |
| 4 | **RDS** | `streamhub-db` *Available*, PostgreSQL, endpoint, **Publicly accessible: No**, SG `sg-streamhub-db` | `04-rds.png` |
| 5 | RDS — datos | `psql ... -c '\dt'` y `SELECT` de `videos` con filas reales | `05-rds-tablas.png` |
| 6 | Security Groups | Reglas de entrada de ambos SG (5432 solo desde `sg-streamhub-api`) | `06-security-groups.png` |
| 7 | **S3 — 3 buckets** | Lista con `frontend`, `videos`, `thumbnails` | `07-s3-buckets.png` |
| 8 | S3 Frontend | Solo `index.html`, `favicon.svg`, `assets/` + *Static website hosting* activado | `08-s3-frontend.png` |
| 9 | S3 Videos | Objetos `.mp4` en `videos/<user_id>/` · *Block public access: On* | `09-s3-videos.png` |
| 10 | S3 Miniaturas | Objetos `.jpg/.png` en `thumbnails/<user_id>/` | `10-s3-miniaturas.png` |
| 11 | Swagger | `/docs` con todos los endpoints | `11-docs.png` |

## Funcionamiento

| # | Funcionalidad | Cómo evidenciarlo | Archivo |
|---|---|---|---|
| 12 | **Registro** | Formulario lleno → redirección con sesión iniciada | `12-registro.png` |
| 13 | **Login** | Cerrar sesión e iniciar de nuevo · (extra) error con contraseña incorrecta | `13-login.png` |
| 14 | **Catálogo** | Página principal con miniatura, título, usuario, vistas y fecha | `14-catalogo.png` |
| 15 | **Reproducción** | Video reproduciéndose (barra de progreso avanzada) | `15-reproduccion.png` |
| 16 | **Comentarios** | Comentario publicado en la lista | `16-comentarios.png` |
| 17 | **Recomendados** | Panel lateral con otros videos; clic → cambia de video | `17-recomendados.png` |
| 18 | **Perfil** | Datos del usuario, nº de videos publicados y lista | `18-perfil.png` |
| 19 | **Publicación** | Barra de progreso + mensaje de éxito + archivo nuevo en S3 | `19-publicacion.png` |
| 20 | Editar video | Modal de edición y título actualizado | `20-editar.png` |
| 21 | Eliminar video | Confirmación y video ausente en la lista **y** en S3 | `21-eliminar.png` |
| 22 | DevTools → Network | Llamadas a `http://<IP>/videos` con `200` (prueba que los datos vienen de FastAPI) | `22-network.png` |

## Calidad (opcional, suma puntos)

| # | Evidencia | Archivo |
|---|---|---|
| 23 | `pytest` → 26 pruebas pasando | `23-tests.png` |
| 24 | GitHub Actions en verde | `24-ci.png` |
