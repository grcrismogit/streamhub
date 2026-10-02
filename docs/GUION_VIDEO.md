# Guion del video explicativo (8–10 minutos)

Graba en 1080p con OBS (pantalla + micrófono). Ten abiertas de antemano todas las pestañas: SPA, `/docs`, consola de AWS (EC2, RDS, S3, IAM), terminal SSH y el repositorio.

| Min. | Sección | Qué mostrar | Qué decir (idea) |
|---|---|---|---|
| 0:00 | **Presentación** | Portada del README | Nombre, materia, objetivo: plataforma de videos con React, FastAPI y AWS. |
| 0:30 | **Arquitectura** | Diagrama del README | Recorre el flujo: SPA desde S3 → API en EC2 → RDS para datos → S3 para archivos. Explica por qué los buckets de medios son privados y se usan URLs prefirmadas. |
| 1:30 | **Código — backend** | `app/` en el editor | Capas (routes, schemas, models, services). Muestra `config.py` (todo por variables de entorno), `storage.py` (validación por *magic bytes*, subida a S3) y `security.py` (Argon2 + JWT). |
| 3:00 | **Código — frontend** | `src/pages` | Las 4 páginas y el cliente `api/`. Menciona la barra de progreso y el manejo de sesión. |
| 3:45 | **Infraestructura** | Consola AWS | EC2 (IAM role, SG, IP elástica) → RDS (no público, SG solo desde la API) → 3 buckets → política IAM de mínimo privilegio. |
| 5:00 | **Demo** | SPA | Registro → login → publicar video (progreso) → catálogo → reproducir → comentar → recomendados → perfil: editar y eliminar. |
| 7:30 | **Prueba de integración** | S3 + `psql` + `/docs` | Muestra el `.mp4` nuevo en S3, la fila en `videos` en RDS y un endpoint probado en Swagger. Tras eliminar, demuestra que el objeto desapareció de S3. |
| 8:30 | **Calidad** | Terminal / GitHub | `pytest` (26 pruebas) y el CI en verde. |
| 9:00 | **Cierre** | README → Mejoras futuras | Lecciones aprendidas y mejoras (HTTPS con CloudFront/ALB, Secrets Manager, HLS). |

**Tips:** sube primero 2–3 videos con miniaturas bonitas para que el catálogo se vea lleno; usa videos cortos (<20 MB) para que la subida en vivo sea rápida; oculta contraseñas y el archivo `api.env` al grabar.
